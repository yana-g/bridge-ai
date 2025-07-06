# 🌉 BRIDGE - Intelligent LLM Routing System

> An advanced AI routing system that intelligently directs user queries to the most appropriate language model based on complexity, context, and quality requirements.

## 🚀 Features

- **Smart Model Routing**: Automatically routes queries to the most suitable LLM (GPT-3.5, GPT-4, etc.) based on complexity and context.
- **Quality Assessment**: Evaluates response quality and can upgrade to more capable models when needed.
- **Context-Aware**: Supports multiple conversation styles (Academic, Business, Technical, etc.).
- **User Authentication**: Secure API key-based authentication system.
- **Modern Web Interface**: Streamlit-based UI for easy interaction.
- **Semantic Caching**: Reduces API calls by caching similar queries.

## 🛠 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/bridge-ai.git
   cd BRIDGE
   ```

2. **Set up a virtual environment** (recommended)
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # On Windows
   source venv/bin/activate  # On macOS/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the project root with the following variables:
   ```env
   OPENAI_API_KEY=your_openai_api_key
   MONGODB_URI=your_mongodb_connection_string
   SECRET_KEY=your_secret_key_for_jwt
   ```

## 🏃‍♂️ Running the Application

### 1. Start the API Server
```bash
# In terminal 1
cd BRIDGE
set PYTHONPATH=%CD%
python -m api.entry_point_api
```

The API will be available at `http://localhost:8000`

### 2. Start the Web UI (Optional)
```bash
# In terminal 2
cd BRIDGE
set PYTHONPATH=%CD%
streamlit run ui/loginUI.py
```

The UI will be available at `http://localhost:8501`

## 📚 Project Structure

```
BRIDGE/
├── api/                   # FastAPI backend
│   ├── entry_point_api.py # Main API endpoints
│   ├── userHandler.py     # User management
│   └── authHandler.py     # Authentication logic
├── llm_bridge/           # Core LLM routing logic
│   ├── bridge.py         # Main routing logic
│   ├── prompt_analyzer.py # Analyzes prompt complexity
│   ├── llm_router.py     # Routes to appropriate LLM
│   └── answer_evaluator.py # Evaluates response quality
├── ui/                   # Streamlit web interface
│   ├── loginUI.py        # Login/signup interface
│   └── chatUI.py         # Main chat interface
├── data_layer/           # Database interactions
├── tests/                # Test suite
├── .env                 # Environment variables
└── requirements.txt     # Project dependencies
```

## 🔍 API Endpoints

### Authentication
- `POST /register` - Register a new user
- `POST /login` - Get an API key

### Core Functionality
- `POST /ask-llm` - Send a question to the LLM
- `GET /health` - Check API status

### Example Request
```bash
curl -X POST "http://localhost:8000/ask-llm" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "vibe": "Academic/Research",
    "sender_id": "user123",
    "question": "Explain quantum computing",
    "confidence": true,
    "nature_of_answer": "Detailed"
  }'
```

## 🤖 Supported Vibe Modes

- **Academic/Research**: For detailed, citation-heavy responses
- **Business/Professional**: Formal and strategic business advice
- **Technical/Development**: Code-focused, technical explanations
- **Daily/General**: Casual, everyday conversation
- **Creative/Emotional**: Expressive and empathetic responses

## 🧪 Running Tests

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run tests
pytest
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with FastAPI and Streamlit
- Uses OpenAI's GPT models for language processing
- MongoDB for data persistence