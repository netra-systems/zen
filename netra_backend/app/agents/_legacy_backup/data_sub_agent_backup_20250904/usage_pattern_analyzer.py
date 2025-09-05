"""Usage pattern analysis module for DataSubAgent."""

from typing import Any, Dict, List, Optional, Tuple

from netra_backend.app.logging_config import central_logger as logger


class UsagePatternAnalyzer:
    """Focused usage pattern analysis operations."""
    
    def __init__(self, query_builder: Any, clickhouse_ops: Any, redis_manager: Any) -> None:
        self.query_builder = query_builder
        self.clickhouse_ops = clickhouse_ops
        self.redis_manager = redis_manager
    
    async def analyze_usage_patterns(
        self,
        user_id: int,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Analyze usage patterns over time."""
        data = await self._fetch_usage_data(user_id, days_back)
        if not data:
            return self._create_no_usage_data_response()
        
        patterns = self._aggregate_usage_patterns(data)
        peaks = self._find_peak_usage_times(patterns)
        summary = self._calculate_usage_summary(patterns, days_back, peaks)
        return self._build_usage_response(days_back, summary, patterns)
    
    async def _fetch_usage_data(self, user_id: int, days_back: int) -> Optional[List[Dict]]:
        """Fetch usage pattern data from ClickHouse."""
        query = self._build_usage_query(user_id, days_back)
        cache_key = self._build_usage_cache_key(user_id, days_back)
        return await self.clickhouse_ops.fetch_data(query, cache_key, self.redis_manager)
    
    def _build_usage_query(self, user_id: int, days_back: int) -> str:
        """Build usage patterns query."""
        return self.query_builder.build_usage_patterns_query(user_id, days_back)
    
    def _build_usage_cache_key(self, user_id: int, days_back: int) -> str:
        """Build cache key for usage patterns."""
        return f"usage_patterns:{user_id}:{days_back}"
    
    def _create_no_usage_data_response(self) -> Dict[str, Any]:
        """Create response for no usage data."""
        return {"status": "no_data", "message": "No usage data available"}
    
    def _aggregate_usage_patterns(self, data: List[Dict]) -> Dict[str, Dict]:
        """Aggregate usage data by day and hour patterns."""
        daily_patterns, hourly_patterns = {}, {}
        
        for row in data:
            self._update_daily_pattern(daily_patterns, row)
            self._update_hourly_pattern(hourly_patterns, row)
        
        return {"daily": daily_patterns, "hourly": hourly_patterns}
    
    def _update_daily_pattern(self, daily_patterns: Dict, row: Dict) -> None:
        """Update daily usage pattern with row data."""
        dow = row['day_of_week']
        if dow not in daily_patterns:
            daily_patterns[dow] = self._create_empty_daily_pattern()
        self._add_daily_metrics(daily_patterns[dow], row)
    
    def _create_empty_daily_pattern(self) -> Dict[str, Any]:
        """Create empty daily pattern structure."""
        return {
            "total_events": 0,
            "total_cost": 0,
            "unique_workloads": set(),
            "unique_models": set()
        }
    
    def _add_daily_metrics(self, pattern: Dict, row: Dict) -> None:
        """Add metrics to daily pattern."""
        pattern["total_events"] += row['event_count']
        pattern["total_cost"] += row['total_cost']
    
    def _update_hourly_pattern(self, hourly_patterns: Dict, row: Dict) -> None:
        """Update hourly usage pattern with row data."""
        hour = row['hour_of_day']
        if hour not in hourly_patterns:
            hourly_patterns[hour] = self._create_empty_hourly_pattern()
        self._add_hourly_metrics(hourly_patterns[hour], row)
    
    def _create_empty_hourly_pattern(self) -> Dict[str, Any]:
        """Create empty hourly pattern structure."""
        return {"total_events": 0, "total_cost": 0}
    
    def _add_hourly_metrics(self, pattern: Dict, row: Dict) -> None:
        """Add metrics to hourly pattern."""
        pattern["total_events"] += row['event_count']
        pattern["total_cost"] += row['total_cost']
    
    def _find_peak_usage_times(self, patterns: Dict) -> Dict[str, Any]:
        """Find peak usage times from patterns."""
        peak_day = self._find_peak_daily_usage(patterns["daily"])
        peak_hour = self._find_peak_hourly_usage(patterns["hourly"])
        return {"day": peak_day, "hour": peak_hour}
    
    def _find_peak_daily_usage(self, daily_patterns: Dict) -> Tuple[int, Dict]:
        """Find peak daily usage."""
        return max(daily_patterns.items(), key=lambda x: x[1]["total_events"])
    
    def _find_peak_hourly_usage(self, hourly_patterns: Dict) -> Tuple[int, Dict]:
        """Find peak hourly usage."""
        return max(hourly_patterns.items(), key=lambda x: x[1]["total_events"])
    
    def _calculate_usage_summary(self, patterns: Dict, days_back: int, peaks: Dict) -> Dict[str, Any]:
        """Calculate usage summary statistics."""
        day_names = self._get_day_names()
        total_cost = self._calculate_total_cost(patterns["daily"])
        total_events = self._calculate_total_events(patterns["daily"])
        
        return {
            "total_cost": total_cost,
            "average_daily_cost": self._calculate_average_daily_cost(total_cost, days_back),
            "peak_usage_day": self._get_peak_day_name(peaks["day"][0], day_names),
            "peak_usage_hour": self._format_peak_hour(peaks["hour"][0]),
            "total_events": total_events
        }
    
    def _get_day_names(self) -> List[str]:
        """Get day names array."""
        return ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    
    def _calculate_total_cost(self, daily_patterns: Dict) -> float:
        """Calculate total cost from daily patterns."""
        return sum(d["total_cost"] for d in daily_patterns.values())
    
    def _calculate_total_events(self, daily_patterns: Dict) -> int:
        """Calculate total events from daily patterns."""
        return sum(d["total_events"] for d in daily_patterns.values())
    
    def _calculate_average_daily_cost(self, total_cost: float, days_back: int) -> float:
        """Calculate average daily cost."""
        return total_cost / days_back if days_back > 0 else 0
    
    def _get_peak_day_name(self, peak_day_index: int, day_names: List[str]) -> str:
        """Get peak day name from index."""
        return day_names[peak_day_index - 1]
    
    def _format_peak_hour(self, peak_hour: int) -> str:
        """Format peak hour for display."""
        return f"{peak_hour:02d}:00"
    
    def _build_usage_response(self, days_back: int, summary: Dict, patterns: Dict) -> Dict[str, Any]:
        """Build usage patterns response."""
        day_names = self._get_day_names()
        return {
            "period": f"Last {days_back} days",
            "summary": summary,
            "daily_patterns": self._format_daily_patterns(patterns["daily"], day_names),
            "hourly_distribution": patterns["hourly"]
        }
    
    def _format_daily_patterns(self, daily_patterns: Dict, day_names: List[str]) -> Dict[str, Any]:
        """Format daily patterns with day names."""
        return {day_names[k - 1]: v for k, v in daily_patterns.items()}