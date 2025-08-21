"""
Prometheus format metrics exporter
Converts metrics data to Prometheus text exposition format
"""

from typing import Dict, List, Any
from datetime import datetime, UTC
from netra_backend.app.schemas.Metrics import MetricsSnapshot, CorpusMetric


class PrometheusExporter:
    """Handles export of metrics data in Prometheus format"""
    
    async def export(self, data: Any, include_metadata: bool) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        timestamp_ms = int(datetime.now(UTC).timestamp() * 1000)
        await self._add_prometheus_data_lines(lines, data, timestamp_ms)
        self._add_prometheus_metadata_if_needed(lines, include_metadata, timestamp_ms)
        return "\n".join(lines)
    
    async def _add_prometheus_data_lines(self, lines: List[str], data: Any, timestamp_ms: int) -> None:
        """Add Prometheus data lines based on data type."""
        if isinstance(data, MetricsSnapshot):
            lines.extend(await self._snapshot_to_prometheus(data, timestamp_ms))
        elif isinstance(data, list):
            lines.extend(await self._list_to_prometheus(data, timestamp_ms))
    
    def _add_prometheus_metadata_if_needed(self, lines: List[str], include_metadata: bool, timestamp_ms: int) -> None:
        """Add Prometheus metadata lines if requested."""
        if include_metadata:
            lines.append(f"# HELP corpus_metrics_export_info Export metadata information")
            lines.append(f"# TYPE corpus_metrics_export_info gauge")
            lines.append(f'corpus_metrics_export_info{{format="prometheus",version="1.0"}} 1 {timestamp_ms}')
    
    async def _snapshot_to_prometheus(self, snapshot: MetricsSnapshot, timestamp_ms: int) -> List[str]:
        """Convert snapshot to Prometheus format"""
        lines = []
        corpus_id = snapshot.corpus_id
        self._add_all_prometheus_metrics(lines, snapshot, corpus_id, timestamp_ms)
        return lines
    
    def _add_all_prometheus_metrics(self, lines: List[str], snapshot: MetricsSnapshot, corpus_id: str, timestamp_ms: int) -> None:
        """Add all Prometheus metrics to lines."""
        self._add_prometheus_basic_info(lines, snapshot, corpus_id, timestamp_ms)
        self._add_prometheus_health_status(lines, snapshot, corpus_id, timestamp_ms)
        self._add_prometheus_operation_metrics(lines, snapshot, corpus_id, timestamp_ms)
        self._add_prometheus_resource_usage(lines, snapshot, corpus_id, timestamp_ms)
    
    def _add_prometheus_basic_info(self, lines: List[str], snapshot: MetricsSnapshot, corpus_id: str, timestamp_ms: int) -> None:
        """Add basic corpus info to Prometheus lines."""
        lines.append(f"# HELP corpus_total_records Total records in corpus")
        lines.append(f"# TYPE corpus_total_records gauge")
        lines.append(f'corpus_total_records{{corpus_id="{corpus_id}"}} {snapshot.total_records} {timestamp_ms}')
    
    def _add_prometheus_health_status(self, lines: List[str], snapshot: MetricsSnapshot, corpus_id: str, timestamp_ms: int) -> None:
        """Add health status to Prometheus lines."""
        health_value = {"excellent": 4, "good": 3, "fair": 2, "poor": 1}.get(snapshot.health_status, 0)
        lines.append(f"# HELP corpus_health_status Corpus health status")
        lines.append(f"# TYPE corpus_health_status gauge")
        lines.append(f'corpus_health_status{{corpus_id="{corpus_id}",status="{snapshot.health_status}"}} {health_value} {timestamp_ms}')
    
    def _add_prometheus_operation_metrics(self, lines: List[str], snapshot: MetricsSnapshot, corpus_id: str, timestamp_ms: int) -> None:
        """Add operation metrics to Prometheus lines."""
        for op_metric in snapshot.operation_metrics:
            if op_metric.duration_ms:
                self._add_single_prometheus_operation(lines, op_metric, corpus_id, timestamp_ms)
    
    def _add_single_prometheus_operation(self, lines: List[str], op_metric, corpus_id: str, timestamp_ms: int) -> None:
        """Add single operation metric to Prometheus lines."""
        lines.append(f"# HELP corpus_operation_duration_ms Operation duration")
        lines.append(f"# TYPE corpus_operation_duration_ms histogram")
        lines.append(f'corpus_operation_duration_ms{{corpus_id="{corpus_id}",operation="{op_metric.operation_type}"}} {op_metric.duration_ms} {timestamp_ms}')
    
    def _add_prometheus_resource_usage(self, lines: List[str], snapshot: MetricsSnapshot, corpus_id: str, timestamp_ms: int) -> None:
        """Add resource usage to Prometheus lines."""
        for resource in snapshot.resource_usage:
            metric_name = f"corpus_resource_{resource.resource_type.value}"
            self._add_single_prometheus_resource(lines, resource, metric_name, corpus_id, timestamp_ms)
    
    def _add_single_prometheus_resource(self, lines: List[str], resource, metric_name: str, corpus_id: str, timestamp_ms: int) -> None:
        """Add single resource metric to Prometheus lines."""
        lines.append(f"# HELP {metric_name} Resource usage for {resource.resource_type.value}")
        lines.append(f"# TYPE {metric_name} gauge")
        lines.append(f'{metric_name}{{corpus_id="{corpus_id}",unit="{resource.unit}"}} {resource.current_value} {timestamp_ms}')
    
    async def _list_to_prometheus(self, data_list: List[Any], timestamp_ms: int) -> List[str]:
        """Convert list data to Prometheus format"""
        lines = []
        for item in data_list:
            if isinstance(item, CorpusMetric):
                self._add_prometheus_corpus_metric(lines, item, timestamp_ms)
        return lines
    
    def _add_prometheus_corpus_metric(self, lines: List[str], item, timestamp_ms: int) -> None:
        """Add corpus metric to Prometheus lines."""
        metric_name = f"corpus_{item.metric_type.value}"
        self._add_prometheus_metric_headers(lines, metric_name, item.metric_type.value)
        tag_str = self._build_prometheus_tag_string(item.tags, item.corpus_id)
        lines.append(f'{metric_name}{{corpus_id="{item.corpus_id}"{tag_str}}} {item.value} {timestamp_ms}')
    
    def _add_prometheus_metric_headers(self, lines: List[str], metric_name: str, metric_type: str) -> None:
        """Add Prometheus metric headers."""
        lines.append(f"# HELP {metric_name} {metric_type} metric")
        lines.append(f"# TYPE {metric_name} gauge")
    
    def _build_prometheus_tag_string(self, tags: Dict[str, Any], corpus_id: str) -> str:
        """Build Prometheus tag string from tags dictionary."""
        if not tags:
            return ''
        tag_pairs = [f'{k}="{v}"' for k, v in tags.items()]
        return f',{",".join(tag_pairs)}'