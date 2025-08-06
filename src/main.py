#!/usr/bin/env python3
"""
FastAPI application demonstrating MSK pub/sub functionality for EKS deployment.
Using faststream for Kafka integration.
"""

import logging
import os
import time
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import FastAPI
from faststream import FastStream
from faststream.kafka import KafkaBroker
from faststream.kafka.fastapi import KafkaRouter
from src.api.router import router
from src.api.models import MessageData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set specific loggers to WARNING level to reduce noise
logging.getLogger('kafka.conn').setLevel(logging.WARNING)
logging.getLogger('kafka.coordinator').setLevel(logging.WARNING)
logging.getLogger('kafka.consumer.subscription_state').setLevel(logging.WARNING)
logging.getLogger('kafka.cluster').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Initialize FastAPI app with FastStream integration
app = FastAPI(
    title="MSK Pub/Sub API",
    description="FastAPI application demonstrating MSK pub/sub functionality for EKS deployment",
    version="1.0.0",
    debug=False,
)

# Global variables for message buffer
message_buffer = []
max_buffer_size = 1000

# Configuration
CLUSTER_NAME = os.getenv('MSK_CLUSTER_NAME', 'eks-pubsub-cluster')
# Use localhost:9092 as default for local development with docker-compose
BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
REGION = os.getenv('AWS_REGION', 'us-east-1')
GROUP_ID = os.getenv('CONSUMER_GROUP_ID', 'eks-app-group')
TOPICS = os.getenv('KAFKA_TOPICS', 'user-events,system-alerts').split(',')
PORT = int(os.getenv('PORT', 8000))

# Set up security protocol based on environment
security_protocol = "PLAINTEXT" if BOOTSTRAP_SERVERS == "localhost:9092" else "SSL"

# Initialize Kafka broker with faststream
broker = KafkaBroker(
    bootstrap_servers=BOOTSTRAP_SERVERS,
    client_id=f"eks-app-{int(time.time())}"
)

# Create a FastStream application (not needed for simple broker usage)
# faststream_app = FastStream(broker)

# Global variable to track start time
start_time = time.time()

# Include router in app
app.include_router(router, prefix="/api/v1", tags=["MSK Pub/Sub"])

# Function to publish messages to Kafka
async def publish_message_to_kafka(topic: str, message: Dict[str, Any], key: Optional[str] = None) -> bool:
    """
    Publish a message to a Kafka topic.
    
    Args:
        topic: Kafka topic name
        message: Message data
        key: Optional message key for partitioning
        
    Returns:
        True if message was sent successfully
    """
    try:
        # Add metadata to message
        enriched_message = {
            'source': 'fastapi-api',
            'published_at': datetime.utcnow().isoformat(),
            'data': message
        }
        
        # Convert key to bytes if it's a string
        key_bytes = key.encode('utf-8') if key is not None else None
        
        # Publish message using faststream
        await broker.publish(
            message=enriched_message,
            topic=topic,
            key=key_bytes
        )
        
        logger.info(f"Message sent to {topic} with key {key}")
        return True
    except Exception as e:
        logger.error(f"Failed to send message to {topic}: {e}")
        return False

# Message handler for incoming Kafka messages
@broker.subscriber("user-events", group_id=GROUP_ID)
async def handle_message(message: dict):
    """Handle incoming messages from Kafka topics."""
    global message_buffer
    
    try:
        logger.info(f"Received message: {message}")
        
        # Extract the actual message content from the enriched message structure
        # When messages are published, they're wrapped with source, published_at, and data fields
        # The actual message content is in the 'data' field
        message_content = message.get('data', message)
        
        # Create a message data structure similar to the original implementation
        message_data = {
            'topic': 'user-events',
            'partition': 0,
            'offset': 0,
            'key': None,
            'value': message_content,
            'timestamp': None,
            'received_at': datetime.utcnow().isoformat()
        }
        
        # Add to buffer (with size limit)
        if len(message_buffer) >= max_buffer_size:
            message_buffer.pop(0)  # Remove oldest message
            
        message_buffer.append(message_data)
        
        logger.info(f"Processed message from user-events")
        logger.info(f"Message buffer size: {len(message_buffer)}")
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        logger.exception("Full traceback:")

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize components on application startup."""
    logger.info("Starting FastAPI MSK pub/sub application with faststream...")
    
    # Start the broker
    await broker.start()
    logger.info("Kafka broker started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    logger.info("Shutting down FastAPI MSK pub/sub application...")
    
    # Stop the broker
    await broker.stop()
    logger.info("Kafka broker stopped")


if __name__ == '__main__':
    import uvicorn

    logger.info(f"Starting FastAPI app on port {PORT}")
    uvicorn.run("src.main:app", host="0.0.0.0", port=PORT, log_level="info")
