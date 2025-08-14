"""
Tests for tool invocation generation in SyntheticDataService
"""

import pytest
from unittest.mock import MagicMock

from app.services.synthetic_data_service import SyntheticDataService


@pytest.fixture
def service():
    """Create fresh SyntheticDataService instance"""
    return SyntheticDataService()


class TestToolInvocations:
    """Test tool invocation generation"""
    
    def test_generate_tool_invocations_simple(self, service):
        """Test simple queries tool invocation"""
        invocations = service._generate_tool_invocations("simple_queries")
        
        assert len(invocations) == 1
        assert "name" in invocations[0]
        assert "type" in invocations[0]
        assert "latency_ms" in invocations[0]
        assert "status" in invocations[0]
        assert invocations[0]["status"] in ["success", "failed"]
    
    def test_generate_tool_invocations_orchestration(self, service):
        """Test tool orchestration invocations"""
        invocations = service._generate_tool_invocations("tool_orchestration")
        
        assert 2 <= len(invocations) <= 5
        for inv in invocations:
            assert "name" in inv
            assert "latency_ms" in inv
            assert inv["latency_ms"] > 0
    
    def test_generate_tool_invocations_data_analysis(self, service):
        """Test data analysis tool invocations"""
        invocations = service._generate_tool_invocations("data_analysis")
        
        # Should have query and analysis tools
        assert len(invocations) >= 1
        tool_types = [inv.get("type") for inv in invocations]
        # May have query or analysis tools (depends on availability)
        assert any(t in ["query", "analysis"] for t in tool_types if t)
    
    def test_generate_tool_invocations_error_scenarios(self, service):
        """Test error scenario invocations"""
        invocations = service._generate_tool_invocations("error_scenarios")
        
        assert len(invocations) == 1
        assert invocations[0]["status"] == "failed"
        assert "error" in invocations[0]
        assert invocations[0]["error"] == "Simulated error"
    
    def test_create_tool_invocation(self, service):
        """Test individual tool invocation creation"""
        tool = {
            "name": "test_tool",
            "type": "query",
            "latency_ms_range": (50, 200),
            "failure_rate": 0.1
        }
        
        invocation = service._create_tool_invocation(tool)
        
        assert invocation["name"] == "test_tool"
        assert invocation["type"] == "query"
        assert 50 <= invocation["latency_ms"] <= 200
        assert invocation["status"] in ["success", "failed"]
        
        if invocation["status"] == "failed":
            assert invocation["error"] == "Tool execution failed"
        else:
            assert invocation["error"] == None