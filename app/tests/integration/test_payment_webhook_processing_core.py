"""Core Tests - Split from test_payment_webhook_processing.py

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
