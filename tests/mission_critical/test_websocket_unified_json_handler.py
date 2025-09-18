class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True"""
        self.is_connected = True"""
"""
        """Send JSON message.""""""
        """Send JSON message.""""""
        raise RuntimeError("WebSocket is closed)"
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure):"
        """Close WebSocket connection."""
        pass
        self._closed = True"""
        self._closed = True"""
"""
"""
        """Get all sent messages.""""""
        """Get all sent messages.""""""
        return self.messages_sent.copy()"""
        return self.messages_sent.copy()"""
        """
        """
        MISSION CRITICAL: WebSocket Unified JSON Handler Test Suite"""
        MISSION CRITICAL: WebSocket Unified JSON Handler Test Suite"""
        This test suite specifically validates the WebSocket manager"s JSON serialization"
        methods that will be used by the unified JSON handler. It focuses on edge cases
        and performance requirements that are critical for chat functionality.

        CRITICAL SERIALIZATION METHODS:
        1. _serialize_message_safely() - Synchronous fallback serialization
        2. _serialize_message_safely_async() - Async serialization with timeout
        3. Frontend message type conversion
        4. Complex Pydantic model handling (DeepAgentState, etc.)
        5. Error recovery and fallback patterns

        Business Value Justification:
        - Segment: Platform/Internal
        - Business Goal: System Stability (unified JSON handling)
        - Value Impact: Eliminates JSON serialization inconsistencies across WebSocket events
        - Strategic Impact: Single point of JSON handling reduces maintenance and bugs"""
        - Strategic Impact: Single point of JSON handling reduces maintenance and bugs""""


import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.state import ( )
        DeepAgentState, OptimizationsResult, ActionPlanResult,
        ReportResult, SyntheticDataResult, SupplyResearchResult
            
from netra_backend.app.schemas.registry import WebSocketMessage, AgentStarted, ServerMessage
from netra_backend.app.schemas.websocket_models import ( )
        BaseWebSocketPayload, AgentUpdatePayload, ToolCall, ToolResult,
        AgentCompleted, StreamChunk, StreamComplete, WebSocketError
            
from netra_backend.app.schemas.agent_models import AgentMetadata
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as WebSocketManager
from netra_backend.app.websocket_core.types import get_frontend_message_type
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env"""
from shared.isolated_environment import get_env"""
"""
"""
        """Test unified JSON handling in WebSocket manager."""
        pass"""
        pass"""
        @pytest.fixture"""
        @pytest.fixture"""
        """Use real service instance.""""""
        """Use real service instance.""""""
        """Create WebSocket manager for testing."""
        pass
        return WebSocketManager()"""
        return WebSocketManager()"""
        @pytest.fixture"""
        @pytest.fixture"""
        """Use real service instance.""""""
        """Use real service instance.""""""
        """Create maximally complex DeepAgentState for stress testing.""""""
        """Create maximally complex DeepAgentState for stress testing.""""""
    # Create all possible result types"""
    # Create all possible result types"""
        optimization_type="comprehensive_optimization,"
        recommendations=[ )
        "Implement auto-scaling for EC2 instances,"
        "Switch to Reserved Instances for predictable workloads,"
        "Use Lambda for event-driven processes,"
        "Optimize S3 storage classes,"
        "Implement CloudFront CDN"
        ],
        cost_savings=5280.95,
        performance_improvement=28.7,
        confidence_score=0.94
    

        action_plan = ActionPlanResult( )
        action_plan_summary="Multi-phase cloud optimization implementation,"
        total_estimated_time="6-8 weeks,"
        required_approvals=["CTO", "CFO", "Engineering Manager", "Operations Lead],"
        actions=[ )
        { )
        "id: 1,"
        "action": "Conduct comprehensive infrastructure audit,"
        "priority": "critical,"
        "estimated_hours: 40,"
        "dependencies: [],"
        "owner": "DevOps Team"
        },
        { )
        "id: 2,"
        "action": "Implement monitoring and alerting,"
        "priority": "high,"
        "estimated_hours: 60,"
        "dependencies: [1],"
        "owner": "Platform Team"
        },
        { )
        "id: 3,"
        "action": "Migrate to optimized instance types,"
        "priority": "high,"
        "estimated_hours: 80,"
        "dependencies: [1, 2],"
        "owner": "Cloud Architecture Team"
    
        ],
        execution_timeline=[ )
        { )
        "phase": "Phase 1 - Assessment,"
        "duration": "2 weeks,"
        "tasks": ["Infrastructure audit", "Cost analysis", "Performance benchmarking],"
        "deliverables": ["Audit report", "Cost analysis", "Optimization roadmap]"
        },
        { )
        "phase": "Phase 2 - Planning,"
        "duration": "1 week,"
        "tasks": ["Detailed implementation plan", "Risk assessment", "Resource allocation],"
        "deliverables": ["Implementation plan", "Risk mitigation strategy]"
        },
        { )
        "phase": "Phase 3 - Implementation,"
        "duration": "3-4 weeks,"
        "tasks": ["Instance optimization", "Auto-scaling setup", "Monitoring deployment],"
        "deliverables": ["Optimized infrastructure", "Monitoring dashboard]"
        },
        { )
        "phase": "Phase 4 - Validation,"
        "duration": "1 week,"
        "tasks": ["Performance testing", "Cost validation", "Documentation],"
        "deliverables": ["Validation report", "Updated documentation]"
    
        ],
        supply_config_updates=[ )
        { )
        "service": "EC2,"
        "changes": ["Instance type optimization", "Auto-scaling configuration],"
        "impact": "30% cost reduction, 25% performance improvement"
        },
        { )
        "service": "RDS,"
        "changes": ["Multi-AZ optimization", "Storage optimization],"
        "impact": "20% cost reduction, improved availability"
    
        ],
post_implementation={"monitoring_setup": "CloudWatch dashboards with custom metrics",, "maintenance_schedule": "Monthly optimization reviews",, "success_metrics": ["Cost per transaction", "Response time", "System availability"],, "rollback_plan": "Automated rollback using Infrastructure as Code}"
        },
cost_benefit_analysis={"implementation_cost": 45000,, "annual_savings": 63372,, "roi_percentage": 140.8,, "payback_period_months": 8.5,, "risk_factors": ["Temporary performance impact", "Team training requirements]}"
        report = ReportResult( )
        report_type="comprehensive_optimization_analysis,"
        content="This comprehensive analysis identified significant opportunities for cloud infrastructure optimization...,"
        sections=[ )
        { )
        "section_id": "exec_summary,"
        "title": "Executive Summary,"
        "content": "Our analysis reveals potential annual savings of $63,372...,"
        "section_type": "summary"
        },
        { )
        "section_id": "technical_findings,"
        "title": "Technical Findings,"
        "content": "Current infrastructure analysis shows...,"
        "section_type": "technical"
    
        ],
        attachments=[ )
        "cost_analysis_detailed.xlsx,"
        "performance_benchmarks.pdf,"
        "implementation_roadmap.pdf"""

    
    

        synthetic_data = SyntheticDataResult( )
        data_type="infrastructure_usage_patterns,"
        generation_method="Monte Carlo simulation,"
        sample_count=10000,
        quality_score=0.91,
        file_path="/tmp/synthetic_usage_data.json"
    

        supply_research = SupplyResearchResult( )
        research_scope="Cloud service provider comparison,"
        findings=[ )
        "AWS Reserved Instances offer 40% savings for predictable workloads,"
        "Azure Spot Instances provide up to 90% cost reduction for fault-tolerant workloads,"
        "GCP sustained use discounts apply automatically"
        ],
        recommendations=[ )
        "Implement multi-cloud strategy for optimal pricing,"
        "Use spot instances for development environments,"
        "Reserve instances for production databases"
        ],
        data_sources=[ )
        "AWS Pricing Calculator,"
        "Azure Pricing Calculator,"
        "GCP Pricing Calculator,"
        "Gartner Cloud Infrastructure Report 2024"
        ],
        confidence_level=0.88
    

        return DeepAgentState( )
        user_request="Perform comprehensive analysis of our cloud infrastructure with detailed optimization recommendations and implementation plan,"
        chat_thread_id="thread-comprehensive-analysis,"
        user_id="user-enterprise-customer,"
        run_id="run-comprehensive-12345,"
agent_input={"analysis_scope": "full_infrastructure",, "optimization_goals": ["cost_reduction", "performance_improvement", "scalability"],, "constraints": ["minimal_downtime", "compliance_requirements"],, "budget_limit: 50000}"
        },
        optimizations_result=optimizations,
        action_plan_result=action_plan,
        report_result=report,
        synthetic_data_result=synthetic_data,
        supply_research_result=supply_research,
        final_report="Comprehensive infrastructure optimization analysis completed. Identified $63,372 annual savings opportunity with 140% ROI. Implementation plan includes 4 phases over 6-8 weeks with minimal risk.,"
        step_count=15,
        messages=[ )
        { )
        "role": "user,"
        "content": "I need a comprehensive analysis of our cloud infrastructure,"
        "timestamp: datetime.now(timezone.utc).isoformat(),"
        "metadata": {"priority": "high", "scope": "enterprise}"
        },
        { )
        "role": "assistant,"
        "content": "I"ll perform a comprehensive analysis of your cloud infrastructure...","
        "timestamp: datetime.now(timezone.utc).isoformat(),"
        "metadata": {"analysis_type": "comprehensive", "estimated_duration": "15_minutes}"
        },
        { )
        "role": "system,"
        "content": "Analysis phase 1 completed - Infrastructure audit,"
        "timestamp: datetime.now(timezone.utc).isoformat(),"
        "metadata": {"phase": 1, "status": "completed}"
    
        ],
        metadata=AgentMetadata( )
execution_context={"environment": "production",, "region": "us-east-1",, "instance_type": "enterprise",, "analysis_depth": "comprehensive}"
        },
custom_fields={"customer_tier": "enterprise",, "sla_level": "premium",, "compliance_requirements": "SOC2,HIPAA,PCI",, "business_unit": "cloud_optimization}"
        ),
quality_metrics={"analysis_completeness": 0.95,, "confidence_score": 0.92,, "data_quality": 0.89,, "recommendation_relevance: 0.94}"
        },
context_tracking={"conversation_depth": 5,, "topic_coherence": 0.91,, "user_satisfaction_predicted": 0.88,, "business_value_score: 0.96}"
    def test_serialize_message_safely_basic_types(self, websocket_manager):
        """Test basic type serialization."""

    # Test None
        result = websocket_manager._serialize_message_safely(None)"""
        result = websocket_manager._serialize_message_safely(None)"""
"""
"""
        test_dict = {"type": "test", "data": "value}"
        result = websocket_manager._serialize_message_safely(test_dict)
        assert result == test_dict

    # Test string (not typical for WebSocket but should handle)
        result = websocket_manager._serialize_message_safely("test_string)"
        assert result == "test_string"

    # Test number
        result = websocket_manager._serialize_message_safely(42)
        assert result == 42

    def test_serialize_message_safely_pydantic_models(self, websocket_manager):
        """Test Pydantic model serialization.""""""
        """Test Pydantic model serialization.""""""
    # Test WebSocketMessage"""
    # Test WebSocketMessage"""
        type="agent_update,"
        payload={"agent_name": "test", "status": "active},"
        sender="test-sender"
    
        result = websocket_manager._serialize_message_safely(ws_message)

        assert isinstance(result, "dict)"
        assert result["type"] == "agent_update"
        assert result["sender"] == "test-sender"

    # Test BaseWebSocketPayload
        base_payload = BaseWebSocketPayload()
        result = websocket_manager._serialize_message_safely(base_payload)

        assert isinstance(result, "dict)"
        assert "timestamp in result"
        assert "correlation_id in result"

    def test_serialize_message_safely_complex_deep_agent_state(self, websocket_manager, complex_deep_agent_state):
        """Test complex DeepAgentState serialization."""

        result = websocket_manager._serialize_message_safely(complex_deep_agent_state)

    # Must be dict
        assert isinstance(result, "dict)"

    # Test JSON serialization
        json_str = json.dumps(result)"""
        json_str = json.dumps(result)"""
"""
"""
        assert deserialized["user_request] == complex_deep_agent_state.user_request"
        assert deserialized["run_id] == complex_deep_agent_state.run_id"
        assert deserialized["step_count] == 15"

    # Verify complex nested objects are serialized
        assert "optimizations_result in deserialized"
        opt_result = deserialized["optimizations_result]"
        assert opt_result["cost_savings] == 5280.95"
        assert len(opt_result["recommendations]) == 5"

    # Verify action plan with complex nested structures
        assert "action_plan_result in deserialized"
        action_plan = deserialized["action_plan_result]"
        assert len(action_plan["actions]) == 3"
        assert len(action_plan["execution_timeline]) == 4"
        assert "cost_benefit_analysis in action_plan"
        assert action_plan["cost_benefit_analysis"]["roi_percentage] == 140.8"

    # Verify all result types are included
        assert "report_result in deserialized"
        assert "synthetic_data_result in deserialized"
        assert "supply_research_result in deserialized"

@pytest.mark.asyncio
    async def test_serialize_message_safely_async_performance(self, websocket_manager, complex_deep_agent_state):
    """Test async serialization performance."""

        # Test with complex state
start_time = time.time()
        # Should complete quickly (under 2 seconds even for complex data)
assert (end_time - start_time) < 2.0

        # Result should be JSON serializable
json_str = json.dumps(result)
assert len(json_str) > 1000  # Should be substantial content"""
assert len(json_str) > 1000  # Should be substantial content"""
        # Verify accuracy"""
        # Verify accuracy"""
assert deserialized["optimizations_result"]["cost_savings] == 5280.95"

@pytest.mark.asyncio
    async def test_serialize_message_safely_async_timeout(self, websocket_manager):
    """Test async serialization timeout handling."""

            # Create a mock that simulates slow serialization
with patch.object(websocket_manager, '_serialize_message_safely') as mock_sync:"""
with patch.object(websocket_manager, '_serialize_message_safely') as mock_sync:"""
time.sleep(6)  # Longer than 5-second timeout"""
time.sleep(6)  # Longer than 5-second timeout"""
return {"type": "slow}"

mock_sync.side_effect = slow_serialize

    # Should timeout and return fallback
result = await websocket_manager._serialize_message_safely_async({"test": "data})"

    # Should get timeout fallback response
assert "serialization_error in result"
assert "timed out" in result["serialization_error]"

def test_serialize_message_safely_error_recovery(self, websocket_manager):
    pass
"""Test error recovery in serialization."""

    # Create a problematic object that fails model_dump"""
    # Create a problematic object that fails model_dump"""
    def model_dump(self, **kwargs):"""
    def model_dump(self, **kwargs):"""
        raise ValueError("Serialization failed)"

    def to_dict(self):
        pass
        raise RuntimeError("to_dict also failed)"

    def dict(self):
        pass
        raise TypeError("dict method failed too)"

    def __str__(self):
        pass
        return "ProblematicObject representation"

        problematic = ProblematicObject()
        result = websocket_manager._serialize_message_safely(problematic)

    # Should fallback to string representation
        assert isinstance(result, "dict)"
        assert "payload in result"
        assert "ProblematicObject representation" in result["payload]"
        assert "serialization_error in result"

    def test_serialize_message_safely_with_frontend_type_conversion(self, websocket_manager):
        """Test message type conversion for frontend compatibility.""""""
        """Test message type conversion for frontend compatibility.""""""
    # Test various backend message types"""
    # Test various backend message types"""
        "agent_status_update,"
        "tool_execution_started,"
        "sub_agent_completed,"
        "optimization_result_ready"
    

        for backend_type in backend_types:
        message = {"type": backend_type, "payload": {"test": "data}}"
        result = websocket_manager._serialize_message_safely(message)

        # Should convert to frontend type
        expected_frontend_type = get_frontend_message_type(backend_type)
        assert result["type] == expected_frontend_type"

    def test_serialize_message_safely_special_characters(self, websocket_manager):
        """Test serialization with special characters and unicode."""
"""
"""
special_message = {"type": "agent_message",, "payload": { ), "unicode_text": "Hello [U+4E16][U+"754C"]! [U+1F30D] [U+00D1]o[U+00F1]o caf[U+00E9] r[U+00E9]sum[U+00E9]",, "special_chars": ["@", "#", "$", "%", "^", "&", "*"],, "emojis": ["[U+1F600]", "[U+1F680]", " IDEA: ", " LIGHTNING: ", "[U+1F31F]"],, "quotes": ["'single'", '"double"', "`backtick`"],, "newlines_and_tabs": "Line 1}"
        Line 2\tTabbed","
        "null_and_empty": [None, "", "   ],"
        "control_chars": "\u0000\u0001\u0002"
    
    

        result = websocket_manager._serialize_message_safely(special_message)

    # Should serialize without errors
        json_str = json.dumps(result, ensure_ascii=False)
        deserialized = json.loads(json_str)

    # Verify special characters are preserved
        assert "[U+4E16][U+"754C"]" in deserialized["payload"]["unicode_text]"
        assert "[U+1F30D]" in deserialized["payload"]["unicode_text]"
        assert len(deserialized["payload"]["emojis]) == 5"

    def test_serialize_message_safely_deeply_nested_structures(self, websocket_manager):
        """Test serialization of deeply nested structures."""
"""
"""
    def create_nested_dict(depth):"""
    def create_nested_dict(depth):"""
        return {"value": f"leaf_value, ""numbers: [1, 2, 3]}"
        return { )
        "level: depth,"
        "nested: create_nested_dict(depth - 1),"
        "array": [{"item: i} for i in range(3)],"
        "metadata": {"depth": depth, "type": "nested}"
        

deeply_nested = {"type": "deeply_nested",, "payload: create_nested_dict(10)}"
        result = websocket_manager._serialize_message_safely(deeply_nested)

        # Should serialize successfully
        json_str = json.dumps(result)
        deserialized = json.loads(json_str)

        # Verify structure is preserved
        assert deserialized["type"] == "deeply_nested"
        current = deserialized["payload]"
        for expected_level in range(10, 0, -1):
        assert current["level] == expected_level"
        if expected_level > 1:
        current = current["nested]"
        else:
        assert current["nested"]["value"] == "leaf_value"

@pytest.mark.asyncio
    async def test_serialize_message_safely_async_concurrent_calls(self, websocket_manager, complex_deep_agent_state):
    """Test concurrent async serialization calls."""

                        # Create multiple complex messages for concurrent serialization"""
                        # Create multiple complex messages for concurrent serialization"""
for i in range(20):"""
for i in range(20):"""
state = complex_deep_agent_state.copy_with_updates(run_id="formatted_string,, step_count=i + 1)"
messages.append(state)

                            # Serialize all concurrently
start_time = time.time()
websocket_manager._serialize_message_safely_async(msg)
for msg in messages
                            
results = await asyncio.gather(*tasks)
end_time = time.time()

                            # Should complete reasonably quickly
assert (end_time - start_time) < 10.0

                            # All should succeed
assert len(results) == 20

                            # Verify each result is correct
for i, result in enumerate(results):
    json_str = json.dumps(result)
deserialized = json.loads(json_str)
assert deserialized["run_id"] == "formatted_string"
assert deserialized["step_count] == i + 1"

def test_serialize_message_safely_circular_reference_protection(self, websocket_manager):
    pass
"""Test protection against circular references."""
"""
"""
circular_dict = {"type": "circular", "payload: {}}"
circular_dict["payload"]["self_reference] = circular_dict  # Circular reference"

    # Should handle gracefully (either by breaking the cycle or falling back)
try:
    pass
result = websocket_manager._serialize_message_safely(circular_dict)
        # If it doesn't throw, it should produce a valid result'
json.dumps(result)  # This should not fail
except (ValueError, TypeError, RecursionError):
            # If it does throw, it should be a controlled error, not infinite recursion
pytest.fail("Circular reference caused uncontrolled error)"

def test_serialize_message_safely_very_large_messages(self, websocket_manager):
    pass
"""Test handling of very large messages."""
"""
"""
large_array = ["x * 1000 for _ in range(1000)]  # "1MB" of data"
large_message = {"type": "large_message",, "payload": { ), "large_array": large_array,, "metadata": {"size": len(large_array), "item_size: 1000}}"
    # Should serialize (WebSocket manager doesn't enforce size limits during serialization)'
result = websocket_manager._serialize_message_safely(large_message)

    # Should be JSON serializable
json_str = json.dumps(result)
assert len(json_str) > 1000000  # Should be > "1MB"

    # Verify accuracy
deserialized = json.loads(json_str)
assert len(deserialized["payload"]["large_array]) == 1000"

def test_serialize_message_safely_datetime_handling(self, websocket_manager):
    pass
"""Test proper datetime serialization."""
"""
"""
message_with_datetimes = {"type": "datetime_test",, "payload": { ), "timestamp": now,, "created_at": now.isoformat(),, "dates_array": [now, datetime(2024, 1, 1, tzinfo=timezone.utc)],, "nested_datetime": { ), "event_time": now,, "processed_at: now.timestamp()}"
result = websocket_manager._serialize_message_safely(message_with_datetimes)

    # Should serialize successfully
json_str = json.dumps(result)
deserialized = json.loads(json_str)

    # Datetimes should be converted to JSON-compatible format
assert isinstance(deserialized["payload"]["timestamp"], "str)"
assert isinstance(deserialized["payload"]["created_at"], "str)"
assert isinstance(deserialized["payload"]["nested_datetime"]["processed_at"], "(int, float))"

def test_serialize_message_safely_websocket_error_objects(self, websocket_manager):
    pass
"""Test serialization of WebSocket error objects.""""""
"""Test serialization of WebSocket error objects.""""""
    # Test WebSocketError model"""
    # Test WebSocketError model"""
message="Connection lost unexpectedly,"
error_type="connection_error,"
code="WS_CONN_LOST,"
severity="high,"
details={"connection_id": "conn_123",, "duration_ms": 1500,, "retry_attempts": 3,, "last_ping: datetime.now(timezone.utc).isoformat()}"
},
trace_id="trace-abc-123"
    

result = websocket_manager._serialize_message_safely(ws_error)

    # Should serialize successfully
json_str = json.dumps(result)
deserialized = json.loads(json_str)

    # Verify error fields are preserved
assert deserialized["message"] == "Connection lost unexpectedly"
assert deserialized["error_type"] == "connection_error"
assert deserialized["severity"] == "high"
assert "connection_id" in deserialized["details]"

@pytest.mark.asyncio
    async def test_websocket_manager_integration_with_serialization(self, websocket_manager):
    """Test integration between WebSocket manager methods and serialization.""""""
"""Test integration between WebSocket manager methods and serialization.""""""
        # Test send_to_thread method uses serialization properly"""
        # Test send_to_thread method uses serialization properly"""
user_request="Test integration,"
run_id="integration-test,"
optimizations_result=OptimizationsResult( )
optimization_type="integration_test,"
recommendations=["Test recommendation],"
cost_savings=100.0
        
        

        # Mock the actual WebSocket sending
websocket_manager.send_to_thread = AsyncMock(return_value=True)

        # This should use the serialization methods internally
await websocket_manager.send_to_thread("test-thread, complex_message)"

        # Verify it was called
websocket_manager.send_to_thread.assert_called_once()

        # Verify the message would be serializable
serialized = websocket_manager._serialize_message_safely(complex_message)
json_str = json.dumps(serialized)
assert len(json_str) > 100  # Should have substantial content
pass

]
}}}}}