"""
Metrics export functionality supporting multiple formats
Exports corpus metrics in JSON, Prometheus, CSV, and InfluxDB formats
"""

import json
import csv
import io
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional, Union
from dataclasses import asdict

from app.logging_config import central_logger
from app.schemas.Metrics import (
    MetricsSnapshot, ExportFormat, CorpusMetric, 
    TimeSeriesPoint, ResourceUsage, QualityMetrics
)

logger = central_logger.get_logger(__name__)


class MetricsExporter:
    """Exports metrics data in various formats for external consumption"""
    
    def __init__(self):
        self._export_handlers = {
            ExportFormat.JSON: self._export_json,
            ExportFormat.PROMETHEUS: self._export_prometheus,
            ExportFormat.CSV: self._export_csv,
            ExportFormat.INFLUX: self._export_influxdb
        }
    
    async def export_metrics(
        self,
        metrics_data: Union[MetricsSnapshot, List[CorpusMetric], Dict[str, Any]],
        export_format: ExportFormat,
        include_metadata: bool = True
    ) -> str:
        """Export metrics in specified format"""
        handler = self._export_handlers.get(export_format)
        if not handler:
            raise ValueError(f"Unsupported export format: {export_format}")
        
        try:
            result = await handler(metrics_data, include_metadata)
            logger.debug(f"Exported metrics in {export_format.value} format")
            return result
        except Exception as e:
            logger.error(f"Failed to export metrics in {export_format.value}: {str(e)}")
            raise
    
    async def _export_json(self, data: Any, include_metadata: bool) -> str:
        """Export metrics as JSON"""
        export_data = await self._prepare_json_data(data, include_metadata)
        return json.dumps(export_data, indent=2, default=str)
    
    async def _prepare_json_data(self, data: Any, include_metadata: bool) -> Dict[str, Any]:
        """Prepare data structure for JSON export"""
        if isinstance(data, MetricsSnapshot):
            return await self._snapshot_to_dict(data, include_metadata)
        elif isinstance(data, list):
            return await self._list_to_dict(data, include_metadata)
        elif isinstance(data, dict):
            return data
        else:
            return {"data": str(data), "type": type(data).__name__}
    
    async def _snapshot_to_dict(self, snapshot: MetricsSnapshot, include_metadata: bool) -> Dict[str, Any]:
        """Convert metrics snapshot to dictionary"""
        result = {
            "corpus_id": snapshot.corpus_id,
            "snapshot_time": snapshot.snapshot_time.isoformat(),
            "total_records": snapshot.total_records,
            "health_status": snapshot.health_status,
            "operation_metrics": [
                await self._operation_metrics_to_dict(op) for op in snapshot.operation_metrics
            ],
            "resource_usage": [
                await self._resource_usage_to_dict(ru) for ru in snapshot.resource_usage
            ],
            "custom_metrics": [
                await self._corpus_metric_to_dict(cm) for cm in snapshot.custom_metrics
            ]
        }
        
        if snapshot.quality_metrics:
            result["quality_metrics"] = await self._quality_metrics_to_dict(snapshot.quality_metrics)
        
        if include_metadata:
            result["export_metadata"] = {
                "exported_at": datetime.now(UTC).isoformat(),
                "format": "json",
                "version": "1.0"
            }
        
        return result
    
    async def _list_to_dict(self, data_list: List[Any], include_metadata: bool) -> Dict[str, Any]:
        """Convert list data to dictionary format"""
        result = {"metrics": [], "count": len(data_list)}
        
        for item in data_list:
            if isinstance(item, CorpusMetric):
                result["metrics"].append(await self._corpus_metric_to_dict(item))
            elif isinstance(item, TimeSeriesPoint):
                result["metrics"].append(await self._time_series_to_dict(item))
            else:
                result["metrics"].append(str(item))
        
        if include_metadata:
            result["export_metadata"] = {
                "exported_at": datetime.now(UTC).isoformat(),
                "format": "json",
                "data_type": "list"
            }
        
        return result
    
    async def _export_prometheus(self, data: Any, include_metadata: bool) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        timestamp_ms = int(datetime.now(UTC).timestamp() * 1000)
        
        if isinstance(data, MetricsSnapshot):
            lines.extend(await self._snapshot_to_prometheus(data, timestamp_ms))
        elif isinstance(data, list):
            lines.extend(await self._list_to_prometheus(data, timestamp_ms))
        
        if include_metadata:
            lines.append(f"# HELP corpus_metrics_export_info Export metadata information")
            lines.append(f"# TYPE corpus_metrics_export_info gauge")
            lines.append(f'corpus_metrics_export_info{{format="prometheus",version="1.0"}} 1 {timestamp_ms}')
        
        return "\n".join(lines)
    
    async def _snapshot_to_prometheus(self, snapshot: MetricsSnapshot, timestamp_ms: int) -> List[str]:
        """Convert snapshot to Prometheus format"""
        lines = []
        corpus_id = snapshot.corpus_id
        
        # Basic corpus info
        lines.append(f"# HELP corpus_total_records Total records in corpus")
        lines.append(f"# TYPE corpus_total_records gauge")
        lines.append(f'corpus_total_records{{corpus_id="{corpus_id}"}} {snapshot.total_records} {timestamp_ms}')
        
        # Health status (convert to numeric)
        health_value = {"excellent": 4, "good": 3, "fair": 2, "poor": 1}.get(snapshot.health_status, 0)
        lines.append(f"# HELP corpus_health_status Corpus health status")
        lines.append(f"# TYPE corpus_health_status gauge")
        lines.append(f'corpus_health_status{{corpus_id="{corpus_id}",status="{snapshot.health_status}"}} {health_value} {timestamp_ms}')
        
        # Operation metrics
        for op_metric in snapshot.operation_metrics:
            if op_metric.duration_ms:
                lines.append(f"# HELP corpus_operation_duration_ms Operation duration")
                lines.append(f"# TYPE corpus_operation_duration_ms histogram")
                lines.append(f'corpus_operation_duration_ms{{corpus_id="{corpus_id}",operation="{op_metric.operation_type}"}} {op_metric.duration_ms} {timestamp_ms}')
        
        # Resource usage
        for resource in snapshot.resource_usage:
            metric_name = f"corpus_resource_{resource.resource_type.value}"
            lines.append(f"# HELP {metric_name} Resource usage for {resource.resource_type.value}")
            lines.append(f"# TYPE {metric_name} gauge")
            lines.append(f'{metric_name}{{corpus_id="{corpus_id}",unit="{resource.unit}"}} {resource.current_value} {timestamp_ms}')
        
        return lines
    
    async def _list_to_prometheus(self, data_list: List[Any], timestamp_ms: int) -> List[str]:
        """Convert list data to Prometheus format"""
        lines = []
        
        for item in data_list:
            if isinstance(item, CorpusMetric):
                metric_name = f"corpus_{item.metric_type.value}"
                lines.append(f"# HELP {metric_name} {item.metric_type.value} metric")
                lines.append(f"# TYPE {metric_name} gauge")
                
                tags = ",".join([f'{k}="{v}"' for k, v in item.tags.items()])
                tag_str = f',{tags}' if tags else ''
                
                lines.append(f'{metric_name}{{corpus_id="{item.corpus_id}"{tag_str}}} {item.value} {timestamp_ms}')
        
        return lines
    
    async def _export_csv(self, data: Any, include_metadata: bool) -> str:
        """Export metrics as CSV"""
        output = io.StringIO()
        
        if isinstance(data, MetricsSnapshot):
            await self._snapshot_to_csv(data, output, include_metadata)
        elif isinstance(data, list):
            await self._list_to_csv(data, output, include_metadata)
        else:
            await self._generic_to_csv(data, output)
        
        return output.getvalue()
    
    async def _snapshot_to_csv(self, snapshot: MetricsSnapshot, output: io.StringIO, include_metadata: bool):
        """Convert snapshot to CSV format"""
        writer = csv.writer(output)
        
        if include_metadata:
            writer.writerow(["# Corpus Metrics Export"])
            writer.writerow(["# Exported at:", datetime.now(UTC).isoformat()])
            writer.writerow(["# Corpus ID:", snapshot.corpus_id])
            writer.writerow([])
        
        # Operation metrics
        if snapshot.operation_metrics:
            writer.writerow(["Operation Metrics"])
            writer.writerow(["Operation Type", "Duration (ms)", "Success", "Records Processed", "Throughput"])
            
            for op in snapshot.operation_metrics:
                writer.writerow([
                    op.operation_type,
                    op.duration_ms or "",
                    op.success,
                    op.records_processed or "",
                    op.throughput_per_second or ""
                ])
            writer.writerow([])
        
        # Resource usage
        if snapshot.resource_usage:
            writer.writerow(["Resource Usage"])
            writer.writerow(["Resource Type", "Current Value", "Unit", "Timestamp"])
            
            for resource in snapshot.resource_usage:
                writer.writerow([
                    resource.resource_type.value,
                    resource.current_value,
                    resource.unit,
                    resource.timestamp.isoformat()
                ])
    
    async def _list_to_csv(self, data_list: List[Any], output: io.StringIO, include_metadata: bool):
        """Convert list data to CSV format"""
        writer = csv.writer(output)
        
        if include_metadata:
            writer.writerow(["# Metrics Export"])
            writer.writerow(["# Exported at:", datetime.now(UTC).isoformat()])
            writer.writerow([])
        
        if not data_list:
            writer.writerow(["No data to export"])
            return
        
        # Determine data type and headers
        first_item = data_list[0]
        if isinstance(first_item, CorpusMetric):
            writer.writerow(["Metric ID", "Corpus ID", "Type", "Value", "Unit", "Timestamp"])
            for metric in data_list:
                if isinstance(metric, CorpusMetric):
                    writer.writerow([
                        metric.metric_id, metric.corpus_id, metric.metric_type.value,
                        metric.value, metric.unit, metric.timestamp.isoformat()
                    ])
    
    async def _export_influxdb(self, data: Any, include_metadata: bool) -> str:
        """Export metrics in InfluxDB line protocol format"""
        lines = []
        
        if isinstance(data, MetricsSnapshot):
            lines.extend(await self._snapshot_to_influx(data))
        elif isinstance(data, list):
            lines.extend(await self._list_to_influx(data))
        
        return "\n".join(lines)
    
    async def _snapshot_to_influx(self, snapshot: MetricsSnapshot) -> List[str]:
        """Convert snapshot to InfluxDB line protocol"""
        lines = []
        timestamp_ns = int(snapshot.snapshot_time.timestamp() * 1_000_000_000)
        
        # Basic metrics
        lines.append(f"corpus_info,corpus_id={snapshot.corpus_id} total_records={snapshot.total_records}i,health_status=\"{snapshot.health_status}\" {timestamp_ns}")
        
        # Operation metrics
        for op in snapshot.operation_metrics:
            tags = f"corpus_id={snapshot.corpus_id},operation={op.operation_type}"
            fields = []
            
            if op.duration_ms:
                fields.append(f"duration_ms={op.duration_ms}i")
            fields.append(f"success={str(op.success).lower()}")
            if op.records_processed:
                fields.append(f"records_processed={op.records_processed}i")
            
            if fields:
                lines.append(f"corpus_operations,{tags} {','.join(fields)} {timestamp_ns}")
        
        return lines
    
    async def _list_to_influx(self, data_list: List[Any]) -> List[str]:
        """Convert list data to InfluxDB format"""
        lines = []
        
        for item in data_list:
            if isinstance(item, CorpusMetric):
                timestamp_ns = int(item.timestamp.timestamp() * 1_000_000_000)
                measurement = f"corpus_{item.metric_type.value}"
                tags = f"corpus_id={item.corpus_id}"
                
                if item.tags:
                    tag_pairs = [f"{k}={v}" for k, v in item.tags.items()]
                    tags += "," + ",".join(tag_pairs)
                
                lines.append(f"{measurement},{tags} value={item.value} {timestamp_ns}")
        
        return lines
    
    # Helper methods for data conversion
    async def _operation_metrics_to_dict(self, op_metrics) -> Dict[str, Any]:
        """Convert operation metrics to dictionary"""
        return {
            "operation_type": op_metrics.operation_type,
            "start_time": op_metrics.start_time.isoformat(),
            "end_time": op_metrics.end_time.isoformat() if op_metrics.end_time else None,
            "duration_ms": op_metrics.duration_ms,
            "success": op_metrics.success,
            "error_message": op_metrics.error_message,
            "records_processed": op_metrics.records_processed,
            "throughput_per_second": op_metrics.throughput_per_second
        }
    
    async def _resource_usage_to_dict(self, resource_usage: ResourceUsage) -> Dict[str, Any]:
        """Convert resource usage to dictionary"""
        return {
            "resource_type": resource_usage.resource_type.value,
            "current_value": resource_usage.current_value,
            "max_value": resource_usage.max_value,
            "average_value": resource_usage.average_value,
            "unit": resource_usage.unit,
            "timestamp": resource_usage.timestamp.isoformat()
        }
    
    async def _corpus_metric_to_dict(self, metric: CorpusMetric) -> Dict[str, Any]:
        """Convert corpus metric to dictionary"""
        return {
            "metric_id": metric.metric_id,
            "corpus_id": metric.corpus_id,
            "metric_type": metric.metric_type.value,
            "value": metric.value,
            "unit": metric.unit,
            "timestamp": metric.timestamp.isoformat(),
            "tags": metric.tags,
            "metadata": metric.metadata
        }
    
    async def _quality_metrics_to_dict(self, quality: QualityMetrics) -> Dict[str, Any]:
        """Convert quality metrics to dictionary"""
        return {
            "overall_score": quality.overall_score,
            "validation_score": quality.validation_score,
            "completeness_score": quality.completeness_score,
            "consistency_score": quality.consistency_score,
            "accuracy_score": quality.accuracy_score,
            "timestamp": quality.timestamp.isoformat(),
            "issues_detected": quality.issues_detected
        }
    
    async def _time_series_to_dict(self, point: TimeSeriesPoint) -> Dict[str, Any]:
        """Convert time series point to dictionary"""
        return {
            "timestamp": point.timestamp.isoformat(),
            "value": point.value,
            "tags": point.tags
        }
    
    async def _generic_to_csv(self, data: Any, output: io.StringIO):
        """Generic data to CSV conversion"""
        writer = csv.writer(output)
        writer.writerow(["Data Type", "Value"])
        writer.writerow([type(data).__name__, str(data)])