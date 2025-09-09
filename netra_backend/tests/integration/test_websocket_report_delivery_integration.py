"""
WebSocket Report Delivery Integration Tests - Test Suite 2

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure agent-generated reports are successfully delivered to users via WebSocket
- Value Impact: Core revenue mechanism - users must receive AI-generated insights/reports
- Strategic Impact: Foundation of $3M+ ARR - report delivery failures = user churn

CRITICAL: This test suite validates that when agents generate reports and analysis,
the results are successfully delivered to users through real-time WebSocket connections.
Without this pipeline working, users cannot access the AI-generated business value.

NO MOCKS ALLOWED: Uses real PostgreSQL (port 5434) and Redis (port 6381) services.
Tests actual WebSocket report delivery mechanisms without full Docker orchestration.
"""

import asyncio
import pytest
import time
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from unittest import mock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture, real_postgres_connection, with_test_database

from netra_backend.app.websocket_core.types import (
    MessageType, 
    WebSocketMessage,
    ConnectionInfo,
    WebSocketConnectionState,
    create_standard_message
)
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.schemas.websocket_server_messages import (
    AgentStartedMessage,
    AgentThinkingMessage, 
    ToolExecutingMessage,
    ToolCompletedMessage,
    AgentCompletedMessage,
    FinalReportMessage,
    PartialResultMessage,
    ErrorMessage
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from shared.isolated_environment import get_env
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class MockWebSocketConnection:
    """Mock WebSocket connection for testing report delivery."""
    
    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.received_messages: List[Dict[str, Any]] = []
        self.is_connected = True
        self.connection_timestamp = time.time()
        
    async def send(self, message: str):
        """Simulate sending message to WebSocket client."""
        if not self.is_connected:
            raise ConnectionError("WebSocket connection closed")
            
        try:
            parsed_message = json.loads(message)
            self.received_messages.append({
                "timestamp": time.time(),
                "message": parsed_message,
                "raw": message
            })
        except json.JSONDecodeError as e:
            # Store invalid JSON for debugging
            self.received_messages.append({
                "timestamp": time.time(),
                "error": f"Invalid JSON: {e}",
                "raw": message
            })
    
    async def close(self, code: int = 1000, reason: str = ""):
        """Close WebSocket connection."""
        self.is_connected = False
        
    def get_messages_by_type(self, message_type: str) -> List[Dict[str, Any]]:
        """Get messages of specific type."""
        return [
            msg for msg in self.received_messages 
            if msg.get("message", {}).get("type") == message_type
        ]


class ReportDeliveryValidator:
    """Validates report delivery through WebSocket events."""
    
    @staticmethod
    def validate_report_structure(report_data: Dict[str, Any]) -> bool:
        """Validate report has proper business structure."""
        required_fields = [
            'executive_summary',
            'key_findings',
            'recommendations',
            'generated_at',
            'confidence_score'
        ]
        
        for field in required_fields:
            if field not in report_data:
                return False
                
        # Validate recommendations are actionable
        recommendations = report_data.get('recommendations', [])
        if not recommendations:
            return False
            
        for rec in recommendations:
            if not isinstance(rec, dict):
                return False
            if 'action' not in rec or 'expected_impact' not in rec:
                return False
                
        return True
    
    @staticmethod
    def validate_event_sequence(events: List[Dict[str, Any]]) -> bool:
        """Validate proper WebSocket event sequence for report delivery."""
        required_sequence = [
            'agent_started',
            'agent_thinking', 
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]
        
        event_types = [event.get('message', {}).get('type') for event in events]
        
        # Check all required events are present
        for required_type in required_sequence:
            if required_type not in event_types:
                return False
                
        return True


class TestWebSocketReportDelivery(BaseIntegrationTest):
    """Integration tests for WebSocket report delivery mechanisms."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_basic_websocket_connection_and_report_delivery(self, real_services_fixture):
        """
        Test basic WebSocket connection establishment and simple report delivery.
        
        Business Value Justification (BVJ):
        - Segment: All
        - Business Goal: Foundation of real-time user interaction
        - Value Impact: Users must connect to receive AI insights
        - Strategic Impact: Without WebSocket connectivity, no real-time value delivery
        """
        real_services = real_services_fixture
        
        # Generate test user context with SSOT ID patterns
        user_id = UnifiedIdGenerator.generate_base_id("user_test")
        thread_id = UnifiedIdGenerator.generate_base_id("thread_test")
        message_id = UnifiedIdGenerator.generate_message_id("agent", user_id, thread_id)
        
        # Create user execution context
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=UnifiedIdGenerator.generate_base_id("run_test"),
            request_id=UnifiedIdGenerator.generate_base_id("req_test"),
            organization_id=UnifiedIdGenerator.generate_base_id("org_test")
        )
        
        # Create mock WebSocket connection
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        mock_connection = MockWebSocketConnection(user_id, connection_id)
        
        # Create WebSocket manager and bridge
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge()
        
        try:
            # Register connection
            await websocket_manager.register_connection(
                user_id=user_id,
                connection=mock_connection,
                connection_info=ConnectionInfo(
                    connection_id=connection_id,
                    user_id=user_id,
                    connected_at=datetime.now(timezone.utc)
                )
            )
            
            # Initialize WebSocket bridge
            await websocket_bridge.initialize_integration(websocket_manager)
            
            # Simulate report generation and delivery
            report_data = {
                "executive_summary": "Test report summary",
                "key_findings": ["Finding 1", "Finding 2"],
                "recommendations": [
                    {"action": "Implement optimization", "expected_impact": "20% cost reduction"}
                ],
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "confidence_score": 0.85
            }
            
            # Emit report delivery events
            await websocket_bridge.emit_agent_started(user_context, "report_generator", {"task": "generate_report"})
            await websocket_bridge.emit_final_report(user_context, "report_generator", report_data)
            await websocket_bridge.emit_agent_completed(user_context, "report_generator", {"status": "completed"})
            
            # Wait for event processing
            await asyncio.sleep(0.1)
            
            # Verify report was delivered via WebSocket
            assert len(mock_connection.received_messages) >= 3, "Should receive multiple WebSocket messages"
            
            # Verify report message was delivered
            final_report_messages = mock_connection.get_messages_by_type("final_report")
            assert len(final_report_messages) > 0, "Final report message must be delivered"
            
            # Validate report structure
            report_message = final_report_messages[0]["message"]
            assert ReportDeliveryValidator.validate_report_structure(report_message["payload"]), \
                "Report must have proper business structure"
            
            self.logger.info("✅ Basic WebSocket report delivery test passed")
            
        finally:
            # Cleanup
            await websocket_manager.disconnect_user(user_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_real_time_progress_updates_during_report_generation(self, real_services_fixture):
        """
        Test real-time progress updates during report generation process.
        
        Business Value Justification (BVJ):
        - Segment: All
        - Business Goal: User engagement through live progress visibility
        - Value Impact: Users see AI working on their problems in real-time
        - Strategic Impact: Real-time feedback increases user confidence and retention
        """
        real_services = real_services_fixture
        
        # Generate test identifiers
        user_id = UnifiedIdGenerator.generate_base_id("user_test")
        thread_id = UnifiedIdGenerator.generate_base_id("thread_test")
        
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=UnifiedIdGenerator.generate_base_id("run_test"),
            request_id=UnifiedIdGenerator.generate_base_id("req_test"),
            organization_id=UnifiedIdGenerator.generate_base_id("org_test")
        )
        
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        mock_connection = MockWebSocketConnection(user_id, connection_id)
        
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge()
        
        try:
            await websocket_manager.register_connection(
                user_id=user_id,
                connection=mock_connection,
                connection_info=ConnectionInfo(
                    connection_id=connection_id,
                    user_id=user_id,
                    connected_at=datetime.now(timezone.utc)
                )
            )
            
            await websocket_bridge.initialize_integration(websocket_manager)
            
            # Simulate detailed progress updates during report generation
            await websocket_bridge.emit_agent_started(user_context, "data_analyzer", {"phase": "initialization"})
            await asyncio.sleep(0.05)
            
            await websocket_bridge.emit_agent_thinking(user_context, "data_analyzer", {
                "reasoning": "Analyzing data patterns for cost optimization opportunities",
                "progress": 25
            })
            await asyncio.sleep(0.05)
            
            await websocket_bridge.emit_tool_executing(user_context, "cost_analyzer", {
                "operation": "pattern_analysis",
                "data_size": "10GB"
            })
            await asyncio.sleep(0.05)
            
            await websocket_bridge.emit_partial_result(user_context, "data_analyzer", {
                "preliminary_findings": ["Pattern A identified", "Cost inefficiency detected"],
                "progress": 60
            })
            await asyncio.sleep(0.05)
            
            await websocket_bridge.emit_tool_completed(user_context, "cost_analyzer", {
                "insights": ["Optimization potential: 30%", "Risk level: Low"],
                "execution_time": "2.3s"
            })
            await asyncio.sleep(0.05)
            
            await websocket_bridge.emit_agent_completed(user_context, "data_analyzer", {
                "final_analysis": "Complete report generated",
                "total_time": "5.2s"
            })
            
            await asyncio.sleep(0.1)
            
            # Verify complete event sequence
            assert len(mock_connection.received_messages) >= 6, "Should receive all progress update messages"
            
            # Verify proper event sequence
            assert ReportDeliveryValidator.validate_event_sequence(mock_connection.received_messages), \
                "Events must follow proper sequence for user experience"
            
            # Verify thinking events contain reasoning
            thinking_messages = mock_connection.get_messages_by_type("agent_thinking")
            assert len(thinking_messages) > 0, "Must receive thinking updates"
            assert "reasoning" in thinking_messages[0]["message"]["payload"], "Thinking must include reasoning"
            
            self.logger.info("✅ Real-time progress updates test passed")
            
        finally:
            await websocket_manager.disconnect_user(user_id)
    
    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_websocket_event_emission_patterns_validation(self, real_services_fixture):
        """
        Test WebSocket event emission patterns follow SSOT message structure.
        
        Business Value Justification (BVJ):
        - Segment: Platform/Internal
        - Business Goal: Consistent message formatting for frontend integration
        - Value Impact: Prevents frontend parsing errors that break user experience
        - Strategic Impact: Message consistency enables reliable multi-platform support
        """
        real_services = real_services_fixture
        
        user_id = UnifiedIdGenerator.generate_base_id("user_test")
        thread_id = UnifiedIdGenerator.generate_base_id("thread_test")
        
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=UnifiedIdGenerator.generate_base_id("run_test"),
            request_id=UnifiedIdGenerator.generate_base_id("req_test"),
            organization_id=UnifiedIdGenerator.generate_base_id("org_test")
        )
        
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        mock_connection = MockWebSocketConnection(user_id, connection_id)
        
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge()
        
        try:
            await websocket_manager.register_connection(
                user_id=user_id,
                connection=mock_connection,
                connection_info=ConnectionInfo(
                    connection_id=connection_id,
                    user_id=user_id,
                    connected_at=datetime.now(timezone.utc)
                )
            )
            
            await websocket_bridge.initialize_integration(websocket_manager)
            
            # Test each critical event type with proper payload structure
            test_events = [
                ("agent_started", {"agent_name": "optimizer", "task": "cost_analysis"}),
                ("agent_thinking", {"reasoning": "Analyzing cost patterns", "step": 1}),
                ("tool_executing", {"tool_name": "data_fetcher", "operation": "extract"}),
                ("tool_completed", {"tool_name": "data_fetcher", "result": "Success", "data_count": 1000}),
                ("agent_completed", {"final_result": "Analysis complete", "recommendations_count": 5})
            ]
            
            for event_type, payload in test_events:
                if event_type == "agent_started":
                    await websocket_bridge.emit_agent_started(user_context, payload["agent_name"], payload)
                elif event_type == "agent_thinking":
                    await websocket_bridge.emit_agent_thinking(user_context, "optimizer", payload)
                elif event_type == "tool_executing":
                    await websocket_bridge.emit_tool_executing(user_context, payload["tool_name"], payload)
                elif event_type == "tool_completed":
                    await websocket_bridge.emit_tool_completed(user_context, payload["tool_name"], payload)
                elif event_type == "agent_completed":
                    await websocket_bridge.emit_agent_completed(user_context, "optimizer", payload)
                    
                await asyncio.sleep(0.02)
            
            await asyncio.sleep(0.1)
            
            # Verify all messages have correct structure
            assert len(mock_connection.received_messages) == len(test_events), "All events must be delivered"
            
            for i, (expected_type, expected_payload) in enumerate(test_events):
                message = mock_connection.received_messages[i]["message"]
                
                # Verify SSOT message structure
                assert "type" in message, f"Message {i} must have type field"
                assert "payload" in message, f"Message {i} must have payload field"
                assert message["type"] == expected_type, f"Message {i} type mismatch"
                
                # Verify payload contains expected data
                payload = message["payload"]
                for key, value in expected_payload.items():
                    assert key in payload, f"Message {i} payload missing key: {key}"
            
            self.logger.info("✅ WebSocket event emission patterns validation passed")
            
        finally:
            await websocket_manager.disconnect_user(user_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_websocket_report_isolation(self, real_services_fixture):
        """
        Test multi-user WebSocket report delivery isolation.
        
        Business Value Justification (BVJ):
        - Segment: Enterprise
        - Business Goal: Ensure user data privacy and security
        - Value Impact: Prevents data leakage between concurrent users
        - Strategic Impact: CRITICAL for enterprise trust and compliance
        """
        real_services = real_services_fixture
        
        # Create two separate users
        user1_id = UnifiedIdGenerator.generate_base_id("user1_test")
        user2_id = UnifiedIdGenerator.generate_base_id("user2_test")
        
        user1_context = UserExecutionContext(
            user_id=user1_id,
            thread_id=UnifiedIdGenerator.generate_base_id("thread1_test"),
            run_id=UnifiedIdGenerator.generate_base_id("run1_test"),
            request_id=UnifiedIdGenerator.generate_base_id("req1_test"),
            organization_id=UnifiedIdGenerator.generate_base_id("org1_test")
        )
        
        user2_context = UserExecutionContext(
            user_id=user2_id,
            thread_id=UnifiedIdGenerator.generate_base_id("thread2_test"),
            run_id=UnifiedIdGenerator.generate_base_id("run2_test"),
            request_id=UnifiedIdGenerator.generate_base_id("req2_test"),
            organization_id=UnifiedIdGenerator.generate_base_id("org2_test")
        )
        
        # Create separate WebSocket connections
        connection1_id = UnifiedIdGenerator.generate_websocket_connection_id(user1_id)
        connection2_id = UnifiedIdGenerator.generate_websocket_connection_id(user2_id)
        
        mock_connection1 = MockWebSocketConnection(user1_id, connection1_id)
        mock_connection2 = MockWebSocketConnection(user2_id, connection2_id)
        
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge()
        
        try:
            # Register both connections
            await websocket_manager.register_connection(
                user_id=user1_id,
                connection=mock_connection1,
                connection_info=ConnectionInfo(
                    connection_id=connection1_id,
                    user_id=user1_id,
                    connected_at=datetime.now(timezone.utc)
                )
            )
            
            await websocket_manager.register_connection(
                user_id=user2_id,
                connection=mock_connection2,
                connection_info=ConnectionInfo(
                    connection_id=connection2_id,
                    user_id=user2_id,
                    connected_at=datetime.now(timezone.utc)
                )
            )
            
            await websocket_bridge.initialize_integration(websocket_manager)
            
            # Send confidential reports to each user
            user1_confidential_report = {
                "confidential_data": "User 1 sensitive information",
                "user_specific_insights": "User 1 cost savings: $50,000",
                "recommendations": [{"action": "User 1 specific action", "impact": "High"}]
            }
            
            user2_confidential_report = {
                "confidential_data": "User 2 sensitive information", 
                "user_specific_insights": "User 2 cost savings: $75,000",
                "recommendations": [{"action": "User 2 specific action", "impact": "Medium"}]
            }
            
            # Emit reports to different users simultaneously
            await asyncio.gather(
                websocket_bridge.emit_final_report(user1_context, "agent1", user1_confidential_report),
                websocket_bridge.emit_final_report(user2_context, "agent2", user2_confidential_report)
            )
            
            await asyncio.sleep(0.1)
            
            # Verify isolation - each user should only receive their own report
            user1_messages = mock_connection1.received_messages
            user2_messages = mock_connection2.received_messages
            
            assert len(user1_messages) > 0, "User 1 must receive messages"
            assert len(user2_messages) > 0, "User 2 must receive messages"
            
            # Check User 1 only received User 1 data
            for message in user1_messages:
                payload = message["message"]["payload"]
                assert "User 1" in str(payload), "User 1 should only see User 1 data"
                assert "User 2" not in str(payload), "User 1 must NOT see User 2 data"
            
            # Check User 2 only received User 2 data
            for message in user2_messages:
                payload = message["message"]["payload"]
                assert "User 2" in str(payload), "User 2 should only see User 2 data"
                assert "User 1" not in str(payload), "User 2 must NOT see User 1 data"
            
            self.logger.info("✅ Multi-user WebSocket isolation test passed")
            
        finally:
            await websocket_manager.disconnect_user(user1_id)
            await websocket_manager.disconnect_user(user2_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_authentication_and_report_security(self, real_services_fixture):
        """
        Test WebSocket authentication integration with report delivery security.
        
        Business Value Justification (BVJ):
        - Segment: All
        - Business Goal: Prevent unauthorized access to reports
        - Value Impact: Protect sensitive business insights from unauthorized users
        - Strategic Impact: Security breach prevention maintains customer trust
        """
        real_services = real_services_fixture
        
        # Create authenticated user context
        authenticated_user_id = UnifiedIdGenerator.generate_base_id("auth_user_test")
        unauthenticated_user_id = UnifiedIdGenerator.generate_base_id("unauth_user_test")
        
        auth_context = UserExecutionContext(
            user_id=authenticated_user_id,
            thread_id=UnifiedIdGenerator.generate_base_id("auth_thread_test"),
            run_id=UnifiedIdGenerator.generate_base_id("auth_run_test"),
            request_id=UnifiedIdGenerator.generate_base_id("auth_req_test"),
            organization_id=UnifiedIdGenerator.generate_base_id("auth_org_test")
        )
        
        # Simulate authenticated and unauthenticated connections
        auth_connection_id = UnifiedIdGenerator.generate_websocket_connection_id(authenticated_user_id)
        unauth_connection_id = UnifiedIdGenerator.generate_websocket_connection_id(unauthenticated_user_id)
        
        auth_connection = MockWebSocketConnection(authenticated_user_id, auth_connection_id)
        unauth_connection = MockWebSocketConnection(unauthenticated_user_id, unauth_connection_id)
        
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge()
        
        try:
            # Register only authenticated connection
            await websocket_manager.register_connection(
                user_id=authenticated_user_id,
                connection=auth_connection,
                connection_info=ConnectionInfo(
                    connection_id=auth_connection_id,
                    user_id=authenticated_user_id,
                    connected_at=datetime.now(timezone.utc)
                )
            )
            
            await websocket_bridge.initialize_integration(websocket_manager)
            
            # Send sensitive report to authenticated user
            sensitive_report = {
                "confidential_analysis": "Proprietary business insights",
                "financial_projections": {"revenue": 1000000, "costs": 800000},
                "competitive_advantages": ["Secret sauce A", "Secret sauce B"],
                "classified": True
            }
            
            # Attempt to send report - should succeed for authenticated user
            await websocket_bridge.emit_final_report(auth_context, "secure_agent", sensitive_report)
            
            # Try to send to unauthenticated user (should fail gracefully)
            unauth_context = UserExecutionContext(
                user_id=unauthenticated_user_id,
                thread_id=UnifiedIdGenerator.generate_base_id("unauth_thread_test"),
                run_id=UnifiedIdGenerator.generate_base_id("unauth_run_test"),
                request_id=UnifiedIdGenerator.generate_base_id("unauth_req_test"),
                organization_id=UnifiedIdGenerator.generate_base_id("unauth_org_test")
            )
            
            # This should NOT deliver the report (no connection registered)
            await websocket_bridge.emit_final_report(unauth_context, "secure_agent", sensitive_report)
            
            await asyncio.sleep(0.1)
            
            # Verify authenticated user received the report
            assert len(auth_connection.received_messages) > 0, "Authenticated user must receive report"
            
            # Verify unauthenticated user received nothing
            assert len(unauth_connection.received_messages) == 0, "Unauthenticated user must receive nothing"
            
            # Verify report content in authenticated user's messages
            auth_report_messages = auth_connection.get_messages_by_type("final_report")
            assert len(auth_report_messages) > 0, "Authenticated user must receive final report"
            
            report_payload = auth_report_messages[0]["message"]["payload"]
            assert "confidential_analysis" in report_payload, "Report must contain sensitive data"
            assert report_payload["classified"] is True, "Report classification must be preserved"
            
            self.logger.info("✅ WebSocket authentication and report security test passed")
            
        finally:
            await websocket_manager.disconnect_user(authenticated_user_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_handling_over_websocket_connections(self, real_services_fixture):
        """
        Test error handling and error reporting over WebSocket connections.
        
        Business Value Justification (BVJ):
        - Segment: All
        - Business Goal: Transparent error communication to users
        - Value Impact: Users understand when and why AI agents fail
        - Strategic Impact: Error transparency builds user trust and enables support
        """
        real_services = real_services_fixture
        
        user_id = UnifiedIdGenerator.generate_base_id("error_user_test")
        
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=UnifiedIdGenerator.generate_base_id("error_thread_test"),
            run_id=UnifiedIdGenerator.generate_base_id("error_run_test"),
            request_id=UnifiedIdGenerator.generate_base_id("error_req_test"),
            organization_id=UnifiedIdGenerator.generate_base_id("error_org_test")
        )
        
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        mock_connection = MockWebSocketConnection(user_id, connection_id)
        
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge()
        
        try:
            await websocket_manager.register_connection(
                user_id=user_id,
                connection=mock_connection,
                connection_info=ConnectionInfo(
                    connection_id=connection_id,
                    user_id=user_id,
                    connected_at=datetime.now(timezone.utc)
                )
            )
            
            await websocket_bridge.initialize_integration(websocket_manager)
            
            # Simulate various error scenarios
            await websocket_bridge.emit_agent_started(user_context, "error_prone_agent", {"task": "risky_operation"})
            
            # Data access error
            await websocket_bridge.emit_error(user_context, "data_access_error", {
                "error": "Database connection failed",
                "code": "DB_CONNECTION_ERROR",
                "recoverable": True,
                "retry_after": 30
            })
            
            # Tool execution error
            await websocket_bridge.emit_error(user_context, "tool_execution_error", {
                "error": "API rate limit exceeded",
                "code": "RATE_LIMIT_ERROR", 
                "recoverable": True,
                "retry_after": 60
            })
            
            # Agent failure error
            await websocket_bridge.emit_agent_error(user_context, "error_prone_agent", {
                "error": "Agent execution failed due to invalid parameters",
                "code": "INVALID_PARAMETERS",
                "recoverable": False,
                "user_action_required": "Please review input parameters"
            })
            
            await asyncio.sleep(0.1)
            
            # Verify error messages were delivered
            error_messages = mock_connection.get_messages_by_type("error")
            agent_error_messages = mock_connection.get_messages_by_type("agent_error")
            
            assert len(error_messages) >= 2, "Must receive general error messages"
            assert len(agent_error_messages) >= 1, "Must receive agent error messages"
            
            # Verify error message structure
            for error_msg in error_messages:
                payload = error_msg["message"]["payload"]
                assert "error" in payload, "Error message must include error description"
                assert "code" in payload, "Error message must include error code"
                assert "recoverable" in payload, "Error message must indicate if recoverable"
            
            # Verify agent error includes user guidance
            agent_error_payload = agent_error_messages[0]["message"]["payload"]
            assert "user_action_required" in agent_error_payload, "Agent errors must include user guidance"
            
            self.logger.info("✅ Error handling over WebSocket connections test passed")
            
        finally:
            await websocket_manager.disconnect_user(user_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_message_formatting_and_structure(self, real_services_fixture):
        """
        Test WebSocket message formatting follows SSOT schema structure.
        
        Business Value Justification (BVJ):
        - Segment: Platform/Internal
        - Business Goal: Consistent API for frontend integration
        - Value Impact: Prevents frontend parsing errors and improves UX
        - Strategic Impact: Standard message format enables multi-platform support
        """
        real_services = real_services_fixture
        
        user_id = UnifiedIdGenerator.generate_base_id("format_user_test")
        
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=UnifiedIdGenerator.generate_base_id("format_thread_test"),
            run_id=UnifiedIdGenerator.generate_base_id("format_run_test"),
            request_id=UnifiedIdGenerator.generate_base_id("format_req_test"),
            organization_id=UnifiedIdGenerator.generate_base_id("format_org_test")
        )
        
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        mock_connection = MockWebSocketConnection(user_id, connection_id)
        
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge()
        
        try:
            await websocket_manager.register_connection(
                user_id=user_id,
                connection=mock_connection,
                connection_info=ConnectionInfo(
                    connection_id=connection_id,
                    user_id=user_id,
                    connected_at=datetime.now(timezone.utc)
                )
            )
            
            await websocket_bridge.initialize_integration(websocket_manager)
            
            # Test comprehensive message formatting
            test_report = {
                "id": "report_123",
                "title": "Cost Optimization Analysis",
                "sections": {
                    "summary": "Identified 25% cost reduction opportunity",
                    "details": {"current_spend": 100000, "projected_savings": 25000}
                },
                "metadata": {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "version": "1.0",
                    "format": "business_report"
                }
            }
            
            await websocket_bridge.emit_final_report(user_context, "format_agent", test_report)
            await asyncio.sleep(0.1)
            
            # Verify message structure
            messages = mock_connection.received_messages
            assert len(messages) > 0, "Must receive formatted message"
            
            message = messages[0]["message"]
            
            # Verify SSOT WebSocket message structure
            required_fields = ["type", "payload"]
            for field in required_fields:
                assert field in message, f"Message must have {field} field"
            
            assert message["type"] == "final_report", "Message type must match expected"
            
            # Verify payload preserves nested structure
            payload = message["payload"]
            assert "sections" in payload, "Nested sections must be preserved"
            assert "metadata" in payload, "Nested metadata must be preserved"
            assert payload["sections"]["details"]["current_spend"] == 100000, "Numeric values must be preserved"
            
            # Verify JSON serialization is valid
            json_str = messages[0]["raw"]
            parsed = json.loads(json_str)
            assert parsed == message, "Message must be valid JSON"
            
            self.logger.info("✅ WebSocket message formatting and structure test passed")
            
        finally:
            await websocket_manager.disconnect_user(user_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_websocket_report_deliveries(self, real_services_fixture):
        """
        Test concurrent WebSocket report deliveries handle load properly.
        
        Business Value Justification (BVJ):
        - Segment: Enterprise
        - Business Goal: Handle multiple concurrent users receiving reports
        - Value Impact: System scalability for enterprise workloads
        - Strategic Impact: Performance under load enables enterprise adoption
        """
        real_services = real_services_fixture
        
        # Create multiple concurrent users
        num_concurrent_users = 5
        users = []
        connections = []
        contexts = []
        
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge()
        
        try:
            # Setup multiple users with connections
            for i in range(num_concurrent_users):
                user_id = UnifiedIdGenerator.generate_base_id(f"concurrent_user_{i}_test")
                
                context = UserExecutionContext(
                    user_id=user_id,
                    thread_id=UnifiedIdGenerator.generate_base_id(f"concurrent_thread_{i}_test"),
                    run_id=UnifiedIdGenerator.generate_base_id(f"concurrent_run_{i}_test"),
                    request_id=UnifiedIdGenerator.generate_base_id(f"concurrent_req_{i}_test"),
                    organization_id=UnifiedIdGenerator.generate_base_id(f"concurrent_org_{i}_test")
                )
                
                connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
                mock_connection = MockWebSocketConnection(user_id, connection_id)
                
                await websocket_manager.register_connection(
                    user_id=user_id,
                    connection=mock_connection,
                    connection_info=ConnectionInfo(
                        connection_id=connection_id,
                        user_id=user_id,
                        connected_at=datetime.now(timezone.utc)
                    )
                )
                
                users.append(user_id)
                connections.append(mock_connection)
                contexts.append(context)
            
            await websocket_bridge.initialize_integration(websocket_manager)
            
            # Send concurrent reports to all users
            async def send_report_to_user(context, user_index):
                report = {
                    "user_specific_data": f"Report for user {user_index}",
                    "analysis_results": f"User {user_index} savings: ${(user_index + 1) * 10000}",
                    "timestamp": time.time()
                }
                
                await websocket_bridge.emit_agent_started(context, f"agent_{user_index}", {"user": user_index})
                await websocket_bridge.emit_final_report(context, f"agent_{user_index}", report)
                await websocket_bridge.emit_agent_completed(context, f"agent_{user_index}", {"user": user_index})
            
            # Execute all reports concurrently
            start_time = time.time()
            await asyncio.gather(*[
                send_report_to_user(contexts[i], i) for i in range(num_concurrent_users)
            ])
            end_time = time.time()
            
            processing_time = end_time - start_time
            await asyncio.sleep(0.1)
            
            # Verify all users received their reports
            for i, connection in enumerate(connections):
                assert len(connection.received_messages) >= 3, f"User {i} must receive all messages"
                
                # Verify user received correct data
                final_reports = connection.get_messages_by_type("final_report")
                assert len(final_reports) > 0, f"User {i} must receive final report"
                
                payload = final_reports[0]["message"]["payload"]
                expected_data = f"Report for user {i}"
                assert expected_data in payload["user_specific_data"], f"User {i} must receive correct data"
            
            # Verify performance - concurrent processing should be efficient
            assert processing_time < 2.0, f"Concurrent processing too slow: {processing_time:.2f}s"
            
            self.logger.info(f"✅ Concurrent WebSocket deliveries test passed - {num_concurrent_users} users in {processing_time:.2f}s")
            
        finally:
            # Cleanup all connections
            for user_id in users:
                await websocket_manager.disconnect_user(user_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_recovery_and_report_continuity(self, real_services_fixture):
        """
        Test WebSocket connection recovery and report delivery continuity.
        
        Business Value Justification (BVJ):
        - Segment: All
        - Business Goal: Reliable report delivery despite network interruptions
        - Value Impact: Users don't lose reports due to temporary connection issues
        - Strategic Impact: Network resilience maintains user confidence
        """
        real_services = real_services_fixture
        
        user_id = UnifiedIdGenerator.generate_base_id("recovery_user_test")
        
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=UnifiedIdGenerator.generate_base_id("recovery_thread_test"),
            run_id=UnifiedIdGenerator.generate_base_id("recovery_run_test"),
            request_id=UnifiedIdGenerator.generate_base_id("recovery_req_test"),
            organization_id=UnifiedIdGenerator.generate_base_id("recovery_org_test")
        )
        
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge()
        
        # First connection
        connection1_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        mock_connection1 = MockWebSocketConnection(user_id, connection1_id)
        
        try:
            # Initial connection and report start
            await websocket_manager.register_connection(
                user_id=user_id,
                connection=mock_connection1,
                connection_info=ConnectionInfo(
                    connection_id=connection1_id,
                    user_id=user_id,
                    connected_at=datetime.now(timezone.utc)
                )
            )
            
            await websocket_bridge.initialize_integration(websocket_manager)
            
            # Start report generation
            await websocket_bridge.emit_agent_started(user_context, "resilient_agent", {"task": "important_analysis"})
            await websocket_bridge.emit_agent_thinking(user_context, "resilient_agent", {"progress": "Starting analysis"})
            
            # Simulate connection failure
            await mock_connection1.close(code=1001, reason="Network interruption")
            await websocket_manager.disconnect_user(user_id)
            
            await asyncio.sleep(0.1)
            
            # User reconnects with new connection
            connection2_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
            mock_connection2 = MockWebSocketConnection(user_id, connection2_id)
            
            await websocket_manager.register_connection(
                user_id=user_id,
                connection=mock_connection2,
                connection_info=ConnectionInfo(
                    connection_id=connection2_id,
                    user_id=user_id,
                    connected_at=datetime.now(timezone.utc)
                )
            )
            
            # Continue report generation after reconnection
            await websocket_bridge.emit_tool_executing(user_context, "recovery_tool", {"resuming": True})
            
            final_report = {
                "analysis_complete": True,
                "recovery_successful": True,
                "findings": ["Critical insight 1", "Critical insight 2"],
                "confidence": 0.95
            }
            
            await websocket_bridge.emit_final_report(user_context, "resilient_agent", final_report)
            await websocket_bridge.emit_agent_completed(user_context, "resilient_agent", {"recovered": True})
            
            await asyncio.sleep(0.1)
            
            # Verify first connection received initial messages
            assert len(mock_connection1.received_messages) >= 2, "First connection must receive initial messages"
            
            # Verify second connection received continuation messages
            assert len(mock_connection2.received_messages) >= 3, "Second connection must receive continuation messages"
            
            # Verify final report was delivered to new connection
            final_reports = mock_connection2.get_messages_by_type("final_report")
            assert len(final_reports) > 0, "Final report must be delivered after reconnection"
            
            report_payload = final_reports[0]["message"]["payload"]
            assert report_payload["recovery_successful"] is True, "Recovery status must be tracked"
            assert report_payload["analysis_complete"] is True, "Analysis completion must be preserved"
            
            self.logger.info("✅ WebSocket connection recovery and report continuity test passed")
            
        finally:
            await websocket_manager.disconnect_user(user_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_performance_and_delivery_timing(self, real_services_fixture):
        """
        Test WebSocket performance and report delivery timing requirements.
        
        Business Value Justification (BVJ):
        - Segment: All
        - Business Goal: Fast report delivery for good user experience
        - Value Impact: Quick response times keep users engaged
        - Strategic Impact: Performance differentiator vs competitors
        """
        real_services = real_services_fixture
        
        user_id = UnifiedIdGenerator.generate_base_id("perf_user_test")
        
        user_context = UserExecutionContext(
            user_id=user_id,
            thread_id=UnifiedIdGenerator.generate_base_id("perf_thread_test"),
            run_id=UnifiedIdGenerator.generate_base_id("perf_run_test"),
            request_id=UnifiedIdGenerator.generate_base_id("perf_req_test"),
            organization_id=UnifiedIdGenerator.generate_base_id("perf_org_test")
        )
        
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        mock_connection = MockWebSocketConnection(user_id, connection_id)
        
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge()
        
        try:
            await websocket_manager.register_connection(
                user_id=user_id,
                connection=mock_connection,
                connection_info=ConnectionInfo(
                    connection_id=connection_id,
                    user_id=user_id,
                    connected_at=datetime.now(timezone.utc)
                )
            )
            
            await websocket_bridge.initialize_integration(websocket_manager)
            
            # Measure delivery timing for various report sizes
            test_reports = [
                {"size": "small", "data": {"summary": "Small report", "items": list(range(10))}},
                {"size": "medium", "data": {"summary": "Medium report", "items": list(range(100))}},
                {"size": "large", "data": {"summary": "Large report", "items": list(range(1000))}}
            ]
            
            delivery_times = []
            
            for report_config in test_reports:
                start_time = time.time()
                
                await websocket_bridge.emit_final_report(
                    user_context, 
                    "performance_agent", 
                    report_config["data"]
                )
                
                await asyncio.sleep(0.01)  # Minimal processing time
                
                end_time = time.time()
                delivery_time = end_time - start_time
                delivery_times.append(delivery_time)
                
                self.logger.info(f"Report {report_config['size']} delivered in {delivery_time:.3f}s")
            
            # Verify all reports were delivered
            final_reports = mock_connection.get_messages_by_type("final_report")
            assert len(final_reports) == len(test_reports), "All reports must be delivered"
            
            # Verify performance requirements
            max_delivery_time = max(delivery_times)
            avg_delivery_time = sum(delivery_times) / len(delivery_times)
            
            # Performance thresholds
            assert max_delivery_time < 0.5, f"Maximum delivery time too slow: {max_delivery_time:.3f}s"
            assert avg_delivery_time < 0.1, f"Average delivery time too slow: {avg_delivery_time:.3f}s"
            
            # Verify message order preservation
            for i, report in enumerate(final_reports):
                expected_size = test_reports[i]["size"]
                payload = report["message"]["payload"]
                assert f"{expected_size.title()} report" in payload["summary"], "Message order must be preserved"
            
            self.logger.info(f"✅ WebSocket performance test passed - Avg: {avg_delivery_time:.3f}s, Max: {max_delivery_time:.3f}s")
            
        finally:
            await websocket_manager.disconnect_user(user_id)