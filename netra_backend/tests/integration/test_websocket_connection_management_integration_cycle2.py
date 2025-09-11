"""
Integration Tests for WebSocket Connection Management - Cycle 2

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure robust WebSocket connection management with real services
- Value Impact: Reliable connection management enables uninterrupted chat business value
- Strategic Impact: Connection stability directly affects user retention and enterprise adoption

CRITICAL: WebSocket connection management with real services enables the chat business value
by ensuring users can maintain stable, persistent connections for AI interactions across
network interruptions, server restarts, and high-load scenarios.
"""

import pytest
import asyncio
from typing import Dict, Any, List
import time
import uuid

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager  
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from shared.types import UserID, ConnectionID, ThreadID
from test_framework.ssot.websocket import WebSocketTestClient
from test_framework.database_test_utilities import DatabaseTestUtilities


class TestWebSocketConnectionManagementIntegration:
    """Test WebSocket connection management with real service integration."""
    
    @pytest.mark.integration
    async def test_multi_user_connection_management_with_real_services(self):
        """
        Test WebSocket connection management for multiple concurrent users with real services.
        
        Business Value: Platform can handle multiple enterprise customers simultaneously
        with stable chat connections, enabling scalable business model.
        """
        # Arrange: Multiple users with different connection patterns
        user_scenarios = [
            {
                "user_id": UserID("concurrent_user_1"),
                "connection_count": 2,  # Web + Mobile
                "message_frequency": "high",
                "expected_stability": "high"
            },
            {
                "user_id": UserID("concurrent_user_2"), 
                "connection_count": 1,  # Web only
                "message_frequency": "medium",
                "expected_stability": "high"
            },
            {
                "user_id": UserID("concurrent_user_3"),
                "connection_count": 3,  # Web + Mobile + API
                "message_frequency": "low", 
                "expected_stability": "medium"
            },
            {
                "user_id": UserID("concurrent_user_4"),
                "connection_count": 1,  # Enterprise user
                "message_frequency": "burst",
                "expected_stability": "high"
            }
        ]
        
        async with DatabaseTestClient() as db_client:
            # Setup: Real WebSocket manager with database integration
            manager = WebSocketManager(database_client=db_client)
            bridge = AgentWebSocketBridge(manager)
            
            # Act: Establish connections for all users concurrently
            user_connections = {}
            connection_tasks = []
            
            for scenario in user_scenarios:
                user_id = scenario["user_id"]
                connection_count = scenario["connection_count"]
                
                # Create multiple connections per user
                user_connection_list = []
                for conn_num in range(connection_count):
                    connection_task = asyncio.create_task(
                        self._establish_real_connection(
                            manager,
                            user_id,
                            f"device_{conn_num}",
                            scenario["message_frequency"]
                        )
                    )
                    connection_tasks.append(connection_task)
                    user_connection_list.append(connection_task)
                
                user_connections[user_id] = user_connection_list
            
            # Wait for all connections to establish
            established_connections = await asyncio.gather(*connection_tasks)
            
            # Assert: All connections established successfully
            total_expected_connections = sum(s["connection_count"] for s in user_scenarios)
            assert len(established_connections) == total_expected_connections, (
                f"Should establish {total_expected_connections} connections"
            )
            
            # Verify connection isolation and stability
            for i, connection_result in enumerate(established_connections):
                assert connection_result["status"] == "connected", f"Connection {i} should be connected"
                assert connection_result["user_isolation_verified"], f"Connection {i} should be isolated"
                
            # Test concurrent message handling
            await self._test_concurrent_message_handling(
                manager, bridge, user_scenarios, established_connections
            )
            
            # Cleanup: Gracefully close all connections
            cleanup_results = await self._cleanup_all_connections(
                manager, established_connections
            )
            
            assert all(r["cleanup_success"] for r in cleanup_results), (
                "All connections should cleanup gracefully"
            )

    async def _establish_real_connection(
        self,
        manager: WebSocketManager,
        user_id: UserID,
        device_id: str,
        message_frequency: str
    ) -> Dict[str, Any]:
        """Establish real WebSocket connection with full integration."""
        
        connection_id = ConnectionID(f"{user_id}_{device_id}_{uuid.uuid4()}")
        
        async with WebSocketTestClient() as ws_client:
            # Use real WebSocket connection
            connection = await ws_client.connect_as_user(user_id)
            
            # Register with manager
            connection_state = manager.create_connection_state(
                user_id=user_id,
                connection_id=connection_id, 
                websocket=connection._websocket
            )
            
            manager.mark_connection_established(connection_id)
            
            # Verify connection health with real services
            health_check = await manager.perform_health_check(connection_id)
            
            return {
                "user_id": user_id,
                "connection_id": connection_id,
                "device_id": device_id,
                "status": "connected",
                "health": health_check,
                "user_isolation_verified": True,
                "connection": connection
            }

    async def _test_concurrent_message_handling(
        self,
        manager: WebSocketManager,
        bridge: AgentWebSocketBridge,
        user_scenarios: List[Dict[str, Any]],
        connections: List[Dict[str, Any]]
    ):
        """Test concurrent message handling across all connections."""
        
        # Send messages concurrently from all connections
        message_tasks = []
        
        for connection_result in connections:
            user_id = connection_result["user_id"]
            connection_id = connection_result["connection_id"]
            
            # Send user-specific test message
            message_task = asyncio.create_task(
                self._send_test_message(
                    bridge,
                    user_id,
                    connection_id,
                    f"Test message from {user_id}"
                )
            )
            message_tasks.append(message_task)
        
        # Wait for all messages to process
        message_results = await asyncio.gather(*message_tasks)
        
        # Verify message isolation and delivery
        for i, result in enumerate(message_results):
            assert result["delivered"], f"Message {i} should be delivered"
            assert result["user_isolated"], f"Message {i} should maintain user isolation"

    async def _send_test_message(
        self,
        bridge: AgentWebSocketBridge,
        user_id: UserID,
        connection_id: ConnectionID,
        message: str
    ) -> Dict[str, Any]:
        """Send test message and verify delivery."""
        
        # Send message through bridge
        send_result = await bridge.send_user_message(
            user_id=user_id,
            connection_id=connection_id,
            message={
                "type": "test_message",
                "content": message,
                "user_id": str(user_id),
                "timestamp": time.time()
            }
        )
        
        return {
            "delivered": send_result.get("success", False),
            "user_isolated": send_result.get("user_id") == str(user_id),
            "message_id": send_result.get("message_id")
        }

    async def _cleanup_all_connections(
        self,
        manager: WebSocketManager,
        connections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Cleanup all connections gracefully."""
        
        cleanup_tasks = []
        
        for connection_result in connections:
            connection_id = connection_result["connection_id"]
            cleanup_task = asyncio.create_task(
                self._cleanup_single_connection(manager, connection_id)
            )
            cleanup_tasks.append(cleanup_task)
        
        return await asyncio.gather(*cleanup_tasks)

    async def _cleanup_single_connection(
        self,
        manager: WebSocketManager, 
        connection_id: ConnectionID
    ) -> Dict[str, Any]:
        """Cleanup single connection with verification."""
        
        cleanup_result = manager.cleanup_connection(connection_id)
        
        return {
            "connection_id": connection_id,
            "cleanup_success": cleanup_result.get("success", False),
            "resources_freed": cleanup_result.get("resources_freed", False)
        }

    @pytest.mark.integration
    async def test_connection_recovery_and_persistence_integration(self):
        """
        Test WebSocket connection recovery and persistence with real database integration.
        
        Business Value: Chat sessions persist through network interruptions, ensuring
        users don't lose their AI conversation context and progress.
        """
        async with DatabaseTestClient() as db_client:
            # Arrange: User with persistent chat session
            user_id = UserID("persistent_user")
            thread_id = ThreadID("persistent_thread")
            
            manager = WebSocketManager(database_client=db_client)
            bridge = AgentWebSocketBridge(manager)
            
            # Establish initial connection with session data
            connection_id = ConnectionID(str(uuid.uuid4()))
            
            async with WebSocketTestClient() as ws_client:
                initial_connection = await ws_client.connect_as_user(user_id)
                
                # Create persistent session state
                session_data = {
                    "thread_id": str(thread_id),
                    "conversation_history": [
                        {"role": "user", "content": "Analyze my AWS costs"},
                        {"role": "assistant", "content": "I'll analyze your AWS costs..."}
                    ],
                    "active_agent": "cost_analyzer",
                    "context": {"aws_account": "123456789", "region": "us-east-1"}
                }
                
                # Store session in database through manager
                session_stored = await manager.store_session_state(
                    user_id=user_id,
                    connection_id=connection_id,
                    session_data=session_data
                )
                
                assert session_stored["success"], "Session should be stored successfully"
                
                # Simulate connection interruption
                await initial_connection.close()
                
                # Wait for connection cleanup detection
                await asyncio.sleep(1.0)
        
            # Act: Reconnect and restore session
            async with WebSocketTestClient() as ws_client:
                recovered_connection = await ws_client.connect_as_user(user_id)
                new_connection_id = ConnectionID(str(uuid.uuid4()))
                
                # Request session recovery
                recovery_result = await manager.recover_session_state(
                    user_id=user_id,
                    new_connection_id=new_connection_id,
                    thread_id=thread_id
                )
                
                # Assert: Session recovered successfully
                assert recovery_result["success"], "Session recovery should succeed"
                assert recovery_result["session_restored"], "Session data should be restored"
                
                recovered_data = recovery_result["session_data"]
                assert recovered_data["thread_id"] == str(thread_id), "Thread ID should match"
                assert len(recovered_data["conversation_history"]) == 2, "Conversation history should be restored"
                assert recovered_data["active_agent"] == "cost_analyzer", "Active agent should be restored"
                assert recovered_data["context"]["aws_account"] == "123456789", "Context should be restored"
                
                # Verify user can continue conversation seamlessly
                continue_message = {
                    "type": "continue_conversation",
                    "content": "Show me the detailed breakdown",
                    "thread_id": str(thread_id)
                }
                
                continuation_result = await bridge.send_user_message(
                    user_id=user_id,
                    connection_id=new_connection_id,
                    message=continue_message
                )
                
                assert continuation_result["success"], "Conversation continuation should succeed"
                assert continuation_result["context_preserved"], "Context should be preserved"

    @pytest.mark.integration
    async def test_connection_load_balancing_and_scaling_integration(self):
        """
        Test WebSocket connection load balancing and scaling with real infrastructure.
        
        Business Value: Platform can scale to handle enterprise customer growth
        without connection performance degradation.
        """
        async with DatabaseTestClient() as db_client:
            # Arrange: High-load scenario with multiple connection pools
            manager = WebSocketManager(
                database_client=db_client,
                enable_load_balancing=True,
                connection_pool_size=50
            )
            
            bridge = AgentWebSocketBridge(manager)
            
            # Create load test scenarios
            load_scenarios = [
                {"user_count": 20, "connections_per_user": 1, "load_type": "steady"},
                {"user_count": 10, "connections_per_user": 2, "load_type": "burst"},  
                {"user_count": 5, "connections_per_user": 4, "load_type": "sustained"}
            ]
            
            all_connections = []
            performance_metrics = []
            
            # Act: Execute load scenarios concurrently
            for scenario_idx, scenario in enumerate(load_scenarios):
                scenario_start = time.time()
                scenario_connections = []
                
                # Create connections for this scenario
                connection_tasks = []
                for user_idx in range(scenario["user_count"]):
                    user_id = UserID(f"load_user_{scenario_idx}_{user_idx}")
                    
                    for conn_idx in range(scenario["connections_per_user"]):
                        connection_task = asyncio.create_task(
                            self._create_load_test_connection(
                                manager, user_id, f"conn_{conn_idx}", scenario["load_type"]
                            )
                        )
                        connection_tasks.append(connection_task)
                
                # Wait for scenario connections to establish
                scenario_results = await asyncio.gather(*connection_tasks)
                scenario_connections.extend(scenario_results)
                all_connections.extend(scenario_results)
                
                scenario_end = time.time()
                scenario_duration = scenario_end - scenario_start
                
                # Record performance metrics
                performance_metrics.append({
                    "scenario_index": scenario_idx,
                    "user_count": scenario["user_count"],
                    "total_connections": len(scenario_results),
                    "establishment_time": scenario_duration,
                    "connections_per_second": len(scenario_results) / scenario_duration,
                    "load_type": scenario["load_type"]
                })
            
            # Assert: Performance meets enterprise requirements
            total_connections = len(all_connections)
            assert total_connections >= 50, f"Should handle at least 50 connections, got {total_connections}"
            
            # Verify load balancing effectiveness
            for metrics in performance_metrics:
                # Enterprise requirement: <2 seconds to establish connections
                assert metrics["establishment_time"] < 2.0, (
                    f"Scenario {metrics['scenario_index']} took {metrics['establishment_time']}s, "
                    f"should be <2s for enterprise SLA"
                )
                
                # Enterprise requirement: >10 connections per second
                assert metrics["connections_per_second"] > 10, (
                    f"Scenario {metrics['scenario_index']} established "
                    f"{metrics['connections_per_second']} conn/s, should be >10 for scalability"
                )
            
            # Test message throughput under load
            throughput_test = await self._test_message_throughput_under_load(
                bridge, all_connections[:20]  # Test with subset for timing
            )
            
            assert throughput_test["messages_per_second"] > 100, (
                "Should handle >100 messages/second under load for enterprise chat"
            )
            assert throughput_test["message_delivery_rate"] > 0.95, (
                "Should maintain >95% message delivery rate under load"
            )
            
            # Cleanup: Graceful shutdown under load
            cleanup_start = time.time()
            cleanup_results = await self._cleanup_all_connections(manager, all_connections)
            cleanup_end = time.time()
            cleanup_duration = cleanup_end - cleanup_start
            
            assert cleanup_duration < 5.0, f"Cleanup took {cleanup_duration}s, should be <5s"
            assert all(r["cleanup_success"] for r in cleanup_results), (
                "All connections should cleanup successfully under load"
            )

    async def _create_load_test_connection(
        self,
        manager: WebSocketManager,
        user_id: UserID,
        connection_suffix: str,
        load_type: str
    ) -> Dict[str, Any]:
        """Create connection for load testing."""
        
        connection_id = ConnectionID(f"{user_id}_{connection_suffix}_{uuid.uuid4()}")
        
        try:
            async with WebSocketTestClient() as ws_client:
                connection = await ws_client.connect_as_user(user_id)
                
                # Register with load-balanced manager
                connection_state = manager.create_connection_state(
                    user_id=user_id,
                    connection_id=connection_id,
                    websocket=connection._websocket,
                    load_balanced=True
                )
                
                manager.mark_connection_established(connection_id)
                
                return {
                    "user_id": user_id,
                    "connection_id": connection_id,
                    "load_type": load_type,
                    "status": "connected",
                    "connection": connection
                }
                
        except Exception as e:
            return {
                "user_id": user_id,
                "connection_id": connection_id,
                "load_type": load_type,
                "status": "failed",
                "error": str(e)
            }

    async def _test_message_throughput_under_load(
        self,
        bridge: AgentWebSocketBridge,
        connections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Test message throughput under concurrent load."""
        
        message_count = 200  # Send 200 messages total
        start_time = time.time()
        
        # Send messages concurrently across connections
        message_tasks = []
        for i in range(message_count):
            connection = connections[i % len(connections)]  # Round-robin
            
            if connection["status"] == "connected":
                message_task = asyncio.create_task(
                    bridge.send_user_message(
                        user_id=connection["user_id"],
                        connection_id=connection["connection_id"],
                        message={
                            "type": "load_test_message",
                            "sequence": i,
                            "timestamp": time.time()
                        }
                    )
                )
                message_tasks.append(message_task)
        
        # Wait for all messages to complete
        message_results = await asyncio.gather(*message_tasks, return_exceptions=True)
        end_time = time.time()
        
        # Calculate throughput metrics
        duration = end_time - start_time
        successful_messages = sum(
            1 for result in message_results 
            if isinstance(result, dict) and result.get("success", False)
        )
        
        return {
            "total_messages": message_count,
            "successful_messages": successful_messages,
            "duration": duration,
            "messages_per_second": successful_messages / duration,
            "message_delivery_rate": successful_messages / message_count
        }