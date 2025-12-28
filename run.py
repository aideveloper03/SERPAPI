#!/usr/bin/env python3
"""
Quick start script for Web Scraping System
Usage: python run.py [options]
"""
import sys
import os
import argparse
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    parser = argparse.ArgumentParser(description="Web Scraping System")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind (default: 8000)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of worker processes (default: 4)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (development mode)"
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Log level (default: info)"
    )
    
    args = parser.parse_args()
    
    # Import here to avoid issues if dependencies not installed
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn not installed. Run: pip install -r requirements.txt")
        sys.exit(1)
    
    # Check if .env exists
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        print("Warning: .env file not found. Using default settings.")
        print("Copy .env.example to .env and configure as needed.")
    
    # Check if config directory exists
    config_dir = Path(__file__).parent / "config"
    if not config_dir.exists():
        print("Error: config directory not found")
        sys.exit(1)
    
    # Create logs directory if not exists
    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    print("=" * 60)
    print("Web Scraping System")
    print("=" * 60)
    print(f"Starting server on http://{args.host}:{args.port}")
    print(f"Workers: {args.workers if not args.reload else 1}")
    print(f"Log level: {args.log_level}")
    print(f"Reload: {args.reload}")
    print()
    print("API Documentation:")
    print(f"  Swagger UI: http://localhost:{args.port}/docs")
    print(f"  ReDoc: http://localhost:{args.port}/redoc")
    print()
    print("Press CTRL+C to quit")
    print("=" * 60)
    
    # Run server
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        workers=args.workers if not args.reload else 1,
        reload=args.reload,
        log_level=args.log_level
    )


if __name__ == "__main__":
    main()
