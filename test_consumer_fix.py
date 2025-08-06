#!/usr/bin/env python3
"""
Test script to verify that the consumer fix is working properly.
"""

import requests
import json
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_consumer_fix():
    """Test that messages are being consumed properly after the fix."""
    try:
        # First, publish a message
        message_data = {
            "topic": "user-events",
            "message": {
                "user_id": "test-consumer-fix",
                "action": "test",
                "name": "Test User"
            },
            "key": "consumer-test-key"
        }
        
        logger.info("Publishing test message...")
        response = requests.post(
            "http://localhost:8000/api/v1/publish",
            json=message_data
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to publish message: {response.status_code}")
            return False
            
        logger.info("Message published successfully")
        
        # Wait a moment for the consumer to process the message
        time.sleep(2)
        
        # Check if the message was received
        logger.info("Checking if message was received...")
        response = requests.get("http://localhost:8000/api/v1/messages?limit=10")
        
        if response.status_code != 200:
            logger.error(f"Failed to get messages: {response.status_code}")
            return False
            
        messages_data = response.json()
        logger.info(f"Retrieved {messages_data['returned_count']} messages")
        
        # Look for our test message
        test_message_found = False
        for msg in messages_data['messages']:
            if (msg.get('value', {}).get('user_id') == 'test-consumer-fix' and 
                msg.get('value', {}).get('action') == 'test'):
                test_message_found = True
                logger.info(f"Found test message: {msg}")
                break
                
        if test_message_found:
            logger.info("✅ Consumer fix is working! Message was received and stored.")
            return True
        else:
            logger.warning("⚠️  Test message not found in received messages")
            logger.info(f"Available messages: {json.dumps(messages_data['messages'], indent=2)}")
            return False
            
    except Exception as e:
        logger.error(f"Error testing consumer fix: {e}")
        return False

if __name__ == "__main__":
    logger.info("Testing consumer fix...")
    result = test_consumer_fix()
    
    if result:
        logger.info("Consumer fix test PASSED!")
        exit(0)
    else:
        logger.error("Consumer fix test FAILED!")
        exit(1) 