# Local Kafka Setup for AWS MSK PubSub Project

This document describes the changes made to connect the FastAPI application to a local Kafka server created by the docker-compose.yaml file.

## Changes Made

### 1. Updated Bootstrap Servers Configuration

In `src/main.py`, the `BOOTSTRAP_SERVERS` environment variable now defaults to 'localhost:9092' for local development:

```python
# Use localhost:9092 as default for local development with docker-compose
BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
```

### 2. Modified Security Protocol

In `src/main.py`, the security protocol is now set to "PLAINTEXT" for local Kafka and "SSL" for AWS MSK:

```python
# Use PLAINTEXT protocol for local Kafka, SSL for AWS MSK
security_protocol = "PLAINTEXT" if BOOTSTRAP_SERVERS == "localhost:9092" else "SSL"
msk_client = MSKClient(
    cluster_name=CLUSTER_NAME,
    bootstrap_servers=BOOTSTRAP_SERVERS,
    region=REGION,
    security_protocol=security_protocol
)
```

### 3. Disabled Compression

In `src/helpers/msk.py`, the compression type is now set to `None` for local development:

```python
'compression_type': None,  # No compression for local development
```

### 4. Adjusted Consumer Timeouts

In `src/helpers/msk.py`, the consumer timeouts have been adjusted for local development:

```python
'session_timeout_ms': 30000,  # Reduced timeout for local development
'heartbeat_interval_ms': 3000,  # Reduced heartbeat for local development
```

## Running the Application

1. Start the local Kafka environment:

```bash
docker-compose up -d
```

2. Run the FastAPI application:

```bash
cd src
PORT=8081 python main.py
```

Note: The application uses port 8081 to avoid conflict with the Kafka UI which runs on port 8080.

## Testing

A test script `test_kafka_connection.py` has been created to verify the connection to the local Kafka server. Run it with:

```bash
python test_kafka_connection.py
```

## Kafka UI

The Kafka UI is available at http://localhost:8080 for monitoring topics, messages, and consumer groups.

## Environment Variables

The following environment variables can be used to configure the application:

- `KAFKA_BOOTSTRAP_SERVERS`: Kafka bootstrap servers (default: 'localhost:9092')
- `MSK_CLUSTER_NAME`: Name of the MSK cluster (default: 'eks-pubsub-cluster')
- `AWS_REGION`: AWS region (default: 'us-east-1')
- `CONSUMER_GROUP_ID`: Kafka consumer group ID (default: 'eks-app-group')
- `KAFKA_TOPICS`: Comma-separated list of Kafka topics (default: 'user-events,system-alerts')
- `PORT`: Port for the FastAPI application (default: 8080)