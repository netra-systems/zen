"""
E2E Test Temporal Patterns Generator

This module provides temporal pattern generators for comprehensive testing:
- Seasonal patterns (annual, quarterly, monthly)
- Cyclical patterns (daily, weekly) 
- Burst patterns (traffic spikes)
- Growth patterns (linear, exponential)

ARCHITECTURAL COMPLIANCE:
- Maximum file size: 300 lines
- Maximum function size: 8 lines
- Single responsibility: Temporal pattern generation
- Strong typing: All functions typed
- Modular design: Composable pattern generators

Usage:
    from netra_backend.tests.e2e.data.temporal_patterns import (
        TemporalPatternGenerator,
        SeasonalPatternGenerator,
        BurstPatternGenerator
    )
"""

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Union

import numpy as np

class TemporalPatternType(Enum):
    """Types of temporal patterns."""
    SEASONAL = "seasonal"
    CYCLICAL = "cyclical"
    BURST = "burst"
    LINEAR_GROWTH = "linear_growth"
    EXPONENTIAL_GROWTH = "exponential_growth"

@dataclass
class TemporalPattern:
    """Temporal pattern configuration."""
    pattern_type: TemporalPatternType
    base_value: float
    amplitude: float
    period_hours: int
    phase_offset: float = 0.0

class TemporalPatternGenerator:
    """Generates temporal patterns for testing."""
    
    def __init__(self):
        self.patterns = self._initialize_patterns()
    
    def generate_seasonal_pattern(self, hours: int) -> Iterator[float]:
        """Generate seasonal usage pattern."""
        pattern = self.patterns[TemporalPatternType.SEASONAL]
        for hour in range(hours):
            yield self._calculate_pattern_value(pattern, hour)
    
    def generate_burst_pattern(self, bursts: int) -> Iterator[float]:
        """Generate burst traffic pattern."""
        pattern = self.patterns[TemporalPatternType.BURST]
        for burst in range(bursts):
            yield self._calculate_burst_value(pattern, burst)
    
    def generate_growth_pattern(self, days: int) -> Iterator[float]:
        """Generate growth pattern over time."""
        pattern = self.patterns[TemporalPatternType.LINEAR_GROWTH]
        for day in range(days):
            yield self._calculate_growth_value(pattern, day)
    
    def _initialize_patterns(self) -> Dict[TemporalPatternType, TemporalPattern]:
        """Initialize temporal pattern configurations."""
        return {
            TemporalPatternType.SEASONAL: TemporalPattern(
                TemporalPatternType.SEASONAL, 100.0, 50.0, 8760
            ),
            TemporalPatternType.BURST: TemporalPattern(
                TemporalPatternType.BURST, 50.0, 200.0, 24
            ),
            TemporalPatternType.LINEAR_GROWTH: TemporalPattern(
                TemporalPatternType.LINEAR_GROWTH, 100.0, 0.1, 365
            )
        }

class SeasonalPatternGenerator:
    """Generates seasonal patterns for business scenarios."""
    
    def __init__(self):
        self.business_patterns = self._initialize_business_patterns()
    
    def generate_business_hours_pattern(self, days: int) -> Iterator[Dict[str, Any]]:
        """Generate business hours usage pattern."""
        for day in range(days):
            for hour in range(24):
                yield self._create_business_hour_record(day, hour)
    
    def generate_quarterly_pattern(self, quarters: int) -> Iterator[Dict[str, Any]]:
        """Generate quarterly business cycle pattern."""
        for quarter in range(quarters):
            for month in range(3):
                yield self._create_quarterly_record(quarter, month)
    
    def generate_holiday_pattern(self, year: int) -> Iterator[Dict[str, Any]]:
        """Generate holiday period patterns."""
        holidays = self._get_holiday_periods(year)
        for holiday in holidays:
            yield self._create_holiday_record(holiday)
    
    def _initialize_business_patterns(self) -> Dict[str, Any]:
        """Initialize business pattern configurations."""
        return {
            "business_hours": {"start": 9, "end": 17, "multiplier": 2.0},
            "weekend_reduction": {"multiplier": 0.3},
            "quarter_end_spike": {"multiplier": 1.5}
        }

class BurstPatternGenerator:
    """Generates burst and spike patterns for stress testing."""
    
    def __init__(self):
        self.burst_configs = self._initialize_burst_configs()
    
    def generate_traffic_burst(self, duration_minutes: int) -> Iterator[Dict[str, Any]]:
        """Generate traffic burst pattern."""
        for minute in range(duration_minutes):
            intensity = self._calculate_burst_intensity(minute, duration_minutes)
            yield self._create_burst_record(minute, intensity)
    
    def generate_concurrent_spike(self, max_users: int) -> Iterator[Dict[str, Any]]:
        """Generate concurrent user spike pattern."""
        for user_count in range(1, max_users + 1):
            spike_probability = self._calculate_spike_probability(user_count, max_users)
            yield self._create_spike_record(user_count, spike_probability)
    
    def generate_resource_pressure(self, pressure_level: float) -> Dict[str, Any]:
        """Generate resource pressure scenario."""
        return {
            "pressure_type": "resource_exhaustion",
            "pressure_level": pressure_level,
            "duration_minutes": int(pressure_level * 60),
            "recovery_time_minutes": int(pressure_level * 30)
        }
    
    def _initialize_burst_configs(self) -> Dict[str, Any]:
        """Initialize burst configuration parameters."""
        return {
            "short_burst": {"duration": 5, "intensity": 10.0},
            "medium_burst": {"duration": 15, "intensity": 5.0},
            "long_burst": {"duration": 60, "intensity": 2.0}
        }

class GrowthPatternGenerator:
    """Generates growth patterns for capacity planning."""
    
    def __init__(self):
        self.growth_models = self._initialize_growth_models()
    
    def generate_linear_growth(self, months: int, growth_rate: float) -> Iterator[Dict[str, Any]]:
        """Generate linear growth pattern."""
        base_usage = 100.0
        for month in range(months):
            usage = base_usage * (1 + growth_rate * month / 12)
            yield self._create_growth_record(month, usage, "linear")
    
    def generate_exponential_growth(self, months: int, growth_factor: float) -> Iterator[Dict[str, Any]]:
        """Generate exponential growth pattern."""
        base_usage = 100.0
        for month in range(months):
            usage = base_usage * (growth_factor ** (month / 12))
            yield self._create_growth_record(month, usage, "exponential")
    
    def generate_seasonal_growth(self, years: int) -> Iterator[Dict[str, Any]]:
        """Generate seasonal growth with annual trends."""
        for year in range(years):
            for month in range(12):
                seasonal_factor = self._calculate_seasonal_factor(month)
                yield self._create_seasonal_growth_record(year, month, seasonal_factor)
    
    def _initialize_growth_models(self) -> Dict[str, Any]:
        """Initialize growth model parameters."""
        return {
            "conservative": {"rate": 0.1, "factor": 1.1},
            "moderate": {"rate": 0.3, "factor": 1.3},
            "aggressive": {"rate": 0.5, "factor": 1.5}
        }

# Helper functions for pattern calculations
def _calculate_pattern_value(pattern: TemporalPattern, time_unit: int) -> float:
    """Calculate pattern value at specific time."""
    angle = 2 * np.pi * time_unit / pattern.period_hours + pattern.phase_offset
    seasonal_component = pattern.amplitude * np.sin(angle)
    return pattern.base_value + seasonal_component

def _calculate_burst_value(pattern: TemporalPattern, burst_index: int) -> float:
    """Calculate burst pattern value."""
    burst_intensity = np.random.exponential(pattern.amplitude)
    return pattern.base_value + burst_intensity

def _calculate_growth_value(pattern: TemporalPattern, day: int) -> float:
    """Calculate growth pattern value."""
    growth_rate = pattern.amplitude
    return pattern.base_value * (1 + growth_rate * day / pattern.period_hours)

def _calculate_burst_intensity(minute: int, total_duration: int) -> float:
    """Calculate burst intensity at specific minute."""
    peak_minute = total_duration // 2
    distance_from_peak = abs(minute - peak_minute)
    intensity = max(0.1, 1.0 - (distance_from_peak / peak_minute))
    return intensity * np.random.uniform(0.8, 1.2)

def _calculate_spike_probability(user_count: int, max_users: int) -> float:
    """Calculate spike probability for user count."""
    normalized_count = user_count / max_users
    return np.exp(-5 * normalized_count * normalized_count)

def _calculate_seasonal_factor(month: int) -> float:
    """Calculate seasonal factor for month."""
    seasonal_months = [11, 0, 2, 5, 8]  # Nov, Dec, Jan, Mar, Jun, Sep
    if month in seasonal_months:
        return 1.5
    return 1.0

def _create_business_hour_record(day: int, hour: int) -> Dict[str, Any]:
    """Create business hour usage record."""
    is_business_hour = 9 <= hour <= 17
    is_weekend = day % 7 in [5, 6]
    multiplier = 2.0 if is_business_hour and not is_weekend else 0.5
    return {
        "day": day, "hour": hour, "usage_multiplier": multiplier,
        "is_business_hour": is_business_hour, "is_weekend": is_weekend
    }

def _create_quarterly_record(quarter: int, month: int) -> Dict[str, Any]:
    """Create quarterly business cycle record."""
    is_quarter_end = month == 2
    multiplier = 1.5 if is_quarter_end else 1.0
    return {
        "quarter": quarter, "month": month,
        "usage_multiplier": multiplier, "is_quarter_end": is_quarter_end
    }

def _create_holiday_record(holiday: Dict[str, Any]) -> Dict[str, Any]:
    """Create holiday period record."""
    return {
        "holiday_name": holiday["name"],
        "start_date": holiday["start"], "end_date": holiday["end"],
        "usage_multiplier": holiday["multiplier"]
    }

def _create_burst_record(minute: int, intensity: float) -> Dict[str, Any]:
    """Create burst pattern record."""
    return {
        "minute": minute, "burst_intensity": intensity,
        "requests_per_second": int(intensity * 100),
        "expected_latency_ms": max(50, 500 / intensity)
    }

def _create_spike_record(user_count: int, probability: float) -> Dict[str, Any]:
    """Create spike pattern record."""
    return {
        "concurrent_users": user_count, "spike_probability": probability,
        "resource_pressure": min(1.0, user_count / 1000),
        "expected_response_time": 100 + (user_count * 0.1)
    }

def _create_growth_record(month: int, usage: float, growth_type: str) -> Dict[str, Any]:
    """Create growth pattern record."""
    return {"month": month, "projected_usage": usage, "growth_type": growth_type}

def _create_seasonal_growth_record(year: int, month: int, factor: float) -> Dict[str, Any]:
    """Create seasonal growth record."""
    return {"year": year, "month": month, "seasonal_factor": factor}

def _get_holiday_periods(year: int) -> List[Dict[str, Any]]:
    """Get holiday periods for year."""
    return [{"name": "New Year", "start": f"{year}-12-31", "end": f"{year+1}-01-02", "multiplier": 0.2}]