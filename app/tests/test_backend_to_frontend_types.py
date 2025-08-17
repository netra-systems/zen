"""Backend to Frontend Type Safety Tests.

Validates that backend response structures match frontend expectations
ensuring type consistency in the response flow.
"""

import json
import pytest
from typing import Dict, Any

# Import backend schemas
from app.schemas.registry import (
    WebSocketMessageType,
    AgentUpdate,
    StreamChunk,
    StreamComplete,
    WebSocketMessage
)
from app.schemas.Agent import AgentStarted, AgentCompleted, AgentErrorMessage
from app.schemas.Tool import ToolStarted, ToolCompleted, ToolStatus


class TestAgentResponseSerialization:
    """Test agent response serialization for frontend consumption."""
    
    def test_agent_started_response_structure(self) -> None:
        """Test AgentStarted response structure."""
        backend_response = AgentStarted(run_id="run123")
        json_data = backend_response.model_dump()
        
        assert "run_id" in json_data
        assert isinstance(json_data["run_id"], str)
        assert json_data["run_id"] == "run123"
    
    def test_agent_started_json_serialization(self) -> None:
        """Test AgentStarted JSON string serialization."""
        backend_response = AgentStarted(run_id="run123")
        json_str = backend_response.model_dump_json()
        
        parsed = json.loads(json_str)
        assert parsed["run_id"] == "run123"
    
    def test_agent_completed_response_structure(self) -> None:
        """Test AgentCompleted response structure."""
        backend_response = AgentCompleted(
            run_id="run123",
            result={"analysis": "complete", "recommendations": ["opt1", "opt2"]}
        )
        json_data = backend_response.model_dump()
        
        assert "run_id" in json_data
        assert "result" in json_data
        assert isinstance(json_data["result"]["recommendations"], list)
        assert len(json_data["result"]["recommendations"]) == 2
    
    def test_agent_completed_complex_result(self) -> None:
        """Test AgentCompleted with complex result structure."""
        complex_result = {
            "analysis": "complete",
            "metrics": {"cpu": 85.2, "memory": 67.8},
            "recommendations": ["scale_up", "optimize_queries"],
            "details": {
                "bottlenecks": ["database", "network"],
                "severity": "medium"
            }
        }
        
        response = AgentCompleted(run_id="run123", result=complex_result)
        json_data = response.model_dump()
        
        assert json_data["result"]["metrics"]["cpu"] == 85.2
        assert "bottlenecks" in json_data["result"]["details"]
    
    def test_agent_update_response_structure(self) -> None:
        """Test AgentUpdate response structure."""
        update_data = {
            "content": "Processing data...",
            "run_id": "run123",
            "metadata": {"step": "analysis"}
        }
        
        update = AgentUpdate(**update_data)
        json_data = update.model_dump()
        
        assert json_data["content"] == "Processing data..."
        assert json_data["run_id"] == "run123"
        assert json_data["metadata"]["step"] == "analysis"


class TestToolResponseSerialization:
    """Test tool response serialization for frontend consumption."""
    
    def test_tool_started_response_structure(self) -> None:
        """Test ToolStarted response structure."""
        backend_response = ToolStarted(
            tool_name="log_fetcher",
            tool_args={"start_time": "2025-01-01T00:00:00Z"},
            run_id="run123"
        )
        json_data = backend_response.model_dump()
        
        assert json_data["tool_name"] == "log_fetcher"
        assert "tool_args" in json_data
        assert json_data["run_id"] == "run123"
    
    def test_tool_started_complex_args(self) -> None:
        """Test ToolStarted with complex arguments."""
        complex_args = {
            "query": "SELECT * FROM logs",
            "filters": {"level": ["error", "warning"]},
            "pagination": {"page": 1, "limit": 100},
            "options": {"include_metadata": True}
        }
        
        response = ToolStarted(
            tool_name="database_query",
            tool_args=complex_args,
            run_id="run123"
        )
        json_data = response.model_dump()
        
        assert json_data["tool_args"]["pagination"]["limit"] == 100
        assert "error" in json_data["tool_args"]["filters"]["level"]
    
    def test_tool_completed_response_structure(self) -> None:
        """Test ToolCompleted response structure."""
        backend_response = ToolCompleted(
            tool_name="log_fetcher",
            tool_output={"logs": ["log1", "log2"], "count": 2},
            run_id="run123",
            status=ToolStatus.SUCCESS
        )
        json_data = backend_response.model_dump()
        
        assert json_data["status"] == "success"
        assert json_data["tool_output"]["count"] == 2
        assert len(json_data["tool_output"]["logs"]) == 2
    
    def test_tool_completed_error_status(self) -> None:
        """Test ToolCompleted with error status."""
        error_response = ToolCompleted(
            tool_name="failing_tool",
            tool_output={"error": "Connection timeout"},
            run_id="run123",
            status=ToolStatus.ERROR
        )
        json_data = error_response.model_dump()
        
        assert json_data["status"] == "error"
        assert json_data["tool_output"]["error"] == "Connection timeout"


class TestErrorResponseSerialization:
    """Test error response serialization."""
    
    def test_agent_error_message_structure(self) -> None:
        """Test AgentErrorMessage response structure."""
        backend_response = AgentErrorMessage(
            run_id="run123",
            message="Processing failed due to timeout"
        )
        json_data = backend_response.model_dump()
        
        assert json_data["run_id"] == "run123"
        assert json_data["message"] == "Processing failed due to timeout"
    
    def test_agent_error_with_details(self) -> None:
        """Test AgentErrorMessage with additional details."""
        error_details = {
            "code": "TIMEOUT_ERROR",
            "timestamp": "2025-01-01T12:00:00Z",
            "context": {"step": "data_processing"}
        }
        
        response = AgentErrorMessage(
            run_id="run123",
            message="Processing failed",
            details=error_details
        )
        json_data = response.model_dump()
        
        assert json_data["details"]["code"] == "TIMEOUT_ERROR"
        assert json_data["details"]["context"]["step"] == "data_processing"


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


class TestStreamingResponseSerialization:
    """Test streaming response serialization."""
    
    def test_stream_chunk_structure(self) -> None:
        """Test StreamChunk response structure."""
        chunk_data = {
            "content": "Processing data...",
            "index": 0,
            "finished": False,
            "metadata": {"tokens": 15, "model": "gpt-4"}
        }
        
        chunk = StreamChunk(**chunk_data)
        json_data = chunk.model_dump()
        
        assert json_data["content"] == "Processing data..."
        assert json_data["index"] == 0
        assert json_data["finished"] is False
        assert json_data["metadata"]["tokens"] == 15
    
    def test_streaming_sequence(self) -> None:
        """Test sequence of streaming chunks."""
        chunks = [
            StreamChunk(content="Processing", index=0, finished=False),
            StreamChunk(content=" data", index=1, finished=False),
            StreamChunk(content=" complete", index=2, finished=True)
        ]
        
        for i, chunk in enumerate(chunks):
            json_data = chunk.model_dump()
            assert json_data["index"] == i
            assert json_data["finished"] == (i == 2)
    
    def test_stream_complete_structure(self) -> None:
        """Test StreamComplete response structure."""
        complete_data = {
            "content": "Analysis completed successfully",
            "metadata": {"total_tokens": 150, "duration": 5.2}
        }
        
        complete = StreamComplete(**complete_data)
        json_data = complete.model_dump()
        
        assert json_data["content"] == "Analysis completed successfully"
        assert json_data["metadata"]["duration"] == 5.2


class TestComplexPayloadSerialization:
    """Test complex nested payload serialization."""
    
    def test_nested_agent_result_serialization(self) -> None:
        """Test complex nested agent result."""
        complex_result = {
            "summary": "Performance analysis complete",
            "metrics": {
                "cpu_usage": {"avg": 78.5, "peak": 95.2},
                "memory_usage": {"avg": 64.3, "peak": 87.1},
                "network": {"throughput": "1.2GB/s", "latency": "15ms"}
            },
            "recommendations": [
                {
                    "action": "scale_cpu",
                    "priority": "high",
                    "impact": {"cost": "+$200/month", "performance": "+30%"}
                }
            ],
            "timeline": [
                {"timestamp": "2025-01-01T10:00:00Z", "event": "analysis_start"},
                {"timestamp": "2025-01-01T10:05:00Z", "event": "data_collected"}
            ]
        }
        
        response = AgentCompleted(run_id="run123", result=complex_result)
        json_data = response.model_dump()
        
        metrics = json_data["result"]["metrics"]
        assert metrics["cpu_usage"]["peak"] == 95.2
        assert len(json_data["result"]["timeline"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])