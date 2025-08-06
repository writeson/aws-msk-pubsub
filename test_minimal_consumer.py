#!/usr/bin/env python3
"""
Minimal test to verify FastStream consumer is working.
"""

import asyncio
import logging
from faststream import FastStream
from faststream.kafka import KafkaBroker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize broker
broker = KafkaBroker("localhost:9092")
app = FastStream(broker)

messages_received = []

@broker.subscriber("user-events")
async def handle_message(message: dict):
    """Handle incoming messages."""
    logger.info(f"Received message: {message}")
    messages_received.append(message)

async def test_consumer():
    """Test the consumer."""
    try:
        # Start the broker
        await broker.start()
        logger.info("Broker started")
        
        # Wait a moment for the consumer to start
        await asyncio.sleep(2)
        
        # Publish a test message
        await broker.publish(
            {"test": "message", "id": "minimal-test"},
            topic="user-events"
        )
        logger.info("Test message published")
        
        # Wait for the message to be received
        await asyncio.sleep(3)
        
        if messages_received:
            logger.info(f"✅ Consumer is working! Received {len(messages_received)} messages")
            return True
        else:
            logger.error("❌ Consumer is not receiving messages")
            return False
            
    except Exception as e:
        logger.error(f"Error testing consumer: {e}")
        return False
    finally:
        await broker.close()

if __name__ == "__main__":
    result = asyncio.run(test_consumer())
    exit(0 if result else 1) 