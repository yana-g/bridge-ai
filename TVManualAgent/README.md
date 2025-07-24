# 📺 TV Manual Agent

A smart assistant that answers user questions based on TV manuals.  
Combines **semantic search** from user-uploaded PDFs with **LLM reasoning**, using either a local model or a remote BRIDGE API fallback.

## 🧠 What It Does

- Accepts **TV manual PDFs** via local folder
- Answers natural-language queries (e.g., "How do I connect HDMI?")
- Prioritizes fast semantic lookup from embedded manuals
- Falls back to LLM Bridge when PDF data is insufficient
- Presents clean chat-like interface with source info and suggestions

## 🧱 Architecture

TVManualAgent/
│
├── main.py                     # Streamlit frontend logic
├── llm_load.py                 # Load local open-source LLMs (e.g., DialoGPT, Llama-2)
├── api_client.py               # Client for querying remote BRIDGE API
├── pdf_load.py                 # PDF parsing, embedding, indexing with FAISS
├── test_bridge_connection.py   # Quick connectivity tester for BRIDGE API
└── 📁 Data/                    # Folder containing user-uploaded TV manuals in PDF

## ⚙️ Features

### 🔍 Hybrid QA Pipeline
1. **PDF Embedding Search**: Via FAISS + MiniLM
2. **Fallback to LLM API**: Via `/ask-llm/` if no confident match
3. **Structured Response Rendering**: Markdown + follow-up suggestions

### 📄 PDF Processing
- Extracts text from `.pdf` using `PyPDF2`
- Chunks into 500-word segments with 50-word overlap
- Embeds via `all-MiniLM-L6-v2` (SentenceTransformers)
- Indexes with FAISS (`faiss-cpu` or `faiss-gpu`)

### 🤖 LLM Support
- Load HuggingFace models like:
  - `DialoGPT`, `GPT2`, `Llama-2-7b-chat-hf` (with token)
- Customize via HuggingFace token input
- Auto format prompt per model

### 🔗 BRIDGE API Fallback
- Calls `/ask-llm/` endpoint with:
  - `question`, `vibe`, `confidence`, `sender_id`
- Auth via `x-api-key`
- Returns structured JSON with answer + follow-up questions

## 📁 Current Manuals (Sample)

| File Name   | Description         | Size   |
|-------------|---------------------|--------|
| jvc.pdf     | JVC TV Manual       | 1.9 MB |
| smart.pdf   | Smart TV Guide      | 7.1 MB |
| tcl.pdf     | TCL TV Manual       | 1.3 MB |

To add more, simply drop new `.pdf` files into `/Data`.

## 🧪 Example Use Cases

| Question                          | Behavior |
|-----------------------------------|----------|
| “How do I set parental controls?” | Searches manual PDFs |
| No match found                    | Escalates to BRIDGE |
| Bridge returns follow-up          | Chat UI renders it |
| Want source context?              | Expand original PDF chunk view |

## 🚀 How It Works (Pipeline)

1. **Extract Text** → from PDFs using PyPDF2
2. **Chunk Content** → into overlapping 500-word segments
3. **Create Embeddings** → using Sentence Transformers
4. **Build FAISS Index** → enables semantic search
5. **Answer Query** → via model or BRIDGE fallback

## 🔧 Setup Instructions

### Setup checklist:
1. Make sure you have created a 'Data' folder in your project directory
2. Add your TV manual PDF files to the 'Data' folder
3. Install dependencies: `pip install -r requirements.txt`
4. Run the command above in VSCode terminal

### Troubleshooting:
- If streamlit is not recognized, try: `pip install streamlit`
- If you get permission errors, run VSCode as administrator
- For first-time model download, ensure good internet connection (13GB download)

### Before running the app make sure you have:
1. BRIDGE_v2 app API running
2. BRIDGE_v2 app API is accessible via `http://localhost:8000`

### Method 1: Direct command
```bash
streamlit run TVManualAgent/main.py
```

### Method 2: Using Python module
```bash
python -m streamlit run TVManualAgent/main.py
```

### 💬 Example Prompts
- “Where is the HDMI port?”
- “How to update firmware?”
- “Why is the screen blurry?”
- “How do I reset factory settings?”

### 📎 Related Projects
-  🔗 BRIDGE API: The LLM fallback system

