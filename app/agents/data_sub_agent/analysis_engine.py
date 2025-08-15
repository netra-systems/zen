"""Advanced data analysis capabilities."""

from typing import Dict, List, Any, Optional
from datetime import datetime
import numpy as np


class AnalysisEngine:
    """Advanced data analysis capabilities"""
    
    @staticmethod
    def calculate_statistics(values: List[float]) -> Optional[Dict[str, float]]:
        """Calculate comprehensive statistics for a metric"""
        if not values:
            return None
        
        arr = np.array(values)
        std_value = float(np.std(arr))
        return {
            "count": len(values),
            "mean": float(np.mean(arr)),
            "median": float(np.median(arr)),
            "std_dev": std_value,
            "std": std_value,  # Alias for backward compatibility
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "p25": float(np.percentile(arr, 25)),
            "p75": float(np.percentile(arr, 75)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99))
        }
    
    @staticmethod
    def detect_trend(values: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """Detect trend in time series data"""
        if len(values) < 3:
            return {"has_trend": False, "reason": "insufficient_data"}
        
        # Convert timestamps to numeric (seconds since first timestamp)
        time_numeric = [(t - timestamps[0]).total_seconds() for t in timestamps]
        
        # Calculate linear regression
        x = np.array(time_numeric)
        y = np.array(values)
        
        # Add small epsilon to avoid division by zero
        x_std = np.std(x)
        if x_std == 0:
            return {"has_trend": False, "reason": "no_time_variation"}
        
        # Normalize to avoid numerical issues
        x_norm = (x - np.mean(x)) / x_std
        
        # Calculate slope and intercept
        slope = np.cov(x_norm, y)[0, 1] / np.var(x_norm)
        intercept = np.mean(y) - slope * np.mean(x_norm)
        
        # Calculate R-squared
        y_pred = slope * x_norm + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # Determine trend direction and strength
        trend_direction = "increasing" if slope > 0 else "decreasing"
        trend_strength = "strong" if abs(r_squared) > 0.7 else "moderate" if abs(r_squared) > 0.4 else "weak"
        
        return {
            "has_trend": abs(r_squared) > 0.2,
            "direction": trend_direction,
            "strength": trend_strength,
            "slope": float(slope),
            "r_squared": float(r_squared),
            "predicted_next": float(slope * (x[-1] + 3600) + intercept)  # Predict 1 hour ahead
        }
    
    @staticmethod
    def detect_seasonality(values: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """Detect daily/hourly seasonality patterns"""
        if len(values) < 24:  # Need at least 24 data points
            return {"has_seasonality": False, "reason": "insufficient_data"}
        
        # Group by hour of day
        hourly_groups = {}
        for ts, val in zip(timestamps, values):
            hour = ts.hour
            if hour not in hourly_groups:
                hourly_groups[hour] = []
            hourly_groups[hour].append(val)
        
        # Calculate hourly averages
        hourly_means = {h: np.mean(vals) for h, vals in hourly_groups.items()}
        
        if len(hourly_means) < 12:  # Need data from at least half the hours
            return {"has_seasonality": False, "reason": "insufficient_hourly_coverage"}
        
        overall_mean = np.mean(list(hourly_means.values()))
        hourly_variance = np.var(list(hourly_means.values()))
        
        # Determine if there's significant hourly variation
        cv = np.sqrt(hourly_variance) / overall_mean if overall_mean != 0 else 0
        has_daily_pattern = cv > 0.2  # 20% coefficient of variation threshold
        
        # Find peak and low hours
        peak_hour = max(hourly_means, key=hourly_means.get)
        low_hour = min(hourly_means, key=hourly_means.get)
        
        return {
            "has_seasonality": has_daily_pattern,
            "daily_pattern": {
                "peak_hour": peak_hour,
                "peak_value": hourly_means[peak_hour],
                "low_hour": low_hour,
                "low_value": hourly_means[low_hour],
                "coefficient_of_variation": float(cv)
            },
            "hourly_averages": hourly_means
        }
    
    @staticmethod
    def identify_outliers(values: List[float], method: str = "iqr") -> List[int]:
        """Identify outliers using IQR or Z-score method"""
        if len(values) < 4:
            return []
        
        arr = np.array(values)
        outlier_indices = []
        
        if method == "iqr":
            q1 = np.percentile(arr, 25)
            q3 = np.percentile(arr, 75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            for i, val in enumerate(arr):
                if val < lower_bound or val > upper_bound:
                    outlier_indices.append(i)
        
        elif method == "zscore":
            mean = np.mean(arr)
            std = np.std(arr)
            if std == 0:
                return []
            
            for i, val in enumerate(arr):
                z_score = abs((val - mean) / std)
                if z_score >= 3:
                    outlier_indices.append(i)
        
        return outlier_indices