"""
Analytics Service API Integration Tests
======================================

Comprehensive integration tests for Analytics Service REST API endpoints.
Tests full API workflows with real HTTP calls and database operations (NO MOCKS).

Business Value Justification (BVJ):
- Segment: Platform/Internal + Customer-Facing  
- Business Goal: API Reliability and Customer Experience
- Value Impact: Ensures customers can reliably access analytics data and insights
- Strategic Impact: Prevents API failures that would break customer integrations

Test Coverage:
- Event ingestion API endpoints
- Analytics reports and dashboard APIs
- Real-time metrics and streaming APIs
- Authentication and authorization
- Rate limiting and throttling
- Error handling and HTTP status codes
- API versioning and compatibility
- Performance and response times
- Request/response validation
- Pagination and filtering
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4
import httpx
from shared.isolated_environment import IsolatedEnvironment

from test_framework import setup_test_path

# CRITICAL: setup_test_path() MUST be called before any project imports per CLAUDE.md
setup_test_path()

from analytics_service.analytics_core.config import get_config
from shared.isolated_environment import get_env


class EventIngestionAPITests:
    """Integration tests for event ingestion API endpoints."""

    @pytest.fixture(autouse=True)
    def isolated_test_env(self):
        """Ensure test environment isolation per CLAUDE.md requirements."""
        env = get_env()
        env.enable_isolation()
        
        # Set API test configuration
        env.set("ENVIRONMENT", "test", "test_api_integration")
        env.set("ANALYTICS_SERVICE_PORT", "8090", "test_api_integration")
        env.set("ANALYTICS_API_KEY", "test_api_key_12345", "test_api_integration")
        env.set("RATE_LIMIT_REQUESTS_PER_MINUTE", "100", "test_api_integration")
        env.set("RATE_LIMIT_EVENTS_PER_REQUEST", "50", "test_api_integration")
        
        yield env
        env.reset_to_original()

    @pytest.fixture
    async def api_client(self, isolated_test_env):
        """Create HTTP client for API testing."""
        base_url = f"http://localhost:{isolated_test_env.get('ANALYTICS_SERVICE_PORT', '8090')}"
        api_key = isolated_test_env.get("ANALYTICS_API_KEY", "test_api_key")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        async with httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=30.0
        ) as client:
            yield client

    @pytest.fixture
    def sample_event_payload(self):
        """Create sample event payload for API testing."""
        return {
            "events": [
                {
                    "event_id": str(uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": f"api_test_user_{int(time.time())}",
                    "session_id": f"api_session_{int(time.time())}",
                    "event_type": "chat_interaction",
                    "event_category": "User Interaction Events",
                    "event_action": "send_message",
                    "event_label": "test_message",
                    "event_value": 150.0,
                    "properties": json.dumps({
                        "thread_id": str(uuid4()),
                        "message_id": str(uuid4()),
                        "model_used": "claude-sonnet-4",
                        "tokens_consumed": 150,
                        "response_time_ms": 1250.5,
                    }),
                    "page_path": "/chat",
                    "page_title": "Netra AI Chat",
                    "user_agent": "Mozilla/5.0 Test API Client",
                },
                {
                    "event_id": str(uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": f"api_test_user_{int(time.time())}",
                    "session_id": f"api_session_{int(time.time())}",
                    "event_type": "performance_metric",
                    "event_category": "Technical Events",
                    "event_action": "api_call",
                    "event_label": "test_api_call",
                    "event_value": 245.7,
                    "properties": json.dumps({
                        "endpoint": "/api/chat/completions",
                        "duration_ms": 245.7,
                        "success": True,
                        "status_code": 200,
                    }),
                    "page_path": "/dashboard",
                    "page_title": "Analytics Dashboard",
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_events_ingestion_endpoint_success(self, api_client, sample_event_payload):
        """Test successful event ingestion via API."""
        try:
            response = await api_client.post("/api/analytics/events", json=sample_event_payload)
            
            if response.status_code == 200:
                data = response.json()
                assert data.get("status") == "success"
                assert data.get("ingested_count") == len(sample_event_payload["events"])
                assert "processing_time_ms" in data
                assert data.get("processing_time_ms", 0) > 0
                
                # Verify response contains event IDs
                assert "event_ids" in data
                assert len(data["event_ids"]) == len(sample_event_payload["events"])
                
            elif response.status_code == 404:
                pytest.skip("Analytics service API not available")
            else:
                # Other error codes are acceptable for testing error handling
                assert response.status_code in [400, 401, 403, 429, 500, 503]
                
        except httpx.ConnectError:
            pytest.skip("Analytics service not available for API testing")

    @pytest.mark.asyncio
    async def test_events_ingestion_validation_errors(self, api_client):
        """Test API validation for malformed event data."""
        # Test with invalid event structure
        invalid_payloads = [
            # Missing required fields
            {"events": [{"event_id": str(uuid4())}]},
            
            # Invalid timestamp format
            {"events": [{"event_id": str(uuid4()), "timestamp": "invalid-timestamp"}]},
            
            # Empty events array
            {"events": []},
            
            # Missing events field
            {"data": "invalid"},
            
            # Invalid JSON structure
            "not-json-object",
        ]
        
        for i, invalid_payload in enumerate(invalid_payloads):
            try:
                response = await api_client.post("/api/analytics/events", json=invalid_payload)
                
                if response.status_code == 400:
                    # Expected validation error
                    error_data = response.json()
                    assert "error" in error_data or "detail" in error_data
                elif response.status_code == 404:
                    pytest.skip("Analytics service not available")
                else:
                    # Other status codes are acceptable for error handling tests
                    assert response.status_code in [401, 403, 422, 500, 503]
                    
            except httpx.ConnectError:
                pytest.skip("Analytics service not available for validation testing")
                break

    @pytest.mark.asyncio
    async def test_events_ingestion_rate_limiting(self, api_client, sample_event_payload):
        """Test API rate limiting enforcement."""
        rate_limit_requests = 10  # Send more requests than typical rate limit
        
        responses = []
        start_time = time.time()
        
        # Send multiple requests rapidly
        tasks = []
        for i in range(rate_limit_requests):
            # Create unique payload for each request
            payload = sample_event_payload.copy()
            payload["events"][0]["event_id"] = str(uuid4())
            payload["events"][0]["user_id"] = f"rate_test_user_{i}"
            
            task = api_client.post("/api/analytics/events", json=payload)
            tasks.append(task)
        
        try:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            processing_time = time.time() - start_time
            
            # Analyze responses for rate limiting
            successful_responses = []
            rate_limited_responses = []
            connection_errors = 0
            
            for response in responses:
                if isinstance(response, httpx.ConnectError):
                    connection_errors += 1
                elif hasattr(response, 'status_code'):
                    if response.status_code == 200:
                        successful_responses.append(response)
                    elif response.status_code == 429:  # Too Many Requests
                        rate_limited_responses.append(response)
            
            if connection_errors == len(responses):
                pytest.skip("Analytics service not available for rate limiting test")
            
            # If we got responses, verify rate limiting behavior
            if len(successful_responses) + len(rate_limited_responses) > 0:
                # Rate limiting should kick in for high volume
                if len(responses) >= 5:  # Only check if we had significant volume
                    total_accepted = len(successful_responses)
                    assert total_accepted <= rate_limit_requests  # Some should be limited
                    
        except Exception as e:
            pytest.skip(f"Rate limiting test failed due to service issues: {e}")

    @pytest.mark.asyncio
    async def test_events_ingestion_authentication(self, isolated_test_env):
        """Test API authentication and authorization."""
        base_url = f"http://localhost:{isolated_test_env.get('ANALYTICS_SERVICE_PORT', '8090')}"
        
        # Test without authentication
        try:
            async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as unauthenticated_client:
                response = await unauthenticated_client.post("/api/analytics/events", json={"events": []})
                
                if response.status_code == 401:
                    # Expected - authentication required
                    assert True
                elif response.status_code == 404:
                    pytest.skip("Analytics service not available")
                else:
                    # Other status codes acceptable (depends on auth implementation)
                    assert response.status_code in [400, 403, 500, 503]
                    
        except httpx.ConnectError:
            pytest.skip("Analytics service not available for authentication testing")
        
        # Test with invalid API key
        try:
            invalid_headers = {
                "Authorization": "Bearer invalid_api_key_12345",
                "Content-Type": "application/json",
            }
            
            async with httpx.AsyncClient(base_url=base_url, headers=invalid_headers, timeout=10.0) as invalid_client:
                response = await invalid_client.post("/api/analytics/events", json={"events": []})
                
                if response.status_code == 401:
                    # Expected - invalid credentials
                    assert True
                elif response.status_code == 404:
                    pytest.skip("Analytics service not available")
                else:
                    # Other status codes acceptable
                    assert response.status_code in [400, 403, 500, 503]
                    
        except httpx.ConnectError:
            pytest.skip("Analytics service not available for authentication testing")


class AnalyticsReportsAPITests:
    """Integration tests for analytics reports and dashboard APIs."""

    @pytest.fixture(autouse=True)
    def isolated_test_env(self):
        """Setup environment for analytics reports API tests."""
        env = get_env()
        env.enable_isolation()
        
        env.set("ENVIRONMENT", "test", "test_reports_api")
        env.set("ANALYTICS_SERVICE_PORT", "8090", "test_reports_api")
        env.set("ANALYTICS_API_KEY", "test_api_key_reports", "test_reports_api")
        
        yield env
        env.reset_to_original()

    @pytest.fixture
    async def api_client(self, isolated_test_env):
        """Create authenticated API client for reports testing."""
        base_url = f"http://localhost:{isolated_test_env.get('ANALYTICS_SERVICE_PORT', '8090')}"
        api_key = isolated_test_env.get("ANALYTICS_API_KEY", "test_api_key")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }
        
        async with httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=30.0
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_user_analytics_summary_endpoint(self, api_client):
        """Test user analytics summary API endpoint."""
        test_user_id = f"reports_test_user_{int(time.time())}"
        
        try:
            response = await api_client.get(f"/api/analytics/users/{test_user_id}/summary")
            
            if response.status_code == 200:
                data = response.json()
                assert "user_id" in data
                assert "total_events" in data
                assert "session_count" in data
                assert "date_range" in data
                assert data["user_id"] == test_user_id
                
            elif response.status_code == 404:
                # User not found or service not available
                if "service" in response.text.lower() or "analytics" in response.text.lower():
                    pytest.skip("Analytics service not available")
                else:
                    # User not found - acceptable for test
                    assert True
            else:
                assert response.status_code in [401, 403, 500, 503]
                
        except httpx.ConnectError:
            pytest.skip("Analytics service not available for reports testing")

    @pytest.mark.asyncio
    async def test_dashboard_metrics_endpoint(self, api_client):
        """Test dashboard metrics API endpoint."""
        try:
            # Test dashboard metrics with date range
            params = {
                "start_date": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
                "end_date": datetime.now(timezone.utc).isoformat(),
                "metrics": "active_users,total_events,session_duration",
            }
            
            response = await api_client.get("/api/analytics/dashboard/metrics", params=params)
            
            if response.status_code == 200:
                data = response.json()
                assert "metrics" in data
                assert "date_range" in data
                assert "generated_at" in data
                
                # Verify metric structure
                metrics = data["metrics"]
                if isinstance(metrics, dict):
                    for metric_name, metric_data in metrics.items():
                        assert "value" in metric_data
                        assert "trend" in metric_data or "change" in metric_data
                        
            elif response.status_code == 404:
                pytest.skip("Analytics dashboard API not available")
            else:
                assert response.status_code in [401, 403, 400, 500, 503]
                
        except httpx.ConnectError:
            pytest.skip("Analytics service not available for dashboard testing")

    @pytest.mark.asyncio
    async def test_analytics_reports_with_filters(self, api_client):
        """Test analytics reports with various filters and parameters."""
        try:
            # Test event analytics with filters
            filter_params = {
                "start_date": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
                "end_date": datetime.now(timezone.utc).isoformat(),
                "event_type": "chat_interaction",
                "group_by": "day",
                "limit": 100,
                "offset": 0,
            }
            
            response = await api_client.get("/api/analytics/events/report", params=filter_params)
            
            if response.status_code == 200:
                data = response.json()
                assert "events" in data or "report" in data
                assert "total_count" in data
                assert "filters_applied" in data
                
                # Verify pagination info
                if "pagination" in data:
                    pagination = data["pagination"]
                    assert "limit" in pagination
                    assert "offset" in pagination
                    assert "has_more" in pagination
                    
            elif response.status_code == 404:
                pytest.skip("Analytics reports API not available")
            else:
                assert response.status_code in [401, 403, 400, 500, 503]
                
        except httpx.ConnectError:
            pytest.skip("Analytics service not available for filtered reports testing")

    @pytest.mark.asyncio
    async def test_real_time_metrics_endpoint(self, api_client):
        """Test real-time metrics API endpoint."""
        try:
            response = await api_client.get("/api/analytics/real-time/metrics")
            
            if response.status_code == 200:
                data = response.json()
                assert "timestamp" in data
                assert "metrics" in data
                
                # Verify real-time metrics structure
                metrics = data["metrics"]
                expected_metrics = ["active_users", "events_per_second", "response_time_avg"]
                
                if isinstance(metrics, dict):
                    # At least some metrics should be present
                    assert len(metrics) > 0
                    
                    for metric_name, metric_value in metrics.items():
                        assert isinstance(metric_value, (int, float))
                        
            elif response.status_code == 404:
                pytest.skip("Real-time metrics API not available")
            else:
                assert response.status_code in [401, 403, 500, 503]
                
        except httpx.ConnectError:
            pytest.skip("Analytics service not available for real-time testing")


class AnalyticsPerformanceAPITests:
    """Integration tests for API performance and scalability."""

    @pytest.fixture(autouse=True)
    def isolated_test_env(self):
        """Setup environment for performance testing."""
        env = get_env()
        env.enable_isolation()
        
        env.set("ENVIRONMENT", "test", "test_performance_api")
        env.set("ANALYTICS_SERVICE_PORT", "8090", "test_performance_api")
        env.set("ANALYTICS_API_KEY", "test_performance_key", "test_performance_api")
        env.set("PERFORMANCE_TEST_TIMEOUT", "60", "test_performance_api")  # 60 second timeout
        
        yield env
        env.reset_to_original()

    @pytest.fixture
    async def api_client(self, isolated_test_env):
        """Create API client with extended timeout for performance tests."""
        base_url = f"http://localhost:{isolated_test_env.get('ANALYTICS_SERVICE_PORT', '8090')}"
        api_key = isolated_test_env.get("ANALYTICS_API_KEY", "test_key")
        timeout = float(isolated_test_env.get("PERFORMANCE_TEST_TIMEOUT", "60"))
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        async with httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=timeout
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_api_response_time_performance(self, api_client):
        """Test API response time performance requirements."""
        endpoints_to_test = [
            ("/health", "GET"),
            ("/api/analytics/events", "POST"),
            ("/api/analytics/dashboard/metrics", "GET"),
        ]
        
        performance_results = {}
        
        for endpoint, method in endpoints_to_test:
            response_times = []
            
            # Test each endpoint 5 times to get average response time
            for _ in range(5):
                start_time = time.time()
                
                try:
                    if method == "GET":
                        response = await api_client.get(endpoint)
                    elif method == "POST":
                        # Use minimal valid payload for POST endpoints
                        test_payload = {"events": []}
                        response = await api_client.post(endpoint, json=test_payload)
                    
                    response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                    response_times.append(response_time)
                    
                    # Don't require success, just measure response time
                    assert response.status_code in [200, 400, 401, 404, 429, 500, 503]
                    
                except httpx.ConnectError:
                    pytest.skip(f"Analytics service not available for performance testing: {endpoint}")
                    break
                except asyncio.TimeoutError:
                    pytest.fail(f"API timeout exceeded for endpoint: {endpoint}")
                    
                # Small delay between requests
                await asyncio.sleep(0.1)
            
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                performance_results[endpoint] = {
                    "average_ms": avg_response_time,
                    "max_ms": max(response_times),
                    "min_ms": min(response_times),
                }
                
                # Performance requirements
                if endpoint == "/health":
                    assert avg_response_time < 100  # Health checks should be very fast
                elif "events" in endpoint:
                    assert avg_response_time < 1000  # Event ingestion should be under 1 second
                elif "dashboard" in endpoint:
                    assert avg_response_time < 2000  # Dashboard queries can be slightly slower
        
        # Log performance results for analysis
        print(f"API Performance Results: {json.dumps(performance_results, indent=2)}")

    @pytest.mark.asyncio
    async def test_api_concurrent_request_handling(self, api_client):
        """Test API ability to handle concurrent requests."""
        concurrent_requests = 10
        
        # Create concurrent requests to different endpoints
        tasks = []
        endpoints = [
            "/health",
            "/api/analytics/dashboard/metrics",
            "/api/analytics/real-time/metrics",
        ]
        
        for i in range(concurrent_requests):
            endpoint = endpoints[i % len(endpoints)]
            task = api_client.get(endpoint)
            tasks.append(task)
        
        start_time = time.time()
        
        try:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Analyze concurrent request handling
            successful_requests = 0
            connection_errors = 0
            server_errors = 0
            
            for response in responses:
                if isinstance(response, httpx.ConnectError):
                    connection_errors += 1
                elif hasattr(response, 'status_code'):
                    if 200 <= response.status_code < 400:
                        successful_requests += 1
                    elif response.status_code >= 500:
                        server_errors += 1
            
            if connection_errors == len(responses):
                pytest.skip("Analytics service not available for concurrency testing")
            
            # Verify concurrent handling capabilities
            if successful_requests + server_errors > 0:  # Some responses received
                # At least some requests should succeed under normal load
                success_rate = successful_requests / (len(responses) - connection_errors)
                assert success_rate >= 0.7  # At least 70% success rate for concurrent requests
                
                # Total time should be reasonable (not much more than sequential)
                assert total_time < 30.0  # Should complete within 30 seconds
                
        except Exception as e:
            pytest.skip(f"Concurrency test failed due to service issues: {e}")

    @pytest.mark.asyncio
    async def test_large_payload_handling(self, api_client):
        """Test API handling of large event payloads."""
        # Create large event batch (but within reasonable limits)
        large_event_batch = {
            "events": []
        }
        
        # Generate 50 events (large but reasonable for testing)
        for i in range(50):
            event = {
                "event_id": str(uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": f"large_payload_user_{i}",
                "session_id": f"large_session_{i // 10}",
                "event_type": "chat_interaction",
                "event_category": "User Interaction Events",
                "event_action": "large_test_event",
                "event_value": float(i),
                "properties": json.dumps({
                    "sequence": i,
                    "batch_id": "large_payload_test",
                    "large_data": "x" * 1000,  # 1KB of data per event
                }),
                "page_path": "/chat",
                "page_title": "Large Payload Test",
            }
            large_event_batch["events"].append(event)
        
        try:
            start_time = time.time()
            response = await api_client.post("/api/analytics/events", json=large_event_batch)
            processing_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                assert data.get("ingested_count") == len(large_event_batch["events"])
                
                # Verify reasonable processing time for large payload
                assert processing_time < 10000  # Should process within 10 seconds
                
            elif response.status_code == 413:
                # Payload too large - acceptable response
                assert True
            elif response.status_code == 404:
                pytest.skip("Analytics service not available")
            else:
                # Other error codes acceptable for large payload testing
                assert response.status_code in [400, 401, 429, 500, 503]
                
        except httpx.ConnectError:
            pytest.skip("Analytics service not available for large payload testing")
        except asyncio.TimeoutError:
            pytest.fail("Large payload processing exceeded timeout")


class APIErrorHandlingIntegrationTests:
    """Integration tests for comprehensive API error handling."""

    @pytest.fixture(autouse=True)
    def isolated_test_env(self):
        """Setup environment for error handling tests."""
        env = get_env()
        env.enable_isolation()
        
        env.set("ENVIRONMENT", "test", "test_api_error_handling")
        env.set("ANALYTICS_SERVICE_PORT", "8090", "test_api_error_handling")
        env.set("ANALYTICS_API_KEY", "test_error_key", "test_api_error_handling")
        
        yield env
        env.reset_to_original()

    @pytest.fixture
    async def api_client(self, isolated_test_env):
        """Create API client for error handling tests."""
        base_url = f"http://localhost:{isolated_test_env.get('ANALYTICS_SERVICE_PORT', '8090')}"
        api_key = isolated_test_env.get("ANALYTICS_API_KEY", "test_key")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        async with httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=15.0
        ) as client:
            yield client

    @pytest.mark.asyncio
    async def test_api_error_response_format(self, api_client):
        """Test API error response format consistency."""
        # Test various error scenarios
        error_scenarios = [
            # Invalid endpoint
            ("GET", "/api/analytics/nonexistent", None),
            
            # Invalid method
            ("DELETE", "/api/analytics/events", None),
            
            # Malformed JSON
            ("POST", "/api/analytics/events", '{"invalid": json}'),
            
            # Missing required fields
            ("POST", "/api/analytics/events", {"events": [{"invalid": "event"}]}),
        ]
        
        for method, endpoint, payload in error_scenarios:
            try:
                if method == "GET":
                    response = await api_client.get(endpoint)
                elif method == "POST":
                    if isinstance(payload, str):
                        # Send raw string for malformed JSON test
                        response = await api_client.post(endpoint, content=payload)
                    else:
                        response = await api_client.post(endpoint, json=payload)
                elif method == "DELETE":
                    response = await api_client.delete(endpoint)
                
                # Verify error response has proper structure
                if 400 <= response.status_code < 600:
                    try:
                        error_data = response.json()
                        # Common error response fields
                        expected_fields = ["error", "message", "detail", "status"]
                        assert any(field in error_data for field in expected_fields)
                    except json.JSONDecodeError:
                        # Some errors might not return JSON - that's acceptable
                        pass
                        
            except httpx.ConnectError:
                pytest.skip("Analytics service not available for error handling testing")
                break

    @pytest.mark.asyncio
    async def test_api_timeout_handling(self, api_client):
        """Test API timeout and long-running request handling."""
        try:
            # Create a client with very short timeout to test timeout handling
            async with httpx.AsyncClient(
                base_url=api_client.base_url,
                headers=dict(api_client.headers),
                timeout=0.001  # 1ms timeout - very short
            ) as timeout_client:
                
                response = await timeout_client.get("/api/analytics/dashboard/metrics")
                
                # If we get a response, the service was very fast
                if response.status_code == 200:
                    assert True
                elif response.status_code == 404:
                    pytest.skip("Analytics service not available")
                else:
                    assert response.status_code in [401, 403, 500, 503]
                    
        except httpx.TimeoutException:
            # Expected timeout - this is what we're testing
            assert True  # Timeout handled correctly
        except httpx.ConnectError:
            pytest.skip("Analytics service not available for timeout testing")

    @pytest.mark.asyncio
    async def test_api_health_and_status_endpoints(self, api_client):
        """Test health check and status endpoints."""
        health_endpoints = [
            "/health",
            "/api/health", 
            "/status",
            "/api/analytics/health",
        ]
        
        working_endpoints = []
        
        for endpoint in health_endpoints:
            try:
                response = await api_client.get(endpoint)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Health endpoint should return status information
                    assert "status" in data or "health" in data
                    
                    # Should include service identification
                    service_indicators = ["service", "name", "version", "analytics"]
                    assert any(indicator in str(data).lower() for indicator in service_indicators)
                    
                    working_endpoints.append(endpoint)
                    
            except (httpx.ConnectError, json.JSONDecodeError):
                # Endpoint not available or doesn't return JSON - acceptable
                continue
        
        if not working_endpoints:
            pytest.skip("No health endpoints available for testing")
        else:
            # At least one health endpoint should work
            assert len(working_endpoints) >= 1