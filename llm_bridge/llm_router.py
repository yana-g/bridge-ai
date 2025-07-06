import requests
from config import get_config
import re

# Get the configuration
config = get_config()
llm_config = config['llm']

class LLMRouter:
    def __init__(self):
        print("\n=== Initializing LLMRouter ===")
        print(f"Config keys: {list(llm_config.keys())}")
        
        # Debug: Print all config values
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
        
        # Set up LLM2 config
        self.llm2_config = {
            'model': llm_config['llm2_model'],
            'model_name': llm_config.get('llm2_model_name', 'GPT-3.5'),  # Default fallback
            'max_tokens': llm_config['basic_max_tokens'],
            'temperature': llm_config['temperature']
        }
        
        # Set up LLM3 config
        self.llm3_config = {
            'model': llm_config['llm3_model'],
            'model_name': llm_config.get('llm3_model_name', 'GPT-4'),  # Default fallback
            'max_tokens': llm_config['enhanced_max_tokens'],
            'temperature': llm_config['temperature']
        }
        
        print(f"LLM2 Config: {self.llm2_config}")
        print(f"LLM3 Config: {self.llm3_config}")
        print("LLMRouter initialization complete\n")

    def extract_confidence(self, text):
        match = re.search(r'\[CONFIDENCE:([0-1]\.[0-9])\]', text) 
        return float(match.group(1)) if match else None

    def clean_response(self, text):
        return re.sub(r'\s*\[CONFIDENCE:[0-1]\.[0-9]\]\s*$', '', text).strip() 

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
                
                print(f"Extracted answer: {clean_answer[:100]}...")
                print(f"Model used: {model_used}")
                
                response_obj = {
                    'answer': clean_answer,
                    'llm_used': model_used,  # Use the display name from config
                    'model': config['model'],  # Keep the actual model ID as well
                    'confidence': confidence,
                    'success': True
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
