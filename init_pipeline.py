import asyncio
from alm.pipeline.offline import whole_pipeline
from alm.utils.phoenix import register_phoenix
import os
import glob
import shutil
from pathlib import Path


def setup_data_directories():
    """
    Setup data directory structure in PVC mount path.
    Creates necessary directories and copies PDFs from image to PVC if needed.
    """
    from src.alm.config import config

    print("\n" + "=" * 70)
    print("SETTING UP DATA DIRECTORY STRUCTURE")
    print("=" * 70)

    # Get paths from config (uses DATA_DIR and KNOWLEDGE_BASE_DIR env vars)
    data_dir = Path(config.storage.data_dir)
    knowledge_base_dir = Path(config.storage.knowledge_base_dir)
    logs_dir = data_dir / "logs" / "failed"

    # Create necessary directories
    print("Creating directories...")
    data_dir.mkdir(parents=True, exist_ok=True)
    knowledge_base_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    print(f"  ✓ {data_dir}")
    print(f"  ✓ {knowledge_base_dir}")
    print(f"  ✓ {logs_dir}")

    # Copy PDFs from image to PVC if PVC knowledge_base is empty
    image_kb_dir = Path("/app/data/knowledge_base")
    pvc_kb_dir = knowledge_base_dir

    # Check if PVC knowledge_base has any PDFs
    pvc_pdfs = list(pvc_kb_dir.glob("*.pdf"))

    if not pvc_pdfs:
        # PVC is empty, copy from image if available
        if image_kb_dir.exists():
            image_pdfs = list(image_kb_dir.glob("*.pdf"))
            if image_pdfs:
                print(f"\nCopying {len(image_pdfs)} PDF file(s) from image to PVC...")
                for pdf_path in image_pdfs:
                    dest_path = pvc_kb_dir / pdf_path.name
                    try:
                        shutil.copy2(pdf_path, dest_path)
                        print(f"  ✓ Copied {pdf_path.name}")
                    except Exception as e:
                        print(f"  ✗ Error copying {pdf_path.name}: {e}")
                print("✓ Knowledge base PDFs copied to PVC")
            else:
                print(f"\n⚠ No PDFs found in image at {image_kb_dir}")
        else:
            print(f"\n⚠ Image knowledge base directory not found at {image_kb_dir}")
    else:
        print(
            f"\n✓ PVC knowledge base already contains {len(pvc_pdfs)} PDF file(s), skipping copy"
        )

    print("=" * 70)


def build_rag_index():
    """
    Build RAG index from knowledge base PDFs.
    This runs during the init job to create the FAISS index and metadata.
    """
    from src.alm.config import config
    from src.alm.rag.ingest_and_chunk import AnsibleErrorParser
    from src.alm.rag.embed_and_index import AnsibleErrorEmbedder

    # Check if RAG is enabled
    rag_enabled = os.getenv("RAG_ENABLED", "true").lower() == "true"
    if not rag_enabled:
        print("RAG is disabled (RAG_ENABLED=false), skipping RAG index build")
        return

    # Check if index already exists (skip rebuild for faster upgrades)
    index_path = Path(config.storage.index_path)
    metadata_path = Path(config.storage.metadata_path)

    if index_path.exists() and metadata_path.exists():
        print("✓ RAG index already exists, skipping rebuild")
        print(f"  Index: {index_path}")
        print(f"  Metadata: {metadata_path}")
        print("  To force rebuild, delete the PVC or these files")
        return

    print("\n" + "=" * 70)
    print("BUILDING RAG INDEX FROM KNOWLEDGE BASE")
    print("=" * 70)

    try:
        # Validate configuration
        config.print_config()
        config.validate()

        # Initialize components
        parser = AnsibleErrorParser()
        embedder = AnsibleErrorEmbedder()

        # Find PDFs in knowledge base
        kb_dir = config.storage.knowledge_base_dir
        pdf_files = sorted(glob.glob(str(kb_dir / "*.pdf")))

        if not pdf_files:
            print(f"⚠ WARNING: No PDF files found in {kb_dir}")
            print("  RAG index will not be created")
            return

        print(f"\n✓ Found {len(pdf_files)} PDF files in knowledge base:")
        for pdf in pdf_files:
            print(f"  - {Path(pdf).name}")

        # Process all PDFs
        all_chunks = []
        for pdf_path in pdf_files:
            print(f"\n📄 Processing: {Path(pdf_path).name}")
            try:
                chunks = parser.parse_pdf_to_chunks(pdf_path)
                all_chunks.extend(chunks)
                print(f"  ✓ Extracted {len(chunks)} chunks")
            except Exception as e:
                print(f"  ✗ Error processing {Path(pdf_path).name}: {e}")
                continue

        if not all_chunks:
            print("\n⚠ WARNING: No chunks extracted from PDFs")
            print("  RAG index will not be created")
            return

        print(f"\n{'=' * 70}")
        print(f"TOTAL: {len(all_chunks)} chunks from {len(pdf_files)} PDFs")
        print(f"{'=' * 70}")

        # Build and save index
        embedder.ingest_and_index(all_chunks)

        print("\n" + "=" * 70)
        print("✓ RAG INDEX BUILD COMPLETE")
        print("=" * 70)
        print(f"  Index: {index_path}")
        print(f"  Metadata: {metadata_path}")

    except Exception as e:
        print(f"\n✗ ERROR building RAG index: {e}")
        print("  The system will continue without RAG functionality")
        import traceback

        traceback.print_exc()


async def main():
    # Setup and initialization
    print("\n" + "=" * 70)
    print("ANSIBLE LOG MONITOR - INITIALIZATION PIPELINE")
    print("=" * 70)

    # Step 1: Setup data directories (create dirs, copy PDFs if needed)
    setup_data_directories()

    # Step 2: Build RAG index
    build_rag_index()

    # Step 3: Run main pipeline (clustering, summarization, etc.)
    print("\n" + "=" * 70)
    print("RUNNING MAIN PIPELINE")
    print("=" * 70)
    await whole_pipeline()

    print("\n" + "=" * 70)
    print("✓ INITIALIZATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    register_phoenix()
    asyncio.run(main())
