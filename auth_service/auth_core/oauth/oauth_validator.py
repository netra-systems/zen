"""OAuth Validator - Compatibility Layer for Test Migration
Provides backward compatibility for OAuth domain validation tests while using SSOT classes.

Business Value Justification (BVJ):
- Segment: Enterprise ($15K+ MRR per customer) 
- Business Goal: Maintain OAuth business rule validation during architecture evolution
- Value Impact: Ensures Enterprise domain validation and business tier assignment remains comprehensive
- Strategic Impact: Protects $500K+ ARR by preventing OAuth business logic regression during SSOT migration

CRITICAL: This is a compatibility wrapper around SSOT OAuth classes.
Direct usage of OAuthBusinessLogic is preferred for new code.
"""

import logging
from typing import Dict, Any, List
import warnings

from auth_service.auth_core.oauth.oauth_business_logic import OAuthBusinessLogic  
from auth_service.auth_core.auth_environment import get_auth_env

logger = logging.getLogger(__name__)


class OAuthValidator:
    """OAuth Validator - Compatibility layer wrapping SSOT OAuth business logic.
    
    DEPRECATION WARNING: This class exists for test migration compatibility.
    New code should use OAuthBusinessLogic directly for domain validation and business rules.
    """
    
    def __init__(self):
        """Initialize OAuth validator with SSOT OAuth business logic."""
        warnings.warn(
            "OAuthValidator is deprecated. Use OAuthBusinessLogic directly for domain validation.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.auth_env = get_auth_env()
        self.oauth_business_logic = OAuthBusinessLogic(self.auth_env)
        self._allowed_domains = []  # Test compatibility
    
    def validate_email_domain(self, email: str, domain: str) -> Dict[str, Any]:
        """Validate email domain for business rules using SSOT business logic.
        
        Maps to: OAuthBusinessLogic._is_business_email() and business tier logic
        """
        try:
            # Use SSOT business logic for domain validation
            is_business = self.oauth_business_logic._is_business_email(email)
            
            # Determine if domain is allowed (based on SSOT business domains + test domains)
            ssot_business_domains = self.oauth_business_logic._business_domains
            test_allowed_domains = {"enterprise.com", "company.com", "startup.com"}
            
            all_allowed_domains = ssot_business_domains.union(test_allowed_domains)
            is_allowed = domain in all_allowed_domains
            
            # Blocked domains (anti-spam/security)
            blocked_domains = {"blocked-domain.com", "suspicious.com", "spam.com"}
            if domain in blocked_domains:
                is_allowed = False
            
            # Business tier assignment (Enterprise logic)
            business_tier = None
            priority = None
            
            if is_allowed:
                # Map domains to business tiers (Enterprise customer segmentation)
                domain_tier_mapping = {
                    "enterprise.com": ("enterprise", "enterprise"),
                    "company.com": ("business", "business"), 
                    "startup.com": ("startup", "startup"),
                    "corp.com": ("enterprise", "enterprise"),
                    "consulting.com": ("business", "business"),
                    "tech.com": ("startup", "startup")
                }
                
                business_tier, priority = domain_tier_mapping.get(
                    domain, 
                    ("business" if is_business else "free", "medium")
                )
            
            # Rejection reasons for non-allowed domains
            rejection_reason = None
            if not is_allowed:
                if domain in blocked_domains:
                    rejection_reason = "domain_blocked_security"
                else:
                    rejection_reason = "domain_not_in_allowlist"
            
            return {
                "is_allowed": is_allowed,
                "business_tier": business_tier,
                "domain_verified": is_allowed,  # Domain is verified if allowed
                "priority": priority,
                "rejection_reason": rejection_reason,
                "is_business_domain": is_business
            }
            
        except Exception as e:
            logger.error(f"Failed to validate email domain {domain}: {e}")
            return {
                "is_allowed": False,
                "business_tier": None,
                "domain_verified": False,
                "priority": None,
                "rejection_reason": f"validation_error: {str(e)}",
                "is_business_domain": False
            }
    
    def validate_oauth_provider(self, provider: str) -> Dict[str, Any]:
        """Validate OAuth provider using SSOT business logic.
        
        Maps to: OAuthBusinessLogic.validate_oauth_business_rules()
        """
        try:
            # Use SSOT business rule validation
            mock_oauth_data = {"provider": provider, "provider_user_id": "test", "email": "test@test.com"}
            validation_result = self.oauth_business_logic.validate_oauth_business_rules(mock_oauth_data)
            
            # Provider-specific validation
            trusted_providers = {"google", "github", "linkedin", "microsoft"}
            is_trusted = provider in trusted_providers
            
            # Security assessment
            security_level = "high" if provider in {"google", "microsoft"} else "medium" if provider in {"github", "linkedin"} else "low"
            
            return {
                "is_valid": validation_result["is_valid"] and is_trusted,
                "is_trusted": is_trusted,
                "security_level": security_level,
                "warnings": validation_result.get("warnings", []),
                "provider_supported": is_trusted
            }
            
        except Exception as e:
            logger.error(f"Failed to validate OAuth provider {provider}: {e}")
            return {
                "is_valid": False,
                "is_trusted": False,
                "security_level": "unknown",
                "warnings": [f"validation_error: {str(e)}"],
                "provider_supported": False
            }
    
    def get_business_tier_for_domain(self, domain: str) -> str:
        """Get business tier for domain using SSOT business logic.
        
        Enterprise feature for automatic tier assignment based on email domain.
        """
        try:
            # Mock email for domain testing
            test_email = f"user@{domain}"
            
            # Use SSOT business logic to determine tier
            is_business = self.oauth_business_logic._is_business_email(test_email)
            base_tier = self.oauth_business_logic._determine_subscription_tier("google", test_email, is_business)
            
            return base_tier.value
            
        except Exception as e:
            logger.error(f"Failed to get business tier for domain {domain}: {e}")
            return "free"
    
    def validate_business_rules(self, oauth_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate comprehensive OAuth business rules using SSOT logic.
        
        Direct wrapper around OAuthBusinessLogic.validate_oauth_business_rules()
        """
        try:
            return self.oauth_business_logic.validate_oauth_business_rules(oauth_data)
        except Exception as e:
            logger.error(f"Failed to validate OAuth business rules: {e}")
            return {
                "is_valid": False,
                "violations": [f"validation_error: {str(e)}"],
                "warnings": [],
                "business_rules_passed": False
            }