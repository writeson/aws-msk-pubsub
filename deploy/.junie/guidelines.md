# CipherPay Development Guidelines

This document provides concise guidance for new developers working on the CipherPay project.

## Project Overview

CipherPay is a FastAPI-based application that manages encryption/decryption needs for payment processing. It provides RESTful API endpoints for payment processing, transaction management, and general operations.

## Project Structure

```
cipherpay/
├── src/                  # Source code
│   ├── api/              # API endpoints and models
│   │   └── v1/           # API version 1
│   │       ├── general/  # General endpoints
│   │       ├── payment/  # Payment endpoints
│   │       └── transaction/ # Transaction endpoints
│   ├── helpers/          # Helper functions and utilities
│   ├── static/           # Static files
│   ├── main.py           # Application entry point
│   └── settings.toml     # Configuration settings
├── tests/                # Test files
│   ├── api/              # API tests
│   ├── conftest.py       # Pytest fixtures
│   └── pytest.ini        # Pytest configuration
├── docs/                 # Documentation
├── resources/            # Additional resources
└── pyproject.toml        # Project configuration
```

## Tech Stack

- **Python 3.13.3**: Programming language
- **FastAPI**: Web framework for building APIs
- **Pydantic**: Data validation and settings management
- **Uvicorn**: ASGI server
- **Pytest**: Testing framework
- **Ruff**: Linting and code formatting
- **Structlog**: Structured logging
- **AWS SDK**: For AWS services integration
- **Docker**: For containerization

## Development Workflow

### Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -e .
   pip install -e ".[dev]"
   ```
3. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Running the Application

Start the application locally:

```bash
uvicorn src.main:app --reload
```

The API documentation will be available at http://localhost:8000/docs

### Docker

Build and run with Docker:

```bash
docker-compose up --build
```

## Testing Guidelines

### Running Tests

Run all tests:

```bash
pytest
```

Run specific tests:

```bash
pytest tests/api/v1/general/test_models.py
```

Run with verbose output:

```bash
pytest -v
```

### Writing Tests

- Place tests in the `tests/` directory, mirroring the structure of `src/`
- Use function-based tests (not class-based)
- Place fixtures in `conftest.py`
- Test both positive and negative scenarios
- Use descriptive test names that explain what is being tested
- Each test should have a docstring explaining its purpose

Example:

```python
def test_valid_friendly_name(valid_friendly_name_data):
    """Test that a valid friendly name is accepted."""
    friendly_name = FriendlyName(**valid_friendly_name_data)
    assert friendly_name.merchant_account_id == valid_friendly_name_data["merchant_account_id"]
```

## Coding Standards

- Follow PEP 8 with 100 character line limit
- Use double quotes for strings
- Use f-strings for string formatting
- Use restructured text style docstrings
- Follow FastAPI's recommended patterns for API endpoints
- Use Pydantic for data validation and models
- Place API models in dedicated `models.py` files
- Place API endpoints in dedicated `router.py` files

### Error Handling

- Use appropriate HTTP status codes
- Return structured error responses
- Log errors with context using structlog

### Linting

Run linting checks:

```bash
ruff check .
```

Fix auto-fixable issues:

```bash
ruff check --fix .
```