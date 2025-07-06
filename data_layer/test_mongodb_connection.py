"""
MongoDB Connection Tester

A standalone utility to test MongoDB connection with various configurations.
Automatically loads environment variables from .env file.
"""

import os
import sys
import certifi
from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv
from urllib.parse import quote_plus

def test_mongodb_connection():
    """Test MongoDB connection with various configurations."""
    print("\n=== MongoDB Connection Tester ===\n")
    
    # Load environment variables from .env file
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir.parent  # Go up one level from data_layer to project root
    env_path = project_root / '.env'
    
    print(f"Looking for .env file at: {env_path}")
    
    if not env_path.exists():
        print(f"✗ .env file not found at: {env_path}")
        return False
        
    load_dotenv(dotenv_path=env_path)
    
    # Get connection string from environment
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        print("✗ MONGO_URI not found in environment variables")
        print("Please make sure it's set in your .env file")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Environment variables loaded from: {env_path}")
        return False
    
    # Print a safe version of the URI (without credentials)
    safe_uri = mongo_uri.split('@')[-1] if '@' in mongo_uri else mongo_uri
    print(f"Testing connection to: {safe_uri}")
    
    # Test configurations
    test_cases = [
        {
            "name": "1. TLS with system CA certificates (recommended for Atlas)",
            "options": {
                "tls": True,
                "tlsCAFile": certifi.where(),
                "retryWrites": True,
                "w": 'majority',
                "connectTimeoutMS": 10000,
                "serverSelectionTimeoutMS": 10000,
                "appname": 'MongoDBTester'
            }
        },
        {
            "name": "2. TLS with invalid certs allowed (for testing only)",
            "options": {
                "tls": True,
                "tlsAllowInvalidCertificates": True,
                "tlsInsecure": True,
                "retryWrites": True,
                "w": 'majority',
                "connectTimeoutMS": 10000,
                "serverSelectionTimeoutMS": 10000,
                "appname": 'MongoDBTester'
            }
        },
    ]
    
    for test in test_cases:
        print(f"\n{test['name']}")
        print("-" * 60)
        print(f"Options: {test['options']}")
        
        try:
            # Create a new client with the specified options
            client = MongoClient(mongo_uri, **test['options'])
            
            # Test the connection with a ping
            print("Sending ping to MongoDB...")
            ping_result = client.admin.command('ping')
            print("✓ Successfully connected to MongoDB")
            print(f"Ping response: {ping_result}")
            
            # Test database operations
            try:
                db_name = os.getenv("MONGO_DB_NAME", "test")
                db = client[db_name]
                print(f"✓ Connected to database: {db.name}")
                
                # List collections (may be empty)
                collections = db.list_collection_names()
                print(f"Available collections: {collections}")
                
                # If we get here, connection was successful
                client.close()
                return True
                
            except Exception as e:
                print(f"⚠ Database operation failed: {e}")
                client.close()
                return True
            
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            continue
    
    print("\n✗ All connection attempts failed")
    print("\nTroubleshooting tips for MongoDB Atlas:")
    print("1. Verify your IP is whitelisted in MongoDB Atlas Network Access")
    print("2. Check if your credentials are correct")
    print("3. Make sure your cluster is running")
    print("4. Try connecting with MongoDB Compass using the same connection string")
    print("5. Check if there are any firewall or network restrictions")
    
    return False

if __name__ == "__main__":
    try:
        # Install python-dotenv if not already installed
        try:
            import dotenv
        except ImportError:
            print("Installing python-dotenv...")
            import subprocess
            import sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
            from dotenv import load_dotenv
            
        if test_mongodb_connection():
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
