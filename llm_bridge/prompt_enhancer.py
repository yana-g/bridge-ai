
class PromptEnhancer:
    def __init__(self):
        self.templates = {
            'academic': {
                'simple': "Please provide a concise academic answer about {topic}. {additional_context}",
                'complex': "Please provide a detailed academic explanation about {topic}, showing your chain of thought. {additional_context}"
            },
            'technical': {
                'simple': "Please provide a technical answer about {topic}. {additional_context}",
                'complex': "Please explain in depth the technical aspects of {topic}, including reasoning. {additional_context}"
            }
        }
        self.default_template = {
            'simple': "Please answer the following question: {original_prompt}. {additional_context}",
            'complex': "Please provide a detailed answer with your reasoning for: {original_prompt}. {additional_context}"
        }

    def enhance_prompt(self, original_prompt, vibe, response_type, additional_info=None, show_confidence=False):
        topic = original_prompt
        additional_context = ""
        if additional_info:
            additional_context = "Additional context: " + ", ".join(additional_info)
        if show_confidence:
            additional_context += "End your response with: [CONFIDENCE:X] where X is 0.0 to 1.0"
        if vibe in self.templates and response_type in self.templates[vibe]:
            template = self.templates[vibe][response_type]
        else:
            template = self.default_template[response_type]
        return template.format(topic=topic, original_prompt=original_prompt, additional_context=additional_context)
