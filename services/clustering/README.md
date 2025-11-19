# Clustering Service

FastAPI microservice for clustering predictions with support for local models and model registries.

## API

**POST `/predict`** - Make predictions
```json
// Request
{"features": [1.0, 2.0, 3.0, 4.0]}

// Response  
{"prediction": [0]}
```

## Configuration

| Variable | Default |
|----------|---------|
| `MODEL_REGISTRY_NAMESPACE` | `rhoai-model-registries` |
| `MODEL_REGISTRY_CONTAINER` | `modelregistry-sample` |

