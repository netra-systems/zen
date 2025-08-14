"""Log Data Generator

This module generates realistic log data with specific patterns and behaviors.
"""

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

from .models import RealisticTestDataConfigManager


class LogGenerator:
    """Generates realistic log data with various patterns"""
    
    def __init__(self, config_manager: RealisticTestDataConfigManager):
        """Initialize log generator"""
        self.config = config_manager
    
    def generate_realistic_log_data(
        self,
        pattern: str = "normal_operation",
        duration_hours: int = 24,
        volume: int = 10000
    ) -> List[Dict[str, Any]]:
        """
        Generate realistic log data with specific patterns
        
        Args:
            pattern: Type of log pattern to generate
            duration_hours: Time span for logs
            volume: Number of log entries
            
        Returns:
            List of realistic log entries
        """
        logs = []
        start_time = datetime.now(timezone.utc) - timedelta(hours=duration_hours)
        time_increment = timedelta(hours=duration_hours) / volume
        
        pattern_config = self.config.get_log_pattern_config(pattern)
        
        for i in range(volume):
            timestamp = start_time + (time_increment * i)
            
            log_entry = {
                "timestamp": timestamp.isoformat(),
                "level": self._select_log_level(pattern, i, volume),
                "service": random.choice(["api", "worker", "scheduler", "agent", "database"]),
                "message": self._generate_log_message(pattern, i, volume),
                "metrics": self._generate_log_metrics(pattern, i, volume, pattern_config)
            }
            
            # Add trace information
            if random.random() < 0.3:
                log_entry["trace_id"] = str(uuid.uuid4())
                log_entry["span_id"] = str(uuid.uuid4())[:8]
            
            logs.append(log_entry)
        
        return logs
    
    def _select_log_level(self, pattern: str, index: int, total: int) -> str:
        """Select appropriate log level based on pattern"""
        if pattern == "error_cascade":
            # Increasing error rate
            error_probability = (index / total) * 0.8
            if random.random() < error_probability:
                return random.choice(["ERROR", "CRITICAL"])
            elif random.random() < 0.3:
                return "WARNING"
            else:
                return "INFO"
        
        elif pattern == "memory_leak":
            # Increasing warnings
            if index > total * 0.7:
                return random.choice(["WARNING", "ERROR"])
            else:
                return random.choice(["INFO", "DEBUG"])
        
        else:  # normal_operation
            weights = [0.7, 0.2, 0.08, 0.02]  # INFO, DEBUG, WARNING, ERROR
            return random.choices(
                ["INFO", "DEBUG", "WARNING", "ERROR"],
                weights=weights
            )[0]
    
    def _generate_log_message(self, pattern: str, index: int, total: int) -> str:
        """Generate realistic log message based on pattern"""
        if pattern == "error_cascade":
            if index < total * 0.3:
                return random.choice([
                    "Request processed successfully",
                    "Cache hit for query",
                    "Model inference completed"
                ])
            elif index < total * 0.6:
                return random.choice([
                    "Connection pool exhausted, queuing request",
                    "Retry attempt 1 of 3",
                    "Upstream service responding slowly"
                ])
            else:
                return random.choice([
                    "Connection refused: Too many connections",
                    "Circuit breaker opened for service",
                    "Cascading failure detected",
                    "Emergency shutdown initiated"
                ])
        
        elif pattern == "memory_leak":
            base_messages = [
                f"Heap size: {1000 + (index * 10)}MB",
                f"GC pause: {50 + (index / total * 500)}ms",
                f"Active connections: {100 + (index // 10)}",
                "Memory allocation failed, retrying"
            ]
            return random.choice(base_messages)
        
        else:
            return random.choice([
                "Request processed in 45ms",
                "Model loaded successfully",
                "Batch processing completed",
                "Cache refreshed",
                "Health check passed",
                "Metrics exported",
                "Configuration reloaded"
            ])
    
    def _generate_log_metrics(
        self,
        pattern: str,
        index: int,
        total: int,
        pattern_config: Dict[str, Any]
    ) -> Dict[str, float]:
        """Generate metrics that follow the pattern"""
        progress = index / total
        
        if pattern == "memory_leak":
            return {
                "memory_mb": 500 + (progress * 3000),  # Gradual increase
                "gc_count": int(10 + progress * 100),
                "response_time_ms": 50 + (progress * 200),  # Degrading
                "cpu_percent": min(20 + (progress * 60), 95)
            }
        
        elif pattern == "error_cascade":
            error_rate = 0.01 if progress < 0.3 else min(progress * 0.5, 0.8)
            return {
                "error_rate": error_rate,
                "success_rate": 1 - error_rate,
                "response_time_ms": 100 * (1 + progress * 5),  # Exponential degradation
                "queue_depth": int(10 * (1 + progress ** 2 * 100))
            }
        
        elif pattern == "performance_degradation":
            return {
                "p50_latency_ms": 50 + (progress * 50),
                "p95_latency_ms": 150 + (progress * 300),
                "p99_latency_ms": 300 + (progress * 700),
                "throughput_rps": max(1000 - (progress * 800), 100),
                "error_rate": min(0.01 + (progress * 0.1), 0.15)
            }
        
        else:  # normal_operation
            # Add realistic noise
            return {
                "response_time_ms": 50 + random.gauss(0, 10),
                "throughput_rps": 1000 + random.gauss(0, 50),
                "error_rate": max(0, 0.01 + random.gauss(0, 0.002)),
                "cpu_percent": 40 + random.gauss(0, 5),
                "memory_mb": 2000 + random.gauss(0, 100)
            }