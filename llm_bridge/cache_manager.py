"""
Cache manager for the LLM Bridge application.
Handles all cache operations for both user management and QA records.
""" 
import os
import json
import time
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any
from sentence_transformers import SentenceTransformer
from config import DEV_MODE
from sklearn.metrics.pairwise import cosine_similarity
from data_layer.mongoHandler import MongoDBHandler
import re

class LocalCacheManager:
    def __init__(self, cache_dir: str = './cache', max_retries: int = 3, retry_delay: int = 1):
        """
        Initialize the LocalCacheManager with optional MongoDB fallback.

        Args:
            cache_dir: Directory to store cache files
            max_retries: Maximum number of retry attempts for MongoDB operations
            retry_delay: Delay between retry attempts in seconds
        """
        self.cache_dir = cache_dir
        self.index_file = os.path.join(self.cache_dir, 'index.json')
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Stats tracking (optional)
        self.stats = {
            'hits': 0,
            'misses': 0,
            'mongo_hits': 0,
            'mongo_misses': 0,
            'errors': 0
        }

        # Initialize sentence embedding model
        try:
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            print("✅ Embedding model loaded")
        except Exception as e:
            print(f"❌ Failed to load embedding model: {e}")
            self.embedding_model = None

        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)

        # Load cache index or initialize new one
        self.load_index()

        # Initialize MongoDB fallback
        self.mongo_available = False
        self.mongo_handler = self._init_mongodb()
        if self.mongo_handler:
            print("📦 MongoDB handler initialized")
        else:
            print("⚠️ MongoDB fallback is unavailable")
    
    def _init_mongodb(self) -> Optional[MongoDBHandler]:
        """Initialize MongoDB connection with retry logic"""
        for attempt in range(self.max_retries):
            try:
                handler = MongoDBHandler()
                # Test the connection
                handler.db.command('ping')
                self.mongo_available = True
                if DEV_MODE:
                    print("✅ MongoDB connection successful")
                return handler
            except Exception as e:
                if attempt < self.max_retries - 1:
                    if DEV_MODE:
                        print(f"⚠️ MongoDB connection attempt {attempt + 1} failed, retrying in {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                else:
                    if DEV_MODE:
                        print(f"❌ Failed to connect to MongoDB after {self.max_retries} attempts: {e}")
                    self.mongo_available = False
                    return None
    
    def _validate_prompt(self, prompt: Any) -> Tuple[bool, str]:
        """Validate the prompt input"""
        if not isinstance(prompt, str):
            return False, "Prompt must be a string"
        if not prompt.strip():
            return False, "Prompt cannot be empty"
        if len(prompt) > 10000:  # Arbitrary large limit
            return False, "Prompt is too long"
        return True, ""
    
    def exact_match_search(self, prompt: str, vibe: str = None, nature_of_answer: str = None) -> Tuple[Optional[Dict], bool, float]:
        """
        Search for an exact match of the prompt in the cache
        
        Args:
            prompt: The prompt to search for
            
        Returns:
            Tuple of (cached_response, found, similarity) where:
            - cached_response: The cached response if found, else None
            - found: Boolean indicating if an exact match was found
            - similarity: Always 1.0 for exact matches
        """
        # Input validation
        is_valid, error = self._validate_prompt(prompt)
        if not is_valid:
            if DEV_MODE:
                print(f"⚠️ Invalid prompt in exact_match_search: {error}")
            return None, False, 0.0
        
        try:
            # Create composite cache key for search
            search_key = self._create_cache_key(prompt, vibe, nature_of_answer)
        
            if search_key in self.index['prompts']:
                self.stats['hits'] += 1
                idx = self.index['prompts'].index(search_key)
                with open(self.index['file_paths'][idx], 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                    # Check TTL if enabled
                    if self._is_expired(cached_data):
                        if DEV_MODE:
                            print(f"⚠️ Cache entry expired: {search_key[:50]}...")
                        self._remove_from_cache(self.index['file_paths'][idx], idx)
                        self.stats['misses'] += 1
                        self.stats['hits'] -= 1  # Adjust stats
                        return None, False, 0.0
                    
                    return cached_data, True, 1.0
                
            self.stats['misses'] += 1
            return None, False, 0.0
        
        except Exception as e:
            self.stats['errors'] += 1
            if DEV_MODE:
                print(f"⚠️ Cache: Error in exact match search: {e}")
                import traceback
                traceback.print_exc()
            return None, False, 0.0
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics
        
        Returns:
            Dictionary containing cache statistics
        """
        return {
            **self.stats,
            'total_queries': self.stats['hits'] + self.stats['misses'],
            'hit_ratio': self.stats['hits'] / max(1, self.stats['hits'] + self.stats['misses']),
            'cache_size': len(self.index['prompts']),
            'mongo_available': self.mongo_available
        }
    
    def clear_cache(self) -> bool:
        """
        Clear the entire cache
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Clear in-memory index
            self.index = {'prompts': [], 'embeddings': [], 'file_paths': []}
            
            # Remove all cache files
            for filename in os.listdir(self.cache_dir):
                if filename != 'index.json':  # Keep the index file
                    try:
                        os.remove(os.path.join(self.cache_dir, filename))
                    except Exception as e:
                        print(f"⚠️ Failed to delete cache file {filename}: {e}")
            
            # Save the empty index
            self.save_index()
            
            # Reset stats
            self.stats = {k: 0 for k in self.stats}
            
            if DEV_MODE:
                print("✅ Cache cleared successfully")
            return True
            
        except Exception as e:
            if DEV_MODE:
                print(f"❌ Failed to clear cache: {e}")
            return False
    
    def load_index(self):
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'r') as f:
                    content = f.read().strip()
                    if content:  # Only try to parse if file is not empty
                        self.index = json.loads(content)
                        if DEV_MODE:
                            print(f"✅ Loaded cache index with {len(self.index['prompts'])} entries")
                        return
                if DEV_MODE:
                    print("⚠️ Index file was empty, creating new index")
            except json.JSONDecodeError as e:
                if DEV_MODE:
                    print(f"⚠️ Error loading cache index: {e}. Creating new index.")
                # Backup the corrupted file
                try:
                    import shutil
                    backup_path = f"{self.index_file}.bak"
                    shutil.copy2(self.index_file, backup_path)
                    if DEV_MODE:
                        print(f"⚠️ Backed up corrupted index to: {backup_path}")
                except Exception as backup_error:
                    if DEV_MODE:
                        print(f"⚠️ Failed to backup corrupted index: {backup_error}")
        
        # Initialize new index if file doesn't exist or was corrupted
        self.index = {'prompts': [], 'embeddings': [], 'file_paths': []}
        self.save_index()  # Save the new index to create the file
        if DEV_MODE:
            print("✅ Created new cache index")

    def _init_mongodb(self):
        """Attempt to initialize the MongoDBHandler safely."""
        try:
            from data_layer.mongoHandler import MongoDBHandler
            return MongoDBHandler()
        except Exception as e:
            print(f"⚠️ Failed to initialize MongoDBHandler: {e}")
            return None

    def save_index(self):
        if DEV_MODE:
            print(f"💾 Saving index ({len(self.index['prompts'])} entries)")
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f)

    def store_response(self, session_json: Dict, ttl_seconds: Optional[int] = None) -> bool:
        """
        Store a response in the local cache.
        
        Args:
            session_json: The session data to cache
            ttl_seconds: Optional time-to-live in seconds (unused in local cache)
            
        Returns:
            bool: True if storage was successful, False otherwise
        """
        if 'initial_prompt' not in session_json:
            if DEV_MODE:
                print("❌ Cache: Missing 'initial_prompt' in session data")
            return False
        
        prompt = session_json['initial_prompt']
        vibe = session_json.get('vibe')
        nature_of_answer = session_json.get('nature_of_answer') or session_json.get('response_preference')
    
        try:
            # Save locally only in DEV_MODE
            if DEV_MODE:
                # Ensure the cache directory exists
                os.makedirs(self.cache_dir, exist_ok=True)
                
                # Create composite cache key
                cache_key = self._create_cache_key(prompt, vibe, nature_of_answer)
            
                # Use the sanitized filename based on cache key
                filename = self._sanitize_filename(cache_key)
                file_path = os.path.join(self.cache_dir, filename)
            
                # Ensure the response is JSON serializable
            try:
                json.dumps(session_json)  # Test serialization
            except (TypeError, OverflowError) as e:
                print(f"❌ Cache: Non-serializable data in session: {e}")
                # Try to make it serializable by removing non-serializable fields
                if 'final_output' in session_json and 'model_metadata' in session_json['final_output']:
                    if 'embedding' in session_json['final_output']['model_metadata']:
                        session_json['final_output']['model_metadata']['embedding'] = "[embedding removed]"
                session_json['final_output'] = str(session_json.get('final_output', {}))
            
            # Ensure searchable fields are present at top-level
            session_json['vibe'] = vibe
            session_json['nature_of_answer'] = nature_of_answer

            # Store the session data locally
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(session_json, f, ensure_ascii=False, indent=2)
            
            # Get and store the embedding using ONLY the prompt (not the composite key)
            try:
                if self.embedding_model:
                    embedding = self.embedding_model.encode(prompt)  # רק prompt לembedding
                    self.index['prompts'].append(cache_key)  # אבל composite key ב-index
                    self.index['embeddings'].append(embedding.tolist())
                    self.index['file_paths'].append(file_path)
                    
                    # Save the updated index
                    self.save_index()
                    
                if DEV_MODE:
                    print(f"✅ Cached with key: {cache_key[:100]}...")
                
            except Exception as e:
                print(f"❌ Cache: Failed to update local index: {str(e)}")

        except Exception as e:
            print(f"❌ Cache: Error in store_response: {str(e)}")
            if DEV_MODE:
                import traceback
                traceback.print_exc()
            return False
    
        return True
    
    def _sanitize_filename(self, prompt: str) -> str:
        # Remove all non-word characters (everything except numbers and letters) and convert to lowercase
        safe_prompt = re.sub(r'[^\w\s-]', '', prompt).strip().lower()
        # Replace spaces and multiple dashes with single underscore
        safe_prompt = re.sub(r'[\s-]+', '_', safe_prompt)
        # Trim to 50 chars and add hash for uniqueness
        return f"{safe_prompt[:50]}__{abs(hash(prompt)) % 10000}.json"

    def _create_cache_key(self, prompt: str, vibe: Optional[str] = None, nature_of_answer: Optional[str] = None) -> str:
        """
        Create a composite cache key that includes prompt, vibe, and nature_of_answer
        
        Args:
            prompt: The user's prompt
            vibe: Optional vibe parameter
            nature_of_answer: Optional nature of answer parameter
        
        Returns:
            str: A composite cache key
        """
        # Create a composite key that includes all parameters
        key_components = [prompt]
        if vibe:
            key_components.append(f"vibe:{vibe}")
        if nature_of_answer:
            key_components.append(f"nature:{nature_of_answer}")
    
        return "||".join(key_components)
    
    def semantic_search(self, prompt: str, vibe: str = None, nature_of_answer: str = None, threshold: float = 0.85) -> Tuple[Optional[Dict], bool, float]:
        """
        Search for semantically similar prompts in the cache with vibe and nature_of_answer filtering
        
        Args:
            prompt: The prompt to search for
            vibe: Optional vibe parameter
            nature_of_answer: Optional nature of answer parameter
            threshold: Minimum similarity score (0-1) to consider a match
        
        Returns:
            Tuple of (cached_response, found, similarity) where:
            - cached_response: The best matching cached response if found, else None
            - found: Boolean indicating if a match was found
            - similarity: The similarity score of the best match (0.0 if no match)
        """
        # Input validation
        is_valid, error = self._validate_prompt(prompt)
        if not is_valid:
            if DEV_MODE:
                print(f"⚠️ Invalid prompt in semantic_search: {error}")
            return None, False, 0.0
        
        try:
            if not self.index['prompts']:
                self.stats['misses'] += 1
                return None, False, 0.0
                
            # Generate query embedding (only for the prompt, not composite key)
            query_embedding = self.embedding_model.encode(prompt).reshape(1, -1)
            embeddings = np.array(self.index['embeddings'])

            if len(embeddings) == 0:
                self.stats['misses'] += 1
                return None, False, 0.0 
        
            # Filter cache keys that match vibe and nature_of_answer BEFORE similarity calculation
            valid_indices = []
            for idx, cache_key in enumerate(self.index['prompts']):
                # Parse composite key to check vibe and nature
                key_parts = cache_key.split("||")
                cached_prompt = key_parts[0]
            
                # Extract vibe and nature from key
                cached_vibe = None
                cached_nature = None
                for part in key_parts[1:]:
                    if part.startswith("vibe:"):
                        cached_vibe = part[5:]  # Remove "vibe:" prefix
                    elif part.startswith("nature:"):
                        cached_nature = part[7:]  # Remove "nature:" prefix
            
                # Check if vibe matches (if provided)
                if vibe is not None and cached_vibe != vibe:
                    continue
                
                # Check if nature_of_answer matches (if provided)
                if nature_of_answer is not None and cached_nature != nature_of_answer:
                    continue
                
                valid_indices.append(idx)
        
            if not valid_indices:
                self.stats['misses'] += 1
                return None, False, 0.0
        
            # Calculate similarities only for valid indices
            valid_embeddings = embeddings[valid_indices]
            similarities = cosine_similarity(valid_embeddings, query_embedding)
        
            # Find best match
            max_idx_in_valid = np.argmax(similarities)
            max_similarity = float(similarities[max_idx_in_valid][0])
        
            # Check if the best match meets the threshold
            if max_similarity >= threshold:
                self.stats['hits'] += 1
                original_idx = valid_indices[max_idx_in_valid]
                file_path = self.index['file_paths'][original_idx]
            
                with open(file_path, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                # Check TTL if enabled
                if self._is_expired(cached_data):
                    if DEV_MODE:
                        print(f"⚠️ Cache entry expired: {prompt[:50]}...")
                    self._remove_from_cache(file_path, original_idx)
                    self.stats['misses'] += 1
                    self.stats['hits'] -= 1  # Adjust stats
                    return None, False, 0.0
                    
                return cached_data, True, max_similarity
                
            self.stats['misses'] += 1
            return None, False, 0.0
        
        except Exception as e:
            self.stats['errors'] += 1
            if DEV_MODE:
                print(f"⚠️ Cache: Error in semantic search: {e}")
                import traceback
                traceback.print_exc()
            return None, False, 0.0

    def _is_expired(self, cached_data: Dict) -> bool:
        """Check if a cached item has expired based on its TTL"""
        if 'expires_at' not in cached_data.get('metadata', {}):
            return False
            
        try:
            expires_at = cached_data['metadata']['expires_at']
            return time.time() > expires_at
        except (KeyError, TypeError):
            return False
    
    def _remove_from_cache(self, file_path: str, index: int):
        """Remove an entry from the cache"""
        try:
            # Remove the file
            if os.path.exists(file_path):
                os.remove(file_path)
                
            # Update the index
            if index < len(self.index['prompts']):
                del self.index['prompts'][index]
                del self.index['embeddings'][index]
                del self.index['file_paths'][index]
                self.save_index()
                
        except Exception as e:
            if DEV_MODE:
                print(f"⚠️ Failed to remove cache entry: {e}")

    def search(self, prompt, vibe=None, nature_of_answer=None, threshold=0.85):
        """
        Search for a prompt in the cache, trying exact match first, then semantic search,
        and finally falling back to MongoDB if available.
        
        Args:
            prompt: The prompt to search for
            vibe: Optional vibe parameter
            nature_of_answer: Optional nature of answer parameter
            threshold: Minimum similarity score for semantic search (0-1)
        
        Returns:
            Tuple containing:
                - The cached response if found, else None
                - The match type ('exact', 'semantic', 'mongo', or 'not_found')
                - The similarity score (1.0 for exact matches, 0.0 for no match)
        """
        if not prompt or not isinstance(prompt, str):
            return None, 'not_found', 0.0

        # --- Exact Match ---
        result, found, similarity = self.exact_match_search(prompt, vibe=vibe, nature_of_answer=nature_of_answer)
        if found:
            if DEV_MODE:
                print(f"🔍 Exact match found in local cache")
            return result, 'exact', similarity

        # --- Semantic Match ---
        result, found, similarity = self.semantic_search(prompt, vibe=vibe, nature_of_answer=nature_of_answer, threshold=threshold)
        if found:
            if DEV_MODE:
                print(f"🔍 Semantic match found in local cache (similarity: {similarity:.2f})")
            return result, 'semantic', similarity

        # --- MongoDB Fallback ---
        if hasattr(self, 'mongo_handler') and self.mongo_handler:
            try:
                # 🔧 FIX: Pass vibe and nature_of_answer to MongoDB search
                mongo_result, match_type, similarity = self.mongo_handler.search(
                    prompt, 
                    vibe=vibe, 
                    nature_of_answer=nature_of_answer, 
                    threshold=threshold
                )
            
                if mongo_result:
                    self.stats['mongo_hits'] += 1
                    if DEV_MODE:
                        print(f"✅ MongoDB {match_type} match found (similarity: {similarity:.2f})")
                    return mongo_result, 'mongo', similarity
                else:
                    self.stats['mongo_misses'] += 1
                    if DEV_MODE:
                        print("❌ No match found in MongoDB")
                    
            except Exception as e:
                self.stats['errors'] += 1
                if DEV_MODE:
                    print(f"⚠️ MongoDB search failed: {e}")
                    import traceback
                    traceback.print_exc()

        return None, 'not_found', 0.0

    def get_embedding(self, prompt):
        try:
            return self.embedding_model.encode(prompt)
        except Exception as e:
            print(f"Error encoding prompt: {str(e)}")
            return None
