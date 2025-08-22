"""Tests for service model classes."""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from datetime import UTC, datetime

# Add project root to path
from netra_backend.app.core.service_interfaces import ServiceHealth, ServiceMetrics

# Add project root to path


class TestServiceModels:
    """Test service model classes."""
    
    def test_service_health_creation(self):
        """Test ServiceHealth model creation."""
        health = ServiceHealth(
            service_name="test-service",
            status="healthy",
            timestamp=datetime.now(UTC),
            dependencies={"db": "healthy"},
            metrics={"requests": 100}
        )
        
        assert health.service_name == "test-service"
        assert health.status == "healthy"
        assert health.dependencies == {"db": "healthy"}
        assert health.metrics == {"requests": 100}
    
    def test_service_metrics_creation(self):
        """Test ServiceMetrics model creation."""
        metrics = ServiceMetrics(
            requests_total=100,
            requests_successful=95,
            requests_failed=5,
            average_response_time=0.25
        )
        
        assert metrics.requests_total == 100
        assert metrics.requests_successful == 95
        assert metrics.requests_failed == 5
        assert metrics.average_response_time == 0.25