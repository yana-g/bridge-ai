"""
answer_evaluator.py - Response Quality Assessment Module

This module implements the AnswerEvaluator class, which is responsible for:
1. Evaluating the quality and completeness of LLM-generated responses
2. Determining if a response meets quality thresholds
3. Identifying when to upgrade to a more capable model
4. Detecting common response issues (e.g., uncertainty, vagueness)
5. Providing feedback on response quality

Key Features:
- Multi-dimensional quality assessment
- Configurable quality thresholds
- Model upgrade recommendations
- Detailed quality scoring
- Support for different response types
"""

class AnswerEvaluator:
    """
    Evaluates the quality of LLM-generated responses and determines if upgrades are needed.
    
    The AnswerEvaluator analyzes responses based on various quality indicators,
    scores them, and decides whether a response meets the required quality standards.
    It can recommend upgrading to a more capable model when responses are subpar.
    
    Attributes:
        quality_indicators (dict): Positive and negative indicators of response quality
        thresholds (dict): Quality thresholds for different assessment criteria
        upgradeable_models (dict): Tracks which models can be upgraded
    """
    
    def __init__(self):
        """Initialize the AnswerEvaluator with default quality indicators and thresholds."""
        # Organized quality indicators instead of simple list
        self.quality_indicators = {
            'negative': {
                'uncertainty': ["i don't know", "i'm not sure", "unable to answer", "unclear", "not certain"],
                'refusal': ["i cannot", "i can't help", "not possible", "cannot provide"],
                'generic': ["it depends", "varies", "different for everyone"]
            },
            'positive': {
                'specificity': ["specifically", "precisely", "exactly", "in particular"],
                'confidence': ["definitely", "certainly", "clearly", "obviously"],
                'detailed': ["furthermore", "additionally", "moreover", "for example"]
            }
        }
        
        # Quality assessment thresholds
        self.thresholds = {
            'minimum_length': 20,  # words
            'upgrade_threshold': 0.7,  # quality score below this triggers upgrade
            'excellent_threshold': 0.8  # high quality threshold
        }
        
        # Model upgrade capabilities - only models that actually exist
        self.upgradeable_models = {
            'GPT-3.5': True,    # Basic model (LLM2), can upgrade to GPT-4 (LLM3)
            'gpt-3.5-turbo': True, # Basic model (LLM2), can upgrade to GPT-4 (LLM3)
            'GPT-4': False,     # Advanced model (LLM3), no upgrade needed
            'cache': False,     # Cache response, no upgrade possible
            'BRIDGE': False     # Bridge direct response, no upgrade needed
        }

    def evaluate_answer(self, response_obj, original_prompt):
        """Comprehensive answer evaluation with detailed scoring"""
        
        answer = response_obj.get('answer', '')
        llm_used = response_obj.get('llm_used') or response_obj.get('model_metadata', {}).get('llm_used', 'unknown')
        
        # Calculate quality components
        quality_components = self._calculate_quality_components(answer, original_prompt)
        
        # Combine components into overall quality score
        overall_quality = self._calculate_overall_quality(quality_components, response_obj)
        
        # Determine if upgrade is needed
        needs_upgrade = self._should_upgrade(overall_quality, llm_used)
        
        return {
            'quality': overall_quality,
            'needs_upgrade': needs_upgrade,
            'quality_breakdown': quality_components,
            'evaluation_details': {
                'llm_used': llm_used,
                'can_upgrade': self._can_upgrade(llm_used),
                'upgrade_available': self._can_upgrade(llm_used)
            }
        }

    def _calculate_quality_components(self, answer, original_prompt):
        """Calculate individual quality components"""
        answer_lower = answer.lower()
        word_count = len(answer.split())
        
        components = {
            'content_quality': self._assess_content_quality(answer_lower),
            'length_adequacy': self._assess_length_adequacy(word_count),
            'specificity': self._assess_specificity(answer_lower),
            'confidence_level': self._assess_confidence_level(answer_lower)
        }
        
        return components

    def _assess_content_quality(self, answer_lower):
        """Assess the quality of content based on indicators"""
        score = 1.0
        
        # Check for negative indicators - be more strict
        negative_count = 0
        for category, indicators in self.quality_indicators['negative'].items():
            for indicator in indicators:
                if indicator in answer_lower:
                    negative_count += 1
        
        # Penalize based on negative indicators - increased penalty
        score -= min(negative_count * 0.25, 0.8)  # Max penalty of 0.8 (increased from 0.6)
        
        # Boost for positive indicators
        positive_count = 0
        for category, indicators in self.quality_indicators['positive'].items():
            for indicator in indicators:
                if indicator in answer_lower:
                    positive_count += 1
        
        # Boost based on positive indicators
        score += min(positive_count * 0.1, 0.3)  # Max boost of 0.3
        
        return max(0.0, min(1.0, score))

    def _assess_length_adequacy(self, word_count):
        """Assess if answer length is adequate"""
        min_length = self.thresholds['minimum_length']
        
        if word_count < 3:  # Very short answers like "Yes."
            return 0.1  # Very low score for extremely short answers
        elif word_count < min_length:
            # Gradual penalty for short answers
            ratio = word_count / min_length
            return ratio * 0.5  # Max score of 0.5 for short answers
        elif word_count > 200:
            # Slight penalty for being too verbose (might indicate confusion)
            return 0.9
        else:
            # Good length range
            return 1.0

    def _assess_specificity(self, answer_lower):
        """Assess how specific and detailed the answer is"""
        # Look for specific details, examples, numbers
        specificity_indicators = [
            'for example', 'specifically', 'such as', 'including',
            'step 1', 'step 2', 'first', 'second', 'third',
            'percent', '%', 'number', 'amount'
        ]
        
        specific_count = sum(1 for indicator in specificity_indicators if indicator in answer_lower)
        
        # Convert count to score
        if specific_count >= 3:
            return 1.0
        elif specific_count >= 1:
            return 0.7 + (specific_count * 0.1)
        else:
            return 0.5  # Base score for general answers

    def _assess_confidence_level(self, answer_lower):
        """Assess the confidence level of the answer"""
        # High confidence indicators
        high_confidence = sum(1 for indicator in self.quality_indicators['positive']['confidence'] 
                            if indicator in answer_lower)
        
        # Low confidence indicators  
        low_confidence = sum(1 for indicator in self.quality_indicators['negative']['uncertainty'] 
                           if indicator in answer_lower)
        
        if low_confidence > high_confidence:
            return 0.2  # Low confidence (reduced from 0.3)
        elif high_confidence > low_confidence:
            return 1.0  # High confidence
        else:
            return 0.7  # Moderate confidence

    def _calculate_overall_quality(self, quality_components, response_obj):
        """Calculate weighted overall quality score"""
        # Special case for extremely short answers (like "Yes.")
        if quality_components['length_adequacy'] <= 0.1:
            return 0.3  # Force low quality score for very short answers
            
        weights = {
            'content_quality': 0.4,
            'length_adequacy': 0.3,  # Increased weight for length
            'specificity': 0.2,
            'confidence_level': 0.1   # Reduced weight for confidence
        }
        
        weighted_score = sum(
            quality_components[component] * weights[component]
            for component in weights
        )
        
        # Factor in explicit confidence if available
        explicit_confidence = response_obj.get('confidence')
        if explicit_confidence is not None:
            # Average with explicit confidence
            weighted_score = (weighted_score + explicit_confidence) / 2
        
        return max(0.0, min(1.0, weighted_score))

    def _should_upgrade(self, quality_score, llm_used):
        """Determine if answer should be upgraded to better model"""
        # Only upgrade if quality is below threshold AND model can be upgraded
        return (quality_score < self.thresholds['upgrade_threshold'] and 
                self._can_upgrade(llm_used))

    def _can_upgrade(self, llm_used):
        """Check if model can be upgraded"""
        """Check if model can be upgraded – using relaxed name matching"""
        if not llm_used:
            return False

        normalized = llm_used.lower().strip()

        # Accept variations like gpt-3.5-turbo, gpt-3.5-turbo-0613, openai-gpt, etc.
        upgrade_keywords = ['gpt-3.5', '3.5', 'turbo', 'openai-3.5', 'openai-gpt']
        return any(keyword in normalized for keyword in upgrade_keywords)

    def get_evaluation_details(self, response_obj, original_prompt):
        """Get detailed evaluation breakdown for debugging"""
        evaluation = self.evaluate_answer(response_obj, original_prompt)
        
        answer = response_obj.get('answer', '')
        quality_components = evaluation['quality_breakdown']
        
        details = {
            'answer_preview': answer[:100] + "..." if len(answer) > 100 else answer,
            'word_count': len(answer.split()),
            'quality_components': quality_components,
            'overall_quality': evaluation['quality'],
            'meets_upgrade_threshold': evaluation['quality'] >= self.thresholds['upgrade_threshold'],
            'can_upgrade': self._can_upgrade(response_obj.get('llm_used') or response_obj.get('model_metadata', {}).get('llm_used', 'unknown')),
            'recommendation': 'upgrade' if evaluation['needs_upgrade'] else 'keep'
        }
        
        return details