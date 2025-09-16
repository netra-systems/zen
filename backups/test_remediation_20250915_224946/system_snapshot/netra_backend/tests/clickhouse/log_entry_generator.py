"""
Log Entry Generator
Generates realistic log entry data for testing
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from netra_backend.tests.clickhouse.data_models import LogEntry
from netra_backend.tests.clickhouse.generator_base import DataGeneratorBase

class LogEntryGenerator(DataGeneratorBase):
    """Generate realistic log entries"""
    
    def _setup_log_generation(self, count: int, start_time: Optional[datetime]) -> tuple[datetime, List[str]]:
        """Setup log generation with start time and request IDs"""
        if not start_time:
            start_time = datetime.now() - timedelta(hours=1)
        request_ids = [str(uuid.uuid4()) for _ in range(count // 10)]
        return start_time, request_ids
    
    def _calculate_log_timestamp(self, start_time: datetime) -> datetime:
        """Calculate realistic log timestamp using exponential distribution"""
        time_offset = random.expovariate(1 / 60)  # Average 60 seconds between logs
        return start_time + timedelta(seconds=min(time_offset, 3600))
    
    def _determine_log_level(self, error_rate: float) -> str:
        """Determine log level with realistic distribution"""
        rand = random.random()
        if rand < error_rate:
            return "ERROR"
        elif rand < error_rate * 3:
            return "WARNING"
        elif rand < 0.3:
            return "DEBUG"
        return "INFO"
    
    def _generate_error_message(self, component: str) -> str:
        """Generate realistic error messages"""
        pattern = random.choice(self.error_patterns)
        return pattern.format(
            service=random.choice(["redis", "postgres", "clickhouse"]),
            model=random.choice(self.models),
            component=component,
            size=random.randint(100, 8192),
            tokens=random.randint(5000, 10000),
            limit=4096,
            user_id=random.randint(1, 100),
            op=random.choice(["insert", "update", "delete", "query"]),
            field=random.choice(["user_id", "workload_id", "metrics"])
        )
    
    def _generate_warning_message(self) -> str:
        """Generate realistic warning messages"""
        return random.choice([
            f"High latency detected: {random.uniform(1000, 5000):.2f}ms",
            f"Memory usage above threshold: {random.uniform(80, 95):.1f}%",
            f"Retry attempt {random.randint(1, 3)} for operation",
            f"Cache miss rate high: {random.uniform(30, 60):.1f}%",
            f"Queue depth increasing: {random.randint(100, 1000)} messages"
        ])
    
    def _generate_debug_message(self, request_ids: List[str]) -> str:
        """Generate realistic debug messages"""
        return random.choice([
            f"Processing request {random.choice(request_ids)}",
            f"Cache hit for key: {uuid.uuid4().hex[:8]}",
            f"Database query executed in {random.uniform(1, 100):.2f}ms",
            f"WebSocket message sent to {random.randint(1, 50)} clients",
            f"Background task completed: {random.choice(['cleanup', 'sync', 'backup'])}"
        ])
    
    def _generate_info_message(self) -> str:
        """Generate realistic info messages"""
        return random.choice([
            f"Request completed successfully",
            f"New connection from user {random.randint(1, 100)}",
            f"Model {random.choice(self.models)} initialized",
            f"Health check passed",
            f"Scheduled task started: {random.choice(['metrics', 'cleanup', 'report'])}"
        ])
    
    def _generate_message_by_level(self, level: str, component: str, request_ids: List[str]) -> str:
        """Generate message based on log level"""
        if level == "ERROR":
            return self._generate_error_message(component)
        elif level == "WARNING":
            return self._generate_warning_message()
        elif level == "DEBUG":
            return self._generate_debug_message(request_ids)
        return self._generate_info_message()
    
    def _create_log_entry(self, timestamp: datetime, level: str, component: str, 
                         message: str, request_ids: List[str]) -> LogEntry:
        """Create LogEntry with metadata"""
        return LogEntry(
            timestamp=timestamp,
            level=level,
            component=component,
            message=message,
            metadata={
                "request_id": random.choice(request_ids),
                "user_id": random.randint(1, 100),
                "trace_id": str(uuid.uuid4()),
                "latency_ms": random.uniform(10, 500) if random.random() > 0.5 else None,
                "error_code": random.choice(["ERR_001", "ERR_002", "ERR_003"]) if level == "ERROR" else None
            }
        )
    
    def generate_log_entries(self, count: int, start_time: Optional[datetime] = None,
                           error_rate: float = 0.05) -> List[LogEntry]:
        """Generate realistic log entries with patterns"""
        start_time, request_ids = self._setup_log_generation(count, start_time)
        logs = []
        for i in range(count):
            timestamp = self._calculate_log_timestamp(start_time)
            level = self._determine_log_level(error_rate)
            component = random.choice(self.components)
            message = self._generate_message_by_level(level, component, request_ids)
            log = self._create_log_entry(timestamp, level, component, message, request_ids)
            logs.append(log)
        return sorted(logs, key=lambda x: x.timestamp)