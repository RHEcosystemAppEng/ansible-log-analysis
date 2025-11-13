.PHONY: deploy start stop status help postgres backend ui annotation health logs restart clean
.DEFAULT_GOAL := help

include ../../.env
export $(shell sed 's/=.*//' ../../.env | xargs)

train: run-whole-training-pipeline
training: run-whole-training-pipeline

install: start ## Install all services (alias for start)

deploy: start ## Deploy all services (alias for start)

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
	@docker-compose -f compose.yaml up -d postgres

phoenix: ## 📊 Start Phoenix	
	@echo "   Starting Phoenix..."
	@docker-compose -f compose.yaml up -d phoenix

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
	@$(MAKE) -s stop-postgres
	@$(MAKE) -s stop-phoenix
	@$(MAKE) -s kill-ports
	@echo "👋 All services stopped"

stop-postgres: ## 🛑 Stop PostgreSQL database
	@docker-compose -f compose.yaml down postgres
	@echo "   ✓ PostgreSQL stopped"

stop-phoenix: ## 🛑 Stop Phoenix
	@docker-compose -f compose.yaml down phoenix
	@echo "   ✓ Phoenix stopped"

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

status: ## 📊 Show status of all services
	@echo "📊 Service Status:"
	@echo "   📊 PostgreSQL: $(shell docker-compose ps -q postgres >/dev/null 2>&1 && echo 'Running' || echo 'Stopped') - localhost:5432"
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
restart: stop start ## 🔄 Restart all services

clean: ## 🧹 Clean PID files and logs
	@echo "🧹 Cleaning up PID files and logs..."
	@echo "   ✓ Cleanup completed"
