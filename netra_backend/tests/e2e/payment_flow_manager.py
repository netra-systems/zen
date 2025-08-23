"""
Payment Flow Manager for E2E Testing

Provides utilities for testing payment flows and operations.
"""

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MockPaymentProvider:
    """Mock payment provider for testing."""
    
    def __init__(self, name: str = "test_provider"):
        self.name = name
        self.payments = {}
        self.should_fail = False
    
    async def process_payment(self, payment_id: str, amount: float, currency: str = "USD") -> Dict[str, Any]:
        """Process a payment through the mock provider."""
        if self.should_fail:
            return {
                "payment_id": payment_id,
                "status": PaymentStatus.FAILED,
                "error": "Mock payment failure",
                "timestamp": datetime.utcnow()
            }
        
        payment_record = {
            "payment_id": payment_id,
            "amount": amount,
            "currency": currency,
            "status": PaymentStatus.COMPLETED,
            "provider": self.name,
            "timestamp": datetime.utcnow()
        }
        
        self.payments[payment_id] = payment_record
        return payment_record
    
    async def refund_payment(self, payment_id: str) -> Dict[str, Any]:
        """Process a refund for a payment."""
        if payment_id not in self.payments:
            return {
                "payment_id": payment_id,
                "status": "error",
                "error": "Payment not found"
            }
        
        return {
            "payment_id": payment_id,
            "status": "refunded",
            "timestamp": datetime.utcnow()
        }
    
    def set_failure_mode(self, should_fail: bool) -> None:
        """Configure the provider to simulate failures."""
        self.should_fail = should_fail


class PaymentFlowManager:
    """Manages payment flows for E2E testing."""
    
    def __init__(self):
        self.providers = {}
        self.default_provider = None
        self.payment_history = []
        self.initialized = False
    
    async def initialize(self) -> None:
        """Initialize the payment flow manager."""
        # Set up default mock provider
        self.default_provider = MockPaymentProvider("default_test_provider")
        self.providers["default"] = self.default_provider
        self.initialized = True
    
    async def add_provider(self, name: str, provider: MockPaymentProvider) -> None:
        """Add a payment provider."""
        self.providers[name] = provider
    
    async def process_payment_flow(
        self, 
        user_id: str, 
        amount: float, 
        currency: str = "USD",
        provider_name: str = "default"
    ) -> Dict[str, Any]:
        """Process a complete payment flow."""
        if not self.initialized:
            await self.initialize()
        
        provider = self.providers.get(provider_name, self.default_provider)
        payment_id = f"pay_{len(self.payment_history)}_{user_id}"
        
        try:
            result = await provider.process_payment(payment_id, amount, currency)
            
            flow_record = {
                "user_id": user_id,
                "payment_id": payment_id,
                "amount": amount,
                "currency": currency,
                "provider": provider_name,
                "result": result,
                "timestamp": datetime.utcnow()
            }
            
            self.payment_history.append(flow_record)
            return flow_record
            
        except Exception as e:
            error_record = {
                "user_id": user_id,
                "payment_id": payment_id,
                "error": str(e),
                "status": "error",
                "timestamp": datetime.utcnow()
            }
            self.payment_history.append(error_record)
            return error_record
    
    async def get_payment_history(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get payment history, optionally filtered by user."""
        if user_id:
            return [p for p in self.payment_history if p.get("user_id") == user_id]
        return self.payment_history.copy()
    
    async def simulate_webhook(self, payment_id: str, status: str) -> Dict[str, Any]:
        """Simulate a payment webhook notification."""
        webhook_data = {
            "payment_id": payment_id,
            "status": status,
            "timestamp": datetime.utcnow(),
            "webhook_id": f"webhook_{len(self.payment_history)}"
        }
        return webhook_data
    
    async def clear_history(self) -> None:
        """Clear payment history."""
        self.payment_history.clear()
    
    async def shutdown(self) -> None:
        """Shutdown the payment flow manager."""
        self.initialized = False
        self.payment_history.clear()
        self.providers.clear()