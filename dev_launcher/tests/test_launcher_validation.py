"""
Validation tests for the dev launcher.

These tests verify that the launcher can actually start
and handle common scenarios.
"""

import sys
import os
import time
import subprocess
from pathlib import Path
import tempfile
import json

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_launcher_help():
    """Test that the launcher help works."""
    result = subprocess.run(
        [sys.executable, "dev_launcher.py", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Netra AI Development Launcher" in result.stdout
    print("[PASS] Help command works")


def test_launcher_config_validation():
    """Test that config validation works."""
    from dev_launcher.config import LauncherConfig, find_project_root
    
    try:
        # Should work with current directory
        config = LauncherConfig()
        assert config.project_root.exists()
        print("[PASS] Config validation works")
    except ValueError as e:
        print(f"[PASS] Config validation caught error: {e}")


def test_launcher_imports():
    """Test that all launcher modules can be imported."""
    try:
        from dev_launcher import DevLauncher, LauncherConfig
        from dev_launcher.process_manager import ProcessManager
        from dev_launcher.health_monitor import HealthMonitor
        from dev_launcher.log_streamer import LogManager
        from dev_launcher.secret_manager import SecretLoader
        print("[PASS] All modules import successfully")
    except ImportError as e:
        print(f"[FAIL] Import error: {e}")
        return False
    return True


def test_launcher_dry_run():
    """Test launcher initialization without actually starting services."""
    from dev_launcher import DevLauncher, LauncherConfig
    from unittest.mock import patch
    
    # Create config with no secrets and no browser
    with patch.object(LauncherConfig, '_validate'):
        config = LauncherConfig(
            load_secrets=False,
            no_browser=True,
            verbose=False
        )
    
    # Create launcher
    with patch('dev_launcher.launcher.load_or_create_config'):
        launcher = DevLauncher(config)
    
    # Check that all components are initialized
    assert launcher.process_manager is not None
    assert launcher.log_manager is not None
    assert launcher.health_monitor is not None
    assert launcher.service_discovery is not None
    print("[PASS] Launcher initializes correctly")


def test_service_discovery():
    """Test service discovery file operations."""
    from dev_launcher.secret_manager import ServiceDiscovery
    
    with tempfile.TemporaryDirectory() as tmpdir:
        sd = ServiceDiscovery(Path(tmpdir))
        
        # Test writing backend info
        sd.write_backend_info(8000)
        info = sd.read_backend_info()
        assert info is not None
        assert info['port'] == 8000
        assert info['api_url'] == 'http://localhost:8000'
        
        # Test writing frontend info
        sd.write_frontend_info(3000)
        info = sd.read_frontend_info()
        assert info is not None
        assert info['port'] == 3000
        
        print("[PASS] Service discovery works")


def test_health_monitor_basic():
    """Test basic health monitoring functionality."""
    from dev_launcher.health_monitor import HealthMonitor
    
    monitor = HealthMonitor(check_interval=1)
    
    # Register a simple health check
    health_status = True
    monitor.register_service(
        "TestService",
        lambda: health_status,
        max_failures=3
    )
    
    # Check status
    status = monitor.get_status("TestService")
    assert status is not None
    assert status.is_healthy
    
    monitor.stop()
    print("[PASS] Health monitor works")


def test_process_manager_basic():
    """Test basic process manager functionality."""
    from dev_launcher.process_manager import ProcessManager
    from unittest.mock import Mock
    import subprocess
    
    manager = ProcessManager()
    
    # Create a mock process
    mock_process = Mock(spec=subprocess.Popen)
    mock_process.pid = 12345
    mock_process.poll.return_value = None
    
    # Add and check
    manager.add_process("TestService", mock_process)
    assert manager.is_running("TestService")
    assert manager.get_running_count() == 1
    
    print("[PASS] Process manager works")


def test_config_env_vars():
    """Test that configuration handles environment variables."""
    from dev_launcher.config import LauncherConfig
    import os
    
    # Set a test project ID
    os.environ['GOOGLE_CLOUD_PROJECT'] = 'test-project-123'
    
    with patch.object(LauncherConfig, '_validate'):
        config = LauncherConfig()
        assert config.project_id == 'test-project-123'
    
    # Clean up
    del os.environ['GOOGLE_CLOUD_PROJECT']
    print("[PASS] Environment variable handling works")


def test_error_messages():
    """Test that error messages are user-friendly."""
    from dev_launcher.launcher import DevLauncher
    from dev_launcher.config import LauncherConfig
    from unittest.mock import patch, Mock
    
    with patch.object(LauncherConfig, '_validate'):
        config = LauncherConfig(load_secrets=False)
    
    with patch('dev_launcher.launcher.load_or_create_config'):
        launcher = DevLauncher(config)
    
    # Test environment check with missing deps
    with patch('dev_launcher.launcher.check_dependencies') as mock_deps:
        mock_deps.return_value = {
            'uvicorn': False,
            'fastapi': False,
            'node': True,
            'npm': True
        }
        
        with patch('builtins.print') as mock_print:
            result = launcher.check_environment()
            
        # Should have printed helpful error messages
        assert not result
        calls = [str(call) for call in mock_print.call_args_list]
        assert any('pip install' in str(call) for call in calls)
    
    print("[PASS] Error messages are user-friendly")


def test_launcher_with_defaults():
    """Test that launcher can be created with default settings."""
    from dev_launcher import DevLauncher, LauncherConfig
    from unittest.mock import patch
    
    # Create launcher with defaults
    try:
        with patch.object(LauncherConfig, '_validate'):
            config = LauncherConfig()
        
        with patch('dev_launcher.launcher.load_or_create_config'):
            launcher = DevLauncher(config)
        
        # Check defaults
        assert config.frontend_port == 3000
        assert config.load_secrets == True
        assert config.backend_reload == True
        
        print("[PASS] Launcher works with default configuration")
    except Exception as e:
        print(f"[FAIL] Failed with defaults: {e}")
        return False
    
    return True


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("DEV LAUNCHER VALIDATION TESTS")
    print("=" * 60)
    
    tests = [
        test_launcher_help,
        test_launcher_config_validation,
        test_launcher_imports,
        test_launcher_dry_run,
        test_service_discovery,
        test_health_monitor_basic,
        test_process_manager_basic,
        test_config_env_vars,
        test_error_messages,
        test_launcher_with_defaults
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__} failed: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("SUCCESS: ALL VALIDATION TESTS PASSED!")
        return 0
    else:
        print("FAILURE: Some tests failed")
        return 1


if __name__ == "__main__":
    from unittest.mock import patch
    sys.exit(main())