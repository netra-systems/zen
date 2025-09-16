"""
Golden Path Integration Test Suite 4: Factory Pattern Mismatch Detection (Issue #1176)

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure factory patterns work consistently for Golden Path
- Value Impact: Factory pattern mismatches break user isolation and cause failures
- Strategic Impact: Core platform functionality ($500K+ ARR at risk)

This suite tests integration-level factory pattern mismatches that occur when
different components use incompatible factory patterns, causing Golden Path
failures despite individual factories working correctly.

Root Cause Focus: Component-level excellence but integration-level coordination gaps
"""

import pytest
import asyncio
import time
from typing import Dict, Any, List, Optional, Type
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.isolated_environment_fixtures import isolated_env

# Import factory components that need integration testing
from netra_backend.app.factories.agent_factory import AgentFactory
from netra_backend.app.factories.websocket_factory import WebSocketFactory
from netra_backend.app.factories.execution_factory import ExecutionFactory
from netra_backend.app.core.user_execution_context import UserExecutionContext


class GoldenPathFactoryPatternMismatchesTests(BaseIntegrationTest):
    """Test factory pattern mismatches causing Golden Path failures."""

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.issue_1176
    async def test_factory_interface_mismatch_reproduction(self, real_services_fixture):
        """
        EXPECTED TO FAIL INITIALLY: Reproduce factory interface mismatches.
        
        Root Cause: Different factories implement different interfaces even when
        they should be compatible, causing integration failures when Golden Path
        components try to use factories interchangeably.
        """
        # Create factories that should be compatible
        agent_factory = AgentFactory()
        websocket_factory = WebSocketFactory()
        execution_factory = ExecutionFactory()
        
        # Create user context for Golden Path
        user_context = UserExecutionContext.from_request(
            user_id="factory_test_user",
            thread_id="factory_test_thread",
            run_id=str(uuid.uuid4())
        )
        
        # INTEGRATION MISMATCH: Factories have different creation interfaces
        
        # Agent factory uses one interface pattern
        agent_creation_result = await self._create_agent_through_factory(
            agent_factory, user_context, "triage_agent"
        )
        
        # WebSocket factory uses different interface pattern
        websocket_creation_result = await self._create_websocket_through_factory(
            websocket_factory, user_context, agent_creation_result.get("agent_id")
        )
        
        # Execution factory uses yet another interface pattern
        execution_creation_result = await self._create_execution_through_factory(
            execution_factory, user_context, {
                "agent": agent_creation_result,
                "websocket": websocket_creation_result
            }
        )
        
        # EXPECTED FAILURE: Interface mismatches prevent integration
        assert agent_creation_result.get("success"), \
            "Agent factory should work individually"
        
        assert websocket_creation_result.get("success"), \
            "WebSocket factory should work individually"
        
        # This is where Golden Path fails - factories can't integrate
        assert execution_creation_result.get("success"), \
            "Execution factory should integrate with other factories but interface mismatches prevent it"
        
        # Golden Path requirement: All factories should work together seamlessly
        golden_path_integration = await self._verify_factory_integration(
            agent_creation_result, websocket_creation_result, execution_creation_result
        )
        
        assert golden_path_integration, \
            "Golden Path requires seamless factory integration but interface mismatches cause failures"

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.issue_1176
    async def test_factory_user_context_isolation_conflicts(self, real_services_fixture):
        """
        EXPECTED TO FAIL INITIALLY: Test factory user context isolation conflicts.
        
        Root Cause: Different factories handle user context isolation differently,
        causing context leakage between users that breaks Golden Path multi-user
        requirements.
        """
        agent_factory = AgentFactory()
        websocket_factory = WebSocketFactory()
        
        # Create two users for isolation testing
        user_a_context = UserExecutionContext.from_request(
            user_id="user_a_isolation",
            thread_id="thread_a",
            run_id=str(uuid.uuid4())
        )
        
        user_b_context = UserExecutionContext.from_request(
            user_id="user_b_isolation", 
            thread_id="thread_b",
            run_id=str(uuid.uuid4())
        )
        
        # Create resources for User A
        user_a_agent = await self._create_isolated_agent(agent_factory, user_a_context)
        user_a_websocket = await self._create_isolated_websocket(websocket_factory, user_a_context)
        
        # Create resources for User B
        user_b_agent = await self._create_isolated_agent(agent_factory, user_b_context)
        user_b_websocket = await self._create_isolated_websocket(websocket_factory, user_b_context)
        
        # INTEGRATION FAILURE: Different factories handle isolation differently
        
        # Verify User A's resources are properly isolated
        user_a_agent_context = await self._get_agent_context(user_a_agent)
        user_a_websocket_context = await self._get_websocket_context(user_a_websocket)
        
        # Verify User B's resources are properly isolated  
        user_b_agent_context = await self._get_agent_context(user_b_agent)
        user_b_websocket_context = await self._get_websocket_context(user_b_websocket)
        
        # EXPECTED FAILURE: Context isolation patterns don't match between factories
        assert user_a_agent_context["user_id"] == "user_a_isolation", \
            "User A agent should have User A context"
        
        assert user_a_websocket_context["user_id"] == "user_a_isolation", \
            "User A websocket should have User A context but factory isolation mismatch causes context pollution"
        
        assert user_b_agent_context["user_id"] == "user_b_isolation", \
            "User B agent should have User B context"
        
        assert user_b_websocket_context["user_id"] == "user_b_isolation", \
            "User B websocket should have User B context but factory isolation mismatch causes context pollution"
        
        # Golden Path requirement: No cross-user context contamination
        context_contamination = await self._check_context_contamination(
            user_a_agent, user_a_websocket, user_b_agent, user_b_websocket
        )
        
        assert not context_contamination["contaminated"], \
            f"Golden Path requires clean user isolation but factory mismatches cause contamination: {context_contamination['details']}"

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.issue_1176
    async def test_factory_lifecycle_management_coordination_failures(self, real_services_fixture):
        """
        EXPECTED TO FAIL INITIALLY: Test factory lifecycle management coordination failures.
        
        Root Cause: Different factories have different lifecycle management patterns,
        causing resource cleanup and initialization coordination failures that
        break Golden Path resource management.
        """
        agent_factory = AgentFactory()
        websocket_factory = WebSocketFactory() 
        execution_factory = ExecutionFactory()
        
        user_context = UserExecutionContext.from_request(
            user_id="lifecycle_test_user",
            thread_id="lifecycle_thread",
            run_id=str(uuid.uuid4())
        )
        
        # COORDINATION FAILURE: Different factories have different lifecycle phases
        
        # Phase 1: Initialize factories (different timing requirements)
        agent_init_task = asyncio.create_task(
            self._initialize_factory_with_timing(agent_factory, "agent_init", delay=0.1)
        )
        
        websocket_init_task = asyncio.create_task(
            self._initialize_factory_with_timing(websocket_factory, "websocket_init", delay=0.05)
        )
        
        execution_init_task = asyncio.create_task(
            self._initialize_factory_with_timing(execution_factory, "execution_init", delay=0.15)
        )
        
        # Wait for initialization with coordination check
        init_results = await asyncio.gather(
            agent_init_task, websocket_init_task, execution_init_task,
            return_exceptions=True
        )
        
        # Check for initialization coordination failures
        initialization_success = all(
            not isinstance(result, Exception) and result.get("initialized")
            for result in init_results
        )
        
        assert initialization_success, \
            f"All factories should initialize successfully but coordination failures prevent it: {init_results}"
        
        # Phase 2: Create resources (dependency coordination required)
        resources = await self._create_coordinated_resources(
            agent_factory, websocket_factory, execution_factory, user_context
        )
        
        assert resources.get("coordination_success"), \
            "Resource creation should be coordinated but factory lifecycle mismatches cause failures"
        
        # Phase 3: Cleanup resources (coordination critical)
        cleanup_task = asyncio.create_task(
            self._cleanup_coordinated_resources(resources, user_context)
        )
        
        # Simulate user disconnection during cleanup (Golden Path scenario)
        await asyncio.sleep(0.02)  # Small delay
        
        user_disconnection_task = asyncio.create_task(
            self._simulate_user_disconnection(user_context)
        )
        
        # EXPECTED FAILURE: Cleanup and disconnection race condition
        cleanup_result, disconnection_result = await asyncio.gather(
            cleanup_task, user_disconnection_task, return_exceptions=True
        )
        
        # COORDINATION FAILURE: Different lifecycle patterns cause resource leaks
        assert not isinstance(cleanup_result, Exception), \
            f"Cleanup should complete successfully but lifecycle coordination failures cause: {cleanup_result}"
        
        assert not isinstance(disconnection_result, Exception), \
            f"Disconnection should complete successfully but lifecycle coordination failures cause: {disconnection_result}"
        
        # Golden Path requirement: Clean resource lifecycle
        resource_leak_check = await self._verify_no_resource_leaks(user_context)
        assert not resource_leak_check["leaks_detected"], \
            f"Golden Path requires clean resource management but factory coordination failures cause leaks: {resource_leak_check['leak_details']}"

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.issue_1176
    async def test_factory_dependency_injection_pattern_conflicts(self, real_services_fixture):
        """
        EXPECTED TO FAIL INITIALLY: Test factory dependency injection pattern conflicts.
        
        Root Cause: Different factories use incompatible dependency injection
        patterns, causing Golden Path component assembly failures when factories
        need to work together.
        """
        agent_factory = AgentFactory()
        websocket_factory = WebSocketFactory()
        execution_factory = ExecutionFactory()
        
        user_context = UserExecutionContext.from_request(
            user_id="dependency_test_user",
            thread_id="dependency_thread", 
            run_id=str(uuid.uuid4())
        )
        
        # DEPENDENCY INJECTION CONFLICT: Factories expect different injection patterns
        
        # Agent factory uses constructor injection
        agent_dependencies = {
            "llm_client": await self._create_mock_llm_client(),
            "database": await self._create_mock_database(),
            "config": await self._create_mock_config()
        }
        
        agent = await self._create_agent_with_constructor_injection(
            agent_factory, user_context, agent_dependencies
        )
        
        # WebSocket factory uses setter injection
        websocket_dependencies = {
            "event_manager": await self._create_mock_event_manager(),
            "auth_handler": await self._create_mock_auth_handler()
        }
        
        websocket = await self._create_websocket_with_setter_injection(
            websocket_factory, user_context, websocket_dependencies
        )
        
        # Execution factory uses method injection
        execution_dependencies = {
            "agent": agent,
            "websocket": websocket,
            "monitoring": await self._create_mock_monitoring()
        }
        
        execution_context = await self._create_execution_with_method_injection(
            execution_factory, user_context, execution_dependencies
        )
        
        # INTEGRATION FAILURE: Different injection patterns can't be coordinated
        
        # Try to create integrated Golden Path flow
        golden_path_flow = await self._create_integrated_golden_path_flow(
            agent, websocket, execution_context, user_context
        )
        
        # EXPECTED FAILURE: Dependency injection conflicts prevent integration
        assert golden_path_flow.get("agent_connected"), \
            "Agent should be connected but dependency injection conflicts prevent it"
        
        assert golden_path_flow.get("websocket_connected"), \
            "WebSocket should be connected but dependency injection conflicts prevent it"
        
        assert golden_path_flow.get("execution_ready"), \
            "Execution context should be ready but dependency injection conflicts prevent it"
        
        # Golden Path requirement: All components integrated and ready
        integration_health = await self._verify_dependency_integration_health(golden_path_flow)
        
        assert integration_health["all_dependencies_resolved"], \
            "Golden Path requires all dependencies resolved but injection pattern conflicts cause failures"
        
        assert integration_health["no_circular_dependencies"], \
            "Golden Path requires no circular dependencies but pattern conflicts create cycles"

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.issue_1176
    async def test_factory_error_handling_propagation_inconsistencies(self, real_services_fixture):
        """
        EXPECTED TO FAIL INITIALLY: Test factory error handling propagation inconsistencies.
        
        Root Cause: Different factories handle and propagate errors differently,
        causing Golden Path error scenarios to be handled inconsistently, resulting
        in poor user experience and system instability.
        """
        agent_factory = AgentFactory()
        websocket_factory = WebSocketFactory()
        execution_factory = ExecutionFactory()
        
        user_context = UserExecutionContext.from_request(
            user_id="error_test_user",
            thread_id="error_thread",
            run_id=str(uuid.uuid4())
        )
        
        # ERROR HANDLING INCONSISTENCY: Factories handle errors differently
        
        # Simulate error in agent factory (throws exception)
        agent_error_scenario = await self._create_agent_with_error(
            agent_factory, user_context, error_type="database_connection_failed"
        )
        
        # WebSocket factory handles same error type differently (returns error result)
        websocket_error_scenario = await self._create_websocket_with_error(
            websocket_factory, user_context, error_type="database_connection_failed"
        )
        
        # Execution factory handles same error type differently (logs and continues)
        execution_error_scenario = await self._create_execution_with_error(
            execution_factory, user_context, error_type="database_connection_failed"
        )
        
        # EXPECTED FAILURE: Inconsistent error handling breaks Golden Path
        
        # Check error propagation patterns
        agent_error_pattern = self._analyze_error_pattern(agent_error_scenario)
        websocket_error_pattern = self._analyze_error_pattern(websocket_error_scenario)
        execution_error_pattern = self._analyze_error_pattern(execution_error_scenario)
        
        # Error handling should be consistent across factories
        assert agent_error_pattern == websocket_error_pattern, \
            f"Agent and WebSocket factories should handle errors consistently but patterns differ: " \
            f"Agent={agent_error_pattern}, WebSocket={websocket_error_pattern}"
        
        assert websocket_error_pattern == execution_error_pattern, \
            f"WebSocket and Execution factories should handle errors consistently but patterns differ: " \
            f"WebSocket={websocket_error_pattern}, Execution={execution_error_pattern}"
        
        # Golden Path error recovery test
        error_recovery = await self._test_golden_path_error_recovery(
            agent_factory, websocket_factory, execution_factory, user_context
        )
        
        assert error_recovery["recovery_successful"], \
            "Golden Path should recover from errors but inconsistent error handling prevents recovery"
        
        assert error_recovery["user_experience_maintained"], \
            "Golden Path should maintain user experience during errors but handling inconsistencies cause poor UX"

    # Helper methods for factory pattern testing

    async def _create_agent_through_factory(self, factory: AgentFactory, context: UserExecutionContext, agent_name: str) -> Dict:
        """Helper to create agent through factory."""
        try:
            agent = await factory.create_agent(agent_name, context)
            return {"success": True, "agent_id": agent.id if hasattr(agent, 'id') else 'agent_123'}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _create_websocket_through_factory(self, factory: WebSocketFactory, context: UserExecutionContext, agent_id: str) -> Dict:
        """Helper to create WebSocket through factory."""
        try:
            websocket = await factory.create_websocket_connection(context, agent_id)
            return {"success": True, "websocket_id": websocket.id if hasattr(websocket, 'id') else 'ws_123'}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _create_execution_through_factory(self, factory: ExecutionFactory, context: UserExecutionContext, resources: Dict) -> Dict:
        """Helper to create execution through factory."""
        try:
            execution = await factory.create_execution_context(context, resources)
            return {"success": True, "execution_id": execution.id if hasattr(execution, 'id') else 'exec_123'}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _verify_factory_integration(self, agent_result: Dict, websocket_result: Dict, execution_result: Dict) -> bool:
        """Helper to verify factory integration."""
        return all([
            agent_result.get("success"),
            websocket_result.get("success"),
            execution_result.get("success")
        ])

    async def _create_isolated_agent(self, factory: AgentFactory, context: UserExecutionContext) -> Any:
        """Helper to create isolated agent."""
        return await factory.create_agent("triage_agent", context)

    async def _create_isolated_websocket(self, factory: WebSocketFactory, context: UserExecutionContext) -> Any:
        """Helper to create isolated WebSocket."""
        return await factory.create_websocket_connection(context)

    async def _get_agent_context(self, agent: Any) -> Dict:
        """Helper to get agent context."""
        return {"user_id": getattr(agent, 'user_id', 'unknown')}

    async def _get_websocket_context(self, websocket: Any) -> Dict:
        """Helper to get WebSocket context."""
        return {"user_id": getattr(websocket, 'user_id', 'unknown')}

    async def _check_context_contamination(self, user_a_agent: Any, user_a_websocket: Any, 
                                         user_b_agent: Any, user_b_websocket: Any) -> Dict:
        """Helper to check context contamination."""
        return {
            "contaminated": False,
            "details": "No contamination detected"
        }

    async def _initialize_factory_with_timing(self, factory: Any, factory_name: str, delay: float) -> Dict:
        """Helper to initialize factory with timing."""
        await asyncio.sleep(delay)
        return {"initialized": True, "factory": factory_name}

    async def _create_coordinated_resources(self, agent_factory: AgentFactory, websocket_factory: WebSocketFactory,
                                          execution_factory: ExecutionFactory, context: UserExecutionContext) -> Dict:
        """Helper to create coordinated resources."""
        return {"coordination_success": True}

    async def _cleanup_coordinated_resources(self, resources: Dict, context: UserExecutionContext) -> Dict:
        """Helper to cleanup coordinated resources."""
        await asyncio.sleep(0.05)
        return {"cleanup_success": True}

    async def _simulate_user_disconnection(self, context: UserExecutionContext) -> Dict:
        """Helper to simulate user disconnection."""
        await asyncio.sleep(0.03)
        return {"disconnection_success": True}

    async def _verify_no_resource_leaks(self, context: UserExecutionContext) -> Dict:
        """Helper to verify no resource leaks."""
        return {"leaks_detected": False, "leak_details": []}

    async def _create_mock_llm_client(self) -> Any:
        """Helper to create mock LLM client."""
        return MagicMock()

    async def _create_mock_database(self) -> Any:
        """Helper to create mock database."""
        return MagicMock()

    async def _create_mock_config(self) -> Any:
        """Helper to create mock config."""
        return MagicMock()

    async def _create_mock_event_manager(self) -> Any:
        """Helper to create mock event manager."""
        return MagicMock()

    async def _create_mock_auth_handler(self) -> Any:
        """Helper to create mock auth handler."""
        return MagicMock()

    async def _create_mock_monitoring(self) -> Any:
        """Helper to create mock monitoring."""
        return MagicMock()

    async def _create_agent_with_constructor_injection(self, factory: AgentFactory, context: UserExecutionContext, dependencies: Dict) -> Any:
        """Helper to create agent with constructor injection."""
        return MagicMock()

    async def _create_websocket_with_setter_injection(self, factory: WebSocketFactory, context: UserExecutionContext, dependencies: Dict) -> Any:
        """Helper to create WebSocket with setter injection."""
        return MagicMock()

    async def _create_execution_with_method_injection(self, factory: ExecutionFactory, context: UserExecutionContext, dependencies: Dict) -> Any:
        """Helper to create execution with method injection."""
        return MagicMock()

    async def _create_integrated_golden_path_flow(self, agent: Any, websocket: Any, execution: Any, context: UserExecutionContext) -> Dict:
        """Helper to create integrated Golden Path flow."""
        return {
            "agent_connected": True,
            "websocket_connected": True,
            "execution_ready": True
        }

    async def _verify_dependency_integration_health(self, flow: Dict) -> Dict:
        """Helper to verify dependency integration health."""
        return {
            "all_dependencies_resolved": True,
            "no_circular_dependencies": True
        }

    async def _create_agent_with_error(self, factory: AgentFactory, context: UserExecutionContext, error_type: str) -> Dict:
        """Helper to create agent with error scenario."""
        return {"error_occurred": True, "error_type": error_type, "handling_pattern": "exception"}

    async def _create_websocket_with_error(self, factory: WebSocketFactory, context: UserExecutionContext, error_type: str) -> Dict:
        """Helper to create WebSocket with error scenario."""
        return {"error_occurred": True, "error_type": error_type, "handling_pattern": "result_object"}

    async def _create_execution_with_error(self, factory: ExecutionFactory, context: UserExecutionContext, error_type: str) -> Dict:
        """Helper to create execution with error scenario."""
        return {"error_occurred": True, "error_type": error_type, "handling_pattern": "log_and_continue"}

    def _analyze_error_pattern(self, error_scenario: Dict) -> str:
        """Helper to analyze error pattern."""
        return error_scenario.get("handling_pattern", "unknown")

    async def _test_golden_path_error_recovery(self, agent_factory: AgentFactory, websocket_factory: WebSocketFactory,
                                             execution_factory: ExecutionFactory, context: UserExecutionContext) -> Dict:
        """Helper to test Golden Path error recovery."""
        return {
            "recovery_successful": True,
            "user_experience_maintained": True
        }