# main.py
import streamlit as st
import os
from dotenv import load_dotenv
from llm_load import LlamaModel
from pdf_load import PDFProcessor
from api_client import APIClient

# Load environment variables
load_dotenv()

def main():
    st.set_page_config(
        page_title="TV Manual Agent",
        page_icon="📺",
        layout="wide"
    )
    
    st.title("📺 TV Manual Agent")
    st.markdown("Ask questions about your TV manuals and get instant answers!")
    
    # Initialize session state
    if 'llm_model' not in st.session_state:
        st.session_state.llm_model = LlamaModel()
    
    if 'pdf_processor' not in st.session_state:
        st.session_state.pdf_processor = PDFProcessor()
    
    # Initialize other session state variables
    if 'model_loaded' not in st.session_state:
        st.session_state.model_loaded = False
    
    if 'pdfs_processed' not in st.session_state:
        st.session_state.pdfs_processed = False
        
    if 'hf_token' not in st.session_state:
        st.session_state.hf_token = ""
    
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = None
    
    if 'api_initialized' not in st.session_state:
        st.session_state.api_initialized = False
    
    # Initialize API client
    if 'api_client' not in st.session_state:
        try:
            api_key = os.getenv("API_KEY")
            base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
            
            if not api_key:
                st.error("API key not found. Please set the API_KEY in your .env file.")
                st.stop()
                
            st.session_state.api_client = APIClient(
                base_url=base_url,
                api_key=api_key
            )
            
            # Test the connection
            health = st.session_state.api_client.check_health()
            if health.get("status") != "healthy":
                st.error(f"Failed to connect to BRIDGE API: {health.get('error', 'Unknown error')}")
                st.stop()
                
            st.session_state.api_initialized = True
            
        except Exception as e:
            st.error(f"Failed to initialize API client: {str(e)}")
            st.session_state.api_initialized = False
    
    # Sidebar for setup
    with st.sidebar:
        st.header("Setup")
        
        # API Status
        st.subheader("🔗 API Connection")
        try:
            # Test API connection
            health = st.session_state.api_client.check_health()
            if health.get("status") == "healthy":
                st.success("✅ Connected to LLM Bridge API")
            else:
                st.error("❌ API Connection Failed")
        except:
            st.error("❌ Cannot reach API")

        st.divider()

        # Model selection and loading section
        st.subheader("1. Select & Load Language Model")
        
        # HuggingFace token input (optional)
        with st.expander("🔑 Use Llama-2 (Optional - Requires HF Token)"):
            hf_token = st.text_input(
                "HuggingFace Token:", 
                value=st.session_state.hf_token,
                type="password",
                help="Get your token from https://huggingface.co/settings/tokens"
            )
            if hf_token and hf_token != st.session_state.hf_token:
                st.session_state.hf_token = hf_token
                st.rerun()
            if st.session_state.hf_token:
                st.info("Will try to load Llama-2-7b-chat-hf with your token")
        
        # Model selection for open models
        st.write("**Select Open Model:**")
        selected_model_name = st.selectbox(
            "Choose model:",
            [model["display_name"] for model in st.session_state.llm_model.available_models],
            index=0
        )
        
        # Find selected model info
        selected_model = next(
            model for model in st.session_state.llm_model.available_models 
            if model["display_name"] == selected_model_name
        )
        
        # Load model button
        if st.button("Load Selected Model"):
            st.session_state.model_loaded = st.session_state.llm_model.load_model(
                selected_model=selected_model,
                hf_token=st.session_state.hf_token if st.session_state.hf_token else None
            )
        
        # Model status
        if st.session_state.model_loaded:
            current_model = st.session_state.llm_model.model_name
            st.success(f"✅ Loaded: {current_model}")
        else:
            st.warning("⚠️ No model loaded")
        
        st.divider()
        
        # PDF processing section
        st.subheader("2. Process PDF Files")
        st.info("Place your TV manual PDF files in the 'Data' folder")
        
        if st.button("Load & Process PDFs"):
            if st.session_state.pdf_processor.load_embedding_model():
                if st.session_state.pdf_processor.load_pdfs():
                    if st.session_state.pdf_processor.create_embeddings():
                        st.session_state.pdfs_processed = True
                        st.session_state.pdf_processor.save_index()
        
        # Try to load existing index
        if not st.session_state.pdfs_processed:
            if st.session_state.pdf_processor.load_embedding_model():
                if st.session_state.pdf_processor.load_index():
                    st.session_state.pdfs_processed = True
                    st.success("✅ Loaded existing index")
        
        if st.session_state.pdfs_processed:
            st.success("✅ PDFs processed")
            st.info(f"Loaded {len(st.session_state.pdf_processor.documents)} text chunks")
        else:
            st.warning("⚠️ PDFs not processed")
    
    # Main chat interface
    st.subheader("Ask a Question")
    
    # Initialize chat history if it doesn't exist
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "How can I help you with your TV manual today?"}
        ]
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            content = message["content"]
            
            # Check if it's a structured message with follow-up questions
            if isinstance(content, dict):
                # Display the main response
                st.markdown(content.get("response", ""))
                
                # Display follow-up questions if any
                follow_ups = content.get("follow_up_questions", [])
                if follow_ups and isinstance(follow_ups, list):
                    st.markdown("\n**To help me provide a better answer, could you clarify:**")
                    for question in follow_ups:
                        st.markdown(f"- {question}")
            else:
                # Regular text message
                st.markdown(content)
    
    # Chat input
    if prompt := st.text_input("Enter your question about the TV manual:", 
                             placeholder="e.g., How do I change the channel?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display assistant response
        with st.spinner("Searching for answer..."):
            # Search for relevant documents
            relevant_docs = st.session_state.pdf_processor.search_similar_documents(
                prompt, k=3
            )
            
            if not relevant_docs:
                # No relevant docs found - ask the bridge
                st.warning("🔍 No relevant information found in TV manuals. Asking LLM Bridge...")
                
                try:
                    # Get response from BRIDGE API
                    response = st.session_state.api_client.ask_bridge(prompt)
                    print("DEBUG: Bridge API response:", response)

                    if response.get("success", True):
                        # Store the full response in the message
                        message_content = {
                            "response": response.get("response", "No response received."),
                            "follow_up_questions": response.get("follow_up_questions", [])
                        }
                        
                        # Display the main response
                        st.subheader("Answer from LLM Bridge:")
                        main_answer = message_content["response"]
                        follow_ups = message_content["follow_up_questions"]
                        if follow_ups:
                            followup_md = "\n\n**To help me provide a better answer, could you clarify:**\n" + "\n".join([f"- {q}" for q in follow_ups])
                            main_answer += followup_md
                        st.markdown(main_answer)
                        
                        # Store the structured response in chat history
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": message_content
                        })
                        
                    else:
                        error_msg = f"Error: {response.get('error', 'Unknown error')}"
                        st.error(error_msg)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_msg
                        })
                        
                except Exception as e:
                    error_msg = f"An error occurred: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                
                return
            
            # Prepare context for LLM
            context = "\n\n".join([doc['text'] for doc in relevant_docs])
            
            # Create prompt for LLM
            llm_prompt = f"""Based on the following TV manual information, answer the user's question. If the information is not sufficient to answer the question, respond with "I should ask BRIDGE".

Context from TV manuals:
{context}

Question: {prompt}

Answer:"""
            
            # Generate response
            response = st.session_state.llm_model.generate_response(llm_prompt)
            
            # Check if model suggests asking the bridge
            if "I should ask BRIDGE" in response or "ask BRIDGE" in response.lower():
                st.warning("🔍 TV manual information insufficient. Asking LLM Bridge...")
                
                try:
                    # Get response from BRIDGE API
                    response = st.session_state.api_client.ask_bridge(prompt)
                    
                    if response.get("success", True):
                        # Store the full response in the message
                        message_content = {
                            "response": response.get("response", "No response received."),
                            "follow_up_questions": response.get("follow_up_questions", [])
                        }
                        
                        # Display the main response
                        st.subheader("Answer from LLM Bridge:")
                        main_answer = message_content["response"]
                        follow_ups = message_content["follow_up_questions"]
                        if follow_ups:
                            followup_md = "\n\n**To help me provide a better answer, could you clarify:**\n" + "\n".join([f"- {q}" for q in follow_ups])
                            main_answer += followup_md
                        st.markdown(main_answer)
                        
                        # Store the structured response in chat history
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": message_content
                        })
                        
                    else:
                        error_msg = f"Error: {response.get('error', 'Unknown error')}"
                        st.error(error_msg)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_msg
                        })
                        
                except Exception as e:
                    error_msg = f"An error occurred: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
            else:
                # Display regular TV manual response
                st.subheader("Answer from TV Manual:")
                st.markdown(response)
                
                # Store the simple response in chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response
                })
                
                # Show source documents
                with st.expander("View Source Documents"):
                    for i, doc in enumerate(relevant_docs):
                        st.write(f"**Source {i+1}:** {doc['source']}")
                        st.write(f"**Similarity Score:** {doc['similarity_score']:.4f}")
                        st.write(f"**Text:** {doc['text'][:300]}...")
                        st.divider()
                
if __name__ == "__main__":
    main()