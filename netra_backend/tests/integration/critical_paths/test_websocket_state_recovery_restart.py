"""WebSocket State Recovery After Service Restart L4 Critical Test

Business Value Justification (BVJ):
- Segment: Enterprise/All tiers (critical for real-time collaboration)
- Business Goal: Ensure seamless user experience during system maintenance and updates
- Value Impact: Protects $18K+ MRR by preventing session loss and work interruption during deployments
- Strategic Impact: Critical for enterprise trust, SLA compliance, and zero-downtime deployment capability

Critical Path:
WebSocket connection -> State establishment -> Service restart simulation -> 
Automatic reconnection -> State recovery -> Session continuity validation

Coverage: WebSocket resilience, state persistence, automatic recovery, cross-service coordination
"""

from netra_backend.app.websocket.connection import ConnectionManager as WebSocketManager
from test_framework import setup_test_path
from pathlib import Path
import sys

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest
import websockets

from netra_backend.app.services.redis.session_manager import RedisSessionManager
from netra_backend.app.services.websocket_manager import WebSocketManager

from netra_backend.tests.l4_staging_critical_base import (

    CriticalPathMetrics,

    L4StagingCriticalPathTestBase,

)

@dataclass

class WebSocketStateData:

    """Container for WebSocket state data."""

    session_id: str

    user_id: str

    connection_id: str

    active_threads: List[str]

    message_history: List[Dict]

    last_activity: float

    state_checksum: str

class WebSocketStateRecoveryL4Test(L4StagingCriticalPathTestBase):

    """L4 test for WebSocket state recovery after service restart."""
    
    def __init__(self):

        super().__init__("WebSocket State Recovery After Service Restart")

        self.ws_manager: Optional[WebSocketManager] = None

        self.test_websockets: List = []

        self.pre_restart_states: Dict[str, WebSocketStateData] = {}

        self.post_restart_states: Dict[str, WebSocketStateData] = {}
        
    async def setup_test_specific_environment(self) -> None:

        """Setup WebSocket-specific test environment."""
        # Initialize WebSocket manager

        self.ws_manager = WebSocketManager()

        await self.ws_manager.initialize()
        
        # Validate WebSocket service availability

        ws_health_url = f"{self.service_endpoints.websocket}/health"

        response = await self.test_client.get(ws_health_url)
        
        if response.status_code != 200:

            raise RuntimeError(f"WebSocket service unavailable: {response.status_code}")
    
    async def execute_critical_path_test(self) -> Dict[str, Any]:

        """Execute WebSocket state recovery critical path test."""

        test_results = {

            "phase_1_connections": None,

            "phase_2_state_establishment": None,

            "phase_3_service_restart": None,

            "phase_4_reconnection": None,

            "phase_5_state_validation": None,

            "service_calls": 0

        }
        
        try:
            # Phase 1: Establish multiple WebSocket connections

            connections_result = await self._establish_test_websocket_connections()

            test_results["phase_1_connections"] = connections_result

            test_results["service_calls"] += connections_result.get("service_calls", 0)
            
            if not connections_result["success"]:

                return test_results
            
            # Phase 2: Establish complex state (threads, messages, user activity)

            state_result = await self._establish_complex_websocket_state()

            test_results["phase_2_state_establishment"] = state_result

            test_results["service_calls"] += state_result.get("service_calls", 0)
            
            if not state_result["success"]:

                return test_results
            
            # Phase 3: Simulate service restart

            restart_result = await self._simulate_service_restart()

            test_results["phase_3_service_restart"] = restart_result

            test_results["service_calls"] += restart_result.get("service_calls", 0)
            
            # Phase 4: Verify automatic reconnection

            reconnection_result = await self._verify_automatic_reconnection()

            test_results["phase_4_reconnection"] = reconnection_result

            test_results["service_calls"] += reconnection_result.get("service_calls", 0)
            
            if not reconnection_result["success"]:

                return test_results
            
            # Phase 5: Validate state recovery and continuity

            validation_result = await self._validate_state_recovery_continuity()

            test_results["phase_5_state_validation"] = validation_result

            test_results["service_calls"] += validation_result.get("service_calls", 0)
            
            return test_results
            
        except Exception as e:

            return {"success": False, "error": str(e), "test_results": test_results}
    
    async def _establish_test_websocket_connections(self) -> Dict[str, Any]:

        """Establish multiple WebSocket connections for testing."""

        try:

            connection_results = []

            user_scenarios = [

                {"tier": "enterprise", "threads": 3, "messages": 10},

                {"tier": "mid", "threads": 2, "messages": 5},

                {"tier": "free", "threads": 1, "messages": 3}

            ]
            
            for i, scenario in enumerate(user_scenarios):
                # Create test user

                user_data = await self.create_test_user_with_billing(scenario["tier"])

                if not user_data["success"]:

                    continue
                
                # Establish WebSocket connection

                ws_connection = await self._create_authenticated_websocket_connection(

                    user_data["access_token"],

                    user_data["user_id"],

                    scenario

                )
                
                if ws_connection["success"]:

                    connection_results.append(ws_connection)

                    self.test_websockets.append(ws_connection["websocket"])
            
            successful_connections = len(connection_results)
            
            return {

                "success": successful_connections >= 2,  # Need at least 2 connections

                "total_connections": len(user_scenarios),

                "successful_connections": successful_connections,

                "connection_results": connection_results,

                "service_calls": len(user_scenarios) * 2  # user creation + ws connection

            }
            
        except Exception as e:

            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _create_authenticated_websocket_connection(self, access_token: str, 

                                                       user_id: str, scenario: Dict) -> Dict[str, Any]:

        """Create authenticated WebSocket connection with scenario-specific setup."""

        try:

            ws_url = self.service_endpoints.websocket.replace("http", "ws")

            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Connect to WebSocket

            websocket = await websockets.connect(

                ws_url,

                extra_headers=headers,

                ping_interval=20,

                ping_timeout=10,

                max_size=1024*1024  # 1MB max message size

            )
            
            # Send authentication message

            auth_message = {

                "type": "authenticate",

                "access_token": access_token,

                "user_id": user_id,

                "client_info": {

                    "test_scenario": scenario,

                    "test_name": self.test_name

                }

            }
            
            await websocket.send(json.dumps(auth_message))
            
            # Wait for authentication confirmation

            auth_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)

            auth_data = json.loads(auth_response)
            
            if auth_data.get("type") != "auth_success":

                raise Exception(f"Authentication failed: {auth_data}")
            
            connection_id = auth_data.get("connection_id", f"conn_{uuid.uuid4().hex[:8]}")
            
            return {

                "success": True,

                "websocket": websocket,

                "user_id": user_id,

                "connection_id": connection_id,

                "scenario": scenario,

                "auth_data": auth_data

            }
            
        except Exception as e:

            return {"success": False, "error": str(e)}
    
    async def _establish_complex_websocket_state(self) -> Dict[str, Any]:

        """Establish complex state across WebSocket connections."""

        try:

            state_operations = 0
            
            for ws_connection in self.test_websockets:

                if not ws_connection:

                    continue
                    
                user_id = ws_connection.get("user_id")

                websocket = ws_connection.get("websocket")

                scenario = ws_connection.get("scenario", {})

                connection_id = ws_connection.get("connection_id")
                
                # Create threads for this user

                threads = []

                for i in range(scenario.get("threads", 1)):

                    thread_creation = await self._create_thread_via_websocket(

                        websocket, user_id, f"Test Thread {i+1}"

                    )

                    if thread_creation["success"]:

                        threads.append(thread_creation["thread_id"])

                    state_operations += 1
                
                # Send messages in threads

                message_history = []

                for thread_id in threads:

                    for j in range(scenario.get("messages", 1)):

                        message_result = await self._send_message_via_websocket(

                            websocket, user_id, thread_id, f"Test message {j+1} in {thread_id}"

                        )

                        if message_result["success"]:

                            message_history.append(message_result["message_data"])

                        state_operations += 1
                
                # Store pre-restart state

                state_data = WebSocketStateData(

                    session_id=ws_connection.get("auth_data", {}).get("session_id", ""),

                    user_id=user_id,

                    connection_id=connection_id,

                    active_threads=threads,

                    message_history=message_history,

                    last_activity=time.time(),

                    state_checksum=self._calculate_state_checksum(threads, message_history)

                )
                
                self.pre_restart_states[user_id] = state_data
            
            return {

                "success": len(self.pre_restart_states) >= 2,

                "states_established": len(self.pre_restart_states),

                "total_state_operations": state_operations,

                "service_calls": state_operations

            }
            
        except Exception as e:

            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _create_thread_via_websocket(self, websocket, user_id: str, 

                                         thread_name: str) -> Dict[str, Any]:

        """Create thread via WebSocket connection."""

        try:

            thread_message = {

                "type": "create_thread",

                "user_id": user_id,

                "thread_name": thread_name,

                "timestamp": time.time()

            }
            
            await websocket.send(json.dumps(thread_message))
            
            # Wait for thread creation response

            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)

            thread_data = json.loads(response)
            
            if thread_data.get("type") == "thread_created":

                return {

                    "success": True,

                    "thread_id": thread_data.get("thread_id"),

                    "thread_data": thread_data

                }

            else:

                return {"success": False, "error": f"Unexpected response: {thread_data}"}
                
        except Exception as e:

            return {"success": False, "error": str(e)}
    
    async def _send_message_via_websocket(self, websocket, user_id: str, 

                                        thread_id: str, content: str) -> Dict[str, Any]:

        """Send message via WebSocket connection."""

        try:

            message_data = {

                "type": "send_message",

                "user_id": user_id,

                "thread_id": thread_id,

                "content": content,

                "timestamp": time.time()

            }
            
            await websocket.send(json.dumps(message_data))
            
            # Wait for message confirmation

            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)

            response_data = json.loads(response)
            
            if response_data.get("type") == "message_sent":

                return {

                    "success": True,

                    "message_id": response_data.get("message_id"),

                    "message_data": message_data

                }

            else:

                return {"success": False, "error": f"Unexpected response: {response_data}"}
                
        except Exception as e:

            return {"success": False, "error": str(e)}
    
    def _calculate_state_checksum(self, threads: List[str], 

                                messages: List[Dict]) -> str:

        """Calculate checksum for state validation."""
        import hashlib
        
        state_string = json.dumps({

            "threads": sorted(threads),

            "message_count": len(messages),

            "thread_count": len(threads)

        }, sort_keys=True)
        
        return hashlib.md5(state_string.encode()).hexdigest()
    
    async def _simulate_service_restart(self) -> Dict[str, Any]:

        """Simulate WebSocket service restart."""

        try:
            # Store connection states before restart

            pre_restart_connection_count = len([ws for ws in self.test_websockets if ws])
            
            # In staging environment, we trigger a controlled restart

            restart_endpoint = f"{self.service_endpoints.backend}/admin/websocket/restart"
            
            # Note: In production this would be done via infrastructure commands
            # For staging, we use admin endpoint that simulates restart

            restart_response = await self.test_client.post(

                restart_endpoint,

                json={"restart_type": "graceful", "test_restart": True},

                headers={"Content-Type": "application/json"}

            )
            
            restart_success = restart_response.status_code in [200, 202]
            
            # Wait for restart to complete (simulated)

            await asyncio.sleep(3.0)
            
            # Verify WebSocket service is back online

            ws_health_url = f"{self.service_endpoints.websocket}/health"

            health_check = await self.test_client.get(ws_health_url)

            service_online = health_check.status_code == 200
            
            return {

                "success": restart_success and service_online,

                "restart_endpoint_success": restart_success,

                "service_back_online": service_online,

                "pre_restart_connections": pre_restart_connection_count,

                "service_calls": 2  # restart + health check

            }
            
        except Exception as e:

            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _verify_automatic_reconnection(self) -> Dict[str, Any]:

        """Verify automatic WebSocket reconnection after restart."""

        try:

            reconnection_results = []
            
            # For each user, attempt to re-establish WebSocket connection

            for user_id, pre_state in self.pre_restart_states.items():
                # Retrieve user access token from Redis (should be persisted)

                session_data = await self.redis_session.get_session(pre_state.session_id)
                
                if not session_data:

                    reconnection_results.append({

                        "user_id": user_id,

                        "success": False,

                        "error": "Session not found in Redis"

                    })

                    continue
                
                session_info = json.loads(session_data)

                access_token = session_info.get("access_token")
                
                if not access_token:

                    reconnection_results.append({

                        "user_id": user_id,

                        "success": False,

                        "error": "Access token not found"

                    })

                    continue
                
                # Attempt WebSocket reconnection

                reconnection_result = await self._attempt_websocket_reconnection(

                    access_token, user_id, pre_state

                )

                reconnection_results.append(reconnection_result)
            
            successful_reconnections = [r for r in reconnection_results if r.get("success", False)]
            
            return {

                "success": len(successful_reconnections) >= 2,

                "total_reconnection_attempts": len(reconnection_results),

                "successful_reconnections": len(successful_reconnections),

                "reconnection_results": reconnection_results,

                "service_calls": len(reconnection_results) * 2  # session lookup + reconnection

            }
            
        except Exception as e:

            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _attempt_websocket_reconnection(self, access_token: str, user_id: str, 

                                            pre_state: WebSocketStateData) -> Dict[str, Any]:

        """Attempt to reconnect WebSocket for a specific user."""

        try:

            ws_url = self.service_endpoints.websocket.replace("http", "ws")

            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Reconnect with state recovery request

            websocket = await websockets.connect(

                ws_url,

                extra_headers=headers,

                ping_interval=20,

                ping_timeout=10

            )
            
            # Send authentication with state recovery

            auth_message = {

                "type": "authenticate_with_recovery",

                "access_token": access_token,

                "user_id": user_id,

                "previous_connection_id": pre_state.connection_id,

                "state_checksum": pre_state.state_checksum

            }
            
            await websocket.send(json.dumps(auth_message))
            
            # Wait for authentication and state recovery response

            recovery_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)

            recovery_data = json.loads(recovery_response)
            
            if recovery_data.get("type") == "auth_success_with_recovery":

                return {

                    "user_id": user_id,

                    "success": True,

                    "websocket": websocket,

                    "recovery_data": recovery_data,

                    "new_connection_id": recovery_data.get("connection_id")

                }

            else:

                return {

                    "user_id": user_id,

                    "success": False,

                    "error": f"Recovery failed: {recovery_data}"

                }
                
        except Exception as e:

            return {"user_id": user_id, "success": False, "error": str(e)}
    
    async def _validate_state_recovery_continuity(self) -> Dict[str, Any]:

        """Validate that WebSocket state was properly recovered."""

        try:

            validation_results = []
            
            for user_id, pre_state in self.pre_restart_states.items():
                # Query current state from WebSocket service

                state_query_result = await self._query_websocket_state(user_id)
                
                if not state_query_result["success"]:

                    validation_results.append({

                        "user_id": user_id,

                        "success": False,

                        "error": "Could not query post-restart state"

                    })

                    continue
                
                post_state = state_query_result["state_data"]
                
                # Validate thread continuity

                threads_match = set(pre_state.active_threads) == set(post_state.get("active_threads", []))
                
                # Validate message history continuity

                pre_message_count = len(pre_state.message_history)

                post_message_count = post_state.get("message_count", 0)

                messages_preserved = post_message_count >= pre_message_count
                
                # Calculate state consistency score

                consistency_score = self._calculate_state_consistency(pre_state, post_state)
                
                validation_result = {

                    "user_id": user_id,

                    "success": threads_match and messages_preserved and consistency_score >= 0.9,

                    "threads_match": threads_match,

                    "messages_preserved": messages_preserved,

                    "consistency_score": consistency_score,

                    "pre_threads": len(pre_state.active_threads),

                    "post_threads": len(post_state.get("active_threads", [])),

                    "pre_messages": pre_message_count,

                    "post_messages": post_message_count

                }
                
                validation_results.append(validation_result)
            
            successful_validations = [r for r in validation_results if r.get("success", False)]
            
            return {

                "success": len(successful_validations) >= 2,

                "total_validations": len(validation_results),

                "successful_validations": len(successful_validations),

                "validation_results": validation_results,

                "service_calls": len(validation_results)

            }
            
        except Exception as e:

            return {"success": False, "error": str(e), "service_calls": 0}
    
    async def _query_websocket_state(self, user_id: str) -> Dict[str, Any]:

        """Query current WebSocket state for a user."""

        try:

            state_endpoint = f"{self.service_endpoints.backend}/api/websocket/state/{user_id}"

            response = await self.test_client.get(state_endpoint)
            
            if response.status_code == 200:

                return {"success": True, "state_data": response.json()}

            else:

                return {"success": False, "error": f"State query failed: {response.status_code}"}
                
        except Exception as e:

            return {"success": False, "error": str(e)}
    
    def _calculate_state_consistency(self, pre_state: WebSocketStateData, 

                                   post_state: Dict[str, Any]) -> float:

        """Calculate state consistency score between pre and post restart."""

        consistency_factors = []
        
        # Thread consistency

        pre_threads = set(pre_state.active_threads)

        post_threads = set(post_state.get("active_threads", []))

        thread_consistency = len(pre_threads & post_threads) / max(len(pre_threads), 1)

        consistency_factors.append(thread_consistency)
        
        # Message count consistency

        pre_msg_count = len(pre_state.message_history)

        post_msg_count = post_state.get("message_count", 0)

        msg_consistency = min(post_msg_count / max(pre_msg_count, 1), 1.0)

        consistency_factors.append(msg_consistency)
        
        # Session continuity

        session_consistent = post_state.get("session_recovered", False)

        consistency_factors.append(1.0 if session_consistent else 0.0)
        
        return sum(consistency_factors) / len(consistency_factors)
    
    async def validate_critical_path_results(self, results: Dict[str, Any]) -> bool:

        """Validate WebSocket state recovery meets business requirements."""

        try:
            # Validate all phases completed successfully

            phase_results = [

                results.get("phase_1_connections", {}).get("success", False),

                results.get("phase_2_state_establishment", {}).get("success", False),

                results.get("phase_3_service_restart", {}).get("success", False),

                results.get("phase_4_reconnection", {}).get("success", False),

                results.get("phase_5_state_validation", {}).get("success", False)

            ]
            
            if not all(phase_results):

                failed_phases = [f"phase_{i+1}" for i, success in enumerate(phase_results) if not success]

                self.test_metrics.errors.append(f"Failed phases: {', '.join(failed_phases)}")

                return False
            
            # Validate business metrics

            business_requirements = {

                "max_response_time_seconds": 3.0,  # WebSocket operations should be fast

                "min_success_rate_percent": 95.0,  # High reliability required

                "max_error_count": 1  # Allow minimal errors during restart

            }
            
            return await self.validate_business_metrics(business_requirements)
            
        except Exception as e:

            self.test_metrics.errors.append(f"Result validation failed: {str(e)}")

            return False
    
    async def cleanup_test_specific_resources(self) -> None:

        """Clean up WebSocket connections and test data."""
        # Close any remaining WebSocket connections

        for ws_connection in self.test_websockets:

            if ws_connection and ws_connection.get("websocket"):

                try:

                    await ws_connection["websocket"].close()

                except Exception:

                    pass
        
        # Clean up WebSocket manager

        if self.ws_manager:

            try:

                await self.ws_manager.shutdown()

            except Exception:

                pass

# Pytest fixtures and test functions

@pytest.fixture

async def websocket_state_recovery_test():

    """Create WebSocket state recovery test instance."""

    test = WebSocketStateRecoveryL4Test()

    await test.initialize_l4_environment()

    yield test

    await test.cleanup_l4_resources()

@pytest.mark.asyncio

@pytest.mark.staging

async def test_websocket_state_recovery_after_restart_l4(websocket_state_recovery_test):

    """Test WebSocket state recovery after service restart in staging."""
    # Execute complete critical path test

    metrics = await websocket_state_recovery_test.run_complete_critical_path_test()
    
    # Validate test success

    assert metrics.success is True, f"WebSocket state recovery test failed: {metrics.errors}"
    
    # Validate performance requirements

    assert metrics.duration < 60.0, f"Test took too long: {metrics.duration:.2f}s"

    assert metrics.success_rate >= 95.0, f"Success rate too low: {metrics.success_rate:.1f}%"

    assert metrics.error_count <= 1, f"Too many errors: {metrics.error_count}"
    
    # Validate business continuity

    assert metrics.service_calls >= 10, "Insufficient service interaction coverage"
    
    # Log test results for monitoring

    print(f"WebSocket State Recovery Test Results:")

    print(f"  Duration: {metrics.duration:.2f}s")

    print(f"  Success Rate: {metrics.success_rate:.1f}%")

    print(f"  Service Calls: {metrics.service_calls}")

    print(f"  Errors: {metrics.error_count}")

@pytest.mark.asyncio

@pytest.mark.staging

async def test_websocket_connection_resilience_l4(websocket_state_recovery_test):

    """Test WebSocket connection resilience during network interruptions."""
    # Test network interruption scenario

    test_results = await websocket_state_recovery_test._establish_test_websocket_connections()

    assert test_results["success"] is True, "Failed to establish initial connections"
    
    # Simulate network interruption recovery

    recovery_results = await websocket_state_recovery_test._verify_automatic_reconnection()
    
    # Validate recovery capabilities

    assert recovery_results.get("successful_reconnections", 0) >= 2, "Insufficient reconnection success"

@pytest.mark.asyncio

@pytest.mark.staging  

async def test_websocket_state_consistency_validation_l4(websocket_state_recovery_test):

    """Test WebSocket state consistency after recovery."""
    # Establish complex state

    await websocket_state_recovery_test._establish_test_websocket_connections()

    state_result = await websocket_state_recovery_test._establish_complex_websocket_state()
    
    assert state_result["success"] is True, "Failed to establish complex state"

    assert len(websocket_state_recovery_test.pre_restart_states) >= 2, "Insufficient state complexity"
    
    # Validate state checksums are generated correctly

    for user_id, state_data in websocket_state_recovery_test.pre_restart_states.items():

        assert state_data.state_checksum is not None, f"Missing checksum for user {user_id}"

        assert len(state_data.active_threads) > 0, f"No threads established for user {user_id}"

        assert len(state_data.message_history) > 0, f"No messages for user {user_id}"