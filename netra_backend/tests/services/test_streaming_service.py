# app/tests/services/test_streaming_service.py
"""Test streaming service functionality."""

import pytest
import asyncio
from typing import AsyncGenerator
from unittest.mock import Mock, AsyncMock

from netra_backend.app.services.streaming_service import (
    StreamingService,
    StreamChunk,
    StreamProtocol,
    TextStreamProcessor,
    get_streaming_service
)
class TestStreamingService:
    """Test streaming service."""
    
    async def test_streaming_service_initialization(self):
        """Test service initialization."""
        service = StreamingService(buffer_size=50, chunk_delay_ms=10)
        assert service.buffer_size == 50
        assert service.chunk_delay_ms == 10
        assert len(service.active_streams) == 0
    
    async def test_text_stream_processor(self):
        """Test text stream processor."""
        processor = TextStreamProcessor(chunk_size=3)
        text = "This is a test message for streaming"
        
        chunks = []
        async for chunk in processor.process(text):
            chunks.append(chunk)
        
        # Should split into chunks of 3 words
        assert len(chunks) == 3
        assert chunks[0] == "This is a "
        assert chunks[1] == "test message for "
        assert chunks[2] == "streaming"
    
    async def test_stream_chunk_creation(self):
        """Test stream chunk creation."""
        chunk = StreamChunk(
            type="data",
            data="test data",
            metadata={"key": "value"}
        )
        
        assert chunk.type == "data"
        assert chunk.data == "test data"
        assert chunk.metadata == {"key": "value"}
        assert chunk.id is not None
        assert chunk.timestamp is not None
        
        # Test conversions
        dict_data = chunk.to_dict()
        assert dict_data["type"] == "data"
        assert dict_data["data"] == "test data"
        
        sse_data = chunk.to_sse()
        assert f"id: {chunk.id}" in sse_data
        assert "event: data" in sse_data
        
        json_data = chunk.to_json()
        assert "data" in json_data
    
    async def test_create_stream_success(self):
        """Test successful stream creation."""
        service = StreamingService(chunk_delay_ms=0)
        
        # Create mock processor
        class TestProcessor:
            async def process(self, data):
                for i in range(3):
                    yield f"chunk_{i}"
        
        processor = TestProcessor()
        chunks = []
        
        async for chunk in service.create_stream(processor, None):
            chunks.append(chunk)
        
        # Should have start, 3 data chunks, and end
        assert len(chunks) == 5
        assert chunks[0].type == "stream_start"
        assert chunks[1].type == "data"
        assert chunks[1].data == "chunk_0"
        assert chunks[-1].type == "stream_end"
    
    async def test_create_stream_with_error(self):
        """Test stream creation with error."""
        service = StreamingService()
        
        # Create processor that raises error
        class ErrorProcessor:
            async def process(self, data):
                yield "chunk_1"
                raise ValueError("Test error")
        
        processor = ErrorProcessor()
        chunks = []
        
        async for chunk in service.create_stream(processor, None):
            chunks.append(chunk)
        
        # Should have start, one data chunk, and error
        assert len(chunks) == 3
        assert chunks[0].type == "stream_start"
        assert chunks[1].type == "data"
        assert chunks[2].type == "error"
        assert "Test error" in chunks[2].data["error"]
    
    async def test_buffer_stream(self):
        """Test stream buffering."""
        service = StreamingService(buffer_size=2)
        
        # Create test chunks
        async def generate_chunks():
            for i in range(5):
                yield StreamChunk("data", f"chunk_{i}")
        
        buffers = []
        async for buffer in service.buffer_stream(generate_chunks()):
            buffers.append(buffer)
        
        # Should have 3 buffers: [2, 2, 1]
        assert len(buffers) == 3
        assert len(buffers[0]) == 2
        assert len(buffers[1]) == 2
        assert len(buffers[2]) == 1
    
    async def test_active_streams_tracking(self):
        """Test active streams tracking."""
        service = StreamingService(chunk_delay_ms=0)
        
        class SlowProcessor:
            async def process(self, data):
                for i in range(2):
                    yield f"chunk_{i}"
                    # Check active streams during processing
                    active = service.get_active_streams()
                    assert len(active) == 1
        
        processor = SlowProcessor()
        
        # Process stream
        chunks = []
        async for chunk in service.create_stream(processor, None):
            chunks.append(chunk)
        
        # After completion, no active streams
        assert len(service.get_active_streams()) == 0
    
    async def test_terminate_stream(self):
        """Test stream termination."""
        service = StreamingService()
        
        # Manually add a stream
        stream_id = "test_stream_123"
        service.active_streams[stream_id] = {
            "start_time": asyncio.get_event_loop().time(),
            "protocol": StreamProtocol.HTTP_STREAM,
            "chunk_count": 0
        }
        
        assert len(service.active_streams) == 1
        
        # Terminate stream
        result = await service.terminate_stream(stream_id)
        assert result is True
        assert len(service.active_streams) == 0
        
        # Try terminating non-existent stream
        result = await service.terminate_stream("non_existent")
        assert result is False
    
    async def test_get_streaming_service_singleton(self):
        """Test singleton pattern."""
        service1 = get_streaming_service()
        service2 = get_streaming_service()
        
        assert service1 is service2