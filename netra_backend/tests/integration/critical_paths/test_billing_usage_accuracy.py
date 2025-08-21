"""Billing and Usage Accuracy Critical Path Tests

Business Value Justification (BVJ):
- Segment: All tiers (billing accuracy critical for revenue)
- Business Goal: Accurate usage tracking and billing to maintain customer trust
- Value Impact: Prevents revenue leakage, ensures billing compliance, customer retention
- Strategic Impact: $50K-100K MRR protection through accurate billing and usage metering

Critical Path: Usage event capture -> Metering aggregation -> Billing calculation -> Invoice generation -> Payment processing
Coverage: Usage tracking accuracy, billing calculations, invoice generation, payment reconciliation
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.schemas.billing import BillingTier, Invoice, UsageEvent
from netra_backend.app.services.billing.billing_engine import BillingEngine
from netra_backend.app.services.billing.invoice_generator import InvoiceGenerator
from netra_backend.app.services.billing.payment_processor import PaymentProcessor

# Add project root to path
from netra_backend.app.services.billing.usage_tracker import UsageTracker

# Add project root to path

logger = logging.getLogger(__name__)


class BillingAccuracyManager:
    """Manages billing accuracy testing with real usage tracking."""
    
    def __init__(self):
        self.usage_tracker = None
        self.billing_engine = None
        self.invoice_generator = None
        self.payment_processor = None
        self.usage_events = []
        self.billing_calculations = []
        self.invoices_generated = []
        self.payment_transactions = []
        
    async def initialize_services(self):
        """Initialize billing services."""
        try:
            self.usage_tracker = UsageTracker()
            await self.usage_tracker.initialize()
            
            self.billing_engine = BillingEngine()
            await self.billing_engine.initialize()
            
            self.invoice_generator = InvoiceGenerator()
            await self.invoice_generator.initialize()
            
            self.payment_processor = PaymentProcessor()
            await self.payment_processor.initialize()
            
            logger.info("Billing accuracy services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize billing services: {e}")
            raise
    
    async def track_usage_event(self, user_id: str, tier: BillingTier, event_type: str, 
                              quantity: float, metadata: Dict = None) -> Dict[str, Any]:
        """Track a usage event with accuracy validation."""
        event_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        try:
            usage_event = UsageEvent(
                id=event_id,
                user_id=user_id,
                tier=tier,
                event_type=event_type,
                quantity=quantity,
                timestamp=timestamp,
                metadata=metadata or {}
            )
            
            # Record usage event
            tracking_result = await self.usage_tracker.record_event(usage_event)
            
            if tracking_result["success"]:
                self.usage_events.append({
                    "event_id": event_id,
                    "user_id": user_id,
                    "tier": tier.value,
                    "event_type": event_type,
                    "quantity": quantity,
                    "timestamp": timestamp,
                    "tracked_successfully": True,
                    "tracking_latency": tracking_result.get("latency", 0)
                })
            else:
                self.usage_events.append({
                    "event_id": event_id,
                    "user_id": user_id,
                    "tier": tier.value,
                    "event_type": event_type,
                    "quantity": quantity,
                    "timestamp": timestamp,
                    "tracked_successfully": False,
                    "error": tracking_result.get("error")
                })
            
            return {
                "event_id": event_id,
                "tracked": tracking_result["success"],
                "tracking_result": tracking_result
            }
            
        except Exception as e:
            logger.error(f"Failed to track usage event: {e}")
            return {
                "event_id": event_id,
                "tracked": False,
                "error": str(e)
            }
    
    async def calculate_billing_for_period(self, user_id: str, start_date: datetime, 
                                         end_date: datetime) -> Dict[str, Any]:
        """Calculate billing for a specific period with accuracy validation."""
        calculation_id = str(uuid.uuid4())
        
        try:
            # Get usage data for period
            usage_data = await self.usage_tracker.get_usage_for_period(
                user_id, start_date, end_date
            )
            
            # Calculate billing
            billing_result = await self.billing_engine.calculate_billing(
                user_id, usage_data, start_date, end_date
            )
            
            calculation_record = {
                "calculation_id": calculation_id,
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date,
                "usage_events_count": len(usage_data.get("events", [])),
                "total_amount": billing_result.get("total_amount", Decimal("0")),
                "billing_breakdown": billing_result.get("breakdown", {}),
                "calculation_timestamp": datetime.utcnow(),
                "success": billing_result.get("success", False)
            }
            
            self.billing_calculations.append(calculation_record)
            
            return {
                "calculation_id": calculation_id,
                "success": billing_result.get("success", False),
                "total_amount": billing_result.get("total_amount", Decimal("0")),
                "breakdown": billing_result.get("breakdown", {}),
                "usage_summary": usage_data
            }
            
        except Exception as e:
            error_record = {
                "calculation_id": calculation_id,
                "user_id": user_id,
                "error": str(e),
                "calculation_timestamp": datetime.utcnow(),
                "success": False
            }
            
            self.billing_calculations.append(error_record)
            
            return {
                "calculation_id": calculation_id,
                "success": False,
                "error": str(e)
            }
    
    async def generate_invoice(self, user_id: str, billing_calculation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate invoice with accuracy validation."""
        invoice_id = str(uuid.uuid4())
        
        try:
            invoice_data = {
                "invoice_id": invoice_id,
                "user_id": user_id,
                "calculation_id": billing_calculation["calculation_id"],
                "total_amount": billing_calculation["total_amount"],
                "breakdown": billing_calculation["breakdown"],
                "due_date": datetime.utcnow() + timedelta(days=30),
                "generated_at": datetime.utcnow()
            }
            
            generation_result = await self.invoice_generator.generate_invoice(invoice_data)
            
            if generation_result["success"]:
                invoice_record = {
                    "invoice_id": invoice_id,
                    "user_id": user_id,
                    "total_amount": billing_calculation["total_amount"],
                    "status": "generated",
                    "generated_at": datetime.utcnow(),
                    "invoice_data": generation_result.get("invoice_data", {})
                }
                
                self.invoices_generated.append(invoice_record)
            
            return {
                "invoice_id": invoice_id,
                "generated": generation_result["success"],
                "generation_result": generation_result
            }
            
        except Exception as e:
            return {
                "invoice_id": invoice_id,
                "generated": False,
                "error": str(e)
            }
    
    async def process_payment(self, invoice_id: str, payment_method: str = "card") -> Dict[str, Any]:
        """Process payment with transaction tracking."""
        transaction_id = str(uuid.uuid4())
        
        try:
            # Find invoice
            invoice = next(
                (inv for inv in self.invoices_generated if inv["invoice_id"] == invoice_id),
                None
            )
            
            if not invoice:
                raise ValueError(f"Invoice {invoice_id} not found")
            
            # Process payment
            payment_result = await self.payment_processor.process_payment(
                transaction_id, invoice["total_amount"], payment_method
            )
            
            transaction_record = {
                "transaction_id": transaction_id,
                "invoice_id": invoice_id,
                "user_id": invoice["user_id"],
                "amount": invoice["total_amount"],
                "payment_method": payment_method,
                "status": payment_result.get("status", "failed"),
                "processed_at": datetime.utcnow(),
                "success": payment_result.get("success", False)
            }
            
            self.payment_transactions.append(transaction_record)
            
            # Update invoice status
            if payment_result.get("success"):
                invoice["status"] = "paid"
                invoice["paid_at"] = datetime.utcnow()
            
            return {
                "transaction_id": transaction_id,
                "success": payment_result.get("success", False),
                "payment_result": payment_result
            }
            
        except Exception as e:
            error_record = {
                "transaction_id": transaction_id,
                "invoice_id": invoice_id,
                "error": str(e),
                "processed_at": datetime.utcnow(),
                "success": False
            }
            
            self.payment_transactions.append(error_record)
            
            return {
                "transaction_id": transaction_id,
                "success": False,
                "error": str(e)
            }
    
    async def validate_usage_accuracy(self, user_id: str, expected_events: List[Dict]) -> Dict[str, Any]:
        """Validate that tracked usage matches expected events."""
        try:
            # Get tracked events for user
            tracked_events = [
                event for event in self.usage_events 
                if event["user_id"] == user_id and event["tracked_successfully"]
            ]
            
            validation_results = {
                "total_expected": len(expected_events),
                "total_tracked": len(tracked_events),
                "accuracy_rate": 0,
                "missing_events": [],
                "extra_events": [],
                "quantity_discrepancies": []
            }
            
            # Check for missing events
            for expected in expected_events:
                matching_tracked = [
                    tracked for tracked in tracked_events
                    if (tracked["event_type"] == expected["event_type"] and
                        abs((tracked["timestamp"] - expected["timestamp"]).total_seconds()) < 5)
                ]
                
                if not matching_tracked:
                    validation_results["missing_events"].append(expected)
                else:
                    # Check quantity accuracy
                    tracked_event = matching_tracked[0]
                    if abs(tracked_event["quantity"] - expected["quantity"]) > 0.001:
                        validation_results["quantity_discrepancies"].append({
                            "event_type": expected["event_type"],
                            "expected_quantity": expected["quantity"],
                            "tracked_quantity": tracked_event["quantity"],
                            "difference": tracked_event["quantity"] - expected["quantity"]
                        })
            
            # Calculate accuracy rate
            accurate_events = len(expected_events) - len(validation_results["missing_events"]) - len(validation_results["quantity_discrepancies"])
            if len(expected_events) > 0:
                validation_results["accuracy_rate"] = (accurate_events / len(expected_events)) * 100
            
            return validation_results
            
        except Exception as e:
            return {
                "error": str(e),
                "accuracy_rate": 0
            }
    
    async def cleanup(self):
        """Clean up billing resources."""
        try:
            if self.usage_tracker:
                await self.usage_tracker.shutdown()
            if self.billing_engine:
                await self.billing_engine.shutdown()
            if self.invoice_generator:
                await self.invoice_generator.shutdown()
            if self.payment_processor:
                await self.payment_processor.shutdown()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def billing_manager():
    """Create billing accuracy manager for testing."""
    manager = BillingAccuracyManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
async def test_usage_tracking_accuracy(billing_manager):
    """Test accuracy of usage event tracking."""
    user_id = "usage_accuracy_user"
    tier = BillingTier.MID
    
    # Define expected usage events
    expected_events = [
        {"type": "api_call", "quantity": 1.0, "timestamp": datetime.utcnow()},
        {"type": "llm_request", "quantity": 5.0, "timestamp": datetime.utcnow()},
        {"type": "api_call", "quantity": 2.0, "timestamp": datetime.utcnow()}
    ]
    
    # Track events
    for event in expected_events:
        result = await billing_manager.track_usage_event(
            user_id, tier, event["type"], event["quantity"]
        )
        assert result["tracked"] is True
    
    # Validate tracking accuracy
    validation = await billing_manager.validate_usage_accuracy(user_id, expected_events)
    
    assert validation["accuracy_rate"] >= 98.0
    assert len(validation["missing_events"]) == 0
    assert len(validation["quantity_discrepancies"]) == 0


@pytest.mark.asyncio
async def test_billing_calculation_accuracy(billing_manager):
    """Test accuracy of billing calculations."""
    user_id = "billing_calc_user"
    tier = BillingTier.ENTERPRISE
    
    # Track usage events
    test_events = [
        {"type": "api_call", "quantity": 100.0},
        {"type": "llm_request", "quantity": 50.0}
    ]
    
    for event in test_events:
        await billing_manager.track_usage_event(
            user_id, tier, event["type"], event["quantity"]
        )
    
    # Calculate billing
    start_date = datetime.utcnow() - timedelta(hours=1)
    end_date = datetime.utcnow() + timedelta(hours=1)
    
    billing_result = await billing_manager.calculate_billing_for_period(
        user_id, start_date, end_date
    )
    
    assert billing_result["success"] is True
    assert billing_result["total_amount"] > 0
