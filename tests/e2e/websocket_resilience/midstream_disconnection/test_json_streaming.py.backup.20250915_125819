"""
JSON Streaming Disconnection Recovery Tests.

Business Value Justification (BVJ):
- Segment: Enterprise/Mid
- Business Goal: Data Streaming Reliability
- Value Impact: Ensures JSON data streaming integrity after interruption
- Strategic/Revenue Impact: Prevents data corruption and loss
"""

import asyncio
import json
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
class TestJSONStreamingDisconnection:
    """Test JSON streaming disconnection and recovery."""
    
    @pytest.mark.resilience
    @pytest.mark.websocket
    async def test_json_stream_interruption(self, network_condition, stream_buffer:
                                          test_user_id, response_configs):
        """Test JSON streaming interruption and recovery."""
        config = response_configs["json_response"]
        generator = StreamingResponseGenerator(
            ResponseType.JSON,
            config["size"],
            config["chunk_size"]
        )
        
        simulator = NetworkSimulator(network_condition)
        valid_json_chunks = 0
        
        async for chunk in generator.generate_stream(config["delay_between_chunks"]):
            await simulator.simulate_latency()
            
            # Simulate disconnection after some chunks
            if stream_buffer.chunks_received == 2:
                simulator.disconnect()
                await asyncio.sleep(0.5)
                simulator.reconnect()
            
            if simulator.is_connected and not simulator.should_drop_packet():
                stream_buffer.add_chunk(chunk)
                
                # Validate JSON structure
                try:
                    json.loads(chunk)
                    valid_json_chunks += 1
                except json.JSONDecodeError:
                    pass  # Partial chunks may not be valid JSON
        
        # Should maintain JSON integrity
        assert stream_buffer.chunks_received > 0
        assert valid_json_chunks > 0
        
    @pytest.mark.resilience
    @pytest.mark.websocket
    async def test_json_structure_preservation(self, network_condition, stream_buffer:
                                             test_user_id, response_configs):
        """Test JSON structure is preserved across disconnections."""
        config = response_configs["json_response"]
        generator = StreamingResponseGenerator(
            ResponseType.JSON,
            config["size"],
            config["chunk_size"]
        )
        
        simulator = NetworkSimulator(network_condition)
        complete_json_objects = []
        
        async for chunk in generator.generate_stream(config["delay_between_chunks"]):
            # Multiple disconnections
            if stream_buffer.chunks_received in [1, 3, 5]:
                simulator.disconnect()
                await asyncio.sleep(0.3)
                simulator.reconnect()
            
            if simulator.is_connected and not simulator.should_drop_packet():
                stream_buffer.add_chunk(chunk)
                
                # Try to parse as complete JSON
                try:
                    json_obj = json.loads(chunk)
                    complete_json_objects.append(json_obj)
                except json.JSONDecodeError:
                    pass
        
        # Should have valid JSON objects
        assert len(complete_json_objects) > 0
        
        # Validate JSON structure
        for obj in complete_json_objects:
            assert "chunk_id" in obj
            assert "timestamp" in obj
            assert "data" in obj
            
    @pytest.mark.resilience
    @pytest.mark.websocket
    async def test_large_json_streaming(self, network_condition, stream_buffer:
                                      test_user_id, response_configs):
        """Test large JSON streaming with disconnections."""
        # Create larger JSON response
        large_config = {
            "type": ResponseType.JSON,
            "size": 4096,
            "chunk_size": 256,
            "delay_between_chunks": 0.02
        }
        
        generator = StreamingResponseGenerator(
            ResponseType.JSON,
            large_config["size"],
            large_config["chunk_size"]
        )
        
        simulator = NetworkSimulator(network_condition)
        disconnections = 0
        
        async for chunk in generator.generate_stream(large_config["delay_between_chunks"]):
            # Periodic disconnections for large stream
            if stream_buffer.chunks_received > 0 and stream_buffer.chunks_received % 3 == 0 and disconnections < 5:
                simulator.disconnect()
                disconnections += 1
                await asyncio.sleep(0.4)
                simulator.reconnect()
            
            if simulator.is_connected and not simulator.should_drop_packet():
                stream_buffer.add_chunk(chunk)
        
        # Should handle large JSON streams
        assert disconnections > 0
        assert stream_buffer.total_size > 1000  # Significant data received
        
    @pytest.mark.resilience
    @pytest.mark.websocket
    async def test_malformed_json_during_disconnection(self, network_condition, stream_buffer:
                                                     test_user_id, response_configs):
        """Test handling of malformed JSON during disconnection."""
        config = response_configs["json_response"]
        generator = StreamingResponseGenerator(
            ResponseType.JSON,
            config["size"],
            config["chunk_size"]
        )
        
        simulator = NetworkSimulator(network_condition)
        json_errors = 0
        
        async for chunk in generator.generate_stream(config["delay_between_chunks"]):
            # Frequent disconnections to increase chance of partial JSON
            if stream_buffer.chunks_received % 2 == 0:
                simulator.disconnect()
                await asyncio.sleep(0.1)
                simulator.reconnect()
            
            if simulator.is_connected and not simulator.should_drop_packet():
                stream_buffer.add_chunk(chunk)
                
                # Check for JSON parsing errors
                try:
                    json.loads(chunk)
                except json.JSONDecodeError:
                    json_errors += 1
        
        # Should handle malformed JSON gracefully
        assert stream_buffer.chunks_received > 0
        # Some JSON errors are expected due to partial chunks
        
    @pytest.mark.resilience
    @pytest.mark.websocket
    async def test_json_array_streaming(self, network_condition, stream_buffer:
                                      test_user_id, response_configs):
        """Test JSON array streaming with disconnections."""
        # Simulate JSON array streaming
        config = response_configs["json_response"]
        generator = StreamingResponseGenerator(
            ResponseType.JSON,
            config["size"],
            config["chunk_size"]
        )
        
        simulator = NetworkSimulator(network_condition)
        array_elements = []
        
        async for chunk in generator.generate_stream(config["delay_between_chunks"]):
            # Disconnection during array streaming
            if len(array_elements) == 2:
                simulator.disconnect()
                await asyncio.sleep(0.6)
                simulator.reconnect()
            
            if simulator.is_connected and not simulator.should_drop_packet():
                stream_buffer.add_chunk(chunk)
                
                # Parse as array element
                try:
                    element = json.loads(chunk)
                    array_elements.append(element)
                except json.JSONDecodeError:
                    pass
        
        # Should maintain array consistency
        assert len(array_elements) > 0
        
        # Validate array elements have sequential chunk_ids
        if len(array_elements) > 1:
            chunk_ids = [elem.get("chunk_id", -1) for elem in array_elements]
            # Should be roughly sequential (allowing for some gaps due to disconnections)
            assert max(chunk_ids) > min(chunk_ids)
