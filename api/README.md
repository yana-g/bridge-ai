# LLM Bridge API

A FastAPI-based service that provides a structured interface for interacting with Large Language Models (LLMs). The API handles authentication, request validation, and response formatting, making it easy to integrate LLM capabilities into your applications.

## 🌟 Features

- **Structured Requests**: Send well-formatted prompts with configurable parameters
- **Multiple Response Styles**: Choose from different response vibes (Academic, Business, Technical, etc.)
- **Robust Authentication**: Secure API key and username-based authentication
- **Request Validation**: Comprehensive input validation with meaningful error messages
- **Request Logging**: Detailed logging for all API requests and responses
- **Health Monitoring**: Built-in health check endpoint
- **Async Support**: Fully asynchronous implementation for high performance
- **Comprehensive Testing**: Complete test coverage including authentication and error cases

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- MongoDB (for user management and logging)
- API key and username for authentication

### Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Run the API
   ```bash
   uvicorn api.entry_point_api:app --reload
   ```

   The API will be available at `http://localhost:8000`

## 📚 API Documentation

Once the API is running, you can access:

- **Interactive API Docs**: `http://localhost:8000/docs`
- **Alternative API Docs**: `http://localhost:8000/redoc`

## 🔑 Authentication

The API uses API Key and Username authentication. Include both in the request headers:

- `X-API-Key`: Your API key
- `X-Username`: Your username (must match the username associated with the API key)

Example:
```
GET /health
X-API-Key: your-api-key
X-Username: admin
```

**Note:** Both headers are required for all authenticated endpoints. Missing or invalid credentials will result in a `401 Unauthorized` response.

## 🛠️ Endpoints

### Health Check

```
GET /health
```

Check if the API is running and its current status.

**Headers: (Authentication required)**
- `X-API-Key`: Your API key
- `X-Username`: Your username

**Response:**
```json
{
  "status": "ok",
  "environment": "development",
  "version": "1.0.0"
}
```

### Ask LLM

```
POST /ask-llm/
```

Send a question to the LLM and get a response.

**Headers: (Authentication required)**
- `X-API-Key`: Your API key
- `X-Username`: Your username
- `Content-Type`: application/json

**Request Body:**
```json
{
  "vibe": "Business/Professional",
  "sender_id": "user123",
  "question_id": "unique-id-123",
  "question": "What is the capital of France?",
  "confidence": true,
  "nature_of_answer": "Medium"
}
```

**Response:**
```json
{
  "response": "The capital of France is Paris.",
  "vibe_used": "Business/Professional",
  "question_id": "unique-id-123",
  "sender_id": "user123",
  "model_metadata": {}
}
```

**Possible Error Responses:**
- `400 Bad Request`: Invalid request body
- `401 Unauthorized`: Missing or invalid authentication
- `422 Unprocessable Entity`: Missing required fields or invalid data format
- `500 Internal Server Error`: Server error while processing the request

## 🧪 Testing

Run the test suite with:

```bash
pytest tests/ -v
```

### Test Coverage

The test suite includes:
- Authentication and authorization tests
- Request validation tests
- Error handling tests
- End-to-end API tests

To run tests with coverage report:

```bash
pytest --cov=api tests/
```

## 🧩 Project Structure

```
api/
├── __init__.py
├── entry_point_api.py      # Main FastAPI application and routes
├── authHandler.py         # Authentication and authorization logic
├── middleware/            # Custom middleware
│   └── validation.py      # Request validation
├── tests/                 # Test files
│   ├── __init__.py
│   ├── conftest.py        # Test fixtures and mocks
│   └── test_core.py       # Test cases
├── .env.example          # Example environment variables
├── requirements.txt       # Project dependencies
└── README.md             # This file
```

## 🔄 API Versioning

The API follows semantic versioning (SemVer). The current version is v1.

## 📈 Monitoring and Logging

All API requests are logged with the following information:
- Request method and path
- Client IP address
- Request ID for tracing
- Processing time
- Response status code
- Error messages (if any)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

**Development Requirements:**
- All code must have corresponding tests
- Follow PEP 8 style guide
- Update documentation for any API changes
- Ensure all tests pass before submitting a PR

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Uses [MongoDB](https://www.mongodb.com/) for data storage
- [Pytest](https://docs.pytest.org/) for testing
- [HTTPX](https://www.python-httpx.org/) for async HTTP client

---

*Last updated: June 2025*
