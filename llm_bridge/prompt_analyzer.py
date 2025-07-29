"""
prompt_analyzer.py - Prompt Analysis and Classification Module

This module implements the PromptAnalyzer class, which is responsible for:
1. Analyzing input prompts to determine their intent and requirements
2. Classifying prompts into different categories (academic, technical, etc.)
3. Extracting key information and context from prompts
4. Identifying special patterns like math expressions
5. Determining if additional information is needed
6. Handling simple intents and non-English detection
"""

import re
import string
import requests

class PromptAnalyzer:
    """
    Analyzes and classifies natural language prompts to determine their requirements.
    
    The PromptAnalyzer examines input prompts to understand their intent, complexity,
    and context requirements. It helps route queries to appropriate handlers and
    ensures all necessary information is present for high-quality responses.
    """
    
    def __init__(self):
        """Initialize the PromptAnalyzer with default configuration."""
        # Basic question indicators
        self.question_indicators = {
            'question_words': ['who', 'what', 'where', 'when', 'why', 'how'],
            'question_markers': ['?']
        }
        
        # Enhanced context requirements with more flexible keyword matching
        self.context_requirements = {
            'academic': {
                'required_elements': {
                    'subject': {
                        'keywords': ['subject', 'field', 'discipline', 'mathematics', 'science', 'history', 
                                   'calculus', 'physics', 'chemistry', 'biology', 'literature', 'psychology',
                                   'computer science', 'engineering', 'economics', 'philosophy'],
                        'question': "What specific academic subject is this related to?"
                    },
                    'level': {
                        'keywords': ['level', 'grade', 'year', 'undergraduate', 'graduate', 'university',
                                   'college', 'high school', 'elementary', 'advanced', 'beginner', 'course'],
                        'question': "What academic level is this for?"
                    }
                },
                'optional_elements': {
                    'purpose': {
                        'keywords': ['purpose', 'goal', 'assignment', 'research', 'homework', 'project'],
                        'question': "What is the purpose of this academic work?"
                    }
                }
            },
            'professional': {
                'required_elements': {
                    'industry': {
                        'keywords': ['industry', 'sector', 'business', 'company', 'technology', 'healthcare',
                                   'finance', 'marketing', 'sales', 'consulting', 'startup'],
                        'question': "Which industry or business sector is this question about?"
                    },
                    'role': {
                        'keywords': ['role', 'position', 'job', 'responsibility', 'manager', 'developer',
                                   'analyst', 'director', 'coordinator', 'specialist'],
                        'question': "What is your role or position in this context?"
                    }
                }
            },
            'technical': {
                'required_elements': {
                    'technology': {
                        'keywords': ['programming language', 'framework', 'library', 'technology', 'tool', 'platform',
                                   'python', 'javascript', 'react', 'node.js', 'docker', 'aws', 'api', 'database'],
                        'question': "Which specific technology or platform are you working with?"
                    },
                    'problem': {
                        'keywords': ['error', 'issue', 'problem', 'bug', 'not working', 'fix', 'solution', 'troubleshoot'],
                        'question': "Can you describe the specific problem or error you're encountering?"
                    }
                },
                'optional_elements': {
                    'code': {
                        'keywords': ['code', 'snippet', 'example', 'implementation'],
                        'question': "Could you share the relevant code or error message?"
                    },
                    'environment': {
                        'keywords': ['environment', 'version', 'os', 'browser', 'device'],
                        'question': "What is your development environment or setup?"
                    }
                }
            }
        }
        
        # Adjusted minimum requirements for more lenient assessment
        self.assessment_thresholds = {
            'too_short': 3,  # minimum word count
            'basic_question': 0.4,  # has question structure
            'contextual_completeness': 0.5,  # lowered from 0.7
            'high_quality': 0.8  # lowered from 0.9
        }

        # Unclear intent detection
        self.unclear = {
            'frustrated_indicators': ['stuck', 'not working', 'error', 'broken', 'issue', 'wrong'],
            'help_seeking_indicators': ['help', 'assist', 'support', 'need help'],
            'vague_question_phrases': [
                'how do I fix', 'how does it work', 'what should I do', 'why is it not', 'why won’t it',
                'how come', 'what’s wrong', 'why does it'
            ],
            'responses': {
                'frustrated': "Sounds like something isn't working right. Can you share a bit more so I can help you fix it?",
                'help_seeking': (
                    "I'm here to help! I can assist with:\n\n"
                    "• **Technical questions and coding** …\n"
                    "• **Business and professional advice** …\n"
                    "• **Academic research and explanations** …\n"
                    "• **Creative projects and brainstorming** …\n"
                    "• **General questions and problem-solving** …\n\n"
                    "What would you like help with?"
                ),
                'vague_question': "Let's figure this out together. Could you share a bit more context?",
                'default': "Got it! Let's take it from the top—what are you trying to figure out?"
            }
        }

    # === Language Detection ===
    def detect_non_english(self, prompt):
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

        except (ImportError, Exception):
            # Safe fallback: If langdetect is not installed or detection fails, assume English 
            return False

    # === Simple Intent Detection ===
    def detect_simple_intent(self, prompt):
        """
        Detect simple intents in the input prompt.
        
        Args:
            prompt (str): Input prompt to check
        
        Returns:
            str: Detected simple intent, or None if no simple intent is detected
        """
        prompt_lower = prompt.lower().strip()
        
        # Remove punctuation for consistent word matching
        translator = str.maketrans('', '', string.punctuation)
        prompt_clean = prompt_lower.translate(translator)
        
        # split into words
        words = prompt_clean.split()
        
        # Check for greeting - includes multilingual greetings like 'shalom'
        greeting_patterns = [
            'hello', 'hi', 'hey', 'greetings', 'hola', 'bonjour', 'ciao', 'hallo', 'namaste', 'shalom',
            'good morning', 'good afternoon', 'good evening', 'how are you', 'how do you do', 
            'nice to meet you', 'good to see you', 'long time no see'
        ]
        if len(words) <= 3:  # Only check short prompts
            # Use cleaned prompt for pattern matching
            if any(pattern in prompt_clean for pattern in greeting_patterns):
                return 'greeting'

        # Check for thanks - include more variations
        thanks_patterns = [
            'thanks', 'thank you', 'appreciate it', 'much obliged', 'cheers', 
            'thanks a lot', 'thank you very much', 'grateful', 'appreciate'
        ]
        # Use cleaned prompt for pattern matching
        if any(pattern in prompt_clean for pattern in thanks_patterns):
            return 'thanks'

        # Check for system info - include more variations  
        system_info_patterns = [
            'what is bridge', 'how does this work', 'who made you', 'what can you do', 
            'are you human', 'are you a bot', 'are you ai', 'your capabilities', 'capabilities',
            'tell me about bridge', 'about bridge', 'how do you work'
        ]
        # Use cleaned prompt for pattern matching
        if any(pattern in prompt_clean for pattern in system_info_patterns):
            return 'system_info'

        # Check for unclear intent - help requests and common unclear phrases
        unclear_words = ['help', 'what', 'who', 'when', 'where', 'why', 'how', 'problem', 'stuck', 'error', 'working']
        unclear_phrases = ['not working', 'broken', 'issue', 'wrong', 'need help', 'i need help']
        
        # Check for unclear phrases first - use cleaned prompt
        if any(phrase in prompt_clean for phrase in unclear_phrases):
            return 'unclear'
            
        # Single word help requests
        if len(words) == 1 and words[0] in unclear_words:
            return 'unclear'
        
        # Short phrases with help or unclear words (expanded to 3 words)
        if len(words) <= 3 and any(word in unclear_words for word in words):
            return 'unclear'

        return None

    def get_simple_response(self, intent, prompt):
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
                    'frustrated': "Sounds like something isn't working right. Can you share a bit more so I can help you fix it?",
                    'help_seeking': (
                        "I'm here to help! I can assist with:\n\n"
                        "• **Technical questions and coding** …\n"
                        "• **Business and professional advice** …\n"
                        "• **Academic research and explanations** …\n"
                        "• **Creative projects and brainstorming** …\n"
                        "• **General questions and problem-solving** …\n\n"
                        "What would you like help with?"
                    ),
                    'vague_question': "Let's figure this out together. Could you share a bit more context?",
                    'default': "Got it! Let's take it from the top—what are you trying to figure out?"
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
            return """I'm Bridge - your smart question routing system! 🌐<br><br>
🎯 What I do:<br>
- Analyzing your questions and routing them to the most suitable AI model<br>
- Supporting five categories: Business & Professional, Academic & Research, Technical & Development, Daily & General, Creative & Emotional<br>
- Problem-solving, content creation, and project assistance<br>
- Clear explanations and guidance<br><br>
💡 How it works:<br>
You ask → I analyze → the best AI answers.<br>
Simple questions get fast responses; complex ones get deeper analysis.<br><br>
💬 Just ask me anything! I'm here to connect you with the perfect answer."""
        
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

    def handle_non_english_intent(self, prompt):
        """
        Handle non-English prompts with a polite response.
        
        Args:
            prompt (str): Input prompt to handle
        
        Returns:
            str: Polite message response
        """
        return "I notice you've written in a language other than English. I'm designed to work in English only. Could you please rephrase your question in English? I'm here to help! 🌍"

# === Math Expression Handling ===
    def extract_math_expression(self, prompt: str) -> str:
        """
        Extract a math expression from free text using regex.
        Supports digits, operators, functions, parentheses, and natural language.
        """
        # Step 1: Try to find standard math expressions first
        function_pattern = r'((?:log|ln|sin|cos|tan|sqrt|exp|abs|floor|ceil|round)\s*\([^)]+\))'
        basic_expr_pattern = r'([0-9\.\s\+\-\*/\^\(\)]+)'
        
        # First try to find function calls
        func_match = re.search(function_pattern, prompt, re.IGNORECASE)
        if func_match:
            expr = func_match.group(1)
            expr = self.clean_math_expression(expr)
            print(f"[MATH] 🎯 Extracted function expression: {expr}")
            return expr
        
        # Then try basic expressions
        basic_match = re.search(basic_expr_pattern, prompt)
        if basic_match:
            expr = basic_match.group(1)
            expr = self.clean_math_expression(expr)
            # Only return if it has operators (not just a number)
            if re.search(r'[\+\-\*/\^]', expr):
                print(f"[MATH] 🎯 Extracted basic expression: {expr}")
                return expr
        
        # Step 2: If no standard math found, try natural language conversion
        natural_expr = self._convert_text_to_math(prompt)
        if natural_expr:
            print(f"[MATH] 🎯 Extracted from natural language: {natural_expr}")
            return natural_expr
        
        return ""

    def _convert_text_to_math(self, prompt: str) -> str:
        """
        Convert natural English math expressions to mathematical syntax.
        (e.g., 'two plus three' → '2 + 3')
        Only converts if the context is clearly mathematical.
        """
        # First check: does this look like a non-math request?
        non_math_indicators = [
            'list', 'show', 'give me', 'tell me', 'find', 'search', 'get', 'fetch',
            'display', 'provide', 'suggest', 'recommend', 'create', 'make', 'generate',
            'explain', 'describe', 'write', 'help', 'assist', 'need', 'want',
            'countries', 'examples', 'reasons', 'items', 'things', 'ways', 'steps',
            'people', 'places', 'books', 'movies', 'songs', 'tips', 'ideas',
            'facts', 'questions', 'answers', 'solutions', 'methods', 'options',
            'features', 'benefits', 'advantages', 'tools', 'resources', 'websites',
            'companies', 'brands', 'products', 'services', 'applications', 'apps',
            'games', 'activities', 'exercises', 'recipes', 'ingredients', 'names'
        ]
        
        prompt_lower = prompt.lower()
        found_indicator = None
        for indicator in non_math_indicators:
            if indicator in prompt_lower:
                found_indicator = indicator
                break
                
        if found_indicator:
            print(f"[MATH] ❌ Non-math context detected: contains '{found_indicator}'")
            return ""

        word_to_num = {
            'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
            'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
            'ten': '10', 'eleven': '11', 'twelve': '12', 'thirteen': '13', 
            'fourteen': '14', 'fifteen': '15', 'sixteen': '16', 'seventeen': '17',
            'eighteen': '18', 'nineteen': '19', 'twenty': '20', 'thirty': '30',
            'forty': '40', 'fifty': '50', 'sixty': '60', 'seventy': '70',
            'eighty': '80', 'ninety': '90', 'hundred': '100'
        }

        ops = {
            'plus': '+', 'add': '+', 'added to': '+', 'sum': '+',
            'minus': '-', 'subtract': '-', 'take away': '-', 'less': '-',
            'times': '*', 'multiplied by': '*', 'multiply': '*', 'mult': '*',
            'divided by': '/', 'divide': '/', 'over': '/', 'split by': '/',
            'mod': '%', 'modulo': '%', 'remainder': '%'
        }

        # Work on lowercase
        text = prompt_lower
        
        # Replace number words with digits
        for word, num in word_to_num.items():
            text = re.sub(rf'\b{word}\b', num, text)

        # Replace operation words with symbols
        for word, op in ops.items():
            text = re.sub(rf'\b{word}\b', f' {op} ', text)

        # Clean up: keep only numbers, operators, spaces, and parentheses
        text = re.sub(r'[^0-9+\-*/%(). ]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()

        # Validate result: must have numbers AND operators
        if (re.search(r'\d', text) and 
            re.search(r'[\+\-\*/]', text) and 
            re.fullmatch(r'[\d+\-*/%(). ]+', text)):
            return text

        return ""

    def clean_math_expression(self, expr: str) -> str:
        """
        Remove trailing = ? , etc. and trim whitespace.
        """
        expr = expr.strip()
        # Remove trailing punctuation and equals signs
        expr = re.sub(r'[=:\?\.,;]+$', '', expr)
        # Remove extra whitespace
        expr = re.sub(r'\s+', ' ', expr)
        return expr.strip()

    def is_math_expression(self, prompt: str) -> bool:
        """
        Determines if the prompt includes a valid math expression.
        Considers both basic operations and mathematical functions.
        """
        expr = self.extract_math_expression(prompt)
        if not expr:
            print(f"[MATH] ❌ No valid math expression extracted from: {prompt}")
            return False

        # Check for mathematical functions
        math_functions = ['log', 'ln', 'sin', 'cos', 'tan', 'sqrt', 'exp', 'abs', 'floor', 'ceil', 'round']
        has_function = any(func in expr.lower() for func in math_functions)
        
        # Check for basic operations
        has_operator = bool(re.search(r'[\+\-\*/\^]', expr))
        has_digit = bool(re.search(r'\d', expr))
        has_parentheses = '(' in expr and ')' in expr
        
        # Check if it's just a single number (not a calculation)
        is_single_number = re.match(r'^\s*\d+\.?\d*\s*$', expr.strip())

        # Valid if: 
        # 1. Has mathematical function with parentheses, OR
        # 2. Has digits AND operators AND is not just a single number
        is_valid = (has_function and has_parentheses) or (has_digit and has_operator and not is_single_number)

        print(f"[MATH] ✅ Expression check: '{expr}' | Function: {has_function} | Operator: {has_operator} | Parentheses: {has_parentheses} | Single number: {is_single_number} | Valid: {is_valid}")
        return is_valid

    def evaluate_math_expression(self, prompt: str):
        """
        Evaluate the extracted expression using MathJS API with local fallback.
        
        Returns:
            tuple: (cleaned_expression, result)
        """
        expr = self.extract_math_expression(prompt)
        if not expr or not self.is_math_expression(prompt):
            return "", "❌ No valid math expression found"
        
        # First try MathJS API
        try:
            # Replace ^ with ** for proper exponentiation in MathJS
            expr_for_api = expr.replace('^', '**')
            
            response = requests.get(
                "https://api.mathjs.org/v4/", 
                params={"expr": expr_for_api},
                timeout=3
            )
            
            if response.status_code == 200:
                result = response.text.strip()
                print(f"[MATH] ✅ Evaluated via MathJS: {expr} = {result}")
                return expr, result
            else:
                print(f"[MATH] ❌ MathJS returned error: {response.text}")
                # Fall back to local evaluation
                return self.evaluate_math_local(expr)
                
        except requests.exceptions.Timeout:
            print(f"[MATH] ❌ MathJS timeout - falling back to local evaluation")
            return self.evaluate_math_local(expr)
        except requests.exceptions.RequestException as e:
            print(f"[MATH] ❌ MathJS network error: {e} - falling back to local evaluation")
            return self.evaluate_math_local(expr)
        except Exception as e:
            print(f"[MATH] ❌ MathJS exception: {e} - falling back to local evaluation")
            return self.evaluate_math_local(expr)

    def evaluate_math_local(self, expr: str):
        """
        Evaluate math expression locally using Python's math module and eval (with safety checks).
        
        Returns:
            tuple: (expression, result)
        """
        try:
            import math
            
            # Replace mathematical functions with Python equivalents
            expr_for_eval = expr.replace('^', '**')
            
            # Map common math functions to Python's math module
            function_mapping = {
                'log(': 'math.log10(',  # Default log is log10
                'ln(': 'math.log(',     # Natural logarithm
                'sin(': 'math.sin(',
                'cos(': 'math.cos(',
                'tan(': 'math.tan(',
                'sqrt(': 'math.sqrt(',
                'exp(': 'math.exp(',
                'abs(': 'abs(',        # Built-in abs function
                'floor(': 'math.floor(',
                'ceil(': 'math.ceil(',
                'round(': 'round('     # Built-in round function
            }
            
            for func, replacement in function_mapping.items():
                expr_for_eval = expr_for_eval.replace(func, replacement)
            
            # Remove spaces for cleaner evaluation
            expr_for_eval = expr_for_eval.replace(' ', '')
            
            # Security: only allow safe mathematical operations and functions
            allowed_chars = set('0123456789+-*/().**,mathlogsincotan.abcdefghijklmnopqrstuvwxyz')
            if not all(c.lower() in allowed_chars for c in expr_for_eval):
                return expr, "❌ Invalid characters in expression"
            
            # Additional security: check for dangerous patterns
            dangerous_patterns = ['import', 'exec', 'eval', '__', 'open', 'file']
            if any(pattern in expr_for_eval.lower() for pattern in dangerous_patterns):
                return expr, "❌ Potentially unsafe expression"
            
            # Create safe namespace with only math functions
            safe_namespace = {
                '__builtins__': {},
                'math': math,
                'abs': abs,
                'round': round
            }
            
            # Evaluate safely
            result = eval(expr_for_eval, safe_namespace)
            
            # Format result nicely
            if isinstance(result, float):
                if result.is_integer():
                    result = int(result)
                else:
                    # Round to reasonable precision
                    result = round(result, 10)
            
            print(f"[MATH] ✅ Evaluated locally: {expr} = {result}")
            return expr, str(result)
            
        except ZeroDivisionError:
            print(f"[MATH] ❌ Division by zero")
            return expr, "❌ Division by zero"
        except ValueError as e:
            print(f"[MATH] ❌ Math domain error: {e}")
            return expr, "❌ Math domain error (e.g., log of negative number)"
        except SyntaxError:
            print(f"[MATH] ❌ Invalid syntax in expression")
            return expr, "❌ Invalid mathematical expression"
        except Exception as e:
            print(f"[MATH] ❌ Local evaluation exception: {e}")
            return expr, f"❌ Error evaluating expression: {str(e)}"

    # === Informativeness Analysis ===
    def analyze_informativeness(self, prompt, vibe):
        """
        Analyze how informative a prompt is and what additional info might be needed.
        First check for explicit “unclear” patterns, then length, structure and context.
        """
        text = prompt.lower().strip()

        # 1) Unclear/help/vague first
        for tok in self.unclear['help_seeking_indicators']:
            if tok in text:
                return 0.2, [ self.unclear['responses']['help_seeking'] ]
        for tok in self.unclear['frustrated_indicators']:
            if tok in text:
                return 0.2, [ self.unclear['responses']['frustrated'] ]
        for tok in self.unclear['vague_question_phrases']:
            if tok in text:
                return 0.2, [ self.unclear['responses']['vague_question'] ]

        # 2) Length check
        word_count = len(prompt.split())
        if word_count < self.assessment_thresholds['too_short']:
            return 0.2, ["Could you provide more details about your question?"]

        # 3) Question structure
        if not self._has_question_structure(prompt):
            return self.assessment_thresholds['basic_question'], [
                "Could you phrase your request as a question?"
            ]

        # 4) Vibe‐specific context
        if vibe in self.context_requirements:
            score, missing = self._assess_context_completeness(prompt, vibe)
            if score < self.assessment_thresholds['contextual_completeness'] and missing:
                return score, missing[:3]

        # 5) High‐quality prompt
        return self.assessment_thresholds['high_quality'], []

    def _has_question_structure(self, prompt):
        """Check if prompt has basic question structure"""
        prompt_lower = prompt.lower()
        
        # Check for question mark
        has_question_mark = any(marker in prompt for marker in self.question_indicators['question_markers'])
        
        # Check for question words
        has_question_word = any(word in prompt_lower for word in self.question_indicators['question_words'])
        
        return has_question_mark or has_question_word

    def _assess_context_completeness(self, prompt, vibe):
        """Enhanced context completeness assessment with flexible scoring"""
        prompt_lower = prompt.lower()
        requirements = self.context_requirements[vibe]
        
        # Check required elements
        missing_required = []
        required_elements = requirements['required_elements']
        
        for element_name, element_data in required_elements.items():
            if not any(keyword in prompt_lower for keyword in element_data['keywords']):
                missing_required.append(element_data['question'])
        
        # Enhanced scoring - more generous for partial completion
        total_required = len(required_elements)
        missing_count = len(missing_required)
        
        if missing_count == 0:
            return 0.8, []  # Good completion
        elif missing_count == 1 and total_required > 1:
            return 0.6, missing_required  # Partial completion - increased from 0.3
        else:
            # Score decreases based on missing required elements
            completion_ratio = (total_required - missing_count) / total_required
            score = 0.4 + (0.4 * completion_ratio)  # Base 0.4 + up to 0.4 bonus
            return score, missing_required

    def get_analysis_details(self, prompt, vibe):
        """Debug method to get detailed analysis information"""
        word_count = len(prompt.split())
        has_question_structure = self._has_question_structure(prompt)
        
        analysis = {
            'word_count': word_count,
            'meets_length_requirement': word_count >= self.assessment_thresholds['too_short'],
            'has_question_structure': has_question_structure,
            'vibe': vibe,
            'vibe_supported': vibe in self.context_requirements
        }
        
        if vibe in self.context_requirements:
            context_score, missing_questions = self._assess_context_completeness(prompt, vibe)
            analysis.update({
                'context_score': context_score,
                'missing_questions': missing_questions,
                'context_requirements': self.context_requirements[vibe]
            })
        
        final_score, questions = self.analyze_informativeness(prompt, vibe)
        analysis.update({
            'final_score': final_score,
            'final_questions': questions
        })
        
        return analysis