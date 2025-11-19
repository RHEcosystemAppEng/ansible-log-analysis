#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration management for Ansible Error RAG System.
Loads settings from .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class EmbeddingsConfig:
    """Configuration for embedding model."""

    def __init__(self):
        # Check if .env file exists - this is the only test
        env_path = Path(__file__).parent.parent.parent / ".env"
        env_file_exists = env_path.exists()

        # Get environment variables - raise error if not set
        self.model_name = self._get_required_env(
            "EMBEDDINGS_LLM_MODEL_NAME", env_file_exists
        ).strip()
        self.api_url = self._get_required_env(
            "EMBEDDINGS_LLM_URL", env_file_exists
        ).strip()
        self.api_key = self._get_required_env(
            "EMBEDDINGS_LLM_API_KEY", env_file_exists
        ).strip()

        # Validate that values are not empty after stripping
        self._validate_maas_config(env_file_exists)

    def _get_required_env(self, var_name: str, env_file_exists: bool) -> str:
        """
        Get a required environment variable, raising an error if not set.

        If .env file exists, requires the variable to be set (in .env or as env var).
        If .env file doesn't exist, assumes containerized environment and only checks env vars.

        Args:
            var_name: Name of the environment variable
            env_file_exists: Whether .env file exists

        Returns:
            The environment variable value

        Raises:
            ValueError: If the environment variable is not set
        """
        # load_dotenv() at module level already loaded .env file if it exists
        value = os.getenv(var_name)

        if value is None:
            env_example_path = Path(__file__).parent.parent.parent / ".env.example"

            if env_file_exists:
                # .env file exists - require variable to be set
                error_msg = (
                    f"{var_name} is required but not set. "
                    f"Please set {var_name} in your .env file or as an environment variable. "
                )
            else:
                # No .env file - assume containerized environment
                error_msg = (
                    f"{var_name} is required but not set. "
                    f"Please set {var_name} as an environment variable. "
                )

            if env_example_path.exists():
                error_msg += "See .env.example for reference."

            raise ValueError(error_msg)

        return value

    def _validate_maas_config(self, env_file_exists: bool):
        """
        Validate that MAAS configuration values are not empty.
        Raises an error if EMBEDDINGS_LLM_URL or EMBEDDINGS_LLM_API_KEY are empty.

        Args:
            env_file_exists: Whether .env file exists (for error message context)
        """
        env_example_path = Path(__file__).parent.parent.parent / ".env.example"
        example_hint = (
            " See .env.example for reference." if env_example_path.exists() else ""
        )

        if env_file_exists:
            location_hint = "in your .env file or as an environment variable"
        else:
            location_hint = "as an environment variable"

        if not self.api_url:
            raise ValueError(
                f"EMBEDDINGS_LLM_URL is required but is empty. "
                f"Please set EMBEDDINGS_LLM_URL {location_hint} with a valid value."
                + example_hint
            )
        if not self.api_key:
            raise ValueError(
                f"EMBEDDINGS_LLM_API_KEY is required but is empty. "
                f"Please set EMBEDDINGS_LLM_API_KEY {location_hint} with a valid value."
                + example_hint
            )
        if not self.model_name:
            raise ValueError(
                f"EMBEDDINGS_LLM_MODEL_NAME is required but is empty. "
                f"Please set EMBEDDINGS_LLM_MODEL_NAME {location_hint} with a valid value."
                + example_hint
            )

    @property
    def is_local(self) -> bool:
        """Check if using local model (not API-based)."""
        return not self.api_url

    @property
    def is_api(self) -> bool:
        """Check if using API-based embeddings."""
        return bool(self.api_url)

    @property
    def requires_api_key(self) -> bool:
        """Check if API key is required and missing."""
        return self.is_api and not self.api_key

    def validate(self):
        """Validate configuration."""
        if not self.model_name:
            raise ValueError("EMBEDDINGS_LLM_MODEL_NAME must be set")

        if self.is_api and not self.api_key:
            raise ValueError(
                f"EMBEDDINGS_LLM_API_KEY is required when using API endpoint: {self.api_url}"
            )

    def __repr__(self):
        return (
            f"EmbeddingsConfig(\n"
            f"  model_name={self.model_name}\n"
            f"  mode={'API' if self.is_api else 'LOCAL'}\n"
            f"  api_url={self.api_url or 'N/A'}\n"
            f"  api_key={'***' + self.api_key[-4:] if self.api_key else 'N/A'}\n"
            f")"
        )


class StorageConfig:
    """Configuration for data storage paths."""

    def __init__(self):
        self.data_dir = Path(os.getenv("DATA_DIR", "./data"))
        self.knowledge_base_dir = Path(
            os.getenv("KNOWLEDGE_BASE_DIR", "./data/knowledge_base")
        )

    @property
    def index_path(self) -> str:
        """Path to FAISS index file."""
        return str(self.data_dir / "ansible_errors.index")

    @property
    def metadata_path(self) -> str:
        """Path to metadata pickle file."""
        return str(self.data_dir / "error_metadata.pkl")

    def ensure_directories(self):
        """Create directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge_base_dir.mkdir(parents=True, exist_ok=True)

    def __repr__(self):
        return (
            f"StorageConfig(\n"
            f"  data_dir={self.data_dir}\n"
            f"  knowledge_base_dir={self.knowledge_base_dir}\n"
            f"  index_path={self.index_path}\n"
            f"  metadata_path={self.metadata_path}\n"
            f")"
        )


class Config:
    """Main configuration object."""

    def __init__(self):
        self.embeddings = EmbeddingsConfig()
        self.storage = StorageConfig()

    def validate(self):
        """Validate all configuration."""
        self.embeddings.validate()
        self.storage.ensure_directories()

    def print_config(self):
        """Print configuration summary."""
        print("=" * 70)
        print("CONFIGURATION")
        print("=" * 70)
        print(self.embeddings)
        print(self.storage)
        print("=" * 70)


# Global config instance
config = Config()


if __name__ == "__main__":
    # Test configuration loading
    config.print_config()
    config.validate()
    print("\n✓ Configuration validated successfully")
