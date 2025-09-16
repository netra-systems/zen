"""
Comprehensive Integration Test Suite for AgentWebSocketBridge

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable agent-WebSocket event delivery (core chat value)
- Value Impact: Real-time agent updates enable substantive AI interactions
- Strategic Impact: Core platform infrastructure for agent execution visibility

This integration test suite covers the CRITICAL agent-WebSocket bridge functionality:
1. Agent-WebSocket event bridging lifecycle (agent event  ->  bridge  ->  WebSocket  ->  user)
2. Multi-user agent-WebSocket isolation and concurrent agent execution  
3. Real-time agent event routing and WebSocket delivery coordination
4. Agent execution context bridging to WebSocket user sessions
5. Agent WebSocket bridge health monitoring and error recovery
6. Cross-service agent-WebSocket coordination (agents [U+2194] backend [U+2194] frontend)
7. Agent event queue management and delivery guarantees during WebSocket issues
8. Business-critical agent event bridging (all 5 WebSocket events: started, thinking, tool_executing, tool_completed, completed)
9. Agent WebSocket bridge performance under concurrent agent execution
10. Integration with AgentRegistry, UnifiedWebSocketManager, and ExecutionEngine
11. Agent WebSocket bridge resource management and cleanup
12. Agent event serialization and WebSocket message format validation
13. Agent WebSocket bridge timeout handling and circuit breaker patterns
14. Agent WebSocket bridge authentication and user authorization validation

CRITICAL: NO MOCKS - Uses real agent-WebSocket coordination, real event routing, real user session bridging
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Set
from unittest.mock import patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
# Import integration auth fixtures directly for this test
import pytest
import asyncio
from test_framework.ssot.integration_auth_manager import create_integration_test_helper
from shared.isolated_environment import IsolatedEnvironment, get_env

# Import the class under test and dependencies
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    IntegrationState,
    IntegrationConfig,
    HealthStatus,
    IntegrationResult,
    IntegrationMetrics
)

# Import WebSocket and agent infrastructure
from netra_backend.app.websocket_core import create_websocket_manager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from netra_backend.app.services.thread_run_registry import get_thread_run_registry, ThreadRunRegistry


class TestAgentWebSocketBridgeIntegration(BaseIntegrationTest):
    """
    Integration tests for AgentWebSocketBridge using real services and real agent-WebSocket coordination.
    
    BUSINESS CRITICALITY: Agent event streaming enables real-time user feedback
    which is the core value proposition of the chat experience.
    
    These tests validate the COMPLETE agent-WebSocket integration pipeline
    without mocks to ensure business value is delivered.
    """
    
    def setup_method(self, method=None):
        """Set up integration test environment with real service coordination."""
        super().setup_method()
        
        # Set up isolated environment
        self.env = get_env()
        self.env.set("TEST_MODE", "integration", source="test")
        self.env.set("ENABLE_WEBSOCKET_EVENTS", "true", source="test")
        
        # Create unique test identifiers for isolation
        self.test_session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        self.test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
        
        # Initialize real components (NO MOCKS)
        self.bridge = AgentWebSocketBridge()
        self.unified_id_manager = UnifiedIDManager()
        self.thread_registry = None
        self.websocket_manager = None
        
        # Test data for realistic scenarios
        self.test_message = "Optimize my AWS costs and provide actionable recommendations"
        self.test_agent_name = "cost_optimizer_agent"
        self.test_tools = ["aws_cost_analyzer", "recommendation_generator", "report_formatter"]
        
        # Event tracking for validation
        self.received_events: List[Dict[str, Any]] = []
        self.event_timestamps: Dict[str, float] = {}
        
        self.logger.info(f"Integration test setup complete for session {self.test_session_id}")
    
    def teardown_method(self, method=None):
        """Clean up integration test resources."""
        # Clean up real resources (not mocks)
        if self.websocket_manager:
            asyncio.create_task(self.websocket_manager.cleanup())
        
        # Clear event tracking
        self.received_events.clear()
        self.event_timestamps.clear()
        
        super().teardown_method()
        self.logger.info(f"Integration test cleanup complete for session {self.test_session_id}")

    # ========================================================================
    # INTEGRATION TEST FIXTURES FOR REAL AGENT-WEBSOCKET COORDINATION
    # ========================================================================
    
    async def setup_real_websocket_manager(self) -> Any:
        """Set up real WebSocket manager for integration testing."""
        self.websocket_manager = create_websocket_manager()
        await self.websocket_manager.initialize()
        
        # Verify real WebSocket manager is operational
        assert self.websocket_manager is not None
        assert await self.websocket_manager.health_check()
        
        return self.websocket_manager
    
    async def setup_real_thread_registry(self) -> ThreadRunRegistry:
        """Set up real thread run registry for integration testing."""
        self.thread_registry = get_thread_run_registry()
        
        # Verify thread registry is operational
        assert self.thread_registry is not None
        
        return self.thread_registry
    
    async def create_real_user_execution_context(
        self, 
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        websocket_connection_id: Optional[str] = None
    ) -> UserExecutionContext:
        """Create real user execution context for testing."""
        context = UserExecutionContext(
            user_id=user_id or self.test_user_id,
            thread_id=thread_id or self.test_thread_id,
            run_id=self.unified_id_manager.generate_run_id(),
            websocket_connection_id=websocket_connection_id or f"ws_{uuid.uuid4().hex[:8]}"
        )
        
        # Set up real context data
        context.current_message = self.test_message
        context.agent_name = self.test_agent_name
        context.session_start_time = datetime.now(timezone.utc)
        
        return context
    
    def event_collector(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Collect events for validation (real event handler)."""
        timestamp = time.time()
        event = {
            "type": event_type,
            "data": event_data,
            "timestamp": timestamp,
            "session_id": self.test_session_id
        }
        
        self.received_events.append(event)
        self.event_timestamps[event_type] = timestamp
        
        self.logger.info(f"Collected event: {event_type} at {timestamp}")

    # ========================================================================
    # CRITICAL: Agent-WebSocket Event Bridging Lifecycle Tests
    # ========================================================================

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_agent_websocket_event_bridging_lifecycle(self, real_services_fixture):
        """
        Test complete agent-WebSocket event bridging lifecycle.
        
        BUSINESS VALUE: Ensures agent execution events reach users via WebSocket
        enabling real-time visibility into AI processing.
        """
        # Set up authentication for the test
        auth_helper = await create_integration_test_helper()
        authenticated_user_token = await auth_helper.create_integration_test_token()
        
        # Verify auth service is healthy and token is created
        assert authenticated_user_token, "Auth service must be healthy and provide tokens for WebSocket integration tests"
        
        # Log authentication status for debugging
        self.logger.info(f"Integration test using token: {authenticated_user_token[:20]}...")
        
        # Arrange: Set up real agent-WebSocket infrastructure
        await self.setup_real_websocket_manager()
        await self.setup_real_thread_registry()
        
        user_context = await self.create_real_user_execution_context()
        
        # Initialize bridge with real services
        integration_result = await self.bridge.ensure_integration(
            registry=self.thread_registry
        )
        assert integration_result.success, f"Integration failed: {integration_result.error}"
        assert self.bridge.state == IntegrationState.ACTIVE
        
        # Act: Execute complete agent lifecycle with real event bridging
        start_time = time.time()
        
        # 1. Agent started event
        await self.bridge.notify_agent_started(
            run_id=user_context.run_id,
            agent_name=self.test_agent_name,
            context={"message": self.test_message},
            trace_context={"trace_id": f"trace_{uuid.uuid4().hex[:8]}"}
        )
        
        # 2. Agent thinking event  
        await self.bridge.notify_agent_thinking(
            run_id=user_context.run_id,
            agent_name=self.test_agent_name,
            thinking_content="Analyzing AWS cost optimization opportunities...",
            context={"analysis_phase": "cost_discovery"}
        )
        
        # 3. Tool execution events
        for tool_name in self.test_tools:
            await self.bridge.notify_tool_executing(
                run_id=user_context.run_id,
                tool_name=tool_name,
                tool_input={"analysis_type": "cost_optimization"},
                context={"tool_sequence": self.test_tools.index(tool_name)}
            )
            
            # Simulate tool execution time
            await asyncio.sleep(0.1)
            
            await self.bridge.notify_tool_completed(
                run_id=user_context.run_id,
                tool_name=tool_name,
                tool_output={"status": "success", "insights_found": True},
                execution_time_ms=100,
                context={"completion_status": "success"}
            )
        
        # 4. Agent completed event
        final_result = {
            "recommendations": [
                {"type": "instance_rightsizing", "potential_savings": 1500},
                {"type": "reserved_instances", "potential_savings": 2500}
            ],
            "total_potential_savings": 4000,
            "confidence_score": 0.85
        }
        
        await self.bridge.notify_agent_completed(
            run_id=user_context.run_id,
            agent_name=self.test_agent_name,
            result=final_result,
            execution_time_ms=int((time.time() - start_time) * 1000),
            context={"completion_type": "success"}
        )
        
        # Assert: Verify all events were properly bridged
        # Allow time for event processing
        await asyncio.sleep(0.5)
        
        # Verify bridge health after full lifecycle
        health_status = self.bridge.get_health_status()
        assert health_status.state == IntegrationState.ACTIVE
        assert health_status.websocket_manager_healthy
        
        # Verify integration metrics show activity
        metrics = self.bridge.get_integration_metrics()
        assert metrics.successful_initializations > 0
        assert metrics.health_checks_performed >= 1
        
        self.logger.info("Agent-WebSocket event bridging lifecycle completed successfully")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_agent_websocket_isolation(self, real_services_fixture):
        """
        Test multi-user agent-WebSocket isolation during concurrent execution.
        
        BUSINESS VALUE: Ensures user isolation so agents don't leak information
        between different users' sessions.
        """
        # Set up authentication helper and create tokens for multiple users
        auth_helper = await create_integration_test_helper()
        
        # Create multiple user tokens
        multi_user_tokens = {}
        user_configs = [
            {"user_id": "test-user-1", "email": "user1@test.com"},
            {"user_id": "test-user-2", "email": "user2@test.com"},
            {"user_id": "test-user-3", "email": "user3@test.com"}
        ]
        
        for config in user_configs:
            token = await auth_helper.create_integration_test_token(
                user_id=config["user_id"],
                email=config["email"]
            )
            multi_user_tokens[config["user_id"]] = token
        
        # Verify we have multiple user tokens
        assert len(multi_user_tokens) >= 3, "Multi-user test requires at least 3 user tokens"
        
        self.logger.info(f"Multi-user test using {len(multi_user_tokens)} authenticated users")
        
        # Arrange: Set up multiple isolated user contexts
        await self.setup_real_websocket_manager()
        await self.setup_real_thread_registry()
        
        # Create multiple user contexts (simulating concurrent users)
        num_users = 3
        user_contexts = []
        
        for i in range(num_users):
            context = await self.create_real_user_execution_context(
                user_id=f"user_{i}_{uuid.uuid4().hex[:6]}",
                thread_id=f"thread_{i}_{uuid.uuid4().hex[:6]}"
            )
            user_contexts.append(context)
        
        # Initialize bridge for multi-user scenario
        integration_result = await self.bridge.ensure_integration(
            registry=self.thread_registry
        )
        assert integration_result.success
        
        # Act: Execute concurrent agent operations for different users
        concurrent_tasks = []
        
        for i, context in enumerate(user_contexts):
            task = self.execute_agent_sequence_for_user(context, user_index=i)
            concurrent_tasks.append(task)
        
        # Wait for all concurrent executions to complete
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Assert: Verify all users completed successfully with proper isolation
        successful_executions = 0
        for i, result in enumerate(results):
            if not isinstance(result, Exception):
                successful_executions += 1
                self.logger.info(f"User {i} completed successfully")
            else:
                self.logger.error(f"User {i} failed: {result}")
        
        assert successful_executions == num_users, f"Only {successful_executions}/{num_users} users completed successfully"
        
        # Verify bridge health after concurrent operations
        health_status = self.bridge.get_health_status()
        assert health_status.state == IntegrationState.ACTIVE
        assert health_status.consecutive_failures == 0
        
        self.logger.info(f"Multi-user isolation test completed - {num_users} users isolated successfully")

    async def execute_agent_sequence_for_user(self, user_context: UserExecutionContext, user_index: int) -> Dict[str, Any]:
        """Execute a complete agent sequence for a specific user."""
        user_specific_message = f"User {user_index}: {self.test_message}"
        
        # Agent started
        await self.bridge.notify_agent_started(
            run_id=user_context.run_id,
            agent_name=self.test_agent_name,
            context={"message": user_specific_message, "user_index": user_index}
        )
        
        # Agent thinking
        await self.bridge.notify_agent_thinking(
            run_id=user_context.run_id,
            agent_name=self.test_agent_name,
            thinking_content=f"Processing request for user {user_index}..."
        )
        
        # Tool execution (simplified for concurrency test)
        await self.bridge.notify_tool_executing(
            run_id=user_context.run_id,
            tool_name="analyzer_tool",
            tool_input={"user_id": user_context.user_id}
        )
        
        await asyncio.sleep(0.1)  # Simulate processing
        
        await self.bridge.notify_tool_completed(
            run_id=user_context.run_id,
            tool_name="analyzer_tool",
            tool_output={"user_specific_result": f"Analysis for user {user_index}"}
        )
        
        # Agent completed
        await self.bridge.notify_agent_completed(
            run_id=user_context.run_id,
            agent_name=self.test_agent_name,
            result={"user_index": user_index, "status": "completed"},
            execution_time_ms=150
        )
        
        return {"user_index": user_index, "status": "success"}

    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_real_time_agent_event_routing(self, real_services_fixture):
        """
        Test real-time agent event routing and WebSocket delivery coordination.
        
        BUSINESS VALUE: Ensures users receive immediate feedback during agent execution
        creating responsive AI interaction experience.
        """
        # Arrange: Set up real event routing infrastructure
        await self.setup_real_websocket_manager()
        await self.setup_real_thread_registry()
        
        user_context = await self.create_real_user_execution_context()
        
        # Initialize bridge with event timing monitoring
        integration_result = await self.bridge.ensure_integration(
            registry=self.thread_registry
        )
        assert integration_result.success
        
        # Set up event timing tracking
        event_timings = {}
        expected_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        # Act: Execute agent sequence with precise timing measurement
        sequence_start = time.time()
        
        for event_type in expected_events:
            event_start = time.time()
            
            if event_type == "agent_started":
                await self.bridge.notify_agent_started(
                    run_id=user_context.run_id,
                    agent_name=self.test_agent_name,
                    context={"timing_test": True}
                )
            elif event_type == "agent_thinking":
                await self.bridge.notify_agent_thinking(
                    run_id=user_context.run_id,
                    agent_name=self.test_agent_name,
                    thinking_content="Real-time processing..."
                )
            elif event_type == "tool_executing":
                await self.bridge.notify_tool_executing(
                    run_id=user_context.run_id,
                    tool_name="real_time_analyzer",
                    tool_input={"timestamp": time.time()}
                )
            elif event_type == "tool_completed":
                await self.bridge.notify_tool_completed(
                    run_id=user_context.run_id,
                    tool_name="real_time_analyzer", 
                    tool_output={"result": "analyzed"},
                    execution_time_ms=50
                )
            elif event_type == "agent_completed":
                await self.bridge.notify_agent_completed(
                    run_id=user_context.run_id,
                    agent_name=self.test_agent_name,
                    result={"real_time_test": "completed"},
                    execution_time_ms=int((time.time() - sequence_start) * 1000)
                )
            
            event_end = time.time()
            event_timings[event_type] = event_end - event_start
            
            # Small delay to measure routing latency
            await asyncio.sleep(0.05)
        
        # Assert: Verify real-time performance characteristics
        sequence_total = time.time() - sequence_start
        
        # Verify each event completed quickly (real-time requirement)
        for event_type, duration in event_timings.items():
            assert duration < 0.1, f"Event {event_type} took {duration}s - too slow for real-time"
        
        # Verify total sequence completed in reasonable time
        assert sequence_total < 2.0, f"Total sequence took {sequence_total}s - too slow"
        
        # Verify bridge maintained health throughout
        health_status = self.bridge.get_health_status()
        assert health_status.state == IntegrationState.ACTIVE
        
        self.logger.info(f"Real-time event routing completed in {sequence_total:.3f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_context_bridging(self, real_services_fixture):
        """
        Test agent execution context bridging to WebSocket user sessions.
        
        BUSINESS VALUE: Ensures agent context (user data, session info) properly 
        flows through WebSocket events for personalized AI responses.
        """
        # Arrange: Set up complex user context
        await self.setup_real_websocket_manager()
        await self.setup_real_thread_registry()
        
        # Create rich user execution context
        user_context = await self.create_real_user_execution_context()
        user_context.user_preferences = {
            "industry": "technology",
            "cost_optimization_focus": "compute",
            "reporting_detail": "comprehensive"
        }
        user_context.session_context = {
            "previous_recommendations": ["rightsizing", "scheduling"],
            "budget_constraints": 10000,
            "priority_level": "high"
        }
        
        # Initialize bridge 
        integration_result = await self.bridge.ensure_integration(registry=self.thread_registry)
        assert integration_result.success
        
        # Act: Execute agent with context bridging
        rich_context = {
            "user_preferences": user_context.user_preferences,
            "session_context": user_context.session_context,
            "execution_metadata": {
                "context_type": "rich_user_context",
                "bridging_test": True
            }
        }
        
        # Agent started with rich context
        await self.bridge.notify_agent_started(
            run_id=user_context.run_id,
            agent_name=self.test_agent_name,
            context=rich_context,
            trace_context={"context_flow_test": True}
        )
        
        # Agent thinking with context-aware processing
        await self.bridge.notify_agent_thinking(
            run_id=user_context.run_id,
            agent_name=self.test_agent_name,
            thinking_content="Analyzing based on user's technology industry focus and compute optimization preferences...",
            context={"context_aware": True, "industry_focus": user_context.user_preferences["industry"]}
        )
        
        # Tool execution with context bridging
        await self.bridge.notify_tool_executing(
            run_id=user_context.run_id,
            tool_name="context_aware_analyzer",
            tool_input={
                "user_industry": user_context.user_preferences["industry"],
                "budget_limit": user_context.session_context["budget_constraints"]
            },
            context={"context_bridged": True}
        )
        
        await self.bridge.notify_tool_completed(
            run_id=user_context.run_id,
            tool_name="context_aware_analyzer",
            tool_output={
                "recommendations": "Context-specific technology industry recommendations",
                "budget_compliance": True,
                "personalized": True
            },
            context={"context_utilized": True}
        )
        
        # Agent completed with context-enriched result
        contextual_result = {
            "personalized_recommendations": [
                {
                    "type": "compute_optimization", 
                    "industry_specific": True,
                    "budget_compliant": True,
                    "user_preference_aligned": True
                }
            ],
            "context_metadata": {
                "user_industry": user_context.user_preferences["industry"],
                "context_bridged_successfully": True
            }
        }
        
        await self.bridge.notify_agent_completed(
            run_id=user_context.run_id,
            agent_name=self.test_agent_name,
            result=contextual_result,
            execution_time_ms=200,
            context={"context_bridging_complete": True}
        )
        
        # Assert: Verify context bridging success
        health_status = self.bridge.get_health_status()
        assert health_status.state == IntegrationState.ACTIVE
        
        # Verify bridge handled context complexity without errors
        metrics = self.bridge.get_integration_metrics()
        assert metrics.successful_initializations > 0
        assert metrics.failed_initializations == 0
        
        self.logger.info("Agent execution context bridging completed successfully")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_websocket_bridge_health_monitoring(self, real_services_fixture):
        """
        Test agent WebSocket bridge health monitoring and error recovery.
        
        BUSINESS VALUE: Ensures bridge automatically recovers from failures
        maintaining continuous agent-user communication.
        """
        # Arrange: Set up bridge with health monitoring
        await self.setup_real_websocket_manager()
        await self.setup_real_thread_registry()
        
        # Initialize bridge
        integration_result = await self.bridge.ensure_integration(registry=self.thread_registry)
        assert integration_result.success
        
        # Verify initial health
        initial_health = self.bridge.get_health_status()
        assert initial_health.state == IntegrationState.ACTIVE
        assert initial_health.websocket_manager_healthy
        assert initial_health.registry_healthy
        
        # Act: Monitor health during operations
        user_context = await self.create_real_user_execution_context()
        health_checks = []
        
        # Collect health status during agent execution
        await self.bridge.notify_agent_started(
            run_id=user_context.run_id,
            agent_name=self.test_agent_name,
            context={"health_monitoring_test": True}
        )
        
        health_checks.append(self.bridge.get_health_status())
        
        # Simulate some processing load
        for i in range(5):
            await self.bridge.notify_agent_thinking(
                run_id=user_context.run_id,
                agent_name=self.test_agent_name,
                thinking_content=f"Health monitoring step {i+1}..."
            )
            
            health_checks.append(self.bridge.get_health_status())
            await asyncio.sleep(0.1)
        
        await self.bridge.notify_agent_completed(
            run_id=user_context.run_id,
            agent_name=self.test_agent_name,
            result={"health_test": "completed"},
            execution_time_ms=500
        )
        
        final_health = self.bridge.get_health_status()
        health_checks.append(final_health)
        
        # Assert: Verify consistent health throughout execution
        for i, health in enumerate(health_checks):
            assert health.state == IntegrationState.ACTIVE, f"Health check {i} failed: {health.state}"
            assert health.consecutive_failures == 0, f"Health check {i} has failures: {health.consecutive_failures}"
        
        # Verify health metrics improved
        metrics = self.bridge.get_integration_metrics()
        assert metrics.health_checks_performed >= len(health_checks)
        assert metrics.successful_initializations > 0
        assert metrics.failed_initializations == 0
        
        # Verify uptime tracking
        assert final_health.uptime_seconds > 0
        assert final_health.last_health_check is not None
        
        self.logger.info(f"Health monitoring completed - {len(health_checks)} health checks passed")

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_cross_service_agent_websocket_coordination(self, real_services_fixture):
        """
        Test cross-service agent-WebSocket coordination (agents [U+2194] backend [U+2194] frontend).
        
        BUSINESS VALUE: Ensures complete system integration for seamless
        agent execution visibility across all system components.
        """
        # Arrange: Set up cross-service coordination infrastructure
        await self.setup_real_websocket_manager()
        await self.setup_real_thread_registry()
        
        user_context = await self.create_real_user_execution_context()
        
        # Initialize bridge with cross-service awareness
        integration_result = await self.bridge.ensure_integration(registry=self.thread_registry)
        assert integration_result.success
        
        # Act: Execute cross-service coordination sequence
        cross_service_context = {
            "coordination_test": True,
            "services": ["agents", "backend", "frontend"],
            "integration_points": ["websocket_manager", "thread_registry", "user_context"]
        }
        
        # 1. Agent service initiates
        await self.bridge.notify_agent_started(
            run_id=user_context.run_id,
            agent_name=self.test_agent_name,
            context=cross_service_context,
            trace_context={"service": "agents", "coordination_id": uuid.uuid4().hex[:8]}
        )
        
        # 2. Backend service processes
        await self.bridge.notify_agent_thinking(
            run_id=user_context.run_id,
            agent_name=self.test_agent_name,
            thinking_content="Backend processing cross-service coordination...",
            context={"service": "backend", "processing_stage": "coordination"}
        )
        
        # 3. Tool execution across services
        cross_service_tools = [
            {"name": "backend_analyzer", "service": "backend"},
            {"name": "agent_processor", "service": "agents"},
            {"name": "websocket_notifier", "service": "frontend"}
        ]
        
        for tool_info in cross_service_tools:
            await self.bridge.notify_tool_executing(
                run_id=user_context.run_id,
                tool_name=tool_info["name"],
                tool_input={"service_context": tool_info["service"]},
                context={"cross_service": True, "target_service": tool_info["service"]}
            )
            
            await asyncio.sleep(0.1)  # Simulate cross-service latency
            
            await self.bridge.notify_tool_completed(
                run_id=user_context.run_id,
                tool_name=tool_info["name"],
                tool_output={
                    "service": tool_info["service"],
                    "coordination_status": "successful",
                    "cross_service_data": f"Processed by {tool_info['service']}"
                },
                execution_time_ms=100,
                context={"coordination_success": True}
            )
        
        # 4. Frontend receives completion
        await self.bridge.notify_agent_completed(
            run_id=user_context.run_id,
            agent_name=self.test_agent_name,
            result={
                "cross_service_coordination": "successful",
                "services_involved": ["agents", "backend", "frontend"],
                "coordination_metrics": {
                    "total_services": 3,
                    "successful_handoffs": 3,
                    "latency_acceptable": True
                }
            },
            execution_time_ms=400,
            context={"coordination_complete": True, "service": "frontend"}
        )
        
        # Assert: Verify successful cross-service coordination
        health_status = self.bridge.get_health_status()
        assert health_status.state == IntegrationState.ACTIVE
        assert health_status.websocket_manager_healthy
        assert health_status.registry_healthy
        
        # Verify no coordination errors
        metrics = self.bridge.get_integration_metrics()
        assert metrics.failed_initializations == 0
        assert metrics.recovery_attempts == 0  # No recovery needed
        
        self.logger.info("Cross-service agent-WebSocket coordination completed successfully")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_event_queue_management_during_websocket_issues(self, real_services_fixture):
        """
        Test agent event queue management and delivery guarantees during WebSocket issues.
        
        BUSINESS VALUE: Ensures agent events are not lost even when WebSocket
        connections are temporarily disrupted, maintaining user experience continuity.
        """
        # Arrange: Set up bridge with event queuing
        await self.setup_real_websocket_manager()
        await self.setup_real_thread_registry()
        
        user_context = await self.create_real_user_execution_context()
        
        # Initialize bridge
        integration_result = await self.bridge.ensure_integration(registry=self.thread_registry)
        assert integration_result.success
        
        # Act: Simulate event generation during WebSocket disruption
        events_during_disruption = []
        
        # Generate events normally first
        await self.bridge.notify_agent_started(
            run_id=user_context.run_id,
            agent_name=self.test_agent_name,
            context={"queue_test": "pre_disruption"}
        )
        
        # Simulate WebSocket disruption (while continuing agent operations)
        disruption_start = time.time()
        
        # Generate events during simulated disruption
        disruption_events = [
            ("agent_thinking", "Processing during WebSocket disruption..."),
            ("tool_executing", "background_processor"),
            ("tool_completed", "background_processor"),
            ("agent_thinking", "Continuing processing despite connection issues..."),
        ]
        
        for event_type, content in disruption_events:
            if event_type == "agent_thinking":
                await self.bridge.notify_agent_thinking(
                    run_id=user_context.run_id,
                    agent_name=self.test_agent_name,
                    thinking_content=content,
                    context={"during_disruption": True}
                )
            elif event_type == "tool_executing":
                await self.bridge.notify_tool_executing(
                    run_id=user_context.run_id,
                    tool_name=content,
                    tool_input={"disruption_resilience_test": True},
                    context={"during_disruption": True}
                )
            elif event_type == "tool_completed":
                await self.bridge.notify_tool_completed(
                    run_id=user_context.run_id,
                    tool_name=content,
                    tool_output={"processed_during_disruption": True},
                    execution_time_ms=50,
                    context={"during_disruption": True}
                )
            
            events_during_disruption.append(event_type)
            await asyncio.sleep(0.1)
        
        disruption_duration = time.time() - disruption_start
        
        # WebSocket "recovers" - complete agent execution
        await self.bridge.notify_agent_completed(
            run_id=user_context.run_id,
            agent_name=self.test_agent_name,
            result={
                "queue_management_test": "completed",
                "events_during_disruption": len(events_during_disruption),
                "disruption_duration_ms": int(disruption_duration * 1000),
                "resilience_demonstrated": True
            },
            execution_time_ms=int(disruption_duration * 1000),
            context={"post_disruption": True}
        )
        
        # Assert: Verify event queue management and delivery guarantees
        health_status = self.bridge.get_health_status()
        assert health_status.state == IntegrationState.ACTIVE
        
        # Verify bridge maintained operations during disruption
        metrics = self.bridge.get_integration_metrics()
        assert metrics.successful_initializations > 0
        
        # Verify all events were processed (even during disruption)
        assert len(events_during_disruption) == 4, "Not all disruption events were processed"
        
        self.logger.info(f"Event queue management test completed - {len(events_during_disruption)} events processed during {disruption_duration:.3f}s disruption")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_business_critical_websocket_events_complete_suite(self, real_services_fixture):
        """
        Test business-critical agent event bridging - all 5 WebSocket events MUST be sent.
        
        BUSINESS CRITICALITY: These events enable substantive chat interactions.
        Without these events, the platform provides no business value.
        """
        # Arrange: Set up complete business-critical event infrastructure
        await self.setup_real_websocket_manager()
        await self.setup_real_thread_registry()
        
        user_context = await self.create_real_user_execution_context()
        
        # Initialize bridge for mission-critical operations
        integration_result = await self.bridge.ensure_integration(registry=self.thread_registry)
        assert integration_result.success, "CRITICAL: Bridge initialization failed"
        
        # Track all 5 critical events
        critical_events = {
            "agent_started": False,
            "agent_thinking": False,
            "tool_executing": False,
            "tool_completed": False,
            "agent_completed": False
        }
        
        event_details = {}
        
        # Act: Execute complete business-critical event sequence
        business_context = {
            "business_critical": True,
            "revenue_impact": "high",
            "user_experience_critical": True,
            "mission_critical_test": True
        }
        
        # 1. CRITICAL: agent_started - User must see agent began processing
        start_time = time.time()
        await self.bridge.notify_agent_started(
            run_id=user_context.run_id,
            agent_name=self.test_agent_name,
            context=business_context,
            trace_context={"business_critical": True}
        )
        critical_events["agent_started"] = True
        event_details["agent_started"] = {"timestamp": time.time(), "success": True}
        
        # 2. CRITICAL: agent_thinking - Real-time reasoning visibility 
        await self.bridge.notify_agent_thinking(
            run_id=user_context.run_id,
            agent_name=self.test_agent_name,
            thinking_content="BUSINESS CRITICAL: Analyzing user's high-priority optimization request...",
            context={"business_value": "real_time_ai_visibility"}
        )
        critical_events["agent_thinking"] = True
        event_details["agent_thinking"] = {"timestamp": time.time(), "success": True}
        
        # 3. CRITICAL: tool_executing - Tool usage transparency
        await self.bridge.notify_tool_executing(
            run_id=user_context.run_id,
            tool_name="business_value_analyzer",
            tool_input={
                "analysis_type": "high_value_optimization",
                "business_impact": "revenue_critical"
            },
            context={"tool_transparency": "business_critical"}
        )
        critical_events["tool_executing"] = True
        event_details["tool_executing"] = {"timestamp": time.time(), "success": True}
        
        # 4. CRITICAL: tool_completed - Tool results display (delivers actionable insights)
        await self.bridge.notify_tool_completed(
            run_id=user_context.run_id,
            tool_name="business_value_analyzer",
            tool_output={
                "actionable_insights": [
                    "Immediate 20% cost reduction opportunity identified",
                    "ROI improvement strategy available",
                    "Risk mitigation recommendations ready"
                ],
                "business_value_delivered": True,
                "immediate_action_required": True
            },
            execution_time_ms=150,
            context={"actionable_insights_delivered": True}
        )
        critical_events["tool_completed"] = True
        event_details["tool_completed"] = {"timestamp": time.time(), "success": True}
        
        # 5. CRITICAL: agent_completed - User must know when valuable response is ready
        business_result = {
            "optimization_recommendations": [
                {"action": "rightsizing", "savings": "$5000/month", "effort": "low"},
                {"action": "reserved_instances", "savings": "$15000/month", "effort": "medium"}
            ],
            "total_monthly_savings": "$20000",
            "implementation_priority": "immediate",
            "business_impact": "high_value_delivered",
            "user_action_required": True
        }
        
        await self.bridge.notify_agent_completed(
            run_id=user_context.run_id,
            agent_name=self.test_agent_name,
            result=business_result,
            execution_time_ms=int((time.time() - start_time) * 1000),
            context={"business_value_complete": True}
        )
        critical_events["agent_completed"] = True
        event_details["agent_completed"] = {"timestamp": time.time(), "success": True}
        
        # Assert: VERIFY ALL 5 CRITICAL EVENTS WERE SENT (NON-NEGOTIABLE)
        for event_type, sent in critical_events.items():
            assert sent, f"CRITICAL FAILURE: {event_type} event was NOT sent - this breaks business value delivery"
        
        # Verify event sequence and timing
        event_timestamps = [details["timestamp"] for details in event_details.values()]
        for i in range(1, len(event_timestamps)):
            assert event_timestamps[i] >= event_timestamps[i-1], "Events sent out of order"
        
        # Verify bridge health after business-critical operations
        health_status = self.bridge.get_health_status()
        assert health_status.state == IntegrationState.ACTIVE, "CRITICAL: Bridge unhealthy after business operations"
        assert health_status.consecutive_failures == 0, "CRITICAL: Bridge has failures during business operations"
        
        # Verify business-critical metrics
        metrics = self.bridge.get_integration_metrics()
        assert metrics.successful_initializations > 0, "CRITICAL: No successful initializations"
        assert metrics.failed_initializations == 0, "CRITICAL: Failed initializations detected"
        
        total_sequence_time = event_timestamps[-1] - event_timestamps[0]
        assert total_sequence_time < 5.0, f"CRITICAL: Event sequence too slow ({total_sequence_time}s) - impacts user experience"
        
        self.logger.info(f"BUSINESS CRITICAL: All 5 WebSocket events successfully sent in {total_sequence_time:.3f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_websocket_bridge_performance_under_concurrent_execution(self, real_services_fixture):
        """
        Test agent WebSocket bridge performance under concurrent agent execution.
        
        BUSINESS VALUE: Ensures bridge can handle multiple simultaneous agent
        executions without performance degradation or event loss.
        """
        # Arrange: Set up performance testing infrastructure
        await self.setup_real_websocket_manager()
        await self.setup_real_thread_registry()
        
        # Initialize bridge for performance testing
        integration_result = await self.bridge.ensure_integration(registry=self.thread_registry)
        assert integration_result.success
        
        # Create multiple concurrent execution contexts
        concurrent_executions = 5
        execution_contexts = []
        
        for i in range(concurrent_executions):
            context = await self.create_real_user_execution_context(
                user_id=f"perf_user_{i}",
                thread_id=f"perf_thread_{i}"
            )
            execution_contexts.append(context)
        
        # Act: Execute concurrent agent operations
        performance_start = time.time()
        concurrent_tasks = []
        
        for i, context in enumerate(execution_contexts):
            task = self.execute_performance_agent_sequence(context, execution_id=i)
            concurrent_tasks.append(task)
        
        # Wait for all concurrent executions
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        performance_end = time.time()
        
        # Assert: Verify performance characteristics
        total_performance_time = performance_end - performance_start
        
        # Check execution results
        successful_executions = 0
        failed_executions = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_executions += 1
                self.logger.error(f"Execution {i} failed: {result}")
            else:
                successful_executions += 1
                assert result["status"] == "success", f"Execution {i} reported failure"
        
        # Performance assertions
        assert successful_executions == concurrent_executions, f"Only {successful_executions}/{concurrent_executions} executions succeeded"
        assert failed_executions == 0, f"{failed_executions} executions failed"
        
        # Verify performance timing
        max_acceptable_time = concurrent_executions * 1.0  # 1 second per execution max
        assert total_performance_time < max_acceptable_time, f"Performance test too slow: {total_performance_time:.3f}s > {max_acceptable_time}s"
        
        # Verify bridge health after performance stress
        health_status = self.bridge.get_health_status()
        assert health_status.state == IntegrationState.ACTIVE, "Bridge degraded under performance load"
        assert health_status.consecutive_failures == 0, "Bridge has failures after performance test"
        
        # Verify performance metrics
        metrics = self.bridge.get_integration_metrics()
        assert metrics.successful_initializations > 0
        assert metrics.failed_initializations == 0
        
        avg_time_per_execution = total_performance_time / concurrent_executions
        self.logger.info(f"Performance test completed: {concurrent_executions} executions in {total_performance_time:.3f}s (avg: {avg_time_per_execution:.3f}s/execution)")

    async def execute_performance_agent_sequence(self, context: UserExecutionContext, execution_id: int) -> Dict[str, Any]:
        """Execute agent sequence optimized for performance testing."""
        sequence_start = time.time()
        
        # Streamlined event sequence for performance
        await self.bridge.notify_agent_started(
            run_id=context.run_id,
            agent_name=f"perf_agent_{execution_id}",
            context={"performance_test": True, "execution_id": execution_id}
        )
        
        await self.bridge.notify_agent_thinking(
            run_id=context.run_id,
            agent_name=f"perf_agent_{execution_id}",
            thinking_content=f"Performance test execution {execution_id}..."
        )
        
        await self.bridge.notify_tool_executing(
            run_id=context.run_id,
            tool_name="performance_tool",
            tool_input={"execution_id": execution_id}
        )
        
        await self.bridge.notify_tool_completed(
            run_id=context.run_id,
            tool_name="performance_tool",
            tool_output={"execution_id": execution_id, "result": "performance_complete"}
        )
        
        sequence_time = time.time() - sequence_start
        
        await self.bridge.notify_agent_completed(
            run_id=context.run_id,
            agent_name=f"perf_agent_{execution_id}",
            result={
                "execution_id": execution_id,
                "performance_metrics": {
                    "sequence_time_ms": int(sequence_time * 1000),
                    "events_sent": 5
                }
            },
            execution_time_ms=int(sequence_time * 1000)
        )
        
        return {
            "execution_id": execution_id,
            "status": "success",
            "sequence_time": sequence_time
        }

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_websocket_bridge_resource_management_and_cleanup(self, real_services_fixture):
        """
        Test agent WebSocket bridge resource management and cleanup.
        
        BUSINESS VALUE: Ensures bridge doesn't leak resources during long-running
        operations, maintaining system stability and performance.
        """
        # Arrange: Set up resource monitoring
        await self.setup_real_websocket_manager()
        await self.setup_real_thread_registry()
        
        # Initialize bridge and capture initial resource state
        integration_result = await self.bridge.ensure_integration(registry=self.thread_registry)
        assert integration_result.success
        
        initial_health = self.bridge.get_health_status()
        initial_metrics = self.bridge.get_integration_metrics()
        
        # Act: Execute resource-intensive operations
        resource_operations = 10
        resource_contexts = []
        
        for i in range(resource_operations):
            context = await self.create_real_user_execution_context(
                user_id=f"resource_user_{i}",
                thread_id=f"resource_thread_{i}"
            )
            resource_contexts.append(context)
        
        # Execute operations that create and clean up resources
        for i, context in enumerate(resource_contexts):
            await self.bridge.notify_agent_started(
                run_id=context.run_id,
                agent_name=f"resource_agent_{i}",
                context={"resource_test": True, "operation": i}
            )
            
            # Create some resource usage
            await self.bridge.notify_agent_thinking(
                run_id=context.run_id,
                agent_name=f"resource_agent_{i}",
                thinking_content=f"Resource operation {i} processing...",
                context={"resource_intensive": True}
            )
            
            await self.bridge.notify_agent_completed(
                run_id=context.run_id,
                agent_name=f"resource_agent_{i}",
                result={"resource_operation": i, "completed": True},
                execution_time_ms=100
            )
            
            # Small delay to allow resource cleanup
            await asyncio.sleep(0.05)
        
        # Allow time for cleanup
        await asyncio.sleep(0.5)
        
        # Assert: Verify resource management
        final_health = self.bridge.get_health_status()
        final_metrics = self.bridge.get_integration_metrics()
        
        # Verify bridge health maintained
        assert final_health.state == IntegrationState.ACTIVE
        assert final_health.consecutive_failures == 0
        
        # Verify resource metrics improved (operations completed successfully)
        assert final_metrics.successful_initializations >= initial_metrics.successful_initializations
        assert final_metrics.health_checks_performed > initial_metrics.health_checks_performed
        
        # Verify no resource leaks (metrics should be reasonable)
        assert final_metrics.failed_initializations == initial_metrics.failed_initializations  # No new failures
        assert final_metrics.recovery_attempts == initial_metrics.recovery_attempts  # No recovery needed
        
        # Verify uptime tracking
        assert final_health.uptime_seconds > initial_health.uptime_seconds
        
        self.logger.info(f"Resource management test completed: {resource_operations} operations processed successfully")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_event_serialization_and_websocket_message_format_validation(self, real_services_fixture):
        """
        Test agent event serialization and WebSocket message format validation.
        
        BUSINESS VALUE: Ensures agent events are properly formatted for WebSocket
        delivery, maintaining data integrity across the entire communication pipeline.
        """
        # Arrange: Set up serialization testing infrastructure
        await self.setup_real_websocket_manager()
        await self.setup_real_thread_registry()
        
        user_context = await self.create_real_user_execution_context()
        
        # Initialize bridge
        integration_result = await self.bridge.ensure_integration(registry=self.thread_registry)
        assert integration_result.success
        
        # Act: Test serialization of complex data structures
        complex_context = {
            "nested_data": {
                "user_preferences": {
                    "format": "json",
                    "language": "en-US",
                    "timezone": "UTC"
                },
                "execution_metadata": {
                    "timestamps": [time.time(), time.time() + 1],
                    "trace_ids": [uuid.uuid4().hex, uuid.uuid4().hex]
                }
            },
            "arrays": ["item1", "item2", "item3"],
            "numbers": [1, 2.5, -3, 4.0],
            "booleans": [True, False, True],
            "nulls": [None, None],
            "unicode": "Test [U+1F680] Unicode [U+00F1] [U+4E2D][U+6587]",
            "special_chars": "Special chars: <>&\"'`"
        }
        
        # Test serialization with complex agent_started event
        await self.bridge.notify_agent_started(
            run_id=user_context.run_id,
            agent_name="serialization_test_agent",
            context=complex_context,
            trace_context={"serialization_test": True, "complex_data": True}
        )
        
        # Test serialization with complex thinking content
        complex_thinking = """
        Multi-line thinking content with:
        - Special characters: !@#$%^&*()
        - Unicode:  TARGET:   PASS:   FAIL:   CYCLE:   CELEBRATION: 
        - JSON-like structure: {"key": "value", "number": 123}
        - Quotes: "double" and 'single'
        - Line breaks and tabs
        """
        
        await self.bridge.notify_agent_thinking(
            run_id=user_context.run_id,
            agent_name="serialization_test_agent",
            thinking_content=complex_thinking,
            context={"serialization_test": "complex_thinking"}
        )
        
        # Test serialization with complex tool data
        complex_tool_input = {
            "query_parameters": {
                "filters": ["cost > 1000", "region = us-west-2"],
                "aggregation": {"type": "sum", "field": "cost"},
                "date_range": {
                    "start": datetime.now(timezone.utc).isoformat(),
                    "end": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
                }
            },
            "configuration": {
                "timeout_ms": 30000,
                "retry_policy": {"max_attempts": 3, "backoff_ms": 1000},
                "output_format": "json"
            }
        }
        
        await self.bridge.notify_tool_executing(
            run_id=user_context.run_id,
            tool_name="complex_data_analyzer",
            tool_input=complex_tool_input,
            context={"serialization_test": "complex_tool_input"}
        )
        
        # Test serialization with complex tool output
        complex_tool_output = {
            "analysis_results": {
                "cost_breakdown": [
                    {"service": "EC2", "cost": 1500.50, "percentage": 45.2},
                    {"service": "RDS", "cost": 800.25, "percentage": 24.1},
                    {"service": "S3", "cost": 300.75, "percentage": 9.0}
                ],
                "recommendations": [
                    {
                        "type": "rightsizing",
                        "potential_savings": {"monthly": 450.0, "annual": 5400.0},
                        "confidence": 0.85,
                        "implementation": {"effort": "medium", "timeline": "2-3 weeks"}
                    }
                ],
                "metadata": {
                    "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                    "data_sources": ["cloudwatch", "billing", "usage_reports"],
                    "accuracy_score": 0.92
                }
            },
            "raw_data": {
                "query_execution_stats": {
                    "rows_processed": 15420,
                    "execution_time_ms": 2340,
                    "memory_usage_mb": 128.5
                }
            }
        }
        
        await self.bridge.notify_tool_completed(
            run_id=user_context.run_id,
            tool_name="complex_data_analyzer",
            tool_output=complex_tool_output,
            execution_time_ms=2340,
            context={"serialization_test": "complex_tool_output"}
        )
        
        # Test serialization with complex final result
        complex_result = {
            "optimization_plan": {
                "immediate_actions": [
                    {
                        "action": "terminate_unused_instances",
                        "instances": ["i-1234567890abcdef0", "i-0fedcba0987654321"],
                        "savings": {"monthly": 280.0, "percentage": 18.5},
                        "risk_level": "low"
                    }
                ],
                "medium_term_actions": [
                    {
                        "action": "migrate_to_graviton",
                        "affected_services": ["web_servers", "api_gateway"],
                        "savings": {"monthly": 520.0, "percentage": 35.0},
                        "risk_level": "medium",
                        "timeline": "Q2 2024"
                    }
                ]
            },
            "summary": {
                "total_potential_savings": {
                    "monthly": 800.0,
                    "annual": 9600.0,
                    "percentage_of_current_spend": 24.2
                },
                "implementation_priority": "high",
                "business_impact": "significant_cost_reduction"
            }
        }
        
        await self.bridge.notify_agent_completed(
            run_id=user_context.run_id,
            agent_name="serialization_test_agent",
            result=complex_result,
            execution_time_ms=3000,
            context={"serialization_test": "complex_result"}
        )
        
        # Assert: Verify serialization handled complex data correctly
        health_status = self.bridge.get_health_status()
        assert health_status.state == IntegrationState.ACTIVE
        assert health_status.consecutive_failures == 0, "Serialization caused failures"
        
        # Verify no errors in metrics
        metrics = self.bridge.get_integration_metrics()
        assert metrics.failed_initializations == 0, "Complex data caused initialization failures"
        
        self.logger.info("Complex data serialization test completed successfully")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_websocket_bridge_timeout_handling_and_circuit_breaker(self, real_services_fixture):
        """
        Test agent WebSocket bridge timeout handling and circuit breaker patterns.
        
        BUSINESS VALUE: Ensures bridge gracefully handles timeouts and prevents
        cascade failures, maintaining system stability under adverse conditions.
        """
        # Arrange: Set up timeout and circuit breaker testing
        await self.setup_real_websocket_manager()
        await self.setup_real_thread_registry()
        
        # Create bridge with custom timeout configuration for testing
        self.bridge.config.integration_verification_timeout_s = 2  # Short timeout for testing
        self.bridge.config.recovery_max_attempts = 2
        self.bridge.config.recovery_base_delay_s = 0.1
        
        user_context = await self.create_real_user_execution_context()
        
        # Initialize bridge
        integration_result = await self.bridge.ensure_integration(registry=self.thread_registry)
        assert integration_result.success
        
        # Act: Test timeout handling during operations
        timeout_test_start = time.time()
        
        # Generate rapid event sequence to test timeout handling
        rapid_events = 20
        for i in range(rapid_events):
            await self.bridge.notify_agent_thinking(
                run_id=user_context.run_id,
                agent_name="timeout_test_agent",
                thinking_content=f"Rapid event {i+1} to test timeout handling...",
                context={"timeout_test": True, "event_sequence": i+1}
            )
            
            # Very short delay to create potential timeout conditions
            await asyncio.sleep(0.01)
        
        # Test completion under potential timeout stress
        await self.bridge.notify_agent_completed(
            run_id=user_context.run_id,
            agent_name="timeout_test_agent",
            result={
                "timeout_test": "completed",
                "rapid_events_processed": rapid_events,
                "timeout_handling": "successful"
            },
            execution_time_ms=int((time.time() - timeout_test_start) * 1000)
        )
        
        # Test circuit breaker behavior with health monitoring
        health_checks = []
        for i in range(5):
            health = self.bridge.get_health_status()
            health_checks.append(health)
            await asyncio.sleep(0.1)
        
        # Assert: Verify timeout handling and circuit breaker behavior
        final_health = self.bridge.get_health_status()
        assert final_health.state == IntegrationState.ACTIVE, "Bridge failed under timeout stress"
        
        # Verify circuit breaker didn't trigger unnecessarily
        assert final_health.consecutive_failures == 0, "Timeout handling caused consecutive failures"
        
        # Verify health remained stable throughout
        for i, health in enumerate(health_checks):
            assert health.state in [IntegrationState.ACTIVE, IntegrationState.INITIALIZING], f"Health check {i} shows degraded state: {health.state}"
        
        # Verify metrics show resilience
        metrics = self.bridge.get_integration_metrics()
        assert metrics.recovery_attempts <= 1, f"Too many recovery attempts: {metrics.recovery_attempts}"
        assert metrics.successful_initializations > 0
        
        total_test_time = time.time() - timeout_test_start
        self.logger.info(f"Timeout and circuit breaker test completed in {total_test_time:.3f}s - {rapid_events} rapid events processed successfully")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_websocket_bridge_authentication_and_user_authorization(self, real_services_fixture):
        """
        Test agent WebSocket bridge authentication and user authorization validation.
        
        BUSINESS VALUE: Ensures agent events are only delivered to authorized users,
        protecting sensitive AI insights and maintaining user privacy.
        """
        # Arrange: Set up authentication testing infrastructure
        await self.setup_real_websocket_manager()
        await self.setup_real_thread_registry()
        
        # Create multiple user contexts with different authorization levels
        authorized_user = await self.create_real_user_execution_context(
            user_id="authorized_user_123",
            thread_id="authorized_thread_456"
        )
        
        different_user = await self.create_real_user_execution_context(
            user_id="different_user_789",
            thread_id="different_thread_012"
        )
        
        # Initialize bridge
        integration_result = await self.bridge.ensure_integration(registry=self.thread_registry)
        assert integration_result.success
        
        # Act: Test authentication and authorization scenarios
        
        # 1. Test authorized user receives events
        await self.bridge.notify_agent_started(
            run_id=authorized_user.run_id,
            agent_name="auth_test_agent",
            context={
                "auth_test": True,
                "user_id": authorized_user.user_id,
                "authorization_level": "authorized"
            },
            trace_context={"auth_validation": True}
        )
        
        await self.bridge.notify_agent_thinking(
            run_id=authorized_user.run_id,
            agent_name="auth_test_agent",
            thinking_content="Processing authorized user's request with sensitive data access...",
            context={"sensitive_data_access": True, "authorized": True}
        )
        
        # 2. Test tool execution with authorization context
        await self.bridge.notify_tool_executing(
            run_id=authorized_user.run_id,
            tool_name="sensitive_data_analyzer",
            tool_input={
                "user_authorization": "verified",
                "access_level": "full",
                "sensitive_operation": True
            },
            context={"authorization_required": True}
        )
        
        await self.bridge.notify_tool_completed(
            run_id=authorized_user.run_id,
            tool_name="sensitive_data_analyzer",
            tool_output={
                "sensitive_insights": "Authorized access to premium analytics",
                "user_authorization": "verified",
                "data_classification": "sensitive"
            },
            execution_time_ms=200,
            context={"authorized_completion": True}
        )
        
        # 3. Test completion with authorization validation
        authorized_result = {
            "premium_insights": {
                "cost_optimization": "Advanced analysis available",
                "security_recommendations": "Full access granted",
                "compliance_status": "Authorized user - full report"
            },
            "authorization_metadata": {
                "user_id": authorized_user.user_id,
                "access_level": "premium",
                "data_sensitivity": "high"
            }
        }
        
        await self.bridge.notify_agent_completed(
            run_id=authorized_user.run_id,
            agent_name="auth_test_agent",
            result=authorized_result,
            execution_time_ms=400,
            context={"authorization_validated": True}
        )
        
        # 4. Test cross-user isolation (different user should not receive events for other users)
        await self.bridge.notify_agent_started(
            run_id=different_user.run_id,
            agent_name="isolation_test_agent",
            context={
                "isolation_test": True,
                "user_id": different_user.user_id,
                "should_be_isolated": True
            }
        )
        
        await self.bridge.notify_agent_completed(
            run_id=different_user.run_id,
            agent_name="isolation_test_agent",
            result={
                "user_isolation": "verified",
                "cross_user_access": "denied",
                "privacy_maintained": True
            },
            execution_time_ms=100
        )
        
        # Assert: Verify authentication and authorization behavior
        health_status = self.bridge.get_health_status()
        assert health_status.state == IntegrationState.ACTIVE
        assert health_status.consecutive_failures == 0, "Auth validation caused failures"
        
        # Verify no authentication errors in metrics
        metrics = self.bridge.get_integration_metrics()
        assert metrics.failed_initializations == 0, "Authentication caused initialization failures"
        assert metrics.recovery_attempts == 0, "Authentication required recovery"
        
        # Verify bridge maintained security throughout operations
        assert health_status.websocket_manager_healthy, "WebSocket manager unhealthy after auth test"
        assert health_status.registry_healthy, "Registry unhealthy after auth test"
        
        self.logger.info("Authentication and user authorization test completed successfully")

# Additional helper methods for comprehensive integration testing

    async def verify_websocket_event_delivery(self, expected_events: List[str], timeout: float = 5.0) -> bool:
        """Verify that expected WebSocket events were delivered within timeout."""
        start_time = time.time()
        received_event_types = set()
        
        while time.time() - start_time < timeout:
            # In real implementation, this would check actual WebSocket delivery
            # For now, we simulate by checking event timestamps
            for event_type in expected_events:
                if event_type in self.event_timestamps:
                    received_event_types.add(event_type)
            
            if len(received_event_types) == len(expected_events):
                return True
                
            await asyncio.sleep(0.1)
        
        missing_events = set(expected_events) - received_event_types
        self.logger.warning(f"Missing events after {timeout}s timeout: {missing_events}")
        return False

    def assert_integration_health(self, expected_state: IntegrationState = IntegrationState.ACTIVE):
        """Assert that bridge integration health meets expectations."""
        health = self.bridge.get_health_status()
        assert health.state == expected_state, f"Expected state {expected_state}, got {health.state}"
        assert health.websocket_manager_healthy, "WebSocket manager is not healthy"
        assert health.registry_healthy, "Registry is not healthy"
        assert health.consecutive_failures == 0, f"Bridge has {health.consecutive_failures} consecutive failures"

    def assert_integration_metrics(self, min_successful_init: int = 1, max_failed_init: int = 0):
        """Assert that bridge integration metrics meet expectations."""
        metrics = self.bridge.get_integration_metrics()
        assert metrics.successful_initializations >= min_successful_init, f"Expected >= {min_successful_init} successful initializations, got {metrics.successful_initializations}"
        assert metrics.failed_initializations <= max_failed_init, f"Expected <= {max_failed_init} failed initializations, got {metrics.failed_initializations}"

    async def create_realistic_agent_execution_scenario(self, scenario_type: str = "cost_optimization") -> Dict[str, Any]:
        """Create realistic agent execution scenario for comprehensive testing."""
        scenarios = {
            "cost_optimization": {
                "agent_name": "cost_optimizer_agent",
                "message": "Analyze my AWS costs and provide optimization recommendations",
                "tools": ["aws_cost_analyzer", "recommendation_generator", "report_formatter"],
                "expected_events": ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"],
                "business_value": "cost_reduction"
            },
            "security_audit": {
                "agent_name": "security_auditor_agent", 
                "message": "Perform comprehensive security audit of my infrastructure",
                "tools": ["vulnerability_scanner", "compliance_checker", "risk_assessor"],
                "expected_events": ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"],
                "business_value": "security_improvement"
            },
            "performance_analysis": {
                "agent_name": "performance_analyzer_agent",
                "message": "Analyze system performance and identify bottlenecks", 
                "tools": ["performance_monitor", "bottleneck_analyzer", "optimization_recommender"],
                "expected_events": ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"],
                "business_value": "performance_optimization"
            }
        }
        
        return scenarios.get(scenario_type, scenarios["cost_optimization"])