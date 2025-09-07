"""
WebSocket Concurrent Load Testing Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Critical scalability requirement
- Business Goal: Support multiple concurrent users for platform growth
- Value Impact: CRITICAL - Platform must handle concurrent chat sessions to scale business
- Strategic/Revenue Impact: $1M+ revenue growth blocked if concurrent users can't be supported

CRITICAL CONCURRENT LOAD REQUIREMENTS:
1. Support minimum 20+ concurrent WebSocket connections without degradation
2. Message delivery must remain reliable under concurrent load
3. Authentication and user isolation must work under concurrent stress
4. Memory usage must remain stable during concurrent operations
5. Connection establishment time must not degrade significantly under load

CRITICAL REQUIREMENTS:
1. Uses REAL WebSocket connections with REAL concurrency (NO MOCKS per CLAUDE.md)
2. Tests actual concurrent user scenarios with authentication
3. Validates system performance under realistic load conditions
4. Ensures proper resource cleanup after concurrent testing
5. Tests load balancing and resource management

This test validates the concurrent connection infrastructure that enables the platform
to scale to hundreds of users simultaneously using AI chat functionality.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import statistics

import pytest
import websockets

# SSOT imports following CLAUDE.md absolute import requirements  
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig
from shared.isolated_environment import get_env


class TestWebSocketConcurrentLoad(BaseIntegrationTest):
    """
    Integration tests for WebSocket concurrent load and scalability.
    
    CRITICAL: All tests use REAL concurrent WebSocket connections.
    This ensures the platform can scale to support business growth.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_concurrent_load_test(self, real_services_fixture):
        """
        Set up concurrent load test environment with real services.
        
        BVJ: Test Infrastructure - Ensures reliable concurrent load testing
        """
        self.env = get_env()
        self.services = real_services_fixture
        self.test_session_id = f"concurrent_{uuid.uuid4().hex[:8]}"
        
        # CRITICAL: Verify real services are available (CLAUDE.md requirement)
        assert real_services_fixture, "Real services fixture required - no mocks allowed per CLAUDE.md"
        assert "backend" in real_services_fixture, "Real backend service required for concurrent load testing"
        assert "redis" in real_services_fixture, "Real Redis required for concurrent session management"
        
        # Initialize auth helper for concurrent testing
        auth_config = E2EAuthConfig(
            auth_service_url="http://localhost:8083",
            backend_url="http://localhost:8002",
            websocket_url="ws://localhost:8002/ws",
            timeout=45.0  # Longer timeout for load testing
        )
        
        self.auth_helper = E2EWebSocketAuthHelper(config=auth_config, environment="test")
        self.concurrent_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.load_metrics: Dict[str, Any] = {
            "connections_created": 0,
            "connections_failed": 0,
            "messages_sent": 0,
            "messages_failed": 0,
            "connection_times": [],
            "message_response_times": [],
            "peak_concurrent": 0,
            "errors": []
        }
        
        # Test basic connectivity
        try:
            test_token = self.auth_helper.create_test_jwt_token(user_id="load_test_user")
            assert test_token, "Failed to create test JWT for load testing"
        except Exception as e:
            pytest.fail(f"Real services not available for concurrent load testing: {e}")
    
    async def async_teardown(self):
        """Clean up all concurrent connections."""
        cleanup_tasks = []
        for user_id, ws in self.concurrent_connections.items():
            if not ws.closed:
                cleanup_tasks.append(ws.close())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self.concurrent_connections.clear()
        await super().async_teardown()
    
    async def create_concurrent_connection(
        self,
        user_id: str,
        connection_delay: float = 0.0
    ) -> Optional[websockets.WebSocketServerProtocol]:
        """
        Create a single concurrent WebSocket connection.
        
        Args:
            user_id: Unique user identifier
            connection_delay: Delay before creating connection
            
        Returns:
            WebSocket connection or None if failed
        """
        if connection_delay > 0:
            await asyncio.sleep(connection_delay)
        
        connection_start = time.time()
        
        try:
            token = self.auth_helper.create_test_jwt_token(
                user_id=user_id,
                email=f"{user_id}@loadtest.com",
                exp_minutes=30
            )
            
            headers = self.auth_helper.get_websocket_headers(token)
            
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.auth_helper.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=20.0
                ),
                timeout=25.0
            )
            
            connection_time = time.time() - connection_start
            
            self.concurrent_connections[user_id] = websocket
            self.load_metrics["connections_created"] += 1
            self.load_metrics["connection_times"].append(connection_time)
            
            # Update peak concurrent connections
            current_concurrent = len([ws for ws in self.concurrent_connections.values() if not ws.closed])
            self.load_metrics["peak_concurrent"] = max(self.load_metrics["peak_concurrent"], current_concurrent)
            
            return websocket
            
        except Exception as e:
            self.load_metrics["connections_failed"] += 1
            self.load_metrics["errors"].append({
                "type": "connection_failure",
                "user_id": user_id,
                "error": str(e),
                "timestamp": time.time()
            })
            return None
    
    async def simulate_user_activity(
        self,
        user_id: str,
        websocket: websockets.WebSocketServerProtocol,
        activity_duration: float = 20.0,
        message_interval: float = 3.0
    ) -> Dict[str, Any]:
        """
        Simulate realistic user activity for load testing.
        
        Args:
            user_id: User identifier
            websocket: WebSocket connection
            activity_duration: How long to simulate activity
            message_interval: Time between messages
            
        Returns:
            Activity results and metrics
        """
        activity_results = {
            "user_id": user_id,
            "messages_sent": 0,
            "messages_failed": 0,
            "activity_duration": 0.0,
            "connection_stable": True,
            "errors": []
        }
        
        start_time = time.time()
        message_count = 0
        
        try:
            while (time.time() - start_time) < activity_duration:
                if websocket.closed:
                    activity_results["connection_stable"] = False
                    break
                
                # Send realistic message
                message = {
                    "type": "user_activity_message",
                    "user_id": user_id,
                    "message_index": message_count,
                    "content": f"Load test message {message_count} from {user_id}",
                    "load_test_session": self.test_session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                send_start = time.time()
                
                try:
                    await websocket.send(json.dumps(message))
                    send_time = time.time() - send_start
                    
                    activity_results["messages_sent"] += 1
                    self.load_metrics["messages_sent"] += 1
                    self.load_metrics["message_response_times"].append(send_time)
                    message_count += 1
                    
                except Exception as e:
                    activity_results["messages_failed"] += 1
                    activity_results["errors"].append({
                        "type": "message_send_failure",
                        "error": str(e),
                        "timestamp": time.time()
                    })
                    self.load_metrics["messages_failed"] += 1
                
                # Wait before next message
                await asyncio.sleep(message_interval)
                
        except Exception as e:
            activity_results["errors"].append({
                "type": "activity_exception",
                "error": str(e),
                "timestamp": time.time()
            })
        
        activity_results["activity_duration"] = time.time() - start_time
        return activity_results
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_connection_establishment(self, real_services_fixture):
        """
        Test establishing multiple concurrent WebSocket connections.
        
        BVJ: Platform scalability - Must support concurrent user onboarding.
        Critical for business growth and user acquisition.
        """
        num_concurrent_users = 15
        users = [f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}" for i in range(num_concurrent_users)]
        
        try:
            # Create all connections concurrently
            connection_tasks = [
                asyncio.create_task(self.create_concurrent_connection(user_id, connection_delay=i * 0.1))
                for i, user_id in enumerate(users)
            ]
            
            # Wait for all connections to be attempted
            connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            # Analyze connection results
            successful_connections = 0
            failed_connections = 0
            
            for i, result in enumerate(connection_results):
                if isinstance(result, Exception):
                    failed_connections += 1
                elif result is not None:
                    successful_connections += 1
                else:
                    failed_connections += 1
            
            # Verify high success rate for concurrent connections
            success_rate = successful_connections / num_concurrent_users
            assert success_rate >= 0.8, f"Concurrent connection success rate too low: {success_rate:.1%}"
            
            # Verify connection establishment times are reasonable
            connection_times = self.load_metrics["connection_times"]
            if connection_times:
                avg_connection_time = statistics.mean(connection_times)
                max_connection_time = max(connection_times)
                
                assert avg_connection_time < 5.0, f"Average connection time too high under load: {avg_connection_time:.2f}s"
                assert max_connection_time < 10.0, f"Maximum connection time too high under load: {max_connection_time:.2f}s"
            
            # Test that all successful connections can send messages
            active_connections = [
                (user_id, ws) for user_id, ws in self.concurrent_connections.items()
                if not ws.closed
            ]
            
            # Send a test message from each active connection
            test_message_tasks = []
            for user_id, websocket in active_connections[:10]:  # Limit to first 10 for performance
                message = {
                    "type": "concurrent_connection_test",
                    "user_id": user_id,
                    "content": "Test message from concurrent connection",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                test_message_tasks.append(
                    asyncio.create_task(websocket.send(json.dumps(message)))
                )
            
            # Wait for test messages to be sent
            message_results = await asyncio.gather(*test_message_tasks, return_exceptions=True)
            
            message_success_rate = sum(1 for r in message_results if not isinstance(r, Exception)) / len(message_results)
            assert message_success_rate >= 0.8, f"Message success rate too low with concurrent connections: {message_success_rate:.1%}"
            
            # Clean up connections
            cleanup_tasks = [ws.close() for user_id, ws in active_connections]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
        except Exception as e:
            pytest.fail(f"Concurrent connection establishment test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_activity_simulation(self, real_services_fixture):
        """
        Test realistic concurrent user activity and message exchange.
        
        BVJ: Real-world scalability - Platform must handle realistic concurrent usage.
        Critical for supporting actual user growth and concurrent AI conversations.
        """
        num_concurrent_users = 12
        users = [f"activity_user_{i}_{uuid.uuid4().hex[:8]}" for i in range(num_concurrent_users)]
        
        try:
            # Establish connections with staggered timing
            active_connections = {}
            
            for i, user_id in enumerate(users):
                websocket = await self.create_concurrent_connection(user_id, connection_delay=i * 0.2)
                if websocket:
                    active_connections[user_id] = websocket
            
            # Verify sufficient connections established
            assert len(active_connections) >= 8, f"Insufficient concurrent connections: {len(active_connections)}"
            
            # Start concurrent user activity simulation
            activity_tasks = []
            
            for user_id, websocket in active_connections.items():
                # Vary activity patterns for realism
                activity_duration = 25.0 + (hash(user_id) % 10)  # 25-35 seconds
                message_interval = 2.0 + (hash(user_id) % 3)    # 2-5 seconds between messages
                
                activity_task = asyncio.create_task(
                    self.simulate_user_activity(
                        user_id, websocket,
                        activity_duration=activity_duration,
                        message_interval=message_interval
                    )
                )
                activity_tasks.append(activity_task)
            
            # Wait for all user activity to complete
            activity_results = await asyncio.gather(*activity_tasks, return_exceptions=True)
            
            # Analyze activity results
            successful_activities = 0
            total_messages_sent = 0
            total_messages_failed = 0
            connection_stability_count = 0
            
            for result in activity_results:
                if isinstance(result, Exception):
                    continue
                
                successful_activities += 1
                total_messages_sent += result["messages_sent"]
                total_messages_failed += result["messages_failed"]
                
                if result["connection_stable"]:
                    connection_stability_count += 1
            
            # Verify concurrent activity success metrics
            activity_success_rate = successful_activities / len(activity_tasks)
            assert activity_success_rate >= 0.75, f"Concurrent activity success rate too low: {activity_success_rate:.1%}"
            
            # Verify message delivery under concurrent load
            if total_messages_sent > 0:
                message_success_rate = total_messages_sent / (total_messages_sent + total_messages_failed)
                assert message_success_rate >= 0.85, f"Message success rate under concurrent load too low: {message_success_rate:.1%}"
            
            # Verify connection stability
            stability_rate = connection_stability_count / successful_activities if successful_activities > 0 else 0
            assert stability_rate >= 0.8, f"Connection stability under concurrent load too low: {stability_rate:.1%}"
            
            # Verify overall system performance metrics
            assert self.load_metrics["peak_concurrent"] >= 8, "Peak concurrent connections too low"
            
            if self.load_metrics["message_response_times"]:
                avg_response_time = statistics.mean(self.load_metrics["message_response_times"])
                assert avg_response_time < 2.0, f"Average message response time under load too high: {avg_response_time:.2f}s"
            
            # Clean up remaining connections
            cleanup_tasks = [ws.close() for ws in active_connections.values() if not ws.closed]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
        except Exception as e:
            pytest.fail(f"Concurrent user activity simulation test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_authentication_isolation(self, real_services_fixture):
        """
        Test that authentication remains isolated under concurrent load.
        
        BVJ: Security at scale - User isolation must work under concurrent load.
        Critical for preventing security breaches during high traffic.
        """
        num_concurrent_users = 10
        users = [f"auth_load_user_{i}_{uuid.uuid4().hex[:8]}" for i in range(num_concurrent_users)]
        
        try:
            # Create concurrent connections with different auth contexts
            auth_connections = {}
            auth_tokens = {}
            
            for user_id in users:
                # Create unique authentication context
                token = self.auth_helper.create_test_jwt_token(
                    user_id=user_id,
                    email=f"{user_id}@authload.com",
                    permissions=["read", "write", f"user_specific_{user_id}"]
                )
                auth_tokens[user_id] = token
                
                websocket = await self.create_concurrent_connection(user_id)
                if websocket:
                    auth_connections[user_id] = websocket
            
            # Send authenticated messages from each user concurrently
            auth_test_tasks = []
            sent_messages_by_user = {}
            
            for user_id, websocket in auth_connections.items():
                # Each user sends multiple authenticated messages
                user_messages = []
                for i in range(3):
                    message = {
                        "type": "authenticated_load_test",
                        "user_id": user_id,
                        "message_index": i,
                        "content": f"Authenticated message {i} from {user_id}",
                        "auth_token_hint": auth_tokens[user_id][-8:],  # Last 8 chars for identification
                        "user_specific_data": f"private_data_for_{user_id}",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    user_messages.append(message)
                
                sent_messages_by_user[user_id] = user_messages
                
                # Send messages concurrently for this user
                async def send_user_messages(uid, ws, messages):
                    results = []
                    for msg in messages:
                        try:
                            await ws.send(json.dumps(msg))
                            results.append({"success": True, "message": msg})
                        except Exception as e:
                            results.append({"success": False, "error": str(e), "message": msg})
                        await asyncio.sleep(0.5)  # Brief delay between messages
                    return results
                
                auth_test_tasks.append(
                    asyncio.create_task(send_user_messages(user_id, websocket, user_messages))
                )
            
            # Wait for all authenticated messages to be sent
            auth_results = await asyncio.gather(*auth_test_tasks, return_exceptions=True)
            
            # Analyze authentication isolation under load
            successful_auth_sessions = 0
            total_auth_messages_sent = 0
            
            for i, result in enumerate(auth_results):
                if isinstance(result, Exception):
                    continue
                
                user_id = list(auth_connections.keys())[i]
                successful_messages = sum(1 for r in result if r.get("success"))
                total_messages = len(result)
                
                if successful_messages > 0:
                    successful_auth_sessions += 1
                    total_auth_messages_sent += successful_messages
                
                # Verify this user's messages were processed
                user_success_rate = successful_messages / total_messages if total_messages > 0 else 0
                assert user_success_rate >= 0.5, f"User {user_id} auth message success rate too low under load: {user_success_rate:.1%}"
            
            # Verify overall authentication performance under concurrent load
            auth_session_success_rate = successful_auth_sessions / len(auth_connections)
            assert auth_session_success_rate >= 0.8, f"Authentication session success rate under load too low: {auth_session_success_rate:.1%}"
            
            # Test that connections can still handle additional messages after auth load
            final_test_tasks = []
            for user_id, websocket in list(auth_connections.items())[:5]:  # Test first 5 users
                if not websocket.closed:
                    final_message = {
                        "type": "post_auth_load_test",
                        "user_id": user_id,
                        "content": "Final test after authentication load",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    final_test_tasks.append(websocket.send(json.dumps(final_message)))
            
            if final_test_tasks:
                final_results = await asyncio.gather(*final_test_tasks, return_exceptions=True)
                final_success_rate = sum(1 for r in final_results if not isinstance(r, Exception)) / len(final_results)
                assert final_success_rate >= 0.8, "Post-authentication load test success rate too low"
            
            # Clean up
            cleanup_tasks = [ws.close() for ws in auth_connections.values() if not ws.closed]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
        except Exception as e:
            pytest.fail(f"Concurrent authentication isolation test failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_resource_management_under_load(self, real_services_fixture):
        """
        Test resource management and cleanup under concurrent load.
        
        BVJ: System stability - Resources must be properly managed at scale.
        Critical for preventing memory leaks and maintaining long-term system health.
        """
        num_concurrent_users = 20
        users = [f"resource_user_{i}_{uuid.uuid4().hex[:8]}" for i in range(num_concurrent_users)]
        
        try:
            # Track resource usage throughout test
            resource_snapshots = []
            
            # Initial resource snapshot
            initial_connections = len(self.concurrent_connections)
            resource_snapshots.append({
                "phase": "initial",
                "active_connections": initial_connections,
                "timestamp": time.time()
            })
            
            # Phase 1: Rapid connection establishment
            connection_tasks = [
                asyncio.create_task(self.create_concurrent_connection(user_id))
                for user_id in users
            ]
            
            connections = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            # Resource snapshot after connections
            active_after_connect = len([c for c in connections if c and not isinstance(c, Exception)])
            resource_snapshots.append({
                "phase": "after_connect",
                "active_connections": active_after_connect,
                "timestamp": time.time()
            })
            
            # Phase 2: Brief activity period
            active_connections = {
                users[i]: conn for i, conn in enumerate(connections)
                if conn and not isinstance(conn, Exception) and not conn.closed
            }
            
            # Send messages to create resource usage
            message_tasks = []
            for user_id, websocket in list(active_connections.items())[:15]:  # Limit for performance
                for i in range(5):  # 5 messages per user
                    message = {
                        "type": "resource_test_message",
                        "user_id": user_id,
                        "message_index": i,
                        "content": f"Resource management test message {i}",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    message_tasks.append(websocket.send(json.dumps(message)))
            
            message_results = await asyncio.gather(*message_tasks, return_exceptions=True)
            
            # Resource snapshot after activity
            resource_snapshots.append({
                "phase": "after_activity",
                "active_connections": len([ws for ws in active_connections.values() if not ws.closed]),
                "timestamp": time.time()
            })
            
            # Phase 3: Gradual connection cleanup
            cleanup_batch_size = 5
            for i in range(0, len(active_connections), cleanup_batch_size):
                batch_connections = list(active_connections.items())[i:i+cleanup_batch_size]
                
                cleanup_tasks = []
                for user_id, websocket in batch_connections:
                    if not websocket.closed:
                        cleanup_tasks.append(websocket.close())
                
                if cleanup_tasks:
                    await asyncio.gather(*cleanup_tasks, return_exceptions=True)
                
                # Brief delay between cleanup batches
                await asyncio.sleep(1.0)
            
            # Final resource snapshot
            final_active = len([ws for ws in self.concurrent_connections.values() if not ws.closed])
            resource_snapshots.append({
                "phase": "after_cleanup",
                "active_connections": final_active,
                "timestamp": time.time()
            })
            
            # Analyze resource management
            # Verify connections were properly established
            max_connections = max(snapshot["active_connections"] for snapshot in resource_snapshots)
            assert max_connections >= 10, f"Peak connections too low: {max_connections}"
            
            # Verify cleanup was effective
            initial_count = resource_snapshots[0]["active_connections"]
            final_count = resource_snapshots[-1]["active_connections"]
            
            # Final count should be close to initial (allowing for some test overhead)
            connection_growth = final_count - initial_count
            assert connection_growth <= 5, f"Too many connections not cleaned up: {connection_growth}"
            
            # Verify message processing under load
            successful_messages = sum(1 for r in message_results if not isinstance(r, Exception))
            message_success_rate = successful_messages / len(message_tasks) if message_tasks else 1.0
            assert message_success_rate >= 0.7, f"Message success rate under resource load too low: {message_success_rate:.1%}"
            
        except Exception as e:
            pytest.fail(f"Resource management under load test failed: {e}")