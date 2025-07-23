# Data Layer Module

This module provides database connectivity and data management for the BRIDGE LLM Routing System, handling all interactions with MongoDB.

## Features

- **MongoDB Integration**: Thread-safe singleton pattern for database connections
- **User Management**: CRUD operations for user accounts and authentication
- **QA Storage**: Efficient storage and retrieval of question-answer pairs
- **Semantic Search**: Advanced search capabilities using sentence transformers
- **Performance**: Caching and optimization for high throughput
- **Error Handling**: Robust error handling and connection retry logic

## Dependencies

- Python 3.8+
- pymongo
- sentence-transformers
- scikit-learn
- python-dotenv

## Environment Variables

```
MONGO_URI=your_mongodb_connection_string
DB_NAME=bridge_db  # optional, defaults to 'bridge_db'
EMBEDDING_MODEL=all-MiniLM-L6-v2  # optional, defaults to 'all-MiniLM-L6-v2'
```

## Usage

```python
from data_layer.mongoHandler import db_handler

# Initialize connection (happens automatically on first use)
db_handler.test_connection()

# Create a new user
user_id = db_handler.create_user(
    username="testuser",
    email="user@example.com",
    password="securepassword"
)

# Save a QA pair
qa_id = db_handler.save_qa_record(
    user_id=user_id,
    question="What is FastAPI?",
    answer="FastAPI is a modern, fast web framework...",
    metadata={"source": "documentation"}
)

# Search for similar questions
results = db_handler.semantic_search_by_prompt(
    query="Tell me about FastAPI",
    threshold=0.8,
    top_k=3
)
```

## API Reference

### MongoDBHandler

Singleton class that handles all database operations.

#### Key Methods

- `test_connection()`: Verify database connectivity
- `create_user(username, email, password)`: Register a new user
- `verify_user(username, password)`: Authenticate a user
- `get_user(user_id)`: Retrieve user details
- `save_qa_record(user_id, question, answer, metadata)`: Store a new QA pair
- `semantic_search_by_prompt(query, threshold, top_k)`: Find similar questions using semantic search
- `search(prompt, threshold)`: Unified search that tries exact match first, then semantic search

## Testing

Run the test script to verify your MongoDB connection:

```bash
python test_mongodb_connection.py
```

## Error Handling

The module includes comprehensive error handling for:
- Connection failures
- Timeouts
- Duplicate keys
- Invalid operations

## Performance

- Connection pooling for efficient resource usage
- Caching of frequently accessed data
- Batch operations where applicable
- Indexed queries for optimal performance

## Security

- Password hashing (implemented in the calling application)
- API key rotation support
- Input validation
- Secure connection to MongoDB (when configured with proper URI)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request
