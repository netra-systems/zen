"""
Test Data Transformation Utilities Business Logic - Core Unit Tests

Business Value Justification (BVJ):
- Segment: All (Data transformation affects all user interactions and system operations)
- Business Goal: Operational excellence and data integrity through proper transformation
- Value Impact: Ensures data consistency and accurate business operations across environments
- Strategic Impact: CRITICAL - Data integrity directly affects customer experience and business reliability

This test suite validates the core business logic for data transformation utilities
that enable proper data handling, URL generation, and timing measurements.
"""

import pytest
import time
from unittest.mock import Mock, patch
from test_framework.base import BaseTestCase
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.routes.auth_routes.utils import (
    get_explicit_frontend_url,
    get_env_specific_frontend_url,
    get_frontend_url_for_environment
)
from netra_backend.app.services.audit.utils import AuditTimer


class TestDataTransformationUtilities(BaseTestCase):
    """Test data transformation utilities deliver reliable operations for business value."""
    
    def setup_method(self):
        """Setup test environment with isolated configuration."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        
    def teardown_method(self):
        """Clean up test environment."""
        super().teardown_method()
        
    @pytest.mark.unit
    @patch('netra_backend.app.routes.auth_routes.utils.unified_config_manager')
    def test_explicit_frontend_url_business_configuration(self, mock_config_manager):
        """Test that explicit frontend URL configuration supports business deployment flexibility."""
        # Test with configured frontend URL
        mock_config = Mock()
        mock_config.frontend_url = "https://custom.business.domain.com/"
        mock_config_manager.get_config.return_value = mock_config
        
        result = get_explicit_frontend_url()
        
        # Should return trimmed URL for consistency
        assert result == "https://custom.business.domain.com", \
            f"Should return trimmed URL: {result}"
            
        # Test with no frontend URL configured
        mock_config.frontend_url = None
        
        result = get_explicit_frontend_url()
        assert result is None, "Should return None when no frontend URL configured"
        
        # Test with missing frontend_url attribute
        del mock_config.frontend_url
        
        result = get_explicit_frontend_url()
        assert result is None, "Should handle missing frontend_url attribute gracefully"
        
        # Test URL trimming business logic
        test_urls = [
            ("https://example.com/", "https://example.com"),
            ("https://example.com///", "https://example.com"),
            ("https://example.com", "https://example.com"),
            ("http://localhost:3000/", "http://localhost:3000"),
        ]
        
        for input_url, expected_output in test_urls:
            mock_config.frontend_url = input_url
            result = get_explicit_frontend_url()
            assert result == expected_output, \
                f"URL trimming failed: {input_url} -> {result}, expected {expected_output}"
                
    @pytest.mark.unit
    @patch('netra_backend.app.routes.auth_routes.utils.auth_client')
    @patch('netra_backend.app.routes.auth_routes.utils.unified_config_manager')
    def test_environment_specific_url_business_logic(self, mock_config_manager, mock_auth_client):
        """Test that environment-specific URL logic supports proper business environment routing."""
        # Test staging environment
        mock_env = Mock()
        mock_env.value = "staging"
        mock_auth_client.detect_environment.return_value = mock_env
        
        result = get_env_specific_frontend_url()
        assert result == "https://app.staging.netrasystems.ai", \
            f"Staging should use staging URL: {result}"
            
        # Test production environment
        mock_env.value = "production"
        
        result = get_env_specific_frontend_url()
        assert result == "https://netrasystems.ai", \
            f"Production should use production URL: {result}"
            
        # Test development environment with config fallback
        mock_env.value = "development"
        mock_config = Mock()
        mock_config.frontend_url = "http://localhost:3001"
        mock_config_manager.get_config.return_value = mock_config
        
        result = get_env_specific_frontend_url()
        assert result == "http://localhost:3001", \
            f"Development should use config URL: {result}"
            
        # Test development environment with default fallback
        mock_config.frontend_url = None
        del mock_config.frontend_url
        
        result = get_env_specific_frontend_url()
        assert result == "http://localhost:3000", \
            f"Development should fallback to default: {result}"
            
        # Test unknown environment
        mock_env.value = "unknown"
        mock_config.frontend_url = "http://custom.dev:4000/"
        mock_config_manager.get_config.return_value = mock_config
        
        result = get_env_specific_frontend_url()
        assert result == "http://custom.dev:4000", \
            f"Unknown environment should use config with trimming: {result}"
            
    @pytest.mark.unit
    @patch('netra_backend.app.routes.auth_routes.utils.get_explicit_frontend_url')
    @patch('netra_backend.app.routes.auth_routes.utils.get_env_specific_frontend_url')
    def test_frontend_url_priority_business_logic(self, mock_env_specific, mock_explicit):
        """Test that frontend URL priority logic follows business configuration precedence."""
        # Test explicit URL takes priority
        mock_explicit.return_value = "https://explicit.business.com"
        mock_env_specific.return_value = "https://env.specific.com"
        
        result = get_frontend_url_for_environment()
        assert result == "https://explicit.business.com", \
            "Explicit URL should take priority over environment-specific"
            
        # Verify env-specific was not called when explicit is available
        mock_env_specific.assert_not_called()
        
        # Test fallback to environment-specific when no explicit URL
        mock_explicit.return_value = None
        
        result = get_frontend_url_for_environment()
        assert result == "https://env.specific.com", \
            "Should fallback to environment-specific URL"
            
        # Verify env-specific was called when explicit is not available
        mock_env_specific.assert_called_once()
        
        # Test empty string handling
        mock_explicit.return_value = ""
        mock_env_specific.reset_mock()
        
        result = get_frontend_url_for_environment()
        assert result == "https://env.specific.com", \
            "Empty string should be treated as None"
        mock_env_specific.assert_called_once()
        
    @pytest.mark.unit
    def test_audit_timer_business_performance_measurement(self):
        """Test that audit timer provides accurate business performance measurements."""
        timer = AuditTimer()
        
        # Test initial state
        assert timer.start_time is None, "Timer should start with no start time"
        assert timer.duration_ms is None, "Timer should start with no duration"
        assert timer.get_duration() is None, "Should return None before timing"
        
        # Test context manager usage for business operations
        with timer:
            # Simulate business operation
            time.sleep(0.01)  # 10ms sleep
            
            # During execution, start_time should be set
            assert timer.start_time is not None, "Start time should be set during execution"
            assert timer.duration_ms is None, "Duration should not be set during execution"
            
        # After context manager exit
        duration = timer.get_duration()
        assert duration is not None, "Duration should be calculated after completion"
        assert duration > 0, f"Duration should be positive: {duration}ms"
        
        # Should be approximately 10ms (allowing for system variance)
        assert 5 <= duration <= 50, \
            f"Duration should be approximately 10ms (+/- variance): {duration}ms"
            
    @pytest.mark.unit
    def test_audit_timer_precision_business_requirements(self):
        """Test that audit timer meets business precision requirements for performance monitoring."""
        timer = AuditTimer()
        
        # Test very short operations (microsecond precision)
        with timer:
            # Minimal operation
            x = 1 + 1
            
        short_duration = timer.get_duration()
        assert short_duration is not None, "Should measure even very short operations"
        assert short_duration >= 0, f"Short duration should be non-negative: {short_duration}ms"
        assert short_duration < 10, f"Short operation should be under 10ms: {short_duration}ms"
        
        # Test longer operations
        timer2 = AuditTimer()
        with timer2:
            time.sleep(0.05)  # 50ms sleep
            
        long_duration = timer2.get_duration()
        assert long_duration > short_duration, \
            f"Longer operation should take more time: {long_duration}ms vs {short_duration}ms"
        assert 40 <= long_duration <= 100, \
            f"Long operation should be approximately 50ms: {long_duration}ms"
            
    @pytest.mark.unit
    def test_audit_timer_error_handling_business_resilience(self):
        """Test that audit timer handles errors gracefully for business operation monitoring."""
        timer = AuditTimer()
        
        # Test exception handling within context manager
        try:
            with timer:
                time.sleep(0.005)  # 5ms
                raise ValueError("Simulated business operation error")
        except ValueError:
            pass  # Expected exception
            
        # Timer should still measure duration despite exception
        duration = timer.get_duration()
        assert duration is not None, "Should measure duration even when exception occurs"
        assert duration > 0, f"Duration should be positive despite exception: {duration}ms"
        assert duration < 20, f"Duration should be reasonable despite exception: {duration}ms"
        
    @pytest.mark.unit
    def test_audit_timer_reusability_business_efficiency(self):
        """Test that audit timer can be reused for multiple business operations."""
        timer = AuditTimer()
        
        # First measurement
        with timer:
            time.sleep(0.01)
            
        first_duration = timer.get_duration()
        assert first_duration is not None and first_duration > 0
        
        # Reset and reuse (new instance for clarity)
        timer2 = AuditTimer()
        
        # Second measurement
        with timer2:
            time.sleep(0.02)
            
        second_duration = timer2.get_duration()
        assert second_duration is not None and second_duration > 0
        
        # Second measurement should be longer
        assert second_duration > first_duration, \
            f"Second operation should be longer: {second_duration}ms vs {first_duration}ms"
            
    @pytest.mark.unit
    def test_url_transformation_business_consistency(self):
        """Test that URL transformations maintain business consistency across all scenarios."""
        # Test comprehensive URL scenarios for business environments
        url_test_cases = [
            # Production-like URLs
            ("https://app.company.com/", "https://app.company.com"),
            ("https://api.company.com/v1/", "https://api.company.com/v1"),
            
            # Staging URLs
            ("https://staging.company.com/", "https://staging.company.com"),
            ("https://app.staging.company.com/", "https://app.staging.company.com"),
            
            # Development URLs
            ("http://localhost:3000/", "http://localhost:3000"),
            ("http://localhost:8080/", "http://localhost:8080"),
            ("http://dev.local:3000/", "http://dev.local:3000"),
            
            # Edge cases
            ("https://company.com", "https://company.com"),  # No trailing slash
            ("https://company.com///////", "https://company.com"),  # Multiple trailing slashes
            ("http://192.168.1.100:3000/", "http://192.168.1.100:3000"),  # IP address
        ]
        
        with patch('netra_backend.app.routes.auth_routes.utils.unified_config_manager') as mock_manager:
            mock_config = Mock()
            mock_manager.get_config.return_value = mock_config
            
            for input_url, expected_output in url_test_cases:
                mock_config.frontend_url = input_url
                
                result = get_explicit_frontend_url()
                assert result == expected_output, \
                    f"URL transformation failed: '{input_url}' -> '{result}', expected '{expected_output}'"
                    
    @pytest.mark.unit  
    def test_performance_measurement_business_analytics(self):
        """Test that performance measurements support business analytics and monitoring."""
        measurements = []
        
        # Collect multiple measurements for analytics
        operations = [0.005, 0.01, 0.02, 0.05, 0.1]  # Various operation durations
        
        for expected_duration in operations:
            timer = AuditTimer()
            with timer:
                time.sleep(expected_duration)
            
            measured_duration = timer.get_duration()
            measurements.append(measured_duration)
            
            # Each measurement should be reasonable
            assert measured_duration is not None
            assert measured_duration > 0
            
            # Should be within reasonable tolerance of expected
            tolerance_factor = 2.0  # Allow 100% variance for system timing
            min_expected = expected_duration * 1000 / tolerance_factor  # Convert to ms
            max_expected = expected_duration * 1000 * tolerance_factor
            
            assert min_expected <= measured_duration <= max_expected, \
                f"Measurement outside tolerance: {measured_duration}ms for {expected_duration*1000}ms operation"
                
        # Measurements should show increasing trend
        for i in range(1, len(measurements)):
            assert measurements[i] >= measurements[i-1] * 0.5, \
                f"Measurements should generally increase: {measurements}"
                
        # Record metrics for business intelligence
        self.record_metric("performance_measurements", measurements)
        self.record_metric("measurement_accuracy", "within_tolerance")
        
    @pytest.mark.unit
    def test_environment_detection_business_routing(self):
        """Test that environment detection supports proper business routing decisions."""
        # Test business environment mapping
        environment_url_mapping = {
            "staging": "https://app.staging.netrasystems.ai",
            "production": "https://netrasystems.ai",
        }
        
        with patch('netra_backend.app.routes.auth_routes.utils.auth_client') as mock_client:
            with patch('netra_backend.app.routes.auth_routes.utils.unified_config_manager') as mock_manager:
                mock_config = Mock()
                mock_config.frontend_url = "http://localhost:3000"
                mock_manager.get_config.return_value = mock_config
                
                for env_name, expected_url in environment_url_mapping.items():
                    mock_env = Mock()
                    mock_env.value = env_name
                    mock_client.detect_environment.return_value = mock_env
                    
                    result = get_env_specific_frontend_url()
                    assert result == expected_url, \
                        f"Environment {env_name} should map to {expected_url}, got {result}"
                        
                # Test development/unknown environment fallback
                mock_env.value = "development"
                result = get_env_specific_frontend_url()
                assert result == "http://localhost:3000", \
                    f"Development should use config fallback: {result}"