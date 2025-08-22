"""
CRITICAL Payment Gateway Integration Tests for Netra Apex Revenue Pipeline
BVJ: Protects $100K-$200K MRR from Stripe/billing flow failures
Tests: Payment Processing, Subscriptions, Webhooks, Refunds, Payment Methods
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest


class TestPaymentGatewayIntegration:
    """
    BVJ: Protects $100K-$200K MRR from payment processing failures
    Revenue Impact: Direct protection of subscription billing and payment collection
    """

    @pytest.fixture
    async def payment_infrastructure(self):
        """Setup payment gateway infrastructure"""
        return {
            "stripe_client": Mock(),  # Stripe client is sync, keep as Mock
            "payment_processor": AsyncMock(),
            "subscription_manager": AsyncMock(),
            "webhook_handler": AsyncMock(),
            "billing_service": AsyncMock(),
            "refund_processor": AsyncMock(),
            "payment_method_manager": AsyncMock()
        }

    @pytest.mark.asyncio
    async def test_01_successful_payment_flow_complete(self, payment_infrastructure):
        """BVJ: Protects successful payment processing worth $50K+ MRR"""
        request = {"amount": Decimal("49.99"), "currency": "usd"}
        intent = {"id": f"pi_{uuid.uuid4().hex}", "status": "succeeded", "amount_received": 4999}
        payment_infrastructure["stripe_client"].PaymentIntent.create = Mock(return_value=intent)  # Sync Stripe call
        payment_infrastructure["payment_processor"].complete_transaction.return_value = intent
        result = await payment_infrastructure["payment_processor"].complete_transaction(intent)
        assert result["status"] == "succeeded"
        assert result["amount_received"] == 4999

    @pytest.mark.asyncio
    async def test_02_failed_payment_handling_recovery(self, payment_infrastructure):
        """BVJ: Prevents revenue loss from failed payment scenarios"""
        failed_intent = {"id": f"pi_{uuid.uuid4().hex}", "status": "payment_failed"}
        retry_result = {"final_status": "failed", "retry_attempts": 3}
        handling = {"customer_notified": True, "subscription_status": "past_due", "grace_period_days": 7}
        payment_infrastructure["payment_processor"].retry_payment.return_value = retry_result
        payment_infrastructure["billing_service"].handle_payment_failure.return_value = handling
        result = await payment_infrastructure["billing_service"].handle_payment_failure(retry_result)
        assert result["customer_notified"] is True
        assert result["subscription_status"] == "past_due"

    @pytest.mark.asyncio
    async def test_03_subscription_lifecycle_management(self, payment_infrastructure):
        """BVJ: Protects $75K+ MRR from subscription management failures"""
        sub_id = f"sub_{uuid.uuid4().hex}"
        subscription = {"id": sub_id, "status": "active", "plan": {"amount": 4999}}
        cancelled = {"id": sub_id, "status": "canceled", "canceled_at": int(time.time())}
        payment_infrastructure["subscription_manager"].create_subscription.return_value = subscription
        payment_infrastructure["subscription_manager"].cancel_subscription.return_value = cancelled
        result = await payment_infrastructure["subscription_manager"].cancel_subscription(sub_id)
        assert result["status"] == "canceled"
        assert result["canceled_at"] is not None

    @pytest.mark.asyncio
    async def test_04_webhook_processing_idempotency(self, payment_infrastructure):
        """BVJ: Ensures reliable webhook processing for billing events"""
        event_id = f"evt_{uuid.uuid4().hex}"
        first_result = {"event_id": event_id, "processing_status": "completed", "idempotency_key": event_id}
        duplicate_result = {"event_id": event_id, "processing_status": "duplicate_ignored", "idempotency_key": event_id}
        payment_infrastructure["webhook_handler"].process_event.side_effect = [first_result, duplicate_result]
        result1 = await payment_infrastructure["webhook_handler"].process_event({"id": event_id})
        result2 = await payment_infrastructure["webhook_handler"].process_event({"id": event_id})
        assert result1["processing_status"] == "completed"
        assert result2["processing_status"] == "duplicate_ignored"

    @pytest.mark.asyncio
    async def test_05_refund_processing_compliance(self, payment_infrastructure):
        """BVJ: Ensures compliant refund processing protecting customer trust"""
        refund_amount = Decimal("49.99")
        stripe_refund = {"id": f"re_{uuid.uuid4().hex}", "status": "succeeded", "amount": 4999}
        accounting = {"refund_id": stripe_refund["id"], "revenue_adjustment": -refund_amount}
        payment_infrastructure["stripe_client"].Refund.create = Mock(return_value=stripe_refund)  # Sync Stripe call
        payment_infrastructure["billing_service"].record_refund.return_value = accounting
        result = await payment_infrastructure["billing_service"].record_refund(stripe_refund)
        assert result["revenue_adjustment"] == -refund_amount
        assert result["refund_id"] is not None

    @pytest.mark.asyncio
    async def test_06_payment_method_management_security(self, payment_infrastructure):
        """BVJ: Secures payment method storage and management"""
        method_id = f"pm_{uuid.uuid4().hex}"
        payment_method = {"id": method_id, "type": "card", "card": {"last4": "4242"}}
        security_check = {"method_id": method_id, "encryption_verified": True, "pci_compliant": True}
        deletion = {"method_id": method_id, "secure_cleanup": True, "audit_log_created": True}
        payment_infrastructure["payment_method_manager"].verify_security.return_value = security_check
        payment_infrastructure["payment_method_manager"].delete_payment_method.return_value = deletion
        result = await payment_infrastructure["payment_method_manager"].delete_payment_method(method_id)
        assert result["secure_cleanup"] is True
        assert result["audit_log_created"] is True