#!/usr/bin/env python3
"""
Start Backend Services for E2E Testing

This script starts the backend and auth services needed for E2E testing.
It's designed to be called by the test runner or CI/CD system to ensure
required services are running on the correct ports.

Usage:
    python scripts/start_backend_services.py
    python scripts/start_backend_services.py --wait-for-health
    python scripts/start_backend_services.py --stop
"""

import asyncio
import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared.isolated_environment import get_env
from test_framework.docker_port_discovery import DockerPortDiscovery

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackendServiceManager:
    """Manager for backend services needed for E2E testing."""
    
    def __init__(self):
        self.env = get_env()
        self.port_discovery = DockerPortDiscovery(use_test_services=True)
        self.processes: Dict[str, subprocess.Popen] = {}
        
        # Service configurations
        self.services = {
            "backend": {
                "port": 8001,  # Test backend port
                "command": [
                    sys.executable, "-m", "uvicorn",
                    "netra_backend.app.main:app",
                    "--host", "0.0.0.0",
                    "--port", "8001",
                    "--reload"
                ],
                "cwd": PROJECT_ROOT,
                "health_endpoint": "/health"
            },
            "auth": {
                "port": 8082,  # Test auth port
                "command": [
                    sys.executable, "-m", "uvicorn", 
                    "auth_service.main:app",
                    "--host", "0.0.0.0",
                    "--port", "8082",
                    "--reload"
                ],
                "cwd": PROJECT_ROOT,
                "health_endpoint": "/health"
            }
        }
    
    async def start_services(self, services: Optional[List[str]] = None) -> bool:
        """Start backend services."""
        if services is None:
            services = list(self.services.keys())
        
        logger.info(f"🚀 Starting backend services: {services}")
        
        # Set up environment for services
        self._configure_service_environment()
        
        success = True
        for service_name in services:
            if service_name in self.services:
                if await self._start_service(service_name):
                    logger.info(f"✅ {service_name} service started")
                else:
                    logger.error(f"❌ {service_name} service failed to start")
                    success = False
            else:
                logger.error(f"❌ Unknown service: {service_name}")
                success = False
        
        return success
    
    async def _start_service(self, service_name: str) -> bool:
        """Start a single service."""
        config = self.services[service_name]
        
        # Check if service is already running
        if await self._is_service_running(service_name, config["port"]):
            logger.info(f"⚡ {service_name} is already running on port {config['port']}")
            return True
        
        logger.info(f"🚀 Starting {service_name} service on port {config['port']}")
        
        try:
            # Prepare environment
            service_env = self.env.get_subprocess_env()
            service_env.update({
                "PYTHONUNBUFFERED": "1",
                "PYTHONPATH": str(PROJECT_ROOT),
                "PORT": str(config["port"]),
                "HOST": "0.0.0.0",
            })
            
            # Start the service process
            process = subprocess.Popen(
                config["command"],
                cwd=config["cwd"],
                env=service_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )
            
            self.processes[service_name] = process
            
            # Wait a moment for the process to start
            await asyncio.sleep(2)
            
            # Check if process is still running
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                logger.error(f"❌ {service_name} process exited immediately")
                logger.error(f"STDOUT: {stdout}")
                logger.error(f"STDERR: {stderr}")
                return False
            
            logger.info(f"✅ {service_name} process started (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start {service_name}: {e}")
            return False
    
    async def _is_service_running(self, service_name: str, port: int) -> bool:
        """Check if a service is already running on its port."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("localhost", port),
                timeout=2.0
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False
    
    async def wait_for_health(self, services: Optional[List[str]] = None, timeout: float = 60.0) -> bool:
        """Wait for services to be healthy."""
        if services is None:
            services = list(self.services.keys())
        
        logger.info(f"🏥 Waiting for services to be healthy: {services}")
        
        start_time = time.time()
        
        for service_name in services:
            config = self.services[service_name]
            
            logger.info(f"⏳ Waiting for {service_name} health check...")
            
            healthy = False
            while time.time() - start_time < timeout:
                if await self._check_service_health(service_name, config):
                    logger.info(f"✅ {service_name} is healthy")
                    healthy = True
                    break
                
                await asyncio.sleep(2)
            
            if not healthy:
                logger.error(f"❌ {service_name} health check timed out")
                return False
        
        elapsed = time.time() - start_time
        logger.info(f"🎉 All services are healthy ({elapsed:.1f}s)")
        return True
    
    async def _check_service_health(self, service_name: str, config: Dict) -> bool:
        """Check health of a specific service."""
        port = config["port"]
        health_endpoint = config.get("health_endpoint", "/health")
        
        try:
            # Try HTTP health check if aiohttp is available
            try:
                import aiohttp
                
                url = f"http://localhost:{port}{health_endpoint}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        return response.status == 200
            except ImportError:
                # Fallback to port connectivity
                return await self._is_service_running(service_name, port)
        except Exception:
            return False
    
    def stop_services(self, services: Optional[List[str]] = None) -> bool:
        """Stop backend services."""
        if services is None:
            services = list(self.processes.keys())
        
        logger.info(f"🛑 Stopping services: {services}")
        
        success = True
        for service_name in services:
            if service_name in self.processes:
                process = self.processes[service_name]
                
                try:
                    # Terminate gracefully
                    process.terminate()
                    
                    # Wait for graceful shutdown
                    try:
                        process.wait(timeout=10)
                        logger.info(f"✅ {service_name} stopped gracefully")
                    except subprocess.TimeoutExpired:
                        # Force kill if needed
                        process.kill()
                        process.wait()
                        logger.warning(f"⚠️ {service_name} force killed")
                    
                    del self.processes[service_name]
                    
                except Exception as e:
                    logger.error(f"❌ Failed to stop {service_name}: {e}")
                    success = False
        
        return success
    
    def _configure_service_environment(self) -> None:
        """Configure environment for backend services."""
        # Set test environment variables
        env = self.env
        
        # Environment setup
        env.set("ENVIRONMENT", "test", "backend_service_manager")
        env.set("TESTING", "1", "backend_service_manager")
        env.set("LOG_LEVEL", "INFO", "backend_service_manager")
        
        # Database configuration (use orchestrated test services)
        env.set("DATABASE_URL", "postgresql://test_user:test_pass@localhost:5434/netra_test", "backend_service_manager")
        env.set("POSTGRES_HOST", "localhost", "backend_service_manager")
        env.set("POSTGRES_PORT", "5434", "backend_service_manager")
        env.set("POSTGRES_USER", "test_user", "backend_service_manager")
        env.set("POSTGRES_PASSWORD", "test_pass", "backend_service_manager")
        env.set("POSTGRES_DB", "netra_test", "backend_service_manager")
        
        # Redis configuration
        env.set("REDIS_URL", "redis://localhost:6381/1", "backend_service_manager")
        env.set("REDIS_HOST", "localhost", "backend_service_manager")
        env.set("REDIS_PORT", "6381", "backend_service_manager")
        
        # ClickHouse configuration
        env.set("CLICKHOUSE_HOST", "localhost", "backend_service_manager")
        env.set("CLICKHOUSE_PORT", "9002", "backend_service_manager")
        env.set("CLICKHOUSE_USER", "test_user", "backend_service_manager")
        env.set("CLICKHOUSE_PASSWORD", "test_pass", "backend_service_manager")
        env.set("CLICKHOUSE_DB", "netra_test_analytics", "backend_service_manager")
        
        # Service URLs
        env.set("AUTH_SERVICE_URL", "http://localhost:8082", "backend_service_manager")
        env.set("BACKEND_SERVICE_URL", "http://localhost:8001", "backend_service_manager")
        
        # Security settings for testing
        env.set("JWT_SECRET_KEY", "test-jwt-secret-key-must-be-at-least-32-characters", "backend_service_manager")
        env.set("SERVICE_SECRET", "test-service-secret-for-cross-service-auth-32-chars-minimum", "backend_service_manager")
        env.set("FERNET_KEY", "iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw=", "backend_service_manager")
        
        # Enable CORS for testing
        env.set("CORS_ORIGINS", "*", "backend_service_manager")
        
        # Disable some production features for testing
        env.set("SECURE_HEADERS_ENABLED", "false", "backend_service_manager")
        
        logger.info("🔧 Backend service environment configured for testing")
    
    def get_service_status(self) -> Dict[str, str]:
        """Get status of all services."""
        status = {}
        
        for service_name, process in self.processes.items():
            if process.poll() is None:
                status[service_name] = "running"
            else:
                status[service_name] = "stopped"
        
        return status


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Backend Service Manager for E2E Testing")
    parser.add_argument("--services", nargs="+", choices=["backend", "auth"],
                       help="Services to manage (default: all)")
    parser.add_argument("--wait-for-health", action="store_true",
                       help="Wait for services to be healthy")
    parser.add_argument("--stop", action="store_true",
                       help="Stop services instead of starting")
    parser.add_argument("--status", action="store_true",
                       help="Show service status")
    parser.add_argument("--timeout", type=float, default=60.0,
                       help="Health check timeout in seconds")
    
    args = parser.parse_args()
    
    manager = BackendServiceManager()
    
    try:
        if args.stop:
            success = manager.stop_services(args.services)
            return 0 if success else 1
        
        elif args.status:
            status = manager.get_service_status()
            print("\nService Status:")
            for service, state in status.items():
                print(f"  {service}: {state}")
            return 0
        
        else:
            # Start services
            success = await manager.start_services(args.services)
            if not success:
                return 1
            
            # Wait for health if requested
            if args.wait_for_health:
                healthy = await manager.wait_for_health(args.services, args.timeout)
                if not healthy:
                    return 1
            
            logger.info("🎉 Backend services are ready for E2E testing")
            
            # For CLI usage, keep services running
            if sys.stdin.isatty():
                logger.info("Press Ctrl+C to stop services...")
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Stopping services...")
                    manager.stop_services()
            
            return 0
    
    except Exception as e:
        logger.error(f"❌ Backend service management failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))