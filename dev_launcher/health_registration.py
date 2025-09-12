"""
Health monitoring registration helpers for the dev launcher.

This module handles the registration of health monitoring for backend
and frontend services after they are verified ready.
"""

import logging
from typing import Any, Dict, Optional

from dev_launcher.health_monitor import (
    HealthMonitor,
    create_process_health_check,
    create_url_health_check,
)
from dev_launcher.utils import print_with_emoji

logger = logging.getLogger(__name__)


class HealthRegistrationHelper:
    """Helper class for registering health monitoring."""
    
    def __init__(self, health_monitor: HealthMonitor, use_emoji: bool = True):
        """Initialize health registration helper."""
        self.health_monitor = health_monitor
        self.use_emoji = use_emoji
    
    def register_backend(self, health_info: Optional[Dict[str, Any]]):
        """Register backend health monitoring."""
        if not health_info:
            return
        backend_url = f"http://localhost:{health_info['port']}/health/live"
        self._register_backend_service(backend_url)
        logger.info("Backend health monitoring registered")
    
    def _register_backend_service(self, backend_url: str):
        """Register backend service with health monitor."""
        self.health_monitor.register_service(
            "Backend",
            health_check=create_url_health_check(backend_url),
            recovery_action=lambda: logger.error("Backend needs restart - please restart the launcher"),
            max_failures=5
        )
    
    def register_frontend(self, health_info: Optional[Dict[str, Any]]):
        """Register frontend health monitoring."""
        if not health_info:
            return
        self._register_frontend_service(health_info)
        logger.info("Frontend health monitoring registered")
    
    def _register_frontend_service(self, health_info: Dict[str, Any]):
        """Register frontend service with health monitor."""
        self.health_monitor.register_service(
            "Frontend",
            health_check=create_process_health_check(health_info['process']),
            recovery_action=lambda: logger.error("Frontend needs restart - please restart the launcher"),
            max_failures=5
        )
    
    def register_auth(self, auth_info: Optional[Dict[str, Any]]):
        """Register auth service health monitoring."""
        if not auth_info:
            return
        auth_url = f"{auth_info['url']}{auth_info.get('health_endpoint', '/health')}"
        self._register_auth_service(auth_url)
        logger.info("Auth service health monitoring registered")
    
    def _register_auth_service(self, auth_url: str):
        """Register auth service with health monitor."""
        self.health_monitor.register_service(
            "Auth",
            health_check=create_url_health_check(auth_url),
            recovery_action=lambda: logger.error("Auth service needs restart - please restart the launcher"),
            max_failures=5
        )
    
    def register_all_services(self, backend_info: Optional[Dict[str, Any]], 
                            frontend_info: Optional[Dict[str, Any]],
                            auth_info: Optional[Dict[str, Any]] = None):
        """Register all services for health monitoring."""
        self._print("[U+1F49A]", "HEALTH", "Registering service health monitoring endpoints...")
        if auth_info:
            self.register_auth(auth_info)
        self.register_backend(backend_info)
        self.register_frontend(frontend_info)
    
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        print_with_emoji(emoji, text, message, self.use_emoji)