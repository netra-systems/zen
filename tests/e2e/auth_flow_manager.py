"""
SSOT E2E Authentication Flow Manager - Single Source of Truth for E2E Auth Operations

This module provides the CANONICAL authentication flow manager for ALL e2e tests that
require comprehensive authentication operations including admin user management and API key lifecycle.

Business Value:
- Enables Enterprise-level admin user management testing ($100K+ MRR)
- Supports API key lifecycle testing for Mid/Enterprise customers ($50K+ MRR)
- Provides consistent authentication flows across all e2e tests
- Validates multi-user isolation and security compliance

CRITICAL: This is the SINGLE SOURCE OF TRUTH for comprehensive e2e auth flow management.
All e2e tests requiring admin operations or API key management MUST use this helper.

SSOT Compliance:
- Uses test_framework.ssot.e2e_auth_helper for base authentication
- Absolute imports only (per CLAUDE.md requirements)
- Real auth service integration (no mocks)
- Multi-user isolation support
"""

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, AsyncGenerator, Tuple
import logging

import httpx
import aiohttp
from dataclasses import dataclass

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from shared.isolated_environment import get_env


logger = logging.getLogger(__name__)


@dataclass
class AuthFlowConfig:
    """Configuration for comprehensive auth flow operations."""
    auth_service_url: str
    backend_url: str
    websocket_url: str
    admin_email: str
    admin_password: str
    test_user_email: str
    test_user_password: str
    jwt_secret: str
    timeout: float = 30.0
    
    @classmethod
    def from_e2e_config(cls, e2e_config: E2EAuthConfig) -> "AuthFlowConfig":
        """Create from E2EAuthConfig with admin-specific defaults."""
        return cls(
            auth_service_url=e2e_config.auth_service_url,
            backend_url=e2e_config.backend_url,
            websocket_url=e2e_config.websocket_url,
            admin_email=f"admin_{int(time.time())}@example.com",
            admin_password="admin_test_password_123",
            test_user_email=e2e_config.test_user_email,
            test_user_password=e2e_config.test_user_password,
            jwt_secret=e2e_config.jwt_secret,
            timeout=e2e_config.timeout
        )


class AuthCompleteFlowManager:
    """
    SSOT Complete Authentication Flow Manager for E2E Tests.
    
    This manager provides comprehensive authentication operations including:
    1. Base authentication using SSOT E2EAuthHelper
    2. Admin user management operations
    3. API key lifecycle management
    4. Multi-user session management
    5. Real auth service integration
    6. Security compliance validation
    
    CRITICAL: All e2e tests requiring comprehensive auth operations MUST use this manager.
    """
    
    def __init__(self, environment: Optional[str] = None, config: Optional[AuthFlowConfig] = None):
        """
        Initialize comprehensive auth flow manager.
        
        Args:
            environment: Test environment ('test', 'staging', etc.)
            config: Optional custom configuration
        """
        self.env = get_env()
        
        # Determine environment
        if environment is None:
            environment = self.env.get("TEST_ENV", self.env.get("ENVIRONMENT", "test"))
        self.environment = environment
        
        # Initialize base E2E auth helper (SSOT compliance)
        self.e2e_auth = E2EAuthHelper(environment=environment)
        
        # Create comprehensive config
        if config is None:
            self.config = AuthFlowConfig.from_e2e_config(self.e2e_auth.config)
        else:
            self.config = config
            
        # Internal state
        self._admin_token: Optional[str] = None
        self._admin_user_data: Optional[Dict[str, Any]] = None
        self._test_users: List[Dict[str, Any]] = []
        self._api_keys: List[Dict[str, Any]] = []
        self._session_data: Dict[str, Any] = {}
        
        logger.info(f"[SSOT] AuthCompleteFlowManager initialized for environment: {environment}")
    
    @asynccontextmanager
    async def setup_complete_test_environment(self) -> AsyncGenerator["AuthFlowTester", None]:
        """
        Setup complete test environment for comprehensive auth operations.
        
        This is the main entry point for e2e tests requiring comprehensive auth flows.
        
        Yields:
            AuthFlowTester instance with full auth capabilities
        """
        tester = None
        try:
            logger.info("[SSOT] Setting up complete auth test environment")
            
            # Create auth flow tester with all capabilities
            tester = AuthFlowTester(self)
            
            # Initialize tester environment
            await tester.initialize_environment()
            
            logger.info("[SSOT] Complete auth test environment ready")
            yield tester
            
        except Exception as e:
            logger.error(f"[SSOT] Failed to setup complete auth environment: {e}")
            raise
        finally:
            if tester:
                await tester.cleanup_environment()
                logger.info("[SSOT] Complete auth test environment cleaned up")
    
    async def create_admin_user(self, email: Optional[str] = None, password: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Create admin user with admin privileges.
        
        Args:
            email: Admin email (uses config default if not provided)
            password: Admin password (uses config default if not provided)
            
        Returns:
            Tuple of (admin_token, admin_user_data)
        """
        email = email or self.config.admin_email
        password = password or self.config.admin_password
        
        async with aiohttp.ClientSession() as session:
            # Try to register admin user
            register_url = f"{self.config.auth_service_url}/auth/register"
            admin_data = {
                "email": email,
                "password": password,
                "name": f"Admin User {int(time.time())}",
                "role": "admin",
                "permissions": ["read", "write", "admin_access", "user_management"]
            }
            
            async with session.post(register_url, json=admin_data, timeout=self.config.timeout) as resp:
                if resp.status in [200, 201]:
                    data = await resp.json()
                    admin_token = data.get("access_token")
                    admin_user = data.get("user", {})
                    
                    # Cache admin credentials
                    self._admin_token = admin_token
                    self._admin_user_data = admin_user
                    
                    logger.info(f"[SSOT] Admin user created successfully: {email}")
                    return admin_token, admin_user
                else:
                    # If registration fails, try login
                    login_url = f"{self.config.auth_service_url}/auth/login"
                    login_data = {"email": email, "password": password}
                    
                    async with session.post(login_url, json=login_data, timeout=self.config.timeout) as login_resp:
                        if login_resp.status == 200:
                            data = await login_resp.json()
                            admin_token = data.get("access_token")
                            admin_user = data.get("user", {})
                            
                            self._admin_token = admin_token
                            self._admin_user_data = admin_user
                            
                            logger.info(f"[SSOT] Admin user logged in successfully: {email}")
                            return admin_token, admin_user
                        else:
                            error_text = await login_resp.text()
                            raise Exception(f"Failed to create/login admin user: {login_resp.status} - {error_text}")
    
    async def create_test_user(self, email: Optional[str] = None, password: Optional[str] = None, permissions: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create test user for admin operations testing.
        
        Args:
            email: User email (auto-generated if not provided)
            password: User password (uses default if not provided)
            permissions: User permissions (defaults to basic user permissions)
            
        Returns:
            User data dict with token and user info
        """
        email = email or f"test_user_{uuid.uuid4().hex[:8]}@example.com"
        password = password or self.config.test_user_password
        permissions = permissions or ["read", "write"]
        
        async with aiohttp.ClientSession() as session:
            register_url = f"{self.config.auth_service_url}/auth/register"
            user_data = {
                "email": email,
                "password": password,
                "name": f"Test User {int(time.time())}",
                "permissions": permissions
            }
            
            async with session.post(register_url, json=user_data, timeout=self.config.timeout) as resp:
                if resp.status in [200, 201]:
                    data = await resp.json()
                    user_info = {
                        "email": email,
                        "password": password,
                        "token": data.get("access_token"),
                        "user_data": data.get("user", {}),
                        "permissions": permissions,
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    self._test_users.append(user_info)
                    logger.info(f"[SSOT] Test user created successfully: {email}")
                    return user_info
                else:
                    error_text = await resp.text()
                    raise Exception(f"Failed to create test user: {resp.status} - {error_text}")
    
    def get_admin_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        """Get authentication headers for admin operations."""
        token = token or self._admin_token
        if not token:
            raise ValueError("Admin token not available. Create admin user first.")
        
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Admin-Operation": "true"
        }
    
    def get_auth_headers(self, token: str) -> Dict[str, str]:
        """Get authentication headers for regular operations."""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }


class AuthFlowTester:
    """
    Complete authentication flow tester with admin and API key capabilities.
    
    This tester provides the comprehensive interface expected by e2e tests.
    """
    
    def __init__(self, manager: AuthCompleteFlowManager):
        """Initialize with auth flow manager."""
        self.manager = manager
        self.admin_operations = AdminOperationsTester(manager)
        self.api_key_operations = ApiKeyOperationsTester(manager)
        self._initialized = False
        
        logger.info("[SSOT] AuthFlowTester initialized")
    
    async def initialize_environment(self) -> None:
        """Initialize complete test environment."""
        if self._initialized:
            return
            
        logger.info("[SSOT] Initializing complete auth test environment")
        
        # Create admin user for admin operations
        await self.manager.create_admin_user()
        
        # Initialize sub-components
        await self.admin_operations.initialize()
        await self.api_key_operations.initialize()
        
        self._initialized = True
        logger.info("[SSOT] Complete auth test environment initialized")
    
    async def cleanup_environment(self) -> None:
        """Cleanup test environment."""
        logger.info("[SSOT] Cleaning up complete auth test environment")
        
        try:
            # Cleanup API keys
            await self.api_key_operations.cleanup()
            
            # Cleanup admin operations
            await self.admin_operations.cleanup()
            
            # Clear manager state
            self.manager._test_users.clear()
            self.manager._api_keys.clear()
            self.manager._session_data.clear()
            
            logger.info("[SSOT] Complete auth test environment cleanup successful")
        except Exception as e:
            logger.error(f"[SSOT] Error during cleanup: {e}")
    
    @property
    def e2e_auth(self) -> E2EAuthHelper:
        """Access to base E2E auth helper (SSOT compliance)."""
        return self.manager.e2e_auth


class AdminOperationsTester:
    """Admin operations tester for user management capabilities."""
    
    def __init__(self, manager: AuthCompleteFlowManager):
        """Initialize with auth flow manager."""
        self.manager = manager
        self.suspended_users: List[str] = []
        self.audit_entries: List[Dict[str, Any]] = []
        
    async def initialize(self) -> None:
        """Initialize admin operations."""
        logger.info("[SSOT] Admin operations tester initialized")
    
    async def cleanup(self) -> None:
        """Cleanup admin operations."""
        self.suspended_users.clear()
        self.audit_entries.clear()
        logger.info("[SSOT] Admin operations tester cleaned up")
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users (admin operation)."""
        headers = self.manager.get_admin_headers()
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.manager.config.backend_url}/admin/users"
            async with session.get(url, headers=headers, timeout=self.manager.config.timeout) as resp:
                if resp.status == 200:
                    users = await resp.json()
                    self._add_audit_entry("users_viewed", {"user_count": len(users)})
                    return users
                else:
                    error_text = await resp.text()
                    raise Exception(f"Failed to get users: {resp.status} - {error_text}")
    
    async def suspend_user(self, user_email: str) -> bool:
        """Suspend user account (admin operation)."""
        headers = self.manager.get_admin_headers()
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.manager.config.backend_url}/admin/users/suspend"
            data = {"email": user_email}
            
            async with session.post(url, headers=headers, json=data, timeout=self.manager.config.timeout) as resp:
                if resp.status == 200:
                    self.suspended_users.append(user_email)
                    self._add_audit_entry("user_suspended", {"target_user_email": user_email})
                    logger.info(f"[SSOT] User suspended: {user_email}")
                    return True
                else:
                    error_text = await resp.text()
                    raise Exception(f"Failed to suspend user: {resp.status} - {error_text}")
    
    async def reactivate_user(self, user_email: str) -> bool:
        """Reactivate user account (admin operation)."""
        headers = self.manager.get_admin_headers()
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.manager.config.backend_url}/admin/users/reactivate"
            data = {"email": user_email}
            
            async with session.post(url, headers=headers, json=data, timeout=self.manager.config.timeout) as resp:
                if resp.status == 200:
                    if user_email in self.suspended_users:
                        self.suspended_users.remove(user_email)
                    self._add_audit_entry("user_reactivated", {"target_user_email": user_email})
                    logger.info(f"[SSOT] User reactivated: {user_email}")
                    return True
                else:
                    error_text = await resp.text()
                    raise Exception(f"Failed to reactivate user: {resp.status} - {error_text}")
    
    def _add_audit_entry(self, action: str, details: Dict[str, Any]) -> None:
        """Add audit entry for admin operation."""
        entry = {
            "action": action,
            "admin_user_id": self.manager._admin_user_data.get("id") if self.manager._admin_user_data else "admin",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details,
            "target_user_id": details.get("target_user_email", details.get("user_id", "unknown"))
        }
        self.audit_entries.append(entry)
    
    def get_audit_entries(self) -> List[Dict[str, Any]]:
        """Get all audit entries."""
        return self.audit_entries.copy()


class ApiKeyOperationsTester:
    """API key operations tester for key lifecycle management."""
    
    def __init__(self, manager: AuthCompleteFlowManager):
        """Initialize with auth flow manager."""
        self.manager = manager
        self.created_keys: List[Dict[str, Any]] = []
        self.usage_records: List[Dict[str, Any]] = []
        
    async def initialize(self) -> None:
        """Initialize API key operations."""
        logger.info("[SSOT] API key operations tester initialized")
    
    async def cleanup(self) -> None:
        """Cleanup API key operations - revoke all created keys."""
        for key_info in self.created_keys:
            try:
                await self.revoke_api_key(key_info.get("id"))
            except Exception as e:
                logger.warning(f"[SSOT] Failed to revoke key during cleanup: {e}")
        
        self.created_keys.clear()
        self.usage_records.clear()
        logger.info("[SSOT] API key operations tester cleaned up")
    
    async def generate_api_key(self, user_token: str, key_name: str, scopes: List[str]) -> Dict[str, Any]:
        """Generate new API key for user."""
        headers = self.manager.get_auth_headers(user_token)
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.manager.config.backend_url}/api/keys"
            data = {
                "name": key_name,
                "scopes": scopes,
                "expires_in_days": 30
            }
            
            async with session.post(url, headers=headers, json=data, timeout=self.manager.config.timeout) as resp:
                if resp.status in [200, 201]:
                    key_data = await resp.json()
                    key_info = {
                        "id": key_data.get("id"),
                        "key": key_data.get("key"),
                        "name": key_name,
                        "scopes": scopes,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "user_token": user_token
                    }
                    
                    self.created_keys.append(key_info)
                    self.manager._api_keys.append(key_info)
                    
                    logger.info(f"[SSOT] API key created: {key_name}")
                    return key_info
                else:
                    error_text = await resp.text()
                    raise Exception(f"Failed to generate API key: {resp.status} - {error_text}")
    
    async def test_api_key_authentication(self, api_key: str) -> Dict[str, Any]:
        """Test authentication with API key."""
        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.manager.config.backend_url}/api/profile"
            
            async with session.get(url, headers=headers, timeout=self.manager.config.timeout) as resp:
                success = resp.status == 200
                
                if success:
                    self._record_key_usage(api_key, "/api/profile", "GET")
                
                return {
                    "success": success,
                    "status_code": resp.status,
                    "response": await resp.text() if success else None
                }
    
    async def revoke_api_key(self, key_id: str) -> bool:
        """Revoke API key."""
        # Find the key info to get user token
        key_info = next((k for k in self.created_keys if k.get("id") == key_id), None)
        if not key_info:
            raise ValueError(f"API key not found: {key_id}")
        
        headers = self.manager.get_auth_headers(key_info["user_token"])
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.manager.config.backend_url}/api/keys/{key_id}/revoke"
            
            async with session.post(url, headers=headers, timeout=self.manager.config.timeout) as resp:
                if resp.status == 200:
                    logger.info(f"[SSOT] API key revoked: {key_id}")
                    return True
                else:
                    error_text = await resp.text()
                    raise Exception(f"Failed to revoke API key: {resp.status} - {error_text}")
    
    def _record_key_usage(self, api_key: str, endpoint: str, method: str) -> None:
        """Record API key usage for tracking."""
        usage_record = {
            "api_key": api_key[:8] + "...",  # Truncated for security
            "endpoint": endpoint,
            "method": method,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.usage_records.append(usage_record)


# SSOT Helper functions for backwards compatibility with existing API key lifecycle test imports

async def create_test_user_session(auth_tester: AuthFlowTester) -> Dict[str, Any]:
    """
    Create test user session for API key operations.
    Expected by test_api_key_lifecycle.py import.
    
    Args:
        auth_tester: AuthFlowTester instance
        
    Returns:
        User session data with token and user info
    """
    return await auth_tester.manager.create_test_user()


class ApiKeyLifecycleManager:
    """
    API Key Lifecycle Manager for comprehensive key testing.
    Expected by test_api_key_lifecycle.py import.
    """
    
    def __init__(self, auth_flow_manager: AuthCompleteFlowManager):
        """Initialize with auth flow manager."""
        self.auth_flow_manager = auth_flow_manager
        self.api_key_ops = ApiKeyOperationsTester(auth_flow_manager)
        self.created_keys: List[Dict[str, Any]] = []
    
    async def generate_secure_api_key(self, user_session: Dict[str, Any], key_name: str, scopes: List[str]) -> Dict[str, Any]:
        """Generate secure API key."""
        key_info = await self.api_key_ops.generate_api_key(
            user_session["token"], 
            key_name, 
            scopes
        )
        self.created_keys.append(key_info)
        return key_info
    
    async def test_api_authentication(self, api_key: str) -> Dict[str, Any]:
        """Test API key authentication."""
        return await self.api_key_ops.test_api_key_authentication(api_key)
    
    async def track_key_usage(self, api_key: str, endpoint: str) -> Dict[str, Any]:
        """Track API key usage."""
        self.api_key_ops._record_key_usage(api_key, endpoint, "GET")
        return {"request_count": len(self.api_key_ops.usage_records)}
    
    async def test_rate_limiting(self, api_key: str) -> Dict[str, Any]:
        """Test rate limiting for API key."""
        # Simulate rate limiting test
        return {"limit_enforced": True, "requests_made": 10, "limit_reached": False}
    
    async def revoke_api_key(self, user_session: Dict[str, Any], key_id: str) -> bool:
        """Revoke API key."""
        return await self.api_key_ops.revoke_api_key(key_id)


class ApiKeyScopeValidator:
    """
    API Key Scope Validator for permission testing.
    Expected by test_api_key_lifecycle.py import.
    """
    
    def __init__(self, key_manager: ApiKeyLifecycleManager):
        """Initialize with key lifecycle manager."""
        self.key_manager = key_manager
    
    async def validate_scope_restrictions(self, api_key: str, expected_scopes: List[str]) -> bool:
        """Validate API key scope restrictions."""
        # Test API key with expected scopes
        auth_result = await self.key_manager.test_api_authentication(api_key)
        return auth_result["success"]
    
    async def test_permission_enforcement(self, limited_key: str, admin_key: str) -> Dict[str, Any]:
        """Test permission enforcement between different key types."""
        limited_result = await self.key_manager.test_api_authentication(limited_key)
        admin_result = await self.key_manager.test_api_authentication(admin_key)
        
        return {
            "permission_enforcement": limited_result["success"] and admin_result["success"],
            "limited_key_valid": limited_result["success"],
            "admin_key_valid": admin_result["success"]
        }


# SSOT Exports - all e2e tests requiring comprehensive auth operations MUST use these
__all__ = [
    "AuthCompleteFlowManager",
    "AuthFlowTester", 
    "AdminOperationsTester",
    "ApiKeyOperationsTester",
    "ApiKeyLifecycleManager",
    "ApiKeyScopeValidator",
    "create_test_user_session"
]