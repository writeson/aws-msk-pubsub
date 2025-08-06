
import time
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from faststream.kafka import KafkaBroker

from src.helpers.config import settings

logger = logging.getLogger(__name__)


# Global variables for message buffer
message_buffer = []
max_buffer_size = 1000

# Initialize Kafka broker with faststream
broker = KafkaBroker(
    bootstrap_servers=settings.BOOTSTRAP_SERVERS,
    client_id=f"eks-app-{int(time.time())}"
)

# Periodic task for system alerts
async def system_alerts_task():
    """
    Periodic task that runs every 10 seconds and publishes a message to the "system-alerts" topic.
    """
    while True:
        try:
            # Create a system alert message
            alert_message = {
                "alert_type": "periodic_check",
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {
                    "message": "Periodic system check",
                    "check_id": f"check-{int(time.time())}"
                }
            }
            
            # Publish the message to the system-alerts topic
            await publish_message_to_kafka(
                topic="system-alerts",
                message=alert_message,
                key="periodic-check"
            )
            
            logger.info(f"Published periodic system alert message")
            
            # Wait for 10 seconds before the next iteration
            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"Error in system alerts task: {e}")
            await asyncio.sleep(10)  # Still wait before retrying


# Function to publish messages to Kafka
async def publish_message_to_kafka(topic: str, message: Dict[str, Any],
                                   key: Optional[str] = None) -> bool:
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


# Message handler for incoming Kafka messages from user-events topic
@broker.subscriber("user-events", group_id=settings.GROUP_ID)
async def handle_user_message(message: dict):
    """Handle incoming messages from the user-events topic."""
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


# Message handler for incoming Kafka messages from system-alerts topic
@broker.subscriber("system-alerts", group_id=settings.GROUP_ID)
async def handle_system_alert(message: dict):
    """Handle incoming messages from the system-alerts topic."""
    global message_buffer

    try:
        logger.info(f"Received system alert: {message}")

        # Extract the actual message content from the enriched message structure
        message_content = message.get('data', message)

        # Create a message data structure
        message_data = {
            'topic': 'system-alerts',
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

        logger.info(f"Processed system alert message")
        logger.info(f"Message buffer size: {len(message_buffer)}")

    except Exception as e:
        logger.error(f"Error handling system alert: {e}")
        logger.exception("Full traceback:")

