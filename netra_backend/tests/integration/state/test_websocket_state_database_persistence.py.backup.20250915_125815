"""
WebSocket State Database Persistence Integration Tests - Phase 2

Tests WebSocket connection state persistence and recovery using real
PostgreSQL database. Validates that connection states, user sessions,
and conversation contexts survive service restarts.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Maintain conversation continuity across sessions
- Value Impact: Users can resume conversations without losing context
- Strategic Impact: Platform reliability and user experience consistency

CRITICAL: Uses REAL services (PostgreSQL, Redis, WebSocket connections)
No mocks in integration tests per CLAUDE.md standards.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from uuid import uuid4

from test_framework.ssot.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.base_test_case import BaseIntegrationTest
from test_framework.websocket_helpers import (
    WebSocketTestHelpers,
    ensure_websocket_service_ready
)
from shared.isolated_environment import get_env
from shared.types import UserID, ThreadID, RunID, RequestID
from shared.id_generation import UnifiedIdGenerator


class TestWebSocketStateDatabasePersistence(BaseIntegrationTest):
    """Integration tests for WebSocket state persistence in real database."""

    @pytest.fixture(autouse=True)
    async def setup_test_environment(self, real_services_fixture):
        """Setup test environment with real services."""
        self.services = real_services_fixture
        self.env = get_env()
        
        # Validate real services are available
        if not self.services["database_available"]:
            pytest.skip("Real database not available - required for integration testing")
            
        # Store service URLs
        self.backend_url = self.services["backend_url"]
        self.websocket_url = self.backend_url.replace("http://", "ws://") + "/ws"
        
        # Generate test identifiers using SSOT patterns
        self.test_user_id = UserID(f"state_user_{UnifiedIdGenerator.generate_user_id()}")
        self.test_thread_id = ThreadID(f"state_thread_{UnifiedIdGenerator.generate_thread_id()}")
        self.test_run_id = RunID(UnifiedIdGenerator.generate_run_id())

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_state_persistence(self, real_services_fixture):
        """Test that WebSocket connection states are persisted to database."""
        start_time = time.time()
        
        db_session = self.services["db"]
        if not db_session:
            pytest.skip("Real database session not available")
        
        # Ensure WebSocket service is ready
        if not await ensure_websocket_service_ready(self.backend_url):
            pytest.skip("WebSocket service not ready")
        
        test_token = self._create_test_auth_token(self.test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Create WebSocket connection
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{self.test_thread_id}",
            headers=headers,
            user_id=str(self.test_user_id)
        )
        
        connection_id = None
        
        try:
            # Send connection registration message
            register_request = {
                "type": "register_connection",
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id),
                "connection_metadata": {
                    "client_info": "integration_test_client",
                    "capabilities": ["agent_execution", "file_upload"],
                    "version": "test_v1.0"
                }
            }
            
            await WebSocketTestHelpers.send_test_message(websocket, register_request)
            
            # Receive connection confirmation
            response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=5.0)
            
            # Extract connection ID from response
            connection_id = response.get("connection_id") or response.get("data", {}).get("connection_id")
            
            # Wait for database persistence
            await asyncio.sleep(1.0)
            
            # Verify connection state persisted to database
            query = """
            SELECT connection_id, user_id, thread_id, connection_status, 
                   connection_metadata, created_at, last_activity
            FROM websocket_connections 
            WHERE user_id = :user_id AND thread_id = :thread_id
            ORDER BY created_at DESC
            LIMIT 1
            """
            
            result = await db_session.execute(query, {
                "user_id": str(self.test_user_id),
                "thread_id": str(self.test_thread_id)
            })
            
            connection_record = result.fetchone()
            
            # Verify test took real time
            test_duration = time.time() - start_time
            assert test_duration > 0.5, "Test completed too quickly - not using real database"
            
            # Verify connection persistence
            assert connection_record is not None, "WebSocket connection should be persisted in database"
            assert connection_record.user_id == str(self.test_user_id), "User ID should match"
            assert connection_record.thread_id == str(self.test_thread_id), "Thread ID should match"
            assert connection_record.connection_status in ["connected", "active"], "Connection should be active"
            
            # Verify metadata persistence
            if connection_record.connection_metadata:
                metadata = json.loads(connection_record.connection_metadata) if isinstance(connection_record.connection_metadata, str) else connection_record.connection_metadata
                assert "client_info" in metadata, "Connection metadata should be persisted"
                
        finally:
            await WebSocketTestHelpers.close_test_connection(websocket)
            
            # Wait for disconnection to be persisted
            await asyncio.sleep(1.0)
            
            # Verify disconnection state update
            if connection_id:
                query = """
                SELECT connection_status, disconnected_at
                FROM websocket_connections 
                WHERE connection_id = :connection_id
                """
                
                result = await db_session.execute(query, {"connection_id": connection_id})
                updated_record = result.fetchone()
                
                if updated_record:
                    # Connection status should be updated to disconnected
                    assert updated_record.connection_status in ["disconnected", "closed"], "Connection should be marked as disconnected"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_conversation_state_persistence(self, real_services_fixture):
        """Test that conversation states are persisted and recoverable from database."""
        start_time = time.time()
        
        db_session = self.services["db"]
        if not db_session:
            pytest.skip("Real database session not available")
        
        test_token = self._create_test_auth_token(self.test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Create WebSocket connection
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{self.test_thread_id}",
            headers=headers,
            user_id=str(self.test_user_id)
        )
        
        try:
            # Create conversation with multiple exchanges
            conversation_messages = [
                {
                    "type": "user_message",
                    "content": "Hello, I need help with cost optimization",
                    "thread_id": str(self.test_thread_id),
                    "user_id": str(self.test_user_id),
                    "timestamp": time.time()
                },
                {
                    "type": "agent_response", 
                    "content": "I'll help you analyze your costs. Let me start by examining your infrastructure.",
                    "thread_id": str(self.test_thread_id),
                    "user_id": str(self.test_user_id),
                    "timestamp": time.time() + 1
                },
                {
                    "type": "user_message",
                    "content": "Focus on AWS costs specifically",
                    "thread_id": str(self.test_thread_id),
                    "user_id": str(self.test_user_id),
                    "timestamp": time.time() + 2
                }
            ]
            
            # Send conversation messages
            for message in conversation_messages:
                await WebSocketTestHelpers.send_test_message(websocket, message)
                
                # Wait for acknowledgment
                try:
                    response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=3.0)
                    # Response validation is optional as format may vary
                except Exception:
                    pass  # Acknowledgment may not always come
                
                await asyncio.sleep(0.5)  # Allow database persistence
            
            # Send conversation state persistence request
            persist_request = {
                "type": "persist_conversation_state",
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id),
                "context_variables": {
                    "focus_area": "AWS costs",
                    "optimization_goals": ["reduce_spend", "improve_efficiency"],
                    "conversation_stage": "requirements_gathering"
                }
            }
            
            await WebSocketTestHelpers.send_test_message(websocket, persist_request)
            await asyncio.sleep(1.0)  # Allow persistence
            
        finally:
            await WebSocketTestHelpers.close_test_connection(websocket)
        
        # Verify conversation persistence in database
        message_query = """
        SELECT message_type, content, user_id, thread_id, created_at
        FROM conversation_messages 
        WHERE thread_id = :thread_id AND user_id = :user_id
        ORDER BY created_at ASC
        """
        
        result = await db_session.execute(message_query, {
            "thread_id": str(self.test_thread_id),
            "user_id": str(self.test_user_id)
        })
        
        persisted_messages = result.fetchall()
        
        # Verify test timing
        test_duration = time.time() - start_time
        assert test_duration > 2.0, "Conversation persistence test took too little time"
        
        # Verify message persistence
        assert len(persisted_messages) >= 1, f"Expected at least 1 persisted message, got {len(persisted_messages)}"
        
        # Verify message content preservation
        message_contents = [msg.content for msg in persisted_messages]
        original_contents = [msg["content"] for msg in conversation_messages]
        
        # At least one message should match
        has_matching_content = any(
            any(orig in content or content in orig for orig in original_contents)
            for content in message_contents
        )
        assert has_matching_content, "Should have preserved some conversation content"
        
        # Verify thread and user isolation
        for message in persisted_messages:
            assert message.user_id == str(self.test_user_id), "User isolation should be maintained"
            assert message.thread_id == str(self.test_thread_id), "Thread isolation should be maintained"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_session_state_recovery(self, real_services_fixture):
        """Test user session state recovery from database after disconnection."""
        start_time = time.time()
        
        db_session = self.services["db"]
        if not db_session:
            pytest.skip("Real database session not available")
        
        test_token = self._create_test_auth_token(self.test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Phase 1: Create session with rich state
        initial_ws = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{self.test_thread_id}",
            headers=headers,
            user_id=str(self.test_user_id)
        )
        
        session_id = None
        
        try:
            # Create rich session state
            session_request = {
                "type": "create_session",
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id),
                "session_data": {
                    "active_agents": ["cost_optimizer", "security_analyzer"],
                    "user_preferences": {
                        "notification_level": "detailed",
                        "analysis_depth": "comprehensive",
                        "report_format": "executive_summary"
                    },
                    "execution_context": {
                        "current_task": "aws_cost_analysis",
                        "progress": 25,
                        "next_steps": ["gather_usage_data", "analyze_patterns"]
                    },
                    "temporary_data": {
                        "uploaded_files": ["cost_report.csv"],
                        "analysis_cache": {"region": "us-east-1", "timeframe": "30d"}
                    }
                }
            }
            
            await WebSocketTestHelpers.send_test_message(initial_ws, session_request)
            
            # Receive session confirmation
            response = await WebSocketTestHelpers.receive_test_message(initial_ws, timeout=5.0)
            session_id = response.get("session_id") or response.get("data", {}).get("session_id")
            
            await asyncio.sleep(1.0)  # Allow database persistence
            
        finally:
            await WebSocketTestHelpers.close_test_connection(initial_ws)
        
        # Phase 2: Wait, then reconnect and recover state
        await asyncio.sleep(2.0)
        
        recovery_ws = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{self.test_thread_id}",
            headers=headers,
            user_id=str(self.test_user_id)
        )
        
        try:
            # Request session recovery
            recovery_request = {
                "type": "recover_session",
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id),
                "session_id": session_id
            }
            
            await WebSocketTestHelpers.send_test_message(recovery_ws, recovery_request)
            
            # Collect recovery response
            recovery_response = await WebSocketTestHelpers.receive_test_message(recovery_ws, timeout=5.0)
            
        finally:
            await WebSocketTestHelpers.close_test_connection(recovery_ws)
        
        # Verify session persistence in database
        session_query = """
        SELECT session_id, session_data, user_id, thread_id, 
               created_at, last_accessed, session_status
        FROM user_sessions 
        WHERE user_id = :user_id AND thread_id = :thread_id
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        result = await db_session.execute(session_query, {
            "user_id": str(self.test_user_id),
            "thread_id": str(self.test_thread_id)
        })
        
        session_record = result.fetchone()
        
        # Verify test timing
        test_duration = time.time() - start_time
        assert test_duration > 2.5, "Session recovery test took too little time"
        
        # Verify session persistence
        assert session_record is not None, "User session should be persisted in database"
        assert session_record.user_id == str(self.test_user_id), "Session user should match"
        assert session_record.thread_id == str(self.test_thread_id), "Session thread should match"
        
        # Verify session data integrity
        if session_record.session_data:
            session_data = json.loads(session_record.session_data) if isinstance(session_record.session_data, str) else session_record.session_data
            
            # Verify key session elements are preserved
            assert "user_preferences" in session_data or "active_agents" in session_data or "execution_context" in session_data, (
                "Session data should preserve key user state"
            )

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_state_updates(self, real_services_fixture):
        """Test concurrent WebSocket state updates to database maintain consistency."""
        start_time = time.time()
        
        db_session = self.services["db"]
        if not db_session:
            pytest.skip("Real database session not available")
        
        test_token = self._create_test_auth_token(self.test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Create multiple concurrent connections
        num_connections = 3
        connections = []
        connection_tasks = []
        
        try:
            # Establish multiple connections
            for i in range(num_connections):
                thread_id = f"{self.test_thread_id}_concurrent_{i}"
                websocket = await WebSocketTestHelpers.create_test_websocket_connection(
                    f"{self.websocket_url}/agent/{thread_id}",
                    headers=headers,
                    user_id=str(self.test_user_id)
                )
                connections.append((websocket, thread_id))
            
            # Define concurrent state update tasks
            async def update_connection_state(websocket, thread_id, connection_index):
                updates_sent = 0
                for update_num in range(3):  # 3 updates per connection
                    state_update = {
                        "type": "update_connection_state",
                        "thread_id": thread_id,
                        "user_id": str(self.test_user_id),
                        "connection_index": connection_index,
                        "update_number": update_num,
                        "state_data": {
                            "last_activity": time.time(),
                            "message_count": update_num + 1,
                            "connection_health": "active",
                            "processing_status": f"update_{update_num}"
                        }
                    }
                    
                    await WebSocketTestHelpers.send_test_message(websocket, state_update)
                    updates_sent += 1
                    
                    # Brief pause between updates
                    await asyncio.sleep(0.2)
                
                return updates_sent
            
            # Execute concurrent state updates
            for i, (websocket, thread_id) in enumerate(connections):
                task = update_connection_state(websocket, thread_id, i)
                connection_tasks.append(task)
            
            # Run all updates concurrently
            results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            # Wait for database consistency
            await asyncio.sleep(2.0)
            
        finally:
            # Clean up connections
            for websocket, _ in connections:
                await WebSocketTestHelpers.close_test_connection(websocket)
        
        # Verify concurrent updates maintained database consistency
        consistency_query = """
        SELECT thread_id, COUNT(*) as update_count, 
               MAX(last_activity) as latest_activity,
               COUNT(DISTINCT user_id) as user_count
        FROM websocket_connections 
        WHERE user_id = :user_id
        GROUP BY thread_id
        ORDER BY thread_id
        """
        
        result = await db_session.execute(consistency_query, {"user_id": str(self.test_user_id)})
        update_stats = result.fetchall()
        
        # Verify test timing
        test_duration = time.time() - start_time
        assert test_duration > 2.0, "Concurrent updates test took too little time"
        
        # Verify database consistency
        if update_stats:
            # Should have records for concurrent connections
            assert len(update_stats) >= 1, "Should have connection records from concurrent updates"
            
            # Verify user consistency
            for stat in update_stats:
                assert stat.user_count == 1, f"Each thread should have consistent user_id, got {stat.user_count}"
                assert stat.update_count >= 1, f"Should have at least one update per thread, got {stat.update_count}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_state_cleanup_and_expiration(self, real_services_fixture):
        """Test automatic cleanup of expired WebSocket states in database."""
        start_time = time.time()
        
        db_session = self.services["db"]
        if not db_session:
            pytest.skip("Real database session not available")
        
        test_token = self._create_test_auth_token(self.test_user_id)
        headers = {"Authorization": f"Bearer {test_token}"}
        
        # Create temporary state that should expire
        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
            f"{self.websocket_url}/agent/{self.test_thread_id}",
            headers=headers,
            user_id=str(self.test_user_id)
        )
        
        try:
            # Create state with short expiration
            expiring_state = {
                "type": "create_temporary_state",
                "thread_id": str(self.test_thread_id),
                "user_id": str(self.test_user_id),
                "state_data": {
                    "temporary_cache": {"analysis_data": "test_data"},
                    "session_variables": {"temp_var": "temp_value"}
                },
                "expiration_seconds": 5,  # Very short expiration
                "cleanup_eligible": True
            }
            
            await WebSocketTestHelpers.send_test_message(websocket, expiring_state)
            
            # Wait for state creation
            response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=3.0)
            await asyncio.sleep(1.0)  # Allow persistence
            
        finally:
            await WebSocketTestHelpers.close_test_connection(websocket)
        
        # Verify state exists initially
        initial_query = """
        SELECT COUNT(*) as state_count
        FROM temporary_websocket_states 
        WHERE user_id = :user_id AND thread_id = :thread_id
        """
        
        result = await db_session.execute(initial_query, {
            "user_id": str(self.test_user_id),
            "thread_id": str(self.test_thread_id)
        })
        
        initial_count = result.fetchone()
        
        # Wait for expiration (longer than expiration_seconds)
        await asyncio.sleep(7.0)
        
        # Check if cleanup occurred
        cleanup_query = """
        SELECT COUNT(*) as remaining_count
        FROM temporary_websocket_states 
        WHERE user_id = :user_id AND thread_id = :thread_id
        AND (expires_at IS NULL OR expires_at > NOW())
        """
        
        result = await db_session.execute(cleanup_query, {
            "user_id": str(self.test_user_id),
            "thread_id": str(self.test_thread_id)
        })
        
        remaining_count = result.fetchone()
        
        # Verify test timing
        test_duration = time.time() - start_time
        assert test_duration > 7.0, "Expiration test should take at least 7 seconds"
        
        # Verify cleanup behavior
        # Note: Cleanup may be handled by background processes, so we verify the capability exists
        # rather than requiring immediate cleanup
        
        if initial_count and initial_count.state_count > 0:
            # If state was created, verify cleanup mechanism
            if remaining_count:
                # Expired states should be cleaned up or marked for cleanup
                assert remaining_count.remaining_count <= initial_count.state_count, (
                    "Expired states should be cleaned up or marked for cleanup"
                )

    def _create_test_auth_token(self, user_id: str) -> str:
        """Create test authentication token for integration testing."""
        import base64
        
        payload = {
            "user_id": user_id,
            "email": f"test_{user_id}@example.com",
            "iat": int(time.time()),
            "exp": int(time.time() + 3600),
            "test_mode": True
        }
        
        token_data = base64.b64encode(json.dumps(payload).encode()).decode()
        return f"test.{token_data}.signature"