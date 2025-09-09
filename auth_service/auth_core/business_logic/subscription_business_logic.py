"""
Subscription Business Logic Validator - SSOT for subscription-related business rules

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Correct subscription tier access control and usage limits
- Value Impact: Ensures proper resource allocation and feature access per tier
- Strategic Impact: Protects platform revenue through proper tier enforcement

This module provides centralized business logic validation for:
1. Subscription tier access control
2. Usage limit enforcement
3. Feature access validation
4. Upgrade recommendations
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from netra_backend.app.schemas.tenant import SubscriptionTier
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


@dataclass
class TierLimits:
    """Data class for subscription tier limits"""
    api_calls_per_month: Optional[int]
    agents: Optional[int]
    storage_gb: Optional[int] = None
    concurrent_sessions: int = 3


@dataclass
class FeatureAccessResult:
    """Result object for feature access validation"""
    has_access: bool
    upgrade_message: str = ""
    required_tier: Optional[SubscriptionTier] = None


@dataclass
class UsageComplianceResult:
    """Result object for usage compliance validation"""
    within_limits: bool
    usage_percentage: float = 0.0
    requires_upgrade: bool = False
    overage_amount: int = 0


class SubscriptionBusinessLogic:
    """SSOT validator for subscription-related business logic"""
    
    # Tier limits mapping
    TIER_LIMITS = {
        SubscriptionTier.FREE: TierLimits(
            api_calls_per_month=1000,
            agents=1,
            storage_gb=1,
            concurrent_sessions=3
        ),
        SubscriptionTier.EARLY: TierLimits(
            api_calls_per_month=10000,
            agents=3,
            storage_gb=10,
            concurrent_sessions=5
        ),
        SubscriptionTier.MID: TierLimits(
            api_calls_per_month=50000,
            agents=5,
            storage_gb=100,
            concurrent_sessions=10
        ),
        SubscriptionTier.ENTERPRISE: TierLimits(
            api_calls_per_month=None,  # Unlimited
            agents=None,  # Unlimited
            storage_gb=None,  # Unlimited
            concurrent_sessions=25
        )
    }
    
    # Features that require specific tiers
    FEATURE_REQUIREMENTS = {
        "advanced_analytics": [SubscriptionTier.MID, SubscriptionTier.ENTERPRISE],
        "custom_integrations": [SubscriptionTier.ENTERPRISE],
        "sso": [SubscriptionTier.ENTERPRISE],
        "priority_support": [SubscriptionTier.MID, SubscriptionTier.ENTERPRISE],
        "api_access": [SubscriptionTier.EARLY, SubscriptionTier.MID, SubscriptionTier.ENTERPRISE],
        "basic_chat": [SubscriptionTier.FREE, SubscriptionTier.EARLY, SubscriptionTier.MID, SubscriptionTier.ENTERPRISE]
    }
    
    def get_tier_limits(self, tier: SubscriptionTier) -> Dict[str, Any]:
        """
        Get the limits for a specific subscription tier
        
        Args:
            tier: SubscriptionTier enum
            
        Returns:
            Dict containing tier limits
        """
        try:
            tier_limits = self.TIER_LIMITS.get(tier, self.TIER_LIMITS[SubscriptionTier.FREE])
            
            return {
                "api_calls_per_month": tier_limits.api_calls_per_month,
                "agents": tier_limits.agents,
                "storage_gb": tier_limits.storage_gb,
                "concurrent_sessions": tier_limits.concurrent_sessions
            }
            
        except Exception as e:
            logger.error(f"Error getting tier limits for {tier}: {e}")
            # Return FREE tier limits as fallback
            return self.get_tier_limits(SubscriptionTier.FREE)
    
    def validate_feature_access(self, tier: SubscriptionTier, feature: str) -> FeatureAccessResult:
        """
        Validate if a subscription tier has access to a specific feature
        
        Args:
            tier: User's current subscription tier
            feature: Feature name to check access for
            
        Returns:
            FeatureAccessResult with access status and upgrade information
        """
        try:
            required_tiers = self.FEATURE_REQUIREMENTS.get(feature, [])
            
            if not required_tiers:
                # Feature not found - default to no access
                return FeatureAccessResult(
                    has_access=False,
                    upgrade_message=f"Feature '{feature}' is not available",
                    required_tier=SubscriptionTier.ENTERPRISE
                )
            
            if tier in required_tiers:
                return FeatureAccessResult(
                    has_access=True,
                    upgrade_message="",
                    required_tier=None
                )
            
            # Find the minimum required tier
            tier_order = [SubscriptionTier.FREE, SubscriptionTier.EARLY, SubscriptionTier.MID, SubscriptionTier.ENTERPRISE]
            min_required_tier = min(required_tiers, key=lambda t: tier_order.index(t))
            
            return FeatureAccessResult(
                has_access=False,
                upgrade_message=f"Please upgrade to {min_required_tier.value.title()} tier or higher to access {feature}",
                required_tier=min_required_tier
            )
            
        except Exception as e:
            logger.error(f"Error validating feature access for {feature}: {e}")
            return FeatureAccessResult(
                has_access=False,
                upgrade_message="Feature access validation failed",
                required_tier=SubscriptionTier.ENTERPRISE
            )
    
    def validate_usage_compliance(self, usage_data: Dict[str, Any]) -> UsageComplianceResult:
        """
        Validate if current usage is within subscription tier limits
        
        Args:
            usage_data: Dict containing current usage information
                - subscription_tier: SubscriptionTier
                - current_month_api_calls: int
                - current_agents: int
                - storage_used_gb: float (optional)
                
        Returns:
            UsageComplianceResult with compliance status
        """
        try:
            tier = usage_data.get("subscription_tier", SubscriptionTier.FREE)
            current_api_calls = usage_data.get("current_month_api_calls", 0)
            current_agents = usage_data.get("current_agents", 0)
            storage_used = usage_data.get("storage_used_gb", 0)
            
            tier_limits = self.TIER_LIMITS.get(tier, self.TIER_LIMITS[SubscriptionTier.FREE])
            
            # Check API calls limit
            api_within_limits = True
            api_overage = 0
            api_usage_pct = 0.0
            
            if tier_limits.api_calls_per_month is not None:
                api_within_limits = current_api_calls <= tier_limits.api_calls_per_month
                if not api_within_limits:
                    api_overage = current_api_calls - tier_limits.api_calls_per_month
                api_usage_pct = (current_api_calls / tier_limits.api_calls_per_month) * 100
            
            # Check agents limit  
            agents_within_limits = True
            agents_overage = 0
            
            if tier_limits.agents is not None:
                agents_within_limits = current_agents <= tier_limits.agents
                if not agents_within_limits:
                    agents_overage = current_agents - tier_limits.agents
            
            # Check storage limit
            storage_within_limits = True
            storage_overage = 0
            
            if tier_limits.storage_gb is not None:
                storage_within_limits = storage_used <= tier_limits.storage_gb
                if not storage_within_limits:
                    storage_overage = storage_used - tier_limits.storage_gb
            
            # Overall compliance
            within_limits = api_within_limits and agents_within_limits and storage_within_limits
            requires_upgrade = not within_limits
            total_overage = api_overage + agents_overage + int(storage_overage)
            
            return UsageComplianceResult(
                within_limits=within_limits,
                usage_percentage=api_usage_pct,
                requires_upgrade=requires_upgrade,
                overage_amount=total_overage
            )
            
        except Exception as e:
            logger.error(f"Error validating usage compliance: {e}")
            # Fail secure - assume over limits
            return UsageComplianceResult(
                within_limits=False,
                usage_percentage=100.0,
                requires_upgrade=True,
                overage_amount=1
            )


# Create default instance for module-level access
subscription_validator = SubscriptionBusinessLogic()