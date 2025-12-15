# Makefile for Web Scraping System

.PHONY: help install run dev test clean docker-build docker-run docker-stop logs setup check

# Default target
help:
	@echo "Web Scraping System - Available Commands:"
	@echo ""
	@echo "  make install       Install dependencies"
	@echo "  make setup         Initial setup (install + configure)"
	@echo "  make run           Run production server"
	@echo "  make dev           Run development server (with reload)"
	@echo "  make test          Run tests"
	@echo "  make check         Check configuration"
	@echo "  make clean         Clean temporary files"
	@echo ""
	@echo "  make docker-build  Build Docker image"
	@echo "  make docker-run    Run with Docker Compose"
	@echo "  make docker-stop   Stop Docker containers"
	@echo "  make docker-logs   View Docker logs"
	@echo ""
	@echo "  make logs          View application logs"
	@echo "  make health        Check API health"
	@echo ""

# Installation
install:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt
	@echo "Installing Playwright browsers..."
	playwright install chromium
	@echo "Installation complete!"

# Initial setup
setup: install
	@echo "Setting up configuration..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file. Please edit with your settings."; \
	else \
		echo ".env file already exists."; \
	fi
	@mkdir -p logs
	@echo "Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env file with your settings"
	@echo "  2. Add proxies to config/proxies.txt (optional)"
	@echo "  3. Run 'make dev' to start development server"

# Run production server
run:
	@echo "Starting production server..."
	python run.py --workers 4

# Run development server
dev:
	@echo "Starting development server..."
	python run.py --reload --log-level debug

# Run tests
test:
	@echo "Running tests..."
	pytest tests/ -v

# Check configuration
check:
	@echo "Checking configuration..."
	@python -c "from app.config import settings; print('Configuration loaded successfully')"
	@python -c "import yaml; yaml.safe_load(open('config/config.yaml')); print('YAML config valid')"
	@if command -v redis-cli > /dev/null; then \
		echo "Testing Redis connection..."; \
		redis-cli ping || echo "Redis not available (will use in-memory rate limiting)"; \
	else \
		echo "Redis CLI not found (optional)"; \
	fi
	@echo "Configuration check complete!"

# Clean temporary files
clean:
	@echo "Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete!"

# Docker commands
docker-build:
	@echo "Building Docker image..."
	docker build -t web-scraper .

docker-run:
	@echo "Starting services with Docker Compose..."
	docker-compose up -d
	@echo "Services started!"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"

docker-stop:
	@echo "Stopping Docker containers..."
	docker-compose down

docker-logs:
	@echo "Viewing Docker logs..."
	docker-compose logs -f

# View logs
logs:
	@echo "Viewing application logs..."
	@if [ -f logs/scraper.log ]; then \
		tail -f logs/scraper.log; \
	else \
		echo "No log file found. Start the application first."; \
	fi

# Health check
health:
	@echo "Checking API health..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "API not running"

# Format code
format:
	@echo "Formatting code..."
	@command -v black > /dev/null && black app/ || echo "black not installed"
	@command -v isort > /dev/null && isort app/ || echo "isort not installed"

# Lint code
lint:
	@echo "Linting code..."
	@command -v flake8 > /dev/null && flake8 app/ || echo "flake8 not installed"
	@command -v pylint > /dev/null && pylint app/ || echo "pylint not installed"
