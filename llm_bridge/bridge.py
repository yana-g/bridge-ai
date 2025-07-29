# bridge.py - Core LLM Bridge Implementation

"""
LLM Bridge - Intelligent Query Routing and Processing System

This module implements the core LLMBridge class that serves as the central orchestrator
for processing natural language queries through a pipeline of specialized components.

The LLMBridge handles:
1. Initial query analysis and preprocessing
2. Semantic caching and response retrieval
3. Dynamic model selection and routing
4. Response quality evaluation
5. Follow-up question generation
6. Output formatting and delivery

Key Components:
- PromptAnalyzer: Determines query intent and requirements
- LLMRouter: Selects appropriate LLM based on query characteristics
- AnswerEvaluator: Assesses response quality and suggests improvements
- CacheManager: Handles response caching and retrieval
- OutputManager: Formats and structures final responses

Example Usage:
    bridge = LLMBridge(config={
        'use_cache': True,
        'check_informativeness': True
    })
    
    response = bridge.process_request({
        'prompt': 'Explain quantum computing',
        'vibe': 'Academic/Research',
        'sender_id': 'user123',
        'confidence': True,
        'nature_of_answer': 'Detailed'
    })
"""

import re
from urllib.parse import quote_plus
from llm_bridge.cache_manager import LocalCacheManager
from llm_bridge.prompt_analyzer import PromptAnalyzer
from llm_bridge.response_classifier import ResponseTypeClassifier
from llm_bridge.prompt_enhancer import PromptEnhancer
from llm_bridge.llm_router import LLMRouter
from llm_bridge.answer_evaluator import AnswerEvaluator
from llm_bridge.output_manager import OutputManager

class LLMBridge:
    """
    Main orchestrator for processing natural language queries through the LLM pipeline.
    
    The LLMBridge coordinates between various components to:
    1. Analyze incoming prompts for intent and requirements
    2. Check for cached responses before processing
    3. Route queries to appropriate LLM models
    4. Evaluate and enhance response quality
    5. Generate follow-up questions when needed
    6. Format and return final responses
    
    Attributes:
        config (dict): Configuration parameters for the bridge
        cache_manager (LocalCacheManager): Handles response caching
        prompt_analyzer (PromptAnalyzer): Analyzes prompt complexity and requirements
        response_classifier (ResponseTypeClassifier): Classifies response types
        prompt_enhancer (PromptEnhancer): Enhances prompts for better LLM responses
        llm_router (LLMRouter): Routes queries to appropriate LLM models
        answer_evaluator (AnswerEvaluator): Evaluates response quality
        output_manager (OutputManager): Formats and structures final responses
        use_cache (bool): Whether to use response caching
        check_informativeness (bool): Whether to check response informativeness
    """
    
    def __init__(self, config=None):
        """
        Initialize the LLMBridge with optional configuration.
        
        Args:
            config (dict, optional): Configuration dictionary. May include:
                - use_cache (bool): Enable/disable response caching
                - check_informativeness (bool): Enable/disable response quality checks
                - cache_ttl (int): Cache time-to-live in seconds
                - max_cache_size (int): Maximum number of cache entries
        """
        self.config = config or {}
        self.cache_manager = LocalCacheManager()
        self.prompt_analyzer = PromptAnalyzer()
        self.response_classifier = ResponseTypeClassifier()
        self.prompt_enhancer = PromptEnhancer()
        self.llm_router = LLMRouter(cache_manager=self.cache_manager)  # Pass cache manager to router
        self.answer_evaluator = AnswerEvaluator()
        self.output_manager = OutputManager(self.cache_manager)
        
        # Allow disabling cache for testing
        self.use_cache = self.config.get('use_cache', True)
        # Allow disabling "needs more info" for testing
        self.check_informativeness = self.config.get('check_informativeness', True)

    def process_request(self, request_json):
        """
        Process a natural language query through the LLM pipeline.
        
        Args:
            request_json (dict): Request data containing the query prompt and other metadata
        
        Returns:
            dict: Final response object containing the answer, metadata, and other relevant information
        """
        print("\n=== Starting LLMBridge.process_request ===")
        prompt = request_json.get('prompt', '')
        print(f"Processing prompt: {prompt}")
        
        cot_steps = [] # List to store CoT steps (if any) 

        # Step 0: Check for simple intents that Bridge can handle directly
        simple_response = self._handle_simple_intents(prompt, request_json)
        if simple_response:
            print("Simple intent detected - returning direct response")
            simple_response.setdefault("model_metadata", {})
            simple_response["model_metadata"]["cot"] = "Simple intent detected - responded directly without external LLM."
            return simple_response

        # Step 1: Check if this is a math expression
        if self.prompt_analyzer.is_math_expression(prompt):
            cleaned_expr, result = self.prompt_analyzer.evaluate_math_expression(prompt)
            
            # Check if evaluation was successful
            if "❌" in result:
                response_text = f"⚠️ Sorry, I couldn't compute that. {result}"
                confidence = 0.0
            else:
                response_text = f"{cleaned_expr} = {result}"
                confidence = 1.0

            return {
                'response': response_text,
                'llm_used': 'math_evaluator',
                'model_metadata': {
                    'confidence': confidence,
                    'simple_intent': 'math_expression',
                    'from_cache': False,
                    'is_guest': request_json.get('sender_id', '').startswith('guest_')
                }
            }

        # Step 2: Check cache first (if enabled)
        if self.use_cache:
            print("\n--- Checking cache ---")
            # Extract vibe and nature_of_answer from request
            vibe = request_json.get("vibe")
            nature_of_answer = request_json.get("nature_of_answer")
        
            print(f"Cache search parameters: prompt='{prompt[:50]}...', vibe='{vibe}', nature_of_answer='{nature_of_answer}'")
        
            # Call cache search with all parameters
            cached_response, match_type, similarity = self.cache_manager.search(
                prompt=prompt,
                vibe=vibe,
                nature_of_answer=nature_of_answer
            )
        
            print(f"Cache search - match_type: {match_type}, cached_response: {cached_response is not None}")
        
            if match_type in ['exact', 'semantic', 'mongo'] and cached_response:
                # Correct cache source detection
                if match_type == 'mongo':
                    cache_source = 'mongo'
                    response_text = cached_response.get('answer', '')
                    existing_metadata = cached_response.get('metadata', {})
                else:
                    # match_type is 'exact' or 'semantic' from local cache
                    cache_source = 'local'
                    # Local cache has response in final_output
                    if 'final_output' in cached_response:
                        response_text = cached_response['final_output']['response']
                        existing_metadata = cached_response['final_output'].get('model_metadata', {})
                    else:
                        response_text = ''
                        existing_metadata = {}
                
                print(f"Serving from {cache_source} cache (match type: {match_type}, similarity: {similarity:.2f})")
            
                # Unified response format
                model_metadata = existing_metadata.copy()
                model_metadata.update({
                    'cache_match_type': match_type,
                    'cache_similarity': similarity,
                    'from_cache': True,
                    'is_guest': request_json.get('sender_id', '').startswith('guest_'),
                    'cot': f"Response retrieved from {cache_source} cache - match type: {match_type}, similarity: {similarity:.2f}. Search included vibe: '{vibe}', nature_of_answer: '{nature_of_answer}'."
                })
            
                return {
                    'response': response_text,
                    'llm_used': f'cache_{cache_source}',
                    'model_metadata': {k: v for k, v in model_metadata.items() if k != 'llm_used'}
                }
            
            print("Cache entry not found, proceeding with LLM processing")
            cot_steps.append(f"Cache entry not found for prompt with vibe '{vibe}' and nature_of_answer '{nature_of_answer}' - proceeding with LLM processing.")
        else:
            print("Cache disabled, proceeding directly to LLM processing")
            cot_steps.append("Cache disabled - proceeding with LLM processing.")

        # Step 3: Full Bridge logic (existing)
        return self._full_bridge_process(prompt, request_json, cot_steps)

    def _handle_simple_intents(self, prompt, request_json):
        """
        Handle simple intents that don't require LLM processing.
        
        Args:
            prompt (str): Input prompt to check
            request_json (dict): Request data containing the query prompt and other metadata
        
        Returns:
            dict: Response object with a direct response and metadata, or None if no simple intent is detected
        """
        
        # First check for non-English
        if self.prompt_analyzer.detect_non_english(prompt):
            response_text = self.prompt_analyzer.handle_non_english_intent(prompt)
            return {
                'response': response_text,
                'llm_used': 'BRIDGE',
                'model_metadata': {
                    'confidence': 1.0,
                    'from_cache': False,
                    'simple_intent': 'non_english',
                    'is_guest': request_json.get('sender_id', '').startswith('guest_')
                }
            }

        # Then check for other simple intents
        intent = self.prompt_analyzer.detect_simple_intent(prompt)
        
        if intent:
            response_text = self.prompt_analyzer.get_simple_response(intent, prompt)
            if response_text:
                return {
                    'response': response_text,
                    'llm_used': 'BRIDGE',
                    'model_metadata': {
                        'confidence': 1.0,
                        'from_cache': False,
                        'simple_intent': intent,
                        'is_guest': request_json.get('sender_id', '').startswith('guest_')
                    }
                }

        return None

    def _full_bridge_process(self, prompt, request_json, cot_steps=None):
        """
        Run the full Bridge processing pipeline for the input prompt.
        
        Args:
            prompt (str): Input prompt to process
            request_json (dict): Request data containing the query prompt and other metadata
            cot_steps (list): List of chain-of-thought steps to track processing
        
        Returns:
            dict: Final response object containing the answer, metadata, and other relevant information
        """
        print("Running full Bridge processing...")

        # Initialize cot_steps if None 
        if cot_steps is None:
            cot_steps = []
        
        # Check if we need more information - made much less strict for better flow
        if self.check_informativeness:
            score, questions = self.prompt_analyzer.analyze_informativeness(prompt, request_json.get('vibe', 'general'))
            if score < 0.3 and questions:  # Changed from 0.5 to 0.3 - much less strict
                print("Prompt needs more information")
                # Create a response object that includes the questions
                response_obj = {
                    'response': "I'd love to help! To give you the most helpful answer, could you share a bit more about what you're looking for?",
                    'follow_up_questions': questions,
                    'needs_more_info': True,
                    'llm_used': 'BRIDGE',
                    'confidence': 1.0
                }
                # Pass the response object to prepare_output
                return self.output_manager.prepare_output(request_json, prompt, response_obj, {}, [])

        # Process the request through the LLM
        response_type = self.response_classifier.classify_response_type(prompt, request_json.get('vibe', 'general'), request_json.get('response_preference', 'informative'))
        cot_steps.append(f"Classified response type as '{response_type}' based on prompt and vibe.")
        additional_info = request_json.get('additional_info', [])
        enhanced_prompt = self.prompt_enhancer.enhance_prompt(prompt, request_json.get('vibe', 'general'), response_type, additional_info, request_json.get('show_confidence', False))
        
        print(f"Routing to LLM with response type: {response_type}")
        response_obj = self.llm_router.route_to_llm(enhanced_prompt, response_type)
        model_used = response_obj.get('llm_used', 'unknown').lower()
        llm2_name = self.llm_router.llm2_config['model_name'].lower()
        llm3_name = self.llm_router.llm3_config['model_name'].lower()

        if llm3_name in model_used:
            used_llm_label = "LLM3"
        elif llm2_name in model_used:
            used_llm_label = "LLM2"
        else:
            used_llm_label = "Unknown"

        cot_steps.append(f"Called {used_llm_label} with response type '{response_type}' - model used: {model_used}.")
        print(f"Initial response_obj: {response_obj}")
        
        evaluation = self.answer_evaluator.evaluate_answer(response_obj, prompt)
        print(f"Evaluation: {evaluation}")

        # If upgrade needed, try with LLM3
        if evaluation.get('needs_upgrade', False):
            print("Upgrading to LLM3")
            score = evaluation.get('quality')
            threshold = self.answer_evaluator.thresholds.get('upgrade_threshold')
            model_used = response_obj.get('llm_used', 'unknown')
            cot_steps.append(
                f"Initial response from {model_used} scored {score:.2f}, below threshold {threshold} → fallback triggered to LLM3."
            )
            response_obj = self.llm_router._call_openai_api(
                enhanced_prompt, 
                self.llm_router.llm3_config, 
                self.llm_router.llm3_config['model_name']
            )
            cot_steps.append(f"LLM3 responded - model used: {response_obj.get('llm_used', 'unknown')}.")    
            print(f"Upgraded response_obj: {response_obj}")
            evaluation = self.answer_evaluator.evaluate_answer(response_obj, prompt)

        # Prepare the final output
        response_obj.setdefault("cot_steps", cot_steps)
        output = self.output_manager.prepare_output(request_json, enhanced_prompt, response_obj, evaluation, additional_info)
        
        # Ensure llm_used is properly set in the response
        if 'llm_used' not in output.get('model_metadata', {}) and 'llm_used' in response_obj:
            output.setdefault('model_metadata', {})['llm_used'] = response_obj['llm_used']
        
        print(f"Final output from bridge: {output}")
        return output