"""
BRIDGE Chat Interface

This module implements the main chat interface for the BRIDGE AI system, providing a Streamlit-based
web interface for users to interact with various LLM models through the BRIDGE API. The interface
supports different conversation styles, message history, and real-time interaction with the LLM backend.

Key Features:
- Real-time chat interface with message history
- Support for different conversation styles (vibes) and answer lengths
- Code block formatting and syntax highlighting
- User authentication and session management
- Responsive design for various screen sizes
- Integration with BRIDGE API for LLM routing

Dependencies:
    streamlit: Web application framework
    requests: HTTP client for API communication
    pathlib: Path manipulation
    datetime: Timestamp handling
    uuid: Unique ID generation
    re: Regular expressions for text processing
    asyncio: Asynchronous operations
"""

import os
import uuid
import streamlit as st
import requests
from pathlib import Path
from datetime import datetime
import time
import asyncio
from streamlit.runtime.scriptrunner import add_script_run_ctx
import re

# Base URL for the BRIDGE API
API_BASE_URL = "http://localhost:8000"

def load_css():
    """
    Load and inject custom CSS styles for the chat interface.
    
    This function locates and loads the CSS file from the project's static directory.
    The CSS file is expected to be at: /ui/static/styles.css relative to the project root.
    
    The function includes error handling for file operations and logs any issues.
    """
    print("✅ CSS loaded!")
    # Navigate to the project root and then to the UI static directory
    css_file = Path(__file__).parent / "static" / "styles.css"
    print(f"Loading CSS from: {css_file}") 
    try:
        with open(css_file) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"CSS file not found at: {css_file}")
        print(f"Error: CSS file not found at: {css_file}")
    except Exception as e:
        st.error(f"Error loading CSS: {str(e)}")
        print(f"Error loading CSS: {str(e)}")

def escape_html(text):
    """
    Escape HTML special characters to prevent XSS and ensure safe rendering.
    
    Args:
        text (str): The input text containing HTML special characters
        
    Returns:
        str: Escaped text with HTML special characters converted to entities
    """
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))

def format_code_blocks(text):
    """
    Convert Markdown-style code blocks and inline code into styled HTML.
    
    This function processes the input text to identify and format:
    - Code blocks (```code```) as pre-formatted blocks with syntax highlighting
    - Inline code (`code`) as inline code spans
    
    Args:
        text (str): The input text containing Markdown-style code blocks
        
    Returns:
        str: HTML-formatted text with styled code blocks and spans
    """
    if not isinstance(text, str):
        text = str(text)

    # Process code blocks (```...```)
    def block_replacer(match):
        code = match.group(1).strip()
        return (
            '<div class="code-block"><pre><code>'
            + escape_html(code)
            + '</code></pre></div>'
        )

    text = re.sub(
        r'```(?:[\w\-+]*\n)?(.*?)```',
        block_replacer,
        text,
        flags=re.DOTALL
    )

    # Process inline code (`...`)
    text = re.sub(
        r'(?<!`)`([^`\n]+?)`(?!`)',
        r'<code>\1</code>',
        text
    )

    return text

def send_message(question: str, vibe: str, nature_of_answer: str, confidence: bool = True) -> dict:
    """
    Send a message to the LLM API and return the response.
    
    Args:
        question: The question to ask the LLM
        vibe: The vibe to use for the question
        nature_of_answer: The nature of the answer to expect
        confidence: Whether to include confidence in the response
    
    Returns:
        dict: The response from the LLM API
    """
    try:
        # Get values from session state with defaults
        api_key = st.session_state.get('api_key', 'guest_key')
        username = st.session_state.get('username', 'guest_user')
        
        # Debug log
        print(f"\n=== Sending request to /ask-llm/ ===")
        print(f"API Key: {api_key}")
        print(f"Username: {username}")
        
        # Prepare headers with the values from session state
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": str(api_key),
            "X-Username": str(username)
        }
        print(f"Headers: {headers}")
        
        # For logged-in users, ensure we have a valid API key
        if not st.session_state.get('is_guest', True) and (not api_key or api_key == 'guest_key'):
            print("Error: Invalid session - no API key for logged-in user")
            return {"response": "Error: Invalid session. Please log in again."}
        
        payload = {
            "vibe": vibe,
            "sender_id": username,
            "question_id": str(uuid.uuid4()),
            "question": question,
            "confidence": confidence,
            "nature_of_answer": nature_of_answer
        }
        print(f"Payload: {payload}")
        
        response = requests.post(
            f"{API_BASE_URL}/ask-llm/", 
            json=payload, 
            headers=headers,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error response: {response.text}")
            return {"response": f"Error: {response.status_code} - {response.text}"}
            
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {str(e)}")
        return {"response": f"Connection error: {str(e)}"}
    except Exception as e:
        print(f"Exception in send_message: {str(e)}")
        return {"response": f"An error occurred: {str(e)}"}

def render_chat_messages():
    """
    Render the chat messages in the UI with appropriate styling.
    
    This function processes and displays all messages in the chat history,
    applying different styles for user and AI messages. It handles:
    - Formatting code blocks and inline code
    - Displaying timestamps
    - Showing model information and confidence scores for AI responses
    - Handling streaming vs. complete messages
    
    The function expects the following in st.session_state:
    - chat_history: List of message dictionaries with 'role', 'content', and 'timestamp' keys
    - For AI messages: 'model_metadata' with 'llm_used' and 'confidence' information
    """
    if not st.session_state.get('chat_history'):
        st.markdown(''' ''', unsafe_allow_html=True)
        return
        
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            # Format user message with proper escaping and code blocks
            content = format_code_blocks(message["content"])
            st.markdown(f'''
                <div class="chat-message user-message">
                    <div class="message-content">{content}</div>
                    <div class="message-time">{message.get("timestamp", "")}</div>
                </div>
            ''', unsafe_allow_html=True)
        else:
            # Process AI response message
            model_metadata = message.get("model_metadata", {})
            model_name = model_metadata.get("llm_used", "Bridge AI").upper()
            
            # Default to BRIDGE if model is unknown
            if model_name.lower() == "unknown":
                model_name = "BRIDGE"

            # Extract confidence score from metadata or response text
            confidence = model_metadata.get("confidence")
            if confidence is None and "Confidence score:" in message["content"]:
                try:
                    # Parse confidence score from response text if not in metadata
                    confidence_str = message["content"].split("Confidence score:")[1].strip().split()[0].rstrip('., ')
                    confidence = float(confidence_str)
                except (IndexError, ValueError):
                    pass

            # Format confidence for display
            confidence_display = f"Confidence: {int(confidence * 100)}%" if confidence is not None else "N/A"
            content = format_code_blocks(message["content"])
            
            # Handle streaming vs. complete messages
            if message.get("is_streaming"):
                # Show typing indicator for streaming responses
                st.markdown(f'''
                    <div class="chat-message ai-message">
                        <div class="message-header">
                            <div class="model-info">
                                <span class="model-name">{model_name}</span>
                                <span class="confidence-score">• {confidence_display}</span>
                            </div>                          
                        </div>
                        <div class="message-content">
                            {content}<span style="animation: blink 1s infinite; color: #666;">▌</span>
                        </div>
                        <div class="message-time">{message.get("timestamp", "")}</div>
                    </div>
                ''', unsafe_allow_html=True)
            else:
                # Show complete response
                st.markdown(f'''
                    <div class="chat-message ai-message">
                        <div class="message-header">
                            <div class="model-info">
                                <span class="model-name">{model_name}</span>
                                <span class="confidence-score">• {confidence_display}</span>
                            </div>                          
                        </div>
                        <div class="message-content">{content}</div>
                        <div class="message-time">{message.get("timestamp", "")}</div>
                    </div>
                ''', unsafe_allow_html=True)

def chat_page():
    """
    Render the chat page.
    
    This function handles the main chat interface, including:
    - User authentication and session management
    - Chat history rendering
    - User input handling and message sending
    - Real-time interaction with the LLM backend
    
    The function expects the following in st.session_state:
    - logged_in: Boolean indicating whether the user is logged in
    - is_guest: Boolean indicating whether the user is a guest
    - username: The username of the logged-in user
    - chat_history: List of message dictionaries with 'role', 'content', and 'timestamp' keys
    - api_key: The API key for the logged-in user
    """
    # Check if user is logged in or is a guest
    if not st.session_state.get('logged_in'):
        st.query_params.clear()
        st.rerun()
        return

    # Initialize session state with defaults if they don't exist
    st.session_state.setdefault('is_guest', True)
    st.session_state.setdefault('username', f"guest_{str(uuid.uuid4())[:8]}")
    st.session_state.setdefault('chat_history', [])
    st.session_state.setdefault('form_key', str(uuid.uuid4()))
    
    # Set default API key for guest users
    if st.session_state.is_guest and (not st.session_state.get('api_key') or st.session_state.api_key == 'None'):
        st.session_state.api_key = "guest_key"
    
    # Load CSS
    load_css()

    # Create sidebar with user info and logout button
    with st.sidebar:
        # User info and logout button in a single row
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f'''
                <div class="sidebar-username">
                    @{st.session_state.username}
                </div>
            ''', unsafe_allow_html=True)
        with col2:
            # Simple logout form that redirects to login page
            st.markdown('''
                <form action="loginUI.py" method="get">
                    <input type="hidden" name="logout" value="true">
                    <button type="submit" class="logout-link">Logout</button>
                </form>
            ''', unsafe_allow_html=True)
        
        # Add some space
        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    # Create HTML layout - everything EXCEPT the footer
    st.markdown('''
        <div class="main">
            <div class="header-section">
                <h1>BRIDGE AI</h1>
                <p>Bridge your prompts. Maximize your answers.</p>
            </div>
            <div class="chat-area-wrapper">
                <div class="chat-history">
    ''', unsafe_allow_html=True)

    # Render chat messages
    render_chat_messages()

    st.markdown('''
                </div>
            </div>
        </div>
    ''', unsafe_allow_html=True)

    # Create FOOTER with form inside
    with st.container():
        with st.form(key=f'chat_form_{st.session_state.form_key}', clear_on_submit=True):
            user_input = st.text_area(
                "Your message",
                label_visibility="collapsed",
                placeholder="Let Bridge route your prompt...",
                key=f"user_input_{st.session_state.form_key}",
                height=60
            )
        
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                vibe = st.selectbox(
                    "Style",
                    ["Business/Professional", "Academic/Research",
                     "Technical/Development", "Daily/General", "Creative/Emotional"],
                    key=f"vibe_{st.session_state.form_key}",
                    label_visibility="collapsed"
                )
            with col2:
                nature = st.selectbox(
                    "Length",
                    ["Short", "Medium", "Detailed"],
                    key=f"nature_{st.session_state.form_key}",
                    label_visibility="collapsed"
                )
            with col3:
                submit_button = st.form_submit_button("Send", use_container_width=True, type="primary")
            
            if submit_button and user_input.strip():
                # Add user message to chat history
                st.session_state.chat_history.append({
                    "role": "user", 
                    "content": user_input,
                    "vibe": vibe,
                    "nature": nature,
                    "timestamp": datetime.now().strftime("%H:%M")
                })
    
                # Set loading state
                st.session_state.waiting_for_response = True
                st.session_state.current_response = ""
    
                # Rerun to show user message and spinner
                st.rerun()

    # Show spinner if we're waiting for a response
    if st.session_state.get('waiting_for_response', False):
        with st.spinner('Bridge is routing your request...'):
            # Only run the API call if we haven't started it yet
            if not st.session_state.get('api_call_started', False):
                st.session_state.api_call_started = True
                st.rerun()
            else:
                # This is where the API call happens
                try:
                    response = send_message(
                        st.session_state.chat_history[-1]["content"],
                        st.session_state.chat_history[-1]["vibe"],
                        st.session_state.chat_history[-1]["nature"],
                        confidence=True
                    )
                    
                    # Debug: Print the full response structure
                    print("\n=== DEBUG: Full Response ===")
                    print(response)
                    print("=== End of Response ===\n")
                
                    if response and 'response' in response:
                        # Process the response...
                        model_metadata = response.get('model_metadata', {})
                        # print("\n=== DEBUG: Model Metadata ===")
                        # print(model_metadata)
                        # print("=== End of Model Metadata ===\n")
                        
                        model_name = model_metadata.get("llm_used", "Bridge AI").upper()
                        if model_name.lower() == "unknown":
                            model_name = "BRIDGE"
                        
                        # Debug: Check for follow-up questions
                        print("\n=== DEBUG: Checking for follow-up questions ===")
                        print(f"Response keys: {response.keys()}")
                        if 'follow_up_questions' in response:
                            print(f"Follow-up questions found: {response['follow_up_questions']}")
                        print("=== End of Follow-up Check ===\n")
                        
                        # Add AI response to history
                        ai_response = response['response']
                        
                        # Add follow-up questions if they exist
                        if 'follow_up_questions' in response and response['follow_up_questions']:
                            questions = response['follow_up_questions']
                            print(f"\n=== DEBUG: Processing {len(questions)} follow-up questions ===")
                            if isinstance(questions, list):
                                questions_html = "<br><br>" + "<br>• ".join([""] + questions)
                                print(f"Questions HTML: {questions_html}")
                                ai_response += questions_html
                            print("=== End of Questions Processing ===\n")
                        
                        ai_message = {
                            "role": "ai",
                            "content": ai_response,
                            "vibe": st.session_state.chat_history[-1]["vibe"],
                            "nature": st.session_state.chat_history[-1]["nature"],
                            "timestamp": datetime.now().strftime("%H:%M"),
                            "model_metadata": model_metadata,
                            "is_streaming": False
                        }
                        st.session_state.chat_history.append(ai_message)
                
                        # Reset states
                        st.session_state.waiting_for_response = False
                        st.session_state.api_call_started = False
                        st.rerun()
                
                except Exception as e:
                    st.error(f"Error getting response: {str(e)}")
                    st.session_state.waiting_for_response = False
                    st.session_state.api_call_started = False
                    st.rerun()
                
        # Show spinner if we're waiting for a response
        if st.session_state.get('waiting_for_response', False):
            with st.spinner('Bridge is routing your request...'):
                pass  # Just show the spinner
                
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    chat_page()