"""
MongoDB handler for the LLM Bridge application.
Handles all database operations for both user management and QA records.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from pymongo import MongoClient
from pymongo.errors import PyMongoError, DuplicateKeyError
from bson import ObjectId
import certifi
from dotenv import load_dotenv
import datetime
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MongoDBHandler:
    """Handles MongoDB connection and operations."""
    
    _instance = None
    _client = None
    _db = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super(MongoDBHandler, cls).__new__(cls)
            cls._instance._initialize_connection()
        return cls._instance
    
    def _initialize_connection(self):
        """Initialize MongoDB connection with retry logic."""
        max_retries = 3
        retry_delay = 2  # seconds
        
        self.mongo_uri = os.getenv("MONGO_URI")
        if not self.mongo_uri:
            logger.error("MONGO_URI environment variable is not set")
            raise ValueError("MONGO_URI environment variable is not set")
        
        self.db_name = os.getenv("MONGO_DB_NAME", "bridge_db")
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Attempting to connect to MongoDB at: {self.mongo_uri}")
                
                # Use the working connection settings from our test
                connection_params = {
                    'tls': True,
                    'tlsCAFile': certifi.where(),
                    'retryWrites': True,
                    'w': 'majority',
                    'connectTimeoutMS': 10000,
                    'serverSelectionTimeoutMS': 10000,
                    'appname': 'BRIDGE-API'
                }
                
                if os.getenv('ENV', 'development') == 'development':
                    logger.warning("Running in development mode with relaxed SSL settings")
                    connection_params.update({
                        'tlsAllowInvalidCertificates': True,
                        'tlsAllowInvalidHostnames': True
                    })
                
                self._client = MongoClient(self.mongo_uri, **connection_params)
                
                # Test the connection
                self._client.admin.command('ping')
                logger.info("Successfully connected to MongoDB")
                self._db = self._client[self.db_name]
                self._init_collections()
                logger.info(f"Successfully initialized database '{self.db_name}'")
                return
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Connection attempt {attempt} failed: {error_msg}")
                if attempt < max_retries:
                    logger.warning(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Failed to connect to MongoDB after 3 attempts: " + error_msg)
                    logger.error("\nPlease check:")
                    logger.error("1. Your internet connection")
                    logger.error("2. MongoDB Atlas network access (IP whitelist)")
                    logger.error("3. MongoDB credentials and connection string")
                    logger.error("4. Try connecting with MongoDB Compass to verify credentials")
                    raise ConnectionError(f"Failed to connect to MongoDB after {max_retries} attempts: {error_msg}")
    
    def _init_collections(self):
        """Initialize collections and indexes."""
        # Users collection
        self.users = self._db["users"]
        self.users.create_index("username", unique=True)
        self.users.create_index("email", unique=True)
        self.users.create_index("api_key", unique=True, sparse=True)
        
        # QA records collection
        self.qa_records = self._db["qa_records"]
        self.qa_records.create_index("user_id")
        self.qa_records.create_index([("timestamp", -1)])
    
    # User management methods
    def create_user(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """Create a new user."""
        try:
            # Check if user already exists
            if self.users.find_one({"$or": [{"username": username}, {"email": email}]}):
                raise ValueError("Username or email already exists")
            
            # Hash password
            from passlib.hash import bcrypt
            hashed_password = bcrypt.using(rounds=12).hash(password)
            
            # Generate API key
            import secrets
            api_key = f"brdg_{secrets.token_urlsafe(32)}"
            
            # Create user document
            user = {
                "username": username,
                "email": email,
                "hashed_password": hashed_password,
                "api_key": api_key,
                "is_active": True,
                "created_at": datetime.datetime.utcnow(),
                "last_login": None
            }
            
            # Insert user
            result = self.users.insert_one(user)
            user["id"] = str(result.inserted_id)
            
            # Don't return sensitive data
            user.pop("hashed_password", None)
            user.pop("_id", None)
            
            return user
            
        except DuplicateKeyError:
            raise ValueError("Username or email already exists")
        except PyMongoError as e:
            logger.error(f"Error creating user: {e}")
            raise
    
    def verify_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Verify user credentials."""
        try:
            user = self.users.find_one({"username": username, "is_active": True})
            if not user:
                return None
                
            from passlib.hash import bcrypt
            if not bcrypt.verify(password, user["hashed_password"]):
                return None
                
            # Update last login
            self.users.update_one(
                {"_id": user["_id"]},
                {"$set": {"last_login": datetime.datetime.utcnow()}}
            )
            
            # Prepare user data to return
            user_data = {
                "id": str(user["_id"]),
                "username": user["username"],
                "email": user["email"],
                "api_key": user.get("api_key"),
                "is_active": user.get("is_active", True)
            }
            
            return user_data
            
        except PyMongoError as e:
            logger.error(f"Error verifying user: {e}")
            raise
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            user = self.users.find_one({"_id": ObjectId(user_id), "is_active": True})
            if not user:
                return None
                
            return {
                "id": str(user["_id"]),
                "username": user["username"],
                "email": user["email"],
                "is_active": user.get("is_active", True),
                "created_at": user.get("created_at"),
                "last_login": user.get("last_login")
            }
            
        except PyMongoError as e:
            logger.error(f"Error getting user: {e}")
            raise
    
    def rotate_api_key(self, user_id: str) -> Optional[str]:
        """Generate a new API key for the user."""
        try:
            import secrets
            new_api_key = f"brdg_{secrets.token_urlsafe(32)}"
            
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"api_key": new_api_key}}
            )
            
            if result.modified_count == 0:
                return None
                
            return new_api_key
            
        except PyMongoError as e:
            logger.error(f"Error rotating API key: {e}")
            raise
    
    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update user data.
        
        Args:
            user_id: The ID of the user to update
            update_data: Dictionary of fields to update
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            from bson import ObjectId
            
            # Convert string ID to ObjectId if needed
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
                
            # Don't allow updating _id
            update_data.pop('_id', None)
            
            result = self.users.update_one(
                {"_id": user_id},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False
    
    # QA Records methods
    def save_qa_record(self, user_id: str, question: str, answer: str, metadata: Optional[Dict] = None) -> str:
        """Save a QA record to the database."""
        try:
            record = {
                "user_id": user_id,
                "question": question,
                "answer": answer,
                "metadata": metadata or {},
                "timestamp": datetime.datetime.utcnow()
            }
            
            result = self.qa_records.insert_one(record)
            return str(result.inserted_id)
            
        except PyMongoError as e:
            logger.error(f"Error saving QA record: {e}")
            raise
    
    def get_user_qa_history(self, user_id: str, limit: int = 10, skip: int = 0) -> List[Dict]:
        """Get QA history for a user."""
        try:
            cursor = self.qa_records.find({"user_id": user_id})\
                                 .sort("timestamp", -1)\
                                 .skip(skip)\
                                 .limit(limit)
            
            return [{
                "id": str(record["_id"]),
                "question": record["question"],
                "answer": record["answer"],
                "timestamp": record["timestamp"],
                "metadata": record.get("metadata", {})
            } for record in cursor]
            
        except PyMongoError as e:
            logger.error(f"Error getting QA history: {e}")
            raise

# Create a singleton instance
db_handler = MongoDBHandler()
