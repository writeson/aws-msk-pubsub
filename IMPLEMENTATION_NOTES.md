# Implementation Notes: Periodic System Alerts Task

## Overview

This document describes the implementation of a periodic task that runs every 5 seconds, publishes a message to the "system-alerts" topic, and logs the receipt of that message.

## Implementation Details

### 1. Periodic Task Function

A periodic task function called `system_alerts_task` was added to `src/helpers/broker.py`. This function:

- Runs in an infinite loop
- Creates a system alert message with a timestamp and other details
- Publishes the message to the "system-alerts" topic using the existing `publish_message_to_kafka` function
- Logs the publication of the message
- Waits for 5 seconds before the next iteration
- Includes error handling to ensure the task continues running even if an error occurs

```python
# Periodic task for system alerts
async def system_alerts_task():
    """
    Periodic task that runs every 5 seconds and publishes a message to the "system-alerts" topic.
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
            
            # Wait for 5 seconds before the next iteration
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Error in system alerts task: {e}")
            await asyncio.sleep(5)  # Still wait before retrying
```

### 2. System Alerts Subscriber

A subscriber for the "system-alerts" topic was added to `src/helpers/broker.py`. This subscriber:

- Handles incoming messages from the "system-alerts" topic
- Logs the receipt of the message
- Adds the message to the message buffer
- Includes error handling

```python
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
```

### 3. Starting and Stopping the Periodic Task

The periodic task is started when the application starts up and is properly cancelled when the application shuts down. This is done in `src/main.py`:

```python
# Task to store the system alerts background task
system_alerts_background_task = None

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize components on application startup."""
    global system_alerts_background_task
    
    logger.info("Starting FastAPI MSK pub/sub application with faststream...")
    
    # Start the broker
    await broker.start()
    logger.info("Kafka broker started successfully")
    
    # Start the system alerts periodic task
    system_alerts_background_task = asyncio.create_task(system_alerts_task())
    logger.info("System alerts periodic task started")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    global system_alerts_background_task
    
    logger.info("Shutting down FastAPI MSK pub/sub application...")
    
    # Cancel the system alerts task if it's running
    if system_alerts_background_task is not None:
        logger.info("Cancelling system alerts periodic task...")
        system_alerts_background_task.cancel()
        try:
            await system_alerts_background_task
        except asyncio.CancelledError:
            logger.info("System alerts periodic task cancelled successfully")
    
    # Stop the broker
    await broker.stop()
    logger.info("Kafka broker stopped")
```

### 4. Testing

A test script called `test_system_alerts.py` was created to verify that the periodic task is working correctly. The script:

- Starts the FastAPI application in a subprocess
- Waits for the application to start
- Waits for a few cycles of the periodic task
- Terminates the application
- Checks the output for expected log messages indicating that messages were published and received
- Reports whether the test passed or failed

## Conclusion

The implementation successfully meets the requirements:

1. A periodic task runs every 5 seconds
2. The task publishes a message to the "system-alerts" topic
3. The receipt of the message is logged

The task is properly started when the application starts up and is properly cancelled when the application shuts down. The implementation is robust, with error handling to ensure the task continues running even if an error occurs.