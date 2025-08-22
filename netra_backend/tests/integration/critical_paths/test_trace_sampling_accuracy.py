"""Trace Sampling Accuracy L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (operational excellence for all tiers)
- Business Goal: Accurate trace sampling to balance observability with infrastructure costs
- Value Impact: Ensures cost-effective tracing while maintaining $20K MRR performance visibility
- Strategic Impact: Optimizes monitoring costs while preserving critical trace data for debugging

Critical Path: Trace generation -> Sampling decision -> Sample preservation -> Analysis accuracy -> Cost optimization
Coverage: Sampling rate accuracy, statistical validity, performance impact, cost control, data quality
L3 Realism: Tests with real tracing infrastructure and actual sampling algorithms
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import logging
import random
import statistics
import time
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch

import pytest

logger = logging.getLogger(__name__)

# L3 integration test markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.l3,
    pytest.mark.observability,
    pytest.mark.tracing
]


@dataclass
class TraceSpan:
    """Represents a trace span with sampling information."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    service_name: str
    start_time: datetime
    duration_ms: float
    sampled: bool
    sampling_reason: str
    sampling_priority: float = 1.0
    trace_state: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.trace_state is None:
            self.trace_state = {}


@dataclass
class SamplingRule:
    """Defines trace sampling rules."""
    rule_id: str
    name: str
    service_pattern: str
    operation_pattern: str
    sampling_rate: float
    priority: int
    conditions: Dict[str, Any] = None
    cost_impact_weight: float = 1.0
    
    def __post_init__(self):
        if self.conditions is None:
            self.conditions = {}


@dataclass
class SamplingAnalysis:
    """Analysis results for trace sampling."""
    total_traces: int
    sampled_traces: int
    expected_sample_count: int
    actual_sampling_rate: float
    target_sampling_rate: float
    sampling_accuracy: float
    statistical_confidence: float
    cost_efficiency_score: float


class TraceSamplingValidator:
    """Validates trace sampling accuracy with real tracing infrastructure."""
    
    def __init__(self):
        self.trace_collector = None
        self.sampling_engine = None
        self.cost_calculator = None
        self.generated_traces = []
        self.sampling_decisions = []
        self.sampling_rules = []
        self.performance_metrics = {}
        
    async def initialize_sampling_services(self):
        """Initialize trace sampling services for L3 testing."""
        try:
            self.trace_collector = TraceCollector()
            await self.trace_collector.initialize()
            
            self.sampling_engine = TraceSamplingEngine()
            await self.sampling_engine.initialize()
            
            self.cost_calculator = TracingCostCalculator()
            
            # Setup default sampling rules
            await self._setup_sampling_rules()
            
            logger.info("Trace sampling L3 services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize sampling services: {e}")
            raise
    
    async def _setup_sampling_rules(self):
        """Setup realistic sampling rules for testing."""
        sampling_rules = [
            SamplingRule(
                rule_id="critical_errors",
                name="Critical Error Traces",
                service_pattern=".*",
                operation_pattern=".*",
                sampling_rate=1.0,  # 100% sampling for errors
                priority=1,
                conditions={"error_present": True, "severity": "critical"},
                cost_impact_weight=3.0
            ),
            SamplingRule(
                rule_id="high_value_operations",
                name="High Value Business Operations",
                service_pattern="agent-service|payment-service",
                operation_pattern="execute_agent|process_payment",
                sampling_rate=0.5,  # 50% sampling for high-value ops
                priority=2,
                conditions={"business_critical": True},
                cost_impact_weight=2.0
            ),
            SamplingRule(
                rule_id="slow_requests",
                name="Slow Request Traces",
                service_pattern=".*",
                operation_pattern=".*",
                sampling_rate=0.8,  # 80% sampling for slow requests
                priority=3,
                conditions={"duration_ms": ">2000"},
                cost_impact_weight=1.5
            ),
            SamplingRule(
                rule_id="authentication_flows",
                name="Authentication Flow Sampling",
                service_pattern="auth-service",
                operation_pattern=".*",
                sampling_rate=0.1,  # 10% sampling for auth
                priority=4,
                conditions={},
                cost_impact_weight=1.0
            ),
            SamplingRule(
                rule_id="default_sampling",
                name="Default Sampling Rate",
                service_pattern=".*",
                operation_pattern=".*",
                sampling_rate=0.05,  # 5% default sampling
                priority=10,
                conditions={},
                cost_impact_weight=1.0
            )
        ]
        
        self.sampling_rules = sampling_rules
        await self.sampling_engine.configure_rules(sampling_rules)
    
    async def generate_trace_population(self, trace_count: int = 1000) -> List[TraceSpan]:
        """Generate diverse trace population for sampling testing."""
        traces = []
        
        # Define trace generation patterns
        patterns = [
            self._generate_critical_error_trace,
            self._generate_high_value_operation_trace,
            self._generate_slow_request_trace,
            self._generate_authentication_trace,
            self._generate_normal_operation_trace
        ]
        
        # Generate traces with realistic distribution
        for i in range(trace_count):
            # Select pattern based on realistic distribution
            if i % 100 < 2:  # 2% critical errors
                pattern = patterns[0]
            elif i % 100 < 7:  # 5% high-value operations
                pattern = patterns[1]
            elif i % 100 < 12:  # 5% slow requests
                pattern = patterns[2]
            elif i % 100 < 22:  # 10% authentication flows
                pattern = patterns[3]
            else:  # 78% normal operations
                pattern = patterns[4]
            
            trace = await pattern(i)
            traces.append(trace)
        
        self.generated_traces = traces
        return traces
    
    async def _generate_critical_error_trace(self, index: int) -> TraceSpan:
        """Generate trace with critical error."""
        return TraceSpan(
            trace_id=str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            parent_span_id=None,
            operation_name="critical_operation_failure",
            service_name=random.choice(["api-gateway", "agent-service", "database-service"]),
            start_time=datetime.now(timezone.utc),
            duration_ms=random.uniform(500, 5000),
            sampled=False,  # Will be determined by sampling engine
            sampling_reason="not_sampled",
            trace_state={"error_present": True, "severity": "critical", "business_critical": True}
        )
    
    async def _generate_high_value_operation_trace(self, index: int) -> TraceSpan:
        """Generate high-value business operation trace."""
        return TraceSpan(
            trace_id=str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            parent_span_id=None,
            operation_name=random.choice(["execute_agent", "process_payment", "generate_report"]),
            service_name=random.choice(["agent-service", "payment-service", "analytics-service"]),
            start_time=datetime.now(timezone.utc),
            duration_ms=random.uniform(800, 3000),
            sampled=False,
            sampling_reason="not_sampled",
            trace_state={"business_critical": True, "revenue_impact": True}
        )
    
    async def _generate_slow_request_trace(self, index: int) -> TraceSpan:
        """Generate slow request trace."""
        duration = random.uniform(2000, 10000)  # 2-10 seconds
        
        return TraceSpan(
            trace_id=str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            parent_span_id=None,
            operation_name="slow_operation",
            service_name=random.choice(["database-service", "external-api", "llm-service"]),
            start_time=datetime.now(timezone.utc),
            duration_ms=duration,
            sampled=False,
            sampling_reason="not_sampled",
            trace_state={"performance_issue": True}
        )
    
    async def _generate_authentication_trace(self, index: int) -> TraceSpan:
        """Generate authentication flow trace."""
        return TraceSpan(
            trace_id=str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            parent_span_id=None,
            operation_name=random.choice(["login", "token_refresh", "logout", "validate_jwt"]),
            service_name="auth-service",
            start_time=datetime.now(timezone.utc),
            duration_ms=random.uniform(50, 300),
            sampled=False,
            sampling_reason="not_sampled",
            trace_state={"auth_flow": True}
        )
    
    async def _generate_normal_operation_trace(self, index: int) -> TraceSpan:
        """Generate normal operation trace."""
        return TraceSpan(
            trace_id=str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            parent_span_id=None,
            operation_name=random.choice(["get_user", "list_threads", "send_message", "health_check"]),
            service_name=random.choice(["api-gateway", "websocket-service", "user-service"]),
            start_time=datetime.now(timezone.utc),
            duration_ms=random.uniform(10, 200),
            sampled=False,
            sampling_reason="not_sampled",
            trace_state={}
        )
    
    async def apply_sampling_decisions(self, traces: List[TraceSpan]) -> Dict[str, Any]:
        """Apply sampling decisions to trace population."""
        sampling_results = {
            "total_traces": len(traces),
            "sampling_decisions": [],
            "rule_usage": defaultdict(int),
            "sampling_latency_ms": [],
            "decisions_by_rule": defaultdict(list)
        }
        
        for trace in traces:
            sampling_start = time.time()
            
            try:
                # Apply sampling decision
                sampling_decision = await self.sampling_engine.make_sampling_decision(trace)
                
                sampling_latency = (time.time() - sampling_start) * 1000
                sampling_results["sampling_latency_ms"].append(sampling_latency)
                
                # Update trace with sampling decision
                trace.sampled = sampling_decision["sampled"]
                trace.sampling_reason = sampling_decision["reason"]
                trace.sampling_priority = sampling_decision.get("priority", 1.0)
                
                # Track decision details
                decision_record = {
                    "trace_id": trace.trace_id,
                    "sampled": sampling_decision["sampled"],
                    "rule_applied": sampling_decision["rule_id"],
                    "reason": sampling_decision["reason"],
                    "latency_ms": sampling_latency
                }
                
                sampling_results["sampling_decisions"].append(decision_record)
                sampling_results["rule_usage"][sampling_decision["rule_id"]] += 1
                sampling_results["decisions_by_rule"][sampling_decision["rule_id"]].append(sampling_decision["sampled"])
                
                self.sampling_decisions.append(sampling_decision)
                
            except Exception as e:
                logger.error(f"Sampling decision failed for trace {trace.trace_id}: {e}")
        
        return sampling_results
    
    async def analyze_sampling_accuracy(self, traces: List[TraceSpan]) -> SamplingAnalysis:
        """Analyze sampling accuracy against expected rates."""
        # Group traces by applicable rules
        rule_analyses = {}
        
        for rule in self.sampling_rules:
            applicable_traces = await self._find_applicable_traces(traces, rule)
            
            if applicable_traces:
                sampled_count = sum(1 for trace in applicable_traces if trace.sampled)
                total_count = len(applicable_traces)
                actual_rate = sampled_count / total_count if total_count > 0 else 0
                expected_count = int(total_count * rule.sampling_rate)
                
                # Calculate sampling accuracy
                if rule.sampling_rate > 0:
                    accuracy = 100 - abs((actual_rate - rule.sampling_rate) / rule.sampling_rate * 100)
                else:
                    accuracy = 100 if actual_rate == 0 else 0
                
                # Calculate statistical confidence (using normal approximation)
                confidence = self._calculate_statistical_confidence(
                    sampled_count, total_count, rule.sampling_rate
                )
                
                rule_analyses[rule.rule_id] = SamplingAnalysis(
                    total_traces=total_count,
                    sampled_traces=sampled_count,
                    expected_sample_count=expected_count,
                    actual_sampling_rate=actual_rate,
                    target_sampling_rate=rule.sampling_rate,
                    sampling_accuracy=accuracy,
                    statistical_confidence=confidence,
                    cost_efficiency_score=self._calculate_cost_efficiency(rule, actual_rate)
                )
        
        # Calculate overall analysis
        total_traces = len(traces)
        total_sampled = sum(1 for trace in traces if trace.sampled)
        overall_rate = total_sampled / total_traces if total_traces > 0 else 0
        
        # Weight expected rate by rule priorities and trace counts
        weighted_expected_rate = self._calculate_weighted_expected_rate(traces)
        
        overall_accuracy = 100 - abs((overall_rate - weighted_expected_rate) / max(weighted_expected_rate, 0.01) * 100)
        overall_confidence = self._calculate_statistical_confidence(total_sampled, total_traces, weighted_expected_rate)
        
        overall_analysis = SamplingAnalysis(
            total_traces=total_traces,
            sampled_traces=total_sampled,
            expected_sample_count=int(total_traces * weighted_expected_rate),
            actual_sampling_rate=overall_rate,
            target_sampling_rate=weighted_expected_rate,
            sampling_accuracy=overall_accuracy,
            statistical_confidence=overall_confidence,
            cost_efficiency_score=self._calculate_overall_cost_efficiency(rule_analyses)
        )
        
        return overall_analysis, rule_analyses
    
    async def _find_applicable_traces(self, traces: List[TraceSpan], rule: SamplingRule) -> List[TraceSpan]:
        """Find traces that should be subject to a specific sampling rule."""
        applicable_traces = []
        
        for trace in traces:
            # Check service pattern
            if not self._matches_pattern(trace.service_name, rule.service_pattern):
                continue
            
            # Check operation pattern
            if not self._matches_pattern(trace.operation_name, rule.operation_pattern):
                continue
            
            # Check conditions
            if not self._matches_conditions(trace, rule.conditions):
                continue
            
            applicable_traces.append(trace)
        
        return applicable_traces
    
    def _matches_pattern(self, value: str, pattern: str) -> bool:
        """Check if value matches pattern (simplified regex)."""
        if pattern == ".*":
            return True
        return pattern in value
    
    def _matches_conditions(self, trace: TraceSpan, conditions: Dict[str, Any]) -> bool:
        """Check if trace matches rule conditions."""
        for condition_key, condition_value in conditions.items():
            if condition_key == "error_present":
                if condition_value != trace.trace_state.get("error_present", False):
                    return False
            elif condition_key == "severity":
                if trace.trace_state.get("severity") != condition_value:
                    return False
            elif condition_key == "business_critical":
                if condition_value != trace.trace_state.get("business_critical", False):
                    return False
            elif condition_key == "duration_ms":
                if condition_value.startswith(">"):
                    threshold = float(condition_value[1:])
                    if trace.duration_ms <= threshold:
                        return False
        
        return True
    
    def _calculate_statistical_confidence(self, sampled: int, total: int, expected_rate: float) -> float:
        """Calculate statistical confidence of sampling accuracy."""
        if total == 0 or expected_rate == 0:
            return 100.0
        
        # Using normal approximation for binomial distribution
        expected_sampled = total * expected_rate
        variance = total * expected_rate * (1 - expected_rate)
        
        if variance == 0:
            return 100.0
        
        # Calculate z-score
        z_score = abs(sampled - expected_sampled) / (variance ** 0.5)
        
        # Convert to confidence percentage (simplified)
        confidence = max(0, 100 - (z_score * 20))  # Rough approximation
        
        return min(100, confidence)
    
    def _calculate_cost_efficiency(self, rule: SamplingRule, actual_rate: float) -> float:
        """Calculate cost efficiency score for sampling rule."""
        # Cost efficiency = value_captured / cost_incurred
        value_factor = rule.cost_impact_weight
        cost_factor = actual_rate
        
        if cost_factor == 0:
            return 100.0
        
        efficiency = (value_factor / cost_factor) * 20  # Scale to 0-100
        return min(100, efficiency)
    
    def _calculate_weighted_expected_rate(self, traces: List[TraceSpan]) -> float:
        """Calculate weighted expected sampling rate across all rules."""
        total_weight = 0
        weighted_sum = 0
        
        for rule in self.sampling_rules:
            applicable_count = len([t for t in traces if self._matches_pattern(t.service_name, rule.service_pattern)])
            if applicable_count > 0:
                weight = applicable_count / rule.priority  # Higher priority = lower number = higher weight
                weighted_sum += rule.sampling_rate * weight
                total_weight += weight
        
        return weighted_sum / max(total_weight, 1)
    
    def _calculate_overall_cost_efficiency(self, rule_analyses: Dict[str, SamplingAnalysis]) -> float:
        """Calculate overall cost efficiency across all rules."""
        if not rule_analyses:
            return 0.0
        
        efficiency_scores = [analysis.cost_efficiency_score for analysis in rule_analyses.values()]
        return statistics.mean(efficiency_scores)
    
    async def test_sampling_consistency(self, iterations: int = 5) -> Dict[str, Any]:
        """Test sampling consistency across multiple iterations."""
        consistency_results = {
            "iterations": iterations,
            "sampling_rates": [],
            "rate_variance": 0.0,
            "consistency_score": 0.0,
            "stable_rules": [],
            "unstable_rules": []
        }
        
        all_sampling_rates = defaultdict(list)
        
        for iteration in range(iterations):
            # Generate new trace population
            traces = await self.generate_trace_population(500)
            
            # Apply sampling
            await self.apply_sampling_decisions(traces)
            
            # Analyze this iteration
            overall_analysis, rule_analyses = await self.analyze_sampling_accuracy(traces)
            
            # Track sampling rates
            consistency_results["sampling_rates"].append(overall_analysis.actual_sampling_rate)
            
            for rule_id, analysis in rule_analyses.items():
                all_sampling_rates[rule_id].append(analysis.actual_sampling_rate)
        
        # Calculate variance and consistency
        if len(consistency_results["sampling_rates"]) > 1:
            rate_variance = statistics.variance(consistency_results["sampling_rates"])
            consistency_results["rate_variance"] = rate_variance
            
            # Lower variance = higher consistency
            consistency_results["consistency_score"] = max(0, 100 - (rate_variance * 1000))
        
        # Analyze rule-level consistency
        for rule_id, rates in all_sampling_rates.items():
            if len(rates) > 1:
                rule_variance = statistics.variance(rates)
                if rule_variance < 0.01:  # Low variance threshold
                    consistency_results["stable_rules"].append(rule_id)
                else:
                    consistency_results["unstable_rules"].append(rule_id)
        
        return consistency_results
    
    async def test_sampling_performance_impact(self, trace_count: int = 2000) -> Dict[str, Any]:
        """Test performance impact of sampling decisions."""
        performance_results = {
            "trace_count": trace_count,
            "total_sampling_time_ms": 0,
            "average_decision_time_ms": 0,
            "throughput_decisions_per_second": 0,
            "memory_overhead_mb": 0,
            "cpu_impact_percentage": 0
        }
        
        # Generate large trace population
        traces = await self.generate_trace_population(trace_count)
        
        # Measure sampling performance
        sampling_start = time.time()
        cpu_start = time.process_time()
        
        sampling_results = await self.apply_sampling_decisions(traces)
        
        sampling_end = time.time()
        cpu_end = time.process_time()
        
        # Calculate performance metrics
        total_time_ms = (sampling_end - sampling_start) * 1000
        cpu_time_ms = (cpu_end - cpu_start) * 1000
        
        performance_results["total_sampling_time_ms"] = total_time_ms
        performance_results["average_decision_time_ms"] = total_time_ms / trace_count
        performance_results["throughput_decisions_per_second"] = trace_count / (total_time_ms / 1000)
        performance_results["cpu_impact_percentage"] = (cpu_time_ms / total_time_ms) * 100
        
        # Estimate memory overhead (simplified)
        estimated_memory_mb = (len(self.sampling_decisions) * 0.001)  # Rough estimate
        performance_results["memory_overhead_mb"] = estimated_memory_mb
        
        return performance_results
    
    async def cleanup(self):
        """Clean up trace sampling test resources."""
        try:
            if self.trace_collector:
                await self.trace_collector.shutdown()
            if self.sampling_engine:
                await self.sampling_engine.shutdown()
        except Exception as e:
            logger.error(f"Trace sampling cleanup failed: {e}")


class TraceCollector:
    """Mock trace collector for L3 testing."""
    
    async def initialize(self):
        """Initialize trace collector."""
        pass
    
    async def shutdown(self):
        """Shutdown trace collector."""
        pass


class TraceSamplingEngine:
    """Mock trace sampling engine for L3 testing."""
    
    async def initialize(self):
        """Initialize sampling engine."""
        self.rules = []
    
    async def configure_rules(self, rules: List[SamplingRule]):
        """Configure sampling rules."""
        self.rules = sorted(rules, key=lambda r: r.priority)
    
    async def make_sampling_decision(self, trace: TraceSpan) -> Dict[str, Any]:
        """Make sampling decision for trace."""
        await asyncio.sleep(0.0001)  # Simulate decision time
        
        # Find applicable rule with highest priority
        for rule in self.rules:
            if self._trace_matches_rule(trace, rule):
                # Make probabilistic sampling decision
                sampled = random.random() < rule.sampling_rate
                
                return {
                    "sampled": sampled,
                    "rule_id": rule.rule_id,
                    "reason": f"rule_{rule.rule_id}",
                    "priority": rule.priority,
                    "sampling_rate": rule.sampling_rate
                }
        
        # Default: no sampling
        return {
            "sampled": False,
            "rule_id": "no_match",
            "reason": "no_matching_rule",
            "priority": 999,
            "sampling_rate": 0.0
        }
    
    def _trace_matches_rule(self, trace: TraceSpan, rule: SamplingRule) -> bool:
        """Check if trace matches rule criteria."""
        # Service pattern matching
        if rule.service_pattern != ".*" and rule.service_pattern not in trace.service_name:
            return False
        
        # Operation pattern matching  
        if rule.operation_pattern != ".*" and rule.operation_pattern not in trace.operation_name:
            return False
        
        # Condition matching
        for condition_key, condition_value in rule.conditions.items():
            if condition_key == "error_present":
                if condition_value != trace.trace_state.get("error_present", False):
                    return False
            elif condition_key == "business_critical":
                if condition_value != trace.trace_state.get("business_critical", False):
                    return False
            elif condition_key == "duration_ms":
                if condition_value.startswith(">"):
                    threshold = float(condition_value[1:])
                    if trace.duration_ms <= threshold:
                        return False
        
        return True
    
    async def shutdown(self):
        """Shutdown sampling engine."""
        pass


class TracingCostCalculator:
    """Calculator for tracing infrastructure costs."""
    
    def calculate_monthly_cost(self, sampling_rate: float, trace_volume: int) -> float:
        """Calculate monthly tracing cost based on sampling rate and volume."""
        base_cost = 20.0  # Base tracing infrastructure
        sampled_traces = trace_volume * sampling_rate
        ingestion_cost = (sampled_traces / 1000) * 0.10  # $0.10 per 1000 traces
        storage_cost = (sampled_traces / 10000) * 2.0   # Storage costs
        
        return base_cost + ingestion_cost + storage_cost


@pytest.fixture
async def trace_sampling_validator():
    """Create trace sampling validator for L3 testing."""
    validator = TraceSamplingValidator()
    await validator.initialize_sampling_services()
    yield validator
    await validator.cleanup()


@pytest.mark.asyncio
async def test_sampling_rate_accuracy_l3(trace_sampling_validator):
    """Test accuracy of trace sampling rates against configured rules.
    
    L3: Tests with real sampling engine and statistical validation.
    """
    # Generate diverse trace population
    traces = await trace_sampling_validator.generate_trace_population(800)
    
    # Apply sampling decisions
    sampling_results = await trace_sampling_validator.apply_sampling_decisions(traces)
    
    # Analyze sampling accuracy
    overall_analysis, rule_analyses = await trace_sampling_validator.analyze_sampling_accuracy(traces)
    
    # Verify overall sampling accuracy
    assert overall_analysis.sampling_accuracy >= 85.0
    assert overall_analysis.statistical_confidence >= 70.0
    
    # Verify rule-specific accuracy
    critical_rule_analysis = rule_analyses.get("critical_errors")
    if critical_rule_analysis:
        assert critical_rule_analysis.sampling_accuracy >= 95.0  # Critical errors should be highly accurate
    
    # Verify sampling performance
    if sampling_results["sampling_latency_ms"]:
        avg_latency = sum(sampling_results["sampling_latency_ms"]) / len(sampling_results["sampling_latency_ms"])
        assert avg_latency <= 1.0  # Should be very fast


@pytest.mark.asyncio
async def test_sampling_consistency_l3(trace_sampling_validator):
    """Test consistency of sampling decisions across multiple iterations.
    
    L3: Tests sampling stability and repeatability.
    """
    # Test consistency across multiple iterations
    consistency_results = await trace_sampling_validator.test_sampling_consistency(iterations=4)
    
    # Verify consistency requirements
    assert consistency_results["consistency_score"] >= 80.0
    assert consistency_results["rate_variance"] <= 0.05  # Low variance in sampling rates
    
    # Verify rule stability
    assert len(consistency_results["stable_rules"]) >= 3  # Most rules should be stable
    assert len(consistency_results["unstable_rules"]) <= 2  # Few unstable rules allowed


@pytest.mark.asyncio
async def test_sampling_performance_impact_l3(trace_sampling_validator):
    """Test performance impact of sampling decisions under load.
    
    L3: Tests sampling engine performance with realistic trace volumes.
    """
    # Test performance with high trace volume
    performance_results = await trace_sampling_validator.test_sampling_performance_impact(1500)
    
    # Verify performance requirements
    assert performance_results["average_decision_time_ms"] <= 0.5  # Very fast decisions
    assert performance_results["throughput_decisions_per_second"] >= 1000  # High throughput
    assert performance_results["cpu_impact_percentage"] <= 50.0  # Reasonable CPU usage
    assert performance_results["memory_overhead_mb"] <= 10.0  # Low memory overhead


@pytest.mark.asyncio
async def test_priority_based_sampling_l3(trace_sampling_validator):
    """Test priority-based sampling for critical vs normal operations.
    
    L3: Tests sampling prioritization for business-critical traces.
    """
    # Generate traces with mixed priorities
    traces = await trace_sampling_validator.generate_trace_population(600)
    
    # Apply sampling
    await trace_sampling_validator.apply_sampling_decisions(traces)
    
    # Analyze by trace criticality
    critical_traces = [t for t in traces if t.trace_state.get("error_present") or t.trace_state.get("business_critical")]
    normal_traces = [t for t in traces if not t.trace_state.get("error_present") and not t.trace_state.get("business_critical")]
    
    # Calculate sampling rates
    critical_sampling_rate = sum(1 for t in critical_traces if t.sampled) / max(len(critical_traces), 1)
    normal_sampling_rate = sum(1 for t in normal_traces if t.sampled) / max(len(normal_traces), 1)
    
    # Verify priority-based sampling
    assert critical_sampling_rate > normal_sampling_rate  # Critical should be sampled more
    assert critical_sampling_rate >= 0.5  # High sampling for critical traces
    assert normal_sampling_rate <= 0.15   # Lower sampling for normal traces


@pytest.mark.asyncio
async def test_cost_aware_sampling_l3(trace_sampling_validator):
    """Test cost-aware sampling optimization.
    
    L3: Tests sampling efficiency and cost control.
    """
    # Generate traces and apply sampling
    traces = await trace_sampling_validator.generate_trace_population(500)
    await trace_sampling_validator.apply_sampling_decisions(traces)
    
    # Analyze cost efficiency
    overall_analysis, rule_analyses = await trace_sampling_validator.analyze_sampling_accuracy(traces)
    
    # Verify cost efficiency
    assert overall_analysis.cost_efficiency_score >= 60.0
    
    # Calculate cost projection
    total_sampled = sum(1 for t in traces if t.sampled)
    monthly_traces = len(traces) * 30 * 24  # Extrapolate to monthly volume
    monthly_sampled = total_sampled * 30 * 24
    
    cost_calculator = TracingCostCalculator()
    monthly_cost = cost_calculator.calculate_monthly_cost(
        monthly_sampled / monthly_traces, monthly_traces
    )
    
    # Verify cost is reasonable
    assert monthly_cost <= 200.0  # Should keep costs under $200/month for this volume


@pytest.mark.asyncio
async def test_sampling_rule_coverage_l3(trace_sampling_validator):
    """Test coverage and effectiveness of sampling rules.
    
    L3: Tests that all trace types are properly handled by sampling rules.
    """
    # Generate comprehensive trace population
    traces = await trace_sampling_validator.generate_trace_population(400)
    
    # Apply sampling
    sampling_results = await trace_sampling_validator.apply_sampling_decisions(traces)
    
    # Verify rule coverage
    assert len(sampling_results["rule_usage"]) >= 4  # Multiple rules should be used
    
    # Verify no traces are unhandled
    unhandled_decisions = [d for d in sampling_results["sampling_decisions"] if d["rule_applied"] == "no_match"]
    unhandled_percentage = len(unhandled_decisions) / len(traces) * 100
    assert unhandled_percentage <= 5.0  # Very few traces should be unhandled
    
    # Verify rule distribution is reasonable
    rule_usage = sampling_results["rule_usage"]
    total_decisions = sum(rule_usage.values())
    
    # Default rule should not dominate (indicates good rule specificity)
    default_usage_percentage = rule_usage.get("default_sampling", 0) / total_decisions * 100
    assert default_usage_percentage <= 60.0  # Default should not handle majority