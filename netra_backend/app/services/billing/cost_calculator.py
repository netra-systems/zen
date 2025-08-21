"""Cost Calculator for comprehensive billing cost calculations."""

import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum


class CostType(Enum):
    """Types of costs that can be calculated."""
    COMPUTE = "compute"
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"
    API_CALLS = "api_calls"
    LLM_TOKENS = "llm_tokens"
    AGENT_EXECUTION = "agent_execution"
    WEBSOCKET_CONNECTIONS = "websocket_connections"
    PREMIUM_FEATURES = "premium_features"


@dataclass
class CostComponent:
    """Individual cost component."""
    cost_type: CostType
    quantity: Decimal
    unit_price: Decimal
    total_cost: Decimal
    unit: str
    description: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CostBreakdown:
    """Complete cost breakdown."""
    user_id: str
    period_start: datetime
    period_end: datetime
    components: List[CostComponent]
    subtotal: Decimal
    discounts: Decimal
    taxes: Decimal
    total_cost: Decimal
    currency: str = "USD"
    metadata: Optional[Dict[str, Any]] = None


class PricingTier:
    """Pricing tier with usage limits and rates."""
    
    def __init__(self, name: str, monthly_base: Decimal = Decimal("0")):
        self.name = name
        self.monthly_base = monthly_base
        self.pricing: Dict[CostType, Dict[str, Any]] = {}
        self.limits: Dict[CostType, Decimal] = {}
        self.overages: Dict[CostType, Decimal] = {}
    
    def set_pricing(self, cost_type: CostType, unit_price: Decimal, 
                   unit: str = "unit", limit: Optional[Decimal] = None,
                   overage_price: Optional[Decimal] = None) -> None:
        """Set pricing for a cost type."""
        self.pricing[cost_type] = {
            "unit_price": unit_price,
            "unit": unit,
        }
        
        if limit is not None:
            self.limits[cost_type] = limit
        
        if overage_price is not None:
            self.overages[cost_type] = overage_price
    
    def get_cost(self, cost_type: CostType, quantity: Decimal) -> Tuple[Decimal, Decimal]:
        """Calculate cost and overage for quantity."""
        if cost_type not in self.pricing:
            return Decimal("0"), Decimal("0")
        
        pricing_info = self.pricing[cost_type]
        base_price = pricing_info["unit_price"]
        
        # Check if there's a limit
        if cost_type in self.limits:
            limit = self.limits[cost_type]
            
            if quantity <= limit:
                # Within limit
                return quantity * base_price, Decimal("0")
            else:
                # Exceeds limit
                base_cost = limit * base_price
                overage_quantity = quantity - limit
                overage_price = self.overages.get(cost_type, base_price)
                overage_cost = overage_quantity * overage_price
                
                return base_cost, overage_cost
        else:
            # No limit, just calculate based on quantity
            return quantity * base_price, Decimal("0")


class CostCalculator:
    """Comprehensive cost calculator for all billing scenarios."""
    
    def __init__(self):
        """Initialize cost calculator."""
        self.pricing_tiers: Dict[str, PricingTier] = {}
        self.tax_rates: Dict[str, Decimal] = {
            "default": Decimal("0.08"),  # 8% default
            "enterprise": Decimal("0.00"),  # No tax for enterprise
            "eu": Decimal("0.20"),  # 20% VAT
            "canada": Decimal("0.13")  # 13% HST
        }
        
        self.discount_rules: List[Dict[str, Any]] = []
        
        # Initialize default pricing tiers
        self._setup_default_tiers()
        
        self.enabled = True
        
        # Statistics
        self.stats = {
            "calculations_performed": 0,
            "total_cost_calculated": Decimal("0.00"),
            "calculations_by_tier": {},
            "average_calculation_value": Decimal("0.00")
        }
    
    def _setup_default_tiers(self) -> None:
        """Setup default pricing tiers."""
        # Free tier
        free_tier = PricingTier("free")
        free_tier.set_pricing(CostType.API_CALLS, Decimal("0"), "call", limit=Decimal("1000"))
        free_tier.set_pricing(CostType.LLM_TOKENS, Decimal("0"), "token", limit=Decimal("50000"))
        free_tier.set_pricing(CostType.STORAGE, Decimal("0"), "GB", limit=Decimal("1"))
        self.pricing_tiers["free"] = free_tier
        
        # Starter tier
        starter_tier = PricingTier("starter", Decimal("10.00"))
        starter_tier.set_pricing(CostType.API_CALLS, Decimal("0.001"), "call")
        starter_tier.set_pricing(CostType.LLM_TOKENS, Decimal("0.00002"), "token")
        starter_tier.set_pricing(CostType.STORAGE, Decimal("0.10"), "GB")
        starter_tier.set_pricing(CostType.BANDWIDTH, Decimal("0.09"), "GB")
        starter_tier.set_pricing(CostType.WEBSOCKET_CONNECTIONS, Decimal("0.001"), "connection-hour")
        self.pricing_tiers["starter"] = starter_tier
        
        # Professional tier
        pro_tier = PricingTier("professional", Decimal("50.00"))
        pro_tier.set_pricing(CostType.API_CALLS, Decimal("0.0008"), "call")
        pro_tier.set_pricing(CostType.LLM_TOKENS, Decimal("0.000015"), "token")
        pro_tier.set_pricing(CostType.STORAGE, Decimal("0.08"), "GB")
        pro_tier.set_pricing(CostType.BANDWIDTH, Decimal("0.07"), "GB")
        pro_tier.set_pricing(CostType.WEBSOCKET_CONNECTIONS, Decimal("0.0008"), "connection-hour")
        pro_tier.set_pricing(CostType.AGENT_EXECUTION, Decimal("0.005"), "execution")
        self.pricing_tiers["professional"] = pro_tier
        
        # Enterprise tier
        enterprise_tier = PricingTier("enterprise", Decimal("500.00"))
        enterprise_tier.set_pricing(CostType.API_CALLS, Decimal("0.0005"), "call")
        enterprise_tier.set_pricing(CostType.LLM_TOKENS, Decimal("0.00001"), "token")
        enterprise_tier.set_pricing(CostType.STORAGE, Decimal("0.05"), "GB")
        enterprise_tier.set_pricing(CostType.BANDWIDTH, Decimal("0.05"), "GB")
        enterprise_tier.set_pricing(CostType.WEBSOCKET_CONNECTIONS, Decimal("0.0005"), "connection-hour")
        enterprise_tier.set_pricing(CostType.AGENT_EXECUTION, Decimal("0.003"), "execution")
        enterprise_tier.set_pricing(CostType.PREMIUM_FEATURES, Decimal("0.01"), "feature-use")
        self.pricing_tiers["enterprise"] = enterprise_tier
    
    def calculate_cost_breakdown(self, user_id: str, usage_data: Dict[str, Any],
                               tier_name: str = "starter", 
                               period_start: Optional[datetime] = None,
                               period_end: Optional[datetime] = None,
                               region: str = "default") -> CostBreakdown:
        """Calculate comprehensive cost breakdown."""
        if not self.enabled:
            raise RuntimeError("Cost calculator is disabled")
        
        if period_start is None:
            period_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if period_end is None:
            period_end = datetime.now(timezone.utc)
        
        # Get pricing tier
        tier = self.pricing_tiers.get(tier_name, self.pricing_tiers["starter"])
        
        components = []
        subtotal = Decimal("0.00")
        
        # Add base monthly fee if applicable
        if tier.monthly_base > 0:
            component = CostComponent(
                cost_type=CostType.PREMIUM_FEATURES,
                quantity=Decimal("1"),
                unit_price=tier.monthly_base,
                total_cost=tier.monthly_base,
                unit="month",
                description=f"{tier_name.title()} Plan Monthly Fee"
            )
            components.append(component)
            subtotal += tier.monthly_base
        
        # Calculate costs for each usage type
        for usage_type_str, usage_info in usage_data.items():
            try:
                cost_type = CostType(usage_type_str)
            except ValueError:
                continue  # Skip unknown cost types
            
            quantity = Decimal(str(usage_info.get("quantity", 0)))
            if quantity <= 0:
                continue
            
            # Get cost from tier
            base_cost, overage_cost = tier.get_cost(cost_type, quantity)
            total_cost = base_cost + overage_cost
            
            if total_cost > 0:
                # Calculate effective unit price
                unit_price = total_cost / quantity
                
                component = CostComponent(
                    cost_type=cost_type,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_cost=total_cost,
                    unit=tier.pricing.get(cost_type, {}).get("unit", "unit"),
                    description=f"{cost_type.value.replace('_', ' ').title()}",
                    metadata={
                        "base_cost": float(base_cost),
                        "overage_cost": float(overage_cost),
                        "tier": tier_name
                    }
                )
                components.append(component)
                subtotal += total_cost
        
        # Apply discounts
        discounts = self._calculate_discounts(subtotal, usage_data, tier_name)
        
        # Calculate taxes
        tax_rate = self.tax_rates.get(region, self.tax_rates["default"])
        if tier_name == "enterprise":
            tax_rate = self.tax_rates["enterprise"]
        
        taxes = ((subtotal - discounts) * tax_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        # Calculate total
        total_cost = subtotal - discounts + taxes
        
        # Update statistics
        self.stats["calculations_performed"] += 1
        self.stats["total_cost_calculated"] += total_cost
        
        if tier_name not in self.stats["calculations_by_tier"]:
            self.stats["calculations_by_tier"][tier_name] = 0
        self.stats["calculations_by_tier"][tier_name] += 1
        
        self.stats["average_calculation_value"] = (
            self.stats["total_cost_calculated"] / 
            max(self.stats["calculations_performed"], 1)
        )
        
        return CostBreakdown(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
            components=components,
            subtotal=subtotal,
            discounts=discounts,
            taxes=taxes,
            total_cost=total_cost,
            metadata={
                "tier": tier_name,
                "region": region,
                "tax_rate": float(tax_rate)
            }
        )
    
    def estimate_monthly_cost(self, usage_projections: Dict[str, float],
                            tier_name: str = "starter") -> Dict[str, Any]:
        """Estimate monthly cost based on usage projections."""
        # Convert projections to usage_data format
        usage_data = {
            cost_type: {"quantity": quantity}
            for cost_type, quantity in usage_projections.items()
        }
        
        # Calculate cost breakdown
        breakdown = self.calculate_cost_breakdown(
            user_id="projection",
            usage_data=usage_data,
            tier_name=tier_name
        )
        
        return {
            "tier": tier_name,
            "projected_monthly_cost": float(breakdown.total_cost),
            "breakdown_by_type": {
                component.cost_type.value: {
                    "quantity": float(component.quantity),
                    "unit_price": float(component.unit_price),
                    "total_cost": float(component.total_cost),
                    "unit": component.unit
                }
                for component in breakdown.components
            },
            "subtotal": float(breakdown.subtotal),
            "discounts": float(breakdown.discounts),
            "taxes": float(breakdown.taxes)
        }
    
    def compare_tier_costs(self, usage_projections: Dict[str, float]) -> Dict[str, Any]:
        """Compare costs across all tiers for given usage."""
        comparisons = {}
        
        for tier_name in self.pricing_tiers.keys():
            estimate = self.estimate_monthly_cost(usage_projections, tier_name)
            comparisons[tier_name] = estimate
        
        # Find cheapest tier
        cheapest_tier = min(comparisons.keys(), 
                           key=lambda t: comparisons[t]["projected_monthly_cost"])
        
        return {
            "comparisons": comparisons,
            "cheapest_tier": cheapest_tier,
            "cheapest_cost": comparisons[cheapest_tier]["projected_monthly_cost"],
            "usage_projections": usage_projections
        }
    
    def _calculate_discounts(self, subtotal: Decimal, usage_data: Dict[str, Any],
                           tier_name: str) -> Decimal:
        """Calculate applicable discounts."""
        total_discount = Decimal("0.00")
        
        for rule in self.discount_rules:
            discount = self._apply_discount_rule(rule, subtotal, usage_data, tier_name)
            total_discount += discount
        
        return total_discount
    
    def _apply_discount_rule(self, rule: Dict[str, Any], subtotal: Decimal,
                           usage_data: Dict[str, Any], tier_name: str) -> Decimal:
        """Apply a specific discount rule."""
        rule_type = rule.get("type")
        
        if rule_type == "volume_discount":
            # Volume discount based on total amount
            threshold = Decimal(str(rule.get("threshold", 0)))
            discount_rate = Decimal(str(rule.get("discount_rate", 0)))
            
            if subtotal >= threshold:
                return subtotal * discount_rate
        
        elif rule_type == "tier_discount":
            # Tier-specific discount
            applicable_tiers = rule.get("tiers", [])
            discount_amount = Decimal(str(rule.get("discount_amount", 0)))
            
            if tier_name in applicable_tiers:
                return discount_amount
        
        elif rule_type == "usage_discount":
            # Discount based on specific usage type
            usage_type = rule.get("usage_type")
            min_quantity = Decimal(str(rule.get("min_quantity", 0)))
            discount_rate = Decimal(str(rule.get("discount_rate", 0)))
            
            if usage_type in usage_data:
                quantity = Decimal(str(usage_data[usage_type].get("quantity", 0)))
                if quantity >= min_quantity:
                    return subtotal * discount_rate
        
        return Decimal("0.00")
    
    def add_discount_rule(self, rule: Dict[str, Any]) -> None:
        """Add a discount rule."""
        self.discount_rules.append(rule)
    
    def get_pricing_tier(self, tier_name: str) -> Optional[PricingTier]:
        """Get pricing tier by name."""
        return self.pricing_tiers.get(tier_name)
    
    def add_pricing_tier(self, tier: PricingTier) -> None:
        """Add a new pricing tier."""
        self.pricing_tiers[tier.name] = tier
    
    def update_tax_rate(self, region: str, tax_rate: Decimal) -> None:
        """Update tax rate for a region."""
        self.tax_rates[region] = tax_rate
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cost calculator statistics."""
        return {
            "enabled": self.enabled,
            "calculations_performed": self.stats["calculations_performed"],
            "total_cost_calculated": float(self.stats["total_cost_calculated"]),
            "average_calculation_value": float(self.stats["average_calculation_value"]),
            "calculations_by_tier": self.stats["calculations_by_tier"],
            "pricing_tiers_available": len(self.pricing_tiers),
            "discount_rules_active": len(self.discount_rules),
            "tax_regions_configured": len(self.tax_rates)
        }
    
    def disable(self) -> None:
        """Disable cost calculator."""
        self.enabled = False
    
    def enable(self) -> None:
        """Enable cost calculator."""
        self.enabled = True
