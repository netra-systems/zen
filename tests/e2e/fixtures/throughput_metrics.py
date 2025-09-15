"""
Throughput testing metrics and data structures.

This module contains the core data classes and configuration for high-volume
throughput testing of the Netra Apex AI platform.
"""

import os
import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, NamedTuple, Optional

# High-volume test configuration
HIGH_VOLUME_CONFIG = {
    # Throughput targets
    "max_message_rate": 10000,           # messages/second
    "sustained_throughput_target": 5000, # messages/second
    "peak_throughput_target": 10000,     # messages/second
    
    # Latency requirements
    "latency_p50_target": 0.05,          # 50ms
    "latency_p95_target": 0.2,           # 200ms  
    "latency_p99_target": 0.5,           # 500ms
    
    # Connection and scaling
    "max_concurrent_connections": 500,
    "connection_scaling_steps": [1, 10, 50, 100, 250, 500],
    "message_rate_scaling_steps": [100, 500, 1000, 2500, 5000, 7500, 10000],
    
    # Test durations
    "burst_duration": 60,                # seconds
    "sustained_load_time": 30,           # seconds
    "ramp_up_time": 10,                  # seconds
    "ramp_down_time": 10,                # seconds
    "stress_test_duration": 300,         # 5 minutes
    
    # Resource limits
    "max_memory_growth_mb": 200,
    "memory_leak_threshold_mb": 50,
    "cpu_usage_threshold": 0.8,          # 80%
    
    # Reliability thresholds
    "min_delivery_ratio": 0.999,         # 99.9%
    "max_message_loss_ratio": 0.001,     # 0.1%
    "max_duplicate_ratio": 0.001,        # 0.1%
    
    # Queue and backpressure
    "queue_overflow_threshold": 10000,
    "backpressure_timeout": 5.0,
    "queue_recovery_timeout": 30.0,
    
    # Error injection
    "error_injection_rate": 0.1,         # 10%
    "connection_drop_rate": 0.05,        # 5%
    "network_failure_duration": 5.0,     # seconds
}


class ThroughputMetrics(NamedTuple):
    """Comprehensive throughput metrics."""
    messages_sent: int
    messages_received: int
    messages_failed: int
    send_rate: float  # messages/second
    receive_rate: float
    latency_p50: float
    latency_p95: float
    latency_p99: float
    delivery_ratio: float
    error_rate: float
    memory_usage_mb: float
    cpu_usage: float
    queue_depth: int
    backpressure_events: int


@dataclass
class LatencyMeasurement:
    """Individual latency measurement."""
    message_id: str
    send_time: float
    receive_time: float
    processing_time: float
    queue_time: float = 0.0
    
    @property
    def total_latency(self) -> float:
        """Total end-to-end latency."""
        return self.receive_time - self.send_time
    
    @property
    def server_latency(self) -> float:
        """Server processing latency."""
        return self.processing_time


@dataclass
class LoadTestResults:
    """Comprehensive load test results."""
    test_name: str
    start_time: float
    end_time: float
    total_duration: float
    
    # Throughput metrics
    peak_throughput: float = 0.0
    sustained_throughput: float = 0.0
    average_throughput: float = 0.0
    
    # Latency metrics
    latency_measurements: List[LatencyMeasurement] = field(default_factory=list)
    latency_p50: float = 0.0
    latency_p95: float = 0.0
    latency_p99: float = 0.0
    latency_p999: float = 0.0
    
    # Reliability metrics
    messages_sent: int = 0
    messages_received: int = 0
    messages_failed: int = 0
    delivery_ratio: float = 0.0
    duplicate_count: int = 0
    ordering_violations: int = 0
    
    # Resource metrics
    peak_memory_mb: float = 0.0
    memory_growth_mb: float = 0.0
    peak_cpu_usage: float = 0.0
    connection_count: int = 0
    
    # Error and recovery metrics
    error_count: int = 0
    recovery_count: int = 0
    backpressure_events: int = 0
    queue_overflow_events: int = 0
    
    # Scaling metrics
    connection_scaling_data: Dict[int, ThroughputMetrics] = field(default_factory=dict)
    rate_scaling_data: Dict[int, ThroughputMetrics] = field(default_factory=dict)


class ThroughputAnalyzer:
    """Analyze throughput test results and metrics."""
    
    @staticmethod
    def analyze_latency_distribution(latency_measurements: List[LatencyMeasurement]) -> Dict[str, float]:
        """Analyze latency distribution and return percentiles."""
        if not latency_measurements:
            return {
                "p50": 0.0, "p95": 0.0, "p99": 0.0, "p999": 0.0,
                "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0
            }
        
        latencies = [m.total_latency for m in latency_measurements]
        latencies.sort()
        
        def percentile(data, p):
            index = int(len(data) * p / 100.0)
            return data[min(index, len(data) - 1)]
        
        return {
            "p50": percentile(latencies, 50),
            "p95": percentile(latencies, 95),
            "p99": percentile(latencies, 99),
            "p999": percentile(latencies, 99.9),
            "mean": statistics.mean(latencies),
            "std": statistics.stdev(latencies) if len(latencies) > 1 else 0.0,
            "min": min(latencies),
            "max": max(latencies)
        }
    
    @staticmethod
    def calculate_throughput_metrics(start_time: float, end_time: float, 
                                   messages_sent: int, messages_received: int) -> Dict[str, float]:
        """Calculate throughput metrics from test data."""
        duration = end_time - start_time
        if duration <= 0:
            return {"send_rate": 0.0, "receive_rate": 0.0, "delivery_ratio": 0.0}
        
        send_rate = messages_sent / duration
        receive_rate = messages_received / duration
        delivery_ratio = messages_received / messages_sent if messages_sent > 0 else 0.0
        
        return {
            "send_rate": send_rate,
            "receive_rate": receive_rate,
            "delivery_ratio": delivery_ratio,
            "duration": duration
        }
    
    @staticmethod
    def validate_message_ordering(received_messages: List[Dict]) -> Dict[str, Any]:
        """Validate message ordering and detect violations."""
        validation_result = {
            "total_messages": len(received_messages),
            "ordering_violations": 0,
            "missing_messages": [],
            "duplicate_messages": [],
            "out_of_order_sequences": []
        }
        
        if not received_messages:
            return validation_result
        
        # Group by sequence to check ordering
        sequence_groups = {}
        seen_message_ids = set()
        
        for msg in received_messages:
            msg_id = msg.get("message_id")
            sequence_id = msg.get("sequence_id", 0)
            
            # Check for duplicates
            if msg_id in seen_message_ids:
                validation_result["duplicate_messages"].append(msg_id)
            else:
                seen_message_ids.add(msg_id)
            
            # Group by sequence
            if sequence_id not in sequence_groups:
                sequence_groups[sequence_id] = []
            sequence_groups[sequence_id].append(msg)
        
        # Check ordering within sequences
        for sequence_id, messages in sequence_groups.items():
            messages.sort(key=lambda x: x.get("timestamp", 0))
            
            expected_sequence = 0
            for msg in messages:
                msg_sequence = msg.get("sequence_id", 0)
                if msg_sequence != expected_sequence:
                    validation_result["ordering_violations"] += 1
                    validation_result["out_of_order_sequences"].append({
                        "expected": expected_sequence,
                        "actual": msg_sequence,
                        "message_id": msg.get("message_id")
                    })
                
                # Check for missing messages in sequence
                if msg_sequence > expected_sequence:
                    for missing in range(expected_sequence, msg_sequence):
                        validation_result["missing_messages"].append({
                            "sequence_id": missing
                        })
                
                expected_sequence = sequence_id + 1
        
        return validation_result
