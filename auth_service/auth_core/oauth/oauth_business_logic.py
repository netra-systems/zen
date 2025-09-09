"""
OAuth Business Logic - Auth Service

Business logic for OAuth user processing, including registration,
account linking, and subscription tier assignment based on OAuth data.

Following SSOT principles for OAuth business rule processing.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from auth_service.auth_core.auth_environment import AuthEnvironment
from netra_backend.app.schemas.tenant import SubscriptionTier


@dataclass
class OAuthUserResult:
    """Result of OAuth user processing."""
    user_id: Optional[str]
    is_new_user: bool
    assigned_tier: SubscriptionTier
    email_verified: bool
    profile_complete: bool
    requires_additional_info: bool = False
    business_email_detected: bool = False
    suggested_tier: Optional[SubscriptionTier] = None
    provider_data: Dict[str, Any] = None
    should_create_account: bool = True
    should_link_accounts: bool = False
    email_verification_required: bool = False
    
    def __post_init__(self):
        if self.provider_data is None:
            self.provider_data = {}


class OAuthBusinessLogic:
    """Handles business logic for OAuth user processing and account management."""
    
    def __init__(self, auth_env: AuthEnvironment):
        """Initialize OAuth business logic with auth environment."""
        self.auth_env = auth_env
        
        # Business email domains that suggest higher tier
        self._business_domains = {
            "enterprise.com", "corp.com", "company.com", "business.com",
            "consulting.com", "finance.com", "tech.com", "software.com"
        }
        
        # Provider-specific tier mapping
        self._provider_tier_mapping = {
            "google": SubscriptionTier.FREE,  # Default for Google OAuth
            "github": SubscriptionTier.EARLY,  # Developers often on Early tier
            "linkedin": SubscriptionTier.MID,  # Business professionals
        }
    
    def process_oauth_user(self, oauth_user_data: Dict[str, Any]) -> OAuthUserResult:
        """
        Process OAuth user data and determine account creation/linking.
        
        Args:
            oauth_user_data: Dict containing provider, provider_user_id, email, etc.
        
        Returns:
            OAuthUserResult with processing outcome
        """
        provider = oauth_user_data.get("provider")
        email = oauth_user_data.get("email")
        verified_email = oauth_user_data.get("verified_email", False)
        name = oauth_user_data.get("name")
        
        # Determine if this is a business email
        business_email_detected = self._is_business_email(email)
        
        # Assign subscription tier based on provider and email
        assigned_tier = self._determine_subscription_tier(provider, email, business_email_detected)
        
        # Check if additional info is needed
        requires_additional_info = not name or not email
        
        # Check if this is account linking or new account creation
        existing_user_id = oauth_user_data.get("existing_user_id")
        is_new_user = not existing_user_id
        should_create_account = is_new_user
        should_link_accounts = not is_new_user
        
        user_id = existing_user_id if existing_user_id else f"oauth-{provider}-{oauth_user_data.get('provider_user_id')}"
        
        # Email verification required if OAuth provider didn't verify it
        email_verification_required = not verified_email
        
        # Suggest tier upgrade for business emails, otherwise use assigned tier
        suggested_tier = assigned_tier
        if business_email_detected and assigned_tier == SubscriptionTier.FREE:
            suggested_tier = SubscriptionTier.EARLY
        
        return OAuthUserResult(
            user_id=user_id,
            is_new_user=is_new_user,
            assigned_tier=assigned_tier,
            email_verified=verified_email,
            profile_complete=bool(name and email),
            requires_additional_info=requires_additional_info,
            business_email_detected=business_email_detected,
            suggested_tier=suggested_tier,
            provider_data=oauth_user_data,
            should_create_account=should_create_account,
            should_link_accounts=should_link_accounts,
            email_verification_required=email_verification_required
        )
    
    def validate_oauth_business_rules(self, oauth_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate OAuth data against business rules.
        
        Args:
            oauth_data: OAuth user data to validate
            
        Returns:
            Dict with validation results and any policy violations
        """
        violations = []
        warnings = []
        
        # Check required fields
        required_fields = ["provider", "provider_user_id", "email"]
        for field in required_fields:
            if not oauth_data.get(field):
                violations.append(f"missing_required_field_{field}")
        
        # Check email format and verification
        email = oauth_data.get("email")
        if email and "@" not in email:
            violations.append("invalid_email_format")
        
        if not oauth_data.get("verified_email", False):
            warnings.append("email_not_verified_by_provider")
        
        # Check for suspicious provider data
        provider = oauth_data.get("provider")
        if provider and provider not in ["google", "github", "linkedin", "microsoft"]:
            warnings.append("uncommon_oauth_provider")
        
        return {
            "is_valid": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
            "business_rules_passed": len(violations) == 0
        }
    
    def process_oauth_account_linking(self, existing_user_id: str, oauth_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process linking OAuth account to existing user.
        
        Args:
            existing_user_id: ID of existing user account
            oauth_data: OAuth data to link
            
        Returns:
            Dict with linking result
        """
        provider = oauth_data.get("provider")
        provider_user_id = oauth_data.get("provider_user_id")
        
        # Validate linking business rules
        linking_result = {
            "success": True,
            "linked_provider": provider,
            "existing_user_id": existing_user_id,
            "enhanced_verification": oauth_data.get("verified_email", False),
            "profile_enrichment": {}
        }
        
        # Add profile enrichment data
        if oauth_data.get("name"):
            linking_result["profile_enrichment"]["name"] = oauth_data["name"]
        
        if oauth_data.get("picture"):
            linking_result["profile_enrichment"]["profile_picture"] = oauth_data["picture"]
        
        return linking_result
    
    def _is_business_email(self, email: str) -> bool:
        """Check if email appears to be from a business domain."""
        if not email:
            return False
        
        domain = email.split("@")[-1].lower()
        
        # Check against known business domains
        if domain in self._business_domains:
            return True
        
        # Check for common consumer email providers (return False for these)
        consumer_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"}
        if domain in consumer_domains:
            return False
        
        # If it's not a known consumer domain and has corporate patterns, consider it business
        business_patterns = ["corp", "company", "inc", "llc", "ltd", "consulting"]
        return any(pattern in domain for pattern in business_patterns)
    
    def _determine_subscription_tier(self, provider: str, email: str, is_business: bool) -> SubscriptionTier:
        """Determine appropriate subscription tier based on OAuth data."""
        # Start with provider default
        base_tier = self._provider_tier_mapping.get(provider, SubscriptionTier.FREE)
        
        # Upgrade for business emails
        if is_business:
            if base_tier == SubscriptionTier.FREE:
                return SubscriptionTier.EARLY
            elif base_tier == SubscriptionTier.EARLY:
                return SubscriptionTier.MID
        
        return base_tier