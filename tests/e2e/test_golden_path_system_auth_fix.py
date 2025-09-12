
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
Golden Path System Authentication Fix E2E Tests for GitHub Issue #115

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Validate complete golden path user flow restoration
- Value Impact: Golden path delivers core business value through AI agents
- Strategic Impact: End-to-end business functionality validation on staging

CRITICAL: These E2E tests validate golden path restoration on GCP staging.
They MUST PASS after implementing service authentication fix.

This test suite follows CLAUDE.md requirements:
- ALL e2e tests MUST use real authentication (JWT/OAuth) per CLAUDE.md Section 7.4
- NO MOCKS in e2e tests (forbidden per CLAUDE.md)
- Real services, real staging environment, real WebSocket connections
- Uses SSOT E2E auth helper for proper authentication patterns
"""

import pytest
import asyncio
import aiohttp
import websockets
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    E2EWebSocketAuthHelper,
    create_test_user_with_auth,
    create_authenticated_user
)
from tests.e2e.staging_config import StagingTestConfig
from shared.isolated_environment import get_env
from netra_backend.app.services.user_execution_context import UserExecutionContext

logger = logging.getLogger(__name__)

class TestGoldenPathSystemAuthFix(SSotBaseTestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """
    E2E Tests: Validate golden path restoration with fixed system authentication.
    
    These tests run on GCP staging environment and validate that:
    1. Complete golden path user flow works end-to-end
    2. System user authentication no longer blocks internal operations  
    3. WebSocket agent events work with proper authentication context
    4. Database sessions create successfully with service authentication
    5. Business value delivery is restored
    
    CRITICAL: These tests should PASS after implementing service authentication fix.
    """

    def setup_method(self, method):
        """Set up staging environment for golden path E2E testing."""
        super().setup_method(method)
        self.env = get_env()
        
        # Use staging environment for E2E tests
        self.environment = "staging"
        self.staging_config = StagingTestConfig()
        
        # Initialize E2E auth helpers
        self.auth_helper = E2EAuthHelper(environment=self.environment)
        self.websocket_helper = E2EWebSocketAuthHelper(environment=self.environment)
        
        logger.info(f"[U+1F310] GOLDEN PATH E2E TEST: {method.__name__}")
        logger.info(f"Environment: {self.environment}")
        logger.info(f"Backend URL: {self.staging_config.urls.backend_url}")
        logger.info(f"WebSocket URL: {self.staging_config.urls.websocket_url}")

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.golden_path
    async def test_golden_path_with_fixed_authentication(self):
        """
        Test complete golden path user flow works with fixed system authentication.
        
        EXPECTED: This test should PASS after service auth implementation
        VALIDATES: End-to-end business value delivery restored on staging
        """
        logger.info("[U+1F680] GOLDEN PATH E2E: Testing complete user flow with fixed auth")
        
        # Create authenticated user using SSOT patterns
        user_token, user_data = await create_authenticated_user(
            environment=self.environment,
            permissions=["read", "write", "agent_execution"]
        )
        
        user_id = user_data["id"]
        
        async with aiohttp.ClientSession() as session:
            # Test complete golden path flow
            test_url = f"{self.staging_config.urls.backend_url}/api/chat/start-conversation"
            headers = {
                "Authorization": f"Bearer {user_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "message": "Analyze my costs and provide optimization recommendations",
                "agent_type": "cost_optimizer", 
                "user_id": user_id,
                "thread_id": f"golden_path_test_{int(datetime.now().timestamp())}"
            }
            
            try:
                # Golden path should complete successfully with fixed auth
                async with session.post(test_url, headers=headers, json=data, timeout=30) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        response_data = await response.json() if response.content_type == 'application/json' else {}
                        
                        logger.info(" PASS:  GOLDEN PATH SUCCESS: End-to-end flow completed")
                        logger.info(f"Response includes: {list(response_data.keys())}")
                        
                        # Validate business value indicators
                        self._validate_golden_path_business_value(response_data, response_text)
                        return
                        
                    elif response.status in [500, 503]:
                        # Check for system auth issues (should be resolved)
                        system_auth_errors = [
                            "system_user_auth_failure", "system user failed authentication",
                            "not authenticated", "database session", "session factory"
                        ]
                        
                        if any(error in response_text.lower() for error in system_auth_errors):
                            pytest.fail(
                                f"GOLDEN PATH FAILED: System authentication issues persist. "
                                f"Status: {response.status}, Response: {response_text}. "
                                f"Service authentication fix may be incomplete or not deployed to staging."
                            )
                        else:
                            pytest.fail(
                                f"GOLDEN PATH FAILED: Non-auth error in golden path. "
                                f"Status: {response.status}, Response: {response_text}"
                            )
                    elif response.status in [401, 403]:
                        pytest.fail(
                            f"GOLDEN PATH FAILED: Authentication issues in golden path. "
                            f"Status: {response.status}, Response: {response_text}. "
                            f"Check if user authentication is working properly."
                        )
                    else:
                        pytest.fail(
                            f"GOLDEN PATH FAILED: Unexpected error. "
                            f"Status: {response.status}, Response: {response_text}"
                        )
                        
            except asyncio.TimeoutError:
                pytest.fail(
                    "GOLDEN PATH FAILED: Request timed out. This may indicate "
                    "system authentication issues still preventing completion."
                )
            except Exception as e:
                pytest.fail(f"GOLDEN PATH FAILED: Unexpected error: {e}")

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.websocket
    async def test_websocket_agent_events_with_authenticated_system_user(self):
        """
        Test WebSocket agent events work with authenticated system user context.
        
        EXPECTED: This test should PASS after service auth implementation
        VALIDATES: WebSocket events delivered with proper system user authentication
        """
        logger.info("[U+1F50C] WEBSOCKET E2E: Testing agent events with authenticated system user")
        
        try:
            # Create authenticated WebSocket connection
            websocket = await self.websocket_helper.connect_authenticated_websocket(timeout=15.0)
            
            # Send agent execution request
            request_data = {
                "type": "agent_request",
                "agent": "triage_agent", 
                "message": "Test system user authentication for WebSocket events",
                "user_id": f"e2e_websocket_test_{int(datetime.now().timestamp())}",
                "thread_id": f"websocket_test_thread_{int(datetime.now().timestamp())}"
            }
            
            await websocket.send(json.dumps(request_data))
            logger.info("[U+1F4E4] Sent agent request via WebSocket")
            
            # Collect WebSocket events
            events_received = []
            start_time = datetime.now()
            timeout_seconds = 25.0
            
            while True:
                try:
                    # Wait for WebSocket message with timeout
                    remaining_time = timeout_seconds - (datetime.now() - start_time).total_seconds()
                    if remaining_time <= 0:
                        break
                        
                    message = await asyncio.wait_for(websocket.recv(), timeout=remaining_time)
                    event_data = json.loads(message)
                    events_received.append(event_data)
                    
                    logger.info(f"[U+1F4E8] Received WebSocket event: {event_data.get('type', 'unknown')}")
                    
                    # Check if agent execution completed
                    if event_data.get("type") == "agent_completed":
                        logger.info(" PASS:  Agent execution completed")
                        break
                        
                except asyncio.TimeoutError:
                    logger.warning("[U+23F0] WebSocket timeout waiting for more events")
                    break
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("[U+1F50C] WebSocket connection closed")
                    break
                    
            await websocket.close()
            
            # Validate WebSocket events received
            if not events_received:
                pytest.fail(
                    "WEBSOCKET E2E FAILED: No WebSocket events received. "
                    "This may indicate system user authentication is still blocking agent execution."
                )
            
            # Validate critical agent events are present
            event_types = [event.get("type") for event in events_received]
            required_events = ["agent_started"]  # Minimum required
            
            missing_events = [event for event in required_events if event not in event_types]
            if missing_events:
                pytest.fail(
                    f"WEBSOCKET E2E FAILED: Missing required WebSocket events: {missing_events}. "
                    f"Received events: {event_types}. "
                    f"This may indicate system user authentication issues preventing agent execution."
                )
            
            logger.info(f" PASS:  WEBSOCKET E2E SUCCESS: Received {len(events_received)} events: {event_types}")
            
        except Exception as e:
            pytest.fail(f"WEBSOCKET E2E FAILED: Error in WebSocket agent events test: {e}")

    @pytest.mark.e2e
    @pytest.mark.staging  
    @pytest.mark.database
    async def test_database_operations_with_system_user_authentication(self):
        """
        Test database operations work with system user service authentication.
        
        EXPECTED: This test should PASS after service auth implementation
        VALIDATES: Database sessions create successfully with service authentication
        """
        logger.info("[U+1F5C4][U+FE0F] DATABASE E2E: Testing database operations with system user auth")
        
        # Create authenticated user
        auth_result = await create_test_user_with_auth(
            email="database_test@example.com",
            environment=self.environment,
            permissions=["read", "write"]
        )
        
        user_token = auth_result["jwt_token"]
        
        async with aiohttp.ClientSession() as session:
            # Test database operation that requires system user authentication
            test_url = f"{self.staging_config.urls.backend_url}/api/threads/create"
            headers = {
                "Authorization": f"Bearer {user_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "title": "Test Database Operations with System Auth",
                "description": "Testing database session creation with fixed system user authentication"
            }
            
            try:
                async with session.post(test_url, headers=headers, json=data, timeout=15) as response:
                    response_text = await response.text()
                    
                    if response.status == 201:
                        logger.info(" PASS:  DATABASE E2E SUCCESS: Database operations working with system auth")
                        
                        # Validate response structure
                        if response.content_type == 'application/json':
                            response_data = await response.json()
                            if "thread_id" in response_data or "id" in response_data:
                                logger.info(f"Thread created successfully: {response_data.get('id', 'N/A')}")
                                return
                        
                        logger.info("Database operation completed successfully")
                        return
                        
                    elif response.status in [500, 503]:
                        # Check for system auth errors (should be resolved) 
                        system_auth_errors = [
                            "system_user_auth_failure", "system user failed authentication",
                            "not authenticated", "database session", "session factory"
                        ]
                        
                        if any(error in response_text.lower() for error in system_auth_errors):
                            pytest.fail(
                                f"DATABASE E2E FAILED: System authentication errors persist in database operations. "
                                f"Status: {response.status}, Response: {response_text}. "
                                f"Service authentication fix may not be working for database operations."
                            )
                        else:
                            pytest.fail(
                                f"DATABASE E2E FAILED: Non-auth error in database operations. "
                                f"Status: {response.status}, Response: {response_text}"
                            )
                    elif response.status in [401, 403]:
                        pytest.fail(
                            f"DATABASE E2E FAILED: Authentication error in database operations. "
                            f"Status: {response.status}, Response: {response_text}"
                        )
                    else:
                        pytest.fail(
                            f"DATABASE E2E FAILED: Unexpected error in database operations. "
                            f"Status: {response.status}, Response: {response_text}"
                        )
                        
            except asyncio.TimeoutError:
                pytest.fail(
                    "DATABASE E2E FAILED: Database operation timed out. "
                    "This may indicate system authentication issues preventing database access."
                )
            except Exception as e:
                pytest.fail(f"DATABASE E2E FAILED: Error in database operations test: {e}")

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.health_check  
    async def test_staging_system_user_auth_health_validation(self):
        """
        Test staging environment system user authentication health.
        
        EXPECTED: This test should PASS after service auth implementation
        VALIDATES: Staging environment properly configured for service authentication
        """
        logger.info("[U+1F3E5] HEALTH E2E: Testing staging system user authentication health")
        
        health_checks = []
        
        async with aiohttp.ClientSession() as session:
            # Test 1: System user service authentication health
            try:
                health_url = f"{self.staging_config.urls.backend_url}/api/health/system-auth"
                async with session.get(health_url, timeout=10) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        health_checks.append("system_auth: HEALTHY")
                        logger.info(" PASS:  System auth health check: PASSED")
                    else:
                        health_checks.append(f"system_auth: FAILED ({response.status})")
                        logger.warning(f" WARNING: [U+FE0F] System auth health check failed: {response.status}")
                        
            except Exception as e:
                health_checks.append(f"system_auth: ERROR ({e})")
                logger.error(f" FAIL:  System auth health check error: {e}")
            
            # Test 2: Database connectivity with system user
            try:
                db_health_url = f"{self.staging_config.urls.backend_url}/api/health/database"
                async with session.get(db_health_url, timeout=10) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        health_checks.append("database: HEALTHY")
                        logger.info(" PASS:  Database health check: PASSED")
                    else:
                        health_checks.append(f"database: FAILED ({response.status})")
                        logger.warning(f" WARNING: [U+FE0F] Database health check failed: {response.status}")
                        
            except Exception as e:
                health_checks.append(f"database: ERROR ({e})")
                logger.error(f" FAIL:  Database health check error: {e}")
            
            # Test 3: Service authentication configuration
            try:
                service_auth_url = f"{self.staging_config.urls.backend_url}/api/health/service-auth"
                async with session.get(service_auth_url, timeout=10) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        health_checks.append("service_auth_config: HEALTHY")
                        logger.info(" PASS:  Service auth config check: PASSED")
                    else:
                        health_checks.append(f"service_auth_config: FAILED ({response.status})")
                        logger.warning(f" WARNING: [U+FE0F] Service auth config check failed: {response.status}")
                        
            except Exception as e:
                health_checks.append(f"service_auth_config: ERROR ({e})")
                logger.error(f" FAIL:  Service auth config check error: {e}")
        
        # Evaluate overall health
        failed_checks = [check for check in health_checks if "FAILED" in check or "ERROR" in check]
        
        logger.info(f" CHART:  HEALTH SUMMARY: {health_checks}")
        
        if failed_checks:
            pytest.fail(
                f"HEALTH E2E FAILED: Staging environment has health issues: {failed_checks}. "
                f"Full health report: {health_checks}. "
                f"System authentication fix may not be properly deployed or configured."
            )
        
        logger.info(" PASS:  HEALTH E2E SUCCESS: All staging environment health checks passed")

    def _validate_golden_path_business_value(self, response_data: Dict[str, Any], response_text: str):
        """
        Validate that golden path delivers actual business value.
        
        Args:
            response_data: Parsed JSON response data
            response_text: Raw response text
        """
        business_value_indicators = [
            "recommendation", "optimization", "cost", "savings", 
            "insight", "analysis", "agent_response", "result"
        ]
        
        # Check for business value indicators in response
        found_indicators = []
        
        # Check in structured response data
        if response_data:
            for key, value in response_data.items():
                if any(indicator in key.lower() for indicator in business_value_indicators):
                    found_indicators.append(f"data.{key}")
                if isinstance(value, str) and any(indicator in value.lower() for indicator in business_value_indicators):
                    found_indicators.append(f"data.{key}.content")
        
        # Check in response text
        text_indicators = [indicator for indicator in business_value_indicators if indicator in response_text.lower()]
        found_indicators.extend([f"text.{indicator}" for indicator in text_indicators])
        
        if not found_indicators:
            logger.warning(
                f" WARNING: [U+FE0F] BUSINESS VALUE WARNING: Golden path response may lack business value indicators. "
                f"Response keys: {list(response_data.keys()) if response_data else 'None'}, "
                f"Text length: {len(response_text)}"
            )
        else:
            logger.info(f" PASS:  BUSINESS VALUE VALIDATED: Found indicators: {found_indicators}")

    def teardown_method(self, method):
        """Clean up after test."""
        logger.info(f"[U+1F3C1] GOLDEN PATH E2E TEST COMPLETE: {method.__name__}")
        super().teardown_method(method)