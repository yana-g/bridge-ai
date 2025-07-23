# BRIDGE Web Interface

This directory contains the Streamlit-based web interface for the BRIDGE LLM Routing System. The UI provides an interactive way for users to interact with the LLM routing system through a modern, responsive web interface.

## Directory Structure

```
ui/
├── chat/               # Chat interface components
│   ├── __init__.py
│   └── chat_interface.py  # Main chat interface implementation
├── dashboard/          # Analytics and monitoring dashboard
│   └── ...
├── static/             # Static assets (images, CSS, JS)
│   └── ...
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

3. **Configuration**
   Create a `.env` file in the UI directory with the following variables:
   ```
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

## Running the Application

```bash
# Start the Streamlit app
streamlit run app.py
```

The application will be available at `http://localhost:8501` by default.

## Development

### Adding New Features

1. **Chat Extensions**
   - Add new chat components to the `chat/` directory
   - Register new components in `chat/__init__.py`

2. **Dashboard Widgets**
   - Add new dashboard components to the `dashboard/` directory
   - Update the main dashboard view to include new widgets

### Testing

Run the test suite:
```bash
pytest tests/
```

## Deployment

The UI can be deployed using any Streamlit-compatible hosting service, such as:
- Streamlit Cloud
- Heroku
- AWS App Runner
- Google Cloud Run

## Troubleshooting

- **Connection Issues**: Ensure the BRIDGE API server is running and accessible
- **Authentication Errors**: Verify API keys and authentication configuration
- **UI Rendering Problems**: Clear browser cache or try a different browser

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.
