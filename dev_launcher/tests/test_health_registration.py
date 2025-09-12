"""
Tests for health registration helper module.

This module tests the health monitoring registration functionality
for backend and frontend services.
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import unittest
from shared.isolated_environment import IsolatedEnvironment

from dev_launcher.health_registration import HealthRegistrationHelper


class TestHealthRegistrationHelper(SSotBaseTestCase):
    """Test cases for HealthRegistrationHelper."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock: Generic component isolation for controlled unit testing
        self.mock_health_monitor = Mock()
        self.helper = HealthRegistrationHelper(
            self.mock_health_monitor, 
            use_emoji=False
        )
    
    def test_register_backend_with_health_info(self):
        """Test backend registration with valid health info."""
        health_info = {'port': 8000}
        self.helper.register_backend(health_info)
        self.mock_health_monitor.register_service.assert_called_once()
        args = self.mock_health_monitor.register_service.call_args
        self.assertEqual(args[0][0], "Backend")
    
    def test_register_backend_without_health_info(self):
        """Test backend registration with no health info."""
        self.helper.register_backend(None)
        self.mock_health_monitor.register_service.assert_not_called()
    
    def test_register_frontend_with_health_info(self):
        """Test frontend registration with valid health info."""
        # Mock: Generic component isolation for controlled unit testing
        health_info = {'process': Mock()}
        self.helper.register_frontend(health_info)
        self.mock_health_monitor.register_service.assert_called_once()
        args = self.mock_health_monitor.register_service.call_args
        self.assertEqual(args[0][0], "Frontend")
    
    def test_register_frontend_without_health_info(self):
        """Test frontend registration with no health info."""
        self.helper.register_frontend(None)
        self.mock_health_monitor.register_service.assert_not_called()
    
    # Mock: Component isolation for testing without external dependencies
    def test_register_all_services(self, mock_print):
        """Test registering all services."""
        backend_info = {'port': 8000}
        # Mock: Generic component isolation for controlled unit testing
        frontend_info = {'process': Mock()}
        self.helper.register_all_services(backend_info, frontend_info)
        mock_print.assert_called_once()
        self.assertEqual(self.mock_health_monitor.register_service.call_count, 2)
    
    def test_health_check_creation(self):
        """Test health check callback creation."""
        health_info = {'port': 8000}
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.health_registration.create_url_health_check') as mock_create:
            mock_create.return_value = lambda: True
            self.helper.register_backend(health_info)
            mock_create.assert_called_once_with('http://localhost:8000/health/live')
    
    def test_max_failures_configuration(self):
        """Test max failures is properly configured."""
        health_info = {'port': 8000}
        self.helper.register_backend(health_info)
        kwargs = self.mock_health_monitor.register_service.call_args[1]
        self.assertEqual(kwargs['max_failures'], 5)


if __name__ == '__main__':
    unittest.main()