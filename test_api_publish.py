#!/usr/bin/env python3
"""
Test script to verify the fix for the publish message endpoint.
This script makes a request to the /api/v1/publish endpoint and checks the response.
"""

import requests
import json
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_publish_endpoint(base_url="http://localhost:8000"):
    """Test the /api/v1/publish endpoint."""
    try:
        # Endpoint URL
        url = f"{base_url}/api/v1/publish"
        
        # Test message data
        message_data = {
            "topic": "user-events",
            "message": {
                "user_id": "test-user-123",
                "action": "login",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {
                    "ip": "192.168.1.1",
                    "device": "desktop",
                    "browser": "chrome"
                }
            },
            "key": "test-key"
        }
        
        # Make the request
        logger.info(f"Sending POST request to {url} with data: {json.dumps(message_data, indent=2)}")
        response = requests.post(url, json=message_data)
        
        # Check response
        if response.status_code == 200:
            logger.info(f"Request successful! Response: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            logger.error(f"Request failed with status code {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error testing publish endpoint: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting API publish endpoint test...")
    
    # Allow custom base URL from command line
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    result = test_publish_endpoint(base_url)
    
    if result:
        logger.info("API publish endpoint test PASSED!")
        exit(0)
    else:
        logger.error("API publish endpoint test FAILED!")
        exit(1)