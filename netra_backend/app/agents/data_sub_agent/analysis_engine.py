"""Analysis Engine Compatibility Module

Simple compatibility wrapper for legacy AnalysisEngine imports.
Provides backward compatibility while delegating to modern implementations.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import numpy as np


class AnalysisEngine:
    """Legacy AnalysisEngine for backward compatibility.
    
    Provides a simple interface for existing test cases without complex dependencies.
    Statistical analysis methods for time series data, outlier detection, and trend analysis.
    """
    
    def __init__(self):
        pass
    
    @staticmethod
    def calculate_statistics(values: List[float]) -> Optional[Dict[str, Union[float, int]]]:
        """Calculate basic statistics for a metric.
        
        Args:
            values: List of numeric values to analyze
            
        Returns:
            Dictionary with statistical measures (mean, std, min, max, etc.) or None if empty data
        """
        if not values:
            return None
        
        arr = np.array(values)
        return {
            "mean": float(np.mean(arr)),
            "median": float(np.median(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "count": len(values),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99))
        }
    
    @staticmethod
    def detect_trend(values: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """Detect trend in time series data using linear regression.
        
        Args:
            values: List of numeric values over time
            timestamps: List of datetime objects (currently not used in calculation)
            
        Returns:
            Dictionary with trend information including has_trend boolean and optional slope/direction
        """
        if len(values) < 3:
            return {"has_trend": False, "reason": "insufficient_data"}
        
        # Simple linear regression for trend detection
        n = len(values)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return {"has_trend": False, "reason": "no_variance"}
        
        slope = numerator / denominator
        
        return {
            "has_trend": abs(slope) > 0.1,  # Simple threshold
            "slope": slope,
            "direction": "increasing" if slope > 0 else "decreasing"
        }
    
    @staticmethod
    def detect_seasonality(values: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """Detect basic seasonality patterns using variance analysis.
        
        Args:
            values: List of numeric values over time
            timestamps: List of datetime objects (currently not used in calculation)
            
        Returns:
            Dictionary with seasonality information including has_seasonality boolean and confidence
        """
        if len(values) < 24:
            return {"has_seasonality": False, "reason": "insufficient_data"}
        
        # Simple seasonality detection based on variance
        mean_val = np.mean(values)
        variance = np.var(values)
        
        return {
            "has_seasonality": variance > mean_val * 0.1,  # Simple heuristic
            "confidence": min(1.0, variance / (mean_val + 0.001)),
            "period": "daily"  # Default assumption
        }
    
    @staticmethod
    def identify_outliers(values: List[float], method: str = "iqr") -> List[int]:
        """Identify outliers using statistical methods.
        
        Args:
            values: List of numeric values to analyze
            method: Statistical method to use ("iqr" or "zscore")
            
        Returns:
            List of indices of outlier values, empty list if insufficient data
        """
        if len(values) < 4:
            return []
        
        arr = np.array(values)
        
        if method == "iqr":
            q1 = np.percentile(arr, 25)
            q3 = np.percentile(arr, 75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            return [i for i, val in enumerate(values) 
                   if val < lower_bound or val > upper_bound]
        
        elif method == "zscore":
            mean = np.mean(arr)
            std = np.std(arr)
            if std == 0:
                return []
            z_scores = np.abs((arr - mean) / std)
            return [i for i, z in enumerate(z_scores) if z > 3]
        
        return []