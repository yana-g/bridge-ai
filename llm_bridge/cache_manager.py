import json, os, time
import numpy as np
from sentence_transformers import SentenceTransformer

class LocalCacheManager:
    def __init__(self, cache_dir='./cache'):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index_file = os.path.join(cache_dir, 'index.json')
        self.load_index()

    def load_index(self):
        if os.path.exists(self.index_file):
            with open(self.index_file, 'r') as f:
                self.index = json.load(f)
        else:
            self.index = {'prompts': [], 'embeddings': [], 'file_paths': []}

    def save_index(self):
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f)

    def exact_match_search(self, prompt):
        print("\n--- CacheManager.exact_match_search ---")
        print(f"Searching cache for exact match with prompt: {prompt[:50]}...")
        
        if prompt in self.index['prompts']:
            idx = self.index['prompts'].index(prompt)
            file_path = self.index['file_paths'][idx]
            print(f"Found exact match in cache: {file_path}")
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        return json.load(f), True
                else:
                    # Clean up the index if the file doesn't exist
                    print(f"Cache file not found, cleaning up index: {file_path}")
                    self.index['prompts'].pop(idx)
                    self.index['file_paths'].pop(idx)
                    if self.index['embeddings']:  # If we have embeddings, remove the corresponding one
                        self.index['embeddings'].pop(idx)
                    self.save_index()
            except Exception as e:
                print(f"Error loading cache file {file_path}: {str(e)}")
                return None, False
        print("No exact match found in cache")
        return None, False

    def semantic_search(self, prompt, threshold=0.85):
        print("\n--- CacheManager.semantic_search ---")
        print(f"Searching cache for semantic match with prompt: {prompt[:50]}...")
        
        if not self.index['embeddings']:
            print("No embeddings found in cache")
            return None, False
        query_embedding = self.embedding_model.encode(prompt)
        stored_embeddings = np.array(self.index['embeddings'])
        similarities = np.dot(stored_embeddings, query_embedding)
        best_match_idx = np.argmax(similarities)
        best_match_score = similarities[best_match_idx]
        if best_match_score >= threshold:
            file_path = self.index['file_paths'][best_match_idx]
            print(f"Found semantic match in cache: {file_path}")
            with open(file_path, 'r') as f:
                return json.load(f), True
        print("No semantic match found in cache")
        return None, False

    def store_response(self, session_json):
        print("\n--- CacheManager.store_response ---")
        prompt = session_json['initial_prompt']
        print(f"Storing in cache for prompt: {prompt[:50]}...")

        try:
            # Use the sanitized filename
            filename = self._sanitize_filename(prompt)
            file_path = os.path.join(self.cache_dir, filename)
    
            # Store the session data
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(session_json, f, ensure_ascii=False)
    
            # Get and store the embedding
            embedding = self.embedding_model.encode(prompt)
            self.index['prompts'].append(prompt)
            self.index['embeddings'].append(embedding.tolist())
            self.index['file_paths'].append(file_path)
    
            self.save_index()
            print(f"Cache size: {len(self.index['prompts'])}")

        except Exception as e:
            print(f"Error storing in cache: {str(e)}")

    def search(self, prompt):
        print("\n--- CacheManager.search ---")
        print(f"Searching cache for prompt: {prompt[:50]}...")
        
        try:
            result, found = self.exact_match_search(prompt)
            if found and result is not None:
                return result, True
                
            # Only proceed to semantic search if exact match wasn't found or failed
            return self.semantic_search(prompt)
            
        except Exception as e:
            print(f"Error during cache search: {str(e)}")
            # If there's any error, clear the cache index to prevent further issues
            self.index = {'prompts': [], 'embeddings': [], 'file_paths': []}
            self.save_index()
            return None, False

    def _sanitize_filename(self, text):
        """Convert text to a safe filename by removing or replacing invalid characters."""
        import re
        # Replace any non-alphanumeric character with underscore
        safe = re.sub(r'[^a-zA-Z0-9]', '_', text)
        # Remove multiple underscores
        safe = re.sub(r'_+', '_', safe)
        # Limit length and add hash to ensure uniqueness
        return f"{safe[:50]}_{hash(text) % 10000}.json"