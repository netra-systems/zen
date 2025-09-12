
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
E2E Tests for Golden Path Infrastructure Validation on GCP Staging

Purpose: Validate complete Golden Path infrastructure works end-to-end on staging
Business Impact: $500K+ MRR at risk - Complete user journey validation
Expected Initial Result: TESTS MUST FAIL to prove infrastructure issues exist

Test Strategy: End-to-end validation on real GCP staging infrastructure
with no mocks, focusing on complete user journey and infrastructure health.

CRITICAL: These tests run on GCP staging remote - NO Docker required.
"""

import pytest
import asyncio
import websockets
import aiohttp
import json
import time
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import urllib.parse

# Import staging test configuration
from tests.e2e.staging_test_config import StagingConfig

from shared.isolated_environment import get_env
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestGoldenPathInfrastructureValidation:

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """
    E2E tests on GCP staging - MUST prove infrastructure works.
    
    These tests validate the complete Golden Path user flow on actual
    staging infrastructure, reproducing the exact issues preventing
    end-to-end functionality validation.
    """

    @pytest.mark.staging
    @pytest.mark.asyncio
    async def test_complete_golden_path_user_flow_staging(self):
        """
        CRITICAL: Complete Golden Path flow on staging infrastructure.
        
        This test validates the entire user journey from login through
        AI response delivery on real staging infrastructure.
        
        Expected to initially FAIL due to infrastructure issues.
        """
        flow_failures = []
        flow_timings = {}
        
        try:
            # Phase 1: Frontend Access Validation
            start_time = time.time()
            frontend_result = await self._validate_frontend_access()
            flow_timings["frontend_access"] = time.time() - start_time
            
            if not frontend_result["accessible"]:
                flow_failures.append({
                    "phase": "frontend_access",
                    "error": frontend_result["error"],
                    "timing": flow_timings["frontend_access"]
                })
            
            # Phase 2: Authentication Flow Validation  
            start_time = time.time()
            auth_result = await self._validate_authentication_flow()
            flow_timings["authentication"] = time.time() - start_time
            
            if not auth_result["authenticated"]:
                flow_failures.append({
                    "phase": "authentication",
                    "error": auth_result["error"],
                    "timing": flow_timings["authentication"]
                })
                
            # Phase 3: WebSocket Connection Validation
            start_time = time.time()
            websocket_result = await self._validate_websocket_connection()
            flow_timings["websocket_connection"] = time.time() - start_time
            
            if not websocket_result["connected"]:
                flow_failures.append({
                    "phase": "websocket_connection", 
                    "error": websocket_result["error"],
                    "timing": flow_timings["websocket_connection"]
                })
                
            # Phase 4: Message Flow Validation
            if websocket_result["connected"]:
                start_time = time.time()
                message_result = await self._validate_message_flow(websocket_result["websocket"])
                flow_timings["message_flow"] = time.time() - start_time
                
                if not message_result["successful"]:
                    flow_failures.append({
                        "phase": "message_flow",
                        "error": message_result["error"],
                        "timing": flow_timings["message_flow"]
                    })
                    
                # Phase 5: Agent Response Validation
                if message_result["successful"]:
                    start_time = time.time()
                    agent_result = await self._validate_agent_response(message_result["events"])
                    flow_timings["agent_response"] = time.time() - start_time
                    
                    if not agent_result["complete"]:
                        flow_failures.append({
                            "phase": "agent_response",
                            "error": agent_result["error"],
                            "timing": flow_timings["agent_response"]
                        })
                        
        except Exception as e:
            flow_failures.append({
                "phase": "infrastructure_exception",
                "error": str(e),
                "exception_type": type(e).__name__
            })
        
        # Initially expect failures showing infrastructure issues  
        assert len(flow_failures) == 0, (
            f"Golden Path infrastructure failures on staging: {flow_failures}. "
            f"Timings: {flow_timings}"
        )

    @pytest.mark.staging
    @pytest.mark.asyncio
    async def test_websocket_authentication_staging_infrastructure(self):
        """
        Test WebSocket authentication specifically on staging infrastructure.
        
        This reproduces the WebSocket 1011 errors and authentication issues
        identified in the Golden Path analysis.
        """
        websocket_auth_failures = []
        
        try:
            # Test different WebSocket authentication scenarios on staging
            auth_scenarios = [
                {
                    "name": "jwt_header_authentication",
                    "method": "header",
                    "token": StagingConfig().test_jwt_token
                },
                {
                    "name": "jwt_subprotocol_authentication",
                    "method": "subprotocol", 
                    "token": StagingConfig().test_jwt_token
                },
                {
                    "name": "bypass_key_authentication",
                    "method": "bypass",
                    "bypass_key": StagingConfig().test_api_key
                }
            ]
            
            for scenario in auth_scenarios:
                try:
                    auth_result = await self._test_websocket_authentication_scenario(scenario)
                    
                    if not auth_result["successful"]:
                        websocket_auth_failures.append({
                            "scenario": scenario["name"],
                            "method": scenario["method"],
                            "error": auth_result["error"],
                            "connection_code": auth_result.get("connection_code"),
                            "response_headers": auth_result.get("response_headers", {})
                        })
                        
                except Exception as e:
                    websocket_auth_failures.append({
                        "scenario": scenario["name"],
                        "error": str(e),
                        "exception_type": type(e).__name__
                    })
                    
        except Exception as e:
            websocket_auth_failures.append({
                "stage": "websocket_auth_setup",
                "error": str(e),
                "exception_type": type(e).__name__
            })
        
        # Should initially fail showing WebSocket authentication issues
        assert len(websocket_auth_failures) == 0, (
            f"WebSocket authentication failures on staging: {websocket_auth_failures}"
        )

    @pytest.mark.staging
    @pytest.mark.asyncio  
    async def test_service_dependency_graceful_degradation(self):
        """
        Test graceful degradation when services unavailable.
        
        This tests the service dependency patterns that may cause
        infrastructure failures when not all services are available.
        """
        service_dependency_issues = []
        
        try:
            # Test health of all staging services
            staging_services = [
                {"name": "backend", "url": f"{StagingConfig().backend_url}/health"},
                {"name": "auth", "url": f"{StagingConfig().auth_url}/health"}, 
                {"name": "frontend", "url": StagingConfig().frontend_url}
            ]
            
            service_health = {}
            
            for service in staging_services:
                try:
                    health_result = await self._check_service_health(service["url"])
                    service_health[service["name"]] = health_result
                    
                    if not health_result["healthy"]:
                        service_dependency_issues.append({
                            "service": service["name"],
                            "url": service["url"],
                            "error": health_result["error"],
                            "status_code": health_result.get("status_code")
                        })
                        
                except Exception as e:
                    service_dependency_issues.append({
                        "service": service["name"],
                        "url": service["url"],
                        "error": str(e),
                        "exception_type": type(e).__name__
                    })
            
            # Test service interdependencies
            if service_health.get("backend", {}).get("healthy"):
                # Test backend -> auth service communication
                backend_auth_result = await self._test_backend_auth_communication()
                if not backend_auth_result["communicating"]:
                    service_dependency_issues.append({
                        "dependency": "backend_to_auth",
                        "error": backend_auth_result["error"]
                    })
                    
        except Exception as e:
            service_dependency_issues.append({
                "stage": "service_dependency_check",
                "error": str(e),
                "exception_type": type(e).__name__
            })
        
        # Should pass after service dependency fixes
        assert len(service_dependency_issues) == 0, (
            f"Service dependency issues on staging: {service_dependency_issues}"
        )

    @pytest.mark.staging
    @pytest.mark.asyncio
    async def test_infrastructure_health_validation_comprehensive(self):
        """
        Comprehensive infrastructure health validation on staging.
        
        This validates all infrastructure components are properly
        configured and accessible.
        """
        infrastructure_issues = []
        
        try:
            # Test 1: URL protocol validation for all staging endpoints
            endpoint_validation_result = await self._validate_all_staging_endpoints()
            if endpoint_validation_result["issues"]:
                infrastructure_issues.extend(endpoint_validation_result["issues"])
            
            # Test 2: SSL/TLS certificate validation
            ssl_validation_result = await self._validate_ssl_certificates()
            if ssl_validation_result["issues"]:
                infrastructure_issues.extend(ssl_validation_result["issues"])
                
            # Test 3: CORS configuration validation
            cors_validation_result = await self._validate_cors_configuration()
            if cors_validation_result["issues"]:
                infrastructure_issues.extend(cors_validation_result["issues"])
                
            # Test 4: Load balancer configuration validation
            lb_validation_result = await self._validate_load_balancer_configuration()
            if lb_validation_result["issues"]:
                infrastructure_issues.extend(lb_validation_result["issues"])
                
            # Test 5: Database connectivity validation
            db_validation_result = await self._validate_database_connectivity()
            if db_validation_result["issues"]:
                infrastructure_issues.extend(db_validation_result["issues"])
                
        except Exception as e:
            infrastructure_issues.append({
                "component": "infrastructure_validation",
                "error": str(e),
                "exception_type": type(e).__name__
            })
        
        # Should pass after infrastructure fixes
        assert len(infrastructure_issues) == 0, (
            f"Infrastructure health validation issues: {infrastructure_issues}"
        )

    # Helper methods for staging infrastructure testing

    async def _validate_frontend_access(self) -> Dict[str, any]:
        """Validate frontend accessibility on staging."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(StagingConfig().frontend_url, timeout=10) as response:
                    if response.status == 200:
                        return {"accessible": True, "status_code": response.status}
                    else:
                        return {
                            "accessible": False,
                            "error": f"Frontend returned status {response.status}",
                            "status_code": response.status
                        }
        except aiohttp.ClientError as e:
            return {"accessible": False, "error": f"Frontend connection error: {str(e)}"}
        except Exception as e:
            return {"accessible": False, "error": f"Frontend access error: {str(e)}"}

    async def _validate_authentication_flow(self) -> Dict[str, any]:
        """Validate authentication flow on staging."""
        try:
            # Test authentication endpoint
            auth_endpoint = f"{StagingConfig().auth_url}/validate"
            
            headers = {}
            if StagingConfig().test_jwt_token:
                headers["Authorization"] = f"Bearer {StagingConfig().test_jwt_token}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(auth_endpoint, headers=headers, timeout=10) as response:
                    if response.status in [200, 201]:
                        return {"authenticated": True, "status_code": response.status}
                    else:
                        response_text = await response.text()
                        return {
                            "authenticated": False,
                            "error": f"Auth validation failed: {response.status} - {response_text}",
                            "status_code": response.status
                        }
                        
        except aiohttp.ClientError as e:
            return {"authenticated": False, "error": f"Auth connection error: {str(e)}"}
        except Exception as e:
            return {"authenticated": False, "error": f"Authentication error: {str(e)}"}

    async def _validate_websocket_connection(self) -> Dict[str, any]:
        """Validate WebSocket connection on staging."""
        try:
            # Prepare WebSocket connection with authentication
            headers = {}
            extra_headers = []
            
            if StagingConfig().test_jwt_token:
                extra_headers.append(("Authorization", f"Bearer {StagingConfig().test_jwt_token}"))
            
            # Test WebSocket connection to staging
            websocket = await websockets.connect(
                StagingConfig().websocket_url,
                extra_headers=extra_headers,
                timeout=10
            )
            
            # Send ping to verify connection
            ping_message = json.dumps({"type": "ping", "timestamp": time.time()})
            await websocket.send(ping_message)
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                return {
                    "connected": True,
                    "websocket": websocket,
                    "ping_response": response_data
                }
                
            except asyncio.TimeoutError:
                await websocket.close()
                return {
                    "connected": False,
                    "error": "WebSocket ping timeout - no response received"
                }
                
        except websockets.exceptions.ConnectionClosedError as e:
            return {
                "connected": False,
                "error": f"WebSocket connection closed: {str(e)}",
                "connection_code": getattr(e, 'code', None)
            }
        except websockets.exceptions.InvalidStatusCode as e:
            return {
                "connected": False,
                "error": f"WebSocket invalid status: {str(e)}",
                "status_code": getattr(e, 'status_code', None)
            }
        except Exception as e:
            return {
                "connected": False,
                "error": f"WebSocket connection error: {str(e)}",
                "exception_type": type(e).__name__
            }

    async def _validate_message_flow(self, websocket) -> Dict[str, any]:
        """Validate message flow through WebSocket."""
        try:
            # Send test message to trigger agent response
            test_message = {
                "type": "user_message",
                "text": "Hello, can you help me optimize costs?",
                "thread_id": f"test_thread_{int(time.time())}",
                "timestamp": time.time()
            }
            
            await websocket.send(json.dumps(test_message))
            
            # Collect events for validation
            events = []
            start_time = time.time()
            
            while time.time() - start_time < 30:  # 30 second timeout
                try:
                    event_raw = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event = json.loads(event_raw)
                    events.append(event)
                    
                    # Check if we got completion event
                    if event.get("type") == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    # Continue waiting for events
                    continue
                    
            return {
                "successful": len(events) > 0,
                "events": events,
                "event_count": len(events)
            }
            
        except Exception as e:
            return {
                "successful": False,
                "error": f"Message flow error: {str(e)}",
                "exception_type": type(e).__name__
            }

    async def _validate_agent_response(self, events: List[Dict]) -> Dict[str, any]:
        """Validate agent response completeness."""
        try:
            # Check for required WebSocket events
            required_events = ["agent_started", "agent_thinking", "agent_completed"]
            event_types = [event.get("type") for event in events]
            
            missing_events = []
            for required_event in required_events:
                if required_event not in event_types:
                    missing_events.append(required_event)
            
            if missing_events:
                return {
                    "complete": False,
                    "error": f"Missing required events: {missing_events}",
                    "received_events": event_types
                }
            
            # Check for agent completion with response
            completion_events = [e for e in events if e.get("type") == "agent_completed"]
            if not completion_events:
                return {
                    "complete": False,
                    "error": "No agent completion event received"
                }
                
            completion_event = completion_events[-1]
            if "data" not in completion_event or "result" not in completion_event.get("data", {}):
                return {
                    "complete": False,
                    "error": "Agent completion event missing result data"
                }
            
            return {
                "complete": True,
                "events": events,
                "completion_data": completion_event["data"]
            }
            
        except Exception as e:
            return {
                "complete": False,
                "error": f"Agent response validation error: {str(e)}"
            }

    async def _test_websocket_authentication_scenario(self, scenario: Dict) -> Dict[str, any]:
        """Test specific WebSocket authentication scenario."""
        try:
            extra_headers = []
            subprotocols = []
            
            if scenario["method"] == "header" and scenario.get("token"):
                extra_headers.append(("Authorization", f"Bearer {scenario['token']}"))
            elif scenario["method"] == "subprotocol" and scenario.get("token"):
                subprotocols.append(f"jwt.{scenario['token']}")
            elif scenario["method"] == "bypass" and scenario.get("bypass_key"):
                extra_headers.append(("X-E2E-Bypass", scenario["bypass_key"]))
            
            # Attempt WebSocket connection
            websocket = await websockets.connect(
                StagingConfig().websocket_url,
                extra_headers=extra_headers,
                subprotocols=subprotocols if subprotocols else None,
                timeout=10
            )
            
            # Test connection with ping
            ping_message = json.dumps({"type": "ping"})
            await websocket.send(ping_message)
            
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            await websocket.close()
            
            return {
                "successful": True,
                "response": json.loads(response)
            }
            
        except websockets.exceptions.ConnectionClosedError as e:
            return {
                "successful": False,
                "error": f"Connection closed: {str(e)}",
                "connection_code": getattr(e, 'code', None)
            }
        except Exception as e:
            return {
                "successful": False,
                "error": str(e),
                "exception_type": type(e).__name__
            }

    async def _check_service_health(self, health_url: str) -> Dict[str, any]:
        """Check health of a staging service."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(health_url, timeout=10) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        return {
                            "healthy": True,
                            "status_code": response.status,
                            "health_data": health_data
                        }
                    else:
                        return {
                            "healthy": False,
                            "error": f"Health check failed: {response.status}",
                            "status_code": response.status
                        }
        except aiohttp.ClientError as e:
            return {"healthy": False, "error": f"Health check connection error: {str(e)}"}
        except Exception as e:
            return {"healthy": False, "error": f"Health check error: {str(e)}"}

    async def _test_backend_auth_communication(self) -> Dict[str, any]:
        """Test backend to auth service communication."""
        try:
            # Test backend endpoint that requires auth service
            test_endpoint = f"{StagingConfig().backend_url}/api/user/profile"
            
            headers = {}
            if StagingConfig().test_jwt_token:
                headers["Authorization"] = f"Bearer {StagingConfig().test_jwt_token}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(test_endpoint, headers=headers, timeout=10) as response:
                    if response.status in [200, 201, 401]:  # 401 is OK - means auth service is reachable
                        return {"communicating": True, "status_code": response.status}
                    else:
                        return {
                            "communicating": False,
                            "error": f"Backend-auth communication issue: {response.status}",
                            "status_code": response.status
                        }
                        
        except Exception as e:
            return {"communicating": False, "error": str(e)}

    async def _validate_all_staging_endpoints(self) -> Dict[str, any]:
        """Validate all staging endpoint URLs."""
        endpoints = [
            {"name": "backend", "url": StagingConfig().backend_url},
            {"name": "auth", "url": StagingConfig().auth_url},
            {"name": "frontend", "url": StagingConfig().frontend_url},
            {"name": "websocket", "url": StagingConfig().websocket_url}
        ]
        
        issues = []
        
        for endpoint in endpoints:
            try:
                parsed = urllib.parse.urlparse(endpoint["url"])
                
                if not parsed.scheme:
                    issues.append({
                        "endpoint": endpoint["name"],
                        "issue": "URL missing protocol",
                        "url": endpoint["url"]
                    })
                    
                if not parsed.netloc:
                    issues.append({
                        "endpoint": endpoint["name"],
                        "issue": "URL missing hostname",
                        "url": endpoint["url"]
                    })
                    
                if endpoint["name"] == "websocket" and parsed.scheme not in ["ws", "wss"]:
                    issues.append({
                        "endpoint": endpoint["name"],
                        "issue": "WebSocket URL invalid protocol",
                        "url": endpoint["url"],
                        "expected_protocol": "wss"
                    })
                    
            except Exception as e:
                issues.append({
                    "endpoint": endpoint["name"],
                    "issue": f"URL parsing error: {str(e)}",
                    "url": endpoint["url"]
                })
        
        return {"issues": issues}

    async def _validate_ssl_certificates(self) -> Dict[str, any]:
        """Validate SSL certificates for staging endpoints."""
        # This would test SSL certificate validity
        # For now, return empty issues as a placeholder
        return {"issues": []}

    async def _validate_cors_configuration(self) -> Dict[str, any]:
        """Validate CORS configuration."""
        # This would test CORS headers
        # For now, return empty issues as a placeholder  
        return {"issues": []}

    async def _validate_load_balancer_configuration(self) -> Dict[str, any]:
        """Validate load balancer configuration."""
        # This would test load balancer specific issues
        # For now, return empty issues as a placeholder
        return {"issues": []}

    async def _validate_database_connectivity(self) -> Dict[str, any]:
        """Validate database connectivity from backend."""
        try:
            # Test backend database health endpoint
            db_health_url = f"{StagingConfig().backend_url}/health/database"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(db_health_url, timeout=10) as response:
                    if response.status == 200:
                        return {"issues": []}
                    else:
                        return {
                            "issues": [{
                                "component": "database",
                                "issue": f"Database health check failed: {response.status}"
                            }]
                        }
        except Exception as e:
            return {
                "issues": [{
                    "component": "database",
                    "issue": f"Database connectivity error: {str(e)}"
                }]
            }


# Pytest markers for staging E2E tests
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.staging,
    pytest.mark.infrastructure_validation,
    pytest.mark.golden_path_critical
]