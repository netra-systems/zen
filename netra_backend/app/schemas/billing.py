"""
Billing and invoicing schemas for Netra platform.
"""

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Re-export from UserPlan for compatibility
from netra_backend.app.schemas.user_plan import PlanTier as BillingTier


class UsageEventType(str, Enum):
    """Types of usage events for billing"""
    API_CALL = "api_call"
    TOOL_EXECUTION = "tool_execution"
    DATA_PROCESSING = "data_processing"
    STORAGE = "storage"
    COMPUTE = "compute"
    BANDWIDTH = "bandwidth"


class UsageEvent(BaseModel):
    """Individual usage event for billing tracking"""
    id: str = Field(description="Unique event identifier")
    user_id: str = Field(description="User who generated the usage")
    event_type: UsageEventType = Field(description="Type of usage event")
    resource_name: str = Field(description="Name of the resource used")
    quantity: Decimal = Field(description="Quantity used")
    unit: str = Field(description="Unit of measurement")
    cost_per_unit: Decimal = Field(description="Cost per unit in USD")
    total_cost: Decimal = Field(description="Total cost for this event")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional event metadata")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    billing_period: str = Field(description="Billing period this event belongs to")


class InvoiceStatus(str, Enum):
    """Invoice status values"""
    DRAFT = "draft"
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class InvoiceLineItem(BaseModel):
    """Individual line item on an invoice"""
    description: str = Field(description="Description of the charge")
    quantity: Decimal = Field(description="Quantity")
    unit_price: Decimal = Field(description="Price per unit")
    total: Decimal = Field(description="Line item total")
    usage_events: List[str] = Field(default_factory=list, description="Related usage event IDs")


class Invoice(BaseModel):
    """Invoice for billing"""
    id: str = Field(description="Unique invoice identifier")
    user_id: str = Field(description="User being billed")
    billing_period_start: datetime = Field(description="Start of billing period")
    billing_period_end: datetime = Field(description="End of billing period")
    line_items: List[InvoiceLineItem] = Field(description="Invoice line items")
    subtotal: Decimal = Field(description="Subtotal before taxes")
    tax_amount: Decimal = Field(default=Decimal('0'), description="Tax amount")
    total_amount: Decimal = Field(description="Total amount due")
    currency: str = Field(default="USD", description="Currency code")
    status: InvoiceStatus = Field(default=InvoiceStatus.DRAFT)
    due_date: datetime = Field(description="Payment due date")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    paid_at: Optional[datetime] = Field(default=None, description="When payment was received")
    payment_method: Optional[str] = Field(default=None, description="Payment method used")


class PaymentStatus(str, Enum):
    """Payment status values"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class Payment(BaseModel):
    """Payment record"""
    id: str = Field(description="Unique payment identifier")
    invoice_id: str = Field(description="Related invoice ID")
    user_id: str = Field(description="User making payment")
    amount: Decimal = Field(description="Payment amount")
    currency: str = Field(default="USD", description="Currency code")
    status: PaymentStatus = Field(description="Payment status")
    payment_method: str = Field(description="Payment method used")
    transaction_id: Optional[str] = Field(default=None, description="External transaction ID")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = Field(default=None, description="When payment completed")
    failure_reason: Optional[str] = Field(default=None, description="Failure reason if applicable")


class BillingPeriod(BaseModel):
    """Billing period definition"""
    id: str = Field(description="Unique period identifier")
    start_date: datetime = Field(description="Period start date")
    end_date: datetime = Field(description="Period end date")
    closed: bool = Field(default=False, description="Whether period is closed for billing")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UsageSummary(BaseModel):
    """Usage summary for a billing period"""
    user_id: str = Field(description="User ID")
    billing_period_id: str = Field(description="Billing period")
    total_events: int = Field(description="Total usage events")
    total_cost: Decimal = Field(description="Total cost for period")
    usage_by_type: Dict[str, Decimal] = Field(description="Usage breakdown by type")
    cost_by_type: Dict[str, Decimal] = Field(description="Cost breakdown by type")
    tier: BillingTier = Field(description="User's billing tier during period")