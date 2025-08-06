"""
Router module for MSK Pub/Sub API endpoints.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from src.helpers.config import settings
from src.helpers import broker
from src.api.models import (
    HealthResponse, 
    ReadinessResponse,
    PublishResponse,
    MessageData,
    MessageResponse,
    TopicsResponse,
    MetricsResponse
)

# Configure logging
logger = logging.getLogger(__name__)

# Global variable to track start time
start_time = time.time()


# Create router
router = APIRouter()

# Define routes
@router.get('/health', response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""

    # Check if broker is connected
    broker_connected = broker.broker.is_connected if hasattr(broker.broker, 'is_connected') else True
    
    status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'msk_connected': broker_connected,
        'producer_ready': broker_connected,
        'consumer_ready': broker_connected
    }
    return status

@router.get('/ready', response_model=ReadinessResponse)
async def readiness_check():
    """Readiness check endpoint."""

    # Check if broker is connected
    broker_connected = broker.broker.is_connected if hasattr(broker.broker, 'is_connected') else True
    
    if broker_connected:
        return {'status': 'ready'}
    else:
        return JSONResponse(
            status_code=503,
            content={'status': 'not ready'}
        )

@router.post('/publish', response_model=PublishResponse)
async def publish_message(message_data: MessageData):
    """Publish a message to a Kafka topic."""

    try:
        topic = message_data.topic
        message = message_data.message
        key = message_data.key

        if not message:
            raise HTTPException(status_code=400, detail="Message is required")

        # Publish message using faststream
        timestamp = datetime.utcnow().isoformat()
        success = await broker.publish_message_to_kafka(
            topic=topic,
            message=message,
            key=key
        )

        if success:
            return {
                'status': 'success',
                'topic': topic,
                'key': key,
                'timestamp': timestamp
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to publish message")

    except Exception as e:
        logger.error(f"Error publishing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/messages', response_model=MessageResponse)
async def get_messages(
    limit: int = Query(50, description="Maximum number of messages to return"),
    topic: Optional[str] = Query(None, description="Filter messages by topic")
):
    try:
        filtered_messages = broker.message_buffer

        if topic:
            filtered_messages = [
                msg for msg in broker.message_buffer
                if msg['topic'] == topic
            ]

        # Return most recent messages
        recent_messages = filtered_messages[-limit:] if limit > 0 else filtered_messages

        return {
            'messages': recent_messages,
            'total_count': len(filtered_messages),
            'returned_count': len(recent_messages)
        }

    except Exception as e:
        logger.error(f"Error retrieving messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/topics', response_model=TopicsResponse)
async def get_topics():
    """Get information about subscribed topics."""

    return {
        'subscribed_topics': settings.TOPICS,
        'cluster_name': settings.CLUSTER_NAME,
        'consumer_group': settings.GROUP_ID
    }

@router.get('/metrics', response_model=MetricsResponse)
async def get_metrics():
    """Get basic application metrics."""

    try:
        topic_counts = {}
        for msg in broker.message_buffer:
            topic = msg['topic']
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

        metrics = {
            'buffer_size': len(broker.message_buffer),
            'max_buffer_size': broker.max_buffer_size,
            'messages_by_topic': topic_counts,
            'uptime_seconds': time.time() - start_time
        }

        return metrics

    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))