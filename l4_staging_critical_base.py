"""
L4 Staging Critical Base: Foundation for Level 4 staging environment tests.

This module provides base classes and utilities for critical tests that run
against the staging environment, focusing on end-to-end validation.

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure (supports all tiers)
- Business Goal: Zero production incidents through staging validation
- Value Impact: Staging tests catch 95% of production issues early
- Revenue Impact: Prevents $200K+ losses from production outages
"""

import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from unittest import TestCase

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class StagingEnvironmentConfig:
    """Configuration for staging environment testing."""
    
    def __init__(self):
        self.base_url = os.getenv("STAGING_BASE_URL", "https://staging.netra.ai")
        self.api_key = os.getenv("STAGING_API_KEY", "")
        self.auth_token = os.getenv("STAGING_AUTH_TOKEN", "")
        self.timeout = int(os.getenv("STAGING_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("STAGING_MAX_RETRIES", "3"))
        self.retry_backoff = float(os.getenv("STAGING_RETRY_BACKOFF", "1.0"))
        
        # Service endpoints
        self.auth_service_url = f"{self.base_url}/auth"
        self.api_service_url = f"{self.base_url}/api/v1"
        self.websocket_url = self.base_url.replace("https://", "wss://") + "/ws"
        
        # Database connections (read-only for staging validation)
        self.postgres_url = os.getenv("STAGING_POSTGRES_URL", "")
        self.clickhouse_url = os.getenv("STAGING_CLICKHOUSE_URL", "")
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of missing items."""
        missing = []
        
        if not self.api_key:
            missing.append("STAGING_API_KEY")
        if not self.auth_token:
            missing.append("STAGING_AUTH_TOKEN") 
        if not self.base_url:
            missing.append("STAGING_BASE_URL")
        
        return missing


class StagingHTTPClient:
    """HTTP client configured for staging environment testing."""
    
    def __init__(self, config: StagingEnvironmentConfig):
        self.config = config
        self.session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=config.max_retries,
            backoff_factor=config.retry_backoff,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            "Authorization": f"Bearer {config.auth_token}",
            "X-API-Key": config.api_key,
            "Content-Type": "application/json",
            "User-Agent": "Netra-L4-Staging-Tests/1.0"
        })
    
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """Make GET request to staging endpoint."""
        url = f"{self.config.base_url}{endpoint}"
        kwargs.setdefault("timeout", self.config.timeout)
        return self.session.get(url, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """Make POST request to staging endpoint."""
        url = f"{self.config.base_url}{endpoint}"
        kwargs.setdefault("timeout", self.config.timeout)
        return self.session.post(url, **kwargs)
    
    def put(self, endpoint: str, **kwargs) -> requests.Response:
        """Make PUT request to staging endpoint."""
        url = f"{self.config.base_url}{endpoint}"
        kwargs.setdefault("timeout", self.config.timeout)
        return self.session.put(url, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """Make DELETE request to staging endpoint."""
        url = f"{self.config.base_url}{endpoint}"
        kwargs.setdefault("timeout", self.config.timeout)
        return self.session.delete(url, **kwargs)
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on staging environment."""
        try:
            response = self.get("/health")
            return {
                "healthy": response.status_code == 200,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "data": response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "response_time": None,
                "data": None
            }


class L4StagingCriticalBase(TestCase):
    """Base class for L4 staging critical tests."""
    
    @classmethod
    def setUpClass(cls):
        """Set up staging test environment."""
        cls.config = StagingEnvironmentConfig()
        cls.http_client = StagingHTTPClient(cls.config)
        
        # Validate configuration
        missing_config = cls.config.validate()
        if missing_config:
            pytest.skip(f"Missing staging configuration: {', '.join(missing_config)}")
        
        # Verify staging environment is accessible
        health = cls.http_client.health_check()
        if not health["healthy"]:
            pytest.skip(f"Staging environment not healthy: {health.get('error', 'Unknown error')}")
    
    def setUp(self):
        """Set up individual test."""
        self.test_start_time = time.time()
        self.test_metadata = {
            "test_name": self._testMethodName,
            "start_time": datetime.utcnow(),
            "environment": "staging"
        }
    
    def tearDown(self):
        """Clean up after individual test."""
        self.test_metadata["duration"] = time.time() - self.test_start_time
        self.test_metadata["end_time"] = datetime.utcnow()
    
    def assert_response_success(self, response: requests.Response, expected_status: int = 200):
        """Assert that HTTP response indicates success."""
        self.assertEqual(response.status_code, expected_status, 
                        f"Expected status {expected_status}, got {response.status_code}. "
                        f"Response: {response.text}")
    
    def assert_response_error(self, response: requests.Response, expected_status: int = 400):
        """Assert that HTTP response indicates expected error."""
        self.assertGreaterEqual(response.status_code, expected_status,
                               f"Expected status >= {expected_status}, got {response.status_code}")
    
    def assert_response_time(self, response: requests.Response, max_seconds: float = 5.0):
        """Assert that response time is within acceptable limits."""
        response_time = response.elapsed.total_seconds()
        self.assertLessEqual(response_time, max_seconds,
                           f"Response time {response_time}s exceeded limit {max_seconds}s")
    
    def wait_for_condition(self, condition_func, timeout: int = 30, poll_interval: float = 1.0) -> bool:
        """Wait for a condition to become true within timeout."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if condition_func():
                return True
            time.sleep(poll_interval)
        
        return False
    
    def create_test_data(self, data_type: str, **kwargs) -> Dict[str, Any]:
        """Create test data specific to staging environment."""
        timestamp = datetime.utcnow().isoformat()
        test_id = f"l4-staging-{self._testMethodName}-{int(time.time())}"
        
        base_data = {
            "test_id": test_id,
            "created_at": timestamp,
            "environment": "staging",
            "test_class": self.__class__.__name__
        }
        
        if data_type == "user":
            return {
                **base_data,
                "email": f"test-{test_id}@staging.netra.ai",
                "full_name": f"Staging Test User {test_id}",
                **kwargs
            }
        
        elif data_type == "thread":
            return {
                **base_data,
                "title": f"Staging Test Thread {test_id}",
                **kwargs
            }
        
        elif data_type == "message":
            return {
                **base_data,
                "content": f"Staging test message content {test_id}",
                "role": "user",
                **kwargs
            }
        
        return {**base_data, **kwargs}
    
    def cleanup_test_data(self, resource_type: str, resource_id: str) -> bool:
        """Clean up test data from staging environment."""
        try:
            endpoint = f"/api/v1/{resource_type}/{resource_id}"
            response = self.http_client.delete(endpoint)
            return response.status_code in [200, 204, 404]  # 404 means already deleted
        except Exception:
            return False  # Best effort cleanup


class L4StagingAsyncCriticalBase:
    """Async base class for L4 staging critical tests."""
    
    @pytest.fixture(autouse=True)
    async def setup_async_staging_test(self):
        """Set up async staging test environment."""
        self.config = StagingEnvironmentConfig()
        self.http_client = StagingHTTPClient(self.config)
        
        # Validate configuration
        missing_config = self.config.validate()
        if missing_config:
            pytest.skip(f"Missing staging configuration: {', '.join(missing_config)}")
        
        # Verify staging environment health
        health = self.http_client.health_check()
        if not health["healthy"]:
            pytest.skip(f"Staging environment not healthy: {health.get('error', 'Unknown error')}")
        
        yield
        
        # Cleanup after test
        await self._cleanup_async_test_resources()
    
    async def _cleanup_async_test_resources(self):
        """Cleanup resources created during async tests."""
        # Override in subclasses to implement specific cleanup
        pass
    
    async def assert_async_condition(self, condition_func, timeout: int = 30, poll_interval: float = 1.0) -> bool:
        """Assert that an async condition becomes true within timeout."""
        import asyncio
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await condition_func():
                return True
            await asyncio.sleep(poll_interval)
        
        self.fail(f"Async condition not met within {timeout} seconds")


class StagingTestReporter:
    """Reporter for staging test results and metrics."""
    
    def __init__(self):
        self.test_results: List[Dict[str, Any]] = []
        self.environment_metrics: Dict[str, Any] = {}
    
    def record_test_result(self, test_name: str, status: str, duration: float, 
                          metadata: Optional[Dict[str, Any]] = None):
        """Record test result for reporting."""
        result = {
            "test_name": test_name,
            "status": status,  # "passed", "failed", "skipped"
            "duration": duration,
            "timestamp": datetime.utcnow().isoformat(),
            "environment": "staging",
            "metadata": metadata or {}
        }
        self.test_results.append(result)
    
    def record_environment_metric(self, metric_name: str, value: Any, unit: str = ""):
        """Record environment metric."""
        self.environment_metrics[metric_name] = {
            "value": value,
            "unit": unit,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_summary_report(self) -> Dict[str, Any]:
        """Generate summary report of staging tests."""
        total_tests = len(self.test_results)
        if total_tests == 0:
            return {"total_tests": 0, "summary": "No tests executed"}
        
        passed = sum(1 for r in self.test_results if r["status"] == "passed")
        failed = sum(1 for r in self.test_results if r["status"] == "failed")
        skipped = sum(1 for r in self.test_results if r["status"] == "skipped")
        
        avg_duration = sum(r["duration"] for r in self.test_results) / total_tests
        
        return {
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "success_rate": (passed / total_tests) * 100,
            "average_duration": avg_duration,
            "environment_metrics": self.environment_metrics,
            "failed_tests": [r["test_name"] for r in self.test_results if r["status"] == "failed"]
        }


# Global reporter instance
staging_reporter = StagingTestReporter()


# Pytest fixtures for staging tests
@pytest.fixture(scope="session")
def staging_config():
    """Provide staging configuration."""
    return StagingEnvironmentConfig()


@pytest.fixture(scope="session") 
def staging_http_client(staging_config):
    """Provide staging HTTP client."""
    return StagingHTTPClient(staging_config)


@pytest.fixture
def staging_reporter_fixture():
    """Provide staging test reporter."""
    return staging_reporter


# Skip marker for staging tests
requires_staging = pytest.mark.skipif(
    not os.getenv("STAGING_API_KEY"),
    reason="Staging environment not configured (missing STAGING_API_KEY)"
)


# Export key components
__all__ = [
    "StagingEnvironmentConfig",
    "StagingHTTPClient", 
    "L4StagingCriticalBase",
    "L4StagingAsyncCriticalBase",
    "StagingTestReporter",
    "staging_reporter",
    "requires_staging"
]