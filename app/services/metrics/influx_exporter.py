"""
InfluxDB line protocol metrics exporter
Converts metrics data to InfluxDB line protocol format for time series databases
"""

from typing import Dict, List, Any, Optional
from app.schemas.Metrics import MetricsSnapshot, CorpusMetric


class InfluxExporter:
    """Handles export of metrics data in InfluxDB line protocol format"""
    
    async def export(self, data: Any, include_metadata: bool) -> str:
        """Export metrics in InfluxDB line protocol format"""
        lines = []
        await self._add_influx_lines_by_type(lines, data)
        return "\n".join(lines)
    
    async def _add_influx_lines_by_type(self, lines: List[str], data: Any) -> None:
        """Add InfluxDB lines based on data type."""
        if isinstance(data, MetricsSnapshot):
            lines.extend(await self._snapshot_to_influx(data))
        elif isinstance(data, list):
            lines.extend(await self._list_to_influx(data))
    
    async def _snapshot_to_influx(self, snapshot: MetricsSnapshot) -> List[str]:
        """Convert snapshot to InfluxDB line protocol"""
        lines = []
        timestamp_ns = int(snapshot.snapshot_time.timestamp() * 1_000_000_000)
        self._add_influx_basic_info(lines, snapshot, timestamp_ns)
        self._add_influx_operation_metrics(lines, snapshot, timestamp_ns)
        return lines
    
    def _add_influx_basic_info(self, lines: List[str], snapshot: MetricsSnapshot, timestamp_ns: int) -> None:
        """Add basic corpus info to InfluxDB lines."""
        line = f"corpus_info,corpus_id={snapshot.corpus_id} total_records={snapshot.total_records}i,health_status=\"{snapshot.health_status}\" {timestamp_ns}"
        lines.append(line)
    
    def _add_influx_operation_metrics(self, lines: List[str], snapshot: MetricsSnapshot, timestamp_ns: int) -> None:
        """Add operation metrics to InfluxDB lines."""
        for op in snapshot.operation_metrics:
            influx_line = self._build_influx_operation_line(op, snapshot.corpus_id, timestamp_ns)
            if influx_line:
                lines.append(influx_line)
    
    def _build_influx_operation_line(self, op, corpus_id: str, timestamp_ns: int) -> Optional[str]:
        """Build InfluxDB line for single operation metric."""
        tags = f"corpus_id={corpus_id},operation={op.operation_type}"
        fields = self._build_influx_operation_fields(op)
        return f"corpus_operations,{tags} {','.join(fields)} {timestamp_ns}" if fields else None
    
    def _build_influx_operation_fields(self, op) -> List[str]:
        """Build InfluxDB fields for operation metric."""
        fields = []
        self._add_influx_duration_field(fields, op)
        self._add_influx_success_field(fields, op)
        self._add_influx_records_field(fields, op)
        return fields
    
    def _add_influx_duration_field(self, fields: List[str], op) -> None:
        """Add duration field if present."""
        if op.duration_ms:
            fields.append(f"duration_ms={op.duration_ms}i")
    
    def _add_influx_success_field(self, fields: List[str], op) -> None:
        """Add success field to InfluxDB fields."""
        fields.append(f"success={str(op.success).lower()}")
    
    def _add_influx_records_field(self, fields: List[str], op) -> None:
        """Add records processed field if present."""
        if op.records_processed:
            fields.append(f"records_processed={op.records_processed}i")
    
    async def _list_to_influx(self, data_list: List[Any]) -> List[str]:
        """Convert list data to InfluxDB format"""
        lines = []
        for item in data_list:
            if isinstance(item, CorpusMetric):
                influx_line = self._build_influx_corpus_metric_line(item)
                lines.append(influx_line)
        return lines
    
    def _build_influx_corpus_metric_line(self, item) -> str:
        """Build InfluxDB line for corpus metric."""
        timestamp_ns = int(item.timestamp.timestamp() * 1_000_000_000)
        measurement = f"corpus_{item.metric_type.value}"
        tags = self._build_influx_tags(item)
        return f"{measurement},{tags} value={item.value} {timestamp_ns}"
    
    def _build_influx_tags(self, item) -> str:
        """Build InfluxDB tags string for corpus metric."""
        tags = f"corpus_id={item.corpus_id}"
        if item.tags:
            additional_tags = self._format_influx_additional_tags(item.tags)
            tags += f",{additional_tags}"
        return tags
    
    def _format_influx_additional_tags(self, tags_dict: Dict[str, Any]) -> str:
        """Format additional tags for InfluxDB."""
        tag_pairs = [f"{k}={v}" for k, v in tags_dict.items()]
        return ",".join(tag_pairs)