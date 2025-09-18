"""
ClickHouse Billing Helper for E2E Testing

Provides utilities for testing billing operations with ClickHouse.
"""

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


class ClickHouseBillingHelper:
    """Helper for ClickHouse billing operations in E2E tests."""
    
    def __init__(self):
        self.billing_records = []
        self.metrics = {}
        self.initialized = False
    
    async def initialize(self) -> None:
        """Initialize the billing helper."""
        self.initialized = True
    
    async def record_usage(self, user_id: str, usage_type: str, amount: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record usage for billing."""
        record = {
            "user_id": user_id,
            "usage_type": usage_type,
            "amount": amount,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc)
        }
        self.billing_records.append(record)
    
    async def get_usage_summary(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get usage summary for a user in a date range."""
        filtered_records = [
            r for r in self.billing_records 
            if r["user_id"] == user_id and start_date <= r["timestamp"] <= end_date
        ]
        
        total_usage = sum(r["amount"] for r in filtered_records)
        usage_by_type = {}
        for record in filtered_records:
            usage_type = record["usage_type"]
            usage_by_type[usage_type] = usage_by_type.get(usage_type, 0) + record["amount"]
        
        return {
            "user_id": user_id,
            "total_usage": total_usage,
            "usage_by_type": usage_by_type,
            "record_count": len(filtered_records)
        }
    
    async def clear_records(self) -> None:
        """Clear all billing records."""
        self.billing_records.clear()
    
    async def shutdown(self) -> None:
        """Shutdown the billing helper."""
        self.initialized = False
        self.billing_records.clear()