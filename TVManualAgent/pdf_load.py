"""
PDF Processing Module for TV Manual Agent

This module handles the loading, processing, and searching of TV manual PDFs.
It extracts text from PDFs, creates vector embeddings, and enables semantic search
functionality using FAISS for efficient similarity search.

Key Features:
- PDF text extraction with PyPDF2
- Text chunking with configurable size and overlap
- Vector embeddings using Sentence Transformers
- FAISS-based similarity search
- Persistent index storage and loading

Dependencies:
    PyPDF2: For PDF text extraction
    sentence-transformers: For creating text embeddings
    faiss-cpu/faiss-gpu: For efficient similarity search
    numpy: For numerical operations
    streamlit: For UI components and progress tracking
"""

import os
import PyPDF2
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import streamlit as st
import pickle

class PDFProcessor:
    """
    Handles the processing and searching of PDF documents.
    
    This class provides functionality to load PDFs, extract text, create vector
    embeddings, and perform similarity searches across the document collection.
    
    Attributes:
        documents (list): List of processed document chunks with metadata
        embeddings (numpy.ndarray): Vector embeddings of document chunks
        index (faiss.Index): FAISS index for similarity search
        embedding_model (SentenceTransformer): Model for generating embeddings
        data_folder (str): Directory containing PDF files (default: "Data")
    """
    
    def __init__(self):
        """
        Initialize the PDF processor with default settings
        
        Initializes an instance of the PDFProcessor class with default values.
        Sets up empty lists for documents and embeddings, and initializes other attributes.
        """
        self.documents = []
        self.embeddings = None
        self.index = None
        self.embedding_model = None
        # Use absolute path for the Data folder
        self.data_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Data")
        print(f"PDFProcessor initialized. Data folder path: {self.data_folder}")
        
        # Create Data folder if it doesn't exist
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            print(f"Created Data folder at: {self.data_folder}")
        
    def load_embedding_model(self):
        """ 
        Load the sentence transformer model for generating embeddings.
        
        Returns:
            bool: True if the model was loaded successfully, False otherwise
            
        Displays:
            - Loading spinner while the model is being loaded
            - Success/error message in the Streamlit interface
        """
        try:
            with st.spinner("Loading embedding model..."):
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            st.success("Embedding model loaded!")
            return True
        except Exception as e:
            st.error(f"Error loading embedding model: {str(e)}")
            return False
    
    def extract_text_from_pdf(self, pdf_path):
        """
        Extract text content from a PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            str: Extracted text content, or empty string on error
            
        Displays:
            - Error message if the PDF cannot be read
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            st.error(f"Error reading PDF {pdf_path}: {str(e)}")
            return ""
    
    def chunk_text(self, text, chunk_size=500, overlap=50):
        """
        Split text into overlapping chunks for better retrieval.
        
        Args:
            text (str): Input text to be chunked
            chunk_size (int): Number of words per chunk (default: 500)
            overlap (int): Number of words to overlap between chunks (default: 50)
            
        Returns:
            list: List of text chunks
        """
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)
            
        return chunks
    
    def load_pdfs(self):
        """Load and process all PDF files from the data folder.
        
        Returns:
            bool: True if PDFs were loaded successfully, False otherwise
            
        Displays:
            - Warning if no PDFs are found
            - Progress spinner while processing PDFs
            - Success message with processing summary
        """
        print(f"Looking for PDFs in: {self.data_folder}")
        
        if not os.path.exists(self.data_folder):
            error_msg = f"Data folder does not exist: {self.data_folder}"
            print(error_msg)
            st.error(error_msg)
            return False
        
        # List all files in the directory
        try:
            all_files = os.listdir(self.data_folder)
            print(f"All files in directory: {all_files}")
            
            # Filter for PDF files (case insensitive)
            pdf_files = [f for f in all_files if f.lower().endswith('.pdf')]
            print(f"Found PDF files: {pdf_files}")
            
            if not pdf_files:
                error_msg = f"No PDF files found in {self.data_folder}. Files present: {all_files}"
                print(error_msg)
                st.warning(error_msg)
                return False
            
            self.documents = []
            
            with st.spinner(f"Processing {len(pdf_files)} PDF files..."):
                for pdf_file in pdf_files:
                    pdf_path = os.path.join(self.data_folder, pdf_file)
                    print(f"Processing file: {pdf_path}")
                    
                    try:
                        text = self.extract_text_from_pdf(pdf_path)
                        if text and text.strip():
                            print(f"Successfully extracted text from {pdf_file}, length: {len(text)} chars")
                            chunks = self.chunk_text(text)
                            print(f"Split into {len(chunks)} chunks")
                            
                            for chunk in chunks:
                                self.documents.append({
                                    'text': chunk,
                                    'source': pdf_file,
                                    'chunk_id': len(self.documents)
                                })
                        else:
                            print(f"Warning: No text extracted from {pdf_file}")
                            st.warning(f"Warning: No text could be extracted from {pdf_file}. The file might be corrupted or password protected.")
                    except Exception as e:
                        print(f"Error processing {pdf_file}: {str(e)}")
                        st.error(f"Error processing {pdf_file}: {str(e)}")
            
            if self.documents:
                success_msg = f"Successfully loaded {len(self.documents)} text chunks from {len(pdf_files)} PDF files."
                print(success_msg)
                st.success(success_msg)
                return True
            else:
                error_msg = "No documents were successfully loaded from PDFs."
                print(error_msg)
                st.error(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Error accessing Data folder: {str(e)}"
            print(error_msg)
            st.error(error_msg)
            return False
    
    def create_embeddings(self):
        """
        Create vector embeddings for all document chunks.
        
        Returns:
            bool: True if embeddings were created successfully, False otherwise
            
        Displays:
            - Error messages if documents aren't loaded or model isn't available
            - Progress spinner while creating embeddings
            - Success message when complete
        """
        if not self.documents:
            st.error("No documents loaded. Please load PDFs first.")
            return False
        
        if not self.embedding_model:
            st.error("Embedding model not loaded.")
            return False
        
        try:
            with st.spinner("Creating embeddings..."):
                texts = [doc['text'] for doc in self.documents]
                self.embeddings = self.embedding_model.encode(texts)
                
                # Create FAISS index
                dimension = self.embeddings.shape[1]
                self.index = faiss.IndexFlatL2(dimension)
                self.index.add(self.embeddings.astype('float32'))
            
            st.success("Embeddings created successfully!")
            return True
            
        except Exception as e:
            st.error(f"Error creating embeddings: {str(e)}")
            return False
    
    def search_similar_documents(self, query, k=3):
        """
        Search for documents similar to the query.
        
        Args:
            query (str): Search query text
            k (int): Maximum number of results to return (default: 3)
            
        Returns:
            list: List of matching document chunks with similarity scores
            
        Displays:
            - Warning if no good matches are found
            - Info messages about skipped documents
            - Error message if search fails
        """
        if not self.index or not self.embedding_model:
            return []

        try:
            # Create embedding for query
            query_embedding = self.embedding_model.encode([query])

            # Search in FAISS index
            distances, indices = self.index.search(query_embedding.astype('float32'), k)

            # Get relevant documents
            relevant_docs = []
            any_match = False  # Track if we found any good match

            for i, idx in enumerate(indices[0]):
                if 0 <= idx < len(self.documents):
                    score = float(distances[0][i])
                    if score <= 1:  # Threshold for good matches
                        doc = self.documents[idx].copy()
                        doc['similarity_score'] = score
                        relevant_docs.append(doc)
                        any_match = True
                    else:
                        st.info(f"⛔ Skipping document with similarity score {score:.2f} (too low match)")
                else:
                    st.warning(f"⚠️ Skipped invalid index: {idx} (documents count = {len(self.documents)})")

            if not any_match:
                st.warning("I should ask BRIDGE")

            return relevant_docs

        except Exception as e:
            st.error(f"Error searching documents: {str(e)}")
            return []

    def save_index(self, filepath="pdf_index.pkl"):
        """Save the processed index and documents"""
        try:
            data = {
                'documents': self.documents,
                'embeddings': self.embeddings
            }
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
            if self.index:
                faiss.write_index(self.index, "faiss_index.index")
            return True
        except Exception as e:
            st.error(f"Error saving index: {str(e)}")
            return False

    def load_index(self, filepath="pdf_index.pkl"):
        """
        Load a previously saved FAISS index and document metadata.
        
        Args:
            filepath (str): Path to the saved index file
            
        Returns:
            bool: True if load was successful, False otherwise
        """
        try:
            if os.path.exists(filepath) and os.path.exists("faiss_index.index"):
                with open(filepath, 'rb') as f:
                    data = pickle.load(f)
                    self.documents = data['documents']
                    self.embeddings = data['embeddings']
                    self.index = faiss.read_index("faiss_index.index")
                return True
        except Exception as e:
            st.error(f"Error loading index: {str(e)}")
            return False
