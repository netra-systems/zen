"""Anomaly Detector - Consolidated Anomaly Detection Logic

Consolidates anomaly detection functionality from multiple fragmented files.
Contains ONLY business logic - no infrastructure concerns.
"""

from typing import Any, Dict, List, Optional, Tuple
import math

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AnomalyDetector:
    """Advanced anomaly detection with multiple statistical methods."""
    
    def __init__(self):
        self.detection_stats = {"anomalies_detected": 0, "total_analyzed": 0}
    
    def detect_anomalies(self, data: List[Dict[str, Any]], 
                        metric_field: str = "value",
                        method: str = "zscore",
                        threshold: float = 2.0) -> List[Dict[str, Any]]:
        """Detect anomalies using specified statistical method."""
        if not data or len(data) < 3:
            return []
        
        # Extract values for analysis
        values = self._extract_metric_values(data, metric_field)
        if len(values) < 3:
            return []
        
        # Apply selected detection method
        if method == "zscore":
            anomalies = self._detect_zscore_anomalies(data, values, threshold, metric_field)
        elif method == "iqr":
            anomalies = self._detect_iqr_anomalies(data, values, metric_field)
        elif method == "isolation_forest":
            anomalies = self._detect_isolation_forest_anomalies(data, values, metric_field)
        else:
            logger.warning(f"Unknown anomaly detection method: {method}, using zscore")
            anomalies = self._detect_zscore_anomalies(data, values, threshold, metric_field)
        
        # Update statistics
        self.detection_stats["total_analyzed"] += len(data)
        self.detection_stats["anomalies_detected"] += len(anomalies)
        
        return anomalies
    
    def _extract_metric_values(self, data: List[Dict[str, Any]], metric_field: str) -> List[float]:
        """Extract numeric values from data for analysis."""
        values = []
        for item in data:
            value = item.get(metric_field)
            if value is not None:
                try:
                    values.append(float(value))
                except (ValueError, TypeError):
                    continue
        return values
    
    def _detect_zscore_anomalies(self, data: List[Dict[str, Any]], 
                                values: List[float], 
                                threshold: float, 
                                metric_field: str) -> List[Dict[str, Any]]:
        """Detect anomalies using Z-score method."""
        if len(values) < 3:
            return []
        
        # Calculate statistics
        mean_val = sum(values) / len(values)
        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return []  # No variation in data
        
        anomalies = []
        for i, item in enumerate(data):
            value = item.get(metric_field)
            if value is not None:
                try:
                    value = float(value)
                    z_score = abs((value - mean_val) / std_dev)
                    
                    if z_score > threshold:
                        anomalies.append({
                            "index": i,
                            "timestamp": item.get("timestamp"),
                            "value": value,
                            "z_score": round(z_score, 3),
                            "deviation_type": "high" if value > mean_val else "low",
                            "method": "zscore",
                            "severity": self._calculate_severity(z_score, threshold)
                        })
                except (ValueError, TypeError):
                    continue
        
        return anomalies
    
    def _detect_iqr_anomalies(self, data: List[Dict[str, Any]], 
                             values: List[float], 
                             metric_field: str) -> List[Dict[str, Any]]:
        """Detect anomalies using Interquartile Range (IQR) method."""
        if len(values) < 4:
            return []
        
        # Calculate quartiles
        sorted_values = sorted(values)
        n = len(sorted_values)
        q1_idx = n // 4
        q3_idx = 3 * n // 4
        
        q1 = sorted_values[q1_idx]
        q3 = sorted_values[q3_idx]
        iqr = q3 - q1
        
        # Calculate outlier bounds
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        anomalies = []
        for i, item in enumerate(data):
            value = item.get(metric_field)
            if value is not None:
                try:
                    value = float(value)
                    
                    if value < lower_bound or value > upper_bound:
                        # Calculate how far outside the bounds
                        distance = max(0, lower_bound - value) + max(0, value - upper_bound)
                        outlier_score = distance / iqr if iqr > 0 else 0
                        
                        anomalies.append({
                            "index": i,
                            "timestamp": item.get("timestamp"),
                            "value": value,
                            "iqr_score": round(outlier_score, 3),
                            "bounds": {"lower": lower_bound, "upper": upper_bound},
                            "deviation_type": "low" if value < lower_bound else "high",
                            "method": "iqr",
                            "severity": self._calculate_iqr_severity(outlier_score)
                        })
                except (ValueError, TypeError):
                    continue
        
        return anomalies
    
    def _detect_isolation_forest_anomalies(self, data: List[Dict[str, Any]], 
                                         values: List[float], 
                                         metric_field: str) -> List[Dict[str, Any]]:
        """Detect anomalies using simplified isolation forest approach."""
        if len(values) < 8:
            return []  # Need sufficient data for isolation forest
        
        # Simplified isolation forest: use random sampling and depth analysis
        anomalies = []
        n_trees = 10
        contamination = 0.1  # Expect 10% anomalies
        
        # Calculate anomaly scores for each point
        anomaly_scores = []
        for value in values:
            score = self._calculate_isolation_score(value, values, n_trees)
            anomaly_scores.append(score)
        
        # Determine threshold based on contamination rate
        sorted_scores = sorted(anomaly_scores, reverse=True)
        threshold_idx = max(0, int(len(sorted_scores) * contamination))
        threshold = sorted_scores[threshold_idx] if threshold_idx < len(sorted_scores) else max(sorted_scores)
        
        # Identify anomalies above threshold
        for i, item in enumerate(data):
            if i < len(anomaly_scores) and anomaly_scores[i] >= threshold:
                value = item.get(metric_field)
                if value is not None:
                    anomalies.append({
                        "index": i,
                        "timestamp": item.get("timestamp"),
                        "value": float(value),
                        "isolation_score": round(anomaly_scores[i], 3),
                        "method": "isolation_forest",
                        "severity": self._calculate_isolation_severity(anomaly_scores[i])
                    })
        
        return anomalies
    
    def _calculate_isolation_score(self, value: float, all_values: List[float], n_trees: int) -> float:
        """Calculate isolation score for a single value."""
        import random
        
        scores = []
        for _ in range(n_trees):
            depth = self._isolation_path_length(value, all_values.copy())
            scores.append(depth)
        
        # Average path length, normalized
        avg_depth = sum(scores) / len(scores)
        expected_depth = self._expected_path_length(len(all_values))
        
        return math.pow(2, -avg_depth / expected_depth) if expected_depth > 0 else 0
    
    def _isolation_path_length(self, value: float, values: List[float]) -> int:
        """Calculate path length for isolation of a value."""
        import random
        
        if len(values) <= 1:
            return 0
        
        depth = 0
        current_values = values.copy()
        
        while len(current_values) > 1 and depth < 20:  # Limit depth to prevent infinite loops
            # Random split
            min_val = min(current_values)
            max_val = max(current_values)
            
            if min_val == max_val:
                break
            
            split_point = random.uniform(min_val, max_val)
            
            if value < split_point:
                current_values = [v for v in current_values if v < split_point]
            else:
                current_values = [v for v in current_values if v >= split_point]
            
            depth += 1
        
        return depth
    
    def _expected_path_length(self, n: int) -> float:
        """Calculate expected path length for n points."""
        if n <= 1:
            return 0
        return 2 * (math.log(n - 1) + 0.5772156649) - (2 * (n - 1) / n)
    
    def _calculate_severity(self, z_score: float, threshold: float) -> str:
        """Calculate severity level based on Z-score."""
        if z_score >= threshold * 2:
            return "critical"
        elif z_score >= threshold * 1.5:
            return "high"
        elif z_score >= threshold:
            return "medium"
        else:
            return "low"
    
    def _calculate_iqr_severity(self, iqr_score: float) -> str:
        """Calculate severity level based on IQR score."""
        if iqr_score >= 3.0:
            return "critical"
        elif iqr_score >= 2.0:
            return "high"
        elif iqr_score >= 1.0:
            return "medium"
        else:
            return "low"
    
    def _calculate_isolation_severity(self, isolation_score: float) -> str:
        """Calculate severity level based on isolation score."""
        if isolation_score >= 0.8:
            return "critical"
        elif isolation_score >= 0.6:
            return "high"
        elif isolation_score >= 0.4:
            return "medium"
        else:
            return "low"
    
    def analyze_anomaly_patterns(self, anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns in detected anomalies."""
        if not anomalies:
            return {"patterns": [], "summary": "No anomalies detected"}
        
        # Group by severity
        severity_counts = {}
        for anomaly in anomalies:
            severity = anomaly.get("severity", "unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Group by deviation type
        deviation_counts = {}
        for anomaly in anomalies:
            dev_type = anomaly.get("deviation_type", "unknown")
            deviation_counts[dev_type] = deviation_counts.get(dev_type, 0) + 1
        
        # Temporal pattern analysis
        timestamps = [a.get("timestamp") for a in anomalies if a.get("timestamp")]
        temporal_pattern = self._analyze_temporal_pattern(timestamps)
        
        return {
            "total_anomalies": len(anomalies),
            "severity_distribution": severity_counts,
            "deviation_distribution": deviation_counts,
            "temporal_pattern": temporal_pattern,
            "anomaly_rate": len(anomalies) / self.detection_stats["total_analyzed"] * 100 if self.detection_stats["total_analyzed"] > 0 else 0,
            "summary": f"Detected {len(anomalies)} anomalies with {severity_counts.get('critical', 0)} critical issues"
        }
    
    def _analyze_temporal_pattern(self, timestamps: List[str]) -> Dict[str, Any]:
        """Analyze temporal patterns in anomaly occurrences."""
        if not timestamps:
            return {"pattern": "none", "clustering": False}
        
        # Simple temporal clustering analysis
        from datetime import datetime
        
        parsed_times = []
        for ts in timestamps:
            try:
                parsed_times.append(datetime.fromisoformat(ts.replace('Z', '+00:00')))
            except:
                continue
        
        if len(parsed_times) < 2:
            return {"pattern": "insufficient_data", "clustering": False}
        
        parsed_times.sort()
        
        # Calculate time differences
        time_diffs = []
        for i in range(1, len(parsed_times)):
            diff = (parsed_times[i] - parsed_times[i-1]).total_seconds()
            time_diffs.append(diff)
        
        # Simple clustering detection: if most anomalies occur within short time windows
        short_intervals = sum(1 for diff in time_diffs if diff < 3600)  # Within 1 hour
        clustering = short_intervals / len(time_diffs) > 0.5 if time_diffs else False
        
        return {
            "pattern": "clustered" if clustering else "distributed",
            "clustering": clustering,
            "total_timespan_hours": (parsed_times[-1] - parsed_times[0]).total_seconds() / 3600,
            "avg_interval_minutes": sum(time_diffs) / len(time_diffs) / 60 if time_diffs else 0
        }
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """Get anomaly detection statistics."""
        stats = self.detection_stats.copy()
        if stats["total_analyzed"] > 0:
            stats["overall_anomaly_rate"] = stats["anomalies_detected"] / stats["total_analyzed"] * 100
        else:
            stats["overall_anomaly_rate"] = 0.0
        
        return stats
    
    def reset_stats(self) -> None:
        """Reset detection statistics."""
        self.detection_stats = {"anomalies_detected": 0, "total_analyzed": 0}