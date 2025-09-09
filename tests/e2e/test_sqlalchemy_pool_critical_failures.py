"""
SQLAlchemy Pool Critical Failures E2E Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prevent system-wide outages due to database pool misconfigurations
- Value Impact: Ensures users can access agents and perform optimizations without 500 errors
- Strategic Impact: Database reliability prevents revenue loss and maintains user trust

CRITICAL: These E2E tests reproduce system-level failures that occur when database 
pool configurations are incompatible with async engines. They simulate real user journeys
that would fail catastrophically with the original QueuePool + async engine configuration.

E2E Scenarios Tested:
1. API endpoint 500 errors due to session creation failures  
2. System user authentication failures cascading from database issues
3. WebSocket connection failures when database sessions can't be created
4. Multi-user concurrent requests failing due to pool errors
5. Agent execution pipeline failures from database connectivity issues

IMPORTANT: These tests MUST use real services and authentication. 
Tests that complete in 0.00s are automatically considered failures.
"""

import asyncio
import pytest
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import json
from unittest.mock import patch, MagicMock
import httpx
import websockets
from urllib.parse import urljoin

# E2E test framework imports
from test_framework.base_e2e_test import BaseE2ETest  
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.websocket_helpers import WebSocketTestClient
from test_framework.ssot.e2e_auth_helper import create_test_user, get_auth_headers

# Database imports for mocking broken configurations
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.exc import ArgumentError

logger = logging.getLogger(__name__)


@pytest.mark.e2e
@pytest.mark.real_services
class TestSQLAlchemyPoolCriticalFailures:
    """E2E tests for SQLAlchemy pool configuration critical failures."""
    
    @pytest.fixture
    async def test_user(self, real_services_fixture):
        """Create authenticated test user for E2E scenarios."""
        # Create test user with real authentication
        user_data = await create_test_user(
            email="sqlalchemy.pool.test@netra.ai",
            name="SQLAlchemy Pool Test User",
            subscription="enterprise"
        )
        return user_data
    
    @pytest.fixture
    async def backend_base_url(self, real_services_fixture):
        """Get backend service URL from real services."""
        services = real_services_fixture
        backend_url = services.get("backend_url", "http://localhost:8000")
        return backend_url
    
    @pytest.fixture
    async def auth_headers(self, test_user):
        """Get authentication headers for API requests."""
        return await get_auth_headers(test_user["token"])
    
    async def test_mcp_servers_endpoint_500_error(self, backend_base_url, auth_headers):
        """MUST return 500 error for /api/mcp/servers due to database session failure.
        
        This test simulates what happens when the QueuePool configuration prevents
        database sessions from being created, causing API endpoints to fail with 500 errors.
        """
        start_time = time.time()
        
        # Mock the database configuration to use broken QueuePool
        with patch('netra_backend.app.database.create_async_engine') as mock_create_engine:
            # Configure mock to raise QueuePool error
            mock_create_engine.side_effect = ArgumentError(
                "Pool class QueuePool cannot be used with asyncio engine"
            )
            
            # Force reset of global engine to trigger recreation
            import netra_backend.app.database
            original_engine = netra_backend.app.database._engine
            netra_backend.app.database._engine = None
            
            try:
                # Act: Make API request that requires database session
                async with httpx.AsyncClient(timeout=30.0) as client:
                    url = urljoin(backend_base_url, "/api/mcp/servers")
                    
                    # This should fail with 500 due to database session creation failure
                    response = await client.get(url, headers=auth_headers)
                    
                    # Assert: Should get 500 Internal Server Error
                    assert response.status_code == 500, (
                        f"Expected 500 error due to pool configuration, got {response.status_code}. "
                        f"Response: {response.text}"
                    )
                    
                    # Verify error message indicates database/session issue
                    error_text = response.text.lower()
                    database_error_indicators = [
                        "database", "session", "pool", "connection", 
                        "internal server error", "asyncio engine"
                    ]
                    
                    has_db_error_indicator = any(indicator in error_text for indicator in database_error_indicators)
                    assert has_db_error_indicator, (
                        f"Error response should indicate database/session issue. "
                        f"Response: {response.text}"
                    )
            
            finally:
                # Restore original engine state
                netra_backend.app.database._engine = original_engine
        
        # Verify this was a real E2E test with meaningful execution time
        execution_time = time.time() - start_time
        assert execution_time > 5.0, (
            f"E2E test execution time {execution_time:.3f}s too fast - "
            "indicates test didn't use real services or network calls"
        )
    
    async def test_system_user_authentication_cascade_failure(self, backend_base_url):
        """MUST fail system user auth due to database session creation failure.
        
        This test reproduces the cascade failure where system user authentication fails
        because the database session required for auth validation can't be created
        due to pool configuration errors.
        """
        start_time = time.time()
        
        # Mock database session creation to fail with pool error
        with patch('netra_backend.app.dependencies.get_request_scoped_db_session') as mock_get_session:
            # Configure mock to raise pool compatibility error
            async def failing_session_generator():
                raise ArgumentError("Pool class QueuePool cannot be used with asyncio engine")
                yield  # Never reached
            
            mock_get_session.return_value = failing_session_generator()
            
            # Act: Make request that requires system user authentication
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Use health endpoint which often uses system user for database checks
                url = urljoin(backend_base_url, "/api/health/detailed")
                
                # This should fail due to authentication cascade failure
                response = await client.get(url)
                
                # Assert: Should get authentication-related error or 500
                assert response.status_code in [401, 403, 500], (
                    f"Expected auth failure or 500 error, got {response.status_code}. "
                    f"Response: {response.text}"
                )
                
                # For detailed analysis of the failure
                if response.status_code == 500:
                    # Internal server error due to database session failure
                    error_text = response.text.lower()
                    auth_db_indicators = [
                        "authentication", "session", "database", "pool", "system user"
                    ]
                    
                    has_auth_db_indicator = any(indicator in error_text for indicator in auth_db_indicators)
                    assert has_auth_db_indicator, (
                        f"500 error should indicate authentication/database issue. "
                        f"Response: {response.text}"
                    )
                
                elif response.status_code in [401, 403]:
                    # Authentication failure as expected
                    logger.info(f"Got expected auth failure {response.status_code}: {response.text}")
        
        # Verify real E2E test execution
        execution_time = time.time() - start_time
        assert execution_time > 5.0, f"E2E test execution time {execution_time:.3f}s too fast"
    
    async def test_websocket_connection_failure_due_to_session_error(self, backend_base_url, test_user):
        """MUST fail WebSocket connection when database sessions can't be created.
        
        This test validates that WebSocket connections fail gracefully when the underlying
        database session creation fails due to pool configuration errors.
        """
        start_time = time.time()
        
        # Mock session factory to fail with pool error
        with patch('netra_backend.app.websocket_core.websocket_manager_factory.create_websocket_manager') as mock_create_manager:
            # Configure mock to simulate session creation failure
            async def failing_manager_creation(user_context):
                raise ArgumentError("Pool class QueuePool cannot be used with asyncio engine")
            
            mock_create_manager.side_effect = failing_manager_creation
            
            # Act: Attempt WebSocket connection
            try:
                websocket_url = backend_base_url.replace("http://", "ws://").replace("https://", "wss://")
                websocket_url = urljoin(websocket_url, f"/ws/{test_user['id']}/test_thread")
                
                # This should fail during connection establishment
                async with websockets.connect(
                    websocket_url,
                    additional_headers={"Authorization": f"Bearer {test_user['token']}"},
                    timeout=10.0
                ) as websocket:
                    # If connection succeeds, try to send a message (should fail)
                    await websocket.send(json.dumps({
                        "type": "agent_request", 
                        "agent": "triage_agent",
                        "message": "Test message"
                    }))
                    
                    # Wait for response (should get error)
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    
                    # Should get an error response
                    assert response_data.get("type") == "error", (
                        f"Expected error response due to session failure, got: {response_data}"
                    )
                    
                    error_message = response_data.get("error", "").lower()
                    session_error_indicators = ["session", "database", "pool", "asyncio engine"]
                    
                    has_session_error = any(indicator in error_message for indicator in session_error_indicators)
                    assert has_session_error, (
                        f"Error should indicate session/database issue. Got: {response_data}"
                    )
            
            except (websockets.exceptions.ConnectionClosed, 
                   websockets.exceptions.InvalidStatusCode,
                   websockets.exceptions.WebSocketException,
                   OSError) as e:
                # Connection failure is expected due to session creation failure
                logger.info(f"WebSocket connection failed as expected: {e}")
                
                # Verify the error is related to our mocked failure
                error_msg = str(e).lower()
                expected_error_indicators = ["connection", "refused", "closed", "failed"]
                
                has_connection_error = any(indicator in error_msg for indicator in expected_error_indicators)
                assert has_connection_error, f"Unexpected WebSocket error type: {e}"
            
            except asyncio.TimeoutError:
                # Timeout is also acceptable - indicates connection couldn't be established
                logger.info("WebSocket connection timed out as expected due to session creation failure")
        
        # Verify real E2E test execution
        execution_time = time.time() - start_time
        assert execution_time > 8.0, f"E2E test execution time {execution_time:.3f}s too fast"
    
    async def test_concurrent_user_requests_cascade_failure(self, backend_base_url):
        """MUST fail for multiple concurrent users due to pool configuration errors.
        
        This test simulates what happens when multiple users make concurrent requests
        and all fail due to the database pool misconfiguration preventing session creation.
        """
        start_time = time.time()
        
        # Create multiple test users for concurrent testing
        async def create_test_users(count: int) -> List[Dict]:
            """Create multiple test users for concurrent testing."""
            users = []
            for i in range(count):
                try:
                    user = await create_test_user(
                        email=f"concurrent.pool.test.{i}@netra.ai",
                        name=f"Concurrent Pool Test User {i}",
                        subscription="basic"
                    )
                    users.append(user)
                except Exception as e:
                    logger.warning(f"Failed to create test user {i}: {e}")
            return users
        
        test_users = await create_test_users(3)
        assert len(test_users) >= 2, "Need at least 2 test users for concurrent testing"
        
        # Mock database session creation to fail
        with patch('netra_backend.app.database.get_engine') as mock_get_engine:
            # Configure mock to raise pool error
            mock_get_engine.side_effect = ArgumentError(
                "Pool class QueuePool cannot be used with asyncio engine"
            )
            
            # Act: Make concurrent requests from different users
            async def make_user_request(user_data: Dict) -> Dict:
                """Make API request as a specific user."""
                try:
                    headers = await get_auth_headers(user_data["token"])
                    
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        url = urljoin(backend_base_url, "/api/threads")
                        response = await client.get(url, headers=headers)
                        
                        return {
                            "user_id": user_data["id"],
                            "user_email": user_data["email"], 
                            "status_code": response.status_code,
                            "response_text": response.text,
                            "success": response.status_code < 400
                        }
                
                except Exception as e:
                    return {
                        "user_id": user_data["id"],
                        "user_email": user_data["email"],
                        "status_code": None,
                        "response_text": str(e),
                        "success": False,
                        "error": str(e)
                    }
            
            # Execute concurrent requests
            concurrent_tasks = [make_user_request(user) for user in test_users]
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=False)
            
            # Assert: All requests should fail due to database pool error
            for result in results:
                assert not result["success"], (
                    f"Request for user {result['user_email']} should have failed. "
                    f"Got status {result['status_code']}: {result['response_text']}"
                )
                
                # Should get 500 error or exception
                if result["status_code"]:
                    assert result["status_code"] >= 500, (
                        f"Expected 500+ error for user {result['user_email']}, "
                        f"got {result['status_code']}"
                    )
                    
                    # Verify error indicates database/session issue
                    error_content = result["response_text"].lower()
                    db_error_indicators = ["database", "session", "pool", "internal server error"]
                    
                    has_db_error = any(indicator in error_content for indicator in db_error_indicators)
                    assert has_db_error, (
                        f"Error should indicate database issue for user {result['user_email']}. "
                        f"Response: {result['response_text']}"
                    )
                else:
                    # Exception occurred (also acceptable)
                    assert "error" in result, f"Expected error field for user {result['user_email']}"
                    
                    error_msg = result["error"].lower()
                    connection_indicators = ["connection", "pool", "session", "database"]
                    
                    has_connection_error = any(indicator in error_msg for indicator in connection_indicators)
                    assert has_connection_error, (
                        f"Exception should indicate connection/database issue for user {result['user_email']}. "
                        f"Error: {result['error']}"
                    )
        
        # Verify all users failed consistently
        failed_users = [r["user_email"] for r in results if not r["success"]]
        assert len(failed_users) == len(test_users), (
            f"All {len(test_users)} users should fail, but only {len(failed_users)} failed"
        )
        
        # Verify real E2E test execution
        execution_time = time.time() - start_time
        assert execution_time > 8.0, f"E2E test execution time {execution_time:.3f}s too fast"
    
    async def test_agent_execution_pipeline_failure(self, backend_base_url, test_user):
        """MUST fail agent execution due to database session creation errors.
        
        This test validates that agent execution pipelines fail gracefully when
        database sessions required for execution context can't be created.
        """
        start_time = time.time()
        
        # Mock agent execution dependencies to fail with pool error
        with patch('netra_backend.app.core.supervisor_factory.create_supervisor_core') as mock_create_supervisor:
            # Configure mock to fail due to session creation error
            async def failing_supervisor_creation(*args, **kwargs):
                raise ArgumentError("Pool class QueuePool cannot be used with asyncio engine")
            
            mock_create_supervisor.side_effect = failing_supervisor_creation
            
            # Act: Attempt agent execution via API
            try:
                headers = await get_auth_headers(test_user["token"])
                
                async with httpx.AsyncClient(timeout=60.0) as client:
                    # Create a thread first (may also fail, but try)
                    thread_url = urljoin(backend_base_url, "/api/threads")
                    thread_data = {
                        "title": "SQLAlchemy Pool Test Thread"
                    }
                    
                    # This might fail too, but proceed anyway
                    thread_response = await client.post(
                        thread_url, 
                        json=thread_data, 
                        headers=headers
                    )
                    
                    if thread_response.status_code >= 400:
                        # Thread creation failed - probably due to same pool issue
                        assert thread_response.status_code >= 500, (
                            f"Thread creation should fail with 500+ error, got {thread_response.status_code}"
                        )
                        
                        error_text = thread_response.text.lower() 
                        thread_error_indicators = ["database", "session", "pool", "internal server error"]
                        
                        has_thread_error = any(indicator in error_text for indicator in thread_error_indicators)
                        assert has_thread_error, (
                            f"Thread creation error should indicate database issue. "
                            f"Response: {thread_response.text}"
                        )
                        
                        logger.info(f"Thread creation failed as expected: {thread_response.status_code}")
                        return  # Test accomplished - thread creation itself failed due to pool error
                    
                    # If thread creation succeeded, try agent execution
                    thread_data = thread_response.json()
                    thread_id = thread_data["id"]
                    
                    # Attempt agent execution
                    agent_url = urljoin(backend_base_url, f"/api/threads/{thread_id}/agents")
                    agent_request = {
                        "agent": "triage_agent",
                        "message": "Test agent execution with pool error"
                    }
                    
                    agent_response = await client.post(
                        agent_url,
                        json=agent_request,
                        headers=headers
                    )
                    
                    # Should fail due to supervisor creation failure
                    assert agent_response.status_code >= 500, (
                        f"Agent execution should fail with 500+ error, got {agent_response.status_code}. "
                        f"Response: {agent_response.text}"
                    )
                    
                    # Verify error indicates supervisor/session creation failure
                    error_text = agent_response.text.lower()
                    agent_error_indicators = [
                        "supervisor", "session", "database", "pool", 
                        "internal server error", "asyncio engine"
                    ]
                    
                    has_agent_error = any(indicator in error_text for indicator in agent_error_indicators)
                    assert has_agent_error, (
                        f"Agent execution error should indicate supervisor/session issue. "
                        f"Response: {agent_response.text}"
                    )
            
            except httpx.RequestError as e:
                # Network/connection error also acceptable
                logger.info(f"Request failed as expected due to pool configuration: {e}")
            
            except Exception as e:
                # Any other exception indicates the system failed as expected
                error_msg = str(e).lower()
                expected_indicators = ["pool", "session", "database", "asyncio engine"]
                
                has_expected_error = any(indicator in error_msg for indicator in expected_indicators)
                assert has_expected_error, (
                    f"Exception should be related to pool/session issue. Got: {e}"
                )
        
        # Verify real E2E test execution
        execution_time = time.time() - start_time
        assert execution_time > 10.0, f"E2E test execution time {execution_time:.3f}s too fast"
    
    async def test_system_health_check_cascade_failure(self, backend_base_url):
        """MUST fail system health checks due to database connectivity issues.
        
        This test validates that system health checks properly detect and report
        database pool configuration issues that prevent session creation.
        """
        start_time = time.time()
        
        # Mock database connectivity to fail with pool error
        with patch('netra_backend.app.database.get_sessionmaker') as mock_get_sessionmaker:
            # Configure mock to fail when creating sessionmaker
            mock_get_sessionmaker.side_effect = ArgumentError(
                "Pool class QueuePool cannot be used with asyncio engine"  
            )
            
            # Act: Check system health endpoints
            async with httpx.AsyncClient(timeout=30.0) as client:
                health_endpoints = [
                    "/api/health",
                    "/api/health/detailed", 
                    "/api/health/database"
                ]
                
                health_results = []
                
                for endpoint in health_endpoints:
                    try:
                        url = urljoin(backend_base_url, endpoint)
                        response = await client.get(url)
                        
                        health_results.append({
                            "endpoint": endpoint,
                            "status_code": response.status_code,
                            "response": response.text,
                            "success": response.status_code == 200
                        })
                        
                    except Exception as e:
                        health_results.append({
                            "endpoint": endpoint,
                            "status_code": None,
                            "response": str(e),
                            "success": False,
                            "error": str(e)
                        })
                
                # Assert: Health checks should fail or report database issues
                for result in health_results:
                    endpoint = result["endpoint"]
                    
                    if result["success"]:
                        # If health check succeeds, it should report database issues
                        response_text = result["response"].lower()
                        
                        # Look for health status indicators
                        unhealthy_indicators = [
                            "unhealthy", "degraded", "error", "failed", 
                            "database", "session", "pool"
                        ]
                        
                        has_unhealthy_status = any(indicator in response_text for indicator in unhealthy_indicators)
                        assert has_unhealthy_status, (
                            f"Health check {endpoint} should report unhealthy status due to database issues. "
                            f"Response: {result['response']}"
                        )
                        
                    else:
                        # Health check failed (also acceptable)
                        if result["status_code"]:
                            # HTTP error response
                            assert result["status_code"] >= 500, (
                                f"Health check {endpoint} should fail with 500+ error, "
                                f"got {result['status_code']}"
                            )
                        else:
                            # Exception occurred
                            assert "error" in result, f"Expected error for {endpoint}"
                
                # Verify at least one health check detected the database issue
                database_issue_detected = any(
                    "database" in result["response"].lower() or 
                    "session" in result["response"].lower() or
                    "pool" in result["response"].lower()
                    for result in health_results
                )
                
                assert database_issue_detected, (
                    f"At least one health check should detect database/session/pool issue. "
                    f"Results: {health_results}"
                )
        
        # Verify real E2E test execution
        execution_time = time.time() - start_time
        assert execution_time > 6.0, f"E2E test execution time {execution_time:.3f}s too fast"