

import os
from dataclasses import dataclass
from typing import Final


@dataclass
class Settings:
    """
    Configuration settings for the application.

    Attributes:
        CLUSTER_NAME (str): Name of the MSK cluster.
        BOOTSTRAP_SERVERS (str): Kafka bootstrap servers.
        REGION (str): AWS region.
        GROUP_ID (str): Consumer group ID.
        TOPICS (list[str]): List of Kafka topics to subscribe to.
        PORT (int): Port for the application to run on.
    """

    CLUSTER_NAME: str = os.getenv('MSK_CLUSTER_NAME', 'eks-pubsub-cluster')
    BOOTSTRAP_SERVERS: str = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    REGION: str = os.getenv('AWS_REGION', 'us-east-1')
    GROUP_ID: str = os.getenv('CONSUMER_GROUP_ID', 'eks-app-group')
    TOPICS: list[str] = None  # Will be set in __post_init__
    PORT: int = int(os.getenv('PORT', 8000))
    SECURITY_PROTOCOL: str = None  # Will be set in __post_init__
    AUTO_OFFSET_RESET: str = os.getenv('AUTO_OFFSET_RESET', 'latest')
    MAX_BUFFER_SIZE: int = int(os.getenv('MAX_BUFFER_SIZE', 1000))

    def __post_init__(self):
        """Post-initialization to handle complex field assignments."""
        # Parse topics from environment variable
        topics_env = os.getenv('KAFKA_TOPICS', 'user-events,system-alerts')
        self.TOPICS = [topic.strip() for topic in topics_env.split(',')]

        # Set security protocol based on bootstrap servers
        self.SECURITY_PROTOCOL = (
            "PLAINTEXT" if self.BOOTSTRAP_SERVERS == "localhost:9092" else "SSL"
        )


# Module-level settings instance (Singleton pattern)
settings: Final[Settings] = Settings()