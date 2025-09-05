"""Data Processor - Consolidated Data Processing Logic

Consolidates data processing functionality from multiple fragmented files.
Contains ONLY business logic - no infrastructure concerns.
"""

from typing import Any, Dict, List, Optional, Union

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class DataProcessor:
    """Data processing engine for validation, transformation, and enrichment."""
    
    def __init__(self):
        self.processing_stats = {"processed": 0, "errors": 0}
    
    async def process_analysis_request(self, request: Dict[str, Union[str, List[str], Optional[str]]]) -> Dict[str, Any]:
        """Process and validate analysis request."""
        processed_request = {
            "type": self._validate_analysis_type(request.get("type", "performance")),
            "timeframe": self._validate_timeframe(request.get("timeframe", "24h")),
            "metrics": self._validate_metrics(request.get("metrics", [])),
            "filters": self._validate_filters(request.get("filters", {})),
            "user_id": request.get("user_id")
        }
        
        return processed_request
    
    def _validate_analysis_type(self, analysis_type: str) -> str:
        """Validate and normalize analysis type."""
        valid_types = ["performance", "cost_optimization", "trend_analysis", "anomaly_detection"]
        if analysis_type in valid_types:
            return analysis_type
        
        logger.warning(f"Invalid analysis type '{analysis_type}', defaulting to 'performance'")
        return "performance"
    
    def _validate_timeframe(self, timeframe: str) -> str:
        """Validate and normalize timeframe."""
        valid_timeframes = ["1h", "24h", "7d", "30d", "90d"]
        if timeframe in valid_timeframes:
            return timeframe
        
        logger.warning(f"Invalid timeframe '{timeframe}', defaulting to '24h'")
        return "24h"
    
    def _validate_metrics(self, metrics: Union[List[str], str, None]) -> List[str]:
        """Validate and normalize metrics list."""
        if isinstance(metrics, str):
            metrics = [metrics]
        elif not isinstance(metrics, list):
            metrics = []
        
        valid_metrics = [
            "latency_ms", "latency_p50", "latency_p95", "latency_p99",
            "cost_cents", "throughput", "requests_per_second", "error_rate"
        ]
        
        validated_metrics = [m for m in metrics if m in valid_metrics]
        
        if not validated_metrics:
            # Default metrics for analysis
            validated_metrics = ["latency_ms", "cost_cents", "throughput"]
        
        return validated_metrics
    
    def _validate_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize filters."""
        validated_filters = {}
        
        # Validate user_id filter
        if "user_id" in filters and isinstance(filters["user_id"], (int, str)):
            try:
                validated_filters["user_id"] = int(filters["user_id"])
            except ValueError:
                logger.warning(f"Invalid user_id filter: {filters['user_id']}")
        
        # Validate workload_id filter
        if "workload_id" in filters and isinstance(filters["workload_id"], str):
            validated_filters["workload_id"] = filters["workload_id"]
        
        # Validate service_name filter
        if "service_name" in filters and isinstance(filters["service_name"], str):
            validated_filters["service_name"] = filters["service_name"]
        
        return validated_filters
    
    async def enrich_analysis_result(self, result: Dict[str, Any], original_request: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich analysis result with metadata and context."""
        enriched_result = result.copy()
        
        # Add request context
        enriched_result["request_context"] = {
            "analysis_type": original_request.get("type"),
            "timeframe": original_request.get("timeframe"),
            "metrics_requested": original_request.get("metrics"),
        }
        
        # Add processing metadata
        enriched_result["processing_metadata"] = {
            "processed_at": self._get_current_timestamp(),
            "processor_version": "1.0.0",
            "data_quality": self._assess_data_quality(result)
        }
        
        # Update processing stats
        self.processing_stats["processed"] += 1
        
        return enriched_result
    
    def _assess_data_quality(self, result: Dict[str, Any]) -> str:
        """Assess the quality of analysis results."""
        data_points = result.get("data_points", 0)
        
        if data_points >= 100:
            return "high"
        elif data_points >= 20:
            return "medium"
        elif data_points >= 5:
            return "low"
        else:
            return "insufficient"
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    async def validate_data_integrity(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate data integrity and completeness."""
        if not data:
            return {"valid": False, "reason": "No data provided"}
        
        # Check for required fields
        required_fields = ["timestamp", "user_id"]
        missing_fields = []
        
        for field in required_fields:
            if not any(item.get(field) for item in data):
                missing_fields.append(field)
        
        if missing_fields:
            return {
                "valid": False, 
                "reason": f"Missing required fields: {', '.join(missing_fields)}"
            }
        
        # Check data freshness
        timestamps = [item.get("timestamp") for item in data if item.get("timestamp")]
        if timestamps:
            # Data quality assessment based on timestamp distribution
            data_span = len(set(timestamps))
            freshness = "fresh" if data_span > len(data) * 0.8 else "stale"
        else:
            freshness = "unknown"
        
        return {
            "valid": True,
            "data_points": len(data),
            "freshness": freshness,
            "completeness": self._calculate_completeness(data)
        }
    
    def _calculate_completeness(self, data: List[Dict[str, Any]]) -> float:
        """Calculate data completeness percentage."""
        if not data:
            return 0.0
        
        important_fields = ["timestamp", "user_id", "latency_p50", "cost_cents", "throughput"]
        total_possible = len(data) * len(important_fields)
        total_present = 0
        
        for item in data:
            for field in important_fields:
                if item.get(field) is not None:
                    total_present += 1
        
        return (total_present / total_possible) * 100 if total_possible > 0 else 0.0
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return self.processing_stats.copy()
    
    def reset_stats(self) -> None:
        """Reset processing statistics."""
        self.processing_stats = {"processed": 0, "errors": 0}