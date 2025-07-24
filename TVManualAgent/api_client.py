"""
BRIDGE API Client for TV Manual Agent

This module provides a client for interacting with the BRIDGE API to process
natural language questions and retrieve answers based on TV manual content.

Key Features:
- Authentication with API keys
- Question submission with configurable parameters
- Response handling and error management
- Support for different response vibes and answer natures

Dependencies:
    requests: For making HTTP requests to the BRIDGE API
    uuid: For generating unique question IDs
"""
import requests
import json
import uuid
from typing import Dict, Any

class APIClient:
    def __init__(self, base_url: str, api_key: str):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL of the BRIDGE API
            api_key: API key for authentication
            
        Raises:
            ValueError: If the API key is empty or invalid
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key.strip()
        
        if not self.api_key:
            raise ValueError("API key is required")
        
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def ask_bridge(self, question: str, vibe: str = "Business/Professional", 
                  sender_id: str = "tv_manual_agent") -> Dict[str, Any]:
        """
        Send a question to the BRIDGE API.
        
        Args:
            question: The question to ask
            vibe: The tone/style of the response
            sender_id: Identifier for the client making the request
            
        Returns:
            dict: The API response containing the answer and metadata
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
            ValueError: If the response cannot be parsed or contains an error
        """
        try:
            data = {
                "question": question,
                "vibe": vibe,
                "sender_id": sender_id,
                "question_id": str(uuid.uuid4()),
                "confidence": True,
                "nature_of_answer": "Medium"
            }
            
            response = requests.post(
                f"{self.base_url}/ask-llm/",
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"API request failed: {str(e)}",
                "response": "I'm having trouble connecting to the knowledge base. Please try again later."
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "response": "An unexpected error occurred. Please try again."
            }
    
    def check_health(self) -> Dict[str, Any]:
        """
        Check the health of the BRIDGE API
        
        Returns:
            dict: The API response containing the health status and details
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
            ValueError: If the response cannot be parsed or contains an error
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            response.raise_for_status()
            return {"status": "healthy", "details": response.json()}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}