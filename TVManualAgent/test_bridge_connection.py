import os
import requests
import uuid
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_connection():
    # Get configuration from environment variables
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    api_key = os.getenv("API_KEY")
    
    if not api_key:
        print("Error: API_KEY not found in .env file")
        return
    
    # Test health endpoint
    print(f"\nTesting health endpoint at {base_url}/health...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Status Code: {response.status_code}")
        print("Response:", response.text)
    except Exception as e:
        print(f"Error: {str(e)}")
        return
    
    # Test ask-llm endpoint
    print(f"\nTesting ask-llm endpoint at {base_url}/ask-llm/...")
    try:
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "question": "Test connection",
            "vibe": "Business/Professional",
            "sender_id": "test-client",
            "question_id": str(uuid.uuid4()),
            "confidence": True,
            "nature_of_answer": "Short"
        }
        
        response = requests.post(
            f"{base_url}/ask-llm/",
            json=data,
            headers=headers
        )
        
        print(f"Status Code: {response.status_code}")
        response_data = response.json()
        print("Response:", response_data)
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_connection()