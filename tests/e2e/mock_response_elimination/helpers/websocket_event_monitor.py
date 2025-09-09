"""
WebSocket Event Monitor

Helper utility to monitor and validate WebSocket events for authenticity
during mock response elimination tests. Ensures WebSocket events accurately
communicate AI processing authenticity to users.

Business Value: Protects user trust by ensuring WebSocket events honestly
represent whether users are receiving authentic AI responses or fallbacks.
"""

import asyncio
import logging
import time
import json
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(Enum):
    """WebSocket event types for AI interactions."""
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking" 
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    AGENT_COMPLETED = "agent_completed"
    SYSTEM_STATUS = "system_status"
    ERROR_NOTIFICATION = "error_notification"


@dataclass
class WebSocketEventCapture:
    """Captured WebSocket event with metadata."""
    timestamp: float
    event_type: str
    data: Dict[str, Any]
    sequence_number: int
    processing_time_ms: Optional[float] = None
    authenticity_indicators: Dict[str, Any] = field(default_factory=dict)
    business_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthenticityAnalysis:
    """Analysis of event authenticity indicators."""
    is_authentic_processing: bool
    authenticity_score: float
    misleading_indicators: List[str]
    trust_violations: List[str]
    business_impact_assessment: str
    recommendations: List[str]


class WebSocketEventMonitor:
    """
    Monitor WebSocket events for authenticity and business value protection.
    
    This class validates that WebSocket events accurately represent the
    authenticity of AI processing and do not mislead users about whether
    they're receiving genuine AI responses or fallback responses.
    """
    
    def __init__(self):
        self.event_captures: List[WebSocketEventCapture] = []
        self.sequence_counter = 0
        self.monitoring_active = False
        self.start_time = None
        
        # Expected event sequence for authentic AI processing
        self.authentic_ai_sequence = [
            EventType.AGENT_STARTED,
            EventType.AGENT_THINKING,
            EventType.TOOL_EXECUTING,  # Optional
            EventType.TOOL_COMPLETED,  # Optional  
            EventType.AGENT_COMPLETED
        ]
    
    def start_monitoring(self) -> None:
        """Start monitoring WebSocket events."""
        self.monitoring_active = True
        self.start_time = time.time()
        self.event_captures.clear()
        self.sequence_counter = 0
        logger.info("WebSocket event monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop monitoring WebSocket events."""
        self.monitoring_active = False
        logger.info(f"WebSocket event monitoring stopped. Captured {len(self.event_captures)} events")
    
    def capture_event(self, event: Dict[str, Any]) -> WebSocketEventCapture:
        """
        Capture and analyze a WebSocket event.
        
        Args:
            event: WebSocket event dictionary
            
        Returns:
            Captured event with analysis metadata
        """
        if not self.monitoring_active:
            return None
        
        self.sequence_counter += 1
        timestamp = time.time()
        
        event_type = event.get("type", "unknown")
        event_data = event.get("data", {})
        
        # Extract authenticity indicators
        authenticity_indicators = {
            "llm_api_called": event_data.get("llm_api_called", False),
            "tool_execution": event_data.get("tool_execution", False),
            "is_fallback": event_data.get("is_fallback", False),
            "processing_authentic": event_data.get("processing_authentic", None),
            "confidence_score": event_data.get("confidence_score"),
            "data_source": event_data.get("data_source", "unknown")
        }
        
        # Extract business context
        business_context = {
            "user_subscription": event_data.get("user_subscription"),
            "arr_value": event_data.get("arr_value"),
            "business_critical": event_data.get("business_critical", False),
            "decision_impact": event_data.get("decision_impact"),
            "financial_implications": event_data.get("financial_implications")
        }
        
        # Calculate processing time if available
        processing_time_ms = None
        if self.start_time:
            processing_time_ms = (timestamp - self.start_time) * 1000
        
        capture = WebSocketEventCapture(
            timestamp=timestamp,
            event_type=event_type,
            data=event_data,
            sequence_number=self.sequence_counter,
            processing_time_ms=processing_time_ms,
            authenticity_indicators=authenticity_indicators,
            business_context=business_context
        )
        
        self.event_captures.append(capture)
        
        logger.debug(f"Captured event #{self.sequence_counter}: {event_type}")
        
        return capture
    
    def analyze_event_authenticity(
        self,
        final_response_content: str = "",
        expected_authentic: bool = True
    ) -> AuthenticityAnalysis:
        """
        Analyze captured events for authenticity and trust violations.
        
        Args:
            final_response_content: Final response content to check for fallbacks
            expected_authentic: Whether authentic processing was expected
            
        Returns:
            Comprehensive authenticity analysis
        """
        if not self.event_captures:
            return AuthenticityAnalysis(
                is_authentic_processing=False,
                authenticity_score=0.0,
                misleading_indicators=["No events captured"],
                trust_violations=["No WebSocket events sent to user"],
                business_impact_assessment="critical",
                recommendations=["Implement proper WebSocket event emission"]
            )
        
        # Analyze event sequence
        event_types = [capture.event_type for capture in self.event_captures]
        
        # Check for authentic AI processing indicators
        authentic_indicators = []
        misleading_indicators = []
        trust_violations = []
        
        # Analyze final response for fallback indicators
        is_fallback_response = self._detect_fallback_response(final_response_content)
        
        # Check for agent_thinking events
        thinking_events = [c for c in self.event_captures if c.event_type == "agent_thinking"]
        
        if thinking_events and is_fallback_response:
            misleading_indicators.append(
                f"Sent {len(thinking_events)} 'agent_thinking' events but final response was fallback"
            )
            trust_violations.append(
                "Users misled about AI processing - thinking events sent during fallback"
            )
        
        # Check for tool execution events
        tool_executing = [c for c in self.event_captures if c.event_type == "tool_executing"]
        tool_completed = [c for c in self.event_captures if c.event_type == "tool_completed"]
        
        if tool_executing and is_fallback_response:
            misleading_indicators.append(
                f"Sent {len(tool_executing)} 'tool_executing' events but no actual tools used"
            )
        
        if tool_completed and is_fallback_response:
            misleading_indicators.append(
                f"Sent {len(tool_completed)} 'tool_completed' events but tools didn't actually execute"
            )
        
        # Check completion event authenticity metadata
        completion_events = [c for c in self.event_captures if c.event_type == "agent_completed"]
        
        if completion_events:
            completion_event = completion_events[-1]
            completion_data = completion_event.data
            
            # Check for authenticity metadata
            authenticity_meta = completion_data.get("authenticity", {})
            
            if not authenticity_meta:
                trust_violations.append(
                    "No authenticity metadata provided in completion event"
                )
            else:
                claimed_authentic = authenticity_meta.get("is_authentic", True)
                claimed_fallback = authenticity_meta.get("is_fallback", False)
                
                if is_fallback_response and claimed_authentic:
                    trust_violations.append(
                        "Claimed authentic=True but response was fallback"
                    )
                
                if is_fallback_response and not claimed_fallback:
                    trust_violations.append(
                        "Fallback response but is_fallback != True in metadata"
                    )
        
        # Calculate authenticity score
        authenticity_score = self._calculate_authenticity_score(
            authentic_indicators, misleading_indicators, trust_violations
        )
        
        # Assess business impact
        business_impact = self._assess_business_impact(
            trust_violations, misleading_indicators, self.event_captures
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            trust_violations, misleading_indicators, business_impact
        )
        
        return AuthenticityAnalysis(
            is_authentic_processing=not is_fallback_response and len(trust_violations) == 0,
            authenticity_score=authenticity_score,
            misleading_indicators=misleading_indicators,
            trust_violations=trust_violations,
            business_impact_assessment=business_impact,
            recommendations=recommendations
        )
    
    def _detect_fallback_response(self, response_content: str) -> bool:
        """Detect if response content indicates a fallback response."""
        fallback_indicators = [
            "i apologize, but i encountered an error",
            "processing completed with fallback response",
            "fallback response for:",
            "fallback",
            "generic error",
            "system error"
        ]
        
        content_lower = response_content.lower()
        return any(indicator in content_lower for indicator in fallback_indicators)
    
    def _calculate_authenticity_score(
        self,
        authentic_indicators: List[str],
        misleading_indicators: List[str], 
        trust_violations: List[str]
    ) -> float:
        """Calculate authenticity score from 0.0 to 1.0."""
        
        base_score = 0.8  # Start with assumption of authenticity
        
        # Deduct for misleading indicators
        score = base_score - (len(misleading_indicators) * 0.2)
        
        # Severe penalty for trust violations
        score -= (len(trust_violations) * 0.3)
        
        # Bonus for authentic indicators
        score += (len(authentic_indicators) * 0.1)
        
        return max(0.0, min(1.0, score))
    
    def _assess_business_impact(
        self,
        trust_violations: List[str],
        misleading_indicators: List[str],
        event_captures: List[WebSocketEventCapture]
    ) -> str:
        """Assess business impact of authenticity violations."""
        
        # Check for high-value customer indicators
        high_value_customer = False
        enterprise_customer = False
        
        for capture in event_captures:
            business_context = capture.business_context
            arr_value = business_context.get("arr_value", 0)
            subscription = business_context.get("user_subscription", "")
            
            if arr_value >= 500000:  # $500K+ ARR
                high_value_customer = True
            
            if subscription == "enterprise":
                enterprise_customer = True
        
        # Assess impact severity
        violation_count = len(trust_violations) + len(misleading_indicators)
        
        if high_value_customer and violation_count > 0:
            return "critical"  # High-value customers cannot receive misleading events
        elif enterprise_customer and violation_count >= 2:
            return "high"      # Enterprise customers expect transparency
        elif violation_count >= 3:
            return "high"      # Multiple violations indicate systemic issue
        elif violation_count >= 1:
            return "medium"    # Some violations but manageable
        else:
            return "low"       # No significant violations
    
    def _generate_recommendations(
        self,
        trust_violations: List[str],
        misleading_indicators: List[str],
        business_impact: str
    ) -> List[str]:
        """Generate recommendations to address authenticity issues."""
        
        recommendations = []
        
        if trust_violations:
            recommendations.append(
                "Implement proper authenticity metadata in all completion events"
            )
            
            if business_impact in ["critical", "high"]:
                recommendations.append(
                    "Add enterprise-grade authenticity verification for high-value customers"
                )
        
        if misleading_indicators:
            recommendations.append(
                "Only send processing events (thinking, tool_executing) during actual processing"
            )
            
            recommendations.append(
                "Add clear fallback indicators in events when using fallback responses"
            )
        
        if business_impact == "critical":
            recommendations.append(
                "Implement immediate escalation for high-value customers during failures"
            )
        
        return recommendations
    
    def get_event_sequence_analysis(self) -> Dict[str, Any]:
        """Analyze the sequence of captured events."""
        
        if not self.event_captures:
            return {"error": "No events captured"}
        
        event_types = [capture.event_type for capture in self.event_captures]
        
        # Check for required events
        required_events = ["agent_started", "agent_completed"]
        missing_required = [event for event in required_events if event not in event_types]
        
        # Check event order
        order_violations = []
        
        if "agent_started" in event_types and "agent_completed" in event_types:
            start_index = event_types.index("agent_started")
            complete_index = event_types.index("agent_completed")
            
            if start_index >= complete_index:
                order_violations.append("agent_completed before agent_started")
        
        # Analyze timing
        timing_analysis = {}
        if len(self.event_captures) >= 2:
            total_time = self.event_captures[-1].timestamp - self.event_captures[0].timestamp
            timing_analysis = {
                "total_duration_seconds": total_time,
                "average_interval_seconds": total_time / (len(self.event_captures) - 1),
                "event_count": len(self.event_captures)
            }
        
        return {
            "event_sequence": event_types,
            "missing_required_events": missing_required,
            "order_violations": order_violations,
            "timing_analysis": timing_analysis,
            "total_events_captured": len(self.event_captures)
        }
    
    def validate_enterprise_transparency(
        self,
        arr_value: int,
        subscription_tier: str = "enterprise"
    ) -> Dict[str, Any]:
        """
        Validate that enterprise customers receive appropriate transparency.
        
        Args:
            arr_value: Annual recurring revenue value
            subscription_tier: Customer subscription tier
            
        Returns:
            Validation results for enterprise transparency requirements
        """
        if subscription_tier != "enterprise" or arr_value < 100000:
            return {"applicable": False, "reason": "Not enterprise customer"}
        
        enterprise_requirements = {
            "detailed_processing_steps": False,
            "llm_model_information": False, 
            "confidence_scores": False,
            "processing_time_breakdown": False,
            "data_source_attribution": False,
            "quality_indicators": False
        }
        
        # Check events for enterprise transparency features
        for capture in self.event_captures:
            event_data = capture.data
            
            # Check for detailed processing information
            if event_data.get("processing_details", {}).get("detailed_steps"):
                enterprise_requirements["detailed_processing_steps"] = True
            
            if event_data.get("processing_details", {}).get("llm_model"):
                enterprise_requirements["llm_model_information"] = True
            
            if event_data.get("confidence_score") is not None:
                enterprise_requirements["confidence_scores"] = True
            
            if event_data.get("processing_time_ms"):
                enterprise_requirements["processing_time_breakdown"] = True
            
            if event_data.get("data_sources"):
                enterprise_requirements["data_source_attribution"] = True
            
            if event_data.get("quality_indicators"):
                enterprise_requirements["quality_indicators"] = True
        
        # Calculate transparency score
        transparency_score = sum(enterprise_requirements.values())
        max_score = len(enterprise_requirements)
        transparency_percentage = (transparency_score / max_score) * 100
        
        # Determine if meets enterprise standards
        minimum_enterprise_features = 4  # At least 4 out of 6 features
        meets_standards = transparency_score >= minimum_enterprise_features
        
        return {
            "applicable": True,
            "meets_enterprise_standards": meets_standards,
            "transparency_score": transparency_score,
            "max_score": max_score,
            "transparency_percentage": transparency_percentage,
            "features_provided": enterprise_requirements,
            "missing_features": [
                feature for feature, provided in enterprise_requirements.items()
                if not provided
            ],
            "arr_value": arr_value,
            "minimum_required_features": minimum_enterprise_features
        }


def create_event_monitor() -> WebSocketEventMonitor:
    """Create and return a new WebSocket event monitor."""
    return WebSocketEventMonitor()


def validate_authentic_event_sequence(
    events: List[Dict[str, Any]],
    final_response: str,
    user_context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Validate that event sequence represents authentic AI processing.
    
    Args:
        events: List of WebSocket events to validate
        final_response: Final response content
        user_context: User context including subscription, ARR value, etc.
        
    Returns:
        Validation results with authenticity assessment
    """
    monitor = WebSocketEventMonitor()
    monitor.start_monitoring()
    
    # Process all events
    for event in events:
        monitor.capture_event(event)
    
    monitor.stop_monitoring()
    
    # Analyze authenticity
    analysis = monitor.analyze_event_authenticity(final_response)
    
    # Add user context validation if available
    enterprise_validation = {}
    if user_context:
        arr_value = user_context.get("arr_value", 0)
        subscription = user_context.get("subscription", "free")
        
        if subscription == "enterprise" and arr_value >= 100000:
            enterprise_validation = monitor.validate_enterprise_transparency(
                arr_value, subscription
            )
    
    return {
        "authenticity_analysis": analysis,
        "event_sequence_analysis": monitor.get_event_sequence_analysis(),
        "enterprise_validation": enterprise_validation,
        "total_events": len(events),
        "monitoring_duration": monitor.event_captures[-1].timestamp - monitor.event_captures[0].timestamp if monitor.event_captures else 0
    }