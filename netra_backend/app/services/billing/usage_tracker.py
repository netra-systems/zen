"""Usage Tracker for billing and cost management."""

import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class UsageType(Enum):
    """Types of usage that can be tracked."""
    API_CALL = "api_call"
    LLM_TOKENS = "llm_tokens"
    STORAGE = "storage"
    COMPUTE = "compute"
    BANDWIDTH = "bandwidth"
    WEBSOCKET_CONNECTION = "websocket_connection"
    AGENT_EXECUTION = "agent_execution"


@dataclass
class UsageEvent:
    """Individual usage event."""
    user_id: str
    usage_type: UsageType
    quantity: float
    unit: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    cost: float = 0.0
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if isinstance(self.usage_type, str):
            self.usage_type = UsageType(self.usage_type)


class UsageTracker:
    """Tracks usage events for billing purposes."""
    
    def __init__(self):
        """Initialize usage tracker."""
        # In-memory storage for demo/test purposes
        self.usage_events: List[UsageEvent] = []
        self.user_totals: Dict[str, Dict[str, float]] = {}
        self.enabled = True
        
        # Rate limits and pricing
        self.rate_limits = {
            UsageType.API_CALL: {"limit": 1000, "window": 3600},  # 1000 per hour
            UsageType.LLM_TOKENS: {"limit": 100000, "window": 3600},  # 100k tokens per hour
            UsageType.WEBSOCKET_CONNECTION: {"limit": 10, "window": 60}  # 10 connections per minute
        }
        
        self.pricing = {
            UsageType.API_CALL: 0.001,  # $0.001 per call
            UsageType.LLM_TOKENS: 0.00002,  # $0.02 per 1k tokens
            UsageType.STORAGE: 0.023,  # $0.023 per GB-month
            UsageType.COMPUTE: 0.10,  # $0.10 per CPU hour
            UsageType.BANDWIDTH: 0.09,  # $0.09 per GB
            UsageType.WEBSOCKET_CONNECTION: 0.0001,  # $0.0001 per connection-minute
            UsageType.AGENT_EXECUTION: 0.005  # $0.005 per execution
        }
    
    async def track_usage(self, user_id: str, usage_type: UsageType, 
                         quantity: float, unit: str = "count", 
                         metadata: Optional[Dict[str, Any]] = None) -> UsageEvent:
        """Track a usage event."""
        if not self.enabled:
            return None
        
        # Calculate cost
        unit_price = self.pricing.get(usage_type, 0.0)
        cost = quantity * unit_price
        
        # Create usage event
        event = UsageEvent(
            user_id=user_id,
            usage_type=usage_type,
            quantity=quantity,
            unit=unit,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {},
            cost=cost
        )
        
        # Store event
        self.usage_events.append(event)
        
        # Update user totals
        if user_id not in self.user_totals:
            self.user_totals[user_id] = {}
        
        usage_key = usage_type.value
        if usage_key not in self.user_totals[user_id]:
            self.user_totals[user_id][usage_key] = 0.0
        
        self.user_totals[user_id][usage_key] += quantity
        
        # Store in database if available
        await self._persist_event(event)
        
        return event
    
    async def get_user_usage(self, user_id: str, 
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Get usage summary for a user."""
        # Filter events by time range
        filtered_events = []
        for event in self.usage_events:
            if event.user_id != user_id:
                continue
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue
            filtered_events.append(event)
        
        # Aggregate usage
        usage_summary = {}
        total_cost = 0.0
        
        for event in filtered_events:
            usage_type = event.usage_type.value
            if usage_type not in usage_summary:
                usage_summary[usage_type] = {
                    "quantity": 0.0,
                    "cost": 0.0,
                    "events": 0
                }
            
            usage_summary[usage_type]["quantity"] += event.quantity
            usage_summary[usage_type]["cost"] += event.cost
            usage_summary[usage_type]["events"] += 1
            total_cost += event.cost
        
        return {
            "user_id": user_id,
            "period": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None
            },
            "usage_summary": usage_summary,
            "total_cost": total_cost,
            "total_events": len(filtered_events)
        }
    
    async def check_rate_limit(self, user_id: str, usage_type: UsageType) -> Dict[str, Any]:
        """Check if user is within rate limits."""
        if usage_type not in self.rate_limits:
            return {"allowed": True, "remaining": float('inf')}
        
        limit_config = self.rate_limits[usage_type]
        window_seconds = limit_config["window"]
        max_quantity = limit_config["limit"]
        
        # Get recent events within window
        cutoff_time = datetime.now(timezone.utc).timestamp() - window_seconds
        recent_usage = 0.0
        
        for event in self.usage_events:
            if (event.user_id == user_id and 
                event.usage_type == usage_type and
                event.timestamp.timestamp() > cutoff_time):
                recent_usage += event.quantity
        
        remaining = max(0, max_quantity - recent_usage)
        allowed = recent_usage < max_quantity
        
        return {
            "allowed": allowed,
            "remaining": remaining,
            "limit": max_quantity,
            "window_seconds": window_seconds,
            "current_usage": recent_usage,
            "reset_time": cutoff_time + window_seconds
        }
    
    async def get_usage_analytics(self, start_time: Optional[datetime] = None,
                                end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Get usage analytics across all users."""
        # Filter events
        filtered_events = []
        for event in self.usage_events:
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue
            filtered_events.append(event)
        
        # Calculate analytics
        total_events = len(filtered_events)
        total_cost = sum(event.cost for event in filtered_events)
        unique_users = len(set(event.user_id for event in filtered_events))
        
        # Usage by type
        usage_by_type = {}
        for event in filtered_events:
            usage_type = event.usage_type.value
            if usage_type not in usage_by_type:
                usage_by_type[usage_type] = {
                    "events": 0,
                    "quantity": 0.0,
                    "cost": 0.0
                }
            
            usage_by_type[usage_type]["events"] += 1
            usage_by_type[usage_type]["quantity"] += event.quantity
            usage_by_type[usage_type]["cost"] += event.cost
        
        # Top users
        user_costs = {}
        for event in filtered_events:
            if event.user_id not in user_costs:
                user_costs[event.user_id] = 0.0
            user_costs[event.user_id] += event.cost
        
        top_users = sorted(user_costs.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "period": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None
            },
            "totals": {
                "events": total_events,
                "cost": total_cost,
                "unique_users": unique_users
            },
            "usage_by_type": usage_by_type,
            "top_users": [{
                "user_id": user_id,
                "cost": cost
            } for user_id, cost in top_users]
        }
    
    async def _persist_event(self, event: UsageEvent) -> None:
        """Persist event to database (if available)."""
        try:
            # Try to save to database
            # This would integrate with the actual database layer
            pass
        except Exception:
            # Fallback to in-memory storage (already done)
            pass
    
    def get_pricing(self) -> Dict[str, float]:
        """Get current pricing for all usage types."""
        return {usage_type.value: price for usage_type, price in self.pricing.items()}
    
    def update_pricing(self, pricing_updates: Dict[str, float]) -> None:
        """Update pricing for usage types."""
        for usage_type_str, price in pricing_updates.items():
            try:
                usage_type = UsageType(usage_type_str)
                self.pricing[usage_type] = price
            except ValueError:
                continue
    
    def get_rate_limits(self) -> Dict[str, Dict[str, Any]]:
        """Get current rate limits."""
        return {usage_type.value: config for usage_type, config in self.rate_limits.items()}
    
    def update_rate_limits(self, rate_limit_updates: Dict[str, Dict[str, Any]]) -> None:
        """Update rate limits."""
        for usage_type_str, config in rate_limit_updates.items():
            try:
                usage_type = UsageType(usage_type_str)
                self.rate_limits[usage_type] = config
            except ValueError:
                continue
    
    def get_stats(self) -> Dict[str, Any]:
        """Get tracker statistics."""
        return {
            "enabled": self.enabled,
            "total_events": len(self.usage_events),
            "total_users": len(self.user_totals),
            "total_cost": sum(event.cost for event in self.usage_events),
            "usage_types_tracked": len(self.pricing),
            "rate_limits_configured": len(self.rate_limits)
        }
    
    def clear_data(self) -> None:
        """Clear all tracking data (for testing)."""
        self.usage_events.clear()
        self.user_totals.clear()
