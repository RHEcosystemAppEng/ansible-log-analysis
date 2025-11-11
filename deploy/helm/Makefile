# Makefile for Ansible Log Monitor Deployment
# Replaces the original deploy.sh script with additional uninstall functionality

MAKEFLAGS += --no-print-directory

# Default values
NAMESPACE ?= $(shell oc project -q 2>/dev/null || echo "default")
# OPENAI_API_TOKEN = 
OPENAI_API_ENDPOINT ?= https://llama-4-scout-17b-16e-w4a16-maas-apicast-production.apps.prod.rhoai.rh-aiservices-bu.com:443/v1
OPENAI_MODEL ?= llama-4-scout-17b-16e-w4a16
OPENAI_TEMPERATURE ?= 0.7
ANSIBLE_LOG_MONITOR_CHART := ansible-log-monitor

# Parameter validation functions
define check_namespace
	@echo "Using namespace: $(NAMESPACE)"
endef

# Function to prompt for OpenAI credentials
define prompt_openai_credentials
	@bash -c '\
	DEFAULT_ENDPOINT="$(OPENAI_API_ENDPOINT)"; \
	DEFAULT_MODEL="$(OPENAI_MODEL)"; \
	DEFAULT_TEMP="$(OPENAI_TEMPERATURE)"; \
	NAMESPACE_VAR="$(NAMESPACE)"; \
	echo "============================================"; \
	echo "   LLM API Configuration Required"; \
	echo "============================================"; \
	echo ""; \
	if [ -z "$$OPENAI_API_TOKEN" ]; then \
		echo -n "Enter MaaS LLM API TOKEN: "; \
		read -s OPENAI_API_TOKEN_INPUT; \
		echo ""; \
		export OPENAI_API_TOKEN=$$OPENAI_API_TOKEN_INPUT; \
	else \
		echo "Using provided OPENAI_API_TOKEN"; \
	fi; \
	if [ -z "$$OPENAI_API_ENDPOINT" ]; then \
		echo -n "Enter MaaS LLM API ENDPOINT (include /v1 suffix) [default: $$DEFAULT_ENDPOINT]: "; \
		read OPENAI_API_ENDPOINT_INPUT; \
		if [ -z "$$OPENAI_API_ENDPOINT_INPUT" ]; then \
			export OPENAI_API_ENDPOINT="$$DEFAULT_ENDPOINT"; \
		else \
			export OPENAI_API_ENDPOINT=$$OPENAI_API_ENDPOINT_INPUT; \
		fi; \
	else \
		echo "Using provided OPENAI_API_ENDPOINT: $$OPENAI_API_ENDPOINT"; \
	fi; \
	if [ -z "$$OPENAI_MODEL" ]; then \
		echo -n "Enter MaaS LLM MODEL NAME [default: $$DEFAULT_MODEL]: "; \
		read OPENAI_MODEL_INPUT; \
		if [ -z "$$OPENAI_MODEL_INPUT" ]; then \
			export OPENAI_MODEL="$$DEFAULT_MODEL"; \
		else \
			export OPENAI_MODEL=$$OPENAI_MODEL_INPUT; \
		fi; \
	else \
		echo "Using provided OPENAI_MODEL: $$OPENAI_MODEL"; \
	fi; \
	if [ -z "$$OPENAI_TEMPERATURE" ]; then \
		echo -n "Enter LLM TEMPERATURE [default: $$DEFAULT_TEMP]: "; \
		read OPENAI_TEMPERATURE_INPUT; \
		if [ -z "$$OPENAI_TEMPERATURE_INPUT" ]; then \
			export OPENAI_TEMPERATURE="$$DEFAULT_TEMP"; \
		else \
			export OPENAI_TEMPERATURE=$$OPENAI_TEMPERATURE_INPUT; \
		fi; \
	else \
		echo "Using provided OPENAI_TEMPERATURE: $$OPENAI_TEMPERATURE"; \
	fi; \
	echo ""; \
	echo "============================================"; \
	echo "   RAG Embedding API Configuration"; \
	echo "============================================"; \
	echo ""; \
	echo "Configure MAAS embedding API for RAG (Retrieval Augmented Generation)"; \
	echo ""; \
	if [ -z "$$EMBEDDINGS_LLM_API_KEY" ]; then \
		echo -n "Enter MaaS EMBEDDING API KEY [press Enter to use same as LLM]: "; \
		read -s EMBEDDINGS_API_KEY_INPUT; \
		echo ""; \
		if [ -z "$$EMBEDDINGS_API_KEY_INPUT" ]; then \
			export EMBEDDINGS_LLM_API_KEY=$$OPENAI_API_TOKEN; \
			echo "Using same token as LLM"; \
		else \
			export EMBEDDINGS_LLM_API_KEY=$$EMBEDDINGS_API_KEY_INPUT; \
		fi; \
	else \
		echo "Using provided EMBEDDINGS_LLM_API_KEY"; \
	fi; \
	if [ -z "$$EMBEDDINGS_LLM_URL" ]; then \
		echo -n "Enter MaaS EMBEDDING API ENDPOINT (include /v1 suffix): "; \
		read EMBEDDINGS_URL_INPUT; \
		export EMBEDDINGS_LLM_URL=$$EMBEDDINGS_URL_INPUT; \
	else \
		echo "Using provided EMBEDDINGS_LLM_URL: $$EMBEDDINGS_LLM_URL"; \
	fi; \
	if [ -z "$$EMBEDDINGS_LLM_MODEL_NAME" ]; then \
		echo -n "Enter EMBEDDING MODEL NAME [default: nomic-ai/nomic-embed-text-v1.5]: "; \
		read EMBEDDINGS_MODEL_INPUT; \
		if [ -z "$$EMBEDDINGS_MODEL_INPUT" ]; then \
			export EMBEDDINGS_LLM_MODEL_NAME="nomic-ai/nomic-embed-text-v1.5"; \
		else \
			export EMBEDDINGS_LLM_MODEL_NAME=$$EMBEDDINGS_MODEL_INPUT; \
		fi; \
	else \
		echo "Using provided EMBEDDINGS_LLM_MODEL_NAME: $$EMBEDDINGS_LLM_MODEL_NAME"; \
	fi; \
	echo ""; \
	echo "Creating Kubernetes secret '\''model-secret'\''..."; \
	oc create secret generic model-secret \
		--from-literal=OPENAI_API_TOKEN=$$OPENAI_API_TOKEN \
		--from-literal=OPENAI_API_ENDPOINT=$$OPENAI_API_ENDPOINT \
		--from-literal=OPENAI_MODEL=$$OPENAI_MODEL \
		--from-literal=OPENAI_TEMPERATURE=$$OPENAI_TEMPERATURE \
		--from-literal=EMBEDDINGS_LLM_API_KEY=$$EMBEDDINGS_LLM_API_KEY \
		--from-literal=EMBEDDINGS_LLM_URL=$$EMBEDDINGS_LLM_URL \
		--from-literal=EMBEDDINGS_LLM_MODEL_NAME=$$EMBEDDINGS_LLM_MODEL_NAME \
		-n "$$NAMESPACE_VAR" --dry-run=client -o yaml | oc apply -f -; \
	echo "Secret '\''model-secret'\'' created successfully"; \
	echo ""'
endef

env_args = \
	-f ansible-log-monitor/global-values.yaml \
	-f ansible-log-monitor/values.yaml

# Default target
.PHONY: help
help:
	@echo "Ansible Log Monitor - OpenShift Deployment"
	@echo "=========================================="
	@echo ""
	@echo "Available Commands:"
	@echo "  install                    Deploy the application (prompts for OpenAI credentials)"
	@echo "  upgrade                    Upgrade the application (prompts for OpenAI credentials)"
	@echo "  uninstall                  Remove the application"
	@echo "  namespace                  Create/switch to namespace"
	@echo "  port-forward-ui           Forward UI service to localhost:7860"
	@echo "  port-forward-backend      Forward Backend service to localhost:8000"
	@echo "  port-forward-annotation   Forward Annotation Interface to localhost:7861"
	@echo "  port-forward-grafana      Forward Grafana to localhost:3000"
	@echo ""
	@echo "Usage Examples:"
	@echo "  make install                              # Will prompt for credentials"
	@echo "  make install NAMESPACE=ansible-logs      # Will prompt for credentials"
	@echo "  make upgrade                              # Will prompt for credentials"
	@echo "  make uninstall"
	@echo "  make port-forward-ui"
	@echo ""
	@echo "Configuration Variables:"
	@echo "  NAMESPACE                  OpenShift namespace (default: current project)"
	@echo "  OPENAI_API_TOKEN          MaaS API Token (will prompt if not provided)"
	@echo "  OPENAI_API_ENDPOINT       AI API endpoint (will prompt if not provided, defaults to llama-4-scout)"
	@echo "  OPENAI_MODEL              AI model to use (will prompt if not provided, default: llama-4-scout-17b-16e-w4a16)"
	@echo "  OPENAI_TEMPERATURE        AI temperature setting (will prompt if not provided, default: 0.7)"
	@echo ""
	@echo "Note: All commands use the current OpenShift project by default."
	@echo "      Use NAMESPACE=your-namespace to override."
	@echo "      The install/upgrade commands will create a 'model-secret' with OpenAI configuration."



# Create namespace/project and deploy (NAMESPACE optional, defaults to current project)
.PHONY: namespace
namespace:
	$(call check_namespace)
	@echo "Setting up project $(NAMESPACE)..."
	@oc new-project $(NAMESPACE) 2>/dev/null || oc project $(NAMESPACE) 2>/dev/null || true
	@oc label namespace $(NAMESPACE) app=ansible-log-monitor --overwrite
	@echo "Project $(NAMESPACE) ready"

# Install the application (NAMESPACE optional, defaults to current project)
.PHONY: install
install: namespace
	$(call prompt_openai_credentials)
	@echo "Installing Ansible Log Monitor in namespace $(NAMESPACE)..."
	@oc project $(NAMESPACE)
	@helm install alm ./ansible-log-monitor -n $(NAMESPACE) $(env_args)
	@echo "Ansible Log Monitor installed"

# Uninstall the deployment and clean up (NAMESPACE optional, defaults to current project)
.PHONY: uninstall
uninstall: 
	$(call check_namespace)
	@echo "Uninstalling Ansible Log Monitor from namespace $(NAMESPACE)..."
	@helm uninstall alm -n $(NAMESPACE)
	@echo "Removing model-secret if it exists..."
	@oc delete secret model-secret -n $(NAMESPACE) --ignore-not-found
	@echo "Ansible Log Monitor uninstalled"

# Upgrade 
.PHONY: upgrade
upgrade:
	$(call check_namespace)
	$(call prompt_openai_credentials)
	@echo "Upgrading Ansible Log Monitor in namespace $(NAMESPACE)..."
	@helm upgrade alm ./ansible-log-monitor -n $(NAMESPACE) $(env_args)
	@echo "Ansible Log Monitor upgraded"

# Restart
.PHONY: restart
restart: uninstall install
	$(call check_namespace)
	@echo "Restarting Ansible Log Monitor in namespace $(NAMESPACE)..."
	@echo "Ansible Log Monitor restarted"

# Port forwarding helpers (NAMESPACE optional, defaults to current project)
.PHONY: port-forward-ui
port-forward-ui:
	$(call check_namespace)
	@echo "🔗 Forwarding UI service to localhost:7860..."
	@oc port-forward -n $(NAMESPACE) svc/ui 7860:7860

.PHONY: port-forward-backend
port-forward-backend:
	$(call check_namespace)
	@echo "🔗 Forwarding Backend service to localhost:8000..."
	@oc port-forward -n $(NAMESPACE) svc/backend 8000:8000

.PHONY: port-forward-annotation
port-forward-annotation:
	$(call check_namespace)
	@echo "🔗 Forwarding Annotation Interface to localhost:7861..."
	@oc port-forward -n $(NAMESPACE) svc/annotation-interface 7861:7861

.PHONY: port-forward-grafana
port-forward-grafana:
	$(call check_namespace)
	@echo "🔗 Forwarding Grafana to localhost:3000..."
	@oc port-forward -n $(NAMESPACE) svc/grafana 3000:3000
