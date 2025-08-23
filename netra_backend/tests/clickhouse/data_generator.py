"""
Realistic Data Generator for ClickHouse Tests
Unified interface for generating production-like test data
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from netra_backend.tests.clickhouse.corpus_generator import CorpusGenerator
from netra_backend.tests.clickhouse.data_models import LLMEvent, LogEntry, WorkloadMetric
from netra_backend.tests.clickhouse.llm_event_generator import LLMEventGenerator
from netra_backend.tests.clickhouse.log_entry_generator import LogEntryGenerator
from netra_backend.tests.clickhouse.workload_metric_generator import WorkloadMetricGenerator

class RealisticDataGenerator:
    """Generate realistic test data for ClickHouse"""
    
    def __init__(self, seed: Optional[int] = None):
        self.llm_generator = LLMEventGenerator(seed)
        self.workload_generator = WorkloadMetricGenerator(seed)
        self.log_generator = LogEntryGenerator(seed)
        self.corpus_generator = CorpusGenerator(seed)
    
    def generate_llm_events(self, count: int, start_time: Optional[datetime] = None,
                           time_span_hours: int = 24) -> List[LLMEvent]:
        """Generate realistic LLM events"""
        return self.llm_generator.generate_llm_events(count, start_time, time_span_hours)
    
    def generate_workload_metrics(self, count: int, start_time: Optional[datetime] = None,
                                 interval_seconds: int = 60) -> List[WorkloadMetric]:
        """Generate realistic workload metrics with nested arrays"""
        return self.workload_generator.generate_workload_metrics(count, start_time, interval_seconds)
    
    def generate_log_entries(self, count: int, start_time: Optional[datetime] = None,
                           error_rate: float = 0.05) -> List[LogEntry]:
        """Generate realistic log entries with patterns"""
        return self.log_generator.generate_log_entries(count, start_time, error_rate)
    
    def generate_corpus_data(self, count: int, 
                           workload_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Generate realistic corpus data for training"""
        return self.corpus_generator.generate_corpus_data(count, workload_types)