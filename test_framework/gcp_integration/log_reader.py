"""
GCP Log Reader for Integration Tests.

This module provides functionality to read and analyze logs from GCP Cloud Logging
for integration testing and debugging purposes.
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator, Dict, List, Optional

try:
    from google.cloud import logging as gcp_logging
    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False
    gcp_logging = None

from test_framework.gcp_integration.base import GCPBaseClient, GCPConfig


@dataclass
class LogEntry:
    """Log entry data structure for GCP logs."""
    timestamp: datetime
    severity: str
    message: str
    service_name: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)
    json_payload: Dict[str, Any] = field(default_factory=dict)
    text_payload: Optional[str] = None
    source_location: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize default values after creation."""
        if self.labels is None:
            self.labels = {}
        if self.json_payload is None:
            self.json_payload = {}

    @classmethod
    def from_gcp_entry(cls, entry: Any) -> 'LogEntry':
        """Create LogEntry from GCP log entry."""
        if not GCP_AVAILABLE:
            raise ImportError("google-cloud-logging is not installed")
            
        # Handle severity - in v3.x it's already a string
        severity = str(entry.severity) if entry.severity else 'DEFAULT'
        
        return cls(
            timestamp=entry.timestamp or datetime.now(timezone.utc),
            severity=severity,
            message=entry.payload.get('message', '') if isinstance(entry.payload, dict) else str(entry.payload or ''),
            service_name=entry.resource.labels.get('service_name', 'unknown') if entry.resource else 'unknown',
            trace_id=entry.trace,
            span_id=entry.span_id,
            labels=dict(entry.labels) if entry.labels else {},
            json_payload=entry.payload if isinstance(entry.payload, dict) else {},
            text_payload=str(entry.payload) if not isinstance(entry.payload, dict) else None,
            source_location=entry.source_location._asdict() if hasattr(entry, 'source_location') and entry.source_location else None
        )


@dataclass
class LogFilter:
    """Filter criteria for GCP logs."""
    resource_type: Optional[str] = None
    service_name: Optional[str] = None
    severity: Optional[str] = None
    text_search: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize default values after creation."""
        if self.labels is None:
            self.labels = {}
        if self.end_time is None:
            self.end_time = datetime.now(timezone.utc)
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


class GCPLogReader(GCPBaseClient):
    """GCP Cloud Logging client for integration tests."""
    
    def __init__(self, gcp_config: GCPConfig):
        """Initialize GCP log reader."""
        super().__init__(gcp_config)
        self._client: Optional[Any] = None
        
        if not GCP_AVAILABLE:
            # In test environments without GCP, use mock behavior
            self._mock_mode = True
        else:
            self._mock_mode = False
    
    @property
    def client(self):
        """Get or create GCP logging client."""
        if self._mock_mode:
            return None
            
        if not self._client and GCP_AVAILABLE:
            self._client = gcp_logging.Client(project=self.config.project_id)
        return self._client
    
    async def read_logs(self, log_filter: LogFilter, max_results: int = 100) -> List[LogEntry]:
        """Read logs from GCP Cloud Logging."""
        if self._mock_mode:
            # Return empty logs in test environments without GCP
            return []
        
        if not GCP_AVAILABLE:
            raise ImportError("google-cloud-logging is not installed")
        
        try:
            filter_string = log_filter.to_filter_string()
            
            # Use sync client in async context (GCP client handles this)
            entries = self.client.list_entries(
                filter_=filter_string,
                order_by=gcp_logging.DESCENDING,
                max_results=max_results
            )
            
            log_entries = []
            for entry in entries:
                log_entry = LogEntry.from_gcp_entry(entry)
                log_entries.append(log_entry)
            
            return log_entries
            
        except Exception as e:
            # In integration tests, log the error but don't fail
            print(f"Warning: GCP log reading failed: {e}")
            return []
    
    async def search_errors(self, time_range_hours: int = 1, service_name: Optional[str] = None) -> List[LogEntry]:
        """Search for error logs in the specified time range."""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=time_range_hours)
        
        log_filter = LogFilter(
            severity="ERROR",
            service_name=service_name,
            start_time=start_time,
            end_time=end_time
        )
        
        return await self.read_logs(log_filter)
    
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
    
    async def close(self):
        """Close the GCP client connection."""
        if self._client:
            # GCP logging client doesn't require explicit cleanup
            pass