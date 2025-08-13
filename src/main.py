#!/usr/bin/env python3
"""
FastAPI application demonstrating MSK pub/sub functionality for EKS deployment.
Using faststream for Kafka integration.
"""

import logging
import asyncio

from fastapi import FastAPI
from src.api.router import router
from src.helpers.config import settings
from src.helpers.broker import broker, system_alerts_task

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

# Include router in app
app.include_router(router, prefix="/api/v1", tags=["MSK Pub/Sub"])

# Task to store the system alerts background task
system_alerts_background_task = None

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """
    Initialize components on application startup.

    :return: None. Starts Kafka broker and schedules the background system alerts task.
    """
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
    """
    Clean up resources on application shutdown.

    :return: None. Cancels background tasks and stops the Kafka broker gracefully.
    """
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


if __name__ == '__main__':
    import uvicorn

    logger.info(f"Starting FastAPI app on port {settings.PORT}")
    uvicorn.run("src.main:app", host="0.0.0.0", port=settings.PORT, log_level="info")
