# Text Embeddings Inference (TEI) Chart

This chart deploys a custom TEI service with pre-downloaded `nomic-ai/nomic-embed-text-v1.5` model.

## Features

- **Pre-downloaded Model**: Model is baked into the container image, eliminating download time on startup
- **HuggingFace Cache**: Uses `/data` as cache directory (mounted from PVC)
- **Optimized Resources**: Memory and CPU limits tuned for actual usage
- **OpenAI-compatible API**: Works with existing embedding client code

## Image Building

The custom TEI image must be built and pushed before deployment:

```bash
cd services/text-embeddings-inference
docker build -t quay.io/rh-ai-quickstart/tei-nomic-preloaded:latest -f Dockerfile .
docker push quay.io/rh-ai-quickstart/tei-nomic-preloaded:latest
```

## Configuration

Key configuration options in `values.yaml`:

- `image.repository`: Container image repository (default: `quay.io/rh-ai-quickstart/tei-nomic-preloaded`)
- `image.tag`: Image tag (default: `latest`)
- `env.MODEL_ID`: Model identifier (default: `nomic-ai/nomic-embed-text-v1.5`)
- `service.port`: Service port (default: `8080`)
- `resources`: CPU and memory limits/requests
- `persistence.enabled`: Enable PVC for HuggingFace cache (default: `true`)

## Integration

The backend service is automatically configured to use this embedding service:
- Model is hardcoded to `nomic-ai/nomic-embed-text-v1.5` (no config needed)
- `EMBEDDINGS_LLM_URL`: Optional, defaults to `http://alm-embedding:8080` if not set

## Testing

Test the service:

```bash
# Health check
curl http://alm-embedding:8080/health

# Generate embeddings
curl -X POST http://alm-embedding:8080/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nomic-ai/nomic-embed-text-v1.5",
    "input": ["search_document: document text", "search_query: query text"]
  }'
```

