"""
Data validation module for analysis requests and data quality checks.
Provides comprehensive validation for data analysis operations.
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DataValidator:
    """Comprehensive data validator for analysis operations."""
    
    def __init__(self):
        """Initialize DataValidator with default thresholds and configurations."""
        self.logger = logger
        
        # Validation thresholds
        self.thresholds = {
            "min_data_points": 10,
            "max_null_percentage": 20.0,
            "min_time_span_hours": 1.0,
            "max_outlier_percentage": 10.0
        }
        
        # Valid metrics configuration
        self.valid_metrics = {
            "latency_ms": {
                "min": 0,
                "max": 30000,
                "type": "float"
            },
            "cost_cents": {
                "min": 0,
                "max": 10000,
                "type": "float"
            },
            "throughput": {
                "min": 0,
                "max": 100000,
                "type": "float"
            },
            "success_rate": {
                "min": 0.0,
                "max": 1.0,
                "type": "float"
            },
            "tokens_input": {
                "min": 0,
                "max": 1000000,
                "type": "int"
            },
            "tokens_output": {
                "min": 0,
                "max": 1000000,
                "type": "int"
            }
        }
        
        # Valid analysis types
        self.valid_analysis_types = [
            "performance", "anomaly", "correlation", "usage_pattern", 
            "cost_optimization", "trend", "trend_analysis"
        ]
        
        # Timeframe pattern (e.g., "24h", "7d", "2w", "30d")
        self.timeframe_pattern = re.compile(r'^\d+[hdw]$')
        
        self.logger.debug("Initialized DataValidator with comprehensive validation")
    
    def validate_analysis_request(self, request: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate analysis request structure and content."""
        errors = []
        
        # Check required fields
        if "type" not in request:
            errors.append("Analysis type is required")
        elif request["type"] not in self.valid_analysis_types:
            errors.append(f"Invalid analysis type: {request['type']}")
            
        if "timeframe" not in request:
            errors.append("Timeframe is required")
        elif not self._validate_timeframe_format(request["timeframe"]):
            errors.append(f"Invalid timeframe format: {request['timeframe']}")
            
        # Validate metrics if provided
        if "metrics" in request:
            if not isinstance(request["metrics"], list):
                errors.append("Metrics must be a list")
            else:
                invalid_metrics = []
                for metric in request["metrics"]:
                    if metric not in self.valid_metrics:
                        invalid_metrics.append(metric)
                if invalid_metrics:
                    errors.append(f"Invalid metrics: {invalid_metrics}")
        
        return len(errors) == 0, errors
    
    def _validate_timeframe_format(self, timeframe: str) -> bool:
        """Validate timeframe format (e.g., 24h, 7d, 2w, 30d)."""
        if not isinstance(timeframe, str):
            return False
        return bool(self.timeframe_pattern.match(timeframe))
    
    def validate_raw_data(self, data: List[Dict[str, Any]], metrics: List[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """Validate raw data quality."""
        errors = []
        warnings = []
        
        if not data:
            return False, {
                "valid": False,
                "data_points": 0,
                "errors": ["No data provided for validation"],
                "warnings": [],
                "quality_score": 0.0
            }
            
        if len(data) < self.thresholds["min_data_points"]:
            warnings.append(f"Low data point count: {len(data)} < {self.thresholds['min_data_points']} recommended")
            
        # Check for required fields
        required_fields = ["timestamp"]
        for i, record in enumerate(data):
            for field in required_fields:
                if field not in record:
                    errors.append(f"Missing required field '{field}' in record {i}")
                    
        # Check null percentage
        null_counts = {}
        total_records = len(data)
        
        for record in data:
            for key, value in record.items():
                if key not in null_counts:
                    null_counts[key] = 0
                if value is None or value == "":
                    null_counts[key] += 1
                    
        for field, null_count in null_counts.items():
            null_percentage = (null_count / total_records) * 100
            if null_percentage > self.thresholds["max_null_percentage"]:
                errors.append(f"High null percentage for {field}: {null_percentage:.1f}%")
        
        # Validate time span (only if we have enough data points)
        if data and "timestamp" in data[0] and len(data) >= 2:
            time_span_valid, time_errors = self._validate_time_span(data)
            if not time_span_valid:
                errors.extend(time_errors)
        elif len(data) == 1:
            # Single data point - add warning instead of error
            warnings.append("Single data point - time span validation skipped")
                
        # Validate metric values (only for specified metrics if provided)
        if metrics:
            metric_errors = self._validate_specific_metric_values(data, metrics)
        else:
            metric_errors = self._validate_metric_values(data)
        errors.extend(metric_errors)
        
        # Calculate quality score (convert from 0-100 to 0-1.1 scale)
        quality_score_100 = self.calculate_quality_score(data, errors, warnings)
        quality_score = quality_score_100 / 100.0  # Convert to 0-1.0 base scale
        
        # Add bonus for large datasets (up to +0.1)
        if len(data) > 50:
            bonus = min(0.1, (len(data) - 50) / 500)
            quality_score += bonus
            
        quality_score = max(0.0, min(1.1, quality_score))
        
        is_valid = len(errors) == 0
        
        return is_valid, {
            "valid": is_valid,
            "data_points": len(data),
            "errors": errors,
            "warnings": warnings,
            "quality_score": quality_score
        }
    
    def _validate_time_span(self, data: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate time span of data."""
        errors = []
        
        if len(data) < 2:
            errors.append("Need at least 2 data points for time span validation")
            return False, errors
            
        timestamps = []
        for record in data:
            if "timestamp" in record and record["timestamp"]:
                try:
                    if isinstance(record["timestamp"], str):
                        # Use fromisoformat for flexible ISO parsing, with fallback to strptime
                        try:
                            ts = datetime.fromisoformat(record["timestamp"])
                            timestamps.append(ts)
                        except ValueError:
                            # Fallback to manual parsing for different formats
                            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
                                try:
                                    ts = datetime.strptime(record["timestamp"], fmt)
                                    timestamps.append(ts)
                                    break
                                except ValueError:
                                    continue
                    elif isinstance(record["timestamp"], datetime):
                        timestamps.append(record["timestamp"])
                except Exception:
                    errors.append(f"Invalid timestamp format: {record['timestamp']}")
                    
        if len(timestamps) < 2:
            errors.append("Insufficient valid timestamps for time span validation")
            return False, errors
            
        # Check time span duration
        min_time = min(timestamps)
        max_time = max(timestamps)
        time_span_hours = (max_time - min_time).total_seconds() / 3600
        
        if time_span_hours < self.thresholds["min_time_span_hours"]:
            errors.append(f"Time span too short: {time_span_hours:.1f}h < {self.thresholds['min_time_span_hours']}h")
            
        return len(errors) == 0, errors
    
    def _validate_metric_values(self, data: List[Dict[str, Any]]) -> List[str]:
        """Validate metric values against configured ranges."""
        errors = []
        
        for record in data:
            for metric_name, metric_config in self.valid_metrics.items():
                if metric_name in record:
                    value = record[metric_name]
                    if value is None:
                        continue
                        
                    # Type validation
                    expected_type = float if metric_config["type"] == "float" else int
                    try:
                        typed_value = expected_type(value)
                    except (ValueError, TypeError):
                        errors.append(f"Invalid type for {metric_name}: expected {metric_config['type']}")
                        continue
                        
                    # Range validation  
                    if typed_value < metric_config["min"] or typed_value > metric_config["max"]:
                        errors.append(f"Value out of range for {metric_name}: {typed_value}")
                        
        return errors
    
    def _validate_specific_metric_values(self, data: List[Dict[str, Any]], metrics: List[str]) -> List[str]:
        """Validate specific metric values against configured ranges."""
        errors = []
        
        for record in data:
            for metric_name in metrics:
                if metric_name in record and metric_name in self.valid_metrics:
                    value = record[metric_name]
                    if value is None:
                        continue
                        
                    metric_config = self.valid_metrics[metric_name]
                    
                    # Type validation
                    expected_type = float if metric_config["type"] == "float" else int
                    try:
                        typed_value = expected_type(value)
                    except (ValueError, TypeError):
                        errors.append(f"Invalid type for {metric_name}: expected {metric_config['type']}")
                        continue
                        
                    # Range validation  
                    if typed_value < metric_config["min"] or typed_value > metric_config["max"]:
                        errors.append(f"Value out of range for {metric_name}: {typed_value}")
                        
        return errors
    
    def validate_analysis_result(self, result: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate analysis result structure."""
        errors = []
        
        required_fields = ["type", "findings", "recommendations"]
        for field in required_fields:
            if field not in result:
                errors.append(f"Missing required field: {field}")
                
        # Validate findings structure
        if "findings" in result:
            if not isinstance(result["findings"], list):
                errors.append("Findings must be a list")
            elif len(result["findings"]) == 0:
                errors.append("Findings cannot be empty")
                
        # Validate recommendations structure  
        if "recommendations" in result:
            if not isinstance(result["recommendations"], list):
                errors.append("Recommendations must be a list")
                
        # Validate cost savings if present
        if "cost_savings" in result:
            cost_savings = result["cost_savings"]
            if isinstance(cost_savings, dict):
                if "percentage" in cost_savings:
                    pct = cost_savings["percentage"]
                    if not isinstance(pct, (int, float)) or pct < 0 or pct > 100:
                        errors.append("Cost savings percentage must be between 0 and 100")
                        
                if "total" in cost_savings:
                    total = cost_savings["total"]
                    if not isinstance(total, (int, float)) or total < 0:
                        errors.append("Cost savings total must be non-negative")
                        
        return len(errors) == 0, errors
    
    def calculate_quality_score(self, data: List[Dict[str, Any]], 
                              errors: List[str], warnings: List[str]) -> float:
        """Calculate data quality score (0-100)."""
        base_score = 100.0
        
        # Deduct for errors (major issues)
        error_penalty = len(errors) * 10
        base_score -= error_penalty
        
        # Deduct for warnings (minor issues)
        warning_penalty = len(warnings) * 5
        base_score -= warning_penalty
        
        # Bonus for large datasets (up to +10 points)
        if data and len(data) > 1000:
            bonus = min(10.0, len(data) / 1000)
            base_score += bonus
            
        return max(0.0, min(100.0, base_score))
    
    def _calculate_quality_score(self, validation_result: Dict[str, Any]) -> float:
        """Calculate quality score from validation result (0.0-1.1 scale)."""
        base_score = 1.0  # Start with perfect score
        
        # Deduct for errors (major penalty: -0.1 per error)
        errors = validation_result.get("errors", [])
        error_penalty = len(errors) * 0.1
        base_score -= error_penalty
        
        # Deduct for warnings (minor penalty: -0.05 per warning)
        warnings = validation_result.get("warnings", [])
        warning_penalty = len(warnings) * 0.05
        base_score -= warning_penalty
        
        # Bonus for large datasets (up to +0.1 bonus)
        data_points = validation_result.get("data_points", 0)
        if data_points > 50:
            bonus = min(0.1, (data_points - 50) / 500)  # Gradual bonus up to 0.1
            base_score += bonus
            
        return max(0.0, min(1.1, base_score))
    
    def validate_data(self, data: Any) -> bool:
        """Validate data - general validation method."""
        if isinstance(data, list):
            valid, _ = self.validate_raw_data(data)
            return valid
        elif isinstance(data, dict):
            # Check if it's an analysis request
            if "type" in data and "timeframe" in data:
                valid, _ = self.validate_analysis_request(data)
                return valid
            # Check if it's an analysis result
            elif "findings" in data:
                valid, _ = self.validate_analysis_result(data)
                return valid
        return True
    
    def validate_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Validate data against schema."""
        # Basic schema validation
        for field, field_type in schema.items():
            if field in data:
                if not isinstance(data[field], field_type):
                    return False
            elif field not in schema.get("optional_fields", []):
                return False
        return True
    
    def get_validation_errors(self) -> List[str]:
        """Get validation errors - placeholder for compatibility."""
        return []


__all__ = [
    "DataValidator",
]