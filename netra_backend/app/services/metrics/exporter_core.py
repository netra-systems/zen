"""
Core metrics exporter functionality
Main orchestration and JSON export functionality
"""

import json
from datetime import UTC, datetime
from typing import Any, Dict, List, Union

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.Metrics import (
    CorpusMetric,
    ExportFormat,
    MetricsSnapshot,
    QualityMetrics,
    ResourceUsage,
    TimeSeriesPoint,
)
from netra_backend.app.services.metrics.csv_exporter import CSVExporter
from netra_backend.app.services.metrics.influx_exporter import InfluxExporter
from netra_backend.app.services.metrics.prometheus_exporter import PrometheusExporter

logger = central_logger.get_logger(__name__)


class MetricsExporter:
    """Exports metrics data in various formats for external consumption"""
    
    def __init__(self):
        self._initialize_exporters()
        self._initialize_handlers()
    
    def _initialize_exporters(self) -> None:
        """Initialize format-specific exporters."""
        self._prometheus_exporter = PrometheusExporter()
        self._csv_exporter = CSVExporter()
        self._influx_exporter = InfluxExporter()
    
    def _initialize_handlers(self) -> None:
        """Initialize export handler mapping."""
        self._export_handlers = {
            ExportFormat.JSON: self._export_json,
            ExportFormat.PROMETHEUS: self._prometheus_exporter.export,
            ExportFormat.CSV: self._csv_exporter.export,
            ExportFormat.INFLUX: self._influx_exporter.export
        }
    
    async def export_metrics(
        self,
        metrics_data: Union[MetricsSnapshot, List[CorpusMetric], Dict[str, Any]],
        export_format: ExportFormat,
        include_metadata: bool = True
    ) -> str:
        """Export metrics in specified format"""
        return await self._perform_export(metrics_data, export_format, include_metadata)
    
    async def _perform_export(
        self, 
        metrics_data: Union[MetricsSnapshot, List[CorpusMetric], Dict[str, Any]], 
        export_format: ExportFormat, 
        include_metadata: bool
    ) -> str:
        """Perform the actual export operation."""
        handler = self._get_export_handler(export_format)
        return await self._execute_export(handler, metrics_data, include_metadata, export_format)
    
    def _get_export_handler(self, export_format: ExportFormat):
        """Get export handler for format."""
        handler = self._export_handlers.get(export_format)
        if not handler:
            raise ValueError(f"Unsupported export format: {export_format}")
        return handler
    
    async def _execute_export(self, handler, metrics_data, include_metadata: bool, export_format: ExportFormat) -> str:
        """Execute export with error handling."""
        try:
            return await self._run_handler_with_logging(handler, metrics_data, include_metadata, export_format)
        except Exception as e:
            self._log_export_error(export_format, e)
            raise
    
    async def _run_handler_with_logging(self, handler, metrics_data, include_metadata: bool, export_format: ExportFormat) -> str:
        """Run handler and log success."""
        result = await handler(metrics_data, include_metadata)
        self._log_export_success(export_format)
        return result
    
    def _log_export_success(self, export_format: ExportFormat) -> None:
        """Log successful export."""
        logger.debug(f"Exported metrics in {export_format.value} format")
    
    def _log_export_error(self, export_format: ExportFormat, error: Exception) -> None:
        """Log export error."""
        logger.error(f"Failed to export metrics in {export_format.value}: {str(error)}")

    async def _export_json(self, data: Any, include_metadata: bool) -> str:
        """Export metrics as JSON"""
        export_data = await self._prepare_json_data(data, include_metadata)
        return json.dumps(export_data, indent=2, default=str)
    
    async def _prepare_json_data(self, data: Any, include_metadata: bool) -> Dict[str, Any]:
        """Prepare data structure for JSON export"""
        return await self._convert_data_by_type(data, include_metadata)
    
    async def _convert_data_by_type(self, data: Any, include_metadata: bool) -> Dict[str, Any]:
        """Convert data based on its type."""
        return await self._route_data_conversion(data, include_metadata)
    
    async def _route_data_conversion(self, data: Any, include_metadata: bool) -> Dict[str, Any]:
        """Route data to appropriate conversion method."""
        if isinstance(data, MetricsSnapshot):
            return await self._snapshot_to_dict(data, include_metadata)
        elif isinstance(data, list):
            return await self._list_to_dict(data, include_metadata)
        elif isinstance(data, dict):
            return data
        return self._create_generic_data_dict(data)
    
    def _create_generic_data_dict(self, data: Any) -> Dict[str, Any]:
        """Create generic data dictionary for unknown types."""
        return {"data": str(data), "type": type(data).__name__}
    
    async def _snapshot_to_dict(self, snapshot: MetricsSnapshot, include_metadata: bool) -> Dict[str, Any]:
        """Convert metrics snapshot to dictionary"""
        result = await self._build_snapshot_base_dict(snapshot)
        await self._add_snapshot_metrics(result, snapshot)
        self._add_snapshot_metadata_if_needed(result, include_metadata)
        return result
    
    async def _build_snapshot_base_dict(self, snapshot: MetricsSnapshot) -> Dict[str, Any]:
        """Build base snapshot dictionary."""
        return {
            "corpus_id": snapshot.corpus_id,
            "snapshot_time": snapshot.snapshot_time.isoformat(),
            "total_records": snapshot.total_records,
            "health_status": snapshot.health_status
        }
    
    async def _add_snapshot_metrics(self, result: Dict[str, Any], snapshot: MetricsSnapshot) -> None:
        """Add metrics arrays to snapshot result."""
        result["operation_metrics"] = await self._convert_operation_metrics(snapshot.operation_metrics)
        result["resource_usage"] = await self._convert_resource_usage(snapshot.resource_usage)
        result["custom_metrics"] = await self._convert_custom_metrics(snapshot.custom_metrics)
        await self._add_quality_metrics_if_present(result, snapshot)
    
    async def _convert_operation_metrics(self, operation_metrics) -> List[Dict[str, Any]]:
        """Convert operation metrics to dictionaries."""
        from netra_backend.app.services.metrics.converter_helpers import convert_operation_metrics
        return await convert_operation_metrics(operation_metrics)
    
    async def _convert_resource_usage(self, resource_usage) -> List[Dict[str, Any]]:
        """Convert resource usage to dictionaries."""
        from netra_backend.app.services.metrics.converter_helpers import convert_resource_usage
        return await convert_resource_usage(resource_usage)
    
    async def _convert_custom_metrics(self, custom_metrics) -> List[Dict[str, Any]]:
        """Convert custom metrics to dictionaries."""
        from netra_backend.app.services.metrics.converter_helpers import convert_custom_metrics
        return await convert_custom_metrics(custom_metrics)
    
    async def _add_quality_metrics_if_present(self, result: Dict[str, Any], snapshot: MetricsSnapshot) -> None:
        """Add quality metrics if present in snapshot."""
        if snapshot.quality_metrics:
            from netra_backend.app.services.metrics.converter_helpers import convert_quality_metrics
            result["quality_metrics"] = await convert_quality_metrics(snapshot.quality_metrics)
    
    def _add_snapshot_metadata_if_needed(self, result: Dict[str, Any], include_metadata: bool) -> None:
        """Add export metadata if requested."""
        if include_metadata:
            result["export_metadata"] = self._create_json_export_metadata()
    
    def _create_json_export_metadata(self) -> Dict[str, str]:
        """Create JSON export metadata."""
        return {
            "exported_at": datetime.now(UTC).isoformat(),
            "format": "json",
            "version": "1.0"
        }
    
    async def _list_to_dict(self, data_list: List[Any], include_metadata: bool) -> Dict[str, Any]:
        """Convert list data to dictionary format"""
        result = {"metrics": [], "count": len(data_list)}
        await self._populate_list_metrics(result, data_list)
        self._add_list_metadata_if_needed(result, include_metadata)
        return result
    
    async def _populate_list_metrics(self, result: Dict[str, Any], data_list: List[Any]) -> None:
        """Populate metrics array from data list."""
        for item in data_list:
            converted_item = await self._convert_list_item(item)
            result["metrics"].append(converted_item)
    
    async def _convert_list_item(self, item: Any) -> Any:
        """Convert individual list item to appropriate format."""
        return await self._convert_item_by_type(item)
    
    async def _convert_item_by_type(self, item: Any) -> Any:
        """Convert item based on its type."""
        if isinstance(item, CorpusMetric):
            return await self._convert_corpus_metric_item(item)
        elif isinstance(item, TimeSeriesPoint):
            return await self._convert_time_series_item(item)
        return str(item)
    
    async def _convert_corpus_metric_item(self, item: CorpusMetric) -> Any:
        """Convert CorpusMetric item."""
        from netra_backend.app.services.metrics.converter_helpers import convert_corpus_metric
        return await convert_corpus_metric(item)
    
    async def _convert_time_series_item(self, item: TimeSeriesPoint) -> Any:
        """Convert TimeSeriesPoint item."""
        from netra_backend.app.services.metrics.converter_helpers import convert_time_series_point
        return await convert_time_series_point(item)
    
    def _add_list_metadata_if_needed(self, result: Dict[str, Any], include_metadata: bool) -> None:
        """Add export metadata for list if requested."""
        if include_metadata:
            result["export_metadata"] = self._create_list_export_metadata()
    
    def _create_list_export_metadata(self) -> Dict[str, str]:
        """Create list export metadata."""
        return {
            "exported_at": datetime.now(UTC).isoformat(),
            "format": "json",
            "data_type": "list"
        }