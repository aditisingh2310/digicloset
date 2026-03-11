# ========================================
# Shopify Fashion Recommendation Engine
# Makefile for common tasks
# ========================================

.PHONY: help install dev test build push deploy clean logs

# Variables
PYTHON := python3
PIP := pip3
DOCKER := docker
DOCKER_COMPOSE := docker-compose
IMAGE_NAME := shopify-recommendation-engine
IMAGE_TAG := latest
REGISTRY := your-registry

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Shopify Fashion Recommendation Engine"
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-30s %s\n", $$1, $$2}'
	@echo ""

# ========== SETUP & INSTALLATION ==========

install: ## Install dependencies
	$(PIP) install -r requirements.txt

install-dev: ## Install dependencies + dev tools
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-asyncio pytest-cov black flake8 mypy

# ========== DEVELOPMENT ==========

dev: ## Run development server with auto-reload
	$(PYTHON) main.py --reload

test: ## Run unit tests
	$(PYTHON) -m pytest test_recommendation_engine.py -v

test-cov: ## Run tests with coverage report
	$(PYTHON) -m pytest test_recommendation_engine.py --cov=ai_service --cov-report=html -v
	@echo "Coverage report generated in htmlcov/index.html"

lint: ## Run code linting (flake8)
	flake8 . --max-line-length=100 --exclude=venv,__pycache__

format: ## Format code with black
	black . --line-length=100

type-check: ## Run type checking with mypy
	mypy . --ignore-missing-imports

example: ## Run example script
	$(PYTHON) examples.py

# ========== DOCKER ==========

docker-build: ## Build Docker image
	$(DOCKER) build -t $(IMAGE_NAME):$(IMAGE_TAG) .
	@echo "✓ Image built: $(IMAGE_NAME):$(IMAGE_TAG)"

docker-run: ## Run Docker container
	$(DOCKER) run -p 8000:8000 \
	  -v recommendation-data:/data \
	  -e CLIP_MODEL_NAME=openai/clip-vit-base-patch32 \
	  $(IMAGE_NAME):$(IMAGE_TAG)

docker-clean: ## Remove Docker image
	$(DOCKER) rmi $(IMAGE_NAME):$(IMAGE_TAG)
	@echo "✓ Image removed: $(IMAGE_NAME):$(IMAGE_TAG)"

# ========== DOCKER COMPOSE ==========

compose-up: ## Start services with docker-compose
	$(DOCKER_COMPOSE) up -d
	@echo "✓ Services started"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"

compose-down: ## Stop services
	$(DOCKER_COMPOSE) down

compose-logs: ## View service logs
	$(DOCKER_COMPOSE) logs -f recommendation-engine

compose-restart: ## Restart services
	$(DOCKER_COMPOSE) restart recommendation-engine

compose-clean: ## Remove containers and volumes
	$(DOCKER_COMPOSE) down -v
	@echo "✓ Containers and volumes removed"

# ========== DEPLOYMENT ==========

deploy-local: install dev ## Deploy locally (install + dev server)

deploy-docker: docker-build docker-run ## Deploy with Docker

deploy-compose: compose-up ## Deploy with docker-compose

# ========== DATABASE & DATA ==========

clean-data: ## Remove indexed data
	rm -rf /tmp/recommendation_index/*
	@echo "✓ Index data cleared"

reset: clean-data ## Full reset (clear data and containers)
	$(DOCKER_COMPOSE) down -v
	@echo "✓ Full reset complete"

# ========== UTILITY ==========

shell: ## Open Python shell with imports
	$(PYTHON) -c "from ai_service.embeddings import CLIPEmbedder; from ai_service.vector_db import ProductVectorIndex; print('AI Service modules loaded'); import code; code.interact(local=locals())"

check-health: ## Check service health
	curl -s http://localhost:8000/api/v1/health | $(PYTHON) -m json.tool

docs: ## Open API documentation
	@echo "Opening API docs at http://localhost:8000/docs"
	@command -v xdg-open >/dev/null && xdg-open http://localhost:8000/docs || \
	command -v open >/dev/null && open http://localhost:8000/docs || \
	echo "Open http://localhost:8000/docs in your browser"

# ========== PERFORMANCE ==========

benchmark: ## Run performance benchmark
	$(PYTHON) -c "import time; from examples import RecommendationEngineClient; c = RecommendationEngineClient(); s=time.time(); c.health_check(); print(f'Latency: {(time.time()-s)*1000:.1f}ms')"

# ========== CODE QUALITY ==========

quality: lint format type-check ## Run all quality checks
	@echo "✓ Code quality checks complete"

ci: install lint test ## Run CI pipeline (install, lint, test)
	@echo "✓ CI pipeline complete"

# ========== HELP & INFO ==========

version: ## Show version information
	@$(PYTHON) -c "import torch; from transformers import __version__; print(f'Python: {import sys; print(sys.version)}'); print(f'PyTorch: {torch.__version__}'); print(f'Transformers: {__version__}')"

requirements: ## Show installed packages
	$(PIP) list | grep -E "torch|transformers|fastapi|faiss|pillow|numpy"

info: ## Show environment information
	@echo "=== Environment Information ==="
	@echo "Python: $(shell $(PYTHON) --version)"
	@echo "Pip: $(shell $(PIP) --version)"
	@echo "Docker: $(shell $(DOCKER) --version)"
	@echo "Docker Compose: $(shell $(DOCKER_COMPOSE) --version)"
	@echo "Current User: $(shell whoami)"
	@echo "Working Directory: $(shell pwd)"
	@echo ""
	@echo "=== Service Status ==="
	@$(PYTHON) -c "import sys; sys.path.insert(0, '.'); from examples import RecommendationEngineClient; c = RecommendationEngineClient(); h = c.health_check(); print('✓ Service healthy' if h else '✗ Service unavailable')" || echo "✗ Service not running"

# ========== CLEANING ==========

clean: ## Remove cache and build files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	@echo "✓ Cache and build files cleaned"

distclean: clean compose-clean ## Deep clean (cache + containers + data)
	rm -rf /tmp/recommendation_index/*
	@echo "✓ Deep clean complete"

# ========== QUICK STARTS ==========

quick-start: compose-up ## Quick start with Docker Compose
	@sleep 2
	@echo ""
	@echo "✓ Service started!"
	@echo ""
	@echo "Try these commands:"
	@echo "  1. Check health: make check-health"
	@echo "  2. Run example: make example"
	@echo "  3. View logs: make compose-logs"
	@echo "  4. Open docs: make docs"
	@echo ""

# ========== ALIASES ==========

start: compose-up ## Alias for compose-up
stop: compose-down ## Alias for compose-down
restart: compose-restart ## Alias for compose-restart
logs: compose-logs ## Alias for compose-logs
status: check-health ## Alias for check-health
