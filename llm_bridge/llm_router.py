"""
llm_router.py - LLM Model Router Implementation

This module implements the LLMRouter class, which is responsible for:
1. Managing connections to different LLM providers
2. Routing queries to appropriate models based on complexity and requirements
3. Handling fallback mechanisms when primary models fail
4. Managing API rate limits and quotas
5. Tracking model usage and performance metrics

Key Features:
- Dynamic model selection based on query characteristics
- Automatic fallback to secondary models on failure
- Configurable rate limiting and quota management
- Support for multiple LLM providers (OpenAI, etc.)
- Response caching integration
"""

import requests
from config import get_config
import re

# Get the configuration
config = get_config()
llm_config = config['llm']

class LLMRouter:
    """
    Routes queries to appropriate LLM models based on complexity and requirements.
    
    The LLMRouter is responsible for selecting the most appropriate language model
    for a given query, managing API connections, and handling fallback mechanisms.
    
    Attributes:
        cache_manager: Reference to the cache manager for response caching
        llm2_config: Configuration for the base model (e.g., GPT-3.5)
        llm3_config: Configuration for the advanced model (e.g., GPT-4)
        api_key: API key for the LLM provider
        
    Configuration Options:
        llm2_model: Identifier for the base model
        llm2_model_name: Display name for the base model
        llm3_model: Identifier for the advanced model
        llm3_model_name: Display name for the advanced model
        basic_max_tokens: Maximum tokens for basic responses
        enhanced_max_tokens: Maximum tokens for enhanced responses
        temperature: Sampling temperature for generation
    """
    
    def __init__(self, cache_manager=None):
        """
        Initialize the LLMRouter with configuration and cache manager.
        
        Args:
            cache_manager: Optional cache manager instance for response caching
        """
        print("\n=== Initializing LLMRouter ===")
        self.cache_manager = cache_manager  # Store the cache manager for embeddings
        
        # Get the configuration
        config = get_config()
        llm_config = config['llm']
        
        print(f"Config keys: {list(llm_config.keys())}")
        
        # Debug: Print all config values (redacting sensitive info)
        for key, value in llm_config.items():
            if 'key' in key.lower() or 'secret' in key.lower():
                print(f"{key}: {'*' * 8}")
            else:
                print(f"{key}: {value}")
        
        self.api_key = llm_config['openai_api_key']
        
        # Ensure required config keys exist
        required_keys = [
            'llm2_model', 'llm2_model_name', 'llm3_model', 'llm3_model_name',
            'basic_max_tokens', 'enhanced_max_tokens', 'temperature'
        ]
        
        for key in required_keys:
            if key not in llm_config:
                print(f"⚠️ Missing required config key: {key}")
        
        # Set up LLM2 config (base model, e.g., GPT-3.5)
        self.llm2_config = {
            'model': llm_config['llm2_model'],
            'model_name': llm_config.get('llm2_model_name', 'GPT-3.5'),
            'max_tokens': llm_config['basic_max_tokens'],
            'temperature': llm_config['temperature']
        }
        
        # Set up LLM3 config (advanced model, e.g., GPT-4)
        self.llm3_config = {
            'model': llm_config['llm3_model'],
            'model_name': llm_config.get('llm3_model_name', 'GPT-4'),
            'max_tokens': llm_config['enhanced_max_tokens'],
            'temperature': llm_config['temperature']
        }
        
        print(f"LLM2 Config: {self.llm2_config}")
        print(f"LLM3 Config: {self.llm3_config}")
        print("LLMRouter initialization complete\n")

    def extract_confidence(self, text):
        match = re.search(r'\[CONFIDENCE:(1\.0|0(\.\d+)?)\]', text)
        return float(match.group(1)) if match else None

    def clean_response(self, text):
        return re.sub(r'\s*\[CONFIDENCE:(1\.0+|0\.\d+)\]\s*$', '', text).strip()

    def route_to_llm(self, prompt, response_type):
        # Use llm3_config (GPT-4) for complex responses, llm2_config (GPT-3.5) for simple ones
        config = self.llm3_config if response_type == 'complex' else self.llm2_config
        return self._call_openai_api(prompt, config, config['model_name'])  

    def _call_openai_api(self, prompt, config, llm_type):
        try:
            print(f"\n=== LLM Router: Calling OpenAI API ===")
            print(f"Using model: {config['model']}")
            print(f"Display name: {config.get('model_name', 'N/A')}")
            print(f"Prompt: {prompt[:100]}...")
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            data = {
                'model': config['model'],
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': config['max_tokens'],
                'temperature': config['temperature']
            }
            
            print(f"Sending request to OpenAI API with data: {data}")
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data
            )
            
            print(f"OpenAI API response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"OpenAI API response: {result}")
                
                raw_answer = result['choices'][0]['message']['content']
                confidence = self.extract_confidence(raw_answer)
                clean_answer = self.clean_response(raw_answer)
                model_used = config.get('model_name', result.get('model', 'unknown'))
                
                # Extract token usage if available
                usage = result.get('usage', {})
                
                print(f"Extracted answer: {clean_answer[:100]}...")
                print(f"Model used: {model_used}")
                print(f"Token usage: {usage}")
                
                # Generate embedding with error handling
                embedding = None
                try:
                    if self.cache_manager:
                        embedding = self.cache_manager.embedding_model.encode(prompt).tolist()
                except Exception as e:
                    print(f"⚠️ Failed to generate embedding: {e}")

                response_obj = {
                    'answer': clean_answer,
                    'llm_used': model_used,
                    'model': config['model'],
                    'confidence': confidence,
                    'success': True,
                    'token_count': usage.get('total_tokens'),
                    'prompt_tokens': usage.get('prompt_tokens'),
                    'completion_tokens': usage.get('completion_tokens'),
                    'embedding': embedding
                }
                
                print(f"Returning response_obj: {response_obj}")
                return response_obj
            else:
                error_msg = f"OpenAI API error: {response.status_code} - {response.text}"
                print(error_msg)
                return {
                    'answer': "I'm sorry, I encountered an error processing your request.",
                    'llm_used': config.get('model_name', 'unknown'),
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            error_msg = f"Error in _call_openai_api: {str(e)}"
            print(error_msg)
            return {
                'answer': "I encountered an error while processing your request.",
                'llm_used': config.get('model_name', 'unknown'),
                'success': False,
                'error': error_msg
            }
