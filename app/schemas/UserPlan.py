"""
User Plan Schemas
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC
from pydantic import BaseModel, Field
from enum import Enum


class PlanTier(str, Enum):
    """Available plan tiers"""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    DEVELOPER = "developer"


class ToolAllowance(BaseModel):
    """Tool usage allowance"""
    tool_name: str = Field(description="Tool name or '*' for all tools")
    limit: int = Field(description="Usage limit (-1 for unlimited)")
    period: str = Field(description="Time period: 'minute', 'hour', 'day', 'month'")
    burst_limit: Optional[int] = Field(default=None, description="Burst allowance")


class PlanFeatures(BaseModel):
    """Features included in a plan"""
    permissions: List[str] = Field(description="Included permissions")
    tool_allowances: List[ToolAllowance] = Field(description="Tool usage allowances")
    feature_flags: List[str] = Field(default_factory=list, description="Enabled feature flags")
    rate_limit_multiplier: float = Field(default=1.0, description="Rate limit multiplier")
    support_level: str = Field(default="basic", description="Support level")
    max_threads: Optional[int] = Field(default=None, description="Maximum threads")
    max_corpus_size: Optional[int] = Field(default=None, description="Maximum corpus size")


class UserPlan(BaseModel):
    """User's subscription plan"""
    user_id: str = Field(description="User identifier")
    tier: PlanTier = Field(description="Plan tier")
    features: PlanFeatures = Field(description="Plan features")
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: Optional[datetime] = Field(default=None, description="Plan expiration")
    auto_renew: bool = Field(default=False, description="Auto-renewal enabled")
    payment_status: str = Field(default="active", description="Payment status")
    trial_period: int = Field(default=0, description="Trial period days (0 = not in trial)")
    upgraded_from: Optional[str] = Field(default=None, description="Previous plan tier")


class PlanDefinition(BaseModel):
    """Definition of a subscription plan"""
    tier: PlanTier = Field(description="Plan tier")
    name: str = Field(description="Display name")
    description: str = Field(description="Plan description")
    price_monthly: Optional[float] = Field(default=None, description="Monthly price in USD")
    price_yearly: Optional[float] = Field(default=None, description="Yearly price in USD")
    features: PlanFeatures = Field(description="Plan features")
    trial_days: int = Field(default=0, description="Free trial days")
    popular: bool = Field(default=False, description="Popular plan marker")
    hidden: bool = Field(default=False, description="Hidden from selection")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UsageRecord(BaseModel):
    """Tool usage record for billing/analytics"""
    user_id: str = Field(description="User identifier")
    tool_name: str = Field(description="Tool used")
    category: str = Field(description="Tool category")
    execution_time_ms: int = Field(description="Execution time in milliseconds")
    tokens_used: Optional[int] = Field(default=None, description="Tokens consumed")
    cost_cents: Optional[int] = Field(default=None, description="Cost in cents")
    status: str = Field(description="Execution status")
    plan_tier: str = Field(description="User's plan at time of usage")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PlanUsageSummary(BaseModel):
    """Summary of plan usage"""
    user_id: str = Field(description="User identifier")
    plan_tier: PlanTier = Field(description="Current plan tier")
    period_start: datetime = Field(description="Usage period start")
    period_end: datetime = Field(description="Usage period end")
    tool_usage: Dict[str, int] = Field(description="Tool usage counts")
    total_executions: int = Field(description="Total tool executions")
    total_cost_cents: int = Field(description="Total cost in cents")
    rate_limit_hits: int = Field(description="Rate limit violations")
    upgrade_suggestions: List[str] = Field(default_factory=list, description="Suggested upgrades")


class PlanUpgrade(BaseModel):
    """Plan upgrade/downgrade request"""
    user_id: str = Field(description="User identifier")
    from_tier: PlanTier = Field(description="Current plan tier")
    to_tier: PlanTier = Field(description="Target plan tier")
    effective_date: Optional[datetime] = Field(default=None, description="When upgrade takes effect")
    prorate: bool = Field(default=True, description="Prorate charges")
    reason: Optional[str] = Field(default=None, description="Reason for change")


class AutoUpgradeRule(BaseModel):
    """Automatic upgrade rule"""
    from_tier: PlanTier = Field(description="Source plan tier")
    to_tier: PlanTier = Field(description="Target plan tier")
    trigger_condition: str = Field(description="Condition that triggers upgrade")
    threshold_value: int = Field(description="Threshold value for condition")
    lookback_days: int = Field(description="Days to look back for condition")
    auto_apply: bool = Field(default=False, description="Automatically apply upgrade")
    notify_user: bool = Field(default=True, description="Notify user of upgrade")


# Plan tier definitions
PLAN_DEFINITIONS = {
    PlanTier.FREE: PlanDefinition(
        tier=PlanTier.FREE,
        name="Free",
        description="Basic functionality for individual users",
        features=PlanFeatures(
            permissions=["basic"],
            tool_allowances=[
                ToolAllowance(tool_name="create_thread", limit=10, period="day"),
                ToolAllowance(tool_name="get_thread_history", limit=100, period="day"),
                ToolAllowance(tool_name="list_agents", limit=100, period="day"),
            ],
            max_threads=5,
            max_corpus_size=1000,
        ),
        trial_days=0,
    ),
    
    PlanTier.PRO: PlanDefinition(
        tier=PlanTier.PRO,
        name="Professional",
        description="Advanced features for professionals and small teams",
        price_monthly=29.0,
        price_yearly=299.0,
        features=PlanFeatures(
            permissions=["basic", "analytics", "data_management"],
            tool_allowances=[
                ToolAllowance(tool_name="*", limit=1000, period="day"),
                ToolAllowance(tool_name="generate_synthetic_data", limit=10000, period="day"),
                ToolAllowance(tool_name="analyze_workload", limit=500, period="day"),
            ],
            feature_flags=["data_operations", "advanced_analytics"],
            rate_limit_multiplier=2.0,
            support_level="priority",
            max_threads=50,
            max_corpus_size=100000,
        ),
        trial_days=14,
        popular=True,
    ),
    
    PlanTier.ENTERPRISE: PlanDefinition(
        tier=PlanTier.ENTERPRISE,
        name="Enterprise",
        description="Full functionality for large organizations",
        price_monthly=299.0,
        price_yearly=2999.0,
        features=PlanFeatures(
            permissions=["basic", "analytics", "data_management", "advanced_optimization", "system_management"],
            tool_allowances=[
                ToolAllowance(tool_name="*", limit=-1, period="day"),  # Unlimited
            ],
            feature_flags=["data_operations", "advanced_analytics", "advanced_optimization", "system_management"],
            rate_limit_multiplier=10.0,
            support_level="dedicated",
            max_threads=-1,  # Unlimited
            max_corpus_size=-1,  # Unlimited
        ),
        trial_days=30,
    ),
    
    PlanTier.DEVELOPER: PlanDefinition(
        tier=PlanTier.DEVELOPER,
        name="Developer",
        description="Full access for Netra developers",
        features=PlanFeatures(
            permissions=["*"],  # All permissions
            tool_allowances=[
                ToolAllowance(tool_name="*", limit=-1, period="day"),  # Unlimited
            ],
            feature_flags=["*"],  # All feature flags
            rate_limit_multiplier=100.0,
            support_level="internal",
            max_threads=-1,  # Unlimited
            max_corpus_size=-1,  # Unlimited
        ),
        hidden=True,  # Not shown in public plan selection
    ),
}