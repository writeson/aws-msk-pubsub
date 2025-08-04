#!/usr/bin/env python3
"""
Flask application demonstrating MSK pub/sub functionality for EKS deployment.
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Dict, Any

from flask import Flask, request, jsonify, Response
from helpers.msk import MSKClient, MSKProducer, MSKConsumer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Global variables for MSK components
msk_client = None
producer = None
consumer = None
message_buffer = []
max_buffer_size = 1000

# Configuration
CLUSTER_NAME = os.getenv('MSK_CLUSTER_NAME', 'eks-pubsub-cluster')
REGION = os.getenv('AWS_REGION', 'us-east-1')
GROUP_ID = os.getenv('CONSUMER_GROUP_ID', 'eks-app-group')
TOPICS = os.getenv('KAFKA_TOPICS', 'user-events,system-alerts').split(',')
PORT = int(os.getenv('PORT', 8080))


def initialize_msk():
    """Initialize MSK client, producer, and consumer."""
    global msk_client, producer, consumer

    try:
        # Initialize MSK client
        msk_client = MSKClient(
            cluster_name=CLUSTER_NAME,
            region=REGION,
            security_protocol="SSL"
        )

        # Initialize producer
        producer = MSKProducer(msk_client)
        logger.info("MSK producer initialized successfully")

        # Initialize consumer
        consumer = MSKConsumer(
            msk_client=msk_client,
            group_id=GROUP_ID,
            topics=TOPICS,
            auto_offset_reset='latest'
        )
        logger.info("MSK consumer initialized successfully")

        return True

    except Exception as e:
        logger.error(f"Failed to initialize MSK components: {e}")
        return False


def message_handler(message):
    """Handle incoming messages from Kafka topics."""
    global message_buffer

    try:
        message_data = {
            'topic': message.topic,
            'partition': message.partition,
            'offset': message.offset,
            'key': message.key,
            'value': message.value,
            'timestamp': message.timestamp,
            'received_at': datetime.utcnow().isoformat()
        }

        # Add to buffer (with size limit)
        if len(message_buffer) >= max_buffer_size:
            message_buffer.pop(0)  # Remove oldest message

        message_buffer.append(message_data)

        logger.info(f"Processed message from {message.topic}: {message.key}")

    except Exception as e:
        logger.error(f"Error handling message: {e}")


def start_consumer():
    """Start the Kafka consumer in a separate thread."""
    if consumer:
        try:
            consumer.consume(message_handler, timeout_ms=1000)
        except Exception as e:
            logger.error(f"Consumer thread error: {e}")


# REST API endpoints
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'msk_connected': msk_client is not None,
        'producer_ready': producer is not None,
        'consumer_ready': consumer is not None
    }
    return jsonify(status)


@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check endpoint."""
    if msk_client and producer and consumer:
        return jsonify({'status': 'ready'}), 200
    else:
        return jsonify({'status': 'not ready'}), 503


@app.route('/publish', methods=['POST'])
def publish_message():
    """Publish a message to a Kafka topic."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        topic = data.get('topic', 'user-events')
        message = data.get('message', {})
        key = data.get('key')

        if not message:
            return jsonify({'error': 'Message is required'}), 400

        # Add metadata
        enriched_message = {
            'source': 'flask-api',
            'published_at': datetime.utcnow().isoformat(),
            'data': message
        }

        # Publish message
        success = producer.publish(
            topic=topic,
            message=enriched_message,
            key=key
        )

        if success:
            return jsonify({
                'status': 'success',
                'topic': topic,
                'key': key,
                'timestamp': enriched_message['published_at']
            }), 200
        else:
            return jsonify({'error': 'Failed to publish message'}), 500

    except Exception as e:
        logger.error(f"Error publishing message: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/messages', methods=['GET'])
def get_messages():
    """Get recent messages from the buffer."""
    try:
        limit = int(request.args.get('limit', 50))
        topic_filter = request.args.get('topic')

        filtered_messages = message_buffer

        if topic_filter:
            filtered_messages = [
                msg for msg in message_buffer
                if msg['topic'] == topic_filter
            ]

        # Return most recent messages
        recent_messages = filtered_messages[-limit:] if limit > 0 else filtered_messages

        return jsonify({
            'messages': recent_messages,
            'total_count': len(filtered_messages),
            'returned_count': len(recent_messages)
        })

    except Exception as e:
        logger.error(f"Error retrieving messages: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/topics', methods=['GET'])
def get_topics():
    """Get information about subscribed topics."""
    return jsonify({
        'subscribed_topics': TOPICS,
        'cluster_name': CLUSTER_NAME,
        'consumer_group': GROUP_ID
    })


@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Get basic application metrics."""
    try:
        topic_counts = {}
        for msg in message_buffer:
            topic = msg['topic']
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

        metrics = {
            'buffer_size': len(message_buffer),
            'max_buffer_size': max_buffer_size,
            'messages_by_topic': topic_counts,
            'uptime_seconds': time.time() - start_time
        }

        return jsonify(metrics)

    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/publish/bulk', methods=['POST'])
def publish_bulk_messages():
    """Publish multiple messages at once."""
    try:
        data = request.get_json()

        if not data or 'messages' not in data:
            return jsonify({'error': 'Messages array is required'}), 400

        messages = data['messages']
        if not isinstance(messages, list):
            return jsonify({'error': 'Messages must be an array'}), 400

        results = []

        for i, msg_data in enumerate(messages):
            topic = msg_data.get('topic', 'user-events')
            message = msg_data.get('message', {})
            key = msg_data.get('key', f'bulk_{i}')

            enriched_message = {
                'source': 'flask-api-bulk',
                'published_at': datetime.utcnow().isoformat(),
                'batch_index': i,
                'data': message
            }

            success = producer.publish(
                topic=topic,
                message=enriched_message,
                key=key
            )

            results.append({
                'index': i,
                'success': success,
                'topic': topic,
                'key': key
            })

        successful_count = sum(1 for r in results if r['success'])

        return jsonify({
            'total_messages': len(messages),
            'successful': successful_count,
            'failed': len(messages) - successful_count,
            'results': results
        })

    except Exception as e:
        logger.error(f"Error publishing bulk messages: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/stream', methods=['GET'])
def stream_messages():
    """Server-sent events endpoint for real-time message streaming."""

    def generate():
        last_index = 0
        while True:
            # Send new messages
            if len(message_buffer) > last_index:
                new_messages = message_buffer[last_index:]
                for msg in new_messages:
                    yield f"data: {json.dumps(msg)}\n\n"
                last_index = len(message_buffer)

            time.sleep(1)  # Poll every second

    return Response(generate(), mimetype='text/plain')


# Global variable to track start time
start_time = time.time()

if __name__ == '__main__':
    logger.info("Starting Flask MSK pub/sub application...")

    # Initialize MSK components
    if not initialize_msk():
        logger.error("Failed to initialize MSK components, exiting...")
        exit(1)

    # Start consumer in background thread
    consumer_thread = threading.Thread(target=start_consumer, daemon=True)
    consumer_thread.start()
    logger.info("Consumer thread started")

    # Start Flask application
    logger.info(f"Starting Flask app on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)