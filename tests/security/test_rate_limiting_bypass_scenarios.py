"""
Rate limiting bypass scenario tests.

Tests critical rate limiting bypass scenarios that cause resource abuse,
preventing revenue loss from quota violations and system resource exhaustion.
"""
import pytest
import asyncio
import time
from shared.isolated_environment import IsolatedEnvironment

from tests.e2e.helpers.performance import RateLimitingTester
from tests.clients.backend_client import BackendClient
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


@pytest.mark.critical
@pytest.mark.security
async def test_rate_limit_enforcement_across_multiple_ips():
    """Test rate limiting can't be bypassed using multiple IP addresses."""
    rate_tester = RateLimitingTester()
    user_id = "user123"
    
    # Simulate requests from different IPs for same user
    ip_addresses = ["192.168.1.1", "192.168.1.2", "192.168.1.3"]
    
    # Each IP should be limited individually, but user quota enforced globally
    total_allowed = 0
    
    for ip in ip_addresses:
        allowed_requests = await rate_tester.test_rate_limit(
            user_id=user_id,
            client_ip=ip,
            requests_per_minute=100,
            test_duration=1.0
        )
        total_allowed += allowed_requests.count
    
    # Global user rate limit should still be enforced
    assert total_allowed <= 150, f"Global user rate limit bypassed: {total_allowed} requests"


@pytest.mark.critical
@pytest.mark.security
async def test_rate_limit_token_bucket_consistency():
    """Test rate limiting token bucket remains consistent under concurrent load."""
    backend_client = BackendClient()
    user_token = "valid_token_123"
    
    # Launch concurrent requests to test token bucket
    async def make_request():
        response = await backend_client.post("/api/chat", 
            headers={"Authorization": f"Bearer {user_token}"},
            json={"message": "test"})
        return response.status_code
    
    # Make 50 concurrent requests
    tasks = [make_request() for _ in range(50)]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Count successful vs rate-limited responses  
    success_count = sum(1 for r in responses if r == 200)
    rate_limited_count = sum(1 for r in responses if r == 429)
    
    # Should have consistent rate limiting (not all succeed or all fail)
    assert 10 <= success_count <= 40, f"Inconsistent rate limiting: {success_count} success"
    assert rate_limited_count > 0, "Rate limiting must engage under load"


@pytest.mark.critical
@pytest.mark.security
async def test_rate_limit_bypass_attempt_via_header_manipulation():
    """Test rate limiting can't be bypassed through header manipulation."""
    backend_client = BackendClient()
    
    # Attempt to bypass using various header tricks
    bypass_headers = [
        {"X-Forwarded-For": "127.0.0.1"},
        {"X-Real-IP": "localhost"},
        {"X-Originating-IP": "internal"},
        {"Client-IP": "bypass"}
    ]
    
    rate_limited_responses = []
    
    for headers in bypass_headers:
        # Make rapid requests with bypass headers
        for i in range(20):
            response = await backend_client.get("/api/health", headers=headers)
            if response.status_code == 429:
                rate_limited_responses.append(response)
                break
    
    # All bypass attempts should still hit rate limits
    assert len(rate_limited_responses) >= 3, "Header bypass attempts must be rate limited"


@pytest.mark.critical
@pytest.mark.security
async def test_quota_enforcement_prevents_resource_exhaustion():
    """Test quota enforcement prevents individual users from exhausting system resources."""
    rate_tester = RateLimitingTester()
    
    # Simulate user attempting to exhaust resources
    resource_intensive_user = "resource_abuser"
    
    # Track resource usage during quota testing
    resource_usage = []
    
    async def monitor_resources():
        while True:
            usage = await rate_tester.get_resource_usage()
            resource_usage.append(usage)
            await asyncio.sleep(0.1)
    
    # Start resource monitoring
    monitor_task = asyncio.create_task(monitor_resources())
    
    try:
        # Attempt resource exhaustion
        await rate_tester.test_resource_intensive_requests(
            user_id=resource_intensive_user,
            request_count=1000,
            concurrent_limit=50
        )
        
        # Stop monitoring
        monitor_task.cancel()
        
        # Check resource usage stayed within bounds
        max_cpu = max(usage.cpu_percent for usage in resource_usage)
        max_memory = max(usage.memory_percent for usage in resource_usage)
        
        assert max_cpu < 80, f"CPU usage too high: {max_cpu}%"
        assert max_memory < 70, f"Memory usage too high: {max_memory}%"
        
    finally:
        if not monitor_task.cancelled():
            monitor_task.cancel()
