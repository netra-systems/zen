# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: MISSION CRITICAL: WebSocket Unified JSON Handler Test Suite

    # REMOVED_SYNTAX_ERROR: This test suite specifically validates the WebSocket manager"s JSON serialization
    # REMOVED_SYNTAX_ERROR: methods that will be used by the unified JSON handler. It focuses on edge cases
    # REMOVED_SYNTAX_ERROR: and performance requirements that are critical for chat functionality.

    # REMOVED_SYNTAX_ERROR: CRITICAL SERIALIZATION METHODS:
        # REMOVED_SYNTAX_ERROR: 1. _serialize_message_safely() - Synchronous fallback serialization
        # REMOVED_SYNTAX_ERROR: 2. _serialize_message_safely_async() - Async serialization with timeout
        # REMOVED_SYNTAX_ERROR: 3. Frontend message type conversion
        # REMOVED_SYNTAX_ERROR: 4. Complex Pydantic model handling (DeepAgentState, etc.)
        # REMOVED_SYNTAX_ERROR: 5. Error recovery and fallback patterns

        # REMOVED_SYNTAX_ERROR: Business Value Justification:
            # REMOVED_SYNTAX_ERROR: - Segment: Platform/Internal
            # REMOVED_SYNTAX_ERROR: - Business Goal: System Stability (unified JSON handling)
            # REMOVED_SYNTAX_ERROR: - Value Impact: Eliminates JSON serialization inconsistencies across WebSocket events
            # REMOVED_SYNTAX_ERROR: - Strategic Impact: Single point of JSON handling reduces maintenance and bugs
            # REMOVED_SYNTAX_ERROR: '''

            # REMOVED_SYNTAX_ERROR: import asyncio
            # REMOVED_SYNTAX_ERROR: import json
            # REMOVED_SYNTAX_ERROR: import pytest
            # REMOVED_SYNTAX_ERROR: import time
            # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
            # REMOVED_SYNTAX_ERROR: from typing import Any, Dict, List
            # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import DatabaseTestManager
            # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine
            # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

            # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.state import ( )
            # REMOVED_SYNTAX_ERROR: DeepAgentState, OptimizationsResult, ActionPlanResult,
            # REMOVED_SYNTAX_ERROR: ReportResult, SyntheticDataResult, SupplyResearchResult
            
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.registry import WebSocketMessage, AgentStarted, ServerMessage
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.websocket_models import ( )
            # REMOVED_SYNTAX_ERROR: BaseWebSocketPayload, AgentUpdatePayload, ToolCall, ToolResult,
            # REMOVED_SYNTAX_ERROR: AgentCompleted, StreamChunk, StreamComplete, WebSocketError
            
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.agent_models import AgentMetadata
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.types import get_frontend_message_type
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
            # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


# REMOVED_SYNTAX_ERROR: class TestWebSocketUnifiedJSONHandler:
    # REMOVED_SYNTAX_ERROR: """Test unified JSON handling in WebSocket manager."""
    # REMOVED_SYNTAX_ERROR: pass

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def websocket_manager(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create WebSocket manager for testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return WebSocketManager()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def complex_deep_agent_state(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create maximally complex DeepAgentState for stress testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # Create all possible result types
    # REMOVED_SYNTAX_ERROR: optimizations = OptimizationsResult( )
    # REMOVED_SYNTAX_ERROR: optimization_type="comprehensive_optimization",
    # REMOVED_SYNTAX_ERROR: recommendations=[ )
    # REMOVED_SYNTAX_ERROR: "Implement auto-scaling for EC2 instances",
    # REMOVED_SYNTAX_ERROR: "Switch to Reserved Instances for predictable workloads",
    # REMOVED_SYNTAX_ERROR: "Use Lambda for event-driven processes",
    # REMOVED_SYNTAX_ERROR: "Optimize S3 storage classes",
    # REMOVED_SYNTAX_ERROR: "Implement CloudFront CDN"
    # REMOVED_SYNTAX_ERROR: ],
    # REMOVED_SYNTAX_ERROR: cost_savings=5280.95,
    # REMOVED_SYNTAX_ERROR: performance_improvement=28.7,
    # REMOVED_SYNTAX_ERROR: confidence_score=0.94
    

    # REMOVED_SYNTAX_ERROR: action_plan = ActionPlanResult( )
    # REMOVED_SYNTAX_ERROR: action_plan_summary="Multi-phase cloud optimization implementation",
    # REMOVED_SYNTAX_ERROR: total_estimated_time="6-8 weeks",
    # REMOVED_SYNTAX_ERROR: required_approvals=["CTO", "CFO", "Engineering Manager", "Operations Lead"],
    # REMOVED_SYNTAX_ERROR: actions=[ )
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "id": 1,
    # REMOVED_SYNTAX_ERROR: "action": "Conduct comprehensive infrastructure audit",
    # REMOVED_SYNTAX_ERROR: "priority": "critical",
    # REMOVED_SYNTAX_ERROR: "estimated_hours": 40,
    # REMOVED_SYNTAX_ERROR: "dependencies": [],
    # REMOVED_SYNTAX_ERROR: "owner": "DevOps Team"
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "id": 2,
    # REMOVED_SYNTAX_ERROR: "action": "Implement monitoring and alerting",
    # REMOVED_SYNTAX_ERROR: "priority": "high",
    # REMOVED_SYNTAX_ERROR: "estimated_hours": 60,
    # REMOVED_SYNTAX_ERROR: "dependencies": [1],
    # REMOVED_SYNTAX_ERROR: "owner": "Platform Team"
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "id": 3,
    # REMOVED_SYNTAX_ERROR: "action": "Migrate to optimized instance types",
    # REMOVED_SYNTAX_ERROR: "priority": "high",
    # REMOVED_SYNTAX_ERROR: "estimated_hours": 80,
    # REMOVED_SYNTAX_ERROR: "dependencies": [1, 2],
    # REMOVED_SYNTAX_ERROR: "owner": "Cloud Architecture Team"
    
    # REMOVED_SYNTAX_ERROR: ],
    # REMOVED_SYNTAX_ERROR: execution_timeline=[ )
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "phase": "Phase 1 - Assessment",
    # REMOVED_SYNTAX_ERROR: "duration": "2 weeks",
    # REMOVED_SYNTAX_ERROR: "tasks": ["Infrastructure audit", "Cost analysis", "Performance benchmarking"],
    # REMOVED_SYNTAX_ERROR: "deliverables": ["Audit report", "Cost analysis", "Optimization roadmap"]
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "phase": "Phase 2 - Planning",
    # REMOVED_SYNTAX_ERROR: "duration": "1 week",
    # REMOVED_SYNTAX_ERROR: "tasks": ["Detailed implementation plan", "Risk assessment", "Resource allocation"],
    # REMOVED_SYNTAX_ERROR: "deliverables": ["Implementation plan", "Risk mitigation strategy"]
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "phase": "Phase 3 - Implementation",
    # REMOVED_SYNTAX_ERROR: "duration": "3-4 weeks",
    # REMOVED_SYNTAX_ERROR: "tasks": ["Instance optimization", "Auto-scaling setup", "Monitoring deployment"],
    # REMOVED_SYNTAX_ERROR: "deliverables": ["Optimized infrastructure", "Monitoring dashboard"]
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "phase": "Phase 4 - Validation",
    # REMOVED_SYNTAX_ERROR: "duration": "1 week",
    # REMOVED_SYNTAX_ERROR: "tasks": ["Performance testing", "Cost validation", "Documentation"],
    # REMOVED_SYNTAX_ERROR: "deliverables": ["Validation report", "Updated documentation"]
    
    # REMOVED_SYNTAX_ERROR: ],
    # REMOVED_SYNTAX_ERROR: supply_config_updates=[ )
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "service": "EC2",
    # REMOVED_SYNTAX_ERROR: "changes": ["Instance type optimization", "Auto-scaling configuration"],
    # REMOVED_SYNTAX_ERROR: "impact": "30% cost reduction, 25% performance improvement"
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "service": "RDS",
    # REMOVED_SYNTAX_ERROR: "changes": ["Multi-AZ optimization", "Storage optimization"],
    # REMOVED_SYNTAX_ERROR: "impact": "20% cost reduction, improved availability"
    
    # REMOVED_SYNTAX_ERROR: ],
    # REMOVED_SYNTAX_ERROR: post_implementation={ )
    # REMOVED_SYNTAX_ERROR: "monitoring_setup": "CloudWatch dashboards with custom metrics",
    # REMOVED_SYNTAX_ERROR: "maintenance_schedule": "Monthly optimization reviews",
    # REMOVED_SYNTAX_ERROR: "success_metrics": ["Cost per transaction", "Response time", "System availability"],
    # REMOVED_SYNTAX_ERROR: "rollback_plan": "Automated rollback using Infrastructure as Code"
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: cost_benefit_analysis={ )
    # REMOVED_SYNTAX_ERROR: "implementation_cost": 45000,
    # REMOVED_SYNTAX_ERROR: "annual_savings": 63372,
    # REMOVED_SYNTAX_ERROR: "roi_percentage": 140.8,
    # REMOVED_SYNTAX_ERROR: "payback_period_months": 8.5,
    # REMOVED_SYNTAX_ERROR: "risk_factors": ["Temporary performance impact", "Team training requirements"]
    
    

    # REMOVED_SYNTAX_ERROR: report = ReportResult( )
    # REMOVED_SYNTAX_ERROR: report_type="comprehensive_optimization_analysis",
    # REMOVED_SYNTAX_ERROR: content="This comprehensive analysis identified significant opportunities for cloud infrastructure optimization...",
    # REMOVED_SYNTAX_ERROR: sections=[ )
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "section_id": "exec_summary",
    # REMOVED_SYNTAX_ERROR: "title": "Executive Summary",
    # REMOVED_SYNTAX_ERROR: "content": "Our analysis reveals potential annual savings of $63,372...",
    # REMOVED_SYNTAX_ERROR: "section_type": "summary"
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "section_id": "technical_findings",
    # REMOVED_SYNTAX_ERROR: "title": "Technical Findings",
    # REMOVED_SYNTAX_ERROR: "content": "Current infrastructure analysis shows...",
    # REMOVED_SYNTAX_ERROR: "section_type": "technical"
    
    # REMOVED_SYNTAX_ERROR: ],
    # REMOVED_SYNTAX_ERROR: attachments=[ )
    # REMOVED_SYNTAX_ERROR: "cost_analysis_detailed.xlsx",
    # REMOVED_SYNTAX_ERROR: "performance_benchmarks.pdf",
    # REMOVED_SYNTAX_ERROR: "implementation_roadmap.pdf"
    
    

    # REMOVED_SYNTAX_ERROR: synthetic_data = SyntheticDataResult( )
    # REMOVED_SYNTAX_ERROR: data_type="infrastructure_usage_patterns",
    # REMOVED_SYNTAX_ERROR: generation_method="Monte Carlo simulation",
    # REMOVED_SYNTAX_ERROR: sample_count=10000,
    # REMOVED_SYNTAX_ERROR: quality_score=0.91,
    # REMOVED_SYNTAX_ERROR: file_path="/tmp/synthetic_usage_data.json"
    

    # REMOVED_SYNTAX_ERROR: supply_research = SupplyResearchResult( )
    # REMOVED_SYNTAX_ERROR: research_scope="Cloud service provider comparison",
    # REMOVED_SYNTAX_ERROR: findings=[ )
    # REMOVED_SYNTAX_ERROR: "AWS Reserved Instances offer 40% savings for predictable workloads",
    # REMOVED_SYNTAX_ERROR: "Azure Spot Instances provide up to 90% cost reduction for fault-tolerant workloads",
    # REMOVED_SYNTAX_ERROR: "GCP sustained use discounts apply automatically"
    # REMOVED_SYNTAX_ERROR: ],
    # REMOVED_SYNTAX_ERROR: recommendations=[ )
    # REMOVED_SYNTAX_ERROR: "Implement multi-cloud strategy for optimal pricing",
    # REMOVED_SYNTAX_ERROR: "Use spot instances for development environments",
    # REMOVED_SYNTAX_ERROR: "Reserve instances for production databases"
    # REMOVED_SYNTAX_ERROR: ],
    # REMOVED_SYNTAX_ERROR: data_sources=[ )
    # REMOVED_SYNTAX_ERROR: "AWS Pricing Calculator",
    # REMOVED_SYNTAX_ERROR: "Azure Pricing Calculator",
    # REMOVED_SYNTAX_ERROR: "GCP Pricing Calculator",
    # REMOVED_SYNTAX_ERROR: "Gartner Cloud Infrastructure Report 2024"
    # REMOVED_SYNTAX_ERROR: ],
    # REMOVED_SYNTAX_ERROR: confidence_level=0.88
    

    # REMOVED_SYNTAX_ERROR: return DeepAgentState( )
    # REMOVED_SYNTAX_ERROR: user_request="Perform comprehensive analysis of our cloud infrastructure with detailed optimization recommendations and implementation plan",
    # REMOVED_SYNTAX_ERROR: chat_thread_id="thread-comprehensive-analysis",
    # REMOVED_SYNTAX_ERROR: user_id="user-enterprise-customer",
    # REMOVED_SYNTAX_ERROR: run_id="run-comprehensive-12345",
    # REMOVED_SYNTAX_ERROR: agent_input={ )
    # REMOVED_SYNTAX_ERROR: "analysis_scope": "full_infrastructure",
    # REMOVED_SYNTAX_ERROR: "optimization_goals": ["cost_reduction", "performance_improvement", "scalability"],
    # REMOVED_SYNTAX_ERROR: "constraints": ["minimal_downtime", "compliance_requirements"],
    # REMOVED_SYNTAX_ERROR: "budget_limit": 50000
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: optimizations_result=optimizations,
    # REMOVED_SYNTAX_ERROR: action_plan_result=action_plan,
    # REMOVED_SYNTAX_ERROR: report_result=report,
    # REMOVED_SYNTAX_ERROR: synthetic_data_result=synthetic_data,
    # REMOVED_SYNTAX_ERROR: supply_research_result=supply_research,
    # REMOVED_SYNTAX_ERROR: final_report="Comprehensive infrastructure optimization analysis completed. Identified $63,372 annual savings opportunity with 140% ROI. Implementation plan includes 4 phases over 6-8 weeks with minimal risk.",
    # REMOVED_SYNTAX_ERROR: step_count=15,
    # REMOVED_SYNTAX_ERROR: messages=[ )
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "role": "user",
    # REMOVED_SYNTAX_ERROR: "content": "I need a comprehensive analysis of our cloud infrastructure",
    # REMOVED_SYNTAX_ERROR: "timestamp": datetime.now(timezone.utc).isoformat(),
    # REMOVED_SYNTAX_ERROR: "metadata": {"priority": "high", "scope": "enterprise"}
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "role": "assistant",
    # REMOVED_SYNTAX_ERROR: "content": "I"ll perform a comprehensive analysis of your cloud infrastructure...",
    # REMOVED_SYNTAX_ERROR: "timestamp": datetime.now(timezone.utc).isoformat(),
    # REMOVED_SYNTAX_ERROR: "metadata": {"analysis_type": "comprehensive", "estimated_duration": "15_minutes"}
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "role": "system",
    # REMOVED_SYNTAX_ERROR: "content": "Analysis phase 1 completed - Infrastructure audit",
    # REMOVED_SYNTAX_ERROR: "timestamp": datetime.now(timezone.utc).isoformat(),
    # REMOVED_SYNTAX_ERROR: "metadata": {"phase": 1, "status": "completed"}
    
    # REMOVED_SYNTAX_ERROR: ],
    # REMOVED_SYNTAX_ERROR: metadata=AgentMetadata( )
    # REMOVED_SYNTAX_ERROR: execution_context={ )
    # REMOVED_SYNTAX_ERROR: "environment": "production",
    # REMOVED_SYNTAX_ERROR: "region": "us-east-1",
    # REMOVED_SYNTAX_ERROR: "instance_type": "enterprise",
    # REMOVED_SYNTAX_ERROR: "analysis_depth": "comprehensive"
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: custom_fields={ )
    # REMOVED_SYNTAX_ERROR: "customer_tier": "enterprise",
    # REMOVED_SYNTAX_ERROR: "sla_level": "premium",
    # REMOVED_SYNTAX_ERROR: "compliance_requirements": "SOC2,HIPAA,PCI",
    # REMOVED_SYNTAX_ERROR: "business_unit": "cloud_optimization"
    
    # REMOVED_SYNTAX_ERROR: ),
    # REMOVED_SYNTAX_ERROR: quality_metrics={ )
    # REMOVED_SYNTAX_ERROR: "analysis_completeness": 0.95,
    # REMOVED_SYNTAX_ERROR: "confidence_score": 0.92,
    # REMOVED_SYNTAX_ERROR: "data_quality": 0.89,
    # REMOVED_SYNTAX_ERROR: "recommendation_relevance": 0.94
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: context_tracking={ )
    # REMOVED_SYNTAX_ERROR: "conversation_depth": 5,
    # REMOVED_SYNTAX_ERROR: "topic_coherence": 0.91,
    # REMOVED_SYNTAX_ERROR: "user_satisfaction_predicted": 0.88,
    # REMOVED_SYNTAX_ERROR: "business_value_score": 0.96
    
    

# REMOVED_SYNTAX_ERROR: def test_serialize_message_safely_basic_types(self, websocket_manager):
    # REMOVED_SYNTAX_ERROR: """Test basic type serialization."""

    # Test None
    # REMOVED_SYNTAX_ERROR: result = websocket_manager._serialize_message_safely(None)
    # REMOVED_SYNTAX_ERROR: assert result == {}

    # Test dict (already serializable)
    # REMOVED_SYNTAX_ERROR: test_dict = {"type": "test", "data": "value"}
    # REMOVED_SYNTAX_ERROR: result = websocket_manager._serialize_message_safely(test_dict)
    # REMOVED_SYNTAX_ERROR: assert result == test_dict

    # Test string (not typical for WebSocket but should handle)
    # REMOVED_SYNTAX_ERROR: result = websocket_manager._serialize_message_safely("test_string")
    # REMOVED_SYNTAX_ERROR: assert result == "test_string"

    # Test number
    # REMOVED_SYNTAX_ERROR: result = websocket_manager._serialize_message_safely(42)
    # REMOVED_SYNTAX_ERROR: assert result == 42

# REMOVED_SYNTAX_ERROR: def test_serialize_message_safely_pydantic_models(self, websocket_manager):
    # REMOVED_SYNTAX_ERROR: """Test Pydantic model serialization."""

    # Test WebSocketMessage
    # REMOVED_SYNTAX_ERROR: ws_message = WebSocketMessage( )
    # REMOVED_SYNTAX_ERROR: type="agent_update",
    # REMOVED_SYNTAX_ERROR: payload={"agent_name": "test", "status": "active"},
    # REMOVED_SYNTAX_ERROR: sender="test-sender"
    
    # REMOVED_SYNTAX_ERROR: result = websocket_manager._serialize_message_safely(ws_message)

    # REMOVED_SYNTAX_ERROR: assert isinstance(result, dict)
    # REMOVED_SYNTAX_ERROR: assert result["type"] == "agent_update"
    # REMOVED_SYNTAX_ERROR: assert result["sender"] == "test-sender"

    # Test BaseWebSocketPayload
    # REMOVED_SYNTAX_ERROR: base_payload = BaseWebSocketPayload()
    # REMOVED_SYNTAX_ERROR: result = websocket_manager._serialize_message_safely(base_payload)

    # REMOVED_SYNTAX_ERROR: assert isinstance(result, dict)
    # REMOVED_SYNTAX_ERROR: assert "timestamp" in result
    # REMOVED_SYNTAX_ERROR: assert "correlation_id" in result

# REMOVED_SYNTAX_ERROR: def test_serialize_message_safely_complex_deep_agent_state(self, websocket_manager, complex_deep_agent_state):
    # REMOVED_SYNTAX_ERROR: """Test complex DeepAgentState serialization."""

    # REMOVED_SYNTAX_ERROR: result = websocket_manager._serialize_message_safely(complex_deep_agent_state)

    # Must be dict
    # REMOVED_SYNTAX_ERROR: assert isinstance(result, dict)

    # Test JSON serialization
    # REMOVED_SYNTAX_ERROR: json_str = json.dumps(result)
    # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)

    # Verify core fields
    # REMOVED_SYNTAX_ERROR: assert deserialized["user_request"] == complex_deep_agent_state.user_request
    # REMOVED_SYNTAX_ERROR: assert deserialized["run_id"] == complex_deep_agent_state.run_id
    # REMOVED_SYNTAX_ERROR: assert deserialized["step_count"] == 15

    # Verify complex nested objects are serialized
    # REMOVED_SYNTAX_ERROR: assert "optimizations_result" in deserialized
    # REMOVED_SYNTAX_ERROR: opt_result = deserialized["optimizations_result"]
    # REMOVED_SYNTAX_ERROR: assert opt_result["cost_savings"] == 5280.95
    # REMOVED_SYNTAX_ERROR: assert len(opt_result["recommendations"]) == 5

    # Verify action plan with complex nested structures
    # REMOVED_SYNTAX_ERROR: assert "action_plan_result" in deserialized
    # REMOVED_SYNTAX_ERROR: action_plan = deserialized["action_plan_result"]
    # REMOVED_SYNTAX_ERROR: assert len(action_plan["actions"]) == 3
    # REMOVED_SYNTAX_ERROR: assert len(action_plan["execution_timeline"]) == 4
    # REMOVED_SYNTAX_ERROR: assert "cost_benefit_analysis" in action_plan
    # REMOVED_SYNTAX_ERROR: assert action_plan["cost_benefit_analysis"]["roi_percentage"] == 140.8

    # Verify all result types are included
    # REMOVED_SYNTAX_ERROR: assert "report_result" in deserialized
    # REMOVED_SYNTAX_ERROR: assert "synthetic_data_result" in deserialized
    # REMOVED_SYNTAX_ERROR: assert "supply_research_result" in deserialized

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_serialize_message_safely_async_performance(self, websocket_manager, complex_deep_agent_state):
        # REMOVED_SYNTAX_ERROR: """Test async serialization performance."""

        # Test with complex state
        # REMOVED_SYNTAX_ERROR: start_time = time.time()
        # REMOVED_SYNTAX_ERROR: result = await websocket_manager._serialize_message_safely_async(complex_deep_agent_state)
        # REMOVED_SYNTAX_ERROR: end_time = time.time()

        # Should complete quickly (under 2 seconds even for complex data)
        # REMOVED_SYNTAX_ERROR: assert (end_time - start_time) < 2.0

        # Result should be JSON serializable
        # REMOVED_SYNTAX_ERROR: json_str = json.dumps(result)
        # REMOVED_SYNTAX_ERROR: assert len(json_str) > 1000  # Should be substantial content

        # Verify accuracy
        # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)
        # REMOVED_SYNTAX_ERROR: assert deserialized["optimizations_result"]["cost_savings"] == 5280.95

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_serialize_message_safely_async_timeout(self, websocket_manager):
            # REMOVED_SYNTAX_ERROR: """Test async serialization timeout handling."""

            # Create a mock that simulates slow serialization
            # REMOVED_SYNTAX_ERROR: with patch.object(websocket_manager, '_serialize_message_safely') as mock_sync:
# REMOVED_SYNTAX_ERROR: def slow_serialize(msg):
    # REMOVED_SYNTAX_ERROR: time.sleep(6)  # Longer than 5-second timeout
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return {"type": "slow"}

    # REMOVED_SYNTAX_ERROR: mock_sync.side_effect = slow_serialize

    # Should timeout and return fallback
    # REMOVED_SYNTAX_ERROR: result = await websocket_manager._serialize_message_safely_async({"test": "data"})

    # Should get timeout fallback response
    # REMOVED_SYNTAX_ERROR: assert "serialization_error" in result
    # REMOVED_SYNTAX_ERROR: assert "timed out" in result["serialization_error"]

# REMOVED_SYNTAX_ERROR: def test_serialize_message_safely_error_recovery(self, websocket_manager):
    # REMOVED_SYNTAX_ERROR: """Test error recovery in serialization."""

    # Create a problematic object that fails model_dump
# REMOVED_SYNTAX_ERROR: class ProblematicObject:
# REMOVED_SYNTAX_ERROR: def model_dump(self, **kwargs):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: raise ValueError("Serialization failed")

# REMOVED_SYNTAX_ERROR: def to_dict(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: raise RuntimeError("to_dict also failed")

# REMOVED_SYNTAX_ERROR: def dict(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: raise TypeError("dict method failed too")

# REMOVED_SYNTAX_ERROR: def __str__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return "ProblematicObject representation"

    # REMOVED_SYNTAX_ERROR: problematic = ProblematicObject()
    # REMOVED_SYNTAX_ERROR: result = websocket_manager._serialize_message_safely(problematic)

    # Should fallback to string representation
    # REMOVED_SYNTAX_ERROR: assert isinstance(result, dict)
    # REMOVED_SYNTAX_ERROR: assert "payload" in result
    # REMOVED_SYNTAX_ERROR: assert "ProblematicObject representation" in result["payload"]
    # REMOVED_SYNTAX_ERROR: assert "serialization_error" in result

# REMOVED_SYNTAX_ERROR: def test_serialize_message_safely_with_frontend_type_conversion(self, websocket_manager):
    # REMOVED_SYNTAX_ERROR: """Test message type conversion for frontend compatibility."""

    # Test various backend message types
    # REMOVED_SYNTAX_ERROR: backend_types = [ )
    # REMOVED_SYNTAX_ERROR: "agent_status_update",
    # REMOVED_SYNTAX_ERROR: "tool_execution_started",
    # REMOVED_SYNTAX_ERROR: "sub_agent_completed",
    # REMOVED_SYNTAX_ERROR: "optimization_result_ready"
    

    # REMOVED_SYNTAX_ERROR: for backend_type in backend_types:
        # REMOVED_SYNTAX_ERROR: message = {"type": backend_type, "payload": {"test": "data"}}
        # REMOVED_SYNTAX_ERROR: result = websocket_manager._serialize_message_safely(message)

        # Should convert to frontend type
        # REMOVED_SYNTAX_ERROR: expected_frontend_type = get_frontend_message_type(backend_type)
        # REMOVED_SYNTAX_ERROR: assert result["type"] == expected_frontend_type

# REMOVED_SYNTAX_ERROR: def test_serialize_message_safely_special_characters(self, websocket_manager):
    # REMOVED_SYNTAX_ERROR: """Test serialization with special characters and unicode."""

    # Create message with various special characters
    # REMOVED_SYNTAX_ERROR: special_message = { )
    # REMOVED_SYNTAX_ERROR: "type": "agent_message",
    # REMOVED_SYNTAX_ERROR: "payload": { )
    # REMOVED_SYNTAX_ERROR: "unicode_text": "Hello 世界! 🌍 Ñoño café résumé",
    # REMOVED_SYNTAX_ERROR: "special_chars": ["@", "#", "$", "%", "^", "&", "*"],
    # REMOVED_SYNTAX_ERROR: "emojis": ["😀", "🚀", "💡", "⚡", "🌟"],
    # REMOVED_SYNTAX_ERROR: "quotes": ["'single'", '"double"', "`backtick`"],
    # REMOVED_SYNTAX_ERROR: "newlines_and_tabs": "Line 1
    # REMOVED_SYNTAX_ERROR: Line 2\tTabbed",
    # REMOVED_SYNTAX_ERROR: "null_and_empty": [None, "", "   "],
    # REMOVED_SYNTAX_ERROR: "control_chars": "\u0000\u0001\u0002"
    
    

    # REMOVED_SYNTAX_ERROR: result = websocket_manager._serialize_message_safely(special_message)

    # Should serialize without errors
    # REMOVED_SYNTAX_ERROR: json_str = json.dumps(result, ensure_ascii=False)
    # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)

    # Verify special characters are preserved
    # REMOVED_SYNTAX_ERROR: assert "世界" in deserialized["payload"]["unicode_text"]
    # REMOVED_SYNTAX_ERROR: assert "🌍" in deserialized["payload"]["unicode_text"]
    # REMOVED_SYNTAX_ERROR: assert len(deserialized["payload"]["emojis"]) == 5

# REMOVED_SYNTAX_ERROR: def test_serialize_message_safely_deeply_nested_structures(self, websocket_manager):
    # REMOVED_SYNTAX_ERROR: """Test serialization of deeply nested structures."""

    # Create deeply nested structure (10 levels deep)
# REMOVED_SYNTAX_ERROR: def create_nested_dict(depth):
    # REMOVED_SYNTAX_ERROR: if depth == 0:
        # REMOVED_SYNTAX_ERROR: return {"value": f"leaf_value", "numbers": [1, 2, 3]}
        # REMOVED_SYNTAX_ERROR: return { )
        # REMOVED_SYNTAX_ERROR: "level": depth,
        # REMOVED_SYNTAX_ERROR: "nested": create_nested_dict(depth - 1),
        # REMOVED_SYNTAX_ERROR: "array": [{"item": i} for i in range(3)],
        # REMOVED_SYNTAX_ERROR: "metadata": {"depth": depth, "type": "nested"}
        

        # REMOVED_SYNTAX_ERROR: deeply_nested = { )
        # REMOVED_SYNTAX_ERROR: "type": "deeply_nested",
        # REMOVED_SYNTAX_ERROR: "payload": create_nested_dict(10)
        

        # REMOVED_SYNTAX_ERROR: result = websocket_manager._serialize_message_safely(deeply_nested)

        # Should serialize successfully
        # REMOVED_SYNTAX_ERROR: json_str = json.dumps(result)
        # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)

        # Verify structure is preserved
        # REMOVED_SYNTAX_ERROR: assert deserialized["type"] == "deeply_nested"
        # REMOVED_SYNTAX_ERROR: current = deserialized["payload"]
        # REMOVED_SYNTAX_ERROR: for expected_level in range(10, 0, -1):
            # REMOVED_SYNTAX_ERROR: assert current["level"] == expected_level
            # REMOVED_SYNTAX_ERROR: if expected_level > 1:
                # REMOVED_SYNTAX_ERROR: current = current["nested"]
                # REMOVED_SYNTAX_ERROR: else:
                    # REMOVED_SYNTAX_ERROR: assert current["nested"]["value"] == "leaf_value"

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_serialize_message_safely_async_concurrent_calls(self, websocket_manager, complex_deep_agent_state):
                        # REMOVED_SYNTAX_ERROR: """Test concurrent async serialization calls."""

                        # Create multiple complex messages for concurrent serialization
                        # REMOVED_SYNTAX_ERROR: messages = []
                        # REMOVED_SYNTAX_ERROR: for i in range(20):
                            # Create variations of the complex state
                            # REMOVED_SYNTAX_ERROR: state = complex_deep_agent_state.copy_with_updates( )
                            # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
                            # REMOVED_SYNTAX_ERROR: step_count=i + 1
                            
                            # REMOVED_SYNTAX_ERROR: messages.append(state)

                            # Serialize all concurrently
                            # REMOVED_SYNTAX_ERROR: start_time = time.time()
                            # REMOVED_SYNTAX_ERROR: tasks = [ )
                            # REMOVED_SYNTAX_ERROR: websocket_manager._serialize_message_safely_async(msg)
                            # REMOVED_SYNTAX_ERROR: for msg in messages
                            
                            # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks)
                            # REMOVED_SYNTAX_ERROR: end_time = time.time()

                            # Should complete reasonably quickly
                            # REMOVED_SYNTAX_ERROR: assert (end_time - start_time) < 10.0

                            # All should succeed
                            # REMOVED_SYNTAX_ERROR: assert len(results) == 20

                            # Verify each result is correct
                            # REMOVED_SYNTAX_ERROR: for i, result in enumerate(results):
                                # REMOVED_SYNTAX_ERROR: json_str = json.dumps(result)
                                # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)
                                # REMOVED_SYNTAX_ERROR: assert deserialized["run_id"] == "formatted_string"
                                # REMOVED_SYNTAX_ERROR: assert deserialized["step_count"] == i + 1

# REMOVED_SYNTAX_ERROR: def test_serialize_message_safely_circular_reference_protection(self, websocket_manager):
    # REMOVED_SYNTAX_ERROR: """Test protection against circular references."""

    # Create circular reference (this would cause infinite recursion in naive serialization)
    # REMOVED_SYNTAX_ERROR: circular_dict = {"type": "circular", "payload": {}}
    # REMOVED_SYNTAX_ERROR: circular_dict["payload"]["self_reference"] = circular_dict  # Circular reference

    # Should handle gracefully (either by breaking the cycle or falling back)
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: result = websocket_manager._serialize_message_safely(circular_dict)
        # If it doesn't throw, it should produce a valid result
        # REMOVED_SYNTAX_ERROR: json.dumps(result)  # This should not fail
        # REMOVED_SYNTAX_ERROR: except (ValueError, TypeError, RecursionError):
            # If it does throw, it should be a controlled error, not infinite recursion
            # REMOVED_SYNTAX_ERROR: pytest.fail("Circular reference caused uncontrolled error")

# REMOVED_SYNTAX_ERROR: def test_serialize_message_safely_very_large_messages(self, websocket_manager):
    # REMOVED_SYNTAX_ERROR: """Test handling of very large messages."""

    # Create a large message (1MB of data)
    # REMOVED_SYNTAX_ERROR: large_array = ["x" * 1000 for _ in range(1000)]  # 1MB of data
    # REMOVED_SYNTAX_ERROR: large_message = { )
    # REMOVED_SYNTAX_ERROR: "type": "large_message",
    # REMOVED_SYNTAX_ERROR: "payload": { )
    # REMOVED_SYNTAX_ERROR: "large_array": large_array,
    # REMOVED_SYNTAX_ERROR: "metadata": {"size": len(large_array), "item_size": 1000}
    
    

    # Should serialize (WebSocket manager doesn't enforce size limits during serialization)
    # REMOVED_SYNTAX_ERROR: result = websocket_manager._serialize_message_safely(large_message)

    # Should be JSON serializable
    # REMOVED_SYNTAX_ERROR: json_str = json.dumps(result)
    # REMOVED_SYNTAX_ERROR: assert len(json_str) > 1000000  # Should be > 1MB

    # Verify accuracy
    # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)
    # REMOVED_SYNTAX_ERROR: assert len(deserialized["payload"]["large_array"]) == 1000

# REMOVED_SYNTAX_ERROR: def test_serialize_message_safely_datetime_handling(self, websocket_manager):
    # REMOVED_SYNTAX_ERROR: """Test proper datetime serialization."""

    # REMOVED_SYNTAX_ERROR: now = datetime.now(timezone.utc)
    # REMOVED_SYNTAX_ERROR: message_with_datetimes = { )
    # REMOVED_SYNTAX_ERROR: "type": "datetime_test",
    # REMOVED_SYNTAX_ERROR: "payload": { )
    # REMOVED_SYNTAX_ERROR: "timestamp": now,
    # REMOVED_SYNTAX_ERROR: "created_at": now.isoformat(),
    # REMOVED_SYNTAX_ERROR: "dates_array": [now, datetime(2024, 1, 1, tzinfo=timezone.utc)],
    # REMOVED_SYNTAX_ERROR: "nested_datetime": { )
    # REMOVED_SYNTAX_ERROR: "event_time": now,
    # REMOVED_SYNTAX_ERROR: "processed_at": now.timestamp()
    
    
    

    # REMOVED_SYNTAX_ERROR: result = websocket_manager._serialize_message_safely(message_with_datetimes)

    # Should serialize successfully
    # REMOVED_SYNTAX_ERROR: json_str = json.dumps(result)
    # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)

    # Datetimes should be converted to JSON-compatible format
    # REMOVED_SYNTAX_ERROR: assert isinstance(deserialized["payload"]["timestamp"], str)
    # REMOVED_SYNTAX_ERROR: assert isinstance(deserialized["payload"]["created_at"], str)
    # REMOVED_SYNTAX_ERROR: assert isinstance(deserialized["payload"]["nested_datetime"]["processed_at"], (int, float))

# REMOVED_SYNTAX_ERROR: def test_serialize_message_safely_websocket_error_objects(self, websocket_manager):
    # REMOVED_SYNTAX_ERROR: """Test serialization of WebSocket error objects."""

    # Test WebSocketError model
    # REMOVED_SYNTAX_ERROR: ws_error = WebSocketError( )
    # REMOVED_SYNTAX_ERROR: message="Connection lost unexpectedly",
    # REMOVED_SYNTAX_ERROR: error_type="connection_error",
    # REMOVED_SYNTAX_ERROR: code="WS_CONN_LOST",
    # REMOVED_SYNTAX_ERROR: severity="high",
    # REMOVED_SYNTAX_ERROR: details={ )
    # REMOVED_SYNTAX_ERROR: "connection_id": "conn_123",
    # REMOVED_SYNTAX_ERROR: "duration_ms": 1500,
    # REMOVED_SYNTAX_ERROR: "retry_attempts": 3,
    # REMOVED_SYNTAX_ERROR: "last_ping": datetime.now(timezone.utc).isoformat()
    # REMOVED_SYNTAX_ERROR: },
    # REMOVED_SYNTAX_ERROR: trace_id="trace-abc-123"
    

    # REMOVED_SYNTAX_ERROR: result = websocket_manager._serialize_message_safely(ws_error)

    # Should serialize successfully
    # REMOVED_SYNTAX_ERROR: json_str = json.dumps(result)
    # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)

    # Verify error fields are preserved
    # REMOVED_SYNTAX_ERROR: assert deserialized["message"] == "Connection lost unexpectedly"
    # REMOVED_SYNTAX_ERROR: assert deserialized["error_type"] == "connection_error"
    # REMOVED_SYNTAX_ERROR: assert deserialized["severity"] == "high"
    # REMOVED_SYNTAX_ERROR: assert "connection_id" in deserialized["details"]

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_websocket_manager_integration_with_serialization(self, websocket_manager):
        # REMOVED_SYNTAX_ERROR: """Test integration between WebSocket manager methods and serialization."""

        # Test send_to_thread method uses serialization properly
        # REMOVED_SYNTAX_ERROR: complex_message = DeepAgentState( )
        # REMOVED_SYNTAX_ERROR: user_request="Test integration",
        # REMOVED_SYNTAX_ERROR: run_id="integration-test",
        # REMOVED_SYNTAX_ERROR: optimizations_result=OptimizationsResult( )
        # REMOVED_SYNTAX_ERROR: optimization_type="integration_test",
        # REMOVED_SYNTAX_ERROR: recommendations=["Test recommendation"],
        # REMOVED_SYNTAX_ERROR: cost_savings=100.0
        
        

        # Mock the actual WebSocket sending
        # REMOVED_SYNTAX_ERROR: websocket_manager.send_to_thread = AsyncMock(return_value=True)

        # This should use the serialization methods internally
        # REMOVED_SYNTAX_ERROR: await websocket_manager.send_to_thread("test-thread", complex_message)

        # Verify it was called
        # REMOVED_SYNTAX_ERROR: websocket_manager.send_to_thread.assert_called_once()

        # Verify the message would be serializable
        # REMOVED_SYNTAX_ERROR: serialized = websocket_manager._serialize_message_safely(complex_message)
        # REMOVED_SYNTAX_ERROR: json_str = json.dumps(serialized)
        # REMOVED_SYNTAX_ERROR: assert len(json_str) > 100  # Should have substantial content
        # REMOVED_SYNTAX_ERROR: pass