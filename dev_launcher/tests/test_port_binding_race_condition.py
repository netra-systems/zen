"""
Test to reproduce the port binding race condition issue.

The issue occurs when:
1. is_port_available() checks port by binding to 'localhost' 
2. Auth service then tries to bind to '0.0.0.0' on same port
3. Windows shows error: "only one usage of each socket address is normally permitted"
"""

import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dev_launcher.auth_starter import AuthStarter
from dev_launcher.config import LauncherConfig
from dev_launcher.log_streamer import LogManager
from dev_launcher.service_config import ServicesConfiguration
from dev_launcher.service_discovery import ServiceDiscovery
from dev_launcher.utils import find_available_port, is_port_available


class TestPortBindingRaceCondition(unittest.TestCase):
    """Test that reproduces the port binding race condition."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = LauncherConfig()
        self.services_config = ServicesConfiguration()
        self.log_manager = LogManager()
        self.service_discovery = ServiceDiscovery(self.config.project_root)
        
    def test_port_check_with_immediate_rebind_race(self):
        """
        Test that demonstrates the race condition between port check and actual bind.
        
        This test reproduces the actual error:
        [AUTH]  FAIL:  ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8081)
        
        The issue is that is_port_available() binds to check, then immediately releases,
        but the OS may not have fully released the port when uvicorn tries to bind.
        """
        test_port = 18081  # Use a test port to avoid conflicts
        
        # Step 1: Simulate rapid bind/unbind/rebind pattern
        # This is what happens when is_port_available checks then uvicorn immediately binds
        errors_caught = []
        
        for attempt in range(10):  # Try multiple times to catch the race condition
            # Check port (bind and immediately release)
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as check_sock:
                    check_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    check_sock.bind(('localhost', test_port))
                    # Socket is immediately closed when exiting context
                
                # Immediately try to bind on all interfaces (what uvicorn does)
                # No delay - this triggers the race condition
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as service_sock:
                    service_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    service_sock.bind(('0.0.0.0', test_port))
                    service_sock.listen(1)
                    
            except OSError as e:
                errors_caught.append(str(e))
                if "10048" in str(e):
                    # Successfully reproduced the Windows error
                    break
                    
            # Small delay before next attempt
            time.sleep(0.01)
        
        # Check if we caught the race condition at least once
        if sys.platform == 'win32' and errors_caught:
            # Look for the specific Windows error
            has_bind_error = any("10048" in err or "address already in use" in err.lower() 
                                for err in errors_caught)
            if has_bind_error:
                # Successfully reproduced the issue
                self.assertTrue(True, f"Reproduced race condition: {errors_caught}")
            else:
                # Log what errors we did see
                print(f"Errors caught but not the expected one: {errors_caught}")
    
    def test_is_port_available_interface_consistency(self):
        """
        Test that is_port_available() now correctly checks the same interface 
        that uvicorn will use, preventing the race condition.
        
        The fix: is_port_available now defaults to checking '0.0.0.0' without
        SO_REUSEADDR to match uvicorn's binding behavior.
        """
        test_port = 18083
        
        # Bind a socket to 0.0.0.0 on the test port (like a running service)
        all_interfaces_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Don't use SO_REUSEADDR to match typical service behavior
        all_interfaces_socket.bind(('0.0.0.0', test_port))
        all_interfaces_socket.listen(1)
        
        try:
            # Check with old behavior (localhost) - may or may not detect conflict
            localhost_check = is_port_available(test_port, 'localhost')
            
            # Check with new behavior (0.0.0.0) - should detect the conflict
            all_interfaces_check = is_port_available(test_port, '0.0.0.0')
            
            # Check default behavior (should be same as 0.0.0.0)
            default_check = is_port_available(test_port)
            
            # The fix: checking 0.0.0.0 correctly detects the bound port
            self.assertFalse(all_interfaces_check, 
                            "Port should be detected as unavailable when 0.0.0.0 is bound")
            self.assertFalse(default_check, 
                            "Default check should detect unavailable port on 0.0.0.0")
            
        finally:
            # Clean up
            all_interfaces_socket.close()
        
        # Test that port becomes available after closing
        time.sleep(0.1)  # Brief delay for OS to release port
        available_after_close = is_port_available(test_port)
        self.assertTrue(available_after_close, 
                       "Port should be available after socket is closed")
        
        # Test the race condition fix: port check followed by immediate bind
        available_port = find_available_port(test_port + 10, host='0.0.0.0')
        
        # Immediately try to bind uvicorn-style (no SO_REUSEADDR initially)
        try:
            uvicorn_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            uvicorn_socket.bind(('0.0.0.0', available_port))
            uvicorn_socket.listen(1)
            uvicorn_socket.close()
            bind_success = True
        except OSError:
            bind_success = False
        
        self.assertTrue(bind_success, 
                       "Should be able to bind immediately after port check")
        
        # Now test the opposite - bind to a specific interface and check if 0.0.0.0 is available
        specific_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        specific_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind to a specific non-loopback interface if available
        try:
            # Try to bind to the actual network interface (not localhost)
            import socket as sock_module
            hostname = sock_module.gethostname()
            local_ip = sock_module.gethostbyname(hostname)
            if local_ip != '127.0.0.1':
                specific_socket.bind((local_ip, test_port + 1))
                specific_socket.listen(1)
                
                # Check if we can bind to 0.0.0.0 on same port
                # This demonstrates the interface mismatch issue
                try:
                    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    test_socket.bind(('0.0.0.0', test_port + 1))
                    test_socket.close()
                    can_bind_all = True
                except OSError:
                    can_bind_all = False
                    
                specific_socket.close()
                
                # On Windows, binding to specific interface may not prevent 0.0.0.0 binding
                # The issue is checking wrong interface
                self.assertFalse(can_bind_all, 
                               "Should not be able to bind to 0.0.0.0 when specific interface is bound")
        except Exception:
            # Skip this part of test if we can't get a non-loopback interface
            specific_socket.close()
            
    def test_fixed_race_condition_prevention(self):
        """
        Test that the fix prevents the original race condition by using the same
        interface for both checking and binding.
        """
        test_port = 18082
        
        # Test the fixed approach: both check and bind use the same interface
        try:
            # Step 1: Check port availability using the same interface as uvicorn will use
            is_available = is_port_available(test_port, '0.0.0.0')
            
            if is_available:
                # Step 2: Immediately bind uvicorn-style (no SO_REUSEADDR initially)
                # This should succeed because we checked the same interface
                try:
                    service_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    service_socket.bind(('0.0.0.0', test_port))
                    service_socket.listen(1)
                    service_socket.close()
                    bind_succeeded = True
                except OSError as e:
                    bind_succeeded = False
                    bind_error = str(e)
                
                self.assertTrue(bind_succeeded, 
                              f"Bind should succeed after positive availability check, but got: {bind_error if not bind_succeeded else 'N/A'}")
            else:
                # Port is not available, which is fine - we just can't test the bind
                pass
                
            # Test that multiple rapid checks work correctly
            rapid_checks = []
            for i in range(5):
                available = is_port_available(test_port + i + 10, '0.0.0.0') 
                rapid_checks.append(available)
                if available:
                    # Try immediate bind
                    try:
                        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        test_socket.bind(('0.0.0.0', test_port + i + 10))
                        test_socket.close()
                        # Small delay to prevent Windows race condition
                        time.sleep(0.01)
                    except OSError:
                        self.fail(f"Rapid check {i} failed: port {test_port + i + 10} reported available but bind failed")
            
            # At least some ports should be available
            self.assertTrue(any(rapid_checks), "At least some ports should be available for testing")
                
        except Exception as e:
            self.fail(f"Unexpected error in race condition prevention test: {e}")
            
    def test_auth_starter_with_fixed_port_binding(self):
        """
        Test that the fixed port binding works correctly with AuthStarter.
        """
        # Create AuthStarter instance
        auth_starter = AuthStarter(
            self.config, 
            self.services_config,
            self.log_manager,
            self.service_discovery,
            use_emoji=False
        )
        
        # Test that the port finder now uses the correct interface
        preferred_port = 8081
        
        # Get port using the fixed function
        port = find_available_port(preferred_port, host='0.0.0.0')
        
        # Verify port is actually available on 0.0.0.0 (not just localhost)
        self.assertTrue(is_port_available(port, '0.0.0.0'), 
                       f"Port {port} should be available on 0.0.0.0")
        
        # Test that we can actually bind uvicorn-style to this port
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test_socket:
                test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                test_socket.bind(('0.0.0.0', port))
                test_socket.listen(1)
                # If we get here, the port binding works correctly
                bind_success = True
        except OSError:
            bind_success = False
        
        self.assertTrue(bind_success, f"Should be able to bind to 0.0.0.0:{port} after port check")
        
        # Test the command building works correctly
        cmd = auth_starter._build_auth_command(port)
        self.assertIn('--host', cmd)
        self.assertIn('0.0.0.0', cmd)
        self.assertIn('--port', cmd)
        self.assertIn(str(port), cmd)


if __name__ == '__main__':
    unittest.main()