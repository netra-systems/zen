"""OAuth Handler - Compatibility Layer for Test Migration
Provides backward compatibility for OAuth integration tests while using SSOT classes.

Business Value Justification (BVJ):
- Segment: Enterprise ($15K+ MRR per customer)
- Business Goal: Maintain OAuth validation test coverage during architecture evolution
- Value Impact: Ensures Enterprise OAuth authentication validation remains comprehensive
- Strategic Impact: Protects $500K+ ARR by preventing OAuth regression during SSOT migration

CRITICAL: This is a compatibility wrapper around SSOT OAuth classes.
Direct usage of SSOT classes (OAuthManager, GoogleOAuthProvider, OAuthBusinessLogic) is preferred.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import warnings

from auth_service.auth_core.oauth_manager import OAuthManager
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from auth_service.auth_core.oauth.oauth_business_logic import OAuthBusinessLogic
from auth_service.auth_core.auth_environment import get_auth_env

logger = logging.getLogger(__name__)


class OAuthHandler:
    """OAuth Handler - Compatibility layer wrapping SSOT OAuth classes.
    
    DEPRECATION WARNING: This class exists for test migration compatibility.
    New code should use OAuthManager, GoogleOAuthProvider, and OAuthBusinessLogic directly.
    """
    
    def __init__(self):
        """Initialize OAuth handler with SSOT OAuth components."""
        warnings.warn(
            "OAuthHandler is deprecated. Use OAuthManager, GoogleOAuthProvider, "
            "and OAuthBusinessLogic directly.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.oauth_manager = OAuthManager()
        self.auth_env = get_auth_env()
        self.oauth_business_logic = OAuthBusinessLogic(self.auth_env)
        self._oauth_client = None  # Mock compatibility
        self._jwt_handler = None   # Mock compatibility
    
    def generate_authorization_url(self, provider: str, email_hint: Optional[str] = None, 
                                 conversion_priority: str = "medium") -> Dict[str, Any]:
        """Generate OAuth authorization URL using SSOT GoogleOAuthProvider.
        
        Maps to: GoogleOAuthProvider.get_authorization_url()
        """
        try:
            google_provider = self.oauth_manager.get_provider("google")
            if not google_provider:
                return {
                    "error": "Provider not available",
                    "auth_url": None,
                    "state_token": None
                }
            
            # Generate secure unique state token using UnifiedIdGenerator
            state_token = UnifiedIdGenerator.generate_session_id("oauth", "web")
            
            # Get authorization URL from SSOT provider
            auth_url = google_provider.get_authorization_url(
                state=state_token,
                scopes=["openid", "email", "profile"]
            )
            
            return {
                "auth_url": auth_url,
                "state_token": state_token,
                "conversion_tracking": {
                    "provider": provider,
                    "conversion_priority": conversion_priority,
                    "email_hint": email_hint
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate authorization URL: {e}")
            return {
                "error": str(e),
                "auth_url": None,
                "state_token": None
            }
    
    def process_oauth_callback(self, authorization_code: str, state_token: str, 
                             user_business_logic) -> Dict[str, Any]:
        """Process OAuth callback using SSOT OAuth components.
        
        Maps to: GoogleOAuthProvider.exchange_code_for_user_info() + OAuthBusinessLogic.process_oauth_user()
        """
        try:
            google_provider = self.oauth_manager.get_provider("google")
            if not google_provider:
                return {"success": False, "error": "Provider not available"}
            
            # Exchange code for user info using SSOT provider
            user_info = google_provider.exchange_code_for_user_info(authorization_code)
            
            # Process user through SSOT business logic
            oauth_data = {
                "provider": "google",
                "provider_user_id": user_info.get("id", user_info.get("sub")),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "verified_email": user_info.get("email_verified", True),
                "picture": user_info.get("picture")
            }
            
            result = self.oauth_business_logic.process_oauth_user(oauth_data)
            
            return {
                "success": True,
                "user": {
                    "user_id": result.user_id,
                    "email": oauth_data["email"],
                    "subscription_tier": result.assigned_tier.value,
                    "is_new_user": result.is_new_user
                },
                "oauth_result": result
            }
            
        except Exception as e:
            logger.error(f"Failed to process OAuth callback: {e}")
            return {"success": False, "error": str(e)}
    
    def create_oauth_session(self, user_email: str, subscription_tier: str, 
                           user_type: str) -> Dict[str, Any]:
        """Create OAuth session with retention optimization.
        
        Enterprise feature for session management based on subscription tier.
        """
        try:
            # Session duration based on subscription tier (Enterprise optimization)
            session_durations = {
                "enterprise_admin": timedelta(hours=8),  # Work day
                "premium_user": timedelta(hours=4),      # Half day  
                "free_user": timedelta(hours=1)          # Short session
            }
            
            duration = session_durations.get(user_type, timedelta(hours=2))
            expires_at = datetime.now(timezone.utc) + duration
            
            # Auto-extend for paid tiers (retention optimization)
            auto_extend = user_type in ["enterprise_admin", "premium_user"]
            
            # Security level based on tier
            security_levels = {
                "enterprise_admin": "high",
                "premium_user": "medium",
                "free_user": "basic"
            }
            security_level = security_levels.get(user_type, "basic")
            
            # Generate secure unique IDs using UnifiedIdGenerator
            session_id = UnifiedIdGenerator.generate_session_id("oauth", "web")
            user_id = UnifiedIdGenerator.generate_base_id("user")  # Would be real user ID in production
            
            return {
                "session_id": session_id,
                "user_id": user_id,
                "expires_at": expires_at,
                "auto_extend_enabled": auto_extend,
                "security_level": security_level
            }
            
        except Exception as e:
            logger.error(f"Failed to create OAuth session: {e}")
            return {"error": str(e)}
    
    def handle_oauth_error(self, error_type: str, error_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle OAuth errors with conversion optimization.
        
        Provides user-friendly error messages and recovery strategies to minimize conversion loss.
        """
        try:
            # Error recovery strategies (conversion optimization)
            recovery_strategies = {
                "access_denied": "retry_with_incentive",
                "invalid_grant": "automatic_retry", 
                "server_error": "fallback_email_signup",
                "invalid_client": "immediate_alert_and_fallback"
            }
            
            recovery_strategy = recovery_strategies.get(error_type, "contact_support")
            
            # User-friendly error messages (no technical jargon)
            user_messages = {
                "access_denied": "Authentication was cancelled. Would you like to try again?",
                "invalid_grant": "Session expired. Please try signing in again.",
                "server_error": "Authentication service temporarily unavailable. Try email signup or retry later.",
                "invalid_client": "Authentication temporarily unavailable. Please try email signup."
            }
            
            user_message = user_messages.get(error_type, "Authentication failed. Please try again or contact support.")
            
            return {
                "error_handled": True,
                "recovery_strategy": recovery_strategy,
                "user_message": user_message,
                "error_type": error_type,
                "context": error_context
            }
            
        except Exception as e:
            logger.error(f"Failed to handle OAuth error: {e}")
            return {
                "error_handled": False,
                "error": str(e),
                "user_message": "Authentication failed. Please contact support."
            }
    
    def track_oauth_business_event(self, event_type: str, user_segment: str, 
                                 conversion_value: float, funnel_step: str) -> None:
        """Track OAuth business metrics for conversion optimization.
        
        Enterprise analytics for OAuth conversion funnel tracking.
        """
        try:
            # Log business event for analytics (would integrate with analytics service)
            logger.info(f"OAuth Business Event: {event_type} | {user_segment} | ${conversion_value} | {funnel_step}")
            
            # Mock analytics tracker for test compatibility
            if hasattr(self, '_analytics_tracker') and self._analytics_tracker:
                if hasattr(self._analytics_tracker, 'track'):
                    self._analytics_tracker.track(
                        event=event_type,
                        properties={
                            "user_segment": user_segment,
                            "conversion_value": conversion_value,
                            "funnel_step": funnel_step,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
            
        except Exception as e:
            logger.error(f"Failed to track OAuth business event: {e}")