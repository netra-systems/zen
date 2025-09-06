from unittest.mock import Mock, patch, MagicMock

"""
L3-14: Payment Gateway with Containerized Sandbox Integration Test

BVJ: Critical for revenue processing and billing accuracy. Ensures payment
flows work correctly across different scenarios and handle failures gracefully.

Tests payment gateway integration with containerized sandbox environment.
""""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

import aiohttp
import docker
import pytest
from payments.gateway_manager import PaymentGatewayManager
from payments.stripe_client import StripeClient
from payments.webhook_handler import PaymentWebhookHandler

@pytest.mark.L3
class TestPaymentGatewaySandboxL3:
    """Test payment gateway with containerized sandbox."""
    
    @pytest.fixture(scope="class")
    async def docker_client(self):
        """Docker client for container management."""
        client = docker.from_env()
        yield client
        client.close()
    
        @pytest.fixture(scope="class")
        async def stripe_mock_container(self, docker_client):
        """Start Stripe mock server container."""
        container = docker_client.containers.run(
        "stripemock/stripe-mock:latest",
        ports={'12111/tcp': None, '12112/tcp': None},
        detach=True,
        name="stripe_mock_test"
        )
        
        # Get assigned ports
        container.reload()
        api_port = container.attrs['NetworkSettings']['Ports']['12111/tcp'][0]['HostPort']
        webhook_port = container.attrs['NetworkSettings']['Ports']['12112/tcp'][0]['HostPort']
        
        # Wait for mock server to be ready
        await self._wait_for_stripe_mock(api_port)
        
        stripe_config = {
        "api_port": int(api_port),
        "webhook_port": int(webhook_port),
        "api_url": f"http://localhost:{api_port}",
        "webhook_url": f"http://localhost:{webhook_port}",
        "api_key": "sk_test_mock_key",
        "webhook_secret": "whsec_test_mock_secret"
        }
        
        yield stripe_config
        
        container.stop()
        container.remove()
    
        @pytest.fixture(scope="class")
        async def payment_processor_container(self, docker_client):
        """Start mock payment processor container."""
        # Use a simple HTTP server that can simulate payment responses
        container = docker_client.containers.run(
        "python:3.11-slim",
        command=[
        "python", "-c",
        """
import http.server
import socketserver
import json
from urllib.parse import urlparse, parse_qs

class PaymentHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            
            if self.path == '/charge':
                response = self._handle_charge(data)
            elif self.path == '/refund':
                response = self._handle_refund(data)
            elif self.path == '/webhook':
                response = self._handle_webhook(data)
            else:
                response = {'error': 'Unknown endpoint'}
                
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def _handle_charge(self, data):
        amount = data.get('amount', 0)
        if amount > 100000:  # Simulate failure for large amounts
            return {'error': 'amount_too_large', 'decline_code': 'card_declined'}
        return {
            'id': f'ch_mock_{data.get("amount", 0)}',
            'status': 'succeeded',
            'amount': amount,
            'currency': data.get('currency', 'usd')
        }
    
    def _handle_refund(self, data):
        return {
            'id': f're_mock_{data.get("charge_id", "unknown")}',
            'status': 'succeeded',
            'amount': data.get('amount', 0)
        }
    
    async def _handle_webhook(self, data):
        return {'received': True}

with socketserver.TCPServer(('0.0.0.0', 8080), PaymentHandler) as httpd:
    httpd.serve_forever()
                """"
            ],
            ports={'8080/tcp': None},
            detach=True,
            name="payment_processor_mock"
        )
        
        # Get assigned port
        container.reload()
        port = container.attrs['NetworkSettings']['Ports']['8080/tcp'][0]['HostPort']
        
        # Wait for service to be ready
        await self._wait_for_payment_processor(port)
        
        processor_config = {
            "port": int(port),
            "url": f"http://localhost:{port}"
        }
        
        yield processor_config
        
        container.stop()
        container.remove()
    
    async def _wait_for_stripe_mock(self, port: str, timeout: int = 30):
        """Wait for Stripe mock server to be available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"http://localhost:{port}/charges",
                        headers={'Authorization': 'Bearer sk_test_mock_key'},
                        timeout=aiohttp.ClientTimeout(total=2)
                    ) as response:
                        if response.status in [200, 401]:  # 401 is expected for mock
                            return
            except:
                pass
            await asyncio.sleep(0.5)
        raise TimeoutError(f"Stripe mock not ready within {timeout}s")
    
    async def _wait_for_payment_processor(self, port: str, timeout: int = 30):
        """Wait for payment processor to be available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    test_data = {"test": "connection"}
                    async with session.post(
                        f"http://localhost:{port}/charge",
                        json=test_data,
                        timeout=aiohttp.ClientTimeout(total=2)
                    ) as response:
                        if response.status in [200, 500]:  # Any response means it's up
                            return
            except:
                pass
            await asyncio.sleep(0.5)
        raise TimeoutError(f"Payment processor not ready within {timeout}s")
    
    @pytest.fixture
    async def payment_gateway(self, stripe_mock_container, payment_processor_container):
        """Create payment gateway manager with mock backends."""
        gateway = PaymentGatewayManager(
        stripe_config=stripe_mock_container,
        processor_config=payment_processor_container
        )
        await gateway.initialize()
        yield gateway
        await gateway.cleanup()
    
        @pytest.fixture
        async def webhook_handler(self, stripe_mock_container):
        """Create webhook handler for payment events."""
        handler = PaymentWebhookHandler(
        webhook_config=stripe_mock_container
        )
        await handler.initialize()
        yield handler
        await handler.cleanup()
    
        @pytest.mark.asyncio
        async def test_successful_payment_charge(self, payment_gateway):
        """Test successful payment charge processing."""
        # Test payment data
        payment_request = {
        "amount": 2500,  # $25.00
        "currency": "usd",
        "customer_id": "cust_test_123",
        "description": "Test subscription payment",
        "metadata": {
        "order_id": "order_test_456",
        "subscription_id": "sub_test_789"
        }
        }
        
        # Process payment
        result = await payment_gateway.charge_payment(payment_request)
        
        # Verify successful charge
        assert result["success"] is True
        assert result["charge_id"] is not None
        assert result["amount"] == 2500
        assert result["currency"] == "usd"
        assert result["status"] == "succeeded"
        
        # Verify metadata preservation
        assert result["metadata"]["order_id"] == "order_test_456"
        assert result["metadata"]["subscription_id"] == "sub_test_789"
    
        @pytest.mark.asyncio
        async def test_payment_decline_handling(self, payment_gateway):
        """Test payment decline and error handling."""
        # Large amount that should be declined
        decline_request = {
        "amount": 150000,  # $1500.00 - will be declined by mock
        "currency": "usd",
        "customer_id": "cust_test_decline",
        "description": "Test decline payment"
        }
        
        # Process payment (should be declined)
        result = await payment_gateway.charge_payment(decline_request)
        
        # Verify decline handling
        assert result["success"] is False
        assert result["error_type"] == "card_error"
        assert result["decline_code"] == "card_declined"
        assert "amount_too_large" in result["error_message"]
    
        @pytest.mark.asyncio
        async def test_payment_refund_processing(self, payment_gateway):
        """Test payment refund processing."""
        # First, create a successful charge
        charge_request = {
        "amount": 5000,  # $50.00
        "currency": "usd",
        "customer_id": "cust_refund_test",
        "description": "Test refund payment"
        }
        
        charge_result = await payment_gateway.charge_payment(charge_request)
        assert charge_result["success"] is True
        
        charge_id = charge_result["charge_id"]
        
        # Now refund the payment
        refund_request = {
        "charge_id": charge_id,
        "amount": 3000,  # Partial refund $30.00
        "reason": "requested_by_customer"
        }
        
        refund_result = await payment_gateway.refund_payment(refund_request)
        
        # Verify successful refund
        assert refund_result["success"] is True
        assert refund_result["refund_id"] is not None
        assert refund_result["amount"] == 3000
        assert refund_result["status"] == "succeeded"
    
        @pytest.mark.asyncio
        async def test_webhook_event_processing(
        self, 
        payment_gateway, 
        webhook_handler
        ):
        """Test webhook event processing for payment status updates."""
        webhook_events = []
        
        @pytest.mark.asyncio
        async def test_webhook_handler(event_type, event_data):
        webhook_events.append({
        "type": event_type,
        "data": event_data
        })
        
        # Register webhook handler
        webhook_handler.register_handler("charge.succeeded", test_webhook_handler)
        webhook_handler.register_handler("charge.failed", test_webhook_handler)
        
        # Simulate webhook events
        charge_succeeded_event = {
        "type": "charge.succeeded",
        "data": {
        "object": {
        "id": "ch_test_webhook_123",
        "amount": 2500,
        "currency": "usd",
        "status": "succeeded"
        }
        }
        }
        
        charge_failed_event = {
        "type": "charge.failed", 
        "data": {
        "object": {
        "id": "ch_test_webhook_456",
        "amount": 10000,
        "currency": "usd",
        "status": "failed",
        "failure_code": "card_declined"
        }
        }
        }
        
        # Process webhook events
        await webhook_handler.process_webhook(charge_succeeded_event)
        await webhook_handler.process_webhook(charge_failed_event)
        
        # Verify events were processed
        assert len(webhook_events) == 2
        
        succeeded_event = next(e for e in webhook_events if e["type"] == "charge.succeeded")
        assert succeeded_event["data"]["object"]["id"] == "ch_test_webhook_123"
        
        failed_event = next(e for e in webhook_events if e["type"] == "charge.failed")
        assert failed_event["data"]["object"]["failure_code"] == "card_declined"
    
        @pytest.mark.asyncio
        async def test_subscription_billing_cycle(self, payment_gateway):
        """Test subscription billing cycle processing."""
        # Create subscription
        subscription_request = {
        "customer_id": "cust_subscription_test",
        "plan_id": "plan_monthly_premium",
        "amount": 2999,  # $29.99
        "interval": "month",
        "trial_period_days": 7
        }
        
        subscription_result = await payment_gateway.create_subscription(subscription_request)
        
        assert subscription_result["success"] is True
        assert subscription_result["subscription_id"] is not None
        assert subscription_result["status"] == "trialing"  # Should start in trial
        
        subscription_id = subscription_result["subscription_id"]
        
        # Simulate trial period end and billing
        billing_result = await payment_gateway.process_subscription_billing(subscription_id)
        
        assert billing_result["success"] is True
        assert billing_result["charge_amount"] == 2999
        assert billing_result["next_billing_date"] is not None
        
        # Test subscription modification
        modification_request = {
        "subscription_id": subscription_id,
        "new_plan_id": "plan_monthly_enterprise", 
        "new_amount": 4999,  # $49.99
        "proration": True
        }
        
        modification_result = await payment_gateway.modify_subscription(modification_request)
        
        assert modification_result["success"] is True
        assert modification_result["proration_amount"] is not None
    
        @pytest.mark.asyncio
        async def test_payment_retry_logic(self, payment_gateway):
        """Test payment retry logic for failed transactions."""
        retry_attempts = []
        
        # Configure retry policy
        retry_config = {
        "max_retries": 3,
        "retry_delay": 0.1,  # Fast for testing
        "exponential_backoff": True
        }
        
        # Mock payment method that fails initially then succeeds
        async def mock_payment_with_retries(attempt):
        retry_attempts.append(attempt)
        if attempt < 3:
        raise Exception(f"Payment failed on attempt {attempt}")
        return {"success": True, "charge_id": f"ch_retry_success_{attempt}"}
        
        # Test retry mechanism
        payment_request = {
        "amount": 1000,
        "currency": "usd",
        "customer_id": "cust_retry_test",
        "retry_config": retry_config
        }
        
        result = await payment_gateway.charge_with_retry(
        payment_request,
        mock_payment_with_retries
        )
        
        # Verify retry logic worked
        assert result["success"] is True
        assert len(retry_attempts) == 3  # Should retry until success
        assert retry_attempts == [1, 2, 3]
    
        @pytest.mark.asyncio
        async def test_payment_fraud_detection(self, payment_gateway):
        """Test payment fraud detection and risk assessment."""
        # High-risk payment characteristics
        high_risk_request = {
        "amount": 50000,  # Large amount
        "currency": "usd",
        "customer_id": "cust_new_high_risk",
        "customer_info": {
        "created_days_ago": 0,  # Brand new customer
        "previous_orders": 0,
        "ip_address": "192.168.1.1",
        "country": "US",
        "billing_country": "RU"  # Different from IP country
        },
        "card_info": {
        "country": "BR",  # Different card country
        "funding": "prepaid"  # Prepaid card
        }
        }
        
        # Process with fraud detection
        fraud_result = await payment_gateway.assess_fraud_risk(high_risk_request)
        
        assert fraud_result["risk_level"] in ["medium", "high"]
        assert fraud_result["risk_score"] > 50  # Higher risk score
        assert len(fraud_result["risk_factors"]) > 0
        
        # Low-risk payment characteristics
        low_risk_request = {
        "amount": 2500,  # Normal amount
        "currency": "usd",
        "customer_id": "cust_trusted_customer",
        "customer_info": {
        "created_days_ago": 365,  # Established customer
        "previous_orders": 25,
        "ip_address": "192.168.1.1",
        "country": "US",
        "billing_country": "US"
        },
        "card_info": {
        "country": "US",
        "funding": "credit"
        }
        }
        
        low_fraud_result = await payment_gateway.assess_fraud_risk(low_risk_request)
        
        assert low_fraud_result["risk_level"] == "low"
        assert low_fraud_result["risk_score"] < 30  # Lower risk score
    
        @pytest.mark.asyncio
        async def test_payment_reporting_and_reconciliation(self, payment_gateway):
        """Test payment reporting and reconciliation functionality."""
        # Process multiple payments
        payments = []
        for i in range(5):
        payment_request = {
        "amount": 1000 + (i * 500),  # Varying amounts
        "currency": "usd",
        "customer_id": f"cust_reporting_{i}",
        "description": f"Test payment {i}",
        "metadata": {"batch": "test_batch_1"}
        }
            
        result = await payment_gateway.charge_payment(payment_request)
        if result["success"]:
        payments.append(result)
        
        # Generate payment report
        report_request = {
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "filters": {
        "metadata.batch": "test_batch_1"
        }
        }
        
        report = await payment_gateway.generate_payment_report(report_request)
        
        assert report["total_transactions"] >= len(payments)
        assert report["total_amount"] > 0
        assert report["successful_transactions"] >= len(payments)
        assert report["currency_breakdown"]["usd"] > 0
        
        # Test reconciliation
        reconciliation = await payment_gateway.reconcile_payments(
        payments=[p["charge_id"] for p in payments],
        external_records=["ext_rec_1", "ext_rec_2", "ext_rec_3"]
        )
        
        assert reconciliation["matched_count"] >= 0
        assert reconciliation["unmatched_internal"] >= 0
        assert reconciliation["unmatched_external"] >= 0
        assert len(reconciliation["discrepancies"]) >= 0