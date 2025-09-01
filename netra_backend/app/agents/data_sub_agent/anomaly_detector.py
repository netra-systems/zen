"""Modernized anomaly detection module implementing BaseExecutionInterface.

Business Value: Standardized anomaly detection with reliability patterns.
Provides consistent execution workflow for anomaly detection operations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from netra_backend.app.agents.base.errors import (
    AgentExecutionError,
    ValidationError,
)
from netra_backend.app.core.unified_error_handler import agent_error_handler as ExecutionErrorHandler
from netra_backend.app.agents.base.executor import BaseExecutionEngine
from netra_backend.app.agents.base.interface import (
    
    ExecutionContext,
    ExecutionResult)
from netra_backend.app.schemas.core_enums import 
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.schemas.shared_types import (
    AnomalyDetail,
    AnomalyDetectionResponse,
    AnomalySeverity,
)


class AnomalyDetector:
    """Modernized anomaly detection with BaseExecutionInterface."""
    
    def __init__(self, query_builder: Any, clickhouse_ops: Any, 
                 redis_manager: Any, websocket_manager=None) -> None:
        self.agent_name = "AnomalyDetector"
        self.websocket_manager = websocket_manager
        self.query_builder = query_builder
        self.clickhouse_ops = clickhouse_ops
        self.redis_manager = redis_manager
        self._init_modern_infrastructure()
    
    def _init_modern_infrastructure(self) -> None:
        """Initialize modern execution infrastructure."""
        self.monitor = ExecutionMonitor()
        self.reliability_manager = ReliabilityManager()
        self.execution_engine = BaseExecutionEngine(
            self.reliability_manager, self.monitor
        )
        self.error_handler = ExecutionErrorHandler
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate anomaly detection preconditions."""
        metadata = context.metadata or {}
        if not metadata.get('user_id'):
            raise ValidationError("user_id required in metadata")
        if not metadata.get('metric_name'):
            raise ValidationError("metric_name required in metadata")
        if not metadata.get('time_range'):
            raise ValidationError("time_range required in metadata")
        return True
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core anomaly detection logic."""
        params = self._extract_execution_parameters(context)
        await self._send_execution_start_status(context, params['metric_name'])
        response = await self._process_anomaly_detection(params)
        await self._send_execution_complete_status(context, response)
        return {"anomaly_response": response}
    
    def _extract_execution_parameters(self, context: ExecutionContext) -> Dict[str, Any]:
        """Extract and validate execution parameters from context."""
        metadata = context.metadata
        return {
            'user_id': metadata['user_id'],
            'metric_name': metadata['metric_name'],
            'time_range': metadata['time_range'],
            'z_score_threshold': metadata.get('z_score_threshold', 2.0)
        }
    
    async def _send_execution_start_status(self, context: ExecutionContext, 
                                         metric_name: str) -> None:
        """Send execution start status update."""
        await self.send_status_update(
            context, "executing", 
            f"Detecting anomalies in {metric_name}..."
        )
    
    async def _process_anomaly_detection(self, params: Dict[str, Any]) -> Any:
        """Process the anomaly detection with given parameters."""
        data = await self._fetch_anomaly_data(
            params['user_id'], params['metric_name'], 
            params['time_range'], params['z_score_threshold']
        )
        return self._convert_to_typed_response(
            data, params['metric_name'], 
            params['z_score_threshold'], params['time_range']
        )
    
    async def _send_execution_complete_status(self, context: ExecutionContext, 
                                            response: Any) -> None:
        """Send execution complete status update."""
        await self.send_status_update(
            context, "completed", 
            f"Found {response.anomaly_count} anomalies"
        )
    
    async def detect_anomalies(
        self, user_id: int, metric_name: str,
        time_range: Tuple[datetime, datetime],
        z_score_threshold: float = 2.0
    ) -> AnomalyDetectionResponse:
        """Public interface for anomaly detection with modern patterns."""
        data = await self._fetch_anomaly_data(
            user_id, metric_name, time_range, z_score_threshold
        )
        return self._convert_to_typed_response(
            data, metric_name, z_score_threshold, time_range
        )
    
    async def _fetch_anomaly_data(self, user_id: int, metric_name: str, 
                                 time_range: Tuple[datetime, datetime],
                                 z_score_threshold: float) -> Optional[List[Dict]]:
        """Fetch anomaly data from ClickHouse with caching."""
        start_time, end_time = time_range
        query_params = self._prepare_query_parameters(
            user_id, metric_name, start_time, end_time, z_score_threshold
        )
        return await self.clickhouse_ops.fetch_data(
            query_params['query'], query_params['cache_key'], self.redis_manager
        )
    
    def _prepare_query_parameters(self, user_id: int, metric_name: str,
                                start_time: datetime, end_time: datetime,
                                z_score_threshold: float) -> Dict[str, str]:
        """Prepare query and cache key for anomaly data fetch."""
        query = self._build_anomaly_query(
            user_id, metric_name, start_time, end_time, z_score_threshold
        )
        cache_key = self._build_anomaly_cache_key(
            user_id, metric_name, start_time, z_score_threshold
        )
        return {'query': query, 'cache_key': cache_key}
    
    def _build_anomaly_query(self, user_id: int, metric_name: str, 
                           start_time: datetime, end_time: datetime,
                           z_score_threshold: float) -> str:
        """Build anomaly detection query."""
        return self.query_builder.build_anomaly_detection_query(
            user_id, metric_name, start_time, end_time, z_score_threshold
        )
    
    def _build_anomaly_cache_key(self, user_id: int, metric_name: str,
                               start_time: datetime, 
                               z_score_threshold: float) -> str:
        """Build cache key for anomaly detection."""
        return (
            f"anomalies:{user_id}:{metric_name}:"
            f"{start_time.isoformat()}:{z_score_threshold}"
        )
    
    def _convert_to_typed_response(
        self, data: Optional[List[Dict]], metric_name: str,
        z_score_threshold: float, time_range: Tuple[datetime, datetime]
    ) -> AnomalyDetectionResponse:
        """Convert raw data to typed AnomalyDetectionResponse."""
        if not data:
            return self._create_no_anomalies_response(
                metric_name, z_score_threshold, time_range
            )
        return self._build_anomalies_response(
            data, metric_name, z_score_threshold, time_range
        )
    
    def _create_no_anomalies_response(
        self, metric_name: str, z_score_threshold: float,
        time_range: Tuple[datetime, datetime]
    ) -> AnomalyDetectionResponse:
        """Create typed response for no anomalies found."""
        analysis_period = self._create_analysis_period(time_range)
        recommendations = self._create_no_anomalies_recommendations(metric_name)
        return self._build_no_anomalies_response_object(
            z_score_threshold, analysis_period, recommendations
        )
    
    def _create_analysis_period(self, time_range: Tuple[datetime, datetime]) -> Dict[str, datetime]:
        """Create analysis period dictionary from time range."""
        start_time, end_time = time_range
        return {"start": start_time, "end": end_time}
    
    def _create_no_anomalies_recommendations(self, metric_name: str) -> List[str]:
        """Create recommendations for no anomalies case."""
        return [f"Continue monitoring {metric_name}"]
    
    def _build_no_anomalies_response_object(
        self, z_score_threshold: float, analysis_period: Dict[str, datetime],
        recommendations: List[str]
    ) -> AnomalyDetectionResponse:
        """Build AnomalyDetectionResponse object for no anomalies."""
        return AnomalyDetectionResponse(
            anomalies_detected=False,
            anomaly_count=0,
            confidence_score=0.95,
            threshold_used=z_score_threshold,
            analysis_period=analysis_period,
            recommended_actions=recommendations
        )
    
    def _build_anomalies_response(
        self, data: List[Dict], metric_name: str,
        z_score_threshold: float, time_range: Tuple[datetime, datetime]
    ) -> AnomalyDetectionResponse:
        """Build typed response for detected anomalies."""
        anomaly_details = self._convert_to_anomaly_details(data, metric_name)
        max_severity = self._determine_max_severity(data)
        return self._create_anomaly_response_object(
            data, anomaly_details, max_severity, z_score_threshold, time_range
        )
    
    def _create_anomaly_response_object(
        self, data: List[Dict], anomaly_details: List[AnomalyDetail],
        max_severity: AnomalySeverity, z_score_threshold: float,
        time_range: Tuple[datetime, datetime]
    ) -> AnomalyDetectionResponse:
        """Create AnomalyDetectionResponse object."""
        response_params = self._prepare_anomaly_response_params(
            data, anomaly_details, max_severity, z_score_threshold, time_range
        )
        return self._build_anomaly_response_object(response_params)
    
    def _prepare_anomaly_response_params(
        self, data: List[Dict], anomaly_details: List[AnomalyDetail],
        max_severity: AnomalySeverity, z_score_threshold: float,
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Prepare parameters for anomaly response object creation."""
        start_time, end_time = time_range
        base_params = self._build_base_anomaly_params(data, anomaly_details, max_severity)
        extended_params = self._build_extended_anomaly_params(
            z_score_threshold, start_time, end_time, max_severity
        )
        return {**base_params, **extended_params}
    
    def _build_base_anomaly_params(
        self, data: List[Dict], anomaly_details: List[AnomalyDetail],
        max_severity: AnomalySeverity
    ) -> Dict[str, Any]:
        """Build base anomaly response parameters."""
        return {
            'anomalies_detected': True,
            'anomaly_count': len(data),
            'anomaly_details': anomaly_details[:50],
            'confidence_score': 0.85,
            'severity': max_severity
        }
    
    def _build_extended_anomaly_params(
        self, z_score_threshold: float, start_time: datetime,
        end_time: datetime, max_severity: AnomalySeverity
    ) -> Dict[str, Any]:
        """Build extended anomaly response parameters."""
        return {
            'threshold_used': z_score_threshold,
            'analysis_period': {"start": start_time, "end": end_time},
            'recommended_actions': self._generate_recommendations(max_severity)
        }
    
    def _build_anomaly_response_object(self, params: Dict[str, Any]) -> AnomalyDetectionResponse:
        """Build AnomalyDetectionResponse object from prepared parameters."""
        return AnomalyDetectionResponse(**params)
    
    def _convert_to_anomaly_details(self, data: List[Dict], 
                                  metric_name: str) -> List[AnomalyDetail]:
        """Convert raw data to typed AnomalyDetail objects."""
        return [self._convert_single_anomaly(row, metric_name) for row in data]
    
    def _convert_single_anomaly(self, row: Dict, 
                              metric_name: str) -> AnomalyDetail:
        """Convert single anomaly to typed AnomalyDetail."""
        values = self._extract_anomaly_values(row)
        return self._create_anomaly_detail_object(
            row, metric_name, values
        )
    
    def _extract_anomaly_values(self, row: Dict) -> Tuple[float, float, float]:
        """Extract and convert anomaly values from row."""
        actual_value = float(row.get('metric_value', 0))
        expected_value = float(row.get('expected_value', actual_value))
        z_score = float(row.get('z_score', 0))
        return actual_value, expected_value, z_score
    
    def _create_anomaly_detail_object(
        self, row: Dict, metric_name: str, 
        values: Tuple[float, float, float]
    ) -> AnomalyDetail:
        """Create AnomalyDetail object from extracted values."""
        detail_params = self._prepare_anomaly_detail_params(
            row, metric_name, values
        )
        return self._build_anomaly_detail_object(detail_params)
    
    def _prepare_anomaly_detail_params(
        self, row: Dict, metric_name: str, 
        values: Tuple[float, float, float]
    ) -> Dict[str, Any]:
        """Prepare parameters for anomaly detail object creation."""
        actual_value, expected_value, z_score = values
        deviation_pct = self._calculate_deviation_percentage(actual_value, expected_value)
        base_params = self._build_base_detail_params(row, metric_name, actual_value, expected_value)
        extended_params = self._build_extended_detail_params(deviation_pct, z_score)
        return {**base_params, **extended_params}
    
    def _build_base_detail_params(
        self, row: Dict, metric_name: str, 
        actual_value: float, expected_value: float
    ) -> Dict[str, Any]:
        """Build base anomaly detail parameters."""
        return {
            'timestamp': row.get('timestamp', datetime.now(timezone.utc)),
            'metric_name': metric_name,
            'actual_value': actual_value,
            'expected_value': expected_value
        }
    
    def _build_extended_detail_params(
        self, deviation_pct: float, z_score: float
    ) -> Dict[str, Any]:
        """Build extended anomaly detail parameters."""
        return {
            'deviation_percentage': deviation_pct,
            'z_score': z_score,
            'severity': self._determine_severity(z_score)
        }
    
    def _build_anomaly_detail_object(self, params: Dict[str, Any]) -> AnomalyDetail:
        """Build AnomalyDetail object from prepared parameters."""
        return AnomalyDetail(**params)
    
    def _calculate_deviation_percentage(self, actual: float, 
                                      expected: float) -> float:
        """Calculate deviation percentage between actual and expected."""
        if expected == 0:
            return 100.0 if actual != 0 else 0.0
        return abs((actual - expected) / expected) * 100.0
    
    def _determine_severity(self, z_score: float) -> AnomalySeverity:
        """Determine anomaly severity based on z-score."""
        abs_z = abs(z_score)
        if abs_z > 4:
            return AnomalySeverity.CRITICAL
        elif abs_z > 3:
            return AnomalySeverity.HIGH
        elif abs_z > 2:
            return AnomalySeverity.MEDIUM
        return AnomalySeverity.LOW
    
    def _determine_max_severity(self, data: List[Dict]) -> AnomalySeverity:
        """Determine maximum severity from all anomalies."""
        severities = self._extract_all_severities(data)
        return self._find_highest_severity(severities)
    
    def _extract_all_severities(self, data: List[Dict]) -> List[AnomalySeverity]:
        """Extract severity levels from all anomalies."""
        return [self._determine_severity(row.get('z_score', 0)) for row in data]
    
    def _find_highest_severity(self, severities: List[AnomalySeverity]) -> AnomalySeverity:
        """Find highest severity from list of severities."""
        severity_order = [
            AnomalySeverity.CRITICAL, AnomalySeverity.HIGH,
            AnomalySeverity.MEDIUM, AnomalySeverity.LOW
        ]
        return next((s for s in severity_order if s in severities), 
                   AnomalySeverity.LOW)
    
    def _generate_recommendations(self, severity: AnomalySeverity) -> List[str]:
        """Generate recommendations based on severity."""
        base_recommendations = ["Review recent system changes"]
        if severity in [AnomalySeverity.HIGH, AnomalySeverity.CRITICAL]:
            base_recommendations.extend([
                "Investigate immediately",
                "Consider alerting on-call team"
            ])
        return base_recommendations
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get anomaly detector health status."""
        return {
            "status": "healthy",
            "monitor": self.monitor.get_health_status(),
            "reliability": self.reliability_manager.get_health_status(),
            "last_execution": getattr(self, '_last_execution_time', None)
        }