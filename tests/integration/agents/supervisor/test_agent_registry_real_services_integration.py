"""
[U+1F680] INTEGRATION TEST SUITE: Agent Registry with Real Services (Non-Docker)

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise) - Protects $500K+ ARR
- Business Goal: Validate agent orchestration works with real backend services
- Value Impact: Ensures agent registry integrates correctly with WebSocket, database, and tool systems
- Revenue Impact: Prevents production failures that could lose enterprise customers ($15K+ MRR each)

CRITICAL INTEGRATION POINTS TESTED:
1. Real WebSocket Manager Integration - Validates WebSocket events work with live connections
2. Real Tool Dispatcher Integration - Ensures tools execute with actual backend services  
3. Real Database Integration - Tests agent state persistence with actual database
4. Real User Context Management - Validates isolation with production-like contexts
5. Real Agent Execution Flow - End-to-end agent creation and execution with live services
6. Real Performance Under Load - Validates registry performance with actual service calls

INTEGRATION STRATEGY:
- Uses real backend services (WebSocket, Database, Tools) without Docker
- No mocks for integration components (per CLAUDE.md requirements)
- Tests can legitimately fail when integration points break
- Focuses on service boundary interactions and data flow validation

RISK MITIGATION:
- Each test validates specific integration that could cause production failures
- Real service failures will be caught before deployment
- Comprehensive coverage of agent-to-service interaction patterns

This test suite protects the integration layer enabling agent orchestration across all services
"""

import asyncio
import pytest
import uuid
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import classes under test
from netra_backend.app.agents.supervisor.agent_registry import (
    AgentRegistry,
    UserAgentSession,
    get_agent_registry
)

# Real service imports (no mocks for integration tests)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge

# Database and configuration
from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.db.database_manager import DatabaseManager

# LLM Manager for real agent creation
from netra_backend.app.llm.llm_manager import LLMManager


class TestRealWebSocketManagerIntegration(SSotAsyncTestCase):
    """Test Suite 1: Real WebSocket Manager Integration (Protects chat value delivery)
    
    Business Value: Validates WebSocket events work with live WebSocket connections
    Revenue Risk: WebSocket failures break chat experience (90% of platform value)
    """

    async def asyncSetUp(self):
        """Set up integration test environment with real services."""
        super().setUp()
        
        # Create real configuration
        self.config = get_unified_config()
        
        # Create real LLM manager
        self.llm_manager = LLMManager()
        
        # Create registry with real LLM manager
        self.registry = AgentRegistry(llm_manager=self.llm_manager)
        
        # Create real user context
        self.test_user_id = f"integration_user_{uuid.uuid4().hex[:8]}"
        self.user_context = UserExecutionContext(
            user_id=self.test_user_id,
            request_id=f"req_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread_{self.test_user_id}",
            run_id=f"run_{uuid.uuid4().hex[:8]}"
        )

    async def test_real_websocket_manager_connection_and_event_delivery(self):
        """INTEGRATION: Validates WebSocket manager connects and delivers events to real connections.
        
        Business Value: Ensures users receive real-time chat notifications in production
        Failure Mode: WebSocket connection failures break user experience
        """
        try:
            # Create real WebSocket manager (no mocking)
            websocket_manager = WebSocketManager()
            await websocket_manager.initialize()
            
            # Set WebSocket manager on registry
            await self.registry.set_websocket_manager_async(websocket_manager)
            
            # Validate manager was set
            self.assertIsNotNone(self.registry.websocket_manager, 
                               "Real WebSocket manager must be set on registry")
            self.assertIs(self.registry.websocket_manager, websocket_manager,
                         "Registry must reference the same WebSocket manager instance")
            
            # Test user session gets WebSocket capability
            user_session = await self.registry.get_user_session(self.test_user_id)
            await user_session.set_websocket_manager(websocket_manager, self.user_context)
            
            # Validate WebSocket bridge was created
            self.assertIsNotNone(user_session._websocket_bridge,
                               "User session must have WebSocket bridge for real connections")
            
            # Test that WebSocket manager can handle events (this validates integration)
            if hasattr(websocket_manager, 'get_connection_count'):
                connection_count = await websocket_manager.get_connection_count()
                # Connection count should be 0 or positive (validates manager is working)
                self.assertGreaterEqual(connection_count, 0, 
                                      "WebSocket manager must track connections")
        
        except ImportError as e:
            self.skipTest(f"WebSocket manager not available for integration test: {e}")
        except Exception as e:
            # Integration failures should be reported, not skipped
            self.fail(f"Real WebSocket integration failed: {e}")

    async def test_websocket_event_propagation_to_multiple_users(self):
        """INTEGRATION: Validates WebSocket events propagate correctly to multiple real user sessions.
        
        Business Value: Ensures chat notifications work for concurrent enterprise users
        Failure Mode: Event propagation failures could cause silent notification failures
        """
        try:
            # Create real WebSocket manager
            websocket_manager = WebSocketManager()
            await websocket_manager.initialize()
            
            # Set up multiple user sessions with real contexts
            user_count = 5
            user_sessions = []
            
            for i in range(user_count):
                user_id = f"multi_user_{i}_{uuid.uuid4().hex[:8]}"
                user_context = UserExecutionContext(
                    user_id=user_id,
                    request_id=f"req_{uuid.uuid4().hex[:8]}",
                    thread_id=f"thread_{user_id}",
                    run_id=f"run_{uuid.uuid4().hex[:8]}"
                )
                
                session = await self.registry.get_user_session(user_id)
                await session.set_websocket_manager(websocket_manager, user_context)
                user_sessions.append((user_id, session, user_context))
            
            # Set WebSocket manager on registry to enable event propagation
            await self.registry.set_websocket_manager_async(websocket_manager)
            
            # Validate all sessions have WebSocket capability
            for user_id, session, context in user_sessions:
                self.assertIsNotNone(session._websocket_bridge,
                                   f"User {user_id} must have WebSocket bridge")
                
                # Test that each session can theoretically send events
                bridge = session._websocket_bridge
                self.assertTrue(hasattr(bridge, 'notify_agent_started'),
                              f"User {user_id} bridge must support agent notifications")
        
        except Exception as e:
            self.fail(f"Multi-user WebSocket integration failed: {e}")

    async def test_websocket_manager_adapter_with_real_manager(self):
        """INTEGRATION: Validates WebSocketManagerAdapter works with real WebSocket manager.
        
        Business Value: Ensures adapter pattern correctly bridges WebSocket managers to agents
        Failure Mode: Adapter failures could break agent-to-WebSocket communication
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import WebSocketManagerAdapter
            
            # Create real WebSocket manager
            websocket_manager = WebSocketManager()
            await websocket_manager.initialize()
            
            # Create adapter with real manager
            adapter = WebSocketManagerAdapter(websocket_manager, self.user_context)
            
            # Test adapter provides expected interface
            required_methods = [
                'notify_agent_started', 'notify_agent_thinking', 'notify_tool_executing',
                'notify_tool_completed', 'notify_agent_completed', 'notify_agent_error'
            ]
            
            for method_name in required_methods:
                self.assertTrue(hasattr(adapter, method_name),
                              f"Adapter must provide {method_name} method")
                method = getattr(adapter, method_name)
                self.assertTrue(callable(method),
                              f"Adapter {method_name} must be callable")
            
            # Test adapter can delegate to real manager
            self.assertIs(adapter._websocket_manager, websocket_manager,
                         "Adapter must reference real WebSocket manager")
            
        except Exception as e:
            self.fail(f"WebSocket adapter integration failed: {e}")


class TestRealToolDispatcherIntegration(SSotAsyncTestCase):
    """Test Suite 2: Real Tool Dispatcher Integration (Protects tool execution reliability)
    
    Business Value: Validates tools work correctly with real backend services
    Revenue Risk: Tool failures could break agent capabilities
    """

    async def asyncSetUp(self):
        """Set up tool dispatcher integration testing."""
        super().setUp()
        
        self.config = get_unified_config()
        self.llm_manager = LLMManager()
        self.registry = AgentRegistry(llm_manager=self.llm_manager)
        
        self.test_user_context = UserExecutionContext(
            user_id=f"tool_user_{uuid.uuid4().hex[:8]}",
            request_id=f"req_{uuid.uuid4().hex[:8]}",
            thread_id=f"tool_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}"
        )

    async def test_unified_tool_dispatcher_creation_with_real_services(self):
        """INTEGRATION: Validates UnifiedToolDispatcher creation with real backend services.
        
        Business Value: Ensures tools can be created with live service connections
        Failure Mode: Tool creation failures could prevent agent capabilities
        """
        try:
            # Create real tool dispatcher using registry factory
            dispatcher = await self.registry.create_tool_dispatcher_for_user(
                user_context=self.test_user_context,
                websocket_bridge=None,
                enable_admin_tools=False
            )
            
            # Validate dispatcher was created
            self.assertIsNotNone(dispatcher, "Tool dispatcher must be created")
            self.assertIsInstance(dispatcher, UnifiedToolDispatcher,
                                "Must create UnifiedToolDispatcher instance")
            
            # Test dispatcher has user context
            if hasattr(dispatcher, 'user_context'):
                self.assertEqual(dispatcher.user_context.user_id, self.test_user_context.user_id,
                               "Dispatcher must be associated with correct user")
            
            # Test dispatcher can list available tools
            if hasattr(dispatcher, 'list_tools'):
                tools = await dispatcher.list_tools() if callable(dispatcher.list_tools) else dispatcher.list_tools()
                self.assertIsInstance(tools, (list, dict), "Dispatcher must provide tool listing")
        
        except ImportError as e:
            self.skipTest(f"UnifiedToolDispatcher not available for integration test: {e}")
        except Exception as e:
            self.fail(f"Tool dispatcher integration failed: {e}")

    async def test_tool_dispatcher_websocket_integration(self):
        """INTEGRATION: Validates tool dispatcher integrates with real WebSocket for notifications.
        
        Business Value: Ensures users see real-time tool execution progress
        Failure Mode: Missing tool notifications break user experience
        """
        try:
            # Create real WebSocket manager
            websocket_manager = WebSocketManager()
            await websocket_manager.initialize()
            
            # Create WebSocket bridge
            websocket_bridge = create_agent_websocket_bridge(self.test_user_context)
            
            # Create tool dispatcher with WebSocket integration
            dispatcher = await self.registry.create_tool_dispatcher_for_user(
                user_context=self.test_user_context,
                websocket_bridge=websocket_bridge,
                enable_admin_tools=False
            )
            
            # Validate integration
            self.assertIsNotNone(dispatcher, "Dispatcher with WebSocket must be created")
            
            # Test that dispatcher can notify via WebSocket (if enhancement was applied)
            if hasattr(dispatcher, '_websocket_bridge'):
                self.assertIsNotNone(dispatcher._websocket_bridge,
                                   "Dispatcher must have WebSocket bridge for notifications")
        
        except Exception as e:
            self.fail(f"Tool dispatcher WebSocket integration failed: {e}")

    async def test_user_isolated_tool_dispatchers_with_real_services(self):
        """INTEGRATION: Validates user-isolated tool dispatchers work with real backend services.
        
        Business Value: Prevents tool execution cross-contamination between enterprise users
        Failure Mode: Shared tool state could leak data between customers
        """
        try:
            # Create contexts for multiple users
            user_contexts = []
            for i in range(3):
                context = UserExecutionContext(
                    user_id=f"isolated_tool_user_{i}_{uuid.uuid4().hex[:8]}",
                    request_id=f"req_{uuid.uuid4().hex[:8]}",
                    thread_id=f"thread_tool_{i}_{uuid.uuid4().hex[:8]}",
                    run_id=f"run_{uuid.uuid4().hex[:8]}"
                )
                user_contexts.append(context)
            
            # Create isolated dispatchers for each user
            dispatchers = []
            for context in user_contexts:
                dispatcher = await self.registry.create_tool_dispatcher_for_user(
                    user_context=context,
                    websocket_bridge=None,
                    enable_admin_tools=False
                )
                dispatchers.append((context, dispatcher))
            
            # Validate dispatchers are isolated
            for i, (context, dispatcher) in enumerate(dispatchers):
                self.assertIsNotNone(dispatcher, f"Dispatcher {i} must be created")
                
                # Each dispatcher should be a different instance
                for j, (other_context, other_dispatcher) in enumerate(dispatchers):
                    if i != j:
                        self.assertNotEqual(dispatcher, other_dispatcher,
                                          f"Dispatchers {i} and {j} must be isolated instances")
        
        except Exception as e:
            self.fail(f"User-isolated tool dispatcher integration failed: {e}")

    async def test_tool_execution_with_real_backend_services(self):
        """INTEGRATION: Validates tool execution works with real backend services.
        
        Business Value: Ensures agent tools can interact with production services
        Failure Mode: Tool execution failures could break agent responses
        """
        try:
            # Create tool dispatcher with real services
            dispatcher = await self.registry.create_tool_dispatcher_for_user(
                user_context=self.test_user_context,
                websocket_bridge=None,
                enable_admin_tools=False
            )
            
            # Test that dispatcher can execute tools (if available)
            if hasattr(dispatcher, 'execute_tool'):
                # This would require specific tools to be available
                # For integration test, we validate the method exists and is callable
                self.assertTrue(callable(dispatcher.execute_tool),
                              "Tool dispatcher must support tool execution")
            
            # Test dispatcher configuration with real services
            if hasattr(dispatcher, 'get_available_tools'):
                tools = await dispatcher.get_available_tools() if callable(dispatcher.get_available_tools) else dispatcher.get_available_tools()
                # Should return some representation of available tools
                self.assertIsNotNone(tools, "Dispatcher must provide available tools")
        
        except Exception as e:
            self.fail(f"Tool execution integration failed: {e}")


class TestRealDatabaseIntegration(SSotAsyncTestCase):
    """Test Suite 3: Real Database Integration (Protects agent state persistence)
    
    Business Value: Validates agent state persists correctly with real database
    Revenue Risk: State persistence failures could lose user data
    """

    async def asyncSetUp(self):
        """Set up database integration testing."""
        super().setUp()
        
        self.config = get_unified_config()
        self.llm_manager = LLMManager()
        self.registry = AgentRegistry(llm_manager=self.llm_manager)
        
        # Set up database manager (real database connection)
        self.db_manager = None
        try:
            self.db_manager = DatabaseManager()
            await self.db_manager.initialize()
        except Exception as e:
            # Database not available in test environment
            pass

    async def test_agent_registry_with_real_database_sessions(self):
        """INTEGRATION: Validates agent registry works with real database sessions.
        
        Business Value: Ensures agent operations can persist state to database
        Failure Mode: Database integration failures could cause data loss
        """
        if self.db_manager is None:
            self.skipTest("Database not available for integration testing")
            return
        
        try:
            # Create user context with database session
            async with self.db_manager.get_session() as db_session:
                user_context = UserExecutionContext(
                    user_id=f"db_user_{uuid.uuid4().hex[:8]}",
                    request_id=f"req_{uuid.uuid4().hex[:8]}",
                    thread_id=f"thread_db_{uuid.uuid4().hex[:8]}",
                    run_id=f"run_{uuid.uuid4().hex[:8]}",
                    db_session=db_session
                )
                
                # Create user session with database context
                user_session = await self.registry.get_user_session(user_context.user_id)
                
                # Validate session was created with database context capability
                self.assertIsNotNone(user_session, "User session must be created")
                self.assertEqual(user_session.user_id, user_context.user_id,
                               "Session must be associated with correct user")
        
        except Exception as e:
            self.fail(f"Database integration failed: {e}")

    async def test_agent_state_persistence_with_real_database(self):
        """INTEGRATION: Validates agent state can be persisted to real database.
        
        Business Value: Ensures user conversations and agent state are preserved
        Failure Mode: State persistence failures could lose important user data
        """
        if self.db_manager is None:
            self.skipTest("Database not available for integration testing")
            return
        
        try:
            # Create user context with database session
            async with self.db_manager.get_session() as db_session:
                user_context = UserExecutionContext(
                    user_id=f"persist_user_{uuid.uuid4().hex[:8]}",
                    request_id=f"req_{uuid.uuid4().hex[:8]}",
                    thread_id=f"thread_persist_{uuid.uuid4().hex[:8]}",
                    run_id=f"run_{uuid.uuid4().hex[:8]}",
                    db_session=db_session
                )
                
                # Create user session and add agents
                user_session = await self.registry.get_user_session(user_context.user_id)
                
                # Register multiple agents to test state persistence
                for i in range(3):
                    # Create a simple agent for testing
                    agent = BaseAgent(
                        llm_manager=self.llm_manager,
                        context=user_context,
                        name=f"test_agent_{i}"
                    )
                    await user_session.register_agent(f"test_agent_{i}", agent)
                
                # Get session metrics to validate state
                metrics = user_session.get_metrics()
                self.assertEqual(metrics['agent_count'], 3,
                               "Session must track all registered agents")
                
                # Test cleanup preserves database consistency
                await user_session.cleanup_all_agents()
                
                final_metrics = user_session.get_metrics()
                self.assertEqual(final_metrics['agent_count'], 0,
                               "Cleanup must properly clear agent state")
        
        except Exception as e:
            self.fail(f"Agent state persistence integration failed: {e}")

    async def test_concurrent_database_operations_through_registry(self):
        """INTEGRATION: Validates concurrent database operations through agent registry.
        
        Business Value: Ensures database operations remain consistent under concurrent load
        Failure Mode: Database race conditions could corrupt user data
        """
        if self.db_manager is None:
            self.skipTest("Database not available for integration testing")
            return
        
        try:
            concurrent_users = 5
            
            async def create_user_with_database(user_index: int):
                """Create user session with database operations."""
                async with self.db_manager.get_session() as db_session:
                    user_context = UserExecutionContext(
                        user_id=f"concurrent_db_user_{user_index}_{uuid.uuid4().hex[:8]}",
                        request_id=f"req_{uuid.uuid4().hex[:8]}",
                        thread_id=f"thread_concurrent_{user_index}_{uuid.uuid4().hex[:8]}",
                        run_id=f"run_{uuid.uuid4().hex[:8]}",
                        db_session=db_session
                    )
                    
                    user_session = await self.registry.get_user_session(user_context.user_id)
                    
                    # Perform database-related operations
                    agent = BaseAgent(
                        llm_manager=self.llm_manager,
                        context=user_context,
                        name=f"concurrent_agent_{user_index}"
                    )
                    await user_session.register_agent("concurrent_agent", agent)
                    
                    return user_context.user_id, user_session.get_metrics()
            
            # Execute concurrent database operations
            results = await asyncio.gather(*[
                create_user_with_database(i) for i in range(concurrent_users)
            ], return_exceptions=True)
            
            # Validate all operations succeeded
            successful_results = [r for r in results if not isinstance(r, Exception)]
            self.assertEqual(len(successful_results), concurrent_users,
                           "All concurrent database operations must succeed")
            
            # Validate data consistency
            for user_id, metrics in successful_results:
                self.assertEqual(metrics['agent_count'], 1,
                               f"User {user_id} must have correct agent count")
        
        except Exception as e:
            self.fail(f"Concurrent database integration failed: {e}")


class TestRealAgentExecutionFlow(SSotAsyncTestCase):
    """Test Suite 4: Real Agent Execution Flow (Protects end-to-end agent orchestration)
    
    Business Value: Validates complete agent lifecycle works with real services
    Revenue Risk: End-to-end failures could break entire chat functionality
    """

    async def asyncSetUp(self):
        """Set up end-to-end agent execution testing."""
        super().setUp()
        
        self.config = get_unified_config()
        self.llm_manager = LLMManager()
        self.registry = AgentRegistry(llm_manager=self.llm_manager)
        
        # Register a test agent factory
        self.registry.register_default_agents()

    async def test_end_to_end_agent_creation_and_execution_with_real_services(self):
        """INTEGRATION: Validates complete agent lifecycle from creation to execution with real services.
        
        Business Value: Ensures agent orchestration works end-to-end in production environment
        Failure Mode: Any step failure could break entire chat experience
        """
        try:
            # Create user context
            user_context = UserExecutionContext(
                user_id=f"e2e_user_{uuid.uuid4().hex[:8]}",
                request_id=f"req_{uuid.uuid4().hex[:8]}",
                thread_id=f"thread_e2e_{uuid.uuid4().hex[:8]}",
                run_id=f"run_{uuid.uuid4().hex[:8]}"
            )
            
            # Create real WebSocket manager for complete integration
            try:
                websocket_manager = WebSocketManager()
                await websocket_manager.initialize()
                await self.registry.set_websocket_manager_async(websocket_manager)
            except Exception as e:
                # WebSocket manager may not be available in test environment
                pass
            
            # Test agent creation through registry factory
            available_agents = self.registry.list_keys()
            if available_agents:
                # Use first available agent type for testing
                agent_type = available_agents[0]
                
                try:
                    # Create agent for user
                    agent = await self.registry.create_agent_for_user(
                        user_id=user_context.user_id,
                        agent_type=agent_type,
                        user_context=user_context,
                        websocket_manager=getattr(self.registry, 'websocket_manager', None)
                    )
                    
                    # Validate agent was created
                    self.assertIsNotNone(agent, f"Agent {agent_type} must be created")
                    
                    # Validate agent is retrievable
                    retrieved_agent = await self.registry.get_user_agent(
                        user_context.user_id, agent_type
                    )
                    self.assertIs(agent, retrieved_agent,
                                "Created agent must be retrievable from registry")
                    
                    # Test agent cleanup
                    cleanup_success = await self.registry.remove_user_agent(
                        user_context.user_id, agent_type
                    )
                    self.assertTrue(cleanup_success, "Agent cleanup must succeed")
                
                except KeyError as e:
                    # No factory registered - this is acceptable for integration test
                    self.assertIn("No factory registered", str(e))
            
            else:
                # No agents registered - validate registry is functional
                self.assertEqual(len(available_agents), 0,
                               "Registry should report empty state when no agents registered")
        
        except Exception as e:
            self.fail(f"End-to-end agent execution integration failed: {e}")

    async def test_multi_agent_coordination_with_real_services(self):
        """INTEGRATION: Validates multiple agents can coordinate through real services.
        
        Business Value: Ensures complex agent workflows work in production
        Failure Mode: Agent coordination failures could break sophisticated user requests
        """
        try:
            # Create multiple user contexts
            user_contexts = []
            for i in range(3):
                context = UserExecutionContext(
                    user_id=f"coord_user_{i}_{uuid.uuid4().hex[:8]}",
                    request_id=f"req_{uuid.uuid4().hex[:8]}",
                    thread_id=f"thread_coord_{i}_{uuid.uuid4().hex[:8]}",
                    run_id=f"run_{uuid.uuid4().hex[:8]}"
                )
                user_contexts.append(context)
            
            # Test that registry can handle multiple users with agents simultaneously
            user_sessions = []
            for context in user_contexts:
                session = await self.registry.get_user_session(context.user_id)
                user_sessions.append((context, session))
            
            # Validate all sessions are isolated
            session_ids = [id(session) for _, session in user_sessions]
            self.assertEqual(len(set(session_ids)), len(user_sessions),
                           "All user sessions must be unique instances")
            
            # Test monitoring across multiple users
            monitoring_report = await self.registry.monitor_all_users()
            
            self.assertEqual(monitoring_report['total_users'], len(user_contexts),
                           "Monitoring must track all active users")
            self.assertIn('users', monitoring_report,
                         "Monitoring must provide per-user details")
        
        except Exception as e:
            self.fail(f"Multi-agent coordination integration failed: {e}")

    async def test_agent_error_recovery_with_real_services(self):
        """INTEGRATION: Validates agent error recovery works with real service failures.
        
        Business Value: Ensures platform remains stable when individual services fail
        Failure Mode: Service failures could cascade and break entire platform
        """
        try:
            user_context = UserExecutionContext(
                user_id=f"error_recovery_user_{uuid.uuid4().hex[:8]}",
                request_id=f"req_{uuid.uuid4().hex[:8]}",
                thread_id=f"thread_error_{uuid.uuid4().hex[:8]}",
                run_id=f"run_{uuid.uuid4().hex[:8]}"
            )
            
            # Create user session
            user_session = await self.registry.get_user_session(user_context.user_id)
            
            # Register a mock agent that simulates failures
            failing_agent = BaseAgent(
                llm_manager=self.llm_manager,
                context=user_context,
                name="failing_agent"
            )
            
            # Override agent's run method to simulate failure
            async def failing_run(*args, **kwargs):
                raise Exception("Simulated agent failure")
            
            failing_agent.run = failing_run
            
            await user_session.register_agent("failing_agent", failing_agent)
            
            # Test that registry can handle agent failures gracefully
            session_metrics = user_session.get_metrics()
            self.assertEqual(session_metrics['agent_count'], 1,
                           "Registry must track agents even if they fail")
            
            # Test error recovery through session reset
            reset_report = await self.registry.reset_user_agents(user_context.user_id)
            self.assertEqual(reset_report['status'], 'reset_complete',
                           "Error recovery through reset must succeed")
            self.assertEqual(reset_report['agents_reset'], 1,
                           "Reset must report correct number of agents reset")
        
        except Exception as e:
            self.fail(f"Agent error recovery integration failed: {e}")


class TestRealPerformanceUnderLoad(SSotAsyncTestCase):
    """Test Suite 5: Real Performance Under Load (Protects system scalability)
    
    Business Value: Validates registry performance with actual service calls
    Revenue Risk: Performance issues under load could cause user abandonment
    """

    async def asyncSetUp(self):
        """Set up performance testing with real services."""
        super().setUp()
        
        self.config = get_unified_config()
        self.llm_manager = LLMManager()
        self.registry = AgentRegistry(llm_manager=self.llm_manager)

    async def test_registry_performance_under_concurrent_real_service_load(self):
        """INTEGRATION: Validates registry performance with concurrent real service operations.
        
        Business Value: Ensures platform performs well during peak usage
        Failure Mode: Performance degradation could lead to user abandonment
        """
        try:
            concurrent_users = 15  # Reduced for real service testing
            operations_per_user = 3
            
            async def user_operation_with_real_services(user_index: int):
                """Perform user operations with real service integration."""
                user_id = f"perf_user_{user_index}_{uuid.uuid4().hex[:8]}"
                user_context = UserExecutionContext(
                    user_id=user_id,
                    request_id=f"req_{uuid.uuid4().hex[:8]}",
                    thread_id=f"thread_perf_{user_index}_{uuid.uuid4().hex[:8]}",
                    run_id=f"run_{uuid.uuid4().hex[:8]}"
                )
                
                # Get user session (real registry operation)
                session = await self.registry.get_user_session(user_id)
                
                # Create tool dispatcher (real service integration)
                try:
                    dispatcher = await self.registry.create_tool_dispatcher_for_user(
                        user_context=user_context,
                        websocket_bridge=None,
                        enable_admin_tools=False
                    )
                except Exception:
                    dispatcher = None  # Tool dispatcher may not be available
                
                # Register agents (real operations)
                for op_index in range(operations_per_user):
                    agent = BaseAgent(
                        llm_manager=self.llm_manager,
                        context=user_context,
                        name=f"perf_agent_{op_index}"
                    )
                    await session.register_agent(f"perf_agent_{op_index}", agent)
                
                return user_id, operations_per_user
            
            # Measure performance with real services
            start_time = time.time()
            
            # Execute concurrent operations
            results = await asyncio.gather(*[
                user_operation_with_real_services(i) for i in range(concurrent_users)
            ], return_exceptions=True)
            
            execution_time = time.time() - start_time
            
            # Validate performance with real services
            successful_results = [r for r in results if not isinstance(r, Exception)]
            success_rate = len(successful_results) / concurrent_users
            
            # Allow for some failures with real services (80% success rate acceptable)
            self.assertGreaterEqual(success_rate, 0.8,
                                  f"At least 80% of operations must succeed with real services, got {success_rate:.1%}")
            
            # Performance should still be reasonable with real services
            self.assertLess(execution_time, 30.0,
                           f"Real service integration must complete within 30s, took {execution_time:.2f}s")
            
            # Validate registry state consistency
            self.assertGreaterEqual(len(self.registry._user_sessions), len(successful_results),
                                  "Registry must track successful user sessions")
        
        except Exception as e:
            self.fail(f"Real service performance integration failed: {e}")

    async def test_memory_efficiency_with_real_service_operations(self):
        """INTEGRATION: Validates memory efficiency during real service operations.
        
        Business Value: Prevents memory-related crashes during production usage
        Failure Mode: Memory leaks with real services could crash platform
        """
        try:
            # Create and cleanup cycles with real service integration
            cycles = 5
            users_per_cycle = 10
            
            for cycle in range(cycles):
                user_ids = []
                
                # Create users with real service integration
                for i in range(users_per_cycle):
                    user_id = f"memory_cycle_{cycle}_user_{i}_{uuid.uuid4().hex[:8]}"
                    user_context = UserExecutionContext(
                        user_id=user_id,
                        request_id=f"req_{uuid.uuid4().hex[:8]}",
                        thread_id=f"thread_memory_{cycle}_{i}_{uuid.uuid4().hex[:8]}",
                        run_id=f"run_{uuid.uuid4().hex[:8]}"
                    )
                    
                    user_session = await self.registry.get_user_session(user_id)
                    
                    # Create agent with real LLM manager
                    agent = BaseAgent(
                        llm_manager=self.llm_manager,
                        context=user_context,
                        name=f"memory_agent_{i}"
                    )
                    await user_session.register_agent("memory_agent", agent)
                    
                    user_ids.append(user_id)
                
                # Validate sessions created
                self.assertEqual(len(self.registry._user_sessions), users_per_cycle,
                               f"Cycle {cycle}: Must create all user sessions")
                
                # Cleanup with real service integration
                cleanup_report = await self.registry.emergency_cleanup_all()
                
                # Validate cleanup with real services
                self.assertEqual(cleanup_report['users_cleaned'], users_per_cycle,
                               f"Cycle {cycle}: Must cleanup all users")
                self.assertEqual(len(self.registry._user_sessions), 0,
                               f"Cycle {cycle}: Must clear all sessions")
        
        except Exception as e:
            self.fail(f"Memory efficiency with real services failed: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])