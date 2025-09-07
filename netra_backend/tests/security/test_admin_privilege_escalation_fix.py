"""
CRITICAL SECURITY TEST: Admin Privilege Escalation Vulnerability Fix Validation

This test suite validates the fix for the HIGH severity admin privilege escalation 
vulnerability reported in the security audit. 

VULNERABILITY DESCRIPTION:
- Client-controlled admin flags were trusted without server-side validation
- Admin status could be manipulated through request body or database manipulation
- JWT claims were not properly validated for admin operations

SECURITY FIX VALIDATION:
- Ensures admin status is validated from JWT claims only
- Tests that client-provided admin flags are ignored
- Validates comprehensive audit logging for all admin operations
- Confirms proper error handling and security logging

Test Categories:
1. JWT-based admin validation tests
2. Privilege escalation prevention tests  
3. Audit logging validation tests
4. Security boundary tests
5. Error handling and attack detection tests
"""

import json
import jwt
import pytest
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.routes.admin import (
    verify_admin_role_from_jwt,
    require_admin_with_jwt_validation,
    log_admin_operation
)
from netra_backend.app.auth_integration.auth import (
    extract_admin_status_from_jwt,
    require_admin_with_enhanced_validation,
    _sync_jwt_claims_to_user_record
)
from netra_backend.app.db.models_user import User
from netra_backend.app.services.audit_service import AuditService


class TestJWTAdminValidation:
    """Test JWT-based admin validation."""
    
    @pytest.mark.asyncio
    async def test_verify_admin_role_from_jwt_valid_admin(self):
        """Test that valid admin JWT returns True."""
        # Mock auth_client validation
        mock_validation = {
            "valid": True,
            "user_id": "admin_user_123",
            "role": "admin",
            "permissions": ["admin", "system:*"]
        }
        
        with patch('netra_backend.app.routes.admin.auth_client') as mock_auth_client:
            mock_auth_client.validate_token_jwt = AsyncMock(return_value=mock_validation)
            
            result = await verify_admin_role_from_jwt("valid_admin_token")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_verify_admin_role_from_jwt_non_admin(self):
        """Test that non-admin JWT returns False."""
        mock_validation = {
            "valid": True,
            "user_id": "regular_user_123",
            "role": "user",
            "permissions": ["user"]
        }
        
        with patch('netra_backend.app.routes.admin.auth_client') as mock_auth_client:
            mock_auth_client.validate_token_jwt = AsyncMock(return_value=mock_validation)
            
            result = await verify_admin_role_from_jwt("valid_user_token")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_verify_admin_role_from_jwt_invalid_token(self):
        """Test that invalid JWT returns False."""
        mock_validation = {
            "valid": False,
            "error": "Token expired"
        }
        
        with patch('netra_backend.app.routes.admin.auth_client') as mock_auth_client:
            mock_auth_client.validate_token_jwt = AsyncMock(return_value=mock_validation)
            
            result = await verify_admin_role_from_jwt("invalid_token")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_verify_admin_role_from_jwt_super_admin(self):
        """Test that super_admin role is recognized."""
        mock_validation = {
            "valid": True,
            "user_id": "super_admin_123",
            "role": "super_admin",
            "permissions": ["system:*"]
        }
        
        with patch('netra_backend.app.routes.admin.auth_client') as mock_auth_client:
            mock_auth_client.validate_token_jwt = AsyncMock(return_value=mock_validation)
            
            result = await verify_admin_role_from_jwt("valid_super_admin_token")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_verify_admin_role_from_jwt_admin_permission(self):
        """Test that admin permission in JWT grants access."""
        mock_validation = {
            "valid": True,
            "user_id": "admin_perm_user_123",
            "role": "power_user",
            "permissions": ["user", "admin", "config:read"]
        }
        
        with patch('netra_backend.app.routes.admin.auth_client') as mock_auth_client:
            mock_auth_client.validate_token_jwt = AsyncMock(return_value=mock_validation)
            
            result = await verify_admin_role_from_jwt("valid_admin_perm_token")
            assert result is True


class TestPrivilegeEscalationPrevention:
    """Test prevention of privilege escalation attacks."""
    
    @pytest.mark.asyncio
    async def test_client_provided_admin_flag_ignored(self):
        """Test that client-provided admin flags in request body are ignored."""
        # This test ensures that even if a malicious client sends admin=true
        # in the request body, it's ignored and JWT validation is used
        
        mock_request = MagicNone  # TODO: Use real service instance
        mock_request.headers = {"authorization": "Bearer fake_user_token"}
        mock_request.client.host = "127.0.0.1"
        mock_request.url = "http://test.com/admin/settings"
        
        mock_user = User()
        mock_user.id = "regular_user_123"
        mock_user.role = "user"
        mock_user.is_superuser = False
        
        # JWT says user is NOT admin
        mock_jwt_validation = {
            "valid": True,
            "user_id": "regular_user_123",
            "role": "user",
            "permissions": ["user"]
        }
        
        with patch('netra_backend.app.routes.admin.auth_client') as mock_auth_client:
            mock_auth_client.validate_token_jwt = AsyncMock(return_value=mock_jwt_validation)
            
            # This should raise 403 even if client tries to manipulate admin status
            with pytest.raises(HTTPException) as exc_info:
                await require_admin_with_jwt_validation(mock_request, mock_user)
            
            assert exc_info.value.status_code == 403
            assert "Admin access required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_database_admin_override_by_jwt(self):
        """Test that JWT admin status overrides database record."""
        # Test case where database says user is admin but JWT says otherwise
        
        mock_request = MagicNone  # TODO: Use real service instance
        mock_request.headers = {"authorization": "Bearer admin_token"}
        mock_request.client.host = "127.0.0.1"
        mock_request.url = "http://test.com/admin/settings"
        
        # Database says user is NOT admin
        mock_user = User()
        mock_user.id = "admin_user_123"
        mock_user.role = "user"  # Database has wrong role
        mock_user.is_superuser = False  # Database has wrong admin status
        
        # But JWT says user IS admin (authoritative)
        mock_jwt_validation = {
            "valid": True,
            "user_id": "admin_user_123",
            "role": "admin",
            "permissions": ["admin", "system:*"]
        }
        
        with patch('netra_backend.app.routes.admin.auth_client') as mock_auth_client:
            mock_auth_client.validate_token_jwt = AsyncMock(return_value=mock_jwt_validation)
            
            with patch('netra_backend.app.routes.admin.log_admin_operation') as mock_log:
                mock_log.return_value = AsyncNone  # TODO: Use real service instance
                
                # Should succeed because JWT is authoritative
                result = await require_admin_with_jwt_validation(mock_request, mock_user)
                assert result == mock_user
                
                # Verify audit log was called
                mock_log.assert_called()
    
    @pytest.mark.asyncio
    async def test_jwt_token_tampering_detection(self):
        """Test detection of JWT token tampering attempts."""
        mock_request = MagicNone  # TODO: Use real service instance
        mock_request.headers = {"authorization": "Bearer tampered_token"}
        mock_request.client.host = "192.168.1.100"
        mock_request.url = "http://test.com/admin/settings"
        
        mock_user = User()
        mock_user.id = "attacker_123"
        
        # Simulate tampered/invalid JWT
        mock_jwt_validation = {
            "valid": False,
            "error": "Invalid signature"
        }
        
        with patch('netra_backend.app.routes.admin.auth_client') as mock_auth_client:
            mock_auth_client.validate_token_jwt = AsyncMock(return_value=mock_jwt_validation)
            
            with patch('netra_backend.app.routes.admin.log_admin_operation') as mock_log:
                mock_log.return_value = AsyncNone  # TODO: Use real service instance
                
                with pytest.raises(HTTPException) as exc_info:
                    await require_admin_with_jwt_validation(mock_request, mock_user)
                
                assert exc_info.value.status_code == 403
                
                # Verify security violation was logged
                mock_log.assert_called()
                call_args = mock_log.call_args
                assert "UNAUTHORIZED_ADMIN_ACCESS_ATTEMPT" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_missing_bearer_token_detection(self):
        """Test detection of missing Bearer token."""
        mock_request = MagicNone  # TODO: Use real service instance
        mock_request.headers = {}  # No authorization header
        mock_request.client.host = "10.0.0.1"
        
        mock_user = User()
        mock_user.id = "user_123"
        
        with pytest.raises(HTTPException) as exc_info:
            await require_admin_with_jwt_validation(mock_request, mock_user)
        
        assert exc_info.value.status_code == 401
        assert "Bearer token missing" in str(exc_info.value.detail)


class TestAuditLoggingValidation:
    """Test comprehensive audit logging for admin operations."""
    
    @pytest.mark.asyncio
    async def test_admin_operation_logged(self):
        """Test that admin operations are properly logged."""
        mock_audit_service = MagicNone  # TODO: Use real service instance
        mock_audit_service.log_action = AsyncNone  # TODO: Use real service instance
        
        with patch('netra_backend.app.routes.admin.audit_service', mock_audit_service):
            await log_admin_operation(
                "SET_LOG_TABLE",
                "admin_user_123", 
                {"old_table": "logs_old", "new_table": "logs_new"},
                "192.168.1.10"
            )
            
            mock_audit_service.log_action.assert_called_once()
            call_args = mock_audit_service.log_action.call_args[0]
            
            assert call_args[0] == "ADMIN_SET_LOG_TABLE"
            assert call_args[1] == "admin_user_123"
            assert "old_table" in call_args[2]
            assert "new_table" in call_args[2]
            assert "timestamp" in call_args[2]
            assert "ip_address" in call_args[2]
    
    @pytest.mark.asyncio
    async def test_unauthorized_access_attempt_logged(self):
        """Test that unauthorized admin access attempts are logged."""
        mock_request = MagicNone  # TODO: Use real service instance
        mock_request.headers = {"authorization": "Bearer user_token"}
        mock_request.client.host = "suspicious.ip.address"
        mock_request.url = "http://test.com/admin/settings"
        mock_request.headers.get.return_value = "MaliciousBot/1.0"
        
        mock_user = User()
        mock_user.id = "regular_user_123"
        
        mock_jwt_validation = {
            "valid": True,
            "user_id": "regular_user_123",
            "role": "user",
            "permissions": ["user"]
        }
        
        with patch('netra_backend.app.routes.admin.auth_client') as mock_auth_client:
            mock_auth_client.validate_token_jwt = AsyncMock(return_value=mock_jwt_validation)
            
            with patch('netra_backend.app.routes.admin.log_admin_operation') as mock_log:
                mock_log.return_value = AsyncNone  # TODO: Use real service instance
                
                with pytest.raises(HTTPException):
                    await require_admin_with_jwt_validation(mock_request, mock_user)
                
                # Verify security violation was logged with full details
                mock_log.assert_called_with(
                    "UNAUTHORIZED_ADMIN_ACCESS_ATTEMPT",
                    "regular_user_123",
                    {
                        "reason": "Insufficient admin privileges in JWT",
                        "user_agent": "MaliciousBot/1.0",
                        "attempted_endpoint": "http://test.com/admin/settings"
                    },
                    "suspicious.ip.address"
                )
    
    @pytest.mark.asyncio
    async def test_successful_admin_access_logged(self):
        """Test that successful admin access is logged."""
        mock_request = MagicNone  # TODO: Use real service instance
        mock_request.headers = {"authorization": "Bearer admin_token"}
        mock_request.client.host = "192.168.1.5"
        mock_request.url = "http://test.com/admin/settings"
        mock_request.headers.get.return_value = "Chrome/91.0"
        
        mock_user = User()
        mock_user.id = "admin_user_123"
        
        mock_jwt_validation = {
            "valid": True,
            "user_id": "admin_user_123",
            "role": "admin",
            "permissions": ["admin", "system:*"]
        }
        
        with patch('netra_backend.app.routes.admin.auth_client') as mock_auth_client:
            mock_auth_client.validate_token_jwt = AsyncMock(return_value=mock_jwt_validation)
            
            with patch('netra_backend.app.routes.admin.log_admin_operation') as mock_log:
                mock_log.return_value = AsyncNone  # TODO: Use real service instance
                
                result = await require_admin_with_jwt_validation(mock_request, mock_user)
                assert result == mock_user
                
                # Verify successful access was logged
                mock_log.assert_called_with(
                    "ADMIN_ACCESS_GRANTED",
                    "admin_user_123",
                    {
                        "endpoint": "http://test.com/admin/settings",
                        "user_agent": "Chrome/91.0"
                    },
                    "192.168.1.5"
                )
    
    @pytest.mark.asyncio
    async def test_audit_logging_failure_handling(self):
        """Test that audit logging failures don't break admin operations."""
        mock_audit_service = MagicNone  # TODO: Use real service instance
        mock_audit_service.log_action = AsyncMock(side_effect=Exception("Audit service down"))
        
        with patch('netra_backend.app.routes.admin.audit_service', mock_audit_service):
            # Should not raise exception even if audit fails
            await log_admin_operation(
                "TEST_OPERATION",
                "admin_user_123",
                {"test": "data"},
                "127.0.0.1"
            )
            
            # Verify it attempted to log
            mock_audit_service.log_action.assert_called_once()


class TestSecurityBoundaries:
    """Test security boundary enforcement."""
    
    @pytest.mark.asyncio
    async def test_jwt_claims_sync_to_database(self):
        """Test that JWT claims are synced to database for consistency."""
        mock_user = User()
        mock_user.id = "user_123"
        mock_user.role = "user"  # Wrong role in DB
        mock_user.is_superuser = False  # Wrong admin status in DB
        
        jwt_validation = {
            "role": "admin",
            "permissions": ["admin", "system:*"],
            "user_id": "user_123"
        }
        
        mock_db = AsyncNone  # TODO: Use real service instance
        
        await _sync_jwt_claims_to_user_record(mock_user, jwt_validation, mock_db)
        
        # Verify user record was updated to match JWT
        assert mock_user.role == "admin"
        assert mock_user.is_superuser is True
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_admin_status_comprehensive(self):
        """Test comprehensive admin status extraction from JWT."""
        mock_validation = {
            "valid": True,
            "user_id": "test_admin_123",
            "role": "admin",
            "permissions": ["admin", "config:write", "system:read"]
        }
        
        with patch('netra_backend.app.auth_integration.auth.auth_client') as mock_auth_client:
            mock_auth_client.validate_token_jwt = AsyncMock(return_value=mock_validation)
            
            result = await extract_admin_status_from_jwt("valid_admin_token")
            
            assert result["is_admin"] is True
            assert result["user_id"] == "test_admin_123"
            assert result["role"] == "admin"
            assert "admin" in result["permissions"]
            assert result["source"] == "jwt_claims"
    
    @pytest.mark.asyncio
    async def test_wildcard_permission_recognition(self):
        """Test that wildcard permissions grant admin access."""
        mock_validation = {
            "valid": True,
            "user_id": "system_admin_123",
            "role": "system_admin",
            "permissions": ["system:*"]  # Wildcard permission
        }
        
        with patch('netra_backend.app.auth_integration.auth.auth_client') as mock_auth_client:
            mock_auth_client.validate_token_jwt = AsyncMock(return_value=mock_validation)
            
            result = await extract_admin_status_from_jwt("system_admin_token")
            
            assert result["is_admin"] is True
            assert "system:*" in result["permissions"]


class TestErrorHandlingAndAttackDetection:
    """Test error handling and attack detection mechanisms."""
    
    @pytest.mark.asyncio
    async def test_jwt_validation_service_down(self):
        """Test behavior when JWT validation service is unavailable."""
        with patch('netra_backend.app.routes.admin.auth_client') as mock_auth_client:
            mock_auth_client.validate_token_jwt = AsyncMock(side_effect=Exception("Service unavailable"))
            
            result = await verify_admin_role_from_jwt("any_token")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_malformed_jwt_handling(self):
        """Test handling of malformed JWT tokens."""
        with patch('netra_backend.app.routes.admin.auth_client') as mock_auth_client:
            mock_auth_client.validate_token_jwt = AsyncMock(return_value=None)
            
            result = await verify_admin_role_from_jwt("malformed.jwt.token")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_empty_permissions_handling(self):
        """Test handling of JWT with empty permissions array."""
        mock_validation = {
            "valid": True,
            "user_id": "user_123",
            "role": "user",
            "permissions": []  # Empty permissions
        }
        
        with patch('netra_backend.app.routes.admin.auth_client') as mock_auth_client:
            mock_auth_client.validate_token_jwt = AsyncMock(return_value=mock_validation)
            
            result = await verify_admin_role_from_jwt("empty_perms_token")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_null_role_handling(self):
        """Test handling of JWT with null/missing role."""
        mock_validation = {
            "valid": True,
            "user_id": "user_123",
            "role": None,  # Null role
            "permissions": ["user"]
        }
        
        with patch('netra_backend.app.routes.admin.auth_client') as mock_auth_client:
            mock_auth_client.validate_token_jwt = AsyncMock(return_value=mock_validation)
            
            result = await verify_admin_role_from_jwt("null_role_token")
            assert result is False


@pytest.mark.asyncio
async def test_comprehensive_security_validation():
    """
    Comprehensive test that validates the entire security fix.
    
    This test simulates a complete attack scenario and verifies
    that all security measures are working correctly.
    """
    # Simulate attacker with regular user account trying to escalate privileges
    mock_request = MagicNone  # TODO: Use real service instance
    mock_request.headers = MagicNone  # TODO: Use real service instance
    
    # Mock headers properly
    def mock_headers_get(key, default=None):
        if key == "authorization":
            return "Bearer regular_user_token"
        elif key == "user-agent":
            return "AttackBot/2.0"
        return default
    
    mock_request.headers.get = MagicMock(side_effect=mock_headers_get)
    mock_request.client.host = "attacker.ip.address"
    mock_request.url = "http://test.com/admin/settings/log_table"
    
    # Attacker's user record in database
    attacker_user = User()
    attacker_user.id = "attacker_user_123"
    attacker_user.role = "user"
    attacker_user.is_superuser = False
    
    # Attacker's JWT (valid but non-admin)
    attacker_jwt_validation = {
        "valid": True,
        "user_id": "attacker_user_123", 
        "role": "user",
        "permissions": ["user", "read:basic"]
    }
    
    # Mock the auth client and audit service
    with patch('netra_backend.app.routes.admin.auth_client') as mock_auth_client:
        with patch('netra_backend.app.routes.admin.log_admin_operation') as mock_log:
            mock_auth_client.validate_token_jwt = AsyncMock(return_value=attacker_jwt_validation)
            mock_log.return_value = AsyncNone  # TODO: Use real service instance
            
            # Attempt should be blocked and logged
            with pytest.raises(HTTPException) as exc_info:
                await require_admin_with_jwt_validation(mock_request, attacker_user)
            
            # Verify security response
            assert exc_info.value.status_code == 403
            assert "Admin access required" in str(exc_info.value.detail)
            
            # Verify comprehensive audit logging
            mock_log.assert_called()
            call_args = mock_log.call_args[0]
            assert call_args[0] == "UNAUTHORIZED_ADMIN_ACCESS_ATTEMPT"
            assert call_args[1] == "attacker_user_123"
            assert "Insufficient admin privileges in JWT" in call_args[2]["reason"]
            assert call_args[3] == "attacker.ip.address"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])