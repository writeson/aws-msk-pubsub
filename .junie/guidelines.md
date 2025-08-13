# AWS MSK PubSub Project Guidelines

## Project Overview
This project is a FastAPI application demonstrating AWS MSK (Managed Streaming for Kafka) pub/sub functionality for EKS (Elastic Kubernetes Service) deployment. It provides a RESTful API for publishing and consuming messages from Kafka topics.

## Project Structure
- `src/`: Main source code directory
  - `api/`: API-related code
    - `models.py`: Pydantic models for request/response data
    - `router.py`: FastAPI route definitions
  - `helpers/`: Helper modules
    - `msk.py`: AWS MSK client for pub/sub operations
  - `main.py`: Application entry point
- `deploy/`: Deployment-related code[guidelines.md](../../../rh/air-bridge/.junie/guidelines.md)
  - AWS CDK deployment stack
- `something/`: Miscellaneous scripts and configuration

### Python Style Guidelines
The project uses ruff for linting with the following configuration:

- **Line Length**: 100 characters
- **Docstring Style**: Restructured Text style
- **Enabled Rules**: 
  - E, W: pycodestyle errors and warnings
  - F: Pyflakes (undefined names)
  - I: isort (import sorting)
  - N: pep8-naming (naming conventions)
  - D: pydocstyle (docstring style)
  - UP: pyupgrade (modern syntax)
  - C90: mccabe (complexity)
  - B: bugbear (security and performance)
  - SIM: simplify (reducing unnecessary code)

- **Maximum Complexity**: 10 for functions

### Code Style Docstring Example

```python
def example_function(param1: int, param2: str) -> bool:
    """
    This is an example function that demonstrates proper docstring style.

    :param param1: An integer parameter.
    :param param2: A string parameter.
    :return: A boolean indicating success or failure.
    """
    return True
```

### API Development
- Use Pydantic models for request/response validation
- Implement proper error handling with appropriate HTTP status codes
- Include health and readiness check endpoints
- Document API endpoints with descriptive docstrings

### Kafka Integration
- Use the provided MSKClient, MSKProducer, and MSKConsumer classes for Kafka operations
- Handle Kafka errors gracefully
- Implement proper message serialization/deserialization
- Use appropriate Kafka configuration for production environments

## Development Workflow
1. Set up a local development environment with the required dependencies
2. Make changes to the codebase following the coding standards
3. Test changes locally before committing
4. Submit pull requests for code review

## Deployment
- The application is designed to be deployed on EKS (Elastic Kubernetes Service)
- Use the provided CDK deployment stack in the `deploy/` directory
- Configure environment variables for AWS region, MSK cluster name, etc.

## Environment Variables
- `MSK_CLUSTER_NAME`: Name of the MSK cluster (default: 'eks-pubsub-cluster')
- `AWS_REGION`: AWS region (default: 'us-east-1')
- `CONSUMER_GROUP_ID`: Kafka consumer group ID (default: 'eks-app-group')
- `KAFKA_TOPICS`: Comma-separated list of Kafka topics (default: 'user-events,system-alerts')
- `PORT`: Port for the FastAPI application (default: 8080)

## Security Considerations
- Use SSL for Kafka connections
- Follow AWS security best practices for MSK and EKS
- Implement proper authentication and authorization for the API

## Testing
- Write unit tests for all components
- Implement integration tests for the API endpoints
- Test Kafka integration with a local Kafka instance or AWS MSK

## Monitoring and Logging
- Use structured logging with appropriate log levels
- Implement metrics collection for monitoring
- Set up alerts for critical errors