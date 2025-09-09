"""
Session Policy Validator - Auth Service

Validates session security policies including concurrent session limits,
device restrictions, and subscription tier-based session management.

Following SSOT principles - single source of truth for session policy validation.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from auth_service.auth_core.auth_environment import AuthEnvironment
from netra_backend.app.schemas.tenant import SubscriptionTier


@dataclass
class SessionPolicyResult:
    """Result of session policy validation."""
    max_concurrent_sessions: int
    can_create_new_session: bool
    requires_device_verification: bool = False
    policy_violations: list = None
    denial_reason: Optional[str] = None
    
    def __post_init__(self):
        if self.policy_violations is None:
            self.policy_violations = []


class SessionPolicyValidator:
    """Validates session policies based on business rules and subscription tiers."""
    
    def __init__(self, auth_env: AuthEnvironment):
        """Initialize session policy validator with auth environment."""
        self.auth_env = auth_env
        
        # Session limits by subscription tier
        self._tier_session_limits = {
            SubscriptionTier.FREE: 3,
            SubscriptionTier.EARLY: 5,
            SubscriptionTier.MID: 10,
            SubscriptionTier.ENTERPRISE: 25
        }
    
    def validate_session_policy(self, session_request: Dict[str, Any]) -> SessionPolicyResult:
        """
        Validate session policy for a user session request.
        
        Args:
            session_request: Dict containing user_id, current_sessions, 
                           subscription_tier, device_info
        
        Returns:
            SessionPolicyResult with validation outcome
        """
        user_id = session_request.get("user_id")
        current_sessions = session_request.get("current_sessions", 0)
        subscription_tier = session_request.get("subscription_tier", SubscriptionTier.FREE)
        device_info = session_request.get("device_info", {})
        
        # Get session limit for subscription tier
        max_sessions = self._tier_session_limits.get(subscription_tier, 3)
        
        # Check if user can create new session
        can_create_new = current_sessions < max_sessions
        
        # Validate device requirements for enterprise
        requires_device_verification = (
            subscription_tier == SubscriptionTier.ENTERPRISE and
            device_info.get("type") == "unknown"
        )
        
        policy_violations = []
        denial_reason = None
        
        if not can_create_new:
            policy_violations.append("concurrent_session_limit_exceeded")
            denial_reason = f"Maximum concurrent sessions ({max_sessions}) exceeded"
        
        if requires_device_verification:
            policy_violations.append("device_verification_required")
            if not denial_reason:
                denial_reason = "Device verification required for enterprise accounts"
        
        return SessionPolicyResult(
            max_concurrent_sessions=max_sessions,
            can_create_new_session=can_create_new and not requires_device_verification,
            requires_device_verification=requires_device_verification,
            policy_violations=policy_violations,
            denial_reason=denial_reason
        )
    
    def validate_session_timeout(self, session_data: Dict[str, Any]) -> bool:
        """
        Validate if session should timeout based on policy.
        
        Args:
            session_data: Dict containing session info and last_activity
            
        Returns:
            bool: True if session should timeout
        """
        last_activity = session_data.get("last_activity")
        subscription_tier = session_data.get("subscription_tier", SubscriptionTier.FREE)
        
        if not last_activity:
            return True
        
        # Timeout limits by tier (in hours)
        timeout_limits = {
            SubscriptionTier.FREE: 2,
            SubscriptionTier.EARLY: 8,
            SubscriptionTier.MID: 24,
            SubscriptionTier.ENTERPRISE: 72
        }
        
        timeout_hours = timeout_limits.get(subscription_tier, 2)
        
        if isinstance(last_activity, str):
            last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
        
        time_since_activity = datetime.now(timezone.utc) - last_activity
        timeout_threshold_seconds = timeout_hours * 3600
        
        return time_since_activity.total_seconds() > timeout_threshold_seconds
    
    def get_session_limits(self, subscription_tier: SubscriptionTier) -> Dict[str, Any]:
        """Get session limits for a subscription tier."""
        return {
            "max_concurrent_sessions": self._tier_session_limits.get(subscription_tier, 3),
            "session_timeout_hours": {
                SubscriptionTier.FREE: 2,
                SubscriptionTier.EARLY: 8,
                SubscriptionTier.MID: 24,
                SubscriptionTier.ENTERPRISE: 72
            }.get(subscription_tier, 2),
            "requires_device_verification": subscription_tier == SubscriptionTier.ENTERPRISE
        }