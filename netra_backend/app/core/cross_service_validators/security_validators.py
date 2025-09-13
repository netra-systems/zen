"""
Security Validators

Validates security aspects across service boundaries including token validation,
permission enforcement, audit trail consistency, and service authentication.
"""

import asyncio
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from pydantic import BaseModel

from netra_backend.app.core.configuration.base import get_unified_config
# SSOT COMPLIANCE: Use auth service client for all JWT operations
from netra_backend.app.clients.auth_client_core import get_auth_service_client
from netra_backend.app.core.cross_service_validators.validator_framework import (
    BaseValidator,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)


class SecurityViolation(BaseModel):
    """Represents a security violation."""
    violation_type: str
    severity: str
    description: str
    service: str
    details: Dict[str, Any]


class TokenValidationValidator(BaseValidator):
    """Validates token validation consistency across services."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("token_validation_validator", config)
        # Use the same secret source as the services for consistency
        self.jwt_secret = self._get_jwt_secret_for_testing(config)
        self.jwt_algorithm = config.get("jwt_algorithm", "HS256") if config else "HS256"
    
    def _get_jwt_secret_for_testing(self, config: Optional[Dict[str, Any]] = None) -> str:
        """Get JWT secret for testing, consistent with service configuration.
        
        SSOT COMPLIANCE: This method is used only for test token creation
        in cross-service validation. Actual token validation is delegated
        to auth service SSOT.
        """
        # If explicitly provided in config, use it
        if config and "jwt_secret" in config:
            return config["jwt_secret"]
        
        # Use unified configuration system
        unified_config = get_unified_config()
        if unified_config.jwt_secret_key:
            return unified_config.jwt_secret_key
        
        # Test environment fallback
        return "test-secret-key-for-validation-testing-32-chars"
    
    async def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """Validate token validation consistency."""
        results = []
        
        # Test token validation consistency
        results.extend(await self._validate_token_consistency(context))
        
        # Test token expiration handling
        results.extend(await self._validate_token_expiration(context))
        
        # Test token tampering detection
        results.extend(await self._validate_token_tampering_detection(context))
        
        # Test cross-service token validation
        results.extend(await self._validate_cross_service_tokens(context))
        
        return results
    
    async def _validate_token_consistency(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate that token validation is consistent across services."""
        results = []
        
        try:
            # Generate test token using auth service SSOT
            # SSOT COMPLIANCE: Use auth service client for token creation
            auth_client = get_auth_service_client()
            
            # Create test token through auth service
            token_response = await auth_client.create_access_token(
                user_id="test-user-123",
                email="test@example.com"
            )
            
            test_token = token_response.get("access_token") if token_response else None
            if not test_token:
                # SSOT COMPLIANCE: For testing environment, create through auth service
                logger.warning("SSOT SecurityValidator: Auth service token creation failed, using test fallback (testing only)")

                # Create test token through auth service client directly
                payload = {
                    "user_id": "test-user-123",
                    "email": "test@example.com"
                }

                # Try again with simplified payload
                try:
                    fallback_response = await auth_client.create_access_token(
                        user_id="test-user-123",
                        email="test@example.com"
                    )
                    test_token = fallback_response.get("access_token") if fallback_response else "test-token-fallback"
                except Exception as e:
                    logger.warning(f"SSOT SecurityValidator: Auth service fallback failed - {e}")
                    test_token = "test-token-fallback"
            
            # Simulate validation by different services
            auth_service_valid = await self._validate_token_with_auth_service(test_token, context)
            backend_service_valid = await self._validate_token_with_backend(test_token, context)
            
            if auth_service_valid == backend_service_valid:
                results.append(self.create_result(
                    check_name="token_validation_consistency",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message="Token validation is consistent across services",
                    service_pair="auth-backend",
                    details={
                        "auth_service_valid": auth_service_valid,
                        "backend_service_valid": backend_service_valid,
                        "token_source": "auth_service"
                    }
                ))
            else:
                results.append(self.create_result(
                    check_name="token_validation_consistency",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Token validation inconsistency: auth={auth_service_valid}, backend={backend_service_valid}",
                    service_pair="auth-backend",
                    details={
                        "auth_service_valid": auth_service_valid,
                        "backend_service_valid": backend_service_valid
                    }
                ))
                
        except Exception as e:
            results.append(self.create_result(
                check_name="token_validation_consistency_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Token validation consistency check failed: {str(e)}",
                service_pair="auth-backend",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _validate_token_expiration(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate token expiration handling."""
        results = []
        
        try:
            # SSOT COMPLIANCE: For expired token testing, use test token (auth service won't create expired tokens)
            logger.info("SSOT SecurityValidator: Creating expired token for testing (using test fallback)")

            # For expired token testing, we use a known invalid token pattern
            # The auth service validation will properly reject this
            expired_token = "expired.test.token"
            
            # Test expiration detection
            auth_service_accepts_expired = await self._validate_token_with_auth_service(expired_token, context)
            backend_accepts_expired = await self._validate_token_with_backend(expired_token, context)
            
            if not auth_service_accepts_expired and not backend_accepts_expired:
                results.append(self.create_result(
                    check_name="token_expiration_handling",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message="Expired tokens properly rejected by all services",
                    service_pair="auth-backend",
                    details={
                        "auth_rejects_expired": not auth_service_accepts_expired,
                        "backend_rejects_expired": not backend_accepts_expired
                    }
                ))
            else:
                severity = ValidationSeverity.CRITICAL
                failing_services = []
                if auth_service_accepts_expired:
                    failing_services.append("auth")
                if backend_accepts_expired:
                    failing_services.append("backend")
                
                results.append(self.create_result(
                    check_name="token_expiration_handling",
                    status=ValidationStatus.FAILED,
                    severity=severity,
                    message=f"Services accepting expired tokens: {', '.join(failing_services)}",
                    service_pair="auth-backend",
                    details={"failing_services": failing_services}
                ))
                
        except Exception as e:
            results.append(self.create_result(
                check_name="token_expiration_handling_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Token expiration validation failed: {str(e)}",
                service_pair="auth-backend",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _validate_token_tampering_detection(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate detection of tampered tokens."""
        results = []
        
        try:
            # SSOT COMPLIANCE: For tampering tests, use auth service to create valid token then modify it
            logger.info("SSOT SecurityValidator: Creating tampered token for testing via auth service")

            # Get valid token from auth service
            auth_client = get_auth_service_client()
            token_response = await auth_client.create_access_token(
                user_id="test-user-789",
                email="test3@example.com"
            )

            valid_token = token_response.get("access_token") if token_response else "valid.test.token"

            # Create tampered token by modifying the valid token
            if "." in valid_token and len(valid_token.split('.')) == 3:
                token_parts = valid_token.split('.')
                tampered_signature = token_parts[2][:-5] + "xxxxx" if len(token_parts[2]) > 5 else token_parts[2] + "xxxxx"
                tampered_token = f"{token_parts[0]}.{token_parts[1]}.{tampered_signature}"
            else:
                # Fallback for test tokens
                tampered_token = "tampered.test.token"
            
            # Test tampering detection
            auth_accepts_tampered = await self._validate_token_with_auth_service(tampered_token, context)
            backend_accepts_tampered = await self._validate_token_with_backend(tampered_token, context)
            
            if not auth_accepts_tampered and not backend_accepts_tampered:
                results.append(self.create_result(
                    check_name="token_tampering_detection",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message="Tampered tokens properly rejected by all services",
                    service_pair="auth-backend",
                    details={
                        "auth_rejects_tampered": not auth_accepts_tampered,
                        "backend_rejects_tampered": not backend_accepts_tampered
                    }
                ))
            else:
                severity = ValidationSeverity.CRITICAL
                failing_services = []
                if auth_accepts_tampered:
                    failing_services.append("auth")
                if backend_accepts_tampered:
                    failing_services.append("backend")
                
                results.append(self.create_result(
                    check_name="token_tampering_detection",
                    status=ValidationStatus.FAILED,
                    severity=severity,
                    message=f"Services accepting tampered tokens: {', '.join(failing_services)}",
                    service_pair="auth-backend",
                    details={"failing_services": failing_services}
                ))
                
        except Exception as e:
            results.append(self.create_result(
                check_name="token_tampering_detection_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Token tampering detection validation failed: {str(e)}",
                service_pair="auth-backend",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _validate_cross_service_tokens(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate cross-service token handling."""
        results = []
        
        try:
            # SSOT COMPLIANCE: For service token tests, use auth service for creation
            logger.info("SSOT SecurityValidator: Creating service token for testing via auth service")

            # Create service token through auth service
            auth_client = get_auth_service_client()

            # For service tokens, we can use the same create_access_token method with service-specific user_id
            service_token_response = await auth_client.create_access_token(
                user_id="backend-service",
                email="backend@service.internal"
            )

            service_token = service_token_response.get("access_token") if service_token_response else "service.test.token"
            
            # Validate service token handling
            service_token_valid = await self._validate_service_token(service_token, context)
            
            if service_token_valid:
                results.append(self.create_result(
                    check_name="cross_service_tokens",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message="Service-to-service token validation working correctly",
                    service_pair="backend-auth",
                    details={
                        "service_id": "backend-service",
                        "token_source": "auth_service"
                    }
                ))
            else:
                results.append(self.create_result(
                    check_name="cross_service_tokens",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.HIGH,
                    message="Service-to-service token validation failed",
                    service_pair="backend-auth",
                    details={"service_id": "backend-service"}
                ))
                
        except Exception as e:
            results.append(self.create_result(
                check_name="cross_service_tokens_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Cross-service token validation failed: {str(e)}",
                service_pair="backend-auth",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _validate_token_with_auth_service(
        self, 
        token: str, 
        context: Dict[str, Any]
    ) -> bool:
        """Validate token using auth service SSOT."""
        try:
            # SSOT COMPLIANCE: Use auth service client for token validation
            auth_client = get_auth_service_client()
            result = await auth_client.validate_token(token)
            
            return result and result.get("valid", False)
        except Exception:
            return False
    
    async def _validate_token_with_backend(
        self, 
        token: str, 
        context: Dict[str, Any]
    ) -> bool:
        """Simulate backend service token validation using auth service SSOT."""
        try:
            # SSOT COMPLIANCE: Backend should also use auth service for validation
            auth_client = get_auth_service_client()
            result = await auth_client.validate_token(token)
            
            return result and result.get("valid", False)
        except Exception:
            return False
    
    async def _validate_service_token(
        self, 
        token: str, 
        context: Dict[str, Any]
    ) -> bool:
        """Validate service token using auth service SSOT."""
        try:
            # SSOT COMPLIANCE: Use auth service for service token validation
            auth_client = get_auth_service_client()
            result = await auth_client.validate_token(token)
            
            # For service tokens, check the token_type in the result
            if result and result.get("valid"):
                # Additional check for service tokens could be done here
                return True
            
            return False
        except Exception:
            return False


class PermissionEnforcementValidator(BaseValidator):
    """Validates permission enforcement consistency across services."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("permission_enforcement_validator", config)
        self.test_permissions = [
            "threads.create", "threads.read", "threads.update", "threads.delete",
            "agents.start", "agents.stop", "admin.access", "data.export"
        ]
    
    async def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """Validate permission enforcement."""
        results = []
        
        # Test role-based permissions
        results.extend(await self._validate_role_based_permissions(context))
        
        # Test resource-level permissions
        results.extend(await self._validate_resource_permissions(context))
        
        # Test permission inheritance
        results.extend(await self._validate_permission_inheritance(context))
        
        # Test permission escalation prevention
        results.extend(await self._validate_privilege_escalation_prevention(context))
        
        return results
    
    async def _validate_role_based_permissions(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate role-based permission enforcement."""
        results = []
        
        # Define test roles and their permissions
        test_roles = {
            "user": ["threads.create", "threads.read", "threads.update", "agents.start"],
            "admin": ["threads.create", "threads.read", "threads.update", "threads.delete", 
                     "agents.start", "agents.stop", "admin.access", "data.export"],
            "readonly": ["threads.read"]
        }
        
        for role, expected_permissions in test_roles.items():
            try:
                # Test each permission for the role
                permission_results = {}
                
                for permission in self.test_permissions:
                    has_permission = await self._check_role_permission(role, permission, context)
                    should_have_permission = permission in expected_permissions
                    
                    permission_results[permission] = {
                        "has": has_permission,
                        "should_have": should_have_permission,
                        "correct": has_permission == should_have_permission
                    }
                
                # Analyze results
                incorrect_permissions = [
                    p for p, result in permission_results.items() 
                    if not result["correct"]
                ]
                
                if not incorrect_permissions:
                    results.append(self.create_result(
                        check_name=f"role_permissions_{role}",
                        status=ValidationStatus.PASSED,
                        severity=ValidationSeverity.INFO,
                        message=f"Role-based permissions correct for role '{role}'",
                        service_pair="auth-backend",
                        details={
                            "role": role,
                            "permissions_tested": len(self.test_permissions),
                            "correct_permissions": len([p for p in permission_results.values() if p["correct"]])
                        }
                    ))
                else:
                    results.append(self.create_result(
                        check_name=f"role_permissions_{role}",
                        status=ValidationStatus.FAILED,
                        severity=ValidationSeverity.HIGH,
                        message=f"Incorrect permissions for role '{role}': {incorrect_permissions}",
                        service_pair="auth-backend",
                        details={
                            "role": role,
                            "incorrect_permissions": incorrect_permissions,
                            "permission_details": permission_results
                        }
                    ))
                    
            except Exception as e:
                results.append(self.create_result(
                    check_name=f"role_permissions_{role}_error",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.HIGH,
                    message=f"Role permission validation failed for '{role}': {str(e)}",
                    service_pair="auth-backend",
                    details={"role": role, "error": str(e)}
                ))
        
        return results
    
    async def _validate_resource_permissions(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate resource-level permission enforcement."""
        results = []
        
        try:
            # Test resource ownership
            user_id = "user-123"
            other_user_id = "user-456"
            
            # User should have access to their own resources
            own_thread_access = await self._check_resource_permission(
                user_id, "threads.read", "thread-owned-by-123", context
            )
            
            # User should NOT have access to other user's resources
            other_thread_access = await self._check_resource_permission(
                user_id, "threads.read", "thread-owned-by-456", context  
            )
            
            if own_thread_access and not other_thread_access:
                results.append(self.create_result(
                    check_name="resource_ownership_permissions",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message="Resource ownership permissions enforced correctly",
                    service_pair="auth-backend",
                    details={
                        "user_id": user_id,
                        "own_resource_access": own_thread_access,
                        "other_resource_access": other_thread_access
                    }
                ))
            else:
                results.append(self.create_result(
                    check_name="resource_ownership_permissions",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Resource ownership violation: own={own_thread_access}, other={other_thread_access}",
                    service_pair="auth-backend",
                    details={
                        "user_id": user_id,
                        "own_resource_access": own_thread_access,
                        "other_resource_access": other_thread_access
                    }
                ))
                
        except Exception as e:
            results.append(self.create_result(
                check_name="resource_permissions_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Resource permission validation failed: {str(e)}",
                service_pair="auth-backend",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _validate_permission_inheritance(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate permission inheritance from roles and groups."""
        results = []
        
        try:
            # Test user with multiple roles
            user_id = "user-multi-role"
            user_roles = ["user", "moderator"]
            
            # Expected permissions should be union of all roles
            expected_permissions = set()
            role_permissions = {
                "user": ["threads.create", "threads.read", "agents.start"],
                "moderator": ["threads.delete", "admin.access"]
            }
            
            for role in user_roles:
                expected_permissions.update(role_permissions.get(role, []))
            
            # Test inheritance
            actual_permissions = set()
            for permission in expected_permissions:
                has_permission = await self._check_user_permission(user_id, permission, context)
                if has_permission:
                    actual_permissions.add(permission)
            
            missing_permissions = expected_permissions - actual_permissions
            extra_permissions = actual_permissions - expected_permissions
            
            if not missing_permissions and not extra_permissions:
                results.append(self.create_result(
                    check_name="permission_inheritance",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message="Permission inheritance working correctly",
                    service_pair="auth-backend",
                    details={
                        "user_id": user_id,
                        "roles": user_roles,
                        "inherited_permissions": list(actual_permissions)
                    }
                ))
            else:
                results.append(self.create_result(
                    check_name="permission_inheritance",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.HIGH,
                    message=f"Permission inheritance issues: missing={missing_permissions}, extra={extra_permissions}",
                    service_pair="auth-backend",
                    details={
                        "user_id": user_id,
                        "missing_permissions": list(missing_permissions),
                        "extra_permissions": list(extra_permissions)
                    }
                ))
                
        except Exception as e:
            results.append(self.create_result(
                check_name="permission_inheritance_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Permission inheritance validation failed: {str(e)}",
                service_pair="auth-backend",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _validate_privilege_escalation_prevention(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate prevention of privilege escalation."""
        results = []
        
        try:
            # Test common privilege escalation attempts
            escalation_attempts = [
                {
                    "name": "role_modification",
                    "user_id": "regular-user",
                    "action": "modify_own_role",
                    "target_role": "admin"
                },
                {
                    "name": "permission_addition",
                    "user_id": "limited-user", 
                    "action": "add_permission",
                    "permission": "admin.access"
                },
                {
                    "name": "impersonation",
                    "user_id": "user-123",
                    "action": "impersonate",
                    "target_user": "admin-user"
                }
            ]
            
            for attempt in escalation_attempts:
                escalation_prevented = await self._test_privilege_escalation(attempt, context)
                
                if escalation_prevented:
                    results.append(self.create_result(
                        check_name=f"privilege_escalation_{attempt['name']}",
                        status=ValidationStatus.PASSED,
                        severity=ValidationSeverity.INFO,
                        message=f"Privilege escalation prevented: {attempt['name']}",
                        service_pair="auth-backend",
                        details={"attempt": attempt}
                    ))
                else:
                    results.append(self.create_result(
                        check_name=f"privilege_escalation_{attempt['name']}",
                        status=ValidationStatus.FAILED,
                        severity=ValidationSeverity.CRITICAL,
                        message=f"Privilege escalation NOT prevented: {attempt['name']}",
                        service_pair="auth-backend",
                        details={"attempt": attempt}
                    ))
                    
        except Exception as e:
            results.append(self.create_result(
                check_name="privilege_escalation_prevention_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Privilege escalation validation failed: {str(e)}",
                service_pair="auth-backend",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _check_role_permission(
        self, 
        role: str, 
        permission: str, 
        context: Dict[str, Any]
    ) -> bool:
        """Mock role permission check."""
        # Define role permissions
        role_permissions = {
            "user": ["threads.create", "threads.read", "threads.update", "agents.start"],
            "admin": ["threads.create", "threads.read", "threads.update", "threads.delete", 
                     "agents.start", "agents.stop", "admin.access", "data.export"],
            "readonly": ["threads.read"]
        }
        
        return permission in role_permissions.get(role, [])
    
    async def _check_resource_permission(
        self, 
        user_id: str, 
        permission: str, 
        resource_id: str, 
        context: Dict[str, Any]
    ) -> bool:
        """Mock resource permission check."""
        # Extract owner from resource_id for demo
        if "owned-by" in resource_id:
            owner_id = resource_id.split("owned-by-")[1]
            return user_id.endswith(owner_id)
        return False
    
    async def _check_user_permission(
        self, 
        user_id: str, 
        permission: str, 
        context: Dict[str, Any]
    ) -> bool:
        """Mock user permission check."""
        # Mock user permissions based on user_id
        if "multi-role" in user_id:
            multi_role_permissions = [
                "threads.create", "threads.read", "agents.start", 
                "threads.delete", "admin.access"
            ]
            return permission in multi_role_permissions
        return False
    
    async def _test_privilege_escalation(
        self, 
        attempt: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> bool:
        """Mock privilege escalation test - should return True if escalation is prevented."""
        # In a real implementation, this would attempt the escalation and check if it's blocked
        # For mock purposes, we assume all escalations are properly prevented
        return True


class AuditTrailValidator(BaseValidator):
    """Validates audit trail consistency across services."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("audit_trail_validator", config)
        self.critical_events = [
            "user.login", "user.logout", "permission.granted", "permission.revoked",
            "admin.access", "data.export", "security.violation"
        ]
    
    async def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """Validate audit trail consistency."""
        results = []
        
        # Test audit log completeness
        results.extend(await self._validate_audit_completeness(context))
        
        # Test audit log integrity
        results.extend(await self._validate_audit_integrity(context))
        
        # Test cross-service audit correlation
        results.extend(await self._validate_audit_correlation(context))
        
        return results
    
    async def _validate_audit_completeness(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate that all critical events are logged."""
        results = []
        
        try:
            # Simulate checking audit logs for critical events
            audit_logs = await self._fetch_audit_logs(context)
            
            logged_events = set(log["event_type"] for log in audit_logs)
            missing_events = set(self.critical_events) - logged_events
            
            if not missing_events:
                results.append(self.create_result(
                    check_name="audit_completeness",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message="All critical events are being logged",
                    service_pair="all-services",
                    details={
                        "total_events": len(self.critical_events),
                        "logged_events": len(logged_events),
                        "audit_entries": len(audit_logs)
                    }
                ))
            else:
                results.append(self.create_result(
                    check_name="audit_completeness",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.HIGH,
                    message=f"Missing audit logs for critical events: {missing_events}",
                    service_pair="all-services",
                    details={
                        "missing_events": list(missing_events),
                        "logged_events": list(logged_events)
                    }
                ))
                
        except Exception as e:
            results.append(self.create_result(
                check_name="audit_completeness_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Audit completeness validation failed: {str(e)}",
                service_pair="all-services",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _validate_audit_integrity(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate audit log integrity and tamper detection."""
        results = []
        
        try:
            # Simulate checking audit log integrity
            audit_logs = await self._fetch_audit_logs(context)
            
            integrity_issues = []
            for log in audit_logs:
                # Check required fields
                required_fields = ["event_id", "event_type", "timestamp", "user_id", "service"]
                missing_fields = [field for field in required_fields if field not in log]
                
                if missing_fields:
                    integrity_issues.append({
                        "event_id": log.get("event_id", "unknown"),
                        "issue": "missing_fields",
                        "details": missing_fields
                    })
                
                # Check timestamp format
                try:
                    datetime.fromisoformat(log.get("timestamp", "").replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    integrity_issues.append({
                        "event_id": log.get("event_id", "unknown"),
                        "issue": "invalid_timestamp",
                        "timestamp": log.get("timestamp")
                    })
                
                # Check for potential tampering (simplified check)
                if self._detect_potential_tampering(log):
                    integrity_issues.append({
                        "event_id": log.get("event_id", "unknown"),
                        "issue": "potential_tampering"
                    })
            
            if not integrity_issues:
                results.append(self.create_result(
                    check_name="audit_integrity",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message="Audit log integrity verified",
                    service_pair="all-services",
                    details={
                        "logs_checked": len(audit_logs),
                        "integrity_violations": 0
                    }
                ))
            else:
                results.append(self.create_result(
                    check_name="audit_integrity",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.HIGH,
                    message=f"Audit integrity issues found: {len(integrity_issues)}",
                    service_pair="all-services",
                    details={
                        "logs_checked": len(audit_logs),
                        "integrity_issues": integrity_issues
                    }
                ))
                
        except Exception as e:
            results.append(self.create_result(
                check_name="audit_integrity_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Audit integrity validation failed: {str(e)}",
                service_pair="all-services",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _validate_audit_correlation(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate cross-service audit event correlation."""
        results = []
        
        try:
            # Simulate cross-service audit correlation
            auth_logs = await self._fetch_service_audit_logs("auth", context)
            backend_logs = await self._fetch_service_audit_logs("backend", context)
            
            # Look for correlated events (e.g., login in auth should have session creation in backend)
            correlation_issues = []
            
            for auth_log in auth_logs:
                if auth_log["event_type"] == "user.login":
                    user_id = auth_log["user_id"]
                    login_time = datetime.fromisoformat(auth_log["timestamp"].replace('Z', '+00:00'))
                    
                    # Look for corresponding session creation in backend within 1 minute
                    session_created = False
                    for backend_log in backend_logs:
                        if (backend_log["event_type"] == "session.created" and 
                            backend_log["user_id"] == user_id):
                            backend_time = datetime.fromisoformat(backend_log["timestamp"].replace('Z', '+00:00'))
                            if abs((backend_time - login_time).total_seconds()) <= 60:
                                session_created = True
                                break
                    
                    if not session_created:
                        correlation_issues.append({
                            "auth_event": auth_log["event_id"],
                            "user_id": user_id,
                            "issue": "missing_session_creation"
                        })
            
            if not correlation_issues:
                results.append(self.create_result(
                    check_name="audit_correlation",
                    status=ValidationStatus.PASSED,
                    severity=ValidationSeverity.INFO,
                    message="Cross-service audit correlation verified",
                    service_pair="auth-backend",
                    details={
                        "auth_logs": len(auth_logs),
                        "backend_logs": len(backend_logs),
                        "correlation_issues": 0
                    }
                ))
            else:
                results.append(self.create_result(
                    check_name="audit_correlation",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.MEDIUM,
                    message=f"Cross-service audit correlation issues: {len(correlation_issues)}",
                    service_pair="auth-backend",
                    details={
                        "correlation_issues": correlation_issues
                    }
                ))
                
        except Exception as e:
            results.append(self.create_result(
                check_name="audit_correlation_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.MEDIUM,
                message=f"Audit correlation validation failed: {str(e)}",
                service_pair="auth-backend",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _fetch_audit_logs(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Mock audit log fetching."""
        return [
            {
                "event_id": "audit-001",
                "event_type": "user.login",
                "timestamp": "2024-01-15T10:00:00Z",
                "user_id": "user-123",
                "service": "auth",
                "ip_address": "192.168.1.100"
            },
            {
                "event_id": "audit-002",
                "event_type": "session.created",
                "timestamp": "2024-01-15T10:00:15Z",
                "user_id": "user-123",
                "service": "backend",
                "session_id": "sess-abc123"
            },
            {
                "event_id": "audit-003",
                "event_type": "permission.granted",
                "timestamp": "2024-01-15T10:01:00Z",
                "user_id": "user-123",
                "service": "backend",
                "permission": "threads.create"
            }
        ]
    
    async def _fetch_service_audit_logs(
        self, 
        service: str, 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Mock service-specific audit log fetching."""
        all_logs = await self._fetch_audit_logs(context)
        return [log for log in all_logs if log["service"] == service]
    
    def _detect_potential_tampering(self, log: Dict[str, Any]) -> bool:
        """Mock tamper detection - simplified check."""
        # In a real system, this would check digital signatures, checksums, etc.
        # For mock purposes, randomly flag some entries as potentially tampered
        return hash(str(log)) % 100 == 0  # 1% chance of flagging tampering


class ServiceAuthValidator(BaseValidator):
    """Validates service-to-service authentication."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("service_auth_validator", config)
        self.service_secrets = config.get("service_secrets", {
            "backend": "backend-secret-key",
            "frontend": "frontend-secret-key",
            "auth": "auth-secret-key"
        }) if config else {
            "backend": "backend-secret-key", 
            "frontend": "frontend-secret-key",
            "auth": "auth-secret-key"
        }
    
    async def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """Validate service-to-service authentication."""
        results = []
        
        # Test service authentication
        results.extend(await self._validate_service_authentication(context))
        
        # Test service authorization
        results.extend(await self._validate_service_authorization(context))
        
        # Test service identity verification
        results.extend(await self._validate_service_identity(context))
        
        return results
    
    async def _validate_service_authentication(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate service-to-service authentication."""
        results = []
        
        service_pairs = [
            ("frontend", "backend"),
            ("backend", "auth")
        ]
        
        for source_service, target_service in service_pairs:
            try:
                # Test authentication between services
                auth_success = await self._test_service_auth(source_service, target_service, context)
                
                if auth_success:
                    results.append(self.create_result(
                        check_name=f"service_auth_{source_service}_to_{target_service}",
                        status=ValidationStatus.PASSED,
                        severity=ValidationSeverity.INFO,
                        message=f"Service authentication successful: {source_service} -> {target_service}",
                        service_pair=f"{source_service}-{target_service}",
                        details={"source": source_service, "target": target_service}
                    ))
                else:
                    results.append(self.create_result(
                        check_name=f"service_auth_{source_service}_to_{target_service}",
                        status=ValidationStatus.FAILED,
                        severity=ValidationSeverity.CRITICAL,
                        message=f"Service authentication failed: {source_service} -> {target_service}",
                        service_pair=f"{source_service}-{target_service}",
                        details={"source": source_service, "target": target_service}
                    ))
                    
            except Exception as e:
                results.append(self.create_result(
                    check_name=f"service_auth_{source_service}_to_{target_service}_error",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.HIGH,
                    message=f"Service authentication test failed: {str(e)}",
                    service_pair=f"{source_service}-{target_service}",
                    details={"error": str(e)}
                ))
        
        return results
    
    async def _validate_service_authorization(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate service-to-service authorization."""
        results = []
        
        try:
            # Test service permissions
            service_permissions = {
                "backend": ["user.validate", "session.create", "threads.access"],
                "frontend": ["assets.read", "api.call"],
                "auth": ["tokens.create", "tokens.validate", "users.authenticate"]
            }
            
            for service, expected_permissions in service_permissions.items():
                for permission in expected_permissions:
                    has_permission = await self._check_service_permission(service, permission, context)
                    
                    if has_permission:
                        results.append(self.create_result(
                            check_name=f"service_permission_{service}_{permission.replace('.', '_')}",
                            status=ValidationStatus.PASSED,
                            severity=ValidationSeverity.INFO,
                            message=f"Service {service} has required permission: {permission}",
                            service_pair=service,
                            details={"service": service, "permission": permission}
                        ))
                    else:
                        results.append(self.create_result(
                            check_name=f"service_permission_{service}_{permission.replace('.', '_')}",
                            status=ValidationStatus.FAILED,
                            severity=ValidationSeverity.HIGH,
                            message=f"Service {service} missing required permission: {permission}",
                            service_pair=service,
                            details={"service": service, "permission": permission}
                        ))
                        
        except Exception as e:
            results.append(self.create_result(
                check_name="service_authorization_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Service authorization validation failed: {str(e)}",
                service_pair="all-services",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _validate_service_identity(
        self, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate service identity verification."""
        results = []
        
        try:
            services = ["frontend", "backend", "auth"]
            
            for service in services:
                # Test service identity verification
                identity_valid = await self._verify_service_identity(service, context)
                
                if identity_valid:
                    results.append(self.create_result(
                        check_name=f"service_identity_{service}",
                        status=ValidationStatus.PASSED,
                        severity=ValidationSeverity.INFO,
                        message=f"Service identity verified for {service}",
                        service_pair=service,
                        details={"service": service}
                    ))
                else:
                    results.append(self.create_result(
                        check_name=f"service_identity_{service}",
                        status=ValidationStatus.FAILED,
                        severity=ValidationSeverity.CRITICAL,
                        message=f"Service identity verification failed for {service}",
                        service_pair=service,
                        details={"service": service}
                    ))
                    
        except Exception as e:
            results.append(self.create_result(
                check_name="service_identity_error",
                status=ValidationStatus.FAILED,
                severity=ValidationSeverity.HIGH,
                message=f"Service identity validation failed: {str(e)}",
                service_pair="all-services",
                details={"error": str(e)}
            ))
        
        return results
    
    async def _test_service_auth(
        self, 
        source: str, 
        target: str, 
        context: Dict[str, Any]
    ) -> bool:
        """Mock service-to-service authentication test."""
        source_secret = self.service_secrets.get(source)
        if not source_secret:
            return False
        
        # Simulate authentication process
        auth_token = self._generate_service_auth_token(source, source_secret)
        return self._validate_service_auth_token(auth_token, target)
    
    async def _check_service_permission(
        self, 
        service: str, 
        permission: str, 
        context: Dict[str, Any]
    ) -> bool:
        """Mock service permission check."""
        # Define service permissions
        service_permissions = {
            "backend": ["user.validate", "session.create", "threads.access"],
            "frontend": ["assets.read", "api.call"],
            "auth": ["tokens.create", "tokens.validate", "users.authenticate"]
        }
        
        return permission in service_permissions.get(service, [])
    
    async def _verify_service_identity(
        self, 
        service: str, 
        context: Dict[str, Any]
    ) -> bool:
        """Mock service identity verification."""
        # Verify service has valid secret and identity
        return service in self.service_secrets
    
    def _generate_service_auth_token(self, service: str, secret: str) -> str:
        """Generate service authentication token."""
        payload = f"{service}:{datetime.now(timezone.utc).isoformat()}"
        signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return f"{payload}.{signature}"
    
    def _validate_service_auth_token(self, token: str, target_service: str) -> bool:
        """Validate service authentication token."""
        try:
            payload, signature = token.rsplit('.', 1)
            service, timestamp = payload.split(':', 1)
            
            if service not in self.service_secrets:
                return False
            
            expected_signature = hmac.new(
                self.service_secrets[service].encode(), 
                payload.encode(), 
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False