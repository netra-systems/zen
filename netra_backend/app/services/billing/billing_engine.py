"""Billing Engine for processing usage and generating bills."""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum


class BillingPeriod(Enum):
    """Billing period types."""
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    DAILY = "daily"
    USAGE_BASED = "usage_based"


class BillingStatus(Enum):
    """Billing status types."""
    PENDING = "pending"
    PROCESSED = "processed"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


@dataclass
class BillingLineItem:
    """Individual line item in a bill."""
    description: str
    quantity: float
    unit_price: Decimal
    total_price: Decimal
    usage_type: str
    period_start: datetime
    period_end: datetime
    metadata: Dict[str, Any] = None


@dataclass
class Bill:
    """Complete bill for a user."""
    bill_id: str
    user_id: str
    period_start: datetime
    period_end: datetime
    line_items: List[BillingLineItem]
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    status: BillingStatus
    created_at: datetime
    due_date: datetime
    paid_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None


class BillingEngine:
    """Main billing engine for processing usage and generating bills."""
    
    def __init__(self):
        """Initialize billing engine."""
        self.bills: Dict[str, Bill] = {}
        self.billing_schedules: Dict[str, BillingPeriod] = {}
        self.tax_rates: Dict[str, Decimal] = {
            "default": Decimal("0.08"),  # 8% default tax
            "enterprise": Decimal("0.00")  # No tax for enterprise
        }
        
        self.pricing_tiers = {
            "free": {
                "api_call": Decimal("0.0"),
                "llm_tokens": Decimal("0.0"),
                "monthly_limit": 1000
            },
            "starter": {
                "api_call": Decimal("0.001"),
                "llm_tokens": Decimal("0.00002"),
                "monthly_base": Decimal("10.00")
            },
            "professional": {
                "api_call": Decimal("0.0008"),
                "llm_tokens": Decimal("0.000015"),
                "monthly_base": Decimal("50.00")
            },
            "enterprise": {
                "api_call": Decimal("0.0005"),
                "llm_tokens": Decimal("0.00001"),
                "monthly_base": Decimal("500.00")
            }
        }
        
        self.enabled = True
        
        # Statistics
        self.stats = {
            "bills_generated": 0,
            "total_revenue": Decimal("0.00"),
            "bills_by_status": {status.value: 0 for status in BillingStatus}
        }
    
    async def generate_bill(self, user_id: str, period_start: datetime, 
                          period_end: datetime, usage_data: Dict[str, Any],
                          tier: str = "starter") -> Bill:
        """Generate a bill for a user's usage in a period."""
        if not self.enabled:
            raise RuntimeError("Billing engine is disabled")
        
        # Generate bill ID
        bill_id = f"bill_{user_id}_{int(period_start.timestamp())}"
        
        # Get pricing for tier
        pricing = self.pricing_tiers.get(tier, self.pricing_tiers["starter"])
        
        # Calculate line items
        line_items = []
        subtotal = Decimal("0.00")
        
        # Add base monthly fee if applicable
        if "monthly_base" in pricing:
            base_fee = pricing["monthly_base"]
            line_item = BillingLineItem(
                description=f"{tier.title()} Plan - Monthly Base Fee",
                quantity=1.0,
                unit_price=base_fee,
                total_price=base_fee,
                usage_type="monthly_base",
                period_start=period_start,
                period_end=period_end
            )
            line_items.append(line_item)
            subtotal += base_fee
        
        # Process usage items
        for usage_type, usage_info in usage_data.items():
            if usage_type not in pricing:
                continue
            
            quantity = Decimal(str(usage_info.get("quantity", 0)))
            unit_price = pricing[usage_type]
            
            # Apply free tier limits
            if tier == "free" and "monthly_limit" in pricing:
                quantity = min(quantity, Decimal(str(pricing["monthly_limit"])))
            
            if quantity > 0:
                total_price = (quantity * unit_price).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                
                line_item = BillingLineItem(
                    description=f"{usage_type.replace('_', ' ').title()}",
                    quantity=float(quantity),
                    unit_price=unit_price,
                    total_price=total_price,
                    usage_type=usage_type,
                    period_start=period_start,
                    period_end=period_end,
                    metadata=usage_info.get("metadata")
                )
                line_items.append(line_item)
                subtotal += total_price
        
        # Calculate tax
        tax_rate = self._get_tax_rate(user_id, tier)
        tax_amount = (subtotal * tax_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        # Calculate total
        total_amount = subtotal + tax_amount
        
        # Create bill
        bill = Bill(
            bill_id=bill_id,
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
            line_items=line_items,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            status=BillingStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
            metadata={"tier": tier}
        )
        
        # Store bill
        self.bills[bill_id] = bill
        
        # Update statistics
        self.stats["bills_generated"] += 1
        self.stats["bills_by_status"][BillingStatus.PENDING.value] += 1
        
        return bill
    
    async def process_payment(self, bill_id: str, payment_amount: Decimal,
                            payment_method: str = "card") -> bool:
        """Process payment for a bill."""
        if bill_id not in self.bills:
            return False
        
        bill = self.bills[bill_id]
        
        # Check payment amount
        if payment_amount < bill.total_amount:
            return False
        
        # Update bill status
        old_status = bill.status
        bill.status = BillingStatus.PAID
        bill.paid_at = datetime.now(timezone.utc)
        
        # Update statistics
        self.stats["bills_by_status"][old_status.value] -= 1
        self.stats["bills_by_status"][BillingStatus.PAID.value] += 1
        self.stats["total_revenue"] += bill.total_amount
        
        return True
    
    async def get_user_bills(self, user_id: str, 
                           status_filter: Optional[BillingStatus] = None) -> List[Bill]:
        """Get bills for a user."""
        user_bills = [bill for bill in self.bills.values() if bill.user_id == user_id]
        
        if status_filter:
            user_bills = [bill for bill in user_bills if bill.status == status_filter]
        
        # Sort by creation date (newest first)
        return sorted(user_bills, key=lambda b: b.created_at, reverse=True)
    
    async def get_bill(self, bill_id: str) -> Optional[Bill]:
        """Get a specific bill."""
        return self.bills.get(bill_id)
    
    async def update_bill_status(self, bill_id: str, new_status: BillingStatus) -> bool:
        """Update bill status."""
        if bill_id not in self.bills:
            return False
        
        bill = self.bills[bill_id]
        old_status = bill.status
        
        bill.status = new_status
        
        # Update statistics
        self.stats["bills_by_status"][old_status.value] -= 1
        self.stats["bills_by_status"][new_status.value] += 1
        
        return True
    
    async def get_overdue_bills(self) -> List[Bill]:
        """Get all overdue bills."""
        current_time = datetime.now(timezone.utc)
        overdue_bills = []
        
        for bill in self.bills.values():
            if (bill.status == BillingStatus.PENDING and 
                bill.due_date < current_time):
                # Mark as overdue
                bill.status = BillingStatus.OVERDUE
                overdue_bills.append(bill)
        
        return overdue_bills
    
    async def calculate_monthly_revenue(self, month: Optional[datetime] = None) -> Decimal:
        """Calculate revenue for a specific month."""
        if month is None:
            month = datetime.now(timezone.utc)
        
        month_start = month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = month_start + timedelta(days=32)
        month_end = next_month.replace(day=1) - timedelta(seconds=1)
        
        revenue = Decimal("0.00")
        for bill in self.bills.values():
            if (bill.status == BillingStatus.PAID and
                bill.paid_at and
                month_start <= bill.paid_at <= month_end):
                revenue += bill.total_amount
        
        return revenue
    
    def _get_tax_rate(self, user_id: str, tier: str) -> Decimal:
        """Get tax rate for user and tier."""
        if tier == "enterprise":
            return self.tax_rates["enterprise"]
        return self.tax_rates["default"]
    
    def get_pricing_for_tier(self, tier: str) -> Dict[str, Any]:
        """Get pricing information for a tier."""
        return self.pricing_tiers.get(tier, self.pricing_tiers["starter"]).copy()
    
    def update_pricing(self, tier: str, pricing_updates: Dict[str, Any]) -> bool:
        """Update pricing for a tier."""
        if tier not in self.pricing_tiers:
            return False
        
        for key, value in pricing_updates.items():
            if isinstance(value, (int, float, str)):
                self.pricing_tiers[tier][key] = Decimal(str(value))
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get billing engine statistics."""
        return {
            **self.stats,
            "total_revenue_float": float(self.stats["total_revenue"]),
            "enabled": self.enabled,
            "total_bills": len(self.bills),
            "pricing_tiers": len(self.pricing_tiers)
        }
    
    def disable(self) -> None:
        """Disable billing engine."""
        self.enabled = False
    
    def enable(self) -> None:
        """Enable billing engine."""
        self.enabled = True
