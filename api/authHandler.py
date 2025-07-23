"""
Authentication and authorization handlers for the LLM Bridge API.
"""
import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "api.log"

# Create logger
logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

# Create file handler which logs even debug messages
file_handler = RotatingFileHandler(
    log_file, maxBytes=1024*1024, backupCount=5, encoding='utf-8'
)
file_handler.setLevel(logging.INFO)

# Create console handler with a higher log level
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.ERROR)

# Create formatter and add it to the handlers
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Get API keys from environment
API_KEYS = json.loads(os.getenv("API_KEYS", "{}"))

class APIKeyAuth(HTTPBearer):
    """API Key authentication handler."""
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> Optional[Dict[str, Any]]:
        """Validate API key from request headers."""
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        
        api_key = credentials.credentials
        user = await verify_api_key(api_key)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
        
        return user

async def verify_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """Verify if the provided API key is valid."""
    if not api_key:
        return None
    
    # First check the environment variable API_KEYS
    user = API_KEYS.get(api_key)
    if user:
        return {"username": user, "api_key": api_key}
    
    # If not found in environment, check the database
    try:
        from data_layer.mongoHandler import db_handler
        user_doc = db_handler.users.find_one({"api_key": api_key})
        if user_doc:
            return {
                "username": user_doc.get("username"),
                "api_key": api_key,
                "email": user_doc.get("email"),
                "id": str(user_doc.get("_id"))
            }
    except Exception as e:
        logger.error(f"Error verifying API key in database: {str(e)}")
    
    return None

async def get_user(request: Request) -> Dict[str, Any]:
    """Get the current user from the request."""
    # This is a simplified version - in a real app, you'd get this from a JWT or session
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return {"username": "anonymous", "is_authenticated": False}
    
    user = await verify_api_key(api_key)
    if not user:
        return {"username": "anonymous", "is_authenticated": False}
    
    return {"username": user["username"], "is_authenticated": True}

async def log_request(request: Request, call_next):
    """Log incoming requests."""
    # Log the request
    logger.info(f"Incoming request: {request.method} {request.url}")
    
    # Process the request
    response = await call_next(request)
    
    # Log the response
    logger.info(f"Response status: {response.status_code}")
    
    return response
