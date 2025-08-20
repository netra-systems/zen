"""Core Tests - Split from test_metrics_aggregation_pipeline.py

BVJ (Business Value Justification):
1. Segment: Enterprise ($10K+ MRR customers requiring accurate performance insights)
2. Business Goal: Prevent revenue loss from analytics failures that impact optimization decisions
3. Value Impact: Ensures customers can make data-driven AI optimization decisions 
4. Revenue Impact: Protects $10K MRR by providing accurate, real-time performance metrics

CRITICAL REQUIREMENTS:
1. Multi-source metrics collection from diverse data sources
2. Time-series aggregation accuracy with 99.99% precision
3. Percentile calculations (p50, p95, p99) for latency analysis
4. Alert threshold triggering for proactive monitoring
5. Metrics export to multiple formats (JSON, CSV, Prometheus)

PERFORMANCE TARGETS:
- Ingestion: 1K metrics/second minimum
- Aggregation: <500ms processing time
- Percentile calculation: <100ms for 10K data points
- Export: <1s for standard datasets
"""

import asyncio
import json
import time
import uuid
import statistics
from typing import Dict, List, Any, Optional
from decimal import Decimal
import pytest
import pytest_asyncio
from app.logging_config import central_logger
from test_framework.unified.base_interfaces import IntegrationTestBase
import random

    def __init__(self, source_name: str):
        self.source_name = source_name
        self.metrics_buffer = []
        self.active = False

    def _generate_realistic_latency(self) -> float:
        """Generate realistic latency values with proper distribution."""
        import random
        # Log-normal distribution for realistic latency patterns
        return max(1.0, random.lognormvariate(4.5, 0.5))

    def __init__(self):
        self.metrics_store = {}
        self.aggregation_cache = {}
        self.processing_times = []

    def __init__(self):
        self.calculation_cache = {}

    def __init__(self):
        self.thresholds = {}
        self.alerts_triggered = []

    def configure_threshold(self, 
                          metric_name: str, 
                          threshold_type: str, 
                          value: float,
                          severity: str = "warning") -> None:
        """Configure alert threshold."""
        if metric_name not in self.thresholds:
            self.thresholds[metric_name] = []
        
        self.thresholds[metric_name].append({
            "type": threshold_type,  # "above", "below", "percentile"
            "value": value,
            "severity": severity,
            "enabled": True
        })

    def __init__(self):
        self.export_history = []

    def __init__(self):
        super().__init__()
        self.data_sources = []
        self.aggregator = TimeSeriesAggregator()
        self.percentile_calculator = PercentileCalculator()
        self.alert_monitor = AlertThresholdMonitor()
        self.exporter = MetricsExporter()
