
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
E2E Staging Tests: Golden Path Event Validation SSOT Testing

PURPOSE: Test EventValidator SSOT consolidation in staging GCP environment
EXPECTATION: Tests should FAIL initially to demonstrate staging environment validation issues

Business Value Justification (BVJ):
- Segment: Platform/Internal - E2E Staging Validation
- Business Goal: Revenue Protection - Ensure staging mirrors production validation
- Value Impact: Protects $500K+ ARR by validating staging environment consistency
- Strategic Impact: Validates deployment-ready SSOT consolidation

These tests are designed to FAIL initially, demonstrating:
1. Staging environment still using multiple validators
2. Golden path event validation inconsistencies in staging
3. Staging WebSocket event delivery conflicts
4. Staging agent execution validation differences

Test Plan Phase 3: E2E Staging Tests (GCP Remote Environment)
- Test golden path event validation in staging
- Test staging WebSocket integration with multiple validators
- Test staging agent execution event consistency
- Test staging deployment validation readiness

NOTE: Uses real staging GCP environment without Docker dependencies
"""

import pytest
import asyncio
import aiohttp
import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from unittest.mock import patch, AsyncMock

# Import test framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import staging environment utilities
from shared.isolated_environment import get_env
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestGoldenPathEventValidationStaging(SSotAsyncTestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.from_request(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """
    E2E staging tests for EventValidator SSOT consolidation in GCP environment.
    
    DESIGNED TO FAIL: These tests expose validation inconsistencies in the staging
    environment that indicate incomplete SSOT consolidation deployment.
    """
    
    async def asyncSetUp(self):
        """Set up test fixtures for staging environment testing."""
        await super().asyncSetUp()
        
        # Get staging environment configuration
        self.env = get_env()
        
        # Staging environment endpoints
        self.staging_base_url = self._get_staging_base_url()
        self.staging_websocket_url = self._get_staging_websocket_url()
        
        # Skip tests if staging environment not available
        if not self.staging_base_url:
            pytest.skip("Staging environment not configured")
        
        # Test user and session data for staging
        self.staging_user_id = f"staging-user-{uuid.uuid4().hex[:8]}"
        self.staging_session_token = await self._create_staging_session()
        self.staging_thread_id = f"staging-thread-{uuid.uuid4().hex[:8]}"
        
        # Golden path event sequence for testing
        self.golden_path_events = self._create_golden_path_event_sequence()
        
        # Track validation results across different staging endpoints
        self.staging_validation_results = {}
    
    async def asyncTearDown(self):
        """Clean up staging test fixtures."""
        await super().asyncTearDown()
        
        # Clean up staging session if created
        if hasattr(self, "staging_session_token") and self.staging_session_token:
            await self._cleanup_staging_session()
    
    def _get_staging_base_url(self) -> Optional[str]:
        """Get staging environment base URL."""
        try:
            # Common staging URL patterns
            staging_urls = [
                self.env.get("STAGING_BASE_URL"),
                self.env.get("GCP_STAGING_URL"),
                "https://netra-staging.example.com",  # Replace with actual staging URL
                "https://staging-api.netra.dev"  # Replace with actual staging URL
            ]
            
            for url in staging_urls:
                if url and url.startswith("http"):
                    return url.rstrip("/")
            
            return None
        except Exception:
            return None
    
    def _get_staging_websocket_url(self) -> Optional[str]:
        """Get staging WebSocket URL."""
        base_url = self.staging_base_url
        if base_url:
            return base_url.replace("https://", "wss://").replace("http://", "ws://") + "/ws"
        return None
    
    async def _create_staging_session(self) -> Optional[str]:
        """Create a staging session for testing."""
        if not self.staging_base_url:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                # Attempt to create staging session
                auth_data = {
                    "user_id": self.staging_user_id,
                    "test_session": True,
                    "environment": "staging_test"
                }
                
                async with session.post(
                    f"{self.staging_base_url}/auth/test-session",
                    json=auth_data,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("session_token")
                    else:
                        # Fallback to mock session token
                        return f"staging-test-token-{uuid.uuid4().hex[:16]}"
        except Exception:
            # Fallback to mock session token
            return f"staging-test-token-{uuid.uuid4().hex[:16]}"
    
    async def _cleanup_staging_session(self):
        """Clean up staging session."""
        if not self.staging_base_url or not self.staging_session_token:
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                await session.delete(
                    f"{self.staging_base_url}/auth/session/{self.staging_session_token}",
                    timeout=5
                )
        except Exception:
            pass  # Cleanup failure is not critical
    
    def _create_golden_path_event_sequence(self) -> List[Dict[str, Any]]:
        """Create golden path event sequence for staging testing."""
        base_time = datetime.now(timezone.utc)
        run_id = f"staging-golden-{uuid.uuid4().hex[:8]}"
        
        return [
            {
                "type": "agent_started",
                "run_id": run_id,
                "agent_name": "supervisor-agent",
                "user_id": self.staging_user_id,
                "thread_id": self.staging_thread_id,
                "timestamp": base_time.isoformat(),
                "payload": {
                    "agent": "supervisor-agent",
                    "status": "started",
                    "workflow": "golden_path_test",
                    "environment": "staging"
                }
            },
            {
                "type": "agent_thinking",
                "run_id": run_id,
                "agent_name": "supervisor-agent",
                "user_id": self.staging_user_id,
                "thread_id": self.staging_thread_id,
                "timestamp": (base_time + timedelta(seconds=2)).isoformat(),
                "payload": {
                    "agent": "supervisor-agent",
                    "progress": "analyzing_request",
                    "reasoning": "Processing golden path test request"
                }
            },
            {
                "type": "tool_executing",
                "run_id": run_id,
                "agent_name": "supervisor-agent",
                "user_id": self.staging_user_id,
                "thread_id": self.staging_thread_id,
                "timestamp": (base_time + timedelta(seconds=5)).isoformat(),
                "payload": {
                    "tool": "staging-test-tool",
                    "status": "executing",
                    "operation": "golden_path_validation"
                }
            },
            {
                "type": "tool_completed",
                "run_id": run_id,
                "agent_name": "supervisor-agent",
                "user_id": self.staging_user_id,
                "thread_id": self.staging_thread_id,
                "timestamp": (base_time + timedelta(seconds=10)).isoformat(),
                "payload": {
                    "tool": "staging-test-tool",
                    "status": "completed",
                    "result": "golden_path_success"
                }
            },
            {
                "type": "agent_completed",
                "run_id": run_id,
                "agent_name": "supervisor-agent",
                "user_id": self.staging_user_id,
                "thread_id": self.staging_thread_id,
                "timestamp": (base_time + timedelta(seconds=12)).isoformat(),
                "payload": {
                    "agent": "supervisor-agent",
                    "status": "completed",
                    "result": "golden_path_test_completed"
                }
            }
        ]
    
    async def test_staging_event_validator_endpoint_consistency(self):
        """
        TEST DESIGNED TO FAIL: Should expose multiple event validation endpoints in staging.
        
        Expected failure: Staging environment may have multiple validation endpoints
        using different EventValidator implementations.
        """
        validation_endpoints = [
            "/api/validate-event",  # Potential unified validator endpoint
            "/api/websocket/validate",  # Potential WebSocket validator endpoint
            "/api/events/validate",  # Potential legacy validator endpoint
            "/internal/event-validation"  # Potential internal validator endpoint
        ]
        
        endpoint_responses = {}
        
        # Test each potential validation endpoint
        for endpoint in validation_endpoints:
            if not self.staging_base_url:
                continue
                
            try:
                async with aiohttp.ClientSession() as session:
                    test_event = self.golden_path_events[0]  # Use first event for testing
                    
                    headers = {
                        "Authorization": f"Bearer {self.staging_session_token}",
                        "Content-Type": "application/json"
                    }
                    
                    payload = {
                        "event": test_event,
                        "user_id": self.staging_user_id,
                        "test_mode": True
                    }
                    
                    async with session.post(
                        f"{self.staging_base_url}{endpoint}",
                        json=payload,
                        headers=headers,
                        timeout=10
                    ) as response:
                        endpoint_responses[endpoint] = {
                            "status": response.status,
                            "headers": dict(response.headers),
                            "available": True
                        }
                        
                        if response.status == 200:
                            try:
                                data = await response.json()
                                endpoint_responses[endpoint]["response_data"] = data
                            except Exception:
                                endpoint_responses[endpoint]["response_data"] = await response.text()
                        else:
                            endpoint_responses[endpoint]["response_data"] = await response.text()
                            
            except aiohttp.ClientError:
                endpoint_responses[endpoint] = {"available": False, "error": "connection_failed"}
            except Exception as e:
                endpoint_responses[endpoint] = {"available": False, "error": str(e)}
        
        # Check for multiple available validation endpoints - this should FAIL initially
        available_endpoints = [
            endpoint for endpoint, response in endpoint_responses.items()
            if response.get("available") and response.get("status") in [200, 400, 422]  # 400/422 might indicate endpoint exists but validation failed
        ]
        
        if len(available_endpoints) > 1:
            self.fail(
                f"STAGING SSOT VIOLATION: Multiple event validation endpoints found: {available_endpoints}. "
                f"Endpoint responses: {endpoint_responses}. "
                f"Staging environment should have single unified validation endpoint!"
            )
        
        # If endpoints return validation results, check for consistency
        validation_results = {}
        for endpoint, response in endpoint_responses.items():
            if response.get("status") == 200 and "response_data" in response:
                data = response["response_data"]
                if isinstance(data, dict) and "is_valid" in data:
                    validation_results[endpoint] = {
                        "is_valid": data["is_valid"],
                        "error_message": data.get("error_message"),
                        "validator_type": data.get("validator_type"),
                        "validator_version": data.get("validator_version")
                    }
        
        if len(validation_results) > 1:
            # Check for validation result consistency
            is_valid_values = [result["is_valid"] for result in validation_results.values()]
            validator_types = [result.get("validator_type") for result in validation_results.values()]
            
            if len(set(is_valid_values)) > 1:
                self.fail(
                    f"STAGING VALIDATION INCONSISTENCY: Different endpoints return different validation results: "
                    f"{validation_results}. "
                    f"Same event should produce consistent validation across all endpoints!"
                )
            
            if len(set(validator_types)) > 1:
                self.fail(
                    f"STAGING VALIDATOR TYPE INCONSISTENCY: Different endpoints use different validator types: "
                    f"{dict(zip(validation_results.keys(), validator_types))}. "
                    f"All endpoints should use the unified EventValidator!"
                )
    
    async def test_staging_websocket_event_validation_golden_path(self):
        """
        TEST DESIGNED TO FAIL: Should expose WebSocket event validation inconsistencies in staging.
        
        Expected failure: Staging WebSocket implementation may use different validators
        or validation logic compared to REST endpoints.
        """
        if not self.staging_websocket_url:
            self.skipTest("Staging WebSocket URL not available")
        
        websocket_validation_results = {}
        
        try:
            import websockets
            
            # Connect to staging WebSocket
            headers = {
                "Authorization": f"Bearer {self.staging_session_token}"
            }
            
            async with websockets.connect(
                self.staging_websocket_url,
                extra_headers=headers,
                timeout=10
            ) as websocket:
                
                # Send each golden path event and monitor responses
                for event_idx, event in enumerate(self.golden_path_events):
                    # Send event
                    message = {
                        "action": "emit_event",
                        "event": event,
                        "user_id": self.staging_user_id,
                        "connection_id": f"test-conn-{uuid.uuid4().hex[:8]}"
                    }
                    
                    await websocket.send(json.dumps(message))
                    
                    # Wait for response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response)
                        
                        websocket_validation_results[f"event_{event_idx}"] = {
                            "event_type": event["type"],
                            "sent_successfully": True,
                            "response": response_data,
                            "validation_status": response_data.get("validation_status"),
                            "error_message": response_data.get("error_message")
                        }
                        
                    except asyncio.TimeoutError:
                        websocket_validation_results[f"event_{event_idx}"] = {
                            "event_type": event["type"],
                            "sent_successfully": True,
                            "response": None,
                            "error": "timeout_waiting_for_response"
                        }
                    except Exception as e:
                        websocket_validation_results[f"event_{event_idx}"] = {
                            "event_type": event["type"],
                            "sent_successfully": True,
                            "response": None,
                            "error": str(e)
                        }
                    
                    # Small delay between events
                    await asyncio.sleep(0.5)
        
        except ImportError:
            self.skipTest("websockets library not available")
        except Exception as e:
            websocket_validation_results["connection_error"] = str(e)
        
        # Analyze WebSocket validation results
        if "connection_error" in websocket_validation_results:
            self.fail(
                f"STAGING WEBSOCKET CONNECTION FAILED: {websocket_validation_results['connection_error']}. "
                f"Cannot test WebSocket event validation in staging environment!"
            )
        
        # Check for validation failures in golden path
        validation_failures = []
        timeout_failures = []
        
        for event_key, result in websocket_validation_results.items():
            if "error" in result:
                if "timeout" in result["error"]:
                    timeout_failures.append(event_key)
                else:
                    validation_failures.append({
                        "event": event_key,
                        "error": result["error"]
                    })
            elif result.get("validation_status") == "failed":
                validation_failures.append({
                    "event": event_key,
                    "validation_error": result.get("error_message")
                })
        
        if validation_failures:
            self.fail(
                f"STAGING WEBSOCKET VALIDATION FAILURES: Golden path events failed validation: "
                f"{validation_failures}. "
                f"Full results: {websocket_validation_results}. "
                f"Golden path should validate successfully in staging!"
            )
        
        if timeout_failures:
            self.fail(
                f"STAGING WEBSOCKET TIMEOUT FAILURES: Events timed out waiting for response: "
                f"{timeout_failures}. "
                f"This indicates potential validation processing issues in staging!"
            )
    
    async def test_staging_agent_execution_event_validation_consistency(self):
        """
        TEST DESIGNED TO FAIL: Should expose agent execution validation inconsistencies in staging.
        
        Expected failure: Staging agent execution may use different event validation
        compared to direct event validation endpoints.
        """
        if not self.staging_base_url:
            self.skipTest("Staging base URL not available")
        
        agent_execution_results = {}
        
        try:
            # Trigger agent execution in staging
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.staging_session_token}",
                    "Content-Type": "application/json"
                }
                
                agent_request = {
                    "user_id": self.staging_user_id,
                    "thread_id": self.staging_thread_id,
                    "message": "Execute golden path test for event validation",
                    "agent_type": "supervisor",
                    "test_mode": True,
                    "validate_events": True
                }
                
                # Start agent execution
                async with session.post(
                    f"{self.staging_base_url}/api/agents/execute",
                    json=agent_request,
                    headers=headers,
                    timeout=30
                ) as response:
                    
                    if response.status == 200:
                        execution_data = await response.json()
                        execution_id = execution_data.get("execution_id")
                        
                        agent_execution_results["execution_started"] = {
                            "success": True,
                            "execution_id": execution_id,
                            "response": execution_data
                        }
                        
                        # Monitor execution progress and event validation
                        if execution_id:
                            await self._monitor_staging_execution_events(
                                session, headers, execution_id, agent_execution_results
                            )
                    else:
                        agent_execution_results["execution_started"] = {
                            "success": False,
                            "status": response.status,
                            "error": await response.text()
                        }
                        
        except Exception as e:
            agent_execution_results["execution_error"] = str(e)
        
        # Analyze agent execution event validation
        if not agent_execution_results.get("execution_started", {}).get("success"):
            self.fail(
                f"STAGING AGENT EXECUTION FAILED: Cannot test event validation during agent execution. "
                f"Execution results: {agent_execution_results}. "
                f"Staging environment should support agent execution testing!"
            )
        
        # Check for event validation issues during execution
        execution_events = agent_execution_results.get("execution_events", [])
        event_validation_issues = []
        
        for event in execution_events:
            if event.get("validation_failed"):
                event_validation_issues.append({
                    "event_type": event.get("event_type"),
                    "validation_error": event.get("validation_error"),
                    "timestamp": event.get("timestamp")
                })
        
        if event_validation_issues:
            self.fail(
                f"STAGING AGENT EXECUTION EVENT VALIDATION FAILURES: "
                f"{event_validation_issues}. "
                f"Full execution results: {agent_execution_results}. "
                f"Agent execution should not have event validation failures in staging!"
            )
        
        # Check for missing critical events during execution
        critical_event_types = {"agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"}
        received_event_types = {event.get("event_type") for event in execution_events}
        missing_critical_events = critical_event_types - received_event_types
        
        if missing_critical_events:
            self.fail(
                f"STAGING CRITICAL EVENTS MISSING: Agent execution missing critical events: "
                f"{missing_critical_events}. "
                f"Received events: {received_event_types}. "
                f"All critical events should be emitted during agent execution!"
            )
    
    async def _monitor_staging_execution_events(self, session, headers, execution_id, results):
        """Monitor staging agent execution for event validation analysis."""
        try:
            # Poll execution status and events
            for _ in range(10):  # Poll for up to 10 iterations
                async with session.get(
                    f"{self.staging_base_url}/api/agents/execution/{execution_id}/events",
                    headers=headers,
                    timeout=10
                ) as response:
                    
                    if response.status == 200:
                        events_data = await response.json()
                        events = events_data.get("events", [])
                        
                        results["execution_events"] = events
                        results["total_events"] = len(events)
                        
                        # Check if execution completed
                        completed_events = [e for e in events if e.get("event_type") == "agent_completed"]
                        if completed_events:
                            break
                    
                    await asyncio.sleep(2)  # Wait 2 seconds between polls
                    
        except Exception as e:
            results["monitoring_error"] = str(e)
    
    async def test_staging_deployment_validator_readiness(self):
        """
        TEST DESIGNED TO FAIL: Should expose staging deployment readiness issues.
        
        Expected failure: Staging deployment may not be ready for unified validator,
        indicating incomplete SSOT consolidation deployment.
        """
        if not self.staging_base_url:
            self.skipTest("Staging base URL not available")
        
        deployment_readiness = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                # Check deployment health endpoint
                async with session.get(
                    f"{self.staging_base_url}/health",
                    timeout=10
                ) as response:
                    
                    deployment_readiness["health_check"] = {
                        "status": response.status,
                        "available": response.status == 200
                    }
                    
                    if response.status == 200:
                        health_data = await response.json()
                        deployment_readiness["health_data"] = health_data
                        
                        # Look for validator-related health information
                        validator_health = health_data.get("event_validator", {})
                        deployment_readiness["validator_health"] = validator_health
                
                # Check for API version and validator information
                async with session.get(
                    f"{self.staging_base_url}/api/version",
                    timeout=10
                ) as response:
                    
                    if response.status == 200:
                        version_data = await response.json()
                        deployment_readiness["version_info"] = version_data
                        
                        # Look for validator version information
                        validator_version = version_data.get("event_validator_version")
                        validator_type = version_data.get("event_validator_type")
                        
                        deployment_readiness["validator_deployment"] = {
                            "version": validator_version,
                            "type": validator_type,
                            "unified_deployed": validator_type == "unified" if validator_type else False
                        }
                
        except Exception as e:
            deployment_readiness["error"] = str(e)
        
        # Analyze deployment readiness
        if "error" in deployment_readiness:
            self.fail(
                f"STAGING DEPLOYMENT CHECK FAILED: Cannot assess deployment readiness: "
                f"{deployment_readiness['error']}. "
                f"Staging environment should be accessible for deployment validation!"
            )
        
        # Check health status
        if not deployment_readiness.get("health_check", {}).get("available"):
            self.fail(
                f"STAGING HEALTH CHECK FAILED: Staging environment not healthy. "
                f"Health check: {deployment_readiness.get('health_check')}. "
                f"Staging must be healthy for SSOT validator deployment!"
            )
        
        # Check validator deployment status
        validator_deployment = deployment_readiness.get("validator_deployment", {})
        if not validator_deployment.get("unified_deployed"):
            validator_type = validator_deployment.get("type", "unknown")
            self.fail(
                f"STAGING VALIDATOR DEPLOYMENT INCOMPLETE: Staging using '{validator_type}' validator "
                f"instead of unified validator. "
                f"Deployment readiness: {deployment_readiness}. "
                f"Staging should be deployed with unified EventValidator for SSOT consolidation!"
            )
        
        # Check for validator health issues
        validator_health = deployment_readiness.get("validator_health", {})
        if isinstance(validator_health, dict):
            validator_errors = validator_health.get("errors", [])
            validator_warnings = validator_health.get("warnings", [])
            
            if validator_errors:
                self.fail(
                    f"STAGING VALIDATOR HEALTH ERRORS: {validator_errors}. "
                    f"Full validator health: {validator_health}. "
                    f"Staging validator must be error-free for production deployment!"
                )
            
            if validator_warnings:
                # Warnings might be acceptable, but log them
                deployment_readiness["validator_warnings"] = validator_warnings


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])