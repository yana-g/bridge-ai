import os
import sys
import asyncio
import streamlit as st
from pathlib import Path
import requests
import logging
import uuid

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Now import local modules
from api.userHandler import create_user, verify_user
from ui.chat.chatUI import chat_page

st.set_page_config(
    page_title="BRIDGE",
    page_icon="🌉",
    layout="centered"
)

# API configuration
API_BASE_URL = "http://localhost:8000"

def redirect_to_chat():
    """Redirect to the chat interface."""
    st.session_state['show_chat'] = True
    st.rerun()

def load_css():
    """Load the CSS styles from the external file."""
    css_file = Path(__file__).parent.parent.parent / "ui" / "static" / "styles.css"
    try:
        with open(css_file, 'r', encoding='utf-8') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error loading CSS: {e}")

def login_page():
    """Render the login page."""
    load_css()
    
    # Check if we should show the chat
    if st.session_state.get('show_chat', False):
        from ui.chat.chatUI import main as chat_main
        chat_main()
        return
    
    st.markdown("<div class='login-container'>", unsafe_allow_html=True)
    st.markdown("<h1 class='welcome-text'>Welcome to BRIDGE</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Bridge your prompts. Maximize your answers.</p>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        st.markdown("<h3 class='form-title'>Sign In</h3>", unsafe_allow_html=True)
        
        username = st.text_input("Username or Email", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        login_button = st.form_submit_button("Sign In", type="primary")
        
        if login_button:
            if not username or not password:
                st.error("Please enter both username and password")
            else:
                with st.spinner("Signing in..."):
                    success, result = asyncio.run(handle_login(username, password))
                    if success:
                        st.session_state['api_key'] = result
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = username
                        st.session_state['is_guest'] = False
                        st.session_state['chat_history'] = []  # Reset chat history on new login
                        redirect_to_chat()
                    else:
                        st.error(f"Login failed: {format_error_message(result)}")
    
    st.markdown("<div class='signup-prompt'>Don't have an account?</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Create Account", key="show_signup_btn", use_container_width=True):
            st.session_state['show_signup'] = True
            st.rerun()
    
    with col2:
        if st.button("Continue as Guest", key="guest_login_btn", use_container_width=True, type="secondary"):
            st.session_state['logged_in'] = True
            st.session_state['is_guest'] = True
            st.session_state['username'] = f"guest_{str(uuid.uuid4())[:8]}"  # Generate a random guest ID
            st.session_state['chat_history'] = []  # Initialize empty chat history
            print("Continuing as guest user")  # Debug log
            redirect_to_chat()
    
    st.markdown("</div>", unsafe_allow_html=True)

def signup_page():
    """Render the signup page."""
    load_css()
    
    st.markdown("<div class='login-container'>", unsafe_allow_html=True)
    st.markdown("<h1 class='welcome-text'>Create Account</h1>", unsafe_allow_html=True)
    
    if st.button("← Back to Login", key="back_to_login"):
        st.session_state.pop('show_signup', None)
        st.rerun()
    
    with st.form("signup_form"):
        st.markdown("<h3 class='form-title'>Sign Up</h3>", unsafe_allow_html=True)
        
        username = st.text_input("Username", key="signup_username")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password")
        
        signup_button = st.form_submit_button("Create Account", type="primary")
        
        if signup_button:
            if not all([username, email, password, confirm_password]):
                st.error("Please fill in all fields")
            elif password != confirm_password:
                st.error("Passwords do not match")
            else:
                with st.spinner("Creating account..."):
                    success, result = asyncio.run(handle_signup(username, password, email))
                    if success:
                        st.success("Account created successfully! Please log in.")
                        st.session_state.pop('show_signup', None)
                        st.rerun()
                    else:
                        st.error(f"Registration failed: {format_error_message(result)}")
    
    st.markdown("</div>", unsafe_allow_html=True)

async def handle_login(username: str, password: str) -> tuple[bool, str]:
    """Handle user login."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/users/login",
            json={"username": username, "password": password}
        )
        
        print(f"Login response status: {response.status_code}")  # Debug log
        print(f"Login response: {response.text}")  # Debug log
        
        if response.status_code == 200:
            data = response.json()
            # Check both possible response formats
            if data.get("access_token"):
                return True, data["access_token"]  # If using JWT
            elif data.get("api_key"):
                return True, data["api_key"]  # If using API key directly
            return False, "Invalid response format from server"
            
        return False, f"Login failed: {response.text}"
        
    except Exception as e:
        logging.error(f"Login error: {str(e)}", exc_info=True)
        return False, f"An error occurred: {str(e)}"

async def handle_signup(username: str, password: str, email: str = "") -> tuple[bool, str]:
    """Handle user signup."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/users/register",
            json={"username": username, "password": password, "email": email}
        )
        
        if response.status_code == 201:
            return True, "Account created successfully"
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get('detail', str(error_data))
                return False, error_msg
            except ValueError:
                return False, response.text or "Unknown error occurred"
                
    except Exception as e:
        logging.error(f"Signup error: {str(e)}", exc_info=True)
        return False, str(e)

def format_error_message(error: str) -> str:
    """
    Format error message to be more user-friendly.
    """
    if not error:
        return "An unknown error occurred"
        
    # Handle JSON string errors
    if error.startswith('{') and error.endswith('}'):
        try:
            import json
            error_json = json.loads(error)
            if 'detail' in error_json:
                return str(error_json['detail'])
        except:
            pass
            
    # Remove redundant prefixes
    for prefix in ["Signup failed: ", "Login failed: ", "Registration failed: "]:
        if error.startswith(prefix):
            error = error[len(prefix):]
    
    return error

def main():
    """Main application entry point."""
    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'api_key' not in st.session_state:
        st.session_state.api_key = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'show_signup' not in st.session_state:
        st.session_state.show_signup = False
    if 'is_guest' not in st.session_state:
        st.session_state.is_guest = False
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Show the appropriate page
    if st.session_state.get('logged_in', False):
        chat_page()
    elif st.session_state.get('show_signup', False):
        signup_page()
    else:
        login_page()

if __name__ == "__main__":
    main()