#!/usr/bin/env python3
"""
Demo Auth SSOT Compliance Check - Clean Scenario

This script demonstrates how the auth compliance checker would work
in a "clean" codebase with no JWT violations.

This shows what the output would look like after cleanup.
"""

import tempfile
import os
from pathlib import Path

# Import our compliance checker
from check_auth_ssot_compliance import AuthSSOTComplianceChecker


def create_clean_demo_files():
    """Create demo files that should pass compliance checks."""
    temp_dir = Path(tempfile.mkdtemp())
    
    # Create clean backend structure
    backend_dir = temp_dir / "netra_backend" / "app"
    backend_dir.mkdir(parents=True)
    
    # Clean auth client (uses auth service properly)
    clean_auth_client = """
from netra_backend.app.clients.auth_service_client import AuthServiceClient

class CleanAuthClient:
    def __init__(self):
        self.auth_client = AuthServiceClient()
    
    async def check_token(self, token):
        # Properly delegates to auth service
        result = await self.auth_client.validate_token(token)
        return result
    
    async def get_user_permissions(self, user_id):
        # Uses auth service for permissions
        permissions = await self.auth_client.get_permissions(user_id)
        return permissions
"""
    
    # Clean middleware (no JWT operations)
    clean_middleware = """
from netra_backend.app.clients.auth_service_client import AuthServiceClient

class CleanAuthMiddleware:
    def __init__(self):
        self.auth_client = AuthServiceClient()
    
    async def process_request(self, request):
        token = self.extract_token(request)
        
        # Delegate to auth service instead of local JWT operations
        validation_result = await self.auth_client.validate_token(token)
        
        if validation_result.get('valid'):
            request.user_id = validation_result.get('user_id')
            request.permissions = validation_result.get('permissions', [])
        
        return validation_result.get('valid', False)
    
    def extract_token(self, request):
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        return None
"""
    
    # Clean WebSocket handler (uses auth service client)
    clean_websocket = """
from netra_backend.app.clients.auth_service_client import AuthServiceClient

class CleanWebSocketHandler:
    def __init__(self):
        self.auth_client = AuthServiceClient()
    
    async def authenticate_connection(self, websocket):
        token = self.extract_websocket_token(websocket)
        
        # Use auth service for validation - no local JWT operations
        validation_result = await self.auth_client.validate_token(token)
        
        if validation_result.get('valid'):
            return {
                'user_id': validation_result.get('user_id'),
                'permissions': validation_result.get('permissions', [])
            }
        
        return None
    
    def extract_websocket_token(self, websocket):
        # Extract token from WebSocket headers
        auth_header = websocket.headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        return None
"""
    
    # Write clean files
    (backend_dir / "clean_auth_client.py").write_text(clean_auth_client)
    (backend_dir / "clean_middleware.py").write_text(clean_middleware) 
    (backend_dir / "clean_websocket.py").write_text(clean_websocket)
    
    # Create shared directory with only allowed files
    shared_dir = temp_dir / "shared"
    shared_dir.mkdir(parents=True)
    
    clean_shared_util = """
from shared.isolated_environment import get_env

class CleanSharedUtil:
    def __init__(self):
        self.env = get_env()
    
    def get_service_config(self):
        return {
            'auth_service_url': self.env.get('AUTH_SERVICE_URL'),
            'service_timeout': self.env.get('SERVICE_TIMEOUT', 30)
        }
"""
    
    (shared_dir / "clean_shared_util.py").write_text(clean_shared_util)
    
    return temp_dir


def run_clean_demo():
    """Run compliance check on clean demo files."""
    print("="*70)
    print("AUTH SSOT COMPLIANCE CHECK - CLEAN SCENARIO DEMO")
    print("="*70)
    
    # Create clean demo files
    print("\n[1] Creating clean demo files...")
    demo_dir = create_clean_demo_files()
    print(f"    Demo files created at: {demo_dir}")
    
    print("\n[2] Files created:")
    for py_file in demo_dir.rglob("*.py"):
        rel_path = py_file.relative_to(demo_dir)
        print(f"    - {rel_path}")
    
    print("\n[3] Running compliance check...")
    
    # Run compliance checker
    checker = AuthSSOTComplianceChecker(demo_dir)
    result = checker.run_compliance_check(exclude_tests=True)
    
    print("\n[4] Results:")
    checker.print_results(result, verbose=False)
    
    # Cleanup
    print(f"\n[5] Cleaning up demo files...")
    import shutil
    shutil.rmtree(demo_dir)
    print("    Demo files cleaned up")
    
    print("\n" + "="*70)
    print("DEMO CONCLUSION")
    print("="*70)
    print("\nThis demonstrates what the compliance check looks like when:")
    print("[OK] Backend delegates all auth operations to auth service")
    print("[OK] No direct JWT imports or operations in backend")
    print("[OK] Clean service boundaries are maintained")
    print("[OK] WebSocket uses auth service client instead of local JWT")
    print("\nIn a clean codebase, this tool ensures violations don't creep back in!")


if __name__ == "__main__":
    run_clean_demo()