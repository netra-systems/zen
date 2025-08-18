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
        self._initialize_attributes(type, data, metadata)
    
    def _initialize_attributes(
        self,
        type: str,
        data: Any,
        metadata: Optional[Dict[str, Any]]
    ) -> None:
        """Initialize StreamChunk attributes."""
        self.type = type
        self.data = data
        self._set_chunk_metadata(metadata)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return self._build_dict_representation()
    
    def _build_dict_representation(self) -> Dict[str, Any]:
        """Build dictionary representation of chunk."""
        base_data = {"id": self.id, "type": self.type, "data": self.data}
        extra_data = {"metadata": self.metadata, "timestamp": self.timestamp}
        return {**base_data, **extra_data}
    
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
        self._initialize_service_config(buffer_size, chunk_delay_ms)
    
    def _initialize_service_config(
        self,
        buffer_size: int,
        chunk_delay_ms: int
    ) -> None:
        """Initialize streaming service configuration."""
        self.buffer_size = buffer_size
        self.chunk_delay_ms = chunk_delay_ms
        self.active_streams: Dict[str, Dict[str, Any]] = {}
    
    def _generate_stream_id(self) -> str:
        """Generate unique stream identifier."""
        return str(uuid.uuid4())
    
    def _register_stream(
        self,
        stream_id: str,
        protocol: StreamProtocol
    ) -> None:
        """Register new stream in active streams tracking."""
        self.active_streams[stream_id] = self._build_stream_info(protocol)
    
    def _build_stream_info(self, protocol: StreamProtocol) -> Dict[str, Any]:
        """Build stream information dictionary."""
        return {"start_time": datetime.now(), "protocol": protocol, "chunk_count": 0}
    
    def _create_start_chunk(
        self,
        stream_id: str,
        protocol: StreamProtocol
    ) -> StreamChunk:
        """Create stream start notification chunk."""
        return self._build_start_chunk(stream_id, protocol)
    
    def _build_start_chunk(
        self,
        stream_id: str,
        protocol: StreamProtocol
    ) -> StreamChunk:
        """Build stream start chunk with data and metadata."""
        data = {"stream_id": stream_id}
        metadata = {"protocol": protocol.value}
        return StreamChunk(type="stream_start", data=data, metadata=metadata)
    
    async def _process_data_chunks(
        self,
        processor: StreamProcessor,
        input_data: Any,
        stream_id: str
    ) -> AsyncGenerator[StreamChunk, None]:
        """Process input data and yield data chunks with rate limiting."""
        async for result in processor.process(input_data):
            yield await self._yield_processed_chunk(result, stream_id)
    
    async def _yield_processed_chunk(
        self,
        result: Any,
        stream_id: str
    ) -> StreamChunk:
        """Yield a processed chunk with tracking and rate limiting."""
        chunk = self._create_data_chunk(result, stream_id)
        self._increment_chunk_count(stream_id)
        await self._apply_rate_limiting()
        return chunk
    
    def _create_data_chunk(
        self,
        result: Any,
        stream_id: str
    ) -> StreamChunk:
        """Create data chunk from processor result."""
        return self._build_data_chunk(result, stream_id)
    
    def _build_data_chunk(
        self,
        result: Any,
        stream_id: str
    ) -> StreamChunk:
        """Build data chunk with result and metadata."""
        metadata = {"stream_id": stream_id}
        return StreamChunk(type="data", data=result, metadata=metadata)
    
    def _increment_chunk_count(self, stream_id: str) -> None:
        """Increment chunk counter for stream tracking."""
        self.active_streams[stream_id]["chunk_count"] += 1
    
    async def _apply_rate_limiting(self) -> None:
        """Apply rate limiting delay if configured."""
        if self.chunk_delay_ms > 0:
            await asyncio.sleep(self.chunk_delay_ms / 1000)
    
    def _create_completion_chunk(self, stream_id: str) -> StreamChunk:
        """Create stream completion notification chunk."""
        stream_info = self.active_streams[stream_id]
        duration_ms = self._calculate_stream_duration(stream_info)
        return self._build_completion_chunk(stream_id, stream_info, duration_ms)
    
    def _calculate_stream_duration(self, stream_info: Dict[str, Any]) -> float:
        """Calculate stream duration in milliseconds."""
        return (datetime.now() - stream_info["start_time"]).total_seconds() * 1000
    
    def _build_completion_chunk(
        self,
        stream_id: str,
        stream_info: Dict[str, Any],
        duration_ms: float
    ) -> StreamChunk:
        """Build completion chunk with metrics."""
        data = {"stream_id": stream_id}
        metadata = {"total_chunks": stream_info["chunk_count"], "duration_ms": duration_ms}
        return StreamChunk(type="stream_end", data=data, metadata=metadata)
    
    def _create_error_chunk(
        self,
        stream_id: str,
        error: Exception
    ) -> StreamChunk:
        """Create error notification chunk."""
        return self._build_error_chunk(stream_id, error)
    
    def _build_error_chunk(
        self,
        stream_id: str,
        error: Exception
    ) -> StreamChunk:
        """Build error chunk with error information."""
        data = {"error": str(error)}
        metadata = {"stream_id": stream_id}
        return StreamChunk(type="error", data=data, metadata=metadata)
    
    def _cleanup_stream(self, stream_id: str) -> None:
        """Remove stream from active streams tracking."""
        if stream_id in self.active_streams:
            del self.active_streams[stream_id]
    
    async def create_stream(
        self,
        processor: StreamProcessor,
        input_data: Any,
        protocol: StreamProtocol = StreamProtocol.HTTP_STREAM
    ) -> AsyncGenerator[StreamChunk, None]:
        """Create a new stream with the specified processor."""
        stream_id = self._generate_stream_id()
        async for chunk in self._execute_stream(stream_id, processor, input_data, protocol):
            yield chunk
    
    async def _execute_stream(
        self,
        stream_id: str,
        processor: StreamProcessor,
        input_data: Any,
        protocol: StreamProtocol
    ) -> AsyncGenerator[StreamChunk, None]:
        """Execute stream processing with error handling."""
        try:
            async for chunk in self._run_stream_pipeline(stream_id, processor, input_data, protocol):
                yield chunk
        except Exception as e:
            logger.error(f"Stream {stream_id} error: {e}", exc_info=True)
            yield self._create_error_chunk(stream_id, e)
        finally:
            self._cleanup_stream(stream_id)
    
    async def _run_stream_pipeline(
        self,
        stream_id: str,
        processor: StreamProcessor,
        input_data: Any,
        protocol: StreamProtocol
    ) -> AsyncGenerator[StreamChunk, None]:
        """Run the complete stream processing pipeline."""
        self._register_stream(stream_id, protocol)
        yield self._create_start_chunk(stream_id, protocol)
        async for chunk in self._process_data_chunks(processor, input_data, stream_id):
            yield chunk
        yield self._create_completion_chunk(stream_id)
    
    async def buffer_stream(
        self,
        stream: AsyncGenerator[StreamChunk, None]
    ) -> AsyncGenerator[list[StreamChunk], None]:
        """Buffer stream chunks for batch processing."""
        buffer = []
        async for chunk in stream:
            full_buffer = await self._process_buffered_chunk(buffer, chunk)
            if full_buffer is not None:
                yield full_buffer
                buffer = []
        if buffer:
            yield buffer
    
    async def _process_buffered_chunk(
        self,
        buffer: list[StreamChunk],
        chunk: StreamChunk
    ) -> Optional[list[StreamChunk]]:
        """Process a chunk into buffer and return full buffer if ready."""
        buffer.append(chunk)
        return buffer.copy() if len(buffer) >= self.buffer_size else None
    
    def get_active_streams(self) -> Dict[str, Dict[str, Any]]:
        """Get information about active streams."""
        return self._build_active_streams_info()
    
    def _build_active_streams_info(self) -> Dict[str, Dict[str, Any]]:
        """Build active streams information with duration."""
        return {stream_id: self._build_stream_info_with_duration(info) for stream_id, info in self.active_streams.items()}
    
    def _build_stream_info_with_duration(
        self,
        info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build stream info including duration calculation."""
        duration_seconds = (datetime.now() - info["start_time"]).total_seconds()
        return {**info, "duration_seconds": duration_seconds}
    
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
            suffix = ' ' if i + self.chunk_size < len(words) else ''
            yield ' '.join(chunk) + suffix


# Singleton instance
_streaming_service: Optional[StreamingService] = None


def get_streaming_service() -> StreamingService:
    """Get or create streaming service instance."""
    global _streaming_service
    if _streaming_service is None:
        _streaming_service = StreamingService()
    return _streaming_service

# Helper method to add to StreamChunk
def _set_chunk_metadata(self, metadata: Optional[Dict[str, Any]]) -> None:
    """Set chunk metadata and generate unique identifiers."""
    self.metadata = metadata or {}
    self.timestamp = datetime.now().isoformat()
    self.id = str(uuid.uuid4())

# Add method to StreamChunk class
StreamChunk._set_chunk_metadata = _set_chunk_metadata