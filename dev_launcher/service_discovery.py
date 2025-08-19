"""
Service discovery for development environment.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ServiceDiscovery:
    """
    Service discovery for development environment.
    
    Manages service information for inter-service communication
    during development.
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize service discovery."""
        self.project_root = project_root or Path.cwd()
        self.discovery_dir = self.project_root / ".service_discovery"
        self.discovery_dir.mkdir(exist_ok=True)
    
    def write_backend_info(self, port: int):
        """Write backend service information."""
        info = self._create_backend_info(port)
        info_file = self.discovery_dir / "backend.json"
        self._write_service_info(info_file, info, "backend")
    
    def _create_backend_info(self, port: int) -> Dict[str, Any]:
        """Create backend service information."""
        return {
            "port": port,
            "api_url": f"http://localhost:{port}",
            "ws_url": f"ws://localhost:{port}/ws",
            "timestamp": datetime.now().isoformat()
        }
    
    def write_frontend_info(self, port: int):
        """Write frontend service information."""
        info = self._create_frontend_info(port)
        info_file = self.discovery_dir / "frontend.json"
        self._write_service_info(info_file, info, "frontend")
    
    def _create_frontend_info(self, port: int) -> Dict[str, Any]:
        """Create frontend service information."""
        return {
            "port": port,
            "url": f"http://localhost:{port}",
            "timestamp": datetime.now().isoformat()
        }
    
    def _write_service_info(self, info_file: Path, info: Dict, service_name: str):
        """Write service information to file."""
        with open(info_file, 'w') as f:
            json.dump(info, f, indent=2)
        logger.debug(f"Wrote {service_name} service discovery to {info_file}")
    
    def read_backend_info(self) -> Optional[Dict[str, Any]]:
        """Read backend service information."""
        info_file = self.discovery_dir / "backend.json"
        return self._read_service_info(info_file)
    
    def read_frontend_info(self) -> Optional[Dict[str, Any]]:
        """Read frontend service information."""
        info_file = self.discovery_dir / "frontend.json"
        return self._read_service_info(info_file)
    
    def _read_service_info(self, info_file: Path) -> Optional[Dict[str, Any]]:
        """Read service information from file."""
        if info_file.exists():
            with open(info_file, 'r') as f:
                return json.load(f)
        return None
    
    def write_auth_info(self, info: Dict[str, Any]):
        """Write auth service information."""
        info_file = self.discovery_dir / "auth.json"
        self._write_service_info(info_file, info, "auth")
    
    def read_auth_info(self) -> Optional[Dict[str, Any]]:
        """Read auth service information."""
        info_file = self.discovery_dir / "auth.json"
        return self._read_service_info(info_file)
    
    def clear_all(self):
        """Clear all service discovery information."""
        for file in self.discovery_dir.glob("*.json"):
            file.unlink()
        logger.debug("Cleared all service discovery information")