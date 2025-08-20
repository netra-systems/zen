"""
GCP Cloud Logging reader implementation.

Provides functionality to read and analyze logs from Google Cloud Logging.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, AsyncIterator
from datetime import datetime, timedelta
import asyncio
import json
from google.cloud import logging as gcp_logging
from google.cloud.logging_v2 import enums

from .base import GCPBaseClient, GCPConfig
from ..unified.base_interfaces import ILogAnalyzer


@dataclass
class LogEntry:
    """Represents a single log entry."""
    timestamp: datetime
    severity: str
    message: str
    service_name: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    labels: Dict[str, str] = None
    json_payload: Dict[str, Any] = None
    text_payload: Optional[str] = None
    source_location: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}
        if self.json_payload is None:
            self.json_payload = {}
    
    @classmethod
    def from_gcp_entry(cls, entry: Any) -> 'LogEntry':
        """Create LogEntry from GCP log entry."""
        return cls(
            timestamp=entry.timestamp,
            severity=entry.severity.name if hasattr(entry.severity, 'name') else str(entry.severity),
            message=entry.payload.get('message', '') if isinstance(entry.payload, dict) else str(entry.payload),
            service_name=entry.resource.labels.get('service_name', 'unknown'),
            trace_id=entry.trace,
            span_id=entry.span_id,
            labels=dict(entry.labels) if entry.labels else {},
            json_payload=entry.payload if isinstance(entry.payload, dict) else {},
            text_payload=str(entry.payload) if not isinstance(entry.payload, dict) else None,
            source_location=entry.source_location._asdict() if entry.source_location else None
        )


@dataclass
class LogFilter:
    """Filter criteria for log queries."""
    service_name: Optional[str] = None
    severity: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    text_search: Optional[str] = None
    labels: Dict[str, str] = None
    resource_type: str = "cloud_run_revision"
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}
        if self.end_time is None:
            self.end_time = datetime.utcnow()
        if self.start_time is None:
            self.start_time = self.end_time - timedelta(hours=1)
    
    def to_filter_string(self) -> str:
        """Convert filter to GCP filter string."""
        filters = []
        
        if self.resource_type:
            filters.append(f'resource.type="{self.resource_type}"')
        
        if self.service_name:
            filters.append(f'resource.labels.service_name="{self.service_name}"')
        
        if self.severity:
            filters.append(f'severity>={self.severity}')
        
        if self.text_search:
            filters.append(f'textPayload:"{self.text_search}" OR jsonPayload.message:"{self.text_search}"')
        
        for key, value in self.labels.items():
            filters.append(f'labels.{key}="{value}"')
        
        if self.start_time:
            filters.append(f'timestamp>="{self.start_time.isoformat()}Z"')
        
        if self.end_time:
            filters.append(f'timestamp<="{self.end_time.isoformat()}Z"')
        
        return " AND ".join(filters)


class GCPLogReader(GCPBaseClient, ILogAnalyzer):
    """Implementation of log reading from GCP Cloud Logging."""
    
    def __init__(self, gcp_config: GCPConfig):
        super().__init__(gcp_config)
        self._client: Optional[gcp_logging.Client] = None
    
    async def initialize(self) -> None:
        """Initialize the Cloud Logging client."""
        await super().initialize()
        self._client = gcp_logging.Client(
            project=self.project_id,
            credentials=self._credentials
        )
    
    async def fetch_logs(
        self,
        filter_query: str,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Fetch logs based on filter criteria."""
        self.validate_initialized()
        
        if not end_time:
            end_time = datetime.utcnow()
        
        # Add time bounds to filter
        time_filter = f'timestamp>="{start_time.isoformat()}Z" AND timestamp<="{end_time.isoformat()}Z"'
        full_filter = f"{filter_query} AND {time_filter}" if filter_query else time_filter
        
        entries = []
        
        def _fetch():
            return list(self._client.list_entries(
                filter_=full_filter,
                page_size=1000
            ))
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        gcp_entries = await loop.run_in_executor(None, _fetch)
        
        for entry in gcp_entries:
            log_entry = LogEntry.from_gcp_entry(entry)
            entries.append(log_entry.__dict__)
        
        return entries
    
    async def fetch_logs_by_filter(self, log_filter: LogFilter) -> List[LogEntry]:
        """Fetch logs using a LogFilter object."""
        self.validate_initialized()
        
        filter_string = log_filter.to_filter_string()
        raw_logs = await self.fetch_logs(
            filter_string,
            log_filter.start_time,
            log_filter.end_time
        )
        
        return [LogEntry(**log) for log in raw_logs]
    
    async def analyze_errors(
        self,
        service_name: str,
        duration_minutes: int = 30
    ) -> Dict[str, Any]:
        """Analyze errors for a service."""
        self.validate_initialized()
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=duration_minutes)
        
        error_filter = LogFilter(
            service_name=service_name,
            severity="ERROR",
            start_time=start_time,
            end_time=end_time
        )
        
        error_logs = await self.fetch_logs_by_filter(error_filter)
        
        # Group errors by type
        error_groups = {}
        for log in error_logs:
            error_type = self._extract_error_type(log)
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append({
                "timestamp": log.timestamp.isoformat(),
                "message": log.message,
                "trace_id": log.trace_id
            })
        
        # Calculate error statistics
        error_stats = {
            "total_errors": len(error_logs),
            "unique_error_types": len(error_groups),
            "errors_by_type": {
                error_type: len(errors)
                for error_type, errors in error_groups.items()
            },
            "error_rate_per_minute": len(error_logs) / duration_minutes if duration_minutes > 0 else 0,
            "most_common_error": max(error_groups.keys(), key=lambda k: len(error_groups[k]))
                if error_groups else None
        }
        
        return {
            "service": service_name,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "duration_minutes": duration_minutes
            },
            "statistics": error_stats,
            "error_groups": error_groups
        }
    
    async def get_metrics(
        self,
        service_name: str,
        metric_types: List[str]
    ) -> Dict[str, Any]:
        """Extract performance metrics from logs."""
        self.validate_initialized()
        
        metrics = {}
        
        for metric_type in metric_types:
            if metric_type == "latency":
                metrics["latency"] = await self._get_latency_metrics(service_name)
            elif metric_type == "error_rate":
                metrics["error_rate"] = await self._get_error_rate_metrics(service_name)
            elif metric_type == "throughput":
                metrics["throughput"] = await self._get_throughput_metrics(service_name)
            elif metric_type == "memory":
                metrics["memory"] = await self._get_memory_metrics(service_name)
        
        return metrics
    
    async def stream_logs(
        self,
        log_filter: LogFilter,
        callback: callable
    ) -> None:
        """Stream logs in real-time."""
        self.validate_initialized()
        
        filter_string = log_filter.to_filter_string()
        
        while True:
            # Fetch latest logs
            logs = await self.fetch_logs(
                filter_string,
                log_filter.start_time,
                log_filter.end_time
            )
            
            for log in logs:
                await callback(log)
            
            # Update start time for next iteration
            if logs:
                log_filter.start_time = datetime.fromisoformat(logs[-1]['timestamp'])
            
            await asyncio.sleep(5)  # Poll every 5 seconds
    
    def _extract_error_type(self, log: LogEntry) -> str:
        """Extract error type from log entry."""
        # Try to extract from JSON payload
        if log.json_payload:
            return (log.json_payload.get('error_type') or
                   log.json_payload.get('exception_type') or
                   log.json_payload.get('error', {}).get('type', 'unknown'))
        
        # Try to extract from message
        if "Exception" in log.message:
            parts = log.message.split("Exception")[0].split()
            if parts:
                return parts[-1] + "Exception"
        
        return "unknown"
    
    async def _get_latency_metrics(self, service_name: str) -> Dict[str, float]:
        """Get latency metrics from logs."""
        latency_filter = LogFilter(
            service_name=service_name,
            labels={"metric_type": "latency"},
            start_time=datetime.utcnow() - timedelta(hours=1)
        )
        
        logs = await self.fetch_logs_by_filter(latency_filter)
        latencies = []
        
        for log in logs:
            if 'latency_ms' in log.json_payload:
                latencies.append(log.json_payload['latency_ms'])
        
        if not latencies:
            return {}
        
        latencies.sort()
        return {
            "min": min(latencies),
            "max": max(latencies),
            "avg": sum(latencies) / len(latencies),
            "p50": latencies[len(latencies) // 2],
            "p95": latencies[int(len(latencies) * 0.95)],
            "p99": latencies[int(len(latencies) * 0.99)]
        }
    
    async def _get_error_rate_metrics(self, service_name: str) -> Dict[str, float]:
        """Get error rate metrics."""
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        # Get total requests
        total_filter = LogFilter(
            service_name=service_name,
            start_time=hour_ago
        )
        total_logs = await self.fetch_logs_by_filter(total_filter)
        
        # Get error requests
        error_filter = LogFilter(
            service_name=service_name,
            severity="ERROR",
            start_time=hour_ago
        )
        error_logs = await self.fetch_logs_by_filter(error_filter)
        
        total_count = len(total_logs)
        error_count = len(error_logs)
        
        return {
            "total_requests": total_count,
            "error_requests": error_count,
            "error_rate": error_count / total_count if total_count > 0 else 0,
            "success_rate": 1 - (error_count / total_count) if total_count > 0 else 1
        }
    
    async def _get_throughput_metrics(self, service_name: str) -> Dict[str, float]:
        """Get throughput metrics."""
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        request_filter = LogFilter(
            service_name=service_name,
            start_time=hour_ago
        )
        logs = await self.fetch_logs_by_filter(request_filter)
        
        # Group by minute
        requests_per_minute = {}
        for log in logs:
            minute = log.timestamp.replace(second=0, microsecond=0)
            requests_per_minute[minute] = requests_per_minute.get(minute, 0) + 1
        
        if not requests_per_minute:
            return {}
        
        rpm_values = list(requests_per_minute.values())
        return {
            "avg_rpm": sum(rpm_values) / len(rpm_values),
            "max_rpm": max(rpm_values),
            "min_rpm": min(rpm_values),
            "total_requests": sum(rpm_values)
        }
    
    async def _get_memory_metrics(self, service_name: str) -> Dict[str, float]:
        """Get memory usage metrics."""
        memory_filter = LogFilter(
            service_name=service_name,
            labels={"metric_type": "memory"},
            start_time=datetime.utcnow() - timedelta(hours=1)
        )
        
        logs = await self.fetch_logs_by_filter(memory_filter)
        memory_values = []
        
        for log in logs:
            if 'memory_mb' in log.json_payload:
                memory_values.append(log.json_payload['memory_mb'])
        
        if not memory_values:
            return {}
        
        return {
            "avg_memory_mb": sum(memory_values) / len(memory_values),
            "max_memory_mb": max(memory_values),
            "min_memory_mb": min(memory_values)
        }