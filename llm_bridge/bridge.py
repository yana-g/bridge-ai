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
import requests
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
        
        # Step 0: Try handling direct math expressions
        math_expr = self.prompt_analyzer.extract_math_expression(prompt)
        if math_expr:
            print(f"Detected math expression: {math_expr}")
            result = self._handle_math_expression(math_expr, request_json)
            if result:
                return result

        # Step 1: Check for simple intents that Bridge can handle directly
        simple_response = self._handle_simple_intents(prompt, request_json)
        if simple_response:
            print("Simple intent detected - returning direct response")
            return simple_response

        # Step 2: Check cache first (if enabled)
        if self.use_cache:
            print("\n--- Checking cache ---")
            cached_response, match_type, similarity = self.cache_manager.search(prompt)
            print(f"Cache search - match_type: {match_type}, cached_response: {cached_response is not None}")
            
            if match_type in ['exact', 'semantic', 'mongo'] and cached_response:
                cache_source = 'mongo' if match_type == 'mongo' else 'local'
                print(f"Serving from {cache_source} cache (match type: {match_type}, similarity: {similarity:.2f})")
                
                # Handle different response formats from different cache sources
                if match_type == 'mongo':
                    # MongoDB returns the full record with question/answer in root
                    response_text = cached_response.get('answer', '')
                    model_metadata = cached_response.get('metadata', {})
                    model_metadata.update({
                        'llm_used': f'cache_{cache_source}',
                        'cache_match_type': match_type,
                        'cache_similarity': similarity,
                        'from_cache': True,
                        'is_guest': request_json.get('sender_id', '').startswith('guest_')
                    })
                    return {
                        'response': response_text,
                        'model_metadata': model_metadata
                    }
                else:
                    # Local cache has response in final_output
                    if 'final_output' in cached_response:
                        print(f"Cached response: {cached_response['final_output']}")
                        return {
                            'response': cached_response['final_output']['response'],
                            'model_metadata': {
                                'llm_used': f'cache_{cache_source}',
                                'cache_match_type': match_type,
                                'cache_similarity': similarity,
                                'from_cache': True,
                                'is_guest': request_json.get('sender_id', '').startswith('guest_')
                            }
                        }
            
            print("No valid cache entry found, proceeding with LLM processing")
        else:
            print("Cache disabled, proceeding directly to LLM processing")

        # Step 3: Full Bridge logic (existing)
        return self._full_bridge_process(prompt, request_json)

    def _detect_non_english(self, prompt):
        """
        Detect if the prompt is in a non-English language using langdetect.
        
        Args:
            prompt (str): Input prompt to check
        
        Returns:
            bool: True if the prompt is likely in a non-English language, False otherwise
        """
        try:
            # Fast path
            if any(ord(char) > 127 for char in prompt):
                return True

            # Smart path
            if len(prompt.split()) <= 10:
                return False  # Short English text, don't trust langdetect
            from langdetect import detect_langs
            langs = detect_langs(prompt)
            if langs:
                best_guess = langs[0]
                print(f"Detected language: {best_guess.lang} (confidence: {best_guess.prob:.2f})")
                if best_guess.lang != 'en' and best_guess.prob >= 0.90:  # Require high certainty
                    return True 
            return False  # No language detected, assume English    

        except (ImportError, LangDetectException):
            # Safe fallback: If langdetect is not installed or detection fails, assume English 
            return False

    def _handle_non_english_intent(self, prompt):
        """
        Handle non-English prompts with a polite response.
        
        Args:
            prompt (str): Input prompt to handle
        
        Returns:
            dict: Response object with a polite message and metadata
        """
        return {
            'response': "I notice you've written in a language other than English. I'm designed to work in English only. Could you please rephrase your question in English? I'm here to help! 🌍",
            'model_metadata': {
                'llm_used': 'BRIDGE',
                'confidence': 1.0,
                'from_cache': False,
                'simple_intent': 'non_english',
                'is_guest': False  # This will be updated in the actual call
            }
        }

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
        if self._detect_non_english(prompt):
            response = self._handle_non_english_intent(prompt)
            response['model_metadata']['is_guest'] = request_json.get('sender_id', '').startswith('guest_')
            return response

        # Check if this is a math expression
        if self._is_math_expression(prompt):
            cleaned_expr, result = self._evaluate_math_expression(prompt)

            # basis of the response
            response_text = f"{cleaned_expr} = {result}"

            return {
                'response': response_text,
                'model_metadata': {
                    'llm_used': 'mathjs-api',
                    'confidence': 1.0,
                    'simple_intent': 'math_expression',
                    'from_cache': False,
                    'is_guest': request_json.get('sender_id', '').startswith('guest_')
                }
        }

        # Then check for other simple intents
        intent = self._detect_simple_intent(prompt)
        
        if intent:
            response_text = self._get_simple_response(intent, prompt)
            if response_text:
                return {
                    'response': response_text,
                    'model_metadata': {
                        'llm_used': 'BRIDGE',
                        'confidence': 1.0,
                        'from_cache': False,
                        'simple_intent': intent,
                        'is_guest': request_json.get('sender_id', '').startswith('guest_')
                    }
                }

        return None


    def _detect_simple_intent(self, prompt):
        """
        Detect simple intents in the input prompt.
        
        Args:
            prompt (str): Input prompt to check
        
        Returns:
            str: Detected simple intent, or None if no simple intent is detected
        """
        prompt_lower = prompt.lower().strip()
        words = prompt_lower.split()
        
        # Check for greeting - includes multilingual greetings like 'shalom'
        greeting_patterns = [
            'hello', 'hi', 'hey', 'greetings', 'hola', 'bonjour', 'ciao', 'hallo', 'namaste', 'shalom',
            'good morning', 'good afternoon', 'good evening', 'how are you', 'how do you do', 
            'nice to meet you', 'good to see you', 'long time no see'
        ]
        if len(words) <= 3:  # Only check short prompts
            if any(pattern in prompt_lower for pattern in greeting_patterns):
                return 'greeting'

        # Check for thanks - include more variations
        thanks_patterns = [
            'thanks', 'thank you', 'appreciate it', 'much obliged', 'cheers', 
            'thanks a lot', 'thank you very much', 'grateful', 'appreciate'
        ]
        if any(pattern in prompt_lower for pattern in thanks_patterns):
            return 'thanks'

        # Check for system info - include more variations  
        system_info_patterns = [
            'what is bridge', 'how does this work', 'who made you', 'what can you do', 
            'are you human', 'are you a bot', 'are you ai', 'your capabilities', 'capabilities',
            'tell me about bridge', 'about bridge', 'how do you work'
        ]
        if any(pattern in prompt_lower for pattern in system_info_patterns):
            return 'system_info'

        # Check for unclear intent - single word unclear prompts and common unclear phrases
        unclear_words = ['help', 'what', 'who', 'when', 'where', 'why', 'how', 'problem', 'stuck', 'error', 'working']
        unclear_phrases = ['not working', 'broken', 'issue', 'wrong']
        
        # Check for unclear phrases first
        if any(phrase in prompt_lower for phrase in unclear_phrases):
            return 'unclear'
            
        if len(words) == 1 and words[0] in unclear_words:
            return 'unclear'
        
        # Also check for very short unclear phrases
        if len(words) <= 2 and any(word in unclear_words for word in words):
            return 'unclear'

        return None

    def _get_simple_response(self, intent, prompt):
        """
        Generate a simple response for the detected intent.
        
        Args:
            intent (str): Detected simple intent
            prompt (str): Input prompt
        
        Returns:
            str: Simple response text, or None if no response is generated
        """
        prompt_lower = prompt.lower()
        
        # Define response criteria with better organization
        response_criteria = {
            'greeting': {
                'formal_indicators': ['good morning', 'good afternoon', 'good evening'],
                'casual_indicators': ['hey', 'hi'],
                'responses': {
                    'formal': "Good day. How may I assist you?",
                    'casual': "Hey there! How can I help you today? 😊",
                    'default': "Hello! I'm Bridge. How can I assist you today?"
                }
            },
            'thanks': {
                'enthusiastic_indicators': ['thank you so much', 'really appreciate', 'grateful', 'amazing'],
                'simple_indicators': ['thanks', 'thx', 'ty'],
                'responses': {
                    'enthusiastic': "My pleasure! I'm always here if you need anything 😊",
                    'simple': "You're welcome! Let me know if there's anything else you'd like to explore 😊",
                    'default': "Glad I could help. I'm here if you need anything else."
                }
            },
            'unclear': {
                'frustrated_indicators': ['stuck', 'not working', 'problem', 'error', 'broken', 'issue', 'wrong'],
                'help_seeking_indicators': ['help', 'assist', 'support', 'need help'],
                'vague_question_indicators': ['how', 'what', 'why'],
                'responses': {
                    'frustrated': "Sounds like something isn’t working right. Can you share a bit more so I can help you fix it?",
                    'help_seeking': "Sure! What exactly do you need help with?",
                    'vague_question': "Let’s figure this out together. Could you share a bit more context?",
                    'default': "Got it! Let’s take it from the top—what are you trying to figure out?"
                }
            }
        }
        
        if intent == 'greeting':
            criteria = response_criteria['greeting']
            if any(indicator in prompt_lower for indicator in criteria['formal_indicators']):
                return criteria['responses']['formal']
            elif any(indicator in prompt_lower for indicator in criteria['casual_indicators']) or 'hello there' in prompt_lower or 'hey there' in prompt_lower:
                return criteria['responses']['casual']
            else:
                return criteria['responses']['default']
        
        elif intent == 'thanks':
            criteria = response_criteria['thanks']
            if any(indicator in prompt_lower for indicator in criteria['enthusiastic_indicators']):
                return criteria['responses']['enthusiastic']
            elif any(indicator in prompt_lower for indicator in criteria['simple_indicators']):
                return criteria['responses']['simple']
            else:
                return criteria['responses']['default']
        
        elif intent == 'system_info':
            return """I'm Bridge - your smart question routing system! 🌉<br><br>
🎯 My expertise:<br>
- Analyzing your questions and choosing the best AI model to answer them<br>
- Technical, professional, and academic questions<br>
- Problem-solving and project assistance<br>
- Content creation and detailed explanations<br><br>
💡 How it works:<br>
I examine your question and route it to the most suitable AI model.<br>
Simple questions get quick responses, complex ones get deep analysis.<br><br>
💬 Just ask me anything! I'm here to help you get the best possible answers."""
        
        elif intent == 'unclear':
            criteria = response_criteria['unclear']
            if any(indicator in prompt_lower for indicator in criteria['frustrated_indicators']):
                return criteria['responses']['frustrated']
            elif any(indicator in prompt_lower for indicator in criteria['help_seeking_indicators']):
                return criteria['responses']['help_seeking']
            elif any(indicator in prompt_lower for indicator in criteria['vague_question_indicators']):
                return criteria['responses']['vague_question']
            else:
                return criteria['responses']['default']
        
        return None

    def _full_bridge_process(self, prompt, request_json):
        """
        Run the full Bridge processing pipeline for the input prompt.
        
        Args:
            prompt (str): Input prompt to process
            request_json (dict): Request data containing the query prompt and other metadata
        
        Returns:
            dict: Final response object containing the answer, metadata, and other relevant information
        """
        print("Running full Bridge processing...")
        
        # Check if we need more information - made much less strict for better flow
        if self.check_informativeness:
            score, questions = self.prompt_analyzer.analyze_informativeness(prompt, request_json.get('vibe', 'general'))
            if score < 0.3 and questions:  # Changed from 0.5 to 0.3 - much less strict
                print("Prompt needs more information")
                # Create a response object that includes the questions
                response_obj = {
                    'response': "To give you the best answer, I need a bit more context. Let me ask you a few quick questions:",
                    'follow_up_questions': questions,
                    'needs_more_info': True,
                    'llm_used': 'BRIDGE',
                    'confidence': 1.0
                }
                # Pass the response object to prepare_output
                return self.output_manager.prepare_output(request_json, prompt, response_obj, {}, [])

        # Process the request through the LLM
        response_type = self.response_classifier.classify_response_type(prompt, request_json.get('vibe', 'general'), request_json.get('response_preference', 'informative'))
        additional_info = request_json.get('additional_info', [])
        enhanced_prompt = self.prompt_enhancer.enhance_prompt(prompt, request_json.get('vibe', 'general'), response_type, additional_info, request_json.get('show_confidence', False))
        
        print(f"Routing to LLM with response type: {response_type}")
        response_obj = self.llm_router.route_to_llm(enhanced_prompt, response_type)
        print(f"Initial response_obj: {response_obj}")
        
        evaluation = self.answer_evaluator.evaluate_answer(response_obj, prompt)
        print(f"Evaluation: {evaluation}")

        # If upgrade needed, try with LLM3
        if evaluation.get('needs_upgrade', False):
            print("Upgrading to LLM3")
            response_obj = self.llm_router._call_openai_api(
                enhanced_prompt, 
                self.llm_router.llm3_config, 
                self.llm_router.llm3_config['model_name']
            )
            print(f"Upgraded response_obj: {response_obj}")
            evaluation = self.answer_evaluator.evaluate_answer(response_obj, prompt)

        # Prepare the final output
        output = self.output_manager.prepare_output(request_json, enhanced_prompt, response_obj, evaluation, additional_info)
        
        # Ensure llm_used is properly set in the response
        if 'llm_used' not in output.get('model_metadata', {}) and 'llm_used' in response_obj:
            output.setdefault('model_metadata', {})['llm_used'] = response_obj['llm_used']
        
        print(f"Final output from bridge: {output}")
        return output

    def _handle_math_expression(self, expr, request_json):
        """
        Handle a math expression evaluated via Math.js.
        
        Args:
            expr (str): Math expression to evaluate
            request_json (dict): Request data containing the query prompt and other metadata
        
        Returns:
            dict: Response object containing the evaluated result and metadata
        """
        try:
            response = requests.get("https://api.mathjs.org/v4/", params={"expr": expr})
            if response.status_code == 200:
                result = response.text.strip()
                return {
                'response': f"{expr} = {result}",
                'model_metadata': {
                    'llm_used': 'mathjs-api',
                    'confidence': 1.0,
                    'simple_intent': 'math_expression',
                    'from_cache': False,
                    'is_guest': request_json.get('sender_id', '').startswith('guest_')
                }
            }
            else:
                return {
                    'response': f"⚠️ Sorry, I couldn't compute: {expr}",
                    'model_metadata': {
                        'llm_used': 'mathjs-api',
                        'confidence': 0.0,
                        'simple_intent': 'math_expression',
                        'from_cache': False,
                        'is_guest': request_json.get('sender_id', '').startswith('guest_')
                    }
                }
        except Exception as e:
            return {
                'response': f"⚠️ Error: {str(e)}",
                'model_metadata': {
                    'llm_used': 'mathjs-api',
                    'confidence': 0.0,
                'simple_intent': 'math_expression',
                'from_cache': False,
                'is_guest': request_json.get('sender_id', '').startswith('guest_')
                }
            }


    def _is_math_expression(self, prompt):
        """
        Check if the input prompt is a math expression that can be computed using Math.js.
        
        Args:
            prompt (str): Input prompt to check
        
        Returns:
            bool: True if the prompt is a math expression, False otherwise
        """
        expr = self._clean_math_expression(prompt)
        try:
            response = requests.get("https://api.mathjs.org/v4/", params={"expr": expr})
            return response.status_code == 200
        except:
            return False

    def _clean_math_expression(self, prompt):
        """
        Clean the input prompt to extract a math expression.
        
        Args:
            prompt (str): Input prompt to clean
        
        Returns:
            str: Cleaned math expression
        """
        # Remove = or ? from the end
        return re.sub(r'[=\?]+$', '', prompt.strip())
    
    def _evaluate_math_expression(self, prompt):
        """
        Evaluate a math expression using Math.js.
        
        Args:
            prompt (str): Input prompt containing a math expression
        
        Returns:
            tuple: (Cleaned math expression, evaluated result)
        """
        expr = self._clean_math_expression(prompt)
        try:
            response = requests.get("https://api.mathjs.org/v4/", params={"expr": expr})
            if response.status_code == 200:
                return expr, response.text.strip()
            else:
                return expr, "❌ Invalid expression"
        except Exception as e:
            return expr, f"⚠️ Error evaluating math: {str(e)}"