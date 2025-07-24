# 🌐 BRIDGE AI- Intelligent LLM Routing System

An advanced AI routing system that intelligently directs user queries to the most appropriate language model based on complexity, context, and quality requirements.

---

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

1. **LLM Bridge** (llm_bridge/)
   - bridge.py: Orchestrates the entire query processing pipeline
   - llm_router.py: Routes queries to appropriate LLM models
   - prompt_analyzer.py: Analyzes prompt complexity and requirements
   - answer_evaluator.py: Assesses response quality and suggests improvements
   - cache_manager.py: Manages both exact and semantic caching

2. **API Layer** (api/)
   - FastAPI-based RESTful API
   - JWT authentication
   - Request validation and logging middleware
   - User management endpoints

3. **Data Layer** (data_layer/)
   - MongoDB integration with connection pooling
   - Semantic search capabilities
   - User and conversation history storage

4. **User Interface** (ui/)
   - Streamlit-based web interface
   - Responsive design for various devices
   - Real-time chat interface

# 📚 Project Specification
This spec document fully describes a smart query routing system between language models.
It is designed so an LLM agent can recreate the architecture and logic end-to-end.

---

## 🔧 Purpose

Build an intelligent router between multiple LLMs that:

- Accepts a user query via UI or API
- Detects the prompt's intent and language
- Logs every prompt and response to MongoDB
- Chooses the best model based on rules or confidence
- Returns structured response with `[CONFIDENCE:X.XX]` tag
- Supports dashboard, token tracking, vibe selection, and caching

---

## 📁 Folder Structure (to be generated)

BRIDGE/
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
├── bridge_ui/
│   ├── static/
│   ├── chatUI.py
│   ├── loginUI.py
│   └── __init__.py
│
├── TVManualAgent/         # TV Manual Agent    
│   ├── Data/              # PDF files
│   ├── llm_load.py        # LLM loading
│   ├── pdf_load.py        # PDF loading
│   └── main.py            # Main app
│
├── README.md              # Project documentation
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
└── PROJECT_SPEC.md        # This document  

## ⚙️ .env Template
```env
OPENAI_API_KEY=sk-...
LLM1_URL=http://localhost:5000/
MONGO_URI=mongodb+srv://bridge-user:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority
MONGO_DB_NAME=bridgeDB

## 🔄 Backend API Flow
### Route: POST /ask-llm/
### Input JSON:

{
  "prompt": "Explain PCA in simple terms.",
  "vibe": "Professional",
  "username": "Yana"
}
```
Steps:
1. main.py receives POST → sends to LLMRouter

2. LLMRouter:

1. Detects language (reject non-English)
2. Runs detect_intent() if needed
3. Chooses LLM1 (local) or LLM2 (OpenAI)

### llm_bridge.py sends query to selected LLM

### Appends [CONFIDENCE:X.XX] tag to output

### utils.py parses confidence

### mongo_handler.py logs:

1. Prompt
2. Model used
3. Confidence
4. Token counts
5. Embeddings

### API returns JSON response with metadata

### Output JSON:

{
  "response": "PCA reduces dimensionality by projecting data into fewer components. [CONFIDENCE:0.89]",
  "model_metadata": {
    "llm_used": "GPT-3.5",
    "confidence": 0.89,
    "from_cache": false,
    "simple_intent": "explanation",
    "tokens": {
      "prompt": 12,
      "completion": 26,
      "total": 38
    }
  }
}```    

## 🖥️ UI Flow (Streamlit)
### Main file: ui/app.py

1. User sees:
    * Fixed top header
    * Scrollable chat area
    * Bottom-pinned text input
    * Vibe dropdown
    * Sends message via st.form

2. Display logic:
    * User messages styled with .chat-message.user-message
    * AI responses styled with .chat-message.bot-message
    * Confidence shown as % in faded label
    * Session state tracks history

## 🧠 LLM Router Logic
### def route_prompt(prompt):
    if not prompt:
        return "No prompt provided", None

    lang = detect_language(prompt)  # e.g. "en"
    if lang != "en":
        return "English only supported", None

    if is_simple_question(prompt):
        return LLM1_response(prompt)
    else:
        return LLM2_response(prompt)

## 💾 MongoDB Schema (chat_logs)
### Each log in chat_logs collection includes:

```json
{
  "username": "Yana",
  "prompt": "Explain PCA",
  "response": "PCA reduces data...",
  "llm_used": "GPT-4",
  "confidence": 0.92,
  "vibe": "Professional",
  "tokens": {
    "prompt": 9,
    "completion": 24,
    "total": 33
  },
  "timestamp": "2025-07-23T11:32Z",
  "embedding": [0.123, 0.221, ...],
  "from_cache": false,
  "simple_intent": "explanation"
}
```

## 🧪 Model Routing Rules
Rule	                  |Outcome
--------------------------|-----------------------
Prompt in Hebrew	      |Reject prompt
Contains greeting only    |LLM1
Short technical Qs        |LLM1
Complex or vague intent   |LLM2 or LLM3
Confidence below 0.5      |Reroute to LLM3 (TODO)
Existing embedding found  |Use cache

## 📊 Metrics Tracked 
1. LLM usage frequency
2. Token consumption (per user + model)
3. Confidence distribution
4. Vibe usage
5. Cache hit ratio

## 🛠️ Rebuild Instructions (for AI Agent)
1. Create folders: app, ui
2. Implement API:
    a. FastAPI
    b. Single route: /ask-llm/
3. Implement modules:
    a. LLMRouter (logic-based routing)
    b. llm_bridge.py (model calls)
    c. mongo_handler.py (data persistence)
4. Connect to OpenAI via openai.ChatCompletion.create()
5. Create .env and load via config.py
6. Build Streamlit UI:
    a. Chat section
    b. Bottom input
    c. Tabs for logs and metrics
7. Inject CSS for layout
8. Add logging to MongoDB
9. Support embedding storage (OpenAI / SentenceTransformer)
10. Token counting with tiktoken
11. Use regex to extract [CONFIDENCE:0.XX]
12. Ensure fallback to LLM3 if confidence < threshold (optional)

##✅ Final Notes
* The system must be able to simulate confidence, log user interactions, and adapt routing dynamically.
* All prompts are English-only at this stage.
* Security: use .env and never expose secrets
* Streamlit layout mimics ChatGPT with pinned footer and scrollable chat




