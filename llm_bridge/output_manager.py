# Output manager    
""" 
    This module is responsible for managing the output of the LLM bridge.
    It stores the output in the cache and MongoDB.
"""

import time
import json
from data_layer.mongoHandler import MongoDBHandler

class OutputManager:
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.db_handler = MongoDBHandler()

    # Prepare output and store in cache and MongoDB 
    def prepare_output(self, original_json, enhanced_prompt, response_obj, evaluation, additional_info=None):
        print("\n=== OutputManager.prepare_output ===")
        print(f"response_obj keys: {response_obj.keys()}")
        print(f"response_obj llm_used: {response_obj.get('llm_used')}")

        initial_prompt = original_json.get('prompt', '')
        
        # Prepare model metadata
        model_metadata = {
            'confidence': response_obj.get('confidence'),
            'from_cache': False,  # This is set to False here and can be overridden later
            'is_guest': original_json.get('sender_id', '').startswith('guest_'),
            'tokens': {
                'total': response_obj.get('token_count'),
                'prompt': response_obj.get('prompt_tokens'),
                'completion': response_obj.get('completion_tokens')
            },
            'embedding': response_obj.get('embedding'),
            'reasoning_steps': response_obj.get('reasoning_steps')
        }
        
        # Add Chain-of-Thought steps if available
        cot_steps = response_obj.get("cot_steps")
        if cot_steps:
            model_metadata["cot"] = " → ".join(cot_steps)

        # Get response content, checking both 'response' and 'answer' fields
        response_content = response_obj.get('response') or response_obj.get('answer', '')
        
        output_json = {
            'response': response_content,
            'llm_used': response_obj.get('llm_used', 'unknown'),
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
        
        # Decide whether this should go into the cache
        llm_used = response_obj.get('llm_used', '')
        is_external_llm = llm_used not in [
            'BRIDGE', 'math_evaluator', 'cache_local', 'cache_mongo'
        ]

        # If this is merely a "follow-up" request (needs_more_info), skip caching entirely
        if response_obj.get('needs_more_info', False):
            print("Not storing in cache - follow-up question only")

        # Otherwise, only cache if it’s not already from cache and came from an external LLM
        elif not response_obj.get('from_cache', False) and is_external_llm:
            print(f"Storing in cache - LLM used: {llm_used}")
            self.cache_manager.store_response(session_json)

            # Also save to MongoDB (only non-cache, non-empty answers)
            if response_content:
                try:
                    user_id = original_json.get('sender_id', 'unknown')
                    print("Preparing to save QA record to MongoDB...")
                    print(f" user_id: {user_id}")
                    print(f" question: {initial_prompt}")
                    print(f" answer: {response_content}")
                    self.db_handler.save_qa_record(
                        user_id=user_id,
                        question=initial_prompt,
                        answer=response_content,
                        vibe=original_json.get('vibe', 'general'),
                        nature_of_answer=original_json.get('response_preference') or original_json.get('nature_of_answer', 'informative'),
                        metadata={
                            "model": llm_used,
                            "confidence": response_obj.get('confidence'),
                            "tokens": response_obj.get('token_count'),
                            "embedding": response_obj.get('embedding'),
                            "cot_steps": response_obj.get('cot_steps'),
                            "model_reasoning_steps": response_obj.get('reasoning_steps'),
                            "vibe": original_json.get('vibe', 'general'),
                            "question_id": original_json.get('question_id'),
                        }
                    )
                    print("MongoDB save succeeded")
                except Exception as e:
                    print(f"MongoDB save failed: {e}")

        # ❌ All other cases: don’t store in cache
        else:
            if response_obj.get('from_cache', False):
                print(f"Not storing in cache - already from cache (LLM: {llm_used})")
            else:
                print(f"Not storing in cache - internal response (LLM: {llm_used})")

        print(f"Final output_json: {output_json}")
        return output_json