"""Cost tracking service for AI operations.

Business Value Justification (BVJ):
- Segment: All tiers (cost optimization impacts all users)
- Business Goal: Track and optimize LLM/AI costs across operations
- Value Impact: Provides visibility into cost drivers for optimization
- Revenue Impact: Enables cost-conscious operations and budget management
"""

import asyncio
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager

logger = central_logger.get_logger(__name__)


class CostTracker:
    """Tracks costs for AI operations and provides analytics."""

    def __init__(self):
        self.redis_client = None
        self._cost_cache = {}
        self._usage_cache = defaultdict(lambda: {"tokens": 0, "requests": 0, "cost": Decimal('0')})

    async def _get_redis(self):
        """Get Redis client lazily."""
        if not self.redis_client:
            self.redis_client = await redis_manager.get_client()
        return self.redis_client

    async def track_operation_cost(
        self,
        operation_id: str,
        operation_type: str,
        model_name: str,
        tokens_used: int,
        cost: Decimal,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track the cost of an AI operation."""
        try:
            redis = await self._get_redis()
            cost_data = {
                "operation_id": operation_id,
                "operation_type": operation_type,
                "model_name": model_name,
                "tokens_used": tokens_used,
                "cost": float(cost),
                "timestamp": datetime.now(UTC).isoformat(),
                "metadata": metadata or {}
            }
            
            # Store in Redis with daily key
            daily_key = f"costs:{datetime.now(UTC).strftime('%Y%m%d')}"
            await redis.lpush(daily_key, str(cost_data))
            await redis.expire(daily_key, 3600 * 24 * 90)  # 90 days retention
            
            # Update cache
            self._usage_cache[operation_type]["tokens"] += tokens_used
            self._usage_cache[operation_type]["requests"] += 1
            self._usage_cache[operation_type]["cost"] += cost
            
            logger.debug(f"Tracked cost for operation {operation_id}: ${cost}")
        except Exception as e:
            logger.error(f"Cost tracking error: {str(e)}")

    async def get_daily_costs(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get costs for a specific day."""
        try:
            redis = await self._get_redis()
            target_date = date or datetime.now(UTC)
            daily_key = f"costs:{target_date.strftime('%Y%m%d')}"
            
            cost_entries = await redis.lrange(daily_key, 0, -1)
            
            total_cost = Decimal('0')
            total_tokens = 0
            operations_by_type = defaultdict(lambda: {"count": 0, "cost": Decimal('0'), "tokens": 0})
            
            for entry in cost_entries:
                try:
                    cost_data = eval(entry)  # Simple parsing - would use json in production
                    cost = Decimal(str(cost_data["cost"]))
                    tokens = cost_data["tokens_used"]
                    op_type = cost_data["operation_type"]
                    
                    total_cost += cost
                    total_tokens += tokens
                    operations_by_type[op_type]["count"] += 1
                    operations_by_type[op_type]["cost"] += cost
                    operations_by_type[op_type]["tokens"] += tokens
                except Exception as parse_error:
                    logger.warning(f"Failed to parse cost entry: {parse_error}")
                    continue
            
            return {
                "date": target_date.strftime('%Y-%m-%d'),
                "total_cost": float(total_cost),
                "total_tokens": total_tokens,
                "operations": dict(operations_by_type)
            }
        except Exception as e:
            logger.error(f"Error getting daily costs: {str(e)}")
            return {"date": target_date.strftime('%Y-%m-%d'), "total_cost": 0, "total_tokens": 0, "operations": {}}

    async def get_cost_trends(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get cost trends over multiple days."""
        trends = []
        for i in range(days):
            date = datetime.now(UTC) - timedelta(days=i)
            daily_data = await self.get_daily_costs(date)
            trends.append(daily_data)
        return list(reversed(trends))

    async def estimate_monthly_cost(self) -> Dict[str, Any]:
        """Estimate monthly cost based on recent usage."""
        try:
            # Get last 7 days of data
            trends = await self.get_cost_trends(7)
            if not trends:
                return {"estimated_monthly_cost": 0, "confidence": "low"}
            
            # Calculate average daily cost
            total_cost = sum(day["total_cost"] for day in trends)
            avg_daily_cost = total_cost / len(trends)
            
            # Estimate monthly (30 days)
            estimated_monthly = avg_daily_cost * 30
            
            return {
                "estimated_monthly_cost": round(estimated_monthly, 2),
                "avg_daily_cost": round(avg_daily_cost, 2),
                "based_on_days": len(trends),
                "confidence": "medium" if len(trends) >= 5 else "low"
            }
        except Exception as e:
            logger.error(f"Error estimating monthly cost: {str(e)}")
            return {"estimated_monthly_cost": 0, "confidence": "low"}

    async def get_cost_breakdown_by_model(self, days: int = 7) -> Dict[str, Any]:
        """Get cost breakdown by model type."""
        try:
            models_data = defaultdict(lambda: {"cost": Decimal('0'), "tokens": 0, "requests": 0})
            
            for i in range(days):
                date = datetime.now(UTC) - timedelta(days=i)
                daily_key = f"costs:{date.strftime('%Y%m%d')}"
                redis = await self._get_redis()
                cost_entries = await redis.lrange(daily_key, 0, -1)
                
                for entry in cost_entries:
                    try:
                        cost_data = eval(entry)
                        model = cost_data["model_name"]
                        models_data[model]["cost"] += Decimal(str(cost_data["cost"]))
                        models_data[model]["tokens"] += cost_data["tokens_used"]
                        models_data[model]["requests"] += 1
                    except Exception:
                        continue
            
            # Convert to serializable format
            breakdown = {}
            for model, data in models_data.items():
                breakdown[model] = {
                    "cost": float(data["cost"]),
                    "tokens": data["tokens"],
                    "requests": data["requests"],
                    "avg_cost_per_request": float(data["cost"] / data["requests"]) if data["requests"] > 0 else 0
                }
            
            return breakdown
        except Exception as e:
            logger.error(f"Error getting cost breakdown: {str(e)}")
            return {}

    def get_cached_usage(self) -> Dict[str, Any]:
        """Get cached usage statistics."""
        return dict(self._usage_cache)