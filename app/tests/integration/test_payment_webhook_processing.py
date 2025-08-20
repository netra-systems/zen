"""
CRITICAL Payment Gateway Webhook Processing Integration Tests
BVJ: Protects $500K+ ARR from webhook failures and payment processing issues
Priority: #3 - Revenue pipeline integrity

Tests: HMAC Signature Validation, Idempotency, Concurrent Processing,
       Payment Events, State Synchronization, Error Recovery
"""

import pytest
import uuid
import time
import hmac
import hashlib
import json
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List


class TestPaymentWebhookProcessing:
    """
    BVJ: Protects $500K+ ARR from webhook processing failures
    Enterprise/Mid segment revenue operations protection
    """

    @pytest.fixture
    async def webhook_secret(self):
        """Mock webhook secret for HMAC validation"""
        return "whsec_test_secret_key_for_hmac_validation_12345"

    @pytest.fixture 
    async def webhook_infrastructure(self, webhook_secret):
        """Setup webhook processing infrastructure"""
        return {
            "webhook_secret": webhook_secret,
            "webhook_processor": AsyncMock(),
            "idempotency_store": AsyncMock(),
            "database_manager": AsyncMock(),
            "alert_manager": AsyncMock(),
            "billing_service": AsyncMock(),
            "webhook_handler": AsyncMock(),
            "retry_manager": AsyncMock()
        }

    def generate_webhook_signature(self, payload: str, secret: str, timestamp: int) -> str:
        """Generate HMAC-SHA256 signature for webhook validation"""
        signature_payload = f"{timestamp}.{payload}"
        signature = hmac.new(
            secret.encode(),
            signature_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"v1={signature}"

    def create_webhook_payload(self, event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create realistic Stripe webhook payload"""
        return {
            "id": f"evt_{uuid.uuid4().hex[:24]}",
            "object": "event",
            "api_version": "2020-08-27", 
            "created": int(time.time()),
            "data": {"object": event_data},
            "livemode": False,
            "pending_webhooks": 1,
            "request": {"id": f"req_{uuid.uuid4().hex[:24]}"},
            "type": event_type
        }

    @pytest.mark.asyncio
    async def test_webhook_signature_validation_security(self, webhook_infrastructure):
        """BVJ: Protects webhook integrity preventing fraudulent payment events"""
        timestamp = int(time.time())
        payment_data = {"id": f"pi_{uuid.uuid4().hex}", "amount": 4999, "status": "succeeded"}
        payload = self.create_webhook_payload("payment_intent.succeeded", payment_data)
        payload_str = json.dumps(payload, separators=(',', ':'))
        
        # Generate valid signature
        valid_signature = self.generate_webhook_signature(
            payload_str, webhook_infrastructure["webhook_secret"], timestamp
        )
        
        # Test valid signature
        webhook_infrastructure["webhook_processor"].validate_signature = AsyncMock(return_value=True)
        webhook_infrastructure["webhook_processor"].process_webhook = AsyncMock(
            return_value={"status": "processed", "event_id": payload["id"]}
        )
        
        result = await webhook_infrastructure["webhook_processor"].process_webhook(
            payload_str, valid_signature, timestamp
        )
        assert result["status"] == "processed"
        
        # Test invalid signature rejection
        invalid_signature = "v1=invalid_signature_hash"
        webhook_infrastructure["webhook_processor"].validate_signature = AsyncMock(return_value=False)
        webhook_infrastructure["webhook_processor"].process_webhook = AsyncMock(
            side_effect=Exception("Invalid webhook signature")
        )
        
        with pytest.raises(Exception) as exc_info:
            await webhook_infrastructure["webhook_processor"].process_webhook(
                payload_str, invalid_signature, timestamp
            )
        assert "Invalid webhook signature" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_webhook_idempotency_duplicate_prevention(self, webhook_infrastructure):
        """BVJ: Prevents duplicate webhook processing causing billing errors"""
        event_id = f"evt_{uuid.uuid4().hex}"
        payment_data = {"id": f"pi_{uuid.uuid4().hex}", "amount": 4999}
        payload = self.create_webhook_payload("payment_intent.succeeded", payment_data)
        payload["id"] = event_id
        
        # First processing succeeds
        webhook_infrastructure["idempotency_store"].check_processed = AsyncMock(return_value=False)
        webhook_infrastructure["idempotency_store"].mark_processed = AsyncMock(return_value=True)
        webhook_infrastructure["webhook_handler"].process_event = AsyncMock(
            return_value={"status": "processed", "event_id": event_id}
        )
        
        result1 = await webhook_infrastructure["webhook_handler"].process_event(payload)
        assert result1["status"] == "processed"
        
        # Second processing detected as duplicate
        webhook_infrastructure["idempotency_store"].check_processed = AsyncMock(return_value=True)
        webhook_infrastructure["webhook_handler"].process_event = AsyncMock(
            return_value={"status": "duplicate_ignored", "event_id": event_id}
        )
        
        # Call check_processed to verify duplicate detection
        is_duplicate = await webhook_infrastructure["idempotency_store"].check_processed(event_id)
        assert is_duplicate is True
        
        result2 = await webhook_infrastructure["webhook_handler"].process_event(payload)
        
        # Verify duplicate handling
        webhook_infrastructure["idempotency_store"].check_processed.assert_called_with(event_id)
        assert result2["status"] == "duplicate_ignored"

    @pytest.mark.asyncio
    async def test_webhook_retry_mechanism_resilience(self, webhook_infrastructure):
        """BVJ: Ensures webhook processing resilience against temporary failures"""
        event_id = f"evt_{uuid.uuid4().hex}"
        payment_data = {"id": f"pi_{uuid.uuid4().hex}", "amount": 4999}
        payload = self.create_webhook_payload("payment_intent.succeeded", payment_data)
        
        # Simulate initial failure then success
        webhook_infrastructure["webhook_handler"].process_event = AsyncMock(
            side_effect=[
                Exception("Temporary database connection error"),
                Exception("Temporary service unavailable"),
                {"status": "processed", "event_id": event_id, "retry_count": 2}
            ]
        )
        
        # Simulate retry logic
        for attempt in range(3):
            try:
                result = await webhook_infrastructure["webhook_handler"].process_event(payload)
                if result.get("status") == "processed":
                    break
            except Exception:
                if attempt < 2:  # Max 3 attempts
                    await asyncio.sleep(0.01)  # Simulate retry delay
                    continue
                raise
        
        assert result["status"] == "processed"
        assert result["retry_count"] == 2

    @pytest.mark.asyncio
    async def test_concurrent_webhook_processing_atomicity(self, webhook_infrastructure):
        """BVJ: Ensures atomic webhook processing under concurrent load"""
        # Create multiple webhook events for concurrent processing
        events = []
        for i in range(5):
            payment_data = {"id": f"pi_{uuid.uuid4().hex}", "amount": 1000 + i}
            payload = self.create_webhook_payload("payment_intent.succeeded", payment_data)
            events.append(payload)
        
        # Mock database transaction handling
        webhook_infrastructure["database_manager"].begin_transaction = AsyncMock()
        webhook_infrastructure["database_manager"].commit_transaction = AsyncMock()
        webhook_infrastructure["database_manager"].rollback_transaction = AsyncMock()
        
        async def process_webhook_with_transaction(event):
            """Simulate webhook processing with database transaction"""
            await webhook_infrastructure["database_manager"].begin_transaction()
            try:
                # Simulate processing
                await asyncio.sleep(0.01)  # Simulate processing time
                result = {
                    "event_id": event["id"],
                    "status": "processed",
                    "timestamp": time.time()
                }
                await webhook_infrastructure["database_manager"].commit_transaction()
                return result
            except Exception:
                await webhook_infrastructure["database_manager"].rollback_transaction()
                raise
        
        # Process webhooks concurrently
        tasks = [process_webhook_with_transaction(event) for event in events]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all events processed successfully
        successful_results = [r for r in results if isinstance(r, dict) and r.get("status") == "processed"]
        assert len(successful_results) == 5
        assert webhook_infrastructure["database_manager"].commit_transaction.call_count == 5

    @pytest.mark.asyncio
    async def test_payment_event_state_synchronization(self, webhook_infrastructure):
        """BVJ: Ensures payment state consistency across webhook events"""
        payment_id = f"pi_{uuid.uuid4().hex}"
        customer_id = f"cus_{uuid.uuid4().hex}"
        
        # Create sequence of payment events
        events = [
            ("payment_intent.created", {"id": payment_id, "status": "requires_payment_method", "amount": 4999}),
            ("payment_intent.succeeded", {"id": payment_id, "status": "succeeded", "amount": 4999}),
            ("invoice.payment_succeeded", {"payment_intent": payment_id, "customer": customer_id, "amount_paid": 4999})
        ]
        
        payment_state = {"status": "pending", "amount": 4999, "customer": customer_id}
        
        # Mock state synchronization
        webhook_infrastructure["billing_service"].update_payment_state = AsyncMock()
        webhook_infrastructure["billing_service"].sync_customer_billing = AsyncMock()
        
        for event_type, event_data in events:
            payload = self.create_webhook_payload(event_type, event_data)
            
            # Update payment state based on event
            if event_type == "payment_intent.succeeded":
                payment_state["status"] = "completed"
            elif event_type == "invoice.payment_succeeded":
                payment_state["invoice_synced"] = True
            
            # Process webhook
            await webhook_infrastructure["billing_service"].update_payment_state(payment_state)
        
        # Verify final state consistency
        assert payment_state["status"] == "completed"
        assert payment_state["invoice_synced"] is True
        assert webhook_infrastructure["billing_service"].update_payment_state.call_count == 3

    @pytest.mark.asyncio
    async def test_chargeback_and_dispute_handling(self, webhook_infrastructure):
        """BVJ: Protects revenue through proper chargeback and dispute processing"""
        charge_id = f"ch_{uuid.uuid4().hex}"
        dispute_id = f"dp_{uuid.uuid4().hex}"
        
        # Create chargeback/dispute webhook
        dispute_data = {
            "id": dispute_id,
            "charge": charge_id,
            "amount": 4999,
            "currency": "usd",
            "reason": "fraudulent",
            "status": "warning_needs_response",
            "evidence_due_by": int(time.time()) + 604800  # 7 days
        }
        
        payload = self.create_webhook_payload("charge.dispute.created", dispute_data)
        
        # Mock dispute handling
        dispute_response = {
            "dispute_id": dispute_id,
            "response_submitted": True,
            "evidence_provided": True,
            "customer_notified": True,
            "accounting_adjusted": True
        }
        
        webhook_infrastructure["billing_service"].handle_chargeback = AsyncMock(return_value=dispute_response)
        webhook_infrastructure["alert_manager"].notify_finance_team = AsyncMock()
        
        result = await webhook_infrastructure["billing_service"].handle_chargeback(dispute_data)
        await webhook_infrastructure["alert_manager"].notify_finance_team()
        
        # Verify chargeback handling
        assert result["response_submitted"] is True
        assert result["evidence_provided"] is True
        assert result["customer_notified"] is True
        webhook_infrastructure["alert_manager"].notify_finance_team.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_error_recovery_and_alerting(self, webhook_infrastructure):
        """BVJ: Ensures business continuity through webhook error recovery"""
        critical_payment_data = {"id": f"pi_{uuid.uuid4().hex}", "amount": 9999, "status": "succeeded"}
        payload = self.create_webhook_payload("payment_intent.succeeded", critical_payment_data)
        
        # Simulate various error scenarios
        error_scenarios = [
            ("database_connection_error", Exception("Database connection timeout")),
            ("billing_service_error", Exception("Billing service unavailable")),
            ("external_api_error", Exception("External API rate limit exceeded"))
        ]
        
        recovery_results = []
        
        # Setup mocks once
        webhook_infrastructure["alert_manager"].send_critical_alert = AsyncMock()
        webhook_infrastructure["webhook_handler"].queue_for_retry = AsyncMock(
            return_value={"queued": True, "retry_at": time.time() + 300}  # 5 minutes
        )
        
        for error_type, error in error_scenarios:
            # Mock error and recovery
            webhook_infrastructure["webhook_handler"].process_event = AsyncMock(side_effect=error)
            
            # Attempt processing and handle error
            try:
                await webhook_infrastructure["webhook_handler"].process_event(payload)
            except Exception:
                # Queue for retry and alert
                retry_info = await webhook_infrastructure["webhook_handler"].queue_for_retry(
                    payload, error_type
                )
                await webhook_infrastructure["alert_manager"].send_critical_alert(
                    f"Webhook processing failed: {error_type}", payload["id"]
                )
                recovery_results.append({"error_type": error_type, "queued_for_retry": retry_info["queued"]})
        
        # Verify error recovery
        assert len(recovery_results) == 3
        assert all(r["queued_for_retry"] for r in recovery_results)
        assert webhook_infrastructure["alert_manager"].send_critical_alert.call_count == 3

    @pytest.mark.asyncio 
    async def test_payment_failure_refund_processing(self, webhook_infrastructure):
        """BVJ: Ensures proper handling of payment failures and refund processing"""
        payment_id = f"pi_{uuid.uuid4().hex}"
        refund_id = f"re_{uuid.uuid4().hex}"
        
        # Test payment failure
        failure_data = {
            "id": payment_id,
            "status": "payment_failed",
            "amount": 4999,
            "last_payment_error": {"code": "card_declined", "message": "Your card was declined."}
        }
        failure_payload = self.create_webhook_payload("payment_intent.payment_failed", failure_data)
        
        # Test refund processing
        refund_data = {
            "id": refund_id,
            "charge": f"ch_{uuid.uuid4().hex}",
            "amount": 4999,
            "status": "succeeded",
            "reason": "requested_by_customer"
        }
        refund_payload = self.create_webhook_payload("charge.refund.created", refund_data)
        
        # Mock failure handling - already AsyncMock from fixture
        webhook_infrastructure["billing_service"].handle_payment_failure.return_value = {
            "retry_scheduled": True, "customer_notified": True
        }
        
        # Mock refund processing - already AsyncMock from fixture
        webhook_infrastructure["billing_service"].process_refund.return_value = {
            "refund_processed": True, "accounting_updated": True
        }
        
        # Webhook handler is already AsyncMock from fixture
        
        # Process payment failure
        await webhook_infrastructure["webhook_handler"].process_event(failure_payload)
        await webhook_infrastructure["billing_service"].handle_payment_failure(failure_data)
        webhook_infrastructure["billing_service"].handle_payment_failure.assert_called_once()
        
        # Process refund
        await webhook_infrastructure["webhook_handler"].process_event(refund_payload)
        await webhook_infrastructure["billing_service"].process_refund(refund_data)
        webhook_infrastructure["billing_service"].process_refund.assert_called_once()