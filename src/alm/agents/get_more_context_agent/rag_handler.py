import os
import logging
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)


class RAGHandler:
    """
    Handles RAG (Retrieval-Augmented Generation) operations for retrieving
    relevant context from the knowledge base.

    Uses lazy loading singleton pattern to ensure the FAISS index is loaded
    only once and reused across requests.
    """

    _instance: Optional["RAGHandler"] = None
    _pipeline = None
    _enabled: Optional[bool] = None

    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super(RAGHandler, cls).__new__(cls)
        return cls._instance

    def _initialize_rag_pipeline(self):
        """
        Initialize RAG pipeline with lazy loading (singleton pattern).
        This ensures the FAISS index is loaded only once and reused across requests.

        Returns:
            AnsibleErrorQueryPipeline instance or None if RAG is disabled/failed
        """
        # Check if already initialized
        if self._enabled is not None:
            return self._pipeline

        # Check if RAG is enabled via environment variable
        rag_enabled_env = os.getenv("RAG_ENABLED", "true").lower()
        if rag_enabled_env not in ["true", "1", "yes"]:
            logger.info("RAG is disabled (RAG_ENABLED=%s)", rag_enabled_env)
            self._enabled = False
            self._pipeline = None
            return None

        try:
            logger.info("Initializing RAG pipeline (lazy loading)...")

            from alm.rag.query_pipeline import AnsibleErrorQueryPipeline

            # Get configuration from environment variables
            top_k = int(os.getenv("RAG_TOP_K", "10"))
            top_n = int(os.getenv("RAG_TOP_N", "3"))
            similarity_threshold = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.6"))

            # Initialize pipeline (this loads the FAISS index)
            self._pipeline = AnsibleErrorQueryPipeline(
                top_k=top_k,
                top_n=top_n,
                similarity_threshold=similarity_threshold,
            )

            self._enabled = True
            logger.info(
                "✓ RAG pipeline initialized successfully with %d errors in index",
                len(self._pipeline.embedder.error_store),
            )

            return self._pipeline

        except FileNotFoundError as e:
            logger.warning("RAG index not found: %s", e)
            logger.warning(
                "RAG functionality disabled - proceeding without cheat sheet context"
            )
            self._enabled = False
            self._pipeline = None
            return None

        except Exception as e:
            logger.error("Failed to initialize RAG pipeline: %s", e, exc_info=True)
            logger.warning(
                "RAG functionality disabled - proceeding without cheat sheet context"
            )
            self._enabled = False
            self._pipeline = None
            return None

    def _format_rag_results(self, response) -> str:
        """
        Format RAG query results into a structured string for LLM context.

        Args:
            response: QueryResponse from RAG pipeline

        Returns:
            Formatted string with error solutions
        """
        if not response.results:
            return "No matching solutions found in knowledge base."

        output = ["## Relevant Error Solutions from Knowledge Base\n"]

        for i, result in enumerate(response.results, 1):
            output.append(f"### Error {i}: {result.error_title}")
            output.append(f"**Confidence Score:** {result.similarity_score:.2f}\n")

            if result.sections.description:
                output.append("**Description:**")
                output.append(result.sections.description)
                output.append("")

            if result.sections.symptoms:
                output.append("**Symptoms:**")
                output.append(result.sections.symptoms)
                output.append("")

            if result.sections.resolution:
                output.append("**Resolution:**")
                output.append(result.sections.resolution)
                output.append("")

            if result.sections.code:
                output.append("**Code Example:**")
                output.append(f"```\n{result.sections.code}\n```")
                output.append("")

            output.append("---\n")

        return "\n".join(output)

    async def get_cheat_sheet_context(self, log_summary: str) -> str:
        """
        Retrieve relevant context from the RAG knowledge base for solving the error.

        This function:
        1. Lazily initializes the RAG pipeline (loads FAISS index on first call)
        2. Queries the knowledge base with the log summary
        3. Formats the results for LLM consumption
        4. Returns empty string if RAG is disabled or fails

        Args:
            log_summary: Summary of the Ansible error log

        Returns:
            Formatted string with relevant error solutions, or empty string if unavailable
        """
        logger.info("Retrieving cheat sheet context for log summary")

        # Initialize RAG pipeline (lazy loading)
        pipeline = self._initialize_rag_pipeline()

        if pipeline is None:
            logger.debug("RAG pipeline not available, returning empty context")
            return ""

        try:
            # Query the RAG system
            logger.debug(
                "Querying RAG system with log summary: %s...", log_summary[:100]
            )
            response = pipeline.query(log_summary)

            # Format results
            formatted_context = self._format_rag_results(response)

            logger.info(
                "✓ Retrieved %d relevant errors from knowledge base (search time: %.2fms)",
                response.metadata["num_results"],
                response.metadata["search_time_ms"],
            )

            return formatted_context

        except Exception as e:
            logger.error("Error querying RAG system: %s", e, exc_info=True)
            logger.warning("Proceeding without cheat sheet context")
            return ""
