"""Agent Quality Gate L2 Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise (quality assurance and reliability)
- Business Goal: Ensure consistent AI output quality and reliability
- Value Impact: Protects $11K MRR from quality degradation and customer churn
- Strategic Impact: Maintains competitive advantage through superior AI quality

Critical Path: Quality metrics -> Threshold checks -> Gate decisions -> Feedback loops -> Improvement
Coverage: Real quality assessment, automated gates, performance monitoring
"""

import pytest
import asyncio
import time
import json
import logging
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import statistics
import hashlib

# Real components for L2 testing
from netra_backend.app.services.redis_service import RedisService
from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.core.database_connection_manager import DatabaseConnectionManager
from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.core.config import get_settings

logger = logging.getLogger(__name__)


class QualityMetricType(Enum):
    """Types of quality metrics."""
    ACCURACY = "accuracy"
    RELEVANCE = "relevance"
    COHERENCE = "coherence"
    SAFETY = "safety"
    LATENCY = "latency"
    COST_EFFICIENCY = "cost_efficiency"
    USER_SATISFACTION = "user_satisfaction"
    FACTUAL_CORRECTNESS = "factual_correctness"
    HALLUCINATION_RATE = "hallucination_rate"
    COMPLETENESS = "completeness"


class QualityGateStatus(Enum):
    """Quality gate status values."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    PENDING = "pending"
    BYPASSED = "bypassed"


class QualityGateSeverity(Enum):
    """Severity levels for quality gate failures."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class QualityMetric:
    """Represents a quality metric measurement."""
    metric_id: str
    metric_type: QualityMetricType
    value: float
    threshold_min: Optional[float]
    threshold_max: Optional[float]
    weight: float = 1.0
    measured_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_within_threshold(self) -> bool:
        """Check if metric value is within acceptable thresholds."""
        if self.threshold_min is not None and self.value < self.threshold_min:
            return False
        if self.threshold_max is not None and self.value > self.threshold_max:
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "metric_id": self.metric_id,
            "metric_type": self.metric_type.value,
            "value": self.value,
            "threshold_min": self.threshold_min,
            "threshold_max": self.threshold_max,
            "weight": self.weight,
            "measured_at": self.measured_at.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class QualityAssessment:
    """Represents a complete quality assessment."""
    assessment_id: str
    agent_id: str
    request_id: str
    input_text: str
    output_text: str
    metrics: List[QualityMetric]
    overall_score: float
    gate_status: QualityGateStatus
    created_at: datetime = field(default_factory=datetime.now)
    
    def calculate_weighted_score(self) -> float:
        """Calculate weighted quality score."""
        if not self.metrics:
            return 0.0
        
        total_weight = sum(metric.weight for metric in self.metrics)
        if total_weight == 0:
            return 0.0
        
        weighted_sum = sum(metric.value * metric.weight for metric in self.metrics)
        return weighted_sum / total_weight
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "assessment_id": self.assessment_id,
            "agent_id": self.agent_id,
            "request_id": self.request_id,
            "input_text": self.input_text,
            "output_text": self.output_text,
            "metrics": [metric.to_dict() for metric in self.metrics],
            "overall_score": self.overall_score,
            "gate_status": self.gate_status.value,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class QualityGateRule:
    """Defines a quality gate rule."""
    rule_id: str
    name: str
    metric_type: QualityMetricType
    min_threshold: Optional[float]
    max_threshold: Optional[float]
    severity: QualityGateSeverity
    enabled: bool = True
    description: str = ""
    
    def evaluate(self, metric: QualityMetric) -> bool:
        """Evaluate if a metric passes this rule."""
        if not self.enabled or metric.metric_type != self.metric_type:
            return True
        
        if self.min_threshold is not None and metric.value < self.min_threshold:
            return False
        if self.max_threshold is not None and metric.value > self.max_threshold:
            return False
        
        return True


class QualityMetricCalculator:
    """Calculates various quality metrics for AI outputs."""
    
    def __init__(self):
        self.metric_calculators = {
            QualityMetricType.RELEVANCE: self._calculate_relevance,
            QualityMetricType.COHERENCE: self._calculate_coherence,
            QualityMetricType.SAFETY: self._calculate_safety,
            QualityMetricType.FACTUAL_CORRECTNESS: self._calculate_factual_correctness,
            QualityMetricType.HALLUCINATION_RATE: self._calculate_hallucination_rate,
            QualityMetricType.COMPLETENESS: self._calculate_completeness,
            QualityMetricType.USER_SATISFACTION: self._calculate_user_satisfaction
        }
    
    async def calculate_metrics(self, 
                              input_text: str, 
                              output_text: str, 
                              context: Dict[str, Any] = None) -> List[QualityMetric]:
        """Calculate all available quality metrics."""
        metrics = []
        context = context or {}
        
        for metric_type, calculator in self.metric_calculators.items():
            try:
                metric = await calculator(input_text, output_text, context)
                if metric:
                    metrics.append(metric)
            except Exception as e:
                logger.warning(f"Failed to calculate {metric_type.value} metric: {e}")
        
        return metrics
    
    async def _calculate_relevance(self, input_text: str, output_text: str, context: Dict[str, Any]) -> QualityMetric:
        """Calculate relevance score (mock implementation)."""
        await asyncio.sleep(0.01)  # Simulate processing time
        
        # Mock relevance calculation based on keyword overlap
        input_words = set(input_text.lower().split())
        output_words = set(output_text.lower().split())
        
        if len(input_words) == 0:
            relevance_score = 0.0
        else:
            overlap = len(input_words.intersection(output_words))
            relevance_score = min(1.0, overlap / len(input_words) + 0.3)  # Baseline + overlap
        
        return QualityMetric(
            metric_id=f"relevance_{int(time.time() * 1000)}",
            metric_type=QualityMetricType.RELEVANCE,
            value=relevance_score,
            threshold_min=0.6,
            threshold_max=None,
            weight=1.5,
            metadata={"input_words": len(input_words), "output_words": len(output_words)}
        )
    
    async def _calculate_coherence(self, input_text: str, output_text: str, context: Dict[str, Any]) -> QualityMetric:
        """Calculate coherence score (mock implementation)."""
        await asyncio.sleep(0.01)
        
        # Mock coherence calculation based on sentence structure
        sentences = output_text.split('.')
        sentence_lengths = [len(sentence.strip().split()) for sentence in sentences if sentence.strip()]
        
        if not sentence_lengths:
            coherence_score = 0.0
        else:
            # Coherence based on sentence length consistency
            avg_length = statistics.mean(sentence_lengths)
            variance = statistics.variance(sentence_lengths) if len(sentence_lengths) > 1 else 0
            coherence_score = max(0.0, min(1.0, 0.8 - (variance / (avg_length + 1)) * 0.1))
        
        return QualityMetric(
            metric_id=f"coherence_{int(time.time() * 1000)}",
            metric_type=QualityMetricType.COHERENCE,
            value=coherence_score,
            threshold_min=0.7,
            threshold_max=None,
            weight=1.2,
            metadata={"sentence_count": len(sentences), "avg_sentence_length": avg_length if sentence_lengths else 0}
        )
    
    async def _calculate_safety(self, input_text: str, output_text: str, context: Dict[str, Any]) -> QualityMetric:
        """Calculate safety score (mock implementation)."""
        await asyncio.sleep(0.01)
        
        # Mock safety check for harmful content
        harmful_keywords = ["violence", "hate", "illegal", "dangerous", "harmful"]
        output_lower = output_text.lower()
        
        harmful_count = sum(1 for keyword in harmful_keywords if keyword in output_lower)
        safety_score = max(0.0, 1.0 - (harmful_count * 0.3))
        
        return QualityMetric(
            metric_id=f"safety_{int(time.time() * 1000)}",
            metric_type=QualityMetricType.SAFETY,
            value=safety_score,
            threshold_min=0.8,
            threshold_max=None,
            weight=2.0,  # High weight for safety
            metadata={"harmful_keywords_found": harmful_count}
        )
    
    async def _calculate_factual_correctness(self, input_text: str, output_text: str, context: Dict[str, Any]) -> QualityMetric:
        """Calculate factual correctness score (mock implementation)."""
        await asyncio.sleep(0.02)
        
        # Mock factual correctness check
        # Look for uncertain language patterns
        uncertain_patterns = ["i think", "maybe", "possibly", "i'm not sure", "uncertain"]
        output_lower = output_text.lower()
        
        uncertain_count = sum(1 for pattern in uncertain_patterns if pattern in output_lower)
        
        # Higher uncertainty = lower factual confidence
        factual_score = max(0.3, 1.0 - (uncertain_count * 0.15))
        
        return QualityMetric(
            metric_id=f"factual_{int(time.time() * 1000)}",
            metric_type=QualityMetricType.FACTUAL_CORRECTNESS,
            value=factual_score,
            threshold_min=0.7,
            threshold_max=None,
            weight=1.8,
            metadata={"uncertainty_indicators": uncertain_count}
        )
    
    async def _calculate_hallucination_rate(self, input_text: str, output_text: str, context: Dict[str, Any]) -> QualityMetric:
        """Calculate hallucination rate (mock implementation)."""
        await asyncio.sleep(0.02)
        
        # Mock hallucination detection
        # Look for overly specific claims without evidence
        specific_patterns = ["exactly", "precisely", "definitely happened on", "the exact number is"]
        output_lower = output_text.lower()
        
        specific_claims = sum(1 for pattern in specific_patterns if pattern in output_lower)
        output_length = len(output_text.split())
        
        if output_length == 0:
            hallucination_rate = 0.0
        else:
            hallucination_rate = min(1.0, specific_claims / (output_length / 50))  # Normalize by text length
        
        return QualityMetric(
            metric_id=f"hallucination_{int(time.time() * 1000)}",
            metric_type=QualityMetricType.HALLUCINATION_RATE,
            value=hallucination_rate,
            threshold_min=None,
            threshold_max=0.2,  # Max 20% hallucination rate
            weight=1.5,
            metadata={"specific_claims": specific_claims, "output_length": output_length}
        )
    
    async def _calculate_completeness(self, input_text: str, output_text: str, context: Dict[str, Any]) -> QualityMetric:
        """Calculate completeness score (mock implementation)."""
        await asyncio.sleep(0.01)
        
        # Mock completeness check based on response length vs. query complexity
        input_length = len(input_text.split())
        output_length = len(output_text.split())
        
        # More complex queries should have more complete responses
        expected_length = max(20, input_length * 2)  # At least 20 words, preferably 2x input
        
        if output_length == 0:
            completeness_score = 0.0
        else:
            completeness_score = min(1.0, output_length / expected_length)
        
        return QualityMetric(
            metric_id=f"completeness_{int(time.time() * 1000)}",
            metric_type=QualityMetricType.COMPLETENESS,
            value=completeness_score,
            threshold_min=0.6,
            threshold_max=None,
            weight=1.0,
            metadata={"input_length": input_length, "output_length": output_length, "expected_length": expected_length}
        )
    
    async def _calculate_user_satisfaction(self, input_text: str, output_text: str, context: Dict[str, Any]) -> QualityMetric:
        """Calculate user satisfaction score (mock implementation)."""
        await asyncio.sleep(0.01)
        
        # Mock user satisfaction based on response quality indicators
        positive_indicators = ["helpful", "clear", "thank you", "exactly what", "perfect"]
        negative_indicators = ["wrong", "unhelpful", "confused", "error", "doesn't answer"]
        
        output_lower = output_text.lower()
        
        positive_count = sum(1 for indicator in positive_indicators if indicator in output_lower)
        negative_count = sum(1 for indicator in negative_indicators if indicator in output_lower)
        
        # Default satisfaction with adjustments
        satisfaction_score = 0.75 + (positive_count * 0.1) - (negative_count * 0.2)
        satisfaction_score = max(0.0, min(1.0, satisfaction_score))
        
        return QualityMetric(
            metric_id=f"satisfaction_{int(time.time() * 1000)}",
            metric_type=QualityMetricType.USER_SATISFACTION,
            value=satisfaction_score,
            threshold_min=0.6,
            threshold_max=None,
            weight=1.3,
            metadata={"positive_indicators": positive_count, "negative_indicators": negative_count}
        )


class QualityGateEngine:
    """Main quality gate engine that evaluates assessments."""
    
    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service
        self.rules: Dict[str, QualityGateRule] = {}
        self.metric_calculator = QualityMetricCalculator()
        self.assessment_history: List[QualityAssessment] = []
        
    def add_rule(self, rule: QualityGateRule):
        """Add a quality gate rule."""
        self.rules[rule.rule_id] = rule
    
    def remove_rule(self, rule_id: str):
        """Remove a quality gate rule."""
        self.rules.pop(rule_id, None)
    
    async def assess_quality(self, 
                           agent_id: str, 
                           request_id: str, 
                           input_text: str, 
                           output_text: str,
                           context: Dict[str, Any] = None) -> QualityAssessment:
        """Perform complete quality assessment."""
        
        # Calculate metrics
        metrics = await self.metric_calculator.calculate_metrics(input_text, output_text, context)
        
        # Evaluate against rules
        gate_status = await self._evaluate_gate_status(metrics)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(metrics)
        
        # Create assessment
        assessment = QualityAssessment(
            assessment_id=f"qa_{agent_id}_{int(time.time() * 1000)}",
            agent_id=agent_id,
            request_id=request_id,
            input_text=input_text,
            output_text=output_text,
            metrics=metrics,
            overall_score=overall_score,
            gate_status=gate_status
        )
        
        # Store assessment
        await self._store_assessment(assessment)
        
        # Update real-time metrics
        await self._update_realtime_metrics(assessment)
        
        return assessment
    
    async def _evaluate_gate_status(self, metrics: List[QualityMetric]) -> QualityGateStatus:
        """Evaluate gate status based on rules."""
        if not self.rules:
            return QualityGateStatus.PASSED
        
        critical_failures = 0
        high_failures = 0
        warnings = 0
        
        for metric in metrics:
            for rule in self.rules.values():
                if not rule.evaluate(metric):
                    if rule.severity == QualityGateSeverity.CRITICAL:
                        critical_failures += 1
                    elif rule.severity == QualityGateSeverity.HIGH:
                        high_failures += 1
                    elif rule.severity == QualityGateSeverity.MEDIUM:
                        warnings += 1
        
        # Determine overall status
        if critical_failures > 0:
            return QualityGateStatus.FAILED
        elif high_failures > 1:  # Allow 1 high failure
            return QualityGateStatus.FAILED
        elif high_failures > 0 or warnings > 2:  # Allow up to 2 warnings
            return QualityGateStatus.WARNING
        else:
            return QualityGateStatus.PASSED
    
    def _calculate_overall_score(self, metrics: List[QualityMetric]) -> float:
        """Calculate overall quality score."""
        if not metrics:
            return 0.0
        
        total_weight = sum(metric.weight for metric in metrics)
        if total_weight == 0:
            return 0.0
        
        weighted_sum = sum(metric.value * metric.weight for metric in metrics)
        return weighted_sum / total_weight
    
    async def _store_assessment(self, assessment: QualityAssessment):
        """Store assessment in cache and add to history."""
        # Cache in Redis
        cache_key = f"quality_assessment:{assessment.assessment_id}"
        assessment_data = json.dumps(assessment.to_dict())
        
        await self.redis_service.client.setex(cache_key, 3600, assessment_data)  # 1 hour TTL
        
        # Add to in-memory history (keep last 1000)
        self.assessment_history.append(assessment)
        if len(self.assessment_history) > 1000:
            self.assessment_history.pop(0)
    
    async def _update_realtime_metrics(self, assessment: QualityAssessment):
        """Update real-time quality metrics."""
        today = assessment.created_at.date().isoformat()
        
        # Update agent daily metrics
        agent_key = f"quality_daily:{assessment.agent_id}:{today}"
        
        pipe = self.redis_service.client.pipeline()
        pipe.hincrbyfloat(agent_key, "total_score", assessment.overall_score)
        pipe.hincrby(agent_key, "total_assessments", 1)
        
        # Count status occurrences
        pipe.hincrby(agent_key, f"status_{assessment.gate_status.value}", 1)
        
        # Update individual metric averages
        for metric in assessment.metrics:
            pipe.hincrbyfloat(agent_key, f"metric_{metric.metric_type.value}", metric.value)
        
        pipe.expire(agent_key, 86400 * 7)  # 7 days TTL
        await pipe.execute()
    
    async def get_quality_trends(self, agent_id: str, days: int = 7) -> Dict[str, Any]:
        """Get quality trends for an agent."""
        trends = {"daily_scores": [], "metric_trends": {}, "status_distribution": {}}
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).date().isoformat()
            agent_key = f"quality_daily:{agent_id}:{date}"
            
            daily_data = await self.redis_service.client.hgetall(agent_key)
            
            if daily_data:
                total_score = float(daily_data.get("total_score", 0))
                total_assessments = int(daily_data.get("total_assessments", 0))
                avg_score = total_score / total_assessments if total_assessments > 0 else 0
                
                trends["daily_scores"].append({
                    "date": date,
                    "avg_score": avg_score,
                    "assessments": total_assessments
                })
                
                # Aggregate status distribution
                for status in QualityGateStatus:
                    count = int(daily_data.get(f"status_{status.value}", 0))
                    if status.value not in trends["status_distribution"]:
                        trends["status_distribution"][status.value] = 0
                    trends["status_distribution"][status.value] += count
        
        return trends
    
    async def get_recent_assessments(self, agent_id: str, limit: int = 50) -> List[QualityAssessment]:
        """Get recent assessments for an agent."""
        return [
            assessment for assessment in self.assessment_history[-limit:]
            if assessment.agent_id == agent_id
        ]


class QualityGateOrchestrator:
    """Orchestrates quality gates for multiple agents."""
    
    def __init__(self, gate_engine: QualityGateEngine):
        self.gate_engine = gate_engine
        self.agent_configs: Dict[str, Dict[str, Any]] = {}
        
    def configure_agent_quality_rules(self, agent_id: str, rules: List[QualityGateRule]):
        """Configure quality rules for a specific agent."""
        if agent_id not in self.agent_configs:
            self.agent_configs[agent_id] = {"rules": [], "enabled": True}
        
        self.agent_configs[agent_id]["rules"] = rules
        
        # Add rules to engine
        for rule in rules:
            self.gate_engine.add_rule(rule)
    
    async def process_agent_output(self, 
                                 agent_id: str, 
                                 request_id: str, 
                                 input_text: str, 
                                 output_text: str,
                                 bypass_gate: bool = False) -> Dict[str, Any]:
        """Process agent output through quality gates."""
        
        if agent_id not in self.agent_configs:
            # No configuration, allow pass-through
            return {
                "assessment_id": None,
                "gate_status": QualityGateStatus.BYPASSED.value,
                "overall_score": None,
                "allowed": True,
                "message": "No quality configuration found"
            }
        
        config = self.agent_configs[agent_id]
        
        if not config.get("enabled", True) or bypass_gate:
            return {
                "assessment_id": None,
                "gate_status": QualityGateStatus.BYPASSED.value,
                "overall_score": None,
                "allowed": True,
                "message": "Quality gate bypassed"
            }
        
        # Perform quality assessment
        assessment = await self.gate_engine.assess_quality(
            agent_id, request_id, input_text, output_text
        )
        
        # Determine if output is allowed
        allowed = assessment.gate_status in [
            QualityGateStatus.PASSED, 
            QualityGateStatus.WARNING
        ]
        
        return {
            "assessment_id": assessment.assessment_id,
            "gate_status": assessment.gate_status.value,
            "overall_score": assessment.overall_score,
            "allowed": allowed,
            "metrics": [metric.to_dict() for metric in assessment.metrics],
            "message": self._get_status_message(assessment.gate_status)
        }
    
    def _get_status_message(self, status: QualityGateStatus) -> str:
        """Get human-readable status message."""
        messages = {
            QualityGateStatus.PASSED: "Output meets all quality standards",
            QualityGateStatus.WARNING: "Output meets minimum standards with some concerns",
            QualityGateStatus.FAILED: "Output does not meet quality standards",
            QualityGateStatus.PENDING: "Quality assessment in progress",
            QualityGateStatus.BYPASSED: "Quality gate was bypassed"
        }
        return messages.get(status, "Unknown status")


class QualityGateManager:
    """Manages quality gate testing."""
    
    def __init__(self):
        self.redis_service = None
        self.gate_engine = None
        self.orchestrator = None
        
    async def initialize_services(self):
        """Initialize required services."""
        self.redis_service = RedisService()
        await self.redis_service.initialize()
        
        self.gate_engine = QualityGateEngine(self.redis_service)
        self.orchestrator = QualityGateOrchestrator(self.gate_engine)
        
        # Set up default quality rules
        await self.setup_default_rules()
    
    async def setup_default_rules(self):
        """Set up default quality gate rules."""
        default_rules = [
            QualityGateRule(
                rule_id="safety_critical",
                name="Safety Critical",
                metric_type=QualityMetricType.SAFETY,
                min_threshold=0.8,
                max_threshold=None,
                severity=QualityGateSeverity.CRITICAL,
                description="Ensure output is safe and non-harmful"
            ),
            QualityGateRule(
                rule_id="relevance_high",
                name="Relevance High",
                metric_type=QualityMetricType.RELEVANCE,
                min_threshold=0.6,
                max_threshold=None,
                severity=QualityGateSeverity.HIGH,
                description="Ensure output is relevant to input"
            ),
            QualityGateRule(
                rule_id="coherence_medium",
                name="Coherence Medium",
                metric_type=QualityMetricType.COHERENCE,
                min_threshold=0.7,
                max_threshold=None,
                severity=QualityGateSeverity.MEDIUM,
                description="Ensure output is coherent and well-structured"
            ),
            QualityGateRule(
                rule_id="hallucination_limit",
                name="Hallucination Limit",
                metric_type=QualityMetricType.HALLUCINATION_RATE,
                min_threshold=None,
                max_threshold=0.2,
                severity=QualityGateSeverity.HIGH,
                description="Limit hallucination rate to acceptable levels"
            ),
            QualityGateRule(
                rule_id="factual_accuracy",
                name="Factual Accuracy",
                metric_type=QualityMetricType.FACTUAL_CORRECTNESS,
                min_threshold=0.7,
                max_threshold=None,
                severity=QualityGateSeverity.HIGH,
                description="Ensure factual accuracy of statements"
            )
        ]
        
        for rule in default_rules:
            self.gate_engine.add_rule(rule)
    
    async def cleanup(self):
        """Clean up resources."""
        if self.redis_service:
            await self.redis_service.shutdown()


@pytest.fixture
async def quality_manager():
    """Create quality gate test manager."""
    manager = QualityGateManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_quality_metric_calculation(quality_manager):
    """Test individual quality metric calculations."""
    manager = quality_manager
    calculator = manager.gate_engine.metric_calculator
    
    # Test relevance calculation
    input_text = "What is machine learning?"
    output_text = "Machine learning is a subset of artificial intelligence that enables systems to learn from data."
    
    metrics = await calculator.calculate_metrics(input_text, output_text)
    
    assert len(metrics) > 0
    
    # Find specific metrics
    relevance_metric = next((m for m in metrics if m.metric_type == QualityMetricType.RELEVANCE), None)
    safety_metric = next((m for m in metrics if m.metric_type == QualityMetricType.SAFETY), None)
    coherence_metric = next((m for m in metrics if m.metric_type == QualityMetricType.COHERENCE), None)
    
    assert relevance_metric is not None
    assert safety_metric is not None
    assert coherence_metric is not None
    
    # Verify metric values are in expected ranges
    assert 0.0 <= relevance_metric.value <= 1.0
    assert 0.0 <= safety_metric.value <= 1.0
    assert 0.0 <= coherence_metric.value <= 1.0


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_quality_gate_rule_evaluation(quality_manager):
    """Test quality gate rule evaluation."""
    manager = quality_manager
    
    # Create test rule
    test_rule = QualityGateRule(
        rule_id="test_relevance",
        name="Test Relevance Rule",
        metric_type=QualityMetricType.RELEVANCE,
        min_threshold=0.7,
        max_threshold=None,
        severity=QualityGateSeverity.HIGH
    )
    
    # Test passing metric
    passing_metric = QualityMetric(
        metric_id="test_metric_1",
        metric_type=QualityMetricType.RELEVANCE,
        value=0.8,
        threshold_min=0.7,
        threshold_max=None
    )
    
    assert test_rule.evaluate(passing_metric) is True
    
    # Test failing metric
    failing_metric = QualityMetric(
        metric_id="test_metric_2",
        metric_type=QualityMetricType.RELEVANCE,
        value=0.5,
        threshold_min=0.7,
        threshold_max=None
    )
    
    assert test_rule.evaluate(failing_metric) is False


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_complete_quality_assessment(quality_manager):
    """Test complete quality assessment flow."""
    manager = quality_manager
    
    # Perform quality assessment
    assessment = await manager.gate_engine.assess_quality(
        agent_id="test_agent_001",
        request_id="req_001",
        input_text="Explain quantum computing in simple terms",
        output_text="Quantum computing uses quantum mechanics principles to process information in ways that classical computers cannot, potentially solving certain problems much faster."
    )
    
    assert assessment.assessment_id is not None
    assert assessment.agent_id == "test_agent_001"
    assert assessment.request_id == "req_001"
    assert len(assessment.metrics) > 0
    assert 0.0 <= assessment.overall_score <= 1.0
    assert assessment.gate_status in QualityGateStatus


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_quality_gate_pass_scenario(quality_manager):
    """Test scenario where output passes quality gates."""
    manager = quality_manager
    
    # Configure agent with quality rules
    rules = [
        QualityGateRule(
            rule_id="lenient_safety",
            name="Lenient Safety",
            metric_type=QualityMetricType.SAFETY,
            min_threshold=0.5,
            max_threshold=None,
            severity=QualityGateSeverity.MEDIUM
        )
    ]
    
    manager.orchestrator.configure_agent_quality_rules("pass_test_agent", rules)
    
    # Process high-quality output
    result = await manager.orchestrator.process_agent_output(
        agent_id="pass_test_agent",
        request_id="pass_req_001",
        input_text="What is the capital of France?",
        output_text="The capital of France is Paris, which is located in the north-central part of the country."
    )
    
    assert result["allowed"] is True
    assert result["gate_status"] in ["passed", "warning"]
    assert result["overall_score"] is not None


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_quality_gate_fail_scenario(quality_manager):
    """Test scenario where output fails quality gates."""
    manager = quality_manager
    
    # Configure agent with strict rules
    strict_rules = [
        QualityGateRule(
            rule_id="strict_safety",
            name="Strict Safety",
            metric_type=QualityMetricType.SAFETY,
            min_threshold=0.9,
            max_threshold=None,
            severity=QualityGateSeverity.CRITICAL
        ),
        QualityGateRule(
            rule_id="strict_relevance",
            name="Strict Relevance",
            metric_type=QualityMetricType.RELEVANCE,
            min_threshold=0.9,
            max_threshold=None,
            severity=QualityGateSeverity.HIGH
        )
    ]
    
    manager.orchestrator.configure_agent_quality_rules("fail_test_agent", strict_rules)
    
    # Process low-quality output
    result = await manager.orchestrator.process_agent_output(
        agent_id="fail_test_agent",
        request_id="fail_req_001",
        input_text="What is machine learning?",
        output_text="I think it's something about computers and violence maybe dangerous algorithms."
    )
    
    assert result["allowed"] is False
    assert result["gate_status"] == "failed"


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_quality_gate_bypass(quality_manager):
    """Test quality gate bypass functionality."""
    manager = quality_manager
    
    # Configure agent with strict rules
    strict_rules = [
        QualityGateRule(
            rule_id="bypass_test_safety",
            name="Bypass Test Safety",
            metric_type=QualityMetricType.SAFETY,
            min_threshold=0.95,
            max_threshold=None,
            severity=QualityGateSeverity.CRITICAL
        )
    ]
    
    manager.orchestrator.configure_agent_quality_rules("bypass_test_agent", strict_rules)
    
    # Process output with bypass enabled
    result = await manager.orchestrator.process_agent_output(
        agent_id="bypass_test_agent",
        request_id="bypass_req_001",
        input_text="Test input",
        output_text="Test output that would normally fail",
        bypass_gate=True
    )
    
    assert result["allowed"] is True
    assert result["gate_status"] == "bypassed"


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_safety_metric_detection(quality_manager):
    """Test safety metric detection of harmful content."""
    manager = quality_manager
    calculator = manager.gate_engine.metric_calculator
    
    # Test safe content
    safe_metrics = await calculator.calculate_metrics(
        "How do I bake a cake?",
        "To bake a cake, you need flour, eggs, sugar, and butter. Mix the ingredients and bake at 350°F."
    )
    
    safety_metric = next((m for m in safe_metrics if m.metric_type == QualityMetricType.SAFETY), None)
    assert safety_metric is not None
    assert safety_metric.value > 0.8  # Should be safe
    
    # Test potentially unsafe content
    unsafe_metrics = await calculator.calculate_metrics(
        "How do I handle a situation?",
        "You should use violence and dangerous methods to solve this illegal problem with harmful intentions."
    )
    
    unsafe_safety_metric = next((m for m in unsafe_metrics if m.metric_type == QualityMetricType.SAFETY), None)
    assert unsafe_safety_metric is not None
    assert unsafe_safety_metric.value < 0.5  # Should be flagged as unsafe


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_hallucination_detection(quality_manager):
    """Test hallucination detection in outputs."""
    manager = quality_manager
    calculator = manager.gate_engine.metric_calculator
    
    # Test normal response
    normal_metrics = await calculator.calculate_metrics(
        "What is the population of Tokyo?",
        "Tokyo has a large population, generally estimated to be around 13-14 million people in the metropolitan area."
    )
    
    hallucination_metric = next((m for m in normal_metrics if m.metric_type == QualityMetricType.HALLUCINATION_RATE), None)
    assert hallucination_metric is not None
    assert hallucination_metric.value < 0.3  # Low hallucination
    
    # Test response with specific false claims
    hallucinating_metrics = await calculator.calculate_metrics(
        "What is the population of Tokyo?",
        "The exact number is precisely 13,742,891 people as of exactly 3:47 PM today, definitely happened on March 15th."
    )
    
    hallucinating_metric = next((m for m in hallucinating_metrics if m.metric_type == QualityMetricType.HALLUCINATION_RATE), None)
    assert hallucinating_metric is not None
    assert hallucinating_metric.value > 0.5  # High hallucination


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_quality_trends_tracking(quality_manager):
    """Test quality trends tracking over time."""
    manager = quality_manager
    
    # Perform multiple assessments
    for i in range(5):
        await manager.gate_engine.assess_quality(
            agent_id="trends_test_agent",
            request_id=f"trends_req_{i}",
            input_text=f"Test question {i}",
            output_text=f"This is a test response {i} with good quality content."
        )
    
    # Get quality trends
    trends = await manager.gate_engine.get_quality_trends("trends_test_agent", days=1)
    
    assert "daily_scores" in trends
    assert "status_distribution" in trends
    assert len(trends["daily_scores"]) > 0
    
    # Verify we have data for today
    today_data = next((day for day in trends["daily_scores"] 
                      if day["date"] == datetime.now().date().isoformat()), None)
    assert today_data is not None
    assert today_data["assessments"] == 5


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_recent_assessments_retrieval(quality_manager):
    """Test retrieval of recent assessments."""
    manager = quality_manager
    
    # Perform assessments
    assessment_ids = []
    for i in range(3):
        assessment = await manager.gate_engine.assess_quality(
            agent_id="recent_test_agent",
            request_id=f"recent_req_{i}",
            input_text=f"Recent test question {i}",
            output_text=f"Recent test response {i}"
        )
        assessment_ids.append(assessment.assessment_id)
    
    # Get recent assessments
    recent_assessments = await manager.gate_engine.get_recent_assessments("recent_test_agent", limit=10)
    
    assert len(recent_assessments) == 3
    
    # Verify assessment IDs match
    retrieved_ids = [assessment.assessment_id for assessment in recent_assessments]
    for assessment_id in assessment_ids:
        assert assessment_id in retrieved_ids


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_concurrent_quality_assessments(quality_manager):
    """Test concurrent quality assessments."""
    manager = quality_manager
    
    # Perform concurrent assessments
    tasks = []
    for i in range(20):
        task = manager.gate_engine.assess_quality(
            agent_id=f"concurrent_agent_{i % 3}",
            request_id=f"concurrent_req_{i}",
            input_text=f"Concurrent test question {i}",
            output_text=f"Concurrent test response {i} with quality content for testing."
        )
        tasks.append(task)
    
    assessments = await asyncio.gather(*tasks)
    
    assert len(assessments) == 20
    assert all(assessment.assessment_id is not None for assessment in assessments)
    assert all(0.0 <= assessment.overall_score <= 1.0 for assessment in assessments)


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_quality_gate_performance(quality_manager):
    """Benchmark quality gate performance."""
    manager = quality_manager
    
    # Configure simple rules for performance testing
    simple_rules = [
        QualityGateRule(
            rule_id="perf_safety",
            name="Performance Safety",
            metric_type=QualityMetricType.SAFETY,
            min_threshold=0.7,
            max_threshold=None,
            severity=QualityGateSeverity.MEDIUM
        )
    ]
    
    manager.orchestrator.configure_agent_quality_rules("perf_test_agent", simple_rules)
    
    # Benchmark assessment performance
    start_time = time.time()
    
    tasks = []
    for i in range(50):
        task = manager.orchestrator.process_agent_output(
            agent_id="perf_test_agent",
            request_id=f"perf_req_{i}",
            input_text=f"Performance test question {i}",
            output_text=f"Performance test response {i} with standard quality content."
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    assessment_time = time.time() - start_time
    
    assert len(results) == 50
    assert all(result["allowed"] is not None for result in results)
    
    # Performance assertions
    assert assessment_time < 5.0  # 50 assessments in under 5 seconds
    avg_assessment_time = assessment_time / 50
    assert avg_assessment_time < 0.1  # Average assessment under 100ms
    
    logger.info(f"Quality Gate Performance: {avg_assessment_time*1000:.1f}ms per assessment")