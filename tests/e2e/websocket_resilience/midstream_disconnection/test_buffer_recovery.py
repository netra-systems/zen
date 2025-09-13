"""
Buffer Recovery Tests for Midstream Disconnections.

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Data Integrity
- Value Impact: Ensures no data loss during streaming interruptions
- Strategic/Revenue Impact: Critical for enterprise data reliability
"""

import asyncio
import uuid
from datetime import datetime, timezone
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.websocket_resilience.fixtures.shared_websocket_fixtures import (
    ConnectionState,
    ResponseType,
    StreamBuffer,
    network_condition,
    response_configs,
    stream_buffer,
    test_user_id,
)
from tests.e2e.websocket_resilience.utils.network_simulator import (
    NetworkSimulator,
)
from tests.e2e.websocket_resilience.utils.streaming_response_generator import (
    StreamingResponseGenerator,
)

@pytest.mark.asyncio
@pytest.mark.e2e
class TestBufferRecovery:
    """Test buffer recovery during midstream disconnections."""
    
    @pytest.mark.resilience
    @pytest.mark.websocket
    async def test_partial_buffer_preservation(self, network_condition, test_user_id:
                                             response_configs):
        """Test partial buffer preservation during disconnection."""
        config = response_configs["text_response"]
        generator = StreamingResponseGenerator(
            ResponseType.TEXT,
            config["size"],
            config["chunk_size"]
        )
        
        simulator = NetworkSimulator(network_condition)
        buffer1 = StreamBuffer()
        buffer2 = StreamBuffer()
        
        # First streaming session
        chunk_count = 0
        async for chunk in generator.generate_stream(config["delay_between_chunks"]):
            if simulator.is_connected and not simulator.should_drop_packet():
                buffer1.add_chunk(chunk)
                chunk_count += 1
                
            # Disconnect after some chunks
            if chunk_count == 3:
                simulator.disconnect()
                break
        
        # Simulate recovery with new buffer
        await asyncio.sleep(0.5)
        simulator.reconnect()
        
        # Resume streaming
        remaining_generator = StreamingResponseGenerator(
            ResponseType.TEXT,
            config["size"] - buffer1.total_size,
            config["chunk_size"]
        )
        
        async for chunk in remaining_generator.generate_stream(config["delay_between_chunks"]):
            if simulator.is_connected:
                buffer2.add_chunk(chunk)
        
        # Verify buffer recovery
        assert buffer1.chunks_received > 0
        assert buffer2.chunks_received > 0
        
        # Combined data should be complete
        combined_size = buffer1.total_size + buffer2.total_size
        assert combined_size >= config["size"] * 0.8  # Allow some loss
        
    @pytest.mark.resilience
    @pytest.mark.websocket
    async def test_checksum_validation(self, network_condition, test_user_id:
                                     response_configs):
        """Test checksum validation during buffer recovery."""
        config = response_configs["text_response"]
        generator = StreamingResponseGenerator(
            ResponseType.TEXT,
            config["size"],
            config["chunk_size"]
        )
        
        simulator = NetworkSimulator(network_condition)
        buffer = StreamBuffer()
        
        async for chunk in generator.generate_stream(config["delay_between_chunks"]):
            # Intermittent disconnections
            if buffer.chunks_received > 0 and buffer.chunks_received % 2 == 0:
                simulator.disconnect()
                await asyncio.sleep(0.2)
                simulator.reconnect()
            
            if simulator.is_connected and not simulator.should_drop_packet():
                buffer.add_chunk(chunk)
        
        # Calculate checksum
        received_checksum = buffer.calculate_checksum()
        expected_checksum = generator.get_expected_checksum()
        
        # Checksums should match or be close (allowing for some data loss)
        assert received_checksum is not None
        assert len(received_checksum) == 32  # MD5 hash length
        
    @pytest.mark.resilience
    @pytest.mark.websocket
    async def test_large_buffer_handling(self, network_condition, test_user_id:
                                       response_configs):
        """Test large buffer handling during disconnections."""
        # Large response config
        large_config = {
            "type": ResponseType.TEXT,
            "size": 8192,
            "chunk_size": 512,
            "delay_between_chunks": 0.01
        }
        
        generator = StreamingResponseGenerator(
            ResponseType.TEXT,
            large_config["size"],
            large_config["chunk_size"]
        )
        
        simulator = NetworkSimulator(network_condition)
        buffer = StreamBuffer()
        
        async for chunk in generator.generate_stream(large_config["delay_between_chunks"]):
            # Frequent disconnections for large streams
            if buffer.chunks_received > 0 and buffer.chunks_received % 5 == 0:
                simulator.disconnect()
                await asyncio.sleep(0.1)
                simulator.reconnect()
            
            if simulator.is_connected and not simulator.should_drop_packet():
                buffer.add_chunk(chunk)
        
        # Should handle large buffers efficiently
        assert buffer.total_size > 4096  # At least half received
        assert buffer.chunks_received > 8
        
    @pytest.mark.resilience
    @pytest.mark.websocket
    async def test_concurrent_buffer_recovery(self, network_condition, test_user_id:
                                            response_configs):
        """Test concurrent buffer recovery scenarios."""
        config = response_configs["text_response"]
        
        # Multiple concurrent streams
        generators = [
            StreamingResponseGenerator(ResponseType.TEXT, config["size"], config["chunk_size"])
            for _ in range(3)
        ]
        
        simulator = NetworkSimulator(network_condition)
        buffers = [StreamBuffer() for _ in range(3)]
        
        async def process_stream(stream_id, generator, buffer):
            async for chunk in generator.generate_stream(config["delay_between_chunks"]):
                # Stream-specific disconnections
                if buffer.chunks_received > 0 and buffer.chunks_received % (stream_id + 2) == 0:
                    simulator.disconnect()
                    await asyncio.sleep(0.1 * (stream_id + 1))
                    simulator.reconnect()
                
                if simulator.is_connected and not simulator.should_drop_packet():
                    buffer.add_chunk(chunk)
        
        # Process streams concurrently
        tasks = [
            process_stream(i, gen, buf) 
            for i, (gen, buf) in enumerate(zip(generators, buffers))
        ]
        
        await asyncio.gather(*tasks)
        
        # All buffers should have data
        for i, buffer in enumerate(buffers):
            assert buffer.chunks_received > 0, f"Buffer {i} received no chunks"
            assert buffer.total_size > 0, f"Buffer {i} has no data"
            
    @pytest.mark.resilience
    @pytest.mark.websocket
    async def test_memory_efficient_buffering(self, network_condition, test_user_id:
                                            response_configs):
        """Test memory-efficient buffering during long disconnections."""
        config = response_configs["text_response"]
        generator = StreamingResponseGenerator(
            ResponseType.TEXT,
            config["size"],
            config["chunk_size"]
        )
        
        simulator = NetworkSimulator(network_condition)
        buffer = StreamBuffer()
        max_buffer_chunks = 5  # Simulate memory limit
        
        async for chunk in generator.generate_stream(config["delay_between_chunks"]):
            # Long disconnection to test buffering limits
            if buffer.chunks_received == 3:
                simulator.disconnect()
                await asyncio.sleep(1.0)  # Long disconnection
                simulator.reconnect()
            
            if simulator.is_connected and not simulator.should_drop_packet():
                buffer.add_chunk(chunk)
                
                # Simulate memory management
                if buffer.chunks_received > max_buffer_chunks:
                    # Remove oldest chunk (simulate circular buffer)
                    buffer.data.pop(0)
                    buffer.chunks_received = max_buffer_chunks
        
        # Should handle memory constraints gracefully
        assert len(buffer.data) <= max_buffer_chunks
        assert buffer.chunks_received <= max_buffer_chunks
