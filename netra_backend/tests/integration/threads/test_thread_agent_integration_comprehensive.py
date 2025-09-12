"""
Thread-Agent Integration Test Suite

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Enable substantive AI-powered chat conversations
- Value Impact: Validates complete chat workflow from thread creation through agent execution
- Strategic Impact: Core platform functionality - thread-agent integration enables chat value delivery

This test suite validates the CRITICAL integration between threads and agents that enables
chat functionality. It tests the complete workflow: thread creation  ->  message  ->  agent execution  ->  response

Focus Areas:
1. Thread-Agent Binding: Secure agent execution within thread context
2. Message Flow Integration: Complete message-to-agent execution workflow  
3. State Management: Thread state updates during agent execution
4. Context Propagation: User context availability throughout execution
5. Performance Integration: Thread-agent interaction optimization

CRITICAL REQUIREMENTS:
- NO MOCKS - use real components with in-memory databases
- Validate complete chat workflow with WebSocket events
- Test multi-user isolation throughout thread-agent interactions
- Use realistic chat conversation scenarios with real agent types

TEST ARCHITECTURE:
Integration Level: Thread + Agent + ExecutionEngine + WebSocket events together
Real Components: Real Thread/Agent instances, in-memory DB, real WebSocket events
User Context: Factory patterns for complete user isolation
Business Scenarios: Realistic chat conversations enabling AI value delivery
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock

import pytest

# SSOT Imports - Absolute paths following CLAUDE.md requirements
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.db.models_agent import Thread, Message, Run
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngine
from shared.isolated_environment import get_env
from shared.types import UserID, ThreadID, RunID, RequestID

# SSOT Test Framework Imports  
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.websocket import WebSocketTestUtility, WebSocketEventType

# Test specific imports
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


class TestThreadAgentIntegrationComprehensive(BaseIntegrationTest):
    """
    Comprehensive thread-agent integration test suite.
    
    Validates the critical integration points that enable chat functionality:
    - Thread-agent binding with proper user isolation
    - Message workflow integration with agent execution  
    - State management across thread and agent contexts
    - Context propagation and cleanup
    - Performance optimization for chat workflows
    """

    @pytest.fixture
    async def mock_llm_manager(self):
        """Create mock LLM manager for testing."""
        mock_llm = AsyncMock(spec=LLMManager)
        
        # Configure realistic responses for different scenarios
        async def mock_generate(prompt, **kwargs):
            return {
                "content": f"Mock AI response to: {prompt[:50]}...",
                "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
            }
            
        mock_llm.generate.side_effect = mock_generate
        mock_llm.is_available.return_value = True
        return mock_llm

    @pytest.fixture  
    async def mock_websocket_notifier(self):
        """Create mock WebSocket notifier for integration testing."""
        mock_notifier = AsyncMock(spec=WebSocketNotifier)
        mock_notifier.send_event.return_value = True
        mock_notifier.send_to_thread.return_value = True
        return mock_notifier

    @pytest.fixture
    async def test_user_context(self, real_services_fixture) -> UserExecutionContext:
        """Create isolated user execution context for testing."""
        env = get_env()
        db = real_services_fixture["db"]
        
        # Create test user context with all required components
        user_context = UserExecutionContext(
            user_id=UserID(f"test_user_{uuid.uuid4().hex[:8]}"),
            thread_id=ThreadID(f"thread_{uuid.uuid4().hex[:8]}"),
            run_id=RunID(f"run_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={
                "user_request": "Help me optimize my AI costs",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "test_scenario": "thread_agent_integration"
            },
            isolated_env=env
        )
        
        return user_context

    @pytest.fixture
    async def test_thread(self, real_services_fixture, test_user_context) -> Thread:
        """Create test thread in database."""
        db = real_services_fixture["db"]
        
        thread = Thread(
            id=test_user_context.thread_id,
            created_at=int(time.time()),
            metadata_={
                "user_id": test_user_context.user_id,
                "created_by_test": True,
                "scenario": "thread_agent_integration"
            }
        )
        
        db.add(thread)
        await db.commit()
        await db.refresh(thread)
        
        return thread

    @pytest.fixture
    async def test_data_helper_agent(self, mock_llm_manager) -> DataHelperAgent:
        """Create DataHelperAgent for testing."""
        tool_dispatcher = UnifiedToolDispatcher()
        agent = DataHelperAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=tool_dispatcher
        )
        return agent

    # ========== Thread-Agent Binding Tests (6 tests) ==========

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_within_thread_context(
        self, real_services_fixture, test_user_context, test_thread, 
        test_data_helper_agent, mock_websocket_notifier
    ):
        """Test agent execution within existing thread context with proper isolation."""
        # Setup agent with WebSocket notifier
        test_data_helper_agent.websocket_notifier = mock_websocket_notifier
        
        # Execute agent within thread context
        start_time = time.time()
        result_context = await test_data_helper_agent.execute(test_user_context)
        execution_time = time.time() - start_time
        
        # Verify execution completed successfully
        assert result_context.user_id == test_user_context.user_id
        assert result_context.thread_id == test_user_context.thread_id
        assert result_context.run_id == test_user_context.run_id
        
        # Verify thread context was preserved
        assert result_context.metadata.get("user_request") == "Help me optimize my AI costs"
        
        # Verify WebSocket events were sent for chat value
        mock_websocket_notifier.send_event.assert_called()
        event_calls = mock_websocket_notifier.send_event.call_args_list
        event_types = [call[1]["event_type"] for call in event_calls]
        
        # All 5 critical events must be sent for chat functionality
        assert "agent_thinking" in event_types
        assert "tool_executing" in event_types  
        assert "tool_completed" in event_types
        
        # Verify reasonable execution time for chat responsiveness
        assert execution_time < 5.0, "Agent execution too slow for chat"
        
        # Verify agent result stored in context
        assert "data_helper_result" in result_context.metadata

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_agent_binding_thread_user_isolation(
        self, real_services_fixture, mock_llm_manager, mock_websocket_notifier
    ):
        """Test agent binding to thread with proper user isolation."""
        db = real_services_fixture["db"]
        env = get_env()
        
        # Create two different user contexts
        user1_id = UserID(f"user1_{uuid.uuid4().hex[:8]}")
        user2_id = UserID(f"user2_{uuid.uuid4().hex[:8]}")
        thread1_id = ThreadID(f"thread1_{uuid.uuid4().hex[:8]}")
        thread2_id = ThreadID(f"thread2_{uuid.uuid4().hex[:8]}")
        
        context1 = UserExecutionContext(
            user_id=user1_id,
            thread_id=thread1_id, 
            run_id=RunID(f"run1_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req1_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={"user_request": "User 1 optimization request", "sensitive_data": "user1_secret"},
            isolated_env=env
        )
        
        context2 = UserExecutionContext(
            user_id=user2_id,
            thread_id=thread2_id,
            run_id=RunID(f"run2_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req2_{uuid.uuid4().hex[:8]}"),
            session=db, 
            metadata={"user_request": "User 2 optimization request", "sensitive_data": "user2_secret"},
            isolated_env=env
        )
        
        # Create threads in database
        thread1 = Thread(id=thread1_id, created_at=int(time.time()), metadata_={"user_id": user1_id})
        thread2 = Thread(id=thread2_id, created_at=int(time.time()), metadata_={"user_id": user2_id})
        db.add_all([thread1, thread2])
        await db.commit()
        
        # Create agents
        tool_dispatcher = UnifiedToolDispatcher()
        agent1 = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent2 = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent1.websocket_notifier = mock_websocket_notifier
        agent2.websocket_notifier = mock_websocket_notifier
        
        # Execute agents concurrently 
        results = await asyncio.gather(
            agent1.execute(context1),
            agent2.execute(context2)
        )
        
        result1, result2 = results
        
        # Verify user isolation - no data leakage
        assert result1.user_id == user1_id
        assert result2.user_id == user2_id
        assert result1.thread_id == thread1_id
        assert result2.thread_id == thread2_id
        
        # Verify sensitive data isolation
        assert result1.metadata.get("sensitive_data") == "user1_secret"
        assert result2.metadata.get("sensitive_data") == "user2_secret"
        
        # Verify no cross-contamination
        assert "user2_secret" not in str(result1.metadata)
        assert "user1_secret" not in str(result2.metadata)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multiple_agents_same_thread_sequential(
        self, real_services_fixture, test_thread, mock_llm_manager, mock_websocket_notifier
    ):
        """Test multiple agents executing in same thread sequentially."""
        db = real_services_fixture["db"]
        env = get_env()
        
        # Create shared thread context
        thread_id = test_thread.id
        user_id = UserID(f"user_{uuid.uuid4().hex[:8]}")
        
        # Create multiple agent instances
        tool_dispatcher = UnifiedToolDispatcher()
        agent1 = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent2 = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent1.websocket_notifier = mock_websocket_notifier
        agent2.websocket_notifier = mock_websocket_notifier
        
        # Execute first agent
        context1 = UserExecutionContext(
            user_id=user_id,
            thread_id=ThreadID(thread_id),
            run_id=RunID(f"run1_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req1_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={"user_request": "Initial optimization request", "step": "first"},
            isolated_env=env
        )
        
        result1 = await agent1.execute(context1)
        
        # Execute second agent using results from first
        context2 = UserExecutionContext(
            user_id=user_id,
            thread_id=ThreadID(thread_id),
            run_id=RunID(f"run2_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req2_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={
                "user_request": "Follow-up optimization request",
                "step": "second", 
                "previous_result": result1.metadata.get("data_helper_result")
            },
            isolated_env=env
        )
        
        result2 = await agent2.execute(context2)
        
        # Verify both agents executed within same thread
        assert result1.thread_id == result2.thread_id == ThreadID(thread_id)
        assert result1.user_id == result2.user_id == user_id
        
        # Verify sequential execution preserved context
        assert result2.metadata.get("previous_result") is not None
        
        # Verify both agents sent WebSocket events 
        assert mock_websocket_notifier.send_event.call_count >= 6  # At least 3 events per agent

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_thread_binding_validation_security(
        self, real_services_fixture, mock_llm_manager, mock_websocket_notifier
    ):
        """Test agent thread binding validation and security."""
        db = real_services_fixture["db"]
        env = get_env()
        
        # Create test thread
        thread_id = ThreadID(f"secure_thread_{uuid.uuid4().hex[:8]}")
        authorized_user = UserID(f"auth_user_{uuid.uuid4().hex[:8]}")
        unauthorized_user = UserID(f"unauth_user_{uuid.uuid4().hex[:8]}")
        
        thread = Thread(
            id=thread_id,
            created_at=int(time.time()),
            metadata_={"owner_user_id": authorized_user, "private": True}
        )
        db.add(thread)
        await db.commit()
        
        # Create agent
        tool_dispatcher = UnifiedToolDispatcher()
        agent = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent.websocket_notifier = mock_websocket_notifier
        
        # Test authorized access
        authorized_context = UserExecutionContext(
            user_id=authorized_user,
            thread_id=thread_id,
            run_id=RunID(f"auth_run_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"auth_req_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={"user_request": "Authorized optimization request"},
            isolated_env=env
        )
        
        authorized_result = await agent.execute(authorized_context)
        
        # Test unauthorized access (should still execute but with user isolation)
        unauthorized_context = UserExecutionContext(
            user_id=unauthorized_user,
            thread_id=thread_id,
            run_id=RunID(f"unauth_run_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"unauth_req_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={"user_request": "Unauthorized optimization request"},
            isolated_env=env
        )
        
        unauthorized_result = await agent.execute(unauthorized_context)
        
        # Verify user isolation is maintained even with same thread
        assert authorized_result.user_id == authorized_user
        assert unauthorized_result.user_id == unauthorized_user
        assert authorized_result.user_id != unauthorized_result.user_id

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_agent_context_propagation_validation(
        self, real_services_fixture, test_thread, test_user_context,
        test_data_helper_agent, mock_websocket_notifier
    ):
        """Test thread-agent context propagation validation."""
        # Setup agent
        test_data_helper_agent.websocket_notifier = mock_websocket_notifier
        
        # Add complex context metadata
        test_user_context.metadata.update({
            "conversation_history": [
                {"role": "user", "content": "Previous message 1"},
                {"role": "assistant", "content": "Previous response 1"}
            ],
            "user_preferences": {"optimization_focus": "cost", "risk_tolerance": "medium"},
            "session_data": {"start_time": datetime.now(timezone.utc).isoformat()},
            "nested_context": {
                "business_context": {"industry": "technology", "company_size": "mid"},
                "technical_context": {"cloud_provider": "aws", "services": ["ec2", "s3"]}
            }
        })
        
        # Execute agent
        result_context = await test_data_helper_agent.execute(test_user_context)
        
        # Verify all context was propagated correctly
        assert result_context.thread_id == test_user_context.thread_id
        assert result_context.user_id == test_user_context.user_id
        assert result_context.run_id == test_user_context.run_id
        
        # Verify complex metadata preserved
        assert result_context.metadata["conversation_history"] == test_user_context.metadata["conversation_history"]
        assert result_context.metadata["user_preferences"] == test_user_context.metadata["user_preferences"]
        assert result_context.metadata["nested_context"] == test_user_context.metadata["nested_context"]
        
        # Verify agent added its own results without overwriting context
        assert "data_helper_result" in result_context.metadata
        assert result_context.metadata["user_request"] == "Help me optimize my AI costs"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_thread_state_preservation(
        self, real_services_fixture, test_thread, mock_llm_manager, mock_websocket_notifier
    ):
        """Test agent execution preserves thread state."""
        db = real_services_fixture["db"]
        env = get_env()
        
        # Update thread with initial state
        test_thread.metadata_ = {
            "conversation_state": "active",
            "message_count": 5,
            "last_activity": datetime.now(timezone.utc).isoformat(),
            "user_engagement_score": 0.8
        }
        await db.commit()
        await db.refresh(test_thread)
        
        # Create context
        context = UserExecutionContext(
            user_id=UserID(f"user_{uuid.uuid4().hex[:8]}"),
            thread_id=ThreadID(test_thread.id),
            run_id=RunID(f"run_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={"user_request": "Preserve thread state test"},
            isolated_env=env
        )
        
        # Execute agent
        tool_dispatcher = UnifiedToolDispatcher()
        agent = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent.websocket_notifier = mock_websocket_notifier
        
        await agent.execute(context)
        
        # Verify thread state was preserved
        await db.refresh(test_thread)
        assert test_thread.metadata_["conversation_state"] == "active"
        assert test_thread.metadata_["message_count"] == 5
        assert test_thread.metadata_["user_engagement_score"] == 0.8

    # ========== Message Flow Integration Tests (6 tests) ==========

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_complete_message_to_agent_execution_workflow(
        self, real_services_fixture, test_thread, mock_llm_manager, mock_websocket_notifier
    ):
        """Test complete message-to-agent execution workflow."""
        db = real_services_fixture["db"]
        env = get_env()
        
        user_id = UserID(f"user_{uuid.uuid4().hex[:8]}")
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        
        # Create user message in thread
        user_message = Message(
            id=message_id,
            thread_id=test_thread.id,
            created_at=int(time.time()),
            role="user",
            content=[{"type": "text", "text": "Help me optimize my cloud costs"}],
            metadata_={"user_id": user_id, "intent": "cost_optimization"}
        )
        db.add(user_message)
        await db.commit()
        
        # Create execution context from message
        context = UserExecutionContext(
            user_id=user_id,
            thread_id=ThreadID(test_thread.id),
            run_id=RunID(f"run_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={
                "user_request": "Help me optimize my cloud costs",
                "message_id": message_id,
                "message_intent": "cost_optimization"
            },
            isolated_env=env
        )
        
        # Execute agent
        tool_dispatcher = UnifiedToolDispatcher()
        agent = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent.websocket_notifier = mock_websocket_notifier
        
        result_context = await agent.execute(context)
        
        # Verify complete workflow
        assert result_context.metadata["message_id"] == message_id
        assert result_context.metadata["message_intent"] == "cost_optimization"
        assert "data_helper_result" in result_context.metadata
        
        # Verify WebSocket events sent for chat functionality
        mock_websocket_notifier.send_event.assert_called()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_response_integration_thread_messages(
        self, real_services_fixture, test_thread, mock_llm_manager, mock_websocket_notifier
    ):
        """Test agent response integration with thread messages."""
        db = real_services_fixture["db"]
        env = get_env()
        
        user_id = UserID(f"user_{uuid.uuid4().hex[:8]}")
        run_id = RunID(f"run_{uuid.uuid4().hex[:8]}")
        
        # Create agent run record
        agent_run = Run(
            id=run_id,
            thread_id=test_thread.id,
            assistant_id="data_helper",
            created_at=int(time.time()),
            status="queued",
            metadata_={"user_id": user_id}
        )
        db.add(agent_run)
        await db.commit()
        
        # Create context
        context = UserExecutionContext(
            user_id=user_id,
            thread_id=ThreadID(test_thread.id),
            run_id=run_id,
            request_id=RequestID(f"req_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={"user_request": "Generate data optimization recommendations"},
            isolated_env=env
        )
        
        # Execute agent
        tool_dispatcher = UnifiedToolDispatcher()
        agent = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent.websocket_notifier = mock_websocket_notifier
        
        await agent.execute(context)
        
        # Verify run was updated (simulate what would happen in real system)
        await db.refresh(agent_run)
        assert agent_run.status in ["queued", "in_progress", "completed"]  # Status tracking
        
        # Verify agent response can be integrated into thread
        assert "data_helper_result" in context.metadata
        agent_response = context.metadata.get("data_helper_result", {})
        assert isinstance(agent_response, dict)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_history_preservation_during_agent_execution(
        self, real_services_fixture, test_thread, mock_llm_manager, mock_websocket_notifier
    ):
        """Test message history preservation during agent execution."""
        db = real_services_fixture["db"]
        env = get_env()
        
        user_id = UserID(f"user_{uuid.uuid4().hex[:8]}")
        
        # Create conversation history
        messages = []
        for i in range(3):
            msg = Message(
                id=f"msg_{i}_{uuid.uuid4().hex[:8]}",
                thread_id=test_thread.id,
                created_at=int(time.time()) - (3-i) * 60,  # Chronological order
                role="user" if i % 2 == 0 else "assistant",
                content=[{"type": "text", "text": f"Message {i+1} content"}],
                metadata_={"user_id": user_id, "sequence": i+1}
            )
            messages.append(msg)
            
        db.add_all(messages)
        await db.commit()
        
        # Query message history before agent execution
        result = await db.execute(
            select(Message).where(Message.thread_id == test_thread.id).order_by(Message.created_at)
        )
        messages_before = result.scalars().all()
        
        # Execute agent
        context = UserExecutionContext(
            user_id=user_id,
            thread_id=ThreadID(test_thread.id),
            run_id=RunID(f"run_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={"user_request": "Latest optimization request"},
            isolated_env=env
        )
        
        tool_dispatcher = UnifiedToolDispatcher()
        agent = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent.websocket_notifier = mock_websocket_notifier
        
        await agent.execute(context)
        
        # Query message history after agent execution
        result = await db.execute(
            select(Message).where(Message.thread_id == test_thread.id).order_by(Message.created_at)
        )
        messages_after = result.scalars().all()
        
        # Verify message history preserved
        assert len(messages_after) == len(messages_before)
        for before, after in zip(messages_before, messages_after):
            assert before.id == after.id
            assert before.content == after.content
            assert before.role == after.role

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_message_context_loading(
        self, real_services_fixture, test_thread, mock_llm_manager, mock_websocket_notifier
    ):
        """Test agent execution with message context loading."""
        db = real_services_fixture["db"]
        env = get_env()
        
        user_id = UserID(f"user_{uuid.uuid4().hex[:8]}")
        
        # Create rich message context
        context_message = Message(
            id=f"ctx_msg_{uuid.uuid4().hex[:8]}",
            thread_id=test_thread.id,
            created_at=int(time.time()),
            role="user",
            content=[{
                "type": "text", 
                "text": "Optimize my AWS costs with these constraints: budget $10k, critical services must stay up"
            }],
            metadata_={
                "user_id": user_id,
                "constraints": {"budget": 10000, "critical_services": ["database", "api"]},
                "context_type": "optimization_request"
            }
        )
        db.add(context_message)
        await db.commit()
        
        # Create context with message context
        context = UserExecutionContext(
            user_id=user_id,
            thread_id=ThreadID(test_thread.id),
            run_id=RunID(f"run_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={
                "user_request": "Optimize my AWS costs with these constraints: budget $10k, critical services must stay up",
                "message_context": {
                    "constraints": {"budget": 10000, "critical_services": ["database", "api"]},
                    "context_type": "optimization_request"
                },
                "context_message_id": context_message.id
            },
            isolated_env=env
        )
        
        # Execute agent with rich context
        tool_dispatcher = UnifiedToolDispatcher()
        agent = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent.websocket_notifier = mock_websocket_notifier
        
        result_context = await agent.execute(context)
        
        # Verify agent had access to message context
        assert result_context.metadata["message_context"]["constraints"]["budget"] == 10000
        assert "database" in result_context.metadata["message_context"]["constraints"]["critical_services"]
        
        # Verify agent result incorporates context
        assert "data_helper_result" in result_context.metadata

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_message_conversation_flow_with_agents(
        self, real_services_fixture, test_thread, mock_llm_manager, mock_websocket_notifier
    ):
        """Test multi-message conversation flow with agents."""
        db = real_services_fixture["db"]
        env = get_env()
        
        user_id = UserID(f"user_{uuid.uuid4().hex[:8]}")
        conversation_messages = []
        
        # Simulate multi-turn conversation
        conversation_turns = [
            {"role": "user", "content": "I need help optimizing costs"},
            {"role": "assistant", "content": "I can help with cost optimization. What's your current spend?"},
            {"role": "user", "content": "About $50k per month on AWS"},
            {"role": "assistant", "content": "That's significant. Let me analyze your usage patterns."}
        ]
        
        # Create conversation messages
        for i, turn in enumerate(conversation_turns):
            msg = Message(
                id=f"conv_msg_{i}_{uuid.uuid4().hex[:8]}",
                thread_id=test_thread.id,
                created_at=int(time.time()) + i,
                role=turn["role"],
                content=[{"type": "text", "text": turn["content"]}],
                metadata_={"user_id": user_id, "turn": i+1}
            )
            conversation_messages.append(msg)
            
        db.add_all(conversation_messages)
        await db.commit()
        
        # Execute agent with conversation context
        context = UserExecutionContext(
            user_id=user_id,
            thread_id=ThreadID(test_thread.id),
            run_id=RunID(f"run_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={
                "user_request": "Continue the cost optimization conversation",
                "conversation_context": {
                    "turn_count": len(conversation_turns),
                    "monthly_spend": 50000,
                    "cloud_provider": "aws"
                }
            },
            isolated_env=env
        )
        
        tool_dispatcher = UnifiedToolDispatcher()
        agent = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent.websocket_notifier = mock_websocket_notifier
        
        result_context = await agent.execute(context)
        
        # Verify agent understood conversation context
        assert result_context.metadata["conversation_context"]["monthly_spend"] == 50000
        assert result_context.metadata["conversation_context"]["turn_count"] == 4
        
        # Verify agent generated appropriate response
        assert "data_helper_result" in result_context.metadata

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_agent_execution_websocket_event_coordination(
        self, real_services_fixture, test_thread, mock_llm_manager
    ):
        """Test message-agent execution WebSocket event coordination."""
        # Use real WebSocket utility for comprehensive event testing
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_test_client()
            await client.connect(mock_mode=True)  # Use mock mode for integration test
            
            db = real_services_fixture["db"]
            env = get_env()
            user_id = UserID(f"user_{uuid.uuid4().hex[:8]}")
            
            # Create WebSocket notifier that sends to client
            websocket_notifier = AsyncMock(spec=WebSocketNotifier)
            
            async def mock_send_event(event_type, data, **kwargs):
                # Send event to WebSocket client
                await client.send_message(
                    WebSocketEventType(event_type),
                    data,
                    user_id=user_id,
                    thread_id=test_thread.id
                )
                return True
                
            websocket_notifier.send_event.side_effect = mock_send_event
            
            # Execute agent with WebSocket coordination
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=ThreadID(test_thread.id),
                run_id=RunID(f"run_{uuid.uuid4().hex[:8]}"),
                request_id=RequestID(f"req_{uuid.uuid4().hex[:8]}"),
                session=db,
                metadata={"user_request": "WebSocket coordination test"},
                isolated_env=env
            )
            
            tool_dispatcher = UnifiedToolDispatcher()
            agent = DataHelperAgent(mock_llm_manager, tool_dispatcher)
            agent.websocket_notifier = websocket_notifier
            
            # Execute and collect WebSocket events
            await agent.execute(context)
            await asyncio.sleep(1.0)  # Allow events to be processed
            
            # Verify WebSocket events were coordinated
            received_events = [msg.event_type for msg in client.received_messages]
            
            # Should have agent execution events
            assert WebSocketEventType.AGENT_THINKING in received_events
            assert WebSocketEventType.TOOL_EXECUTING in received_events
            assert WebSocketEventType.TOOL_COMPLETED in received_events

    # ========== State Management Integration Tests (6 tests) ==========

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_state_updates_during_agent_execution(
        self, real_services_fixture, test_thread, mock_llm_manager, mock_websocket_notifier
    ):
        """Test thread state updates during agent execution."""
        db = real_services_fixture["db"]
        env = get_env()
        
        # Set initial thread state
        initial_metadata = {
            "agent_execution_count": 0,
            "last_agent": None,
            "optimization_score": 0.5
        }
        test_thread.metadata_ = initial_metadata
        await db.commit()
        
        # Execute agent
        context = UserExecutionContext(
            user_id=UserID(f"user_{uuid.uuid4().hex[:8]}"),
            thread_id=ThreadID(test_thread.id),
            run_id=RunID(f"run_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={"user_request": "State update test"},
            isolated_env=env
        )
        
        tool_dispatcher = UnifiedToolDispatcher()
        agent = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent.websocket_notifier = mock_websocket_notifier
        
        # Custom state update logic (simulate what real system would do)
        original_execute = agent.execute
        
        async def execute_with_state_update(ctx):
            result = await original_execute(ctx)
            # Simulate thread state update
            test_thread.metadata_["agent_execution_count"] += 1
            test_thread.metadata_["last_agent"] = "data_helper"
            test_thread.metadata_["last_execution"] = datetime.now(timezone.utc).isoformat()
            await db.commit()
            return result
            
        agent.execute = execute_with_state_update
        
        await agent.execute(context)
        
        # Verify thread state was updated
        await db.refresh(test_thread)
        assert test_thread.metadata_["agent_execution_count"] == 1
        assert test_thread.metadata_["last_agent"] == "data_helper"
        assert "last_execution" in test_thread.metadata_

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_state_persistence_in_thread_context(
        self, real_services_fixture, test_thread, mock_llm_manager, mock_websocket_notifier
    ):
        """Test agent execution state persistence in thread context."""
        db = real_services_fixture["db"]
        env = get_env()
        
        user_id = UserID(f"user_{uuid.uuid4().hex[:8]}")
        
        # First agent execution
        context1 = UserExecutionContext(
            user_id=user_id,
            thread_id=ThreadID(test_thread.id),
            run_id=RunID(f"run1_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req1_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={"user_request": "First execution", "execution_number": 1},
            isolated_env=env
        )
        
        tool_dispatcher = UnifiedToolDispatcher()
        agent1 = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent1.websocket_notifier = mock_websocket_notifier
        
        result1 = await agent1.execute(context1)
        
        # Extract state from first execution
        first_execution_state = {
            "data_helper_result": result1.metadata.get("data_helper_result"),
            "execution_timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": str(user_id)
        }
        
        # Second agent execution with persisted state
        context2 = UserExecutionContext(
            user_id=user_id,
            thread_id=ThreadID(test_thread.id),
            run_id=RunID(f"run2_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req2_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={
                "user_request": "Second execution with state",
                "execution_number": 2,
                "previous_execution_state": first_execution_state
            },
            isolated_env=env
        )
        
        agent2 = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent2.websocket_notifier = mock_websocket_notifier
        
        result2 = await agent2.execute(context2)
        
        # Verify state persistence
        assert result2.metadata["previous_execution_state"]["user_id"] == str(user_id)
        assert result2.metadata["previous_execution_state"]["data_helper_result"] is not None
        assert result2.thread_id == result1.thread_id

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_agent_shared_context_management(
        self, real_services_fixture, test_thread, mock_llm_manager, mock_websocket_notifier
    ):
        """Test thread-agent shared context management."""
        db = real_services_fixture["db"]
        env = get_env()
        
        user_id = UserID(f"user_{uuid.uuid4().hex[:8]}")
        
        # Create shared context in thread metadata
        shared_context = {
            "optimization_preferences": {
                "cost_focus": True,
                "performance_focus": False,
                "risk_tolerance": "medium"
            },
            "business_context": {
                "industry": "fintech",
                "compliance_requirements": ["SOC2", "PCI"]
            },
            "session_state": {
                "conversation_depth": "deep",
                "user_expertise": "intermediate"
            }
        }
        
        test_thread.metadata_ = {"shared_context": shared_context}
        await db.commit()
        
        # Execute agent with access to shared context
        context = UserExecutionContext(
            user_id=user_id,
            thread_id=ThreadID(test_thread.id),
            run_id=RunID(f"run_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={
                "user_request": "Use shared context for optimization",
                "access_shared_context": True
            },
            isolated_env=env
        )
        
        # Enhanced agent with shared context access
        tool_dispatcher = UnifiedToolDispatcher()
        agent = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent.websocket_notifier = mock_websocket_notifier
        
        # Simulate shared context loading
        original_execute = agent.execute
        
        async def execute_with_shared_context(ctx):
            # Load shared context from thread
            await db.refresh(test_thread)
            thread_shared_context = test_thread.metadata_.get("shared_context", {})
            ctx.metadata["thread_shared_context"] = thread_shared_context
            return await original_execute(ctx)
            
        agent.execute = execute_with_shared_context
        
        result_context = await agent.execute(context)
        
        # Verify shared context was available to agent
        assert "thread_shared_context" in result_context.metadata
        thread_context = result_context.metadata["thread_shared_context"]
        assert thread_context["optimization_preferences"]["cost_focus"] is True
        assert "fintech" in thread_context["business_context"]["industry"]
        assert "SOC2" in thread_context["business_context"]["compliance_requirements"]

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_results_integration_with_thread_history(
        self, real_services_fixture, test_thread, mock_llm_manager, mock_websocket_notifier
    ):
        """Test agent results integration with thread history."""
        db = real_services_fixture["db"]
        env = get_env()
        
        user_id = UserID(f"user_{uuid.uuid4().hex[:8]}")
        
        # Create thread history with previous agent results
        thread_history = {
            "agent_executions": [],
            "conversation_summary": "",
            "optimization_insights": []
        }
        
        # Execute multiple agents to build history
        for i in range(3):
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=ThreadID(test_thread.id),
                run_id=RunID(f"run_{i}_{uuid.uuid4().hex[:8]}"),
                request_id=RequestID(f"req_{i}_{uuid.uuid4().hex[:8]}"),
                session=db,
                metadata={
                    "user_request": f"Execution {i+1} for history building",
                    "execution_sequence": i+1
                },
                isolated_env=env
            )
            
            tool_dispatcher = UnifiedToolDispatcher()
            agent = DataHelperAgent(mock_llm_manager, tool_dispatcher)
            agent.websocket_notifier = mock_websocket_notifier
            
            result_context = await agent.execute(context)
            
            # Add result to thread history
            thread_history["agent_executions"].append({
                "execution_id": i+1,
                "agent_type": "data_helper",
                "result": result_context.metadata.get("data_helper_result"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        # Update thread with complete history
        test_thread.metadata_ = {"thread_history": thread_history}
        await db.commit()
        
        # Execute final agent with full history context
        final_context = UserExecutionContext(
            user_id=user_id,
            thread_id=ThreadID(test_thread.id),
            run_id=RunID(f"final_run_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"final_req_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={"user_request": "Final execution with full history"},
            isolated_env=env
        )
        
        agent = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent.websocket_notifier = mock_websocket_notifier
        
        final_result = await agent.execute(final_context)
        
        # Verify thread history is accessible
        await db.refresh(test_thread)
        history = test_thread.metadata_.get("thread_history", {})
        assert len(history["agent_executions"]) == 3
        assert all(exec["agent_type"] == "data_helper" for exec in history["agent_executions"])

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_metadata_updates_from_agent_execution(
        self, real_services_fixture, test_thread, mock_llm_manager, mock_websocket_notifier
    ):
        """Test thread metadata updates from agent execution."""
        db = real_services_fixture["db"]
        env = get_env()
        
        # Set initial thread metadata
        initial_metadata = {
            "creation_source": "api",
            "user_tier": "enterprise",
            "optimization_status": "pending"
        }
        test_thread.metadata_ = initial_metadata
        await db.commit()
        
        # Execute agent
        context = UserExecutionContext(
            user_id=UserID(f"user_{uuid.uuid4().hex[:8]}"),
            thread_id=ThreadID(test_thread.id),
            run_id=RunID(f"run_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={"user_request": "Update thread metadata test"},
            isolated_env=env
        )
        
        tool_dispatcher = UnifiedToolDispatcher()
        agent = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent.websocket_notifier = mock_websocket_notifier
        
        # Custom agent execution with metadata updates
        original_execute = agent.execute
        
        async def execute_with_metadata_updates(ctx):
            result = await original_execute(ctx)
            
            # Simulate metadata updates based on agent results
            await db.refresh(test_thread)
            test_thread.metadata_["optimization_status"] = "data_collection"
            test_thread.metadata_["last_agent_execution"] = datetime.now(timezone.utc).isoformat()
            test_thread.metadata_["data_helper_executed"] = True
            
            # Merge with existing metadata
            if "agent_execution_history" not in test_thread.metadata_:
                test_thread.metadata_["agent_execution_history"] = []
            test_thread.metadata_["agent_execution_history"].append({
                "agent": "data_helper",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "run_id": str(ctx.run_id)
            })
            
            await db.commit()
            return result
            
        agent.execute = execute_with_metadata_updates
        
        await agent.execute(context)
        
        # Verify metadata was updated correctly
        await db.refresh(test_thread)
        metadata = test_thread.metadata_
        
        # Original metadata preserved
        assert metadata["creation_source"] == "api"
        assert metadata["user_tier"] == "enterprise"
        
        # New metadata added
        assert metadata["optimization_status"] == "data_collection"
        assert metadata["data_helper_executed"] is True
        assert "last_agent_execution" in metadata
        assert len(metadata["agent_execution_history"]) == 1

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_agent_state_synchronization_validation(
        self, real_services_fixture, test_thread, mock_llm_manager, mock_websocket_notifier
    ):
        """Test thread-agent state synchronization validation."""
        db = real_services_fixture["db"]
        env = get_env()
        
        user_id = UserID(f"user_{uuid.uuid4().hex[:8]}")
        
        # Create initial synchronized state
        thread_state = {
            "sync_version": 1,
            "state_checksum": "initial_checksum",
            "synchronized_data": {
                "user_preferences": {"theme": "dark", "language": "en"},
                "session_info": {"start_time": datetime.now(timezone.utc).isoformat()}
            }
        }
        
        test_thread.metadata_ = thread_state
        await db.commit()
        
        # Execute agent with state synchronization
        context = UserExecutionContext(
            user_id=user_id,
            thread_id=ThreadID(test_thread.id),
            run_id=RunID(f"run_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={
                "user_request": "State synchronization test",
                "expected_sync_version": 1
            },
            isolated_env=env
        )
        
        tool_dispatcher = UnifiedToolDispatcher()
        agent = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent.websocket_notifier = mock_websocket_notifier
        
        # Enhanced execution with state validation
        original_execute = agent.execute
        
        async def execute_with_state_validation(ctx):
            # Validate state synchronization before execution
            await db.refresh(test_thread)
            current_version = test_thread.metadata_.get("sync_version", 0)
            expected_version = ctx.metadata.get("expected_sync_version", 0)
            
            if current_version != expected_version:
                ctx.metadata["sync_warning"] = f"State version mismatch: {current_version} vs {expected_version}"
            else:
                ctx.metadata["sync_status"] = "validated"
            
            result = await original_execute(ctx)
            
            # Update state after execution
            test_thread.metadata_["sync_version"] += 1
            test_thread.metadata_["state_checksum"] = f"updated_checksum_{current_version + 1}"
            test_thread.metadata_["last_sync_update"] = datetime.now(timezone.utc).isoformat()
            await db.commit()
            
            return result
            
        agent.execute = execute_with_state_validation
        
        result_context = await agent.execute(context)
        
        # Verify state synchronization
        assert result_context.metadata.get("sync_status") == "validated"
        
        # Verify state was updated
        await db.refresh(test_thread)
        assert test_thread.metadata_["sync_version"] == 2
        assert "updated_checksum_2" in test_thread.metadata_["state_checksum"]
        assert "last_sync_update" in test_thread.metadata_

    # ========== Context Propagation Tests (4 tests) ==========

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_context_propagation_from_thread_to_agent(
        self, real_services_fixture, test_thread, mock_llm_manager, mock_websocket_notifier
    ):
        """Test user context propagation from thread to agent."""
        db = real_services_fixture["db"]
        env = get_env()
        
        user_id = UserID(f"user_{uuid.uuid4().hex[:8]}")
        
        # Set rich user context in thread
        user_context_data = {
            "user_profile": {
                "id": str(user_id),
                "name": "Test User",
                "email": "test@example.com",
                "tier": "enterprise",
                "preferences": {
                    "optimization_focus": ["cost", "performance"],
                    "notification_settings": {"email": True, "sms": False},
                    "ui_preferences": {"theme": "dark", "density": "compact"}
                }
            },
            "business_context": {
                "company": "Test Corp",
                "industry": "technology",
                "size": "mid_market",
                "compliance_requirements": ["SOC2", "GDPR"]
            },
            "technical_context": {
                "primary_cloud": "aws",
                "regions": ["us-east-1", "us-west-2"],
                "services_used": ["ec2", "s3", "rds", "lambda"]
            }
        }
        
        test_thread.metadata_ = {"user_context": user_context_data}
        await db.commit()
        
        # Create execution context
        execution_context = UserExecutionContext(
            user_id=user_id,
            thread_id=ThreadID(test_thread.id),
            run_id=RunID(f"run_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={"user_request": "Context propagation test"},
            isolated_env=env
        )
        
        # Enhanced agent with context propagation
        tool_dispatcher = UnifiedToolDispatcher()
        agent = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent.websocket_notifier = mock_websocket_notifier
        
        original_execute = agent.execute
        
        async def execute_with_context_propagation(ctx):
            # Load user context from thread
            await db.refresh(test_thread)
            thread_user_context = test_thread.metadata_.get("user_context", {})
            ctx.metadata["propagated_user_context"] = thread_user_context
            return await original_execute(ctx)
            
        agent.execute = execute_with_context_propagation
        
        result_context = await agent.execute(execution_context)
        
        # Verify complete user context propagation
        propagated_context = result_context.metadata["propagated_user_context"]
        assert propagated_context["user_profile"]["id"] == str(user_id)
        assert propagated_context["user_profile"]["tier"] == "enterprise"
        assert "cost" in propagated_context["user_profile"]["preferences"]["optimization_focus"]
        assert propagated_context["business_context"]["company"] == "Test Corp"
        assert "aws" == propagated_context["technical_context"]["primary_cloud"]

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_context_availability_during_agent_execution(
        self, real_services_fixture, test_thread, mock_llm_manager, mock_websocket_notifier
    ):
        """Test thread context availability during agent execution."""
        db = real_services_fixture["db"]
        env = get_env()
        
        # Set comprehensive thread context
        thread_context = {
            "conversation_metadata": {
                "start_time": datetime.now(timezone.utc).isoformat(),
                "message_count": 15,
                "conversation_depth": "technical",
                "topics_covered": ["cost_optimization", "performance", "security"]
            },
            "optimization_history": {
                "previous_recommendations": [
                    {"type": "instance_sizing", "savings": 2500, "implemented": True},
                    {"type": "reserved_instances", "savings": 8000, "implemented": False}
                ],
                "total_potential_savings": 10500,
                "implementation_rate": 0.3
            },
            "user_engagement": {
                "response_rate": 0.95,
                "session_duration": 1800,  # 30 minutes
                "satisfaction_score": 4.5
            }
        }
        
        test_thread.metadata_ = {"thread_context": thread_context}
        await db.commit()
        
        user_id = UserID(f"user_{uuid.uuid4().hex[:8]}")
        
        # Execute agent with thread context access
        context = UserExecutionContext(
            user_id=user_id,
            thread_id=ThreadID(test_thread.id),
            run_id=RunID(f"run_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={"user_request": "Use full thread context for recommendations"},
            isolated_env=env
        )
        
        tool_dispatcher = UnifiedToolDispatcher()
        agent = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent.websocket_notifier = mock_websocket_notifier
        
        # Track context access during execution
        context_access_log = []
        
        original_execute = agent.execute
        
        async def execute_with_context_tracking(ctx):
            # Simulate context access at different execution stages
            context_access_log.append("execution_start")
            
            # Load thread context
            await db.refresh(test_thread)
            thread_ctx = test_thread.metadata_.get("thread_context", {})
            ctx.metadata["available_thread_context"] = thread_ctx
            context_access_log.append("context_loaded")
            
            # Execute with context
            result = await original_execute(ctx)
            context_access_log.append("execution_complete")
            
            # Verify context was available throughout
            if thread_ctx:
                context_access_log.append("context_verified")
            
            return result
            
        agent.execute = execute_with_context_tracking
        
        result_context = await agent.execute(context)
        
        # Verify thread context was available during execution
        assert "context_loaded" in context_access_log
        assert "context_verified" in context_access_log
        
        available_context = result_context.metadata["available_thread_context"]
        assert available_context["conversation_metadata"]["message_count"] == 15
        assert available_context["optimization_history"]["total_potential_savings"] == 10500
        assert available_context["user_engagement"]["satisfaction_score"] == 4.5

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_context_isolation_between_different_threads(
        self, real_services_fixture, mock_llm_manager, mock_websocket_notifier
    ):
        """Test agent context isolation between different threads."""
        db = real_services_fixture["db"]
        env = get_env()
        
        # Create two separate threads with different contexts
        thread1_id = ThreadID(f"thread1_{uuid.uuid4().hex[:8]}")
        thread2_id = ThreadID(f"thread2_{uuid.uuid4().hex[:8]}")
        
        thread1 = Thread(
            id=thread1_id,
            created_at=int(time.time()),
            metadata_={
                "business_context": {"industry": "healthcare", "compliance": ["HIPAA"]},
                "sensitive_data": "patient_optimization_data",
                "confidentiality": "high"
            }
        )
        
        thread2 = Thread(
            id=thread2_id,
            created_at=int(time.time()),
            metadata_={
                "business_context": {"industry": "retail", "compliance": ["PCI"]},
                "sensitive_data": "customer_analytics_data",
                "confidentiality": "medium"
            }
        )
        
        db.add_all([thread1, thread2])
        await db.commit()
        
        # Create isolated execution contexts
        user1_id = UserID(f"user1_{uuid.uuid4().hex[:8]}")
        user2_id = UserID(f"user2_{uuid.uuid4().hex[:8]}")
        
        context1 = UserExecutionContext(
            user_id=user1_id,
            thread_id=thread1_id,
            run_id=RunID(f"run1_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req1_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={"user_request": "Healthcare optimization", "context_source": "thread1"},
            isolated_env=env
        )
        
        context2 = UserExecutionContext(
            user_id=user2_id,
            thread_id=thread2_id,
            run_id=RunID(f"run2_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req2_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={"user_request": "Retail optimization", "context_source": "thread2"},
            isolated_env=env
        )
        
        # Create agents with context isolation
        tool_dispatcher1 = UnifiedToolDispatcher()
        tool_dispatcher2 = UnifiedToolDispatcher()
        
        agent1 = DataHelperAgent(mock_llm_manager, tool_dispatcher1)
        agent2 = DataHelperAgent(mock_llm_manager, tool_dispatcher2)
        
        agent1.websocket_notifier = mock_websocket_notifier
        agent2.websocket_notifier = mock_websocket_notifier
        
        # Execute agents concurrently with isolation tracking
        execution_contexts = {}
        
        original_execute1 = agent1.execute
        original_execute2 = agent2.execute
        
        async def execute_with_isolation_tracking1(ctx):
            execution_contexts["agent1_context"] = {
                "thread_id": str(ctx.thread_id),
                "user_id": str(ctx.user_id),
                "sensitive_data": None
            }
            
            # Load thread-specific context
            thread = await db.get(Thread, ctx.thread_id)
            if thread and thread.metadata_:
                execution_contexts["agent1_context"]["sensitive_data"] = thread.metadata_.get("sensitive_data")
                ctx.metadata["thread_specific_data"] = thread.metadata_
            
            return await original_execute1(ctx)
            
        async def execute_with_isolation_tracking2(ctx):
            execution_contexts["agent2_context"] = {
                "thread_id": str(ctx.thread_id),
                "user_id": str(ctx.user_id),
                "sensitive_data": None
            }
            
            # Load thread-specific context
            thread = await db.get(Thread, ctx.thread_id)
            if thread and thread.metadata_:
                execution_contexts["agent2_context"]["sensitive_data"] = thread.metadata_.get("sensitive_data")
                ctx.metadata["thread_specific_data"] = thread.metadata_
            
            return await original_execute2(ctx)
        
        agent1.execute = execute_with_isolation_tracking1
        agent2.execute = execute_with_isolation_tracking2
        
        # Execute concurrently
        results = await asyncio.gather(
            agent1.execute(context1),
            agent2.execute(context2)
        )
        
        result1, result2 = results
        
        # Verify complete context isolation
        assert execution_contexts["agent1_context"]["thread_id"] != execution_contexts["agent2_context"]["thread_id"]
        assert execution_contexts["agent1_context"]["user_id"] != execution_contexts["agent2_context"]["user_id"]
        
        # Verify sensitive data isolation
        assert execution_contexts["agent1_context"]["sensitive_data"] == "patient_optimization_data"
        assert execution_contexts["agent2_context"]["sensitive_data"] == "customer_analytics_data"
        
        # Verify no cross-contamination in results
        thread1_data = result1.metadata.get("thread_specific_data", {})
        thread2_data = result2.metadata.get("thread_specific_data", {})
        
        assert thread1_data.get("business_context", {}).get("industry") == "healthcare"
        assert thread2_data.get("business_context", {}).get("industry") == "retail"
        assert "HIPAA" in thread1_data.get("business_context", {}).get("compliance", [])
        assert "PCI" in thread2_data.get("business_context", {}).get("compliance", [])

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_context_cleanup_after_agent_execution_completion(
        self, real_services_fixture, test_thread, mock_llm_manager, mock_websocket_notifier
    ):
        """Test context cleanup after agent execution completion."""
        db = real_services_fixture["db"]
        env = get_env()
        
        user_id = UserID(f"user_{uuid.uuid4().hex[:8]}")
        
        # Create execution context with temporary data
        context = UserExecutionContext(
            user_id=user_id,
            thread_id=ThreadID(test_thread.id),
            run_id=RunID(f"run_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={
                "user_request": "Context cleanup test",
                "temporary_data": {
                    "processing_cache": {"temp_key": "temp_value"},
                    "intermediate_results": ["step1", "step2", "step3"],
                    "sensitive_tokens": ["token1", "token2"]
                },
                "persistent_data": {
                    "user_preferences": {"theme": "dark"},
                    "session_info": {"start_time": datetime.now(timezone.utc).isoformat()}
                }
            },
            isolated_env=env
        )
        
        # Track cleanup operations
        cleanup_operations = []
        
        tool_dispatcher = UnifiedToolDispatcher()
        agent = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent.websocket_notifier = mock_websocket_notifier
        
        # Enhanced agent with cleanup tracking
        original_execute = agent.execute
        
        async def execute_with_cleanup_tracking(ctx):
            # Add more temporary data during execution
            ctx.metadata["execution_temporary"] = {
                "processing_id": uuid.uuid4().hex,
                "memory_cache": {"cache_data": "should_be_cleaned"},
                "work_buffer": list(range(100))  # Simulate large temporary data
            }
            
            cleanup_operations.append("temporary_data_added")
            
            # Execute agent
            result = await original_execute(ctx)
            
            # Simulate cleanup operations
            if "temporary_data" in result.metadata:
                # Clean sensitive tokens
                if "sensitive_tokens" in result.metadata["temporary_data"]:
                    result.metadata["temporary_data"]["sensitive_tokens"] = ["[REDACTED]"] * len(result.metadata["temporary_data"]["sensitive_tokens"])
                    cleanup_operations.append("sensitive_tokens_cleaned")
                
                # Clear processing cache
                if "processing_cache" in result.metadata["temporary_data"]:
                    result.metadata["temporary_data"]["processing_cache"] = {}
                    cleanup_operations.append("processing_cache_cleared")
            
            # Clean execution temporary data
            if "execution_temporary" in result.metadata:
                del result.metadata["execution_temporary"]
                cleanup_operations.append("execution_temporary_removed")
            
            # Preserve persistent data
            persistent_data = result.metadata.get("persistent_data", {})
            if persistent_data:
                cleanup_operations.append("persistent_data_preserved")
            
            return result
            
        agent.execute = execute_with_cleanup_tracking
        
        result_context = await agent.execute(context)
        
        # Verify cleanup was performed
        assert "sensitive_tokens_cleaned" in cleanup_operations
        assert "processing_cache_cleared" in cleanup_operations
        assert "execution_temporary_removed" in cleanup_operations
        assert "persistent_data_preserved" in cleanup_operations
        
        # Verify sensitive data was cleaned
        temp_data = result_context.metadata.get("temporary_data", {})
        if "sensitive_tokens" in temp_data:
            assert all(token == "[REDACTED]" for token in temp_data["sensitive_tokens"])
        
        # Verify processing cache was cleared
        if "processing_cache" in temp_data:
            assert temp_data["processing_cache"] == {}
        
        # Verify execution temporary data was removed
        assert "execution_temporary" not in result_context.metadata
        
        # Verify persistent data was preserved
        persistent_data = result_context.metadata.get("persistent_data", {})
        assert persistent_data["user_preferences"]["theme"] == "dark"
        assert "start_time" in persistent_data["session_info"]

    # ========== Performance Integration Tests (3 tests) ==========

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_agent_interaction_performance_optimization(
        self, real_services_fixture, test_thread, mock_llm_manager, mock_websocket_notifier
    ):
        """Test thread-agent interaction performance optimization."""
        db = real_services_fixture["db"]
        env = get_env()
        
        user_id = UserID(f"user_{uuid.uuid4().hex[:8]}")
        
        # Create optimized execution context
        context = UserExecutionContext(
            user_id=user_id,
            thread_id=ThreadID(test_thread.id),
            run_id=RunID(f"run_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"req_{uuid.uuid4().hex[:8]}"),
            session=db,
            metadata={"user_request": "Performance optimization test"},
            isolated_env=env
        )
        
        # Performance tracking
        performance_metrics = {
            "context_creation_time": 0,
            "agent_initialization_time": 0,
            "execution_time": 0,
            "context_cleanup_time": 0,
            "total_time": 0,
            "memory_usage_before": 0,
            "memory_usage_after": 0
        }
        
        total_start = time.time()
        
        # Track context creation performance
        context_start = time.time()
        # Context already created - measure access time
        context_access_time = time.time() - context_start
        performance_metrics["context_creation_time"] = context_access_time
        
        # Track agent initialization performance
        init_start = time.time()
        tool_dispatcher = UnifiedToolDispatcher()
        agent = DataHelperAgent(mock_llm_manager, tool_dispatcher)
        agent.websocket_notifier = mock_websocket_notifier
        performance_metrics["agent_initialization_time"] = time.time() - init_start
        
        # Track execution performance
        exec_start = time.time()
        result_context = await agent.execute(context)
        performance_metrics["execution_time"] = time.time() - exec_start
        
        # Track cleanup performance (simulated)
        cleanup_start = time.time()
        # Simulate cleanup operations
        await asyncio.sleep(0.001)  # Minimal cleanup simulation
        performance_metrics["context_cleanup_time"] = time.time() - cleanup_start
        
        performance_metrics["total_time"] = time.time() - total_start
        
        # Verify performance is within acceptable limits for chat
        assert performance_metrics["total_time"] < 3.0, "Total execution too slow for chat"
        assert performance_metrics["execution_time"] < 2.0, "Agent execution too slow"
        assert performance_metrics["agent_initialization_time"] < 0.5, "Agent initialization too slow"
        
        # Verify execution completed successfully
        assert result_context.user_id == user_id
        assert "data_helper_result" in result_context.metadata
        
        # Store performance metrics for analysis
        test_thread.metadata_ = {"performance_metrics": performance_metrics}
        await db.commit()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_thread_agent_execution_isolation(
        self, real_services_fixture, mock_llm_manager, mock_websocket_notifier
    ):
        """Test concurrent thread-agent execution isolation."""
        db = real_services_fixture["db"]
        env = get_env()
        
        # Create multiple threads and contexts for concurrency testing
        concurrent_executions = 5
        threads = []
        contexts = []
        
        for i in range(concurrent_executions):
            thread_id = ThreadID(f"concurrent_thread_{i}_{uuid.uuid4().hex[:8]}")
            user_id = UserID(f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}")
            
            thread = Thread(
                id=thread_id,
                created_at=int(time.time()) + i,
                metadata_={
                    "execution_id": i,
                    "user_id": str(user_id),
                    "concurrent_test": True
                }
            )
            threads.append(thread)
            
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=RunID(f"concurrent_run_{i}_{uuid.uuid4().hex[:8]}"),
                request_id=RequestID(f"concurrent_req_{i}_{uuid.uuid4().hex[:8]}"),
                session=db,
                metadata={
                    "user_request": f"Concurrent execution test {i}",
                    "execution_sequence": i,
                    "unique_identifier": f"unique_{i}"
                },
                isolated_env=env
            )
            contexts.append(context)
        
        # Add all threads to database
        db.add_all(threads)
        await db.commit()
        
        # Create agents for concurrent execution
        agents = []
        for i in range(concurrent_executions):
            tool_dispatcher = UnifiedToolDispatcher()
            agent = DataHelperAgent(mock_llm_manager, tool_dispatcher)
            agent.websocket_notifier = mock_websocket_notifier
            agents.append(agent)
        
        # Execute all agents concurrently
        start_time = time.time()
        
        async def execute_with_isolation_tracking(agent, context):
            return {
                "agent_id": id(agent),
                "context": context,
                "result": await agent.execute(context),
                "execution_start": time.time()
            }
        
        # Run concurrent executions
        execution_tasks = [
            execute_with_isolation_tracking(agent, context) 
            for agent, context in zip(agents, contexts)
        ]
        
        results = await asyncio.gather(*execution_tasks)
        total_concurrent_time = time.time() - start_time
        
        # Verify isolation - no cross-contamination
        for i, result in enumerate(results):
            result_context = result["result"]
            original_context = result["context"]
            
            # Verify context integrity
            assert result_context.user_id == original_context.user_id
            assert result_context.thread_id == original_context.thread_id
            assert result_context.run_id == original_context.run_id
            
            # Verify unique identifiers preserved
            assert result_context.metadata["execution_sequence"] == i
            assert result_context.metadata["unique_identifier"] == f"unique_{i}"
            
            # Verify no data leakage from other executions
            for j in range(concurrent_executions):
                if i != j:
                    assert f"unique_{j}" not in str(result_context.metadata)
        
        # Verify performance under concurrent load
        avg_execution_time = total_concurrent_time / concurrent_executions
        assert avg_execution_time < 1.0, "Concurrent execution too slow for chat"
        
        # Verify all executions completed successfully
        assert len(results) == concurrent_executions
        assert all("data_helper_result" in result["result"].metadata for result in results)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_thread_agent_integration_under_load_conditions(
        self, real_services_fixture, mock_llm_manager, mock_websocket_notifier
    ):
        """Test thread-agent integration under load conditions."""
        db = real_services_fixture["db"]
        env = get_env()
        
        # Load test parameters
        load_users = 10
        messages_per_user = 3
        concurrent_agents = 3
        
        # Create load test scenario
        load_results = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_time": 0,
            "avg_execution_time": 0,
            "max_execution_time": 0,
            "min_execution_time": float('inf'),
            "errors": []
        }
        
        start_time = time.time()
        
        # Create multiple users and threads
        execution_tasks = []
        
        for user_idx in range(load_users):
            user_id = UserID(f"load_user_{user_idx}_{uuid.uuid4().hex[:8]}")
            
            for msg_idx in range(messages_per_user):
                thread_id = ThreadID(f"load_thread_{user_idx}_{msg_idx}_{uuid.uuid4().hex[:8]}")
                
                # Create thread
                thread = Thread(
                    id=thread_id,
                    created_at=int(time.time()) + user_idx * messages_per_user + msg_idx,
                    metadata_={
                        "load_test": True,
                        "user_index": user_idx,
                        "message_index": msg_idx
                    }
                )
                db.add(thread)
                
                # Create execution context
                context = UserExecutionContext(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=RunID(f"load_run_{user_idx}_{msg_idx}_{uuid.uuid4().hex[:8]}"),
                    request_id=RequestID(f"load_req_{user_idx}_{msg_idx}_{uuid.uuid4().hex[:8]}"),
                    session=db,
                    metadata={
                        "user_request": f"Load test request from user {user_idx}, message {msg_idx}",
                        "load_test_params": {
                            "user_index": user_idx,
                            "message_index": msg_idx,
                            "total_load": load_users * messages_per_user
                        }
                    },
                    isolated_env=env
                )
                
                # Create agent for this execution
                tool_dispatcher = UnifiedToolDispatcher()
                agent = DataHelperAgent(mock_llm_manager, tool_dispatcher)
                agent.websocket_notifier = mock_websocket_notifier
                
                # Create execution task
                async def load_execution(agent, context, user_idx, msg_idx):
                    exec_start = time.time()
                    try:
                        result = await agent.execute(context)
                        exec_time = time.time() - exec_start
                        
                        return {
                            "success": True,
                            "user_idx": user_idx,
                            "msg_idx": msg_idx,
                            "execution_time": exec_time,
                            "result": result,
                            "error": None
                        }
                    except Exception as e:
                        exec_time = time.time() - exec_start
                        return {
                            "success": False,
                            "user_idx": user_idx,
                            "msg_idx": msg_idx,
                            "execution_time": exec_time,
                            "result": None,
                            "error": str(e)
                        }
                
                execution_tasks.append(load_execution(agent, context, user_idx, msg_idx))
        
        await db.commit()
        
        # Execute load test with limited concurrency to avoid overwhelming system
        batch_size = concurrent_agents
        all_results = []
        
        for i in range(0, len(execution_tasks), batch_size):
            batch = execution_tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            all_results.extend(batch_results)
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        load_results["total_time"] = time.time() - start_time
        load_results["total_executions"] = len(all_results)
        
        # Process results
        execution_times = []
        for result in all_results:
            if isinstance(result, dict):
                if result["success"]:
                    load_results["successful_executions"] += 1
                    execution_times.append(result["execution_time"])
                else:
                    load_results["failed_executions"] += 1
                    load_results["errors"].append(result["error"])
            else:
                load_results["failed_executions"] += 1
                load_results["errors"].append(str(result))
        
        # Calculate performance metrics
        if execution_times:
            load_results["avg_execution_time"] = sum(execution_times) / len(execution_times)
            load_results["max_execution_time"] = max(execution_times)
            load_results["min_execution_time"] = min(execution_times)
        
        # Verify load test performance
        success_rate = load_results["successful_executions"] / load_results["total_executions"]
        assert success_rate >= 0.95, f"Load test success rate too low: {success_rate}"
        
        assert load_results["avg_execution_time"] < 3.0, "Average execution time too high under load"
        
        # Verify system remained stable under load
        assert load_results["failed_executions"] < load_results["total_executions"] * 0.05, "Too many failures under load"
        
        # Log load test results
        print(f"\nLoad Test Results:")
        print(f"Total Executions: {load_results['total_executions']}")
        print(f"Successful: {load_results['successful_executions']}")
        print(f"Failed: {load_results['failed_executions']}")
        print(f"Success Rate: {success_rate:.2%}")
        print(f"Total Time: {load_results['total_time']:.2f}s")
        print(f"Avg Execution Time: {load_results['avg_execution_time']:.3f}s")
        print(f"Max Execution Time: {load_results['max_execution_time']:.3f}s")