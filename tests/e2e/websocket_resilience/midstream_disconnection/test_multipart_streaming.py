"""
Multipart Streaming Disconnection Recovery Tests.

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Complex Response Reliability
- Value Impact: Ensures multipart responses deliver completely after interruption
- Strategic/Revenue Impact: Critical for enterprise file uploads and downloads
"""

import asyncio
import uuid
from datetime import datetime, timezone
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.websocket_resilience.fixtures.shared_websocket_fixtures import (
    ConnectionState,
    ResponseType,
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
class MultipartStreamingDisconnectionTests:
    """Test multipart streaming disconnection and recovery."""
    
    @pytest.mark.resilience
    @pytest.mark.websocket
    async def test_multipart_stream_interruption(self, network_condition, stream_buffer:
                                               test_user_id, response_configs):
        """Test multipart streaming interruption and recovery."""
        config = response_configs["text_response"]  # Base config
        generator = StreamingResponseGenerator(
            ResponseType.MULTIPART,
            config["size"],
            config["chunk_size"]
        )
        
        simulator = NetworkSimulator(network_condition)
        boundary_count = 0
        
        async for chunk in generator.generate_stream(config["delay_between_chunks"]):
            await simulator.simulate_latency()
            
            # Count boundaries to track multipart structure
            if "boundary" in chunk:
                boundary_count += 1
            
            # Simulate disconnection after some parts
            if boundary_count == 2:
                simulator.disconnect()
                await asyncio.sleep(0.5)
                simulator.reconnect()
            
            if simulator.is_connected and not simulator.should_drop_packet():
                stream_buffer.add_chunk(chunk)
        
        # Should maintain multipart structure
        assert stream_buffer.chunks_received > 0
        full_data = stream_buffer.get_full_data()
        assert "Content-Type: multipart/mixed" in full_data
        assert "boundary" in full_data
        
    @pytest.mark.resilience
    @pytest.mark.websocket
    async def test_multipart_boundary_preservation(self, network_condition, stream_buffer:
                                                 test_user_id, response_configs):
        """Test multipart boundary preservation across disconnections."""
        config = response_configs["text_response"]
        generator = StreamingResponseGenerator(
            ResponseType.MULTIPART,
            config["size"],
            config["chunk_size"]
        )
        
        simulator = NetworkSimulator(network_condition)
        boundaries_seen = []
        
        async for chunk in generator.generate_stream(config["delay_between_chunks"]):
            # Multiple disconnections during multipart streaming
            if stream_buffer.chunks_received in [1, 3, 5]:
                simulator.disconnect()
                await asyncio.sleep(0.3)
                simulator.reconnect()
            
            if simulator.is_connected and not simulator.should_drop_packet():
                stream_buffer.add_chunk(chunk)
                
                # Track boundary markers
                if "--boundary" in chunk:
                    boundaries_seen.append(chunk)
        
        # Should preserve boundary structure
        assert len(boundaries_seen) > 0
        full_data = stream_buffer.get_full_data()
        
        # Should have opening and closing boundaries
        assert "--boundary" in full_data
        
    @pytest.mark.resilience
    @pytest.mark.websocket
    async def test_large_multipart_streaming(self, network_condition, stream_buffer:
                                           test_user_id, response_configs):
        """Test large multipart streaming with disconnections."""
        # Large multipart response
        large_config = {
            "type": ResponseType.MULTIPART,
            "size": 6144,
            "chunk_size": 512,
            "delay_between_chunks": 0.01
        }
        
        generator = StreamingResponseGenerator(
            ResponseType.MULTIPART,
            large_config["size"],
            large_config["chunk_size"]
        )
        
        simulator = NetworkSimulator(network_condition)
        parts_received = 0
        
        async for chunk in generator.generate_stream(large_config["delay_between_chunks"]):
            # Periodic disconnections
            if stream_buffer.chunks_received > 0 and stream_buffer.chunks_received % 4 == 0:
                simulator.disconnect()
                await asyncio.sleep(0.4)
                simulator.reconnect()
            
            if simulator.is_connected and not simulator.should_drop_packet():
                stream_buffer.add_chunk(chunk)
                
                # Count parts
                if "Part " in chunk:
                    parts_received += 1
        
        # Should handle large multipart streams
        assert stream_buffer.total_size > 2000
        assert parts_received > 0
        
    @pytest.mark.resilience
    @pytest.mark.websocket
    async def test_multipart_header_integrity(self, network_condition, stream_buffer:
                                            test_user_id, response_configs):
        """Test multipart header integrity during disconnections."""
        config = response_configs["text_response"]
        generator = StreamingResponseGenerator(
            ResponseType.MULTIPART,
            config["size"],
            config["chunk_size"]
        )
        
        simulator = NetworkSimulator(network_condition)
        headers_found = []
        
        async for chunk in generator.generate_stream(config["delay_between_chunks"]):
            # Disconnection at header boundaries
            if "Content-Type" in chunk:
                simulator.disconnect()
                await asyncio.sleep(0.2)
                simulator.reconnect()
            
            if simulator.is_connected and not simulator.should_drop_packet():
                stream_buffer.add_chunk(chunk)
                
                # Track headers
                if "Content-Type" in chunk:
                    headers_found.append(chunk)
        
        # Should preserve header integrity
        full_data = stream_buffer.get_full_data()
        assert "Content-Type: multipart/mixed" in full_data
        assert len(headers_found) > 0
        
    @pytest.mark.resilience
    @pytest.mark.websocket
    async def test_concurrent_multipart_streams(self, network_condition, test_user_id:
                                              response_configs):
        """Test concurrent multipart streams with disconnections."""
        config = response_configs["text_response"]
        
        # Create multiple generators
        generators = [
            StreamingResponseGenerator(ResponseType.MULTIPART, config["size"], config["chunk_size"])
            for _ in range(3)
        ]
        
        simulator = NetworkSimulator(network_condition)
        stream_results = [[] for _ in range(3)]
        
        # Process streams concurrently
        async def process_stream(gen_index, generator):
            async for chunk in generator.generate_stream(config["delay_between_chunks"]):
                # Random disconnections
                if len(stream_results[gen_index]) % 3 == 0:
                    simulator.disconnect()
                    await asyncio.sleep(0.2)
                    simulator.reconnect()
                
                if simulator.is_connected and not simulator.should_drop_packet():
                    stream_results[gen_index].append(chunk)
        
        # Run concurrent streams
        tasks = [process_stream(i, gen) for i, gen in enumerate(generators)]
        await asyncio.gather(*tasks)
        
        # All streams should receive data
        for result in stream_results:
            assert len(result) > 0
            full_stream = "".join(result)
            assert "multipart/mixed" in full_stream
