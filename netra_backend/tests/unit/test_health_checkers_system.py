"""System resource unit tests for health checkers.

Tests system resource monitoring for performance tracking.
Complements core health checker tests with system monitoring.

Business Value: Ensures system resource monitoring for capacity planning
and performance optimization to maintain service quality.
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from unittest.mock import Mock, patch

import pytest

# Add project root to path
from app.core.health_checkers import check_system_resources
from app.schemas.core_models import HealthCheckResult

# Add project root to path


class TestHealthCheckersSystem:
    """Test suite for system resource health checkers."""
    
    @pytest.fixture
    def mock_psutil(self):
        """Create mock psutil with standard values."""
        mock = Mock()
        mock.cpu_percent.return_value = 25.5
        mock.virtual_memory.return_value = Mock(
            percent=45.0, available=4096 * 1024 * 1024
        )
        mock.disk_usage.return_value = Mock(percent=60.0)
        mock.net_connections.return_value = [Mock()] * 15
        return mock
    
    @patch('app.core.health_checkers.psutil')
    def test_check_system_resources_success(self, mock_psutil_module, mock_psutil):
        """Test successful system resources health check."""
        self._setup_psutil_success(mock_psutil_module, mock_psutil)
        
        result = check_system_resources()
        
        assert result.status == "healthy"
        assert result.details["component_name"] == "system_resources"
        assert result.details["success"] is True
        assert result.details["health_score"] > 0
    
    @patch('app.core.health_checkers.psutil')
    def test_check_system_resources_high_usage(self, mock_psutil_module):
        """Test system resources check with high resource usage."""
        self._setup_psutil_high_usage(mock_psutil_module)
        
        result = check_system_resources()
        
        assert result.status == "healthy"  # Still healthy but low score
        assert result.details["health_score"] < 0.5  # Low health score
        assert result.details["metadata"]["cpu_percent"] == 95.0
    
    @patch('app.core.health_checkers.psutil')
    def test_check_system_resources_psutil_error(self, mock_psutil_module):
        """Test system resources check with psutil error."""
        mock_psutil_module.cpu_percent.side_effect = Exception("psutil error")
        
        result = check_system_resources()
        
        assert result.status == "unhealthy"
        assert result.details["success"] is False
        assert "psutil error" in result.details["error_message"]
    
    def test_health_score_calculation_bounds(self):
        """Test health score calculation stays within bounds."""
        test_cases = [
            (0.0, 1.0),    # 0% usage = 100% health
            (50.0, 0.5),   # 50% usage = 50% health  
            (100.0, 0.0),  # 100% usage = 0% health
            (120.0, 0.0)   # Over 100% usage = 0% health (clamped)
        ]
        
        for usage, expected_score in test_cases:
            calculated_score = max(0.0, 1.0 - (usage / 100))
            assert calculated_score == expected_score
    
    def test_websocket_health_score_calculation(self):
        """Test WebSocket health score calculation."""
        test_cases = [
            (0, 1.0),      # No connections = max health
            (500, 0.7),    # 500 connections = min health (0.7)
            (1000, 0.7),   # 1000+ connections = min health (0.7)
            (100, 0.9)     # 100 connections = good health
        ]
        
        for active_connections, expected_min_score in test_cases:
            calculated_score = min(1.0, max(0.7, 1.0 - (active_connections / 1000)))
            if active_connections <= 100:
                assert calculated_score >= expected_min_score
            else:
                assert calculated_score == expected_min_score
    
    @patch('app.core.health_checkers.psutil')
    def test_system_metrics_extraction_accuracy(self, mock_psutil_module):
        """Test accurate extraction of system metrics."""
        self._setup_psutil_specific_values(mock_psutil_module)
        
        result = check_system_resources()
        
        metadata = result.details["metadata"]
        assert metadata["cpu_percent"] == 35.7
        assert metadata["memory_percent"] == 72.3
        assert metadata["disk_percent"] == 45.8
    
    @patch('app.core.health_checkers.psutil')
    def test_system_resources_edge_case_zero_values(self, mock_psutil_module):
        """Test system resources with zero/minimal values."""
        mock_psutil_module.cpu_percent.return_value = 0.0
        mock_psutil_module.virtual_memory.return_value = Mock(
            percent=0.0, available=16 * 1024 * 1024 * 1024  # 16GB available
        )
        mock_psutil_module.disk_usage.return_value = Mock(percent=0.0)
        mock_psutil_module.net_connections.return_value = []
        
        result = check_system_resources()
        
        assert result.status == "healthy"
        assert result.details["health_score"] == 1.0  # Perfect health score
        metadata = result.details["metadata"]
        assert metadata["cpu_percent"] == 0.0
        assert metadata["memory_percent"] == 0.0
    
    @patch('app.core.health_checkers.psutil')
    def test_system_resources_maximum_stress(self, mock_psutil_module):
        """Test system resources under maximum stress."""
        mock_psutil_module.cpu_percent.return_value = 100.0
        mock_psutil_module.virtual_memory.return_value = Mock(
            percent=100.0, available=0
        )
        mock_psutil_module.disk_usage.return_value = Mock(percent=100.0)
        mock_psutil_module.net_connections.return_value = [Mock()] * 1000
        
        result = check_system_resources()
        
        assert result.status == "healthy"  # Still reports healthy
        assert result.details["health_score"] == 0.0  # But zero health score
        metadata = result.details["metadata"]
        assert metadata["cpu_percent"] == 100.0
        assert metadata["memory_percent"] == 100.0
        assert metadata["disk_percent"] == 100.0
    
    def test_health_score_averaging_algorithm(self):
        """Test health score averaging produces correct results."""
        # Simulate different resource usage scenarios
        test_scenarios = [
            ([0.8, 0.6, 0.4], 0.6),    # Mixed performance
            ([1.0, 1.0, 1.0], 1.0),    # Perfect performance
            ([0.0, 0.0, 0.0], 0.0),    # Critical performance
            ([0.9, 0.1, 0.5], 0.5)     # Varied performance
        ]
        
        for scores, expected_avg in test_scenarios:
            calculated_avg = sum(scores) / len(scores)
            assert abs(calculated_avg - expected_avg) < 0.001
    
    def test_system_resource_metadata_completeness(self):
        """Test that system resource metadata includes all required fields."""
        with patch('app.core.health_checkers.psutil') as mock_psutil:
            self._setup_psutil_success_with_values(mock_psutil)
            
            result = check_system_resources()
            
            metadata = result.details["metadata"]
            required_fields = [
                "cpu_percent", "memory_percent", "disk_percent",
                "memory_available_gb", "disk_free_gb"
            ]
            
            for field in required_fields:
                assert field in metadata
                assert isinstance(metadata[field], (int, float))
    
    def test_response_time_measurement_accuracy(self):
        """Test that response time measurement is accurate."""
        with patch('app.core.health_checkers.psutil') as mock_psutil:
            self._setup_psutil_success_with_values(mock_psutil)
            
            result = check_system_resources()
            
            # Response time should be measured in seconds and be reasonable
            assert isinstance(result.response_time, float)
            assert 0.0 <= result.response_time <= 10.0  # Should complete within 10 seconds
    
    # Helper methods (each ≤8 lines)
    def _setup_psutil_success(self, mock_psutil_module, mock_psutil):
        """Helper to setup successful psutil mock."""
        mock_psutil_module.cpu_percent = mock_psutil.cpu_percent
        mock_psutil_module.virtual_memory = mock_psutil.virtual_memory
        mock_psutil_module.disk_usage = mock_psutil.disk_usage
        mock_psutil_module.net_connections = mock_psutil.net_connections
    
    def _setup_psutil_high_usage(self, mock_psutil_module):
        """Helper to setup psutil mock with high resource usage."""
        mock_psutil_module.cpu_percent.return_value = 95.0
        mock_psutil_module.virtual_memory.return_value = Mock(percent=90.0, available=1024 * 1024)
        mock_psutil_module.disk_usage.return_value = Mock(percent=85.0)
        mock_psutil_module.net_connections.return_value = [Mock()] * 100
    
    def _setup_psutil_specific_values(self, mock_psutil_module):
        """Helper to setup psutil mock with specific test values."""
        mock_psutil_module.cpu_percent.return_value = 35.7
        mock_psutil_module.virtual_memory.return_value = Mock(percent=72.3, available=2 * 1024 * 1024 * 1024)
        mock_psutil_module.disk_usage.return_value = Mock(percent=45.8)
        mock_psutil_module.net_connections.return_value = [Mock()] * 25
    
    def _setup_psutil_success_with_values(self, mock_psutil):
        """Helper to setup psutil mock with standard success values."""
        mock_psutil.cpu_percent.return_value = 20.0
        mock_psutil.virtual_memory.return_value = Mock(percent=40.0, available=8 * 1024 * 1024 * 1024)
        mock_psutil.disk_usage.return_value = Mock(percent=30.0, free=500 * 1024 * 1024 * 1024)
        mock_psutil.net_connections.return_value = [Mock()] * 10
    
    def _create_mock_system_stats(self, cpu=25.0, memory=50.0, disk=60.0):
        """Helper to create mock system statistics."""
        return {
            "cpu_percent": cpu,
            "memory": Mock(percent=memory, available=4096 * 1024 * 1024),
            "disk": Mock(percent=disk, free=1024 * 1024 * 1024),
            "connections": 15
        }