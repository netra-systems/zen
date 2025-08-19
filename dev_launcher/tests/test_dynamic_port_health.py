"""
Regression tests for dynamic port health checks.

Tests to ensure health checks work correctly with dynamically allocated ports.
"""

import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dev_launcher.startup_validator import StartupValidator


class TestDynamicPortHealthChecks(unittest.TestCase):
    """Test suite for dynamic port health check functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = StartupValidator(use_emoji=False)
        self.temp_dir = tempfile.mkdtemp()
        self.discovery_dir = Path(self.temp_dir) / ".service_discovery"
        self.discovery_dir.mkdir(exist_ok=True)
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_verify_auth_ready_with_dynamic_port(self):
        """Test auth service health check with dynamic port."""
        with patch('dev_launcher.utils.wait_for_service_with_details') as mock_wait:
            mock_wait.return_value = (True, "Success")
            
            # Test with custom port
            result = self.validator._verify_auth_ready(8082)
            
            mock_wait.assert_called_once_with(
                "http://localhost:8082/health", 
                timeout=30
            )
            self.assertTrue(result)
    
    def test_verify_backend_ready_with_dynamic_port(self):
        """Test backend service health check with dynamic port."""
        with patch('dev_launcher.utils.wait_for_service_with_details') as mock_wait:
            mock_wait.return_value = (True, "Success")
            
            # Test with dynamic port
            result = self.validator._verify_backend_ready(62832)
            
            mock_wait.assert_called_once_with(
                "http://localhost:62832/health/ready", 
                timeout=30
            )
            self.assertTrue(result)
    
    def test_verify_frontend_ready_with_dynamic_port(self):
        """Test frontend service health check with dynamic port."""
        with patch('dev_launcher.utils.wait_for_service_with_details') as mock_wait:
            mock_wait.return_value = (True, "Success")
            
            # Test with dynamic port
            result = self.validator._verify_frontend_ready(62837)
            
            mock_wait.assert_called_once_with(
                "http://localhost:62837", 
                timeout=60
            )
            self.assertTrue(result)
    
    @patch('pathlib.Path.cwd')
    def test_verify_all_services_ready_reads_discovery_files(self, mock_cwd):
        """Test that verify_all_services_ready reads port info from discovery files."""
        mock_cwd.return_value = Path(self.temp_dir)
        
        # Create mock discovery files
        auth_info = {"port": 8082, "url": "http://localhost:8082"}
        backend_info = {"port": 62832, "api_url": "http://localhost:62832"}
        frontend_info = {"port": 62837, "url": "http://localhost:62837"}
        
        # Write discovery files
        (self.discovery_dir / "auth.json").write_text(json.dumps(auth_info))
        (self.discovery_dir / "backend.json").write_text(json.dumps(backend_info))
        (self.discovery_dir / "frontend.json").write_text(json.dumps(frontend_info))
        
        with patch('dev_launcher.utils.wait_for_service_with_details') as mock_wait:
            mock_wait.return_value = (True, "Success")
            
            # Call the method
            result = self.validator.verify_all_services_ready()
            
            # Verify correct ports were used
            calls = mock_wait.call_args_list
            self.assertEqual(len(calls), 3)
            
            # Check auth call
            self.assertIn("8082", str(calls[0]))
            # Check backend call  
            self.assertIn("62832", str(calls[1]))
            # Check frontend call
            self.assertIn("62837", str(calls[2]))
            
            self.assertTrue(result)
    
    @patch('pathlib.Path.cwd')
    def test_verify_all_services_ready_fallback_to_defaults(self, mock_cwd):
        """Test fallback to default ports when discovery files don't exist."""
        mock_cwd.return_value = Path(self.temp_dir)
        
        with patch('dev_launcher.utils.wait_for_service_with_details') as mock_wait:
            mock_wait.return_value = (True, "Success")
            
            # Call without discovery files
            result = self.validator.verify_all_services_ready()
            
            # Verify default ports were used
            calls = mock_wait.call_args_list
            self.assertEqual(len(calls), 3)
            
            # Check default ports
            self.assertIn("8081", str(calls[0]))  # Auth default
            self.assertIn("8000", str(calls[1]))  # Backend default
            self.assertIn("3000", str(calls[2]))  # Frontend default
            
            self.assertTrue(result)
    
    @patch('pathlib.Path.cwd')
    def test_verify_all_services_handles_malformed_discovery_files(self, mock_cwd):
        """Test graceful handling of malformed discovery files."""
        mock_cwd.return_value = Path(self.temp_dir)
        
        # Write malformed JSON
        (self.discovery_dir / "auth.json").write_text("not valid json")
        (self.discovery_dir / "backend.json").write_text("{incomplete")
        
        with patch('dev_launcher.utils.wait_for_service_with_details') as mock_wait:
            mock_wait.return_value = (True, "Success")
            
            # Should not raise exception, should use defaults
            result = self.validator.verify_all_services_ready()
            
            # Verify default ports were used
            calls = mock_wait.call_args_list
            self.assertEqual(len(calls), 3)
            self.assertTrue(result)
    
    def test_extended_timeouts_are_applied(self):
        """Test that extended timeouts are properly applied."""
        with patch('dev_launcher.utils.wait_for_service_with_details') as mock_wait:
            mock_wait.return_value = (False, "Timeout")
            
            # Test auth timeout
            self.validator._verify_auth_ready()
            mock_wait.assert_called_with("http://localhost:8081/health", timeout=30)
            
            # Test backend timeout
            self.validator._verify_backend_ready()
            mock_wait.assert_called_with("http://localhost:8000/health/ready", timeout=30)
            
            # Test frontend timeout
            self.validator._verify_frontend_ready()
            mock_wait.assert_called_with("http://localhost:3000", timeout=60)


if __name__ == '__main__':
    unittest.main()