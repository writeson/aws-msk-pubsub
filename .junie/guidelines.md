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
- `deploy/`: Deployment-related code
  - AWS CDK deployment stack
- `something/`: Miscellaneous scripts and configuration

## Coding Standards

### Python Style Guidelines
- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Document classes and functions with docstrings
- Use meaningful variable and function names

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