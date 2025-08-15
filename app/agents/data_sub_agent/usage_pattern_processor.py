"""Usage pattern processing module with ≤8 line functions."""

from typing import Dict, List, Any


class UsagePatternProcessor:
    """Process usage patterns with focused functions."""
    
    def process_patterns(self, data: List[Dict[str, Any]], days_back: int) -> Dict[str, Any]:
        """Process usage patterns data."""
        daily_patterns = {}
        hourly_patterns = {}
        
        for row in data:
            self._aggregate_daily_patterns(row, daily_patterns)
            self._aggregate_hourly_patterns(row, hourly_patterns)
        
        return self._create_pattern_summary(daily_patterns, hourly_patterns, days_back)
    
    def _aggregate_daily_patterns(self, row: Dict[str, Any], daily_patterns: Dict[int, Dict[str, Any]]) -> None:
        """Aggregate daily usage patterns."""
        dow = row['day_of_week']
        
        if dow not in daily_patterns:
            daily_patterns[dow] = self._create_empty_daily_pattern()
        
        daily_patterns[dow]["total_events"] += row['event_count']
        daily_patterns[dow]["total_cost"] += row['total_cost']
    
    def _aggregate_hourly_patterns(self, row: Dict[str, Any], hourly_patterns: Dict[int, Dict[str, Any]]) -> None:
        """Aggregate hourly usage patterns."""
        hour = row['hour_of_day']
        
        if hour not in hourly_patterns:
            hourly_patterns[hour] = self._create_empty_hourly_pattern()
        
        hourly_patterns[hour]["total_events"] += row['event_count']
        hourly_patterns[hour]["total_cost"] += row['total_cost']
    
    def _create_empty_daily_pattern(self) -> Dict[str, Any]:
        """Create empty daily pattern structure."""
        return {
            "total_events": 0,
            "total_cost": 0,
            "unique_workloads": set(),
            "unique_models": set()
        }
    
    def _create_empty_hourly_pattern(self) -> Dict[str, Any]:
        """Create empty hourly pattern structure."""
        return {
            "total_events": 0,
            "total_cost": 0
        }
    
    def _create_pattern_summary(
        self,
        daily_patterns: Dict[int, Dict[str, Any]],
        hourly_patterns: Dict[int, Dict[str, Any]],
        days_back: int
    ) -> Dict[str, Any]:
        """Create pattern summary result."""
        peak_day = self._find_peak_day(daily_patterns)
        peak_hour = self._find_peak_hour(hourly_patterns)
        total_cost = self._calculate_total_cost(daily_patterns)
        avg_daily_cost = total_cost / days_back if days_back > 0 else 0
        
        return self._format_pattern_result(
            daily_patterns, hourly_patterns, peak_day, peak_hour, 
            total_cost, avg_daily_cost, days_back
        )
    
    def _find_peak_day(self, daily_patterns: Dict[int, Dict[str, Any]]) -> tuple:
        """Find peak usage day."""
        return max(daily_patterns.items(), key=lambda x: x[1]["total_events"])
    
    def _find_peak_hour(self, hourly_patterns: Dict[int, Dict[str, Any]]) -> tuple:
        """Find peak usage hour."""
        return max(hourly_patterns.items(), key=lambda x: x[1]["total_events"])
    
    def _calculate_total_cost(self, daily_patterns: Dict[int, Dict[str, Any]]) -> float:
        """Calculate total cost across all days."""
        return sum(d["total_cost"] for d in daily_patterns.values())
    
    def _format_pattern_result(
        self,
        daily_patterns: Dict[int, Dict[str, Any]],
        hourly_patterns: Dict[int, Dict[str, Any]],
        peak_day: tuple,
        peak_hour: tuple,
        total_cost: float,
        avg_daily_cost: float,
        days_back: int
    ) -> Dict[str, Any]:
        """Format final pattern result."""
        day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        
        return {
            "period": f"Last {days_back} days",
            "summary": self._create_summary_section(
                total_cost, avg_daily_cost, peak_day, peak_hour, 
                daily_patterns, day_names
            ),
            "daily_patterns": self._format_daily_patterns(daily_patterns, day_names),
            "hourly_distribution": hourly_patterns
        }
    
    def _create_summary_section(
        self,
        total_cost: float,
        avg_daily_cost: float,
        peak_day: tuple,
        peak_hour: tuple,
        daily_patterns: Dict[int, Dict[str, Any]],
        day_names: List[str]
    ) -> Dict[str, Any]:
        """Create summary section."""
        return {
            "total_cost": total_cost,
            "average_daily_cost": avg_daily_cost,
            "peak_usage_day": day_names[peak_day[0] - 1],
            "peak_usage_hour": f"{peak_hour[0]:02d}:00",
            "total_events": sum(d["total_events"] for d in daily_patterns.values())
        }
    
    def _format_daily_patterns(
        self,
        daily_patterns: Dict[int, Dict[str, Any]],
        day_names: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Format daily patterns with day names."""
        return {
            day_names[k - 1]: v
            for k, v in daily_patterns.items()
        }