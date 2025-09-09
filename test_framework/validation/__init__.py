#!/usr/bin/env python
"""
Event Validation Infrastructure - MISSION CRITICAL for Business Value

This package provides comprehensive validation infrastructure for WebSocket events
that ensures business value delivery, user engagement, and revenue protection.

Business Value Justification:
- Segment: Platform/Internal - Chat validation infrastructure  
- Business Goal: Ensure WebSocket events deliver substantive chat value
- Value Impact: Validates the event quality that drives $500K+ ARR
- Revenue Impact: Protects against value degradation that causes user churn

CRITICAL VALIDATORS:

1. EventSequenceValidator - Validates critical event ordering for user engagement
2. ContentQualityValidator - Validates event content delivers business value  
3. TimingValidator - Validates response timing preserves user attention
4. BusinessValueValidator - Validates overall business value and conversion potential

@compliance CLAUDE.md - WebSocket events enable substantive chat interactions
@compliance SPEC/core.xml - Comprehensive validation protects business value
"""

from .event_sequence_validator import (
    EventSequenceValidator,
    EventSequenceState,
    EventSequenceRule,
    EventSequenceViolation,
    EventSequenceResult,
    BusinessValueImpact,
    validate_agent_execution_sequence,
    create_test_event_sequence
)

from .content_quality_validator import (
    ContentQualityValidator,
    ContentQualityLevel,
    ContentViolationType,
    ContentQualityViolation,
    ContentQualityResult,
    validate_event_content_quality,
    assert_content_delivers_business_value
)

from .timing_validator import (
    TimingValidator,
    TimingCriticality,
    TimingViolationType,
    TimingRequirement,
    TimingViolation,
    TimingValidationResult,
    validate_event_timing_performance,
    create_timing_test_events
)

from .business_value_validator import (
    BusinessValueValidator,
    BusinessValueImpact as BVImpact,
    UserEngagementLevel,
    ConversionFactor,
    BusinessValueMetric,
    UserEngagementMetrics,
    ConversionPotential,
    BusinessValueViolation,
    BusinessValueResult,
    validate_business_value_delivery,
    assert_revenue_protection
)

# Convenience imports for common usage
__all__ = [
    # Event Sequence Validation
    "EventSequenceValidator",
    "EventSequenceState", 
    "EventSequenceRule",
    "EventSequenceViolation",
    "EventSequenceResult",
    "validate_agent_execution_sequence",
    "create_test_event_sequence",
    
    # Content Quality Validation
    "ContentQualityValidator",
    "ContentQualityLevel",
    "ContentViolationType", 
    "ContentQualityViolation",
    "ContentQualityResult",
    "validate_event_content_quality",
    "assert_content_delivers_business_value",
    
    # Timing Validation
    "TimingValidator",
    "TimingCriticality",
    "TimingViolationType",
    "TimingRequirement",
    "TimingViolation", 
    "TimingValidationResult",
    "validate_event_timing_performance",
    "create_timing_test_events",
    
    # Business Value Validation
    "BusinessValueValidator",
    "BVImpact",
    "UserEngagementLevel",
    "ConversionFactor",
    "BusinessValueMetric",
    "UserEngagementMetrics", 
    "ConversionPotential",
    "BusinessValueViolation",
    "BusinessValueResult",
    "validate_business_value_delivery",
    "assert_revenue_protection",
    
    # Shared types
    "BusinessValueImpact"
]

# Version info
__version__ = "1.0.0"
__author__ = "Netra Systems - Event Validation Team"
__description__ = "Mission-critical validation infrastructure for WebSocket business value"