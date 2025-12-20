# Search Engine Scraping System - Makefile
# Easy commands for development and deployment

.PHONY: help install run dev test docker docker-dev clean

# Default target
help:
	@echo ""
	@echo "🔍 Search Engine Scraping System"
	@echo "================================="
	@echo ""
	@echo "Commands:"
	@echo "  make install     Install dependencies"
	@echo "  make run         Run the API server"
	@echo "  make dev         Run with hot reload (development)"
	@echo "  make docker      Start with Docker Compose"
	@echo "  make docker-dev  Start Docker in development mode"
	@echo "  make test        Run example tests"
	@echo "  make verify      Verify installation"
	@echo "  make logs        View Docker logs"
	@echo "  make stop        Stop Docker containers"
	@echo "  make clean       Clean up cache files"
	@echo ""

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	playwright install chromium
	@echo "✅ Installation complete!"

# Run the API server
run:
	@echo "🚀 Starting API server..."
	python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run in development mode with hot reload
dev:
	@echo "🔧 Starting in development mode..."
	python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

# Start with Docker Compose
docker:
	@echo "🐳 Starting Docker containers..."
	docker-compose up -d
	@echo "✅ API available at http://localhost:8000"
	@echo "📚 Docs at http://localhost:8000/docs"

# Start Docker in development mode
docker-dev:
	@echo "🐳 Starting Docker in development mode..."
	docker-compose --profile dev up api-dev

# Build Docker image
docker-build:
	@echo "🔨 Building Docker image..."
	docker-compose build

# Run example tests
test:
	@echo "🧪 Running example tests..."
	python examples/example_usage.py

# Verify installation
verify:
	@echo "🔍 Verifying installation..."
	python verify_installation.py

# View Docker logs
logs:
	docker-compose logs -f api

# Stop Docker containers
stop:
	@echo "🛑 Stopping containers..."
	docker-compose down

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf logs/*.log 2>/dev/null || true
	@echo "✅ Cleanup complete!"

# Quick health check
health:
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "❌ API not running"

# Quick search test
search:
	@curl -s -X POST http://localhost:8000/api/v1/search/fast \
		-H "Content-Type: application/json" \
		-d '{"query": "python programming", "num_results": 3}' | python3 -m json.tool
