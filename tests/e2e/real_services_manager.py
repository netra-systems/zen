"""
Real Services Manager for E2E Testing
Manages starting/stopping real services without mocking.

CRITICAL REQUIREMENTS:
- Start real Auth service on port 8001
- Start real Backend service on port 8000  
- Start real Frontend service on port 3000
- Health check validation for all services
- Proper cleanup on test completion
- NO MOCKING - real services only
- Maximum 300 lines, functions ≤8 lines each
- Handle Windows/Unix compatibility

NOTE: Now uses dev_launcher_real_system for better integration
"""

import asyncio
import logging
import os
import platform
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from test_framework.http_client import UnifiedHTTPClient, AuthHTTPClient, BackendHTTPClient

# Import test environment config for environment-aware configuration
try:
    from tests.e2e.test_environment_config import TestEnvironmentConfig
except ImportError:
    TestEnvironmentConfig = None

logger = logging.getLogger(__name__)


@dataclass
class ServiceProcess:
    """Represents a running service process."""
    name: str
    port: int
    process: Optional[subprocess.Popen] = None
    health_url: str = ""
    startup_timeout: int = 30
    ready: bool = False


class RealServicesManager:
    """Manages starting/stopping real services for E2E testing."""
    
    def __init__(self, project_root: Optional[Path] = None, env_config=None):
        """Initialize the real services manager.
        
        Args:
            project_root: Optional project root path
            env_config: Optional TestEnvironmentConfig for environment-aware configuration
        """
        self.project_root = project_root or self._detect_project_root()
        self.env_config = env_config
        self.services: Dict[str, ServiceProcess] = {}
        self.http_client: Optional[httpx.AsyncClient] = None
        self.cleanup_handlers: List[callable] = []
        self._setup_services()
    
    def _detect_project_root(self) -> Path:
        """Detect project root directory."""
        current = Path(__file__).parent
        while current.parent != current:
            # Check for project root markers - netra_backend and auth_service directories
            if (current / "netra_backend").exists() and (current / "auth_service").exists():
                return current
            current = current.parent
        raise RuntimeError("Could not detect project root")
    
    def _setup_services(self) -> None:
        """Setup service configurations."""
        self.services = self._create_service_configs()
        logger.info(f"Configured {len(self.services)} services")
    
    def _create_service_configs(self) -> Dict[str, ServiceProcess]:
        """Create service configuration dictionary with environment-aware ports."""
        # Use environment configuration if available for port extraction
        if self.env_config:
            # Extract ports from environment URLs
            backend_port = self._extract_port_from_url(self.env_config.services.backend, 8000)
            auth_port = self._extract_port_from_url(self.env_config.services.auth, 8081)  
            frontend_port = self._extract_port_from_url(self.env_config.services.frontend, 3000)
        else:
            # Fallback to default ports
            backend_port = 8000
            auth_port = 8081
            frontend_port = 3000
        
        return {
            "auth": ServiceProcess("auth", auth_port, health_url="/health"),
            "backend": ServiceProcess("backend", backend_port, health_url="/health/"),
            "frontend": ServiceProcess("frontend", frontend_port, health_url="/")
        }
    
    def _extract_port_from_url(self, url: str, default_port: int) -> int:
        """Extract port from URL or return default."""
        try:
            if ":" in url and not url.startswith("https://"):
                # Handle http://localhost:8000 format
                port_part = url.split(":")[-1]
                if "/" in port_part:
                    port_part = port_part.split("/")[0]
                return int(port_part)
            elif url.startswith("https://"):
                return 443  # HTTPS default
            elif url.startswith("http://"):
                return 80   # HTTP default
            else:
                return default_port
        except (ValueError, IndexError):
            return default_port
    
    async def start_all_services(self, skip_frontend: bool = False) -> None:
        """Start all services and wait for health checks."""
        self.http_client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
        
        await self._start_auth_service()
        await self._start_backend_service()
        if not skip_frontend:
            await self._start_frontend_service()
        await self._validate_all_healthy()
        logger.info("All services started and healthy")
    
    async def _start_auth_service(self) -> None:
        """Start the auth service on port 8081."""
        service = self.services["auth"]
        if await self._is_port_busy(service.port):
            logger.info(f"Auth service already running on port {service.port}")
            await self._wait_for_health(service)
            return
            
        # Try alternate port 8083 if default is busy
        if await self._is_port_busy(8083):
            logger.info(f"Auth service already running on port 8083")
            service.port = 8083
            await self._wait_for_health(service)
            return
            
        cmd = self._get_auth_command()
        await self._start_service_process(service, cmd)
        await self._wait_for_health(service)
    
    async def _start_backend_service(self) -> None:
        """Start the backend service on port 8000."""
        service = self.services["backend"]
        if await self._is_port_busy(service.port):
            logger.info(f"Backend service already running on port {service.port}")
            await self._wait_for_health(service)
            return
            
        cmd = self._get_backend_command()
        await self._start_service_process(service, cmd)
        await self._wait_for_health(service)
    
    async def _start_frontend_service(self) -> None:
        """Start the frontend service on port 3000."""
        service = self.services["frontend"]
        if await self._is_port_busy(service.port):
            logger.info(f"Frontend service already running on port {service.port}")
            await self._wait_for_health(service)
            return
            
        cmd = self._get_frontend_command()
        await self._start_service_process(service, cmd)
        await self._wait_for_health(service)
    
    def _get_auth_command(self) -> List[str]:
        """Get command to start auth service."""
        auth_main = self.project_root / "auth_service" / "main.py"
        return [
            sys.executable, str(auth_main),
            "--host", "0.0.0.0",
            "--port", "8081"
        ]
    
    def _get_backend_command(self) -> List[str]:
        """Get command to start backend service."""
        return [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload", "false"
        ]
    
    def _get_frontend_command(self) -> List[str]:
        """Get command to start frontend service."""
        npm_cmd = self._get_npm_command()
        return [npm_cmd, "run", "dev", "--", "--port", "3000"]
    
    def _get_npm_command(self) -> str:
        """Get npm command based on platform."""
        return "npm.cmd" if platform.system() == "Windows" else "npm"
    
    async def _start_service_process(self, service: ServiceProcess, cmd: List[str]) -> None:
        """Start a service process with error handling."""
        try:
            logger.info(f"Starting {service.name}: {' '.join(cmd)}")
            env = self._prepare_environment()
            cwd = str(self._get_service_cwd(service))
            
            service.process = subprocess.Popen(
                cmd, cwd=cwd, env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True
            )
            self.cleanup_handlers.append(lambda: self._stop_service(service))
        except Exception as e:
            raise RuntimeError(f"Failed to start {service.name}: {e}")
    
    def _prepare_environment(self) -> Dict[str, str]:
        """Prepare environment variables for services."""
        env = os.environ.copy()
        env.update({
            "NODE_ENV": "test",
            "NETRA_ENV": "test",
            "LOG_LEVEL": "WARNING"
        })
        return env
    
    def _get_service_cwd(self, service: ServiceProcess) -> Path:
        """Get working directory for service."""
        return self._resolve_service_path(service.name)
    
    def _resolve_service_path(self, service_name: str) -> Path:
        """Resolve path for specific service."""
        if service_name == "frontend":
            return self.project_root / "frontend"
        return self.project_root
    
    async def _is_port_busy(self, port: int) -> bool:
        """Check if port is already in use."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                return sock.connect_ex(('localhost', port)) == 0
        except Exception:
            return False
    
    async def _wait_for_health(self, service: ServiceProcess) -> None:
        """Wait for service to be healthy."""
        start_time = time.time()
        
        while time.time() - start_time < service.startup_timeout:
            if await self._check_service_health(service):
                service.ready = True
                logger.info(f"{service.name} is healthy")
                return
            await asyncio.sleep(1)
        
        raise RuntimeError(f"{service.name} health check failed")
    
    async def _check_service_health(self, service: ServiceProcess) -> bool:
        """Check service health endpoint."""
        try:
            url = f"http://localhost:{service.port}{service.health_url}"
            response = await self.http_client.get(url)
            return response.status_code == 200
        except Exception:
            return False
    
    async def _validate_all_healthy(self) -> None:
        """Validate all services are healthy."""
        unhealthy = [name for name, svc in self.services.items() if not svc.ready and name != "frontend"]
        if unhealthy:
            raise RuntimeError(f"Unhealthy services: {unhealthy}")
    
    def _stop_service(self, service: ServiceProcess) -> None:
        """Stop a service process gracefully."""
        if not self._is_process_running(service):
            return
        self._terminate_process(service)
    
    def _is_process_running(self, service: ServiceProcess) -> bool:
        """Check if service process is running."""
        return service.process and service.process.poll() is None
    
    def _terminate_process(self, service: ServiceProcess) -> None:
        """Terminate service process with timeout."""
        try:
            service.process.terminate()
            service.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            service.process.kill()
        finally:
            service.ready = False
            logger.info(f"Stopped {service.name}")
    
    async def stop_all_services(self) -> None:
        """Stop all services and cleanup resources."""
        for service in self.services.values():
            self._stop_service(service)
            
        if self.http_client:
            await self.http_client.aclose()
            
        for cleanup_fn in reversed(self.cleanup_handlers):
            try:
                cleanup_fn()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                
        logger.info("All services stopped")
    
    def get_service_urls(self) -> Dict[str, str]:
        """Get URLs for all services, using environment configuration when available."""
        # Use environment configuration if available
        if self.env_config:
            env_urls = {
                "backend": self.env_config.services.backend,
                "auth": self.env_config.services.auth,
                "frontend": self.env_config.services.frontend
            }
            # Return only ready services
            return {
                name: env_urls.get(name, f"http://localhost:{svc.port}")
                for name, svc in self.services.items()
                if svc.ready
            }
        else:
            # Fallback to localhost URLs
            return {
                name: f"http://localhost:{svc.port}"
                for name, svc in self.services.items()
                if svc.ready
            }
    
    def is_all_ready(self) -> bool:
        """Check if all services are ready."""
        return self._check_all_service_status()
    
    def _check_all_service_status(self) -> bool:
        """Check status of all services."""
        return all(svc.ready for svc in self.services.values())
    
    async def health_status(self) -> Dict[str, Any]:
        """Get health status of all services."""
        status = {}
        for name, service in self.services.items():
            status[name] = {
                "ready": service.ready,
                "port": service.port,
                "process_alive": (
                    service.process and 
                    service.process.poll() is None
                )
            }
        return status


# Factory function for easy instantiation
def create_real_services_manager(project_root: Optional[Path] = None) -> RealServicesManager:
    """Create a real services manager instance.
    
    NOTE: Consider using dev_launcher_real_system.create_dev_launcher_system()
    for better integration with the actual dev launcher.
    """
    # Try to use the new dev_launcher integration if available
    try:
        from tests.e2e.dev_launcher_real_system import create_dev_launcher_system
        logger.info("Using dev_launcher_real_system for service management")
        return create_dev_launcher_system(skip_frontend=True)
    except ImportError:
        # Fallback to traditional approach
        logger.info("Using traditional RealServicesManager")
        return RealServicesManager(project_root)
