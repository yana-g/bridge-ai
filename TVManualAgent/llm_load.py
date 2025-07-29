"""
Language Model Management for TV Manual Agent

This module provides functionality to load and manage different language models
for generating responses based on TV manual content. It supports both open models
and authenticated models like Llama-2.

Key Features:
- Support for multiple open-source language models
- Automatic GPU detection and optimization
- Model loading with progress tracking
- Response generation with configurable parameters

Dependencies:
    torch: For model loading and inference
    transformers: For model and tokenizer loading
    huggingface_hub: For model authentication and download
    streamlit: For UI components and progress tracking
"""

import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from huggingface_hub import login
import streamlit as st
from typing import Dict, List, Optional, Union

class LlamaModel:
    """
    Manages loading and using language models for generating responses.
    
    This class handles the lifecycle of language models, including loading,
    configuration, and text generation. It supports both open models and
    authenticated models like Llama-2.
    
    Attributes:
        model: The loaded language model
        tokenizer: Tokenizer for the loaded model
        pipeline: Text generation pipeline
        model_name: Name/ID of the currently loaded model
        available_models: List of pre-configured model options
    """
    
    def __init__(self):
        """Initialize the LlamaModel with default settings and available models."""
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self.model_name = None
        
        # Define available models with metadata
        self.available_models: List[Dict[str, str]] = [
            # Open models (no authentication required)
            {
                "name": "microsoft/DialoGPT-large",
                "display_name": "DialoGPT Large (Conversational)",
                "type": "open"
            },
            {
                "name": "microsoft/DialoGPT-medium", 
                "display_name": "DialoGPT Medium (Faster)",
                "type": "open"
            },
            {
                "name": "gpt2-large",
                "display_name": "GPT-2 Large",
                "type": "open"
            },
            {
                "name": "gpt2-medium",
                "display_name": "GPT-2 Medium",
                "type": "open"
            },
            # Instruction-tuned models
            {
                "name": "microsoft/DialoGPT-small",
                "display_name": "DialoGPT Small (Lightweight)",
                "type": "open"
            }
        ]
        
    def try_load_llama_with_token(self, token=None):
        """
        Try to load Llama-2 with optional token
        
        Args:
            token: Optional Hugging Face authentication token
            
        Returns:
            bool: True if the model was loaded successfully, False otherwise
            
        Displays:
            - Loading spinner during model loading
            - Success/error message in the Streamlit interface
        """
        try:
            if token:
                login(token=token)
            
            with st.spinner("Attempting to load Llama-2-7b-chat-hf..."):
                device = "cuda" if torch.cuda.is_available() else "cpu"
                
                self.model_name = "meta-llama/Llama-2-7b-chat-hf"
                
                # Load tokenizer with trust_remote_code for custom models
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name,
                    trust_remote_code=True
                )
                
                # Load model with appropriate settings based on device
                if device == "cuda":
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_name,
                        torch_dtype=torch.float16,  # Use half precision on GPU
                        device_map="auto",
                        trust_remote_code=True
                    )
                else:
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_name,
                        torch_dtype=torch.float32,  # Full precision on CPU
                        trust_remote_code=True
                    )
                
                # Initialize text generation pipeline
                self.pipeline = pipeline(
                    "text-generation",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    max_length=1024,
                    temperature=0.7,  # Controls randomness (0.0 to 1.0)
                    do_sample=True,   # Enable sampling for more diverse outputs
                    device=0 if device == "cuda" else -1  # Device selection
                )
                
                st.success("Llama-2-7b loaded successfully!")
                return True
                
        except Exception as e:
            st.warning(f"Could not load Llama-2: {str(e)}")
            return False
    
    def load_open_model(self, model_info):
        """
        Load an open model that doesn't require authentication.
        
        Args:
            model_info: Dictionary containing model configuration
                - name: Model identifier on Hugging Face Hub
                - display_name: User-friendly model name
                - type: Model type (should be "open")
                
        Returns:
            bool: True if the model was loaded successfully, False otherwise
            
        Displays:
            - Loading spinner during model loading
            - Success/error message in the Streamlit interface
        """
        try:
            with st.spinner(f"Loading {model_info['display_name']}..."):
                device = "cuda" if torch.cuda.is_available() else "cpu"
                
                self.model_name = model_info['name']
                
                # Load tokenizer and model
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                
                # Add pad token if it doesn't exist
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                
                # Move model to GPU if available
                if device == "cuda":
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_name,
                        torch_dtype=torch.float16,
                        device_map="auto"
                    )
                else:
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_name,
                        torch_dtype=torch.float32
                    )
                
                # Initialize text generation pipeline
                self.pipeline = pipeline(
                    "text-generation",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    max_length=512,
                    temperature=0.7,
                    do_sample=True,
                    device=0 if device == "cuda" else -1,
                    pad_token_id=self.tokenizer.eos_token_id
                )
                
                st.success(f"{model_info['display_name']} loaded successfully!")
                return True
                
        except Exception as e:
            st.error(f"Error loading {model_info['display_name']}: {str(e)}")
            return False
    
    def load_model(self, selected_model=None, hf_token=None):
        """Load model with automatic fallback"""
        
        # If user provided HF token, try Llama-2 first
        if hf_token:
            if self.try_load_llama_with_token(hf_token):
                return True
        
        # If no model selected, try the best available open model
        if not selected_model:
            selected_model = self.available_models[0]  # DialoGPT-large
        
        # Try to load the selected open model
        if self.load_open_model(selected_model):
            return True
        
        # If all fails, try the simplest model
        fallback_model = {
            "name": "gpt2",
            "display_name": "GPT-2 Base (Fallback)",
            "type": "open"
        }
        
        st.warning("Trying fallback model...")
        return self.load_open_model(fallback_model)
    
    def generate_response(self, prompt):
        """Generate response using the loaded model"""
        if not self.pipeline:
            return "Model not loaded. Please load the model first."
        
        try:
            # Truncate the prompt to fit within model limits
            max_tokens_for_prompt = getattr(self, 'max_input_tokens', 512) - 50  # Leave room for formatting
        
            # Simple truncation if no tokenizer available
            if not self.tokenizer:
                max_chars = max_tokens_for_prompt * 4  # Rough estimate
                truncated_prompt = prompt[:max_chars] if len(prompt) > max_chars else prompt
            else:
                # Use tokenizer for accurate truncation
                tokens = self.tokenizer.encode(prompt, truncation=False)
                if len(tokens) <= max_tokens_for_prompt:
                    truncated_prompt = prompt
                else:
                    truncated_tokens = tokens[:max_tokens_for_prompt]
                    truncated_prompt = self.tokenizer.decode(truncated_tokens, skip_special_tokens=True)
        
            # Different prompt formatting based on model type
            if self.model_name and "llama" in self.model_name.lower():
                # Llama-2 chat format
                formatted_prompt = f"<s>[INST] {truncated_prompt} [/INST]"
                max_new_tokens = 150
            elif self.model_name and "dialogpt" in self.model_name.lower():
                # DialoGPT format
                formatted_prompt = f"User: {truncated_prompt}\nBot:"
                max_new_tokens = 100
            else:
                # Standard GPT format
                formatted_prompt = f"Question: {truncated_prompt}\nAnswer:"
                max_new_tokens = 100
        
            # Final check: ensure formatted prompt isn't too long
            max_final_tokens = getattr(self, 'max_input_tokens', 512)
            if not self.tokenizer:
                max_chars = max_final_tokens * 4
                final_prompt = formatted_prompt[:max_chars] if len(formatted_prompt) > max_chars else formatted_prompt
            else:
                tokens = self.tokenizer.encode(formatted_prompt, truncation=False)
                if len(tokens) <= max_final_tokens:
                    final_prompt = formatted_prompt
                else:
                    truncated_tokens = tokens[:max_final_tokens]
                    final_prompt = self.tokenizer.decode(truncated_tokens, skip_special_tokens=True)
        
            # Generate response
            response = self.pipeline(
                final_prompt,
                max_new_tokens=max_new_tokens,
                num_return_sequences=1,
                pad_token_id=self.tokenizer.eos_token_id,
                do_sample=True,
                temperature=0.7,
                top_p=0.9
            )
        
            # Check if response exists and is valid - SEPARATED CHECKS
            if not response or len(response) == 0:
                return "Error: No response from model"
            
            if 'generated_text' not in response[0]:
                return "Error: Invalid response format from model"
        
            generated_text = response[0]['generated_text']
            if not generated_text:
                return "Error: Model generated empty text"
        
            # Clean up the response based on model type
            if self.model_name and "llama" in self.model_name.lower():
                if "[/INST]" in generated_text:
                    answer = generated_text.split("[/INST]")[-1].strip()
                else:
                    answer = generated_text[len(final_prompt):].strip()
            elif self.model_name and "dialogpt" in self.model_name.lower():
                if "Bot:" in generated_text:
                    answer = generated_text.split("Bot:")[-1].strip()
                else:
                    answer = generated_text[len(final_prompt):].strip()
            else:
                if "Answer:" in generated_text:
                    answer = generated_text.split("Answer:")[-1].strip()
                else:
                    answer = generated_text[len(final_prompt):].strip()
        
            # Clean up the answer
            if answer:
                answer = answer.split('\n')[0].strip()  # Take first line only
        
            return answer if answer else "I couldn't generate a proper response"
        
        except Exception as e:
            return f"Error generating response: {str(e)}"