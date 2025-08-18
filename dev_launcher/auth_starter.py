"""
Auth service startup management.
"""

import os
import sys
import time
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple

from dev_launcher.config import LauncherConfig, resolve_path
from dev_launcher.log_streamer import LogStreamer, LogManager, Colors
from dev_launcher.service_discovery import ServiceDiscovery
from dev_launcher.utils import (
    get_free_port, create_process_env, create_subprocess, print_with_emoji
)

logger = logging.getLogger(__name__)


class AuthStarter:
    """
    Handles auth service startup.
    
    Manages auth service server startup with proper configuration,
    environment setup, and error handling.
    """
    
    def __init__(self, config: LauncherConfig, services_config, 
                 log_manager: LogManager, service_discovery: ServiceDiscovery,
                 use_emoji: bool = True):
        """Initialize auth starter."""
        self.config = config
        self.services_config = services_config
        self.log_manager = log_manager
        self.service_discovery = service_discovery
        self.use_emoji = use_emoji
        self.auth_health_info = None
    
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        print_with_emoji(emoji, text, message, self.use_emoji)
    
    def start_auth_service(self) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start the auth service."""
        # Check if auth service is enabled
        auth_config = self.services_config.auth_service
        if not auth_config.get_config().get("enabled", True):
            self._print("⚠️", "AUTH", "Auth service is disabled in configuration")
            return None, None
        
        self._print("🔐", "AUTH", "Starting auth service...")
        
        # Get auth service configuration
        port = auth_config.get_config().get("port", 8081)
        
        # Build command to start auth service
        cmd = self._build_auth_command(port)
        
        # Create environment for auth service
        env = self._create_auth_env(port)
        
        # Start the auth service process
        return self._start_auth_process(cmd, env, port)
    
    def _build_auth_command(self, port: int) -> list:
        """Build auth service command."""
        # Find auth service directory
        auth_service_dir = self.config.project_root / "auth_service"
        
        if not auth_service_dir.exists():
            logger.error(f"Auth service directory not found: {auth_service_dir}")
            return []
        
        # Build uvicorn command to run auth service
        cmd = [
            sys.executable, "-m", "uvicorn",
            "main:app",
            "--host", "0.0.0.0",
            "--port", str(port)
        ]
        
        # Add reload in development mode
        if not self.config.production:
            cmd.append("--reload")
        
        logger.debug(f"Auth service command: {' '.join(cmd)}")
        return cmd
    
    def _create_auth_env(self, port: int) -> dict:
        """Create environment for auth service."""
        env = create_process_env()
        
        # Add auth service specific environment variables
        env["AUTH_SERVICE_PORT"] = str(port)
        env["AUTH_SERVICE_HOST"] = "0.0.0.0"
        
        # Add Redis configuration from services config
        redis_config = self.services_config.redis.get_config()
        if self.services_config.redis.mode.value == "shared":
            # Use shared Redis with authentication
            env["REDIS_URL"] = f"redis://:{redis_config['password']}@{redis_config['host']}:{redis_config['port']}/{redis_config.get('db', 0)}"
        else:
            # Use local Redis without authentication
            env["REDIS_URL"] = f"redis://{redis_config['host']}:{redis_config['port']}/{redis_config.get('db', 0)}"
        
        # Add PostgreSQL configuration
        postgres_config = self.services_config.postgres.get_config()
        env["DATABASE_URL"] = f"postgresql://{postgres_config['user']}:{postgres_config['password']}@{postgres_config['host']}:{postgres_config['port']}/{postgres_config['database']}"
        
        # Add service discovery path
        env["SERVICE_DISCOVERY_PATH"] = str(self.config.project_root / ".service_discovery")
        
        # Add other required environment variables
        env["ENV_MODE"] = "development"
        env["AUTH_SERVICE_NAME"] = "auth-service"
        
        return env
    
    def _start_auth_process(self, cmd: list, env: dict, port: int) -> Tuple[Optional[subprocess.Popen], Optional[LogStreamer]]:
        """Start auth service process."""
        if not cmd:
            return None, None
        
        # Change to auth service directory
        auth_service_dir = self.config.project_root / "auth_service"
        
        try:
            # Create the subprocess
            process = create_subprocess(
                cmd,
                env=env,
                cwd=str(auth_service_dir)
            )
            
            if not process:
                self._print("❌", "ERROR", "Failed to create auth service process")
                return None, None
            
            # Create log streamer for auth service
            streamer = self._create_auth_streamer(process)
            
            # Wait briefly for auth service to start
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is not None:
                self._handle_auth_startup_failure(process)
                return None, None
            
            # Store health info for monitoring
            self.auth_health_info = {
                "url": f"http://localhost:{port}",
                "health_endpoint": "/health",
                "port": port
            }
            
            # Write service discovery info
            self._write_auth_discovery(port)
            
            self._print("✅", "AUTH", f"Auth service started on port {port}")
            return process, streamer
            
        except Exception as e:
            logger.error(f"Failed to start auth service: {e}")
            self._print("❌", "ERROR", f"Auth service startup failed: {str(e)}")
            return None, None
    
    def _create_auth_streamer(self, process: subprocess.Popen) -> LogStreamer:
        """Create log streamer for auth service."""
        streamer = self.log_manager.add_streamer(
            "AUTH",
            process,
            Colors.CYAN
        )
        return streamer
    
    def _handle_auth_startup_failure(self, process: subprocess.Popen):
        """Handle auth service startup failure."""
        exit_code = process.returncode
        self._print("❌", "ERROR", f"Auth service exited with code {exit_code}")
        
        if exit_code == 1:
            logger.error("Auth service failed - check Redis and PostgreSQL connections")
        elif exit_code == 2:
            logger.error("Auth service configuration error")
        elif exit_code == 3:
            logger.error("Auth service dependency error - check if Redis/PostgreSQL are running")
    
    def _write_auth_discovery(self, port: int):
        """Write auth service discovery information."""
        discovery_info = {
            "service": "auth",
            "port": port,
            "url": f"http://localhost:{port}",
            "health": f"http://localhost:{port}/health",
            "docs": f"http://localhost:{port}/docs",
            "started_at": time.time()
        }
        
        self.service_discovery.write_auth_info(discovery_info)