
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field

# Define Pydantic models for request/response data
class MessageData(BaseModel):
    topic: str = Field(default="user-events", description="Kafka topic to publish to")
    message: Dict[str, Any] = Field(..., description="Message content to publish")
    key: Optional[str] = Field(None, description="Optional message key")

class BulkMessageRequest(BaseModel):
    messages: List[MessageData] = Field(..., description="List of messages to publish")

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    msk_connected: bool
    producer_ready: bool
    consumer_ready: bool

class ReadinessResponse(BaseModel):
    status: str

class PublishResponse(BaseModel):
    status: str
    topic: str
    key: Optional[str]
    timestamp: str

class MessageResponse(BaseModel):
    messages: List[Dict[str, Any]]
    total_count: int
    returned_count: int

class TopicsResponse(BaseModel):
    subscribed_topics: List[str]
    cluster_name: str
    consumer_group: str

class MetricsResponse(BaseModel):
    buffer_size: int
    max_buffer_size: int
    messages_by_topic: Dict[str, int]
    uptime_seconds: float

class BulkPublishResult(BaseModel):
    index: int
    success: bool
    topic: str
    key: str

class BulkPublishResponse(BaseModel):
    total_messages: int
    successful: int
    failed: int
    results: List[BulkPublishResult]
