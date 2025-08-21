"""
Service discovery for development environment.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

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
    
    def get_all_service_origins(self) -> list[str]:
        """Get all service origins for CORS integration."""
        origins = []
        
        # Add backend origins
        backend_info = self.read_backend_info()
        if backend_info:
            if backend_info.get('api_url'):
                origins.append(backend_info['api_url'])
            if backend_info.get('ws_url'):
                # Convert ws:// to http:// for CORS origin matching
                ws_url = backend_info['ws_url'].replace('ws://', 'http://').replace('wss://', 'https://')
                origins.append(ws_url.split('/')[0] + '//' + ws_url.split('//')[1].split('/')[0])
        
        # Add frontend origins
        frontend_info = self.read_frontend_info()
        if frontend_info and frontend_info.get('url'):
            origins.append(frontend_info['url'])
        
        # Add auth service origins
        auth_info = self.read_auth_info()
        if auth_info:
            if auth_info.get('url'):
                origins.append(auth_info['url'])
            if auth_info.get('api_url'):
                origins.append(auth_info['api_url'])
        
        return list(set(filter(None, origins)))  # Remove duplicates and None values
    
    def register_service_for_cors(self, service_name: str, service_info: Dict[str, Any]) -> None:
        """Register a service with enhanced CORS metadata."""
        enhanced_info = {
            **service_info,
            'cors_metadata': {
                'registered_at': datetime.now().isoformat(),
                'service_id': f"netra-{service_name.lower()}",
                'supports_cross_service': True,
                'cors_headers_required': [
                    'Authorization',
                    'Content-Type', 
                    'X-Request-ID',
                    'X-Trace-ID',
                    'X-Service-ID',
                    'X-Cross-Service-Auth'
                ]
            }
        }
        
        info_file = self.discovery_dir / f"{service_name.lower()}.json"
        self._write_service_info(info_file, enhanced_info, service_name)
    
    def get_service_cors_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get CORS configuration for a specific service."""
        service_info = None
        
        if service_name.lower() == 'backend':
            service_info = self.read_backend_info()
        elif service_name.lower() == 'frontend':
            service_info = self.read_frontend_info()
        elif service_name.lower() == 'auth':
            service_info = self.read_auth_info()
        
        if service_info and 'cors_metadata' in service_info:
            return service_info['cors_metadata']
        
        return None
    
    def is_service_registered(self, service_name: str) -> bool:
        """Check if a service is registered in discovery."""
        info_file = self.discovery_dir / f"{service_name.lower()}.json"
        return info_file.exists()
    
    def get_cross_service_auth_token(self) -> Optional[str]:
        """Get cross-service authentication token from environment or discovery."""
        # Check environment first
        token = os.getenv('CROSS_SERVICE_AUTH_TOKEN')
        if token:
            return token
        
        # Check if token is stored in service discovery
        token_file = self.discovery_dir / "cross_service_token"
        if token_file.exists():
            return token_file.read_text().strip()
        
        return None
    
    def set_cross_service_auth_token(self, token: str) -> None:
        """Store cross-service authentication token."""
        token_file = self.discovery_dir / "cross_service_token"
        token_file.write_text(token)
        logger.debug("Stored cross-service auth token")