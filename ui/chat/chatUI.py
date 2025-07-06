import os
import uuid
import streamlit as st
import requests
from pathlib import Path
from datetime import datetime
import time
import asyncio
from streamlit.runtime.scriptrunner import add_script_run_ctx

API_BASE_URL = "http://localhost:8000"

def load_css():
    print("✅ CSS loaded!")
    # Go up three directory levels to reach the project root
    # then navigate to ui/static/styles.css
    css_file = Path(__file__).parent.parent.parent / "ui" / "static" / "styles.css"
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

def send_message(question: str, vibe: str, nature_of_answer: str, confidence: bool = True) -> dict:
    try:
        # Get values from session state with defaults
        api_key = st.session_state.get('api_key', 'guest_key')
        username = st.session_state.get('username', 'guest_user')
        
        # Prepare headers with the values from session state
        headers = {
            "Content-Type": "application/json",
            "x-api-key": str(api_key),
            "x-username": str(username)
        }
        
        payload = {
            "vibe": vibe,
            "sender_id": username,
            "question_id": str(uuid.uuid4()),
            "question": question,
            "confidence": confidence,
            "nature_of_answer": nature_of_answer
        }
        
        response = requests.post(
            f"{API_BASE_URL}/ask-llm/", 
            json=payload, 
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"response": f"Error {response.status_code}: {response.text}"}
            
    except requests.exceptions.RequestException as e:
        return {"response": f"Connection error: {str(e)}"}
    except Exception as e:
        return {"response": f"An error occurred: {str(e)}"}

def render_chat_messages():
    if not st.session_state.get('chat_history'):
        st.markdown(''' ''', unsafe_allow_html=True)
    else:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f'''
                    <div class="chat-message user-message">
                        <div class="message-content">{message["content"]}</div>
                        <div class="message-time">{message.get("timestamp", "")}</div>
                    </div>
                ''', unsafe_allow_html=True)
            else:
                # Get model info and confidence from message data
                model_metadata = message.get("model_metadata", {})
                model_name = model_metadata.get("llm_used", "Bridge AI").upper()

                # If model is unknown, use BRIDGE AI
                if model_name.lower() == "unknown":
                    model_name = "BRIDGE"

                # Try to get confidence from metadata first, then from response text
                confidence = model_metadata.get("confidence")
                if confidence is None and "Confidence score:" in message["content"]:
                    try:
                        # Extract confidence from response text (e.g., "...Confidence score: 1.")
                        confidence_str = message["content"].split("Confidence score:")[1].strip().split()[0].rstrip('., ')
                        confidence = float(confidence_str)
                    except (IndexError, ValueError):
                        pass

                confidence_display = f"Confidence: {int(confidence * 100)}%" if confidence is not None else "N/A"
            
                if message.get("is_streaming"):
                    st.markdown(f'''
                        <div class="chat-message ai-message">
                            <div class="message-header">
                                <div class="model-info">
                                    <span class="model-name">{model_name}</span>
                                    <span class="confidence-score">• {confidence_display}</span>
                                </div>                          
                            </div>
                            <div class="message-content">
                                {message["content"]}<span style="animation: blink 1s infinite; color: #666;">▌</span>
                            </div>
                            <div class="message-time" style="margin-left: auto;">{message.get("timestamp", "")}</div>
                        </div>
                    ''', unsafe_allow_html=True)
                else:
                    st.markdown(f'''
                        <div class="chat-message ai-message">
                            <div class="message-header">
                                <div class="model-info">
                                    <span class="model-name">{model_name}</span>
                                    <span class="confidence-score">• {confidence_display}</span>
                                </div>                          
                            </div>
                            <div class="message-content">{message["content"]}</div>
                            <div class="message-time" style="margin-left: auto;">{message.get("timestamp", "")}</div>
                        </div>
                    ''', unsafe_allow_html=True)

def chat_page():
    # Initialize session state
    st.session_state.setdefault('is_guest', True)
    st.session_state.setdefault('logged_in', True)
    st.session_state.setdefault('username', f"guest_{str(uuid.uuid4())[:8]}")
    st.session_state.setdefault('chat_history', [])
    st.session_state.setdefault('form_key', str(uuid.uuid4()))
    
    # Set default API key for guest users
    if st.session_state.is_guest and (not st.session_state.get('api_key') or st.session_state.api_key == 'None'):
        st.session_state.api_key = "guest_key"
    
    # Load CSS
    load_css()

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
                        print("\n=== DEBUG: Model Metadata ===")
                        print(model_metadata)
                        print("=== End of Model Metadata ===\n")
                        
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
