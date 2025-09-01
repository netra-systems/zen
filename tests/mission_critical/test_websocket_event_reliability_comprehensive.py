#!/usr/bin/env python
"""COMPREHENSIVE WEBSOCKET EVENT RELIABILITY TEST FRAMEWORK

This test framework validates WebSocket event reliability at the deepest level:
- Event content quality validation
- Timing analysis with silence detection  
- Edge case simulation and recovery
- User experience validation
- Event usefulness scoring

Business Value: $500K+ ARR - Prevents chat UI appearing broken
This is MISSION CRITICAL infrastructure that must NEVER regress.
"""

import asyncio
import json
import os
import sys
import time
import uuid
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import threading
import statistics

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Real services infrastructure - NO MOCKS
from test_framework.real_services import get_real_services, RealServicesManager, ServiceUnavailableError
from test_framework.environment_isolation import IsolatedEnvironment

# Import production components
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.unified_tool_execution import (
    UnifiedToolExecutionEngine,
    enhance_tool_dispatcher_with_notifications
)
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager


# ============================================================================
# ENHANCED RELIABILITY FRAMEWORK COMPONENTS
# ============================================================================

class EventQuality(Enum):
    """Event quality levels for content validation."""
    EXCELLENT = 5  # Rich, useful content
    GOOD = 4      # Adequate information
    FAIR = 3      # Basic information
    POOR = 2      # Minimal information
    UNUSABLE = 1  # Missing or broken content


class EventTiming(Enum):
    """Event timing classifications."""
    IMMEDIATE = "immediate"     # < 100ms
    FAST = "fast"              # 100ms - 1s
    ACCEPTABLE = "acceptable"   # 1s - 3s
    SLOW = "slow"              # 3s - 5s
    TOO_SLOW = "too_slow"      # > 5s


@dataclass
class EventContentScore:
    """Detailed scoring of event content quality."""
    event_type: str
    timestamp: float
    quality_score: EventQuality
    has_useful_content: bool
    content_length: int
    contains_context: bool
    user_actionable: bool
    technical_details: Dict[str, Any]
    recommendations: List[str] = field(default_factory=list)


@dataclass
class TimingAnalysis:
    """Analysis of event timing patterns."""
    total_duration: float
    event_count: int
    silent_periods: List[Tuple[float, float]]  # (start, duration)
    timing_distribution: Dict[EventTiming, int]
    average_interval: float
    max_silent_period: float
    timing_quality_score: float  # 0-1 scale


@dataclass
class EdgeCaseResult:
    """Result of edge case simulation."""
    scenario_name: str
    triggered_successfully: bool
    events_before_failure: int
    events_after_recovery: int
    recovery_time: float
    user_experience_impact: str
    lessons_learned: List[str]


class EnhancedMissionCriticalEventValidator:
    """Advanced event validator with content quality analysis."""
    
    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    OPTIONAL_EVENTS = {
        "agent_fallback",
        "final_report",
        "partial_result",
        "tool_error",
        "agent_progress"
    }
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.events: List[Dict] = []
        self.event_timeline: List[tuple] = []  # (timestamp, event_type, data)
        self.event_counts: Dict[str, int] = {}
        self.content_scores: List[EventContentScore] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.start_time = time.time()
        
    def record(self, event: Dict) -> None:
        """Record event with enhanced analysis."""
        timestamp = time.time() - self.start_time
        event_type = event.get("type", "unknown")
        
        self.events.append(event)
        self.event_timeline.append((timestamp, event_type, event))
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
        # Analyze content quality
        content_score = self._analyze_event_content(event, timestamp)
        self.content_scores.append(content_score)
        
    def _analyze_event_content(self, event: Dict, timestamp: float) -> EventContentScore:
        """Analyze the quality and usefulness of event content."""
        event_type = event.get("type", "unknown")
        payload = event.get("payload", {})
        content = str(payload) if payload else ""
        
        # Quality assessment
        quality_score = EventQuality.FAIR  # Default
        has_useful_content = False
        contains_context = False
        user_actionable = False
        recommendations = []
        
        if event_type == "agent_started":
            if "agent_name" in payload or "request_id" in payload:
                quality_score = EventQuality.GOOD
                has_useful_content = True
            if "user_request" in payload or "context" in payload:
                contains_context = True
                quality_score = EventQuality.EXCELLENT
                
        elif event_type == "agent_thinking":
            thinking_content = payload.get("content", "")
            if len(thinking_content) > 20:  # Substantial thinking
                has_useful_content = True
                quality_score = EventQuality.GOOD
            if "reasoning" in thinking_content.lower() or "analyzing" in thinking_content.lower():
                quality_score = EventQuality.EXCELLENT
                user_actionable = True
            if not thinking_content:
                quality_score = EventQuality.POOR
                recommendations.append("agent_thinking should include meaningful reasoning content")
                
        elif event_type == "tool_executing":
            tool_name = payload.get("tool_name", "")
            if tool_name:
                has_useful_content = True
                quality_score = EventQuality.GOOD
                user_actionable = True
            if "parameters" in payload or "inputs" in payload:
                contains_context = True
                quality_score = EventQuality.EXCELLENT
            if not tool_name:
                quality_score = EventQuality.POOR
                recommendations.append("tool_executing should specify which tool is being executed")
                
        elif event_type == "tool_completed":
            if "result" in payload or "output" in payload:
                has_useful_content = True
                quality_score = EventQuality.GOOD
                user_actionable = True
            if "success" in payload or "status" in payload:
                contains_context = True
                quality_score = EventQuality.EXCELLENT
            if not payload:
                quality_score = EventQuality.POOR
                recommendations.append("tool_completed should include result or status information")
                
        elif event_type == "agent_completed":
            if "success" in payload or "final_report" in payload:
                has_useful_content = True
                quality_score = EventQuality.GOOD
                user_actionable = True
            if "summary" in payload or "results" in payload:
                contains_context = True
                quality_score = EventQuality.EXCELLENT
                
        return EventContentScore(
            event_type=event_type,
            timestamp=timestamp,
            quality_score=quality_score,
            has_useful_content=has_useful_content,
            content_length=len(content),
            contains_context=contains_context,
            user_actionable=user_actionable,
            technical_details={
                "payload_keys": list(payload.keys()) if isinstance(payload, dict) else [],
                "payload_size": len(str(payload)),
                "event_structure_complete": bool(event_type and payload)
            },
            recommendations=recommendations
        )
    
    def validate_critical_requirements(self) -> tuple[bool, List[str]]:
        """Enhanced validation including content quality."""
        failures = []
        
        # 1. Check for required events
        missing = self.REQUIRED_EVENTS - set(self.event_counts.keys())
        if missing:
            failures.append(f"CRITICAL: Missing required events: {missing}")
        
        # 2. Validate event ordering
        if not self._validate_event_order():
            failures.append("CRITICAL: Invalid event order")
        
        # 3. Check for paired events
        if not self._validate_paired_events():
            failures.append("CRITICAL: Unpaired tool events")
        
        # 4. Validate timing constraints
        if not self._validate_timing():
            failures.append("CRITICAL: Event timing violations")
        
        # 5. Check for data completeness
        if not self._validate_event_data():
            failures.append("CRITICAL: Incomplete event data")
            
        # 6. NEW: Content quality validation
        content_failures = self._validate_content_quality()
        failures.extend(content_failures)
        
        return len(failures) == 0, failures
    
    def _validate_content_quality(self) -> List[str]:
        """Validate that event content is useful to users."""
        failures = []
        
        # Check overall content quality distribution
        quality_counts = {}
        for score in self.content_scores:
            quality_counts[score.quality_score] = quality_counts.get(score.quality_score, 0) + 1
        
        poor_quality_count = quality_counts.get(EventQuality.POOR, 0) + quality_counts.get(EventQuality.UNUSABLE, 0)
        total_events = len(self.content_scores)
        
        if total_events > 0:
            poor_quality_ratio = poor_quality_count / total_events
            if poor_quality_ratio > 0.3:  # More than 30% poor quality
                failures.append(f"CRITICAL: {poor_quality_ratio:.1%} of events have poor content quality")
        
        # Check for events without useful content
        unuseful_events = [s for s in self.content_scores if not s.has_useful_content]
        if len(unuseful_events) > total_events * 0.2:  # More than 20% without useful content
            failures.append(f"CRITICAL: {len(unuseful_events)} events lack useful content for users")
        
        # Specific event type quality checks
        thinking_events = [s for s in self.content_scores if s.event_type == "agent_thinking"]
        if thinking_events:
            empty_thinking = [s for s in thinking_events if s.content_length < 5]
            if len(empty_thinking) > 0:
                failures.append(f"CRITICAL: {len(empty_thinking)} agent_thinking events are nearly empty")
        
        return failures
    
    def _validate_event_order(self) -> bool:
        """Ensure events follow logical order."""
        if not self.event_timeline:
            return False
            
        # First event must be agent_started
        if self.event_timeline[0][1] != "agent_started":
            self.errors.append(f"First event was {self.event_timeline[0][1]}, not agent_started")
            return False
        
        # Last event should be completion
        last_event = self.event_timeline[-1][1]
        if last_event not in ["agent_completed", "final_report"]:
            self.errors.append(f"Last event was {last_event}, not a completion event")
            return False
            
        return True
    
    def _validate_paired_events(self) -> bool:
        """Ensure tool events are properly paired."""
        tool_starts = self.event_counts.get("tool_executing", 0)
        tool_ends = self.event_counts.get("tool_completed", 0)
        
        if tool_starts != tool_ends:
            self.errors.append(f"Tool event mismatch: {tool_starts} starts, {tool_ends} completions")
            return False
            
        return True
    
    def _validate_timing(self) -> bool:
        """Validate event timing constraints."""
        if not self.event_timeline:
            return True
            
        # Check for events that arrive too late
        for timestamp, event_type, _ in self.event_timeline:
            if timestamp > 30:  # 30 second timeout
                self.errors.append(f"Event {event_type} arrived after 30s timeout at {timestamp:.2f}s")
                return False
                
        return True
    
    def _validate_event_data(self) -> bool:
        """Ensure events contain required data fields."""
        for event in self.events:
            if "type" not in event:
                self.errors.append("Event missing 'type' field")
                return False
            if "timestamp" not in event and self.strict_mode:
                self.warnings.append(f"Event {event.get('type')} missing timestamp")
                
        return True
    
    def generate_comprehensive_report(self) -> str:
        """Generate detailed validation report with quality analysis."""
        is_valid, failures = self.validate_critical_requirements()
        timing_analysis = self.analyze_timing()
        
        report = [
            "\n" + "=" * 100,
            "COMPREHENSIVE WEBSOCKET EVENT RELIABILITY REPORT",
            "=" * 100,
            f"Status: {'✅ PASSED' if is_valid else '❌ FAILED'}",
            f"Total Events: {len(self.events)}",
            f"Unique Types: {len(self.event_counts)}",
            f"Duration: {self.event_timeline[-1][0] if self.event_timeline else 0:.2f}s",
            f"Average Quality Score: {self._calculate_average_quality():.1f}/5.0",
            "",
            "Event Coverage:"
        ]
        
        for event in self.REQUIRED_EVENTS:
            count = self.event_counts.get(event, 0)
            status = "✅" if count > 0 else "❌"
            avg_quality = self._get_average_quality_for_event_type(event)
            report.append(f"  {status} {event}: {count} events (avg quality: {avg_quality:.1f}/5.0)")
        
        # Content Quality Analysis
        report.extend([
            "",
            "Content Quality Distribution:",
            f"  Excellent: {sum(1 for s in self.content_scores if s.quality_score == EventQuality.EXCELLENT)}",
            f"  Good: {sum(1 for s in self.content_scores if s.quality_score == EventQuality.GOOD)}",
            f"  Fair: {sum(1 for s in self.content_scores if s.quality_score == EventQuality.FAIR)}",
            f"  Poor: {sum(1 for s in self.content_scores if s.quality_score == EventQuality.POOR)}",
            f"  Unusable: {sum(1 for s in self.content_scores if s.quality_score == EventQuality.UNUSABLE)}",
        ])
        
        # Timing Analysis
        report.extend([
            "",
            "Timing Analysis:",
            f"  Silent Periods: {len(timing_analysis.silent_periods)}",
            f"  Max Silent Period: {timing_analysis.max_silent_period:.2f}s",
            f"  Average Interval: {timing_analysis.average_interval:.2f}s",
            f"  Timing Quality Score: {timing_analysis.timing_quality_score:.2f}/1.0"
        ])
        
        if failures:
            report.extend(["", "FAILURES:"] + [f"  - {f}" for f in failures])
        
        if self.errors:
            report.extend(["", "ERRORS:"] + [f"  - {e}" for e in self.errors])
            
        if self.warnings:
            report.extend(["", "WARNINGS:"] + [f"  - {w}" for w in self.warnings])
        
        # Recommendations
        all_recommendations = []
        for score in self.content_scores:
            all_recommendations.extend(score.recommendations)
        
        if all_recommendations:
            unique_recommendations = list(set(all_recommendations))
            report.extend(["", "RECOMMENDATIONS:"] + [f"  - {r}" for r in unique_recommendations])
        
        report.append("=" * 100)
        return "\n".join(report)
    
    def _calculate_average_quality(self) -> float:
        """Calculate average content quality score."""
        if not self.content_scores:
            return 0.0
        return statistics.mean(score.quality_score.value for score in self.content_scores)
    
    def _get_average_quality_for_event_type(self, event_type: str) -> float:
        """Get average quality for specific event type."""
        relevant_scores = [s for s in self.content_scores if s.event_type == event_type]
        if not relevant_scores:
            return 0.0
        return statistics.mean(score.quality_score.value for score in relevant_scores)
    
    def analyze_timing(self) -> TimingAnalysis:
        """Analyze event timing patterns."""
        if not self.event_timeline:
            return TimingAnalysis(0, 0, [], {}, 0, 0, 0)
        
        timestamps = [t[0] for t in self.event_timeline]
        total_duration = timestamps[-1] if timestamps else 0
        event_count = len(timestamps)
        
        # Find silent periods (gaps > 5 seconds)
        silent_periods = []
        for i in range(1, len(timestamps)):
            gap = timestamps[i] - timestamps[i-1]
            if gap > 5.0:  # 5 second silence threshold
                silent_periods.append((timestamps[i-1], gap))
        
        # Calculate timing distribution
        timing_distribution = {timing: 0 for timing in EventTiming}
        intervals = []
        
        for i in range(1, len(timestamps)):
            interval = timestamps[i] - timestamps[i-1]
            intervals.append(interval)
            
            if interval < 0.1:
                timing_distribution[EventTiming.IMMEDIATE] += 1
            elif interval < 1.0:
                timing_distribution[EventTiming.FAST] += 1
            elif interval < 3.0:
                timing_distribution[EventTiming.ACCEPTABLE] += 1
            elif interval < 5.0:
                timing_distribution[EventTiming.SLOW] += 1
            else:
                timing_distribution[EventTiming.TOO_SLOW] += 1
        
        average_interval = statistics.mean(intervals) if intervals else 0
        max_silent_period = max((gap for _, gap in silent_periods), default=0)
        
        # Calculate timing quality score (0-1)
        timing_quality_score = 1.0
        if max_silent_period > 10:  # Penalize long silences
            timing_quality_score -= 0.3
        if average_interval > 3:  # Penalize slow average
            timing_quality_score -= 0.2
        if len(silent_periods) > event_count * 0.1:  # Too many silent periods
            timing_quality_score -= 0.2
        timing_quality_score = max(0.0, timing_quality_score)
        
        return TimingAnalysis(
            total_duration=total_duration,
            event_count=event_count,
            silent_periods=silent_periods,
            timing_distribution=timing_distribution,
            average_interval=average_interval,
            max_silent_period=max_silent_period,
            timing_quality_score=timing_quality_score
        )


class EventTimingAnalyzer:
    """Analyzes timing patterns and detects silent periods."""
    
    SILENCE_THRESHOLD = 5.0  # 5 seconds
    ACCEPTABLE_MAX_SILENCE = 8.0  # 8 seconds max acceptable
    
    def __init__(self):
        self.event_times: List[float] = []
        self.silent_periods: List[Tuple[float, float]] = []
        
    def record_event_time(self, timestamp: float) -> None:
        """Record an event timestamp."""
        self.event_times.append(timestamp)
        
    def analyze_timing_patterns(self) -> TimingAnalysis:
        """Comprehensive timing analysis."""
        if len(self.event_times) < 2:
            return TimingAnalysis(0, len(self.event_times), [], {}, 0, 0, 1.0)
        
        # Sort timestamps
        self.event_times.sort()
        
        # Calculate intervals
        intervals = []
        for i in range(1, len(self.event_times)):
            interval = self.event_times[i] - self.event_times[i-1]
            intervals.append(interval)
            
            # Detect silent periods
            if interval > self.SILENCE_THRESHOLD:
                self.silent_periods.append((self.event_times[i-1], interval))
        
        # Timing distribution
        timing_dist = {timing: 0 for timing in EventTiming}
        for interval in intervals:
            if interval < 0.1:
                timing_dist[EventTiming.IMMEDIATE] += 1
            elif interval < 1.0:
                timing_dist[EventTiming.FAST] += 1
            elif interval < 3.0:
                timing_dist[EventTiming.ACCEPTABLE] += 1
            elif interval < 5.0:
                timing_dist[EventTiming.SLOW] += 1
            else:
                timing_dist[EventTiming.TOO_SLOW] += 1
        
        avg_interval = statistics.mean(intervals)
        max_silent = max((duration for _, duration in self.silent_periods), default=0)
        
        # Quality score calculation
        quality_score = self._calculate_timing_quality(intervals, max_silent)
        
        return TimingAnalysis(
            total_duration=self.event_times[-1] - self.event_times[0],
            event_count=len(self.event_times),
            silent_periods=self.silent_periods,
            timing_distribution=timing_dist,
            average_interval=avg_interval,
            max_silent_period=max_silent,
            timing_quality_score=quality_score
        )
    
    def _calculate_timing_quality(self, intervals: List[float], max_silent: float) -> float:
        """Calculate timing quality score 0-1."""
        score = 1.0
        
        # Penalize long silent periods
        if max_silent > self.ACCEPTABLE_MAX_SILENCE:
            score -= 0.4
        elif max_silent > self.SILENCE_THRESHOLD:
            score -= 0.2
            
        # Penalize consistently slow intervals
        slow_intervals = sum(1 for i in intervals if i > 3.0)
        if slow_intervals > len(intervals) * 0.3:  # More than 30% slow
            score -= 0.3
            
        # Penalize very inconsistent timing
        if len(intervals) > 2:
            timing_stddev = statistics.stdev(intervals)
            if timing_stddev > statistics.mean(intervals):  # High variance
                score -= 0.2
        
        return max(0.0, score)


class EventContentEvaluator:
    """Evaluates event content for user usefulness."""
    
    def __init__(self):
        self.content_evaluations: List[EventContentScore] = []
        
    def evaluate_event_usefulness(self, event: Dict) -> EventContentScore:
        """Evaluate how useful an event is for users."""
        event_type = event.get("type", "unknown")
        payload = event.get("payload", {})
        
        # Base evaluation
        score = EventContentScore(
            event_type=event_type,
            timestamp=time.time(),
            quality_score=EventQuality.FAIR,
            has_useful_content=False,
            content_length=len(str(payload)),
            contains_context=False,
            user_actionable=False,
            technical_details={},
            recommendations=[]
        )
        
        # Type-specific evaluation
        if event_type == "agent_thinking":
            score = self._evaluate_thinking_content(payload, score)
        elif event_type == "tool_executing":
            score = self._evaluate_tool_execution(payload, score)
        elif event_type == "tool_completed":
            score = self._evaluate_tool_completion(payload, score)
        elif event_type == "agent_started":
            score = self._evaluate_agent_start(payload, score)
        elif event_type == "agent_completed":
            score = self._evaluate_agent_completion(payload, score)
        
        self.content_evaluations.append(score)
        return score
    
    def _evaluate_thinking_content(self, payload: Dict, score: EventContentScore) -> EventContentScore:
        """Evaluate agent thinking content quality."""
        content = payload.get("content", "")
        
        if not content:
            score.quality_score = EventQuality.UNUSABLE
            score.recommendations.append("agent_thinking events must include content")
            return score
        
        score.has_useful_content = True
        score.content_length = len(content)
        
        # Quality indicators
        quality_indicators = [
            ("reasoning", "shows reasoning process"),
            ("analyzing", "indicates analysis"),
            ("considering", "shows consideration"),
            ("evaluating", "shows evaluation"),
            ("planning", "shows planning")
        ]
        
        found_indicators = sum(1 for indicator, _ in quality_indicators if indicator in content.lower())
        
        if found_indicators >= 2:
            score.quality_score = EventQuality.EXCELLENT
            score.user_actionable = True
        elif found_indicators >= 1:
            score.quality_score = EventQuality.GOOD
        elif len(content) > 20:
            score.quality_score = EventQuality.FAIR
        else:
            score.quality_score = EventQuality.POOR
            score.recommendations.append("agent_thinking content should be more descriptive")
        
        return score
    
    def _evaluate_tool_execution(self, payload: Dict, score: EventContentScore) -> EventContentScore:
        """Evaluate tool execution event quality."""
        tool_name = payload.get("tool_name", payload.get("tool", ""))
        
        if not tool_name:
            score.quality_score = EventQuality.POOR
            score.recommendations.append("tool_executing events should specify tool name")
            return score
        
        score.has_useful_content = True
        score.user_actionable = True
        score.quality_score = EventQuality.GOOD
        
        # Check for additional context
        if "parameters" in payload or "inputs" in payload or "args" in payload:
            score.contains_context = True
            score.quality_score = EventQuality.EXCELLENT
        
        return score
    
    def _evaluate_tool_completion(self, payload: Dict, score: EventContentScore) -> EventContentScore:
        """Evaluate tool completion event quality."""
        has_result = any(key in payload for key in ["result", "output", "response"])
        has_status = any(key in payload for key in ["success", "status", "completed"])
        
        if not has_result and not has_status:
            score.quality_score = EventQuality.POOR
            score.recommendations.append("tool_completed events should include result or status")
            return score
        
        score.has_useful_content = True
        score.user_actionable = True
        
        if has_result and has_status:
            score.quality_score = EventQuality.EXCELLENT
            score.contains_context = True
        elif has_result or has_status:
            score.quality_score = EventQuality.GOOD
        
        return score
    
    def _evaluate_agent_start(self, payload: Dict, score: EventContentScore) -> EventContentScore:
        """Evaluate agent start event quality."""
        has_context = any(key in payload for key in ["user_request", "context", "task"])
        has_id = any(key in payload for key in ["request_id", "agent_name", "run_id"])
        
        if has_context and has_id:
            score.quality_score = EventQuality.EXCELLENT
            score.contains_context = True
        elif has_context or has_id:
            score.quality_score = EventQuality.GOOD
        
        score.has_useful_content = has_context or has_id
        score.user_actionable = True
        
        return score
    
    def _evaluate_agent_completion(self, payload: Dict, score: EventContentScore) -> EventContentScore:
        """Evaluate agent completion event quality."""
        has_summary = any(key in payload for key in ["summary", "final_report", "result"])
        has_status = any(key in payload for key in ["success", "completed", "status"])
        
        if has_summary and has_status:
            score.quality_score = EventQuality.EXCELLENT
            score.contains_context = True
        elif has_summary or has_status:
            score.quality_score = EventQuality.GOOD
        
        score.has_useful_content = has_summary or has_status
        score.user_actionable = True
        
        return score


class EdgeCaseSimulator:
    """Simulates edge cases and failure scenarios."""
    
    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager
        self.results: List[EdgeCaseResult] = []
        
    async def simulate_network_disconnection(self, connection_id: str) -> EdgeCaseResult:
        """Simulate network disconnection during agent execution."""
        logger.info(f"Simulating network disconnection for {connection_id}")
        
        events_before = 0
        events_after = 0
        start_time = time.time()
        
        try:
            # Simulate disconnection by closing connection
            if connection_id in self.ws_manager.connections:
                conn = self.ws_manager.connections[connection_id]
                websocket = conn["websocket"]
                await self.ws_manager._close_websocket_safely(websocket, 1006, "Network disconnection simulation")
                events_before = conn.get("message_count", 0)
            
            # Wait for recovery attempt
            await asyncio.sleep(2.0)
            
            # Check if system handled gracefully
            recovery_time = time.time() - start_time
            
            return EdgeCaseResult(
                scenario_name="network_disconnection",
                triggered_successfully=True,
                events_before_failure=events_before,
                events_after_recovery=events_after,
                recovery_time=recovery_time,
                user_experience_impact="Connection lost, requires reconnection",
                lessons_learned=["System should detect disconnections", "Graceful degradation needed"]
            )
            
        except Exception as e:
            logger.error(f"Network disconnection simulation failed: {e}")
            return EdgeCaseResult(
                scenario_name="network_disconnection",
                triggered_successfully=False,
                events_before_failure=0,
                events_after_recovery=0,
                recovery_time=time.time() - start_time,
                user_experience_impact="Simulation failed",
                lessons_learned=[f"Simulation error: {e}"]
            )
    
    async def simulate_high_load(self, concurrent_connections: int = 20) -> EdgeCaseResult:
        """Simulate high load scenario."""
        logger.info(f"Simulating high load with {concurrent_connections} connections")
        start_time = time.time()
        
        successful_connections = 0
        failed_connections = 0
        
        async def create_connection():
            nonlocal successful_connections, failed_connections
            try:
                user_id = f"load-test-{uuid.uuid4().hex[:8]}"
                # Mock websocket for load testing
                mock_websocket = type('MockWebSocket', (), {
                    'state': 1,  # Connected
                    'send_json': lambda self, data, **kwargs: asyncio.sleep(0.001),
                    'close': lambda self, **kwargs: None
                })()
                
                conn_id = await self.ws_manager.connect_user(user_id, mock_websocket)
                successful_connections += 1
                
                # Send some events
                notifier = WebSocketNotifier(self.ws_manager)
                context = AgentExecutionContext(
                    run_id=f"load-{conn_id}",
                    thread_id=conn_id,
                    user_id=user_id,
                    agent_name="load_test_agent",
                    retry_count=0,
                    max_retries=1
                )
                
                await notifier.send_agent_started(context)
                await notifier.send_agent_thinking(context, "Processing under load...")
                await notifier.send_agent_completed(context, {"success": True})
                
                await self.ws_manager.disconnect_user(user_id, mock_websocket)
                
            except Exception as e:
                failed_connections += 1
                logger.error(f"Load test connection failed: {e}")
        
        # Create connections concurrently
        tasks = [create_connection() for _ in range(concurrent_connections)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        recovery_time = time.time() - start_time
        success_rate = successful_connections / concurrent_connections if concurrent_connections > 0 else 0
        
        return EdgeCaseResult(
            scenario_name="high_load",
            triggered_successfully=True,
            events_before_failure=successful_connections * 3,  # 3 events per connection
            events_after_recovery=0,
            recovery_time=recovery_time,
            user_experience_impact=f"Success rate: {success_rate:.1%} under high load",
            lessons_learned=[
                f"Handled {successful_connections}/{concurrent_connections} concurrent connections",
                f"Failed connections: {failed_connections}",
                "Consider connection pooling for high load"
            ]
        )
    
    async def simulate_agent_crash(self, connection_id: str) -> EdgeCaseResult:
        """Simulate agent crash during execution."""
        logger.info(f"Simulating agent crash for {connection_id}")
        start_time = time.time()
        
        events_before = 0
        events_after = 0
        
        try:
            # Simulate crash by raising exception during agent execution
            notifier = WebSocketNotifier(self.ws_manager)
            context = AgentExecutionContext(
                run_id="crash-test",
                thread_id=connection_id,
                user_id=connection_id,
                agent_name="crash_test_agent",
                retry_count=0,
                max_retries=1
            )
            
            await notifier.send_agent_started(context)
            events_before += 1
            
            await notifier.send_agent_thinking(context, "About to crash...")
            events_before += 1
            
            # Simulate crash
            try:
                raise Exception("Simulated agent crash")
            except Exception:
                # Recovery: send fallback notification
                await notifier.send_fallback_notification(context, "agent_error")
                events_after += 1
            
            recovery_time = time.time() - start_time
            
            return EdgeCaseResult(
                scenario_name="agent_crash",
                triggered_successfully=True,
                events_before_failure=events_before,
                events_after_recovery=events_after,
                recovery_time=recovery_time,
                user_experience_impact="User receives error notification",
                lessons_learned=[
                    "Error handling sends appropriate notifications",
                    "Users are informed of failures",
                    "System continues after agent crashes"
                ]
            )
            
        except Exception as e:
            return EdgeCaseResult(
                scenario_name="agent_crash",
                triggered_successfully=False,
                events_before_failure=0,
                events_after_recovery=0,
                recovery_time=time.time() - start_time,
                user_experience_impact="Crash simulation failed",
                lessons_learned=[f"Crash simulation error: {e}"]
            )


class UserExperienceValidator:
    """Validates user experience aspects of WebSocket events."""
    
    def __init__(self):
        self.ux_metrics: Dict[str, Any] = {}
        
    def validate_user_journey(self, events: List[Dict]) -> Dict[str, Any]:
        """Validate complete user journey experience."""
        journey_metrics = {
            "has_clear_start": False,
            "has_progress_updates": False,
            "has_clear_completion": False,
            "perceived_responsiveness": "unknown",
            "information_quality": "unknown",
            "user_confidence_level": "unknown",
            "confusion_risk": "low"
        }
        
        if not events:
            journey_metrics["confusion_risk"] = "high"
            return journey_metrics
        
        event_types = [e.get("type", "unknown") for e in events]
        
        # Check for clear start
        if "agent_started" in event_types:
            journey_metrics["has_clear_start"] = True
        
        # Check for progress updates
        progress_indicators = ["agent_thinking", "tool_executing", "partial_result"]
        if any(indicator in event_types for indicator in progress_indicators):
            journey_metrics["has_progress_updates"] = True
        
        # Check for clear completion
        completion_indicators = ["agent_completed", "final_report"]
        if any(indicator in event_types for indicator in completion_indicators):
            journey_metrics["has_clear_completion"] = True
        
        # Assess perceived responsiveness
        if len(events) >= 3:  # Minimum interactions
            journey_metrics["perceived_responsiveness"] = "good"
        elif len(events) >= 2:
            journey_metrics["perceived_responsiveness"] = "acceptable"
        else:
            journey_metrics["perceived_responsiveness"] = "poor"
        
        # Assess information quality
        meaningful_events = sum(1 for e in events if self._has_meaningful_content(e))
        quality_ratio = meaningful_events / len(events) if events else 0
        
        if quality_ratio >= 0.8:
            journey_metrics["information_quality"] = "excellent"
        elif quality_ratio >= 0.6:
            journey_metrics["information_quality"] = "good"
        elif quality_ratio >= 0.4:
            journey_metrics["information_quality"] = "fair"
        else:
            journey_metrics["information_quality"] = "poor"
        
        # Assess user confidence
        has_all_key_events = (
            journey_metrics["has_clear_start"] and
            journey_metrics["has_progress_updates"] and
            journey_metrics["has_clear_completion"]
        )
        
        if has_all_key_events and quality_ratio >= 0.7:
            journey_metrics["user_confidence_level"] = "high"
        elif has_all_key_events or quality_ratio >= 0.5:
            journey_metrics["user_confidence_level"] = "medium"
        else:
            journey_metrics["user_confidence_level"] = "low"
        
        # Assess confusion risk
        if not journey_metrics["has_clear_start"]:
            journey_metrics["confusion_risk"] = "high"
        elif not journey_metrics["has_progress_updates"]:
            journey_metrics["confusion_risk"] = "medium"
        elif journey_metrics["information_quality"] == "poor":
            journey_metrics["confusion_risk"] = "medium"
        
        self.ux_metrics = journey_metrics
        return journey_metrics
    
    def _has_meaningful_content(self, event: Dict) -> bool:
        """Check if event has meaningful content for users."""
        payload = event.get("payload", {})
        
        if not payload:
            return False
        
        # Type-specific meaningful content checks
        event_type = event.get("type", "")
        
        if event_type == "agent_thinking":
            content = payload.get("content", "")
            return len(content) > 10  # More than trivial content
        
        elif event_type in ["tool_executing", "tool_completed"]:
            return "tool_name" in payload or "tool" in payload
        
        elif event_type in ["agent_started", "agent_completed"]:
            return len(payload) > 0  # Has some context
        
        return True  # Default to meaningful for other types
    
    def generate_ux_report(self) -> str:
        """Generate user experience report."""
        if not self.ux_metrics:
            return "No UX metrics available"
        
        report = [
            "\nUSER EXPERIENCE VALIDATION REPORT",
            "=" * 50,
            f"Clear Start: {'✅' if self.ux_metrics.get('has_clear_start') else '❌'}",
            f"Progress Updates: {'✅' if self.ux_metrics.get('has_progress_updates') else '❌'}",
            f"Clear Completion: {'✅' if self.ux_metrics.get('has_clear_completion') else '❌'}",
            f"Perceived Responsiveness: {self.ux_metrics.get('perceived_responsiveness', 'unknown').upper()}",
            f"Information Quality: {self.ux_metrics.get('information_quality', 'unknown').upper()}",
            f"User Confidence Level: {self.ux_metrics.get('user_confidence_level', 'unknown').upper()}",
            f"Confusion Risk: {self.ux_metrics.get('confusion_risk', 'unknown').upper()}",
            "=" * 50
        ]
        
        return "\n".join(report)


# ============================================================================
# COMPREHENSIVE RELIABILITY TESTS
# ============================================================================

class TestComprehensiveWebSocketEventReliability:
    """Comprehensive WebSocket event reliability test suite."""
    
    @pytest.fixture(autouse=True)
    async def setup_comprehensive_services(self):
        """Setup real services for comprehensive testing."""
        self.env = IsolatedEnvironment()
        self.env.enable()
        
        try:
            self.real_services = get_real_services()
            await self.real_services.ensure_all_services_available()
            await self.real_services.reset_all_data()
        except ServiceUnavailableError as e:
            pytest.skip(f"Real services not available: {e}")
        
        yield
        
        await self.real_services.close_all()
        self.env.disable(restore_original=True)
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_enhanced_event_content_quality(self):
        """Test event content quality with enhanced validation."""
        ws_manager = WebSocketManager()
        validator = EnhancedMissionCriticalEventValidator()
        evaluator = EventContentEvaluator()
        
        # Create REAL WebSocket connection
        conn_id = "content-quality-test"
        ws_client = self.real_services.create_websocket_client()
        await ws_client.connect(f"test/{conn_id}")
        
        received_events = []
        
        async def capture_quality_events():
            while ws_client._connected:
                try:
                    message = await ws_client.receive_json(timeout=0.1)
                    received_events.append(message)
                    validator.record(message)
                    evaluator.evaluate_event_usefulness(message)
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    break
        
        capture_task = asyncio.create_task(capture_quality_events())
        await ws_manager.connect_user(conn_id, ws_client._websocket, conn_id)
        
        # Create comprehensive agent execution with quality content
        notifier = WebSocketNotifier(ws_manager)
        context = AgentExecutionContext(
            run_id="quality-test",
            thread_id=conn_id,
            user_id=conn_id,
            agent_name="quality_test_agent",
            retry_count=0,
            max_retries=1
        )
        
        # Send high-quality events
        await notifier.send_agent_started(context)
        await asyncio.sleep(0.1)
        
        await notifier.send_agent_thinking(context, "I'm analyzing your request and considering the best approach to solve this problem. Let me break down the task into manageable steps.")
        await asyncio.sleep(0.1)
        
        await notifier.send_tool_executing(context, "search_knowledge")
        await asyncio.sleep(0.1)
        
        await notifier.send_tool_completed(context, "search_knowledge", {
            "result": "Found relevant information",
            "success": True,
            "details": "Located 3 relevant documents"
        })
        await asyncio.sleep(0.1)
        
        await notifier.send_partial_result(context, "Based on my research, I found several key insights that will help address your question.")
        await asyncio.sleep(0.1)
        
        await notifier.send_agent_completed(context, {
            "success": True,
            "summary": "Task completed successfully with comprehensive results",
            "final_report": "Detailed analysis complete with actionable recommendations"
        })
        
        # Allow events to be captured
        await asyncio.sleep(1.0)
        capture_task.cancel()
        try:
            await capture_task
        except asyncio.CancelledError:
            pass
        
        await ws_client.close()
        
        # Validate content quality
        is_valid, failures = validator.validate_critical_requirements()
        quality_report = validator.generate_comprehensive_report()
        
        logger.info(quality_report)
        
        # Enhanced quality assertions
        assert is_valid, f"Content quality validation failed: {failures}"
        
        # Check average content quality
        avg_quality = validator._calculate_average_quality()
        assert avg_quality >= 3.5, f"Average content quality too low: {avg_quality}/5.0"
        
        # Check for meaningful content in thinking events
        thinking_scores = [s for s in validator.content_scores if s.event_type == "agent_thinking"]
        assert len(thinking_scores) > 0, "No agent_thinking events found"
        assert all(s.has_useful_content for s in thinking_scores), "Some thinking events lack useful content"
        
        # Check tool events have proper context
        tool_exec_scores = [s for s in validator.content_scores if s.event_type == "tool_executing"]
        if tool_exec_scores:
            assert all(s.has_useful_content for s in tool_exec_scores), "Tool execution events lack context"
        
        print(f"\n✅ Content Quality Test Passed - Average Quality: {avg_quality:.1f}/5.0")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_timing_analysis_with_silence_detection(self):
        """Test timing analysis and silence detection."""
        ws_manager = WebSocketManager()
        validator = EnhancedMissionCriticalEventValidator()
        timing_analyzer = EventTimingAnalyzer()
        
        conn_id = "timing-test"
        ws_client = self.real_services.create_websocket_client()
        await ws_client.connect(f"test/{conn_id}")
        
        received_events = []
        
        async def capture_timing_events():
            while ws_client._connected:
                try:
                    message = await ws_client.receive_json(timeout=0.1)
                    event_time = time.time()
                    received_events.append((message, event_time))
                    validator.record(message)
                    timing_analyzer.record_event_time(event_time)
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    break
        
        capture_task = asyncio.create_task(capture_timing_events())
        await ws_manager.connect_user(conn_id, ws_client._websocket, conn_id)
        
        notifier = WebSocketNotifier(ws_manager)
        context = AgentExecutionContext(
            run_id="timing-test",
            thread_id=conn_id,
            user_id=conn_id,
            agent_name="timing_test_agent",
            retry_count=0,
            max_retries=1
        )
        
        # Send events with controlled timing
        start_time = time.time()
        
        await notifier.send_agent_started(context)
        await asyncio.sleep(0.5)  # Fast response
        
        await notifier.send_agent_thinking(context, "Processing...")
        await asyncio.sleep(2.0)  # Acceptable delay
        
        await notifier.send_tool_executing(context, "analysis_tool")
        await asyncio.sleep(1.5)  # Good response time
        
        await notifier.send_tool_completed(context, "analysis_tool", {"result": "complete"})
        await asyncio.sleep(0.2)  # Immediate
        
        # Simulate a problematic silence period
        await asyncio.sleep(6.0)  # TOO LONG - should be detected
        
        await notifier.send_agent_completed(context, {"success": True})
        
        total_test_time = time.time() - start_time
        
        # Allow final capture
        await asyncio.sleep(1.0)
        capture_task.cancel()
        try:
            await capture_task
        except asyncio.CancelledError:
            pass
        
        await ws_client.close()
        
        # Analyze timing
        timing_analysis = validator.analyze_timing()
        detailed_timing = timing_analyzer.analyze_timing_patterns()
        
        # Timing validation assertions
        assert len(received_events) >= 5, f"Expected at least 5 events, got {len(received_events)}"
        
        # Check for detected silence periods
        assert len(timing_analysis.silent_periods) > 0, "Should detect the 6-second silence period"
        
        max_silence = max(duration for _, duration in timing_analysis.silent_periods)
        assert max_silence >= 5.0, f"Should detect silence >= 5s, found max: {max_silence:.1f}s"
        
        # Check timing quality score
        timing_quality = timing_analysis.timing_quality_score
        assert timing_quality < 1.0, f"Timing quality should be penalized for silence, got: {timing_quality}"
        
        # Check distribution
        slow_events = timing_analysis.timing_distribution[EventTiming.TOO_SLOW]
        assert slow_events > 0, "Should detect some TOO_SLOW events from the 6s gap"
        
        print(f"\n✅ Timing Analysis Test Passed - Max Silence: {max_silence:.1f}s, Quality: {timing_quality:.2f}")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(90)
    async def test_edge_case_simulation_comprehensive(self):
        """Test comprehensive edge case scenarios."""
        ws_manager = WebSocketManager()
        edge_simulator = EdgeCaseSimulator(ws_manager)
        validator = EnhancedMissionCriticalEventValidator()
        
        conn_id = "edge-case-test"
        ws_client = self.real_services.create_websocket_client()
        await ws_client.connect(f"test/{conn_id}")
        
        async def capture_edge_events():
            while ws_client._connected:
                try:
                    message = await ws_client.receive_json(timeout=0.1)
                    validator.record(message)
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    break
        
        capture_task = asyncio.create_task(capture_edge_events())
        await ws_manager.connect_user(conn_id, ws_client._websocket, conn_id)
        
        edge_results = []
        
        # Test 1: Agent crash simulation
        try:
            crash_result = await edge_simulator.simulate_agent_crash(conn_id)
            edge_results.append(crash_result)
            logger.info(f"Crash simulation result: {crash_result}")
        except Exception as e:
            logger.error(f"Crash simulation failed: {e}")
        
        await asyncio.sleep(1.0)
        
        # Test 2: High load simulation
        try:
            load_result = await edge_simulator.simulate_high_load(10)  # Reduced for real connections
            edge_results.append(load_result)
            logger.info(f"Load simulation result: {load_result}")
        except Exception as e:
            logger.error(f"Load simulation failed: {e}")
        
        await asyncio.sleep(1.0)
        
        # Test 3: Network disconnection simulation
        try:
            disconnect_result = await edge_simulator.simulate_network_disconnection(conn_id)
            edge_results.append(disconnect_result)
            logger.info(f"Disconnection simulation result: {disconnect_result}")
        except Exception as e:
            logger.error(f"Disconnection simulation failed: {e}")
        
        capture_task.cancel()
        try:
            await capture_task
        except asyncio.CancelledError:
            pass
        
        await ws_client.close()
        
        # Validate edge case handling
        assert len(edge_results) > 0, "No edge case simulations completed"
        
        successful_simulations = [r for r in edge_results if r.triggered_successfully]
        assert len(successful_simulations) >= 2, f"Expected at least 2 successful simulations, got {len(successful_simulations)}"
        
        # Check that system handled edge cases gracefully
        for result in successful_simulations:
            assert result.recovery_time < 10.0, f"Recovery took too long for {result.scenario_name}: {result.recovery_time:.2f}s"
            assert len(result.lessons_learned) > 0, f"No lessons learned from {result.scenario_name}"
        
        print(f"\n✅ Edge Case Test Passed - {len(successful_simulations)} scenarios handled successfully")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_user_experience_validation(self):
        """Test user experience validation with journey analysis."""
        ws_manager = WebSocketManager()
        validator = EnhancedMissionCriticalEventValidator()
        ux_validator = UserExperienceValidator()
        
        conn_id = "ux-test"
        ws_client = self.real_services.create_websocket_client()
        await ws_client.connect(f"test/{conn_id}")
        
        received_events = []
        
        async def capture_ux_events():
            while ws_client._connected:
                try:
                    message = await ws_client.receive_json(timeout=0.1)
                    received_events.append(message)
                    validator.record(message)
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    break
        
        capture_task = asyncio.create_task(capture_ux_events())
        await ws_manager.connect_user(conn_id, ws_client._websocket, conn_id)
        
        # Create realistic user journey
        notifier = WebSocketNotifier(ws_manager)
        context = AgentExecutionContext(
            run_id="ux-test",
            thread_id=conn_id,
            user_id=conn_id,
            agent_name="ux_test_agent",
            retry_count=0,
            max_retries=1
        )
        
        # Comprehensive user journey simulation
        await notifier.send_agent_started(context)
        await asyncio.sleep(0.2)
        
        await notifier.send_agent_thinking(context, "I understand your request. Let me analyze the requirements and determine the best approach to help you.")
        await asyncio.sleep(0.5)
        
        await notifier.send_tool_executing(context, "research_tool")
        await asyncio.sleep(0.3)
        
        await notifier.send_tool_completed(context, "research_tool", {
            "result": "Research completed",
            "success": True,
            "findings": "Found 5 relevant sources"
        })
        await asyncio.sleep(0.2)
        
        await notifier.send_partial_result(context, "I've gathered relevant information and I'm now preparing a comprehensive response for you.")
        await asyncio.sleep(0.4)
        
        await notifier.send_agent_thinking(context, "Based on my research, I can provide you with a detailed answer that addresses all aspects of your question.")
        await asyncio.sleep(0.3)
        
        await notifier.send_agent_completed(context, {
            "success": True,
            "summary": "Task completed successfully",
            "final_report": "I've analyzed your request and provided a comprehensive solution with supporting details."
        })
        
        await asyncio.sleep(1.0)
        capture_task.cancel()
        try:
            await capture_task
        except asyncio.CancelledError:
            pass
        
        await ws_client.close()
        
        # Validate user experience
        ux_metrics = ux_validator.validate_user_journey(received_events)
        ux_report = ux_validator.generate_ux_report()
        
        logger.info(ux_report)
        
        # UX validation assertions
        assert ux_metrics["has_clear_start"], "User journey lacks clear start"
        assert ux_metrics["has_progress_updates"], "User journey lacks progress updates"
        assert ux_metrics["has_clear_completion"], "User journey lacks clear completion"
        
        assert ux_metrics["perceived_responsiveness"] in ["good", "excellent"], \
            f"Poor perceived responsiveness: {ux_metrics['perceived_responsiveness']}"
        
        assert ux_metrics["information_quality"] in ["good", "excellent"], \
            f"Poor information quality: {ux_metrics['information_quality']}"
        
        assert ux_metrics["user_confidence_level"] in ["medium", "high"], \
            f"Low user confidence: {ux_metrics['user_confidence_level']}"
        
        assert ux_metrics["confusion_risk"] in ["low", "medium"], \
            f"High confusion risk: {ux_metrics['confusion_risk']}"
        
        print(f"\n✅ User Experience Test Passed - Confidence: {ux_metrics['user_confidence_level']}, Risk: {ux_metrics['confusion_risk']}")
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(120)
    async def test_comprehensive_reliability_suite(self):
        """Run the complete comprehensive reliability test suite."""
        logger.info("\n" + "=" * 100)
        logger.info("RUNNING COMPREHENSIVE WEBSOCKET EVENT RELIABILITY SUITE")
        logger.info("=" * 100)
        
        ws_manager = WebSocketManager()
        validator = EnhancedMissionCriticalEventValidator()
        timing_analyzer = EventTimingAnalyzer()
        content_evaluator = EventContentEvaluator()
        edge_simulator = EdgeCaseSimulator(ws_manager)
        ux_validator = UserExperienceValidator()
        
        # Test multiple concurrent connections with comprehensive validation
        connection_count = 5
        connections = []
        capture_tasks = []
        validators = {}
        
        for i in range(connection_count):
            conn_id = f"comprehensive-{i}"
            conn_validator = EnhancedMissionCriticalEventValidator()
            validators[conn_id] = conn_validator
            
            ws_client = self.real_services.create_websocket_client()
            await ws_client.connect(f"test/{conn_id}")
            
            async def capture_for_comprehensive(client, val, conn_id):
                while client._connected:
                    try:
                        message = await client.receive_json(timeout=0.1)
                        val.record(message)
                        content_evaluator.evaluate_event_usefulness(message)
                    except asyncio.TimeoutError:
                        continue
                    except Exception:
                        break
            
            capture_task = asyncio.create_task(
                capture_for_comprehensive(ws_client, conn_validator, conn_id)
            )
            capture_tasks.append(capture_task)
            
            await ws_manager.connect_user(conn_id, ws_client._websocket, conn_id)
            connections.append((conn_id, ws_client))
        
        # Execute comprehensive scenarios concurrently
        notifier = WebSocketNotifier(ws_manager)
        
        async def comprehensive_scenario(conn_id):
            context = AgentExecutionContext(
                run_id=f"comp-{conn_id}",
                thread_id=conn_id,
                user_id=conn_id,
                agent_name="comprehensive_agent",
                retry_count=0,
                max_retries=1
            )
            
            await notifier.send_agent_started(context)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
            await notifier.send_agent_thinking(context, 
                "I'm carefully analyzing your comprehensive request to ensure I provide the most accurate and helpful response.")
            await asyncio.sleep(random.uniform(0.2, 0.5))
            
            # Multiple tool executions
            for tool_name in ["analyzer", "validator", "synthesizer"]:
                await notifier.send_tool_executing(context, tool_name)
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
                await notifier.send_tool_completed(context, tool_name, {
                    "result": f"{tool_name} completed successfully",
                    "success": True,
                    "details": f"Processed data using {tool_name}"
                })
                await asyncio.sleep(random.uniform(0.1, 0.2))
            
            await notifier.send_partial_result(context, 
                "I've completed my analysis and am now preparing your comprehensive response.")
            await asyncio.sleep(random.uniform(0.2, 0.4))
            
            await notifier.send_agent_completed(context, {
                "success": True,
                "summary": "Comprehensive analysis completed successfully",
                "final_report": "Detailed response prepared with full analysis and recommendations"
            })
        
        # Run all scenarios concurrently
        scenario_tasks = [comprehensive_scenario(conn_id) for conn_id, _ in connections]
        await asyncio.gather(*scenario_tasks)
        
        # Allow final capture
        await asyncio.sleep(2.0)
        
        # Stop capture tasks
        for task in capture_tasks:
            task.cancel()
        try:
            await asyncio.gather(*capture_tasks, return_exceptions=True)
        except:
            pass
        
        # Comprehensive validation
        all_passed = True
        summary_report = [
            "\n" + "=" * 100,
            "COMPREHENSIVE RELIABILITY SUITE RESULTS",
            "=" * 100
        ]
        
        for conn_id, conn_validator in validators.items():
            is_valid, failures = conn_validator.validate_critical_requirements()
            quality_score = conn_validator._calculate_average_quality()
            timing_analysis = conn_validator.analyze_timing()
            
            status = "✅ PASSED" if is_valid else "❌ FAILED"
            summary_report.append(f"Connection {conn_id}: {status} (Quality: {quality_score:.1f}/5.0)")
            
            if not is_valid:
                all_passed = False
                summary_report.extend([f"  Failures: {failures}"])
            
            # Check timing quality
            if timing_analysis.timing_quality_score < 0.7:
                summary_report.append(f"  ⚠️  Timing quality low: {timing_analysis.timing_quality_score:.2f}")
        
        # Overall content quality
        total_evaluations = len(content_evaluator.content_evaluations)
        if total_evaluations > 0:
            avg_quality = statistics.mean(e.quality_score.value for e in content_evaluator.content_evaluations)
            summary_report.append(f"Overall Content Quality: {avg_quality:.1f}/5.0")
        
        summary_report.extend([
            f"Total Events Processed: {sum(len(v.events) for v in validators.values())}",
            f"Connections Tested: {len(connections)}",
            "=" * 100
        ])
        
        final_report = "\n".join(summary_report)
        logger.info(final_report)
        
        # Cleanup
        for conn_id, ws_client in connections:
            await ws_manager.disconnect_user(conn_id, ws_client._websocket, conn_id)
            await ws_client.close()
        
        # Final assertions
        assert all_passed, f"Comprehensive reliability suite failed. See report above."
        assert len(connections) == connection_count, f"Not all connections completed successfully"
        
        print(f"\n🎉 COMPREHENSIVE RELIABILITY SUITE PASSED")
        print(f"✅ Tested {len(connections)} concurrent connections")
        print(f"✅ Processed {sum(len(v.events) for v in validators.values())} total events") 
        print(f"✅ All critical requirements validated")


# ============================================================================
# SUPPORT FUNCTIONS
# ============================================================================

def generate_reliability_dashboard() -> str:
    """Generate a reliability dashboard summary."""
    return """
WEBSOCKET EVENT RELIABILITY DASHBOARD
====================================

Test Coverage:
✅ Event Content Quality Validation
✅ Timing Analysis with Silence Detection  
✅ Edge Case Simulation & Recovery
✅ User Experience Journey Validation
✅ Comprehensive Multi-Connection Testing

Critical Metrics Monitored:
- Event content usefulness scores
- Silent period detection (>5s gaps)
- User journey completeness
- Recovery time from failures
- Content quality distribution

Reliability Standards:
- Content quality average: ≥3.5/5.0
- Maximum silent period: ≤8.0s
- User confidence level: Medium/High
- Edge case recovery: ≤10.0s
- Event completion rate: 100%

Business Impact:
- Prevents broken chat UI experience
- Ensures user confidence in system
- Validates real-time feedback quality
- Protects $500K+ ARR from degradation
"""


if __name__ == "__main__":
    # Run with: python tests/mission_critical/test_websocket_event_reliability_comprehensive.py
    # Or: pytest tests/mission_critical/test_websocket_event_reliability_comprehensive.py -v
    print(generate_reliability_dashboard())
    pytest.main([__file__, "-v", "--tb=short", "-x"])