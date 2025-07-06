# response_classifier.py - Enhanced with better structure and STRONG complexity indicators

class ResponseTypeClassifier:
    def __init__(self):
        # Enhanced keyword patterns with comprehensive coverage
        self.classification_patterns = {
            'complex': {
                'analysis_keywords': ['explain', 'analyze', 'compare', 'evaluate', 'synthesize', 'discuss', 'examine', 'assess', 'review'],
                'inquiry_keywords': ['why', 'how', 'what causes', 'what makes', 'what leads'],
                'process_keywords': ['process', 'method', 'steps', 'approach', 'strategy', 'methodology'],
                'subjective_keywords': ['emotional', 'feel', 'think', 'opinion', 'perspective', 'viewpoint'],
                'difficulty_keywords': ['complex', 'implications', 'comprehensive', 'thorough', 'detailed', 'in-depth'],
                'academic_keywords': ['research', 'theory', 'concept', 'principle', 'framework']
            },
            'simple': {
                'factual_keywords': ['what is', 'where is', 'when is', 'who is', 'what are'],
                'definition_keywords': ['define', 'list', 'name', 'identify', 'tell me'],
                'quantitative_keywords': ['price', 'cost', 'distance', 'time', 'number', 'amount']
            }
        }
        
        # Preference mappings
        self.preference_overrides = {
            'CoT': 'complex',
            'informative': 'simple'
        }
        
        # Enhanced vibe-based complexity indicators
        self.complex_vibes = ['academic', 'creative', 'professional']

    def classify_response_type(self, prompt, vibe, user_preference=None):
        """Classify whether response should be simple or complex"""
        print(f"\n=== Classifying response type ===")
        print(f"Prompt: {prompt}")
        print(f"Vibe: {vibe}")
        print(f"User preference: {user_preference}")    
    
        prompt_lower = prompt.lower()
    
        # CRITICAL FIX: Strong indicators for complexity that FORCE GPT-4 routing
        strong_complex_indicators = [
            'analyze', 'comprehensive', 'implications', 'methodology', 
            'research', 'evaluate', 'synthesize', 'compare', 'examine',
            'assess', 'discuss', 'thorough', 'academic', 'discuss the implications'
        ]   
    
        # If ANY strong complex indicators present, immediately return complex
        if any(indicator in prompt_lower for indicator in strong_complex_indicators):
            print("Found strong complex indicator - forcing 'complex' response type")
            return 'complex'
        
        # Then check for user preference override
        if user_preference in self.preference_overrides:
            print(f"Using user preference override: {user_preference} -> {self.preference_overrides[user_preference]}")
            return self.preference_overrides[user_preference]
        
        # Count keyword matches
        complexity_score = self._calculate_complexity_score(prompt_lower)
        
        # Consider prompt length (lowered threshold)
        is_long_prompt = len(prompt.split()) > 10  # Lowered from 15 to 10
        
        # ENHANCED vibe influence - make academic/professional/creative strongly prefer complex
        vibe_suggests_complex = vibe in self.complex_vibes
        
        # Make final decision with enhanced logic
        return self._make_classification_decision(
            complexity_score, 
            is_long_prompt, 
            vibe_suggests_complex
        )

    def _calculate_complexity_score(self, prompt_lower):
        """Calculate complexity score based on keyword patterns"""
        scores = {
            'complex': 0,
            'simple': 0
        }
        
        # Count complex pattern matches
        for category, keywords in self.classification_patterns['complex'].items():
            matches = sum(1 for keyword in keywords if keyword in prompt_lower)
            scores['complex'] += matches
        
        # Count simple pattern matches  
        for category, keywords in self.classification_patterns['simple'].items():
            matches = sum(1 for keyword in keywords if keyword in prompt_lower)
            scores['simple'] += matches
        
        return scores

    def _make_classification_decision(self, complexity_score, is_long_prompt, vibe_suggests_complex):
        """Make final classification decision with STRONG vibe influence"""
    
        # If academic/professional/creative vibe, strongly prefer complex
        if vibe_suggests_complex:
            return 'complex'
        
        # If clear keyword dominance
        if complexity_score['complex'] > complexity_score['simple']:
            return 'complex'
        elif complexity_score['simple'] > complexity_score['complex']:
            return 'simple'
    
        # Default to complex for long prompts
        if is_long_prompt:
            return 'complex'
        
        return 'simple'  # Default fallback

    def get_classification_reasoning(self, prompt, vibe, user_preference=None):
        """Debug method to understand classification reasoning"""
        prompt_lower = prompt.lower()
        complexity_score = self._calculate_complexity_score(prompt_lower)
        
        # Check for strong indicators
        strong_complex_indicators = [
            'analyze', 'comprehensive', 'implications', 'methodology', 
            'research', 'evaluate', 'synthesize', 'compare', 'examine'
        ]
        has_strong_indicators = any(indicator in prompt_lower for indicator in strong_complex_indicators)
        
        reasoning = {
            'complexity_scores': complexity_score,
            'has_strong_indicators': has_strong_indicators,
            'strong_indicators_found': [ind for ind in strong_complex_indicators if ind in prompt_lower],
            'prompt_length': len(prompt.split()),
            'is_long_prompt': len(prompt.split()) > 10,
            'vibe': vibe,
            'vibe_suggests_complex': vibe in self.complex_vibes,
            'user_preference': user_preference,
            'final_classification': self.classify_response_type(prompt, vibe, user_preference)
        }
        
        return reasoning