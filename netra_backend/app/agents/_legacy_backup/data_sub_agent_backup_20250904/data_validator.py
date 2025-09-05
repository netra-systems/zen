"""Data Validator - Input and Output Data Validation

Validates data quality and integrity for reliable analysis.
Ensures analysis results meet quality standards.

Business Value: Prevents incorrect insights that could impact revenue.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from netra_backend.app.logging_config import central_logger


class DataValidator:
    """Validates data quality and integrity for analysis operations."""
    
    def __init__(self):
        self.logger = central_logger.get_logger("DataValidator")
        
        # Data quality thresholds
        self.thresholds = {
            "min_data_points": 10,
            "max_null_percentage": 20.0,
            "min_time_span_hours": 1.0,
            "max_outlier_percentage": 10.0
        }
        
        # Valid metric names and ranges
        self.valid_metrics = {
            "latency_ms": {"min": 0, "max": 30000, "type": "float"},
            "cost_cents": {"min": 0, "max": 1000, "type": "float"},
            "throughput": {"min": 0, "max": 10000, "type": "float"},
            "tokens_input": {"min": 0, "max": 100000, "type": "int"},
            "tokens_output": {"min": 0, "max": 100000, "type": "int"},
            "success_rate": {"min": 0, "max": 1.0, "type": "float"},
            "error_rate": {"min": 0, "max": 1.0, "type": "float"}
        }
    
    def validate_analysis_request(self, request: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate analysis request parameters."""
        errors = []
        
        # Validate required fields
        if not request.get("type"):
            errors.append("Analysis type is required")
        
        if not request.get("timeframe"):
            errors.append("Timeframe is required")
        
        # Validate analysis type
        valid_types = ["performance", "cost_optimization", "trend_analysis"]
        if request.get("type") not in valid_types:
            errors.append(f"Invalid analysis type. Must be one of: {valid_types}")
        
        # Validate timeframe format
        timeframe = request.get("timeframe", "")
        if not self._validate_timeframe_format(timeframe):
            errors.append("Invalid timeframe format. Use format like '24h', '7d', '30d'")
        
        # Validate metrics
        metrics = request.get("metrics", [])
        if metrics:
            invalid_metrics = [m for m in metrics if m not in self.valid_metrics]
            if invalid_metrics:
                errors.append(f"Invalid metrics: {invalid_metrics}")
        
        return len(errors) == 0, errors
    
    def validate_raw_data(self, data: List[Dict[str, Any]], metrics: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """Validate raw data quality and completeness."""
        validation_result = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "quality_score": 0.0,
            "data_points": len(data),
            "quality_metrics": {}
        }
        
        if not data:
            validation_result["valid"] = False
            validation_result["errors"].append("No data provided for validation")
            return False, validation_result
        
        # Check minimum data points
        if len(data) < self.thresholds["min_data_points"]:
            validation_result["warnings"].append(
                f"Low data point count: {len(data)} < {self.thresholds['min_data_points']}"
            )
        
        # Validate data structure and content
        structure_validation = self._validate_data_structure(data)
        validation_result["quality_metrics"]["structure"] = structure_validation
        
        # Validate metric values
        if metrics:
            metric_validation = self._validate_metric_values(data, metrics)
            validation_result["quality_metrics"]["metrics"] = metric_validation
            validation_result["warnings"].extend(metric_validation.get("warnings", []))
            validation_result["errors"].extend(metric_validation.get("errors", []))
        
        # Validate time span
        time_validation = self._validate_time_span(data)
        validation_result["quality_metrics"]["time_span"] = time_validation
        if time_validation.get("warning"):
            validation_result["warnings"].append(time_validation["warning"])
        
        # Calculate overall quality score
        validation_result["quality_score"] = self._calculate_quality_score(validation_result)
        
        # Determine if data is valid (no errors)
        validation_result["valid"] = len(validation_result["errors"]) == 0
        
        return validation_result["valid"], validation_result
    
    def validate_analysis_result(self, result: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate analysis result completeness and consistency."""
        errors = []
        
        # Check required result fields
        required_fields = ["summary", "findings", "recommendations"]
        for field in required_fields:
            if field not in result:
                errors.append(f"Missing required field: {field}")
        
        # Validate findings format
        findings = result.get("findings", [])
        if not isinstance(findings, list):
            errors.append("Findings must be a list")
        elif len(findings) == 0:
            errors.append("Analysis should produce at least one finding")
        
        # Validate recommendations format
        recommendations = result.get("recommendations", [])
        if not isinstance(recommendations, list):
            errors.append("Recommendations must be a list")
        
        # Validate cost savings if present
        if "cost_savings" in result:
            savings_validation = self._validate_cost_savings(result["cost_savings"])
            if not savings_validation[0]:
                errors.extend(savings_validation[1])
        
        return len(errors) == 0, errors
    
    def _validate_timeframe_format(self, timeframe: str) -> bool:
        """Validate timeframe format (e.g., '24h', '7d', '30d')."""
        pattern = r'^\d+[hdw]$'  # hours, days, or weeks
        return bool(re.match(pattern, timeframe))
    
    def _validate_data_structure(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate basic data structure consistency."""
        if not data:
            return {"valid": False, "error": "No data to validate"}
        
        # Check for required fields
        required_fields = ["timestamp", "user_id"]
        missing_fields = set()
        
        for row in data[:10]:  # Sample first 10 rows
            for field in required_fields:
                if field not in row:
                    missing_fields.add(field)
        
        # Count null values
        null_counts = {}
        for row in data:
            for key, value in row.items():
                if value is None or value == "":
                    null_counts[key] = null_counts.get(key, 0) + 1
        
        # Calculate null percentages
        null_percentages = {
            key: (count / len(data)) * 100 
            for key, count in null_counts.items()
        }
        
        high_null_fields = {
            key: pct for key, pct in null_percentages.items() 
            if pct > self.thresholds["max_null_percentage"]
        }
        
        return {
            "valid": len(missing_fields) == 0 and len(high_null_fields) == 0,
            "missing_fields": list(missing_fields),
            "high_null_fields": high_null_fields,
            "null_percentages": null_percentages
        }
    
    def _validate_metric_values(self, data: List[Dict[str, Any]], metrics: List[str]) -> Dict[str, Any]:
        """Validate metric values are within expected ranges."""
        validation = {"warnings": [], "errors": [], "outliers": {}}
        
        for metric in metrics:
            if metric not in self.valid_metrics:
                validation["warnings"].append(f"Unknown metric: {metric}")
                continue
            
            metric_config = self.valid_metrics[metric]
            values = []
            
            # Extract values for this metric
            for row in data:
                value = row.get(metric)
                if value is not None and value != "":
                    try:
                        if metric_config["type"] == "float":
                            values.append(float(value))
                        else:
                            values.append(int(value))
                    except (ValueError, TypeError):
                        validation["errors"].append(
                            f"Invalid {metric} value: {value} (expected {metric_config['type']})"
                        )
            
            if not values:
                validation["warnings"].append(f"No valid values found for metric: {metric}")
                continue
            
            # Check ranges
            out_of_range = [
                v for v in values 
                if v < metric_config["min"] or v > metric_config["max"]
            ]
            
            if out_of_range:
                validation["outliers"][metric] = {
                    "count": len(out_of_range),
                    "percentage": (len(out_of_range) / len(values)) * 100,
                    "range": f"{metric_config['min']}-{metric_config['max']}"
                }
                
                if validation["outliers"][metric]["percentage"] > self.thresholds["max_outlier_percentage"]:
                    validation["warnings"].append(
                        f"High outlier percentage for {metric}: "
                        f"{validation['outliers'][metric]['percentage']:.1f}%"
                    )
        
        return validation
    
    def _validate_time_span(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate time span of data for trend analysis validity."""
        if not data:
            return {"valid": False, "error": "No data for time span validation"}
        
        timestamps = []
        for row in data:
            ts = row.get("timestamp")
            if ts:
                if isinstance(ts, str):
                    try:
                        ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    except ValueError:
                        continue
                elif isinstance(ts, datetime):
                    pass
                else:
                    continue
                timestamps.append(ts)
        
        if len(timestamps) < 2:
            return {"valid": False, "warning": "Insufficient timestamps for time span analysis"}
        
        time_span = max(timestamps) - min(timestamps)
        time_span_hours = time_span.total_seconds() / 3600
        
        validation = {
            "valid": True,
            "time_span_hours": time_span_hours,
            "earliest": min(timestamps).isoformat(),
            "latest": max(timestamps).isoformat()
        }
        
        if time_span_hours < self.thresholds["min_time_span_hours"]:
            validation["warning"] = f"Short time span: {time_span_hours:.1f} hours"
        
        return validation
    
    def _validate_cost_savings(self, cost_savings: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate cost savings calculations."""
        errors = []
        
        if not isinstance(cost_savings, dict):
            return False, ["Cost savings must be a dictionary"]
        
        # Check for required fields
        if "savings_percentage" in cost_savings:
            pct = cost_savings["savings_percentage"]
            if not isinstance(pct, (int, float)) or pct < 0 or pct > 50:
                errors.append("Savings percentage must be between 0-50%")
        
        if "total_potential_savings_cents" in cost_savings:
            savings = cost_savings["total_potential_savings_cents"]
            if not isinstance(savings, (int, float)) or savings < 0:
                errors.append("Total savings must be non-negative")
        
        return len(errors) == 0, errors
    
    def _calculate_quality_score(self, validation_result: Dict[str, Any]) -> float:
        """Calculate overall data quality score (0-1)."""
        score = 1.0
        
        # Penalty for errors (major issues)
        error_count = len(validation_result.get("errors", []))
        if error_count > 0:
            score -= min(0.5, error_count * 0.1)
        
        # Penalty for warnings (minor issues)
        warning_count = len(validation_result.get("warnings", []))
        if warning_count > 0:
            score -= min(0.3, warning_count * 0.05)
        
        # Bonus for sufficient data points
        data_points = validation_result.get("data_points", 0)
        if data_points >= self.thresholds["min_data_points"] * 2:
            score += 0.1
        
        return max(0.0, min(1.0, score))
