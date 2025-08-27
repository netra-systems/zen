# app/tests/services/test_streaming_service.py
"""Test streaming service functionality."""

import sys
from pathlib import Path

import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from netra_backend.app.services.streaming_service import (
    StreamChunk,
    StreamingService,
    StreamProtocol,
    TextStreamProcessor,
    get_streaming_service,
)

class TestStreamingService:
    """Test streaming service."""
    
    @pytest.mark.asyncio
    async def test_streaming_service_initialization(self):
        """Test service initialization."""
        service = StreamingService(buffer_size=50, chunk_delay_ms=10)
        assert service.buffer_size == 50
        assert service.chunk_delay_ms == 10
        assert len(service.active_streams) == 0
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
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
    
    @pytest.mark.asyncio
    async def test_get_streaming_service_singleton(self):
        """Test singleton pattern."""
        service1 = get_streaming_service()
        service2 = get_streaming_service()
        
        assert service1 is service2
    
    @pytest.mark.asyncio
    async def test_stream_buffer_performance_and_memory_management(self):
        """Test stream buffer performance under load and memory efficiency."""
        import asyncio
        import gc
        import time
        from netra_backend.app.services.streaming_service import StreamingService, StreamChunk
        
        # Create service with smaller buffer for faster testing
        service = StreamingService(buffer_size=10, chunk_delay_ms=1)
        
        # Test buffer fill performance
        start_time = time.time()
        test_chunks = []
        
        # Create stream chunks
        for i in range(25):  # 2.5x buffer size to test multiple buffer flushes
            chunk = StreamChunk(
                type="performance_test",
                data={"sequence": i, "payload": f"test_data_{i}" * 10},  # Some bulk
                metadata={"timestamp": time.time()}
            )
            test_chunks.append(chunk)
        
        # Create async generator from list
        async def async_chunks_generator():
            for chunk in test_chunks:
                yield chunk
        
        # Process chunks through buffer
        buffered_chunks = []
        async for buffer in service.buffer_stream(async_chunks_generator()):
            buffered_chunks.extend(buffer)
            
        chunk_processing_time = time.time() - start_time
        
        # Verify buffer performance
        assert len(buffered_chunks) == 25, f"Expected 25 chunks, got {len(buffered_chunks)}"
        assert chunk_processing_time < 0.5, f"Buffer processing took {chunk_processing_time}s, should be < 0.5s"
        
        # Test buffer memory efficiency - no memory leaks
        initial_objects = len(gc.get_objects())
        
        # Process large stream to test memory management
        async def large_chunks_generator():
            for i in range(100):
                chunk = StreamChunk(
                    type="memory_test",
                    data={"large_payload": "x" * 1000, "id": i},
                    metadata={"memory_test": True}
                )
                yield chunk
        
        # Process and immediately discard
        processed_buffers = 0
        async for buffer in service.buffer_stream(large_chunks_generator()):
            processed_buffers += 1
            # Explicitly delete buffer to free memory
            del buffer
        
        # Force garbage collection
        gc.collect()
        
        final_objects = len(gc.get_objects())
        memory_growth = final_objects - initial_objects
        
        # Verify efficient processing
        assert processed_buffers == 10, f"Expected 10 buffers (100/10), got {processed_buffers}"
        assert memory_growth < 50, f"Memory growth {memory_growth} objects, should be minimal"
        
        # Test buffer size configuration impact
        small_buffer_service = StreamingService(buffer_size=5)
        large_buffer_service = StreamingService(buffer_size=20)
        
        async def test_data_generator():
            for i in range(20):
                yield StreamChunk("test", f"data_{i}")
        
        # Count buffers with different buffer sizes
        small_buffer_count = 0
        async for buffer in small_buffer_service.buffer_stream(test_data_generator()):
            small_buffer_count += 1
        
        large_buffer_count = 0
        async for buffer in large_buffer_service.buffer_stream(test_data_generator()):
            large_buffer_count += 1
        
        # Smaller buffers should create more buffer flushes
        assert small_buffer_count == 4, f"Expected 4 small buffers, got {small_buffer_count}"
        assert large_buffer_count == 1, f"Expected 1 large buffer, got {large_buffer_count}"
        
        # Test buffer performance with concurrent streams
        async def process_concurrent_stream(stream_id: int, chunk_count: int):
            async def concurrent_stream_generator():
                for i in range(chunk_count):
                    yield StreamChunk(f"stream_{stream_id}", f"data_{i}")
            
            buffer_count = 0
            async for buffer in service.buffer_stream(concurrent_stream_generator()):
                buffer_count += 1
            return buffer_count
        
        # Run multiple streams concurrently
        concurrent_tasks = [
            process_concurrent_stream(i, 15) for i in range(3)
        ]
        
        concurrent_start = time.time()
        results = await asyncio.gather(*concurrent_tasks)
        concurrent_time = time.time() - concurrent_start
        
        # Verify concurrent processing
        assert all(r == 2 for r in results), f"Expected 2 buffers per stream, got {results}"
        assert concurrent_time < 1.0, f"Concurrent processing took {concurrent_time}s, should be < 1.0s"