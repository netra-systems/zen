"""Payment Processor for handling payments and transactions."""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from uuid import uuid4


class PaymentMethod(Enum):
    """Payment method types."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    CRYPTO = "crypto"
    WALLET = "wallet"


class PaymentStatus(Enum):
    """Payment status types."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIAL_REFUND = "partial_refund"


@dataclass
class PaymentDetails:
    """Payment method details."""
    method: PaymentMethod
    card_last_four: Optional[str] = None
    bank_name: Optional[str] = None
    account_last_four: Optional[str] = None
    paypal_email: Optional[str] = None
    wallet_address: Optional[str] = None
    expiry_month: Optional[int] = None
    expiry_year: Optional[int] = None
    is_default: bool = False


@dataclass
class PaymentTransaction:
    """Payment transaction record."""
    transaction_id: str
    user_id: str
    bill_id: str
    amount: Decimal
    currency: str
    payment_method: PaymentMethod
    status: PaymentStatus
    created_at: datetime
    processed_at: Optional[datetime] = None
    gateway_reference: Optional[str] = None
    gateway_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    refund_amount: Decimal = Decimal("0.00")
    metadata: Optional[Dict[str, Any]] = None


class PaymentGateway:
    """Mock payment gateway for processing payments."""
    
    def __init__(self, name: str, success_rate: float = 0.95):
        """Initialize payment gateway with configurable success rate."""
        self.name = name
        self.success_rate = success_rate
        self.processing_delay = 0.1  # Simulated processing delay
    
    async def process_payment(self, amount: Decimal, payment_details: PaymentDetails,
                            transaction_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Process payment through gateway."""
        # Simulate processing delay
        await asyncio.sleep(self.processing_delay)
        
        # Simulate success/failure based on success rate
        import random
        success = random.random() < self.success_rate
        
        if success:
            response = {
                "status": "success",
                "gateway_reference": f"{self.name}_{transaction_id}_{int(time.time())}",
                "authorization_code": f"AUTH_{random.randint(100000, 999999)}",
                "amount_charged": float(amount),
                "currency": "USD",
                "gateway": self.name
            }
        else:
            response = {
                "status": "failed",
                "error_code": "DECLINED",
                "error_message": "Payment was declined by the issuing bank",
                "gateway": self.name
            }
        
        return success, response
    
    async def refund_payment(self, gateway_reference: str, 
                           amount: Decimal) -> Tuple[bool, Dict[str, Any]]:
        """Process refund through gateway."""
        await asyncio.sleep(self.processing_delay)
        
        # Simulate refund success (higher rate than payments)
        import random
        success = random.random() < 0.98
        
        if success:
            response = {
                "status": "success",
                "refund_reference": f"REF_{gateway_reference}_{int(time.time())}",
                "amount_refunded": float(amount),
                "gateway": self.name
            }
        else:
            response = {
                "status": "failed",
                "error_code": "REFUND_FAILED",
                "error_message": "Unable to process refund",
                "gateway": self.name
            }
        
        return success, response


class PaymentProcessor:
    """Main payment processor for handling all payment operations."""
    
    def __init__(self):
        """Initialize payment processor."""
        self.transactions: Dict[str, PaymentTransaction] = {}
        self.user_payment_methods: Dict[str, List[PaymentDetails]] = {}
        
        # Initialize payment gateways
        self.gateways = {
            "stripe": PaymentGateway("stripe", 0.96),
            "paypal": PaymentGateway("paypal", 0.94),
            "square": PaymentGateway("square", 0.95)
        }
        
        self.enabled = True
        
        # Statistics
        self.stats = {
            "total_transactions": 0,
            "successful_payments": 0,
            "failed_payments": 0,
            "total_amount_processed": Decimal("0.00"),
            "refunds_processed": 0,
            "refund_amount": Decimal("0.00"),
            "transactions_by_method": {},
            "transactions_by_status": {status.value: 0 for status in PaymentStatus}
        }
    
    async def process_payment(self, user_id: str, bill_id: str, amount: Decimal,
                            payment_method: PaymentMethod, 
                            payment_details: Optional[PaymentDetails] = None) -> PaymentTransaction:
        """Process a payment for a bill."""
        if not self.enabled:
            raise RuntimeError("Payment processor is disabled")
        
        # Generate transaction ID
        transaction_id = str(uuid4())
        
        # Create transaction record
        transaction = PaymentTransaction(
            transaction_id=transaction_id,
            user_id=user_id,
            bill_id=bill_id,
            amount=amount,
            currency="USD",
            payment_method=payment_method,
            status=PaymentStatus.PENDING,
            created_at=datetime.now(timezone.utc)
        )
        
        # Store transaction
        self.transactions[transaction_id] = transaction
        
        # Update stats
        self.stats["total_transactions"] += 1
        self.stats["transactions_by_status"][PaymentStatus.PENDING.value] += 1
        
        method_key = payment_method.value
        self.stats["transactions_by_method"][method_key] = (
            self.stats["transactions_by_method"].get(method_key, 0) + 1
        )
        
        try:
            # Update status to processing
            transaction.status = PaymentStatus.PROCESSING
            self.stats["transactions_by_status"][PaymentStatus.PENDING.value] -= 1
            self.stats["transactions_by_status"][PaymentStatus.PROCESSING.value] += 1
            
            # Get payment details
            if not payment_details:
                payment_details = await self._get_user_payment_method(user_id, payment_method)
            
            if not payment_details:
                raise ValueError(f"No payment method found for {payment_method.value}")
            
            # Select gateway based on payment method
            gateway = self._select_gateway(payment_method)
            
            # Process payment
            success, gateway_response = await gateway.process_payment(
                amount, payment_details, transaction_id
            )
            
            # Update transaction
            transaction.processed_at = datetime.now(timezone.utc)
            transaction.gateway_response = gateway_response
            
            if success:
                transaction.status = PaymentStatus.COMPLETED
                transaction.gateway_reference = gateway_response.get("gateway_reference")
                
                # Update stats
                self.stats["successful_payments"] += 1
                self.stats["total_amount_processed"] += amount
            else:
                transaction.status = PaymentStatus.FAILED
                transaction.error_message = gateway_response.get("error_message")
                
                # Update stats
                self.stats["failed_payments"] += 1
            
            # Update status counts
            self.stats["transactions_by_status"][PaymentStatus.PROCESSING.value] -= 1
            self.stats["transactions_by_status"][transaction.status.value] += 1
            
        except Exception as e:
            # Handle processing error
            transaction.status = PaymentStatus.FAILED
            transaction.error_message = str(e)
            transaction.processed_at = datetime.now(timezone.utc)
            
            # Update stats
            self.stats["failed_payments"] += 1
            self.stats["transactions_by_status"][PaymentStatus.PROCESSING.value] -= 1
            self.stats["transactions_by_status"][PaymentStatus.FAILED.value] += 1
        
        return transaction
    
    async def refund_payment(self, transaction_id: str, 
                           refund_amount: Optional[Decimal] = None) -> bool:
        """Process a refund for a completed payment."""
        if transaction_id not in self.transactions:
            return False
        
        transaction = self.transactions[transaction_id]
        
        if transaction.status != PaymentStatus.COMPLETED:
            return False
        
        # Default to full refund
        if refund_amount is None:
            refund_amount = transaction.amount - transaction.refund_amount
        
        # Validate refund amount
        if refund_amount <= 0 or (transaction.refund_amount + refund_amount) > transaction.amount:
            return False
        
        # Get gateway
        gateway = self._select_gateway(transaction.payment_method)
        
        try:
            # Process refund
            success, gateway_response = await gateway.refund_payment(
                transaction.gateway_reference, refund_amount
            )
            
            if success:
                # Update transaction
                transaction.refund_amount += refund_amount
                
                if transaction.refund_amount >= transaction.amount:
                    transaction.status = PaymentStatus.REFUNDED
                else:
                    transaction.status = PaymentStatus.PARTIAL_REFUND
                
                # Update stats
                self.stats["refunds_processed"] += 1
                self.stats["refund_amount"] += refund_amount
                
                return True
        
        except Exception:
            pass
        
        return False
    
    async def add_payment_method(self, user_id: str, 
                               payment_details: PaymentDetails) -> bool:
        """Add payment method for user."""
        if user_id not in self.user_payment_methods:
            self.user_payment_methods[user_id] = []
        
        # If this is set as default, unset other defaults
        if payment_details.is_default:
            for method in self.user_payment_methods[user_id]:
                method.is_default = False
        
        self.user_payment_methods[user_id].append(payment_details)
        return True
    
    async def get_user_payment_methods(self, user_id: str) -> List[PaymentDetails]:
        """Get payment methods for user."""
        return self.user_payment_methods.get(user_id, [])
    
    async def get_transaction(self, transaction_id: str) -> Optional[PaymentTransaction]:
        """Get transaction by ID."""
        return self.transactions.get(transaction_id)
    
    async def get_user_transactions(self, user_id: str, 
                                  status_filter: Optional[PaymentStatus] = None) -> List[PaymentTransaction]:
        """Get transactions for a user."""
        user_transactions = [
            tx for tx in self.transactions.values() 
            if tx.user_id == user_id
        ]
        
        if status_filter:
            user_transactions = [
                tx for tx in user_transactions 
                if tx.status == status_filter
            ]
        
        # Sort by creation date (newest first)
        return sorted(user_transactions, key=lambda t: t.created_at, reverse=True)
    
    async def _get_user_payment_method(self, user_id: str, 
                                     method_type: PaymentMethod) -> Optional[PaymentDetails]:
        """Get user's payment method of specified type."""
        user_methods = self.user_payment_methods.get(user_id, [])
        
        # Try to find default method of this type
        for method in user_methods:
            if method.method == method_type and method.is_default:
                return method
        
        # Fallback to first method of this type
        for method in user_methods:
            if method.method == method_type:
                return method
        
        return None
    
    def _select_gateway(self, payment_method: PaymentMethod) -> PaymentGateway:
        """Select appropriate gateway for payment method."""
        if payment_method == PaymentMethod.PAYPAL:
            return self.gateways["paypal"]
        elif payment_method in [PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD]:
            return self.gateways["stripe"]
        else:
            return self.gateways["square"]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get payment processor statistics."""
        total_tx = self.stats["total_transactions"]
        success_rate = self.stats["successful_payments"] / max(total_tx, 1)
        
        return {
            **self.stats,
            "total_amount_processed_float": float(self.stats["total_amount_processed"]),
            "refund_amount_float": float(self.stats["refund_amount"]),
            "success_rate": success_rate,
            "enabled": self.enabled,
            "gateways_available": len(self.gateways)
        }
    
    def get_supported_methods(self) -> List[str]:
        """Get list of supported payment methods."""
        return [method.value for method in PaymentMethod]
    
    def disable(self) -> None:
        """Disable payment processor."""
        self.enabled = False
    
    def enable(self) -> None:
        """Enable payment processor."""
        self.enabled = True
