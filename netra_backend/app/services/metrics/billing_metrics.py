"""
Billing metrics collection service.
Collects and aggregates billing-related metrics for cost tracking and analysis.
"""

import asyncio
from shared.logging.unified_logging_ssot import get_logger
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union

logger = get_logger(__name__)


class BillingEventType(Enum):
    """Types of billing events."""
    LLM_USAGE = "llm_usage"
    API_CALL = "api_call"
    STORAGE_USAGE = "storage_usage"
    COMPUTE_TIME = "compute_time"
    DATA_TRANSFER = "data_transfer"
    SUBSCRIPTION_CHARGE = "subscription_charge"


@dataclass
class BillingEvent:
    """Represents a billable event."""
    id: str
    event_type: BillingEventType
    user_id: str
    timestamp: datetime
    amount: Decimal
    currency: str = "USD"
    metadata: Dict[str, Any] = field(default_factory=dict)
    processed: bool = False


@dataclass
class UsageMetrics:
    """Usage metrics for a specific period."""
    period_start: datetime
    period_end: datetime
    total_amount: Decimal
    event_count: int
    events_by_type: Dict[BillingEventType, int]
    amounts_by_type: Dict[BillingEventType, Decimal]
    unique_users: int


@dataclass
class UserBillingMetrics:
    """Billing metrics for a specific user."""
    user_id: str
    total_spent: Decimal
    current_period_spent: Decimal
    event_count: int
    last_activity: datetime
    subscription_tier: Optional[str] = None


class BillingMetricsCollector:
    """
    Service for collecting and aggregating billing metrics.
    Tracks usage, costs, and billing events across the platform.
    """
    
    def __init__(self):
        self.events: List[BillingEvent] = []
        self.user_metrics: Dict[str, UserBillingMetrics] = {}
        self.initialized = False
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> bool:
        """Initialize the billing metrics collector."""
        try:
            self.initialized = True
            logger.info("Billing metrics collector initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize billing metrics collector: {e}")
            return False
    
    async def record_event(
        self,
        event_type: BillingEventType,
        user_id: str,
        amount: Union[Decimal, float, str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a new billing event.
        
        Args:
            event_type: Type of billing event
            user_id: ID of the user associated with the event
            amount: Cost amount for the event
            metadata: Additional event metadata
            
        Returns:
            Event ID
        """
        if not self.initialized:
            raise RuntimeError("Billing metrics collector not initialized")
        
        async with self._lock:
            event_id = f"billing_{datetime.now(timezone.utc).timestamp()}"
            
            event = BillingEvent(
                id=event_id,
                event_type=event_type,
                user_id=user_id,
                timestamp=datetime.now(timezone.utc),
                amount=Decimal(str(amount)),
                metadata=metadata or {}
            )
            
            self.events.append(event)
            await self._update_user_metrics(event)
            
            logger.debug(f"Recorded billing event {event_id}: {event_type.value} for user {user_id}")
            return event_id
    
    async def _update_user_metrics(self, event: BillingEvent) -> None:
        """Update user metrics with new event data."""
        user_id = event.user_id
        
        if user_id not in self.user_metrics:
            self.user_metrics[user_id] = UserBillingMetrics(
                user_id=user_id,
                total_spent=Decimal("0"),
                current_period_spent=Decimal("0"),
                event_count=0,
                last_activity=event.timestamp
            )
        
        metrics = self.user_metrics[user_id]
        metrics.total_spent += event.amount
        metrics.current_period_spent += event.amount
        metrics.event_count += 1
        metrics.last_activity = event.timestamp
    
    async def get_usage_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        user_id: Optional[str] = None
    ) -> UsageMetrics:
        """
        Get usage metrics for a specific time period.
        
        Args:
            start_time: Start of the period
            end_time: End of the period
            user_id: Optional user ID to filter by
            
        Returns:
            UsageMetrics for the period
        """
        events = [
            e for e in self.events
            if start_time <= e.timestamp <= end_time and
            (user_id is None or e.user_id == user_id)
        ]
        
        total_amount = sum(e.amount for e in events)
        events_by_type = {}
        amounts_by_type = {}
        
        for event_type in BillingEventType:
            type_events = [e for e in events if e.event_type == event_type]
            events_by_type[event_type] = len(type_events)
            amounts_by_type[event_type] = sum(e.amount for e in type_events)
        
        unique_users = len(set(e.user_id for e in events))
        
        return UsageMetrics(
            period_start=start_time,
            period_end=end_time,
            total_amount=total_amount,
            event_count=len(events),
            events_by_type=events_by_type,
            amounts_by_type=amounts_by_type,
            unique_users=unique_users
        )
    
    async def get_user_metrics(self, user_id: str) -> Optional[UserBillingMetrics]:
        """Get billing metrics for a specific user."""
        return self.user_metrics.get(user_id)
    
    async def get_top_users(self, limit: int = 10) -> List[UserBillingMetrics]:
        """Get top users by total spending."""
        sorted_users = sorted(
            self.user_metrics.values(),
            key=lambda x: x.total_spent,
            reverse=True
        )
        return sorted_users[:limit]
    
    async def get_daily_metrics(
        self,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get daily metrics for the specified number of days."""
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days)
        
        daily_metrics = []
        
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())
            
            day_events = [
                e for e in self.events
                if day_start <= e.timestamp <= day_end
            ]
            
            daily_metrics.append({
                "date": current_date.isoformat(),
                "total_amount": float(sum(e.amount for e in day_events)),
                "event_count": len(day_events),
                "unique_users": len(set(e.user_id for e in day_events))
            })
        
        return daily_metrics
    
    async def calculate_user_costs(
        self,
        user_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Calculate detailed costs for a user."""
        user_events = [e for e in self.events if e.user_id == user_id]
        
        if start_time:
            user_events = [e for e in user_events if e.timestamp >= start_time]
        if end_time:
            user_events = [e for e in user_events if e.timestamp <= end_time]
        
        costs_by_type = {}
        for event_type in BillingEventType:
            type_events = [e for e in user_events if e.event_type == event_type]
            costs_by_type[event_type.value] = {
                "total_amount": float(sum(e.amount for e in type_events)),
                "event_count": len(type_events)
            }
        
        return {
            "user_id": user_id,
            "total_amount": float(sum(e.amount for e in user_events)),
            "total_events": len(user_events),
            "costs_by_type": costs_by_type,
            "period": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None
            }
        }
    
    async def get_revenue_metrics(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Get revenue metrics for business reporting."""
        events = [
            e for e in self.events
            if start_time <= e.timestamp <= end_time
        ]
        
        total_revenue = sum(e.amount for e in events)
        
        # Revenue by event type
        revenue_by_type = {}
        for event_type in BillingEventType:
            type_events = [e for e in events if e.event_type == event_type]
            revenue_by_type[event_type.value] = float(sum(e.amount for e in type_events))
        
        # Active users
        active_users = len(set(e.user_id for e in events))
        
        # Average revenue per user
        arpu = float(total_revenue / active_users) if active_users > 0 else 0
        
        return {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "total_revenue": float(total_revenue),
            "revenue_by_type": revenue_by_type,
            "active_users": active_users,
            "average_revenue_per_user": arpu,
            "total_events": len(events)
        }
    
    async def export_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        format: str = "json"
    ) -> Dict[str, Any]:
        """Export metrics data for external analysis."""
        usage_metrics = await self.get_usage_metrics(start_time, end_time)
        revenue_metrics = await self.get_revenue_metrics(start_time, end_time)
        
        return {
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "usage_metrics": {
                "total_amount": float(usage_metrics.total_amount),
                "event_count": usage_metrics.event_count,
                "unique_users": usage_metrics.unique_users,
                "events_by_type": {k.value: v for k, v in usage_metrics.events_by_type.items()},
                "amounts_by_type": {k.value: float(v) for k, v in usage_metrics.amounts_by_type.items()}
            },
            "revenue_metrics": revenue_metrics
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of billing metrics collector."""
        recent_events = [
            e for e in self.events
            if e.timestamp >= datetime.now(timezone.utc) - timedelta(hours=1)
        ]
        
        return {
            "initialized": self.initialized,
            "total_events": len(self.events),
            "recent_events": len(recent_events),
            "tracked_users": len(self.user_metrics),
            "oldest_event": self.events[0].timestamp.isoformat() if self.events else None,
            "newest_event": self.events[-1].timestamp.isoformat() if self.events else None
        }


# Global instance
billing_metrics_collector = BillingMetricsCollector()