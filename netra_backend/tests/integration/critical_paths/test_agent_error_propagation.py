"""Agent Error Propagation L2 Integration Tests

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (operational excellence)
- Business Goal: Error visibility and debugging efficiency
- Value Impact: Protects $7K MRR from debugging/troubleshooting overhead
- Strategic Impact: Core observability for agent reliability and support

Critical Path: Error capture -> Enrichment -> Propagation -> Aggregation -> Reporting
Coverage: Real error collectors, enrichment pipeline, routing logic, aggregation
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import json
import logging
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
# from app.monitoring.metrics_collector import MetricsCollector  # TODO: Fix import path

from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.core.database_connection_manager import DatabaseConnectionManager

# Real components for L2 testing
from netra_backend.app.services.redis_service import RedisService

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for classification."""
    AGENT_EXECUTION = "agent_execution"
    LLM_API = "llm_api"
    TOOL_EXECUTION = "tool_execution"
    NETWORK = "network"
    DATABASE = "database"
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    RESOURCE = "resource"

@dataclass
class ErrorEvent:
    """Represents an error event in the system."""
    error_id: str
    agent_id: str
    agent_type: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Dict[str, Any]
    stack_trace: str
    context: Dict[str, Any]
    timestamp: datetime
    source_module: str
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["category"] = self.category.value
        data["severity"] = self.severity.value
        data["timestamp"] = self.timestamp.isoformat()
        return data

class ErrorCollector:
    """Collects errors from various sources."""
    
    def __init__(self):
        self.collected_errors = []
        self.error_hooks = []
        
    def add_error_hook(self, hook: Callable[[ErrorEvent], None]):
        """Add a hook that gets called when errors are collected."""
        self.error_hooks.append(hook)
        
    def collect_error(self, error: Exception, context: Dict[str, Any]) -> ErrorEvent:
        """Collect an error and create an error event."""
        error_event = ErrorEvent(
            error_id=f"error_{int(time.time() * 1000000)}",
            agent_id=context.get("agent_id", "unknown"),
            agent_type=context.get("agent_type", "unknown"),
            category=self._classify_error(error, context),
            severity=self._determine_severity(error, context),
            message=str(error),
            details=self._extract_error_details(error),
            stack_trace=traceback.format_exc(),
            context=context,
            timestamp=datetime.now(),
            source_module=context.get("module", "unknown")
        )
        
        self.collected_errors.append(error_event)
        
        # Call hooks
        for hook in self.error_hooks:
            try:
                hook(error_event)
            except Exception as hook_error:
                logger.error(f"Error hook failed: {hook_error}")
        
        return error_event
    
    def _classify_error(self, error: Exception, context: Dict[str, Any]) -> ErrorCategory:
        """Classify error into appropriate category."""
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        if "timeout" in error_msg or isinstance(error, asyncio.TimeoutError):
            return ErrorCategory.TIMEOUT
        elif "connection" in error_msg or "network" in error_msg:
            return ErrorCategory.NETWORK
        elif "database" in error_msg or "sql" in error_msg:
            return ErrorCategory.DATABASE
        elif "validation" in error_msg or "invalid" in error_msg:
            return ErrorCategory.VALIDATION
        elif "llm" in context.get("module", "").lower():
            return ErrorCategory.LLM_API
        elif "tool" in context.get("module", "").lower():
            return ErrorCategory.TOOL_EXECUTION
        elif "memory" in error_msg or "resource" in error_msg:
            return ErrorCategory.RESOURCE
        else:
            return ErrorCategory.AGENT_EXECUTION
    
    def _determine_severity(self, error: Exception, context: Dict[str, Any]) -> ErrorSeverity:
        """Determine error severity based on type and context."""
        if isinstance(error, (SystemExit, KeyboardInterrupt)):
            return ErrorSeverity.CRITICAL
        elif isinstance(error, (ConnectionError, asyncio.TimeoutError)):
            return ErrorSeverity.HIGH
        elif isinstance(error, (ValueError, TypeError)):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def _extract_error_details(self, error: Exception) -> Dict[str, Any]:
        """Extract detailed information from error."""
        details = {
            "error_type": type(error).__name__,
            "error_args": list(error.args) if error.args else []
        }
        
        # Add specific details for known error types
        if hasattr(error, "errno"):
            details["errno"] = error.errno
        if hasattr(error, "strerror"):
            details["strerror"] = error.strerror
            
        return details

class ErrorEnricher:
    """Enriches errors with additional context and metadata."""
    
    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service
        
    async def enrich_error(self, error_event: ErrorEvent) -> ErrorEvent:
        """Enrich error with additional context."""
        # Add system context
        error_event.context["system_time"] = datetime.now().isoformat()
        error_event.context["process_id"] = "test_process"
        
        # Add agent history if available
        if error_event.agent_id != "unknown":
            agent_history = await self._get_agent_history(error_event.agent_id)
            error_event.context["agent_history"] = agent_history
        
        # Add related errors
        related_errors = await self._find_related_errors(error_event)
        if related_errors:
            error_event.context["related_errors"] = [e.error_id for e in related_errors]
        
        return error_event
    
    async def _get_agent_history(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get recent history for the agent."""
        try:
            history_key = f"agent_history:{agent_id}"
            history_data = await self.redis_service.client.lrange(history_key, 0, 10)
            return [json.loads(item) for item in history_data if item]
        except Exception:
            return []
    
    async def _find_related_errors(self, error_event: ErrorEvent) -> List[ErrorEvent]:
        """Find related errors that occurred recently."""
        # This would typically query a more sophisticated storage
        # For testing, we'll return empty list
        return []

class ErrorPropagator:
    """Propagates errors to appropriate handlers."""
    
    def __init__(self):
        self.routes = {}
        self.global_handlers = []
        
    def add_route(self, condition: Callable[[ErrorEvent], bool], handler: Callable[[ErrorEvent], None]):
        """Add a routing rule for errors."""
        route_id = f"route_{len(self.routes)}"
        self.routes[route_id] = {"condition": condition, "handler": handler}
        
    def add_global_handler(self, handler: Callable[[ErrorEvent], None]):
        """Add a global error handler."""
        self.global_handlers.append(handler)
        
    async def propagate_error(self, error_event: ErrorEvent) -> List[str]:
        """Propagate error to appropriate handlers."""
        handled_by = []
        
        # Check routing rules
        for route_id, route in self.routes.items():
            try:
                if route["condition"](error_event):
                    await self._call_handler(route["handler"], error_event)
                    handled_by.append(route_id)
            except Exception as e:
                logger.error(f"Error in route {route_id}: {e}")
        
        # Call global handlers
        for i, handler in enumerate(self.global_handlers):
            try:
                await self._call_handler(handler, error_event)
                handled_by.append(f"global_{i}")
            except Exception as e:
                logger.error(f"Error in global handler {i}: {e}")
        
        return handled_by
    
    async def _call_handler(self, handler: Callable, error_event: ErrorEvent):
        """Call error handler safely."""
        if asyncio.iscoroutinefunction(handler):
            await handler(error_event)
        else:
            handler(error_event)

class ErrorAggregator:
    """Aggregates errors for analysis and reporting."""
    
    def __init__(self):
        self.error_buckets = {}
        self.aggregation_rules = []
        
    def add_aggregation_rule(self, key_func: Callable[[ErrorEvent], str], 
                           window_seconds: int = 300):
        """Add an aggregation rule."""
        self.aggregation_rules.append({
            "key_func": key_func,
            "window_seconds": window_seconds
        })
    
    def aggregate_error(self, error_event: ErrorEvent):
        """Aggregate error according to rules."""
        for rule in self.aggregation_rules:
            key = rule["key_func"](error_event)
            window_key = f"{key}_{int(time.time() // rule['window_seconds'])}"
            
            if window_key not in self.error_buckets:
                self.error_buckets[window_key] = {
                    "count": 0,
                    "first_seen": error_event.timestamp,
                    "last_seen": error_event.timestamp,
                    "severity_counts": {},
                    "examples": []
                }
            
            bucket = self.error_buckets[window_key]
            bucket["count"] += 1
            bucket["last_seen"] = error_event.timestamp
            
            severity = error_event.severity.value
            bucket["severity_counts"][severity] = bucket["severity_counts"].get(severity, 0) + 1
            
            # Keep up to 3 examples
            if len(bucket["examples"]) < 3:
                bucket["examples"].append(error_event.error_id)
    
    def get_error_summary(self, time_window_seconds: int = 3600) -> Dict[str, Any]:
        """Get error summary for the specified time window."""
        cutoff_time = time.time() - time_window_seconds
        recent_buckets = {
            k: v for k, v in self.error_buckets.items()
            if v["last_seen"].timestamp() > cutoff_time
        }
        
        total_errors = sum(bucket["count"] for bucket in recent_buckets.values())
        severity_totals = {}
        
        for bucket in recent_buckets.values():
            for severity, count in bucket["severity_counts"].items():
                severity_totals[severity] = severity_totals.get(severity, 0) + count
        
        return {
            "total_errors": total_errors,
            "unique_error_types": len(recent_buckets),
            "severity_breakdown": severity_totals,
            "time_window_seconds": time_window_seconds
        }

class ErrorReporter:
    """Reports errors to external systems."""
    
    def __init__(self):
        self.reports_sent = []
        
    async def report_critical_error(self, error_event: ErrorEvent):
        """Report critical errors immediately."""
        if error_event.severity == ErrorSeverity.CRITICAL:
            report = {
                "type": "critical_error",
                "error_id": error_event.error_id,
                "agent_id": error_event.agent_id,
                "message": error_event.message,
                "timestamp": error_event.timestamp.isoformat()
            }
            self.reports_sent.append(report)
            logger.critical(f"Critical error reported: {error_event.error_id}")
    
    async def report_error_summary(self, summary: Dict[str, Any]):
        """Report error summary periodically."""
        report = {
            "type": "error_summary",
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
        self.reports_sent.append(report)

class AgentErrorPropagationManager:
    """Manages agent error propagation testing."""
    
    def __init__(self):
        self.redis_service = None
        self.db_manager = None
        self.error_collector = None
        self.error_enricher = None
        self.error_propagator = None
        self.error_aggregator = None
        self.error_reporter = None
        
    async def initialize_services(self):
        """Initialize required services."""
        self.redis_service = RedisService()
        await self.redis_service.initialize()
        
        self.db_manager = DatabaseConnectionManager()
        await self.db_manager.initialize()
        
        self.error_collector = ErrorCollector()
        self.error_enricher = ErrorEnricher(self.redis_service)
        self.error_propagator = ErrorPropagator()
        self.error_aggregator = ErrorAggregator()
        self.error_reporter = ErrorReporter()
        
        self._setup_error_pipeline()
        
    def _setup_error_pipeline(self):
        """Setup error processing pipeline."""
        # Add collection hook to propagate errors
        self.error_collector.add_error_hook(self._process_error)
        
        # Add propagation routes
        self.error_propagator.add_route(
            lambda e: e.severity == ErrorSeverity.CRITICAL,
            self.error_reporter.report_critical_error
        )
        
        # Add aggregation rules
        self.error_aggregator.add_aggregation_rule(
            lambda e: f"{e.agent_type}_{e.category.value}",
            window_seconds=300
        )
        
    def _process_error(self, error_event: ErrorEvent):
        """Process error through the pipeline."""
        asyncio.create_task(self._async_process_error(error_event))
        
    async def _async_process_error(self, error_event: ErrorEvent):
        """Async error processing."""
        try:
            # Enrich error
            enriched_error = await self.error_enricher.enrich_error(error_event)
            
            # Propagate error
            await self.error_propagator.propagate_error(enriched_error)
            
            # Aggregate error
            self.error_aggregator.aggregate_error(enriched_error)
            
        except Exception as e:
            logger.error(f"Error processing pipeline failed: {e}")
    
    def simulate_agent_error(self, error_type: str, context: Dict[str, Any]) -> ErrorEvent:
        """Simulate an agent error for testing."""
        if error_type == "timeout":
            error = asyncio.TimeoutError("Agent execution timed out")
        elif error_type == "validation":
            error = ValueError("Invalid input parameters")
        elif error_type == "network":
            error = ConnectionError("Failed to connect to external service")
        elif error_type == "critical":
            error = SystemExit("Critical system error")
        else:
            error = RuntimeError(f"Generic error: {error_type}")
        
        return self.error_collector.collect_error(error, context)
    
    async def cleanup(self):
        """Clean up resources."""
        if self.redis_service:
            await self.redis_service.shutdown()
        if self.db_manager:
            await self.db_manager.shutdown()

@pytest.fixture
async def error_propagation_manager():
    """Create error propagation manager for testing."""
    manager = AgentErrorPropagationManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_error_collection_and_classification(error_propagation_manager):
    """Test error collection and automatic classification."""
    manager = error_propagation_manager
    
    # Test different error types
    test_cases = [
        ("timeout", {"agent_id": "test_agent", "agent_type": "processor"}),
        ("validation", {"agent_id": "test_agent", "agent_type": "validator"}),
        ("network", {"agent_id": "test_agent", "agent_type": "connector"})
    ]
    
    for error_type, context in test_cases:
        error_event = manager.simulate_agent_error(error_type, context)
        
        assert error_event.agent_id == context["agent_id"]
        assert error_event.agent_type == context["agent_type"]
        assert error_event.error_id is not None
        assert error_event.timestamp is not None
        
        # Verify classification
        if error_type == "timeout":
            assert error_event.category == ErrorCategory.TIMEOUT
        elif error_type == "validation":
            assert error_event.category == ErrorCategory.VALIDATION
        elif error_type == "network":
            assert error_event.category == ErrorCategory.NETWORK

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_error_enrichment_pipeline(error_propagation_manager):
    """Test error enrichment with additional context."""
    manager = error_propagation_manager
    
    # Simulate error
    context = {"agent_id": "enrichment_test", "agent_type": "test_agent"}
    error_event = manager.simulate_agent_error("validation", context)
    
    # Enrich error
    enriched_error = await manager.error_enricher.enrich_error(error_event)
    
    assert "system_time" in enriched_error.context
    assert "process_id" in enriched_error.context
    assert "agent_history" in enriched_error.context
    assert enriched_error.error_id == error_event.error_id

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_error_propagation_routing(error_propagation_manager):
    """Test error propagation routing logic."""
    manager = error_propagation_manager
    
    # Track routed errors
    routed_errors = []
    
    def test_handler(error_event: ErrorEvent):
        routed_errors.append(error_event.error_id)
    
    # Add test route for validation errors
    manager.error_propagator.add_route(
        lambda e: e.category == ErrorCategory.VALIDATION,
        test_handler
    )
    
    # Simulate validation error
    context = {"agent_id": "routing_test", "agent_type": "test_agent"}
    validation_error = manager.simulate_agent_error("validation", context)
    
    # Allow async processing
    await asyncio.sleep(0.1)
    
    # Verify routing
    assert validation_error.error_id in routed_errors

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_critical_error_reporting(error_propagation_manager):
    """Test immediate reporting of critical errors."""
    manager = error_propagation_manager
    
    # Simulate critical error
    context = {"agent_id": "critical_test", "agent_type": "critical_agent"}
    critical_error = manager.simulate_agent_error("critical", context)
    
    # Allow async processing
    await asyncio.sleep(0.1)
    
    # Verify critical error was reported
    critical_reports = [r for r in manager.error_reporter.reports_sent 
                       if r["type"] == "critical_error"]
    
    assert len(critical_reports) > 0
    assert critical_reports[0]["error_id"] == critical_error.error_id

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_error_aggregation_rules(error_propagation_manager):
    """Test error aggregation and bucketing."""
    manager = error_propagation_manager
    
    # Simulate multiple similar errors
    context = {"agent_id": "aggregation_test", "agent_type": "test_agent"}
    
    for i in range(5):
        manager.simulate_agent_error("validation", context)
        await asyncio.sleep(0.01)  # Small delay to ensure different timestamps
    
    # Allow processing
    await asyncio.sleep(0.1)
    
    # Check aggregation
    summary = manager.error_aggregator.get_error_summary(3600)
    
    assert summary["total_errors"] >= 5
    assert summary["unique_error_types"] >= 1
    assert "medium" in summary["severity_breakdown"]  # Validation errors are medium severity

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_error_severity_classification(error_propagation_manager):
    """Test error severity classification logic."""
    manager = error_propagation_manager
    
    test_cases = [
        ("timeout", ErrorSeverity.HIGH),
        ("validation", ErrorSeverity.MEDIUM),
        ("network", ErrorSeverity.HIGH),
        ("critical", ErrorSeverity.CRITICAL)
    ]
    
    context = {"agent_id": "severity_test", "agent_type": "test_agent"}
    
    for error_type, expected_severity in test_cases:
        error_event = manager.simulate_agent_error(error_type, context)
        assert error_event.severity == expected_severity

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_concurrent_error_processing(error_propagation_manager):
    """Test concurrent error processing and pipeline integrity."""
    manager = error_propagation_manager
    
    # Simulate many concurrent errors
    error_tasks = []
    contexts = [
        {"agent_id": f"concurrent_{i}", "agent_type": "test_agent"}
        for i in range(20)
    ]
    
    for i, context in enumerate(contexts):
        error_type = ["timeout", "validation", "network"][i % 3]
        error_event = manager.simulate_agent_error(error_type, context)
        error_tasks.append(error_event)
    
    # Allow processing
    await asyncio.sleep(0.5)
    
    # Verify all errors were collected
    assert len(manager.error_collector.collected_errors) >= 20
    
    # Verify aggregation
    summary = manager.error_aggregator.get_error_summary(3600)
    assert summary["total_errors"] >= 20

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_error_context_preservation(error_propagation_manager):
    """Test that error context is preserved through the pipeline."""
    manager = error_propagation_manager
    
    # Create rich context
    context = {
        "agent_id": "context_test",
        "agent_type": "test_agent",
        "user_id": "user_123",
        "session_id": "session_456",
        "request_id": "req_789",
        "custom_data": {"key": "value"}
    }
    
    error_event = manager.simulate_agent_error("validation", context)
    
    # Verify context preservation
    assert error_event.context["user_id"] == "user_123"
    assert error_event.context["session_id"] == "session_456"
    assert error_event.context["request_id"] == "req_789"
    assert error_event.context["custom_data"]["key"] == "value"

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_error_pipeline_resilience(error_propagation_manager):
    """Test error pipeline resilience to processing failures."""
    manager = error_propagation_manager
    
    # Add failing handler
    def failing_handler(error_event: ErrorEvent):
        raise Exception("Handler failure")
    
    manager.error_propagator.add_global_handler(failing_handler)
    
    # Simulate error
    context = {"agent_id": "resilience_test", "agent_type": "test_agent"}
    error_event = manager.simulate_agent_error("validation", context)
    
    # Allow processing
    await asyncio.sleep(0.1)
    
    # Pipeline should continue working despite handler failure
    assert len(manager.error_collector.collected_errors) >= 1
    
    # Aggregation should still work
    summary = manager.error_aggregator.get_error_summary(3600)
    assert summary["total_errors"] >= 1

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_error_propagation_performance(error_propagation_manager):
    """Benchmark error propagation performance."""
    manager = error_propagation_manager
    
    # Benchmark error processing
    start_time = time.time()
    
    contexts = [
        {"agent_id": f"perf_{i}", "agent_type": "test_agent"}
        for i in range(100)
    ]
    
    for context in contexts:
        manager.simulate_agent_error("validation", context)
    
    processing_time = time.time() - start_time
    
    # Allow async processing to complete
    await asyncio.sleep(1.0)
    
    # Performance assertions
    assert processing_time < 2.0  # 100 errors collected in under 2 seconds
    assert len(manager.error_collector.collected_errors) >= 100
    
    # Check aggregation performance
    summary = manager.error_aggregator.get_error_summary(3600)
    assert summary["total_errors"] >= 100
    
    avg_processing_time = processing_time / 100
    assert avg_processing_time < 0.02  # Under 20ms per error
    
    logger.info(f"Performance: {avg_processing_time*1000:.1f}ms per error")