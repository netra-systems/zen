"""
Test Multi-User Concurrent Sessions E2E

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure system handles concurrent users with proper isolation
- Value Impact: Multiple users can use the platform simultaneously without interference
- Strategic Impact: Platform scalability and multi-tenancy core requirement

CRITICAL AUTHENTICATION REQUIREMENT:
ALL tests MUST use authentication to validate real multi-user scenarios.
Each user gets their own isolated execution context and data boundaries.

CRITICAL MULTI-USER REQUIREMENTS:
- User Isolation: Each user's data and execution context must remain separate
- Concurrent Execution: Multiple users running agents simultaneously
- Resource Management: Shared resources (connection pools, Redis, DB) handled correctly
- WebSocket Separation: Each user gets their own WebSocket connection with proper auth
- Data Segregation: User A cannot access User B's threads, messages, or results
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple
import websockets

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user
from tests.e2e.staging_config import get_staging_config


class TestMultiUserConcurrentSessions(BaseE2ETest):
    """Test multi-user scenarios with proper isolation and concurrent execution."""
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.staging_config = get_staging_config()
        self.auth_helper = E2EAuthHelper(environment="staging")
        
    async def create_test_users(self, count: int) -> List[Tuple[str, Dict]]:
        """Create multiple authenticated test users."""
        users = []
        for i in range(count):
            token, user_data = await create_authenticated_user(
                environment="staging",
                email=f"multi-user-test-{i}-{uuid.uuid4().hex[:8]}@staging.netrasystems.ai",
                permissions=["read", "write", "agent_execute"]
            )
            users.append((token, user_data))
        return users
        
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.staging
    async def test_concurrent_users_different_agents(self, real_services, real_llm):
        """Test multiple users running different agents concurrently."""
        self.logger.info("[U+1F680] Starting Concurrent Users Different Agents E2E Test")
        
        # Create 3 different users
        users = await self.create_test_users(3)
        
        # Define different agent requests for each user
        agent_requests = [
            {
                "agent": "cost_optimizer",
                "message": "Analyze AWS costs for optimization opportunities",
                "context": {"cloud_provider": "aws", "monthly_spend": 25000}
            },
            {
                "agent": "data_analysis", 
                "message": "Analyze Q3 performance metrics for trends",
                "context": {"quarter": "Q3", "analysis_type": "performance"}
            },
            {
                "agent": "business_advisor",
                "message": "Recommend growth strategies for scaling operations",
                "context": {"business_stage": "growth", "focus": "operations"}
            }
        ]
        
        async def run_user_session(user_idx: int, token: str, user_data: Dict, request_config: Dict):
            """Run a single user session."""
            session_id = f"user-{user_idx}-{uuid.uuid4().hex[:6]}"
            self.logger.info(f" CYCLE:  Starting session {session_id} for {user_data['email']}")
            
            try:
                # Connect WebSocket with user authentication
                websocket_headers = self.auth_helper.get_websocket_headers(token)
                websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.staging_config.urls.websocket_url,
                        additional_headers=websocket_headers,
                        open_timeout=20.0
                    ),
                    timeout=25.0
                )
                
                # Send user-specific agent request
                agent_request = {
                    "type": "agent_request",
                    "agent": request_config["agent"],
                    "message": request_config["message"],
                    "context": {
                        **request_config["context"],
                        "user_id": user_data["id"],
                        "session_id": session_id
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Collect events for this user
                events = []
                start_time = time.time()
                
                while time.time() - start_time < 120:  # 2 minute timeout per user
                    try:
                        event_str = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                        event = json.loads(event_str)
                        events.append(event)
                        
                        if event["type"] == "agent_completed":
                            break
                    except asyncio.TimeoutError:
                        break
                
                await websocket.close()
                
                # Validate user-specific results
                event_types = [e["type"] for e in events]
                required_events = ["agent_started", "agent_thinking", "agent_completed"]
                
                for event_type in required_events:
                    assert event_type in event_types, f"User {user_idx} missing {event_type}"
                
                # Extract final result
                final_event = next(e for e in reversed(events) if e["type"] == "agent_completed")
                result = final_event["data"]["result"]
                
                self.logger.info(f" PASS:  Session {session_id} completed successfully")
                
                return {
                    "user_idx": user_idx,
                    "user_id": user_data["id"], 
                    "agent": request_config["agent"],
                    "events": events,
                    "result": result,
                    "thread_id": final_event["data"].get("thread_id"),
                    "execution_time": time.time() - start_time
                }
                
            except Exception as e:
                self.logger.error(f" FAIL:  Session {session_id} failed: {e}")
                raise
        
        # Run all user sessions concurrently
        tasks = []
        for i, ((token, user_data), request_config) in enumerate(zip(users, agent_requests)):
            task = run_user_session(i, token, user_data, request_config)
            tasks.append(task)
        
        # Wait for all sessions to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate concurrent execution results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == 3, f"Expected 3 successful sessions, got {len(successful_results)}"
        
        # Validate user isolation - each user should have different results
        user_ids = [r["user_id"] for r in successful_results]
        assert len(set(user_ids)) == 3, "Users should have different IDs"
        
        thread_ids = [r["thread_id"] for r in successful_results]
        assert len(set(thread_ids)) == 3, "Users should have different thread IDs"
        
        agents_used = [r["agent"] for r in successful_results] 
        assert len(set(agents_used)) == 3, "Users should have used different agents"
        
        self.logger.info(" PASS:  Concurrent Users Different Agents E2E Test completed")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.staging
    async def test_concurrent_users_same_agent(self, real_services, real_llm):
        """Test multiple users using the same agent type concurrently."""
        self.logger.info("[U+1F680] Starting Concurrent Users Same Agent E2E Test")
        
        # Create 3 users
        users = await self.create_test_users(3)
        
        async def run_cost_optimizer_session(user_idx: int, token: str, user_data: Dict):
            """Run cost optimizer for a specific user."""
            try:
                websocket_headers = self.auth_helper.get_websocket_headers(token)
                websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.staging_config.urls.websocket_url,
                        additional_headers=websocket_headers
                    ),
                    timeout=25.0
                )
                
                # Each user has different cost optimization context
                contexts = [
                    {"provider": "aws", "monthly_spend": 50000, "focus": "compute"},
                    {"provider": "azure", "monthly_spend": 75000, "focus": "storage"},
                    {"provider": "gcp", "monthly_spend": 30000, "focus": "networking"}
                ]
                
                agent_request = {
                    "type": "agent_request",
                    "agent": "cost_optimizer",
                    "message": f"Optimize {contexts[user_idx]['provider']} costs focusing on {contexts[user_idx]['focus']}",
                    "context": {
                        **contexts[user_idx],
                        "user_id": user_data["id"],
                        "request_id": f"cost-opt-{user_idx}-{uuid.uuid4().hex[:6]}"
                    }
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Collect events
                events = []
                start_time = time.time()
                
                while time.time() - start_time < 90:
                    try:
                        event_str = await asyncio.wait_for(websocket.recv(), timeout=25.0)
                        event = json.loads(event_str)
                        events.append(event)
                        
                        if event["type"] == "agent_completed":
                            break
                    except asyncio.TimeoutError:
                        break
                
                await websocket.close()
                
                # Validate results
                event_types = [e["type"] for e in events]
                assert "agent_completed" in event_types, f"User {user_idx} agent did not complete"
                
                final_event = next(e for e in reversed(events) if e["type"] == "agent_completed")
                result = final_event["data"]["result"]
                
                return {
                    "user_idx": user_idx,
                    "user_id": user_data["id"],
                    "result": result,
                    "thread_id": final_event["data"].get("thread_id"),
                    "provider": contexts[user_idx]["provider"]
                }
                
            except Exception as e:
                self.logger.error(f" FAIL:  Cost optimizer session for user {user_idx} failed: {e}")
                raise
        
        # Run concurrent sessions
        tasks = [run_cost_optimizer_session(i, token, user_data) for i, (token, user_data) in enumerate(users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == 3, "All cost optimizer sessions should succeed"
        
        # Validate isolation - same agent, different results per user
        user_ids = [r["user_id"] for r in successful_results]
        assert len(set(user_ids)) == 3, "Each user should maintain separate identity"
        
        providers = [r["provider"] for r in successful_results]
        assert len(set(providers)) == 3, "Each user should have different provider context"
        
        self.logger.info(" PASS:  Concurrent Users Same Agent E2E Test completed")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.staging
    async def test_user_isolation_boundary_enforcement(self, real_services, real_llm):
        """Test that users cannot access each other's data or sessions."""
        self.logger.info("[U+1F680] Starting User Isolation Boundary Enforcement E2E Test")
        
        # Create 2 users
        users = await self.create_test_users(2)
        (token_a, user_a), (token_b, user_b) = users
        
        # User A starts a session and creates some data
        websocket_headers_a = self.auth_helper.get_websocket_headers(token_a)
        websocket_a = await websockets.connect(
            self.staging_config.urls.websocket_url,
            additional_headers=websocket_headers_a
        )
        
        agent_request_a = {
            "type": "agent_request",
            "agent": "cost_optimizer",
            "message": "Confidential analysis of internal cost structure",
            "context": {
                "user_id": user_a["id"],
                "confidential": True,
                "internal_data": "sensitive_cost_breakdown"
            }
        }
        
        await websocket_a.send(json.dumps(agent_request_a))
        
        # Wait for User A to complete
        events_a = []
        start_time = time.time()
        thread_id_a = None
        
        while time.time() - start_time < 60:
            try:
                event_str = await asyncio.wait_for(websocket_a.recv(), timeout=15.0)
                event = json.loads(event_str)
                events_a.append(event)
                
                if event["type"] == "agent_completed":
                    thread_id_a = event["data"].get("thread_id")
                    break
            except asyncio.TimeoutError:
                break
        
        await websocket_a.close()
        
        assert thread_id_a is not None, "User A should have created a thread"
        
        # User B tries to access User A's session/data (should fail)
        websocket_headers_b = self.auth_helper.get_websocket_headers(token_b)
        websocket_b = await websockets.connect(
            self.staging_config.urls.websocket_url,
            additional_headers=websocket_headers_b
        )
        
        # Attempt to access User A's thread (should be blocked)
        unauthorized_request = {
            "type": "get_thread", 
            "thread_id": thread_id_a,  # User B trying to access User A's thread
            "user_id": user_b["id"]    # User B's ID
        }
        
        await websocket_b.send(json.dumps(unauthorized_request))
        
        # Check response - should be access denied or no data
        try:
            response_str = await asyncio.wait_for(websocket_b.recv(), timeout=10.0)
            response = json.loads(response_str)
            
            # Should either get access denied or empty/no data
            if "error" in response:
                assert "access" in response["error"].lower() or "unauthorized" in response["error"].lower()
            elif "data" in response:
                assert response["data"] is None or len(response.get("data", [])) == 0
                
        except asyncio.TimeoutError:
            # No response is also acceptable (request ignored)
            pass
        
        await websocket_b.close()
        
        # User B creates their own session (should work fine)
        websocket_b2 = await websockets.connect(
            self.staging_config.urls.websocket_url,
            additional_headers=websocket_headers_b
        )
        
        agent_request_b = {
            "type": "agent_request",
            "agent": "cost_optimizer",
            "message": "My own cost analysis",
            "context": {
                "user_id": user_b["id"],
                "request_type": "standard_analysis"
            }
        }
        
        await websocket_b2.send(json.dumps(agent_request_b))
        
        # User B should successfully get their own results
        events_b = []
        start_time = time.time()
        
        while time.time() - start_time < 60:
            try:
                event_str = await asyncio.wait_for(websocket_b2.recv(), timeout=15.0)
                event = json.loads(event_str)
                events_b.append(event)
                
                if event["type"] == "agent_completed":
                    break
            except asyncio.TimeoutError:
                break
        
        await websocket_b2.close()
        
        # Validate User B got their own results
        event_types_b = [e["type"] for e in events_b]
        assert "agent_completed" in event_types_b, "User B should be able to run their own agents"
        
        final_event_b = next(e for e in reversed(events_b) if e["type"] == "agent_completed")
        thread_id_b = final_event_b["data"].get("thread_id")
        
        # Validate isolation - different thread IDs
        assert thread_id_a != thread_id_b, "Users should have separate threads"
        
        self.logger.info(" PASS:  User Isolation Boundary Enforcement E2E Test completed")
    
    @pytest.mark.e2e
    @pytest.mark.real_services  
    @pytest.mark.staging
    async def test_shared_resource_handling(self, real_services):
        """Test how shared resources (DB connections, Redis) handle concurrent users."""
        self.logger.info("[U+1F680] Starting Shared Resource Handling E2E Test")
        
        # Create 4 users to stress shared resources
        users = await self.create_test_users(4)
        
        async def create_user_load(user_idx: int, token: str, user_data: Dict):
            """Create sustained load from a single user."""
            websocket_headers = self.auth_helper.get_websocket_headers(token)
            
            try:
                websocket = await websockets.connect(
                    self.staging_config.urls.websocket_url,
                    additional_headers=websocket_headers
                )
                
                # Send multiple requests to stress shared resources
                for request_num in range(3):
                    agent_request = {
                        "type": "agent_request",
                        "agent": "triage_agent",  # Lightweight agent
                        "message": f"Quick analysis request {request_num + 1}",
                        "context": {
                            "user_id": user_data["id"],
                            "request_num": request_num,
                            "stress_test": True
                        }
                    }
                    
                    await websocket.send(json.dumps(agent_request))
                    
                    # Wait for completion before next request
                    start_time = time.time()
                    while time.time() - start_time < 30:
                        try:
                            event_str = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                            event = json.loads(event_str)
                            
                            if event["type"] == "agent_completed":
                                break
                        except asyncio.TimeoutError:
                            break
                    
                    # Small delay between requests
                    await asyncio.sleep(1)
                
                await websocket.close()
                return {"user_idx": user_idx, "status": "success"}
                
            except Exception as e:
                self.logger.error(f" FAIL:  User {user_idx} load test failed: {e}")
                return {"user_idx": user_idx, "status": "error", "error": str(e)}
        
        # Run concurrent load from all users
        tasks = [create_user_load(i, token, user_data) for i, (token, user_data) in enumerate(users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate shared resource handling
        successful_users = sum(1 for r in results if not isinstance(r, Exception) and r.get("status") == "success")
        
        # At least 3 out of 4 users should succeed (allows for some resource contention)
        assert successful_users >= 3, f"Shared resource handling failed - only {successful_users}/4 users succeeded"
        
        self.logger.info(f" PASS:  Shared Resource Handling Test - {successful_users}/4 users successful")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.staging
    async def test_websocket_connection_management(self, real_services):
        """Test WebSocket connection management with multiple concurrent users."""
        self.logger.info("[U+1F680] Starting WebSocket Connection Management E2E Test")
        
        # Create 5 users for WebSocket stress testing
        users = await self.create_test_users(5)
        
        async def test_websocket_lifecycle(user_idx: int, token: str, user_data: Dict):
            """Test WebSocket connection lifecycle for a user."""
            websocket_headers = self.auth_helper.get_websocket_headers(token)
            connections = []
            
            try:
                # Test multiple connections per user (simulating page refresh, etc.)
                for conn_num in range(2):
                    websocket = await websockets.connect(
                        self.staging_config.urls.websocket_url,
                        additional_headers=websocket_headers,
                        open_timeout=15.0
                    )
                    connections.append(websocket)
                    
                    # Send a simple message to verify connection works
                    test_message = {
                        "type": "ping",
                        "user_id": user_data["id"],
                        "connection": conn_num,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    
                    # Try to receive response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        # Any response indicates connection is working
                    except asyncio.TimeoutError:
                        # No response is acceptable for ping
                        pass
                
                # Close all connections
                for websocket in connections:
                    await websocket.close()
                
                return {"user_idx": user_idx, "connections": len(connections), "status": "success"}
                
            except Exception as e:
                # Clean up any remaining connections
                for websocket in connections:
                    try:
                        await websocket.close()
                    except:
                        pass
                        
                return {"user_idx": user_idx, "status": "error", "error": str(e)}
        
        # Run WebSocket tests for all users concurrently
        tasks = [test_websocket_lifecycle(i, token, user_data) for i, (token, user_data) in enumerate(users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate WebSocket connection management
        successful_connections = []
        for result in results:
            if not isinstance(result, Exception) and result.get("status") == "success":
                successful_connections.append(result)
        
        assert len(successful_connections) >= 4, f"WebSocket management failed - only {len(successful_connections)}/5 users succeeded"
        
        total_connections = sum(r.get("connections", 0) for r in successful_connections)
        assert total_connections >= 8, "Should handle multiple connections per user"
        
        self.logger.info(f" PASS:  WebSocket Connection Management - {len(successful_connections)}/5 users, {total_connections} total connections")
    
    @pytest.mark.e2e 
    @pytest.mark.real_services
    @pytest.mark.staging
    async def test_user_session_lifecycle(self, real_services):
        """Test complete user session lifecycle with authentication."""
        self.logger.info("[U+1F680] Starting User Session Lifecycle E2E Test")
        
        # Create a user for session testing
        token, user_data = await create_authenticated_user(
            environment="staging",
            email=f"session-lifecycle-{uuid.uuid4().hex[:8]}@staging.netrasystems.ai"
        )
        
        websocket_headers = self.auth_helper.get_websocket_headers(token)
        
        # Test session establishment
        websocket = await websockets.connect(
            self.staging_config.urls.websocket_url,
            additional_headers=websocket_headers
        )
        
        # Start session with initial request
        initial_request = {
            "type": "agent_request",
            "agent": "triage_agent",
            "message": "Start my session with a simple query",
            "context": {
                "user_id": user_data["id"],
                "session_phase": "initialization"
            }
        }
        
        await websocket.send(json.dumps(initial_request))
        
        # Wait for initial response
        initial_events = []
        start_time = time.time()
        
        while time.time() - start_time < 30:
            try:
                event_str = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                event = json.loads(event_str)
                initial_events.append(event)
                
                if event["type"] == "agent_completed":
                    break
            except asyncio.TimeoutError:
                break
        
        # Validate initial session
        initial_event_types = [e["type"] for e in initial_events]
        assert "agent_started" in initial_event_types, "Session should start successfully"
        assert "agent_completed" in initial_event_types, "Session should complete initial request"
        
        # Test session continuation
        followup_request = {
            "type": "agent_request", 
            "agent": "triage_agent",
            "message": "Continue with a follow-up question",
            "context": {
                "user_id": user_data["id"],
                "session_phase": "continuation"
            }
        }
        
        await websocket.send(json.dumps(followup_request))
        
        # Wait for followup response
        followup_events = []
        start_time = time.time()
        
        while time.time() - start_time < 30:
            try:
                event_str = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                event = json.loads(event_str)
                followup_events.append(event)
                
                if event["type"] == "agent_completed":
                    break
            except asyncio.TimeoutError:
                break
        
        # Test session termination
        await websocket.close()
        
        # Validate complete session lifecycle
        followup_event_types = [e["type"] for e in followup_events]
        assert "agent_started" in followup_event_types, "Session continuation should work"
        assert "agent_completed" in followup_event_types, "Session should handle followup"
        
        self.logger.info(" PASS:  User Session Lifecycle E2E Test completed")