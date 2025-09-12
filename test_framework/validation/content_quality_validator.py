#!/usr/bin/env python
"""
Content Quality Validator - MISSION CRITICAL for Business Value

Business Value Justification:
- Segment: Platform/Internal - Chat content quality validation  
- Business Goal: Ensure WebSocket event content delivers substantive value and maintains user engagement
- Value Impact: Validates event content quality that drives user trust and conversions
- Revenue Impact: Protects chat content quality that generates customer satisfaction and retention

CRITICAL REQUIREMENTS FROM CLAUDE.MD:
- WebSocket events enable substantive chat interactions - content MUST deliver business value
- Tests must FAIL HARD when event content compromises business value
- Event content MUST be meaningful, actionable, and user-facing
- No mocks - validate real content from real services

BUSINESS VALUE CONTENT REQUIREMENTS:
- agent_thinking: Must show meaningful progress, not generic messages
- tool_executing: Must show specific tool usage for transparency  
- tool_completed: Must show actionable results and insights
- agent_completed: Must deliver substantial final value to user
- All events: Must preserve user trust and drive engagement

@compliance CLAUDE.md - WebSocket events enable substantive chat interactions
@compliance SPEC/core.xml - Event content quality critical for business value
"""

import json
import logging
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Set, Any, Union
from dataclasses import dataclass, field
from enum import Enum

from test_framework.ssot.real_websocket_test_client import WebSocketEvent

logger = logging.getLogger(__name__)


class ContentQualityLevel(str, Enum):
    """Content quality levels for business value assessment."""
    EXCELLENT = "excellent"      # Exceeds user expectations, drives engagement
    GOOD = "good"               # Meets expectations, maintains trust
    ACCEPTABLE = "acceptable"   # Basic requirements met, minor issues
    POOR = "poor"              # Below standards, impacts user experience
    UNACCEPTABLE = "unacceptable"  # Compromises business value, user abandonment risk


class ContentViolationType(str, Enum):
    """Types of content quality violations."""
    EMPTY_CONTENT = "empty_content"
    GENERIC_MESSAGE = "generic_message"
    MISSING_ACTIONABLE_INFO = "missing_actionable_info"
    TECHNICAL_JARGON = "technical_jargon"
    INCONSISTENT_FORMAT = "inconsistent_format"
    MISSING_USER_VALUE = "missing_user_value"
    SECURITY_LEAK = "security_leak"
    BUSINESS_IP_LEAK = "business_ip_leak"


@dataclass
class ContentQualityViolation:
    """Represents a content quality violation."""
    event_type: str
    violation_type: ContentViolationType
    severity: ContentQualityLevel
    description: str
    content_excerpt: str
    business_impact: str
    user_facing: bool = True
    timestamp: float = field(default_factory=time.time)


@dataclass
class ContentQualityResult:
    """Result of content quality validation for an event."""
    event_type: str
    quality_level: ContentQualityLevel
    violations: List[ContentQualityViolation] = field(default_factory=list)
    business_value_score: float = 0.0  # 0.0-1.0, higher is better
    user_engagement_score: float = 0.0  # 0.0-1.0, higher is better
    actionable_content: bool = False
    user_trust_preserved: bool = True


class ContentQualityValidator:
    """
    MISSION CRITICAL: Content Quality Validator for Business Value Protection
    
    This validator ensures WebSocket event content delivers meaningful business value,
    maintains user engagement, and preserves trust in the AI system.
    
    CRITICAL FEATURES:
    - Validates content meaningfulness and actionability
    - Detects generic/template messages that reduce trust
    - Ensures technical details don't leak business IP
    - Measures user engagement potential of content
    - Fails hard when content compromises business value
    """
    
    # Business value content patterns for each event type
    BUSINESS_VALUE_PATTERNS = {
        "agent_started": {
            "required_elements": ["agent_id", "task_description"],
            "quality_indicators": [
                r"analyzing\s+your\s+request",
                r"processing\s+.*\s+for\s+you",
                r"starting\s+.*\s+analysis",
                r"working\s+on\s+.*\s+solution"
            ],
            "generic_patterns": [  # These indicate poor content
                r"^agent\s+started$",
                r"^starting\s+agent$",
                r"^beginning\s+process$"
            ]
        },
        "agent_thinking": {
            "required_elements": ["content", "progress_indicator"],
            "quality_indicators": [
                r"analyzing\s+.*\s+data",
                r"considering\s+.*\s+options",
                r"researching\s+.*\s+solutions",
                r"evaluating\s+.*\s+approaches",
                r"processing\s+.*\s+information"
            ],
            "generic_patterns": [
                r"^thinking\.\.\.$",
                r"^processing\.\.\.$",
                r"^working\.\.\.$"
            ]
        },
        "tool_executing": {
            "required_elements": ["tool_name", "execution_context"],
            "quality_indicators": [
                r"searching\s+.*\s+for\s+.*",
                r"querying\s+.*\s+database",
                r"analyzing\s+.*\s+with\s+.*",
                r"retrieving\s+.*\s+information"
            ],
            "generic_patterns": [
                r"^executing\s+tool$",
                r"^running\s+.*$",
                r"^tool\s+started$"
            ]
        },
        "tool_completed": {
            "required_elements": ["tool_name", "result", "insights"],
            "quality_indicators": [
                r"found\s+\d+\s+.*\s+results",
                r"identified\s+.*\s+key\s+.*",
                r"discovered\s+.*\s+insights",
                r"retrieved\s+.*\s+data\s+points"
            ],
            "generic_patterns": [
                r"^tool\s+completed$",
                r"^finished\s+execution$",
                r"^done$"
            ]
        },
        "agent_completed": {
            "required_elements": ["result", "summary", "next_steps"],
            "quality_indicators": [
                r"completed\s+.*\s+analysis",
                r"generated\s+.*\s+recommendations",
                r"provided\s+.*\s+solution",
                r"delivered\s+.*\s+insights"
            ],
            "generic_patterns": [
                r"^task\s+completed$",
                r"^agent\s+finished$",
                r"^done\s+processing$"
            ]
        }
    }
    
    # Patterns that indicate business IP leakage (CRITICAL to prevent)
    BUSINESS_IP_PATTERNS = [
        r"internal\s+api\s+key",
        r"secret\s+token",
        r"private\s+endpoint",
        r"internal\s+service\s+.*",
        r"netra\s+internal\s+.*",
        r"backend\s+configuration",
        r"database\s+connection",
        r"auth\s+service\s+.*",
        r"internal\s+tool\s+.*"
    ]
    
    # Patterns indicating security-sensitive information
    SECURITY_PATTERNS = [
        r"user_id\s*[:=]\s*['\"][^'\"]+['\"]",
        r"email\s*[:=]\s*['\"][^'\"]*@[^'\"]*['\"]",
        r"token\s*[:=]\s*['\"][^'\"]+['\"]",
        r"password\s*[:=]\s*['\"][^'\"]+['\"]",
        r"api_key\s*[:=]\s*['\"][^'\"]+['\"]"
    ]
    
    def __init__(self, user_id: str, session_id: str, strict_mode: bool = True):
        """Initialize content quality validator.
        
        Args:
            user_id: User ID for validation context
            session_id: Session ID for tracking
            strict_mode: Whether to apply strict business value requirements
        """
        self.user_id = user_id
        self.session_id = session_id
        self.strict_mode = strict_mode
        
        # Validation tracking
        self.validated_events = 0
        self.total_violations = 0
        self.business_value_failures = 0
        self.content_results: List[ContentQualityResult] = []
        
        logger.info(f"ContentQualityValidator initialized for user {user_id}, strict_mode={strict_mode}")
    
    def validate_event_content(self, event: WebSocketEvent) -> ContentQualityResult:
        """Validate the content quality of a WebSocket event.
        
        Args:
            event: WebSocket event to validate
            
        Returns:
            ContentQualityResult with validation details
        """
        self.validated_events += 1
        
        result = ContentQualityResult(
            event_type=event.event_type,
            quality_level=ContentQualityLevel.ACCEPTABLE
        )
        
        # Extract content for validation
        content = self._extract_event_content(event)
        
        # Run validation checks
        violations = []
        violations.extend(self._validate_content_completeness(event, content))
        violations.extend(self._validate_business_value_content(event, content))
        violations.extend(self._validate_security_compliance(event, content))
        violations.extend(self._validate_user_engagement_quality(event, content))
        
        result.violations = violations
        self.total_violations += len(violations)
        
        # Calculate quality scores
        result.quality_level = self._calculate_quality_level(violations)
        result.business_value_score = self._calculate_business_value_score(event, content, violations)
        result.user_engagement_score = self._calculate_engagement_score(event, content, violations)
        result.actionable_content = self._has_actionable_content(event, content)
        result.user_trust_preserved = self._preserves_user_trust(violations)
        
        # Track business value failures
        if result.business_value_score < 0.5:
            self.business_value_failures += 1
        
        self.content_results.append(result)
        
        # Log critical issues immediately
        critical_violations = [v for v in violations if v.severity == ContentQualityLevel.UNACCEPTABLE]
        for violation in critical_violations:
            logger.error(f" ALERT:  CRITICAL CONTENT VIOLATION: {violation.description}")
        
        return result
    
    def _extract_event_content(self, event: WebSocketEvent) -> Dict[str, Any]:
        """Extract content from WebSocket event data."""
        # Try to get the most relevant content based on event type
        content = {
            "raw_data": event.data,
            "text_content": "",
            "structured_data": {}
        }
        
        # Extract text content based on event type
        if event.event_type == "agent_thinking":
            content["text_content"] = event.data.get("content", "")
            content["structured_data"] = event.data.get("progress", {})
        elif event.event_type == "tool_executing":
            content["text_content"] = f"Executing {event.data.get('tool_name', 'unknown tool')}"
            content["structured_data"] = event.data.get("parameters", {})
        elif event.event_type == "tool_completed":
            content["text_content"] = event.data.get("summary", "")
            content["structured_data"] = event.data.get("result", {})
        elif event.event_type == "agent_completed":
            content["text_content"] = event.data.get("summary", "")
            content["structured_data"] = event.data.get("result", {})
        else:
            # Generic extraction
            text_fields = ["content", "message", "summary", "description"]
            for field in text_fields:
                if field in event.data and isinstance(event.data[field], str):
                    content["text_content"] = event.data[field]
                    break
        
        return content
    
    def _validate_content_completeness(self, event: WebSocketEvent, content: Dict[str, Any]) -> List[ContentQualityViolation]:
        """Validate that event content is complete and non-empty."""
        violations = []
        
        # Check for empty content
        text_content = content.get("text_content", "").strip()
        if not text_content and event.event_type in ["agent_thinking", "agent_completed"]:
            violations.append(ContentQualityViolation(
                event_type=event.event_type,
                violation_type=ContentViolationType.EMPTY_CONTENT,
                severity=ContentQualityLevel.UNACCEPTABLE,
                description=f"Event {event.event_type} has empty content - users see no value",
                content_excerpt=str(event.data)[:100],
                business_impact="Users cannot see AI progress or results, leading to abandonment"
            ))
        
        # Check for required elements based on event type
        if event.event_type in self.BUSINESS_VALUE_PATTERNS:
            pattern_config = self.BUSINESS_VALUE_PATTERNS[event.event_type]
            required_elements = pattern_config.get("required_elements", [])
            
            for element in required_elements:
                if element not in event.data:
                    violations.append(ContentQualityViolation(
                        event_type=event.event_type,
                        violation_type=ContentViolationType.MISSING_ACTIONABLE_INFO,
                        severity=ContentQualityLevel.POOR,
                        description=f"Missing required element '{element}' for business value",
                        content_excerpt=str(event.data)[:100],
                        business_impact=f"Reduced user trust due to incomplete {event.event_type} information"
                    ))
        
        return violations
    
    def _validate_business_value_content(self, event: WebSocketEvent, content: Dict[str, Any]) -> List[ContentQualityViolation]:
        """Validate that content delivers business value to users."""
        violations = []
        text_content = content.get("text_content", "").lower()
        
        if event.event_type not in self.BUSINESS_VALUE_PATTERNS:
            return violations
        
        pattern_config = self.BUSINESS_VALUE_PATTERNS[event.event_type]
        
        # Check for generic/template messages that reduce trust
        generic_patterns = pattern_config.get("generic_patterns", [])
        for pattern in generic_patterns:
            if re.search(pattern, text_content, re.IGNORECASE):
                violations.append(ContentQualityViolation(
                    event_type=event.event_type,
                    violation_type=ContentViolationType.GENERIC_MESSAGE,
                    severity=ContentQualityLevel.POOR,
                    description=f"Generic message pattern detected: reduces user trust",
                    content_excerpt=text_content[:100],
                    business_impact="Generic messages make AI appear less intelligent, reducing conversion"
                ))
        
        # In strict mode, require quality indicators
        if self.strict_mode:
            quality_indicators = pattern_config.get("quality_indicators", [])
            has_quality_indicator = any(
                re.search(pattern, text_content, re.IGNORECASE)
                for pattern in quality_indicators
            )
            
            if quality_indicators and not has_quality_indicator:
                violations.append(ContentQualityViolation(
                    event_type=event.event_type,
                    violation_type=ContentViolationType.MISSING_USER_VALUE,
                    severity=ContentQualityLevel.ACCEPTABLE,
                    description=f"Content lacks business value indicators for {event.event_type}",
                    content_excerpt=text_content[:100],
                    business_impact="Content doesn't demonstrate AI intelligence and capability"
                ))
        
        return violations
    
    def _validate_security_compliance(self, event: WebSocketEvent, content: Dict[str, Any]) -> List[ContentQualityViolation]:
        """Validate content for security and business IP compliance."""
        violations = []
        
        # Check both text content and JSON representation for leaks
        all_content = content.get("text_content", "") + " " + json.dumps(content.get("raw_data", {}))
        
        # Check for business IP leakage (CRITICAL)
        for pattern in self.BUSINESS_IP_PATTERNS:
            if re.search(pattern, all_content, re.IGNORECASE):
                violations.append(ContentQualityViolation(
                    event_type=event.event_type,
                    violation_type=ContentViolationType.BUSINESS_IP_LEAK,
                    severity=ContentQualityLevel.UNACCEPTABLE,
                    description="Business IP leaked in event content - CRITICAL SECURITY ISSUE",
                    content_excerpt="[REDACTED FOR SECURITY]",
                    business_impact="Exposes internal architecture, compromises competitive advantage",
                    user_facing=False
                ))
        
        # Check for security-sensitive information
        for pattern in self.SECURITY_PATTERNS:
            if re.search(pattern, all_content, re.IGNORECASE):
                violations.append(ContentQualityViolation(
                    event_type=event.event_type,
                    violation_type=ContentViolationType.SECURITY_LEAK,
                    severity=ContentQualityLevel.UNACCEPTABLE,
                    description="Security-sensitive information in event content",
                    content_excerpt="[REDACTED FOR SECURITY]",
                    business_impact="Privacy violation, potential data breach",
                    user_facing=False
                ))
        
        return violations
    
    def _validate_user_engagement_quality(self, event: WebSocketEvent, content: Dict[str, Any]) -> List[ContentQualityViolation]:
        """Validate content quality for user engagement."""
        violations = []
        text_content = content.get("text_content", "")
        
        # Check for technical jargon that confuses users
        technical_jargon_patterns = [
            r"http\s+status\s+\d+",
            r"exception\s+thrown",
            r"stack\s+trace",
            r"database\s+query",
            r"api\s+response\s+code",
            r"json\s+parsing\s+error",
            r"connection\s+timeout",
            r"null\s+pointer\s+exception"
        ]
        
        for pattern in technical_jargon_patterns:
            if re.search(pattern, text_content, re.IGNORECASE):
                violations.append(ContentQualityViolation(
                    event_type=event.event_type,
                    violation_type=ContentViolationType.TECHNICAL_JARGON,
                    severity=ContentQualityLevel.POOR,
                    description="Technical jargon detected - confuses users",
                    content_excerpt=text_content[:100],
                    business_impact="Technical language reduces user comprehension and trust"
                ))
        
        # Check content length appropriateness
        if len(text_content) > 500 and event.event_type in ["agent_thinking", "tool_executing"]:
            violations.append(ContentQualityViolation(
                event_type=event.event_type,
                violation_type=ContentViolationType.INCONSISTENT_FORMAT,
                severity=ContentQualityLevel.ACCEPTABLE,
                description=f"Content too verbose for {event.event_type} - may overwhelm user",
                content_excerpt=text_content[:100] + "...",
                business_impact="Verbose progress updates can overwhelm and confuse users"
            ))
        
        return violations
    
    def _calculate_quality_level(self, violations: List[ContentQualityViolation]) -> ContentQualityLevel:
        """Calculate overall quality level based on violations."""
        if not violations:
            return ContentQualityLevel.EXCELLENT
        
        severity_counts = {}
        for violation in violations:
            severity_counts[violation.severity] = severity_counts.get(violation.severity, 0) + 1
        
        # Any unacceptable violation makes the overall quality unacceptable
        if severity_counts.get(ContentQualityLevel.UNACCEPTABLE, 0) > 0:
            return ContentQualityLevel.UNACCEPTABLE
        
        # Multiple poor violations downgrade quality
        if severity_counts.get(ContentQualityLevel.POOR, 0) >= 2:
            return ContentQualityLevel.POOR
        
        if severity_counts.get(ContentQualityLevel.POOR, 0) >= 1:
            return ContentQualityLevel.ACCEPTABLE
        
        return ContentQualityLevel.GOOD
    
    def _calculate_business_value_score(self, event: WebSocketEvent, content: Dict[str, Any], violations: List[ContentQualityViolation]) -> float:
        """Calculate business value score (0.0-1.0)."""
        base_score = 1.0
        
        # Deduct points for violations
        for violation in violations:
            if violation.severity == ContentQualityLevel.UNACCEPTABLE:
                base_score -= 0.5
            elif violation.severity == ContentQualityLevel.POOR:
                base_score -= 0.4  # Increased penalty for poor content
            elif violation.severity == ContentQualityLevel.ACCEPTABLE:
                base_score -= 0.1
        
        # Additional penalty for empty/generic content
        text_content = content.get("text_content", "").strip().lower()
        if not text_content or text_content in ["done", "completed", "finished"]:
            base_score -= 0.4
        
        # Bonus points for actionable content
        if self._has_actionable_content(event, content):
            base_score += 0.1  # Reduced bonus to be more strict
        
        return max(0.0, min(1.0, base_score))
    
    def _calculate_engagement_score(self, event: WebSocketEvent, content: Dict[str, Any], violations: List[ContentQualityViolation]) -> float:
        """Calculate user engagement score (0.0-1.0)."""
        base_score = 0.8  # Start with good baseline
        
        text_content = content.get("text_content", "")
        
        # Engagement factors
        if len(text_content) > 10 and not any(v.violation_type == ContentViolationType.GENERIC_MESSAGE for v in violations):
            base_score += 0.1  # Specific content
        
        if event.event_type in ["tool_completed", "agent_completed"] and len(text_content) > 20:
            base_score += 0.1  # Substantial completion messages
        
        # Deduct for violations that hurt engagement
        for violation in violations:
            if violation.violation_type in [ContentViolationType.GENERIC_MESSAGE, ContentViolationType.TECHNICAL_JARGON]:
                base_score -= 0.2
            elif violation.violation_type == ContentViolationType.EMPTY_CONTENT:
                base_score -= 0.5
        
        return max(0.0, min(1.0, base_score))
    
    def _has_actionable_content(self, event: WebSocketEvent, content: Dict[str, Any]) -> bool:
        """Check if content provides actionable information to users."""
        text_content = content.get("text_content", "").lower()
        structured_data = content.get("structured_data", {})
        
        # Look for actionable patterns
        actionable_patterns = [
            r"found\s+\d+",
            r"discovered\s+.*",
            r"identified\s+.*",
            r"recommendations?",
            r"next\s+steps?",
            r"suggested?\s+.*",
            r"results?\s+show",
            r"analysis\s+reveals"
        ]
        
        has_actionable_text = any(
            re.search(pattern, text_content, re.IGNORECASE)
            for pattern in actionable_patterns
        )
        
        has_structured_results = bool(structured_data and (
            "results" in structured_data or
            "recommendations" in structured_data or
            "insights" in structured_data or
            "summary" in structured_data
        ))
        
        return has_actionable_text or has_structured_results
    
    def _preserves_user_trust(self, violations: List[ContentQualityViolation]) -> bool:
        """Check if content preserves user trust."""
        trust_damaging_types = {
            ContentViolationType.SECURITY_LEAK,
            ContentViolationType.BUSINESS_IP_LEAK,
            ContentViolationType.EMPTY_CONTENT
        }
        
        return not any(v.violation_type in trust_damaging_types for v in violations)
    
    def assert_business_value_preserved(self, min_score_threshold: float = 0.5) -> None:
        """Assert that content quality preserves business value.
        
        Args:
            min_score_threshold: Minimum business value score required
            
        Raises:
            AssertionError: If business value is compromised
        """
        if not self.content_results:
            raise AssertionError("No content validation results available")
        
        failures = []
        critical_violations = []
        
        for result in self.content_results:
            if result.business_value_score < min_score_threshold:
                failures.append(
                    f"{result.event_type}: Score {result.business_value_score:.2f} < {min_score_threshold:.2f}"
                )
            
            if result.quality_level == ContentQualityLevel.UNACCEPTABLE:
                critical_violations.append(
                    f"{result.event_type}: UNACCEPTABLE quality level"
                )
        
        error_parts = []
        if critical_violations:
            error_parts.append("CRITICAL CONTENT VIOLATIONS:")
            error_parts.extend(critical_violations)
        
        if failures:
            error_parts.append("BUSINESS VALUE FAILURES:")
            error_parts.extend(failures)
        
        if error_parts:
            error_message = (
                " ALERT:  CONTENT QUALITY COMPROMISED - WebSocket event content failed business value requirements!\n"
                + "\n".join(error_parts) + "\n\n"
                "This indicates chat content will not deliver substantive value to users."
            )
            logger.error(error_message)
            raise AssertionError(error_message)
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get comprehensive content validation summary.
        
        Returns:
            Dictionary with validation metrics and results
        """
        if not self.content_results:
            return {"error": "No validation results available"}
        
        avg_business_score = sum(r.business_value_score for r in self.content_results) / len(self.content_results)
        avg_engagement_score = sum(r.user_engagement_score for r in self.content_results) / len(self.content_results)
        
        quality_distribution = {}
        for result in self.content_results:
            level = result.quality_level.value
            quality_distribution[level] = quality_distribution.get(level, 0) + 1
        
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "validated_events": self.validated_events,
            "total_violations": self.total_violations,
            "business_value_failures": self.business_value_failures,
            "average_business_value_score": avg_business_score,
            "average_engagement_score": avg_engagement_score,
            "quality_distribution": quality_distribution,
            "critical_violations": [
                {
                    "event_type": result.event_type,
                    "violations": [
                        {
                            "type": v.violation_type.value,
                            "severity": v.severity.value,
                            "description": v.description,
                            "business_impact": v.business_impact
                        }
                        for v in result.violations
                        if v.severity == ContentQualityLevel.UNACCEPTABLE
                    ]
                }
                for result in self.content_results
                if any(v.severity == ContentQualityLevel.UNACCEPTABLE for v in result.violations)
            ]
        }


# Convenience functions

def validate_event_content_quality(event: WebSocketEvent, strict_mode: bool = True) -> ContentQualityResult:
    """Validate content quality of a single WebSocket event.
    
    Args:
        event: WebSocket event to validate
        strict_mode: Whether to apply strict business value requirements
        
    Returns:
        ContentQualityResult with validation details
    """
    validator = ContentQualityValidator(
        user_id=event.data.get("user_id", "test_user"),
        session_id=f"single_validation_{int(time.time())}",
        strict_mode=strict_mode
    )
    
    return validator.validate_event_content(event)


def assert_content_delivers_business_value(events: List[WebSocketEvent], min_score: float = 0.7) -> Dict[str, Any]:
    """Assert that event content delivers business value above minimum threshold.
    
    Args:
        events: List of WebSocket events to validate
        min_score: Minimum business value score required
        
    Returns:
        Validation summary
        
    Raises:
        AssertionError: If business value requirements not met
    """
    validator = ContentQualityValidator(
        user_id="test_user",
        session_id=f"batch_validation_{int(time.time())}",
        strict_mode=True
    )
    
    for event in events:
        validator.validate_event_content(event)
    
    validator.assert_business_value_preserved(min_score_threshold=min_score)
    return validator.get_validation_summary()