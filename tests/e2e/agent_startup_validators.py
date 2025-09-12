"""Agent Startup Response Validation Utilities
BVJ: Enterprise/Growth segment - $100K+ MRR protection from agent failures
Architecture:  <= 300 lines,  <= 8 lines per function, modular validators
"""

import asyncio
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import pytest

from netra_backend.app.schemas.monitoring_types import (
    AlertSeverity,
    MetricData,
    MetricType,
)
from netra_backend.app.schemas.quality_types import (
    ContentType,
    QualityLevel,
    QualityMetrics,
)
from netra_backend.app.schemas.shared_types import (
    AgentStatus,
    ErrorContext,
    ProcessingResult,
)
from tests.e2e.config import CustomerTier, UnifiedTestConfig


class ResponseValidationType(str, Enum):
    """Types of response validation"""
    QUALITY = "quality"
    PERFORMANCE = "performance"
    RESOURCE = "resource"
    CONTENT = "content"
    CONTEXT = "context"
    ERROR = "error"
    MULTI_AGENT = "multi_agent"


class ValidationSeverity(str, Enum):
    """Validation failure severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ResponseValidationMetrics:
    """Comprehensive response validation metrics"""
    response_time_ms: float = 0.0
    content_quality_score: float = 0.0
    context_preservation_score: float = 0.0
    token_count: int = 0
    validation_errors: List[str] = field(default_factory=list)
    performance_warnings: List[str] = field(default_factory=list)
    quality_issues: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Complete validation result with detailed analysis"""
    validation_type: ResponseValidationType
    passed: bool
    severity: ValidationSeverity
    metrics: ResponseValidationMetrics
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ResponseQualityValidator:
    """Validates response quality and content meaningfulness"""
    
    def __init__(self):
        """Initialize quality validator with quality thresholds"""
        self.min_quality_score = 70.0
        self.min_word_count = 10
        self.generic_phrases = _get_generic_phrases()
    
    def validate_response_quality(self, response: str, 
                                 content_type: ContentType) -> ValidationResult:
        """Validate overall response quality"""
        metrics = ResponseValidationMetrics()
        start_time = time.perf_counter()
        
        quality_score = self._calculate_quality_score(response, metrics)
        content_meaningful = self._validate_content_meaningful(response, metrics)
        
        metrics.response_time_ms = (time.perf_counter() - start_time) * 1000
        passed = quality_score >= self.min_quality_score and content_meaningful
        severity = _get_quality_severity(quality_score)
        
        return ValidationResult(ResponseValidationType.QUALITY, passed, severity, metrics)
    
    def _calculate_quality_score(self, response: str, 
                                metrics: ResponseValidationMetrics) -> float:
        """Calculate comprehensive quality score"""
        word_count = len(response.split())
        generic_ratio = self._calculate_generic_ratio(response)
        specificity_score = max(0, 100 - (generic_ratio * 100))
        
        quality_score = min(100, specificity_score * (word_count / self.min_word_count))
        metrics.content_quality_score = quality_score
        return quality_score
    
    def _validate_content_meaningful(self, response: str, 
                                   metrics: ResponseValidationMetrics) -> bool:
        """Validate content contains meaningful information"""
        if len(response.strip()) < self.min_word_count:
            metrics.quality_issues.append("Response too short")
            return False
        
        if self._has_circular_reasoning(response):
            metrics.quality_issues.append("Circular reasoning detected")
            return False
        
        return True
    
    def _calculate_generic_ratio(self, response: str) -> float:
        """Calculate ratio of generic phrases in response"""
        generic_count = sum(1 for phrase in self.generic_phrases 
                          if phrase in response.lower())
        return generic_count / max(len(response.split()), 1)
    
    def _has_circular_reasoning(self, response: str) -> bool:
        """Detect circular reasoning patterns"""
        sentences = response.split('.')
        return len(sentences) != len(set(sentences))


class ResponsePerformanceValidator:
    """Validates response performance metrics"""
    
    def __init__(self):
        """Initialize performance validator with thresholds"""
        self.max_response_time_ms = 5000
        self.max_token_count = 2000
    
    def validate_performance_metrics(self, response_time_ms: float,
                                   token_count: int) -> ValidationResult:
        """Validate response performance metrics"""
        metrics = ResponseValidationMetrics()
        metrics.response_time_ms = response_time_ms
        metrics.token_count = token_count
        
        time_valid = self._validate_response_time(response_time_ms, metrics)
        token_valid = self._validate_token_usage(token_count, metrics)
        
        passed = time_valid and token_valid
        severity = _get_performance_severity(response_time_ms, token_count)
        
        return ValidationResult(ResponseValidationType.PERFORMANCE, passed, severity, metrics)
    
    def _validate_response_time(self, response_time_ms: float,
                               metrics: ResponseValidationMetrics) -> bool:
        """Validate response time within acceptable limits"""
        if response_time_ms > self.max_response_time_ms:
            metrics.performance_warnings.append(f"Response time {response_time_ms}ms exceeds {self.max_response_time_ms}ms")
            return False
        return True
    
    def _validate_token_usage(self, token_count: int,
                             metrics: ResponseValidationMetrics) -> bool:
        """Validate token usage efficiency"""
        if token_count > self.max_token_count:
            metrics.performance_warnings.append(f"Token count {token_count} exceeds {self.max_token_count}")
            return False
        return True


class ContextPreservationValidator:
    """Validates context preservation across agent interactions"""
    
    def __init__(self):
        """Initialize context preservation validator"""
        self.required_context_keys = ['user_id', 'session_id', 'request_id']
        self.context_preservation_threshold = 0.8
    
    def validate_context_preservation(self, original_context: Dict[str, Any],
                                    response_context: Dict[str, Any]) -> ValidationResult:
        """Validate context data preservation"""
        metrics = ResponseValidationMetrics()
        
        preservation_score = self._calculate_preservation_score(original_context, response_context)
        required_keys_present = self._validate_required_keys(response_context, metrics)
        
        metrics.context_preservation_score = preservation_score
        passed = preservation_score >= self.context_preservation_threshold and required_keys_present
        severity = _get_context_severity(preservation_score)
        
        return ValidationResult(ResponseValidationType.CONTEXT, passed, severity, metrics)
    
    def _calculate_preservation_score(self, original: Dict[str, Any],
                                    preserved: Dict[str, Any]) -> float:
        """Calculate context preservation score"""
        if not original:
            return 1.0
        
        preserved_count = sum(1 for key, value in original.items()
                            if preserved.get(key) == value)
        return preserved_count / len(original)
    
    def _validate_required_keys(self, context: Dict[str, Any],
                               metrics: ResponseValidationMetrics) -> bool:
        """Validate required context keys are present"""
        missing_keys = [key for key in self.required_context_keys
                       if key not in context]
        
        if missing_keys:
            metrics.validation_errors.extend(f"Missing context key: {key}" for key in missing_keys)
            return False
        return True


class AgentStartupValidatorSuite:
    """Complete agent startup validation suite"""
    
    def __init__(self, config: Optional[UnifiedTestConfig] = None):
        """Initialize validation suite with configuration"""
        self.config = config or UnifiedTestConfig()
        self.quality_validator = ResponseQualityValidator()
        self.performance_validator = ResponsePerformanceValidator()
        self.context_validator = ContextPreservationValidator()
    
    async def validate_complete_startup_response(self, 
                                               response: Dict[str, Any],
                                               context: Dict[str, Any],
                                               performance_metrics: Dict[str, Any]) -> List[ValidationResult]:
        """Perform complete validation of agent startup response"""
        results = []
        
        # Validate response quality
        if 'content' in response:
            quality_result = self.quality_validator.validate_response_quality(
                response['content'], ContentType.GENERAL
            )
            results.append(quality_result)
        
        # Validate performance metrics
        performance_result = self.performance_validator.validate_performance_metrics(
            performance_metrics.get('response_time_ms', 0),
            performance_metrics.get('token_count', 0)
        )
        results.append(performance_result)
        
        # Validate context preservation
        if 'context' in response:
            context_result = self.context_validator.validate_context_preservation(
                context, response['context']
            )
            results.append(context_result)
        
        return results


# Helper functions for validation logic
def _get_generic_phrases() -> List[str]:
    """Get list of generic phrases that reduce quality scores"""
    return ['I understand', 'Let me help', 'I can assist', 'Thank you for',
            'I appreciate', 'Happy to help', 'Please let me know']

def _get_quality_severity(quality_score: float) -> ValidationSeverity:
    """Determine validation severity based on quality score"""
    if quality_score < 50: return ValidationSeverity.CRITICAL
    elif quality_score < 70: return ValidationSeverity.HIGH
    elif quality_score < 85: return ValidationSeverity.MEDIUM
    return ValidationSeverity.LOW

def _get_performance_severity(response_time: float, token_count: int) -> ValidationSeverity:
    """Determine severity based on performance metrics"""
    if response_time > 10000 or token_count > 4000: return ValidationSeverity.CRITICAL
    elif response_time > 5000 or token_count > 2000: return ValidationSeverity.HIGH
    return ValidationSeverity.MEDIUM

def _get_context_severity(preservation_score: float) -> ValidationSeverity:
    """Determine severity based on context preservation"""
    if preservation_score < 0.5: return ValidationSeverity.CRITICAL
    elif preservation_score < 0.8: return ValidationSeverity.HIGH
    return ValidationSeverity.MEDIUM

# Pytest fixtures for validation utilities
@pytest.fixture
def startup_validator_suite():
    """Provide startup validator suite for testing"""
    return AgentStartupValidatorSuite()

@pytest.fixture  
def sample_startup_responses():
    """Provide sample startup responses for validation testing"""
    return {
        'valid_response': {
            'content': 'Agent successfully initialized with optimization capabilities.',
            'context': {'user_id': 'test-user', 'session_id': 'test-session', 'request_id': 'test-request'},
            'status': AgentStatus.READY.value
        },
        'invalid_response': {'content': 'I understand. Let me help you.', 'context': {}},
        'performance_data': {'response_time_ms': 1200, 'token_count': 150, 'memory_mb': 64}
    }

# Export validation components
__all__ = [
    'ResponseQualityValidator',
    'ResponsePerformanceValidator', 
    'ContextPreservationValidator',
    'AgentStartupValidatorSuite',
    'ValidationResult',
    'ResponseValidationMetrics',
    'ResponseValidationType'
]