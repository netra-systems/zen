"""
Startup validation helpers for the dev launcher.

This module handles verification of backend and frontend services
during the startup process.
"""

import logging
import time
from typing import Any, Dict, Optional, Tuple

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
        if not wait_for_service(backend_ready_url, timeout=60):
            return False
        self._print("✅", "OK", "Backend is ready")
        return self._verify_auth_system(backend_info)
    
    def _verify_auth_system(self, backend_info: Dict[str, Any]) -> bool:
        """Verify auth system is operational."""
        auth_config_url = f"{backend_info['api_url']}/api/auth/config"
        self._print("⏳", "WAIT", "Verifying auth system...")
        if wait_for_service(auth_config_url, timeout=30):
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
        if wait_for_service(frontend_url, timeout=120):
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
        # Get service discovery info for dynamic ports
        import json
        from pathlib import Path
        discovery_dir = Path.cwd() / ".service_discovery"
        
        # Get auth port
        auth_port = 8081
        auth_info_file = discovery_dir / "auth.json"
        if auth_info_file.exists():
            try:
                with open(auth_info_file) as f:
                    auth_info = json.load(f)
                    auth_port = auth_info.get("port", 8081)
            except:
                pass
        
        # Get backend port
        backend_port = 8000
        backend_info_file = discovery_dir / "backend.json"
        if backend_info_file.exists():
            try:
                with open(backend_info_file) as f:
                    backend_info = json.load(f)
                    backend_port = backend_info.get("port", 8000)
            except:
                pass
        
        # Get frontend port
        frontend_port = 3000
        frontend_info_file = discovery_dir / "frontend.json"
        if frontend_info_file.exists():
            try:
                with open(frontend_info_file) as f:
                    frontend_info = json.load(f)
                    frontend_port = frontend_info.get("port", 3000)
            except:
                pass
        
        auth_ready = self._verify_auth_ready(auth_port)
        if not auth_ready:
            logger.error(f"Auth service failed to start: /health endpoint not responding on port {auth_port} (expected 200 within 30s)")
            return False
        
        backend_ready = self._verify_backend_ready(backend_port)
        if not backend_ready:
            logger.error(f"Backend failed to start: /health/ready not responding on port {backend_port} after 30s (expected 200). Check backend logs for startup errors.")
            return False
        
        frontend_ready = self._verify_frontend_ready(frontend_port)
        if not frontend_ready:
            logger.error(f"Frontend failed to start: localhost:{frontend_port} not responding after 60s. Check frontend compilation errors.")
            return False
        
        return True
    
    def _verify_auth_ready(self, port: int = 8081) -> bool:
        """Verify auth service is ready."""
        from dev_launcher.utils import wait_for_service_with_details
        # Try /health/ready first (new), fall back to /health (legacy)
        auth_ready_url = f"http://localhost:{port}/health/ready"
        success, details = wait_for_service_with_details(auth_ready_url, timeout=30)
        if not success:
            # Fallback to basic health endpoint
            auth_url = f"http://localhost:{port}/health"
            success, details = wait_for_service_with_details(auth_url, timeout=30)
            if not success and details:
                logger.debug(f"Auth service check failed: {details}")
        return success
    
    def _verify_backend_ready(self, port: int = 8000) -> bool:
        """Verify backend service is ready."""
        from dev_launcher.utils import wait_for_service_with_details
        backend_url = f"http://localhost:{port}/health/ready" 
        success, details = wait_for_service_with_details(backend_url, timeout=30)
        if not success and details:
            logger.debug(f"Backend service check failed: {details}")
        return success
    
    def _verify_frontend_ready(self, port: int = 3000) -> bool:
        """Verify frontend service is ready."""
        from dev_launcher.utils import wait_for_service_with_details
        frontend_url = f"http://localhost:{port}"
        success, details = wait_for_service_with_details(frontend_url, timeout=60)
        if not success and details:
            logger.debug(f"Frontend service check failed: {details}")
        return success
    
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        print_with_emoji(emoji, text, message, self.use_emoji)