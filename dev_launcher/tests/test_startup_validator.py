"""
Tests for startup validator module.

This module tests the service startup and readiness validation functionality.
"""

import time
import unittest
from unittest.mock import MagicMock, Mock, patch

from dev_launcher.startup_validator import StartupValidator


class TestStartupValidator(unittest.TestCase):
    """Test cases for StartupValidator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = StartupValidator(use_emoji=False)
    
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.startup_validator.wait_for_service')
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.startup_validator.print_with_emoji')
    def test_verify_backend_ready_success(self, mock_print, mock_wait):
        """Test successful backend verification."""
        mock_wait.side_effect = [True, True]  # Ready check, auth check
        backend_info = {'api_url': 'http://localhost:8000'}
        result = self.validator.verify_backend_ready(backend_info)
        self.assertTrue(result)
        self.assertEqual(mock_wait.call_count, 2)
        self.assertIn('Backend is ready', str(mock_print.call_args_list))
    
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.startup_validator.wait_for_service')
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.startup_validator.print_with_emoji')
    def test_verify_backend_ready_failure(self, mock_print, mock_wait):
        """Test backend verification failure."""
        mock_wait.return_value = False
        backend_info = {'api_url': 'http://localhost:8000'}
        result = self.validator.verify_backend_ready(backend_info)
        self.assertFalse(result)
        mock_wait.assert_called_once()
    
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.startup_validator.wait_for_service')
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.startup_validator.print_with_emoji')
    def test_verify_auth_system_timeout(self, mock_print, mock_wait):
        """Test auth system verification timeout."""
        mock_wait.side_effect = [True, False]  # Ready ok, auth timeout
        backend_info = {'api_url': 'http://localhost:8000'}
        result = self.validator.verify_backend_ready(backend_info)
        self.assertFalse(result)
        self.assertIn('Auth config check timed out', str(mock_print.call_args_list))
    
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.utils.open_browser')
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.startup_validator.wait_for_service')
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.startup_validator.print_with_emoji')
    # Mock: Component isolation for testing without external dependencies
    @patch('time.sleep')
    def test_verify_frontend_ready_with_browser(self, mock_sleep, mock_print, mock_wait, mock_browser):
        """Test frontend verification with browser opening."""
        mock_wait.return_value = True
        result = self.validator.verify_frontend_ready(3000, no_browser=False)
        self.assertTrue(result)
        mock_browser.assert_called_once_with('http://localhost:3000')
        mock_sleep.assert_called()
    
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.utils.open_browser')
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.startup_validator.wait_for_service')
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.startup_validator.print_with_emoji')
    # Mock: Component isolation for testing without external dependencies
    @patch('time.sleep')
    def test_verify_frontend_ready_no_browser(self, mock_sleep, mock_print, mock_wait, mock_browser):
        """Test frontend verification without browser opening."""
        mock_wait.return_value = True
        result = self.validator.verify_frontend_ready(3000, no_browser=True)
        self.assertTrue(result)
        mock_browser.assert_not_called()
    
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.startup_validator.wait_for_service')
    # Mock: Component isolation for testing without external dependencies
    @patch('dev_launcher.startup_validator.print_with_emoji')
    # Mock: Component isolation for testing without external dependencies
    @patch('time.sleep')
    def test_verify_frontend_ready_timeout(self, mock_sleep, mock_print, mock_wait):
        """Test frontend verification timeout."""
        mock_wait.return_value = False
        result = self.validator.verify_frontend_ready(3000, no_browser=True)
        self.assertFalse(result)
        self.assertIn('Frontend readiness check timed out', str(mock_print.call_args_list))
    
    # Mock: Component isolation for testing without external dependencies
    @patch('time.sleep')
    def test_allow_nextjs_compile(self, mock_sleep):
        """Test Next.js compilation wait."""
        self.validator._allow_nextjs_compile()
        mock_sleep.assert_called_once_with(5)
    
    def test_url_construction(self):
        """Test correct URL construction."""
        # Mock: Component isolation for testing without external dependencies
        with patch('dev_launcher.startup_validator.wait_for_service') as mock_wait:
            mock_wait.return_value = True
            backend_info = {'api_url': 'http://localhost:8000'}
            self.validator.verify_backend_ready(backend_info)
            calls = mock_wait.call_args_list
            self.assertEqual(calls[0][0][0], 'http://localhost:8000/health/ready')
            self.assertEqual(calls[1][0][0], 'http://localhost:8000/auth/config')


if __name__ == '__main__':
    unittest.main()