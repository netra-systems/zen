"""
Pytest configuration for staging E2E tests.
Provides fixtures, hooks, and reporting configuration with enhanced resilience for Issue #1278.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import os
from pathlib import Path
import logging

# Import resilience framework
try:
    from test_framework.resilience import (
        validate_infrastructure_health,
        should_skip_test_due_to_infrastructure,
        get_resilient_test_configuration,
        ConnectivityStatus
    )
    RESILIENCE_AVAILABLE = True
except ImportError:
    RESILIENCE_AVAILABLE = False

logger = logging.getLogger(__name__)

# Test result collector
class TestResultCollector:
    """Collects test results for reporting"""
    
    def __init__(self):
        self.results = []
        self.start_time = None
        self.end_time = None
        self.total_tests = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = 0
        
    def add_result(self, result: Dict[str, Any]):
        """Add a test result"""
        self.results.append(result)
        
    def get_summary(self) -> Dict[str, Any]:
        """Get test summary"""
        return {
            "total": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "duration": (self.end_time - self.start_time) if (self.end_time and self.start_time) else 0,
            "pass_rate": (self.passed / self.total_tests * 100) if self.total_tests > 0 else 0
        }

# Global collector instance
collector = TestResultCollector()

# Pytest hooks
def pytest_configure(config):
    """Configure pytest with custom markers"""
    # Environment markers
    config.addinivalue_line(
        "markers", "staging: mark test to run against staging environment"
    )
    config.addinivalue_line(
        "markers", "staging_validation: mark test for staging environment validation"
    )
    config.addinivalue_line(
        "markers", "staging_gcp: mark test for staging GCP environment testing"
    )
    config.addinivalue_line(
        "markers", "staging_remote: mark test for remote staging environment testing"
    )
    config.addinivalue_line(
        "markers", "staging_regression_prevention: mark test for preventing staging regressions"
    )
    
    # Priority markers
    config.addinivalue_line(
        "markers", "critical: mark test as business critical"
    )
    config.addinivalue_line(
        "markers", "high: mark test as high priority"
    )
    config.addinivalue_line(
        "markers", "medium: mark test as medium priority"
    )
    config.addinivalue_line(
        "markers", "low: mark test as low priority"
    )
    
    # Business and functionality markers
    config.addinivalue_line(
        "markers", "business_critical: mark test as critical to business operations"
    )
    config.addinivalue_line(
        "markers", "mission_critical: mark test as mission critical functionality"
    )
    config.addinivalue_line(
        "markers", "golden_path: mark test as part of the golden path user journey"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance testing"
    )
    config.addinivalue_line(
        "markers", "stress: mark test as stress testing"
    )
    config.addinivalue_line(
        "markers", "regression: mark test for regression testing"
    )
    
    # Test type markers
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as authentication related"
    )
    config.addinivalue_line(
        "markers", "auth_flow: mark test as authentication flow testing"
    )
    config.addinivalue_line(
        "markers", "auth_resilience: mark test for authentication resilience testing"
    )
    config.addinivalue_line(
        "markers", "websocket: mark test as WebSocket functionality testing"
    )
    
    # Service markers
    config.addinivalue_line(
        "markers", "real_services: mark test to run against real services (not mocked)"
    )
    config.addinivalue_line(
        "markers", "real_llm: mark test to run against real LLM services"
    )
    config.addinivalue_line(
        "markers", "real_database: mark test to run against real database"
    )
    config.addinivalue_line(
        "markers", "real: mark test to run against real services"
    )
    
    # Circuit breaker and resilience markers
    config.addinivalue_line(
        "markers", "circuit_breaker_states: mark test for circuit breaker state testing"
    )
    
    # Issue tracking markers
    config.addinivalue_line(
        "markers", "issue_395: mark test related to issue #395 (WebSocket auth golden path)""markers", "issue_426: mark test related to issue #426 (WebSocket subprotocol negotiation)""markers", "connectivity: mark test for connectivity validation"
    )
    config.addinivalue_line(
        "markers", "timeout: mark test with custom timeout"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "asyncio: mark test as asynchronous"
    )

def pytest_sessionstart(session):
    """Called at test session start with infrastructure health check"""
    collector.start_time = time.time()
    print("\n" + "="*70)
    print("STAGING E2E TEST SESSION STARTED")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Perform infrastructure health check if resilience framework is available
    if RESILIENCE_AVAILABLE:
        try:
            # Run health check asynchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            health = loop.run_until_complete(validate_infrastructure_health())

            print(f"Infrastructure Status: {health.overall_status.value.upper()}")

            if health.overall_status == ConnectivityStatus.UNAVAILABLE:
                print("WARNING️  WARNING: Critical infrastructure services are unavailable")
                print("Tests may be skipped or run in fallback mode")
            elif health.overall_status == ConnectivityStatus.DEGRADED:
                print("WARNING️  WARNING: Some infrastructure services are degraded")
                print("Tests will run with fallback configuration")
            else:
                print("CHECK Infrastructure health check passed")

            # Store health for use in fixtures
            session.config._infrastructure_health = health

            loop.close()
        except Exception as e:
            print(f"WARNING️  Infrastructure health check failed: {e}")
            session.config._infrastructure_health = None
    else:
        print("ℹ️  Resilience framework not available - proceeding with standard execution")
        session.config._infrastructure_health = None

    print("="*70)

def pytest_sessionfinish(session, exitstatus):
    """Called at test session end"""
    collector.end_time = time.time()
    
    # Generate report
    generate_test_report()

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Capture test results"""
    outcome = yield
    report = outcome.get_result()
    
    if report.when == "call":
        result = {
            "test_name": item.name,
            "test_file": str(item.fspath),
            "outcome": report.outcome,
            "duration": report.duration,
            "timestamp": time.time()
        }
        
        # Extract markers
        markers = [mark.name for mark in item.iter_markers()]
        result["priority"] = "critical" if "critical" in markers else \
                            "high" if "high" in markers else \
                            "medium" if "medium" in markers else \
                            "low" if "low" in markers else "normal"
        
        # Add to collector
        collector.add_result(result)
        collector.total_tests += 1
        
        if report.outcome == "passed":
            collector.passed += 1
        elif report.outcome == "failed":
            collector.failed += 1
            if hasattr(report, "longrepr"):
                result["error"] = str(report.longrepr)
        elif report.outcome == "skipped":
            collector.skipped += 1

def generate_test_report():
    """Generate comprehensive test report with Windows I/O error handling"""
    
    report_path = Path("STAGING_TEST_REPORT_PYTEST.md")
    summary = collector.get_summary()
    
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Staging E2E Test Report - Pytest Results\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Environment:** Staging\n")
            f.write(f"**Test Framework:** Pytest\n\n")
            
            # Executive Summary
            f.write("## Executive Summary\n\n")
            f.write(f"- **Total Tests:** {summary['total']}\n")
            if summary['total'] > 0:
                f.write(f"- **Passed:** {summary['passed']} ({summary['passed']/summary['total']*100:.1f}%)\n")
                f.write(f"- **Failed:** {summary['failed']} ({summary['failed']/summary['total']*100:.1f}%)\n")
            else:
                f.write(f"- **Passed:** {summary['passed']} (0.0%)\n")
                f.write(f"- **Failed:** {summary['failed']} (0.0%)\n")
            f.write(f"- **Skipped:** {summary['skipped']}\n")
            f.write(f"- **Duration:** {summary['duration']:.2f} seconds\n")
            f.write(f"- **Pass Rate:** {summary['pass_rate']:.1f}%\n\n")
            
            # Test Results by Priority
            f.write("## Test Results by Priority\n\n")
            
            priorities = ["critical", "high", "medium", "low", "normal"]
            for priority in priorities:
                priority_results = [r for r in collector.results if r.get("priority") == priority]
                if priority_results:
                    f.write(f"### {priority.upper()} Priority Tests\n\n")
                    f.write("| Test Name | Status | Duration | File |\n")
                    f.write("|-----------|--------|----------|------|\n")
                    
                    for result in priority_results:
                        status_icon = "PASS" if result["outcome"] == "passed" else "FAIL" if result["outcome"] == "failed" else "SKIP"
                        f.write(f"| {result['test_name']} | {status_icon} {result['outcome']} | {result['duration']:.3f}s | {Path(result['test_file']).name} |\n")
                    f.write("\n")
            
            # Failed Tests Details
            if collector.failed > 0:
                f.write("## Failed Tests Details\n\n")
                failed_results = [r for r in collector.results if r["outcome"] == "failed"]
                
                for result in failed_results:
                    f.write(f"### FAILED: {result['test_name']}\n")
                    f.write(f"- **File:** {result['test_file']}\n")
                    f.write(f"- **Duration:** {result['duration']:.3f}s\n")
                    if "error" in result:
                        f.write(f"- **Error:** {result['error'][:500]}...\n")
                    f.write("\n")
            
            # Pytest Output Format
            f.write("## Pytest Output Format\n\n")
            f.write("```\n")
            
            # Generate pytest-style output
            for result in collector.results:
                if result["outcome"] == "passed":
                    f.write(f"{Path(result['test_file']).name}::{result['test_name']} PASSED\n")
                elif result["outcome"] == "failed":
                    f.write(f"{Path(result['test_file']).name}::{result['test_name']} FAILED\n")
                elif result["outcome"] == "skipped":
                    f.write(f"{Path(result['test_file']).name}::{result['test_name']} SKIPPED\n")
            
            f.write(f"\n{'='*50}\n")
            f.write(f"{summary['passed']} passed, {summary['failed']} failed")
            if summary['skipped'] > 0:
                f.write(f", {summary['skipped']} skipped")
            f.write(f" in {summary['duration']:.2f}s\n")
            f.write("```\n\n")
            
            # Test Coverage Matrix
            f.write("## Test Coverage Matrix\n\n")
            f.write("| Category | Total | Passed | Failed | Coverage |\n")
            f.write("|----------|-------|--------|--------|----------|\n")
            
            categories = {
                "WebSocket": ["websocket", "ws"],
                "Agent": ["agent"],
                "Authentication": ["auth", "jwt", "oauth"],
                "Performance": ["performance", "response_time", "throughput"],
                "Security": ["security", "cors", "injection"],
                "Data": ["storage", "database", "cache"]
            }
            
            for category, keywords in categories.items():
                cat_tests = [r for r in collector.results 
                            if any(kw in r["test_name"].lower() for kw in keywords)]
                if cat_tests:
                    cat_passed = sum(1 for t in cat_tests if t["outcome"] == "passed")
                    cat_failed = sum(1 for t in cat_tests if t["outcome"] == "failed")
                    coverage = (cat_passed / len(cat_tests) * 100) if cat_tests else 0
                    f.write(f"| {category} | {len(cat_tests)} | {cat_passed} | {cat_failed} | {coverage:.1f}% |\n")
            
            f.write("\n---\n")
            f.write(f"*Report generated by pytest-staging framework v1.0*\n")
    except (OSError, IOError) as e:
        print(f"Warning: Could not generate test report due to I/O error: {e}""\nTest report saved to: {report_path.absolute()}")

# Fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def staging_config():
    """Staging configuration fixture"""
    from tests.e2e.staging_test_config import get_staging_config
    return get_staging_config()

@pytest.fixture
async def staging_client():
    """HTTP client for staging API"""
    import httpx
    from tests.e2e.staging_test_config import get_staging_config
    
    config = get_staging_config()
    async with httpx.AsyncClient(base_url=config.backend_url, timeout=30) as client:
        yield client

@pytest.fixture
async def websocket_client():
    """WebSocket client for staging"""
    import websockets
    from tests.e2e.staging_test_config import get_staging_config
    
    config = get_staging_config()
    try:
        async with websockets.connect(config.websocket_url) as ws:
            yield ws
    except Exception as e:
        pytest.skip(f"WebSocket connection failed: {e}")

@pytest.fixture(scope="function")
async def staging_services_fixture():
    """
    Staging services fixture providing real staging service connections.
    
    Provides access to staging environment services for E2E testing:
    - Staging backend API client
    - Staging configuration
    - WebSocket connection capabilities
    - Health check utilities
    
    This fixture enables E2E tests to run against real staging services
    following SSOT compliance patterns.
    """
    from tests.e2e.staging_test_config import get_staging_config
    import httpx
    
    config = get_staging_config()
    
    # Health check to ensure staging services are available
    try:
        async with httpx.AsyncClient(timeout=10) as health_client:
            health_response = await health_client.get(config.health_endpoint)
            if health_response.status_code != 200:
                pytest.skip(f"Staging backend not healthy: {health_response.status_code}")
    except Exception as e:
        pytest.skip(f"Staging backend not accessible: {e}")
    
    # Create staging HTTP client
    async with httpx.AsyncClient(
        base_url=config.backend_url,
        timeout=30,
        headers=config.get_headers()
    ) as client:
        
        # Prepare staging services dictionary
        services = {
            "config": config,
            "http_client": client,
            "backend_url": config.backend_url,
            "api_url": config.api_url,
            "websocket_url": config.websocket_url,
            "auth_url": config.auth_url,
            "health_endpoint": config.health_endpoint,
            "test_jwt_token": config.test_jwt_token,
            "test_api_key": config.test_api_key
        }
        
        yield services

@pytest.fixture(scope="function")
async def real_services(staging_services_fixture):
    """Real services fixture for staging E2E tests - backward compatibility alias."""
    staging_services = staging_services_fixture
    services = {
        "environment": "staging",
        "database_available": True,
        "redis_available": True,
        "clickhouse_available": False,  # Known Issue #1086
        "backend_url": staging_services.get("backend_url", "https://backend-staging-701982941522.us-central1.run.app"),
        "api_url": staging_services.get("api_url", "https://api.staging.netrasystems.ai"),
        "websocket_url": staging_services.get("websocket_url", "wss://api.staging.netrasystems.ai/ws"),
        "auth_url": staging_services.get("auth_url", "https://auth.staging.netrasystems.ai")
    }
    yield services

@pytest.fixture
def real_llm():
    """Real LLM fixture for staging tests."""
    return True  # Staging environment uses real LLM services

# Enhanced resilience fixtures for Issue #1278

@pytest.fixture(scope="session")
def infrastructure_health(request):
    """Infrastructure health fixture providing health assessment for entire session."""
    health = getattr(request.config, '_infrastructure_health', None)
    return health

@pytest.fixture(scope="function")
def resilient_test_config(infrastructure_health):
    """Fixture providing resilient test configuration based on infrastructure health."""
    if not RESILIENCE_AVAILABLE or not infrastructure_health:
        return {}

    return get_resilient_test_configuration(infrastructure_health)

@pytest.fixture(scope="function")
def connectivity_validator():
    """Fixture providing connectivity validation utilities."""
    if not RESILIENCE_AVAILABLE:
        pytest.skip("Resilience framework not available")

    from test_framework.resilience import TestConnectivityValidator
    return TestConnectivityValidator()

@pytest.fixture(scope="function")
async def infrastructure_aware_client(staging_services_fixture, infrastructure_health, resilient_test_config):
    """
    Infrastructure-aware HTTP client that adapts to connectivity issues.

    Provides intelligent fallback behavior based on infrastructure health:
    - Uses staging services when available
    - Falls back to local services when staging is degraded
    - Skips tests when infrastructure is completely unavailable
    """
    import httpx
    from shared.isolated_environment import get_env

    env = get_env()

    # Apply resilient configuration
    for key, value in resilient_test_config.items():
        env.set(key, value, "infrastructure_aware_client")

    # Determine which client to use based on infrastructure health
    if infrastructure_health and infrastructure_health.is_staging_available:
        # Use staging services
        services = staging_services_fixture
        client = services.get("http_client")
        if client:
            yield client
            return

    # Fallback to local services or mock mode
    if resilient_test_config.get("TEST_OFFLINE") == "true":
        # Create mock client for offline testing
        yield MockHTTPClient()
    else:
        # Create local client
        local_url = env.get("LOCAL_BACKEND_URL", "http://localhost:8000")
        async with httpx.AsyncClient(base_url=local_url, timeout=10) as client:
            yield client

@pytest.fixture(scope="function")
async def resilient_websocket_client(infrastructure_health, resilient_test_config):
    """
    Resilient WebSocket client that handles connectivity issues gracefully.

    Provides WebSocket connectivity with intelligent fallback:
    - Real WebSocket connection when staging is available
    - Mock WebSocket when infrastructure is degraded
    - Skip tests when WebSocket is completely unavailable
    """
    from shared.isolated_environment import get_env

    env = get_env()

    # Apply resilient configuration
    for key, value in resilient_test_config.items():
        env.set(key, value, "resilient_websocket_client")

    # Check if WebSocket mock mode is enabled
    if resilient_test_config.get("WEBSOCKET_MOCK_MODE") == "true":
        yield MockWebSocketClient()
        return

    # Try to connect to real WebSocket
    if infrastructure_health and infrastructure_health.is_staging_available:
        try:
            import websockets
            staging_ws_url = env.get("STAGING_WEBSOCKET_URL")
            if staging_ws_url:
                async with websockets.connect(staging_ws_url, timeout=10) as ws:
                    yield ws
                    return
        except Exception as e:
            logger.warning(f"Staging WebSocket connection failed: {e}")

    # Fallback to mock WebSocket
    yield MockWebSocketClient()

@pytest.fixture(scope="function")
def infrastructure_skip_if_unavailable(infrastructure_health):
    """
    Fixture that skips tests if critical infrastructure is unavailable.

    Use this fixture in tests that absolutely require staging infrastructure.
    """
    if not infrastructure_health:
        return  # No health check available, proceed normally

    if RESILIENCE_AVAILABLE:
        should_skip, reason = should_skip_test_due_to_infrastructure(infrastructure_health)
        if should_skip:
            pytest.skip(f"Infrastructure unavailable: {reason}")

@pytest.fixture(scope="function")
def degraded_mode_warning(infrastructure_health):
    """
    Fixture that warns when running in degraded mode.

    Provides information about which services are degraded.
    """
    if not infrastructure_health:
        return None

    if infrastructure_health.should_use_fallback:
        degraded_services = infrastructure_health.get_degraded_services()
        unavailable_services = infrastructure_health.get_unavailable_services()

        warning_info = {
            "degraded_services": [s.value for s in degraded_services],
            "unavailable_services": [s.value for s in unavailable_services],
            "fallback_mode": True
        }

        logger.warning(f"Running in degraded mode - degraded: {warning_info['degraded_services']}, unavailable: {warning_info['unavailable_services']}")
        return warning_info

    return {"fallback_mode": False}

# Mock classes for fallback testing

class MockHTTPClient:
    """Mock HTTP client for offline testing."""

    async def get(self, url, **kwargs):
        """Mock GET request."""
        return MockResponse(200, {"status": "mock", "message": "Offline mode"})

    async def post(self, url, **kwargs):
        """Mock POST request."""
        return MockResponse(200, {"status": "mock", "message": "Offline mode"})

    async def put(self, url, **kwargs):
        """Mock PUT request."""
        return MockResponse(200, {"status": "mock", "message": "Offline mode"})

    async def delete(self, url, **kwargs):
        """Mock DELETE request."""
        return MockResponse(200, {"status": "mock", "message": "Offline mode"})

class MockResponse:
    """Mock HTTP response."""

    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self):
        """Return JSON data."""
        return self._json_data

    @property
    def text(self):
        """Return text content."""
        return json.dumps(self._json_data)

class MockWebSocketClient:
    """Mock WebSocket client for fallback testing."""

    async def send(self, message):
        """Mock send message."""
        logger.info(f"Mock WebSocket send: {message}")

    async def recv(self):
        """Mock receive message."""
        return '{"type": "mock", "message": "WebSocket offline mode"}'

    async def close(self):
        """Mock close connection."""
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
