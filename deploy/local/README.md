# Local Deployment

Make sure you have updated the environment variable as defined here: [Local deployment](../../README.md#deploy-locally)

## Components

The local deployment includes:
- **PostgreSQL** - Database for storing processed alerts
- **Phoenix** - Observability and tracing
- **Loki Stack** - Loki, Loki MCP Server, Grafana, Promtail for log aggregation
- **AAP Mock** - Mock Ansible Automation Platform log generator (for testing)
- **Backend** - FastAPI application with LangGraph workflow
- **UI** - Gradio user interface
- **Annotation UI** - Annotation tool for improving AI workflow

## Available Operations

### Most Used Commands
| Command | Description |
|---------|-------------|
| `make start` | Start all services (PostgreSQL, Loki, AAP Mock, Backend API, UI, Annotation UI) |
| `make stop` | Stop all services and clean up |
| `make status` | Show running status of all services |
| `make health` | Check health endpoints of running services |
| `make run-whole-training-pipeline` | Execute the complete training pipeline (builds RAG index) |


### Other Commands
| Command | Description |
|---------|-------------|
| `make help` | Show help message with all available targets |
| `make deploy` | Deploy all services (alias for start) |
| `make postgres` | Start PostgreSQL database only |
| `make phoenix` | Start Phoenix only |
| `make loki-stack` | Start Loki stack (Loki, Loki MCP Server, Grafana, Promtail) only |
| `make aap-mock` | Start AAP Mock (Log Generator) only |
| `make backend` | Start Backend API (FastAPI) only |
| `make ui` | Start UI Interface (Gradio) only |
| `make annotation` | Start Annotation UI (Gradio) only |
| `make stop-postgres` | Stop PostgreSQL database only |
| `make stop-phoenix` | Stop Phoenix only |
| `make stop-loki-stack` | Stop Loki stack only |
| `make stop-aap-mock` | Stop AAP Mock only |
| `make kill-ports` | Kill processes using required ports |
| `make rag-status` | Check RAG index status |
| `make restart` | Restart all services |
| `make clean` | Clean volumes and logs |

## Service URLs

Once started, services are available at:
- **Backend API**: http://localhost:8000
- **UI Interface**: http://localhost:7860
- **Annotation UI**: http://localhost:7861
- **Phoenix**: http://localhost:6006
- **Loki**: http://localhost:3100
- **Loki MCP Server**: http://localhost:8080
- **Grafana**: http://localhost:3000
- **AAP Mock**: http://localhost:8081
- **PostgreSQL**: localhost:5432

## Using AAP Mock

### Quick Start

```bash
# Start all services including AAP Mock
make start

# Check AAP Mock health
curl http://localhost:8081/healthz

# Check AAP Mock status
curl http://localhost:8081/api/status | jq

# Start log replay (100 logs/sec, loop)
curl -X POST "http://localhost:8081/api/logs/replay/all?rate=100&loop=true"

# Stop log replay
curl -X POST "http://localhost:8081/api/logs/stop-all"
```

### Verify Logs in Loki

```bash
# Query Loki for AAP Mock logs
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={job="aap-mock"}' \
  --data-urlencode "start=$(date -u -d '5 minutes ago' +%s)000000000" \
  --data-urlencode "end=$(date -u +%s)000000000" | jq
```

### View in Grafana

1. Open http://localhost:3000
2. Go to Explore
3. Select Loki as data source
4. Query: `{job="aap-mock"}`

## Troubleshooting

### Check Container Logs

```bash
# View AAP Mock logs
docker logs aap-mock -f

# Or with podman-compose
podman-compose logs aap-mock -f

# View Promtail logs
docker logs -f $(docker ps -q -f name=promtail)
```

### Rebuild AAP Mock Image

```bash
# Stop services
make stop

# Rebuild AAP Mock container
docker-compose build aap-mock

# Start services
make start
```

### Clear Volumes

```bash
# Stop all services
make stop

# Remove volumes
docker-compose down -v

# Start fresh
make start
```
