#!/usr/bin/env python3
"""
Test script to verify connection to local Kafka server.
"""

import logging
import time
from src.helpers.msk import MSKClient, MSKProducer, MSKConsumer

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set root logger to DEBUG to enable debug logging for all modules
logging.getLogger().setLevel(logging.DEBUG)

# Set specific loggers to DEBUG level
logging.getLogger('kafka').setLevel(logging.DEBUG)
logging.getLogger('kafka.conn').setLevel(logging.WARNING)  # Turn off kafka.conn INFO messages

logger = logging.getLogger(__name__)

def test_kafka_connection():
    """Test connection to local Kafka server."""
    try:
        # Initialize MSK client with local Kafka settings
        logger.info("Initializing MSK client with local Kafka settings...")
        msk_client = MSKClient(
            cluster_name="local-kafka",
            bootstrap_servers="localhost:9092",
            security_protocol="PLAINTEXT"
        )
        
        # Test producer
        logger.info("Testing producer...")
        producer = MSKProducer(msk_client)
        
        # Create test topic if it doesn't exist
        test_topic = "test-topic"
        
        # Publish test message
        test_message = {
            "message": "Test message",
            "timestamp": time.time()
        }
        
        success = producer.publish(
            topic=test_topic,
            message=test_message,
            key="test-key"
        )
        
        if success:
            logger.info("Successfully published test message to Kafka!")
        else:
            logger.error("Failed to publish test message to Kafka.")
            return False
        
        # Test consumer
        logger.info("Testing consumer...")
        consumer = MSKConsumer(
            msk_client=msk_client,
            group_id="test-group",
            topics=[test_topic],
            auto_offset_reset='earliest'
        )
        
        # Define message handler
        messages_received = []
        
        def message_handler(message):
            logger.info(f"Received message: {message.value}")
            messages_received.append(message)
            
        # Start consumer with timeout
        logger.info("Starting consumer...")
        
        # Set a timeout for consumer
        max_wait_time = 10  # seconds
        start_time = time.time()
        
        # Start a separate thread for consumer
        import threading
        consumer_thread = threading.Thread(
            target=lambda: consumer.consume(message_handler, timeout_ms=1000),
            daemon=True
        )
        consumer_thread.start()
        
        # Wait for messages or timeout
        while time.time() - start_time < max_wait_time and not messages_received:
            time.sleep(0.5)
            
        # Stop consumer
        consumer.stop()
        
        if messages_received:
            logger.info(f"Successfully received {len(messages_received)} messages from Kafka!")
            return True
        else:
            logger.warning("No messages received from Kafka within timeout period.")
            return False
            
    except Exception as e:
        logger.error(f"Error testing Kafka connection: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting Kafka connection test...")
    result = test_kafka_connection()
    
    if result:
        logger.info("Kafka connection test PASSED!")
        exit(0)
    else:
        logger.error("Kafka connection test FAILED!")
        exit(1)