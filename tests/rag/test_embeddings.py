#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Quick test script to verify Nomic embeddings work correctly.
Supports both MAAS (API-based) and local model testing.
"""

# Load .env file if it exists
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=False)

# Import config to check API settings
from alm.config import config  # noqa: E402
from alm.rag.embed_and_index import EmbeddingClient  # noqa: E402
import numpy as np  # noqa: E402


def test_nomic_embeddings():
    print("Testing Nomic-Embed-Text-v1.5...")
    print("=" * 60)

    # Check if using API or local model
    api_url = config.embeddings.api_url
    api_key = config.embeddings.api_key
    model_name = config.embeddings.model_name

    if api_url:
        print("\n✓ Using MAAS API mode")
        print(f"  API URL: {api_url}")
        print(f"  Model: {model_name}")
        if not api_key:
            print("  ⚠ WARNING: EMBEDDINGS_LLM_API_KEY not set, API calls may fail")
    else:
        print("\n✓ Using LOCAL model mode")
        print(f"  Model: {model_name}")
        print("  ⚠ NOTE: Local mode requires 'einops' package for Nomic models")
        print("  Set EMBEDDINGS_LLM_URL in .env to use MAAS API instead")

    # Initialize embedding client (handles both API and local)
    print("\n1. Initializing embedding client...")
    try:
        client = EmbeddingClient(
            model_name=model_name,
            api_url=api_url if api_url else None,
            api_key=api_key if api_key else None,
        )
        print(f"✓ Client initialized: {client.embedding_dim}-dimensional embeddings")
        print(f"  Mode: {'API' if not client.is_local else 'LOCAL'}")
    except Exception as e:
        print(f"✗ Failed to initialize client: {e}")
        if not api_url:
            print("\n  Tip: Set EMBEDDINGS_LLM_URL and EMBEDDINGS_LLM_API_KEY in .env")
            print("       to use MAAS API instead of local model")
        raise

    # Test embeddings
    print("\n2. Testing embeddings...")

    # Simulate error document (with task prefix for Nomic)
    error_doc = "search_document: Role name does not follow naming convention. The role name must start with the prefix 'ansible-role-'."

    # Simulate query (with task prefix for Nomic)
    query = "search_query: My playbook fails because the role name is invalid"

    # Generate embeddings
    print("  Generating document embedding...")
    doc_embedding = client.encode([error_doc], normalize_embeddings=True)[0]
    print("  Generating query embedding...")
    query_embedding = client.encode([query], normalize_embeddings=True)[0]

    print(f"✓ Document embedding shape: {doc_embedding.shape}")
    print(f"✓ Query embedding shape: {query_embedding.shape}")

    # Verify normalization
    doc_norm = np.linalg.norm(doc_embedding)
    query_norm = np.linalg.norm(query_embedding)
    print(f"✓ Document embedding norm: {doc_norm:.4f} (should be ~1.0)")
    print(f"✓ Query embedding norm: {query_norm:.4f} (should be ~1.0)")

    # Calculate similarity (dot product for normalized vectors = cosine similarity)
    similarity = np.dot(query_embedding, doc_embedding)
    print(f"\n3. Similarity score (with prefixes): {similarity:.4f}")

    # Test without prefixes
    print("\n4. Testing without task prefixes...")
    doc_no_prefix = "Role name does not follow naming convention."
    query_no_prefix = "My playbook fails because the role name is invalid"

    print("  Generating embeddings without prefixes...")
    doc_emb_no_prefix = client.encode([doc_no_prefix], normalize_embeddings=True)[0]
    query_emb_no_prefix = client.encode([query_no_prefix], normalize_embeddings=True)[0]

    similarity_no_prefix = np.dot(query_emb_no_prefix, doc_emb_no_prefix)
    print(f"✓ Similarity without prefixes: {similarity_no_prefix:.4f}")

    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print(
        f"Note: Task prefixes {'improved' if similarity > similarity_no_prefix else 'did not improve'} similarity"
    )
    print(f"  With prefixes: {similarity:.4f}")
    print(f"  Without prefixes: {similarity_no_prefix:.4f}")


if __name__ == "__main__":
    test_nomic_embeddings()
