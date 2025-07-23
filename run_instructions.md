# run_instructions.md
# Running BRIDGE from VSCode Terminal

## Virtual Environment:
```bash
python -m venv .venv
.\.venv\Scripts\activate 
```

## Install dependences:
```bash
pip install -r requirements.txt
```

## Run API: 
```bash
uvicorn api.entry_point_api:app --reload --port 8000
or Python -m uvicorn...
```

## Run UI:
```bash
streamlit run ui/chat/loginUI.py
```
