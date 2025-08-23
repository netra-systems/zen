#!/usr/bin/env python3
"""
Integration Configuration Fix Script

Fixes:
1. Dynamic auth service port discovery and frontend .env.local update
2. WebSocket URL configuration alignment
3. CORS configuration validation
4. Service discovery integration

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity  
- Value Impact: Eliminates manual configuration steps
- Strategic Impact: Ensures consistent dev environment setup
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dev_launcher.service_discovery import ServiceDiscovery


class IntegrationConfigFixer:
    """Fixes integration configuration issues."""
    
    def __init__(self):
        """Initialize the configuration fixer."""
        self.project_root = project_root
        self.service_discovery = ServiceDiscovery(project_root)
        self.fixes_applied = []
        self.errors = []
    
    def log_fix(self, component: str, description: str, success: bool = True):
        """Log a fix that was applied."""
        status = "✅" if success else "❌"
        print(f"{status} {component}: {description}")
        
        self.fixes_applied.append({
            "component": component,
            "description": description,
            "success": success,
            "timestamp": time.time()
        })
        
        if not success:
            self.errors.append(f"{component}: {description}")
    
    def read_service_info(self) -> Dict[str, Optional[Dict]]:
        """Read service discovery information."""
        print("🔍 Reading service discovery information...")
        
        try:
            services = {
                "backend": self.service_discovery.read_backend_info(),
                "auth": self.service_discovery.read_auth_info(),
                "frontend": self.service_discovery.read_frontend_info()
            }
            
            for service_name, info in services.items():
                if info:
                    self.log_fix(
                        f"service_discovery",
                        f"{service_name} found at {info.get('url', 'N/A')}"
                    )
                else:
                    self.log_fix(
                        f"service_discovery",
                        f"{service_name} service not found",
                        success=False
                    )
            
            return services
            
        except Exception as e:
            self.log_fix(
                "service_discovery",
                f"Failed to read service info: {e}",
                success=False
            )
            return {}
    
    def fix_frontend_env_local(self, services: Dict) -> bool:
        """Fix frontend .env.local with correct service URLs."""
        print("\n🔧 Fixing frontend .env.local configuration...")
        
        env_local_path = self.project_root / "frontend" / ".env.local"
        
        if not env_local_path.exists():
            self.log_fix(
                "frontend_env",
                f"Creating .env.local at {env_local_path}",
                success=False
            )
            return False
        
        try:
            # Read current .env.local
            with open(env_local_path, 'r') as f:
                env_content = f.read()
            
            original_content = env_content
            
            # Extract service URLs
            backend_info = services.get("backend")
            auth_info = services.get("auth")
            
            if backend_info:
                backend_url = backend_info.get("api_url", "http://localhost:8000")
                # Update API URL
                if "NEXT_PUBLIC_API_URL=" in env_content:
                    env_content = re.sub(
                        r'NEXT_PUBLIC_API_URL=.*',
                        f'NEXT_PUBLIC_API_URL={backend_url}',
                        env_content
                    )
                else:
                    env_content += f"\nNEXT_PUBLIC_API_URL={backend_url}\n"
                
                # Fix WebSocket URL - use standard /ws endpoint
                ws_url = backend_url.replace("http://", "ws://") + "/ws"
                if "NEXT_PUBLIC_WEBSOCKET_URL=" in env_content:
                    env_content = re.sub(
                        r'NEXT_PUBLIC_WEBSOCKET_URL=.*',
                        f'NEXT_PUBLIC_WEBSOCKET_URL={ws_url}',
                        env_content
                    )
                else:
                    env_content += f"NEXT_PUBLIC_WEBSOCKET_URL={ws_url}\n"
                
                self.log_fix(
                    "frontend_env",
                    f"Updated backend URL to {backend_url} and WebSocket URL to {ws_url}"
                )
            
            if auth_info:
                auth_url = auth_info.get("url", "http://localhost:8081")
                # Update auth service URL
                if "NEXT_PUBLIC_AUTH_SERVICE_URL=" in env_content:
                    env_content = re.sub(
                        r'NEXT_PUBLIC_AUTH_SERVICE_URL=.*',
                        f'NEXT_PUBLIC_AUTH_SERVICE_URL={auth_url}',
                        env_content
                    )
                else:
                    env_content += f"NEXT_PUBLIC_AUTH_SERVICE_URL={auth_url}\n"
                
                self.log_fix(
                    "frontend_env",
                    f"Updated auth service URL to {auth_url}"
                )
            
            # Only write if content changed
            if env_content != original_content:
                with open(env_local_path, 'w') as f:
                    f.write(env_content)
                
                self.log_fix(
                    "frontend_env",
                    f"Updated {env_local_path}"
                )
                return True
            else:
                self.log_fix(
                    "frontend_env",
                    "No changes needed"
                )
                return True
                
        except Exception as e:
            self.log_fix(
                "frontend_env",
                f"Failed to update .env.local: {e}",
                success=False
            )
            return False
    
    def create_websocket_route_fix(self) -> bool:
        """Create a WebSocket route that matches frontend expectations."""
        print("\n🔌 Checking WebSocket route configuration...")
        
        # Check if we need to add a standard /ws route
        websocket_routes_path = self.project_root / "netra_backend" / "app" / "routes" / "websocket.py"
        
        if not websocket_routes_path.exists():
            # Create a simple WebSocket route that forwards to secure endpoint
            websocket_route_content = '''"""
Standard WebSocket endpoint that forwards to secure WebSocket implementation.

This provides backward compatibility for frontends expecting /ws endpoint.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Standard WebSocket endpoint - redirects to secure implementation.
    
    This endpoint exists for backward compatibility with frontends
    that expect a /ws endpoint. It forwards to /ws.
    """
    # For WebSocket, we can't do HTTP redirects, so we need to
    # handle the connection here and forward to the secure endpoint
    
    # Import the unified WebSocket handler
    from netra_backend.app.routes.websocket_unified import unified_websocket_endpoint
    
    # Delegate to unified endpoint
    await unified_websocket_endpoint(websocket)

@router.get("/ws")
async def websocket_info():
    """Information endpoint for WebSocket connection."""
    return {
        "message": "WebSocket endpoint available",
        "endpoint": "/ws",
        "secure_endpoint": "/ws",
        "status": "available"
    }
'''
            try:
                with open(websocket_routes_path, 'w') as f:
                    f.write(websocket_route_content)
                
                self.log_fix(
                    "websocket_route",
                    f"Created WebSocket route at {websocket_routes_path}"
                )
                return True
                
            except Exception as e:
                self.log_fix(
                    "websocket_route",
                    f"Failed to create WebSocket route: {e}",
                    success=False
                )
                return False
        else:
            self.log_fix(
                "websocket_route", 
                "WebSocket route already exists"
            )
            return True
    
    def validate_cors_configuration(self, services: Dict) -> bool:
        """Validate CORS configuration supports the frontend."""
        print("\n🌐 Validating CORS configuration...")
        
        frontend_info = services.get("frontend")
        if not frontend_info:
            self.log_fix(
                "cors_validation",
                "No frontend info available for CORS validation",
                success=False
            )
            return False
        
        frontend_url = frontend_info.get("url", "http://localhost:3000")
        
        # Check backend CORS middleware configuration
        cors_middleware_path = self.project_root / "netra_backend" / "app" / "core" / "middleware_setup.py"
        
        if cors_middleware_path.exists():
            try:
                with open(cors_middleware_path, 'r') as f:
                    cors_content = f.read()
                
                # Check if localhost origins are included
                if "localhost" in cors_content and ("3000" in cors_content or "*" in cors_content):
                    self.log_fix(
                        "cors_validation",
                        f"CORS configuration supports {frontend_url}"
                    )
                    return True
                else:
                    self.log_fix(
                        "cors_validation",
                        f"CORS may not support {frontend_url}",
                        success=False
                    )
                    return False
                    
            except Exception as e:
                self.log_fix(
                    "cors_validation",
                    f"Failed to read CORS configuration: {e}",
                    success=False
                )
                return False
        else:
            self.log_fix(
                "cors_validation",
                "CORS middleware file not found",
                success=False
            )
            return False
    
    def create_service_restart_script(self, services: Dict) -> bool:
        """Create a script to restart services with correct configuration."""
        print("\n🔄 Creating service restart script...")
        
        restart_script_path = self.project_root / "restart_services.py"
        
        restart_script_content = '''#!/usr/bin/env python3
"""
Service Restart Script

Restarts all services with correct port configuration.
Generated by integration configuration fixer.
"""

import subprocess
import sys
import time
from pathlib import Path

def restart_dev_services():
    """Restart development services."""
    print("🔄 Restarting development services...")
    
    project_root = Path(__file__).parent
    
    try:
        # Use the dev launcher to restart all services
        dev_launcher_path = project_root / "scripts" / "dev_launcher.py"
        
        if dev_launcher_path.exists():
            print("Starting services with dev launcher...")
            result = subprocess.run([
                sys.executable, str(dev_launcher_path)
            ], cwd=project_root)
            
            if result.returncode == 0:
                print("✅ Services started successfully")
                return True
            else:
                print(f"❌ Dev launcher failed with code {result.returncode}")
                return False
        else:
            print(f"❌ Dev launcher not found at {dev_launcher_path}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to restart services: {e}")
        return False

if __name__ == "__main__":
    success = restart_dev_services()
    sys.exit(0 if success else 1)
'''
        
        try:
            with open(restart_script_path, 'w') as f:
                f.write(restart_script_content)
            
            # Make it executable on Unix systems
            if sys.platform != "win32":
                os.chmod(restart_script_path, 0o755)
            
            self.log_fix(
                "restart_script",
                f"Created service restart script at {restart_script_path}"
            )
            return True
            
        except Exception as e:
            self.log_fix(
                "restart_script",
                f"Failed to create restart script: {e}",
                success=False
            )
            return False
    
    def create_test_commands(self) -> bool:
        """Create test commands script."""
        print("\n🧪 Creating test commands...")
        
        test_commands_path = self.project_root / "test_integration.py" 
        
        # The integration test is already created, just reference it
        if (self.project_root / "integration_test.py").exists():
            self.log_fix(
                "test_commands",
                "Integration test available at integration_test.py"
            )
            return True
        else:
            self.log_fix(
                "test_commands",
                "Integration test script not found",
                success=False
            )
            return False
    
    def print_summary(self):
        """Print summary of fixes applied."""
        print("\n" + "="*60)
        print("🔧 CONFIGURATION FIX SUMMARY")
        print("="*60)
        
        total_fixes = len(self.fixes_applied)
        successful_fixes = sum(1 for fix in self.fixes_applied if fix["success"])
        failed_fixes = total_fixes - successful_fixes
        
        print(f"Total Fixes Attempted: {total_fixes}")
        print(f"✅ Successful: {successful_fixes}")
        print(f"❌ Failed: {failed_fixes}")
        
        if failed_fixes > 0:
            print(f"\n❌ FAILED FIXES:")
            for error in self.errors:
                print(f"  • {error}")
        
        print(f"\n📋 NEXT STEPS:")
        print(f"1. Run the integration test: python integration_test.py")
        print(f"2. Restart services if needed: python restart_services.py")
        print(f"3. Check frontend can connect to auth and WebSocket")
        
        # Save results
        results_file = self.project_root / "integration_fix_results.json"
        with open(results_file, 'w') as f:
            json.dump({
                "fixes_applied": self.fixes_applied,
                "errors": self.errors,
                "timestamp": time.time()
            }, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        print("="*60)
    
    def apply_all_fixes(self):
        """Apply all integration fixes."""
        print("🔧 Starting Integration Configuration Fixes...")
        print("="*60)
        
        # Step 1: Read service information
        services = self.read_service_info()
        
        # Step 2: Fix frontend .env.local
        self.fix_frontend_env_local(services)
        
        # Step 3: Ensure WebSocket route exists
        self.create_websocket_route_fix()
        
        # Step 4: Validate CORS configuration
        self.validate_cors_configuration(services)
        
        # Step 5: Create restart script
        self.create_service_restart_script(services)
        
        # Step 6: Verify test commands
        self.create_test_commands()
        
        # Print summary
        self.print_summary()
        
        return len(self.errors) == 0


def main():
    """Main function."""
    print("🔧 Netra Integration Configuration Fixer")
    print("Fixing Auth Service and WebSocket Integration Issues")
    print("=" * 60)
    
    try:
        fixer = IntegrationConfigFixer()
        success = fixer.apply_all_fixes()
        
        if success:
            print("\n🎉 All configuration fixes applied successfully!")
            return 0
        else:
            print(f"\n⚠️  Some fixes failed - check the output above")
            return 1
            
    except Exception as e:
        print(f"\n💥 Configuration fixer failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)