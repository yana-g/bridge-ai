# 🌉 BRIDGE - Intelligent LLM Routing System v2.2

> An advanced AI routing system that intelligently directs user queries to the most appropriate language model based on complexity, context, and quality requirements.

## 🚀 Key Features

- **Smart Model Routing**: Dynamically routes queries to optimal LLMs (GPT-3.5, GPT-4, etc.) based on complexity, context, and quality requirements.
- **Quality Assessment**: Continuously evaluates response quality and can upgrade to more capable models when needed.
- **Context-Aware Processing**: Supports multiple conversation styles (Academic, Business, Technical, etc.) with specialized handling for each.
- **Semantic Caching**: Reduces API calls and improves response times through intelligent caching of similar queries.
- **Modular Architecture**: Clean separation of concerns with distinct components for API, LLM routing, and data persistence.
- **Secure Authentication**: JWT-based API key authentication with secure credential handling.
- **Extensible Design**: Easy to add new LLM providers, analysis modules, or storage backends.

## 🏗 System Architecture

### Core Components

1. **LLM Bridge** (`llm_bridge/`)
   - `bridge.py`: Orchestrates the entire query processing pipeline
   - `llm_router.py`: Routes queries to appropriate LLM models
   - `prompt_analyzer.py`: Analyzes prompt complexity and requirements
   - `answer_evaluator.py`: Assesses response quality and suggests improvements
   - `cache_manager.py`: Manages both exact and semantic caching

2. **API Layer** (`api/`)
   - FastAPI-based RESTful API
   - JWT authentication
   - Request validation and logging middleware
   - User management endpoints

3. **Data Layer** (`data_layer/`)
   - MongoDB integration with connection pooling
   - Semantic search capabilities
   - User and conversation history storage

4. **User Interface** (`ui/`)
   - Streamlit-based web interface
   - Responsive design for various devices
   - Real-time chat interface

## 🛠 Installation & Setup

### Prerequisites
- Python 3.8+
- MongoDB instance (local or cloud)
- OpenAI API key

### Quick Start

1. **Clone and set up the repository**
   ```bash
   git clone https://github.com/yourusername/bridge-ai.git
   cd BRIDGE
   
   # Create and activate virtual environment
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   source venv/bin/activate   # macOS/Linux
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Configure environment variables**
   Create a `.env` file with required settings:
   ```env
   # Required
   OPENAI_API_KEY=your_openai_api_key
   MONGODB_URI=mongodb://localhost:27017/bridge
   SECRET_KEY=your_secure_secret_key
   
   # Optional
   CACHE_TTL=86400  # 24 hours
   LOG_LEVEL=INFO
   ```

## 🚀 Running the Application

### Start the API Server
```bash
export PYTHONPATH=$PWD
python -m api.entry_point_api
```

### Start the Web UI
```bash
streamlit run ui/loginUI.py
```

## 📚 Project Structure

```
BRIDGE_v2.2/
├── api/                    # API implementation
│   ├── __init__.py
│   ├── entry_point_api.py  # Main API endpoints
│   ├── authHandler.py      # Authentication logic
│   ├── userHandler.py      # User management
│   └── middleware/         # Request processing middleware
│
├── llm_bridge/            # Core routing logic
│   ├── __init__.py
│   ├── bridge.py          # Main orchestrator
│   ├── llm_router.py      # Model routing
│   ├── prompt_analyzer.py # Prompt analysis
│   ├── answer_evaluator.py # Response evaluation
│   ├── cache_manager.py   # Caching system
│   └── output_manager.py  # Response formatting
│
├── data_layer/            # Data persistence
│   ├── __init__.py
│   ├── mongoHandler.py    # MongoDB operations
│   └── models/            # Data models
│
├── ui/                    # Web interface
│   ├── loginUI.py         # Authentication UI
│   ├── chatUI.py          # Chat interface
│   └── static/            # Frontend assets
│
├── tests/                 # Test suite
├── .env.example          # Example environment config
└── requirements.txt      # Python dependencies
```

## 🔍 API Documentation

### Authentication
All API endpoints (except `/health`) require authentication via API key in the `X-API-Key` header.

### Available Endpoints

#### Health Check
- `GET /health`
  - Verify API status and database connectivity
  - No authentication required

#### User Management
- `POST /register`
  - Register a new user account
  - Returns: API key for authentication

- `POST /login`
  - Authenticate and receive API key
  - Returns: API key for authentication

#### LLM Interaction
- `POST /ask-llm`
  - Process a natural language query
  - Required fields:
    ```json
    {
      "vibe": "Academic/Research",
      "sender_id": "user123",
      "question": "Explain quantum computing",
      "confidence": true,
      "nature_of_answer": "Detailed"
    }
    ```
  - Returns: 
    ```json
    {
      "response": "Detailed explanation...",
      "vibe_used": "Academic/Research",
      "question_id": "abc123",
      "model_metadata": {
        "model_used": "gpt-4",
        "processing_time": 1.23,
        "cache_hit": false
      },
      "follow_up_questions": ["What are qubits?", "How does quantum entanglement work?"],
      "needs_more_info": false
    }
    ```

## 🤖 Supported Vibe Modes

| Vibe | Description | Best For |
|------|-------------|----------|
| **Academic/Research** | Detailed, citation-heavy responses | Research papers, academic work |
| **Business/Professional** | Formal, strategic business language | Business communications, reports |
| **Technical/Development** | Code-focused explanations | Software development, technical docs |
| **Daily/General** | Casual, conversational tone | Everyday questions, general chat |
| **Creative/Emotional** | Expressive, empathetic responses | Creative writing, emotional support |

## 🧪 Testing

Run the test suite:
```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run specific test file
pytest tests/test_llm_bridge.py -v
```

## 🛡️ Security Considerations

- All API keys are stored securely using environment variables
- Passwords are hashed using bcrypt before storage
- JWT tokens are used for authenticated sessions
- Input validation is performed on all API endpoints
- CORS is enabled with appropriate security headers

## 📈 Performance

- Response times typically under 2 seconds for most queries
- Semantic caching reduces duplicate API calls
- Connection pooling for database operations
- Asynchronous processing for non-blocking I/O

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with ❤️ using FastAPI and Streamlit
- Powered by OpenAI's GPT models
- Data persistence with MongoDB
- Semantic search with Sentence Transformers
- Icons by Feather Icons