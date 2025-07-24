"""
BRIDGE Authentication Interface

This module provides the login and signup functionality for the BRIDGE LLM Routing System.
It handles user authentication, session management, and redirection to the chat interface.

Key Features:
- User login with username/email and password
- New user registration
- Guest access
- Session management
- Error handling and user feedback

Dependencies:
    streamlit: Web application framework
    requests: HTTP client for API communication
    asyncio: Asynchronous operations
    pathlib: Path manipulation
    uuid: Generate unique identifiers
    logging: Error logging
"""
import os
import sys
import asyncio
import streamlit as st
from pathlib import Path
import requests
import logging
import uuid

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Now import local modules
from api.userHandler import create_user, verify_user
from bridge_ui.chatUI import chat_page

st.set_page_config(
    page_title="BRIDGE",
    page_icon="🌐",
    layout="centered"
)

# API configuration
API_BASE_URL = "http://localhost:8000"

def redirect_to_chat():
    """Redirect to the chat interface."""
    st.session_state['show_chat'] = True
    st.rerun()

def load_css():
    """
    Load and inject CSS styles from an external file into the Streamlit app.
    
    This function locates the styles.css file in the project's static directory and
    injects its contents into the page's <head> section using Streamlit's markdown
    with HTML. If the file cannot be found or read, an error message is displayed.
    
    The CSS file is expected to be at: /bridge_ui/static/styles.css relative to the project root.
    
    Note:
        - Uses pathlib for cross-platform path resolution
        - Handles file reading with UTF-8 encoding
        - Gracefully handles file not found and other I/O errors
        
    Raises:
        FileNotFoundError: If the CSS file doesn't exist at the specified location
        IOError: If there are permission issues or other I/O errors
    """ 
    css_file = Path(__file__).parent / "static" / "styles.css"
    try:
        with open(css_file, 'r', encoding='utf-8') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error loading CSS: {e}")

def login_page():
    # Handle logout
    if st.query_params.get("logout"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
    
    # If already logged in, redirect to chat
    if st.session_state.get('logged_in'):
        st.query_params["page"] = "chat"
        st.rerun()
    
    load_css()
    
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
                    success, message, result = asyncio.run(handle_login(username, password))
                    if success:
                        st.session_state.clear()
                        st.session_state.update({
                            'api_key': result['api_key'],
                            'logged_in': True,
                            'username': result['username'],
                            'is_guest': False,
                            'chat_history': []
                        })
                        st.query_params["page"] = "chat"
                        st.rerun()
                    else:
                        st.error(message)
    
    st.markdown("<div class='signup-prompt'>Don't have an account?</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Create Account", key="show_signup_btn", use_container_width=True):
            st.session_state['show_signup'] = True
            st.rerun()
    
    with col2:
        if st.button("Continue as Guest", key="guest_login_btn", use_container_width=True, type="secondary"):
            # Clear any existing session state
            st.session_state.clear()
            # Set guest session state
            st.session_state.update({
                'logged_in': True,
                'is_guest': True,
                'username': f"guest_{str(uuid.uuid4())[:8]}",
                'chat_history': [],
                'api_key': "guest_key"
            })
            # Use st.experimental_set_query_params for navigation
            st.query_params["page"] = "chat"
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

def signup_page():
    """
    Render and handle the user registration page.
    
    This function provides a form for new users to create an account with the following fields:
    - Username (required, must be unique)
    - Email (required, must be valid format)
    - Password (required, with confirmation)
    
    The function validates the input client-side and then communicates with the backend API
    to create a new user account. Upon successful registration, the user is redirected
    back to the login page to sign in with their new credentials.
    
    Session State Variables Used:
        show_signup (bool): Controls whether to show the signup form
    """
    # Load custom CSS for consistent styling
    load_css()
    
    # Start signup container with custom styling
    st.markdown("<div class='login-container'>", unsafe_allow_html=True)
    st.markdown("<h1 class='welcome-text'>Create Account</h1>", unsafe_allow_html=True)
    
    # Add back to login button
    if st.button("← Back to Login", key="back_to_login"):
        st.session_state.pop('show_signup', None)
        st.rerun()
    
    # Create signup form with custom styling
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
                # Server-side valid ation and registration
                with st.spinner("Creating account..."):
                    success, result = asyncio.run(handle_signup(username, password, email))
                    if success:
                        st.success("Account created successfully! Please log in.")
                        # Redirect to login page    
                        st.session_state.pop('show_signup', None)
                        st.rerun()
                    else:
                        # Format error message for user-friendly display    
                        st.error(f"Registration failed: {format_error_message(result)}")
    
    # Close signup container
    st.markdown("</div>", unsafe_allow_html=True)

async def handle_login(username: str, password: str) -> tuple[bool, str, dict]:
    """
    Handle user login.
    
    Args:
        username: Username or email
        password: User's password
        
    Returns:
        tuple: (success: bool, message: str, data: dict) where data contains api_key and username if successful
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/users/login",
            json={"username": username, "password": password}
        )
        
        try:
            data = response.json()
            if data.get("success") is True and data.get("user"):
                return True, "Login successful", {
                    "api_key": data["user"].get("api_key"),
                    "username": data["user"].get("username")
                }
            elif data.get("user") and data["user"].get("api_key"):
                return True, "Login successful", {
                    "api_key": data["user"]["api_key"],
                    "username": data["user"].get("username")
                }
            elif "detail" in data:
                return False, data["detail"], {}
                
        except ValueError:
            if response.status_code == 200:
                return False, "Invalid response format from server", {}
            else:
                return False, f"Login failed with status {response.status_code}", {}
                
    except Exception as e:
        logging.error(f"Login error: {str(e)}", exc_info=True)
        return False, f"An error occurred during login: {str(e)}", {}

async def handle_signup(username: str, password: str, email: str = "") -> tuple[bool, str]:
    """
    Handle the user registration process by communicating with the backend API.
    
    This function sends a registration request to the backend API with the provided
    user credentials. It handles the API response and returns appropriate status
    information to the caller.
    
    Args:
        username (str): The desired username for the new account
        password (str): The password for the new account
        email (str, optional): The email address for the new account. Defaults to "".
        
    Returns:
        tuple[bool, str]: A tuple containing:
            - bool: True if registration was successful, False otherwise
            - str: Success message or error details
            
    Example:
        success, message = await handle_signup("newuser", "securepassword", "user@example.com")
        if success:
            print(f"Registration successful: {message}")
        else:
            print(f"Registration failed: {message}")
    """
    try:
        # Prepare and send registration request
        response = requests.post(
            f"{API_BASE_URL}/users/register",
            json={"username": username, "password": password, "email": email}
        )
        
        # Handle API response, check for successful registration (HTTP 201 Created)   
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
    if 'show_chat' not in st.session_state:
        st.session_state.show_chat = False
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Check if we should show chat or login
    query_params = st.query_params
    
    # If user is trying to access chat but not logged in, redirect to login
    if query_params.get("page") == ["chat"] and not st.session_state.get('logged_in'):
        st.query_params.clear()
        st.rerun()
        return
        
    # If user is logged in, show chat
    if query_params.get("page") == ["chat"] or st.session_state.get('logged_in'):
        from bridge_ui.chatUI import chat_page
        chat_page()
    # If user is logging out
    elif query_params.get("page") == ["login"]:
        login_page()
    # Show signup page if that's what was requested
    elif st.session_state.get('show_signup'):
        signup_page()
    # Default to login page
    else:
        login_page()

if __name__ == "__main__":
    main()