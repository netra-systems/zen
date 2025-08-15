# app/services/streaming_service.py
"""
Production-grade streaming service for real-time data transmission.
Handles SSE, WebSocket, and HTTP streaming protocols.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, Optional, Protocol
from enum import Enum

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class StreamProtocol(Enum):
    """Supported streaming protocols."""
    SSE = "sse"
    WEBSOCKET = "websocket"
    HTTP_STREAM = "http_stream"


class StreamChunk:
    """Represents a single chunk in a stream."""
    
    def __init__(
        self,
        type: str,
        data: Any,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.type = type
        self.data = data
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()
        self.id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "id": self.id,
            "type": self.type,
            "data": self.data,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }
    
    def to_sse(self) -> str:
        """Convert to Server-Sent Events format."""
        event_data = json.dumps(self.to_dict())
        return f"id: {self.id}\nevent: {self.type}\ndata: {event_data}\n\n"
    
    def to_json(self) -> str:
        """Convert to JSON format."""
        return json.dumps(self.to_dict())


class StreamProcessor(Protocol):
    """Protocol for stream processors."""
    
    async def process(
        self,
        input_data: Any
    ) -> AsyncGenerator[Any, None]:
        """Process input and yield results."""
        ...


class StreamingService:
    """
    Manages streaming operations with proper buffering,
    error handling, and protocol support.
    """
    
    def __init__(
        self,
        buffer_size: int = 100,
        chunk_delay_ms: int = 50
    ):
        self.buffer_size = buffer_size
        self.chunk_delay_ms = chunk_delay_ms
        self.active_streams: Dict[str, Dict[str, Any]] = {}
    
    async def create_stream(
        self,
        processor: StreamProcessor,
        input_data: Any,
        protocol: StreamProtocol = StreamProtocol.HTTP_STREAM
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Create a new stream with the specified processor.
        """
        stream_id = str(uuid.uuid4())
        
        try:
            # Register stream
            self.active_streams[stream_id] = {
                "start_time": datetime.now(),
                "protocol": protocol,
                "chunk_count": 0
            }
            
            # Yield start chunk
            yield StreamChunk(
                type="stream_start",
                data={"stream_id": stream_id},
                metadata={"protocol": protocol.value}
            )
            
            # Process and yield data chunks
            async for result in processor.process(input_data):
                chunk = StreamChunk(
                    type="data",
                    data=result,
                    metadata={"stream_id": stream_id}
                )
                
                self.active_streams[stream_id]["chunk_count"] += 1
                yield chunk
                
                # Rate limiting
                if self.chunk_delay_ms > 0:
                    await asyncio.sleep(self.chunk_delay_ms / 1000)
            
            # Yield completion chunk
            yield StreamChunk(
                type="stream_end",
                data={"stream_id": stream_id},
                metadata={
                    "total_chunks": self.active_streams[stream_id]["chunk_count"],
                    "duration_ms": (
                        datetime.now() - self.active_streams[stream_id]["start_time"]
                    ).total_seconds() * 1000
                }
            )
            
        except Exception as e:
            logger.error(f"Stream {stream_id} error: {e}", exc_info=True)
            yield StreamChunk(
                type="error",
                data={"error": str(e)},
                metadata={"stream_id": stream_id}
            )
        
        finally:
            # Cleanup
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
    
    async def buffer_stream(
        self,
        stream: AsyncGenerator[StreamChunk, None]
    ) -> AsyncGenerator[list[StreamChunk], None]:
        """
        Buffer stream chunks for batch processing.
        """
        buffer = []
        
        async for chunk in stream:
            buffer.append(chunk)
            
            if len(buffer) >= self.buffer_size:
                yield buffer
                buffer = []
        
        # Yield remaining chunks
        if buffer:
            yield buffer
    
    def get_active_streams(self) -> Dict[str, Dict[str, Any]]:
        """Get information about active streams."""
        return {
            stream_id: {
                **info,
                "duration_seconds": (
                    datetime.now() - info["start_time"]
                ).total_seconds()
            }
            for stream_id, info in self.active_streams.items()
        }
    
    async def terminate_stream(self, stream_id: str) -> bool:
        """Terminate an active stream."""
        if stream_id in self.active_streams:
            del self.active_streams[stream_id]
            logger.info(f"Terminated stream {stream_id}")
            return True
        return False


class TextStreamProcessor:
    """Processor for streaming text content."""
    
    def __init__(self, chunk_size: int = 5):
        self.chunk_size = chunk_size
    
    async def process(
        self,
        text: str
    ) -> AsyncGenerator[str, None]:
        """Process text into chunks."""
        words = text.split()
        
        for i in range(0, len(words), self.chunk_size):
            chunk = words[i:i + self.chunk_size]
            yield ' '.join(chunk) + (' ' if i + self.chunk_size < len(words) else '')


# Singleton instance
_streaming_service: Optional[StreamingService] = None


def get_streaming_service() -> StreamingService:
    """Get or create streaming service instance."""
    global _streaming_service
    if _streaming_service is None:
        _streaming_service = StreamingService()
    return _streaming_service