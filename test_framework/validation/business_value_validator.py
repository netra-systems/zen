#!/usr/bin/env python
"""
Business Value Validator - MISSION CRITICAL for Revenue Protection

Business Value Justification:
- Segment: Platform/Internal - Business value validation infrastructure
- Business Goal: Ensure WebSocket events deliver measurable business value and drive conversions
- Value Impact: Validates that chat interactions deliver the substantive value that drives $500K+ ARR
- Revenue Impact: Protects against value degradation that causes user churn and lost revenue

CRITICAL REQUIREMENTS FROM CLAUDE.MD:
- WebSocket events enable substantive chat interactions - they serve business goal of delivering AI value
- Tests must FAIL HARD when business value is compromised
- User engagement and trust must be preserved through meaningful interactions
- Revenue-critical event flows must be validated end-to-end

BUSINESS VALUE MEASUREMENT CRITERIA:
1. User Trust Preservation - Events must build/maintain trust in AI capabilities
2. Engagement Maintenance - Events must keep users actively engaged
3. Value Delivery - Events must deliver actionable insights and solutions
4. Conversion Potential - Events must drive users toward paid plans
5. Retention Impact - Events must encourage continued platform usage

@compliance CLAUDE.md - WebSocket events enable substantive chat interactions
@compliance SPEC/core.xml - Business value critical for platform success
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
import statistics

from test_framework.ssot.real_websocket_test_client import WebSocketEvent

logger = logging.getLogger(__name__)


class BusinessValueImpact(str, Enum):
    """Business value impact levels."""
    REVENUE_CRITICAL = "revenue_critical"    # Direct revenue impact, conversion driver
    HIGH_VALUE = "high_value"               # Strong engagement, trust building
    MEDIUM_VALUE = "medium_value"           # Moderate value, maintains interest
    LOW_VALUE = "low_value"                # Minimal value, basic functionality
    NO_VALUE = "no_value"                  # No measurable business value
    NEGATIVE_VALUE = "negative_value"       # Damages trust, reduces conversions


class UserEngagementLevel(str, Enum):
    """User engagement levels for business measurement."""
    HIGHLY_ENGAGED = "highly_engaged"       # User actively interested, likely to convert
    ENGAGED = "engaged"                     # User following along, staying attentive
    NEUTRAL = "neutral"                     # User passively waiting, not disengaged
    DISENGAGING = "disengaging"            # User losing interest, may abandon
    ABANDONED = "abandoned"                 # User likely to leave platform


class ConversionFactor(str, Enum):
    """Factors that influence user conversion to paid plans."""
    INTELLIGENCE_DEMONSTRATION = "intelligence_demonstration"    # AI shows smart capabilities
    PROBLEM_SOLVING = "problem_solving"                         # AI solves real user problems
    TIME_SAVINGS = "time_savings"                              # AI saves user significant time
    INSIGHTS_DELIVERY = "insights_delivery"                    # AI provides valuable insights
    TRANSPARENCY = "transparency"                              # AI shows how it works
    RELIABILITY = "reliability"                               # AI works consistently well
    PERSONALIZATION = "personalization"                       # AI adapts to user needs


@dataclass
class BusinessValueMetric:
    """Metric for measuring business value."""
    name: str
    value: float                    # 0.0-1.0 score
    weight: float = 1.0            # Importance weighting
    description: str = ""
    conversion_impact: float = 0.0  # Direct impact on conversion probability


@dataclass
class UserEngagementMetrics:
    """Comprehensive user engagement metrics."""
    attention_score: float = 0.0           # How well events hold user attention
    trust_score: float = 0.0               # User trust in AI capabilities  
    satisfaction_score: float = 0.0        # User satisfaction with responses
    learning_score: float = 0.0            # How much user learns from AI
    efficiency_score: float = 0.0          # How much time AI saves user
    personalization_score: float = 0.0     # How well AI adapts to user
    
    def overall_engagement(self) -> float:
        """Calculate overall engagement score."""
        scores = [
            self.attention_score, self.trust_score, self.satisfaction_score,
            self.learning_score, self.efficiency_score, self.personalization_score
        ]
        return statistics.mean(scores) if scores else 0.0


@dataclass
class ConversionPotential:
    """Analysis of conversion potential from event sequence."""
    probability: float = 0.0               # 0.0-1.0 likelihood of conversion
    key_factors: List[ConversionFactor] = field(default_factory=list)
    blocking_issues: List[str] = field(default_factory=list)
    revenue_impact: float = 0.0            # Estimated monthly revenue impact
    user_segment: str = "unknown"          # Free, Early, Mid, Enterprise


@dataclass
class BusinessValueViolation:
    """Represents a violation of business value requirements."""
    event_type: str
    violation_type: str
    impact_level: BusinessValueImpact
    description: str
    business_consequence: str
    revenue_impact: float = 0.0            # Estimated negative revenue impact
    user_segment_affected: str = "all"
    remediation_suggestion: str = ""


@dataclass
class BusinessValueResult:
    """Result of business value validation."""
    session_id: str
    total_events: int
    business_value_score: float = 0.0      # Overall business value score (0.0-1.0)
    engagement_metrics: UserEngagementMetrics = field(default_factory=UserEngagementMetrics)
    conversion_potential: ConversionPotential = field(default_factory=ConversionPotential)
    violations: List[BusinessValueViolation] = field(default_factory=list)
    value_metrics: List[BusinessValueMetric] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class BusinessValueValidator:
    """
    MISSION CRITICAL: Business Value Validator for Revenue Protection
    
    This validator ensures WebSocket events deliver measurable business value that
    drives user engagement, builds trust, and increases conversion to paid plans.
    
    CRITICAL FEATURES:
    - Measures substantive value delivery through event analysis
    - Calculates conversion potential and revenue impact
    - Validates user engagement preservation
    - Identifies business value degradation risks
    - Fails hard when revenue-critical value is compromised
    """
    
    # Business value patterns that drive conversions
    HIGH_VALUE_PATTERNS = {
        "intelligence_indicators": [
            r"analyzed\s+\d+\s+data\s+points",
            r"identified\s+key\s+(patterns|trends|insights)",
            r"cross-referenced\s+multiple\s+sources",
            r"synthesized\s+(information|data|findings)",
            r"generated\s+\d+\s+recommendations",
            r"processed\s+(complex|large|comprehensive)\s+dataset"
        ],
        "problem_solving_indicators": [
            r"solved?\s+(your|the)\s+problem",
            r"found\s+(solution|answer|resolution)",
            r"addressed\s+(your|the)\s+(concern|issue|question)",
            r"provided\s+(complete|comprehensive)\s+solution",
            r"resolved\s+(all|multiple)\s+aspects"
        ],
        "time_saving_indicators": [
            r"saved?\s+you\s+\d+\s+(hours?|minutes?)",
            r"automated\s+the\s+(process|task|workflow)",
            r"eliminated\s+manual\s+(work|steps|effort)",
            r"streamlined\s+(your|the)\s+(process|workflow)",
            r"reduced\s+(processing|research|analysis)\s+time"
        ],
        "insights_indicators": [
            r"key\s+(insight|finding|discovery)",
            r"important\s+(trend|pattern|correlation)",
            r"significant\s+(difference|change|impact)",
            r"actionable\s+(recommendation|insight|advice)",
            r"strategic\s+(implication|opportunity|advantage)"
        ]
    }
    
    # Patterns that damage business value
    VALUE_DAMAGING_PATTERNS = [
        r"could\s+not\s+(complete|finish|process)",
        r"(failed|unable)\s+to\s+(access|retrieve|process)",
        r"(error|exception|timeout)\s+occurred",
        r"please\s+try\s+again\s+later",
        r"service\s+(unavailable|down|maintenance)",
        r"(generic|standard|default)\s+response",
        r"no\s+(results|data|information)\s+found"
    ]
    
    # User segments and their conversion characteristics
    USER_SEGMENTS = {
        "free": {"conversion_threshold": 0.6, "monthly_value": 0.0, "upgrade_potential": 29.99},
        "early": {"conversion_threshold": 0.7, "monthly_value": 29.99, "upgrade_potential": 99.99},
        "mid": {"conversion_threshold": 0.8, "monthly_value": 99.99, "upgrade_potential": 299.99},
        "enterprise": {"conversion_threshold": 0.9, "monthly_value": 299.99, "upgrade_potential": 999.99}
    }
    
    def __init__(self, user_id: str, session_id: str, user_segment: str = "free", strict_mode: bool = True):
        """Initialize business value validator.
        
        Args:
            user_id: User ID for validation context
            session_id: Session ID for tracking
            user_segment: User segment (free, early, mid, enterprise)
            strict_mode: Whether to apply strict business value requirements
        """
        self.user_id = user_id
        self.session_id = session_id
        self.user_segment = user_segment.lower()
        self.strict_mode = strict_mode
        
        # Validation tracking
        self.events_processed = 0
        self.violations: List[BusinessValueViolation] = []
        self.value_metrics: List[BusinessValueMetric] = []
        
        # Business metrics
        self.intelligence_demonstrations = 0
        self.problem_solving_instances = 0
        self.time_saving_actions = 0
        self.insights_delivered = 0
        self.transparency_events = 0
        self.personalization_events = 0
        
        # Negative indicators
        self.error_events = 0
        self.generic_responses = 0
        self.value_damaging_events = 0
        
        logger.info(f"BusinessValueValidator initialized for {user_segment} user {user_id}")
    
    def validate_event_business_value(self, event: WebSocketEvent, context: Optional[Dict[str, Any]] = None) -> BusinessValueResult:
        """Validate the business value delivered by a WebSocket event.
        
        Args:
            event: WebSocket event to validate
            context: Additional context for validation
            
        Returns:
            BusinessValueResult with comprehensive business analysis
        """
        self.events_processed += 1
        
        # Extract content for analysis
        content = self._extract_event_content(event)
        
        # Analyze business value components
        value_metrics = self._analyze_value_delivery(event, content)
        engagement_metrics = self._analyze_user_engagement(event, content)
        conversion_factors = self._analyze_conversion_potential(event, content)
        
        # Detect violations
        violations = self._detect_business_value_violations(event, content)
        self.violations.extend(violations)
        
        # Update cumulative metrics
        self._update_business_metrics(event, content)
        
        # Calculate overall scores
        business_value_score = self._calculate_business_value_score(value_metrics)
        conversion_potential = self._calculate_conversion_potential(conversion_factors)
        
        # Generate recommendations
        recommendations = self._generate_business_recommendations(violations, value_metrics)
        
        result = BusinessValueResult(
            session_id=self.session_id,
            total_events=self.events_processed,
            business_value_score=business_value_score,
            engagement_metrics=engagement_metrics,
            conversion_potential=conversion_potential,
            violations=violations,
            value_metrics=value_metrics,
            recommendations=recommendations
        )
        
        # Log critical business value issues
        critical_violations = [v for v in violations if v.impact_level in [BusinessValueImpact.REVENUE_CRITICAL, BusinessValueImpact.NEGATIVE_VALUE]]
        for violation in critical_violations:
            logger.error(f"🚨 BUSINESS VALUE VIOLATION: {violation.description}")
        
        return result
    
    def _extract_event_content(self, event: WebSocketEvent) -> Dict[str, Any]:
        """Extract content from event for business value analysis."""
        content = {
            "text": "",
            "structured_data": event.data,
            "event_type": event.event_type,
            "user_context": event.data.get("user_id", ""),
            "timestamp": time.time()
        }
        
        # Extract meaningful text content
        text_fields = ["content", "message", "summary", "result", "description", "response"]
        for field in text_fields:
            if field in event.data and isinstance(event.data[field], str):
                content["text"] += " " + event.data[field]
        
        # Extract structured results for analysis
        if "result" in event.data and isinstance(event.data["result"], dict):
            content["structured_data"] = {**content["structured_data"], **event.data["result"]}
        
        content["text"] = content["text"].strip()
        return content
    
    def _analyze_value_delivery(self, event: WebSocketEvent, content: Dict[str, Any]) -> List[BusinessValueMetric]:
        """Analyze the business value delivered by an event."""
        metrics = []
        text_content = content["text"].lower()
        
        # Intelligence demonstration analysis
        intelligence_score = 0.0
        for pattern in self.HIGH_VALUE_PATTERNS["intelligence_indicators"]:
            if re.search(pattern, text_content, re.IGNORECASE):
                intelligence_score += 0.2
                self.intelligence_demonstrations += 1
        
        if intelligence_score > 0:
            metrics.append(BusinessValueMetric(
                name="intelligence_demonstration",
                value=min(1.0, intelligence_score),
                weight=1.5,  # High weight for conversion
                description="AI demonstrates intelligent analysis capabilities",
                conversion_impact=0.25  # 25% boost to conversion probability
            ))
        
        # Problem solving analysis
        problem_solving_score = 0.0
        for pattern in self.HIGH_VALUE_PATTERNS["problem_solving_indicators"]:
            if re.search(pattern, text_content, re.IGNORECASE):
                problem_solving_score += 0.3
                self.problem_solving_instances += 1
        
        if problem_solving_score > 0:
            metrics.append(BusinessValueMetric(
                name="problem_solving",
                value=min(1.0, problem_solving_score),
                weight=2.0,  # Highest weight - direct value delivery
                description="AI solves real user problems",
                conversion_impact=0.35  # 35% boost to conversion
            ))
        
        # Time savings analysis
        time_savings_score = 0.0
        for pattern in self.HIGH_VALUE_PATTERNS["time_saving_indicators"]:
            if re.search(pattern, text_content, re.IGNORECASE):
                time_savings_score += 0.25
                self.time_saving_actions += 1
        
        if time_savings_score > 0:
            metrics.append(BusinessValueMetric(
                name="time_savings",
                value=min(1.0, time_savings_score),
                weight=1.3,
                description="AI saves user time and effort",
                conversion_impact=0.20
            ))
        
        # Insights delivery analysis
        insights_score = 0.0
        for pattern in self.HIGH_VALUE_PATTERNS["insights_indicators"]:
            if re.search(pattern, text_content, re.IGNORECASE):
                insights_score += 0.2
                self.insights_delivered += 1
        
        if insights_score > 0:
            metrics.append(BusinessValueMetric(
                name="insights_delivery",
                value=min(1.0, insights_score),
                weight=1.4,
                description="AI provides valuable insights",
                conversion_impact=0.22
            ))
        
        # Transparency analysis (showing work builds trust)
        transparency_score = 0.0
        if event.event_type in ["tool_executing", "agent_thinking"]:
            if text_content and len(text_content) > 20:  # Meaningful progress updates
                transparency_score = 0.7
                self.transparency_events += 1
        
        if transparency_score > 0:
            metrics.append(BusinessValueMetric(
                name="transparency",
                value=transparency_score,
                weight=1.0,
                description="AI shows its work process transparently",
                conversion_impact=0.15
            ))
        
        return metrics
    
    def _analyze_user_engagement(self, event: WebSocketEvent, content: Dict[str, Any]) -> UserEngagementMetrics:
        """Analyze user engagement factors from event."""
        metrics = UserEngagementMetrics()
        text_content = content["text"].lower()
        
        # Attention score - how likely to hold user attention
        if event.event_type in ["agent_thinking", "tool_executing"]:
            if len(text_content) > 10 and not re.search(r"^(thinking|processing|working)\.{3}$", text_content):
                metrics.attention_score = 0.8  # Specific progress holds attention
            else:
                metrics.attention_score = 0.4  # Generic progress less engaging
        elif event.event_type in ["tool_completed", "agent_completed"]:
            if len(text_content) > 30:
                metrics.attention_score = 0.9  # Substantial results very engaging
            else:
                metrics.attention_score = 0.5  # Brief results moderately engaging
        
        # Trust score - how much this builds trust in AI
        if any(re.search(pattern, text_content, re.IGNORECASE) for pattern in self.HIGH_VALUE_PATTERNS["intelligence_indicators"]):
            metrics.trust_score = 0.9
        elif any(re.search(pattern, text_content, re.IGNORECASE) for pattern in self.VALUE_DAMAGING_PATTERNS):
            metrics.trust_score = 0.2  # Errors damage trust
        else:
            metrics.trust_score = 0.6  # Neutral
        
        # Satisfaction score - user satisfaction with response quality
        if event.event_type == "agent_completed":
            if any(re.search(pattern, text_content, re.IGNORECASE) for pattern in self.HIGH_VALUE_PATTERNS["problem_solving_indicators"]):
                metrics.satisfaction_score = 0.95
            elif len(text_content) > 50:
                metrics.satisfaction_score = 0.75
            else:
                metrics.satisfaction_score = 0.5
        else:
            metrics.satisfaction_score = 0.6  # Progress events moderately satisfying
        
        # Learning score - how much user learns from AI
        if any(re.search(pattern, text_content, re.IGNORECASE) for pattern in self.HIGH_VALUE_PATTERNS["insights_indicators"]):
            metrics.learning_score = 0.8
        else:
            metrics.learning_score = 0.4
        
        # Efficiency score - how much time/effort AI saves
        if any(re.search(pattern, text_content, re.IGNORECASE) for pattern in self.HIGH_VALUE_PATTERNS["time_saving_indicators"]):
            metrics.efficiency_score = 0.9
        elif event.event_type in ["tool_executing", "tool_completed"]:
            metrics.efficiency_score = 0.7  # Tool usage implies efficiency
        else:
            metrics.efficiency_score = 0.5
        
        # Personalization score - how well AI adapts to this user
        user_references = len(re.findall(r"\b(you|your|yours)\b", text_content, re.IGNORECASE))
        if user_references > 2:
            metrics.personalization_score = 0.8
            self.personalization_events += 1
        elif user_references > 0:
            metrics.personalization_score = 0.6
        else:
            metrics.personalization_score = 0.3
        
        return metrics
    
    def _analyze_conversion_potential(self, event: WebSocketEvent, content: Dict[str, Any]) -> List[ConversionFactor]:
        """Analyze factors that drive conversion to paid plans."""
        factors = []
        text_content = content["text"].lower()
        
        # Intelligence demonstration drives conversions
        if any(re.search(pattern, text_content, re.IGNORECASE) for pattern in self.HIGH_VALUE_PATTERNS["intelligence_indicators"]):
            factors.append(ConversionFactor.INTELLIGENCE_DEMONSTRATION)
        
        # Problem solving directly drives conversions
        if any(re.search(pattern, text_content, re.IGNORECASE) for pattern in self.HIGH_VALUE_PATTERNS["problem_solving_indicators"]):
            factors.append(ConversionFactor.PROBLEM_SOLVING)
        
        # Time savings show clear value
        if any(re.search(pattern, text_content, re.IGNORECASE) for pattern in self.HIGH_VALUE_PATTERNS["time_saving_indicators"]):
            factors.append(ConversionFactor.TIME_SAVINGS)
        
        # Insights create aha moments
        if any(re.search(pattern, text_content, re.IGNORECASE) for pattern in self.HIGH_VALUE_PATTERNS["insights_indicators"]):
            factors.append(ConversionFactor.INSIGHTS_DELIVERY)
        
        # Transparency builds trust
        if event.event_type in ["tool_executing", "agent_thinking"] and len(text_content) > 20:
            factors.append(ConversionFactor.TRANSPARENCY)
        
        # Personalization shows AI adapts to user
        if len(re.findall(r"\b(you|your|yours)\b", text_content, re.IGNORECASE)) > 2:
            factors.append(ConversionFactor.PERSONALIZATION)
        
        return factors
    
    def _detect_business_value_violations(self, event: WebSocketEvent, content: Dict[str, Any]) -> List[BusinessValueViolation]:
        """Detect violations that damage business value."""
        violations = []
        text_content = content["text"].lower()
        
        # Check for value-damaging patterns
        for pattern in self.VALUE_DAMAGING_PATTERNS:
            if re.search(pattern, text_content, re.IGNORECASE):
                self.value_damaging_events += 1
                violations.append(BusinessValueViolation(
                    event_type=event.event_type,
                    violation_type="value_damaging_content",
                    impact_level=BusinessValueImpact.NEGATIVE_VALUE,
                    description=f"Event contains value-damaging content: reduces user trust",
                    business_consequence="Users lose confidence in AI capabilities, reducing conversion probability",
                    revenue_impact=self._estimate_revenue_impact(BusinessValueImpact.NEGATIVE_VALUE),
                    remediation_suggestion="Improve error handling and provide constructive alternatives"
                ))
        
        # Check for empty/minimal value events
        if event.event_type in ["agent_completed", "tool_completed"] and len(text_content) < 10:
            violations.append(BusinessValueViolation(
                event_type=event.event_type,
                violation_type="minimal_value_delivery",
                impact_level=BusinessValueImpact.LOW_VALUE,
                description="Completion event delivers minimal substantive value",
                business_consequence="Users don't see clear value from AI, reducing willingness to pay",
                revenue_impact=self._estimate_revenue_impact(BusinessValueImpact.LOW_VALUE),
                remediation_suggestion="Ensure completion events summarize clear value delivered"
            ))
        
        # Check for generic responses that damage trust
        generic_patterns = [r"^(ok|done|finished|completed)\.?$", r"^task\s+completed\.?$", r"^processing\.{3}$"]
        for pattern in generic_patterns:
            if re.search(pattern, text_content, re.IGNORECASE):
                self.generic_responses += 1
                violations.append(BusinessValueViolation(
                    event_type=event.event_type,
                    violation_type="generic_response",
                    impact_level=BusinessValueImpact.LOW_VALUE,
                    description="Generic response reduces perceived AI intelligence",
                    business_consequence="Users question AI capability, reducing conversion likelihood",
                    revenue_impact=self._estimate_revenue_impact(BusinessValueImpact.LOW_VALUE),
                    remediation_suggestion="Provide specific, contextual responses that demonstrate intelligence"
                ))
        
        return violations
    
    def _update_business_metrics(self, event: WebSocketEvent, content: Dict[str, Any]):
        """Update cumulative business metrics."""
        if any(re.search(pattern, content["text"], re.IGNORECASE) for pattern in self.VALUE_DAMAGING_PATTERNS):
            self.error_events += 1
    
    def _calculate_business_value_score(self, metrics: List[BusinessValueMetric]) -> float:
        """Calculate overall business value score."""
        if not metrics:
            return 0.0
        
        weighted_sum = sum(metric.value * metric.weight for metric in metrics)
        total_weight = sum(metric.weight for metric in metrics)
        
        base_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # Apply penalties for negative indicators
        penalty = 0.0
        if self.error_events > 0:
            penalty += 0.2 * (self.error_events / self.events_processed)
        if self.generic_responses > 0:
            penalty += 0.1 * (self.generic_responses / self.events_processed)
        
        final_score = max(0.0, base_score - penalty)
        return min(1.0, final_score)
    
    def _calculate_conversion_potential(self, factors: List[ConversionFactor]) -> ConversionPotential:
        """Calculate conversion potential based on value factors."""
        # Base probability based on user segment
        segment_config = self.USER_SEGMENTS.get(self.user_segment, self.USER_SEGMENTS["free"])
        base_probability = 0.1  # 10% base conversion rate
        
        # Boost probability for each conversion factor
        factor_boosts = {
            ConversionFactor.PROBLEM_SOLVING: 0.35,
            ConversionFactor.INTELLIGENCE_DEMONSTRATION: 0.25,
            ConversionFactor.TIME_SAVINGS: 0.20,
            ConversionFactor.INSIGHTS_DELIVERY: 0.22,
            ConversionFactor.TRANSPARENCY: 0.15,
            ConversionFactor.PERSONALIZATION: 0.18
        }
        
        probability = base_probability
        for factor in set(factors):  # Remove duplicates
            probability += factor_boosts.get(factor, 0.05)
        
        # Apply penalties for negative indicators
        if self.error_events > 0:
            probability *= 0.7  # 30% reduction for errors
        if self.generic_responses > 0:
            probability *= 0.8  # 20% reduction for generic responses
        
        probability = min(0.95, probability)  # Cap at 95%
        
        # Calculate revenue impact
        monthly_value = segment_config["monthly_value"]
        upgrade_potential = segment_config["upgrade_potential"]
        revenue_impact = (probability * upgrade_potential) - ((1 - probability) * monthly_value * 0.1)  # Churn risk
        
        # Identify blocking issues
        blocking_issues = []
        if self.error_events > 0:
            blocking_issues.append(f"{self.error_events} error events damage user confidence")
        if self.generic_responses > 0:
            blocking_issues.append(f"{self.generic_responses} generic responses reduce perceived value")
        if not factors:
            blocking_issues.append("No clear conversion factors demonstrated")
        
        return ConversionPotential(
            probability=probability,
            key_factors=list(set(factors)),
            blocking_issues=blocking_issues,
            revenue_impact=revenue_impact,
            user_segment=self.user_segment
        )
    
    def _generate_business_recommendations(self, violations: List[BusinessValueViolation], metrics: List[BusinessValueMetric]) -> List[str]:
        """Generate actionable business recommendations."""
        recommendations = []
        
        # Address violations
        if violations:
            high_impact_violations = [v for v in violations if v.impact_level in [BusinessValueImpact.REVENUE_CRITICAL, BusinessValueImpact.NEGATIVE_VALUE]]
            if high_impact_violations:
                recommendations.append("CRITICAL: Address high-impact violations immediately to prevent revenue loss")
        
        # Improve value delivery
        value_scores = {metric.name: metric.value for metric in metrics}
        if value_scores.get("problem_solving", 0) < 0.5:
            recommendations.append("Improve problem-solving demonstration to drive conversions")
        if value_scores.get("intelligence_demonstration", 0) < 0.5:
            recommendations.append("Enhance AI intelligence visibility to build user confidence")
        if value_scores.get("transparency", 0) < 0.5:
            recommendations.append("Increase process transparency to build user trust")
        
        # Segment-specific recommendations
        if self.user_segment == "free":
            recommendations.append("Focus on demonstrating clear value to drive upgrade to paid plan")
        elif self.user_segment in ["early", "mid"]:
            recommendations.append("Showcase advanced features to encourage tier upgrade")
        
        return recommendations
    
    def _estimate_revenue_impact(self, impact_level: BusinessValueImpact) -> float:
        """Estimate revenue impact of business value violation."""
        segment_config = self.USER_SEGMENTS.get(self.user_segment, self.USER_SEGMENTS["free"])
        monthly_value = segment_config["monthly_value"]
        upgrade_potential = segment_config["upgrade_potential"]
        
        # Impact multipliers based on severity
        impact_multipliers = {
            BusinessValueImpact.REVENUE_CRITICAL: -0.5,    # 50% revenue loss
            BusinessValueImpact.NEGATIVE_VALUE: -0.3,      # 30% revenue loss
            BusinessValueImpact.NO_VALUE: -0.1,            # 10% revenue loss
            BusinessValueImpact.LOW_VALUE: -0.05,          # 5% revenue loss
        }
        
        multiplier = impact_multipliers.get(impact_level, 0)
        return multiplier * upgrade_potential
    
    def validate_session_business_value(self, events: List[WebSocketEvent]) -> BusinessValueResult:
        """Validate business value for an entire event session.
        
        Args:
            events: List of WebSocket events to validate
            
        Returns:
            BusinessValueResult with comprehensive analysis
        """
        all_metrics = []
        all_violations = []
        conversion_factors = []
        
        for event in events:
            result = self.validate_event_business_value(event)
            all_metrics.extend(result.value_metrics)
            all_violations.extend(result.violations)
            conversion_factors.extend(result.conversion_potential.key_factors)
        
        # Calculate session-level scores
        session_business_score = self._calculate_business_value_score(all_metrics)
        session_conversion_potential = self._calculate_conversion_potential(conversion_factors)
        
        # Calculate engagement metrics across all events
        session_engagement = UserEngagementMetrics()
        if events:
            # Average engagement across all events (simplified)
            session_engagement.attention_score = 0.7  # Based on event variety and content
            session_engagement.trust_score = max(0.2, 0.9 - (self.error_events / len(events)))
            session_engagement.satisfaction_score = max(0.3, 0.8 - (self.generic_responses / len(events)))
            session_engagement.learning_score = min(1.0, self.insights_delivered / len(events) * 2)
            session_engagement.efficiency_score = min(1.0, self.time_saving_actions / len(events) * 3)
            session_engagement.personalization_score = min(1.0, self.personalization_events / len(events) * 2)
        
        return BusinessValueResult(
            session_id=self.session_id,
            total_events=len(events),
            business_value_score=session_business_score,
            engagement_metrics=session_engagement,
            conversion_potential=session_conversion_potential,
            violations=all_violations,
            value_metrics=all_metrics,
            recommendations=self._generate_business_recommendations(all_violations, all_metrics)
        )
    
    def assert_business_value_standards_met(self, min_value_score: float = 0.6, max_abandonment_risk: float = 0.3) -> None:
        """Assert that business value standards are met.
        
        Args:
            min_value_score: Minimum business value score required
            max_abandonment_risk: Maximum acceptable abandonment risk
            
        Raises:
            AssertionError: If business value standards are not met
        """
        if self.events_processed == 0:
            raise AssertionError("No events processed for business value validation")
        
        # Calculate current metrics
        dummy_event = WebSocketEvent(event_type="validation", data={"user_id": self.user_id})
        result = self.validate_event_business_value(dummy_event)
        
        failures = []
        critical_issues = []
        
        # Check business value score
        if result.business_value_score < min_value_score:
            failures.append(f"Business value score {result.business_value_score:.2f} < required {min_value_score:.2f}")
        
        # Check conversion potential
        if result.conversion_potential.probability < 0.2:  # Less than 20% conversion chance
            failures.append(f"Conversion probability {result.conversion_potential.probability:.1%} too low for business viability")
        
        # Check for critical violations
        critical_violations = [v for v in self.violations if v.impact_level in [BusinessValueImpact.REVENUE_CRITICAL, BusinessValueImpact.NEGATIVE_VALUE]]
        if critical_violations:
            critical_issues.append(f"{len(critical_violations)} CRITICAL business value violations")
        
        # Check engagement preservation
        overall_engagement = result.engagement_metrics.overall_engagement()
        if overall_engagement < 0.5:
            critical_issues.append(f"User engagement {overall_engagement:.1%} below sustainable threshold")
        
        if critical_issues or failures:
            error_parts = []
            
            if critical_issues:
                error_parts.append("CRITICAL BUSINESS VALUE ISSUES:")
                error_parts.extend(critical_issues)
            
            if failures:
                error_parts.append("BUSINESS VALUE FAILURES:")
                error_parts.extend(failures)
            
            # Add context about violations
            if critical_violations:
                error_parts.append("TOP VIOLATIONS:")
                for v in critical_violations[:3]:
                    error_parts.append(f"- {v.description} (Impact: ${v.revenue_impact:.0f})")
            
            error_message = (
                "🚨 BUSINESS VALUE FAILURE - WebSocket events not delivering revenue-critical value!\n"
                + "\n".join(error_parts) + "\n\n"
                f"Session stats: {self.events_processed} events, {len(self.violations)} violations\n"
                f"User segment: {self.user_segment}, Conversion: {result.conversion_potential.probability:.1%}\n"
                "This will result in user churn and revenue loss."
            )
            
            logger.error(error_message)
            raise AssertionError(error_message)
    
    def get_business_value_summary(self) -> Dict[str, Any]:
        """Get comprehensive business value summary.
        
        Returns:
            Dictionary with business metrics and analysis
        """
        if self.events_processed == 0:
            return {"error": "No events processed"}
        
        # Calculate summary metrics
        dummy_event = WebSocketEvent(event_type="summary", data={"user_id": self.user_id})
        result = self.validate_event_business_value(dummy_event)
        
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "user_segment": self.user_segment,
            "events_processed": self.events_processed,
            "business_value_score": result.business_value_score,
            "conversion_probability": result.conversion_potential.probability,
            "estimated_revenue_impact": result.conversion_potential.revenue_impact,
            "engagement_metrics": {
                "overall_engagement": result.engagement_metrics.overall_engagement(),
                "attention_score": result.engagement_metrics.attention_score,
                "trust_score": result.engagement_metrics.trust_score,
                "satisfaction_score": result.engagement_metrics.satisfaction_score
            },
            "business_indicators": {
                "intelligence_demonstrations": self.intelligence_demonstrations,
                "problem_solving_instances": self.problem_solving_instances,
                "time_saving_actions": self.time_saving_actions,
                "insights_delivered": self.insights_delivered,
                "transparency_events": self.transparency_events,
                "personalization_events": self.personalization_events
            },
            "negative_indicators": {
                "error_events": self.error_events,
                "generic_responses": self.generic_responses,
                "value_damaging_events": self.value_damaging_events
            },
            "conversion_factors": [factor.value for factor in result.conversion_potential.key_factors],
            "blocking_issues": result.conversion_potential.blocking_issues,
            "recommendations": result.recommendations,
            "total_violations": len(self.violations),
            "revenue_at_risk": sum(v.revenue_impact for v in self.violations if v.revenue_impact < 0)
        }


# Convenience functions

def validate_business_value_delivery(events: List[WebSocketEvent], user_segment: str = "free") -> BusinessValueValidator:
    """Validate business value delivery for a sequence of events.
    
    Args:
        events: List of WebSocket events to validate
        user_segment: User segment for business context
        
    Returns:
        BusinessValueValidator with comprehensive results
    """
    user_id = events[0].data.get("user_id", "test_user") if events else "test_user"
    session_id = f"business_validation_{int(time.time())}"
    
    validator = BusinessValueValidator(
        user_id=user_id,
        session_id=session_id,
        user_segment=user_segment,
        strict_mode=True
    )
    
    validator.validate_session_business_value(events)
    validator.assert_business_value_standards_met()
    
    return validator


def assert_revenue_protection(events: List[WebSocketEvent], min_conversion_rate: float = 0.3) -> Dict[str, Any]:
    """Assert that events protect revenue through business value delivery.
    
    Args:
        events: List of WebSocket events to validate
        min_conversion_rate: Minimum conversion rate required for revenue protection
        
    Returns:
        Business value summary
        
    Raises:
        AssertionError: If revenue protection requirements not met
    """
    validator = validate_business_value_delivery(events)
    summary = validator.get_business_value_summary()
    
    if summary.get("conversion_probability", 0) < min_conversion_rate:
        raise AssertionError(
            f"Revenue protection FAILED: Conversion probability {summary['conversion_probability']:.1%} < required {min_conversion_rate:.1%}"
        )
    
    return summary