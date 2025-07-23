# BRIDGE - User Interface

This directory contains the Streamlit-based user interface for the BRIDGE application, providing a modern and interactive web interface for users to interact with the BRIDGE system.

## Directory Structure

```
ui/
├── chat/                  # Chat interface components
│   ├── chatUI.py         # Main chat interface implementation
│   └── loginUI.py        # User authentication interface
├── dashboard/            # Analytics and monitoring dashboard (future)
├── static/               # Static assets
│   └── styles.css        # Global CSS styles
└── README.md             # This file
```

## Features

### Authentication
- User login with username/password
- New user registration
- Session management
- API key handling

### Chat Interface
- Real-time chat with the BRIDGE system
- Message history
- User preferences and settings

### Dashboard (Planned)
- Usage analytics
- System monitoring
- User management

## Prerequisites

- Python 3.8+
- Streamlit
- Required Python packages (see `requirements.txt` in the root directory)

## Setup and Running

1. Install dependencies:
   ```bash
   pip install -r ../requirements.txt
   ```

2. Start the UI server:
   ```bash
   streamlit run chat/loginUI.py
   ```

3. Access the application in your browser at `http://localhost:8501`

## Environment Variables

The following environment variables should be set in a `.env` file in the root directory:

```
API_BASE_URL=http://localhost:8000  # URL of the BRIDGE API server
```

## Development

### Running in Development Mode

For development with hot-reloading:

```bash
streamlit run chat/loginUI.py --server.runOnSave=true
```

### Testing

Run UI tests (if available):

```bash
pytest tests/
```

### Code Style

Follow PEP 8 guidelines. Use `black` for code formatting:

```bash
black .
```

## Deployment

For production deployment, consider using:
- Streamlit Cloud
- Docker containerization
- Reverse proxy (Nginx/Apache)

## Troubleshooting

- **Login issues**: Ensure the API server is running and accessible at the URL specified in `API_BASE_URL`
- **Styling problems**: Check browser console for CSS loading errors
- **Connection errors**: Verify network connectivity and CORS settings on the API server

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.
