"""Modernized anomaly detection module implementing BaseExecutionInterface.

Business Value: Standardized anomaly detection with reliability patterns.
Provides consistent execution workflow for anomaly detection operations.
"""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from app.agents.base.interface import (
    BaseExecutionInterface, ExecutionContext,
    ExecutionResult, ExecutionStatus
)
from app.agents.base.executor import BaseExecutionEngine
from app.agents.base.monitoring import ExecutionMonitor
from app.agents.base.reliability_manager import ReliabilityManager
from app.agents.base.errors import (
    ExecutionErrorHandler, ValidationError,
    AgentExecutionError
)
from app.schemas.shared_types import (
    AnomalyDetectionResponse, AnomalyDetail, AnomalySeverity
)
from app.logging_config import central_logger as logger


class AnomalyDetector(BaseExecutionInterface):
    """Modernized anomaly detection with BaseExecutionInterface."""
    
    def __init__(self, query_builder: Any, clickhouse_ops: Any, 
                 redis_manager: Any, websocket_manager=None) -> None:
        super().__init__("AnomalyDetector", websocket_manager)
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
        self.error_handler = ExecutionErrorHandler()
    
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
        metadata = context.metadata
        user_id = metadata['user_id']
        metric_name = metadata['metric_name']
        time_range = metadata['time_range']
        z_score_threshold = metadata.get('z_score_threshold', 2.0)
        
        await self.send_status_update(
            context, "executing", 
            f"Detecting anomalies in {metric_name}..."
        )
        
        data = await self._fetch_anomaly_data(
            user_id, metric_name, time_range, z_score_threshold
        )
        response = self._convert_to_typed_response(
            data, metric_name, z_score_threshold, time_range
        )
        
        await self.send_status_update(
            context, "completed", 
            f"Found {response.anomaly_count} anomalies"
        )
        
        return {"anomaly_response": response}
    
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
        query = self._build_anomaly_query(
            user_id, metric_name, start_time, end_time, z_score_threshold
        )
        cache_key = self._build_anomaly_cache_key(
            user_id, metric_name, start_time, z_score_threshold
        )
        return await self.clickhouse_ops.fetch_data(
            query, cache_key, self.redis_manager
        )
    
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
        start_time, end_time = time_range
        return AnomalyDetectionResponse(
            anomalies_detected=False,
            anomaly_count=0,
            confidence_score=0.95,
            threshold_used=z_score_threshold,
            analysis_period={"start": start_time, "end": end_time},
            recommended_actions=[f"Continue monitoring {metric_name}"]
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
        start_time, end_time = time_range
        return AnomalyDetectionResponse(
            anomalies_detected=True,
            anomaly_count=len(data),
            anomaly_details=anomaly_details[:50],
            confidence_score=0.85,
            severity=max_severity,
            threshold_used=z_score_threshold,
            analysis_period={"start": start_time, "end": end_time},
            recommended_actions=self._generate_recommendations(max_severity)
        )
    
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
        actual_value, expected_value, z_score = values
        deviation_pct = self._calculate_deviation_percentage(actual_value, expected_value)
        return AnomalyDetail(
            timestamp=row.get('timestamp', datetime.utcnow()),
            metric_name=metric_name,
            actual_value=actual_value,
            expected_value=expected_value,
            deviation_percentage=deviation_pct,
            z_score=z_score,
            severity=self._determine_severity(z_score)
        )
    
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