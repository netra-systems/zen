"""
Health Monitoring Test Suite

Comprehensive test suite for the staging environment health monitoring system.
Includes tests for:
- Staging health monitor core functionality
- Health check API endpoints
- Automated health checks with deployment integration
- Dashboard and alerting functionality
- Docker integration
"""

__version__ = "1.0.0"
__author__ = "Netra Health Monitoring Team"

# Test categories
TEST_CATEGORIES = [
    "unit",           # Unit tests for individual components
    "integration",    # Integration tests for component interactions  
    "api",           # API endpoint tests
    "deployment",    # Deployment integration tests
    "performance",   # Performance and load tests
    "end_to_end"     # Complete workflow tests
]

# Test priority levels
TEST_PRIORITIES = {
    "critical": [
        "test_staging_health_monitor.py::TestWebSocketHealthChecker::test_websocket_health_check_success",
        "test_health_api_endpoints.py::TestStagingHealthOverview::test_get_staging_health_overview_success", 
        "test_automated_health_checks.py::TestPreDeploymentChecks::test_pre_deployment_checks_success",
        "test_automated_health_checks.py::TestPostDeploymentVerification::test_post_deployment_verification_success"
    ],
    "high": [
        "test_staging_health_monitor.py::TestResourceHealthChecker",
        "test_staging_health_monitor.py::TestConfigurationHealthChecker", 
        "test_health_api_endpoints.py::TestWebSocketHealthEndpoint",
        "test_health_api_endpoints.py::TestDatabaseHealthEndpoint"
    ],
    "medium": [
        "test_staging_health_monitor.py::TestPerformanceMetricsChecker",
        "test_health_api_endpoints.py::TestServicesHealthEndpoint",
        "test_automated_health_checks.py::TestContinuousMonitoring"
    ]
}

# Test configuration
TEST_CONFIG = {
    "timeout": 30,          # Default test timeout in seconds
    "retry_count": 3,       # Number of retries for flaky tests
    "parallel_workers": 4,  # Number of parallel test workers
    "coverage_threshold": 85  # Minimum code coverage percentage
}

# Mock data for tests
MOCK_HEALTH_DATA = {
    "healthy_comprehensive": {
        "status": "healthy",
        "service": "staging_environment", 
        "version": "1.0.0",
        "checks": {
            "staging_websocket": {
                "success": True,
                "health_score": 1.0,
                "response_time_ms": 50.0
            },
            "database_postgres": {
                "success": True,
                "health_score": 0.95,
                "response_time_ms": 25.0
            },
            "service_auth_service": {
                "success": True,
                "health_score": 0.98,
                "response_time_ms": 100.0
            }
        },
        "staging_analysis": {
            "business_impact": {"impact_level": "none"},
            "trend_analysis": {"overall_trend": "stable"},
            "remediation_suggestions": [],
            "failure_prediction": {"failure_prediction_available": False}
        },
        "alert_status": {
            "alerts_active": False,
            "alert_count": 0,
            "alert_severity": "none"
        }
    },
    
    "unhealthy_critical": {
        "status": "unhealthy",
        "service": "staging_environment",
        "version": "1.0.0", 
        "checks": {
            "staging_websocket": {
                "success": False,
                "health_score": 0.0,
                "response_time_ms": 999.0
            },
            "database_postgres": {
                "success": False,
                "health_score": 0.0,
                "response_time_ms": 999.0
            },
            "service_auth_service": {
                "success": False,
                "health_score": 0.0,
                "response_time_ms": 999.0
            }
        },
        "staging_analysis": {
            "business_impact": {
                "impact_level": "critical",
                "estimated_user_impact_percent": 100
            },
            "failure_prediction": {
                "failure_prediction_available": True,
                "overall_risk_level": "high"
            },
            "remediation_suggestions": [
                {
                    "action": "restart_websocket_service",
                    "description": "Restart WebSocket service to restore connectivity",
                    "urgency": "high"
                }
            ]
        },
        "alert_status": {
            "alerts_active": True,
            "alert_count": 3,
            "alert_severity": "critical"
        }
    }
}

# Test utilities
def get_mock_health_data(scenario="healthy_comprehensive"):
    """Get mock health data for testing scenarios."""
    import copy
    import time
    
    data = copy.deepcopy(MOCK_HEALTH_DATA.get(scenario, MOCK_HEALTH_DATA["healthy_comprehensive"]))
    data["timestamp"] = time.time()
    return data

def create_test_deployment_id():
    """Create a test deployment ID."""
    import uuid
    return f"test-deployment-{uuid.uuid4().hex[:8]}"

def setup_test_environment():
    """Setup test environment configuration."""
    import os
    
    # Set test environment variables
    test_env_vars = {
        "ENVIRONMENT": "test",
        "DATABASE_URL": "postgresql://test:test@localhost:5434/netra_test",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6381",
        "JWT_SECRET_KEY": "test-jwt-secret-key-for-testing-only",
        "HEALTH_API_TOKEN": "test-health-api-token",
        "WEBHOOK_SECRET": "test-webhook-secret"
    }
    
    for key, value in test_env_vars.items():
        os.environ[key] = value

def teardown_test_environment():
    """Teardown test environment configuration."""
    import os
    
    test_env_vars = [
        "ENVIRONMENT", "DATABASE_URL", "REDIS_HOST", "REDIS_PORT",
        "JWT_SECRET_KEY", "HEALTH_API_TOKEN", "WEBHOOK_SECRET"
    ]
    
    for var in test_env_vars:
        os.environ.pop(var, None)

# Test fixtures and helpers
class HealthMonitoringTestHelper:
    """Helper class for health monitoring tests."""
    
    @staticmethod
    def create_mock_health_checker():
        """Create a mock health checker for testing."""
        from unittest.mock import MagicMock
        
        mock_checker = MagicMock()
        mock_checker.check_health.return_value = get_mock_health_data()
        return mock_checker
    
    @staticmethod
    def create_mock_http_response(data=None, status_code=200):
        """Create a mock HTTP response for testing."""
        from unittest.mock import MagicMock
        
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.json.return_value = data or get_mock_health_data()
        mock_response.raise_for_status.return_value = None
        return mock_response
    
    @staticmethod
    def assert_health_result_structure(result):
        """Assert that a health result has the expected structure."""
        required_fields = ["status", "timestamp"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        if "checks" in result:
            for check_name, check_result in result["checks"].items():
                if isinstance(check_result, dict):
                    assert "success" in check_result, f"Missing 'success' field in check: {check_name}"
    
    @staticmethod
    def assert_api_response_structure(response_data, endpoint_name):
        """Assert that an API response has the expected structure."""
        assert "timestamp" in response_data
        
        if "response_metadata" in response_data:
            metadata = response_data["response_metadata"]
            assert metadata["endpoint"] == endpoint_name
            assert "response_time_ms" in metadata

# Export main components
__all__ = [
    "TEST_CATEGORIES",
    "TEST_PRIORITIES", 
    "TEST_CONFIG",
    "MOCK_HEALTH_DATA",
    "get_mock_health_data",
    "create_test_deployment_id",
    "setup_test_environment",
    "teardown_test_environment",
    "HealthMonitoringTestHelper"
]