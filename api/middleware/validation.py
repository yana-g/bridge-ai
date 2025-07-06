"""
Input validation middleware for the LLM Bridge API.

This module provides middleware for validating incoming requests.
"""

import re
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Callable, Dict, Any, Optional

class InputValidator:
    """Middleware for validating API inputs."""
    
    def __init__(self, app):
        self.app = app
        # Define validation rules for different endpoints
        self.validation_rules = {
            "/ask-llm/": self._validate_llm_request,
            "/health": self._validate_health_check
        }
    
    async def __call__(self, request: Request, call_next):
        # Skip validation for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
            
        # Get validation function for the current path
        validator = self.validation_rules.get(request.url.path)
        if validator:
            try:
                # Validate the request
                await validator(request)
            except HTTPException as e:
                # Re-raise HTTP exceptions
                raise e
            except Exception as e:
                # Catch any other validation errors
                return JSONResponse(
                    status_code=422,
                    content={"detail": f"Validation error: {str(e)}"}
                )
        
        # Proceed to the next middleware/route handler
        return await call_next(request)
    
    async def _validate_llm_request(self, request: Request) -> None:
        """Validate /ask-llm/ endpoint request."""
        try:
            body = await request.json()
            
            # Required fields
            required_fields = ["vibe", "sender_id", "question_id", "question"]
            for field in required_fields:
                if field not in body:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate sender_id format (alphanumeric with underscores and hyphens)
            if not re.match(r'^[a-zA-Z0-9_-]+$', body["sender_id"]):
                raise ValueError("Invalid sender_id format")
                
            # Validate question_id format (UUID or similar)
            if not re.match(r'^[a-f0-9-]+$', body["question_id"]):
                raise ValueError("Invalid question_id format")
                
            # Validate question length
            if len(body["question"].strip()) < 5:
                raise ValueError("Question is too short")
                
            if len(body["question"]) > 10000:
                raise ValueError("Question is too long")
                
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON payload")
    
    async def _validate_health_check(self, request: Request) -> None:
        """No validation needed for health check endpoint."""
        pass

def setup_validation_middleware(app):
    """Configure and return the validation middleware."""
    return InputValidator(app)
