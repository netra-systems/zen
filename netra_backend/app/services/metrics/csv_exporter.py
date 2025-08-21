"""
CSV format metrics exporter
Converts metrics data to CSV format for Excel and analysis tools
"""

import csv
import io
from typing import List, Any
from datetime import datetime, UTC
from netra_backend.app.schemas.Metrics import MetricsSnapshot, CorpusMetric


class CSVExporter:
    """Handles export of metrics data in CSV format"""
    
    async def export(self, data: Any, include_metadata: bool) -> str:
        """Export metrics as CSV"""
        output = io.StringIO()
        await self._write_csv_data_by_type(data, output, include_metadata)
        return output.getvalue()
    
    async def _write_csv_data_by_type(self, data: Any, output: io.StringIO, include_metadata: bool) -> None:
        """Write CSV data based on data type."""
        if isinstance(data, MetricsSnapshot):
            await self._snapshot_to_csv(data, output, include_metadata)
        elif isinstance(data, list):
            await self._list_to_csv(data, output, include_metadata)
        else:
            await self._generic_to_csv(data, output)
    
    async def _snapshot_to_csv(self, snapshot: MetricsSnapshot, output: io.StringIO, include_metadata: bool):
        """Convert snapshot to CSV format"""
        writer = csv.writer(output)
        self._write_csv_metadata_if_needed(writer, snapshot, include_metadata)
        self._write_csv_operation_metrics(writer, snapshot)
        self._write_csv_resource_usage(writer, snapshot)
    
    def _write_csv_metadata_if_needed(self, writer: csv.writer, snapshot: MetricsSnapshot, include_metadata: bool) -> None:
        """Write CSV metadata headers if requested."""
        if include_metadata:
            writer.writerow(["# Corpus Metrics Export"])
            writer.writerow(["# Exported at:", datetime.now(UTC).isoformat()])
            writer.writerow(["# Corpus ID:", snapshot.corpus_id])
            writer.writerow([])
    
    def _write_csv_operation_metrics(self, writer: csv.writer, snapshot: MetricsSnapshot) -> None:
        """Write operation metrics section to CSV."""
        if not snapshot.operation_metrics:
            return
        self._write_csv_operation_headers(writer)
        self._write_csv_operation_data(writer, snapshot.operation_metrics)
        writer.writerow([])
    
    def _write_csv_operation_headers(self, writer: csv.writer) -> None:
        """Write operation metrics headers."""
        writer.writerow(["Operation Metrics"])
        writer.writerow(["Operation Type", "Duration (ms)", "Success", "Records Processed", "Throughput"])
    
    def _write_csv_operation_data(self, writer: csv.writer, operation_metrics) -> None:
        """Write operation metrics data rows."""
        for op in operation_metrics:
            self._write_csv_single_operation(writer, op)
    
    def _write_csv_single_operation(self, writer: csv.writer, op) -> None:
        """Write single operation metric row."""
        writer.writerow([
            op.operation_type, op.duration_ms or "", op.success,
            op.records_processed or "", op.throughput_per_second or ""
        ])
    
    def _write_csv_resource_usage(self, writer: csv.writer, snapshot: MetricsSnapshot) -> None:
        """Write resource usage section to CSV."""
        if not snapshot.resource_usage:
            return
        self._write_csv_resource_headers(writer)
        self._write_csv_resource_data(writer, snapshot.resource_usage)
    
    def _write_csv_resource_headers(self, writer: csv.writer) -> None:
        """Write resource usage headers."""
        writer.writerow(["Resource Usage"])
        writer.writerow(["Resource Type", "Current Value", "Unit", "Timestamp"])
    
    def _write_csv_resource_data(self, writer: csv.writer, resource_usage) -> None:
        """Write resource usage data rows."""
        for resource in resource_usage:
            self._write_csv_single_resource(writer, resource)
    
    def _write_csv_single_resource(self, writer: csv.writer, resource) -> None:
        """Write single resource usage row."""
        writer.writerow([
            resource.resource_type.value, resource.current_value,
            resource.unit, resource.timestamp.isoformat()
        ])
    
    async def _list_to_csv(self, data_list: List[Any], output: io.StringIO, include_metadata: bool):
        """Convert list data to CSV format"""
        writer = csv.writer(output)
        self._write_csv_list_metadata(writer, include_metadata)
        if not data_list:
            self._write_csv_empty_data(writer)
            return
        self._write_csv_list_data(writer, data_list)
    
    def _write_csv_list_metadata(self, writer: csv.writer, include_metadata: bool) -> None:
        """Write CSV list metadata headers."""
        if include_metadata:
            writer.writerow(["# Metrics Export"])
            writer.writerow(["# Exported at:", datetime.now(UTC).isoformat()])
            writer.writerow([])
    
    def _write_csv_empty_data(self, writer: csv.writer) -> None:
        """Write CSV empty data message."""
        writer.writerow(["No data to export"])
    
    def _write_csv_list_data(self, writer: csv.writer, data_list: List[Any]) -> None:
        """Write CSV data based on first item type."""
        first_item = data_list[0]
        if isinstance(first_item, CorpusMetric):
            self._write_csv_corpus_metrics(writer, data_list)
    
    def _write_csv_corpus_metrics(self, writer: csv.writer, data_list: List[Any]) -> None:
        """Write corpus metrics to CSV."""
        writer.writerow(["Metric ID", "Corpus ID", "Type", "Value", "Unit", "Timestamp"])
        for metric in data_list:
            if isinstance(metric, CorpusMetric):
                self._write_csv_single_corpus_metric(writer, metric)
    
    def _write_csv_single_corpus_metric(self, writer: csv.writer, metric) -> None:
        """Write single corpus metric to CSV."""
        writer.writerow([
            metric.metric_id, metric.corpus_id, metric.metric_type.value,
            metric.value, metric.unit, metric.timestamp.isoformat()
        ])
    
    async def _generic_to_csv(self, data: Any, output: io.StringIO):
        """Generic data to CSV conversion"""
        writer = csv.writer(output)
        writer.writerow(["Data Type", "Value"])
        writer.writerow([type(data).__name__, str(data)])