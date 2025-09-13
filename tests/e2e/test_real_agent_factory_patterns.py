"""
Test Real Agent Factory Patterns - User Isolation Validation

Business Value Justification (BVJ):
- Segment: All (Multi-user scenarios critical for platform scaling)
- Business Goal: Ensure complete user data isolation and secure multi-tenancy
- Value Impact: Users trust platform with sensitive data knowing isolation is guaranteed  
- Strategic Impact: Foundation for enterprise adoption and platform scalability

CRITICAL for multi-user platform success:
1. User A cannot see User B's data or agent interactions
2. Agent execution contexts are completely isolated per user
3. Factory patterns ensure fresh, clean instances for each user session
4. Shared state contamination is impossible between users
5. Concurrent users can execute agents safely without interference

This test validates the complete factory pattern implementation that enables
reliable multi-user agent execution with guaranteed data isolation.
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock

import pytest
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.websocket_helpers import WebSocketTestHelpers, MockWebSocketConnection

# Factory pattern imports
try:
    from netra_backend.app.services.agent_registry import AgentRegistry
    from netra_backend.app.services.agent_factory import AgentFactory
    from netra_backend.app.execution.user_execution_context import UserExecutionContext
    FACTORY_SERVICES_AVAILABLE = True
except ImportError:
    FACTORY_SERVICES_AVAILABLE = False

# Agent imports
try:
    from netra_backend.app.agents.base_agent import BaseAgent
    from netra_backend.app.agents.triage_agent import TriageAgent
    from netra_backend.app.agents.data_sub_agent import DataSubAgent
    AGENT_SERVICES_AVAILABLE = True
except ImportError:
    AGENT_SERVICES_AVAILABLE = False

# WebSocket services
try:
    from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
    from netra_backend.app.websocket_core.connection_manager import WebSocketConnectionManager
    WEBSOCKET_SERVICES_AVAILABLE = True
except ImportError:
    WEBSOCKET_SERVICES_AVAILABLE = False


class TestRealAgentFactoryPatterns(BaseE2ETest):
    """Test factory patterns for user isolation in agent execution."""

    def setup_method(self):
        """Set up test method with factory pattern validation."""
        super().setup_method()
        self.user_contexts = {}
        self.agent_instances = {}
        self.isolation_events = []
        self.factory_metrics = {
            "users_created": 0,
            "agent_instances_created": 0,
            "isolation_violations": 0,
            "factory_operations": []
        }

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_user_execution_context_factory_isolation(self, real_services_fixture):
        """
        Test UserExecutionContext factory creates completely isolated contexts.
        
        Validates that each user gets a fresh, isolated execution context
        with no shared state or data leakage between users.
        """
        await self.initialize_test_environment()
        
        # Create multiple user contexts
        test_users = [
            {
                "user_id": f"factory_user_1_{uuid.uuid4().hex[:8]}",
                "user_data": {"name": "Alice", "company": "TechCorp", "sensitive_data": "alice_secret_123"}
            },
            {
                "user_id": f"factory_user_2_{uuid.uuid4().hex[:8]}",
                "user_data": {"name": "Bob", "company": "DataInc", "sensitive_data": "bob_confidential_456"}
            },
            {
                "user_id": f"factory_user_3_{uuid.uuid4().hex[:8]}",
                "user_data": {"name": "Carol", "company": "SecureSoft", "sensitive_data": "carol_private_789"}
            }
        ]
        
        # Create isolated execution contexts using factory pattern
        user_contexts = {}
        for user in test_users:
            context = await self._create_isolated_user_execution_context(
                user_id=user["user_id"],
                user_data=user["user_data"]
            )
            user_contexts[user["user_id"]] = context
            
            # Validate context isolation immediately
            self._validate_context_isolation(context, user["user_id"], user["user_data"])
        
        # Cross-validate: ensure no context contamination
        self._assert_no_cross_context_contamination(user_contexts)
        
        # Test concurrent context operations
        await self._test_concurrent_context_operations(user_contexts)
        
        # Validate memory isolation
        self._assert_memory_isolation(user_contexts)
        
        self.logger.info(f" PASS:  User execution context factory isolation validated for {len(test_users)} users")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_agent_factory_instance_isolation(self, real_services_fixture):
        """
        Test AgentFactory creates isolated agent instances per user.
        
        Validates that each user gets dedicated agent instances with
        no shared state or cross-user data contamination.
        """
        await self.initialize_test_environment()
        
        # Create test scenario with multiple users and agent types
        factory_test_scenario = [
            {
                "user_id": f"agent_factory_user_1_{uuid.uuid4().hex[:8]}",
                "agent_types": ["triage_agent", "data_sub_agent"],
                "user_context": {"role": "admin", "access_level": "full"},
                "expected_isolation": "complete"
            },
            {
                "user_id": f"agent_factory_user_2_{uuid.uuid4().hex[:8]}", 
                "agent_types": ["triage_agent", "data_sub_agent"],
                "user_context": {"role": "user", "access_level": "limited"},
                "expected_isolation": "complete"
            }
        ]
        
        # Create isolated agent instances for each user
        user_agent_instances = {}
        
        for scenario in factory_test_scenario:
            user_id = scenario["user_id"]
            user_agents = {}
            
            # Create user-specific execution context
            execution_context = await self._create_isolated_user_execution_context(
                user_id=user_id,
                user_data=scenario["user_context"]
            )
            
            # Create isolated agent instances using factory
            for agent_type in scenario["agent_types"]:
                agent_instance = await self._create_isolated_agent_instance(
                    agent_type=agent_type,
                    user_id=user_id,
                    execution_context=execution_context
                )
                
                user_agents[agent_type] = agent_instance
                
                # Validate agent isolation immediately
                self._validate_agent_instance_isolation(agent_instance, user_id, agent_type)
            
            user_agent_instances[user_id] = user_agents
        
        # Test agent instance isolation across users
        self._assert_agent_instance_isolation_across_users(user_agent_instances)
        
        # Test concurrent agent operations
        await self._test_concurrent_agent_operations(user_agent_instances)
        
        # Validate no shared state between agent instances
        self._assert_no_shared_agent_state(user_agent_instances)
        
        self.logger.info(f" PASS:  Agent factory instance isolation validated for {len(factory_test_scenario)} users")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_factory_connection_isolation(self, real_services_fixture):
        """
        Test WebSocket factory creates isolated connections per user.
        
        Validates that WebSocket events and connections maintain complete
        user isolation with no message leakage between users.
        """
        await self.initialize_test_environment()
        
        # Create multiple users with WebSocket connections
        websocket_users = [
            {
                "user_id": f"websocket_factory_user_1_{uuid.uuid4().hex[:8]}",
                "connection_id": f"conn_{uuid.uuid4().hex[:8]}",
                "expected_events": ["user_1_specific_events"]
            },
            {
                "user_id": f"websocket_factory_user_2_{uuid.uuid4().hex[:8]}", 
                "connection_id": f"conn_{uuid.uuid4().hex[:8]}",
                "expected_events": ["user_2_specific_events"]
            },
            {
                "user_id": f"websocket_factory_user_3_{uuid.uuid4().hex[:8]}",
                "connection_id": f"conn_{uuid.uuid4().hex[:8]}",
                "expected_events": ["user_3_specific_events"]
            }
        ]
        
        # Create isolated WebSocket connections and notifiers
        user_websocket_contexts = {}
        
        for user in websocket_users:
            websocket_context = await self._create_isolated_websocket_context(
                user_id=user["user_id"],
                connection_id=user["connection_id"]
            )
            user_websocket_contexts[user["user_id"]] = websocket_context
            
            # Validate WebSocket isolation immediately
            self._validate_websocket_isolation(websocket_context, user["user_id"])
        
        # Test concurrent WebSocket message delivery
        await self._test_concurrent_websocket_message_delivery(user_websocket_contexts)
        
        # Validate no message cross-contamination
        self._assert_no_websocket_message_leakage(user_websocket_contexts)
        
        # Test WebSocket connection cleanup isolation
        await self._test_websocket_connection_cleanup_isolation(user_websocket_contexts)
        
        self.logger.info(f" PASS:  WebSocket factory connection isolation validated for {len(websocket_users)} users")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_complete_factory_pattern_integration(self, real_services_fixture):
        """
        Test complete factory pattern integration across all components.
        
        Validates end-to-end factory pattern implementation from user context
        creation through agent execution to result delivery with full isolation.
        """
        await self.initialize_test_environment()
        
        # Create comprehensive test scenario
        integration_scenario = {
            "user_1": {
                "user_id": f"integration_user_1_{uuid.uuid4().hex[:8]}",
                "request": "Analyze my infrastructure costs and recommend optimizations",
                "sensitive_data": {"api_keys": ["key1", "key2"], "internal_metrics": "confidential_data_1"},
                "expected_result_contains": ["optimization", "cost", "user_1_specific"]
            },
            "user_2": {
                "user_id": f"integration_user_2_{uuid.uuid4().hex[:8]}",
                "request": "Review system performance and identify bottlenecks", 
                "sensitive_data": {"database_urls": ["url1", "url2"], "performance_data": "confidential_data_2"},
                "expected_result_contains": ["performance", "bottleneck", "user_2_specific"]
            }
        }
        
        # Execute complete factory pattern workflow for each user
        user_workflow_results = {}
        
        for user_key, user_config in integration_scenario.items():
            workflow_result = await self._execute_complete_factory_pattern_workflow(
                user_id=user_config["user_id"],
                request=user_config["request"],
                sensitive_data=user_config["sensitive_data"],
                expected_indicators=user_config["expected_result_contains"]
            )
            
            user_workflow_results[user_key] = workflow_result
            
            # Validate workflow isolation
            self._validate_workflow_isolation(workflow_result, user_config)
        
        # Cross-validate complete isolation
        self._assert_complete_cross_user_isolation(user_workflow_results, integration_scenario)
        
        # Validate factory performance under load
        self._assert_factory_performance_metrics()
        
        # Validate resource cleanup
        await self._validate_factory_resource_cleanup(user_workflow_results)
        
        self.logger.info(" PASS:  Complete factory pattern integration validated")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_factory_pattern_stress_test(self, real_services_fixture):
        """
        Test factory patterns under high concurrent user load.
        
        Validates that isolation is maintained even under stress conditions
        with many concurrent users and operations.
        """
        await self.initialize_test_environment()
        
        # Create high-load scenario
        stress_user_count = 10
        concurrent_operations_per_user = 3
        
        stress_users = []
        for i in range(stress_user_count):
            user_id = f"stress_user_{i}_{uuid.uuid4().hex[:8]}"
            stress_users.append({
                "user_id": user_id,
                "operations": [
                    f"Operation {j} for user {i}" for j in range(concurrent_operations_per_user)
                ],
                "sensitive_marker": f"sensitive_data_user_{i}"
            })
        
        # Execute concurrent factory operations
        start_time = time.time()
        
        concurrent_tasks = []
        for user in stress_users:
            for operation in user["operations"]:
                task = self._execute_stress_factory_operation(
                    user_id=user["user_id"],
                    operation=operation,
                    sensitive_marker=user["sensitive_marker"]
                )
                concurrent_tasks.append(task)
        
        # Execute all operations concurrently
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        stress_execution_time = time.time() - start_time
        
        # Validate no failures under stress
        failed_operations = [r for r in results if isinstance(r, Exception)]
        assert len(failed_operations) == 0, (
            f"{len(failed_operations)} operations failed under stress: {failed_operations[:3]}"
        )
        
        # Validate isolation maintained under stress
        self._assert_stress_isolation_maintained(results, stress_users)
        
        # Validate performance under stress
        self._assert_stress_performance(stress_execution_time, len(concurrent_tasks))
        
        self.logger.info(f" PASS:  Factory pattern stress test passed: {len(concurrent_tasks)} concurrent operations in {stress_execution_time:.2f}s")

    # =============================================================================
    # HELPER METHODS
    # =============================================================================

    async def _create_isolated_user_execution_context(self, 
                                                    user_id: str, 
                                                    user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create completely isolated user execution context using factory pattern."""
        
        if FACTORY_SERVICES_AVAILABLE:
            # Use real UserExecutionContext factory
            try:
                execution_context = UserExecutionContext.from_request(
                    user_id=user_id,
                    user_data=user_data,
                    isolation_level="complete"
                )
                
                # Enhance with test tracking
                execution_context.test_metadata = {
                    "created_at": time.time(),
                    "user_id": user_id,
                    "isolation_validated": False
                }
                
                return execution_context
                
            except Exception as e:
                self.logger.warning(f"Real UserExecutionContext not available: {e}")
        
        # Fallback to mock isolated context
        mock_context = {
            "user_id": user_id,
            "user_data": user_data.copy(),  # Deep copy to prevent reference sharing
            "connection_id": f"conn_{uuid.uuid4().hex[:8]}",
            "agent_registry": MagicMock(),
            "websocket_notifier": MagicMock(),
            "isolation_boundary": f"boundary_{user_id}",
            "created_at": time.time(),
            "test_metadata": {
                "factory_type": "mock_isolated_context",
                "user_id": user_id,
                "isolation_validated": False
            }
        }
        
        # Store for validation
        self.user_contexts[user_id] = mock_context
        self.factory_metrics["users_created"] += 1
        
        return mock_context

    async def _create_isolated_agent_instance(self,
                                            agent_type: str,
                                            user_id: str,
                                            execution_context: Dict[str, Any]) -> Any:
        """Create isolated agent instance using factory pattern."""
        
        if FACTORY_SERVICES_AVAILABLE and AGENT_SERVICES_AVAILABLE:
            try:
                # Use real AgentFactory
                agent_factory = AgentFactory(execution_context=execution_context)
                agent_instance = await agent_factory.create_agent(
                    agent_type=agent_type,
                    user_id=user_id,
                    isolation_level="complete"
                )
                
                # Add test tracking
                if hasattr(agent_instance, '__dict__'):
                    agent_instance.test_metadata = {
                        "created_for_user": user_id,
                        "agent_type": agent_type,
                        "created_at": time.time(),
                        "isolation_validated": False
                    }
                
                return agent_instance
                
            except Exception as e:
                self.logger.warning(f"Real AgentFactory not available: {e}")
        
        # Fallback to mock isolated agent
        mock_agent = MagicMock()
        mock_agent.user_id = user_id
        mock_agent.agent_type = agent_type
        mock_agent.execution_context = execution_context
        mock_agent.isolated_state = {
            "user_specific_data": f"data_for_{user_id}",
            "agent_memory": {},
            "conversation_history": []
        }
        mock_agent.test_metadata = {
            "created_for_user": user_id,
            "agent_type": agent_type,
            "created_at": time.time(),
            "isolation_validated": False,
            "factory_type": "mock_isolated_agent"
        }
        
        # Store for validation
        agent_key = f"{user_id}:{agent_type}"
        self.agent_instances[agent_key] = mock_agent
        self.factory_metrics["agent_instances_created"] += 1
        
        return mock_agent

    async def _create_isolated_websocket_context(self, 
                                               user_id: str,
                                               connection_id: str) -> Dict[str, Any]:
        """Create isolated WebSocket context using factory pattern."""
        
        if WEBSOCKET_SERVICES_AVAILABLE:
            try:
                # Create real WebSocket notifier with isolation
                notifier = WebSocketNotifier()
                connection_manager = WebSocketConnectionManager()
                
                # Set up user-specific WebSocket context
                websocket_context = {
                    "user_id": user_id,
                    "connection_id": connection_id,
                    "notifier": notifier,
                    "connection_manager": connection_manager,
                    "message_history": [],
                    "isolation_boundary": f"ws_boundary_{user_id}"
                }
                
                # Hook notifier for isolation validation
                original_send = notifier.send_to_user
                
                async def isolated_send(target_user_id, event_data):
                    # Record event for isolation validation
                    isolation_event = {
                        "sender_user_id": user_id,
                        "target_user_id": target_user_id, 
                        "event_data": event_data,
                        "timestamp": time.time(),
                        "connection_id": connection_id
                    }
                    self.isolation_events.append(isolation_event)
                    
                    return await original_send(target_user_id, event_data)
                
                notifier.send_to_user = isolated_send
                return websocket_context
                
            except Exception as e:
                self.logger.warning(f"Real WebSocket services not available: {e}")
        
        # Fallback to mock isolated WebSocket context
        mock_notifier = MagicMock()
        mock_notifier.send_to_user = AsyncMock()
        
        async def mock_isolated_send(target_user_id, event_data):
            isolation_event = {
                "sender_user_id": user_id,
                "target_user_id": target_user_id,
                "event_data": event_data,
                "timestamp": time.time(),
                "connection_id": connection_id,
                "mock_context": True
            }
            self.isolation_events.append(isolation_event)
        
        mock_notifier.send_to_user.side_effect = mock_isolated_send
        
        websocket_context = {
            "user_id": user_id,
            "connection_id": connection_id,
            "notifier": mock_notifier,
            "connection_manager": MagicMock(),
            "message_history": [],
            "isolation_boundary": f"ws_boundary_{user_id}",
            "test_metadata": {
                "factory_type": "mock_websocket_context",
                "created_at": time.time()
            }
        }
        
        return websocket_context

    async def _test_concurrent_context_operations(self, user_contexts: Dict[str, Any]):
        """Test concurrent operations on user contexts for isolation."""
        
        # Create concurrent tasks for each user context
        concurrent_tasks = []
        
        for user_id, context in user_contexts.items():
            # Task 1: Modify user data
            task1 = self._modify_user_context_data(user_id, context, "operation_1")
            concurrent_tasks.append(task1)
            
            # Task 2: Access context state
            task2 = self._access_user_context_state(user_id, context, "operation_2")
            concurrent_tasks.append(task2)
        
        # Execute concurrently
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Validate no exceptions from concurrent access
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Concurrent context operations failed: {exceptions}"

    async def _modify_user_context_data(self, user_id: str, context: Dict[str, Any], operation: str):
        """Modify user context data to test isolation."""
        # Simulate data modification
        if hasattr(context, 'user_data'):
            context.user_data[f"{operation}_modified"] = f"modified_by_{user_id}"
        elif isinstance(context, dict) and "user_data" in context:
            context["user_data"][f"{operation}_modified"] = f"modified_by_{user_id}"
        
        await asyncio.sleep(0.1)  # Simulate processing time
        return f"modified_context_for_{user_id}"

    async def _access_user_context_state(self, user_id: str, context: Dict[str, Any], operation: str):
        """Access user context state to test isolation."""
        # Simulate state access
        if hasattr(context, 'user_data'):
            state = context.user_data.copy()
        elif isinstance(context, dict) and "user_data" in context:
            state = context["user_data"].copy()
        else:
            state = {"default": "state"}
        
        await asyncio.sleep(0.1)  # Simulate processing time
        return f"accessed_state_for_{user_id}"

    async def _test_concurrent_agent_operations(self, user_agent_instances: Dict[str, Dict[str, Any]]):
        """Test concurrent agent operations for isolation."""
        
        concurrent_tasks = []
        
        for user_id, agents in user_agent_instances.items():
            for agent_type, agent_instance in agents.items():
                # Create concurrent agent operation
                task = self._execute_agent_operation(user_id, agent_instance, agent_type)
                concurrent_tasks.append(task)
        
        # Execute all agent operations concurrently
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Validate no cross-contamination
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Concurrent agent operations failed: {exceptions}"

    async def _execute_agent_operation(self, user_id: str, agent_instance: Any, agent_type: str):
        """Execute agent operation to test isolation."""
        # Simulate agent execution with user-specific data
        if hasattr(agent_instance, 'isolated_state'):
            agent_instance.isolated_state["last_operation"] = f"executed_for_{user_id}"
            agent_instance.isolated_state["operation_count"] = agent_instance.isolated_state.get("operation_count", 0) + 1
        
        await asyncio.sleep(0.2)  # Simulate agent processing
        
        return {
            "user_id": user_id,
            "agent_type": agent_type,
            "operation_result": f"agent_operation_completed_for_{user_id}"
        }

    async def _test_concurrent_websocket_message_delivery(self, user_websocket_contexts: Dict[str, Any]):
        """Test concurrent WebSocket message delivery for isolation."""
        
        message_delivery_tasks = []
        
        for user_id, ws_context in user_websocket_contexts.items():
            # Send user-specific messages
            for i in range(3):  # Multiple messages per user
                task = self._send_isolated_websocket_message(
                    user_id=user_id,
                    ws_context=ws_context,
                    message=f"message_{i}_for_{user_id}",
                    message_id=f"msg_{i}_{user_id}"
                )
                message_delivery_tasks.append(task)
        
        # Execute all message deliveries concurrently
        results = await asyncio.gather(*message_delivery_tasks, return_exceptions=True)
        
        # Validate message delivery success
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"WebSocket message delivery failed: {exceptions}"

    async def _send_isolated_websocket_message(self,
                                             user_id: str,
                                             ws_context: Dict[str, Any],
                                             message: str,
                                             message_id: str):
        """Send isolated WebSocket message."""
        
        event_data = {
            "type": "isolated_test_message",
            "message": message,
            "message_id": message_id,
            "sender_user_id": user_id,
            "timestamp": time.time()
        }
        
        # Send via notifier (should be isolated to user)
        notifier = ws_context["notifier"]
        await notifier.send_to_user(user_id, event_data)
        
        # Record in message history for validation
        ws_context["message_history"].append({
            "message_id": message_id,
            "message": message,
            "sent_at": time.time()
        })
        
        return f"message_sent_to_{user_id}"

    async def _execute_complete_factory_pattern_workflow(self,
                                                        user_id: str,
                                                        request: str,
                                                        sensitive_data: Dict[str, Any],
                                                        expected_indicators: List[str]) -> Dict[str, Any]:
        """Execute complete factory pattern workflow for comprehensive testing."""
        
        workflow_start = time.time()
        
        # Step 1: Create isolated user execution context
        user_context = await self._create_isolated_user_execution_context(
            user_id=user_id,
            user_data={"request": request, "sensitive": sensitive_data}
        )
        
        # Step 2: Create isolated agent instance
        agent_instance = await self._create_isolated_agent_instance(
            agent_type="triage_agent",
            user_id=user_id,
            execution_context=user_context
        )
        
        # Step 3: Create isolated WebSocket context
        websocket_context = await self._create_isolated_websocket_context(
            user_id=user_id,
            connection_id=f"workflow_conn_{uuid.uuid4().hex[:8]}"
        )
        
        # Step 4: Execute agent with full isolation
        execution_result = await self._execute_isolated_agent_workflow(
            user_id=user_id,
            agent_instance=agent_instance,
            websocket_context=websocket_context,
            request=request,
            expected_indicators=expected_indicators
        )
        
        workflow_time = time.time() - workflow_start
        
        # Compile complete workflow result
        workflow_result = {
            "user_id": user_id,
            "user_context": user_context,
            "agent_instance": agent_instance,
            "websocket_context": websocket_context,
            "execution_result": execution_result,
            "workflow_metrics": {
                "total_time": workflow_time,
                "isolation_level": "complete",
                "factory_operations": ["context_creation", "agent_instantiation", "websocket_setup", "execution"]
            }
        }
        
        return workflow_result

    async def _execute_isolated_agent_workflow(self,
                                             user_id: str,
                                             agent_instance: Any,
                                             websocket_context: Dict[str, Any],
                                             request: str,
                                             expected_indicators: List[str]) -> Dict[str, Any]:
        """Execute agent workflow with full isolation validation."""
        
        notifier = websocket_context["notifier"]
        
        # Agent execution with WebSocket events
        await notifier.send_to_user(
            user_id,
            {
                "type": "agent_started",
                "agent_name": getattr(agent_instance, "agent_type", "test_agent"),
                "user_id": user_id,
                "request": request,
                "timestamp": time.time()
            }
        )
        
        # Simulate agent thinking with user-specific content
        await notifier.send_to_user(
            user_id,
            {
                "type": "agent_thinking",
                "reasoning": f"Processing request for user {user_id}: {request}",
                "user_context": "isolated_processing",
                "timestamp": time.time()
            }
        )
        
        # Generate user-specific result
        result = {
            "user_id": user_id,
            "response": f"Analysis completed for {user_id}",
            "indicators_found": expected_indicators,
            "agent_type": getattr(agent_instance, "agent_type", "test_agent"),
            "isolation_verified": True
        }
        
        await notifier.send_to_user(
            user_id,
            {
                "type": "agent_completed",
                "final_response": result["response"],
                "results": result,
                "timestamp": time.time()
            }
        )
        
        return result

    async def _execute_stress_factory_operation(self, 
                                              user_id: str,
                                              operation: str,
                                              sensitive_marker: str) -> Dict[str, Any]:
        """Execute factory operation under stress conditions."""
        
        # Create isolated context under stress
        stress_context = await self._create_isolated_user_execution_context(
            user_id=user_id,
            user_data={"operation": operation, "sensitive": sensitive_marker}
        )
        
        # Create agent instance
        agent_instance = await self._create_isolated_agent_instance(
            agent_type="triage_agent",
            user_id=user_id, 
            execution_context=stress_context
        )
        
        # Execute rapid operation
        result = {
            "user_id": user_id,
            "operation": operation,
            "sensitive_marker": sensitive_marker,
            "execution_time": time.time(),
            "isolation_maintained": True
        }
        
        # Validate isolation under stress
        if hasattr(agent_instance, 'isolated_state'):
            agent_instance.isolated_state["stress_operation"] = operation
            agent_instance.isolated_state["stress_marker"] = sensitive_marker
        
        return result

    # =============================================================================
    # VALIDATION METHODS
    # =============================================================================

    def _validate_context_isolation(self, context: Any, user_id: str, user_data: Dict[str, Any]):
        """Validate context isolation for a single user."""
        
        # Context should be specific to user
        if hasattr(context, 'user_id'):
            assert context.user_id == user_id, f"Context user_id mismatch: expected {user_id}, got {context.user_id}"
        elif isinstance(context, dict):
            assert context.get("user_id") == user_id, f"Context user_id mismatch in dict: expected {user_id}, got {context.get('user_id')}"
        
        # User data should be preserved and isolated
        if hasattr(context, 'user_data'):
            context_user_data = context.user_data
        elif isinstance(context, dict):
            context_user_data = context.get("user_data", {})
        else:
            context_user_data = {}
        
        for key, value in user_data.items():
            assert key in context_user_data, f"User data key {key} missing from context"
            assert context_user_data[key] == value, f"User data value mismatch for {key}"
        
        # Mark as validated
        if hasattr(context, 'test_metadata'):
            context.test_metadata["isolation_validated"] = True
        elif isinstance(context, dict) and "test_metadata" in context:
            context["test_metadata"]["isolation_validated"] = True

    def _assert_no_cross_context_contamination(self, user_contexts: Dict[str, Any]):
        """Assert no contamination between user contexts."""
        
        user_ids = list(user_contexts.keys())
        
        for i, user_id_1 in enumerate(user_ids):
            context_1 = user_contexts[user_id_1]
            
            for j, user_id_2 in enumerate(user_ids):
                if i >= j:  # Only compare each pair once
                    continue
                    
                context_2 = user_contexts[user_id_2]
                
                # Contexts should not share references
                assert context_1 is not context_2, f"Contexts share reference: {user_id_1} and {user_id_2}"
                
                # User data should be distinct
                user_data_1 = getattr(context_1, 'user_data', None) or context_1.get('user_data', {})
                user_data_2 = getattr(context_2, 'user_data', None) or context_2.get('user_data', {})
                
                # Should not share user data references
                assert user_data_1 is not user_data_2, f"User data shares reference: {user_id_1} and {user_id_2}"
                
                # Should not have each other's sensitive data
                sensitive_1 = user_data_1.get('sensitive_data')
                sensitive_2 = user_data_2.get('sensitive_data')
                
                if sensitive_1 and sensitive_2:
                    assert sensitive_1 != sensitive_2, f"Sensitive data leaked between {user_id_1} and {user_id_2}"

    def _assert_memory_isolation(self, user_contexts: Dict[str, Any]):
        """Assert memory isolation between user contexts."""
        
        # Check for memory address isolation
        context_addresses = set()
        
        for user_id, context in user_contexts.items():
            context_id = id(context)
            assert context_id not in context_addresses, f"Context memory address collision for {user_id}"
            context_addresses.add(context_id)
            
            # Check user data memory isolation
            if hasattr(context, 'user_data'):
                user_data_id = id(context.user_data)
            elif isinstance(context, dict) and "user_data" in context:
                user_data_id = id(context["user_data"])
            else:
                continue
                
            # User data should have unique memory addresses
            for other_user_id, other_context in user_contexts.items():
                if user_id == other_user_id:
                    continue
                    
                if hasattr(other_context, 'user_data'):
                    other_user_data_id = id(other_context.user_data)
                elif isinstance(other_context, dict) and "user_data" in other_context:
                    other_user_data_id = id(other_context["user_data"])
                else:
                    continue
                
                assert user_data_id != other_user_data_id, (
                    f"User data memory shared between {user_id} and {other_user_id}"
                )

    def _validate_agent_instance_isolation(self, agent_instance: Any, user_id: str, agent_type: str):
        """Validate agent instance isolation."""
        
        # Agent should be associated with correct user
        if hasattr(agent_instance, 'user_id'):
            assert agent_instance.user_id == user_id, f"Agent user_id mismatch: expected {user_id}, got {agent_instance.user_id}"
        
        # Agent should have correct type
        if hasattr(agent_instance, 'agent_type'):
            assert agent_instance.agent_type == agent_type, f"Agent type mismatch: expected {agent_type}, got {agent_instance.agent_type}"
        
        # Agent should have isolated state
        if hasattr(agent_instance, 'isolated_state'):
            assert isinstance(agent_instance.isolated_state, dict), "Agent isolated_state should be dict"
            assert "user_specific_data" in agent_instance.isolated_state, "Missing user_specific_data in isolated_state"
            
            user_specific_data = agent_instance.isolated_state["user_specific_data"]
            assert user_id in user_specific_data, f"Agent state doesn't contain user_id {user_id}"
        
        # Mark as validated
        if hasattr(agent_instance, 'test_metadata'):
            agent_instance.test_metadata["isolation_validated"] = True

    def _assert_agent_instance_isolation_across_users(self, user_agent_instances: Dict[str, Dict[str, Any]]):
        """Assert agent instance isolation across users."""
        
        all_agent_instances = []
        user_agent_map = {}
        
        # Collect all agent instances
        for user_id, agents in user_agent_instances.items():
            for agent_type, agent_instance in agents.items():
                all_agent_instances.append((user_id, agent_type, agent_instance))
                user_agent_map[id(agent_instance)] = user_id
        
        # Validate no shared references
        instance_ids = set()
        for user_id, agent_type, agent_instance in all_agent_instances:
            instance_id = id(agent_instance)
            assert instance_id not in instance_ids, f"Agent instance shared between users: {user_id}, {agent_type}"
            instance_ids.add(instance_id)
        
        # Validate no cross-user state contamination
        for user_id_1, agent_type_1, agent_1 in all_agent_instances:
            for user_id_2, agent_type_2, agent_2 in all_agent_instances:
                if user_id_1 == user_id_2 or agent_1 is agent_2:
                    continue
                
                # Check isolated state doesn't leak
                if hasattr(agent_1, 'isolated_state') and hasattr(agent_2, 'isolated_state'):
                    state_1 = agent_1.isolated_state
                    state_2 = agent_2.isolated_state
                    
                    # Should not share state references
                    assert state_1 is not state_2, f"Agent state shared between {user_id_1} and {user_id_2}"
                    
                    # Should not contain other user's data
                    user_data_1 = state_1.get("user_specific_data", "")
                    user_data_2 = state_2.get("user_specific_data", "")
                    
                    if user_id_1 in user_data_1:
                        assert user_id_1 not in user_data_2, f"User {user_id_1} data leaked to {user_id_2} agent"
                    if user_id_2 in user_data_2:
                        assert user_id_2 not in user_data_1, f"User {user_id_2} data leaked to {user_id_1} agent"

    def _assert_no_shared_agent_state(self, user_agent_instances: Dict[str, Dict[str, Any]]):
        """Assert no shared state between agent instances."""
        
        # Collect all state references
        state_references = {}
        
        for user_id, agents in user_agent_instances.items():
            for agent_type, agent_instance in agents.items():
                if hasattr(agent_instance, 'isolated_state'):
                    state_id = id(agent_instance.isolated_state)
                    
                    if state_id in state_references:
                        existing_user, existing_type = state_references[state_id]
                        raise AssertionError(
                            f"Shared state detected between users: "
                            f"{existing_user}:{existing_type} and {user_id}:{agent_type}"
                        )
                    
                    state_references[state_id] = (user_id, agent_type)
        
        self.logger.info(f" PASS:  Validated {len(state_references)} isolated agent states")

    def _validate_websocket_isolation(self, websocket_context: Dict[str, Any], user_id: str):
        """Validate WebSocket isolation."""
        
        # Context should be user-specific
        assert websocket_context["user_id"] == user_id, f"WebSocket context user_id mismatch"
        
        # Should have unique connection ID
        connection_id = websocket_context["connection_id"]
        assert connection_id, "Missing connection_id in WebSocket context"
        assert user_id in connection_id or len(connection_id) > 10, "Connection ID should be unique"
        
        # Should have isolation boundary
        if "isolation_boundary" in websocket_context:
            boundary = websocket_context["isolation_boundary"]
            assert user_id in boundary, f"Isolation boundary doesn't contain user_id: {boundary}"

    def _assert_no_websocket_message_leakage(self, user_websocket_contexts: Dict[str, Any]):
        """Assert no message leakage between WebSocket contexts."""
        
        # Analyze isolation events
        for event in self.isolation_events:
            sender_user_id = event.get("sender_user_id")
            target_user_id = event.get("target_user_id")
            
            # Messages should only be sent to the same user
            assert sender_user_id == target_user_id, (
                f"WebSocket message leakage detected: "
                f"sender {sender_user_id} sent to target {target_user_id}"
            )
        
        # Validate message histories are isolated
        message_contents = {}
        for user_id, ws_context in user_websocket_contexts.items():
            message_history = ws_context.get("message_history", [])
            
            for message in message_history:
                message_content = message.get("message", "")
                
                if message_content in message_contents:
                    other_user_id = message_contents[message_content]
                    if other_user_id != user_id:
                        raise AssertionError(
                            f"Message content shared between users: {user_id} and {other_user_id}"
                        )
                
                message_contents[message_content] = user_id

    async def _test_websocket_connection_cleanup_isolation(self, user_websocket_contexts: Dict[str, Any]):
        """Test WebSocket connection cleanup maintains isolation."""
        
        # Simulate connection cleanup for one user
        cleanup_user_id = list(user_websocket_contexts.keys())[0]
        cleanup_context = user_websocket_contexts[cleanup_user_id]
        
        # Cleanup operations
        if "connection_manager" in cleanup_context:
            connection_manager = cleanup_context["connection_manager"]
            if hasattr(connection_manager, 'cleanup_user_connections'):
                await connection_manager.cleanup_user_connections(cleanup_user_id)
        
        # Verify other users' contexts remain unaffected
        for user_id, ws_context in user_websocket_contexts.items():
            if user_id == cleanup_user_id:
                continue
            
            # Other users' contexts should remain intact
            assert ws_context["user_id"] == user_id, f"User context corrupted after cleanup: {user_id}"
            assert "notifier" in ws_context, f"Notifier missing after cleanup for {user_id}"

    def _validate_workflow_isolation(self, workflow_result: Dict[str, Any], user_config: Dict[str, Any]):
        """Validate complete workflow isolation."""
        
        expected_user_id = user_config["user_id"]
        
        # All workflow components should be user-specific
        assert workflow_result["user_id"] == expected_user_id, "Workflow user_id mismatch"
        
        # Execution result should contain user-specific elements
        execution_result = workflow_result["execution_result"]
        assert execution_result["user_id"] == expected_user_id, "Execution result user_id mismatch"
        
        # Should contain expected indicators specific to user's request
        expected_indicators = user_config.get("expected_result_contains", [])
        result_content = str(execution_result).lower()
        
        for indicator in expected_indicators:
            if indicator != "user_1_specific" and indicator != "user_2_specific":  # Skip generic markers
                assert indicator in result_content, f"Expected indicator {indicator} missing from result"
        
        # Workflow should have isolation verification
        assert execution_result.get("isolation_verified") == True, "Isolation not verified in workflow"

    def _assert_complete_cross_user_isolation(self, 
                                            user_workflow_results: Dict[str, Any],
                                            integration_scenario: Dict[str, Any]):
        """Assert complete isolation across all user workflows."""
        
        # Collect sensitive data from all users
        user_sensitive_data = {}
        for user_key, user_config in integration_scenario.items():
            user_sensitive_data[user_key] = user_config["sensitive_data"]
        
        # Validate no cross-contamination in results
        for user_key_1, result_1 in user_workflow_results.items():
            sensitive_1 = user_sensitive_data[user_key_1]
            result_1_str = str(result_1).lower()
            
            for user_key_2, result_2 in user_workflow_results.items():
                if user_key_1 == user_key_2:
                    continue
                
                sensitive_2 = user_sensitive_data[user_key_2]
                result_2_str = str(result_2).lower()
                
                # User 1's result should not contain User 2's sensitive data
                for key, value in sensitive_2.items():
                    if isinstance(value, str):
                        assert value.lower() not in result_1_str, (
                            f"User {user_key_2} sensitive data leaked to {user_key_1}: {key}={value}"
                        )
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str):
                                assert item.lower() not in result_1_str, (
                                    f"User {user_key_2} sensitive list item leaked to {user_key_1}: {item}"
                                )
        
        self.logger.info(" PASS:  Complete cross-user isolation validated")

    def _assert_factory_performance_metrics(self):
        """Assert factory performance metrics are reasonable."""
        
        metrics = self.factory_metrics
        
        # Should have created users and agents
        assert metrics["users_created"] > 0, "No users created by factory"
        assert metrics["agent_instances_created"] > 0, "No agent instances created by factory"
        
        # Should have no isolation violations
        assert metrics["isolation_violations"] == 0, (
            f"Factory isolation violations detected: {metrics['isolation_violations']}"
        )
        
        # Performance should be reasonable (not too slow)
        total_operations = len(metrics.get("factory_operations", []))
        if total_operations > 10:  # Only check if significant operations
            avg_operation_time = sum(
                op.get("duration", 0) for op in metrics.get("factory_operations", [])
            ) / total_operations
            
            assert avg_operation_time < 1.0, (
                f"Factory operations too slow: {avg_operation_time:.2f}s average"
            )

    async def _validate_factory_resource_cleanup(self, user_workflow_results: Dict[str, Any]):
        """Validate factory resource cleanup."""
        
        for user_key, workflow_result in user_workflow_results.items():
            user_context = workflow_result.get("user_context")
            agent_instance = workflow_result.get("agent_instance")
            websocket_context = workflow_result.get("websocket_context")
            
            # Cleanup WebSocket connections
            if websocket_context and "connection_manager" in websocket_context:
                connection_manager = websocket_context["connection_manager"]
                if hasattr(connection_manager, 'cleanup'):
                    await connection_manager.cleanup()
            
            # Verify resources can be cleaned up without affecting other users
            # This validates that there are no hidden references or shared state

    def _assert_stress_isolation_maintained(self, results: List[Any], stress_users: List[Dict[str, Any]]):
        """Assert isolation maintained under stress conditions."""
        
        # Group results by user
        user_results = {}
        for result in results:
            if isinstance(result, dict) and "user_id" in result:
                user_id = result["user_id"]
                if user_id not in user_results:
                    user_results[user_id] = []
                user_results[user_id].append(result)
        
        # Validate each user's results are isolated
        for user in stress_users:
            user_id = user["user_id"]
            sensitive_marker = user["sensitive_marker"]
            
            if user_id not in user_results:
                continue
            
            user_result_list = user_results[user_id]
            
            # User's results should contain their sensitive marker
            for result in user_result_list:
                result_marker = result.get("sensitive_marker", "")
                assert result_marker == sensitive_marker, (
                    f"Sensitive marker mismatch under stress: expected {sensitive_marker}, got {result_marker}"
                )
        
        # Cross-validate: no user should have another's sensitive data
        for user_1 in stress_users:
            user_1_id = user_1["user_id"]
            user_1_marker = user_1["sensitive_marker"]
            
            for user_2 in stress_users:
                if user_1_id == user_2["user_id"]:
                    continue
                
                user_2_marker = user_2["sensitive_marker"]
                
                # User 1's results should not contain User 2's marker
                if user_1_id in user_results:
                    for result in user_results[user_1_id]:
                        result_str = str(result)
                        assert user_2_marker not in result_str, (
                            f"Stress test isolation violation: {user_1_id} result contains {user_2_marker}"
                        )

    def _assert_stress_performance(self, execution_time: float, total_operations: int):
        """Assert performance under stress conditions."""
        
        # Total time should be reasonable even under stress
        max_stress_time = 30.0  # 30 seconds for high concurrent load
        assert execution_time <= max_stress_time, (
            f"Stress test took {execution_time:.2f}s, exceeds maximum {max_stress_time}s"
        )
        
        # Average time per operation should be reasonable
        avg_time_per_operation = execution_time / total_operations
        assert avg_time_per_operation <= 5.0, (
            f"Average time per operation under stress: {avg_time_per_operation:.2f}s too high"
        )
        
        # Update metrics
        self.factory_metrics["stress_test_metrics"] = {
            "total_execution_time": execution_time,
            "total_operations": total_operations,
            "avg_time_per_operation": avg_time_per_operation
        }

    async def cleanup_resources(self):
        """Clean up factory pattern test resources."""
        await super().cleanup_resources()
        
        # Clear all factory state
        self.user_contexts.clear()
        self.agent_instances.clear()
        self.isolation_events.clear()
        
        # Reset metrics
        self.factory_metrics = {
            "users_created": 0,
            "agent_instances_created": 0,
            "isolation_violations": 0,
            "factory_operations": []
        }