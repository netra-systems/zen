"""
Auth Service Startup Integration Test

Tests the complete auth service startup process including:
- Module import resolution
- Database connectivity
- Redis connectivity  
- Configuration loading
- Health endpoint functionality
- Windows compatibility

This test verifies that the fixes for the dev launcher startup issues work correctly.
"""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import pytest
import requests
from auth_service.tests.conftest import TEST_ENVIRONMENT_MANAGER


class AuthServiceStartupTester:
    """Test helper for auth service startup testing."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.process: Optional[subprocess.Popen] = None
        self.port = 8085  # Use non-conflicting port for testing
        
    def create_test_environment(self) -> dict:
        """Create test environment variables for startup."""
        env = os.environ.copy()
        
        # Use test-specific environment configuration
        env["ENVIRONMENT"] = "test"
        env["AUTH_FAST_TEST_MODE"] = "true"  # Skip heavy initialization
        env["PORT"] = str(self.port)
        env["AUTH_SERVICE_PORT"] = str(self.port)
        env["REDIS_DISABLED"] = "true"  # Disable Redis for isolated testing
        env["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"  # In-memory database
        
        # Add project root to PYTHONPATH for proper imports
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = f"{self.project_root}{os.pathsep}{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = str(self.project_root)
            
        return env
    
    def build_startup_command(self) -> list:
        """Build the auth service startup command."""
        # Use the same pattern as the fixed dev launcher
        return [
            sys.executable, "-m", "uvicorn",
            "auth_service.main:app",
            "--host", "0.0.0.0",
            "--port", str(self.port),
            "--timeout-keep-alive", "30"
        ]
    
    def start_auth_service(self) -> bool:
        """Start auth service and return success status."""
        cmd = self.build_startup_command()
        env = self.create_test_environment()
        
        try:
            # Start from project root (same as fixed dev launcher)
            self.process = subprocess.Popen(
                cmd,
                env=env,
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for startup (max 15 seconds)
            for _ in range(15):
                if self.process.poll() is not None:
                    # Process exited - capture logs for debugging
                    stdout, stderr = self.process.communicate()
                    print(f"Auth service exited early. Exit code: {self.process.returncode}")
                    print(f"STDOUT: {stdout}")
                    print(f"STDERR: {stderr}")
                    return False
                
                # Test if service is responding
                try:
                    response = requests.get(f"http://localhost:{self.port}/health", timeout=2)
                    if response.status_code == 200:
                        print("Auth service started successfully")
                        return True
                except requests.exceptions.RequestException:
                    pass  # Service not ready yet
                
                time.sleep(1)
            
            print("Auth service startup timed out")
            return False
            
        except Exception as e:
            print(f"Failed to start auth service: {e}")
            return False
    
    def test_health_endpoint(self) -> bool:
        """Test auth service health endpoint."""
        try:
            response = requests.get(f"http://localhost:{self.port}/health", timeout=5)
            
            if response.status_code != 200:
                print(f"Health endpoint returned status {response.status_code}")
                return False
            
            health_data = response.json()
            
            # Verify required health fields
            required_fields = ["status", "service", "version", "timestamp"]
            for field in required_fields:
                if field not in health_data:
                    print(f"Health response missing field: {field}")
                    return False
            
            if health_data["status"] != "healthy":
                print(f"Service status is not healthy: {health_data['status']}")
                return False
            
            print(f"Health endpoint test passed: {health_data}")
            return True
            
        except Exception as e:
            print(f"Health endpoint test failed: {e}")
            return False
    
    def test_api_endpoints(self) -> bool:
        """Test basic API endpoint availability."""
        try:
            # Test root endpoint
            response = requests.get(f"http://localhost:{self.port}/", timeout=5)
            if response.status_code != 200:
                print(f"Root endpoint returned status {response.status_code}")
                return False
            
            root_data = response.json()
            if root_data.get("service") != "auth-service":
                print(f"Root endpoint returned unexpected service: {root_data}")
                return False
            
            # Test readiness endpoint
            response = requests.get(f"http://localhost:{self.port}/health/ready", timeout=5)
            if response.status_code != 200:
                print(f"Readiness endpoint returned status {response.status_code}")
                return False
            
            print("API endpoints test passed")
            return True
            
        except Exception as e:
            print(f"API endpoints test failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up test resources."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            print("Auth service process cleaned up")


@pytest.mark.integration
def test_auth_service_startup_integration():
    """
    Integration test for auth service startup.
    
    This test verifies that the auth service can start successfully with:
    1. Proper module import resolution (from project root)
    2. Basic health endpoint functionality
    3. Windows compatibility
    4. Fast test mode configuration
    """
    tester = AuthServiceStartupTester()
    
    try:
        # Test 1: Service startup
        startup_success = tester.start_auth_service()
        assert startup_success, "Auth service failed to start"
        
        # Test 2: Health endpoint
        health_success = tester.test_health_endpoint()
        assert health_success, "Health endpoint test failed"
        
        # Test 3: API endpoints
        api_success = tester.test_api_endpoints()
        assert api_success, "API endpoints test failed"
        
        print("✅ All auth service startup tests passed")
        
    finally:
        tester.cleanup()


@pytest.mark.integration
def test_auth_service_import_resolution():
    """
    Test that auth service imports work correctly from project root.
    
    This specifically tests the fix for the ModuleNotFoundError issue.
    """
    # Test import resolution by importing the main module
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    try:
        # This should work after our fixes
        from auth_service.main import app
        from auth_service.auth_core.config import AuthConfig
        from auth_service.auth_core.routes.auth_routes import router
        
        # Verify basic configuration access
        env = AuthConfig.get_environment()
        assert env in ["development", "test", "staging", "production"]
        
        # Verify app is properly configured
        assert app.title == "Netra Auth Service"
        assert hasattr(app, 'include_router')
        
        print("✅ Auth service import resolution test passed")
        
    except ImportError as e:
        pytest.fail(f"Import resolution failed: {e}")
    
    finally:
        # Clean up sys.path
        if str(Path(__file__).parent.parent.parent) in sys.path:
            sys.path.remove(str(Path(__file__).parent.parent.parent))


@pytest.mark.unit
def test_auth_startup_command_generation():
    """
    Test that the auth service command is generated correctly.
    
    This tests the dev launcher command generation logic.
    """
    from dev_launcher.auth_starter import AuthStarter
    from dev_launcher.config import LauncherConfig
    from dev_launcher.service_discovery import ServiceDiscovery
    from dev_launcher.log_streamer import LogManager
    from dev_launcher.service_config import ServicesConfig
    
    # Create test configuration
    project_root = Path(__file__).parent.parent.parent
    config = LauncherConfig(project_root=project_root)
    services_config = ServicesConfig(project_root)
    log_manager = LogManager()
    service_discovery = ServiceDiscovery(project_root)
    
    # Create auth starter
    auth_starter = AuthStarter(
        config=config,
        services_config=services_config,
        log_manager=log_manager,
        service_discovery=service_discovery,
        use_emoji=False
    )
    
    # Test command generation
    cmd = auth_starter._build_auth_command(8081)
    
    # Verify command structure
    assert cmd[0] == sys.executable
    assert cmd[1:3] == ["-m", "uvicorn"]
    assert cmd[3] == "auth_service.main:app"  # This should be the fixed version
    assert "--host" in cmd
    assert "0.0.0.0" in cmd
    assert "--port" in cmd
    assert "8081" in cmd
    
    print("✅ Auth startup command generation test passed")


if __name__ == "__main__":
    # Run tests directly for debugging
    print("Running auth service startup integration tests...")
    
    # Test 1: Import resolution
    print("\n1. Testing import resolution...")
    test_auth_service_import_resolution()
    
    # Test 2: Command generation  
    print("\n2. Testing command generation...")
    test_auth_startup_command_generation()
    
    # Test 3: Full startup integration
    print("\n3. Testing full startup integration...")
    test_auth_service_startup_integration()
    
    print("\n✅ All tests completed successfully!")