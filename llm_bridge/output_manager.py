# Output manager    
""" 
    This module is responsible for managing the output of the LLM bridge.
    It stores the output in the cache and MongoDB.
"""

import time

class OutputManager:
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager

    # Prepare output and store in cache and MongoDB 
    def prepare_output(self, original_json, enhanced_prompt, response_obj, evaluation, additional_info=None):
        print("\n=== OutputManager.prepare_output ===")
        print(f"response_obj keys: {response_obj.keys()}")
        print(f"response_obj llm_used: {response_obj.get('llm_used')}")

        initial_prompt = original_json.get('prompt', '')
        
        # Prepare model metadata
        model_metadata = {
            'llm_used': response_obj.get('llm_used', 'unknown'),
            'confidence': response_obj.get('confidence'),
            'from_cache': False,  # This is set to False here and can be overridden later
            'is_guest': original_json.get('sender_id', '').startswith('guest_')
        }
        
        output_json = {
            'response': response_obj.get('response', ''),
            'vibe_used': original_json.get('vibe', 'general'),  
            'question_id': original_json.get('question_id'),
            'sender_id': original_json.get('sender_id'),
            'model_metadata': model_metadata
        }

        # Preserve follow_up_questions and needs_more_info if they exist
        if 'follow_up_questions' in response_obj:
            output_json['follow_up_questions'] = response_obj['follow_up_questions']
        if 'needs_more_info' in response_obj:
            output_json['needs_more_info'] = response_obj['needs_more_info']

        print(f"output_json before cache: {output_json}")

        # Store in cache    
        session_json = {
            'timestamp': int(time.time()),
            'initial_prompt': initial_prompt,
            'vibe': original_json.get('vibe', 'general'),
            'response_preference': original_json.get('response_preference', 'informative'),
            'show_confidence': original_json.get('show_confidence', False),
            'additional_info': additional_info,
            'enhanced_prompt': enhanced_prompt,
            'response': response_obj,
            'evaluation': evaluation,
            'final_output': output_json
        }
        self.cache_manager.store_response(session_json)

        # Save to MongoDB
        try:
            save_record(
                user_id=original_json.get('sender_id'),
                question=initial_prompt,
                answer=response_obj.get('response', ''),
                model=response_obj.get('llm_used', 'unknown'),
                confidence=response_obj.get('confidence'),
                tokens=response_obj.get('token_count', None),
                embedding=response_obj.get('embedding', None),
                cot_steps=response_obj.get('reasoning_steps', None)
            )
        except Exception as e:
            print(f"⚠️ MongoDB save failed: {e}")

        print(f"Final output_json: {output_json}")
        return output_json
