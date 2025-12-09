.PHONY: deploy start stop status help postgres phoenix loki-stack backend ui annotation health logs restart clean stop-postgres stop-phoenix stop-loki-stack
.DEFAULT_GOAL := help

include ../../.env
export $(shell sed 's/=.*//' ../../.env | xargs)

COMPOSE_CMD := $(shell command -v docker-compose 2>/dev/null || command -v podman-compose 2>/dev/null)

train: run-whole-training-pipeline
training: run-whole-training-pipeline

uninstall: stop

install: start
deploy: start

help: ## Show this help message
	@echo "🚀 Ansible Log Monitor - Local Deployment"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'
	@echo ""
	@echo "📚 RAG Setup:"
	@echo "  1. Place PDF files in data/knowledge_base/"
	@echo "  2. Run 'make run-whole-training-pipeline' to build RAG index"
	@echo "  3. Ensure RAG_ENABLED=true in .env file"
	@echo ""


start: stop ## 🚀 Start all services locally
	@echo "🚀 Starting local deployment of Ansible Log Monitor..."
	@echo "🔌 Cleaning up any existing processes..."
	@$(MAKE) -s postgres
	@echo "   Waiting for PostgreSQL to be ready..."
	@$(MAKE) -s phoenix
	@$(MAKE) -s loki-stack
	@$(MAKE) -s embedding
	@echo "   ⚠️  Note: Embedding service may take 3-5 minutes to load the model"
	@echo "   You can check status with: make local/test-embedding"
	@$(MAKE) -s backend
	@$(MAKE) -s ui
	@$(MAKE) -s annotation
	@echo ""
	@echo "🎉 All services are running!"
	@sleep 8
	@$(MAKE) -s status
	@echo ""
	@echo "Press Ctrl+C to stop all services, or run 'make stop'"
	@bash -c 'trap "exit" SIGINT SIGTERM; while true; do sleep 5; done'

postgres: ## 📊 Start PostgreSQL database
	@echo "   Starting PostgreSQL database..."
	@$(COMPOSE_CMD) -f compose.yaml up -d postgres

phoenix: ## 📊 Start Phoenix
	@echo "   Starting Phoenix..."
	@$(COMPOSE_CMD) -f compose.yaml up -d phoenix

loki-stack: ## 📊 Start Loki stack (Loki, Loki MCP Server, Grafana, Promtail)
	@echo "   Starting Loki stack (Loki, Loki MCP Server, Grafana, Promtail)..."
	@$(COMPOSE_CMD) -f compose.yaml up -d loki loki-mcp-server grafana promtail

embedding: ## 🤖 Start Embedding Service (TEI)
	@echo "   Starting Embedding Service (TEI)..."
	@$(COMPOSE_CMD) -f compose.yaml up -d alm-embedding

wait-for-embedding: ## ⏳ Wait for embedding service to be ready (optional, for manual use)
	@echo "   Waiting for embedding service to be ready (this may take 3-5 minutes for model loading)..."
	@timeout=300; \
	elapsed=0; \
	interval=60; \
	while [ $$elapsed -lt $$timeout ]; do \
		if curl -s -f http://localhost:8080/health >/dev/null 2>&1; then \
			echo "   ✓ Embedding service is ready!"; \
			exit 0; \
		fi; \
		echo "   ⏳ Still waiting... ($$elapsed/$$timeout seconds)"; \
		sleep $$interval; \
		elapsed=$$((elapsed + interval)); \
	done; \
	echo "   ⚠️  Warning: Embedding service did not become ready within $$timeout seconds"; \
	echo "   The service may still be loading the model. Check logs with: docker-compose logs alm-embedding"; \
	exit 0

backend: ## ⚙️ Start Backend (FastAPI)
	@echo "   Starting Backend API..."
	@cd ../.. && uv run uvicorn alm.main_fastapi:app --reload &

ui: ## 🖥️ Start UI (Gradio)
	@echo "   Starting UI Interface..."
	@cd ../../ui && uv run gradio app.py &

annotation: ## 🏷️ Start Annotation UI (Gradio)  
	@echo "   Starting Annotation UI..."
	@cd ../.. && uv run gradio annotation_interface/app.py &


stop: ## 🛑 Stop all services
	@echo "🛑 Stopping all services..."
	@echo "🔧 Using: $(COMPOSE_CMD)"
	@$(MAKE) -s stop-loki-stack
	@$(MAKE) -s stop-postgres
	@$(MAKE) -s stop-phoenix
	@$(MAKE) -s stop-embedding
	@$(MAKE) -s kill-ports
	@echo "👋 All services stopped"

stop-postgres: ## 🛑 Stop PostgreSQL database
	@$(COMPOSE_CMD) -f compose.yaml down postgres
	@echo "   ✓ PostgreSQL stopped"

stop-phoenix: ## 🛑 Stop Phoenix
	@$(COMPOSE_CMD) -f compose.yaml down phoenix
	@echo "   ✓ Phoenix stopped"

stop-loki-stack: ## 🛑 Stop Loki stack (Loki, Loki MCP Server, Grafana, Promtail)
	@$(COMPOSE_CMD) -f compose.yaml down loki-mcp-server grafana promtail loki
	@echo "   ✓ Loki stack stopped"

stop-embedding: ## 🛑 Stop Embedding Service
	@$(COMPOSE_CMD) -f compose.yaml down alm-embedding
	@echo "   ✓ Embedding service stopped"

kill-ports: ## 🔌 Kill processes using required ports
	@fuser -k 7860/tcp || true
	@echo "   ✓ UI 7860 killed"
	@fuser -k 7861/tcp || true
	@echo "   ✓ Annotation 7861 killed"
	@fuser -k 8000/tcp || true
	@echo "   ✓ Backend 8000 killed"
	@fuser -k 6006/tcp || true
	@echo "   ✓ Phoenix 6006 killed"
	@fuser -k 4317/tcp || true
	@echo "   ✓ Phoenix 4317 killed"
	@fuser -k 3100/tcp || true
	@echo "   ✓ Loki 3100 killed"
	@fuser -k 8081/tcp || true
	@echo "   ✓ Loki MCP Server 8081 killed"
	@fuser -k 8080/tcp || true
	@echo "   ✓ Embedding service 8080 killed"
	@fuser -k 3000/tcp || true
	@echo "   ✓ Grafana 3000 killed"

status: ## 📊 Show status of all services
	@echo "📊 Service Status:"
	@echo "   📊 PostgreSQL: $(shell $(COMPOSE_CMD) ps 2>/dev/null | grep 'postgres' | grep -q 'Up' && echo 'Running' || echo 'Stopped') - localhost:5432"
	@echo "   🐍 Phoenix: $(shell $(COMPOSE_CMD) ps 2>/dev/null | grep 'phoenix' | grep -q 'Up' && echo 'Running' || echo 'Stopped') - http://localhost:6006"
	@echo "   📊 Loki: $(shell $(COMPOSE_CMD) ps 2>/dev/null | grep 'loki' | grep -v 'loki-mcp' | grep -q 'Up' && echo 'Running' || echo 'Stopped') - http://localhost:3100"
	@echo "   🔍 Loki MCP Server: $(shell $(COMPOSE_CMD) ps 2>/dev/null | grep 'loki-mcp-server' | grep -q 'Up' && echo 'Running' || echo 'Stopped') - http://localhost:8081"
	@echo "   🤖 Embedding Service: $(shell $(COMPOSE_CMD) ps 2>/dev/null | grep 'alm-embedding' | grep -q 'Up' && echo 'Running' || echo 'Stopped') - http://localhost:8080"
	@echo "   📈 Grafana: $(shell $(COMPOSE_CMD) ps 2>/dev/null | grep 'grafana' | grep -q 'Up' && echo 'Running' || echo 'Stopped') - http://localhost:3000"
	@echo "   📝 Promtail: $(shell $(COMPOSE_CMD) ps 2>/dev/null | grep 'promtail' | grep -q 'Up' && echo 'Running' || echo 'Stopped')"
	@if lsof -i :8000 >/dev/null 2>&1; then \
		echo "   ⚙️  Backend API: Running - http://localhost:8000"; \
	else \
		echo "   ⚙️  Backend API: Stopped - http://localhost:8000"; \
	fi
	@if lsof -i :7860 >/dev/null 2>&1; then \
		echo "   🖥️  UI Interface: Running - http://localhost:7860"; \
	else \
		echo "   🖥️  UI Interface: Stopped - http://localhost:7860"; \
	fi
	@if lsof -i :7861 >/dev/null 2>&1; then \
		echo "   🏷️  Annotation UI: Running - http://localhost:7861"; \
	else \
		echo "   🏷️  Annotation UI: Stopped - http://localhost:7861"; \
	fi
	@if curl -s http://localhost:6006 >/dev/null 2>&1; then \
		echo "   🐍  Phoenix: Running - http://localhost:6006"; \
	else \
		echo "   🐍  Phoenix: Stopped - http://localhost:6006"; \
	fi

run-whole-training-pipeline: ## 🔍 Run whole training pipeline (builds RAG index)
	@echo "🔍 Running whole training pipeline..."
	@echo "📚 This will build the RAG index from PDFs in data/knowledge_base/"
	@if [ ! -d "../../data/knowledge_base" ] || [ -z "$$(ls -A ../../data/knowledge_base/*.pdf 2>/dev/null)" ]; then \
		echo "⚠️  WARNING: No PDF files found in data/knowledge_base/"; \
		echo "   RAG index will not be created. Add PDF files and run again."; \
	fi
	@( cd ../.. && uv run init_pipeline.py )

# Add new target to check RAG status
rag-status: ## 📊 Check RAG index status
	@echo "📊 RAG Index Status:"
	@if [ -f "../../data/ansible_errors.index" ] && [ -f "../../data/error_metadata.pkl" ]; then \
		echo "   ✅ RAG index exists"; \
		ls -lh ../../data/ansible_errors.index ../../data/error_metadata.pkl; \
	else \
		echo "   ❌ RAG index not found"; \
		echo "   Run 'make run-whole-training-pipeline' to build it"; \
	fi
	@if [ -d "../../data/knowledge_base" ]; then \
		pdf_count=$$(ls -1 ../../data/knowledge_base/*.pdf 2>/dev/null | wc -l); \
		echo "   📄 PDF files in knowledge_base: $$pdf_count"; \
	else \
		echo "   ⚠️  Knowledge base directory not found"; \
	fi

test-embedding: ## 🧪 Test embedding service
	@echo "🧪 Testing Embedding Service..."
	@echo ""
	@echo "1. Health Check:"
	@if curl -s -f http://localhost:8080/health >/dev/null 2>&1; then \
		echo "   ✅ Service is healthy"; \
	else \
		echo "   ❌ Service is not responding"; \
		exit 1; \
	fi
	@echo ""
	@echo "2. Generating test embedding:"
	@response=$$(curl -s -X POST http://localhost:8080/v1/embeddings \
		-H "Content-Type: application/json" \
		-d '{"model": "nomic-ai/nomic-embed-text-v1.5", "input": ["test query"]}'); \
	if echo "$$response" | grep -q '"data"'; then \
		echo "   ✅ Embedding generated successfully"; \
		echo "   Response preview: $$(echo $$response | head -c 200)..."; \
	else \
		echo "   ❌ Failed to generate embedding"; \
		echo "   Response: $$response"; \
		exit 1; \
	fi
	@echo ""
	@echo "✅ Embedding service test passed!"

test-rag: ## 🧪 Test RAG system (requires RAG index)
	@echo "🧪 Testing RAG System..."
	@if [ ! -f "../../data/ansible_errors.index" ]; then \
		echo "❌ RAG index not found. Run 'make run-whole-training-pipeline' first."; \
		exit 1; \
	fi
	@echo "Running RAG test script..."
	@(cd ../.. && uv run python tests/rag/test_embeddings.py)

health: ## 🔍 Check health of running services
	@echo "🔍 Health Checks:"
	@if curl -s http://localhost:8000/health >/dev/null 2>&1; then \
		echo "   ⚙️  Backend http://localhost:8000: Healthy"; \
	else \
		echo "   ⚙️  Backend http://localhost:8000: Unhealthy"; \
	fi
	@if curl -s http://localhost:7860 >/dev/null 2>&1; then \
		echo "   🖥️  UI http://localhost:7860: Healthy"; \
	else \
		echo "   🖥️  UI http://localhost:7860: Unhealthy"; \
	fi
	@if curl -s http://localhost:7861 >/dev/null 2>&1; then \
		echo "   🏷️  Annotation UI http://localhost:7861: Healthy"; \
	else \
		echo "   🏷️  Annotation UI http://localhost:7861: Unhealthy"; \
	fi
	@if curl -s http://localhost:6006 >/dev/null 2>&1; then \
		echo "   🐍  Phoenix: Running - http://localhost:6006"; \
	else \
		echo "   🐍  Phoenix: Stopped - http://localhost:6006"; \
	fi
	@if curl -s http://localhost:3100/ready >/dev/null 2>&1; then \
		echo "   📊  Loki http://localhost:3100: Healthy"; \
	else \
		echo "   📊  Loki http://localhost:3100: Unhealthy"; \
	fi
	@if curl -s http://localhost:8081 >/dev/null 2>&1; then \
		echo "   🔍  Loki MCP Server http://localhost:8081: Healthy"; \
	else \
		echo "   🔍  Loki MCP Server http://localhost:8081: Unhealthy"; \
	fi
	@if curl -s http://localhost:8080/health >/dev/null 2>&1; then \
		echo "   🤖  Embedding Service http://localhost:8080: Healthy"; \
	else \
		echo "   🤖  Embedding Service http://localhost:8080: Unhealthy (may still be loading model)"; \
	fi
	@if curl -s http://localhost:3000 >/dev/null 2>&1; then \
		echo "   📈  Grafana http://localhost:3000: Healthy"; \
	else \
		echo "   📈  Grafana http://localhost:3000: Unhealthy"; \
	fi
restart: stop start ## 🔄 Restart all services

clean: ## 🧹 Clean PID files and logs
	@echo "🧹 Cleaning up PID files and logs..."
	@docker-compose down -v
	@echo "   ✓ Cleanup completed"
