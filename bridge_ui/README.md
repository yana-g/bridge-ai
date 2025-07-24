# BRIDGE Web Interface

This directory contains the Streamlit-based web interface for the BRIDGE LLM Routing System. The UI provides an interactive way for users to interact with the LLM routing system through a modern, responsive web interface.

## Directory Structure

```
bridge_ui/
├── chatUI.py           # Main chat interface implementation
├── loginUI.py          # User authentication interface
├── static/             # Static assets (CSS, JS, images)
│   └── styles.css      # Custom styles
└── README.md           # This file
```

## Features

1. **Interactive Chat Interface**
   - Real-time conversation with the LLM
   - Support for different conversation styles (vibes)
   - Message history and context management

2. **User Authentication**
   - Secure login/logout functionality
   - API key management
   - User profile management

3. **Dashboard**
   - Usage statistics and analytics
   - Model performance metrics
   - System health monitoring

## Setup and Installation

1. **Prerequisites**
   - Python 3.8+
   - Streamlit
   - BRIDGE API server (must be running)

2. **Installation**
   ```bash
   # Install required packages
   pip install -r requirements.txt
   
   # Set up environment variables
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Running the Application**
   ```bash
   # Start the login interface
   streamlit run loginUI.py
   
   # Or start the chat interface directly (if already authenticated)
   streamlit run chatUI.py
   ```

## Configuration

Update the `.env` file with your configuration:

```env
# API Configuration
API_BASE_URL=http://localhost:8000

# Authentication
REQUIRE_AUTH=true

# UI Settings
PAGE_TITLE="BRIDGE LLM Interface"
PAGE_ICON="🤖"

# Optional: Custom CSS
CUSTOM_CSS=""
```

## Development

### Running the Application

1. Start the BRIDGE API server first
2. In a new terminal, navigate to the `bridge_ui` directory
3. Run `streamlit run loginUI.py`

### Making Changes

- The main application logic is in `chatUI.py`
- Authentication flow is handled in `loginUI.py`
- Custom styles can be modified in `static/styles.css`

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.
