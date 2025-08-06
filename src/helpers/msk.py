#!/usr/bin/env python3
"""
Python Kafka client for connecting to AWS MSK from EKS applications.
This demonstrates pub/sub patterns for your EKS-based applications.
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
import threading

import boto3
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError

# Configure logging
# Note: Main logging configuration is in main.py
logger = logging.getLogger(__name__)

# Set DEBUG level for kafka loggers to help with troubleshooting
# logging.getLogger('kafka').setLevel(logging.DEBUG)
# logging.getLogger('kafka.conn').setLevel(logging.WARNING)  # Set to WARNING in main.py


class MSKClient:
    """
    AWS MSK client for pub/sub operations from EKS applications.
    """

    def __init__(
            self,
            cluster_name: str,
            bootstrap_servers: Optional[str] = None,
            region: str = "us-east-1",
            security_protocol: str = "SSL",
            client_id: Optional[str] = None
    ):
        self.cluster_name = cluster_name
        self.region = region
        self.security_protocol = security_protocol
        self.client_id = client_id or f"eks-app-{int(time.time())}"
        self.bootstrap_servers = None
        self._running = True

        # Initialize MSK client
        if bootstrap_servers:
            self.bootstrap_servers = bootstrap_servers
            logger.info(f"Using provided bootstrap servers: {self.bootstrap_servers}")
        else:
            self.bootstrap_servers = None
            # Initialize MSK client only if we need to discover brokers
            self.msk_client = boto3.client('kafka', region_name=region)
            self._get_bootstrap_servers()

    def _get_bootstrap_servers(self) -> None:
        """Get bootstrap servers from MSK cluster."""
        try:
            response = self.msk_client.get_bootstrap_brokers(
                ClusterArn=self._get_cluster_arn()
            )

            if self.security_protocol == "SSL":
                self.bootstrap_servers = response['BootstrapBrokerStringTls']
            else:
                self.bootstrap_servers = response['BootstrapBrokerString']

            logger.info(f"Bootstrap servers: {self.bootstrap_servers}")

        except Exception as e:
            logger.error(f"Failed to get bootstrap servers: {e}")
            raise

    def _get_cluster_arn(self) -> str:
        """Get the full ARN of the MSK cluster."""
        try:
            response = self.msk_client.list_clusters()
            for cluster in response['ClusterInfoList']:
                if cluster['ClusterName'] == self.cluster_name:
                    return cluster['ClusterArn']
            raise ValueError(f"Cluster {self.cluster_name} not found")
        except Exception as e:
            logger.error(f"Failed to get cluster ARN: {e}")
            raise


class MSKProducer:
    """
    Kafka producer for publishing messages to MSK topics.
    """

    def __init__(self, msk_client: MSKClient):
        self.msk_client = msk_client
        self.producer = None
        self._connect()

    def _connect(self):
        """Initialize Kafka producer with retry logic."""
        producer_config = {
            'bootstrap_servers': self.msk_client.bootstrap_servers,
            'client_id': f"{self.msk_client.client_id}-producer",
            'value_serializer': lambda v: json.dumps(v).encode('utf-8'),
            'key_serializer': lambda k: k.encode('utf-8') if k else None,
            'acks': 'all',  # Wait for all replicas
            'retries': 5,  # Increased retries
            'retry_backoff_ms': 2000,  # Increased backoff
            'request_timeout_ms': 60000,  # Increased timeout
            'connections_max_idle_ms': 180000,  # Keep connections alive longer
            'reconnect_backoff_ms': 2000,  # Increased reconnect backoff
            'reconnect_backoff_max_ms': 10000,  # Max reconnect backoff
            'compression_type': None,  # No compression for local development
            'api_version_auto_timeout_ms': 60000,  # Increased API version discovery timeout
            # Removed unsupported parameters:
            # 'socket_connection_setup_timeout_ms': 60000
            # 'socket_timeout_ms': 60000
        }

        if self.msk_client.security_protocol == "SSL":
            producer_config.update({
                'security_protocol': 'SSL',
                'ssl_check_hostname': True,
                'ssl_cafile': None,  # Use system CA bundle
            })

        # Add retry logic for producer connection
        max_retries = 3
        retry_delay = 5  # seconds

        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect producer (attempt {attempt+1}/{max_retries})")
                self.producer = KafkaProducer(**producer_config)
                logger.info("Kafka producer connected successfully")
                return
            except Exception as e:
                logger.warning(f"Producer connection attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to connect producer after {max_retries} attempts: {e}")
                    raise

    def publish(
            self,
            topic: str,
            message: Dict[str, Any],
            key: Optional[str] = None,
            partition: Optional[int] = None
    ) -> bool:
        """
        Publish a message to a Kafka topic.

        Args:
            topic: Kafka topic name
            message: Message data (will be JSON serialized)
            key: Optional message key for partitioning
            partition: Optional specific partition

        Returns:
            True if message was sent successfully
        """
        try:
            # Add metadata to message
            enriched_message = {
                'timestamp': datetime.utcnow().isoformat(),
                'producer_id': self.msk_client.client_id,
                'data': message
            }

            future = self.producer.send(
                topic=topic,
                value=enriched_message,
                key=key,
                partition=partition
            )

            # Wait for confirmation
            record_metadata = future.get(timeout=10)

            logger.info(
                f"Message sent to {record_metadata.topic} "
                f"partition {record_metadata.partition} "
                f"offset {record_metadata.offset}"
            )
            return True

        except KafkaError as e:
            logger.error(f"Failed to send message to {topic}: {e}")
            return False

    def close(self):
        """Close the producer connection."""
        if self.producer:
            self.producer.close()
            logger.info("Producer connection closed")


class MSKConsumer:
    """
    Kafka consumer for subscribing to MSK topics.
    """

    def __init__(
            self,
            msk_client: MSKClient,
            group_id: str,
            topics: List[str],
            auto_offset_reset: str = 'latest'
    ):
        self.msk_client = msk_client
        self.group_id = group_id
        self.topics = topics
        self.auto_offset_reset = auto_offset_reset
        self.consumer = None
        self._running = True
        self._connect()

    def _connect(self):
        """Initialize Kafka consumer with retry logic."""
        consumer_config = {
            'bootstrap_servers': self.msk_client.bootstrap_servers,
            'client_id': f"{self.msk_client.client_id}-consumer",
            'group_id': self.group_id,
            'auto_offset_reset': self.auto_offset_reset,
            'enable_auto_commit': True,
            'auto_commit_interval_ms': 1000,
            'session_timeout_ms': 30000,  # Reduced timeout for local development
            'heartbeat_interval_ms': 3000,  # Reduced heartbeat for local development
            'max_poll_records': 100,
            'value_deserializer': lambda m: json.loads(m.decode('utf-8')),
            'key_deserializer': lambda m: m.decode('utf-8') if m else None,
            'request_timeout_ms': 60000,  # Increased timeout
            'connections_max_idle_ms': 180000,  # Keep connections alive longer
            'reconnect_backoff_ms': 2000,  # Increased reconnect backoff
            'reconnect_backoff_max_ms': 10000,  # Max reconnect backoff
            'api_version_auto_timeout_ms': 60000,  # Increased API version discovery timeout
            # Removed unsupported parameters:
            # 'socket_connection_setup_timeout_ms': 60000
            # 'socket_timeout_ms': 60000
        }

        if self.msk_client.security_protocol == "SSL":
            consumer_config.update({
                'security_protocol': 'SSL',
                'ssl_check_hostname': True,
                'ssl_cafile': None,  # Use system CA bundle
            })

        # Add retry logic for consumer connection
        max_retries = 3
        retry_delay = 5  # seconds

        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect consumer (attempt {attempt+1}/{max_retries})")
                self.consumer = KafkaConsumer(**consumer_config)
                self.consumer.subscribe(self.topics)
                logger.info(f"Kafka consumer connected and subscribed to {self.topics}")
                return
            except Exception as e:
                logger.warning(f"Consumer connection attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to connect consumer after {max_retries} attempts: {e}")
                    raise

    def consume(self, message_handler: callable, timeout_ms: int = 1000):
        """
        Start consuming messages from subscribed topics.

        Args:
            message_handler: Function to handle received messages
            timeout_ms: Polling timeout in milliseconds
        """
        logger.info("Starting message consumption...")

        try:
            while self._running:
                message_batch = self.consumer.poll(timeout_ms=timeout_ms)

                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        try:
                            message_handler(message)
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")

        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        except Exception as e:
            logger.error(f"Consumer error: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stop the consumer."""
        self._running = False
        if self.consumer:
            self.consumer.close()
            logger.info("Consumer connection closed")


# Example usage and message handlers
def example_message_handler(message):
    """Example message handler for processing received messages."""
    logger.info(
        f"Received message from {message.topic} "
        f"partition {message.partition} "
        f"offset {message.offset}: {message.value}"
    )


def main():
    """
    Example usage of MSK pub/sub client.
    Set environment variables or modify these values:
    """

    # Configuration - get from environment or K8s secrets
    CLUSTER_NAME = os.getenv('MSK_CLUSTER_NAME', 'eks-pubsub-cluster')
    REGION = os.getenv('AWS_REGION', 'us-east-1')
    GROUP_ID = os.getenv('CONSUMER_GROUP_ID', 'eks-app-group')
    TOPICS = os.getenv('KAFKA_TOPICS', 'user-events,system-alerts').split(',')

    # Initialize MSK client
    msk_client = MSKClient(
        cluster_name=CLUSTER_NAME,
        region=REGION,
        security_protocol="SSL"
    )

    # Example 1: Producer usage
    producer = MSKProducer(msk_client)

    # Publish some example messages
    for i in range(5):
        message = {
            'event_type': 'user_action',
            'user_id': f'user_{i}',
            'action': 'page_view',
            'metadata': {'page': '/dashboard', 'session_id': f'session_{i}'}
        }

        producer.publish(
            topic='user-events',
            message=message,
            key=f'user_{i}'
        )
        time.sleep(1)

    # Example 2: Consumer usage
    consumer = MSKConsumer(
        msk_client=msk_client,
        group_id=GROUP_ID,
        topics=TOPICS,
        auto_offset_reset='earliest'
    )

    # Handle shutdown gracefully
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        consumer.stop()
        producer.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start consuming (this will block)
    consumer.consume(example_message_handler)


if __name__ == "__main__":
    main()
