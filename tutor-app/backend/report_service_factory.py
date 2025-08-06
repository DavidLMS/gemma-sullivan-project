"""
Report Service Factory for Tutor App
"""

import logging
import os
from typing import Optional, Any

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

def get_report_service() -> Optional[Any]:
    """
    Get Ollama report generation service - cloud inference removed
    
    Returns:
        Ollama service instance or None if not available
    """
    logger.info("Using Ollama service for report generation (cloud inference removed)")
    return _get_ollama_service()

def _get_ollama_service() -> Optional[Any]:
    """
    Get Ollama service instance
    
    Returns:
        Ollama service instance or None if not available
    """
    try:
        from ollama_service import ollama_service
        
        if ollama_service is None:
            logger.error("Ollama service is not properly initialized")
            return None
        
        return ollama_service
        
    except ImportError as e:
        logger.error(f"Failed to import Ollama service: {e}")
        return None
    except Exception as e:
        logger.error(f"Error accessing Ollama service: {e}")
        return None

async def test_service_connection(service: Any) -> bool:
    """
    Test connection to the provided service
    
    Args:
        service: Service instance to test
        
    Returns:
        True if connection successful, False otherwise
    """
    if service is None:
        logger.error("No service provided for connection test")
        return False
    
    try:
        return await service.test_connection()
    except Exception as e:
        logger.error(f"Service connection test failed: {e}")
        return False

def get_service_info() -> dict:
    """
    Get information about the current service configuration (Ollama only)
    
    Returns:
        Dictionary with service configuration details
    """
    info = {
        "primary_service": "Ollama",
        "cloud_services_removed": True,
        "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        "ollama_model": os.getenv("OLLAMA_MODEL", "gemma3n"),
        "temperature": os.getenv("TEMPERATURE", "0.5"),
        "max_retries": os.getenv("MAX_RETRIES", "50"),
        "timeout_seconds": os.getenv("TIMEOUT_SECONDS", "300")
    }
    
    return info