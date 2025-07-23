"""
entry_point_api.py — BRIDGE API Entry Point

This module implements the main FastAPI application for the BRIDGE LLM routing system.
It provides RESTful endpoints for user authentication, question processing, and system management.

The API follows REST conventions and uses JWT for authentication. All responses are
formatted as JSON and follow standard HTTP status codes.

Key Features:
- User authentication and API key management
- Question processing with LLM routing
- Request validation and error handling
- Comprehensive logging and monitoring
- CORS and security middleware

Endpoints:
    GET  /                   - API status and version
    GET  /health             - Health check and system status
    POST /register           - Register a new user
    POST /login              - Authenticate and get API key
    POST /ask-llm            - Process a question with the LLM
    GET  /test-mongodb       - Test MongoDB connection (debug)

Authentication:
    All endpoints except /health and /register require an API key in the X-API-Key header.

Example Usage:
    # Get API status
    curl http://localhost:8000/

    # Register a new user
    curl -X POST http://localhost:8000/register \
         -H "Content-Type: application/json" \
         -d '{"username":"test", "password":"password123", "email":"test@example.com"}'

    # Get API key
    curl -X POST http://localhost:8000/login \
         -H "Content-Type: application/json" \
         -d '{"username":"test", "password":"password123"}'

    # Ask a question
    curl -X POST http://localhost:8000/ask-llm \
         -H "X-API-Key: your_api_key" \
         -H "Content-Type: application/json" \
         -d '{"vibe":"Technical/Development", "question":"Explain how to use FastAPI"}'
"""

import os
import sys
from pathlib import Path
import uuid

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import logging
import time
from datetime import datetime
from enum import Enum
from fastapi import FastAPI, HTTPException, Request, Depends, status, Header
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json

# Import configuration and middleware
from config import get_config, VIBE_DESCRIPTIONS
from api.middleware.validation import setup_validation_middleware
from llm_bridge.bridge import LLMBridge
from api.authHandler import APIKeyAuth, verify_api_key
from api.userHandler import create_user, get_user, verify_user, rotate_api_key

# Get configuration
config = get_config()

# Initialize FastAPI app with metadata from config
app = FastAPI(
    title=config["api"]["title"],
    description=config["api"]["description"],
    version=config["api"]["version"]
)

# Initialize LLM Bridge
llm_bridge = LLMBridge(config=config)

# Add middleware
setup_validation_middleware(app)

# API Key Security
api_key_auth = APIKeyAuth(auto_error=True)

# --- Health Check Endpoint ---
@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the API is running.
    
    Returns:
        Dict: Status of the API and its components
    """
    try:
        # Check database connection
        db_status = "healthy"
        try:
            # Try to ping the database
            # Replace this with your actual database check
            pass
        except Exception as e:
            db_status = f"error: {str(e)}"
            
        # Check LLM bridge status
        llm_status = "healthy"
        try:
            # Add any LLM bridge health checks here
            pass
        except Exception as e:
            llm_status = f"error: {str(e)}"
            
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": config["api"]["version"],
            "components": {
                "database": db_status,
                "llm_bridge": llm_status
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unavailable: {str(e)}"
        )

# --- Authentication middleware ---
async def authenticate_entity(
    request: Request,
    x_api_key: str = Header(..., description="API key for authentication"),
    x_username: Optional[str] = Header(None, description="Username for user authentication"),  # שונה מ-... ל-None
    x_agent_id: Optional[str] = Header(None, description="Agent ID for agent authentication")
) -> Dict[str, Any]:
    """
    Middleware to authenticate users or agents based on the provided credentials.
    
    Args:
        request: The incoming request
        x_api_key: API key for authentication
        x_username: Username for user authentication (optional)
        x_agent_id: Agent ID for agent authentication (optional)
        
    Returns:
        Dict containing entity information if authenticated
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Allow guest access with 'guest_key'
        if x_api_key == "guest_key":
            if not x_username:
                x_username = f"guest_{str(uuid.uuid4())[:8]}"
            return {
                "type": "guest",
                "id": x_username,
                "permissions": ["read"],
                "is_guest": True
            }
            
        # For non-guest access, verify the API key
        user = await verify_api_key(x_api_key)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
            
        # If we have a username, verify it matches the API key
        if x_username and x_username != user.get("username"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username for API key"
            )
            
        # If we have both username and agent_id, it's invalid
        if x_username and x_agent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot provide both username and agent_id"
            )
            
        # If we have a username, it's a user login
        if x_username:
            return {
                "type": "user",
                "id": x_username,
                "permissions": ["read", "write"]
            }
            
        # If we have an agent ID, it's an agent login
        elif x_agent_id:
            return {
                "type": "agent",
                "id": x_agent_id,
                "permissions": ["read"]
            }
            
        # If neither username nor agent_id, it's an API key only authentication
        return {
            "type": "api_key",
            "id": user.get("username", "anonymous"),
            "permissions": ["read"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}"
        )

# --- Setup daily log file ---
def setup_logger():
    """Set up logging configuration."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create a file handler that writes to a daily log file
    log_file = log_dir / f"api_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Configure the root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

setup_logger()

# --- Enum for personality (vibe) ---
class Vibe(str, Enum):
    ACADEMIC_RESEARCH = "Academic/Research"
    BUSINESS_PROFESSIONAL = "Business/Professional"
    TECHNICAL_DEVELOPMENT = "Technical/Development"
    DAILY_GENERAL = "Daily/General"
    CREATIVE_EMOTIONAL = "Creative/Emotional"

# --- Enum for answer length ---
class NatureOfAnswer(str, Enum):
    SHORT = "Short"
    MEDIUM = "Medium"
    DETAILED = "Detailed"

# --- Vibe behavior descriptions for LLM prompting ---
VIBE_DESCRIPTIONS = {
    Vibe.ACADEMIC_RESEARCH: "Respond like a university professor, citing principles, theories, or academic references.",
    Vibe.BUSINESS_PROFESSIONAL: "Respond in a formal and strategic tone, as if giving business advice to executives.",
    Vibe.TECHNICAL_DEVELOPMENT: "Respond with technical precision, including code examples and best practices.",
    Vibe.DAILY_GENERAL: "Respond in a friendly, conversational tone suitable for everyday questions.",
    Vibe.CREATIVE_EMOTIONAL: "Respond with creativity and emotional intelligence, using metaphors and storytelling."
}

# --- Request model ---
class LLMRequest(BaseModel):
    """Request model for the LLM endpoint."""
    vibe: Vibe
    sender_id: str
    question_id: str
    question: str
    confidence: bool
    nature_of_answer: NatureOfAnswer

# --- Response model ---
class LLMResponse(BaseModel):
    """Response model for the LLM endpoint."""
    response: str
    vibe_used: str
    question_id: str
    sender_id: str
    model_metadata: dict
    follow_up_questions: Optional[List[str]] = None
    needs_more_info: Optional[bool] = False

# --- Middleware: Log every request to file and terminal ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start_time = time.time()
    
    # Get request details
    request_id = request.headers.get("X-Request-ID", "")
    client_host = request.client.host if request.client else "unknown"
    
    # Log the request
    logging.info(f"Request: {request.method} {request.url} from {client_host} (ID: {request_id})")
    
    try:
        # Process the request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log the response
        logging.info(
            f"Response: {response.status_code} in {process_time:.4f}s "
            f"(ID: {request_id})"
        )
        
        # Add headers
        response.headers["X-Process-Time"] = str(process_time)
        if request_id:
            response.headers["X-Request-ID"] = request_id
            
        return response
        
    except Exception as e:
        # Log the error
        logging.error(f"Error processing request: {str(e)}")
        raise

# --- User models ---
class UserCreate(BaseModel):
    """Model for user creation request."""
    username: str
    password: str
    email: Optional[str] = None

class UserResponse(BaseModel):
    """Model for user response."""
    username: str
    email: Optional[str] = None
    api_key: str
    created_at: datetime

class UserLogin(BaseModel):
    """Model for user login data."""
    username: str
    password: str

# --- User Registration Endpoint ---
@app.post("/users/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate):
    """
    Register a new user using the userHandler.create_user function.
    
    This endpoint creates a new user with the provided username, password, and optional email.
    The password is hashed before storage using the logic in userHandler.
    
    Args:
        user_data: User registration data
        
    Returns:
        UserResponse: The created user's information including their API key
        
    Raises:
        HTTPException: If username is already taken or validation fails
    """
    try:
        # Create the user using the userHandler function
        result = await create_user(
            username=user_data.username,
            password=user_data.password,
            email=user_data.email
        )
        
        if not result or not isinstance(result, dict) or not result.get('success', False):
            error_msg = result.get('error', 'Failed to create user') if isinstance(result, dict) else 'Failed to create user'
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
            
        # Get the created user data from the result
        created_user = result.get('user')
        if not created_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User created but user data is missing"
            )
            
        # Return the user data without sensitive information
        return {
            "username": created_user.get("username"),
            "email": created_user.get("email"),
            "api_key": created_user.get("api_key"),
            "created_at": created_user.get("created_at", datetime.utcnow())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error during user registration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during registration: {str(e)}"
        )

# --- User Login Endpoint ---
@app.post("/users/login", response_model=Dict[str, Any])
async def login_user(login_data: UserLogin):
    """
    Authenticate a user and return an API key.
    
    Args:
        login_data: User login credentials
        
    Returns:
        Dict containing user data and API key if successful, error message otherwise
    """
    try:
        # Verify user credentials
        result = await verify_user(login_data.username, login_data.password)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result.get("error", "Invalid credentials")
            )
            
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )

# --- POST endpoint: /ask-llm/ ---
@app.post("/ask-llm/", response_model=LLMResponse)
async def ask_llm(
    request: LLMRequest,
    entity: dict = Depends(authenticate_entity)
):
    """
    Process a question and return an AI-generated response.
    
    Args:
        request: The LLM request containing the question and metadata
        entity: The authenticated entity information from the authentication middleware
        
    Returns:
        LLMResponse: The AI-generated response
    """
    try:
        # Log the request
        logging.info(f"Processing question from {entity.get('id')}: {request.question}")
        
        # Prepare the request payload for the LLM bridge
        request_payload = {
            "prompt": request.question,
            "vibe": request.vibe,
            "response_preference": request.nature_of_answer.lower(),
            "show_confidence": request.confidence,
            "sender_id": request.sender_id,
            "question_id": request.question_id
        }
        
        # Process the request through the LLM bridge
        response = llm_bridge.process_request(request_payload)
        
        # Log the response
        logging.info(f"Response from LLM bridge: {response}")
        
        # Get model metadata from response or use defaults
        model_metadata = response.get('model_metadata', {})
        if not isinstance(model_metadata, dict):
            model_metadata = {}
            
        # Ensure required metadata fields are set
        model_metadata.setdefault('llm_used', response.get('llm_used', 'unknown'))
        model_metadata.setdefault('from_cache', response.get('from_cache', False))
        model_metadata.setdefault('is_guest', entity.get('is_guest', False))
        
        # Return the response
        return LLMResponse(
            response=response.get("response", "No response generated"),
            vibe_used=request.vibe,
            question_id=request.question_id,
            sender_id=request.sender_id,
            model_metadata=model_metadata,
            follow_up_questions=response.get('follow_up_questions', None),
            needs_more_info=response.get('needs_more_info', False)
        )
        
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing your request: {str(e)}"
        )

# --- Vibe to model rating mapping ---
def get_vibe_rating(vibe: Vibe) -> int:
    """
    Map a vibe to a model rating (1-5).
    
    Args:
        vibe: The vibe to map
        
    Returns:
        int: The model rating (1-5)
    """
    vibe_ratings = {
        Vibe.ACADEMIC_RESEARCH: 5,
        Vibe.BUSINESS_PROFESSIONAL: 4,
        Vibe.TECHNICAL_DEVELOPMENT: 4,
        Vibe.DAILY_GENERAL: 3,
        Vibe.CREATIVE_EMOTIONAL: 3
    }
    return vibe_ratings.get(vibe, 3)

# --- Test MongoDB Connection Endpoint ---
@app.get("/test-mongodb")
async def test_mongodb():
    """Test MongoDB connection and access."""
    try:
        # Test the connection
        db_handler.test_connection()
        return {"status": "success", "message": "MongoDB connection test passed!"}
    except Exception as e:
        logger.error(f"MongoDB test failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"MongoDB test failed: {str(e)}"}
        )

# --- Root endpoint ---
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "LLM Bridge API is running",
        "version": config["api"]["version"],
        "documentation": "/docs"
    }

# --- Error handlers ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle all other exceptions."""
    logging.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )