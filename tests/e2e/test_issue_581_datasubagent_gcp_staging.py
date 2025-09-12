"""
E2E Tests for Issue #581: DataSubAgent Workflow on GCP Staging

BUSINESS VALUE:
- Enterprise/Platform | Golden Path Protection | $500K+ ARR rescue
- Validates complete user journey: login → data agent request → AI response
- Tests real GCP Cloud Run deployment with actual agent instantiation
- Protects critical Golden Path user flow with real infrastructure

TEST STRATEGY:
1. Complete E2E workflow testing on GCP staging environment
2. Real user authentication and session management
3. Real WebSocket connections and agent event validation
4. Real data agent instantiation through staging services
5. Real LLM integration and response validation

CRITICAL: These are E2E tests for GCP staging - they require:
- Real GCP staging environment running
- Real authentication services
- Real WebSocket infrastructure  
- Real agent services
- NO Docker - pure GCP Cloud Run testing

SSOT Compliance:
- Uses SSotAsyncTestCase for async E2E testing
- Environment isolation through IsolatedEnvironment
- Real services ONLY - no mocks allowed in E2E
- WebSocket event validation with real connections
- Business value measurement and validation

Related Files:
- GCP Cloud Run services in staging
- /netra_backend/app/agents/data_sub_agent/data_sub_agent.py (alias)
- /netra_backend/app/agents/data/unified_data_agent.py (implementation)
- Staging deployment configuration
"""

import asyncio
import pytest
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from contextlib import asynccontextmanager

# SSOT Compliance: Use SSOT AsyncTestCase for E2E
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# E2E specific imports for real services
try:
    import websockets
    WEBSOCKET_CLIENT_AVAILABLE = True
except ImportError:
    WEBSOCKET_CLIENT_AVAILABLE = False

try:
    import httpx
    HTTP_CLIENT_AVAILABLE = True  
except ImportError:
    HTTP_CLIENT_AVAILABLE = False

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

# Import for staging environment configuration
from shared.isolated_environment import get_env

# Import agent classes to verify in E2E context
from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
from netra_backend.app.agents.data.unified_data_agent import UnifiedDataAgent


@pytest.mark.e2e
@pytest.mark.staging
class TestIssue581DataSubAgentGCPStaging(SSotAsyncTestCase):
    """
    E2E tests for Issue #581 on GCP staging environment.
    
    These tests validate the complete user journey with real GCP services,
    specifically focusing on data agent instantiation and execution.
    """
    
    def setup_method(self, method):
        """Setup E2E test environment for GCP staging."""
        super().setup_method(method)
        
        # Get staging environment configuration
        self.env = get_env()
        self.staging_base_url = self.env.get("STAGING_BASE_URL", "https://netra-staging.example.com")
        self.staging_ws_url = self.env.get("STAGING_WS_URL", "wss://netra-staging.example.com/ws")
        
        # E2E test configuration
        self.test_user_email = f"e2e-test-581-{datetime.now().timestamp()}@netratest.com"
        self.test_user_password = "Test123!E2E"
        self.test_timeout = 30.0  # 30 second timeout for E2E operations
        
        # Record E2E test metrics
        self.record_metric("test_category", "e2e") 
        self.record_metric("issue_number", "581")
        self.record_metric("environment", "gcp_staging")
        self.record_metric("uses_real_services", True)
        self.record_metric("uses_docker", False)
        
        # Skip if required dependencies not available
        if not all([WEBSOCKET_CLIENT_AVAILABLE, HTTP_CLIENT_AVAILABLE, JWT_AVAILABLE]):
            pytest.skip("Required E2E dependencies not available (websockets, httpx, jwt)")
    
    async def test_complete_data_agent_golden_path_flow(self):
        """
        CRITICAL: Complete Golden Path flow with data agent on GCP staging.
        
        This tests the complete user journey:
        1. User authentication 
        2. WebSocket connection
        3. Data agent request (triggering Issue #581)
        4. Agent instantiation and execution
        5. All 5 WebSocket events received
        6. Meaningful AI response delivered
        
        This test should FAIL initially due to Issue #581, then PASS after fix.
        """
        # Step 1: Authenticate user on staging
        auth_token = await self._authenticate_test_user()
        self.assertIsNotNone(auth_token, "Authentication failed on staging")
        self.record_metric("authentication_success", True)
        
        # Step 2: Establish WebSocket connection
        async with self._websocket_connection(auth_token) as websocket:
            self.record_metric("websocket_connection_success", True)
            
            # Step 3: Send data agent request
            agent_request = {
                "type": "agent_request",
                "agent_type": "data",  # This triggers DataSubAgent instantiation
                "message": "Analyze my system performance over the last hour",
                "parameters": {
                    "analysis_type": "performance",
                    "timeframe": "1h",
                    "metrics": ["latency_ms", "throughput", "success_rate"]
                }
            }
            
            start_time = datetime.now(timezone.utc)
            await websocket.send(json.dumps(agent_request))
            self.record_metric("agent_request_sent", True)
            
            # Step 4: Collect all WebSocket events
            events = []
            agent_completed = False
            error_occurred = False
            
            try:
                async with asyncio.timeout(self.test_timeout):
                    while not agent_completed and not error_occurred:
                        try:
                            message = await websocket.recv()
                            event = json.loads(message)
                            events.append(event)
                            
                            # Check for Issue #581 specific error
                            if event.get("type") == "error":
                                error_msg = event.get("message", "")
                                if "unexpected keyword argument 'name'" in error_msg:
                                    self.record_metric("issue_581_error_detected", True)
                                    pytest.fail(f"Issue #581 reproduced in staging: {error_msg}")
                                else:
                                    error_occurred = True
                                    self.record_metric("other_error_occurred", error_msg)
                            
                            # Check for completion
                            elif event.get("type") == "agent_completed":
                                agent_completed = True
                                
                        except websockets.exceptions.ConnectionClosed:
                            break
                        except asyncio.TimeoutError:
                            break
            
            except asyncio.TimeoutError:
                self.record_metric("agent_execution_timeout", True)
                pytest.fail(f"Agent execution timed out after {self.test_timeout}s")
            
            # Step 5: Validate all required WebSocket events were received
            event_types = [event.get("type") for event in events]
            required_events = [
                "agent_started",
                "agent_thinking", 
                "tool_executing",
                "tool_completed", 
                "agent_completed"
            ]
            
            missing_events = [evt for evt in required_events if evt not in event_types]
            if missing_events:
                self.record_metric("missing_websocket_events", missing_events)
                pytest.fail(f"Missing required WebSocket events: {missing_events}")
            
            self.record_metric("all_websocket_events_received", True)
            self.record_metric("total_events_received", len(events))
            
            # Step 6: Validate meaningful response was delivered
            completion_event = next(
                (event for event in events if event.get("type") == "agent_completed"),
                None
            )
            
            self.assertIsNotNone(completion_event, "Agent completion event not found")
            
            result = completion_event.get("result", {})
            self.assertIsNotNone(result, "Agent result is missing")
            
            # Validate business value was delivered
            self._validate_data_analysis_business_value(result)
            
            # Record timing metrics
            end_time = datetime.now(timezone.utc)
            total_time = (end_time - start_time).total_seconds()
            self.record_metric("total_execution_time_seconds", total_time)
            self.record_metric("golden_path_success", True)
    
    async def test_datasubagent_alias_instantiation_staging(self):
        """
        Test DataSubAgent alias instantiation specifically on staging.
        
        This focuses on the alias behavior that might trigger Issue #581.
        """
        # Authenticate and connect
        auth_token = await self._authenticate_test_user()
        
        async with self._websocket_connection(auth_token) as websocket:
            # Send request that specifically uses DataSubAgent alias
            agent_request = {
                "type": "agent_request", 
                "agent_type": "DataSubAgent",  # Explicit alias usage
                "agent_name": "staging_data_sub_agent",  # This might trigger Issue #581
                "message": "Run anomaly detection on recent data",
                "parameters": {
                    "analysis_type": "anomaly",
                    "timeframe": "24h"
                }
            }
            
            await websocket.send(json.dumps(agent_request))
            
            # Collect response
            try:
                async with asyncio.timeout(15.0):
                    message = await websocket.recv()
                    response = json.loads(message)
                    
                    # Check for Issue #581 error
                    if response.get("type") == "error":
                        error_msg = response.get("message", "")
                        if "unexpected keyword argument 'name'" in error_msg:
                            self.record_metric("datasubagent_alias_issue_581", True)
                            pytest.fail(f"DataSubAgent alias Issue #581 reproduced: {error_msg}")
                    
                    # Should get agent_started event
                    self.assertEqual(response.get("type"), "agent_started")
                    self.record_metric("datasubagent_alias_success", True)
                    
            except asyncio.TimeoutError:
                pytest.fail("DataSubAgent alias request timed out")
    
    async def test_concurrent_data_agent_requests_staging(self):
        """
        Test concurrent data agent requests on staging.
        
        This tests multi-user scenarios that might reveal Issue #581
        under concurrent load.
        """
        # Create multiple test users
        num_concurrent_users = 3
        auth_tokens = []
        
        for i in range(num_concurrent_users):
            token = await self._authenticate_test_user(user_suffix=f"_concurrent_{i}")
            auth_tokens.append(token)
        
        # Define concurrent request scenarios
        async def execute_user_request(user_index: int, auth_token: str):
            """Execute data agent request for one user."""
            try:
                async with self._websocket_connection(auth_token) as websocket:
                    request = {
                        "type": "agent_request",
                        "agent_type": "data",
                        "agent_name": f"concurrent_agent_{user_index}",  # Issue #581 trigger
                        "message": f"Analyze performance for user {user_index}",
                        "parameters": {
                            "analysis_type": "performance",
                            "user_id": f"concurrent_user_{user_index}"
                        }
                    }
                    
                    await websocket.send(json.dumps(request))
                    
                    # Wait for completion or error
                    async with asyncio.timeout(20.0):
                        while True:
                            message = await websocket.recv()
                            event = json.loads(message)
                            
                            # Check for Issue #581 error
                            if event.get("type") == "error":
                                error_msg = event.get("message", "")
                                if "unexpected keyword argument 'name'" in error_msg:
                                    return {"success": False, "issue_581": True, "error": error_msg}
                                else:
                                    return {"success": False, "issue_581": False, "error": error_msg}
                            
                            # Check for completion 
                            elif event.get("type") == "agent_completed":
                                return {"success": True, "user_index": user_index}
                
            except Exception as e:
                return {"success": False, "exception": str(e), "user_index": user_index}
        
        # Execute concurrent requests
        tasks = [
            execute_user_request(i, token) 
            for i, token in enumerate(auth_tokens)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_requests = [r for r in results if isinstance(r, dict) and r.get("success")]
        issue_581_failures = [r for r in results if isinstance(r, dict) and r.get("issue_581")]
        other_failures = [r for r in results if isinstance(r, dict) and not r.get("success") and not r.get("issue_581")]
        
        # Record metrics
        self.record_metric("concurrent_successful_requests", len(successful_requests))
        self.record_metric("concurrent_issue_581_failures", len(issue_581_failures))
        self.record_metric("concurrent_other_failures", len(other_failures))
        
        # Fail if Issue #581 occurred
        if issue_581_failures:
            error_details = [f["error"] for f in issue_581_failures]
            pytest.fail(f"Concurrent Issue #581 failures: {error_details}")
        
        # Verify all requests succeeded  
        self.assertEqual(len(successful_requests), num_concurrent_users)
    
    async def test_data_agent_response_quality_staging(self):
        """
        Test that data agent responses deliver real business value on staging.
        
        This validates that the Issue #581 fix doesn't just prevent errors,
        but also maintains the quality of AI responses.
        """
        auth_token = await self._authenticate_test_user()
        
        async with self._websocket_connection(auth_token) as websocket:
            # Send sophisticated data analysis request
            request = {
                "type": "agent_request",
                "agent_type": "data",
                "message": "Perform comprehensive cost optimization analysis with specific recommendations",
                "parameters": {
                    "analysis_type": "cost_optimization",
                    "timeframe": "7d",
                    "include_recommendations": True,
                    "detail_level": "comprehensive"
                }
            }
            
            await websocket.send(json.dumps(request))
            
            # Collect full response
            events = []
            async with asyncio.timeout(45.0):  # Longer timeout for comprehensive analysis
                while True:
                    try:
                        message = await websocket.recv()
                        event = json.loads(message)
                        events.append(event)
                        
                        if event.get("type") == "agent_completed":
                            break
                        elif event.get("type") == "error":
                            error_msg = event.get("message", "")
                            if "unexpected keyword argument 'name'" in error_msg:
                                pytest.fail(f"Quality test Issue #581 reproduced: {error_msg}")
                            else:
                                pytest.fail(f"Other error in quality test: {error_msg}")
                    
                    except websockets.exceptions.ConnectionClosed:
                        break
            
            # Validate response quality
            completion_event = events[-1]
            self.assertEqual(completion_event.get("type"), "agent_completed")
            
            result = completion_event.get("result", {})
            
            # Quality checks for cost optimization analysis
            self.assertIn("analysis_type", result)
            self.assertEqual(result["analysis_type"], "cost_optimization")
            
            # Should have cost analysis
            if "current_monthly_cost" in result:
                self.assertIsInstance(result["current_monthly_cost"], (int, float))
                self.record_metric("cost_analysis_present", True)
            
            # Should have savings opportunities
            if "opportunities" in result:
                self.assertIsInstance(result["opportunities"], list)
                self.record_metric("opportunities_count", len(result["opportunities"]))
            
            # Should have recommendations
            if "recommendations" in result:
                self.assertIsInstance(result["recommendations"], list)
                self.record_metric("recommendations_count", len(result["recommendations"]))
            
            self.record_metric("response_quality_validated", True)
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    async def _authenticate_test_user(self, user_suffix: str = "") -> str:
        """Authenticate test user on staging and return auth token."""
        if not HTTP_CLIENT_AVAILABLE:
            pytest.skip("httpx not available for HTTP requests")
        
        test_email = f"e2e-test-581{user_suffix}-{int(datetime.now().timestamp())}@netratest.com"
        
        async with httpx.AsyncClient() as client:
            # Register test user
            register_response = await client.post(
                f"{self.staging_base_url}/auth/register",
                json={
                    "email": test_email,
                    "password": self.test_user_password,
                    "name": f"E2E Test User 581{user_suffix}"
                },
                timeout=10.0
            )
            
            if register_response.status_code not in [200, 201, 409]:  # 409 = user exists
                pytest.fail(f"User registration failed: {register_response.status_code}")
            
            # Login to get token
            login_response = await client.post(
                f"{self.staging_base_url}/auth/login",
                json={
                    "email": test_email,
                    "password": self.test_user_password
                },
                timeout=10.0
            )
            
            if login_response.status_code != 200:
                pytest.fail(f"User login failed: {login_response.status_code}")
            
            login_data = login_response.json()
            return login_data.get("access_token") or login_data.get("token")
    
    @asynccontextmanager
    async def _websocket_connection(self, auth_token: str):
        """Create authenticated WebSocket connection to staging."""
        if not WEBSOCKET_CLIENT_AVAILABLE:
            pytest.skip("websockets not available for WebSocket connections")
        
        headers = {
            "Authorization": f"Bearer {auth_token}"
        }
        
        try:
            async with websockets.connect(
                self.staging_ws_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            ) as websocket:
                yield websocket
        except Exception as e:
            pytest.fail(f"WebSocket connection failed: {e}")
    
    def _validate_data_analysis_business_value(self, result: Dict[str, Any]) -> None:
        """Validate that the analysis result delivers real business value."""
        # Must have analysis type
        self.assertIn("analysis_type", result, "Analysis type missing from result")
        
        analysis_type = result["analysis_type"]
        self.record_metric("analysis_type_delivered", analysis_type)
        
        # Validate based on analysis type
        if analysis_type == "performance":
            self._validate_performance_analysis_value(result)
        elif analysis_type == "anomaly":
            self._validate_anomaly_analysis_value(result)
        elif analysis_type == "cost_optimization":
            self._validate_cost_optimization_value(result)
        else:
            # Generic validation for other types
            self.assertIsInstance(result, dict, "Result should be a dictionary")
            self.assertTrue(len(result) > 1, "Result should have meaningful content")
        
        self.record_metric("business_value_validated", True)
    
    def _validate_performance_analysis_value(self, result: Dict[str, Any]) -> None:
        """Validate performance analysis delivers business value."""
        # Should have metrics
        if "metrics" in result:
            metrics = result["metrics"]
            self.assertIsInstance(metrics, dict, "Metrics should be a dictionary")
            self.record_metric("performance_metrics_present", True)
        
        # Should have insights or trends
        has_insights = "insights" in result or "trends" in result or "recommendations" in result
        self.assertTrue(has_insights, "Performance analysis should provide insights")
        self.record_metric("performance_insights_present", True)
    
    def _validate_anomaly_analysis_value(self, result: Dict[str, Any]) -> None:
        """Validate anomaly detection delivers business value."""
        # Should have anomalies count
        if "anomalies_found" in result:
            self.assertIsInstance(result["anomalies_found"], int)
            self.record_metric("anomalies_count", result["anomalies_found"])
        
        # Should have severity assessment
        if "severity" in result:
            severity_levels = ["none", "low", "medium", "high", "critical"]
            self.assertIn(result["severity"], severity_levels)
            self.record_metric("anomaly_severity", result["severity"])
    
    def _validate_cost_optimization_value(self, result: Dict[str, Any]) -> None:
        """Validate cost optimization delivers business value."""
        # Should have cost information
        if "current_monthly_cost" in result:
            self.assertIsInstance(result["current_monthly_cost"], (int, float))
            self.record_metric("current_cost_analyzed", True)
        
        # Should have savings potential
        if "potential_savings" in result:
            savings = result["potential_savings"]
            self.assertIsInstance(savings, (int, float))
            self.assertGreaterEqual(savings, 0, "Savings should be non-negative")
            self.record_metric("potential_savings_identified", savings)
        
        # Should have actionable recommendations
        if "recommendations" in result:
            recommendations = result["recommendations"]
            self.assertIsInstance(recommendations, list, "Recommendations should be a list")
            self.assertGreater(len(recommendations), 0, "Should have actionable recommendations")
            self.record_metric("recommendations_provided", len(recommendations))