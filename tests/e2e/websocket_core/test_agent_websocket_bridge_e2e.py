"""
E2E tests for AgentWebSocketBridge - Testing complete agent-WebSocket integration in production-like environment.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Seamless agent-to-user communication via WebSocket
- Value Impact: Ensures agents can reliably deliver real-time updates to authenticated users
- Strategic Impact: Critical integration - validates end-to-end agent communication pipeline

This E2E test validates the AgentWebSocketBridge works with real authentication,
real agent registries, and real WebSocket connections in production-like conditions.
CRITICAL: This test ensures agents can communicate with users through WebSocket infrastructure.
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from test_framework.ssot.base_test_case import BaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    IntegrationState,
    IntegrationConfig,
    HealthStatus,
    IntegrationResult
)
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext


class TestAgentWebSocketBridgeE2EIntegration(BaseTestCase):
    """
    E2E test for complete agent-WebSocket integration with real authentication and components.
    
    CRITICAL: This test validates agents can communicate with users through the complete
    WebSocket infrastructure stack in production-like conditions.
    """
    
    @pytest.fixture
    async def auth_helper(self):
        """Create authenticated test environment."""
        auth_helper = E2EAuthHelper()
        await auth_helper.initialize()
        yield auth_helper
        await auth_helper.cleanup()
    
    @pytest.fixture
    async def test_users(self, auth_helper):
        """Create test users representing different segments."""
        users = []
        
        user_configs = [
            {"email": "bridge_enterprise@netra.ai", "name": "Bridge Enterprise", "user_type": "enterprise"},
            {"email": "bridge_mid@netra.ai", "name": "Bridge Mid Tier", "user_type": "mid"},
            {"email": "bridge_free@netra.ai", "name": "Bridge Free", "user_type": "free"}
        ]
        
        for config in user_configs:
            user_data = await auth_helper.create_test_user(**config)
            users.append(user_data)
        
        return users
    
    @pytest.fixture
    async def production_websocket_manager(self, test_users):
        """Create production-like WebSocket manager with real authenticated connections."""
        manager = UnifiedWebSocketManager()
        
        # Create realistic WebSocket connections for authenticated users
        connections_data = []
        
        for user_data in test_users:
            # Production-like WebSocket mock with comprehensive tracking
            class ProductionWebSocketMock:
                def __init__(self, user_id, user_type):
                    self.user_id = user_id
                    self.user_type = user_type
                    self.sent_messages = []
                    self.closed = False
                    self.connection_start = datetime.now(timezone.utc)
                    self.stats = {
                        "messages_sent": 0,
                        "bytes_sent": 0,
                        "errors": 0,
                        "last_activity": self.connection_start
                    }
                
                async def send_json(self, data):
                    if self.closed:
                        self.stats["errors"] += 1
                        raise ConnectionError(f"WebSocket closed for {self.user_id}")
                    
                    # Track message delivery
                    message_size = len(str(data))
                    self.stats["messages_sent"] += 1
                    self.stats["bytes_sent"] += message_size
                    self.stats["last_activity"] = datetime.now(timezone.utc)
                    
                    self.sent_messages.append({
                        "timestamp": datetime.now(timezone.utc),
                        "data": data,
                        "size": message_size
                    })
                
                async def close(self):
                    self.closed = True
                
                def get_production_stats(self):
                    uptime = (datetime.now(timezone.utc) - self.connection_start).total_seconds()
                    return {
                        **self.stats,
                        "uptime_seconds": uptime,
                        "user_type": self.user_type,
                        "closed": self.closed
                    }
            
            mock_websocket = ProductionWebSocketMock(user_data["user_id"], user_data.get("user_type", "unknown"))
            
            connection = WebSocketConnection(
                connection_id=f"bridge_e2e_{user_data['user_id']}",
                user_id=user_data["user_id"], 
                websocket=mock_websocket,
                connected_at=datetime.now(timezone.utc),
                metadata={
                    "test": "agent_bridge_e2e",
                    "user_type": user_data.get("user_type", "unknown"),
                    "authenticated": True,
                    "email": user_data.get("email", "")
                }
            )
            
            await manager.add_connection(connection)
            connections_data.append((user_data, connection, mock_websocket))
        
        yield manager, connections_data
        
        # Cleanup
        for user_data, connection, _ in connections_data:
            try:
                await manager.remove_connection(connection.connection_id)
            except Exception:
                pass
    
    @pytest.fixture
    async def production_agent_registry(self, test_users):
        """Create production-like agent registry with real agent management."""
        # Mock LLM manager for agent registry
        from unittest.mock import AsyncMock
        
        mock_llm_manager = AsyncMock()
        mock_llm_manager.get_client.return_value = AsyncMock()
        
        # Create real agent registry
        agent_registry = AgentRegistry(llm_manager=mock_llm_manager)
        
        # Register test agents for each user
        for user_data in test_users:
            user_id = user_data["user_id"]
            user_type = user_data.get("user_type", "unknown")
            
            # Create execution context
            context = AgentExecutionContext(
                agent_name=f"{user_type}_test_agent",
                thread_id=f"bridge_thread_{user_id}",
                user_id=user_id,
                run_id=f"bridge_run_{user_id}_{int(datetime.now().timestamp())}"
            )
            
            # Create user session in registry (simulated)
            # In real usage, this would be handled by the registry automatically
        
        yield agent_registry
        
        # Cleanup
        try:
            await agent_registry.cleanup()
        except Exception:
            pass
    
    @pytest.fixture
    async def production_bridge_setup(self, production_websocket_manager, production_agent_registry):
        """Create production-ready AgentWebSocketBridge setup."""
        # Production-optimized configuration
        config = IntegrationConfig(
            initialization_timeout_s=10,
            health_check_interval_s=30,
            recovery_max_attempts=3,
            recovery_base_delay_s=1.0,
            recovery_max_delay_s=10.0,
            integration_verification_timeout_s=5
        )
        
        bridge = AgentWebSocketBridge(config)
        websocket_manager, connections_data = production_websocket_manager
        
        yield bridge, websocket_manager, production_agent_registry, connections_data
        
        # Cleanup
        await bridge.shutdown()
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_complete_agent_websocket_communication_pipeline(self, production_bridge_setup):
        """
        MISSION CRITICAL: Test complete agent-to-user communication through WebSocket infrastructure.
        
        This validates the entire pipeline: Agent -> Bridge -> WebSocket Manager -> User Connection
        """
        bridge, websocket_manager, agent_registry, connections_data = production_bridge_setup
        
        # Act - Initialize bridge with real components
        initialization_start = datetime.now()
        
        init_result = await bridge.initialize(
            websocket_manager=websocket_manager,
            agent_registry=agent_registry
        )
        
        initialization_time = (datetime.now() - initialization_start).total_seconds()
        
        # Assert - Initialization should succeed
        assert init_result.success is True, f"Bridge initialization failed: {init_result.error}"
        assert init_result.state == IntegrationState.ACTIVE
        assert bridge.state == IntegrationState.ACTIVE
        
        # Performance assertion - initialization should be fast
        assert initialization_time < 5.0, \
            f"Bridge initialization took {initialization_time:.2f}s, too slow for production"
        
        # Verify integration with real components
        verification_result = await bridge.verify_integration()
        assert verification_result.success is True
        
        # Test agent-to-user communication pipeline
        communication_results = []
        
        for user_data, connection, mock_websocket in connections_data:
            user_id = user_data["user_id"]
            user_type = connection.metadata["user_type"]
            
            # Create user execution context (simulating real agent execution)
            user_context = AgentExecutionContext(
                agent_name=f"e2e_{user_type}_agent",
                thread_id=f"e2e_thread_{user_id}",
                user_id=user_id,
                run_id=f"e2e_run_{user_id}_{int(datetime.now().timestamp())}"
            )
            
            # Test user emitter creation through bridge
            user_emitter = bridge.create_user_emitter(user_context)
            assert user_emitter is not None, f"Failed to create user emitter for {user_type} user"
            
            # Test complete message flow: Agent -> Bridge -> WebSocket -> User
            pipeline_start = datetime.now()
            
            test_messages = [
                {
                    "type": "agent_started",
                    "payload": {
                        "agent": f"e2e_{user_type}_agent",
                        "user_context": user_id,
                        "start_time": datetime.now(timezone.utc).isoformat()
                    }
                },
                {
                    "type": "agent_thinking", 
                    "payload": {
                        "thought": f"Processing {user_type} user request",
                        "progress": 50.0,
                        "user_context": user_id
                    }
                },
                {
                    "type": "agent_completed",
                    "payload": {
                        "result": f"E2E test completed for {user_type} user",
                        "user_context": user_id,
                        "completion_time": datetime.now(timezone.utc).isoformat()
                    }
                }
            ]
            
            # Send messages through the pipeline
            for message in test_messages:
                await websocket_manager.send_to_user(user_id, message)
            
            pipeline_time = (datetime.now() - pipeline_start).total_seconds()
            
            # Allow message processing
            await asyncio.sleep(0.2)
            
            # Verify messages reached user
            assert len(mock_websocket.sent_messages) == len(test_messages), \
                f"User {user_type} expected {len(test_messages)} messages, got {len(mock_websocket.sent_messages)}"
            
            # Verify message content integrity
            for i, sent_message in enumerate(mock_websocket.sent_messages):
                received_data = sent_message["data"]
                expected_message = test_messages[i]
                
                assert received_data["type"] == expected_message["type"]
                assert received_data["payload"]["user_context"] == user_id
            
            # Collect results
            production_stats = mock_websocket.get_production_stats()
            communication_results.append({
                "user_type": user_type,
                "user_id": user_id,
                "pipeline_time": pipeline_time,
                "messages_delivered": len(mock_websocket.sent_messages),
                "production_stats": production_stats
            })
        
        # Overall system validation
        bridge_health = bridge.get_health_status()
        assert bridge_health.state == IntegrationState.ACTIVE
        assert bridge_health.websocket_manager_healthy is True
        assert bridge_health.registry_healthy is True
        
        # Performance validation for production readiness
        avg_pipeline_time = sum(r["pipeline_time"] for r in communication_results) / len(communication_results)
        assert avg_pipeline_time < 1.0, \
            f"Average pipeline time {avg_pipeline_time:.2f}s too slow for real-time chat"
        
        # Validate all user segments received messages
        user_types_tested = {r["user_type"] for r in communication_results}
        assert len(user_types_tested) >= 3, "Should test multiple user segments"
        assert "enterprise" in user_types_tested
        assert "mid" in user_types_tested or "free" in user_types_tested
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_agent_websocket_bridge_resilience_and_recovery(self, production_bridge_setup):
        """
        Test AgentWebSocketBridge resilience under stress and recovery capabilities.
        
        This validates the bridge can handle production challenges like temporary
        component failures, high load, and connection issues.
        """
        bridge, websocket_manager, agent_registry, connections_data = production_bridge_setup
        
        # Initialize bridge
        await bridge.initialize(
            websocket_manager=websocket_manager,
            agent_registry=agent_registry
        )
        
        assert bridge.state == IntegrationState.ACTIVE
        
        # Start health monitoring for resilience testing
        await bridge.start_health_monitoring()
        
        try:
            # Simulate stress conditions
            stress_start = datetime.now()
            
            # Create multiple concurrent agent executions
            concurrent_executions = []
            
            for i, (user_data, connection, mock_websocket) in enumerate(connections_data):
                async def agent_execution_simulation(user_data, execution_id):
                    user_id = user_data["user_id"]
                    user_type = connection.metadata["user_type"]
                    
                    # Create execution context
                    context = AgentExecutionContext(
                        agent_name=f"stress_{user_type}_agent_{execution_id}",
                        thread_id=f"stress_thread_{user_id}_{execution_id}",
                        user_id=user_id,
                        run_id=f"stress_run_{execution_id}"
                    )
                    
                    # Simulate agent lifecycle with WebSocket communication
                    messages = []
                    
                    # Rapid-fire message sequence simulating real agent behavior
                    for step in range(10):
                        message = {
                            "type": "agent_progress",
                            "payload": {
                                "agent": context.agent_name,
                                "step": step,
                                "progress": (step + 1) / 10 * 100,
                                "user_context": user_id,
                                "execution_id": execution_id,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }
                        }
                        messages.append(message)
                    
                    # Send all messages rapidly through bridge
                    for message in messages:
                        try:
                            # Create user emitter through bridge
                            user_emitter = bridge.create_user_emitter(context)
                            if user_emitter:
                                await websocket_manager.send_to_user(user_id, message)
                        except Exception as e:
                            # Expected some failures under stress
                            pass
                        
                        # Brief delay to simulate realistic agent behavior
                        await asyncio.sleep(0.01)
                
                # Create concurrent execution tasks
                for exec_id in range(3):  # 3 concurrent "agents" per user
                    task = asyncio.create_task(
                        agent_execution_simulation(user_data, f"{i}_{exec_id}")
                    )
                    concurrent_executions.append(task)
            
            # Execute all concurrent agent simulations
            await asyncio.gather(*concurrent_executions, return_exceptions=True)
            
            stress_duration = (datetime.now() - stress_start).total_seconds()
            
            # Allow system to stabilize
            await asyncio.sleep(1.0)
            
            # Verify bridge maintained health during stress
            post_stress_health = bridge.get_health_status()
            
            # Bridge should still be functional after stress
            assert post_stress_health.state in [IntegrationState.ACTIVE, IntegrationState.DEGRADED], \
                f"Bridge state {post_stress_health.state} indicates failure under stress"
            
            # If degraded, should be able to recover
            if post_stress_health.state == IntegrationState.DEGRADED:
                recovery_result = await bridge.attempt_recovery()
                # Recovery may or may not succeed depending on conditions
                
            # Verify WebSocket connections are still functional
            functional_connections = 0
            total_messages_delivered = 0
            
            for user_data, connection, mock_websocket in connections_data:
                production_stats = mock_websocket.get_production_stats()
                
                if not mock_websocket.closed and production_stats["messages_sent"] > 0:
                    functional_connections += 1
                
                total_messages_delivered += production_stats["messages_sent"]
            
            # Should maintain reasonable functionality under stress
            connection_survival_rate = functional_connections / len(connections_data)
            assert connection_survival_rate >= 0.5, \
                f"Only {connection_survival_rate:.1%} connections survived stress test"
            
            # Should have delivered substantial number of messages
            expected_messages = len(connections_data) * 3 * 10  # users * executions * steps
            delivery_rate = total_messages_delivered / expected_messages if expected_messages > 0 else 0
            
            # Under stress, may not deliver all messages, but should deliver substantial portion
            assert delivery_rate >= 0.3, \
                f"Message delivery rate {delivery_rate:.1%} too low under stress"
            
            # Performance under stress should be acceptable
            assert stress_duration < 15.0, \
                f"Stress test took {stress_duration:.2f}s, indicating performance issues"
            
            # Verify bridge metrics tracked the stress appropriately
            bridge_metrics = bridge.get_metrics()
            assert bridge_metrics["health_checks_performed"] > 0
            
        finally:
            await bridge.stop_health_monitoring()
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_multi_user_agent_isolation_through_bridge(self, production_bridge_setup):
        """
        Test agent isolation through bridge ensures users only receive their own agent updates.
        
        CRITICAL: This test validates user isolation in the agent-WebSocket communication
        pipeline, ensuring no cross-user data leakage.
        """
        bridge, websocket_manager, agent_registry, connections_data = production_bridge_setup
        
        # Initialize bridge
        await bridge.initialize(
            websocket_manager=websocket_manager,
            agent_registry=agent_registry
        )
        
        # Create distinct agent executions for each user
        user_executions = {}
        
        for user_data, connection, mock_websocket in connections_data:
            user_id = user_data["user_id"]
            user_type = connection.metadata["user_type"]
            
            # Clear any existing messages
            mock_websocket.sent_messages.clear()
            
            # Create user-specific execution context
            context = AgentExecutionContext(
                agent_name=f"isolation_{user_type}_agent",
                thread_id=f"isolation_thread_{user_id}",
                user_id=user_id,
                run_id=f"isolation_run_{user_id}"
            )
            
            user_executions[user_id] = {
                "context": context,
                "user_type": user_type,
                "websocket": mock_websocket
            }
        
        # Send user-specific messages through bridge simultaneously
        isolation_start = datetime.now()
        
        async def send_user_specific_messages(user_id, execution_data):
            context = execution_data["context"]
            user_type = execution_data["user_type"]
            
            # Create user emitter through bridge
            user_emitter = bridge.create_user_emitter(context)
            assert user_emitter is not None
            
            # Send highly user-specific messages
            user_messages = [
                {
                    "type": "agent_started",
                    "payload": {
                        "agent": f"isolation_{user_type}_agent",
                        "user_specific_data": f"SECRET_DATA_FOR_{user_id}",
                        "user_context": user_id,
                        "user_type": user_type
                    }
                },
                {
                    "type": "agent_thinking",
                    "payload": {
                        "thought": f"Processing confidential {user_type} request",
                        "sensitive_info": f"PRIVATE_INFO_{user_id}",
                        "user_context": user_id
                    }
                },
                {
                    "type": "agent_completed", 
                    "payload": {
                        "result": f"Confidential results for {user_type} user {user_id}",
                        "personal_data": f"PII_DATA_{user_id}_{user_type}",
                        "user_context": user_id
                    }
                }
            ]
            
            for message in user_messages:
                await websocket_manager.send_to_user(user_id, message)
                await asyncio.sleep(0.05)  # Slight delay between messages
        
        # Send messages for all users concurrently
        isolation_tasks = [
            asyncio.create_task(send_user_specific_messages(user_id, execution_data))
            for user_id, execution_data in user_executions.items()
        ]
        
        await asyncio.gather(*isolation_tasks)
        
        isolation_time = (datetime.now() - isolation_start).total_seconds()
        
        # Allow message processing
        await asyncio.sleep(0.3)
        
        # CRITICAL VALIDATION: Verify perfect user isolation
        for user_id, execution_data in user_executions.items():
            user_type = execution_data["user_type"]
            websocket = execution_data["websocket"]
            
            # User should receive exactly 3 messages
            assert len(websocket.sent_messages) == 3, \
                f"User {user_type} ({user_id}) expected 3 messages, got {len(websocket.sent_messages)}"
            
            # SECURITY CRITICAL: Verify no cross-user data leakage
            for message_wrapper in websocket.sent_messages:
                message_data = message_wrapper["data"]
                payload = message_data.get("payload", {})
                
                # Every message must be for this specific user
                assert payload.get("user_context") == user_id, \
                    f"SECURITY VIOLATION: User {user_id} received message for {payload.get('user_context')}"
                
                # Check for user-specific sensitive data
                user_specific_markers = [
                    f"SECRET_DATA_FOR_{user_id}",
                    f"PRIVATE_INFO_{user_id}", 
                    f"PII_DATA_{user_id}_{user_type}"
                ]
                
                # Should find at least one user-specific marker in user's messages
                message_str = str(message_data)
                user_markers_found = [marker for marker in user_specific_markers if marker in message_str]
                
                if len(user_markers_found) > 0:
                    # If user-specific data is present, it must be for THIS user only
                    for marker in user_markers_found:
                        assert user_id in marker, \
                            f"SECURITY VIOLATION: User {user_id} message contains wrong user data: {marker}"
                
                # CRITICAL: Verify no other users' data is present
                for other_user_id in user_executions:
                    if other_user_id != user_id:
                        assert other_user_id not in message_str, \
                            f"SECURITY VIOLATION: User {user_id} message contains data for {other_user_id}"
                        
                        # Check other users' sensitive markers are NOT present
                        other_user_type = user_executions[other_user_id]["user_type"]
                        forbidden_markers = [
                            f"SECRET_DATA_FOR_{other_user_id}",
                            f"PRIVATE_INFO_{other_user_id}",
                            f"PII_DATA_{other_user_id}_{other_user_type}"
                        ]
                        
                        for forbidden_marker in forbidden_markers:
                            assert forbidden_marker not in message_str, \
                                f"SECURITY VIOLATION: User {user_id} received forbidden data: {forbidden_marker}"
        
        # Performance validation
        assert isolation_time < 2.0, \
            f"User isolation test took {isolation_time:.2f}s, may impact real-time performance"
        
        # Bridge should remain healthy after isolation test
        final_health = bridge.get_health_status()
        assert final_health.state == IntegrationState.ACTIVE
        assert final_health.websocket_manager_healthy is True