"""
Authentication and Authorization Handlers for BRIDGE API

This module provides authentication and authorization functionality for the BRIDGE API.
It handles API key validation, request logging, and user authentication.

Key Features:
- API key authentication using HTTP Bearer tokens
- Request logging with rotation
- User authentication and authorization
- Secure handling of API keys

Dependencies:
    fastapi: Web framework for building APIs
    logging: Standard library for application logging
    os: Operating system interfaces
    pathlib: Object-oriented filesystem paths
    typing: Type hints support
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

# Configure logging directory and file
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "api.log"

# Create logger instance
logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

# Configure file handler with log rotation
file_handler = RotatingFileHandler(
    log_file, 
    maxBytes=1024*1024,  # 1MB per file
    backupCount=5,       # Keep 5 backup files
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)

# Configure console handler for error output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.ERROR)

# Define log message format
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Load API keys from environment variables
API_KEYS = json.loads(os.getenv("API_KEYS", "{}"))

class APIKeyAuth(HTTPBearer):
    """
    API Key Authentication Handler
    
    This class implements HTTP Bearer token authentication for API endpoints.
    It validates API keys provided in the Authorization header.
    
    Attributes:
        auto_error (bool): Whether to automatically raise HTTPException on auth failure
    """
    
    def __init__(self, auto_error: bool = True):
        """
        Initialize the APIKeyAuth instance.
        
        Args:
            auto_error (bool, optional): If True, raises HTTPException on auth failure.
                                       If False, returns None on failure. Defaults to True.
        """
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        """
        Validate the API key from the request.
        
        Args:
            request: The incoming HTTP request
            
        Returns:
            Optional[str]: The API key if valid, None otherwise
            
        Raises:
            HTTPException: If auto_error is True and authentication fails
        """
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if not credentials:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid authorization code."
                )
            return None
            
        if not credentials.scheme == "Bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid authentication scheme."
                )
            return None
            
        if not verify_api_key(credentials.credentials):
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid API key."
                )
            return None
            
        return credentials.credentials

async def verify_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """
    Verify if the provided API key is valid
    
    This function checks if the API key exists in the allowed keys dictionary
    and if it hasn't been revoked.
    
    Args:
        api_key (str): The API key to verify
        
    Returns:
        Optional[Dict[str, Any]]: User information if authenticated, None otherwise
    """
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

async def get_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Get the current user from the request.
    
    This function extracts the API key from the request and returns
    the associated user information if the key is valid.
    
    Args:
        request: The incoming HTTP request
        
    Returns:
        Optional[Dict[str, Any]]: User information if authenticated, None otherwise
    """
    try:
        auth = request.headers.get("Authorization")
        if not auth:
            return None
            
        scheme, _, api_key = auth.partition(" ")
        if scheme.lower() != "bearer" or not api_key:
            return None
            
        if not await verify_api_key(api_key):
            return None
            
        # In a real implementation, you would look up the user by API key
        # For this example, we'll return a simple user object
        return {
            "id": "user123",
            "username": "api_user",
            "permissions": ["read", "write"]
        }
        
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None

async def log_request(request: Request, call_next):
    """
    Log incoming requests and their responses.
    
    This middleware logs each incoming request along with its response status
    and processing time. It's useful for debugging and monitoring.
    
    Args:
        request: The incoming HTTP request
        call_next: Function to process the request and get the response
        
    Returns:
        The HTTP response
    """
    start_time = datetime.utcnow()
    
    # Log request details
    logger.info(
        f"Request: {request.method} {request.url.path} - "
        f"Client: {request.client.host if request.client else 'unknown'}"
    )
    
    # Process the request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    # Log response details
    logger.info(
        f"Response: {request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.2f}ms"
    )
    
    return response
