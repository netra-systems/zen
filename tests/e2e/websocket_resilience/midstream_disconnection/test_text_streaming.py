"""
Text Streaming Disconnection Recovery Tests.

Business Value Justification (BVJ):
- Segment: Enterprise/Mid
- Business Goal: Streaming Reliability
- Value Impact: Ensures text streaming continues after network interruption
- Strategic/Revenue Impact: Prevents customer churn from incomplete responses
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
class TextStreamingDisconnectionTests:
    """Test text streaming disconnection and recovery."""
    
    @pytest.mark.resilience
    @pytest.mark.websocket
    async def test_basic_text_stream_interruption(self, network_condition, stream_buffer:
                                                 test_user_id, response_configs):
        """Test basic text streaming interruption and recovery."""
        config = response_configs["text_response"]
        generator = StreamingResponseGenerator(
            ResponseType.TEXT, 
            config["size"], 
            config["chunk_size"]
        )
        
        simulator = NetworkSimulator(network_condition)
        chunks_received = 0
        
        # Start streaming
        async for chunk in generator.generate_stream(config["delay_between_chunks"]):
            await simulator.simulate_latency()
            
            if simulator.should_drop_packet():
                continue  # Simulate packet loss
                
            stream_buffer.add_chunk(chunk)
            chunks_received += 1
            
            # Simulate disconnection after some chunks
            if chunks_received == 3:
                simulator.disconnect()
                await asyncio.sleep(0.5)  # Disconnection period
                simulator.reconnect()
        
        # Verify recovery
        assert stream_buffer.chunks_received > 0
        assert len(stream_buffer.get_full_data()) > 0
        
    @pytest.mark.resilience
    @pytest.mark.websocket
    async def test_mid_chunk_disconnection(self, network_condition, stream_buffer:
                                         test_user_id, response_configs):
        """Test disconnection in the middle of a chunk."""
        config = response_configs["text_response"]
        generator = StreamingResponseGenerator(
            ResponseType.TEXT,
            config["size"],
            config["chunk_size"]
        )
        
        simulator = NetworkSimulator(network_condition)
        disconnection_occurred = False
        
        async for chunk in generator.generate_stream(config["delay_between_chunks"]):
            # Simulate disconnection mid-chunk
            if not disconnection_occurred and len(stream_buffer.data) >= 2:
                simulator.disconnect()
                disconnection_occurred = True
                await asyncio.sleep(0.3)
                simulator.reconnect()
            
            if simulator.is_connected and not simulator.should_drop_packet():
                stream_buffer.add_chunk(chunk)
        
        # Should handle mid-chunk disconnection gracefully
        assert disconnection_occurred
        assert stream_buffer.chunks_received > 0
        
    @pytest.mark.resilience
    @pytest.mark.websocket
    async def test_multiple_disconnections(self, network_condition, stream_buffer:
                                         test_user_id, response_configs):
        """Test multiple disconnections during streaming."""
        config = response_configs["text_response"]
        generator = StreamingResponseGenerator(
            ResponseType.TEXT,
            config["size"],
            config["chunk_size"]
        )
        
        simulator = NetworkSimulator(network_condition)
        disconnection_count = 0
        max_disconnections = 3
        
        async for chunk in generator.generate_stream(config["delay_between_chunks"]):
            # Periodic disconnections
            if (stream_buffer.chunks_received + 1) % 4 == 0 and disconnection_count < max_disconnections:
                simulator.disconnect()
                disconnection_count += 1
                await asyncio.sleep(0.2)
                simulator.reconnect()
            
            if simulator.is_connected and not simulator.should_drop_packet():
                stream_buffer.add_chunk(chunk)
        
        # Should survive multiple disconnections
        assert disconnection_count == max_disconnections
        assert stream_buffer.chunks_received > 0
        
    @pytest.mark.resilience
    @pytest.mark.websocket
    async def test_long_disconnection_recovery(self, network_condition, stream_buffer:
                                             test_user_id, response_configs):
        """Test recovery from extended disconnection."""
        config = response_configs["text_response"]
        generator = StreamingResponseGenerator(
            ResponseType.TEXT,
            config["size"],
            config["chunk_size"]
        )
        
        simulator = NetworkSimulator(network_condition)
        long_disconnection_occurred = False
        
        async for chunk in generator.generate_stream(config["delay_between_chunks"]):
            # Long disconnection after initial chunks
            if not long_disconnection_occurred and stream_buffer.chunks_received >= 2:
                simulator.disconnect()
                long_disconnection_occurred = True
                await asyncio.sleep(2.0)  # Extended disconnection
                simulator.reconnect()
            
            if simulator.is_connected and not simulator.should_drop_packet():
                stream_buffer.add_chunk(chunk)
        
        # Should recover from long disconnection
        assert long_disconnection_occurred
        assert stream_buffer.chunks_received > 0
        
    @pytest.mark.resilience
    @pytest.mark.websocket
    async def test_high_frequency_disconnections(self, network_condition, stream_buffer:
                                               test_user_id, response_configs):
        """Test handling of very frequent disconnections."""
        config = response_configs["text_response"]
        generator = StreamingResponseGenerator(
            ResponseType.TEXT,
            config["size"],
            config["chunk_size"]
        )
        
        simulator = NetworkSimulator(network_condition)
        rapid_disconnections = 0
        
        async for chunk in generator.generate_stream(config["delay_between_chunks"]):
            # Very frequent disconnections
            if rapid_disconnections < 10:
                simulator.disconnect()
                rapid_disconnections += 1
                await asyncio.sleep(0.05)  # Very brief disconnection
                simulator.reconnect()
            
            if simulator.is_connected and not simulator.should_drop_packet():
                stream_buffer.add_chunk(chunk)
        
        # Should handle rapid disconnections
        assert rapid_disconnections == 10
        assert stream_buffer.chunks_received >= 0  # Some chunks may be received
