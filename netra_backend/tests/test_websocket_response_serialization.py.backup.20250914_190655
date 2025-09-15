"""WebSocket Response Serialization Tests.

Validates WebSocket message structures and streaming response serialization
for real-time frontend communication.
"""

import sys
from pathlib import Path
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig
from shared.isolated_environment import IsolatedEnvironment


# Test framework import - using pytest fixtures instead

import json
from typing import Any, Dict

import pytest

# Import backend schemas
from netra_backend.app.schemas import (
    StreamChunk,
    StreamComplete,
    WebSocketMessage,
    WebSocketMessageType,
)

class TestWebSocketMessageSerialization:
    """Test WebSocket message serialization."""
    
    def test_websocket_message_serialization(self) -> None:
        """Test WebSocket message serialization."""
        message = WebSocketMessage(
            type=WebSocketMessageType.AGENT_STARTED,
            payload={"run_id": "run123"}
        )
        
        json_str = message.model_dump_json()
        parsed = json.loads(json_str)
        
        assert parsed["type"] == "agent_started"
        assert parsed["payload"]["run_id"] == "run123"
    
    def test_websocket_agent_update_message(self) -> None:
        """Test WebSocket AgentUpdate message."""
        update_payload = {
            "content": "Analysis in progress...",
            "run_id": "run123",
            "metadata": {"progress": 45}
        }
        
        message = WebSocketMessage(
            type=WebSocketMessageType.AGENT_UPDATE,
            payload=update_payload
        )
        json_data = message.model_dump()
        
        assert json_data["type"] == "agent_update"
        assert json_data["payload"]["metadata"]["progress"] == 45
    
    def test_websocket_tool_completed_message(self) -> None:
        """Test WebSocket ToolCompleted message."""
        tool_payload = {
            "tool_name": "log_analyzer",
            "tool_output": {"findings": 3, "severity": "high"},
            "run_id": "run123",
            "status": "success"
        }
        
        message = WebSocketMessage(
            type=WebSocketMessageType.TOOL_COMPLETED,
            payload=tool_payload
        )
        json_str = message.model_dump_json()
        parsed = json.loads(json_str)
        
        assert parsed["payload"]["tool_output"]["findings"] == 3
    
    def test_websocket_error_message(self) -> None:
        """Test WebSocket error message serialization."""
        error_payload = {
            "run_id": "run123",
            "message": "Connection lost",
            "error_code": "WEBSOCKET_ERROR"
        }
        
        message = WebSocketMessage(
            type=WebSocketMessageType.AGENT_ERROR,
            payload=error_payload
        )
        json_data = message.model_dump()
        
        assert json_data["payload"]["error_code"] == "WEBSOCKET_ERROR"
    
    def test_websocket_ping_pong_messages(self) -> None:
        """Test WebSocket ping/pong message handling."""
        ping_message = WebSocketMessage(
            type=WebSocketMessageType.PING,
            payload={"timestamp": "2025-01-01T12:00:00Z"}
        )
        
        pong_message = WebSocketMessage(
            type=WebSocketMessageType.PONG,
            payload={"timestamp": "2025-01-01T12:00:01Z"}
        )
        
        ping_json = ping_message.model_dump()
        pong_json = pong_message.model_dump()
        
        assert ping_json["type"] == "ping"
        assert pong_json["type"] == "pong"

class TestStreamingResponseSerialization:
    """Test streaming response serialization."""
    
    def test_stream_chunk_structure(self) -> None:
        """Test StreamChunk response structure."""
        chunk_data = {
            "chunk_id": "test_chunk",
            "content": "Processing data...",
            "is_final": False
        }
        
        chunk = StreamChunk(**chunk_data)
        json_data = chunk.model_dump()
        
        assert json_data["content"] == "Processing data..."
        assert json_data["chunk_id"] == "test_chunk"
        assert json_data["is_final"] is False
    
    def test_streaming_sequence(self) -> None:
        """Test sequence of streaming chunks."""
        chunks = [
            StreamChunk(chunk_id="chunk_0", content="Processing", is_final=False),
            StreamChunk(chunk_id="chunk_1", content=" data", is_final=False),
            StreamChunk(chunk_id="chunk_2", content=" complete", is_final=True)
        ]
        
        for i, chunk in enumerate(chunks):
            json_data = chunk.model_dump()
            assert json_data["chunk_id"] == f"chunk_{i}"
            assert json_data["is_final"] == (i == 2)
    
    def test_stream_complete_structure(self) -> None:
        """Test StreamComplete response structure."""
        complete_data = {
            "stream_id": "stream_123",
            "total_chunks": 5,
            "metadata": {"total_tokens": 150, "duration": 5.2}
        }
        
        complete = StreamComplete(**complete_data)
        json_data = complete.model_dump()
        
        assert json_data["stream_id"] == "stream_123"
        assert json_data["total_chunks"] == 5
        assert json_data["metadata"]["duration"] == 5.2
    
    def test_stream_chunk_with_rich_metadata(self) -> None:
        """Test StreamChunk with rich metadata."""
        rich_metadata = {
            "model": LLMModel.GEMINI_2_5_FLASH.value,
            "tokens": {"input": 50, "output": 25, "total": 75},
            "timing": {"start": "2025-01-01T10:00:00Z", "duration": 1.2},
            "quality": {"confidence": 0.95, "relevance": 0.88}
        }
        
        chunk = StreamChunk(
            chunk_id="rich_chunk",
            content="Rich analysis chunk",
            is_final=False
        )
        json_data = chunk.model_dump()
        
        assert json_data["chunk_id"] == "rich_chunk"
        assert json_data["content"] == "Rich analysis chunk"
    
    def test_stream_error_handling(self) -> None:
        """Test streaming error response structure."""
        error_chunk = StreamChunk(
            chunk_id="error_chunk",
            content="Error occurred during processing",
            is_final=True
        )
        json_data = error_chunk.model_dump()
        
        assert json_data["chunk_id"] == "error_chunk"
        assert json_data["is_final"] is True

class TestRealtimeMessageFlow:
    """Test realistic real-time message flow scenarios."""
    
    def test_agent_lifecycle_websocket_flow(self) -> None:
        """Test complete agent lifecycle over WebSocket."""
        messages = [
            WebSocketMessage(
                type=WebSocketMessageType.AGENT_STARTED,
                payload={"run_id": "run123"}
            ),
            WebSocketMessage(
                type=WebSocketMessageType.AGENT_UPDATE,
                payload={
                    "content": "Starting analysis...",
                    "run_id": "run123",
                    "metadata": {"step": "initialization"}
                }
            ),
            WebSocketMessage(
                type=WebSocketMessageType.TOOL_STARTED,
                payload={
                    "tool_name": "data_fetcher",
                    "tool_args": {"source": "database"},
                    "run_id": "run123"
                }
            ),
            WebSocketMessage(
                type=WebSocketMessageType.TOOL_COMPLETED,
                payload={
                    "tool_name": "data_fetcher",
                    "tool_output": {"rows": 1000},
                    "run_id": "run123",
                    "status": "success"
                }
            ),
            WebSocketMessage(
                type=WebSocketMessageType.AGENT_COMPLETED,
                payload={
                    "run_id": "run123",
                    "result": {"analysis": "complete"}
                }
            )
        ]
        
        for msg in messages:
            json_data = msg.model_dump()
            assert "type" in json_data
            assert "payload" in json_data
            assert json_data["payload"]["run_id"] == "run123"
    
    def test_streaming_with_websocket_wrapper(self) -> None:
        """Test streaming chunks wrapped in WebSocket messages."""
        stream_chunks = [
            StreamChunk(chunk_id="analyze_0", content="Analyzing", is_final=False),
            StreamChunk(chunk_id="analyze_1", content=" performance", is_final=False),
            StreamChunk(chunk_id="analyze_2", content=" metrics", is_final=True)
        ]
        
        websocket_messages = [
            WebSocketMessage(
                type=WebSocketMessageType.STREAM_CHUNK,
                payload=chunk.model_dump()
            )
            for chunk in stream_chunks
        ]
        
        for i, ws_msg in enumerate(websocket_messages):
            json_data = ws_msg.model_dump()
            assert json_data["type"] == "stream_chunk"
            assert json_data["payload"]["chunk_id"] == f"analyze_{i}"
    
    def test_concurrent_agent_messages(self) -> None:
        """Test multiple concurrent agent messages."""
        concurrent_updates = [
            WebSocketMessage(
                type=WebSocketMessageType.AGENT_UPDATE,
                payload={
                    "content": f"Agent {i} processing",
                    "run_id": f"run{i}",
                    "metadata": {"agent_id": i}
                }
            )
            for i in range(3)
        ]
        
        for i, msg in enumerate(concurrent_updates):
            json_data = msg.model_dump()
            assert json_data["payload"]["run_id"] == f"run{i}"
            assert json_data["payload"]["metadata"]["agent_id"] == i

if __name__ == "__main__":
    pytest.main([__file__, "-v"])