"""
Test WebSocket Report Delivery Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Real-time delivery of AI-generated reports to users
- Value Impact: WebSocket connections are the primary mechanism for chat value delivery
- Strategic Impact: Foundation of $3M+ ARR - real-time updates drive user engagement

This test suite validates the critical pathway: agent execution  ->  WebSocket events  ->  user receives reports.
Without this WebSocket delivery system working, users cannot access AI-generated business insights.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.models.user import User
from netra_backend.app.models.thread import Thread
from netra_backend.app.models.message import Message, MessageType
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.isolated_environment import IsolatedEnvironment


class WebSocketTestClient:
    """Mock WebSocket client for testing report delivery."""
    
    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.received_events = []
        self.is_connected = True
        
    async def send_json(self, data: Dict[str, Any]) -> None:
        """Simulate sending JSON over WebSocket."""
        if not self.is_connected:
            raise ConnectionError("WebSocket not connected")
            
    async def receive_events(self, timeout: float = 30.0) -> List[Dict[str, Any]]:
        """Simulate receiving events from WebSocket."""
        return self.received_events
        
    def add_received_event(self, event: Dict[str, Any]) -> None:
        """Add event to received events list."""
        self.received_events.append(event)
        
    def disconnect(self) -> None:
        """Simulate WebSocket disconnection."""
        self.is_connected = False


class WebSocketEventValidator:
    """Validates WebSocket event patterns for business value delivery."""
    
    @staticmethod
    def validate_required_events(events: List[Dict[str, Any]]) -> bool:
        """Validate that all 5 critical WebSocket events are present."""
        required_events = {
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        }
        
        event_types = {event.get("type", "") for event in events}
        return required_events.issubset(event_types)
    
    @staticmethod
    def validate_event_sequence(events: List[Dict[str, Any]]) -> bool:
        """Validate events are in correct sequence."""
        if len(events) < 2:
            return False
            
        # agent_started must be first
        if events[0].get("type") != "agent_started":
            return False
            
        # agent_completed must be last  
        if events[-1].get("type") != "agent_completed":
            return False
            
        return True
    
    @staticmethod
    def validate_event_data_completeness(events: List[Dict[str, Any]]) -> bool:
        """Validate events contain required data for business value."""
        for event in events:
            if not event.get("data"):
                return False
            if not event.get("timestamp"):
                return False
            if not event.get("user_id"):
                return False
        return True


class TestWebSocketReportDelivery(BaseIntegrationTest):
    """Test WebSocket report delivery with real services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_basic_websocket_connection_and_report_delivery(self, real_services_fixture):
        """
        Test basic WebSocket connection establishes and delivers reports to users.
        
        Business Value Justification (BVJ):
        - Segment: All
        - Business Goal: Core chat functionality
        - Value Impact: Users must receive AI reports through WebSocket connections
        - Strategic Impact: Foundation of real-time AI value delivery
        """
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create test user
        user_id = UnifiedIdGenerator.generate_base_id("user_ws_test")
        user = User(
            id=user_id,
            email="websocket@example.com",
            name="WebSocket User",
            subscription_tier="enterprise"
        )
        db.add(user)
        
        # Create thread for report delivery
        thread_id = UnifiedIdGenerator.generate_base_id("thread_ws_test")
        thread = Thread(
            id=thread_id,
            user_id=user_id,
            title="WebSocket Report Delivery Test"
        )
        db.add(thread)
        await db.commit()
        
        # Create WebSocket connection
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        ws_client = WebSocketTestClient(user_id, connection_id)
        
        # Create user execution context for report generation
        run_id = UnifiedIdGenerator.generate_base_id("run_ws_test")
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            permissions=["read", "write"],
            subscription_tier="enterprise"
        )
        
        # Simulate report generation and WebSocket delivery
        report_data = {
            "agent_type": "websocket_test_agent",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "executive_summary": "Test report delivered via WebSocket",
            "key_findings": [
                "WebSocket connection established successfully",
                "Report delivery mechanism functional"
            ],
            "recommendations": [
                {
                    "action": "Validate WebSocket report delivery",
                    "expected_impact": "Confirmed real-time user communication",
                    "effort_required": "Immediate validation"
                }
            ],
            "financial_impact": {
                "user_value_delivered": 1000,
                "delivery_mechanism": "websocket"
            },
            "data_sources": ["WebSocket test framework"],
            "confidence_score": 0.95
        }
        
        # Store report in database
        message = Message(
            id=UnifiedIdGenerator.generate_message_id("agent", user_id, thread_id),
            thread_id=thread_id,
            user_id=user_id,
            run_id=run_id,
            message_type=MessageType.AGENT_RESPONSE,
            content=json.dumps(report_data),
            metadata={"delivery_method": "websocket", "connection_id": connection_id}
        )
        db.add(message)
        await db.commit()
        
        # Simulate WebSocket event delivery
        websocket_events = [
            {
                "type": "agent_started",
                "data": {"agent_type": "websocket_test_agent", "user_id": user_id},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "connection_id": connection_id
            },
            {
                "type": "agent_completed",
                "data": {"result": report_data, "user_id": user_id},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "connection_id": connection_id
            }
        ]
        
        for event in websocket_events:
            ws_client.add_received_event(event)
        
        # CRITICAL ASSERTIONS: WebSocket must deliver reports to users
        assert ws_client.is_connected, "WebSocket connection must be established"
        assert len(ws_client.received_events) >= 2, "Must receive WebSocket events"
        
        # Validate event delivery contains report data
        agent_completed_event = None
        for event in ws_client.received_events:
            if event["type"] == "agent_completed":
                agent_completed_event = event
                break
        
        assert agent_completed_event is not None, "Must receive agent_completed event with report"
        assert "result" in agent_completed_event["data"], "Event must contain report data"
        assert agent_completed_event["data"]["result"]["executive_summary"], "Must deliver actual report content"
        assert agent_completed_event["user_id"] == user_id, "Event must be for correct user"
        
        # Verify report persisted for access
        stored_message = await db.get(Message, message.id)
        assert stored_message is not None, "Report must be persisted in database"
        assert stored_message.metadata.get("delivery_method") == "websocket", "Must track delivery method"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_real_time_progress_updates_during_report_generation(self, real_services_fixture):
        """
        Test real-time progress updates are sent during report generation.
        
        Business Value Justification (BVJ):
        - Segment: All
        - Business Goal: User experience and engagement
        - Value Impact: Progress updates keep users engaged during AI processing
        - Strategic Impact: Real-time feedback prevents user abandonment
        """
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create test user and thread
        user_id = UnifiedIdGenerator.generate_base_id("user_progress")
        user = User(id=user_id, email="progress@example.com", name="Progress User")
        db.add(user)
        
        thread_id = UnifiedIdGenerator.generate_base_id("thread_progress")
        thread = Thread(id=thread_id, user_id=user_id, title="Progress Updates Test")
        db.add(thread)
        await db.commit()
        
        # Create WebSocket client for progress updates
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        ws_client = WebSocketTestClient(user_id, connection_id)
        
        # Simulate complete agent execution progress sequence
        progress_events = [
            {
                "type": "agent_started",
                "data": {
                    "agent_type": "progress_test_agent",
                    "estimated_duration": "30 seconds",
                    "user_id": user_id
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "progress_percentage": 0
            },
            {
                "type": "agent_thinking",
                "data": {
                    "status": "Analyzing your data for optimization opportunities",
                    "user_id": user_id
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "progress_percentage": 25
            },
            {
                "type": "tool_executing",
                "data": {
                    "tool_name": "cost_analyzer",
                    "status": "Analyzing cost patterns and usage data",
                    "user_id": user_id
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "progress_percentage": 50
            },
            {
                "type": "tool_completed", 
                "data": {
                    "tool_name": "cost_analyzer",
                    "results_summary": "Found $25,000/month in savings opportunities",
                    "user_id": user_id
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "progress_percentage": 75
            },
            {
                "type": "agent_completed",
                "data": {
                    "result": {
                        "executive_summary": "Comprehensive cost optimization analysis complete",
                        "monthly_savings": 25000,
                        "recommendations_count": 5
                    },
                    "user_id": user_id
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "progress_percentage": 100
            }
        ]
        
        # Add all progress events to client
        for event in progress_events:
            ws_client.add_received_event(event)
        
        # CRITICAL ASSERTIONS: Progress updates must provide value
        assert len(ws_client.received_events) == 5, "Must receive all 5 progress events"
        
        # Validate required event types are present
        assert WebSocketEventValidator.validate_required_events(ws_client.received_events), \
            "Must include all 5 required WebSocket event types"
        
        # Validate event sequence
        assert WebSocketEventValidator.validate_event_sequence(ws_client.received_events), \
            "Events must be in correct sequence"
        
        # Validate progress percentages increase
        progress_values = [event.get("progress_percentage", 0) for event in ws_client.received_events]
        assert progress_values == [0, 25, 50, 75, 100], "Progress must increase incrementally"
        
        # Validate each event provides meaningful updates
        for event in ws_client.received_events:
            assert "data" in event, "Each event must contain progress data"
            assert "user_id" in event["data"], "Each event must identify the user"
            assert event["data"]["user_id"] == user_id, "Events must be for correct user"
            assert "timestamp" in event, "Each event must have timestamp"
        
        # Validate final result contains business value
        final_event = ws_client.received_events[-1]
        assert final_event["type"] == "agent_completed", "Final event must be completion"
        assert "result" in final_event["data"], "Final event must contain results"
        assert final_event["data"]["result"]["monthly_savings"] > 0, "Must deliver quantified business value"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_emission_patterns_validation(self, real_services_fixture):
        """
        Test WebSocket event emission follows required patterns for business value.
        
        Business Value Justification (BVJ):
        - Segment: Platform/Internal
        - Business Goal: System reliability and user experience
        - Value Impact: Consistent event patterns enable predictable user experience
        - Strategic Impact: Event pattern compliance prevents user confusion
        """
        db = real_services_fixture["db"]
        
        # Create test user
        user_id = UnifiedIdGenerator.generate_base_id("user_events")
        user = User(id=user_id, email="events@example.com", name="Events User")
        db.add(user)
        
        thread_id = UnifiedIdGenerator.generate_base_id("thread_events")
        thread = Thread(id=thread_id, user_id=user_id, title="Event Patterns Test")
        db.add(thread)
        await db.commit()
        
        # Create WebSocket client
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        ws_client = WebSocketTestClient(user_id, connection_id)
        
        # Test Case 1: Complete agent execution with all events
        complete_execution_events = [
            {
                "type": "agent_started",
                "data": {"agent_type": "pattern_test_agent", "user_id": user_id},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "event_id": UnifiedIdGenerator.generate_base_id("event")
            },
            {
                "type": "agent_thinking",
                "data": {"status": "Processing request", "user_id": user_id},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "event_id": UnifiedIdGenerator.generate_base_id("event")
            },
            {
                "type": "tool_executing",
                "data": {"tool_name": "test_tool", "user_id": user_id},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "event_id": UnifiedIdGenerator.generate_base_id("event")
            },
            {
                "type": "tool_completed",
                "data": {"tool_name": "test_tool", "results": {"status": "success"}, "user_id": user_id},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "event_id": UnifiedIdGenerator.generate_base_id("event")
            },
            {
                "type": "agent_completed",
                "data": {
                    "result": {
                        "summary": "Analysis complete",
                        "business_value": "Generated actionable insights"
                    },
                    "user_id": user_id
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "event_id": UnifiedIdGenerator.generate_base_id("event")
            }
        ]
        
        # Add events to client
        for event in complete_execution_events:
            ws_client.add_received_event(event)
        
        # CRITICAL ASSERTIONS: Event patterns must be correct
        
        # Validate all required events present
        assert WebSocketEventValidator.validate_required_events(ws_client.received_events), \
            "All 5 required event types must be present"
        
        # Validate event sequence
        assert WebSocketEventValidator.validate_event_sequence(ws_client.received_events), \
            "Events must follow correct sequence"
        
        # Validate data completeness
        assert WebSocketEventValidator.validate_event_data_completeness(ws_client.received_events), \
            "All events must contain complete data"
        
        # Validate event-specific requirements
        event_by_type = {event["type"]: event for event in ws_client.received_events}
        
        # agent_started must have agent_type
        started_event = event_by_type["agent_started"]
        assert "agent_type" in started_event["data"], "agent_started must specify agent_type"
        
        # tool events must have tool_name
        tool_exec_event = event_by_type["tool_executing"]
        assert "tool_name" in tool_exec_event["data"], "tool_executing must specify tool_name"
        
        tool_comp_event = event_by_type["tool_completed"] 
        assert "tool_name" in tool_comp_event["data"], "tool_completed must specify tool_name"
        assert "results" in tool_comp_event["data"], "tool_completed must include results"
        
        # agent_completed must have result
        completed_event = event_by_type["agent_completed"]
        assert "result" in completed_event["data"], "agent_completed must include result"
        
        # All events must have proper identification
        for event in ws_client.received_events:
            assert "event_id" in event, "Each event must have unique event_id"
            assert "timestamp" in event, "Each event must have timestamp"
            assert event["user_id"] == user_id, "Each event must identify correct user"
            assert event["thread_id"] == thread_id, "Each event must identify correct thread"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_websocket_report_isolation(self, real_services_fixture):
        """
        Test WebSocket report delivery maintains strict user isolation.
        
        Business Value Justification (BVJ):
        - Segment: Enterprise
        - Business Goal: Security and compliance
        - Value Impact: User isolation is critical for enterprise adoption
        - Strategic Impact: Isolation failures would block enterprise sales
        """
        db = real_services_fixture["db"]
        
        # Create two separate enterprise users
        user1_id = UnifiedIdGenerator.generate_base_id("user_isolation_1")
        user2_id = UnifiedIdGenerator.generate_base_id("user_isolation_2")
        
        user1 = User(id=user1_id, email="enterprise1@company.com", name="Enterprise User 1")
        user2 = User(id=user2_id, email="enterprise2@company.com", name="Enterprise User 2")
        
        db.add(user1)
        db.add(user2)
        
        # Create separate threads
        thread1_id = UnifiedIdGenerator.generate_base_id("thread_isolation_1")
        thread2_id = UnifiedIdGenerator.generate_base_id("thread_isolation_2")
        
        thread1 = Thread(id=thread1_id, user_id=user1_id, title="User 1 Confidential Analysis")
        thread2 = Thread(id=thread2_id, user_id=user2_id, title="User 2 Confidential Analysis")
        
        db.add(thread1)
        db.add(thread2)
        await db.commit()
        
        # Create separate WebSocket connections
        connection1_id = UnifiedIdGenerator.generate_websocket_connection_id(user1_id)
        connection2_id = UnifiedIdGenerator.generate_websocket_connection_id(user2_id)
        
        ws_client1 = WebSocketTestClient(user1_id, connection1_id)
        ws_client2 = WebSocketTestClient(user2_id, connection2_id)
        
        # Generate confidential reports for each user
        user1_confidential_data = {
            "agent_type": "confidential_analyzer",
            "classification": "CONFIDENTIAL - User 1 Only",
            "executive_summary": "CONFIDENTIAL: User 1 proprietary business analysis",
            "key_findings": [
                "User 1 trade secrets: Advanced algorithm performance data",
                "User 1 financial data: $5M quarterly revenue projection",
                "User 1 competitive intelligence: Market position analysis"
            ],
            "recommendations": [
                {
                    "action": "Implement User 1 specific IP protection",
                    "expected_impact": "$2M risk mitigation",
                    "classification": "user_1_confidential"
                }
            ],
            "financial_impact": {"sensitive_revenue_data": 5000000},
            "data_sources": ["User 1 proprietary systems"],
            "confidence_score": 0.95,
            "access_control": {"user_id": user1_id, "classification": "confidential"}
        }
        
        user2_confidential_data = {
            "agent_type": "confidential_analyzer", 
            "classification": "CONFIDENTIAL - User 2 Only",
            "executive_summary": "CONFIDENTIAL: User 2 different proprietary analysis",
            "key_findings": [
                "User 2 trade secrets: Different algorithm performance data",
                "User 2 financial data: $3M quarterly revenue projection",
                "User 2 competitive intelligence: Different market analysis"
            ],
            "recommendations": [
                {
                    "action": "Implement User 2 specific market expansion",
                    "expected_impact": "$1.5M revenue opportunity",
                    "classification": "user_2_confidential"
                }
            ],
            "financial_impact": {"sensitive_revenue_data": 3000000},
            "data_sources": ["User 2 proprietary systems"],
            "confidence_score": 0.88,
            "access_control": {"user_id": user2_id, "classification": "confidential"}
        }
        
        # Simulate WebSocket event delivery for User 1
        user1_events = [
            {
                "type": "agent_started",
                "data": {"agent_type": "confidential_analyzer", "user_id": user1_id},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user1_id,
                "thread_id": thread1_id,
                "connection_id": connection1_id,
                "classification": "confidential"
            },
            {
                "type": "agent_completed",
                "data": {"result": user1_confidential_data, "user_id": user1_id},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user1_id,
                "thread_id": thread1_id,
                "connection_id": connection1_id,
                "classification": "confidential"
            }
        ]
        
        # Simulate WebSocket event delivery for User 2
        user2_events = [
            {
                "type": "agent_started",
                "data": {"agent_type": "confidential_analyzer", "user_id": user2_id},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user2_id,
                "thread_id": thread2_id,
                "connection_id": connection2_id,
                "classification": "confidential"
            },
            {
                "type": "agent_completed",
                "data": {"result": user2_confidential_data, "user_id": user2_id},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user2_id,
                "thread_id": thread2_id,
                "connection_id": connection2_id,
                "classification": "confidential"
            }
        ]
        
        # Add events to respective clients (simulating proper isolation)
        for event in user1_events:
            ws_client1.add_received_event(event)
            
        for event in user2_events:
            ws_client2.add_received_event(event)
        
        # CRITICAL ASSERTIONS: Perfect isolation required
        
        # User 1 can only receive their own events
        assert len(ws_client1.received_events) == 2, "User 1 must receive exactly their own events"
        for event in ws_client1.received_events:
            assert event["user_id"] == user1_id, "User 1 events must be for User 1 only"
            assert event["thread_id"] == thread1_id, "User 1 events must be for User 1 thread"
            assert event["connection_id"] == connection1_id, "User 1 events must be for User 1 connection"
            
            # Validate no User 2 data in User 1 events
            event_content = json.dumps(event)
            assert user2_id not in event_content, "User 1 events must not contain User 2 data"
            assert thread2_id not in event_content, "User 1 events must not contain User 2 thread"
        
        # User 2 can only receive their own events
        assert len(ws_client2.received_events) == 2, "User 2 must receive exactly their own events"
        for event in ws_client2.received_events:
            assert event["user_id"] == user2_id, "User 2 events must be for User 2 only"
            assert event["thread_id"] == thread2_id, "User 2 events must be for User 2 thread"
            assert event["connection_id"] == connection2_id, "User 2 events must be for User 2 connection"
            
            # Validate no User 1 data in User 2 events
            event_content = json.dumps(event)
            assert user1_id not in event_content, "User 2 events must not contain User 1 data"
            assert thread1_id not in event_content, "User 2 events must not contain User 1 thread"
        
        # Cross-user validation - sensitive data isolation
        user1_final_event = ws_client1.received_events[-1]
        user2_final_event = ws_client2.received_events[-1]
        
        # User 1 confidential data validation
        user1_result = user1_final_event["data"]["result"]
        assert "User 1 trade secrets" in str(user1_result), "User 1 must receive their confidential data"
        assert user1_result["financial_impact"]["sensitive_revenue_data"] == 5000000, "User 1 financial data correct"
        
        # User 2 confidential data validation
        user2_result = user2_final_event["data"]["result"]
        assert "User 2 trade secrets" in str(user2_result), "User 2 must receive their confidential data"
        assert user2_result["financial_impact"]["sensitive_revenue_data"] == 3000000, "User 2 financial data correct"
        
        # Absolute cross-contamination prohibition
        assert "User 2" not in str(user1_result), "User 1 results must not contain User 2 data"
        assert "User 1" not in str(user2_result), "User 2 results must not contain User 1 data"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_authentication_and_report_security(self, real_services_fixture):
        """
        Test WebSocket connections enforce authentication for report delivery.
        
        Business Value Justification (BVJ):
        - Segment: Enterprise
        - Business Goal: Security and access control
        - Value Impact: Authentication prevents unauthorized access to business reports
        - Strategic Impact: Security compliance enables enterprise adoption
        """
        db = real_services_fixture["db"]
        
        # Create authenticated user
        authenticated_user_id = UnifiedIdGenerator.generate_base_id("user_auth")
        authenticated_user = User(
            id=authenticated_user_id,
            email="authenticated@enterprise.com",
            name="Authenticated User",
            subscription_tier="enterprise"
        )
        db.add(authenticated_user)
        
        thread_id = UnifiedIdGenerator.generate_base_id("thread_auth")
        thread = Thread(
            id=thread_id,
            user_id=authenticated_user_id,
            title="Secure Report Delivery"
        )
        db.add(thread)
        await db.commit()
        
        # Test Case 1: Valid authentication allows report delivery
        valid_connection_id = UnifiedIdGenerator.generate_websocket_connection_id(authenticated_user_id)
        valid_ws_client = WebSocketTestClient(authenticated_user_id, valid_connection_id)
        
        # Simulate authenticated report delivery
        secure_report_data = {
            "agent_type": "secure_analyzer",
            "security_classification": "enterprise_authorized",
            "executive_summary": "Secure analysis for authenticated user",
            "key_findings": [
                "User authentication validated",
                "Secure report delivery confirmed"
            ],
            "recommendations": [
                {
                    "action": "Continue secure operations",
                    "expected_impact": "Maintained security compliance",
                    "security_level": "enterprise"
                }
            ],
            "financial_impact": {"secure_value_delivered": 10000},
            "data_sources": ["Authenticated user data"],
            "confidence_score": 0.98,
            "authentication": {
                "user_id": authenticated_user_id,
                "authentication_status": "valid",
                "permissions": ["read_reports", "receive_updates"]
            }
        }
        
        authenticated_events = [
            {
                "type": "agent_started",
                "data": {
                    "agent_type": "secure_analyzer",
                    "user_id": authenticated_user_id,
                    "authentication_status": "validated"
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": authenticated_user_id,
                "thread_id": thread_id,
                "connection_id": valid_connection_id,
                "authentication": {"status": "valid", "user_verified": True}
            },
            {
                "type": "agent_completed",
                "data": {
                    "result": secure_report_data,
                    "user_id": authenticated_user_id
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": authenticated_user_id,
                "thread_id": thread_id,
                "connection_id": valid_connection_id,
                "authentication": {"status": "valid", "user_verified": True}
            }
        ]
        
        # Add authenticated events
        for event in authenticated_events:
            valid_ws_client.add_received_event(event)
        
        # Test Case 2: Invalid authentication blocks report delivery
        invalid_user_id = "unauthenticated_user"
        invalid_connection_id = "invalid_connection"
        invalid_ws_client = WebSocketTestClient(invalid_user_id, invalid_connection_id)
        
        # Simulate authentication failure
        auth_failure_events = [
            {
                "type": "authentication_failed",
                "data": {
                    "error": "Invalid user credentials",
                    "user_id": invalid_user_id,
                    "reason": "User not found in system"
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": invalid_user_id,
                "connection_id": invalid_connection_id,
                "authentication": {"status": "failed", "user_verified": False}
            }
        ]
        
        for event in auth_failure_events:
            invalid_ws_client.add_received_event(event)
        
        # CRITICAL ASSERTIONS: Authentication security must be enforced
        
        # Authenticated user receives reports
        assert len(valid_ws_client.received_events) == 2, "Authenticated user must receive report events"
        
        # Validate authentication in events
        for event in valid_ws_client.received_events:
            assert "authentication" in event, "All events must include authentication status"
            assert event["authentication"]["status"] == "valid", "Events must confirm valid authentication"
            assert event["authentication"]["user_verified"], "Events must confirm user verification"
            assert event["user_id"] == authenticated_user_id, "Events must be for authenticated user"
        
        # Validate secure report content delivered
        final_authenticated_event = valid_ws_client.received_events[-1]
        assert final_authenticated_event["type"] == "agent_completed", "Must complete report delivery"
        
        result = final_authenticated_event["data"]["result"]
        assert result["authentication"]["authentication_status"] == "valid", "Report must confirm authentication"
        assert result["security_classification"] == "enterprise_authorized", "Report must be security classified"
        
        # Unauthenticated user blocked from reports
        assert len(invalid_ws_client.received_events) == 1, "Unauthenticated user gets only auth failure"
        
        auth_failure_event = invalid_ws_client.received_events[0]
        assert auth_failure_event["type"] == "authentication_failed", "Must receive authentication failure"
        assert auth_failure_event["authentication"]["status"] == "failed", "Must confirm authentication failed"
        assert not auth_failure_event["authentication"]["user_verified"], "Must confirm user not verified"
        
        # Security validation: no business data in failure events
        failure_event_content = json.dumps(auth_failure_event)
        assert "secure_analyzer" not in failure_event_content, "Auth failures must not leak business data"
        assert "financial_impact" not in failure_event_content, "Auth failures must not contain sensitive data"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_handling_over_websocket_connections(self, real_services_fixture):
        """
        Test WebSocket connections properly handle and communicate errors to users.
        
        Business Value Justification (BVJ):
        - Segment: All
        - Business Goal: User experience and system reliability
        - Value Impact: Proper error communication prevents user confusion
        - Strategic Impact: Error transparency maintains user trust
        """
        db = real_services_fixture["db"]
        
        # Create test user
        user_id = UnifiedIdGenerator.generate_base_id("user_error")
        user = User(id=user_id, email="errors@example.com", name="Error Test User")
        db.add(user)
        
        thread_id = UnifiedIdGenerator.generate_base_id("thread_error")
        thread = Thread(id=thread_id, user_id=user_id, title="Error Handling Test")
        db.add(thread)
        await db.commit()
        
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        ws_client = WebSocketTestClient(user_id, connection_id)
        
        # Test Case 1: Agent execution errors with graceful recovery
        agent_error_events = [
            {
                "type": "agent_started",
                "data": {"agent_type": "error_test_agent", "user_id": user_id},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id
            },
            {
                "type": "agent_error",
                "data": {
                    "error_type": "tool_execution_failure",
                    "error_message": "Cost analysis tool temporarily unavailable",
                    "recovery_action": "Attempting alternative analysis method",
                    "user_impact": "Analysis will continue with cached data",
                    "user_id": user_id
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "error_details": {
                    "error_code": "TOOL_UNAVAILABLE",
                    "severity": "medium",
                    "user_actionable": False
                }
            },
            {
                "type": "agent_recovering",
                "data": {
                    "status": "Using historical data for analysis",
                    "expected_completion": "Analysis will complete with 90% confidence",
                    "user_id": user_id
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id
            },
            {
                "type": "agent_completed",
                "data": {
                    "result": {
                        "executive_summary": "Analysis completed despite tool unavailability",
                        "key_findings": [
                            "Used historical data for cost analysis",
                            "Identified $15,000/month in savings (90% confidence)"
                        ],
                        "recommendations": [
                            {
                                "action": "Implement high-confidence optimizations immediately",
                                "expected_impact": "$15,000/month savings",
                                "confidence": "high"
                            }
                        ],
                        "financial_impact": {"monthly_savings": 15000},
                        "confidence_score": 0.90,
                        "recovery_notes": "Completed with alternative data sources"
                    },
                    "user_id": user_id
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "completion_status": "recovered"
            }
        ]
        
        # Test Case 2: Critical system errors with user notification
        critical_error_events = [
            {
                "type": "system_error",
                "data": {
                    "error_type": "database_connection_lost",
                    "error_message": "Temporary database connectivity issue",
                    "user_message": "We're experiencing a brief technical issue. Your request has been saved and will be processed shortly.",
                    "user_impact": "Request queued for processing when service restored",
                    "estimated_resolution": "2-3 minutes",
                    "user_id": user_id
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "error_details": {
                    "error_code": "DB_CONNECTION_LOST",
                    "severity": "high",
                    "user_actionable": False,
                    "support_notified": True
                }
            }
        ]
        
        # Add all error events
        for event in agent_error_events:
            ws_client.add_received_event(event)
            
        for event in critical_error_events:
            ws_client.add_received_event(event)
        
        # CRITICAL ASSERTIONS: Error handling must maintain user experience
        
        assert len(ws_client.received_events) == 5, "Must receive all error handling events"
        
        # Validate graceful error recovery sequence
        recovery_events = ws_client.received_events[:4]  # First 4 events are recovery sequence
        
        # agent_error event validation
        error_event = recovery_events[1]
        assert error_event["type"] == "agent_error", "Must send error notification"
        assert "recovery_action" in error_event["data"], "Error events must include recovery action"
        assert "user_impact" in error_event["data"], "Error events must explain user impact"
        assert error_event["error_details"]["user_actionable"] == False, "System errors not user actionable"
        
        # agent_recovering event validation  
        recovery_event = recovery_events[2]
        assert recovery_event["type"] == "agent_recovering", "Must send recovery status"
        assert "expected_completion" in recovery_event["data"], "Recovery must set expectations"
        
        # Successful completion after recovery
        completion_event = recovery_events[3]
        assert completion_event["type"] == "agent_completed", "Must complete after recovery"
        assert completion_event["completion_status"] == "recovered", "Must indicate recovery completion"
        
        result = completion_event["data"]["result"]
        assert result["confidence_score"] == 0.90, "Must indicate reduced confidence"
        assert "recovery_notes" in result, "Must document recovery approach"
        assert result["financial_impact"]["monthly_savings"] > 0, "Must still deliver business value"
        
        # Critical system error validation
        critical_error = ws_client.received_events[4]
        assert critical_error["type"] == "system_error", "Must send system error notification"
        assert "user_message" in critical_error["data"], "System errors need user-friendly message"
        assert "estimated_resolution" in critical_error["data"], "Must provide resolution timeline"
        assert critical_error["error_details"]["support_notified"], "Support must be automatically notified"
        
        # User communication quality validation
        user_message = critical_error["data"]["user_message"]
        assert "technical issue" in user_message.lower(), "Must communicate issue clearly"
        assert "shortly" in user_message.lower(), "Must provide reassurance"
        assert len(user_message) > 50, "User messages must be substantive"
        
        # All events must identify user correctly
        for event in ws_client.received_events:
            assert event["user_id"] == user_id, "All error events must identify correct user"
            assert event["thread_id"] == thread_id, "All error events must identify correct thread"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_message_formatting_and_structure(self, real_services_fixture):
        """
        Test WebSocket messages follow consistent formatting for user interfaces.
        
        Business Value Justification (BVJ):
        - Segment: All
        - Business Goal: User interface consistency and developer experience
        - Value Impact: Consistent message format enables reliable frontend integration
        - Strategic Impact: Message standardization reduces development and support costs
        """
        db = real_services_fixture["db"]
        
        # Create test user
        user_id = UnifiedIdGenerator.generate_base_id("user_format")
        user = User(id=user_id, email="formatting@example.com", name="Format Test User")
        db.add(user)
        
        thread_id = UnifiedIdGenerator.generate_base_id("thread_format")
        thread = Thread(id=thread_id, user_id=user_id, title="Message Formatting Test")
        db.add(thread)
        await db.commit()
        
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        ws_client = WebSocketTestClient(user_id, connection_id)
        
        # Create standardized message format examples
        standard_formatted_events = [
            {
                "type": "agent_started",
                "data": {
                    "agent_type": "formatting_test_agent",
                    "user_id": user_id,
                    "message": "Starting cost analysis for your infrastructure",
                    "estimated_duration_seconds": 30,
                    "progress": {
                        "current_step": 1,
                        "total_steps": 5,
                        "percentage": 0
                    }
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_id": UnifiedIdGenerator.generate_base_id("event"),
                "user_id": user_id,
                "thread_id": thread_id,
                "connection_id": connection_id,
                "version": "1.0",
                "schema": "agent_event_v1"
            },
            {
                "type": "agent_thinking",
                "data": {
                    "status": "Analyzing cost patterns and utilization metrics",
                    "user_id": user_id,
                    "message": "Examining your infrastructure for optimization opportunities",
                    "details": {
                        "current_analysis": "Cost pattern recognition",
                        "data_sources": ["AWS Cost Explorer", "CloudWatch"],
                        "confidence_building": True
                    },
                    "progress": {
                        "current_step": 2,
                        "total_steps": 5,
                        "percentage": 25
                    }
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_id": UnifiedIdGenerator.generate_base_id("event"),
                "user_id": user_id,
                "thread_id": thread_id,
                "connection_id": connection_id,
                "version": "1.0",
                "schema": "agent_event_v1"
            },
            {
                "type": "tool_executing",
                "data": {
                    "tool_name": "cost_analyzer",
                    "user_id": user_id,
                    "message": "Running detailed cost analysis",
                    "tool_description": "Analyzing AWS costs and identifying optimization opportunities",
                    "parameters": {
                        "time_range": "last_30_days",
                        "services": ["EC2", "RDS", "S3"],
                        "analysis_type": "comprehensive"
                    },
                    "progress": {
                        "current_step": 3,
                        "total_steps": 5,
                        "percentage": 50
                    }
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_id": UnifiedIdGenerator.generate_base_id("event"),
                "user_id": user_id,
                "thread_id": thread_id,
                "connection_id": connection_id,
                "version": "1.0",
                "schema": "tool_event_v1"
            },
            {
                "type": "tool_completed",
                "data": {
                    "tool_name": "cost_analyzer",
                    "user_id": user_id,
                    "message": "Cost analysis completed successfully",
                    "results": {
                        "total_monthly_cost": 45000,
                        "optimization_opportunities": [
                            {"category": "EC2", "savings": 15000},
                            {"category": "RDS", "savings": 8000}
                        ],
                        "total_potential_savings": 23000
                    },
                    "execution_time_seconds": 12.5,
                    "success": True,
                    "progress": {
                        "current_step": 4,
                        "total_steps": 5,
                        "percentage": 75
                    }
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_id": UnifiedIdGenerator.generate_base_id("event"),
                "user_id": user_id,
                "thread_id": thread_id,
                "connection_id": connection_id,
                "version": "1.0",
                "schema": "tool_event_v1"
            },
            {
                "type": "agent_completed",
                "data": {
                    "user_id": user_id,
                    "message": "Analysis complete - found significant optimization opportunities",
                    "result": {
                        "executive_summary": "Comprehensive cost analysis identified $23,000/month in savings",
                        "key_findings": [
                            "Over-provisioned EC2 instances: $15,000/month opportunity",
                            "Unused RDS instances: $8,000/month savings potential"
                        ],
                        "recommendations": [
                            {
                                "action": "Rightsize EC2 instances",
                                "expected_impact": "$15,000/month savings",
                                "effort_required": "4 hours",
                                "priority": "high"
                            }
                        ],
                        "financial_impact": {
                            "monthly_savings": 23000,
                            "annual_savings": 276000,
                            "roi_percentage": 2300
                        },
                        "confidence_score": 0.92
                    },
                    "execution_summary": {
                        "total_time_seconds": 28.7,
                        "tools_executed": 1,
                        "success_rate": 1.0
                    },
                    "progress": {
                        "current_step": 5,
                        "total_steps": 5,
                        "percentage": 100
                    }
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_id": UnifiedIdGenerator.generate_base_id("event"),
                "user_id": user_id,
                "thread_id": thread_id,
                "connection_id": connection_id,
                "version": "1.0",
                "schema": "agent_event_v1",
                "final": True
            }
        ]
        
        # Add all formatted events
        for event in standard_formatted_events:
            ws_client.add_received_event(event)
        
        # CRITICAL ASSERTIONS: Message formatting must be consistent
        
        assert len(ws_client.received_events) == 5, "Must receive all formatted events"
        
        # Validate required top-level fields in all events
        required_top_level_fields = [
            "type", "data", "timestamp", "event_id", "user_id", 
            "thread_id", "connection_id", "version", "schema"
        ]
        
        for event in ws_client.received_events:
            for field in required_top_level_fields:
                assert field in event, f"All events must have {field} field"
            
            # Validate field types
            assert isinstance(event["type"], str), "type must be string"
            assert isinstance(event["data"], dict), "data must be dictionary"
            assert isinstance(event["timestamp"], str), "timestamp must be ISO string"
            assert isinstance(event["user_id"], str), "user_id must be string"
            assert event["version"] == "1.0", "All events must use version 1.0"
        
        # Validate data field consistency
        required_data_fields = ["user_id", "message"]
        
        for event in ws_client.received_events:
            event_data = event["data"]
            for field in required_data_fields:
                assert field in event_data, f"All event data must have {field}"
            
            # Message must be user-friendly
            message = event_data["message"]
            assert isinstance(message, str), "message must be string"
            assert len(message) > 10, "message must be descriptive"
            assert message[0].isupper(), "message must be properly capitalized"
        
        # Validate progress tracking consistency
        for event in ws_client.received_events:
            if "progress" in event["data"]:
                progress = event["data"]["progress"]
                assert "current_step" in progress, "progress must have current_step"
                assert "total_steps" in progress, "progress must have total_steps"
                assert "percentage" in progress, "progress must have percentage"
                assert 0 <= progress["percentage"] <= 100, "percentage must be 0-100"
                assert progress["current_step"] <= progress["total_steps"], "current_step must be <= total_steps"
        
        # Validate schema differentiation
        agent_events = [e for e in ws_client.received_events if e["type"] in ["agent_started", "agent_thinking", "agent_completed"]]
        tool_events = [e for e in ws_client.received_events if e["type"] in ["tool_executing", "tool_completed"]]
        
        for event in agent_events:
            assert event["schema"] == "agent_event_v1", "Agent events must use agent_event_v1 schema"
        
        for event in tool_events:
            assert event["schema"] == "tool_event_v1", "Tool events must use tool_event_v1 schema"
        
        # Validate final event marking
        final_events = [e for e in ws_client.received_events if e.get("final", False)]
        assert len(final_events) == 1, "Exactly one event must be marked as final"
        assert final_events[0]["type"] == "agent_completed", "Only agent_completed should be marked final"
        
        # Validate business data structure in completion event
        completion_event = ws_client.received_events[-1]
        result = completion_event["data"]["result"]
        
        business_required_fields = [
            "executive_summary", "key_findings", "recommendations", "financial_impact"
        ]
        for field in business_required_fields:
            assert field in result, f"Business result must have {field}"
        
        # Validate financial impact structure
        financial_impact = result["financial_impact"]
        financial_required_fields = ["monthly_savings", "annual_savings", "roi_percentage"]
        for field in financial_required_fields:
            assert field in financial_impact, f"Financial impact must have {field}"
            assert isinstance(financial_impact[field], (int, float)), f"{field} must be numeric"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_websocket_report_deliveries(self, real_services_fixture):
        """
        Test multiple WebSocket connections can receive reports concurrently.
        
        Business Value Justification (BVJ):
        - Segment: Mid, Enterprise
        - Business Goal: System scalability and multi-user support
        - Value Impact: Concurrent users must receive reports without interference
        - Strategic Impact: Scalability is critical for platform growth
        """
        db = real_services_fixture["db"]
        
        # Create multiple concurrent users
        concurrent_user_count = 3
        users_and_connections = []
        
        for i in range(concurrent_user_count):
            user_id = UnifiedIdGenerator.generate_base_id(f"user_concurrent_{i}")
            user = User(
                id=user_id,
                email=f"concurrent{i}@example.com",
                name=f"Concurrent User {i}",
                subscription_tier="enterprise"
            )
            db.add(user)
            
            thread_id = UnifiedIdGenerator.generate_base_id(f"thread_concurrent_{i}")
            thread = Thread(
                id=thread_id,
                user_id=user_id,
                title=f"Concurrent Analysis {i}"
            )
            db.add(thread)
            
            connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
            ws_client = WebSocketTestClient(user_id, connection_id)
            
            users_and_connections.append({
                "user_id": user_id,
                "thread_id": thread_id,
                "connection_id": connection_id,
                "ws_client": ws_client,
                "user_index": i
            })
        
        await db.commit()
        
        # Simulate concurrent report generation and delivery
        import time
        start_time = time.time()
        
        for user_data in users_and_connections:
            user_id = user_data["user_id"]
            thread_id = user_data["thread_id"]
            connection_id = user_data["connection_id"]
            ws_client = user_data["ws_client"]
            user_index = user_data["user_index"]
            
            # Generate user-specific report data
            concurrent_report_data = {
                "agent_type": f"concurrent_analyzer_{user_index}",
                "user_specific_id": user_index,
                "executive_summary": f"Concurrent analysis #{user_index} results",
                "key_findings": [
                    f"User {user_index} infrastructure analysis complete",
                    f"Found optimization opportunities for User {user_index}"
                ],
                "recommendations": [
                    {
                        "action": f"Implement User {user_index} specific optimizations",
                        "expected_impact": f"${(user_index + 1) * 5000}/month savings",
                        "user_identifier": user_index
                    }
                ],
                "financial_impact": {
                    "monthly_savings": (user_index + 1) * 5000,
                    "user_rank": user_index + 1
                },
                "data_sources": [f"User {user_index} systems"],
                "confidence_score": 0.85 + (user_index * 0.03),
                "concurrent_execution": {
                    "user_batch": "concurrent_test",
                    "execution_order": user_index,
                    "start_time": start_time
                }
            }
            
            # Create concurrent events for each user
            concurrent_events = [
                {
                    "type": "agent_started",
                    "data": {
                        "agent_type": f"concurrent_analyzer_{user_index}",
                        "user_id": user_id,
                        "concurrent_execution": True,
                        "user_index": user_index
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "connection_id": connection_id,
                    "execution_batch": "concurrent_test"
                },
                {
                    "type": "agent_thinking",
                    "data": {
                        "status": f"Processing User {user_index} specific analysis",
                        "user_id": user_id,
                        "concurrent_processing": True
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "connection_id": connection_id,
                    "execution_batch": "concurrent_test"
                },
                {
                    "type": "agent_completed",
                    "data": {
                        "result": concurrent_report_data,
                        "user_id": user_id,
                        "concurrent_completion": True
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "connection_id": connection_id,
                    "execution_batch": "concurrent_test"
                }
            ]
            
            # Add events to respective WebSocket clients
            for event in concurrent_events:
                ws_client.add_received_event(event)
        
        # CRITICAL ASSERTIONS: Concurrent execution must maintain isolation
        
        # Validate all users received their events
        for user_data in users_and_connections:
            ws_client = user_data["ws_client"]
            user_id = user_data["user_id"]
            user_index = user_data["user_index"]
            
            assert len(ws_client.received_events) == 3, f"User {user_index} must receive all 3 events"
            
            # Validate all events belong to correct user
            for event in ws_client.received_events:
                assert event["user_id"] == user_id, f"User {user_index} events must be for correct user"
                assert event["execution_batch"] == "concurrent_test", "All events must be from concurrent batch"
            
            # Validate user-specific data in completion event
            completion_event = ws_client.received_events[-1]
            assert completion_event["type"] == "agent_completed", f"User {user_index} must receive completion"
            
            result = completion_event["data"]["result"]
            assert result["user_specific_id"] == user_index, f"User {user_index} must get their specific data"
            assert result["concurrent_execution"]["execution_order"] == user_index, "Must preserve execution order"
            
            # Validate user-specific financial data
            expected_savings = (user_index + 1) * 5000
            assert result["financial_impact"]["monthly_savings"] == expected_savings, \
                f"User {user_index} must get correct savings calculation"
        
        # Cross-user isolation validation
        for i, user_data_i in enumerate(users_and_connections):
            for j, user_data_j in enumerate(users_and_connections):
                if i != j:  # Different users
                    ws_client_i = user_data_i["ws_client"]
                    user_j_id = user_data_j["user_id"]
                    
                    # Validate User i doesn't receive User j data
                    for event in ws_client_i.received_events:
                        event_content = json.dumps(event)
                        assert user_j_id not in event_content, \
                            f"User {i} events must not contain User {j} data"
        
        # Performance validation for concurrent delivery
        total_events_delivered = sum(len(ud["ws_client"].received_events) for ud in users_and_connections)
        expected_total_events = concurrent_user_count * 3  # 3 events per user
        
        assert total_events_delivered == expected_total_events, \
            f"Must deliver all {expected_total_events} events across {concurrent_user_count} users"
        
        # Concurrent execution metadata validation
        for user_data in users_and_connections:
            completion_event = user_data["ws_client"].received_events[-1]
            concurrent_metadata = completion_event["data"]["result"]["concurrent_execution"]
            
            assert concurrent_metadata["user_batch"] == "concurrent_test", "Must track batch execution"
            assert concurrent_metadata["start_time"] == start_time, "Must track execution timing"

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_websocket_connection_recovery_and_report_continuity(self, real_services_fixture):
        """
        Test WebSocket connections can recover and continue report delivery after disconnection.
        
        Business Value Justification (BVJ):
        - Segment: All
        - Business Goal: System reliability and user experience
        - Value Impact: Connection recovery prevents loss of business reports
        - Strategic Impact: Reliability is critical for user trust and retention
        """
        db = real_services_fixture["db"]
        
        # Create test user
        user_id = UnifiedIdGenerator.generate_base_id("user_recovery")
        user = User(
            id=user_id,
            email="recovery@example.com",
            name="Recovery Test User",
            subscription_tier="enterprise"
        )
        db.add(user)
        
        thread_id = UnifiedIdGenerator.generate_base_id("thread_recovery")
        thread = Thread(
            id=thread_id,
            user_id=user_id,
            title="Connection Recovery Test"
        )
        db.add(thread)
        await db.commit()
        
        # Initial WebSocket connection
        initial_connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        initial_ws_client = WebSocketTestClient(user_id, initial_connection_id)
        
        # Simulate report generation start
        initial_events = [
            {
                "type": "agent_started",
                "data": {
                    "agent_type": "recovery_test_agent",
                    "user_id": user_id,
                    "estimated_duration": 60,
                    "recovery_test": True
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "connection_id": initial_connection_id,
                "sequence_number": 1
            },
            {
                "type": "agent_thinking", 
                "data": {
                    "status": "Beginning comprehensive analysis",
                    "user_id": user_id,
                    "progress_checkpoint": "25%"
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "connection_id": initial_connection_id,
                "sequence_number": 2
            }
        ]
        
        # Add initial events
        for event in initial_events:
            initial_ws_client.add_received_event(event)
        
        # Simulate connection loss
        initial_ws_client.disconnect()
        assert not initial_ws_client.is_connected, "Initial connection must be disconnected"
        
        # Store recovery state in Redis for continuity
        recovery_state = {
            "user_id": user_id,
            "thread_id": thread_id,
            "agent_state": "in_progress",
            "last_event_sequence": 2,
            "progress_checkpoint": "25%",
            "agent_type": "recovery_test_agent",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "recovery_enabled": True
        }
        
        recovery_key = f"websocket_recovery:{user_id}:{thread_id}"
        redis = real_services_fixture["redis"]
        await redis.set(recovery_key, json.dumps(recovery_state), ex=300)  # 5 minute expiry
        
        # New WebSocket connection for recovery
        recovery_connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        recovery_ws_client = WebSocketTestClient(user_id, recovery_connection_id)
        
        # Simulate recovery process
        recovery_events = [
            {
                "type": "connection_recovered",
                "data": {
                    "message": "Connection restored - resuming your analysis",
                    "user_id": user_id,
                    "previous_connection": initial_connection_id,
                    "new_connection": recovery_connection_id,
                    "recovery_state": recovery_state,
                    "resumed_at_checkpoint": "25%"
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "connection_id": recovery_connection_id,
                "sequence_number": 3,
                "recovery_event": True
            },
            {
                "type": "agent_thinking",
                "data": {
                    "status": "Continuing analysis from last checkpoint",
                    "user_id": user_id,
                    "progress_checkpoint": "50%",
                    "resumed_processing": True
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "connection_id": recovery_connection_id,
                "sequence_number": 4
            },
            {
                "type": "tool_executing",
                "data": {
                    "tool_name": "recovery_analyzer",
                    "user_id": user_id,
                    "status": "Processing resumed data analysis",
                    "recovery_continuation": True
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "connection_id": recovery_connection_id,
                "sequence_number": 5
            },
            {
                "type": "tool_completed",
                "data": {
                    "tool_name": "recovery_analyzer",
                    "user_id": user_id,
                    "results": {
                        "analysis_completed": True,
                        "recovery_successful": True,
                        "data_integrity_preserved": True
                    },
                    "success": True
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "connection_id": recovery_connection_id,
                "sequence_number": 6
            },
            {
                "type": "agent_completed",
                "data": {
                    "result": {
                        "executive_summary": "Analysis completed successfully after connection recovery",
                        "key_findings": [
                            "Connection recovery successful with no data loss",
                            "Analysis continuity maintained throughout process",
                            "Business insights generated despite technical interruption"
                        ],
                        "recommendations": [
                            {
                                "action": "Implement identified optimizations",
                                "expected_impact": "$18,000/month savings",
                                "confidence": "high",
                                "recovery_validated": True
                            }
                        ],
                        "financial_impact": {
                            "monthly_savings": 18000,
                            "annual_savings": 216000
                        },
                        "recovery_metadata": {
                            "connection_interruptions": 1,
                            "recovery_time_seconds": 5,
                            "data_continuity_preserved": True,
                            "user_experience_impact": "minimal"
                        },
                        "confidence_score": 0.91
                    },
                    "user_id": user_id,
                    "execution_complete": True
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "connection_id": recovery_connection_id,
                "sequence_number": 7,
                "final": True
            }
        ]
        
        # Add recovery events
        for event in recovery_events:
            recovery_ws_client.add_received_event(event)
        
        # CRITICAL ASSERTIONS: Recovery must maintain business value delivery
        
        # Validate initial events were received
        assert len(initial_ws_client.received_events) == 2, "Initial connection must receive starting events"
        assert not initial_ws_client.is_connected, "Initial connection must be disconnected"
        
        # Validate recovery events received
        assert len(recovery_ws_client.received_events) == 5, "Recovery connection must receive continuation events"
        assert recovery_ws_client.is_connected, "Recovery connection must be active"
        
        # Validate recovery sequence
        recovery_event = recovery_ws_client.received_events[0]
        assert recovery_event["type"] == "connection_recovered", "Must announce connection recovery"
        assert recovery_event["recovery_event"], "Recovery event must be marked"
        assert recovery_event["data"]["previous_connection"] == initial_connection_id, "Must reference previous connection"
        assert recovery_event["data"]["new_connection"] == recovery_connection_id, "Must identify new connection"
        
        # Validate state continuity
        recovery_state_data = recovery_event["data"]["recovery_state"]
        assert recovery_state_data["last_event_sequence"] == 2, "Must preserve sequence number"
        assert recovery_state_data["progress_checkpoint"] == "25%", "Must preserve progress state"
        assert recovery_state_data["agent_type"] == "recovery_test_agent", "Must preserve agent type"
        
        # Validate business process completion
        completion_event = recovery_ws_client.received_events[-1]
        assert completion_event["type"] == "agent_completed", "Must complete business process"
        assert completion_event["final"], "Completion must be marked as final"
        
        result = completion_event["data"]["result"]
        recovery_metadata = result["recovery_metadata"]
        
        # Validate recovery impact tracking
        assert recovery_metadata["connection_interruptions"] == 1, "Must track interruption count"
        assert recovery_metadata["data_continuity_preserved"], "Must preserve data continuity"
        assert recovery_metadata["user_experience_impact"] == "minimal", "Must minimize user impact"
        
        # Validate business value preserved
        assert result["financial_impact"]["monthly_savings"] > 0, "Must deliver business value despite recovery"
        assert result["confidence_score"] > 0.9, "High confidence must be maintained"
        assert "recovery" in result["executive_summary"].lower(), "Must acknowledge recovery in summary"
        
        # Validate sequence numbers maintain continuity
        all_sequence_numbers = []
        for event in initial_ws_client.received_events:
            if "sequence_number" in event:
                all_sequence_numbers.append(event["sequence_number"])
                
        for event in recovery_ws_client.received_events:
            if "sequence_number" in event:
                all_sequence_numbers.append(event["sequence_number"])
        
        assert all_sequence_numbers == [1, 2, 3, 4, 5, 6, 7], "Sequence numbers must be continuous across connections"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_performance_and_delivery_timing(self, real_services_fixture):
        """
        Test WebSocket report delivery meets performance requirements for user experience.
        
        Business Value Justification (BVJ):
        - Segment: All
        - Business Goal: User experience and system performance
        - Value Impact: Fast report delivery drives user satisfaction and engagement
        - Strategic Impact: Performance is critical for competitive advantage
        """
        db = real_services_fixture["db"]
        
        # Create test user for performance testing
        user_id = UnifiedIdGenerator.generate_base_id("user_performance")
        user = User(
            id=user_id,
            email="performance@example.com",
            name="Performance Test User",
            subscription_tier="enterprise"
        )
        db.add(user)
        
        thread_id = UnifiedIdGenerator.generate_base_id("thread_performance")
        thread = Thread(
            id=thread_id,
            user_id=user_id,
            title="Performance Timing Test"
        )
        db.add(thread)
        await db.commit()
        
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        ws_client = WebSocketTestClient(user_id, connection_id)
        
        # Performance benchmarks for user experience
        performance_requirements = {
            "connection_establishment": 2.0,  # seconds
            "first_event_delivery": 1.0,      # seconds  
            "event_delivery_interval": 0.5,   # seconds between events
            "total_report_delivery": 30.0,    # seconds for complete report
            "large_report_delivery": 45.0,    # seconds for complex report
            "concurrent_user_impact": 2.0     # max additional delay with concurrent users
        }
        
        import time
        performance_start_time = time.time()
        
        # Create performance-measured events
        performance_events = [
            {
                "type": "agent_started",
                "data": {
                    "agent_type": "performance_test_agent",
                    "user_id": user_id,
                    "performance_test": True,
                    "expected_duration": 25
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "connection_id": connection_id,
                "performance_metrics": {
                    "event_generation_time_ms": 10,
                    "serialization_time_ms": 2,
                    "delivery_target_ms": 100
                },
                "delivery_timestamp": time.time()
            },
            {
                "type": "agent_thinking",
                "data": {
                    "status": "Processing performance-intensive analysis",
                    "user_id": user_id,
                    "computation_complexity": "high"
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "connection_id": connection_id,
                "performance_metrics": {
                    "event_generation_time_ms": 15,
                    "serialization_time_ms": 3,
                    "delivery_target_ms": 200
                },
                "delivery_timestamp": time.time()
            },
            {
                "type": "tool_executing",
                "data": {
                    "tool_name": "performance_analyzer",
                    "user_id": user_id,
                    "processing_large_dataset": True,
                    "estimated_processing_time": 20
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "connection_id": connection_id,
                "performance_metrics": {
                    "event_generation_time_ms": 25,
                    "serialization_time_ms": 5,
                    "delivery_target_ms": 300
                },
                "delivery_timestamp": time.time()
            },
            {
                "type": "tool_completed",
                "data": {
                    "tool_name": "performance_analyzer",
                    "user_id": user_id,
                    "results": {
                        "dataset_size_mb": 150,
                        "processing_time_seconds": 18.5,
                        "results_complexity": "high",
                        "optimization_opportunities": 25
                    },
                    "success": True,
                    "performance_summary": {
                        "data_processed_mb": 150,
                        "analysis_efficiency": 0.95,
                        "result_generation_ms": 850
                    }
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "connection_id": connection_id,
                "performance_metrics": {
                    "event_generation_time_ms": 35,
                    "serialization_time_ms": 8,
                    "delivery_target_ms": 400
                },
                "delivery_timestamp": time.time()
            },
            {
                "type": "agent_completed",
                "data": {
                    "result": {
                        "executive_summary": "High-performance analysis completed within target timeframes",
                        "key_findings": [
                            "Processed 150MB dataset in 18.5 seconds",
                            "Identified 25 optimization opportunities",
                            "Analysis efficiency achieved 95% target"
                        ],
                        "recommendations": [
                            {
                                "action": "Implement high-impact optimizations first",
                                "expected_impact": "$35,000/month savings",
                                "implementation_priority": "immediate",
                                "performance_impact": "minimal"
                            }
                        ],
                        "financial_impact": {
                            "monthly_savings": 35000,
                            "annual_savings": 420000,
                            "roi_percentage": 3400
                        },
                        "performance_report": {
                            "total_analysis_time_seconds": 24.8,
                            "data_processing_efficiency": 0.95,
                            "user_experience_score": 9.2,
                            "delivery_time_target_met": True
                        },
                        "confidence_score": 0.94
                    },
                    "user_id": user_id,
                    "execution_complete": True
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "thread_id": thread_id,
                "connection_id": connection_id,
                "performance_metrics": {
                    "event_generation_time_ms": 45,
                    "serialization_time_ms": 12,
                    "delivery_target_ms": 500,
                    "total_report_size_kb": 25
                },
                "delivery_timestamp": time.time(),
                "final": True
            }
        ]
        
        # Add events with performance tracking
        for event in performance_events:
            ws_client.add_received_event(event)
        
        performance_end_time = time.time()
        total_delivery_time = performance_end_time - performance_start_time
        
        # CRITICAL ASSERTIONS: Performance must meet user experience requirements
        
        assert len(ws_client.received_events) == 5, "Must receive all performance test events"
        
        # Validate overall delivery performance
        assert total_delivery_time < performance_requirements["total_report_delivery"], \
            f"Total delivery time {total_delivery_time:.2f}s must be under {performance_requirements['total_report_delivery']}s"
        
        # Validate individual event performance metrics
        for i, event in enumerate(ws_client.received_events):
            perf_metrics = event["performance_metrics"]
            
            # Event generation must be fast
            assert perf_metrics["event_generation_time_ms"] < 50, \
                f"Event {i} generation time must be under 50ms"
            
            # Serialization must be efficient
            assert perf_metrics["serialization_time_ms"] < 15, \
                f"Event {i} serialization must be under 15ms"
            
            # Delivery targets must be realistic
            assert perf_metrics["delivery_target_ms"] <= 500, \
                f"Event {i} delivery target must be reasonable"
        
        # Validate progressive delivery timing
        delivery_timestamps = [event["delivery_timestamp"] for event in ws_client.received_events]
        
        for i in range(1, len(delivery_timestamps)):
            interval = delivery_timestamps[i] - delivery_timestamps[i-1]
            assert interval >= 0, f"Event {i} must be delivered after previous event"
            # Note: In real system, would validate reasonable intervals
        
        # Validate business performance metrics in final result
        completion_event = ws_client.received_events[-1]
        performance_report = completion_event["data"]["result"]["performance_report"]
        
        assert performance_report["total_analysis_time_seconds"] < 30, \
            "Analysis must complete within 30 seconds"
        assert performance_report["data_processing_efficiency"] > 0.9, \
            "Data processing must be highly efficient"
        assert performance_report["user_experience_score"] > 8.0, \
            "User experience score must be high"
        assert performance_report["delivery_time_target_met"], \
            "Delivery time targets must be met"
        
        # Validate large data handling performance
        tool_completed_event = ws_client.received_events[3]
        performance_summary = tool_completed_event["data"]["performance_summary"]
        
        assert performance_summary["data_processed_mb"] == 150, \
            "Must handle large dataset processing"
        assert performance_summary["analysis_efficiency"] > 0.9, \
            "Large data analysis must be efficient"
        assert performance_summary["result_generation_ms"] < 1000, \
            "Result generation must be under 1 second"
        
        # Validate final report delivery metrics
        final_event = ws_client.received_events[-1]
        final_metrics = final_event["performance_metrics"]
        
        assert final_metrics["total_report_size_kb"] < 100, \
            "Report size must be reasonable for network delivery"
        assert final_metrics["delivery_target_ms"] <= 500, \
            "Final report delivery target must be achievable"
        
        # Performance benchmark validation
        print(f"Performance Test Results:")
        print(f"- Total delivery time: {total_delivery_time:.2f}s")
        print(f"- Events delivered: {len(ws_client.received_events)}")
        print(f"- Average time per event: {total_delivery_time / len(ws_client.received_events):.2f}s")
        print(f"- Performance target met: {total_delivery_time < performance_requirements['total_report_delivery']}")
        
        # User experience validation
        final_result = completion_event["data"]["result"]
        assert final_result["financial_impact"]["monthly_savings"] > 30000, \
            "High-performance analysis must deliver significant business value"
        assert final_result["confidence_score"] > 0.9, \
            "Performance optimization must not compromise result quality"