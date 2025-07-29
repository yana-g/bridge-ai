"""
User Authentication and Management Handler

This module provides comprehensive user management functionality for the BRIDGE system,
including user registration, authentication, JWT token handling, and user data management.

Key Features:
- User registration with secure password hashing
- JWT-based authentication
- Password verification and hashing
- User data management
- API key generation and rotation

Dependencies:
    fastapi: Web framework for building APIs
    passlib: Password hashing library
    python-jose: JWT token handling
    pymongo: MongoDB database interface
    python-dotenv: Environment variable management
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

# JWT Configuration - Load from environment variables with fallback
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-here")
if SECRET_KEY == "your-secret-key-here":
    logger.warning("Using default JWT secret key. This is not secure for production!")
    
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Password hashing configuration
pwd_context = CryptContext(
    schemes=["bcrypt"],  # Using bcrypt for secure password hashing
    deprecated="auto"    # Automatically handle deprecated hashes
)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with the provided data.
    
    This function generates a JWT token that can be used for authenticating API requests.
    The token includes an expiration time and can contain arbitrary user data.
    
    Args:
        data (dict): Dictionary containing the data to encode in the token
        expires_delta (Optional[timedelta], optional): Token expiration time delta.
            If not provided, defaults to 15 minutes.
            
    Returns:
        str: Encoded JWT token
        
    Example:
        >>> token = create_access_token({"sub": "username"}, timedelta(minutes=30))
        >>> isinstance(token, str)
        True
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
    """
    Verify and decode a JWT token.
    
    This function validates the token signature and checks its expiration.
    
    Args:
        token (str): JWT token to verify
        
    Returns:
        Dict[str, Any]: Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
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
    """
    Dependency to get the current authenticated user from a JWT token.
    
    This function is designed to be used as a FastAPI dependency to protect routes.
    
    Args:
        token (str): JWT token from the Authorization header
        
    Returns:
        Dict[str, Any]: User information
        
    Raises:
        HTTPException: If authentication fails
    """
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

async def create_user(username: str, email: str, password: str, user_type: str = "user") -> Dict[str, Any]:
    """
    Create a new user account.
    
    This function handles the user registration process, including:
    - Validating input data
    - Hashing the password
    - Storing user data in the database
    - Generating an API key
    
    Args:
        username (str): Unique username for the new account
        email (str): User's email address
        password (str): Plain text password (will be hashed)
        user_type (str): Type of user (default: "user")
        
    Returns:    
        Dict[str, Any]: Dictionary containing:
            - success (bool): Whether the operation was successful
            - user (dict, optional): User data if successful
            - error (str, optional): Error message if unsuccessful
            
    Example:
        >>> result = await create_user("testuser", "test@example.com", "password123")
        >>> result["success"]
        True
    """
    try:
        # Use the MongoDBHandler's create_user method
        user = db_handler.create_user(username, email, password, user_type)
        
        return {
            "success": True,
            "user": {
                "id": user.get("id"),
                "username": user.get("username"),
                "email": user.get("email"),
                "api_key": user.get("api_key"),
                "user_type": user.get("user_type"),
                "created_at": user.get("created_at")    
            }
        }
        
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}", exc_info=True)
        return {
            "success": False, 
            "error": f"Failed to create user: {str(e)}"
        }

async def verify_user(username: str, password: str) -> Dict[str, Any]:
    """
    Verify user credentials and return user data if valid.
    
    This function checks if the provided username/email and password match
    a user in the database and updates the last login timestamp.
    
    Args:
        username (str): Username or email address
        password (str): Plain text password to verify
        
    Returns:
        Dict[str, Any]: Dictionary containing:
            - success (bool): Whether verification was successful
            - user (dict, optional): User data if successful
            - error (str, optional): Error message if unsuccessful
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
            
        # Verify password using bcrypt
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
        return {
            "success": False, 
            "error": "An error occurred during authentication"
        }

async def get_user(identifier: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a user by ID, username, or email.
    
    This is a flexible lookup function that can find users by different identifiers.
    
    Args:
        identifier (str): User ID, username, or email address
        
    Returns:
        Optional[Dict[str, Any]]: User document if found, None otherwise
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
            # Convert ObjectId to string for JSON serialization
            user_doc["id"] = str(user_doc.pop("_id"))
            return user_doc
            
        return None
        
    except Exception as e:
        logger.error(f"Error getting user {identifier}: {str(e)}", exc_info=True)
        return None

async def rotate_api_key(user_id: str) -> Dict[str, Any]:
    """
    Generate a new API key for the specified user.
    
    This function creates a new API key and updates the user's record.
    The old API key will no longer be valid after this operation.
    
    Args:
        user_id (str): The ID of the user
        
    Returns:
        Dict[str, Any]: Dictionary containing:
            - success (bool): Whether the operation was successful
            - api_key (str, optional): New API key if successful
            - error (str, optional): Error message if unsuccessful
    """
    try:
        # Generate a new API key
        new_api_key = str(uuid.uuid4())
        
        # Update the user's API key in the database
        result = db_handler.update_user(
            user_id,
            {"api_key": new_api_key}
        )
        
        if result:
            return {
                "success": True,
                "api_key": new_api_key
            }
        else:
            return {
                "success": False,
                "error": "User not found or update failed"
            }
            
    except Exception as e:
        logger.error(f"Error rotating API key for user {user_id}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": "An error occurred while rotating the API key"
        }

# Export the required functions
__all__ = [
    "create_user", 
    "verify_user", 
    "get_user",
    "create_access_token",
    "verify_token",
    "get_current_user",
    "rotate_api_key"
]
