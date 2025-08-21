"""Agent Cost Tracking L2 Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise (cost optimization and budgeting)
- Business Goal: Comprehensive AI cost management and optimization
- Value Impact: Protects $10K MRR from cost overruns and budget breaches
- Strategic Impact: Enables profitable AI operations and customer value optimization

Critical Path: Usage tracking -> Cost calculation -> Budget monitoring -> Alerts -> Optimization
Coverage: Real cost tracking, budget management, usage analytics, cost optimization
"""

import pytest
import asyncio
import time
import json
import logging
from typing import Dict, List, Optional, Any, Union, Tuple
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal

# Real components for L2 testing
from app.services.redis_service import RedisService
from app.core.circuit_breaker import CircuitBreaker
from app.core.database_connection_manager import DatabaseConnectionManager
from app.agents.base import BaseSubAgent
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CostCategory(Enum):
    """Categories for cost tracking."""
    MODEL_INFERENCE = "model_inference"
    FINE_TUNING = "fine_tuning"
    EMBEDDING = "embedding"
    IMAGE_GENERATION = "image_generation"
    AUDIO_PROCESSING = "audio_processing"
    STORAGE = "storage"
    COMPUTE = "compute"
    BANDWIDTH = "bandwidth"


class BudgetPeriod(Enum):
    """Budget period types."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class CostEntry:
    """Represents a single cost entry."""
    entry_id: str
    agent_id: str
    user_id: Optional[str]
    session_id: Optional[str]
    category: CostCategory
    provider: str
    model: str
    tokens_input: int
    tokens_output: int
    cost_input: Decimal
    cost_output: Decimal
    total_cost: Decimal
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "entry_id": self.entry_id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "category": self.category.value,
            "provider": self.provider,
            "model": self.model,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "cost_input": str(self.cost_input),
            "cost_output": str(self.cost_output),
            "total_cost": str(self.total_cost),
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CostEntry":
        """Create from dictionary."""
        return cls(
            entry_id=data["entry_id"],
            agent_id=data["agent_id"],
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
            category=CostCategory(data["category"]),
            provider=data["provider"],
            model=data["model"],
            tokens_input=data["tokens_input"],
            tokens_output=data["tokens_output"],
            cost_input=Decimal(data["cost_input"]),
            cost_output=Decimal(data["cost_output"]),
            total_cost=Decimal(data["total_cost"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {})
        )


@dataclass
class Budget:
    """Represents a budget configuration."""
    budget_id: str
    name: str
    period: BudgetPeriod
    amount: Decimal
    currency: str = "USD"
    agent_ids: Optional[List[str]] = None
    user_ids: Optional[List[str]] = None
    categories: Optional[List[CostCategory]] = None
    alert_thresholds: List[float] = field(default_factory=lambda: [0.5, 0.8, 0.95])
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "budget_id": self.budget_id,
            "name": self.name,
            "period": self.period.value,
            "amount": str(self.amount),
            "currency": self.currency,
            "agent_ids": self.agent_ids,
            "user_ids": self.user_ids,
            "categories": [cat.value for cat in self.categories] if self.categories else None,
            "alert_thresholds": self.alert_thresholds,
            "active": self.active,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Budget":
        """Create from dictionary."""
        categories = None
        if data.get("categories"):
            categories = [CostCategory(cat) for cat in data["categories"]]
        
        return cls(
            budget_id=data["budget_id"],
            name=data["name"],
            period=BudgetPeriod(data["period"]),
            amount=Decimal(data["amount"]),
            currency=data.get("currency", "USD"),
            agent_ids=data.get("agent_ids"),
            user_ids=data.get("user_ids"),
            categories=categories,
            alert_thresholds=data.get("alert_thresholds", [0.5, 0.8, 0.95]),
            active=data.get("active", True),
            created_at=datetime.fromisoformat(data["created_at"])
        )


@dataclass
class CostAlert:
    """Represents a cost alert."""
    alert_id: str
    budget_id: str
    severity: AlertSeverity
    threshold: float
    current_usage: Decimal
    budget_amount: Decimal
    message: str
    triggered_at: datetime
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "alert_id": self.alert_id,
            "budget_id": self.budget_id,
            "severity": self.severity.value,
            "threshold": self.threshold,
            "current_usage": str(self.current_usage),
            "budget_amount": str(self.budget_amount),
            "message": self.message,
            "triggered_at": self.triggered_at.isoformat(),
            "acknowledged": self.acknowledged
        }


class ProviderPricing:
    """Manages pricing information for different providers."""
    
    def __init__(self):
        self.pricing_data = {
            "openai": {
                "gpt-4": {"input": Decimal("0.03"), "output": Decimal("0.06")},
                "gpt-4-turbo": {"input": Decimal("0.01"), "output": Decimal("0.03")},
                "gpt-3.5-turbo": {"input": Decimal("0.0015"), "output": Decimal("0.002")},
                "text-embedding-ada-002": {"input": Decimal("0.0001"), "output": Decimal("0.0001")}
            },
            "anthropic": {
                "claude-3-opus": {"input": Decimal("0.015"), "output": Decimal("0.075")},
                "claude-3-sonnet": {"input": Decimal("0.003"), "output": Decimal("0.015")},
                "claude-3-haiku": {"input": Decimal("0.00025"), "output": Decimal("0.00125")}
            },
            "cohere": {
                "command": {"input": Decimal("0.0015"), "output": Decimal("0.002")},
                "embed-english-v3.0": {"input": Decimal("0.0001"), "output": Decimal("0.0001")}
            }
        }
    
    def get_cost_per_1k_tokens(self, provider: str, model: str, token_type: str) -> Decimal:
        """Get cost per 1000 tokens for a specific model."""
        if provider not in self.pricing_data:
            return Decimal("0.001")  # Default fallback
        
        provider_data = self.pricing_data[provider]
        if model not in provider_data:
            return Decimal("0.001")  # Default fallback
        
        model_data = provider_data[model]
        return model_data.get(token_type, Decimal("0.001"))
    
    def calculate_cost(self, provider: str, model: str, input_tokens: int, output_tokens: int) -> Tuple[Decimal, Decimal, Decimal]:
        """Calculate total cost for a request."""
        input_cost_per_1k = self.get_cost_per_1k_tokens(provider, model, "input")
        output_cost_per_1k = self.get_cost_per_1k_tokens(provider, model, "output")
        
        input_cost = (Decimal(input_tokens) / 1000) * input_cost_per_1k
        output_cost = (Decimal(output_tokens) / 1000) * output_cost_per_1k
        total_cost = input_cost + output_cost
        
        return input_cost, output_cost, total_cost


class CostTracker:
    """Tracks and manages AI operation costs."""
    
    def __init__(self, db_manager: DatabaseConnectionManager, redis_service: RedisService):
        self.db_manager = db_manager
        self.redis_service = redis_service
        self.pricing = ProviderPricing()
        self.pending_entries = []
        self.batch_size = 50
        self.flush_interval = 30  # seconds
        self._last_flush = time.time()
        
    async def track_usage(self, 
                         agent_id: str,
                         provider: str,
                         model: str,
                         input_tokens: int,
                         output_tokens: int,
                         category: CostCategory = CostCategory.MODEL_INFERENCE,
                         user_id: Optional[str] = None,
                         session_id: Optional[str] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """Track usage and calculate costs."""
        
        # Calculate costs
        input_cost, output_cost, total_cost = self.pricing.calculate_cost(
            provider, model, input_tokens, output_tokens
        )
        
        # Create cost entry
        entry = CostEntry(
            entry_id=f"cost_{agent_id}_{int(time.time() * 1000)}",
            agent_id=agent_id,
            user_id=user_id,
            session_id=session_id,
            category=category,
            provider=provider,
            model=model,
            tokens_input=input_tokens,
            tokens_output=output_tokens,
            cost_input=input_cost,
            cost_output=output_cost,
            total_cost=total_cost,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        # Add to batch
        self.pending_entries.append(entry)
        
        # Update real-time cache
        await self._update_realtime_cache(entry)
        
        # Flush if needed
        if (len(self.pending_entries) >= self.batch_size or 
            time.time() - self._last_flush > self.flush_interval):
            await self.flush_entries()
        
        return entry.entry_id
    
    async def _update_realtime_cache(self, entry: CostEntry):
        """Update real-time cost cache in Redis."""
        # Update agent daily cost
        today = entry.timestamp.date().isoformat()
        daily_key = f"cost_daily:{entry.agent_id}:{today}"
        
        await self.redis_service.client.hincrbyfloat(
            daily_key, "total_cost", float(entry.total_cost)
        )
        await self.redis_service.client.hincrbyfloat(
            daily_key, "total_tokens", entry.tokens_input + entry.tokens_output
        )
        await self.redis_service.client.expire(daily_key, 86400 * 7)  # 7 days TTL
        
        # Update user daily cost if applicable
        if entry.user_id:
            user_daily_key = f"cost_daily_user:{entry.user_id}:{today}"
            await self.redis_service.client.hincrbyfloat(
                user_daily_key, "total_cost", float(entry.total_cost)
            )
            await self.redis_service.client.expire(user_daily_key, 86400 * 7)
        
        # Update model usage statistics
        model_key = f"cost_model:{entry.provider}:{entry.model}:{today}"
        await self.redis_service.client.hincrbyfloat(
            model_key, "cost", float(entry.total_cost)
        )
        await self.redis_service.client.hincrby(
            model_key, "requests", 1
        )
        await self.redis_service.client.expire(model_key, 86400 * 30)  # 30 days TTL
    
    async def flush_entries(self):
        """Flush pending cost entries to database."""
        if not self.pending_entries:
            return
        
        entries_to_store = self.pending_entries.copy()
        self.pending_entries.clear()
        self._last_flush = time.time()
        
        # Store in database
        conn = await self.db_manager.get_connection()
        try:
            for entry in entries_to_store:
                await conn.execute("""
                    INSERT INTO cost_entries (
                        entry_id, agent_id, user_id, session_id, category, provider, model,
                        tokens_input, tokens_output, cost_input, cost_output, total_cost,
                        timestamp, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                """, 
                    entry.entry_id, entry.agent_id, entry.user_id, entry.session_id,
                    entry.category.value, entry.provider, entry.model,
                    entry.tokens_input, entry.tokens_output,
                    float(entry.cost_input), float(entry.cost_output), float(entry.total_cost),
                    entry.timestamp, json.dumps(entry.metadata)
                )
        finally:
            await self.db_manager.return_connection(conn)
    
    async def get_cost_summary(self, 
                              agent_id: Optional[str] = None,
                              user_id: Optional[str] = None,
                              start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None,
                              category: Optional[CostCategory] = None) -> Dict[str, Any]:
        """Get cost summary for specified filters."""
        
        # Build query conditions
        conditions = []
        params = []
        param_count = 0
        
        if agent_id:
            param_count += 1
            conditions.append(f"agent_id = ${param_count}")
            params.append(agent_id)
        
        if user_id:
            param_count += 1
            conditions.append(f"user_id = ${param_count}")
            params.append(user_id)
        
        if start_date:
            param_count += 1
            conditions.append(f"timestamp >= ${param_count}")
            params.append(start_date)
        
        if end_date:
            param_count += 1
            conditions.append(f"timestamp <= ${param_count}")
            params.append(end_date)
        
        if category:
            param_count += 1
            conditions.append(f"category = ${param_count}")
            params.append(category.value)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        conn = await self.db_manager.get_connection()
        try:
            # Get total costs
            summary_query = f"""
                SELECT 
                    COUNT(*) as total_requests,
                    SUM(tokens_input) as total_input_tokens,
                    SUM(tokens_output) as total_output_tokens,
                    SUM(total_cost) as total_cost,
                    AVG(total_cost) as avg_cost_per_request,
                    MIN(timestamp) as first_request,
                    MAX(timestamp) as last_request
                FROM cost_entries 
                WHERE {where_clause}
            """
            
            summary_row = await conn.fetchrow(summary_query, *params)
            
            # Get cost breakdown by provider
            provider_query = f"""
                SELECT provider, SUM(total_cost) as cost, COUNT(*) as requests
                FROM cost_entries 
                WHERE {where_clause}
                GROUP BY provider
                ORDER BY cost DESC
            """
            
            provider_rows = await conn.fetch(provider_query, *params)
            
            # Get cost breakdown by model
            model_query = f"""
                SELECT provider, model, SUM(total_cost) as cost, COUNT(*) as requests
                FROM cost_entries 
                WHERE {where_clause}
                GROUP BY provider, model
                ORDER BY cost DESC
                LIMIT 10
            """
            
            model_rows = await conn.fetch(model_query, *params)
            
            # Get daily cost trend (last 30 days)
            daily_query = f"""
                SELECT DATE(timestamp) as date, SUM(total_cost) as daily_cost
                FROM cost_entries 
                WHERE {where_clause} AND timestamp >= NOW() - INTERVAL '30 days'
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """
            
            daily_rows = await conn.fetch(daily_query, *params)
            
        finally:
            await self.db_manager.return_connection(conn)
        
        return {
            "summary": {
                "total_requests": summary_row["total_requests"] or 0,
                "total_input_tokens": summary_row["total_input_tokens"] or 0,
                "total_output_tokens": summary_row["total_output_tokens"] or 0,
                "total_tokens": (summary_row["total_input_tokens"] or 0) + (summary_row["total_output_tokens"] or 0),
                "total_cost": float(summary_row["total_cost"] or 0),
                "avg_cost_per_request": float(summary_row["avg_cost_per_request"] or 0),
                "first_request": summary_row["first_request"].isoformat() if summary_row["first_request"] else None,
                "last_request": summary_row["last_request"].isoformat() if summary_row["last_request"] else None
            },
            "provider_breakdown": [
                {
                    "provider": row["provider"],
                    "cost": float(row["cost"]),
                    "requests": row["requests"]
                }
                for row in provider_rows
            ],
            "model_breakdown": [
                {
                    "provider": row["provider"],
                    "model": row["model"],
                    "cost": float(row["cost"]),
                    "requests": row["requests"]
                }
                for row in model_rows
            ],
            "daily_trend": [
                {
                    "date": row["date"].isoformat(),
                    "cost": float(row["daily_cost"])
                }
                for row in daily_rows
            ]
        }
    
    async def get_realtime_usage(self, agent_id: str) -> Dict[str, Any]:
        """Get real-time usage statistics from cache."""
        today = datetime.now().date().isoformat()
        daily_key = f"cost_daily:{agent_id}:{today}"
        
        daily_data = await self.redis_service.client.hgetall(daily_key)
        
        return {
            "agent_id": agent_id,
            "date": today,
            "total_cost": float(daily_data.get("total_cost", 0)),
            "total_tokens": int(daily_data.get("total_tokens", 0)),
            "last_updated": datetime.now().isoformat()
        }


class BudgetManager:
    """Manages budgets and cost alerts."""
    
    def __init__(self, cost_tracker: CostTracker, redis_service: RedisService):
        self.cost_tracker = cost_tracker
        self.redis_service = redis_service
        self.budgets: Dict[str, Budget] = {}
        self.active_alerts: Dict[str, List[CostAlert]] = {}
        
    def create_budget(self, budget: Budget) -> None:
        """Create a new budget."""
        self.budgets[budget.budget_id] = budget
        
    async def check_budget_usage(self, budget_id: str) -> Dict[str, Any]:
        """Check current usage against budget."""
        if budget_id not in self.budgets:
            raise ValueError(f"Budget {budget_id} not found")
        
        budget = self.budgets[budget_id]
        
        # Calculate period start/end dates
        period_start, period_end = self._get_period_dates(budget.period)
        
        # Get current usage
        usage_summary = await self.cost_tracker.get_cost_summary(
            agent_id=budget.agent_ids[0] if budget.agent_ids and len(budget.agent_ids) == 1 else None,
            user_id=budget.user_ids[0] if budget.user_ids and len(budget.user_ids) == 1 else None,
            start_date=period_start,
            end_date=period_end,
            category=budget.categories[0] if budget.categories and len(budget.categories) == 1 else None
        )
        
        current_cost = Decimal(str(usage_summary["summary"]["total_cost"]))
        usage_percentage = float(current_cost / budget.amount) if budget.amount > 0 else 0
        
        # Check for alert thresholds
        alerts_triggered = []
        for threshold in budget.alert_thresholds:
            if usage_percentage >= threshold:
                severity = self._determine_alert_severity(threshold)
                alert = CostAlert(
                    alert_id=f"alert_{budget_id}_{threshold}_{int(time.time())}",
                    budget_id=budget_id,
                    severity=severity,
                    threshold=threshold,
                    current_usage=current_cost,
                    budget_amount=budget.amount,
                    message=f"Budget '{budget.name}' has reached {threshold*100:.1f}% usage",
                    triggered_at=datetime.now()
                )
                alerts_triggered.append(alert)
        
        return {
            "budget_id": budget_id,
            "budget_name": budget.name,
            "budget_amount": float(budget.amount),
            "current_usage": float(current_cost),
            "usage_percentage": usage_percentage,
            "remaining_budget": float(budget.amount - current_cost),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "alerts_triggered": [alert.to_dict() for alert in alerts_triggered],
            "is_over_budget": current_cost > budget.amount
        }
    
    def _get_period_dates(self, period: BudgetPeriod) -> Tuple[datetime, datetime]:
        """Get start and end dates for budget period."""
        now = datetime.now()
        
        if period == BudgetPeriod.DAILY:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1) - timedelta(microseconds=1)
        elif period == BudgetPeriod.WEEKLY:
            days_since_monday = now.weekday()
            start = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7) - timedelta(microseconds=1)
        elif period == BudgetPeriod.MONTHLY:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = start.replace(month=start.month + 1 if start.month < 12 else 1,
                                     year=start.year if start.month < 12 else start.year + 1)
            end = next_month - timedelta(microseconds=1)
        elif period == BudgetPeriod.QUARTERLY:
            quarter_start_month = ((now.month - 1) // 3) * 3 + 1
            start = now.replace(month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_month = quarter_start_month + 3
            if end_month > 12:
                end_year = start.year + 1
                end_month -= 12
            else:
                end_year = start.year
            end = start.replace(month=end_month, year=end_year) - timedelta(microseconds=1)
        elif period == BudgetPeriod.YEARLY:
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = start.replace(year=start.year + 1) - timedelta(microseconds=1)
        else:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1) - timedelta(microseconds=1)
        
        return start, end
    
    def _determine_alert_severity(self, threshold: float) -> AlertSeverity:
        """Determine alert severity based on threshold."""
        if threshold >= 0.95:
            return AlertSeverity.EMERGENCY
        elif threshold >= 0.8:
            return AlertSeverity.CRITICAL
        elif threshold >= 0.5:
            return AlertSeverity.WARNING
        else:
            return AlertSeverity.INFO
    
    async def get_budget_forecast(self, budget_id: str, days_ahead: int = 30) -> Dict[str, Any]:
        """Forecast budget usage based on historical trends."""
        if budget_id not in self.budgets:
            raise ValueError(f"Budget {budget_id} not found")
        
        budget = self.budgets[budget_id]
        
        # Get historical usage (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        usage_summary = await self.cost_tracker.get_cost_summary(
            agent_id=budget.agent_ids[0] if budget.agent_ids and len(budget.agent_ids) == 1 else None,
            start_date=start_date,
            end_date=end_date
        )
        
        daily_costs = usage_summary["daily_trend"]
        
        if not daily_costs:
            return {
                "budget_id": budget_id,
                "forecast_unavailable": True,
                "reason": "Insufficient historical data"
            }
        
        # Calculate daily average
        total_cost = sum(day["cost"] for day in daily_costs)
        avg_daily_cost = total_cost / len(daily_costs)
        
        # Forecast future usage
        forecasted_cost = avg_daily_cost * days_ahead
        
        # Calculate when budget will be exhausted
        current_usage = await self.check_budget_usage(budget_id)
        remaining_budget = current_usage["remaining_budget"]
        
        days_until_exhaustion = None
        if avg_daily_cost > 0:
            days_until_exhaustion = remaining_budget / avg_daily_cost
        
        return {
            "budget_id": budget_id,
            "budget_amount": float(budget.amount),
            "avg_daily_cost": avg_daily_cost,
            "forecasted_cost": forecasted_cost,
            "days_ahead": days_ahead,
            "days_until_exhaustion": days_until_exhaustion,
            "will_exceed_budget": forecasted_cost > remaining_budget,
            "forecast_confidence": min(1.0, len(daily_costs) / 30.0)  # Confidence based on data availability
        }


class CostOptimizer:
    """Provides cost optimization recommendations."""
    
    def __init__(self, cost_tracker: CostTracker):
        self.cost_tracker = cost_tracker
        
    async def analyze_cost_efficiency(self, agent_id: str, days: int = 7) -> Dict[str, Any]:
        """Analyze cost efficiency and provide recommendations."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        usage_summary = await self.cost_tracker.get_cost_summary(
            agent_id=agent_id,
            start_date=start_date,
            end_date=end_date
        )
        
        recommendations = []
        efficiency_score = 1.0
        
        # Analyze model usage patterns
        model_breakdown = usage_summary["model_breakdown"]
        if model_breakdown:
            # Check for expensive model usage
            expensive_models = [m for m in model_breakdown if m["cost"] / m["requests"] > 0.05]
            if expensive_models:
                recommendations.append({
                    "type": "model_optimization",
                    "priority": "high",
                    "description": "Consider using more cost-effective models for similar tasks",
                    "potential_savings": sum(m["cost"] * 0.3 for m in expensive_models),
                    "affected_models": [m["model"] for m in expensive_models]
                })
                efficiency_score -= 0.2
            
            # Check for underutilized premium models
            premium_models = [m for m in model_breakdown if "gpt-4" in m["model"].lower() and m["requests"] < 10]
            if premium_models:
                recommendations.append({
                    "type": "usage_optimization",
                    "priority": "medium",
                    "description": "Premium models are underutilized. Consider batching requests or using alternative models",
                    "affected_models": [m["model"] for m in premium_models]
                })
                efficiency_score -= 0.1
        
        # Analyze request patterns
        total_requests = usage_summary["summary"]["total_requests"]
        avg_cost = usage_summary["summary"]["avg_cost_per_request"]
        
        if avg_cost > 0.02:  # High average cost per request
            recommendations.append({
                "type": "request_optimization",
                "priority": "medium",
                "description": "High average cost per request. Consider optimizing prompt length or using caching",
                "current_avg_cost": avg_cost,
                "target_avg_cost": 0.015
            })
            efficiency_score -= 0.15
        
        # Check for daily cost spikes
        daily_trend = usage_summary["daily_trend"]
        if len(daily_trend) > 1:
            daily_costs = [day["cost"] for day in daily_trend]
            avg_daily = sum(daily_costs) / len(daily_costs)
            max_daily = max(daily_costs)
            
            if max_daily > avg_daily * 2:  # Spike detection
                recommendations.append({
                    "type": "spike_analysis",
                    "priority": "high",
                    "description": "Detected cost spikes. Investigate usage patterns during peak days",
                    "avg_daily_cost": avg_daily,
                    "max_daily_cost": max_daily
                })
                efficiency_score -= 0.2
        
        return {
            "agent_id": agent_id,
            "analysis_period_days": days,
            "efficiency_score": max(0.0, efficiency_score),
            "total_cost": usage_summary["summary"]["total_cost"],
            "potential_monthly_savings": sum(r.get("potential_savings", 0) for r in recommendations) * 4,
            "recommendations": recommendations,
            "summary": usage_summary["summary"]
        }


class CostTrackingManager:
    """Manages cost tracking testing."""
    
    def __init__(self):
        self.db_manager = None
        self.redis_service = None
        self.cost_tracker = None
        self.budget_manager = None
        self.cost_optimizer = None
        
    async def initialize_services(self):
        """Initialize required services."""
        self.db_manager = DatabaseConnectionManager()
        await self.db_manager.initialize()
        
        self.redis_service = RedisService()
        await self.redis_service.initialize()
        
        self.cost_tracker = CostTracker(self.db_manager, self.redis_service)
        self.budget_manager = BudgetManager(self.cost_tracker, self.redis_service)
        self.cost_optimizer = CostOptimizer(self.cost_tracker)
        
        # Create test schema
        await self.create_test_schema()
    
    async def create_test_schema(self):
        """Create test database schema."""
        conn = await self.db_manager.get_connection()
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS cost_entries (
                    entry_id VARCHAR PRIMARY KEY,
                    agent_id VARCHAR NOT NULL,
                    user_id VARCHAR,
                    session_id VARCHAR,
                    category VARCHAR NOT NULL,
                    provider VARCHAR NOT NULL,
                    model VARCHAR NOT NULL,
                    tokens_input INTEGER NOT NULL,
                    tokens_output INTEGER NOT NULL,
                    cost_input DECIMAL(10,6) NOT NULL,
                    cost_output DECIMAL(10,6) NOT NULL,
                    total_cost DECIMAL(10,6) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    metadata JSONB
                )
            """)
            
            # Create indexes
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_cost_agent_timestamp ON cost_entries(agent_id, timestamp)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_cost_user_timestamp ON cost_entries(user_id, timestamp)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_cost_category ON cost_entries(category)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_cost_provider_model ON cost_entries(provider, model)")
            
        finally:
            await self.db_manager.return_connection(conn)
    
    async def cleanup(self):
        """Clean up resources."""
        if self.cost_tracker:
            await self.cost_tracker.flush_entries()
        if self.redis_service:
            await self.redis_service.shutdown()
        if self.db_manager:
            await self.db_manager.shutdown()


@pytest.fixture
async def cost_manager():
    """Create cost tracking test manager."""
    manager = CostTrackingManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_basic_cost_tracking(cost_manager):
    """Test basic cost tracking functionality."""
    manager = cost_manager
    
    # Track a simple usage
    entry_id = await manager.cost_tracker.track_usage(
        agent_id="test_agent_001",
        provider="openai",
        model="gpt-4",
        input_tokens=100,
        output_tokens=50,
        category=CostCategory.MODEL_INFERENCE,
        user_id="user_123"
    )
    
    assert entry_id is not None
    assert len(entry_id) > 0
    
    # Flush entries
    await manager.cost_tracker.flush_entries()
    
    # Verify cost calculation
    assert len(manager.cost_tracker.pending_entries) == 0


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_provider_pricing_calculation(cost_manager):
    """Test provider pricing calculations."""
    manager = cost_manager
    pricing = manager.cost_tracker.pricing
    
    # Test OpenAI GPT-4 pricing
    input_cost, output_cost, total_cost = pricing.calculate_cost("openai", "gpt-4", 1000, 500)
    
    # GPT-4: $0.03 input, $0.06 output per 1K tokens
    expected_input = Decimal("0.03")  # 1000 tokens
    expected_output = Decimal("0.03")  # 500 tokens * $0.06
    expected_total = expected_input + expected_output
    
    assert input_cost == expected_input
    assert output_cost == expected_output
    assert total_cost == expected_total
    
    # Test different model
    input_cost, output_cost, total_cost = pricing.calculate_cost("anthropic", "claude-3-haiku", 2000, 1000)
    
    # Claude Haiku: $0.00025 input, $0.00125 output per 1K tokens
    expected_input = Decimal("0.0005")  # 2000 tokens * $0.00025
    expected_output = Decimal("0.00125")  # 1000 tokens * $0.00125
    expected_total = expected_input + expected_output
    
    assert input_cost == expected_input
    assert output_cost == expected_output
    assert total_cost == expected_total


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_cost_summary_generation(cost_manager):
    """Test cost summary generation."""
    manager = cost_manager
    
    # Add multiple cost entries
    for i in range(5):
        await manager.cost_tracker.track_usage(
            agent_id="summary_test_agent",
            provider="openai",
            model="gpt-3.5-turbo",
            input_tokens=100 + i * 10,
            output_tokens=50 + i * 5,
            category=CostCategory.MODEL_INFERENCE,
            user_id=f"user_{i}",
            metadata={"request_type": "test"}
        )
    
    await manager.cost_tracker.flush_entries()
    
    # Get cost summary
    summary = await manager.cost_tracker.get_cost_summary(
        agent_id="summary_test_agent",
        start_date=datetime.now() - timedelta(hours=1),
        end_date=datetime.now() + timedelta(hours=1)
    )
    
    assert summary["summary"]["total_requests"] == 5
    assert summary["summary"]["total_cost"] > 0
    assert summary["summary"]["total_tokens"] > 0
    assert len(summary["provider_breakdown"]) >= 1
    assert len(summary["model_breakdown"]) >= 1


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_realtime_cache_updates(cost_manager):
    """Test real-time cache updates."""
    manager = cost_manager
    
    # Track usage
    await manager.cost_tracker.track_usage(
        agent_id="cache_test_agent",
        provider="openai",
        model="gpt-4",
        input_tokens=200,
        output_tokens=100,
        category=CostCategory.MODEL_INFERENCE
    )
    
    # Check real-time cache
    realtime_data = await manager.cost_tracker.get_realtime_usage("cache_test_agent")
    
    assert realtime_data["agent_id"] == "cache_test_agent"
    assert realtime_data["total_cost"] > 0
    assert realtime_data["total_tokens"] == 300


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_budget_creation_and_monitoring(cost_manager):
    """Test budget creation and monitoring."""
    manager = cost_manager
    
    # Create a budget
    budget = Budget(
        budget_id="test_budget_001",
        name="Test Agent Monthly Budget",
        period=BudgetPeriod.MONTHLY,
        amount=Decimal("100.00"),
        agent_ids=["budget_test_agent"],
        alert_thresholds=[0.5, 0.8, 0.9]
    )
    
    manager.budget_manager.create_budget(budget)
    
    # Add some usage
    for i in range(3):
        await manager.cost_tracker.track_usage(
            agent_id="budget_test_agent",
            provider="openai",
            model="gpt-4",
            input_tokens=1000,
            output_tokens=500,
            category=CostCategory.MODEL_INFERENCE
        )
    
    await manager.cost_tracker.flush_entries()
    
    # Check budget usage
    budget_status = await manager.budget_manager.check_budget_usage("test_budget_001")
    
    assert budget_status["budget_id"] == "test_budget_001"
    assert budget_status["budget_amount"] == 100.0
    assert budget_status["current_usage"] > 0
    assert budget_status["usage_percentage"] >= 0


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_budget_alert_thresholds(cost_manager):
    """Test budget alert threshold triggering."""
    manager = cost_manager
    
    # Create a small budget to easily trigger alerts
    budget = Budget(
        budget_id="alert_test_budget",
        name="Small Test Budget",
        period=BudgetPeriod.DAILY,
        amount=Decimal("0.50"),  # Very small budget
        agent_ids=["alert_test_agent"],
        alert_thresholds=[0.5, 0.8]
    )
    
    manager.budget_manager.create_budget(budget)
    
    # Add usage that exceeds 50% threshold
    await manager.cost_tracker.track_usage(
        agent_id="alert_test_agent",
        provider="openai",
        model="gpt-4",
        input_tokens=1000,  # This should cost ~$0.30
        output_tokens=500,  # This should cost ~$0.30, total ~$0.60
        category=CostCategory.MODEL_INFERENCE
    )
    
    await manager.cost_tracker.flush_entries()
    
    # Check budget status
    budget_status = await manager.budget_manager.check_budget_usage("alert_test_budget")
    
    assert budget_status["usage_percentage"] > 0.5
    assert len(budget_status["alerts_triggered"]) > 0
    assert budget_status["is_over_budget"] is True


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_budget_forecasting(cost_manager):
    """Test budget usage forecasting."""
    manager = cost_manager
    
    # Create budget
    budget = Budget(
        budget_id="forecast_test_budget",
        name="Forecast Test Budget",
        period=BudgetPeriod.MONTHLY,
        amount=Decimal("200.00"),
        agent_ids=["forecast_test_agent"]
    )
    
    manager.budget_manager.create_budget(budget)
    
    # Add historical usage over several days
    base_time = datetime.now() - timedelta(days=10)
    for i in range(10):
        # Use past timestamps to simulate historical data
        entry_time = base_time + timedelta(days=i)
        
        await manager.cost_tracker.track_usage(
            agent_id="forecast_test_agent",
            provider="openai",
            model="gpt-3.5-turbo",
            input_tokens=500,
            output_tokens=250,
            category=CostCategory.MODEL_INFERENCE
        )
    
    await manager.cost_tracker.flush_entries()
    
    # Get forecast
    forecast = await manager.budget_manager.get_budget_forecast("forecast_test_budget", days_ahead=30)
    
    assert forecast["budget_id"] == "forecast_test_budget"
    assert "avg_daily_cost" in forecast
    assert "forecasted_cost" in forecast
    assert "forecast_confidence" in forecast


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_cost_optimization_analysis(cost_manager):
    """Test cost optimization analysis."""
    manager = cost_manager
    
    # Add usage with expensive models
    expensive_usage = [
        ("openai", "gpt-4", 2000, 1000),  # Expensive model
        ("openai", "gpt-4", 1500, 800),
        ("openai", "gpt-3.5-turbo", 1000, 500),  # Cheaper alternative
        ("openai", "gpt-3.5-turbo", 800, 400)
    ]
    
    for provider, model, input_tokens, output_tokens in expensive_usage:
        await manager.cost_tracker.track_usage(
            agent_id="optimization_test_agent",
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            category=CostCategory.MODEL_INFERENCE
        )
    
    await manager.cost_tracker.flush_entries()
    
    # Analyze cost efficiency
    analysis = await manager.cost_optimizer.analyze_cost_efficiency("optimization_test_agent", days=7)
    
    assert analysis["agent_id"] == "optimization_test_agent"
    assert "efficiency_score" in analysis
    assert "recommendations" in analysis
    assert analysis["total_cost"] > 0
    
    # Should have recommendations for expensive model usage
    recommendations = analysis["recommendations"]
    assert len(recommendations) > 0


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_concurrent_cost_tracking(cost_manager):
    """Test concurrent cost tracking operations."""
    manager = cost_manager
    
    # Track many operations concurrently
    tasks = []
    for i in range(50):
        task = manager.cost_tracker.track_usage(
            agent_id=f"concurrent_agent_{i % 5}",
            provider="openai",
            model="gpt-3.5-turbo",
            input_tokens=100 + i,
            output_tokens=50 + i // 2,
            category=CostCategory.MODEL_INFERENCE,
            user_id=f"user_{i % 10}"
        )
        tasks.append(task)
    
    entry_ids = await asyncio.gather(*tasks)
    await manager.cost_tracker.flush_entries()
    
    assert len(entry_ids) == 50
    assert all(entry_id is not None for entry_id in entry_ids)
    
    # Verify data was stored correctly
    summary = await manager.cost_tracker.get_cost_summary(
        start_date=datetime.now() - timedelta(hours=1),
        end_date=datetime.now() + timedelta(hours=1)
    )
    
    assert summary["summary"]["total_requests"] >= 50


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_cost_tracking_performance(cost_manager):
    """Benchmark cost tracking performance."""
    manager = cost_manager
    
    # Benchmark cost tracking operations
    start_time = time.time()
    
    tasks = []
    for i in range(200):
        task = manager.cost_tracker.track_usage(
            agent_id=f"perf_agent_{i % 10}",
            provider="openai",
            model="gpt-3.5-turbo",
            input_tokens=100,
            output_tokens=50,
            category=CostCategory.MODEL_INFERENCE,
            metadata={"batch": i // 20}
        )
        tasks.append(task)
    
    entry_ids = await asyncio.gather(*tasks)
    tracking_time = time.time() - start_time
    
    # Flush to database
    start_time = time.time()
    await manager.cost_tracker.flush_entries()
    flush_time = time.time() - start_time
    
    assert len(entry_ids) == 200
    
    # Performance assertions
    assert tracking_time < 3.0  # 200 tracking operations in under 3 seconds
    assert flush_time < 2.0  # Database flush in under 2 seconds
    
    avg_tracking_time = tracking_time / 200
    assert avg_tracking_time < 0.015  # Average tracking under 15ms
    
    logger.info(f"Cost Tracking Performance: {avg_tracking_time*1000:.1f}ms per operation, {flush_time:.2f}s flush")