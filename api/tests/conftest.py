"""
Test configuration and fixtures for the LLM Bridge API.
"""
import os
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncio
from bson import ObjectId
from fastapi import Header
from typing import Dict, Any, Optional

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set test environment variables
os.environ["ENV"] = "test"
os.environ["MONGO_URI"] = "mongodb://localhost:27017/test_db"
os.environ["DB_NAME"] = "test_db"
os.environ["JWT_SECRET_KEY"] = "test_secret_key"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["API_KEYS"] = json.dumps({"test-api-key-123": "test-user"})

# Create mock modules
mock_modules = {
    'cache_manager': MagicMock(),
    'prompt_analyzer': MagicMock(),
    'response_classifier': MagicMock(),
    'prompt_enhancer': MagicMock(),
    'llm_router': MagicMock(),
    'answer_evaluator': MagicMock(),
    'output_manager': MagicMock(),
    'bcrypt': MagicMock(),
    'llm_bridge': MagicMock(),
    'llm_bridge.bridge': MagicMock(),
    'config': MagicMock()  # Add mock for config
}

# Apply all the mocks
for module_name, mock_module in mock_modules.items():
    sys.modules[module_name] = mock_module

# Create a mock config
mock_config = {
    "api": {
        "title": "Test API",
        "description": "Test API Description",
        "version": "1.0.0"
    },
    "mongodb": {
        "uri": "mongodb://localhost:27017/test_db",
        "db_name": "test_db"
    },
    "jwt": {
        "secret_key": "test_secret_key",
        "algorithm": "HS256",
        "access_token_expire_minutes": 30
    },
    "llm": {
        "openai_api_key": "test_openai_key",
        "llm2_model": "gpt-3.5-turbo",
        "llm3_model": "gpt-4",
        "basic_max_tokens": 1000,
        "enhanced_max_tokens": 2000,
        "temperature": 0.7,
        "use_cache": True,
        "show_confidence_default": False
    },
    "vibe_descriptions": {
        "academic_research": "Academic research description",
        "business_professional": "Business professional description",
        "technical_development": "Technical development description",
        "daily_general": "Daily general description",
        "creative_emotional": "Creative emotional description"
    }
}

# Now import the app with all mocks in place
with patch('pymongo.MongoClient'), \
     patch('dotenv.load_dotenv'), \
     patch('api.entry_point_api.get_config', return_value=mock_config), \
     patch('config.get_config', return_value=mock_config):
    from api.entry_point_api import app
    from api.userHandler import get_users_collection

# Test client fixture with default auth headers
@pytest.fixture
def client():
    """Create a test client for the FastAPI app with default auth headers."""
    with TestClient(app) as test_client:
        # Set default headers for all requests
        test_client.headers.update({
            "X-API-Key": "test-api-key-123",
            "X-Username": "test-user"
        })
        yield test_client

# Mock MongoDB client
@pytest.fixture(autouse=True)
def mock_mongodb():
    """Mock MongoDB client for testing."""
    # Create a mock collection
    mock_collection = MagicMock()
    
    # Configure the collection methods
    mock_collection.find_one = AsyncMock(return_value=None)
    mock_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId("507f1f77bcf86cd799439011")))
    mock_collection.update_one = AsyncMock(return_value=MagicMock(matched_count=1, modified_count=1))
    
    # Patch the get_users_collection function
    with patch('api.userHandler.get_users_collection', return_value=mock_collection):
        yield mock_collection

# Mock API key verification
@pytest.fixture(autouse=True)
def mock_auth():
    """Mock the API key verification for all tests."""
    async def mock_authenticate_entity(
        request: Request,
        x_api_key: str = Header(..., description="API key for authentication"),
        x_username: Optional[str] = Header(None, description="Username for user authentication"),
        x_agent_id: Optional[str] = Header(None, description="Agent ID for agent authentication")
    ) -> Dict[str, Any]:
        if x_api_key != "test-api-key-123" or x_username != "test-user":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key or username"
            )
        return {
            "type": "user",
            "id": x_username,
            "permissions": ["read", "write"]
        }
    
    # Patch the authentication function
    with patch('api.entry_point_api.authenticate_entity', new=mock_authenticate_entity):
        yield

# Mock LLM bridge
@pytest.fixture
def mock_llm_bridge():
    """Mock the LLM bridge for all tests."""
    # Create a mock for the llm_bridge instance
    mock_bridge = MagicMock()
    
    # Create an AsyncMock for the process_request method
    mock_process_request = AsyncMock(return_value={
        "response": "Test response",
        "vibe_used": "Business/Professional",
        "question_id": "test-123",
        "sender_id": "test-user",
        "metadata": {}
    })
    
    # Configure the mock to use our AsyncMock
    mock_bridge.process_request = mock_process_request
    
    # Patch the llm_bridge instance in the module
    with patch('api.entry_point_api.llm_bridge', mock_bridge):
        yield mock_bridge

# Add async support for pytest
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
