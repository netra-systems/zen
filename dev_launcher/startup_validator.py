"""
Startup validation helpers for the dev launcher.

This module handles verification of backend and frontend services
during the startup process.
"""

import time
import logging
from typing import Optional, Dict, Any, Tuple

from dev_launcher.utils import print_with_emoji, wait_for_service

logger = logging.getLogger(__name__)


class StartupValidator:
    """Validator for service startup and readiness."""
    
    def __init__(self, use_emoji: bool = True):
        """Initialize startup validator."""
        self.use_emoji = use_emoji
    
    def verify_backend_ready(self, backend_info: Dict[str, Any]) -> bool:
        """Verify backend is ready and healthy."""
        self._print("⏳", "WAIT", "Waiting for backend to be ready...")
        backend_ready_url = f"{backend_info['api_url']}/health/ready"
        if not wait_for_service(backend_ready_url, timeout=30):
            return False
        self._print("✅", "OK", "Backend is ready")
        return self._verify_auth_system(backend_info)
    
    def _verify_auth_system(self, backend_info: Dict[str, Any]) -> bool:
        """Verify auth system is operational."""
        auth_config_url = f"{backend_info['api_url']}/api/auth/config"
        self._print("⏳", "WAIT", "Verifying auth system...")
        if wait_for_service(auth_config_url, timeout=10):
            self._print("✅", "OK", "Auth system is ready")
            return True
        self._print("⚠️", "WARN", "Auth config check timed out")
        return False
    
    def verify_frontend_ready(self, frontend_port: int, no_browser: bool) -> bool:
        """Verify frontend is ready and optionally open browser."""
        self._print("⏳", "WAIT", "Waiting for frontend to be ready...")
        frontend_url = f"http://localhost:{frontend_port}"
        self._allow_nextjs_compile()
        return self._check_frontend_service(frontend_url, no_browser)
    
    def _allow_nextjs_compile(self):
        """Allow Next.js to compile."""
        logger.info("Allowing Next.js to compile...")
        time.sleep(5)
    
    def _check_frontend_service(self, frontend_url: str, no_browser: bool) -> bool:
        """Check frontend service availability."""
        if wait_for_service(frontend_url, timeout=90):
            self._print("✅", "OK", "Frontend is ready")
            self._handle_browser_opening(frontend_url, no_browser)
            return True
        self._print("⚠️", "WARN", "Frontend readiness check timed out")
        return False
    
    def _handle_browser_opening(self, frontend_url: str, no_browser: bool):
        """Handle browser opening if configured."""
        time.sleep(2)
        if not no_browser:
            from dev_launcher.utils import open_browser
            self._print("🌐", "BROWSER", f"Opening browser at {frontend_url}")
            open_browser(frontend_url)
    
    def verify_all_services_ready(self, services: Dict[str, Any] = None) -> bool:
        """Verify that all services (auth, backend, frontend) are ready."""
        return self._verify_auth_ready() and self._verify_backend_ready() and self._verify_frontend_ready()
    
    def _verify_auth_ready(self) -> bool:
        """Verify auth service is ready."""
        from dev_launcher.utils import wait_for_service
        auth_url = "http://localhost:8081/health"
        return wait_for_service(auth_url, timeout=10)
    
    def _verify_backend_ready(self) -> bool:
        """Verify backend service is ready."""
        from dev_launcher.utils import wait_for_service
        backend_url = "http://localhost:8000/health/ready" 
        return wait_for_service(backend_url, timeout=10)
    
    def _verify_frontend_ready(self) -> bool:
        """Verify frontend service is ready."""
        from dev_launcher.utils import wait_for_service
        frontend_url = "http://localhost:3000"
        return wait_for_service(frontend_url, timeout=30)
    
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        print_with_emoji(emoji, text, message, self.use_emoji)