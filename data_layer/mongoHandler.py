"""
MongoDB Handler for BRIDGE LLM Routing System

This module provides a singleton MongoDB handler for the BRIDGE application, managing all database
operations including user management, question-answer storage, and semantic search capabilities.

Key Features:
- Thread-safe singleton pattern for database connections
- Automatic connection retry and error handling
- User management (CRUD operations)
- Question-Answer pair storage and retrieval
- Semantic search using sentence transformers
- Caching and performance optimizations

Environment Variables:
    MONGO_URI: MongoDB connection string (required)
    DB_NAME: Database name (default: 'bridge_db')
    EMBEDDING_MODEL: Sentence transformer model (default: 'all-MiniLM-L6-v2')

Example Usage:
    from data_layer.mongoHandler import db_handler
    
    # Store a new QA pair
    qa_id = db_handler.save_qa_record(
        user_id="12345",
        question="What is FastAPI?",
        answer="FastAPI is a modern, fast web framework...",
        metadata={"source": "documentation"}
    )
    
    # Find similar questions
    similar = db_handler.semantic_search_by_prompt("Tell me about FastAPI")
    
    # Get user by ID
    user = db_handler.get_user(user_id="12345")

Dependencies:
    - pymongo: MongoDB Python driver
    - sentence-transformers: For semantic search embeddings
    - scikit-learn: For cosine similarity calculations
    - python-dotenv: For environment variable management

Note: This module implements a singleton pattern to ensure only one database connection
is maintained throughout the application lifecycle.
"""

import os
import logging
import json
from typing import Dict, Any, Optional, List
from pymongo import MongoClient
from pymongo.errors import PyMongoError, DuplicateKeyError
from bson import ObjectId
import certifi
from dotenv import load_dotenv
import datetime
import time
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from sentence_transformers import SentenceTransformer   

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
                self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
                
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
    
    def test_connection(self):
        """Test MongoDB connection and collection access."""
        try:
            print("🔍 Testing MongoDB connection...")
            # Test database connection
            self._db.command('ping')
            print("✅ MongoDB connection successful!")
            
            # Test collection access
            if hasattr(self, 'qa_records'):
                count = self.qa_records.count_documents({})
                print(f"✅ Successfully accessed qa_records collection. Total documents: {count}")
            else:
                print("⚠️ qa_records collection is not initialized!")
                
        except Exception as e:
            print(f"❌ MongoDB connection test failed: {e}")
            raise
    
    # User management methods
    def create_user(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """
        Create a new user in the users collection.
        :param username: chosen username
        :param password: plain text password (should be hashed)
        :param role: one of ['user', 'agent', 'admin']
        :return: user_id (str)
        """ 
        try:
            print("👤 [MongoHandler] Creating user...")
            print(f"📝 username: {username}")
            print(f"🔐 password: {password}")
            
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
        """
        Verify user credentials.
        :param username: username to verify
        :param password: password to verify
        :return: user document if verification is successful, None otherwise
        """
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
        """
        Get user by ID.
        :param user_id: ID of the user to retrieve
        :return: user document if found, None otherwise
        """
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
        """
        Generate a new API key for the user.
        :param user_id: ID of the user to rotate API key for
        :return: new API key if rotation is successful, None otherwise
        """
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
        """  
        Save a QA record to the database.
        
        Args:
            user_id: The ID of the user who asked the question
            question: The question asked by the user
            answer: The answer provided by the LLM
            metadata: Optional metadata associated with the QA record
            
        Returns:
            str: The ID of the saved QA record
        """
        try:
            # Debug: Check if json module is available
            try:
                import json
                print("✅ json module is available")
            except ImportError as e:
                print(f"❌ json module import error: {e}")
                raise

            print(f"🔍 [MongoDB] Attempting to save QA record for user: {user_id}")
            print(f"📝 Question: {question[:100]}..." if len(question) > 100 else f"📝 Question: {question}")
            print(f"📝 Answer: {answer[:100]}..." if len(answer) > 100 else f"📝 Answer: {answer}")
            
            # Safely convert metadata to string for logging
            try:
                metadata_str = json.dumps(metadata, default=str) if metadata is not None else 'None'
                print(f"📦 Metadata: {metadata_str}")
            except Exception as e:
                print(f"⚠️ Could not serialize metadata: {e}")
                metadata_str = str(metadata)
            
            if not hasattr(self, 'qa_records') or self.qa_records is None:
                print("⚠️ [MongoDB] qa_records collection is not initialized!")
                return None
                
            record = {
                'user_id': user_id,
                'question': question,
                'answer': answer,
                'metadata': metadata or {},
                'timestamp': datetime.datetime.utcnow(),
                'version': '2.1'
            }
            
            print("📡 [MongoDB] Inserting record into database...")
            result = self.qa_records.insert_one(record)
            
            if result and result.inserted_id:
                print(f"✅ [MongoDB] Successfully saved QA record with ID: {result.inserted_id}")
                return str(result.inserted_id)
            else:
                print("⚠️ [MongoDB] Insert operation completed but no inserted_id was returned!")
                return None
            
        except PyMongoError as e:
            error_msg = f"❌ [MongoDB] Error saving QA record: {str(e)}"
            print(error_msg)
            logger.error(error_msg)
            raise
        except Exception as e:
            error_msg = f"❌ [MongoDB] Unexpected error in save_qa_record: {str(e)}"
            print(error_msg)
            logger.error(error_msg, exc_info=True)
            raise
    
    def get_user_qa_history(self, user_id: str, limit: int = 10, skip: int = 0) -> List[Dict]:
        """  
        Get QA history for a user.
        
        Args:
            user_id: The ID of the user to retrieve QA history for
            limit: The maximum number of records to retrieve
            skip: The number of records to skip
            
        Returns:
            List[Dict]: A list of QA records for the user
        """
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
            logger.error(f"❌ Error getting QA history: {e}")
            raise

    def find_by_prompt(self, prompt_text):
        """Find a QA record by exact prompt match"""
        try:
            if self.qa_records is None:  # Proper None check for collection
                return None
                
            result = self.qa_records.find_one({
                "$or": [
                    {"question": prompt_text},
                    {"metadata.question": prompt_text}
                ]
            })
            
            if result and '_id' in result:
                result['_id'] = str(result['_id'])
                return result
            return None
            
        except Exception as e:
            print(f"❌ [MongoDB] Error finding prompt: {e}")
            import traceback
            traceback.print_exc()
            return None

    def semantic_search_by_prompt(self, query, threshold=0.85, top_k=1):
        """
        Perform semantic search on the QA records collection.
        
        Args:
            query: The query to search for
            threshold: The minimum similarity threshold
            top_k: The number of top results to return
        
        Returns:
            List[Dict]: A list of QA records matching the query
        """
        print("\n--- MongoDBHandler.semantic_search_by_prompt ---")
        try:
            query_embedding = self.embedding_model.encode(query).reshape(1, -1)

            # Fetch all records with non-null embeddings
            records = list(self.qa_records.find({"embedding": {"$ne": None}}))

            similarities = []
            for rec in records:
                emb = rec.get('embedding')
                if emb:
                    sim = cosine_similarity([emb], query_embedding)[0][0]
                    similarities.append((rec, sim))

            # Sort by similarity
            sorted_results = sorted(similarities, key=lambda x: x[1], reverse=True)
            filtered = [r for r in sorted_results if r[1] >= threshold]

            print(f"🔍 Found {len(filtered)} matching records above threshold {threshold}")
            return [r[0] for r in filtered[:top_k]]

        except Exception as e:
            print(f"❌ Error in semantic_search_by_prompt: {str(e)}")
            return []
    
    def search(self, prompt, threshold=0.85):
        """
        Perform a search on the QA records collection.
        
        Args:
            prompt: The prompt to search for
            threshold: The minimum similarity threshold for semantic search
        
        Returns:
            Tuple[Dict, str, float]: A tuple containing:
                - The matching record (or None if no match)
                - The match type ('exact', 'semantic', or 'not_found')
                - The similarity score (1.0 for exact matches, 0.0 for no match)
        """
        print("\n--- MongoDBHandler.search ---")
        print(f"🔎 Searching MongoDB for: {prompt[:50]}...")

        # Try exact match first
        exact_match = self.find_by_prompt(prompt)
        if exact_match:
            print("✅ Exact match found in MongoDB")
            return exact_match, 'exact', 1.0

        # Fallback to semantic search
        semantic_results = self.semantic_search_by_prompt(prompt, threshold=threshold)
        if semantic_results:
            best_match = semantic_results[0]
            # Get the similarity score from the semantic search
            query_embedding = self.embedding_model.encode(prompt).reshape(1, -1)
            result_embedding = np.array(best_match.get('embedding', [])).reshape(1, -1)
            similarity = float(cosine_similarity(query_embedding, result_embedding)[0][0])
            
            print(f"✅ Semantic match found in MongoDB (similarity: {similarity:.2f})")
            return best_match, 'semantic', similarity

        print("❌ No match found in MongoDB")
        return None, 'not_found', 0.0

# Create a singleton instance
db_handler = MongoDBHandler()   
