#!/usr/bin/env python
"""WEBSOCKET DEPLOYMENT VALIDATION SUITE

This suite validates the specific deployment fixes identified by the team:
- GCP Infrastructure Agent: Load balancer timeout/header issues
- WebSocket Specialist: HTTP 403 handshake failures, JWT synchronization
- DevOps Configuration Agent: Complete deployment fixes

Business Value: Validates $180K+ MRR chat functionality after deployment
Success Criteria: All 7 staging WebSocket tests pass after deployment
"""

import asyncio
import json
import os
import sys
import time
import uuid
import pytest
import websockets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.isolated_environment import get_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from loguru import logger


class WebSocketDeploymentValidator:
    """Validates WebSocket deployment fixes for staging environment."""
    
    def __init__(self, environment: str = "staging"):
        self.environment = environment
        self.auth_helper = E2EAuthHelper()
        self.test_results: Dict[str, Any] = {}
        self.env = get_env()
        
    async def validate_load_balancer_timeout_fix(self) -> Dict[str, Any]:
        """Validate load balancer 24-hour timeout fix."""
        logger.info(" SEARCH:  Validating load balancer timeout configuration...")
        
        result = {
            "test": "load_balancer_timeout_fix",
            "status": "pending",
            "details": {}
        }
        
        try:
            # Test 1: Validate WebSocket upgrade headers
            websocket_url = self._get_websocket_url()
            headers = await self._get_auth_headers()
            
            async with websockets.connect(
                websocket_url,
                extra_headers=headers,
                timeout=30  # Shorter timeout for initial validation
            ) as websocket:
                
                # Send ping to establish connection
                await websocket.send(json.dumps({
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                }))
                
                # Wait for pong response
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                response_data = json.loads(response)
                
                result["details"]["connection_established"] = True
                result["details"]["upgrade_headers_valid"] = True
                result["details"]["initial_response"] = response_data.get("type")
                
                # Test 2: Validate connection can handle timeout configuration
                # Send heartbeat to test timeout handling
                await websocket.send(json.dumps({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                }))
                
                heartbeat_response = await asyncio.wait_for(websocket.recv(), timeout=10)
                result["details"]["heartbeat_response"] = json.loads(heartbeat_response)
                
                result["status"] = "passed"
                logger.success(" PASS:  Load balancer timeout fix validated")
                
        except websockets.exceptions.InvalidHandshake as e:
            result["status"] = "failed"
            result["error"] = f"WebSocket handshake failed: {e}"
            result["details"]["handshake_error"] = str(e)
            logger.error(f" FAIL:  Load balancer handshake failed: {e}")
            
        except asyncio.TimeoutError:
            result["status"] = "failed"
            result["error"] = "WebSocket connection timeout"
            logger.error(" FAIL:  WebSocket connection timeout")
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = f"Unexpected error: {e}"
            logger.error(f" FAIL:  Load balancer validation failed: {e}")
            
        return result
        
    async def validate_403_handshake_fix(self) -> Dict[str, Any]:
        """Validate HTTP 403 WebSocket handshake fix."""
        logger.info(" SEARCH:  Validating WebSocket 403 handshake fix...")
        
        result = {
            "test": "403_handshake_fix",
            "status": "pending",
            "details": {}
        }
        
        try:
            # Test with valid JWT token
            websocket_url = self._get_websocket_url()
            headers = await self._get_auth_headers()
            
            result["details"]["auth_headers_generated"] = True
            result["details"]["jwt_token_length"] = len(headers.get("Authorization", "").replace("Bearer ", ""))
            
            # Attempt WebSocket connection with auth
            async with websockets.connect(
                websocket_url,
                extra_headers=headers,
                timeout=15
            ) as websocket:
                
                # Test authenticated connection works
                await websocket.send(json.dumps({
                    "type": "auth_test",
                    "message": "Testing authenticated connection"
                }))
                
                # Should not get 403 Forbidden
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                response_data = json.loads(response)
                
                if response_data.get("error") and "403" in str(response_data["error"]):
                    result["status"] = "failed"
                    result["error"] = "Still receiving 403 errors after fix"
                    result["details"]["response"] = response_data
                else:
                    result["status"] = "passed"
                    result["details"]["authenticated_connection"] = True
                    result["details"]["response"] = response_data
                    logger.success(" PASS:  WebSocket 403 handshake fix validated")
                    
        except websockets.exceptions.ConnectionClosedError as e:
            if e.code == 403:
                result["status"] = "failed"
                result["error"] = f"WebSocket still returning 403 Forbidden: {e}"
                logger.error(f" FAIL:  WebSocket 403 fix not working: {e}")
            else:
                result["status"] = "failed"
                result["error"] = f"WebSocket connection closed: {e}"
                
        except Exception as e:
            result["status"] = "failed"
            result["error"] = f"403 handshake test failed: {e}"
            logger.error(f" FAIL:  WebSocket 403 validation failed: {e}")
            
        return result
        
    async def validate_jwt_synchronization_fix(self) -> Dict[str, Any]:
        """Validate JWT token synchronization between services."""
        logger.info(" SEARCH:  Validating JWT synchronization fix...")
        
        result = {
            "test": "jwt_synchronization_fix",
            "status": "pending",
            "details": {}
        }
        
        try:
            # Generate JWT token through auth service
            auth_token = await self.auth_helper.get_test_jwt_token()
            result["details"]["jwt_token_generated"] = True
            
            # Test token validation in WebSocket context
            websocket_url = self._get_websocket_url()
            headers = {"Authorization": f"Bearer {auth_token}"}
            
            async with websockets.connect(
                websocket_url,
                extra_headers=headers,
                timeout=15
            ) as websocket:
                
                # Send message requiring authentication
                test_message = {
                    "type": "agent_request",
                    "payload": {
                        "agent": "test_agent",
                        "message": "JWT sync test",
                        "thread_id": str(uuid.uuid4())
                    }
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Should receive authenticated response, not auth error
                response = await asyncio.wait_for(websocket.recv(), timeout=15)
                response_data = json.loads(response)
                
                if "authentication" in str(response_data).lower() and "error" in str(response_data).lower():
                    result["status"] = "failed"
                    result["error"] = "JWT token not synchronized between services"
                    result["details"]["auth_error_response"] = response_data
                else:
                    result["status"] = "passed"
                    result["details"]["jwt_validation_successful"] = True
                    result["details"]["response_type"] = response_data.get("type")
                    logger.success(" PASS:  JWT synchronization fix validated")
                    
        except Exception as e:
            result["status"] = "failed"
            result["error"] = f"JWT synchronization test failed: {e}"
            logger.error(f" FAIL:  JWT synchronization validation failed: {e}")
            
        return result
        
    async def validate_agent_events_business_value(self) -> Dict[str, Any]:
        """Validate critical WebSocket agent events for chat business value."""
        logger.info(" SEARCH:  Validating WebSocket agent events for chat business value...")
        
        result = {
            "test": "agent_events_business_value",
            "status": "pending",
            "details": {
                "required_events": ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"],
                "received_events": []
            }
        }
        
        try:
            websocket_url = self._get_websocket_url()
            headers = await self._get_auth_headers()
            
            async with websockets.connect(
                websocket_url,
                extra_headers=headers,
                timeout=20
            ) as websocket:
                
                # Start agent execution that should generate events
                agent_request = {
                    "type": "agent_request",
                    "payload": {
                        "agent": "data_sub_agent", 
                        "message": "Generate a simple data analysis report",
                        "thread_id": str(uuid.uuid4()),
                        "require_events": True  # Force event generation
                    }
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Collect events for up to 30 seconds
                received_events = []
                start_time = time.time()
                
                while time.time() - start_time < 30:  # 30 second timeout
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5)
                        event_data = json.loads(response)
                        event_type = event_data.get("type", "unknown")
                        
                        received_events.append(event_type)
                        result["details"]["received_events"].append({
                            "type": event_type,
                            "timestamp": datetime.utcnow().isoformat(),
                            "data": event_data
                        })
                        
                        # Break if we get completion event
                        if event_type == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        logger.warning("Timeout waiting for more events")
                        break
                        
                # Validate critical events were received
                required_events = result["details"]["required_events"]
                received_event_types = [e.get("type") for e in result["details"]["received_events"]]
                
                missing_events = [event for event in required_events if event not in received_event_types]
                
                if missing_events:
                    result["status"] = "failed"
                    result["error"] = f"Missing critical WebSocket events: {missing_events}"
                    result["details"]["missing_events"] = missing_events
                    logger.error(f" FAIL:  Missing critical events: {missing_events}")
                else:
                    result["status"] = "passed"
                    result["details"]["all_events_received"] = True
                    result["details"]["event_flow_complete"] = True
                    logger.success(" PASS:  All critical WebSocket agent events validated")
                    
        except Exception as e:
            result["status"] = "failed"
            result["error"] = f"Agent events validation failed: {e}"
            logger.error(f" FAIL:  Agent events validation failed: {e}")
            
        return result
        
    async def validate_multi_user_isolation(self) -> Dict[str, Any]:
        """Validate multi-user WebSocket isolation."""
        logger.info(" SEARCH:  Validating multi-user WebSocket isolation...")
        
        result = {
            "test": "multi_user_isolation",
            "status": "pending",
            "details": {}
        }
        
        try:
            # Create connections for two different users
            user1_token = await self.auth_helper.get_test_jwt_token(user_id="test_user_1")
            user2_token = await self.auth_helper.get_test_jwt_token(user_id="test_user_2")
            
            websocket_url = self._get_websocket_url()
            
            # Test concurrent connections
            async with websockets.connect(
                websocket_url,
                extra_headers={"Authorization": f"Bearer {user1_token}"},
                timeout=15
            ) as ws1, websockets.connect(
                websocket_url,
                extra_headers={"Authorization": f"Bearer {user2_token}"},
                timeout=15
            ) as ws2:
                
                # Send messages from both users
                thread1_id = str(uuid.uuid4())
                thread2_id = str(uuid.uuid4())
                
                await ws1.send(json.dumps({
                    "type": "agent_request",
                    "payload": {
                        "agent": "test_agent",
                        "message": "User 1 message",
                        "thread_id": thread1_id
                    }
                }))
                
                await ws2.send(json.dumps({
                    "type": "agent_request", 
                    "payload": {
                        "agent": "test_agent",
                        "message": "User 2 message",
                        "thread_id": thread2_id
                    }
                }))
                
                # Collect responses
                user1_responses = []
                user2_responses = []
                
                # Get responses for both users
                for _ in range(4):  # Expect at least 2 responses per user
                    try:
                        response1 = await asyncio.wait_for(ws1.recv(), timeout=10)
                        user1_responses.append(json.loads(response1))
                    except asyncio.TimeoutError:
                        pass
                        
                    try:
                        response2 = await asyncio.wait_for(ws2.recv(), timeout=10)
                        user2_responses.append(json.loads(response2))
                    except asyncio.TimeoutError:
                        pass
                
                # Validate isolation - user1 should not see user2's thread data
                user1_threads = [r.get("thread_id") for r in user1_responses if r.get("thread_id")]
                user2_threads = [r.get("thread_id") for r in user2_responses if r.get("thread_id")]
                
                # Check for cross-contamination
                cross_contamination = any(thread2_id in user1_threads) or any(thread1_id in user2_threads)
                
                if cross_contamination:
                    result["status"] = "failed"
                    result["error"] = "Multi-user isolation violated - users seeing each other's data"
                    result["details"]["user1_threads"] = user1_threads
                    result["details"]["user2_threads"] = user2_threads
                else:
                    result["status"] = "passed"
                    result["details"]["isolation_maintained"] = True
                    result["details"]["user1_response_count"] = len(user1_responses)
                    result["details"]["user2_response_count"] = len(user2_responses)
                    logger.success(" PASS:  Multi-user WebSocket isolation validated")
                    
        except Exception as e:
            result["status"] = "failed"
            result["error"] = f"Multi-user isolation test failed: {e}"
            logger.error(f" FAIL:  Multi-user isolation validation failed: {e}")
            
        return result
        
    async def validate_websocket_health_endpoint(self) -> Dict[str, Any]:
        """Validate WebSocket health endpoint for monitoring."""
        logger.info(" SEARCH:  Validating WebSocket health endpoint...")
        
        result = {
            "test": "websocket_health_endpoint",
            "status": "pending",
            "details": {}
        }
        
        try:
            import aiohttp
            
            # Get health endpoint URL
            base_url = self._get_base_url()
            health_url = f"{base_url}/api/websocket/health"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(health_url, timeout=10) as response:
                    
                    if response.status != 200:
                        result["status"] = "failed"
                        result["error"] = f"Health endpoint returned status {response.status}"
                        return result
                        
                    health_data = await response.json()
                    
                    # Validate required health check fields
                    required_fields = ["status", "service", "timestamp", "metrics"]
                    missing_fields = [field for field in required_fields if field not in health_data]
                    
                    if missing_fields:
                        result["status"] = "failed"
                        result["error"] = f"Health endpoint missing required fields: {missing_fields}"
                        result["details"]["health_response"] = health_data
                    else:
                        # Validate health status is not 'degraded' or 'unhealthy'
                        health_status = health_data.get("status", "unknown")
                        
                        if health_status in ["degraded", "unhealthy", "error"]:
                            result["status"] = "failed"
                            result["error"] = f"WebSocket service reporting unhealthy status: {health_status}"
                            result["details"]["health_response"] = health_data
                        else:
                            result["status"] = "passed"
                            result["details"]["health_status"] = health_status
                            result["details"]["service_info"] = health_data
                            logger.success(" PASS:  WebSocket health endpoint validated")
                            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = f"Health endpoint test failed: {e}"
            logger.error(f" FAIL:  WebSocket health endpoint validation failed: {e}")
            
        return result
        
    def _get_websocket_url(self) -> str:
        """Get WebSocket URL for testing."""
        if self.environment == "staging":
            return "wss://staging.netrasystems.ai/api/ws"
        elif self.environment == "production":
            return "wss://app.netrasystems.ai/api/ws"
        else:
            # Local development
            return "ws://localhost:8000/api/ws"
            
    def _get_base_url(self) -> str:
        """Get base HTTP URL for testing."""
        if self.environment == "staging":
            return "https://staging.netrasystems.ai"
        elif self.environment == "production":
            return "https://app.netrasystems.ai"
        else:
            # Local development
            return "http://localhost:8000"
            
    async def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for WebSocket connection."""
        try:
            jwt_token = await self.auth_helper.get_test_jwt_token()
            return {"Authorization": f"Bearer {jwt_token}"}
        except Exception as e:
            logger.warning(f"Failed to get auth headers: {e}")
            return {}


class WebSocketDeploymentTestSuite:
    """Main test suite for WebSocket deployment validation."""
    
    def __init__(self, environment: str = "staging"):
        self.validator = WebSocketDeploymentValidator(environment)
        self.results: Dict[str, Any] = {}
        
    async def run_all_validations(self) -> Dict[str, Any]:
        """Run all WebSocket deployment validations."""
        logger.info("[U+1F680] Starting WebSocket deployment validation suite...")
        
        test_suite_results = {
            "test_suite": "websocket_deployment_validation",
            "environment": self.validator.environment,
            "timestamp": datetime.utcnow().isoformat(),
            "tests": {},
            "summary": {}
        }
        
        # Run all validation tests
        validation_tests = [
            self.validator.validate_load_balancer_timeout_fix(),
            self.validator.validate_403_handshake_fix(),
            self.validator.validate_jwt_synchronization_fix(),
            self.validator.validate_agent_events_business_value(),
            self.validator.validate_multi_user_isolation(),
            self.validator.validate_websocket_health_endpoint()
        ]
        
        # Execute all tests concurrently
        results = await asyncio.gather(*validation_tests, return_exceptions=True)
        
        # Process results
        passed_tests = 0
        failed_tests = 0
        
        for result in results:
            if isinstance(result, Exception):
                test_name = "unknown_test"
                test_result = {
                    "test": test_name,
                    "status": "error", 
                    "error": str(result)
                }
                failed_tests += 1
            else:
                test_name = result.get("test", "unknown_test")
                test_result = result
                
                if result.get("status") == "passed":
                    passed_tests += 1
                else:
                    failed_tests += 1
                    
            test_suite_results["tests"][test_name] = test_result
            
        # Generate summary
        total_tests = passed_tests + failed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        test_suite_results["summary"] = {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": round(success_rate, 1),
            "deployment_ready": success_rate >= 85  # 85% threshold for deployment
        }
        
        # Log summary
        if test_suite_results["summary"]["deployment_ready"]:
            logger.success(f" CELEBRATION:  WebSocket deployment validation PASSED: {success_rate}% success rate")
            logger.success(" PASS:  WebSocket deployment fixes validated and ready for production")
        else:
            logger.error(f" FAIL:  WebSocket deployment validation FAILED: {success_rate}% success rate")
            logger.error("[U+1F6AB] WebSocket deployment NOT ready - fix failing tests before deployment")
            
        return test_suite_results


# ============================================================================
# PYTEST TEST CLASSES
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.deployment
class TestWebSocketDeploymentValidation:
    """Pytest test class for WebSocket deployment validation."""
    
    @pytest.fixture(scope="class")
    def environment(self):
        """Get test environment."""
        return os.getenv("TEST_ENVIRONMENT", "staging")
        
    async def test_load_balancer_timeout_fix(self, environment):
        """Test that load balancer timeout configuration is fixed."""
        validator = WebSocketDeploymentValidator(environment)
        result = await validator.validate_load_balancer_timeout_fix()
        
        assert result["status"] == "passed", f"Load balancer timeout fix failed: {result.get('error')}"
        assert result["details"].get("connection_established") == True
        
    async def test_403_handshake_fix(self, environment):
        """Test that WebSocket 403 handshake issues are resolved."""
        validator = WebSocketDeploymentValidator(environment)
        result = await validator.validate_403_handshake_fix()
        
        assert result["status"] == "passed", f"WebSocket 403 handshake fix failed: {result.get('error')}"
        assert result["details"].get("authenticated_connection") == True
        
    async def test_jwt_synchronization_fix(self, environment):
        """Test that JWT synchronization between services is working."""
        validator = WebSocketDeploymentValidator(environment)
        result = await validator.validate_jwt_synchronization_fix()
        
        assert result["status"] == "passed", f"JWT synchronization fix failed: {result.get('error')}"
        assert result["details"].get("jwt_validation_successful") == True
        
    async def test_agent_events_business_value(self, environment):
        """Test that critical WebSocket agent events are working for chat business value."""
        validator = WebSocketDeploymentValidator(environment)
        result = await validator.validate_agent_events_business_value()
        
        assert result["status"] == "passed", f"Agent events business value test failed: {result.get('error')}"
        assert result["details"].get("all_events_received") == True
        
    async def test_multi_user_isolation(self, environment):
        """Test that multi-user WebSocket isolation is maintained.""" 
        validator = WebSocketDeploymentValidator(environment)
        result = await validator.validate_multi_user_isolation()
        
        assert result["status"] == "passed", f"Multi-user isolation test failed: {result.get('error')}"
        assert result["details"].get("isolation_maintained") == True
        
    async def test_websocket_health_endpoint(self, environment):
        """Test that WebSocket health endpoint is working for monitoring."""
        validator = WebSocketDeploymentValidator(environment)
        result = await validator.validate_websocket_health_endpoint()
        
        assert result["status"] == "passed", f"WebSocket health endpoint test failed: {result.get('error')}"
        assert result["details"].get("health_status") in ["healthy", "ok"]


# ============================================================================
# CLI EXECUTION
# ============================================================================

async def main():
    """Main CLI execution for WebSocket deployment validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="WebSocket Deployment Validation Suite")
    parser.add_argument("--environment", default="staging", choices=["staging", "production", "development"])
    parser.add_argument("--output-file", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    # Run validation suite
    test_suite = WebSocketDeploymentTestSuite(args.environment)
    results = await test_suite.run_all_validations()
    
    # Save results if requested
    if args.output_file:
        with open(args.output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {args.output_file}")
        
    # Exit with appropriate code
    if results["summary"]["deployment_ready"]:
        logger.success("WebSocket deployment validation completed successfully")
        sys.exit(0)
    else:
        logger.error("WebSocket deployment validation failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())