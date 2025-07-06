"""
User authentication and management handler.
This module provides functions for user registration, authentication, and management.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from dotenv import load_dotenv
import uuid

# Load environment variables from .env file
load_dotenv()

# Import from our consolidated mongoHandler
from data_layer.mongoHandler import db_handler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-here")
if SECRET_KEY == "your-secret-key-here":
    logger.warning("Using default JWT secret key. This is not secure for production!")
    
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Password hashing
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Dict[str, Any]:
    """Verify JWT token and return payload."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return payload
    except jwt.PyJWTError:
        raise credentials_exception

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = verify_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return {"username": username}
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise credentials_exception

async def create_user(username: str, email: str, password: str) -> Dict[str, Any]:
    """
    Create a new user.
    
    Args:
        username: Username for the new user
        email: Email for the new user
        password: Password for the new user
        
    Returns:
        Dict containing success status and user data or error message
    """
    try:
        # Use the MongoDBHandler's create_user method
        user = db_handler.create_user(username, email, password)
        
        return {
            "success": True,
            "user": {
                "id": user.get("id"),
                "username": user.get("username"),
                "email": user.get("email"),
                "api_key": user.get("api_key"),
                "created_at": user.get("created_at")
            }
        }
        
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}", exc_info=True)
        return {"success": False, "error": f"Failed to create user: {str(e)}"}

async def verify_user(username: str, password: str) -> Dict[str, Any]:
    """
    Verify user credentials.
    
    Args:
        username: Username or email
        password: Password to verify
        
    Returns:
        Dict with success status and user data or error message
    """
    try:
        # Try to find user by username or email
        user_doc = db_handler.users.find_one({
            "$or": [
                {"username": username},
                {"email": username}
            ]
        })
        
        if not user_doc:
            return {"success": False, "error": "Invalid username or password"}
            
        # Verify password
        from passlib.hash import bcrypt
        if not bcrypt.verify(password, user_doc.get("hashed_password")):
            return {"success": False, "error": "Invalid username or password"}
        
        # Update last login time
        db_handler.update_user(
            str(user_doc["_id"]),
            {"last_login": datetime.utcnow()}
        )
        
        # Return user data without sensitive information
        return {
            "success": True,
            "user": {
                "id": str(user_doc["_id"]),
                "username": user_doc.get("username"),
                "email": user_doc.get("email"),
                "api_key": user_doc.get("api_key"),
                "created_at": user_doc.get("created_at")
            }
        }
        
    except Exception as e:
        logger.error(f"Error verifying user: {str(e)}", exc_info=True)
        return {"success": False, "error": "An error occurred during authentication"}

async def get_user(identifier: str) -> Optional[Dict[str, Any]]:
    """
    Get user by ID, username, or email.
    
    Args:
        identifier: User ID (as string), username, or email
        
    Returns:
        User document if found, None otherwise
    """
    try:
        from bson import ObjectId
        
        # Try to find by ObjectId first
        try:
            user = db_handler.get_user(identifier)
            if user:
                return user
        except:
            pass  # Not a valid ObjectId, try username/email
            
        # Try to find by username or email
        user_doc = db_handler.users.find_one({
            "$or": [
                {"username": identifier},
                {"email": identifier}
            ]
        })
        
        if user_doc:
            return {
                "id": str(user_doc["_id"]),
                "username": user_doc.get("username"),
                "email": user_doc.get("email"),
                "api_key": user_doc.get("api_key"),
                "created_at": user_doc.get("created_at"),
                "last_login": user_doc.get("last_login"),
                "is_active": user_doc.get("is_active", True)
            }
            
        return None
        
    except Exception as e:
        logger.error(f"Error getting user {identifier}: {str(e)}", exc_info=True)
        return None

def rotate_api_key(user_id: str) -> Dict[str, Any]:
    """
    Generate a new API key for the user.
    
    Args:
        user_id: User ID
        
    Returns:
        Dict with new API key if successful, error message otherwise
    """
    try:
        new_api_key = db_handler.rotate_api_key(user_id)
        if not new_api_key:
            return {"success": False, "error": "User not found or API key rotation failed"}
            
        return {
            "success": True,
            "message": "API key rotated successfully",
            "new_api_key": new_api_key
        }
    except Exception as e:
        logger.error(f"Error rotating API key: {e}")
        return {"success": False, "error": "An error occurred while rotating the API key"}

# Export the required functions
__all__ = [
    "create_user", 
    "verify_user", 
    "get_user", 
    "rotate_api_key",
    "get_current_user",
    "verify_token"
]
