"""
Core test cases for the LLM Bridge API.
"""
import pytest
import asyncio
from fastapi import status, HTTPException
from unittest.mock import patch, MagicMock, AsyncMock
from pydantic import BaseModel
from datetime import datetime, timedelta
from bson import ObjectId

# Test data
TEST_QUESTION = "What is the capital of France?"
TEST_QUESTION_ID = "test-123"
TEST_API_KEY = "test-api-key-123"
TEST_USERNAME = "testuser"
TEST_PASSWORD = "SecurePass123!"
TEST_EMAIL = "test@example.com"
TEST_USER_ID = "507f1f77bcf86cd799439011"

# Mock models
class LLMRequest(BaseModel):
    question: str
    vibe: str = "professional"
    sender_id: str = "test-user"
    question_id: str = TEST_QUESTION_ID
    confidence: bool = False
    nature_of_answer: str = "Short"

class LLMResponse(BaseModel):
    response: str
    question_id: str
    metadata: dict = {}

# --- User Handler Tests ---

@pytest.mark.asyncio
async def test_create_user_success(mock_mongodb):
    """Test successful user creation."""
    from api.userHandler import create_user, hash_password
    
    # Create a mock for the inserted document
    inserted_doc = {}
    
    # Configure the mock to capture the inserted document
    async def mock_insert_one(doc, **kwargs):
        nonlocal inserted_doc
        inserted_doc = doc.copy()
        # Simulate the MongoDB _id generation
        inserted_doc["_id"] = ObjectId(TEST_USER_ID)
        return type('obj', (object,), {'inserted_id': ObjectId(TEST_USER_ID)})()
    
    # Configure the mock to return None for the first call (user doesn't exist)
    mock_mongodb.find_one.return_value = None
    mock_mongodb.insert_one.side_effect = mock_insert_one
    
    # Mock the hash_password function
    with patch('api.userHandler.hash_password', return_value='hashed_password'):
        # Test user creation
        success, result = await create_user(
            username=TEST_USERNAME,
            password=TEST_PASSWORD,
            email=TEST_EMAIL
        )
    
    # Debug output
    print(f"Test create_user result: {result}")
    print(f"Inserted document: {inserted_doc}")
    
    # Check the success flag and result structure
    assert success is True, "User creation should be successful"
    assert isinstance(result, dict), "Result should be a dictionary"
    
    # Check that the response contains the expected fields
    assert "api_key" in result, "Response should contain 'api_key'"
    assert "user" in result, "Response should contain 'user'"
    
    # Check user data in the response
    user_data = result["user"]
    assert user_data["username"] == TEST_USERNAME, "Username should match"
    assert user_data["email"] == TEST_EMAIL, "Email should match"
    assert "_id" in user_data, "User ID should be present"
    
    # Verify sensitive data is not in the response
    assert "hashed_password" not in user_data, "Hashed password should not be in the response"
    
    # Verify the insert was called with correct data
    assert mock_mongodb.insert_one.await_count == 1, "Should insert one document"
    
    # Check the data that was actually inserted
    assert inserted_doc["username"] == TEST_USERNAME, "Inserted username should match"
    assert inserted_doc["email"] == TEST_EMAIL, "Inserted email should match"
    assert "hashed_password" in inserted_doc, "Hashed password should be in inserted document"
    assert inserted_doc["hashed_password"] == "hashed_password", "Hashed password should match mocked value"
    assert "api_key" in inserted_doc, "API key should be in inserted document"
    assert "is_active" in inserted_doc, "is_active flag should be in inserted document"
    assert inserted_doc["is_active"] is True, "New user should be active"
    assert "created_at" in inserted_doc, "Created timestamp should be set"
    assert "updated_at" in inserted_doc, "Updated timestamp should be set"

@pytest.mark.asyncio
async def test_create_user_duplicate(mock_mongodb):
    """Test creating a user that already exists."""
    from api.userHandler import create_user
    
    # Mock existing user
    mock_mongodb.find_one.return_value = {"username": TEST_USERNAME}
    
    success, result = await create_user(
        username=TEST_USERNAME,
        password=TEST_PASSWORD,
        email=TEST_EMAIL
    )
    
    assert success is False
    assert "already exists" in result.get("error", "").lower()
    mock_mongodb.insert_one.assert_not_called()

@pytest.mark.asyncio
async def test_verify_user_minimal(mock_mongodb):
    """Minimal test to verify basic verify_user functionality."""
    print("\n=== Starting test_verify_user_minimal ===")
    
    try:
        # 1. Import required modules
        from api.userHandler import verify_user, verify_password
        from bson import ObjectId
        print("✓ Imports successful")
        
        # 2. Create test data
        test_password = "test123"
        user_id = ObjectId()
        
        # 3. Create a minimal mock user with a pre-hashed password
        # This is a bcrypt hash of "test123" with 12 rounds
        hashed_pw = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
        
        mock_user = {
            "_id": user_id,
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": hashed_pw,
            "is_active": True,
            "api_key": "test-api-key-123"
        }
        
        # 4. Setup mock to return our test user
        async def mock_find_one(*args, **kwargs):
            print(f"\nMongoDB find_one called with args: {args}, kwargs: {kwargs}")
            return mock_user
            
        mock_mongodb.find_one.side_effect = mock_find_one
        
        # 5. Mock the update_one operation
        async def mock_update_one(*args, **kwargs):
            print(f"\nMongoDB update_one called with args: {args}, kwargs: {kwargs}")
            return type('obj', (object,), {'matched_count': 1, 'modified_count': 1})()
            
        mock_mongodb.update_one.side_effect = mock_update_one
        
        # 6. Mock the verify_password function
        with patch('api.userHandler.verify_password', return_value=True) as mock_verify:
            # 7. Call the function
            print("\nCalling verify_user...")
            is_valid, result = await verify_user(
                username="testuser",
                password=test_password,
                collection=mock_mongodb
            )
            print(f"verify_user result: is_valid={is_valid}, result={result}")
            
            # 8. Verify verify_password was called with correct arguments
            mock_verify.assert_called_once_with(test_password, hashed_pw)
        
        # 9. Basic assertions
        print("\nRunning assertions...")
        assert is_valid is True, f"Expected is_valid=True, got {is_valid}"
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        
        # 10. Check the structure of the response
        assert "user" in result, f"Response missing 'user' key. Got keys: {result.keys()}"
        assert "api_key" in result, f"Response missing 'api_key' key. Got keys: {result.keys()}"
        
        # 11. Check user data
        user_data = result["user"]
        assert user_data["username"] == "testuser", f"Username mismatch. Expected 'testuser', got {user_data.get('username')}"
        assert "_id" in user_data, f"User data missing '_id'. Got keys: {user_data.keys()}"
        assert "hashed_password" not in user_data, "Hashed password should not be in response"
        
        # 12. Check API key
        assert result["api_key"] == "test-api-key-123", f"API key mismatch. Expected 'test-api-key-123', got {result.get('api_key')}"
        
        # 13. Verify the update was called to reset failed attempts
        assert mock_mongodb.update_one.await_count > 0, "update_one should have been called"
        
        print("\n✓ All assertions passed!")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        print("\n=== Test completed ===\n")

@pytest.mark.asyncio
async def test_verify_user_success(mock_mongodb):
    """Test successful user verification."""
    print("\n=== Starting test_verify_user_success ===")
    
    try:
        # 1. Import required modules
        from api.userHandler import verify_user, verify_password
        from bson import ObjectId
        from datetime import datetime, timedelta
        print("✓ Imports successful")
        
        # 2. Create test data
        test_password = "securePassword123"
        # Pre-computed bcrypt hash of "securePassword123" with 12 rounds
        hashed_pw = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
        user_id = ObjectId()
        
        # 3. Create a complete mock user
        mock_user = {
            "_id": user_id,
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "hashed_password": hashed_pw,
            "is_active": True,
            "is_superuser": False,
            "api_key": "test-api-key-123",
            "created_at": datetime.utcnow() - timedelta(days=7),
            "last_login": datetime.utcnow() - timedelta(days=1),
            "failed_attempts": 0,
            "preferences": {"theme": "light"}
        }
        
        # 4. Setup mock to return our test user
        async def mock_find_one(*args, **kwargs):
            print(f"\nMongoDB find_one called with args: {args}, kwargs: {kwargs}")
            return mock_user
            
        mock_mongodb.find_one.side_effect = mock_find_one
        
        # 5. Create a mock for update_one
        async def mock_update_one(filter, update, **kwargs):
            print(f"\nMongoDB update_one called with filter: {filter}, update: {update}")
            # Verify the update operation
            assert filter == {"_id": user_id}, f"Should update the correct user. Got filter: {filter}"
            
            # Check if failed_attempts is being reset
            if "$set" in update and "failed_attempts" in update["$set"]:
                assert update["$set"]["failed_attempts"] == 0, "Should reset failed attempts"
            
            # Check if last_login is being updated
            if "$set" in update and "last_login" in update["$set"]:
                assert isinstance(update["$set"]["last_login"], datetime), "Should set last_login to current time"
            
            return type('obj', (object,), {'matched_count': 1, 'modified_count': 1})()
        
        mock_mongodb.update_one.side_effect = mock_update_one
        
        # 6. Mock the verify_password function
        with patch('api.userHandler.verify_password', return_value=True) as mock_verify:
            # 7. Call the function
            print("\nCalling verify_user...")
            is_valid, result = await verify_user(
                username="testuser",
                password=test_password,
                collection=mock_mongodb  # Pass the mock collection directly
            )
            
            # 8. Verify verify_password was called with correct arguments
            mock_verify.assert_called_once_with(test_password, hashed_pw)
        
        # 9. Basic assertions
        print(f"\nResult: is_valid={is_valid}, result={result}")
        assert is_valid is True, f"Expected is_valid=True, got {is_valid}"
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        
        # 10. Check the structure of the response
        assert "user" in result, f"Response missing 'user' key. Got keys: {result.keys()}"
        assert "api_key" in result, f"Response missing 'api_key' key. Got keys: {result.keys()}"
        
        # 11. Check user data
        user_data = result["user"]
        assert user_data["username"] == "testuser", f"Username mismatch. Expected 'testuser', got {user_data.get('username')}"
        assert user_data["email"] == "test@example.com", f"Email mismatch. Expected 'test@example.com', got {user_data.get('email')}"
        assert "_id" in user_data, f"User data missing '_id'. Got keys: {user_data.keys()}"
        assert "hashed_password" not in user_data, "Hashed password should not be in response"
        assert "created_at" in user_data, f"User data missing 'created_at'. Got keys: {user_data.keys()}"
        assert "last_login" in user_data, f"User data missing 'last_login'. Got keys: {user_data.keys()}"
        
        # 12. Check API key
        assert result["api_key"] == "test-api-key-123", f"API key mismatch. Expected 'test-api-key-123', got {result.get('api_key')}"
        
        # 13. Verify the update was called to reset failed attempts and update last login
        assert mock_mongodb.update_one.await_count > 0, "update_one should have been called"
        
        print("\n✓ All assertions passed!")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        print("\n=== Test completed ===\n")

@pytest.mark.asyncio
async def test_verify_user_invalid_password(mock_mongodb):
    """Test user verification with invalid password."""
    print("\n=== Starting test_verify_user_invalid_password ===")
    
    try:
        # 1. Import required modules
        from api.userHandler import verify_user, verify_password
        from bson import ObjectId
        from datetime import datetime, timedelta
        print("✓ Imports successful")
        
        # 2. Create test data
        correct_password = "correct_password"
        incorrect_password = "wrong_password"
        user_id = ObjectId()
        
        # 3. Create a mock user with a pre-computed bcrypt hash
        # This is a pre-computed hash of "correct_password"
        hashed_pw = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
        
        mock_user = {
            "_id": user_id,
            "username": "testuser",
            "hashed_password": hashed_pw,
            "is_active": True,
            "failed_attempts": 0
        }
        
        # 4. Setup mock to return our test user
        async def mock_find_one(*args, **kwargs):
            print(f"\nMongoDB find_one called with args: {args}, kwargs: {kwargs}")
            return mock_user
            
        mock_mongodb.find_one.side_effect = mock_find_one
        
        # 5. Create a mock for update_one
        async def mock_update_one(filter, update, **kwargs):
            print(f"\nMongoDB update_one called with filter: {filter}, update: {update}")
            # Verify the update operation
            assert filter == {"_id": user_id}, f"Should update the correct user. Got filter: {filter}"
            
            # Check if failed_attempts is being incremented
            if "$inc" in update and "failed_attempts" in update["$inc"]:
                assert update["$inc"]["failed_attempts"] == 1, "Should increment failed_attempts by 1"
            
            # Return a mock result
            return type('obj', (object,), {'matched_count': 1, 'modified_count': 1})()
        
        mock_mongodb.update_one.side_effect = mock_update_one
        
        # 6. Mock the verify_password function to return False for incorrect password
        with patch('api.userHandler.verify_password', return_value=False) as mock_verify:
            # 7. Call the function with incorrect password
            print("\nCalling verify_user with incorrect password...")
            is_valid, result = await verify_user(
                username="testuser",
                password=incorrect_password,
                collection=mock_mongodb
            )
            print(f"verify_user result: is_valid={is_valid}, result={result}")
            
            # 8. Verify verify_password was called with correct arguments
            mock_verify.assert_called_once_with(incorrect_password, hashed_pw)
        
        # 9. Verify the response
        print(f"\nResult: is_valid={is_valid}, result={result}")
        assert is_valid is False, f"Expected is_valid=False, got {is_valid}"
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "error" in result, f"Response missing 'error' key. Got keys: {result.keys()}"
        assert "remaining_attempts" in result, f"Response missing 'remaining_attempts' key. Got keys: {result.keys()}"
        assert result["remaining_attempts"] == 4, f"Expected 4 remaining attempts, got {result.get('remaining_attempts')}"
        
        # 10. Verify the database was updated
        assert mock_mongodb.update_one.await_count > 0, "update_one should have been called"
        
        print("\n✓ All assertions passed!")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        print("\n=== Test completed ===\n")

@pytest.mark.asyncio
async def test_rotate_api_key_success(mock_mongodb):
    """Test successful API key rotation."""
    from api.userHandler import rotate_api_key
    
    new_api_key = "new_api_key_123"
    user_id = ObjectId(TEST_USER_ID)  # Convert to ObjectId
    
    with patch('api.userHandler.generate_api_key', return_value=new_api_key):
        success, result = await rotate_api_key(user_id=user_id)
        
        assert success is True
        assert result["api_key"] == new_api_key
        assert "rotated successfully" in result.get("message", "").lower()
        
        # Verify update was called with the new API key
        mock_mongodb.update_one.assert_awaited_once()
        args, _ = mock_mongodb.update_one.await_args
        assert args[0] == {"_id": user_id}
        assert "api_key" in args[1]["$set"]
        assert "updated_at" in args[1]["$set"]

@pytest.mark.asyncio
async def test_rotate_api_key_user_not_found(mock_mongodb):
    """Test API key rotation for non-existent user."""
    from api.userHandler import rotate_api_key
    
    # Configure update to return no matches
    mock_mongodb.update_one.return_value = MagicMock(matched_count=0)
    
    success, result = await rotate_api_key(user_id=ObjectId(TEST_USER_ID))
    
    assert success is False
    assert "user not found" in result.get("error", "").lower()

@pytest.mark.asyncio
async def test_ask_llm_success(client, mock_llm_bridge):
    """Test successful LLM question submission."""
    print("\n=== Starting test_ask_llm_success ===")
    
    try:
        # 1. Setup test data
        test_question = "What is the meaning of life?"
        test_sender = "test-sender-456"
        test_api_key = "test-api-key-123"
        test_question_id = "test-question-123"
        
        # 2. Prepare the request data with correct enum values and required fields
        request_data = {
            "question": test_question,
            "question_id": test_question_id,
            "sender_id": test_sender,
            "vibe": "Business/Professional",
            "confidence": True,
            "nature_of_answer": "Medium"
        }
        
        # 3. Make the request
        print("Sending request to /ask-llm/...")
        response = client.post(
            "/ask-llm/",
            headers={
                "X-API-Key": test_api_key,
                "X-Username": "test-user",
                "Content-Type": "application/json"
            },
            json=request_data
        )
        
        # 4. Print response for debugging
        print(f"Response status: {response.status_code}")
        try:
            response_data = response.json()
            print(f"Response body: {response_data}")
        except Exception as e:
            print(f"Failed to parse response JSON: {e}")
            print(f"Raw response: {response.text}")
            raise
        
        # 5. Verify the response
        assert response.status_code == status.HTTP_200_OK, \
            f"Expected status 200, got {response.status_code}"
            
        # 6. Verify response structure
        assert "response" in response_data, "Response missing 'response' field"
        assert "vibe_used" in response_data, "Response missing 'vibe_used' field"
        assert "question_id" in response_data, "Response missing 'question_id' field"
        assert "sender_id" in response_data, "Response missing 'sender_id' field"
        assert response_data["question_id"] == test_question_id, "Question ID mismatch"
        assert response_data["sender_id"] == test_sender, "Sender ID mismatch"
        
        # 7. Verify the mock was called with the right arguments
        mock_llm_bridge.process_request.assert_awaited_once()
        
        # Get the arguments passed to process_request
        args, kwargs = mock_llm_bridge.process_request.await_args
        
        # Verify the arguments
        assert "question" in kwargs, "Missing 'question' in LLM bridge call"
        assert "vibe" in kwargs, "Missing 'vibe' in LLM bridge call"
        assert "sender_id" in kwargs, "Missing 'sender_id' in LLM bridge call"
        assert "question_id" in kwargs, "Missing 'question_id' in LLM bridge call"
        assert "confidence" in kwargs, "Missing 'confidence' in LLM bridge call"
        assert "nature_of_answer" in kwargs, "Missing 'nature_of_answer' in LLM bridge call"
        
        assert kwargs["question"] == test_question
        assert kwargs["vibe"] == "Business/Professional"
        assert kwargs["sender_id"] == test_sender
        assert kwargs["question_id"] == test_question_id
        assert kwargs["confidence"] is True
        assert kwargs["nature_of_answer"] == "Medium"
        
        print("\n✓ All assertions passed!")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        print("\n=== Test completed ===\n")

@pytest.mark.asyncio
async def test_unauthorized_access(client, mock_llm_bridge, monkeypatch):
    """Test unauthorized access to the LLM endpoint."""
    print("\n=== Starting test_unauthorized_access ===")
    
    # Import the authenticate_entity function directly
    from api.entry_point_api import authenticate_entity, app
    
    # Mock the verify_api_key function to always fail
    async def mock_verify_api_key(api_key):
        return None  # Simulate invalid API key
    
    # Apply the mock to the verify_api_key function
    monkeypatch.setattr("api.entry_point_api.verify_api_key", mock_verify_api_key)
    
    try:
        # 1. Prepare test data
        request_data = {
            "question": "What is the capital of France?",
            "question_id": "test-123",
            "sender_id": "test-user",
            "vibe": "Business/Professional",
            "confidence": True,
            "nature_of_answer": "Medium"
        }
        
        # 2. Test with no authentication headers (should return 422 - validation error)
        print("1. Testing with no authentication headers")
        # Create a new client without default headers
        from fastapi.testclient import TestClient
        from api.entry_point_api import app as test_app
        
        with TestClient(test_app) as no_auth_client:
            response = no_auth_client.post(
                "/ask-llm/",
                json=request_data
            )
        
        print(f"2. Response status (no auth): {response.status_code}")
        print(f"Response content: {response.text}")
        
        # Should return 422 Unprocessable Entity when required headers are missing
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, \
            f"Expected 422 for missing auth headers, got {response.status_code}"
            
        # Check that the error message is about missing required fields
        response_data = response.json()
        assert "detail" in response_data, "Response missing 'detail' field"
        assert any("x-api-key" in str(err) for err in response_data["detail"]), \
            "Error message should mention missing x-api-key header"
        assert any("x-username" in str(err) for err in response_data["detail"]), \
            "Error message should mention missing x-username header"
        
        # 3. Test with invalid API key
        print("3. Testing with invalid API key")
        with TestClient(test_app) as invalid_key_client:
            response = invalid_key_client.post(
                "/ask-llm/",
                headers={
                    "X-API-Key": "invalid-api-key",
                    "X-Username": "test-user",
                    "Content-Type": "application/json"
                },
                json=request_data
            )
        
        print(f"4. Response status (invalid key): {response.status_code}")
        print(f"Response content: {response.text}")
        
        # Should return 401 Unauthorized for invalid API key
        assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
            f"Expected 401 for invalid API key, got {response.status_code}"
            
        # 4. Test with valid API key but invalid username
        print("5. Testing with valid API key but invalid username")
        with TestClient(test_app) as invalid_user_client:
            response = invalid_user_client.post(
                "/ask-llm/",
                headers={
                    "X-API-Key": "test-api-key-123",
                    "X-Username": "invalid-user",
                    "Content-Type": "application/json"
                },
                json=request_data
            )
        
        print(f"6. Response status (invalid user): {response.status_code}")
        print(f"Response content: {response.text}")
        
        # Should return 401 Unauthorized for invalid username
        assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
            f"Expected 401 for invalid username, got {response.status_code}"
        
        print("\n✓ All assertions passed!")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        print("\n=== Test completed ===\n")

@pytest.mark.asyncio
async def test_invalid_input(client, mock_mongodb):
    """Test request with missing or invalid required fields."""
    print("\n=== Starting test_invalid_input ===")
    
    try:
        # 1. Mock the user in the database
        mock_mongodb.find_one.return_value = {
            "_id": "test-user-id",
            "username": "test-user",
            "email": "test@example.com",
            "is_active": True,
            "api_key": "test-api-key-123"
        }
        
        # 2. Test with missing required fields
        print("1. Testing with missing required fields")
        response = client.post(
            "/ask-llm/",
            json={"question": "test"},  # Missing required fields
            headers={
                "X-API-Key": "test-api-key-123",
                "X-Username": "test-user"
            }
        )
        
        print(f"2. Response status (missing fields): {response.status_code}")
        print(f"Response content: {response.text}")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, \
            f"Expected 422 for missing fields, got {response.status_code}"
        
        # 3. Test with invalid field types
        print("4. Testing with invalid field types")
        invalid_data = {
            "vibe": "InvalidVibe",  # Invalid enum value
            "sender_id": 123,  # Should be string
            "question_id": "test-id",
            "question": "test",
            "confidence": "not-a-boolean",  # Should be boolean
            "nature_of_answer": "InvalidNature"  # Invalid enum value
        }
        
        response = client.post(
            "/ask-llm/",
            json=invalid_data,
            headers={
                "X-API-Key": "test-api-key-123",
                "X-Username": "test-user"
            }
        )
        
        print(f"5. Response status (invalid types): {response.status_code}")
        print(f"Response content: {response.text}")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, \
            f"Expected 422 for invalid field types, got {response.status_code}"
        
        # 4. Test with empty request body
        print("7. Testing with empty request body")
        response = client.post(
            "/ask-llm/",
            json={},  # Empty body
            headers={
                "X-API-Key": "test-api-key-123",
                "X-Username": "test-user"
            }
        )
        
        print(f"8. Response status (empty body): {response.status_code}")
        print(f"Response content: {response.text}")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, \
            f"Expected 422 for empty body, got {response.status_code}"
        
        print("\n✓ Test passed!")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        print("\n=== Test completed ===\n")

# --- API Endpoint Tests ---

def test_health_check(client):
    """Test health check endpoint."""
    with patch('api.entry_point_api.health_check', return_value={"status": "healthy"}):
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_environment():
    """Test environment configuration and connections."""
    print("\n=== Starting test_environment ===")
    
    try:
        # 1. Mock the config module
        with patch.dict('os.environ', {
            'MONGODB_URI': 'mongodb://test:test@localhost:27017/test',
            'JWT_SECRET_KEY': 'test-secret-key',
            'API_KEYS': 'test-key-1,test-key-2',
            'ENVIRONMENT': 'test'
        }):
            # 2. Mock pymongo's MongoClient
            with patch('pymongo.MongoClient') as mock_mongo_client:
                # 3. Mock the database and collection
                mock_db = MagicMock()
                mock_collection = MagicMock()
                mock_mongo_client.return_value.__getitem__.return_value = mock_db
                mock_db.__getitem__.return_value = mock_collection
                
                # 4. Import the config after patching
                from api.entry_point_api import app
                from fastapi.testclient import TestClient
                
                # 5. Test MongoDB connection
                print("1. Testing MongoDB connection...")
                client = TestClient(app)
                response = client.get("/health")
                
                # Verify the response status code
                assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
                
                # Verify the response structure
                response_data = response.json()
                assert 'status' in response_data, "Response missing 'status' field"
                assert 'components' in response_data, "Response missing 'components' field"
                assert 'database' in response_data['components'], "Response missing 'database' in components"
                assert 'llm_bridge' in response_data['components'], "Response missing 'llm_bridge' in components"
                
                # 6. Test environment variables
                print("2. Testing environment variables...")
                import os
                assert 'MONGODB_URI' in os.environ, "MONGODB_URI not in environment"
                assert 'JWT_SECRET_KEY' in os.environ, "JWT_SECRET_KEY not in environment"
                assert 'API_KEYS' in os.environ, "API_KEYS not in environment"
                assert os.environ['ENVIRONMENT'] == 'test', "ENVIRONMENT should be 'test'"
                
                print("\n✓ All assertions passed!")
                
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        print("\n=== Test completed ===\n")

@pytest.mark.asyncio
async def test_mongodb_connection():
    """Test direct MongoDB connection with current settings."""
    print("\n=== Testing MongoDB Connection ===")
    
    # Get the actual connection string from environment
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        print("✗ MONGO_URI environment variable is not set")
        assert False, "MONGO_URI environment variable is not set"
    
    # Log a safe version of the URI (without credentials)
    safe_uri = mongo_uri.split('@')[-1] if '@' in mongo_uri else mongo_uri
    print(f"Using MongoDB URI: {safe_uri}")
    
    try:
        from pymongo import MongoClient
        import ssl
        import certifi
        
        # Test with different connection options
        test_cases = [
            {
                "name": "TLS with invalid certs allowed",
                "options": {
                    "tls": True, 
                    "tlsAllowInvalidCertificates": True,
                    "tlsInsecure": True,
                    "connectTimeoutMS": 5000,
                    "serverSelectionTimeoutMS": 5000
                }
            },
            {
                "name": "TLS with CA certificates",
                "options": {
                    "tls": True,
                    "tlsCAFile": certifi.where(),
                    "connectTimeoutMS": 5000,
                    "serverSelectionTimeoutMS": 5000
                }
            },
            {
                "name": "Without TLS (direct connection)",
                "options": {
                    "tls": False,
                    "connectTimeoutMS": 5000,
                    "serverSelectionTimeoutMS": 5000
                }
            },
        ]
        
        success = False
        
        for test in test_cases:
            print(f"\nTest: {test['name']}")
            print(f"Options: {test['options']}")
            
            try:
                # Create a new SSL context for each test case
                ssl_context = None
                if test['options'].get('tls', False):
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    
                    # Try different TLS versions
                    for tls_version in [
                        ssl.PROTOCOL_TLS,
                        ssl.PROTOCOL_TLS_CLIENT,
                        ssl.PROTOCOL_TLSv1_2
                    ]:
                        try:
                            # Create a new context for each version
                            ssl_context = ssl.SSLContext(tls_version)
                            ssl_context.check_hostname = False
                            ssl_context.verify_mode = ssl.CERT_NONE
                            
                            # Add the test options with our custom context
                            test_options = test['options'].copy()
                            test_options['ssl_context'] = ssl_context
                            
                            print(f"Trying TLS version: {tls_version}")
                            client = MongoClient(mongo_uri, **test_options)
                            ping_result = client.admin.command('ping')
                            print(f"✓ Successfully connected to MongoDB with TLS version {tls_version}")
                            print(f"Ping response: {ping_result}")
                            success = True
                            break
                            
                        except Exception as e:
                            print(f"✗ TLS version {tls_version} failed: {str(e)}")
                            continue
                            
                    if success:
                        break
                else:
                    # Non-TLS connection
                    client = MongoClient(mongo_uri, **test['options'])
                    ping_result = client.admin.command('ping')
                    print(f"✓ Successfully connected to MongoDB without TLS")
                    print(f"Ping response: {ping_result}")
                    success = True
                
                if success:
                    # Test basic operations if connection is successful
                    try:
                        db = client.get_database()
                        collections = db.list_collection_names()
                        print(f"Available collections: {collections}")
                    except Exception as op_error:
                        print(f"Warning: Could not list collections: {op_error}")
                    break
                
            except Exception as e:
                print(f"✗ Connection failed: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        if not success:
            print("\n✗ All connection attempts failed")
            print("Troubleshooting tips:")
            print("1. Check your internet connection")
            print("2. Verify your IP is whitelisted in MongoDB Atlas")
            print("3. Try connecting with MongoDB Compass using the same connection string")
            print("4. Check if your organization's firewall is blocking the connection")
            
        assert success, "Failed to establish MongoDB connection with any tested configuration"
        
    except Exception as e:
        print(f"Error during connection test: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        print("=== End of MongoDB Connection Test ===\n")
