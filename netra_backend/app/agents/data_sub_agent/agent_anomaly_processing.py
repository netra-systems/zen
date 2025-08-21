"""Anomaly processing utilities for DataSubAgent."""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, UTC

from netra_backend.app.schemas.shared_types import DataAnalysisResponse, AnomalyDetectionResponse, AnomalySeverity
from netra_backend.app.logging_config import central_logger as logger


class AnomalyProcessor:
    """Handles anomaly processing operations for DataSubAgent."""
    
    def __init__(self, agent):
        self.agent = agent
    
    def convert_anomaly_details(self, llm_anomaly_list: list) -> list:
        """Convert LLM anomaly format to AnomalyDetail format."""
        converted_details = []
        for item in llm_anomaly_list:
            detail = self._process_anomaly_item(item)
            if detail:
                converted_details.append(detail)
        return converted_details
    
    def _process_anomaly_item(self, item: dict) -> Optional[dict]:
        """Process single anomaly item if valid dict."""
        if isinstance(item, dict):
            detail = self._create_anomaly_detail(item)
            return detail.model_dump()
        return None
    
    def _create_anomaly_detail(self, item: dict) -> 'AnomalyDetail':
        """Create AnomalyDetail from LLM response."""
        from netra_backend.app.schemas.shared_types import AnomalyDetail
        timestamp = self._extract_timestamp(item)
        fields = self._extract_anomaly_fields(item)
        severity = self._map_severity(item, self._get_severity_mapping())
        return self._build_anomaly_detail(timestamp, fields, severity)
    
    def _build_anomaly_detail(self, timestamp, fields: dict, severity) -> 'AnomalyDetail':
        """Build AnomalyDetail object from components."""
        from netra_backend.app.schemas.shared_types import AnomalyDetail
        core_params = self._create_anomaly_core_params(timestamp, fields, severity)
        return AnomalyDetail(**core_params)
    
    def _create_anomaly_core_params(self, timestamp, fields: dict, severity) -> dict:
        """Create core parameters for AnomalyDetail creation."""
        return {
            'timestamp': timestamp, 'metric_name': fields['metric_name'],
            'actual_value': fields['actual_value'], 'expected_value': fields['expected_value'],
            'deviation_percentage': fields['deviation_percentage'], 'z_score': fields['z_score'],
            'severity': severity, 'description': fields['description']
        }
    
    def _get_severity_mapping(self) -> Dict[str, Any]:
        """Get severity mapping for anomaly details."""
        return {
            'high': AnomalySeverity.HIGH,
            'medium': AnomalySeverity.MEDIUM,
            'low': AnomalySeverity.LOW,
            'critical': AnomalySeverity.CRITICAL
        }
    
    def _extract_timestamp(self, item: dict):
        """Extract timestamp from anomaly item."""
        default_timestamp = datetime.now(UTC)
        if 'timestamp' not in item:
            return default_timestamp
        return self._parse_timestamp_string(item['timestamp'], default_timestamp)
    
    def _parse_timestamp_string(self, timestamp_str: str, default_timestamp):
        """Parse timestamp string with error handling."""
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, TypeError, AttributeError):
            return default_timestamp
    
    def _extract_anomaly_fields(self, item: dict) -> Dict[str, Any]:
        """Extract all anomaly fields from item."""
        basic_fields = self._extract_basic_anomaly_fields(item)
        metric_fields = self._extract_metric_anomaly_fields(item)
        return {**basic_fields, **metric_fields}
    
    def _extract_basic_anomaly_fields(self, item: dict) -> Dict[str, Any]:
        """Extract basic anomaly fields."""
        return {
            'metric_name': item.get('type', 'unknown_metric'),
            'description': item.get('description', '')
        }
    
    def _extract_metric_anomaly_fields(self, item: dict) -> Dict[str, Any]:
        """Extract metric-specific anomaly fields."""
        return {
            'actual_value': item.get('actual_value', 0.0),
            'expected_value': item.get('expected_value', 0.0),
            'deviation_percentage': item.get('deviation_percentage', 0.0),
            'z_score': item.get('z_score', 0.0)
        }
    
    def _map_severity(self, item: dict, severity_map: Dict) -> Any:
        """Map severity string to enum value."""
        severity_str = item.get('severity', 'low').lower()
        return severity_map.get(severity_str, AnomalySeverity.LOW)
    
    def fix_anomaly_format_issues(self, result_dict: dict) -> None:
        """Fix common format issues from LLM responses."""
        if 'anomalies_detected' in result_dict and isinstance(result_dict['anomalies_detected'], list):
            anomaly_list = result_dict['anomalies_detected']
            result_dict['anomalies_detected'] = bool(anomaly_list)
            result_dict['anomaly_details'] = anomaly_list
            result_dict['anomaly_count'] = len(anomaly_list)
    
    def convert_anomaly_details_format(self, result_dict: dict) -> None:
        """Convert LLM anomaly format to AnomalyDetail format."""
        if 'anomaly_details' in result_dict and isinstance(result_dict['anomaly_details'], list):
            result_dict['anomaly_details'] = self.convert_anomaly_details(result_dict['anomaly_details'])