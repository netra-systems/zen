"""
L3 Integration Test: Authentication Permission Checks
Tests authorization and permission validation
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.services.auth_service import AuthService
from netra_backend.app.config import settings

# Add project root to path


class TestAuthPermissionChecksL3:
    """Test authentication permission and authorization scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_role_based_access_control(self):
        """Test role-based access control"""
        auth_service = AuthService()
        
        users = [
            {"id": "1", "username": "admin", "role": "admin"},
            {"id": "2", "username": "user", "role": "user"},
            {"id": "3", "username": "guest", "role": "guest"}
        ]
        
        for user in users:
            with patch.object(auth_service, '_get_user', return_value=user):
                # Check admin permissions
                can_admin = await auth_service.check_permission(user["id"], "admin:write")
                assert can_admin == (user["role"] == "admin")
                
                # Check user permissions
                can_read = await auth_service.check_permission(user["id"], "user:read")
                assert can_read == (user["role"] in ["admin", "user"])
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_resource_level_permissions(self):
        """Test resource-specific permission checks"""
        auth_service = AuthService()
        
        user = {"id": "123", "username": "testuser", "role": "user"}
        
        with patch.object(auth_service, '_get_user', return_value=user):
            # Own resource
            can_edit_own = await auth_service.check_resource_permission(
                user["id"], "resource:123", "edit"
            )
            assert can_edit_own is True
            
            # Other's resource
            can_edit_other = await auth_service.check_resource_permission(
                user["id"], "resource:456", "edit"
            )
            assert can_edit_other is False
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_permission_inheritance(self):
        """Test permission inheritance through role hierarchy"""
        auth_service = AuthService()
        
        # Admin inherits all permissions
        admin = {"id": "1", "username": "admin", "role": "admin", "permissions": ["*"]}
        
        with patch.object(auth_service, '_get_user', return_value=admin):
            permissions = [
                "user:read", "user:write", 
                "admin:read", "admin:write",
                "system:config"
            ]
            
            for perm in permissions:
                has_perm = await auth_service.check_permission(admin["id"], perm)
                assert has_perm is True, f"Admin should have {perm} permission"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_permission_caching(self):
        """Test permission check caching for performance"""
        auth_service = AuthService()
        
        user = {"id": "123", "username": "testuser", "permissions": ["read", "write"]}
        
        with patch.object(auth_service, '_get_user', return_value=user) as mock_get:
            # First check - should hit database
            result1 = await auth_service.check_permission(user["id"], "read")
            assert result1 is True
            assert mock_get.call_count == 1
            
            # Second check - should use cache
            result2 = await auth_service.check_permission(user["id"], "read")
            assert result2 is True
            assert mock_get.call_count == 1  # No additional call
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_dynamic_permission_updates(self):
        """Test dynamic permission updates without re-login"""
        auth_service = AuthService()
        
        user = {"id": "123", "username": "testuser", "permissions": ["read"]}
        
        with patch.object(auth_service, '_get_user', return_value=user):
            # Initial permission check
            can_write = await auth_service.check_permission(user["id"], "write")
            assert can_write is False
            
            # Update permissions
            user["permissions"].append("write")
            await auth_service.refresh_permissions(user["id"])
            
            # Check updated permission
            can_write_now = await auth_service.check_permission(user["id"], "write")
            assert can_write_now is True