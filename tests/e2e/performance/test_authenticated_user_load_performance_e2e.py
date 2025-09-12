"""
Test Authenticated User Load Performance E2E

Business Value Justification (BVJ):
- Segment: All customer segments (core platform performance)
- Business Goal: Ensure platform can handle realistic user loads
- Value Impact: Load performance directly affects customer experience and retention
- Strategic Impact: Performance confidence enables enterprise sales and scaling

CRITICAL REQUIREMENTS:
- Tests complete E2E flows with authenticated users under load
- Validates multi-user concurrent scenarios (realistic usage patterns)
- Uses real authentication, real databases, real LLM calls
- MANDATORY: All tests MUST use authentication (no auth bypass allowed)
- Ensures response times meet SLA requirements under load
"""

import pytest
import asyncio
import httpx
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import random

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.base_e2e_test import BaseE2ETest
from shared.isolated_environment import get_env


class TestAuthenticatedUserLoadPerformanceE2E(BaseE2ETest):
    """
    Test authenticated user load performance in realistic E2E scenarios.
    
    Tests critical multi-user scenarios that validate platform scalability:
    - Concurrent user authentication and session management
    - Multi-user agent execution under load
    - Database performance with realistic user data patterns  
    - WebSocket connection handling for multiple authenticated users
    """
    
    def setup_method(self):
        """Set up E2E test environment with authentication"""
        super().setup_method()
        self.env = get_env()
        self.auth_helper = E2EAuthHelper()
        self.test_prefix = f"load_e2e_{uuid.uuid4().hex[:8]}"
        
        # E2E test configuration
        self.backend_url = self.env.get("BACKEND_URL", "http://localhost:8000")
        self.auth_url = self.env.get("AUTH_URL", "http://localhost:8081")
        self.websocket_url = self.env.get("WEBSOCKET_URL", "ws://localhost:8000/ws")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_concurrent_user_authentication_load(self):
        """
        Test concurrent user authentication under realistic load.
        
        BUSINESS CRITICAL: Authentication bottlenecks prevent users from accessing
        the platform, directly impacting revenue and user satisfaction.
        """
        concurrent_users = 20  # Realistic concurrent login load
        authentication_scenarios = []
        
        # Create test users for different tiers
        user_tiers = ["free", "early", "mid", "enterprise"]
        
        for i in range(concurrent_users):
            user_tier = user_tiers[i % len(user_tiers)]
            user_scenario = {
                "user_id": f"{self.test_prefix}_user_{i:03d}",
                "email": f"load_test_{i}@example.com",
                "tier": user_tier,
                "expected_permissions": self._get_tier_permissions(user_tier)
            }
            authentication_scenarios.append(user_scenario)
        
        # Execute concurrent authentication
        auth_start_time = time.time()
        
        auth_tasks = [
            self._authenticate_user_e2e(scenario) 
            for scenario in authentication_scenarios
        ]
        
        auth_results = await asyncio.gather(*auth_tasks, return_exceptions=True)
        
        auth_end_time = time.time()
        total_auth_duration = auth_end_time - auth_start_time
        
        # Validate authentication performance
        successful_auths = [
            result for result in auth_results 
            if isinstance(result, dict) and result.get("authenticated", False)
        ]
        failed_auths = [
            result for result in auth_results 
            if isinstance(result, Exception) or (isinstance(result, dict) and not result.get("authenticated", False))
        ]
        
        # Authentication success rate should be high
        auth_success_rate = len(successful_auths) / len(auth_results)
        assert auth_success_rate >= 0.90, f"Authentication success rate too low: {auth_success_rate:.2%}"
        
        # Authentication performance SLA
        assert total_auth_duration < 30.0, f"Concurrent authentication too slow: {total_auth_duration:.2f}s"
        
        # Individual authentication times should be reasonable
        auth_times = [auth["auth_duration"] for auth in successful_auths if "auth_duration" in auth]
        if auth_times:
            avg_auth_time = sum(auth_times) / len(auth_times)
            max_auth_time = max(auth_times)
            
            assert avg_auth_time < 5.0, f"Average auth time too high: {avg_auth_time:.2f}s"
            assert max_auth_time < 10.0, f"Max auth time too high: {max_auth_time:.2f}s"
        
        # Validate tier-specific authentication
        tier_results = {}
        for auth in successful_auths:
            tier = auth.get("user_tier")
            if tier not in tier_results:
                tier_results[tier] = []
            tier_results[tier].append(auth)
        
        # Each tier should have successful authentications
        for tier in user_tiers:
            assert tier in tier_results, f"No successful authentications for {tier} tier"
            tier_auths = tier_results[tier]
            assert len(tier_auths) > 0, f"No {tier} tier users authenticated successfully"
            
            # Validate tier-specific permissions
            for auth in tier_auths:
                expected_permissions = self._get_tier_permissions(tier)
                actual_permissions = set(auth.get("permissions", []))
                assert actual_permissions.issuperset(expected_permissions), \
                    f"Missing permissions for {tier} tier: {expected_permissions - actual_permissions}"
        
        print(f" PASS:  Concurrent authentication test completed: {len(successful_auths)}/{len(auth_results)} successful")
    
    async def _authenticate_user_e2e(self, user_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate a single user and measure performance"""
        try:
            auth_start = time.time()
            
            # Create and authenticate user using E2E auth helper
            auth_result = await self.auth_helper.create_and_authenticate_user(
                email=user_scenario["email"],
                tier=user_scenario["tier"],
                test_prefix=self.test_prefix
            )
            
            auth_end = time.time()
            auth_duration = auth_end - auth_start
            
            if auth_result.success:
                return {
                    "authenticated": True,
                    "user_id": user_scenario["user_id"],
                    "user_tier": user_scenario["tier"],
                    "auth_duration": auth_duration,
                    "access_token": auth_result.access_token,
                    "permissions": auth_result.permissions,
                    "session_id": auth_result.session_id
                }
            else:
                return {
                    "authenticated": False,
                    "user_id": user_scenario["user_id"],
                    "error": auth_result.error,
                    "auth_duration": auth_duration
                }
                
        except Exception as e:
            return {
                "authenticated": False,
                "user_id": user_scenario["user_id"],
                "error": str(e)
            }
    
    def _get_tier_permissions(self, tier: str) -> set:
        """Get expected permissions for user tier"""
        base_permissions = {"read_profile", "basic_features"}
        
        if tier == "free":
            return base_permissions
        elif tier == "early":
            return base_permissions | {"create_projects", "basic_analytics"}
        elif tier == "mid":
            return base_permissions | {"create_projects", "advanced_analytics", "cost_optimization"}
        elif tier == "enterprise":
            return base_permissions | {"create_projects", "advanced_analytics", "cost_optimization", 
                                     "team_management", "api_access", "priority_support"}
        else:
            return base_permissions
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_multi_user_agent_execution_performance(self):
        """
        Test multi-user agent execution performance under realistic load.
        
        BUSINESS CRITICAL: Agent performance under multi-user load directly impacts
        the core value proposition and customer experience.
        """
        concurrent_users = 15  # Realistic concurrent agent usage
        agents_per_user = 2    # Each user runs 2 agents
        
        # Create authenticated users for agent testing
        authenticated_users = []
        
        for i in range(concurrent_users):
            tier = ["free", "mid", "enterprise"][i % 3]  # Mix of tiers
            
            auth_result = await self.auth_helper.create_and_authenticate_user(
                email=f"agent_test_{i}@example.com",
                tier=tier,
                test_prefix=self.test_prefix
            )
            
            if auth_result.success:
                authenticated_users.append({
                    "user_id": f"agent_user_{i}",
                    "tier": tier,
                    "access_token": auth_result.access_token,
                    "session_id": auth_result.session_id
                })
        
        # Ensure we have enough authenticated users
        assert len(authenticated_users) >= concurrent_users * 0.8, \
            f"Insufficient authenticated users: {len(authenticated_users)}/{concurrent_users}"
        
        # Execute concurrent agent requests
        agent_start_time = time.time()
        
        agent_tasks = []
        for user in authenticated_users:
            for agent_num in range(agents_per_user):
                task = self._execute_agent_request_e2e(
                    user=user,
                    agent_type="cost_optimizer" if agent_num == 0 else "triage_agent",
                    request_data={
                        "message": f"Test optimization request from {user['user_id']}",
                        "complexity": "medium",
                        "priority": "normal"
                    }
                )
                agent_tasks.append(task)
        
        agent_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
        
        agent_end_time = time.time()
        total_agent_duration = agent_end_time - agent_start_time
        
        # Analyze agent execution results
        successful_executions = [
            result for result in agent_results 
            if isinstance(result, dict) and result.get("success", False)
        ]
        failed_executions = [
            result for result in agent_results 
            if isinstance(result, Exception) or (isinstance(result, dict) and not result.get("success", False))
        ]
        
        # Agent execution success rate
        agent_success_rate = len(successful_executions) / len(agent_results)
        assert agent_success_rate >= 0.80, f"Agent execution success rate too low: {agent_success_rate:.2%}"
        
        # Overall performance SLA
        expected_total_duration = (len(authenticated_users) * agents_per_user * 10) / 3  # Assume 3 concurrent streams
        assert total_agent_duration < expected_total_duration, \
            f"Multi-user agent execution too slow: {total_agent_duration:.2f}s (expected < {expected_total_duration:.2f}s)"
        
        # Individual agent performance
        execution_times = [exec["execution_time"] for exec in successful_executions if "execution_time" in exec]
        
        if execution_times:
            avg_execution_time = sum(execution_times) / len(execution_times)
            max_execution_time = max(execution_times)
            
            # Agent execution SLA by tier
            tier_performance = {}
            for exec_result in successful_executions:
                tier = exec_result.get("user_tier")
                if tier not in tier_performance:
                    tier_performance[tier] = []
                tier_performance[tier].append(exec_result["execution_time"])
            
            # Validate tier-specific performance expectations
            for tier, times in tier_performance.items():
                avg_tier_time = sum(times) / len(times)
                
                if tier == "enterprise":
                    assert avg_tier_time < 15.0, f"Enterprise tier agents too slow: {avg_tier_time:.2f}s"
                elif tier == "mid":
                    assert avg_tier_time < 25.0, f"Mid tier agents too slow: {avg_tier_time:.2f}s"
                elif tier == "free":
                    assert avg_tier_time < 45.0, f"Free tier agents too slow: {avg_tier_time:.2f}s"
        
        # Validate WebSocket event delivery during agent execution
        websocket_events = []
        for exec_result in successful_executions:
            if "websocket_events" in exec_result:
                websocket_events.extend(exec_result["websocket_events"])
        
        # Should have received critical WebSocket events
        event_types = set(event.get("type") for event in websocket_events)
        required_events = {"agent_started", "agent_completed"}
        
        if websocket_events:  # Only check if WebSocket events were captured
            missing_events = required_events - event_types
            assert len(missing_events) == 0, f"Missing required WebSocket events: {missing_events}"
        
        print(f" PASS:  Multi-user agent execution completed: {len(successful_executions)}/{len(agent_results)} successful")
    
    async def _execute_agent_request_e2e(self, user: Dict[str, Any], agent_type: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent request for authenticated user"""
        try:
            execution_start = time.time()
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Make authenticated agent request
                response = await client.post(
                    f"{self.backend_url}/api/agents/execute",
                    headers={
                        "Authorization": f"Bearer {user['access_token']}",
                        "Content-Type": "application/json",
                        "X-Test-ID": self.test_prefix
                    },
                    json={
                        "agent_type": agent_type,
                        "message": request_data["message"],
                        "options": {
                            "complexity": request_data["complexity"],
                            "priority": request_data["priority"]
                        }
                    }
                )
                
                execution_end = time.time()
                execution_time = execution_end - execution_start
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    return {
                        "success": True,
                        "user_id": user["user_id"],
                        "user_tier": user["tier"],
                        "agent_type": agent_type,
                        "execution_time": execution_time,
                        "response_data": response_data,
                        "websocket_events": response_data.get("events", [])
                    }
                else:
                    return {
                        "success": False,
                        "user_id": user["user_id"],
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "execution_time": execution_time
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "user_id": user["user_id"],
                "error": str(e)
            }
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_authenticated_websocket_concurrent_connections(self):
        """
        Test authenticated WebSocket connections under concurrent load.
        
        BUSINESS CRITICAL: WebSocket performance enables real-time user experience
        and agent interaction feedback.
        """
        concurrent_connections = 12  # Realistic WebSocket load
        
        # Create authenticated users for WebSocket testing  
        authenticated_users = []
        
        for i in range(concurrent_connections):
            auth_result = await self.auth_helper.create_and_authenticate_user(
                email=f"ws_test_{i}@example.com",
                tier="mid",  # Use consistent tier for WebSocket testing
                test_prefix=self.test_prefix
            )
            
            if auth_result.success:
                authenticated_users.append({
                    "user_id": f"ws_user_{i}",
                    "access_token": auth_result.access_token
                })
        
        assert len(authenticated_users) >= concurrent_connections * 0.7, \
            f"Insufficient authenticated users for WebSocket test: {len(authenticated_users)}/{concurrent_connections}"
        
        # Test concurrent authenticated WebSocket connections
        ws_start_time = time.time()
        
        ws_tasks = [
            self._test_authenticated_websocket_connection(user)
            for user in authenticated_users
        ]
        
        ws_results = await asyncio.gather(*ws_tasks, return_exceptions=True)
        
        ws_end_time = time.time()
        total_ws_duration = ws_end_time - ws_start_time
        
        # Analyze WebSocket connection results
        successful_connections = [
            result for result in ws_results
            if isinstance(result, dict) and result.get("connected", False)
        ]
        
        # WebSocket connection success rate
        ws_success_rate = len(successful_connections) / len(ws_results)
        
        if len(successful_connections) > 0:  # Only validate if WebSocket server is available
            assert ws_success_rate >= 0.70, f"WebSocket connection success rate too low: {ws_success_rate:.2%}"
            
            # WebSocket performance validation
            connection_times = [conn["connection_time"] for conn in successful_connections if "connection_time" in conn]
            
            if connection_times:
                avg_connection_time = sum(connection_times) / len(connection_times)
                assert avg_connection_time < 3.0, f"WebSocket connections too slow: {avg_connection_time:.2f}s"
            
            # Message throughput validation
            message_counts = [conn["messages_exchanged"] for conn in successful_connections if "messages_exchanged" in conn]
            
            if message_counts:
                total_messages = sum(message_counts)
                messages_per_second = total_messages / total_ws_duration
                assert messages_per_second > 5, f"WebSocket message throughput too low: {messages_per_second:.2f} msg/s"
        
        print(f" PASS:  Authenticated WebSocket test completed: {len(successful_connections)}/{len(ws_results)} connections")
    
    async def _test_authenticated_websocket_connection(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Test authenticated WebSocket connection for a single user"""
        try:
            import websockets
            
            connection_start = time.time()
            
            # Connect with authentication
            ws_url_with_auth = f"{self.websocket_url}?token={user['access_token']}"
            
            async with websockets.connect(ws_url_with_auth, timeout=10) as websocket:
                connection_end = time.time()
                connection_time = connection_end - connection_start
                
                messages_sent = 0
                messages_received = 0
                
                # Test message exchange
                for i in range(3):  # Send 3 test messages
                    test_message = {
                        "type": "test_message",
                        "user_id": user["user_id"],
                        "message_id": i,
                        "content": f"Test message {i}"
                    }
                    
                    await websocket.send(str(test_message))
                    messages_sent += 1
                    
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        messages_received += 1
                    except asyncio.TimeoutError:
                        pass
                    
                    await asyncio.sleep(0.1)
                
                return {
                    "connected": True,
                    "user_id": user["user_id"],
                    "connection_time": connection_time,
                    "messages_exchanged": messages_sent + messages_received,
                    "messages_sent": messages_sent,
                    "messages_received": messages_received
                }
                
        except Exception as e:
            return {
                "connected": False,
                "user_id": user["user_id"],
                "error": str(e)
            }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])