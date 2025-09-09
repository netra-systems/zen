"""Agent Business Rule Validator - SSOT for business rule enforcement across agent execution.

This module provides business rule validation for agent access control, feature gating,
and tier-based restrictions. It enforces monetization boundaries and ensures proper
feature access control across all customer segments.

Business Value Justification:
- Segment: ALL (Free, Early, Mid, Enterprise)
- Business Goal: Revenue Protection and Feature Gating
- Value Impact: Enforces monetization boundaries and prevents feature abuse
- Strategic Impact: Ensures sustainable business model through proper tier enforcement

SSOT Principle: This is the canonical implementation for agent business rules.
All agent access decisions must go through this validator for consistency.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# =============================================================================
# Business Rule Types and Enums
# =============================================================================

class UserTier(Enum):
    """User tier enumeration for business rule enforcement."""
    FREE = "free"
    EARLY = "early" 
    MID = "mid"
    ENTERPRISE = "enterprise"


@dataclass
class AgentAccessResult:
    """Result of agent access validation."""
    allowed: bool
    reason: Optional[str] = None
    available_features: List[str] = None
    suggested_upgrade: Optional[str] = None
    
    def __post_init__(self):
        if self.available_features is None:
            self.available_features = []


@dataclass
class BusinessRuleConfig:
    """Configuration for business rules by tier."""
    tier: UserTier
    max_agents_per_day: int
    concurrent_executions: int
    allowed_agent_types: List[str]
    premium_features: List[str]
    data_retention_days: int
    support_level: str


# =============================================================================
# Business Rule Configuration - SSOT for tier capabilities
# =============================================================================

BUSINESS_RULE_CONFIGS = {
    UserTier.FREE: BusinessRuleConfig(
        tier=UserTier.FREE,
        max_agents_per_day=10,
        concurrent_executions=1,
        allowed_agent_types=["basic_analysis"],
        premium_features=["basic_optimization", "query_analysis"],
        data_retention_days=7,
        support_level="community"
    ),
    UserTier.EARLY: BusinessRuleConfig(
        tier=UserTier.EARLY,
        max_agents_per_day=100,
        concurrent_executions=3,
        allowed_agent_types=["basic_analysis", "advanced_analysis", "data_optimization"],
        premium_features=["advanced_optimization", "multi_table_analysis", "performance_insights"],
        data_retention_days=30,
        support_level="email"
    ),
    UserTier.MID: BusinessRuleConfig(
        tier=UserTier.MID,
        max_agents_per_day=500,
        concurrent_executions=5,
        allowed_agent_types=["basic_analysis", "advanced_analysis", "data_optimization", "custom_analysis"],
        premium_features=["advanced_optimization", "multi_table_analysis", "performance_insights", "custom_dashboards"],
        data_retention_days=90,
        support_level="priority_email"
    ),
    UserTier.ENTERPRISE: BusinessRuleConfig(
        tier=UserTier.ENTERPRISE,
        max_agents_per_day=1000,
        concurrent_executions=10,
        allowed_agent_types=["*"],  # All agent types
        premium_features=["ai_powered_optimization", "custom_agents", "priority_execution", "dedicated_support"],
        data_retention_days=365,
        support_level="phone_and_email"
    )
}


# =============================================================================
# Agent Business Rule Validator
# =============================================================================

class AgentBusinessRuleValidator:
    """Validates agent access and enforces business rules by user tier.
    
    This class implements tier-based business rule enforcement including:
    - Agent type access control
    - Feature availability validation  
    - Resource limit enforcement
    - Monetization boundary protection
    """
    
    def __init__(self):
        """Initialize business rule validator."""
        self.configs = BUSINESS_RULE_CONFIGS
        
    # =========================================================================
    # Core Business Rule Validation
    # =========================================================================
    
    def validate_agent_access(self, user_permissions: List[str], agent_type: str, user_tier: str) -> AgentAccessResult:
        """Validate if user has access to specific agent type based on tier and permissions.
        
        Args:
            user_permissions: List of user permissions
            agent_type: Type of agent being requested
            user_tier: User's subscription tier
            
        Returns:
            AgentAccessResult: Access validation result with details
        """
        try:
            # Normalize tier
            tier_enum = self._parse_user_tier(user_tier)
            if not tier_enum:
                return AgentAccessResult(
                    allowed=False,
                    reason=f"Invalid user tier: {user_tier}",
                    suggested_upgrade="contact_support"
                )
            
            # Get business rule config
            config = self.configs.get(tier_enum)
            if not config:
                logger.error(f"No business rule config found for tier: {tier_enum}")
                return AgentAccessResult(
                    allowed=False,
                    reason="Configuration error",
                    suggested_upgrade="contact_support"
                )
            
            # Check agent type access
            if not self._is_agent_type_allowed(agent_type, config):
                return AgentAccessResult(
                    allowed=False,
                    reason=f"Agent type '{agent_type}' not available for {user_tier} tier",
                    available_features=config.premium_features,
                    suggested_upgrade=self._get_upgrade_suggestion(tier_enum)
                )
            
            # Check permission requirements
            if not self._has_required_permissions(user_permissions, agent_type):
                return AgentAccessResult(
                    allowed=False,
                    reason="Insufficient permissions for agent execution",
                    available_features=config.premium_features
                )
            
            # Access granted
            return AgentAccessResult(
                allowed=True,
                available_features=config.premium_features
            )
            
        except Exception as e:
            logger.error(f"Agent access validation error: {e}")
            return AgentAccessResult(
                allowed=False,
                reason=f"Validation error: {str(e)}",
                suggested_upgrade="contact_support"
            )
    
    def validate_feature_access(self, user_tier: str, feature_name: str) -> bool:
        """Validate if user has access to specific premium feature.
        
        Args:
            user_tier: User's subscription tier
            feature_name: Name of feature to check
            
        Returns:
            bool: True if feature is available for this tier
        """
        try:
            tier_enum = self._parse_user_tier(user_tier)
            if not tier_enum:
                return False
            
            config = self.configs.get(tier_enum)
            if not config:
                return False
            
            return feature_name in config.premium_features
            
        except Exception as e:
            logger.error(f"Feature access validation error: {e}")
            return False
    
    def get_tier_limits(self, user_tier: str) -> Dict[str, Any]:
        """Get comprehensive limits and capabilities for user tier.
        
        Args:
            user_tier: User's subscription tier
            
        Returns:
            Dict: Tier limits and capabilities
        """
        try:
            tier_enum = self._parse_user_tier(user_tier)
            if not tier_enum:
                # Default to free tier limits for invalid tiers
                tier_enum = UserTier.FREE
            
            config = self.configs.get(tier_enum, self.configs[UserTier.FREE])
            
            return {
                "tier": config.tier.value,
                "max_agents_per_day": config.max_agents_per_day,
                "concurrent_executions": config.concurrent_executions,
                "allowed_agent_types": config.allowed_agent_types,
                "premium_features": config.premium_features,
                "data_retention_days": config.data_retention_days,
                "support_level": config.support_level
            }
            
        except Exception as e:
            logger.error(f"Tier limits retrieval error: {e}")
            return self.configs[UserTier.FREE].__dict__
    
    def suggest_tier_upgrade(self, current_tier: str, desired_feature: str) -> Optional[str]:
        """Suggest appropriate tier upgrade for desired feature access.
        
        Args:
            current_tier: User's current tier
            desired_feature: Feature or agent type user wants access to
            
        Returns:
            Optional[str]: Suggested tier upgrade, or None if already have access
        """
        try:
            current_tier_enum = self._parse_user_tier(current_tier)
            if not current_tier_enum:
                return "early"  # Default suggestion
            
            # Check each tier to find the lowest one that includes the feature
            tier_order = [UserTier.FREE, UserTier.EARLY, UserTier.MID, UserTier.ENTERPRISE]
            
            for tier in tier_order:
                if tier.value == current_tier:
                    continue  # Skip current tier
                    
                config = self.configs.get(tier)
                if not config:
                    continue
                
                # Check if this tier provides the desired feature
                if (desired_feature in config.premium_features or
                    desired_feature in config.allowed_agent_types or
                    "*" in config.allowed_agent_types):
                    return tier.value
            
            return None  # Feature not available in any tier
            
        except Exception as e:
            logger.error(f"Tier upgrade suggestion error: {e}")
            return "enterprise"  # Safe fallback
    
    # =========================================================================
    # Usage Validation and Enforcement
    # =========================================================================
    
    def validate_usage_limits(self, user_tier: str, current_usage: Dict[str, int]) -> Dict[str, Any]:
        """Validate current usage against tier limits.
        
        Args:
            user_tier: User's subscription tier
            current_usage: Dictionary with current usage counts
            
        Returns:
            Dict: Validation result with limits and current usage
        """
        try:
            tier_enum = self._parse_user_tier(user_tier)
            if not tier_enum:
                tier_enum = UserTier.FREE
            
            config = self.configs.get(tier_enum, self.configs[UserTier.FREE])
            
            daily_agents = current_usage.get("daily_agents", 0)
            concurrent_agents = current_usage.get("concurrent_agents", 0)
            
            validation_result = {
                "tier": user_tier,
                "usage_valid": True,
                "limits": {
                    "daily_limit": config.max_agents_per_day,
                    "concurrent_limit": config.concurrent_executions
                },
                "current_usage": {
                    "daily_agents": daily_agents,
                    "concurrent_agents": concurrent_agents
                },
                "violations": []
            }
            
            # Check daily limit
            if daily_agents >= config.max_agents_per_day:
                validation_result["usage_valid"] = False
                validation_result["violations"].append("daily_limit_exceeded")
            
            # Check concurrent limit
            if concurrent_agents >= config.concurrent_executions:
                validation_result["usage_valid"] = False
                validation_result["violations"].append("concurrent_limit_exceeded")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Usage validation error: {e}")
            return {
                "usage_valid": False,
                "error": str(e)
            }
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _parse_user_tier(self, user_tier: str) -> Optional[UserTier]:
        """Parse user tier string to enum."""
        try:
            tier_str = user_tier.lower().strip()
            for tier in UserTier:
                if tier.value == tier_str:
                    return tier
            return None
        except Exception:
            return None
    
    def _is_agent_type_allowed(self, agent_type: str, config: BusinessRuleConfig) -> bool:
        """Check if agent type is allowed for the tier configuration."""
        if "*" in config.allowed_agent_types:
            return True
        return agent_type in config.allowed_agent_types
    
    def _has_required_permissions(self, user_permissions: List[str], agent_type: str) -> bool:
        """Check if user has required permissions for agent type."""
        # Basic requirement: must have at least 'read' permission
        if "read" not in user_permissions:
            return False
        
        # Only premium agents require premium permissions (not advanced agents)
        if "premium" in agent_type.lower() and "premium" not in user_permissions:
            return False
        
        return True
    
    def _get_upgrade_suggestion(self, current_tier: UserTier) -> str:
        """Get appropriate upgrade suggestion based on current tier."""
        upgrade_map = {
            UserTier.FREE: "early",
            UserTier.EARLY: "enterprise", 
            UserTier.MID: "enterprise",
            UserTier.ENTERPRISE: None  # Already at highest tier
        }
        
        return upgrade_map.get(current_tier, "early")
    
    # =========================================================================
    # Business Intelligence Methods
    # =========================================================================
    
    def get_monetization_opportunities(self, user_tier: str, usage_pattern: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify monetization opportunities based on usage patterns.
        
        Args:
            user_tier: Current user tier
            usage_pattern: Dictionary with usage statistics
            
        Returns:
            List[Dict]: Monetization opportunities with recommendations
        """
        try:
            opportunities = []
            
            tier_enum = self._parse_user_tier(user_tier)
            if not tier_enum:
                return opportunities
            
            current_config = self.configs.get(tier_enum)
            if not current_config:
                return opportunities
            
            # Check usage patterns against limits
            daily_usage = usage_pattern.get("daily_agents", 0)
            if daily_usage >= current_config.max_agents_per_day * 0.8:  # 80% of limit
                opportunities.append({
                    "type": "usage_limit_approaching",
                    "description": f"User approaching daily limit ({daily_usage}/{current_config.max_agents_per_day})",
                    "recommendation": f"Suggest upgrade to {self._get_upgrade_suggestion(tier_enum)} tier",
                    "priority": "high"
                })
            
            # Check for premium agent attempts
            premium_attempts = usage_pattern.get("premium_agent_attempts", 0)
            if premium_attempts > 0 and tier_enum == UserTier.FREE:
                opportunities.append({
                    "type": "premium_feature_interest",
                    "description": f"User attempted {premium_attempts} premium agent executions",
                    "recommendation": "Highlight premium features in upgrade offer",
                    "priority": "medium"
                })
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Monetization opportunity analysis error: {e}")
            return []