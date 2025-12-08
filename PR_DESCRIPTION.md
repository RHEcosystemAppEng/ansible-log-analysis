# Enable Embedding Service for Local Deployment

## Problem

Local deployments were attempting to use the production embedding service endpoint, resulting in 403 authentication errors and RAG functionality failures.

## Solution

Added the text-embeddings-inference (TEI) service to local docker-compose and configured the backend to use it.

## Changes

- **Added `alm-embedding` service** to `deploy/local/compose.yaml`
  - Uses pre-loaded TEI image with nomic-embed-text-v1.5 model
  - Exposed on port 8080
  - Configured with proper health checks (180s start period for model loading)

- **Updated backend configuration** in docker-compose
  - Forces `EMBEDDINGS_LLM_URL=http://alm-embedding:8080` for Docker deployments
  - Overrides any production URL from `.env` file

- **Fixed port conflict**
  - Changed loki-mcp-server host port from 8080 to 8081

- **Enhanced Makefile**
  - Added `embedding` target to start the service
  - Added `wait-for-embedding` target that waits for service readiness (checks every 60s, up to 5 minutes)
  - Added `test-embedding` target for quick testing
  - Updated `start` target to wait for embedding service before starting backend

- **Fixed LogLabels JSON serialization**
  - Convert Pydantic model to dict before saving to database

- **Fixed Loki healthcheck**
  - Loki container is a minimal/scratch-based image without shell tools (`/bin/sh`, `wget`, `curl`)
  - Replaced `CMD-SHELL` healthcheck with binary-based check using `/usr/bin/loki -version`
  - Changed `loki-mcp-server` dependency from `service_healthy` to `service_started` to avoid blocking on healthcheck
  - This allows Loki to start successfully without requiring shell tools for health verification

## Testing

```bash
# Test embedding service
make local/test-embedding

# Full local deployment (waits for embedding service)
make local/install
```

## Notes

- Embedding service requires ~8Gi memory and takes 3-5 minutes to load the model
- For local backend development (outside Docker), set `EMBEDDINGS_LLM_URL=http://localhost:8080` in `.env`

