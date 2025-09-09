"""Utilities Tests - Split from log_reader.py"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from typing import Any, AsyncIterator, Dict, List, Optional

# Optional GCP imports with graceful fallback
try:
    from google.cloud import logging as gcp_logging
    GCP_LOGGING_AVAILABLE = True
except ImportError:
    gcp_logging = None
    GCP_LOGGING_AVAILABLE = False

from test_framework.unified.base_interfaces import ILogAnalyzer
from test_framework.gcp_integration.base import GCPBaseClient, GCPConfig


@dataclass
class LogEntry:
    """Log entry data structure"""
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}
        if self.json_payload is None:
            self.json_payload = {}

    def from_gcp_entry(cls, entry: Any) -> 'LogEntry':
        """Create LogEntry from GCP log entry."""
        # Handle severity - in v3.x it's already a string
        severity = str(entry.severity) if entry.severity else 'DEFAULT'
        
        return cls(
            timestamp=entry.timestamp,
            severity=severity,
            message=entry.payload.get('message', '') if isinstance(entry.payload, dict) else str(entry.payload),
            service_name=entry.resource.labels.get('service_name', 'unknown'),
            trace_id=entry.trace,
            span_id=entry.span_id,
            labels=dict(entry.labels) if entry.labels else {},
            json_payload=entry.payload if isinstance(entry.payload, dict) else {},
            text_payload=str(entry.payload) if not isinstance(entry.payload, dict) else None,
            source_location=entry.source_location._asdict() if entry.source_location else None
        )

    def __post_init__(self):
        if self.labels is None:
            self.labels = {}
        if self.end_time is None:
            self.end_time = datetime.now(UTC)
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

    def __init__(self, gcp_config: GCPConfig):
        super().__init__(gcp_config)
        self._client: Optional[gcp_logging.Client] = None

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

        def _fetch():
            return list(self._client.list_entries(
                filter_=full_filter,
                page_size=1000
            ))
