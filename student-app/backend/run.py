#!/usr/bin/env python3
"""
Student App Backend Entry Point

Main application runner for the student app backend.
Starts the FastAPI server and ensures necessary directories exist.

Usage:
    python run.py                    # Start development server
    python run.py --host 0.0.0.0    # Bind to all interfaces
    python run.py --port 8080       # Use custom port
    python run.py --reload          # Enable auto-reload (development)
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def ensure_directories():
    """Ensure necessary directories exist."""
    # Create content/inbox directory if it doesn't exist
    # Other directories will be created on-demand by the functions that need them
    content_dir = Path("content")
    inbox_dir = content_dir / "inbox"
    
    inbox_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"✓ Ensured directory exists: {inbox_dir}")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Student App Backend Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--host",
        default=os.getenv("HOST", "127.0.0.1"),
        help="Host to bind the server to"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", 8000)),
        help="Port to bind the server to"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        default=os.getenv("LOG_LEVEL", "info"),
        help="Set the logging level"
    )
    
    return parser.parse_args()


def print_startup_info(host: str, port: int):
    """Print startup information."""
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    use_openrouter = os.getenv("USE_OPENROUTER", "false").lower() == "true"
    file_watcher = os.getenv("FILE_WATCHER_ENABLED", "true").lower() == "true"
    
    print(f"""
╭─────────────────────────────────────────────────────────────╮
│                                                             │
│             🎓 Student App Backend                         │
│                                                             │
│  Host: {host:<20}                                         │
│  Port: {port:<8}                                          │
│                                                             │
│  API Documentation:                                         │
│    • Interactive: http://{host}:{port}/docs              │
│    • Health:      http://{host}:{port}/health            │
│                                                             │
│  Configuration:                                             │
│    • Debug:       {debug_mode}                              │
│    • AI Service:  {'OpenRouter' if use_openrouter else 'Local Transformers':<15}  │
│    • File Watcher: {'Enabled' if file_watcher else 'Disabled':<15}  │
│                                                             │
╰─────────────────────────────────────────────────────────────╯
""")


def main():
    """Main application entry point."""
    args = parse_arguments()
    
    # Set logging level
    level = getattr(logging, args.log_level.upper())
    logging.getLogger().setLevel(level)
    
    # Ensure directories exist
    try:
        ensure_directories()
        logger.info("✓ Directory validation complete")
    except Exception as e:
        logger.error(f"✗ Directory validation failed: {e}")
        sys.exit(1)
    
    # Print startup information
    print_startup_info(args.host, args.port)
    
    # Configure uvicorn settings
    uvicorn_config = {
        "app": "api_server:app",  # Import the app from api_server.py
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level,
        "access_log": True,
        "reload": args.reload,
    }
    
    # Start the server
    try:
        logger.info("🚀 Starting server...")
        uvicorn.run(**uvicorn_config)
    except KeyboardInterrupt:
        logger.info("🛑 Server shutdown requested")
    except Exception as e:
        logger.error(f"💥 Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()