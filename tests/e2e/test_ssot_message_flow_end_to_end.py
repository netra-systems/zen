"""
E2E Tests: SSOT Message Flow End-to-End Validation

This test suite validates SSOT message flow patterns in complete end-to-end scenarios
including WebSocket communication, agent execution, and database persistence.

PRIMARY TARGET: test_framework/ssot/database.py:596 - Direct session.add() violation
VALIDATION SCOPE: Complete user journey with message creation and agent interaction

Business Value:
- Ensures consistent message flow from WebSocket to database
- Validates agent-generated messages follow SSOT patterns
- Prevents data corruption in production user workflows
- Maintains message integrity across the entire platform

CRITICAL: These tests use REAL services, REAL authentication, and REAL WebSocket
connections to validate actual production behavior. NO MOCKS in E2E testing.

AUTHENTICATION REQUIREMENT: ALL E2E tests MUST authenticate using real auth flows
as mandated by CLAUDE.md. Uses test_framework/ssot/e2e_auth_helper.py.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import pytest
import websockets
import aiohttp

# SSOT Imports - Absolute imports only
from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.database_test_utilities import DatabaseTestUtilities
from netra_backend.app.services.database.message_repository import MessageRepository
from netra_backend.app.services.database.thread_repository import ThreadRepository
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@pytest.mark.e2e
class TestSSotMessageFlowEndToEnd:
    """
    End-to-End Tests for SSOT Message Flow Validation
    
    These tests validate complete user journeys that create messages
    through WebSocket interactions and expose any SSOT violations
    in the message creation pipeline.
    """
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.auth_helper = E2EAuthHelper()
        self.db_helper = DatabaseTestUtilities(service="netra_backend")
        self.message_repository = MessageRepository()
        self.thread_repository = ThreadRepository()
        
        # E2E test configuration
        self.auth_config = E2EAuthConfig()
        
    async def asyncSetUp(self):
        """Setup E2E environment with authentication."""
        # Generate unique test identifiers
        self.test_user_id = f"e2e_user_{uuid.uuid4().hex[:8]}"
        self.test_session_id = f"e2e_session_{uuid.uuid4().hex[:8]}"
        
        # Authenticate for E2E testing (MANDATORY per CLAUDE.md)
        self.auth_result = await self.auth_helper.authenticate_e2e_user(
            user_id=self.test_user_id,
            config=self.auth_config
        )
        
        assert self.auth_result.is_success, f"E2E authentication failed: {self.auth_result.error_message}"
        
        # Clean up any existing test data
        await self._cleanup_test_data()
        
        logger.info(f"E2E Test Setup Complete - User: {self.test_user_id}, Token: {self.auth_result.access_token[:20]}...")
        
    async def asyncTearDown(self):
        """Clean up E2E test data."""
        await self._cleanup_test_data()
        
    async def _cleanup_test_data(self):
        """Remove all test data from database."""
        try:
            async with self.db_helper.get_async_session() as session:
                # Clean up test messages and threads
                await session.execute(
                    text("DELETE FROM message WHERE thread_id LIKE :pattern"),
                    {"pattern": f"%{self.test_user_id}%"}
                )
                await session.execute(
                    text("DELETE FROM thread WHERE metadata_->>'user_id' = :user_id"),
                    {"user_id": self.test_user_id}
                )
                await session.commit()
        except Exception as e:
            logger.warning(f"Cleanup warning (non-critical): {e}")
            
    @pytest.mark.asyncio
    async def test_ssot_websocket_message_creation_e2e(self):
        """
        CRITICAL E2E TEST: Validate SSOT message creation through WebSocket flow.
        
        This test simulates a complete user journey:
        1. User connects via WebSocket (authenticated)
        2. User sends message through WebSocket
        3. System creates thread and messages
        4. Validates SSOT compliance in created messages
        
        EXPECTED: Test should FAIL if test framework creates messages
        with different structure than SSOT repository.
        """
        logger.info("=== E2E WebSocket Message Creation SSOT Test ===")
        
        websocket_url = f"{self.auth_config.websocket_url}?token={self.auth_result.access_token}"
        
        async with websockets.connect(websocket_url) as websocket:
            logger.info("WebSocket connection established")
            
            # 1. Send user message through WebSocket
            user_message = {
                "type": "user_message",
                "content": "E2E SSOT validation test message",
                "timestamp": int(time.time()),
                "session_id": self.test_session_id,
                "metadata": {
                    "test_type": "e2e_ssot_validation",
                    "user_id": self.test_user_id
                }
            }
            
            await websocket.send(json.dumps(user_message))
            logger.info("User message sent via WebSocket")
            
            # 2. Wait for system response and message processing
            response_received = False
            thread_id = None
            response_timeout = 30  # 30 seconds timeout
            start_time = time.time()
            
            while not response_received and (time.time() - start_time) < response_timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    logger.info(f"WebSocket response: {response_data.get('type', 'unknown')}")
                    
                    # Look for thread creation or message response
                    if response_data.get("type") in ["thread_created", "message_response", "agent_response"]:
                        thread_id = response_data.get("thread_id")
                        if thread_id:
                            response_received = True
                            break
                            
                except asyncio.TimeoutError:
                    logger.info("Waiting for WebSocket response...")
                    continue
                except Exception as e:
                    logger.error(f"WebSocket error: {e}")
                    break
                    
            assert response_received, "Did not receive expected WebSocket response within timeout"
            assert thread_id, "No thread_id found in WebSocket response"
            
            logger.info(f"WebSocket processing complete - Thread ID: {thread_id}")
            
            # 3. Validate database state - check message creation patterns
            async with self.db_helper.get_async_session() as session:
                # Get all messages for the thread
                messages_result = await session.execute(
                    select(Message).where(Message.thread_id == thread_id).order_by(Message.created_at)
                )
                created_messages = messages_result.scalars().all()
                
                assert len(created_messages) > 0, "No messages were created during WebSocket flow"
                
                # 4. CRITICAL SSOT VALIDATION: Compare with reference SSOT message
                # Create a reference message using proper SSOT repository
                reference_message = await self.message_repository.create_message(
                    db=session,
                    thread_id=thread_id,
                    role="user",
                    content="SSOT reference message",
                    metadata={"source": "ssot_reference"}
                )
                await session.commit()
                
                # Find user message created by WebSocket flow
                websocket_user_message = None
                for msg in created_messages:
                    if msg.role == "user" and "E2E SSOT validation" in str(msg.content):
                        websocket_user_message = msg
                        break
                        
                assert websocket_user_message, "Could not find user message created by WebSocket flow"
                
                # CRITICAL COMPARISON: Structure should be identical
                
                # Object type consistency
                assert websocket_user_message.object == reference_message.object, \
                    f"SSOT VIOLATION: WebSocket message object '{websocket_user_message.object}' != SSOT reference '{reference_message.object}'"
                
                # Content structure consistency
                assert type(websocket_user_message.content) == type(reference_message.content), \
                    f"SSOT VIOLATION: WebSocket content type {type(websocket_user_message.content)} != SSOT reference {type(reference_message.content)}"
                
                # Content format validation (SSOT should use list with text objects)
                if isinstance(reference_message.content, list) and len(reference_message.content) > 0:
                    ref_content_structure = reference_message.content[0]
                    ws_content_structure = websocket_user_message.content[0] if isinstance(websocket_user_message.content, list) and len(websocket_user_message.content) > 0 else {}
                    
                    assert ref_content_structure.get("type") == ws_content_structure.get("type"), \
                        f"SSOT VIOLATION: Content structure differs - SSOT: {ref_content_structure}, WebSocket: {ws_content_structure}"
                
                # Metadata handling consistency
                assert type(websocket_user_message.metadata_) == type(reference_message.metadata_), \
                    f"SSOT VIOLATION: Metadata type differs - WebSocket: {type(websocket_user_message.metadata_)}, SSOT: {type(reference_message.metadata_)}"
                    
        logger.info("E2E WebSocket Message Creation SSOT Test Completed")
        
    @pytest.mark.asyncio
    async def test_ssot_agent_execution_message_flow_e2e(self):
        """
        CRITICAL E2E TEST: Validate SSOT compliance in agent-generated messages.
        
        This test simulates agent execution creating messages and validates
        the agent message creation follows SSOT patterns.
        """
        logger.info("=== E2E Agent Execution Message Flow SSOT Test ===")
        
        websocket_url = f"{self.auth_config.websocket_url}?token={self.auth_result.access_token}"
        
        async with websockets.connect(websocket_url) as websocket:
            # 1. Send agent execution request
            agent_request = {
                "type": "agent_request",
                "agent_type": "data_analysis",
                "content": "Analyze SSOT compliance patterns",
                "session_id": self.test_session_id,
                "metadata": {
                    "test_type": "e2e_agent_ssot",
                    "user_id": self.test_user_id
                }
            }
            
            await websocket.send(json.dumps(agent_request))
            logger.info("Agent execution request sent")
            
            # 2. Monitor agent execution and collect responses
            agent_messages = []
            execution_timeout = 60  # 60 seconds for agent execution
            start_time = time.time()
            
            while (time.time() - start_time) < execution_timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    
                    # Collect agent-related messages
                    if response_data.get("type") in [
                        "agent_started", "agent_thinking", "tool_executing", 
                        "tool_completed", "agent_completed", "agent_response"
                    ]:
                        agent_messages.append(response_data)
                        logger.info(f"Agent event: {response_data.get('type')}")
                        
                        # Break when agent completes
                        if response_data.get("type") == "agent_completed":
                            break
                            
                except asyncio.TimeoutError:
                    logger.info("Waiting for agent execution...")
                    continue
                except Exception as e:
                    logger.error(f"Agent execution error: {e}")
                    break
                    
            assert len(agent_messages) > 0, "No agent messages received during execution"
            
            # Find thread_id from agent messages
            thread_id = None
            for msg in agent_messages:
                if msg.get("thread_id"):
                    thread_id = msg["thread_id"]
                    break
                    
            assert thread_id, "No thread_id found in agent messages"
            
            # 3. Validate agent-created messages in database
            async with self.db_helper.get_async_session() as session:
                # Get all messages created during agent execution
                agent_db_messages_result = await session.execute(
                    select(Message)
                    .where(Message.thread_id == thread_id)
                    .where(Message.role == "assistant")
                    .order_by(Message.created_at)
                )
                agent_db_messages = agent_db_messages_result.scalars().all()
                
                assert len(agent_db_messages) > 0, "No assistant messages created during agent execution"
                
                # 4. Create reference agent message using SSOT repository
                reference_agent_message = await self.message_repository.create_message(
                    db=session,
                    thread_id=thread_id,
                    role="assistant",
                    content="SSOT reference agent response",
                    assistant_id="test_agent",
                    metadata={"source": "ssot_reference_agent"}
                )
                await session.commit()
                
                # 5. CRITICAL SSOT VALIDATION: Compare agent messages
                for agent_msg in agent_db_messages:
                    # Object type consistency
                    assert agent_msg.object == reference_agent_message.object, \
                        f"SSOT VIOLATION: Agent message object '{agent_msg.object}' != SSOT reference '{reference_agent_message.object}'"
                    
                    # Content structure consistency
                    assert type(agent_msg.content) == type(reference_agent_message.content), \
                        f"SSOT VIOLATION: Agent content type {type(agent_msg.content)} != SSOT reference {type(reference_agent_message.content)}"
                    
                    # Required fields validation
                    required_fields = ["id", "object", "created_at", "thread_id", "role", "content"]
                    for field in required_fields:
                        agent_value = getattr(agent_msg, field, None)
                        reference_value = getattr(reference_agent_message, field, None)
                        
                        assert type(agent_value) == type(reference_value), \
                            f"SSOT VIOLATION: Agent message field '{field}' type differs - Agent: {type(agent_value)}, SSOT: {type(reference_value)}"
                            
        logger.info("E2E Agent Execution Message Flow SSOT Test Completed")
        
    @pytest.mark.asyncio
    async def test_ssot_multi_user_message_isolation_e2e(self):
        """
        E2E TEST: Validate SSOT compliance across multiple users.
        
        This test ensures SSOT message creation maintains proper isolation
        and consistency across multiple authenticated users.
        """
        logger.info("=== E2E Multi-User Message Isolation SSOT Test ===")
        
        # Create second user for isolation testing
        user2_id = f"e2e_user2_{uuid.uuid4().hex[:8]}"
        auth_result2 = await self.auth_helper.authenticate_e2e_user(
            user_id=user2_id,
            config=self.auth_config
        )
        
        assert auth_result2.is_success, f"Second user authentication failed: {auth_result2.error_message}"
        
        try:
            # Connect both users via WebSocket
            websocket_url1 = f"{self.auth_config.websocket_url}?token={self.auth_result.access_token}"
            websocket_url2 = f"{self.auth_config.websocket_url}?token={auth_result2.access_token}"
            
            async with websockets.connect(websocket_url1) as ws1, \
                       websockets.connect(websocket_url2) as ws2:
                
                # Both users send messages simultaneously
                user1_message = {
                    "type": "user_message",
                    "content": "User 1 SSOT isolation test",
                    "session_id": f"session1_{uuid.uuid4().hex[:8]}",
                    "metadata": {"user_id": self.test_user_id}
                }
                
                user2_message = {
                    "type": "user_message", 
                    "content": "User 2 SSOT isolation test",
                    "session_id": f"session2_{uuid.uuid4().hex[:8]}",
                    "metadata": {"user_id": user2_id}
                }
                
                # Send messages concurrently
                await asyncio.gather(
                    ws1.send(json.dumps(user1_message)),
                    ws2.send(json.dumps(user2_message))
                )
                
                # Collect responses
                user1_thread_id = None
                user2_thread_id = None
                
                timeout = 30
                start_time = time.time()
                
                while (not user1_thread_id or not user2_thread_id) and (time.time() - start_time) < timeout:
                    try:
                        # Check user 1 responses
                        if not user1_thread_id:
                            try:
                                response1 = await asyncio.wait_for(ws1.recv(), timeout=2.0)
                                data1 = json.loads(response1)
                                if data1.get("thread_id"):
                                    user1_thread_id = data1["thread_id"]
                            except asyncio.TimeoutError:
                                pass
                        
                        # Check user 2 responses
                        if not user2_thread_id:
                            try:
                                response2 = await asyncio.wait_for(ws2.recv(), timeout=2.0)
                                data2 = json.loads(response2)
                                if data2.get("thread_id"):
                                    user2_thread_id = data2["thread_id"]
                            except asyncio.TimeoutError:
                                pass
                                
                    except Exception as e:
                        logger.warning(f"Multi-user response error: {e}")
                        continue
                        
                assert user1_thread_id, "User 1 did not receive thread_id"
                assert user2_thread_id, "User 2 did not receive thread_id"
                assert user1_thread_id != user2_thread_id, "Thread IDs should be different for different users"
                
                # Validate SSOT compliance for both users
                async with self.db_helper.get_async_session() as session:
                    # Get messages for both users
                    user1_messages_result = await session.execute(
                        select(Message).where(Message.thread_id == user1_thread_id)
                    )
                    user1_messages = user1_messages_result.scalars().all()
                    
                    user2_messages_result = await session.execute(
                        select(Message).where(Message.thread_id == user2_thread_id)
                    )
                    user2_messages = user2_messages_result.scalars().all()
                    
                    assert len(user1_messages) > 0, "User 1 should have messages"
                    assert len(user2_messages) > 0, "User 2 should have messages"
                    
                    # CRITICAL: Both users' messages should follow SSOT structure
                    for msg in user1_messages + user2_messages:
                        assert msg.object == "thread.message", f"Message {msg.id} should have SSOT object type"
                        assert isinstance(msg.content, list), f"Message {msg.id} should have SSOT content structure"
                        assert isinstance(msg.metadata_, dict), f"Message {msg.id} should have SSOT metadata structure"
                        
        finally:
            # Cleanup second user data
            try:
                async with self.db_helper.get_async_session() as session:
                    await session.execute(
                        text("DELETE FROM message WHERE thread_id IN (SELECT id FROM thread WHERE metadata_->>'user_id' = :user_id)"),
                        {"user_id": user2_id}
                    )
                    await session.execute(
                        text("DELETE FROM thread WHERE metadata_->>'user_id' = :user_id"),
                        {"user_id": user2_id}
                    )
                    await session.commit()
            except Exception as e:
                logger.warning(f"User 2 cleanup warning: {e}")
                
        logger.info("E2E Multi-User Message Isolation SSOT Test Completed")


if __name__ == "__main__":
    # Run the E2E test suite
    import sys
    import os
    
    # Add project root to path for imports
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    sys.path.insert(0, project_root)
    
    # Configure logging for test execution
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run E2E tests with real services and authentication
    pytest.main([__file__, "-v", "-s", "--tb=short", "-k", "e2e"])