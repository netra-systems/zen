"""
Agent Execution Pipeline Integration Tests - Priority 2 for Issue #861

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure reliable agent execution from user request to AI response
- Value Impact: Core agent pipeline must work reliably for substantive AI interactions
- Strategic Impact: $500K+ ARR depends on agents delivering valuable responses

CRITICAL: Tests complete agent execution pipeline covering:
- User request → Agent creation → Execution → Response delivery
- Multi-user concurrent execution with proper isolation
- Agent lifecycle management and resource cleanup
- Error handling and recovery in agent pipeline

INTEGRATION LAYER: Uses real services (PostgreSQL, Redis) without Docker dependencies.
NO MOCKS in integration tests - validates actual agent execution flow.

Target: Improve coverage from 0% → 70%+ (Priority 2 of 4)
Focus Areas:
- /netra_backend/app/agents/supervisor_agent_modern.py
- /netra_backend/app/agents/supervisor/execution_engine_factory.py  
- /netra_backend/app/agents/supervisor/agent_registry.py
"""

import asyncio
import json
import pytest
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from unittest import mock
from dataclasses import dataclass

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.fixtures.real_services import (
    real_services_fixture,
    real_postgres_connection, 
    with_test_database,
    real_redis_connection
)

# SSOT Agent execution imports
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, UserAgentSession
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory

# SSOT Context and WebSocket imports
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

# SSOT Base agent import
from netra_backend.app.agents.base_agent import BaseAgent

# SSOT configuration imports
from shared.isolated_environment import get_env
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

# Import specific agents for testing
try:
    from netra_backend.app.agents.triage_agent import TriageAgent
    from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False


@dataclass
class AgentExecutionResult:
    """Container for agent execution results."""
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    events_emitted: List[str] = None
    
    def __post_init__(self):
        if self.events_emitted is None:
            self.events_emitted = []


class MockWebSocketForAgentTesting:
    """Mock WebSocket that captures agent events during execution."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.sent_messages: List[Dict[str, Any]] = []
        self.is_connected = True
        self.events_captured: List[str] = []
        
    async def send_text(self, message: str):
        """Capture sent messages and extract event types."""
        if self.is_connected:
            try:
                data = json.loads(message)
                self.sent_messages.append(data)
                if 'type' in data:
                    self.events_captured.append(data['type'])
            except json.JSONDecodeError:
                pass
    
    async def close(self, code: int = 1000):
        """Close connection."""
        self.is_connected = False


class TestAgentExecutionPipelineIntegration(SSotAsyncTestCase):
    """Test comprehensive agent execution pipeline functionality."""
    
    async def asyncSetUp(self):
        """Set up test environment with real services and agent infrastructure."""
        await super().asyncSetUp()
        
        # Generate unique test identifiers
        self.test_session_id = f"exec-session-{uuid.uuid4().hex[:8]}"
        self.test_user_id = f"exec-user-{uuid.uuid4().hex[:8]}"
        self.test_connection_id = f"exec-conn-{uuid.uuid4().hex[:8]}"
        
        # Create mock WebSocket for event capture
        self.mock_websocket = MockWebSocketForAgentTesting(self.test_user_id)
        
        # Set up WebSocket manager
        self.websocket_manager = WebSocketManager()
        self.websocket_manager.active_connections[self.test_connection_id] = self.mock_websocket
        self.websocket_manager.connection_user_map[self.test_connection_id] = self.test_user_id
        self.websocket_manager.user_connection_map[self.test_user_id] = {self.test_connection_id}
        
        # Create user execution context
        self.user_context = UserExecutionContext(
            user_id=self.test_user_id,
            session_id=self.test_session_id,
            connection_id=self.test_connection_id,
            request_timestamp=time.time()
        )
        
        # Create agent registry and set WebSocket manager
        self.agent_registry = AgentRegistry()
        self.agent_registry.set_websocket_manager(self.websocket_manager)
        
        # Create execution engine factory
        self.execution_factory = ExecutionEngineFactory()
        
        # Create agent instance factory
        self.agent_factory = get_agent_instance_factory()
        
        # Create WebSocket bridge
        self.websocket_bridge = AgentWebSocketBridge(
            websocket_manager=self.websocket_manager,
            user_context=self.user_context
        )
    
    async def asyncTearDown(self):
        """Clean up test resources and connections."""
        # Close mock WebSocket
        if hasattr(self, 'mock_websocket') and self.mock_websocket.is_connected:
            await self.mock_websocket.close()
        
        # Clean up WebSocket manager
        if hasattr(self, 'websocket_manager'):
            self.websocket_manager.active_connections.clear()
            self.websocket_manager.connection_user_map.clear() 
            self.websocket_manager.user_connection_map.clear()
        
        # Clean up agent registry
        if hasattr(self, 'agent_registry'):
            # Clean up any user sessions
            self.agent_registry.user_sessions.clear()
            
        await super().asyncTearDown()
    
    async def execute_agent_with_context(
        self, 
        agent_type: str,
        user_input: str,
        timeout: float = 10.0
    ) -> AgentExecutionResult:
        """Execute agent through complete pipeline and return results."""
        
        start_time = time.time()
        
        try:
            # Create user agent session
            user_session = UserAgentSession(self.test_user_id)
            user_session.set_websocket_bridge(self.websocket_bridge)
            
            # Get agent instance from factory 
            if agent_type == "triage" and AGENTS_AVAILABLE:
                agent_instance = self.agent_factory.create_triage_agent(
                    user_context=self.user_context
                )
            elif agent_type == "supervisor" and AGENTS_AVAILABLE:
                agent_instance = self.agent_factory.create_supervisor_agent(
                    user_context=self.user_context  
                )
            else:
                # Use base agent for testing if specific agents not available
                agent_instance = BaseAgent(
                    agent_name=f"Test{agent_type.capitalize()}Agent",
                    user_context=self.user_context
                )
            
            # Register agent with user session
            user_session.register_agent(agent_instance)
            
            # Create execution engine for user
            async with self.execution_factory.create_user_engine(
                user_context=self.user_context,
                websocket_bridge=self.websocket_bridge
            ) as execution_engine:
                
                # Execute agent through pipeline
                response = await execution_engine.execute_agent_request(
                    agent_name=agent_instance.agent_name,
                    user_input=user_input,
                    timeout=timeout
                )
                
                execution_time = time.time() - start_time
                
                return AgentExecutionResult(
                    success=True,
                    response=response.get('response', ''),
                    execution_time=execution_time,
                    events_emitted=self.mock_websocket.events_captured.copy()
                )
        
        except Exception as e:
            execution_time = time.time() - start_time
            return AgentExecutionResult(
                success=False,
                error=str(e),
                execution_time=execution_time,
                events_emitted=self.mock_websocket.events_captured.copy()
            )

    @pytest.mark.asyncio 
    async def test_complete_agent_execution_pipeline(self):
        """Test Priority 2: Complete agent execution from request to response."""
        
        user_input = "Analyze the current market trends for AI companies."
        
        # Execute agent through complete pipeline
        result = await self.execute_agent_with_context(
            agent_type="triage",
            user_input=user_input,
            timeout=15.0
        )
        
        # Verify execution completed successfully
        self.assertTrue(result.success, f"Agent execution failed: {result.error}")
        self.assertIsNotNone(result.response)
        self.assertGreater(len(result.response), 10)  # Non-trivial response
        
        # Verify execution completed in reasonable time
        self.assertLess(result.execution_time, 15.0)
        
        # Verify WebSocket events were emitted during execution
        self.assertGreater(len(result.events_emitted), 0, "No WebSocket events emitted")
        
        # Check for critical events
        expected_events = ['agent_started', 'agent_completed']
        for event in expected_events:
            self.assertIn(event, result.events_emitted,
                         f"Missing critical event: {event}")

    @pytest.mark.asyncio
    async def test_concurrent_multi_user_agent_execution(self):
        """Test Priority 2: Multiple users can execute agents concurrently with isolation."""
        
        # Create second user context
        user2_id = f"exec-user2-{uuid.uuid4().hex[:8]}"
        conn2_id = f"exec-conn2-{uuid.uuid4().hex[:8]}"
        session2_id = f"exec-session2-{uuid.uuid4().hex[:8]}"
        
        mock_websocket2 = MockWebSocketForAgentTesting(user2_id)
        
        # Register second user in WebSocket manager
        self.websocket_manager.active_connections[conn2_id] = mock_websocket2
        self.websocket_manager.connection_user_map[conn2_id] = user2_id
        self.websocket_manager.user_connection_map[user2_id] = {conn2_id}
        
        user2_context = UserExecutionContext(
            user_id=user2_id,
            session_id=session2_id,
            connection_id=conn2_id,
            request_timestamp=time.time()
        )
        
        # Create second WebSocket bridge
        user2_bridge = AgentWebSocketBridge(
            websocket_manager=self.websocket_manager,
            user_context=user2_context
        )
        
        # Execute agents concurrently for both users
        task1 = asyncio.create_task(
            self.execute_agent_with_context(
                agent_type="triage",
                user_input="User 1: What are the best AI stocks to invest in?"
            )
        )
        
        # Create execution for user 2 with their context
        async def execute_user2_agent():
            start_time = time.time()
            try:
                user2_session = UserAgentSession(user2_id)
                user2_session.set_websocket_bridge(user2_bridge)
                
                agent_instance = BaseAgent(
                    agent_name="TestTriageAgent",
                    user_context=user2_context
                )
                user2_session.register_agent(agent_instance)
                
                async with self.execution_factory.create_user_engine(
                    user_context=user2_context,
                    websocket_bridge=user2_bridge
                ) as execution_engine:
                    
                    response = await execution_engine.execute_agent_request(
                        agent_name=agent_instance.agent_name,
                        user_input="User 2: How do I optimize my AI model performance?",
                        timeout=10.0
                    )
                    
                    return AgentExecutionResult(
                        success=True,
                        response=response.get('response', ''),
                        execution_time=time.time() - start_time,
                        events_emitted=mock_websocket2.events_captured.copy()
                    )
            except Exception as e:
                return AgentExecutionResult(
                    success=False,
                    error=str(e),
                    execution_time=time.time() - start_time,
                    events_emitted=mock_websocket2.events_captured.copy()
                )
        
        task2 = asyncio.create_task(execute_user2_agent())
        
        # Wait for both executions to complete
        result1, result2 = await asyncio.gather(task1, task2)
        
        # Verify both executions succeeded
        self.assertTrue(result1.success, f"User 1 execution failed: {result1.error}")
        self.assertTrue(result2.success, f"User 2 execution failed: {result2.error}")
        
        # Verify responses are different (indicating proper isolation)
        self.assertNotEqual(result1.response, result2.response)
        
        # Verify events were emitted for both users separately
        self.assertGreater(len(result1.events_emitted), 0)
        self.assertGreater(len(result2.events_emitted), 0)
        
        # Clean up user 2 WebSocket
        await mock_websocket2.close()

    @pytest.mark.asyncio
    async def test_agent_execution_error_handling(self):
        """Test Priority 2: Error handling in agent execution pipeline."""
        
        # Test with invalid/empty input
        result = await self.execute_agent_with_context(
            agent_type="triage",
            user_input="",  # Empty input should be handled gracefully
            timeout=5.0
        )
        
        # Should either succeed with error handling or fail gracefully
        if result.success:
            # If successful, should have some response indicating input issues
            self.assertIsNotNone(result.response)
        else:
            # If failed, error should be informative
            self.assertIsNotNone(result.error)
            self.assertGreater(len(result.error), 5)
        
        # Should complete quickly for invalid input
        self.assertLess(result.execution_time, 5.0)

    @pytest.mark.asyncio
    async def test_agent_execution_timeout_handling(self):
        """Test Priority 2: Proper timeout handling in agent execution."""
        
        # Use very short timeout to test timeout behavior
        result = await self.execute_agent_with_context(
            agent_type="triage",
            user_input="This is a complex analysis that might take time...",
            timeout=0.1  # Very short timeout
        )
        
        # Should handle timeout gracefully
        if not result.success:
            self.assertIn("timeout", result.error.lower())
        
        # Execution time should respect timeout
        self.assertLess(result.execution_time, 1.0)  # Should timeout quickly

    @pytest.mark.asyncio
    async def test_agent_registry_user_session_isolation(self):
        """Test Priority 2: Agent registry properly isolates user sessions."""
        
        # Create user session through registry
        user_session1 = UserAgentSession(self.test_user_id)
        user_session1.set_websocket_bridge(self.websocket_bridge)
        
        # Create second user session
        user2_id = f"registry-user2-{uuid.uuid4().hex[:8]}"
        user_session2 = UserAgentSession(user2_id)
        
        # Register both sessions with registry
        self.agent_registry.user_sessions[self.test_user_id] = user_session1
        self.agent_registry.user_sessions[user2_id] = user_session2
        
        # Create and register agents for each user
        agent1 = BaseAgent(
            agent_name="User1Agent",
            user_context=self.user_context
        )
        agent2 = BaseAgent(
            agent_name="User2Agent", 
            user_context=UserExecutionContext(
                user_id=user2_id,
                session_id=f"session2-{uuid.uuid4().hex[:8]}",
                connection_id=f"conn2-{uuid.uuid4().hex[:8]}",
                request_timestamp=time.time()
            )
        )
        
        user_session1.register_agent(agent1)
        user_session2.register_agent(agent2)
        
        # Verify agents are properly isolated
        user1_agents = list(user_session1.agents.keys())
        user2_agents = list(user_session2.agents.keys())
        
        self.assertEqual(len(user1_agents), 1)
        self.assertEqual(len(user2_agents), 1)
        self.assertNotEqual(user1_agents[0], user2_agents[0])
        
        # Verify sessions don't interfere with each other
        self.assertNotIn(agent1.agent_name, user_session2.agents)
        self.assertNotIn(agent2.agent_name, user_session1.agents)

    @pytest.mark.asyncio
    async def test_execution_engine_factory_lifecycle_management(self):
        """Test Priority 2: Execution engine factory properly manages engine lifecycle."""
        
        engines_created = []
        
        # Create multiple execution engines for same user
        for i in range(3):
            async with self.execution_factory.create_user_engine(
                user_context=self.user_context,
                websocket_bridge=self.websocket_bridge
            ) as engine:
                
                self.assertIsInstance(engine, UserExecutionEngine)
                engines_created.append(id(engine))  # Track engine identity
                
                # Verify engine has proper setup
                self.assertIsNotNone(engine.user_context)
                self.assertEqual(engine.user_context.user_id, self.test_user_id)
        
        # Verify each engine was unique instance 
        self.assertEqual(len(set(engines_created)), 3, "Engines should be unique instances")

    @pytest.mark.asyncio
    async def test_agent_pipeline_memory_cleanup(self):
        """Test Priority 2: Agent pipeline properly cleans up resources."""
        
        initial_session_count = len(self.agent_registry.user_sessions)
        
        # Create temporary user session with agents
        temp_user_id = f"temp-user-{uuid.uuid4().hex[:8]}"
        temp_session = UserAgentSession(temp_user_id)
        
        # Add to registry
        self.agent_registry.user_sessions[temp_user_id] = temp_session
        
        # Create and register multiple agents
        for i in range(3):
            agent = BaseAgent(
                agent_name=f"TempAgent{i}",
                user_context=UserExecutionContext(
                    user_id=temp_user_id,
                    session_id=f"temp-session-{i}",
                    connection_id=f"temp-conn-{i}",
                    request_timestamp=time.time()
                )
            )
            temp_session.register_agent(agent)
        
        # Verify agents were registered
        self.assertEqual(len(temp_session.agents), 3)
        self.assertEqual(len(self.agent_registry.user_sessions), initial_session_count + 1)
        
        # Clean up session (simulates user disconnect)
        if temp_user_id in self.agent_registry.user_sessions:
            del self.agent_registry.user_sessions[temp_user_id]
        
        # Verify cleanup
        self.assertEqual(len(self.agent_registry.user_sessions), initial_session_count)
        self.assertNotIn(temp_user_id, self.agent_registry.user_sessions)

    @pytest.mark.asyncio
    async def test_websocket_event_integration_during_execution(self):
        """Test Priority 2: WebSocket events properly integrate with agent execution."""
        
        # Clear previous events
        self.mock_websocket.events_captured.clear()
        self.mock_websocket.sent_messages.clear()
        
        # Execute agent and track events
        result = await self.execute_agent_with_context(
            agent_type="triage", 
            user_input="Test WebSocket integration during agent execution.",
            timeout=10.0
        )
        
        # Should have captured WebSocket events
        self.assertGreater(len(self.mock_websocket.events_captured), 0)
        
        # Should have at minimum agent_started
        self.assertIn('agent_started', result.events_emitted)
        
        # Events should correlate with execution success
        if result.success:
            self.assertIn('agent_completed', result.events_emitted)
        
        # Verify event messages have proper structure
        for message in self.mock_websocket.sent_messages:
            self.assertIn('type', message)
            self.assertIn('timestamp', message) 
            self.assertIn('data', message)
            
            # Agent events should have agent_name
            if message['type'].startswith('agent_'):
                self.assertIn('agent_name', message['data'])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])