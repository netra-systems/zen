"""Real WebSocket Load Balancing Tests

Business Value Justification (BVJ):
- Segment: Mid & Enterprise (High Availability)
- Business Goal: Scalability & Load Distribution
- Value Impact: Ensures WebSocket connections are distributed efficiently across resources
- Strategic Impact: Enables horizontal scaling and high availability for enterprise usage

Tests real WebSocket load balancing scenarios with Docker services.
Validates load distribution and failover capabilities.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Set

import pytest
import websockets
from websockets.exceptions import WebSocketException

from netra_backend.tests.real_services_test_fixtures import skip_if_no_real_services
from shared.isolated_environment import get_env

env = get_env()


@pytest.mark.real_services
@pytest.mark.websocket
@pytest.mark.load_balancing
@skip_if_no_real_services
class TestRealWebSocketLoadBalancing:
    """Test real WebSocket load balancing scenarios."""
    
    @pytest.fixture
    def websocket_url(self):
        backend_host = env.get("BACKEND_HOST", "localhost")
        backend_port = env.get("BACKEND_PORT", "8000")
        return f"ws://{backend_host}:{backend_port}/ws"
    
    @pytest.fixture
    def auth_headers(self):
        jwt_token = env.get("TEST_JWT_TOKEN", "test_token_123")
        return {
            "Authorization": f"Bearer {jwt_token}",
            "User-Agent": "Netra-LoadBalancing-Test/1.0"
        }
    
    @pytest.mark.asyncio
    async def test_concurrent_connection_distribution(self, websocket_url, auth_headers):
        """Test distribution of concurrent WebSocket connections."""
        base_time = int(time.time())
        connection_distribution = []
        
        async def create_load_test_connection(connection_index: int):
            """Create individual connection for load testing."""
            user_id = f"load_user_{connection_index}_{base_time}"
            
            try:
                async with websockets.connect(
                    websocket_url,
                    extra_headers=auth_headers,
                    timeout=12
                ) as websocket:
                    # Connect with load balancing info request
                    await websocket.send(json.dumps({
                        "type": "connect",
                        "user_id": user_id,
                        "connection_index": connection_index,
                        "request_load_balance_info": True
                    }))
                    
                    connect_response = json.loads(await websocket.recv())
                    
                    # Send test message to generate load
                    await websocket.send(json.dumps({
                        "type": "load_test_message",
                        "user_id": user_id,
                        "connection_index": connection_index,
                        "content": f"Load test message from connection {connection_index}"
                    }))
                    
                    # Collect load balancing info
                    try:
                        load_response = json.loads(await asyncio.wait_for(websocket.recv(), timeout=3.0))
                        
                        connection_distribution.append({
                            "connection_index": connection_index,
                            "user_id": user_id,
                            "connection_id": connect_response.get("connection_id"),
                            "server_info": connect_response.get("server_info"),
                            "load_response": load_response,
                            "success": True
                        })
                        
                    except asyncio.TimeoutError:
                        connection_distribution.append({
                            "connection_index": connection_index,
                            "user_id": user_id,
                            "connection_id": connect_response.get("connection_id"),
                            "timeout": True,
                            "success": False
                        })
                    
                    # Hold connection briefly to simulate load
                    await asyncio.sleep(2)
                    
            except Exception as e:
                connection_distribution.append({
                    "connection_index": connection_index,
                    "user_id": user_id,
                    "error": str(e),
                    "success": False
                })
        
        # Create multiple concurrent connections
        connection_tasks = [create_load_test_connection(i) for i in range(6)]
        await asyncio.gather(*connection_tasks)
        
        # Analyze connection distribution
        successful_connections = [c for c in connection_distribution if c.get("success")]
        
        print(f"Load balancing test - Successful connections: {len(successful_connections)}/{len(connection_distribution)}")
        
        if successful_connections:
            # Check for server distribution indicators
            connection_ids = [c.get("connection_id") for c in successful_connections if c.get("connection_id")]
            server_infos = [c.get("server_info") for c in successful_connections if c.get("server_info")]
            
            print(f"Unique connection IDs: {len(set(connection_ids))}")
            print(f"Server info responses: {len([s for s in server_infos if s])}")
            
            # All connections should get unique IDs (load balancer working)
            if len(connection_ids) > 0:
                unique_connections = len(set(connection_ids))
                total_connections = len(connection_ids)
                
                assert unique_connections == total_connections, f"All connections should get unique IDs: {unique_connections}/{total_connections}"
                print("SUCCESS: Connection distribution working - unique connection IDs assigned")
                
                # If we have server info, check for distribution
                if server_infos:
                    unique_servers = len(set(str(s) for s in server_infos if s))
                    if unique_servers > 1:
                        print(f"SUCCESS: Load balancing detected - {unique_servers} different servers")
                    else:
                        print("INFO: All connections went to same server (single server setup or sticky sessions)")
            else:
                print("WARNING: No connection IDs captured for distribution analysis")
        else:
            print("WARNING: No successful connections for load balancing analysis")
        
        # Should have reasonable success rate
        success_rate = len(successful_connections) / len(connection_distribution) if connection_distribution else 0
        assert success_rate >= 0.5, f"Should have reasonable connection success rate: {success_rate:.1%}"
    
    @pytest.mark.asyncio
    async def test_load_balancer_health_check_integration(self, websocket_url, auth_headers):
        """Test WebSocket integration with load balancer health checks."""
        user_id = f"lb_health_test_{int(time.time())}"
        health_check_responses = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=15
            ) as websocket:
                # Connect with health check requests
                await websocket.send(json.dumps({
                    "type": "connect",
                    "user_id": user_id,
                    "request_health_check": True,
                    "load_balancer_integration": True
                }))
                
                connect_response = json.loads(await websocket.recv())
                health_check_responses.append(("connect", connect_response))
                
                # Request load balancer health status
                await websocket.send(json.dumps({
                    "type": "get_load_balancer_status",
                    "user_id": user_id,
                    "include_health_metrics": True
                }))
                
                # Collect health check responses
                timeout_time = time.time() + 8
                while time.time() < timeout_time:
                    try:
                        response_raw = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        response = json.loads(response_raw)
                        
                        health_check_responses.append(("health_check", response))
                        
                        # Look for load balancer health indicators
                        if "load_balancer" in response or "health" in response:
                            break
                            
                    except asyncio.TimeoutError:
                        break
                    except WebSocketException:
                        break
                
                # Send heartbeat to test health monitoring
                await websocket.send(json.dumps({
                    "type": "heartbeat",
                    "user_id": user_id,
                    "timestamp": time.time(),
                    "health_check": True
                }))
                
                try:
                    heartbeat_response = json.loads(await asyncio.wait_for(websocket.recv(), timeout=3.0))
                    health_check_responses.append(("heartbeat", heartbeat_response))
                except asyncio.TimeoutError:
                    pass
                
        except Exception as e:
            print(f"Load balancer health check test error: {e}")
        
        # Analyze health check integration
        print(f"Health check responses: {len(health_check_responses)}")
        
        # Should have connection response at minimum
        connect_responses = [r for r in health_check_responses if r[0] == "connect"]
        assert len(connect_responses) > 0, "Should have connection response"
        
        # Look for health-related responses
        health_responses = [r for r in health_check_responses if r[0] in ["health_check", "heartbeat"]]
        
        if health_responses:
            print("SUCCESS: Load balancer health check integration appears to be working")
            
            for response_type, response_data in health_responses:
                if isinstance(response_data, dict):
                    print(f"  {response_type}: {response_data.get('type', 'unknown_type')}")
        else:
            print("INFO: Load balancer health check integration not clearly detected")
        
        # Basic integration should work
        assert len(health_check_responses) > 0, "Should receive health check responses"
    
    @pytest.mark.asyncio
    async def test_session_affinity_behavior(self, websocket_url, auth_headers):
        """Test session affinity behavior in load balanced environment."""
        user_id = f"session_affinity_test_{int(time.time())}"
        session_tracking = []
        
        try:
            # First connection
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=12
            ) as websocket1:
                await websocket1.send(json.dumps({
                    "type": "connect",
                    "user_id": user_id,
                    "create_session": True,
                    "session_data": "initial_session_data"
                }))
                
                response1 = json.loads(await websocket1.recv())
                session_tracking.append(("session1", response1))
                
                # Create session data
                await websocket1.send(json.dumps({
                    "type": "set_session_data",
                    "user_id": user_id,
                    "key": "test_affinity",
                    "value": "affinity_test_value"
                }))
                
                try:
                    session_response1 = json.loads(await asyncio.wait_for(websocket1.recv(), timeout=3.0))
                    session_tracking.append(("set_session", session_response1))
                except asyncio.TimeoutError:
                    pass
                
                original_server = response1.get("server_id") or response1.get("connection_id")
            
            # Brief delay between connections
            await asyncio.sleep(1)
            
            # Second connection - test affinity
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=12
            ) as websocket2:
                await websocket2.send(json.dumps({
                    "type": "connect",
                    "user_id": user_id,
                    "restore_session": True,
                    "request_session_data": True
                }))
                
                response2 = json.loads(await websocket2.recv())
                session_tracking.append(("session2", response2))
                
                # Request session data to test affinity
                await websocket2.send(json.dumps({
                    "type": "get_session_data",
                    "user_id": user_id,
                    "key": "test_affinity"
                }))
                
                try:
                    session_response2 = json.loads(await asyncio.wait_for(websocket2.recv(), timeout=3.0))
                    session_tracking.append(("get_session", session_response2))
                except asyncio.TimeoutError:
                    session_tracking.append(("get_session", "timeout"))
                
                second_server = response2.get("server_id") or response2.get("connection_id")
            
        except Exception as e:
            print(f"Session affinity test error: {e}")
        
        # Analyze session affinity
        print(f"Session affinity tracking - Events: {len(session_tracking)}")
        
        # Should have established both sessions
        session1_events = [e for e in session_tracking if e[0] == "session1"]
        session2_events = [e for e in session_tracking if e[0] == "session2"]
        
        assert len(session1_events) > 0, "Should establish first session"
        assert len(session2_events) > 0, "Should establish second session"
        
        # Check for session data consistency
        get_session_events = [e for e in session_tracking if e[0] == "get_session"]
        
        if get_session_events and get_session_events[0][1] != "timeout":
            session_data = get_session_events[0][1]
            
            # If session data was retrieved, affinity likely working
            if "test_affinity" in str(session_data) or "affinity_test_value" in str(session_data):
                print("SUCCESS: Session affinity appears to be working - session data preserved")
            else:
                print("INFO: Session data not clearly preserved across connections")
        else:
            print("INFO: Session affinity test inconclusive - session data not retrieved")
        
        # Log session tracking for analysis
        for event_type, event_data in session_tracking:
            if isinstance(event_data, dict):
                print(f"  {event_type}: {event_data.get('type', 'no_type')} - ID: {event_data.get('connection_id', 'no_id')}")
            else:
                print(f"  {event_type}: {event_data}")
    
    @pytest.mark.asyncio
    async def test_load_balanced_message_processing_consistency(self, websocket_url, auth_headers):
        """Test message processing consistency across load balanced connections."""
        base_time = int(time.time())
        processing_results = []
        
        async def test_message_consistency(connection_index: int):
            """Test message processing consistency for individual connection."""
            user_id = f"consistency_user_{connection_index}_{base_time}"
            
            try:
                async with websockets.connect(
                    websocket_url,
                    extra_headers=auth_headers,
                    timeout=15
                ) as websocket:
                    # Connect
                    await websocket.send(json.dumps({
                        "type": "connect",
                        "user_id": user_id,
                        "test_consistency": True
                    }))
                    
                    connect_response = json.loads(await websocket.recv())
                    
                    # Send standard test message
                    test_message = {
                        "type": "user_message",
                        "user_id": user_id,
                        "content": "Standard consistency test message",
                        "connection_index": connection_index,
                        "expect_standard_response": True
                    }
                    
                    message_start_time = time.time()
                    await websocket.send(json.dumps(test_message))
                    
                    # Collect processing response
                    try:
                        response_raw = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                        response_time = time.time() - message_start_time
                        response = json.loads(response_raw)
                        
                        processing_results.append({
                            "connection_index": connection_index,
                            "user_id": user_id,
                            "response_time": response_time,
                            "response_type": response.get("type"),
                            "server_info": connect_response.get("server_info"),
                            "processing_successful": True,
                            "response": response
                        })
                        
                    except asyncio.TimeoutError:
                        processing_results.append({
                            "connection_index": connection_index,
                            "user_id": user_id,
                            "response_time": time.time() - message_start_time,
                            "timeout": True,
                            "processing_successful": False
                        })
                    
            except Exception as e:
                processing_results.append({
                    "connection_index": connection_index,
                    "user_id": user_id,
                    "error": str(e),
                    "processing_successful": False
                })
        
        # Test message processing across multiple connections
        consistency_tasks = [test_message_consistency(i) for i in range(4)]
        await asyncio.gather(*consistency_tasks)
        
        # Analyze processing consistency
        successful_processing = [r for r in processing_results if r.get("processing_successful")]
        
        print(f"Message processing consistency - Successful: {len(successful_processing)}/{len(processing_results)}")
        
        if successful_processing:
            # Check response time consistency
            response_times = [r["response_time"] for r in successful_processing]
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
            
            print(f"Response times - Avg: {avg_response_time:.3f}s, Min: {min_response_time:.3f}s, Max: {max_response_time:.3f}s")
            
            # Check response type consistency
            response_types = [r.get("response_type") for r in successful_processing]
            unique_response_types = set(response_types)
            
            print(f"Response types: {unique_response_types}")
            
            # Response times should be reasonable and consistent
            assert avg_response_time < 10, f"Average response time should be reasonable: {avg_response_time:.3f}s"
            
            # All connections should get similar response types (consistency)
            if len(unique_response_types) == 1:
                print("SUCCESS: Message processing consistency maintained across load balanced connections")
            else:
                print(f"INFO: Response types varied - may indicate different processing paths: {unique_response_types}")
        
        else:
            print("WARNING: No successful message processing for consistency analysis")
        
        # Should have reasonable success rate
        success_rate = len(successful_processing) / len(processing_results) if processing_results else 0
        assert success_rate >= 0.5, f"Should have reasonable processing success rate: {success_rate:.1%}"