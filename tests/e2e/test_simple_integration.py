"""
from shared.isolated_environment import get_env
Simple Integration Test - Bypasses Complex Harness
Tests basic service communication without the full E2E harness
"""
import asyncio
import httpx
import pytest
import subprocess
import time
import sys
import os
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class SimpleServiceManager:
    """Simplified service manager for testing."""
    
    def __init__(self):
        self.processes = {}
        self.http_client = httpx.AsyncClient(timeout=10.0)
    
    async def start_auth_service(self):
        """Start auth service if not running."""
        if await self._check_service_health("http://localhost:8001/health"):
            print("Auth service already running")
            return
        
        auth_main = project_root / "auth_service" / "main.py"
        env = get_env().as_dict().copy()
        env["PORT"] = "8001"
        # Enable fast test mode to avoid database initialization issues
        env["AUTH_FAST_TEST_MODE"] = "true"
        env["ENVIRONMENT"] = "test"
        
        print(f"Starting auth service with command: {sys.executable} {auth_main}")
        self.processes["auth"] = subprocess.Popen(
            [sys.executable, str(auth_main)],
            cwd=str(project_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for service to start, with better error handling
        try:
            await self._wait_for_health("http://localhost:8001/health", timeout=15)
        except RuntimeError:
            # Capture process output for debugging
            if self.processes["auth"].poll() is not None:
                stdout, stderr = self.processes["auth"].communicate()
                print(f"Auth service process exited. STDOUT: {stdout}")
                print(f"Auth service process exited. STDERR: {stderr}")
            raise
    
    async def start_backend_service(self):
        """Start backend service if not running."""
        if await self._check_service_health("http://localhost:8000/health"):
            print("Backend service already running")
            return
        
        env = get_env().as_dict().copy()
        env["ENVIRONMENT"] = "test"
        env["AUTH_FAST_TEST_MODE"] = "true"
        
        print(f"Starting backend service with uvicorn")
        self.processes["backend"] = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "netra_backend.app.main:app", 
             "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"],
            cwd=str(project_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for service to start, with better error handling
        try:
            await self._wait_for_health("http://localhost:8000/health", timeout=30)
        except RuntimeError:
            # Capture process output for debugging
            if self.processes["backend"].poll() is not None:
                stdout, stderr = self.processes["backend"].communicate()
                print(f"Backend service process exited. STDOUT: {stdout}")
                print(f"Backend service process exited. STDERR: {stderr}")
            raise
    
    async def _check_service_health(self, url: str) -> bool:
        """Check if a service is healthy."""
        try:
            response = await self.http_client.get(url)
            return response.status_code == 200
        except Exception:
            return False
    
    async def _wait_for_health(self, url: str, timeout: int = 30):
        """Wait for service to become healthy."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if await self._check_service_health(url):
                print(f"Service at {url} is healthy")
                return
            await asyncio.sleep(1)
        raise RuntimeError(f"Service at {url} failed to become healthy within {timeout}s")
    
    async def cleanup(self):
        """Clean up processes."""
        for name, process in self.processes.items():
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception as e:
                print(f"Error cleaning up {name}: {e}")
        
        await self.http_client.aclose()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_simple_service_startup():
    """Test that services can start and respond to health checks."""
    manager = SimpleServiceManager()
    
    try:
        # Start auth service first
        await manager.start_auth_service()
        
        # Test auth service health
        assert await manager._check_service_health("http://localhost:8001/health")
        
        # Start backend service
        await manager.start_backend_service()
        
        # Test backend service health
        assert await manager._check_service_health("http://localhost:8000/health")
        
        print("Both services started successfully!")
        
    finally:
        await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_service_communication():
    """Test basic communication between services."""
    manager = SimpleServiceManager()
    
    try:
        # Start services
        await manager.start_auth_service()
        await manager.start_backend_service()
        
        # Test direct API calls
        auth_response = await manager.http_client.get("http://localhost:8001/health")
        assert auth_response.status_code == 200
        
        backend_response = await manager.http_client.get("http://localhost:8000/health")  
        assert backend_response.status_code == 200
        
        print("Service communication test passed!")
        
    finally:
        await manager.cleanup()


if __name__ == "__main__":
    asyncio.run(test_simple_service_startup())