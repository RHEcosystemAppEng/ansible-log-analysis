# Text Embeddings Inference (TEI) Helm Chart

This Helm chart deploys the text-embeddings-inference service for generating text embeddings using the `nomic-ai/nomic-embed-text-v1.5` model.

## Overview

Text-embeddings-inference (TEI) is a production-ready embedding service written in Rust, optimized for high-performance embedding generation. It uses an OpenAI-compatible API format.

## Features

- **Production-ready**: Optimized Rust implementation
- **OpenAI-compatible API**: Easy integration with existing code
- **Automatic batching**: Handles batch requests efficiently
- **Task prefix support**: Supports nomic model task prefixes (search_document, search_query, etc.)
- **Scalable**: Can be scaled horizontally with HPA

## Model Configuration

The chart is configured to use `nomic-ai/nomic-embed-text-v1.5` by default. This model:
- Supports task instruction prefixes (search_document, search_query, clustering, classification)
- Has 768-dimensional embeddings (full) or can use Matryoshka dimensions (512, 256, 128, 64)
- Requires task prefixes for optimal performance

## API Usage

The service exposes an OpenAI-compatible API at `/embeddings`:

```bash
curl -X POST http://alm-embedding:8080/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nomic-ai/nomic-embed-text-v1.5",
    "input": ["search_document: document text", "search_query: query text"]
  }'
```

## Configuration

Key configuration options in `values.yaml`:

- `config.modelID`: The model to use (default: `nomic-ai/nomic-embed-text-v1.5`)
- `service.port`: Service port (default: 8080)
- `resources`: CPU and memory limits/requests
- `replicaCount`: Number of replicas
- `autoscaling`: Horizontal pod autoscaling configuration

## Integration

The backend service is automatically configured to use this embedding service via:
- `EMBEDDINGS_LLM_URL`: Set to `http://alm-embedding:8080` by default
- `EMBEDDINGS_LLM_MODEL_NAME`: Set to `nomic-ai/nomic-embed-text-v1.5`

## Health Checks

The service provides health check endpoints:
- `/health`: Liveness and readiness probe endpoint

## Resources

Recommended resource allocation:
- **CPU**: 500m request, 2000m limit
- **Memory**: 2Gi request, 4Gi limit

Adjust based on your workload and cluster capacity.

## Model Caching

The chart includes persistent volume support for model caching:

- **Persistent Volume Claim**: Automatically created when `persistence.enabled: true`
- **Storage**: 5Gi by default (enough for model + cache)
- **Access Mode**: ReadWriteOnce (RWO)
- **Cache Location**: `/data` (configured via `HF_HOME` environment variable)

**Benefits:**
- Model is downloaded once and cached between pod restarts
- Faster pod startup (loads from cache instead of re-downloading)
- Reduces network usage and startup time

**First Deployment:**
- Pod starts → Downloads model from HuggingFace (~2-5 minutes) → Caches to PVC → Ready

**Subsequent Restarts:**
- Pod starts → Loads model from PVC cache (~30 seconds) → Ready

## Notes

- The model is downloaded automatically on first startup and cached to persistent storage
- Task prefixes (search_document:, search_query:) are handled automatically by the backend
- The service uses ClusterIP by default (internal cluster access only)
- Model cache persists across pod restarts when persistence is enabled

