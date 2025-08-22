#!/usr/bin/env python3
"""
Integration Status Analyzer Module
Handles integration checks between components.
Complies with 450-line and 25-line function limits.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

try:
    from .status_types import (
        ApiSyncStatus,
        IntegrationStatus,
        OAuthStatus,
        StatusConfig,
        WebSocketStatus,
    )
except ImportError:
    from status_types import (
        ApiSyncStatus,
        IntegrationStatus,
        OAuthStatus,
        StatusConfig,
        WebSocketStatus,
    )


class IntegrationAnalyzer:
    """Analyzes integration status between components"""
    
    def __init__(self, config: StatusConfig):
        self.config = config
        self.project_root = config.project_root
    
    def check_integration_status(self) -> IntegrationStatus:
        """Check all integration points"""
        websocket = self._check_websocket_integration()
        api_sync = self._check_api_sync()
        oauth = self._check_oauth_integration()
        
        return IntegrationStatus(
            websocket=websocket,
            api_sync=api_sync,
            oauth=oauth
        )
    
    def _check_websocket_integration(self) -> WebSocketStatus:
        """Check WebSocket integration status"""
        backend_status = self._check_backend_websocket()
        frontend_status = self._check_frontend_websocket()
        
        return WebSocketStatus(
            backend_configured=backend_status['configured'],
            frontend_configured=frontend_status,
            heartbeat_enabled=backend_status['heartbeat'],
            auth_enabled=backend_status['auth']
        )
    
    def _check_backend_websocket(self) -> Dict[str, bool]:
        """Check backend WebSocket configuration"""
        ws_manager = self.project_root / "app" / "ws_manager.py"
        if not ws_manager.exists():
            return {'configured': False, 'heartbeat': False, 'auth': False}
        
        content = self._read_file_safely(ws_manager)
        return {
            'configured': True,
            'heartbeat': "heartbeat" in content.lower() if content else False,
            'auth': "authenticate" in content.lower() if content else False
        }
    
    def _check_frontend_websocket(self) -> bool:
        """Check frontend WebSocket configuration"""
        ws_provider = self.project_root / "frontend" / "providers" / "WebSocketProvider.tsx"
        return ws_provider.exists()
    
    def _check_api_sync(self) -> ApiSyncStatus:
        """Check API endpoint synchronization"""
        backend_routes = self._scan_backend_routes()
        frontend_calls = self._scan_frontend_calls()
        
        return ApiSyncStatus(
            backend_endpoints=len(backend_routes),
            frontend_calls=len(frontend_calls),
            sample_backend=list(backend_routes)[:5],
            sample_frontend=list(frontend_calls)[:5]
        )
    
    def _scan_backend_routes(self) -> set:
        """Scan backend API routes"""
        routes = set()
        routes_dir = self.project_root / "app" / "routes"
        
        if routes_dir.exists():
            for route_file in routes_dir.glob("**/*.py"):
                file_routes = self._extract_routes_from_file(route_file)
                routes.update(file_routes)
        
        return routes
    
    def _extract_routes_from_file(self, file_path: Path) -> List[str]:
        """Extract routes from Python file"""
        content = self._read_file_safely(file_path)
        if not content:
            return []
        
        pattern = r'@\w+\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)'
        matches = re.findall(pattern, content)
        return [f"{method.upper()} {path}" for method, path in matches]
    
    def _scan_frontend_calls(self) -> set:
        """Scan frontend API calls"""
        calls = set()
        services_dir = self.project_root / "frontend" / "services"
        
        if services_dir.exists():
            for service_file in services_dir.glob("**/*.ts"):
                file_calls = self._extract_calls_from_file(service_file)
                calls.update(file_calls)
        
        return calls
    
    def _extract_calls_from_file(self, file_path: Path) -> List[str]:
        """Extract API calls from TypeScript file"""
        content = self._read_file_safely(file_path)
        if not content:
            return []
        
        pattern = r'fetch\s*\([^,]+,\s*\{[^}]*method:\s*["\'](\w+)'
        return re.findall(pattern, content, re.IGNORECASE)
    
    def _check_oauth_integration(self) -> OAuthStatus:
        """Check OAuth integration status"""
        backend_oauth = self._check_backend_oauth()
        frontend_oauth = self._check_frontend_oauth()
        
        return OAuthStatus(
            google_configured=backend_oauth['google'],
            callback_configured=backend_oauth['callback'],
            frontend_login=frontend_oauth
        )
    
    def _check_backend_oauth(self) -> Dict[str, bool]:
        """Check backend OAuth configuration"""
        oauth_file = self.project_root / "app" / "auth" / "oauth.py"
        if not oauth_file.exists():
            return {'google': False, 'callback': False}
        
        content = self._read_file_safely(oauth_file)
        return {
            'google': "google" in content.lower() if content else False,
            'callback': "callback" in content.lower() if content else False
        }
    
    def _check_frontend_oauth(self) -> bool:
        """Check frontend OAuth implementation"""
        auth_dir = self.project_root / "frontend" / "app" / "auth"
        if not auth_dir.exists():
            return False
        
        for auth_file in auth_dir.glob("**/*.tsx"):
            content = self._read_file_safely(auth_file)
            if content and "google" in content.lower():
                return True
        return False
    
    def _read_file_safely(self, file_path: Path) -> Optional[str]:
        """Read file content safely"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None