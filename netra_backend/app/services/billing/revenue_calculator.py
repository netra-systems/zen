from netra_backend.app.logging_config import central_logger
"""Revenue Calculator for billing operations.

This module provides functionality for calculating Monthly Recurring Revenue (MRR),
revenue recognition, and other financial metrics for the billing system.

Business Value Justification (BVJ):
- Segment: All tiers (revenue calculations affect entire business)
- Business Goal: Accurate revenue reporting and financial analytics
- Value Impact: Enables accurate financial reporting for stakeholders
- Strategic Impact: Core monetization metrics for business intelligence
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from netra_backend.app.core.unified_logging import get_central_logger
from netra_backend.app.schemas.user_plan import PlanTier

logger = get_central_logger().get_logger(__name__)


class RevenueCalculator:
    """Calculator for revenue metrics and financial reporting."""
    
    def __init__(self):
        """Initialize revenue calculator."""
        self.logger = logger
        
        # Plan tier mappings for compatibility with different naming conventions
        self.tier_mappings = {
            # Test tier names to schema tier names
            "free": PlanTier.FREE,
            "early": PlanTier.PRO,  # Map EARLY to PRO
            "mid": PlanTier.ENTERPRISE,  # Map MID to ENTERPRISE  
            "enterprise": PlanTier.ENTERPRISE,
            # Also support direct schema names
            PlanTier.FREE: PlanTier.FREE,
            PlanTier.PRO: PlanTier.PRO,
            PlanTier.ENTERPRISE: PlanTier.ENTERPRISE,
            PlanTier.DEVELOPER: PlanTier.DEVELOPER,
        }
        
        # Base monthly pricing for different tiers
        self.base_pricing = {
            PlanTier.FREE: Decimal('0'),
            PlanTier.PRO: Decimal('29'),
            PlanTier.ENTERPRISE: Decimal('299'),
            PlanTier.DEVELOPER: Decimal('0'),  # Internal use
        }
    
    async def calculate_mrr(self, subscriptions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate Monthly Recurring Revenue from subscription data.
        
        Args:
            subscriptions: List of subscription dictionaries with plan_tier, 
                         monthly_price, billing_cycle, and status fields
                         
        Returns:
            Dictionary with MRR metrics including total_mrr, active_subscriptions,
            total_subscriptions, and average_arpu
        """
        try:
            total_mrr = Decimal('0')
            active_subscriptions = []
            
            for subscription in subscriptions:
                if subscription.get("status") == "active":
                    active_subscriptions.append(subscription)
                    monthly_price = Decimal(str(subscription.get("monthly_price", 0)))
                    
                    # Adjust for billing cycle
                    billing_cycle = subscription.get("billing_cycle", "monthly")
                    if billing_cycle == "annual":
                        # Convert annual to monthly
                        monthly_price = monthly_price / 12
                    elif billing_cycle == "quarterly":
                        monthly_price = monthly_price / 3
                    
                    total_mrr += monthly_price
            
            active_count = len(active_subscriptions)
            total_count = len(subscriptions)
            average_arpu = total_mrr / active_count if active_count > 0 else Decimal('0')
            
            result = {
                "total_mrr": total_mrr,
                "active_subscriptions": active_count,
                "total_subscriptions": total_count,
                "average_arpu": average_arpu
            }
            
            self.logger.info(f"Calculated MRR: ${total_mrr} from {active_count} active subscriptions")
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating MRR: {e}")
            raise
    
    async def calculate_revenue_recognition(
        self, 
        usage_records: List[Dict[str, Any]], 
        period: Dict[str, datetime]
    ) -> Dict[str, Any]:
        """Calculate revenue recognition for usage-based billing.
        
        Args:
            usage_records: List of usage record dictionaries with user_id,
                         amount, timestamp, and other usage data
            period: Dictionary with 'start' and 'end' datetime keys
                   
        Returns:
            Dictionary with revenue recognition metrics including total_usage_revenue,
            revenue_by_user, and total_users
        """
        try:
            total_usage_revenue = Decimal('0')
            revenue_by_user = {}
            period_start = period["start"]
            period_end = period["end"]
            
            for record in usage_records:
                record_timestamp = record.get("timestamp")
                if not record_timestamp:
                    continue
                    
                # Check if record falls within the recognition period
                if period_start <= record_timestamp <= period_end:
                    user_id = record.get("user_id")
                    if not user_id:
                        continue
                    
                    # Initialize user revenue tracking
                    if user_id not in revenue_by_user:
                        revenue_by_user[user_id] = Decimal('0')
                    
                    # Calculate revenue for this usage record
                    # This is a simplified calculation - in practice, this would
                    # involve more complex pricing models and tier-based calculations
                    amount = Decimal(str(record.get("amount", 0)))
                    usage_type = record.get("type", "unknown")
                    
                    # Simple usage-based revenue calculation
                    # Different types might have different revenue rates
                    revenue_rate = self._get_usage_revenue_rate(usage_type)
                    record_revenue = amount * revenue_rate
                    
                    revenue_by_user[user_id] += record_revenue
                    total_usage_revenue += record_revenue
            
            result = {
                "period": period,
                "total_usage_revenue": total_usage_revenue,
                "revenue_by_user": revenue_by_user,
                "total_users": len(revenue_by_user)
            }
            
            self.logger.info(
                f"Calculated usage revenue: ${total_usage_revenue} from {len(revenue_by_user)} users "
                f"in period {period_start} to {period_end}"
            )
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating revenue recognition: {e}")
            raise
    
    async def calculate_tier_revenue_breakdown(
        self, 
        subscriptions: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate revenue breakdown by plan tier.
        
        Args:
            subscriptions: List of subscription dictionaries
            
        Returns:
            Dictionary with revenue breakdown by tier
        """
        try:
            tier_breakdown = {}
            
            for subscription in subscriptions:
                if subscription.get("status") != "active":
                    continue
                    
                plan_tier = subscription.get("plan_tier", "free")
                monthly_price = Decimal(str(subscription.get("monthly_price", 0)))
                
                # Normalize tier name
                normalized_tier = self._normalize_tier_name(plan_tier)
                
                if normalized_tier not in tier_breakdown:
                    tier_breakdown[normalized_tier] = {
                        "subscription_count": 0,
                        "total_mrr": Decimal('0'),
                        "average_price": Decimal('0')
                    }
                
                tier_breakdown[normalized_tier]["subscription_count"] += 1
                tier_breakdown[normalized_tier]["total_mrr"] += monthly_price
            
            # Calculate averages
            for tier_data in tier_breakdown.values():
                if tier_data["subscription_count"] > 0:
                    tier_data["average_price"] = (
                        tier_data["total_mrr"] / tier_data["subscription_count"]
                    )
            
            return tier_breakdown
            
        except Exception as e:
            self.logger.error(f"Error calculating tier revenue breakdown: {e}")
            raise
    
    async def calculate_churn_impact(
        self, 
        cancelled_subscriptions: List[Dict[str, Any]],
        period: Dict[str, datetime]
    ) -> Dict[str, Any]:
        """Calculate revenue impact from subscription churn.
        
        Args:
            cancelled_subscriptions: List of cancelled subscription dictionaries
            period: Time period for churn analysis
            
        Returns:
            Dictionary with churn impact metrics
        """
        try:
            total_lost_mrr = Decimal('0')
            churn_by_tier = {}
            period_start = period["start"]
            period_end = period["end"]
            
            for subscription in cancelled_subscriptions:
                cancelled_at = subscription.get("cancelled_at")
                if not cancelled_at or not (period_start <= cancelled_at <= period_end):
                    continue
                    
                monthly_price = Decimal(str(subscription.get("monthly_price", 0)))
                plan_tier = self._normalize_tier_name(subscription.get("plan_tier", "free"))
                
                total_lost_mrr += monthly_price
                
                if plan_tier not in churn_by_tier:
                    churn_by_tier[plan_tier] = {
                        "cancelled_count": 0,
                        "lost_mrr": Decimal('0')
                    }
                
                churn_by_tier[plan_tier]["cancelled_count"] += 1
                churn_by_tier[plan_tier]["lost_mrr"] += monthly_price
            
            return {
                "period": period,
                "total_lost_mrr": total_lost_mrr,
                "total_cancellations": len(cancelled_subscriptions),
                "churn_by_tier": churn_by_tier
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating churn impact: {e}")
            raise
    
    def _normalize_tier_name(self, tier: Any) -> str:
        """Normalize tier name for consistency.
        
        Args:
            tier: Tier identifier (string or PlanTier enum)
            
        Returns:
            Normalized tier name as string
        """
        if isinstance(tier, str):
            tier_lower = tier.lower()
            # Map test tier names to standard names
            if tier_lower == "early":
                return "pro"
            elif tier_lower == "mid":
                return "enterprise"
            return tier_lower
        elif hasattr(tier, 'value'):
            return tier.value
        else:
            return str(tier).lower()
    
    def _get_usage_revenue_rate(self, usage_type: str) -> Decimal:
        """Get revenue rate for different usage types.
        
        Args:
            usage_type: Type of usage (api_calls, ai_operations, etc.)
            
        Returns:
            Revenue rate per unit of usage
        """
        # Simple revenue rates - in practice, these would be more sophisticated
        # and potentially vary by customer tier
        usage_rates = {
            "api_calls": Decimal('0.001'),      # $0.001 per API call
            "ai_operations": Decimal('0.01'),   # $0.01 per AI operation
            "data_storage": Decimal('0.1'),     # $0.1 per GB stored
            "default": Decimal('0.01')          # Default rate
        }
        
        return usage_rates.get(usage_type, usage_rates["default"])
    
    def get_supported_tiers(self) -> List[str]:
        """Get list of supported plan tiers.
        
        Returns:
            List of supported tier names
        """
        return list(self.base_pricing.keys())
    
    def get_base_pricing(self) -> Dict[str, Decimal]:
        """Get base pricing for all tiers.
        
        Returns:
            Dictionary of tier to base monthly price mapping
        """
        return self.base_pricing.copy()