# prompt_analyzer.py - Improved with better structure and organization

class PromptAnalyzer:
    def __init__(self):
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
                        'keywords': ['language', 'framework', 'platform', 'technology', 'python', 'javascript',
                                   'react', 'django', 'aws', 'docker', 'api', 'database', 'sql'],
                        'question': "Which programming language or technology are you working with?"
                    },
                    'context': {
                        'keywords': ['project', 'application', 'system', 'website', 'app', 'software'],
                        'question': "What type of project or application is this for?"
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

    def analyze_informativeness(self, prompt, vibe):
        """Analyze how informative a prompt is and what additional info might be needed"""
        
        # Basic length check
        word_count = len(prompt.split())
        if word_count < self.assessment_thresholds['too_short']:
            return 0.2, ["Could you provide more details about your question?"]
        
        # Check for question structure
        has_question_structure = self._has_question_structure(prompt)
        if not has_question_structure:
            return self.assessment_thresholds['basic_question'], ["Could you phrase your request as a question?"]
        
        # Check vibe-specific context completeness
        if vibe in self.context_requirements:
            context_score, missing_questions = self._assess_context_completeness(prompt, vibe)
            if context_score < self.assessment_thresholds['contextual_completeness'] and missing_questions:
                return context_score, missing_questions[:3]  # Limit to 3 questions
        
        # If we get here, the prompt is sufficiently informative
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