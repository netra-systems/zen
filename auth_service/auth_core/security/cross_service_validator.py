"""
Cross-Service Validation Module - SSOT for inter-service authentication

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - affects all cross-service operations
- Business Goal: Secure inter-service communication and proper authorization
- Value Impact: Ensures users can only access resources they're authorized for across services
- Strategic Impact: Protects platform data integrity and maintains security compliance

This module provides centralized cross-service validation for:
1. Cross-service token validation and authentication
2. Service-to-service authorization rules
3. User context validation across service boundaries
4. Resource access control based on user tier and permissions
5. Operation-level authorization (read/write/delete permissions)
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CrossServiceValidationResult:
    """Result object for cross-service request validation"""
    is_authorized: bool
    allowed_operations: List[str]
    denial_reason: str = ""
    user_context: Optional[Dict[str, Any]] = None
    service_permissions: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.allowed_operations is None:
            self.allowed_operations = []


class CrossServiceValidator:
    """
    Cross-service request validator following SSOT principles.
    
    Validates requests between services ensuring proper authentication,
    authorization, and business rule compliance.
    """
    
    def __init__(self, auth_env):
        """
        Initialize cross-service validator.
        
        Args:
            auth_env: AuthEnvironment instance for configuration access
        """
        self.auth_env = auth_env
        self.logger = logging.getLogger(__name__)
        
        # Define service-to-service permissions matrix
        self._service_permissions = {
            "backend": {
                "allowed_targets": ["user_data", "agent_data", "session_data"],
                "default_operations": ["read", "write"],
                "restricted_operations": ["delete", "admin"]
            },
            "frontend": {
                "allowed_targets": ["user_profile", "session_data"],
                "default_operations": ["read"],
                "restricted_operations": ["write", "delete", "admin"]
            },
            "auth": {
                "allowed_targets": ["user_data", "session_data", "auth_data"],
                "default_operations": ["read", "write", "delete"],
                "restricted_operations": ["admin"]
            }
        }
        
        # Define tier-based operation permissions
        self._tier_permissions = {
            "free": {
                "allowed_operations": ["read"],
                "resource_limits": ["user_profile", "basic_data"]
            },
            "early": {
                "allowed_operations": ["read", "write"],
                "resource_limits": ["user_data", "agent_data"]
            },
            "mid": {
                "allowed_operations": ["read", "write"],
                "resource_limits": ["user_data", "agent_data", "session_data"]
            },
            "enterprise": {
                "allowed_operations": ["read", "write", "delete"],
                "resource_limits": []  # No limits for enterprise
            }
        }
    
    def validate_cross_service_request(self, service_request: Dict[str, Any]) -> CrossServiceValidationResult:
        """
        Validate a cross-service request for authorization.
        
        Args:
            service_request: Dictionary containing:
                - requesting_service: Service making the request
                - target_resource: Resource being accessed
                - user_context: User information (user_id, tier, etc.)
                - operation: Requested operation (read/write/delete)
                
        Returns:
            CrossServiceValidationResult with authorization decision
        """
        try:
            # Extract request components
            requesting_service = service_request.get("requesting_service", "")
            target_resource = service_request.get("target_resource", "")
            user_context = service_request.get("user_context", {})
            requested_operation = service_request.get("operation", "")
            
            # Validate required fields
            if not all([requesting_service, target_resource, user_context, requested_operation]):
                return CrossServiceValidationResult(
                    is_authorized=False,
                    allowed_operations=[],
                    denial_reason="Missing required fields in cross-service request"
                )
            
            # Get user tier
            user_tier = user_context.get("tier", "free").lower()
            user_id = user_context.get("user_id", "")
            
            # Log the validation attempt
            self.logger.info(
                f"Cross-service validation: {requesting_service} -> {target_resource} "
                f"for user {user_id} (tier: {user_tier}) operation: {requested_operation}"
            )
            
            # Validate user tier permissions first (more specific business logic)
            tier_validation = self._validate_tier_permissions(
                user_tier, target_resource, requested_operation
            )
            
            if not tier_validation["allowed"]:
                return CrossServiceValidationResult(
                    is_authorized=False,
                    allowed_operations=tier_validation.get("allowed_operations", []),
                    denial_reason=tier_validation["reason"]
                )
            
            # Validate service permissions (infrastructure-level validation)
            service_validation = self._validate_service_permissions(
                requesting_service, target_resource, requested_operation
            )
            
            if not service_validation["allowed"]:
                return CrossServiceValidationResult(
                    is_authorized=False,
                    allowed_operations=service_validation.get("allowed_operations", []),
                    denial_reason=service_validation["reason"]
                )
            
            # If we reach here, the request is authorized
            # For a valid request, return only the requested operation
            allowed_operations = [requested_operation]
            
            return CrossServiceValidationResult(
                is_authorized=True,
                allowed_operations=allowed_operations,
                user_context=user_context,
                service_permissions=service_validation.get("permissions")
            )
            
        except Exception as e:
            self.logger.error(f"Error validating cross-service request: {e}")
            return CrossServiceValidationResult(
                is_authorized=False,
                allowed_operations=[],
                denial_reason=f"Validation error: {str(e)}"
            )
    
    def _validate_service_permissions(self, requesting_service: str, target_resource: str, operation: str) -> Dict[str, Any]:
        """Validate if the requesting service can perform the operation on the target resource."""
        service_config = self._service_permissions.get(requesting_service.lower())
        
        if not service_config:
            return {
                "allowed": False,
                "reason": f"Unknown requesting service: {requesting_service}",
                "allowed_operations": []
            }
        
        # Check if service can access the target resource
        if target_resource not in service_config["allowed_targets"]:
            return {
                "allowed": False,
                "reason": f"Service {requesting_service} cannot access resource {target_resource}",
                "allowed_operations": service_config["default_operations"]
            }
        
        # Check if operation is restricted for this service
        if operation in service_config["restricted_operations"]:
            return {
                "allowed": False,
                "reason": f"Operation {operation} is restricted for service {requesting_service}",
                "allowed_operations": service_config["default_operations"]
            }
        
        return {
            "allowed": True,
            "reason": "Service permissions validated successfully",
            "permissions": service_config,
            "allowed_operations": service_config["default_operations"]
        }
    
    def _validate_tier_permissions(self, user_tier: str, target_resource: str, operation: str) -> Dict[str, Any]:
        """Validate if the user's tier allows the requested operation on the resource."""
        tier_config = self._tier_permissions.get(user_tier.lower())
        
        if not tier_config:
            return {
                "allowed": False,
                "reason": f"Unknown user tier: {user_tier}",
                "allowed_operations": ["read"]  # Default to minimal permissions
            }
        
        # Check if operation is allowed for this tier
        if operation not in tier_config["allowed_operations"]:
            return {
                "allowed": False,
                "reason": f"Insufficient privileges: {user_tier} tier cannot perform {operation}",
                "allowed_operations": tier_config["allowed_operations"]
            }
        
        # Check resource limits for the tier (except enterprise which has no limits)
        if tier_config["resource_limits"] and target_resource not in tier_config["resource_limits"]:
            return {
                "allowed": False,
                "reason": f"Resource {target_resource} not available for {user_tier} tier",
                "allowed_operations": tier_config["allowed_operations"]
            }
        
        return {
            "allowed": True,
            "reason": "Tier permissions validated successfully",
            "allowed_operations": tier_config["allowed_operations"]
        }
    
    def _get_allowed_operations_for_context(self, requesting_service: str, user_tier: str, target_resource: str) -> List[str]:
        """Get the intersection of allowed operations based on service and tier permissions."""
        service_config = self._service_permissions.get(requesting_service.lower(), {})
        tier_config = self._tier_permissions.get(user_tier.lower(), {})
        
        service_operations = set(service_config.get("default_operations", []))
        tier_operations = set(tier_config.get("allowed_operations", []))
        
        # Return intersection of allowed operations
        allowed_operations = list(service_operations.intersection(tier_operations))
        
        # Ensure read is always available if both configs support it
        if "read" in service_operations and "read" in tier_operations and "read" not in allowed_operations:
            allowed_operations.append("read")
        
        return sorted(allowed_operations)