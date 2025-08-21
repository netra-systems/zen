"""
Real-time deployment monitoring with GCP log integration.
"""

import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from test_framework.gcp_integration.log_reader_core import GCPLogReader
from test_framework.gcp_integration.log_reader_helpers import (
    extract_error_patterns,
    filter_logs_by_time,
    format_log_entry,
)

logger = logging.getLogger(__name__)

@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: datetime
    severity: str
    service: str
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)
    resource: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DeploymentMetrics:
    """Real-time deployment metrics."""
    start_time: datetime
    services_started: int = 0
    services_completed: int = 0
    services_failed: int = 0
    total_logs: int = 0
    error_count: int = 0
    warning_count: int = 0
    average_response_time_ms: float = 0.0
    
    @property
    def duration_seconds(self) -> float:
        """Get deployment duration."""
        return (datetime.utcnow() - self.start_time).total_seconds()
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        return self.error_count / self.total_logs if self.total_logs > 0 else 0.0

class RealTimeMonitor:
    """Real-time monitoring of GCP deployments."""
    
    def __init__(self, project_id: str, buffer_size: int = 1000):
        self.project_id = project_id
        self.log_reader = GCPLogReader(project_id)
        self.buffer_size = buffer_size
        self.log_buffer: List[LogEntry] = []
        self.metrics = DeploymentMetrics(start_time=datetime.utcnow())
        self.is_monitoring = False
        
    async def start_monitoring(self, 
                              services: List[str],
                              interval_seconds: int = 5) -> None:
        """
        Start real-time monitoring of services.
        
        Args:
            services: List of service names to monitor
            interval_seconds: Polling interval in seconds
        """
        self.is_monitoring = True
        logger.info(f"Starting real-time monitoring for services: {services}")
        
        while self.is_monitoring:
            try:
                # Fetch logs for each service
                for service in services:
                    await self._fetch_service_logs(service)
                
                # Process buffered logs
                await self._process_log_buffer()
                
                # Wait for next interval
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(interval_seconds)
    
    async def stop_monitoring(self) -> None:
        """Stop real-time monitoring."""
        self.is_monitoring = False
        logger.info("Stopped real-time monitoring")
    
    async def _fetch_service_logs(self, service_name: str) -> None:
        """Fetch recent logs for a service."""
        try:
            # Calculate time window (last 30 seconds)
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(seconds=30)
            
            # Fetch logs from GCP
            raw_logs = self.log_reader.read_logs(
                resource_type="cloud_run_revision",
                resource_labels={"service_name": service_name},
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                limit=100
            )
            
            # Convert to structured entries
            for raw_log in raw_logs:
                entry = self._parse_log_entry(raw_log, service_name)
                if entry:
                    self.log_buffer.append(entry)
                    
                    # Update metrics
                    self.metrics.total_logs += 1
                    if entry.severity == "ERROR":
                        self.metrics.error_count += 1
                    elif entry.severity == "WARNING":
                        self.metrics.warning_count += 1
            
            # Trim buffer if needed
            if len(self.log_buffer) > self.buffer_size:
                self.log_buffer = self.log_buffer[-self.buffer_size:]
                
        except Exception as e:
            logger.error(f"Error fetching logs for {service_name}: {str(e)}")
    
    def _parse_log_entry(self, raw_log: Dict[str, Any], service_name: str) -> Optional[LogEntry]:
        """Parse raw GCP log into structured entry."""
        try:
            # Extract timestamp
            timestamp_str = raw_log.get("timestamp", "")
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                timestamp = datetime.utcnow()
            
            # Extract message
            if "jsonPayload" in raw_log:
                message = json.dumps(raw_log["jsonPayload"])
            elif "textPayload" in raw_log:
                message = raw_log["textPayload"]
            else:
                message = str(raw_log)
            
            return LogEntry(
                timestamp=timestamp,
                severity=raw_log.get("severity", "INFO"),
                service=service_name,
                message=message,
                trace_id=raw_log.get("trace"),
                span_id=raw_log.get("spanId"),
                labels=raw_log.get("labels", {}),
                resource=raw_log.get("resource", {})
            )
            
        except Exception as e:
            logger.error(f"Error parsing log entry: {str(e)}")
            return None
    
    async def _process_log_buffer(self) -> None:
        """Process buffered logs for insights."""
        if not self.log_buffer:
            return
        
        # Detect deployment phases
        for log in self.log_buffer:
            if "deployment started" in log.message.lower():
                self.metrics.services_started += 1
            elif "deployment completed" in log.message.lower():
                self.metrics.services_completed += 1
            elif "deployment failed" in log.message.lower():
                self.metrics.services_failed += 1
    
    async def stream_deployment_logs(self, 
                                    service_name: str,
                                    start_time: Optional[datetime] = None) -> AsyncIterator[LogEntry]:
        """
        Stream deployment logs for a service.
        
        Args:
            service_name: Name of the service
            start_time: Start time for log streaming
            
        Yields:
            LogEntry objects
        """
        if start_time is None:
            start_time = datetime.utcnow()
        
        last_check = start_time
        
        while True:
            try:
                # Fetch new logs since last check
                raw_logs = self.log_reader.read_logs(
                    resource_type="cloud_run_revision",
                    resource_labels={"service_name": service_name},
                    start_time=last_check.isoformat(),
                    limit=50
                )
                
                # Yield new log entries
                for raw_log in raw_logs:
                    entry = self._parse_log_entry(raw_log, service_name)
                    if entry:
                        yield entry
                
                # Update last check time
                last_check = datetime.utcnow()
                
                # Small delay to avoid overwhelming the API
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error streaming logs: {str(e)}")
                await asyncio.sleep(5)
    
    async def detect_critical_errors(self, 
                                    logs: List[LogEntry],
                                    patterns: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Detect critical errors in logs.
        
        Args:
            logs: List of log entries to analyze
            patterns: Optional custom error patterns
            
        Returns:
            List of critical errors found
        """
        if patterns is None:
            patterns = [
                r"CRITICAL",
                r"FATAL",
                r"panic",
                r"OutOfMemory",
                r"StackOverflow",
                r"Connection pool exhausted",
                r"Database connection failed",
                r"Service unavailable"
            ]
        
        critical_errors = []
        
        for log in logs:
            # Check severity
            if log.severity in ["CRITICAL", "EMERGENCY"]:
                critical_errors.append({
                    "timestamp": log.timestamp,
                    "service": log.service,
                    "message": log.message,
                    "type": "severity"
                })
                continue
            
            # Check patterns
            import re
            for pattern in patterns:
                if re.search(pattern, log.message, re.IGNORECASE):
                    critical_errors.append({
                        "timestamp": log.timestamp,
                        "service": log.service,
                        "message": log.message,
                        "type": "pattern",
                        "pattern": pattern
                    })
                    break
        
        return critical_errors
    
    async def recommend_actions(self, 
                               errors: List[Dict[str, Any]]) -> List[str]:
        """
        Recommend actions based on detected errors.
        
        Args:
            errors: List of detected errors
            
        Returns:
            List of recommended actions
        """
        recommendations = []
        
        # Analyze error patterns
        error_types = {}
        for error in errors:
            msg = error["message"].lower()
            
            if "memory" in msg or "oom" in msg:
                error_types["memory"] = error_types.get("memory", 0) + 1
            elif "connection" in msg or "timeout" in msg:
                error_types["network"] = error_types.get("network", 0) + 1
            elif "database" in msg or "sql" in msg:
                error_types["database"] = error_types.get("database", 0) + 1
            elif "permission" in msg or "denied" in msg:
                error_types["permission"] = error_types.get("permission", 0) + 1
        
        # Generate recommendations
        if error_types.get("memory", 0) > 2:
            recommendations.append("Increase memory allocation for affected services")
            recommendations.append("Review code for memory leaks")
        
        if error_types.get("network", 0) > 3:
            recommendations.append("Check network connectivity and firewall rules")
            recommendations.append("Increase timeout values")
        
        if error_types.get("database", 0) > 2:
            recommendations.append("Check database connection pool settings")
            recommendations.append("Verify database credentials and connectivity")
        
        if error_types.get("permission", 0) > 1:
            recommendations.append("Review IAM permissions for service accounts")
            recommendations.append("Check API quota limits")
        
        # General recommendations
        if len(errors) > 10:
            recommendations.append("Consider rolling back deployment due to high error rate")
        
        return recommendations
    
    def get_metrics_summary(self) -> str:
        """Get formatted metrics summary."""
        lines = [
            "DEPLOYMENT METRICS",
            "=" * 40,
            f"Duration: {self.metrics.duration_seconds:.2f} seconds",
            f"Services Started: {self.metrics.services_started}",
            f"Services Completed: {self.metrics.services_completed}",
            f"Services Failed: {self.metrics.services_failed}",
            f"Total Logs: {self.metrics.total_logs}",
            f"Error Count: {self.metrics.error_count}",
            f"Warning Count: {self.metrics.warning_count}",
            f"Error Rate: {self.metrics.error_rate:.2%}"
        ]
        
        return "\n".join(lines)
    
    async def generate_deployment_timeline(self, 
                                          logs: List[LogEntry]) -> List[Dict[str, Any]]:
        """
        Generate deployment timeline from logs.
        
        Args:
            logs: List of log entries
            
        Returns:
            Timeline of deployment events
        """
        timeline = []
        
        # Sort logs by timestamp
        sorted_logs = sorted(logs, key=lambda x: x.timestamp)
        
        for log in sorted_logs:
            # Identify significant events
            event = None
            
            if "started" in log.message.lower():
                event = "start"
            elif "completed" in log.message.lower() or "success" in log.message.lower():
                event = "complete"
            elif "failed" in log.message.lower() or "error" in log.message.lower():
                event = "failure"
            elif "health check" in log.message.lower():
                event = "health_check"
            elif "rollback" in log.message.lower():
                event = "rollback"
            
            if event:
                timeline.append({
                    "timestamp": log.timestamp.isoformat(),
                    "service": log.service,
                    "event": event,
                    "message": log.message[:200]  # Truncate long messages
                })
        
        return timeline