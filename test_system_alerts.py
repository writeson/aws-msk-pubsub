#!/usr/bin/env python3
"""
Test script to verify the system alerts periodic task.
This script starts the FastAPI application and checks the logs to verify that
messages are being published every 5 seconds and that the receipt of messages is being logged.
"""

import subprocess
import time
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_system_alerts():
    """Test the system alerts periodic task."""
    try:
        logger.info("Starting the FastAPI application...")
        
        # Start the FastAPI application in a subprocess
        process = subprocess.Popen(
            ["PYTHONPATH=. PORT=8000 python src/main.py"],
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for the application to start
        logger.info("Waiting for the application to start...")
        time.sleep(5)
        
        # Check if the process is still running
        if process.poll() is not None:
            logger.error("FastAPI application failed to start!")
            stdout, stderr = process.communicate()
            logger.error(f"STDOUT: {stdout}")
            logger.error(f"STDERR: {stderr}")
            return False
        
        # Wait for a few cycles of the periodic task
        logger.info("Waiting for periodic task cycles...")
        time.sleep(15)  # Wait for 3 cycles (5 seconds each)
        
        # Terminate the process
        logger.info("Terminating the FastAPI application...")
        process.terminate()
        
        # Get the output
        stdout, stderr = process.communicate(timeout=5)
        
        # Check for expected log messages
        published_count = stdout.count("Published periodic system alert message")
        received_count = stdout.count("Received system alert")
        
        logger.info(f"Found {published_count} publish messages and {received_count} receive messages")
        
        # Verify that messages were published and received
        if published_count >= 2 and received_count >= 2:
            logger.info("System alerts periodic task is working correctly!")
            return True
        else:
            logger.error("System alerts periodic task is not working correctly!")
            logger.error(f"STDOUT: {stdout}")
            logger.error(f"STDERR: {stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error testing system alerts: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting system alerts test...")
    
    result = test_system_alerts()
    
    if result:
        logger.info("System alerts test PASSED!")
        exit(0)
    else:
        logger.error("System alerts test FAILED!")
        exit(1)