#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ansible Error RAG System - Embedding and Indexing Module

This module implements:
- Groups chunks by error_id
- Creates composite embeddings (description + symptoms)
- Builds FAISS index for similarity search
- Persists index and metadata to disk

Uses TEI (text-embeddings-inference) service for embeddings.
Model is hardcoded to nomic-ai/nomic-embed-text-v1.5.
Service URL defaults to http://alm-embedding:8080 (can be overridden via EMBEDDINGS_LLM_URL).
"""

import os
import pickle
import numpy as np
import requests
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
from pathlib import Path

from langchain_core.documents import Document
import faiss

from alm.config import config


class EmbeddingClient:
    """
    Embedding client for text-embeddings-inference (TEI) service.

    Uses OpenAI-compatible API format. TEI doesn't require authentication
    for internal cluster deployments.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_url: Optional[str] = None,
    ):
        # Use hardcoded defaults from config
        self.model_name = model_name or config.embeddings.MODEL_NAME
        self.api_url = api_url or config.embeddings.api_url

        if not self.api_url:
            raise ValueError(
                "api_url is required. "
                "Please configure EMBEDDINGS_LLM_URL as an environment variable or in your .env file."
            )

        self._init_api_client()

    def _init_api_client(self):
        """Initialize TEI embedding client."""
        print(f"Initializing TEI embedding client: {self.api_url}")
        print(f"  Model: {self.model_name}")

        # Determine embedding dimension based on model
        # nomic-embed-text-v1.5 has 768 dimensions
        if "nomic" in self.model_name.lower():
            self.embedding_dim = 768
        else:
            self.embedding_dim = 768  # Default for nomic models

        print("✓ TEI client initialized")
        print(f"  Embedding dimension: {self.embedding_dim}")

    def encode(
        self,
        texts: List[str],
        normalize_embeddings: bool = True,
        show_progress_bar: bool = True,
    ) -> np.ndarray:
        """
        Encode texts to embeddings via TEI (text-embeddings-inference) API.

        Args:
            texts: List of texts to embed (may include task prefixes like "search_document:")
            normalize_embeddings: Whether to L2-normalize embeddings
            show_progress_bar: Unused (kept for API compatibility)

        Returns:
            Numpy array of embeddings
        """
        embeddings = self._encode_tei_api(texts)

        embeddings = np.array(embeddings)

        # Normalize if requested (TEI may normalize, but we handle it here for consistency)
        if normalize_embeddings:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            # Protect against division by zero - use np.maximum to ensure minimum norm of 1e-8
            # This prevents inf/nan values if TEI returns a zero vector (unlikely but possible)
            embeddings = embeddings / np.maximum(norms, 1e-8)

        return embeddings

    def _encode_tei_api(self, texts: List[str]) -> List[List[float]]:
        """
        Encode using text-embeddings-inference (OpenAI-compatible API).

        TEI supports task prefixes for nomic models:
        - search_document: for documents (already added in create_composite_embeddings)
        - search_query: for queries (added in query_pipeline)

        Texts passed here may already have prefixes, so we don't add them again.

        Batches requests to respect TEI's MAX_CLIENT_BATCH_SIZE limit (default: 16).
        """
        headers = {
            "Content-Type": "application/json",
        }

        # Ensure URL ends with /embeddings for OpenAI format
        url = self.api_url
        if not url.endswith("/embeddings"):
            url = url.rstrip("/") + "/embeddings"

        # TEI batch size limit (TEI MAX_CLIENT_BATCH_SIZE is 32, we use 30 to be safe)
        BATCH_SIZE = 30

        print(f"Calling TEI at: {url}")
        print(f"  Model: {self.model_name}")
        print(
            f"  Total texts: {len(texts)} (will be batched into chunks of {BATCH_SIZE})"
        )

        all_embeddings = []

        # Process texts in batches
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE

            print(
                f"  Processing batch {batch_num}/{total_batches} ({len(batch)} texts)..."
            )

            payload = {
                "model": self.model_name,
                "input": batch,
            }

            try:
                response = requests.post(
                    url, json=payload, headers=headers, timeout=120
                )

                if response.status_code != 200:
                    print(f"Response status: {response.status_code}")
                    print(f"Response body: {response.text[:500]}")

                response.raise_for_status()

                result = response.json()
                # OpenAI format: {"data": [{"embedding": [...]}, ...]}
                if "data" in result:
                    batch_embeddings = [item["embedding"] for item in result["data"]]
                # Alternative format: {"embeddings": [[...], ...]}
                elif "embeddings" in result:
                    batch_embeddings = result["embeddings"]
                else:
                    raise ValueError(f"Unexpected TEI response format: {result.keys()}")

                all_embeddings.extend(batch_embeddings)
                print(
                    f"  ✓ Batch {batch_num} completed ({len(batch_embeddings)} embeddings)"
                )

            except Exception as e:
                print(f"  ✗ Error in batch {batch_num}: {e}")
                raise

        print(f"✓ All batches completed ({len(all_embeddings)} total embeddings)")
        return all_embeddings


class AnsibleErrorEmbedder:
    """
    Handles embedding generation and FAISS index creation for Ansible errors.

    Uses TEI (text-embeddings-inference) service for embeddings.
    Model is hardcoded to nomic-ai/nomic-embed-text-v1.5.
    Service URL defaults to http://alm-embedding:8080 (can be overridden via EMBEDDINGS_LLM_URL).
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_url: Optional[str] = None,
        index_path: Optional[str] = None,
        metadata_path: Optional[str] = None,
    ):
        """
        Initialize the embedder.

        Args:
            model_name: Model name (defaults to hardcoded nomic-ai/nomic-embed-text-v1.5)
            api_url: API endpoint URL (defaults to config, which defaults to http://alm-embedding:8080)
            index_path: Path to save FAISS index (defaults to config)
            metadata_path: Path to save metadata (defaults to config)
        """
        # Use config values as defaults (model is hardcoded in config)
        self.model_name = model_name or config.embeddings.model_name
        self.api_url = api_url or config.embeddings.api_url
        self.index_path = index_path or config.storage.index_path
        self.metadata_path = metadata_path or config.storage.metadata_path

        # Validate configuration
        if not self.api_url:
            raise ValueError(
                "API URL is required. Please configure EMBEDDINGS_LLM_URL as an environment variable or in your .env file."
            )

        # Initialize embedding client (no API key needed for TEI)
        self.client = EmbeddingClient(model_name=self.model_name, api_url=self.api_url)
        self.embedding_dim = self.client.embedding_dim

        self.index = None
        self.error_store = {}

        print("✓ Embedder initialized")
        print("  Mode: TEI Service")

    def group_chunks_by_error(
        self, chunks: List[Document]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Group chunks by error_id and organize into structured format.

        Args:
            chunks: List of Document chunks from parser

        Returns:
            Dictionary mapping error_id to complete error data
        """
        print("\n" + "=" * 60)
        print("STEP:INGESTION - Grouping chunks by error_id")
        print("=" * 60)

        errors_by_id = defaultdict(
            lambda: {
                "error_id": None,
                "error_title": None,
                "sections": {},
                "metadata": {},
            }
        )

        # Track statistics per file
        file_stats = defaultdict(
            lambda: {"errors": set(), "sections": defaultdict(int)}
        )

        for chunk in chunks:
            error_id = chunk.metadata.get("error_id")
            section_type = chunk.metadata.get("section_type")
            source_file = chunk.metadata.get("source_file", "unknown")

            if not error_id or not section_type:
                continue

            # Track per-file statistics
            file_stats[source_file]["errors"].add(error_id)
            file_stats[source_file]["sections"][section_type] += 1

            # Initialize error entry
            if errors_by_id[error_id]["error_id"] is None:
                errors_by_id[error_id]["error_id"] = error_id
                errors_by_id[error_id]["error_title"] = chunk.metadata.get(
                    "error_title"
                )
                errors_by_id[error_id]["metadata"] = {
                    "source_file": chunk.metadata.get("source_file"),
                    "page": chunk.metadata.get("page"),
                }

            # Extract content (remove the header added by chunking)
            content = chunk.page_content
            # Remove "Error: X\n\nSection: Y\n\n" prefix
            lines = content.split("\n\n", 2)
            if len(lines) >= 3:
                content = lines[2]
            else:
                content = lines[-1]

            errors_by_id[error_id]["sections"][section_type] = content

        print(f"✓ Grouped {len(chunks)} chunks into {len(errors_by_id)} unique errors")

        # Print per-file statistics
        print("\n" + "-" * 60)
        print("Section distribution per file:")
        print("-" * 60)
        for source_file in sorted(file_stats.keys()):
            stats = file_stats[source_file]
            num_errors = len(stats["errors"])
            print(f"\n📄 {Path(source_file).name}:")
            print(f"   Total errors: {num_errors}")
            print("   Sections:")
            for section, count in sorted(stats["sections"].items()):
                print(f"     {section}: {count} errors")

        # Overall statistics
        section_counts = defaultdict(int)
        for error in errors_by_id.values():
            for section in error["sections"].keys():
                section_counts[section] += 1

        print("\n" + "-" * 60)
        print("Overall section distribution:")
        print("-" * 60)
        for section, count in sorted(section_counts.items()):
            print(f"  {section}: {count} errors")

        return dict(errors_by_id)

    def create_composite_embeddings(
        self, error_store: Dict[str, Dict[str, Any]]
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Create composite embeddings from description + symptoms for each error.

        Args:
            error_store: Dictionary of errors grouped by error_id

        Returns:
            Tuple of (embedding_matrix, error_ids)
        """
        print("\n" + "=" * 60)
        print("GENERATING COMPOSITE EMBEDDINGS")
        print("=" * 60)

        composite_texts = []
        error_ids = []
        skipped = 0

        # Determine if we should use task prefixes (for Nomic models)
        use_task_prefix = "nomic" in self.model_name.lower()

        for error_id, error_data in error_store.items():
            sections = error_data["sections"]

            # Extract description and symptoms
            description = sections.get("description", "").strip()
            symptoms = sections.get("symptoms", "").strip()

            # Skip errors without description or symptoms
            if not description and not symptoms:
                print(
                    f"⚠ Skipping error {error_data['error_title']}: No description or symptoms"
                )
                skipped += 1
                continue

            # Create composite text
            composite_parts = []
            if description:
                composite_parts.append(description)
            if symptoms:
                composite_parts.append(symptoms)

            composite_text = "\n\n".join(composite_parts)

            # Add task prefix for Nomic models
            if use_task_prefix:
                prefixed_text = f"search_document: {composite_text}"
            else:
                prefixed_text = composite_text

            # Store composite text in error_store for reference (without prefix)
            error_data["composite_text"] = composite_text

            composite_texts.append(prefixed_text)
            error_ids.append(error_id)

        print(f"✓ Created {len(composite_texts)} composite texts")
        if skipped > 0:
            print(f"⚠ Skipped {skipped} errors (missing description and symptoms)")

        if use_task_prefix:
            print("✓ Using task prefix: 'search_document:'")

        # Generate embeddings
        print(f"\nGenerating embeddings using {self.model_name}...")

        embeddings = self.client.encode(
            composite_texts, normalize_embeddings=True, show_progress_bar=True
        )

        print(f"✓ Generated embeddings: shape={embeddings.shape}")

        return embeddings, error_ids

    def build_faiss_index(
        self,
        embeddings: np.ndarray,
        error_ids: List[str],
        error_store: Dict[str, Dict[str, Any]],
    ):
        """Build FAISS index from embeddings."""
        print("\n" + "=" * 60)
        print("STEP:CREATING FAISS INDEX")
        print("=" * 60)

        # Verify embeddings are normalized
        norms = np.linalg.norm(embeddings, axis=1)
        print(
            f"Embedding norms: min={norms.min():.4f}, max={norms.max():.4f}, mean={norms.mean():.4f}"
        )

        # Create FAISS index
        print(f"Building FAISS IndexFlatIP with dimension {self.embedding_dim}...")
        self.index = faiss.IndexFlatIP(self.embedding_dim)

        # Add vectors to index
        self.index.add(embeddings)

        print(f"✓ Index created with {self.index.ntotal} vectors")

        # Create mapping from index position to error_id
        self.index_to_error_id = {i: error_id for i, error_id in enumerate(error_ids)}

        # Store only errors that have embeddings
        self.error_store = {error_id: error_store[error_id] for error_id in error_ids}

        print(f"✓ Stored metadata for {len(self.error_store)} errors")

    def save_index(self):
        """Persist FAISS index and metadata to disk."""
        print("\n" + "=" * 60)
        print("SAVING INDEX AND METADATA")
        print("=" * 60)

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

        # Save FAISS index
        faiss.write_index(self.index, self.index_path)
        index_size_mb = os.path.getsize(self.index_path) / (1024 * 1024)
        print(f"✓ FAISS index saved to: {self.index_path}")
        print(f"  Index size: {index_size_mb:.2f} MB")

        # Save metadata
        metadata = {
            "error_store": self.error_store,
            "index_to_error_id": self.index_to_error_id,
            "model_name": self.model_name,
            "api_url": self.api_url,
            "embedding_dim": self.embedding_dim,
            "total_errors": len(self.error_store),
        }

        with open(self.metadata_path, "wb") as f:
            pickle.dump(metadata, f)

        metadata_size_mb = os.path.getsize(self.metadata_path) / (1024 * 1024)
        print(f"✓ Metadata saved to: {self.metadata_path}")
        print(f"  Metadata size: {metadata_size_mb:.2f} MB")
        print(f"  Total storage: {index_size_mb + metadata_size_mb:.2f} MB")

    def load_index(self):
        """Load FAISS index and metadata from disk."""
        print("\n" + "=" * 60)
        print("LOADING INDEX AND METADATA")
        print("=" * 60)

        if not os.path.exists(self.index_path):
            raise FileNotFoundError(f"Index not found at {self.index_path}")

        self.index = faiss.read_index(self.index_path)
        print(f"✓ FAISS index loaded: {self.index.ntotal} vectors")

        if not os.path.exists(self.metadata_path):
            raise FileNotFoundError(f"Metadata not found at {self.metadata_path}")

        with open(self.metadata_path, "rb") as f:
            metadata = pickle.load(f)

        self.error_store = metadata["error_store"]
        self.index_to_error_id = metadata["index_to_error_id"]

        print(f"✓ Metadata loaded: {len(self.error_store)} errors")
        print(f"  Model: {metadata['model_name']}")

        if metadata["model_name"] != self.model_name:
            print("⚠ Warning: Model mismatch!")
            print(f"  Index: {metadata['model_name']}")
            print(f"  Current: {self.model_name}")

    def ingest_and_index(self, chunks: List[Document]):
        """Complete ingestion and indexing pipeline."""
        print("\n" + "=" * 70)
        print("ANSIBLE ERROR RAG SYSTEM - INGESTION AND INDEXING")
        print("=" * 70)

        error_store = self.group_chunks_by_error(chunks)
        embeddings, error_ids = self.create_composite_embeddings(error_store)
        self.build_faiss_index(embeddings, error_ids, error_store)
        self.save_index()

        print("\n" + "=" * 70)
        print("✓ INGESTION AND INDEXING COMPLETE")
        print("=" * 70)


def main():
    """Process all PDFs in knowledge_base directory."""
    from alm.rag.ingest_and_chunk import AnsibleErrorParser
    import glob

    # Print and validate configuration
    config.print_config()
    config.validate()

    print("\n" + "=" * 70)
    print("ANSIBLE ERROR KNOWLEDGE BASE - EMBEDDING AND INDEXING")
    print("=" * 70)

    # Initialize
    parser = AnsibleErrorParser()
    embedder = AnsibleErrorEmbedder()

    # Find PDFs
    pdf_files = sorted(glob.glob(str(config.storage.knowledge_base_dir / "*.pdf")))

    print(f"\nFound {len(pdf_files)} PDF files")
    for pdf in pdf_files:
        print(f"  - {os.path.basename(pdf)}")

    # Process all PDFs
    all_chunks = []
    for pdf_path in pdf_files:
        print(f"\nProcessing: {os.path.basename(pdf_path)}")
        chunks = parser.parse_pdf_to_chunks(pdf_path)
        all_chunks.extend(chunks)
        print(f"  ✓ {len(chunks)} chunks")

    print(f"\n{'=' * 70}")
    print(f"TOTAL: {len(all_chunks)} chunks from {len(pdf_files)} PDFs")
    print(f"{'=' * 70}")

    # Ingest and index
    embedder.ingest_and_index(all_chunks)

    return embedder


if __name__ == "__main__":
    embedder = main()
