"""
Configuration settings for the LLM Bridge application.

This module contains all configuration parameters used throughout the application,
loaded from environment variables with sensible defaults.
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# === Environment ===
ENV = os.getenv("ENV", "development")  # development / production / test
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# === API Configuration ===
API_CONFIG = {
    "title": "LLM Bridge API",
    "version": "1.0.0",
    "description": "API for routing LLM requests with authentication and logging",
    "api_key_header": "X-API-Key",
    "api_key": os.getenv("BRIDGE_API_KEY"),
    "debug": DEBUG,
    "allowed_agents": [
        "web-client",
        "mobile-app",
        "cli-tool",
        "test-agent"
    ]
}

# === LLM Configuration ===
LLM_CONFIG = {
    "openai_api_key": os.getenv("OPENAI_API_KEY"),
    "llm2_model": os.getenv("LLM2_MODEL", "gpt-3.5-turbo"),
    "llm2_model_name": os.getenv("LLM2_MODEL_NAME", "GPT-3.5"),
    "llm3_model": os.getenv("LLM3_MODEL", "gpt-4"),
    "llm3_model_name": os.getenv("LLM3_MODEL_NAME", "GPT-4"),
    "basic_max_tokens": int(os.getenv("BASIC_LLM_MAX_TOKENS", "1000")),
    "enhanced_max_tokens": int(os.getenv("ENHANCED_LLM_MAX_TOKENS", "2000")),
    "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
    "use_cache": os.getenv("USE_CACHE", "true").lower() == "true",
    "show_confidence_default": os.getenv("SHOW_CONFIDENCE", "false").lower() == "true"
}

# === Vibe Configuration ===
VIBE_DESCRIPTIONS = {
    "academic_research": "Respond like a university professor, citing principles, theories, or academic references.",
    "business_professional": "Respond in a formal and strategic tone, as if giving business advice to executives.",
    "technical_development": "Respond like a software engineer or developer with clear, concise code-related insight.",
    "daily_general": "Respond casually and clearly, like you're helping someone in everyday conversation.",
    "creative_emotional": "Respond with warmth, emotion, and expressive language, like a storyteller or artist.",
    "fun": "Respond in a light-hearted and humorous way.",
    "serious": "Respond in a formal and precise manner.",
    "curious": "Respond with additional questions and show interest in the topic.",
    "sarcastic": "Respond with irony and sarcasm."
}

# === Database Configuration ===
DATABASE_CONFIG = {
    "mongo_uri": os.getenv("MONGO_URI", "mongodb://localhost:27017/"),
    "db_name": os.getenv("MONGO_DB_NAME", "bridgehub"),
    "users_collection": os.getenv("MONGO_USERS_COLLECTION", "users"),
    "conversations_collection": os.getenv("MONGO_CONVERSATIONS_COLLECTION", "conversations")
}

# === Logging Configuration ===
LOGGING_CONFIG = {
    "log_dir": "logs",
    "log_file": "app.log",
    "max_file_size_mb": 10,
    "backup_count": 5,
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
}

def get_config() -> Dict[str, Any]:
    """
    Get the complete configuration dictionary.
    
    Returns:
        Dict[str, Any]: The complete configuration
    """
    return {
        "env": ENV,
        "debug": DEBUG,
        "api": API_CONFIG,
        "llm": LLM_CONFIG,
        "vibes": VIBE_DESCRIPTIONS,
        "database": DATABASE_CONFIG,
        "logging": LOGGING_CONFIG
    }