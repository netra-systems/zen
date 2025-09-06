#!/usr/bin/env python
"""WebSocket Monitoring Utilities for Real-time Event Analysis

Business Value Justification:
- Segment: Platform/Internal (Mission Critical Infrastructure)
- Business Goal: Provide real-time monitoring and analysis of $500K+ ARR chat functionality
- Value Impact: Enables proactive detection of WebSocket issues before they impact users
- Strategic Impact: Maintains chat quality that drives customer retention and conversions

This module provides comprehensive monitoring utilities for WebSocket events:
1. Real-time event capture and analysis
2. Event timeline visualization and reporting
3. Performance metrics collection and trending
4. Failure pattern detection and alerting
5. User isolation monitoring
6. Latency analysis and bottleneck identification

CRITICAL: These utilities ensure WebSocket events deliver substantive chat value.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from collections import defaultdict, deque, Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import pandas as pd
from contextlib import contextmanager

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from loguru import logger

# Import WebSocket components
from netra_backend.app.websocket_core.event_validation_framework import (
    EventType, EventValidationLevel, ValidationResult, ValidatedEvent
)
from shared.isolated_environment import get_env, IsolatedEnvironment


# ============================================================================
# REAL-TIME EVENT MONITORING
# ============================================================================

@dataclass
class EventMetrics:
    """Comprehensive metrics for WebSocket event analysis."""
    timestamp: float
    event_type: str
    thread_id: str
    user_id: Optional[str]
    latency_ms: float
    validation_result: str
    sequence_position: int
    content_size_bytes: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            "latency_ms": self.latency_ms,
            "validation_result": self.validation_result,
            "sequence_position": self.sequence_position,
            "content_size_bytes": self.content_size_bytes,
            "datetime": datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat()
        }


@dataclass
class PerformanceWindow:
    """Rolling performance metrics window."""
    window_size: int = 100
    events: deque = field(default_factory=deque)
    latencies: deque = field(default_factory=deque)
    event_counts: Counter = field(default_factory=Counter)
    
    def add_event(self, metrics: EventMetrics):
        """Add event to performance window."""
        # Maintain rolling window
        if len(self.events) >= self.window_size:
            old_event = self.events.popleft()
            self.event_counts[old_event.event_type] -= 1
            self.latencies.popleft()
        
        self.events.append(metrics)
        self.latencies.append(metrics.latency_ms)
        self.event_counts[metrics.event_type] += 1
    
    @property
    def avg_latency(self) -> float:
        """Calculate average latency in current window."""
        return statistics.mean(self.latencies) if self.latencies else 0.0
    
    @property
    def max_latency(self) -> float:
        """Calculate maximum latency in current window."""
        return max(self.latencies) if self.latencies else 0.0
    
    @property
    def events_per_second(self) -> float:
        """Calculate events per second in current window."""
        if len(self.events) < 2:
            return 0.0
        
        time_span = self.events[-1].timestamp - self.events[0].timestamp
        return len(self.events) / time_span if time_span > 0 else 0.0


class RealTimeEventMonitor:
    """Real-time WebSocket event monitoring and analysis."""
    
    def __init__(self, window_size: int = 100, alert_thresholds: Dict[str, float] = None):
        self.window_size = window_size
        self.alert_thresholds = alert_thresholds or {
            'max_latency_ms': 200.0,
            'min_events_per_second': 0.1,
            'error_rate_percent': 5.0
        }
        
        # Monitoring data
        self.all_events: List[EventMetrics] = []
        self.performance_window = PerformanceWindow(window_size)
        self.user_windows: Dict[str, PerformanceWindow] = defaultdict(lambda: PerformanceWindow(window_size))
        self.thread_sequences: Dict[str, List[EventMetrics]] = defaultdict(list)
        
        # Alert tracking
        self.alerts: List[Dict[str, Any]] = []
        self.alert_callbacks: List[Callable] = []
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Monitoring state
        self.start_time = time.time()
        self.is_active = False
    
    def start_monitoring(self):
        """Start real-time monitoring."""
        with self._lock:
            self.is_active = True
            self.start_time = time.time()
            logger.info("Real-time WebSocket event monitoring started")
    
    def stop_monitoring(self):
        """Stop real-time monitoring."""
        with self._lock:
            self.is_active = False
            logger.info("Real-time WebSocket event monitoring stopped")
    
    def record_event(self, validated_event: ValidatedEvent) -> EventMetrics:
        """Record a validated WebSocket event for monitoring."""
        if not self.is_active:
            return
        
        with self._lock:
            # Extract user ID from event content
            user_id = validated_event.content.get('user_id') or \
                     validated_event.content.get('context', {}).get('user_id')
            
            # Create event metrics
            metrics = EventMetrics(
                timestamp=validated_event.timestamp,
                event_type=validated_event.event_type.value if isinstance(validated_event.event_type, EventType) else str(validated_event.event_type),
                thread_id=validated_event.thread_id,
                user_id=user_id,
                latency_ms=validated_event.latency_ms or 0.0,
                validation_result=validated_event.validation_result.value if isinstance(validated_event.validation_result, ValidationResult) else str(validated_event.validation_result),
                sequence_position=len(self.thread_sequences[validated_event.thread_id]),
                content_size_bytes=len(json.dumps(validated_event.content))
            )
            
            # Store in various collections
            self.all_events.append(metrics)
            self.performance_window.add_event(metrics)
            self.thread_sequences[validated_event.thread_id].append(metrics)
            
            if user_id:
                self.user_windows[user_id].add_event(metrics)
            
            # Check for alerts
            self._check_alerts(metrics)
            
            return metrics
    
    def _check_alerts(self, metrics: EventMetrics):
        """Check for alert conditions."""
        current_time = time.time()
        
        # High latency alert
        if metrics.latency_ms > self.alert_thresholds['max_latency_ms']:
            alert = {
                'type': 'HIGH_LATENCY',
                'message': f'Event latency {metrics.latency_ms:.1f}ms exceeds threshold {self.alert_thresholds["max_latency_ms"]}ms',
                'event_type': metrics.event_type,
                'thread_id': metrics.thread_id,
                'timestamp': current_time,
                'severity': 'WARNING' if metrics.latency_ms < self.alert_thresholds['max_latency_ms'] * 2 else 'CRITICAL'
            }
            self._trigger_alert(alert)
        
        # Event validation failure alert
        if metrics.validation_result != ValidationResult.VALID.value:
            alert = {
                'type': 'VALIDATION_FAILURE',
                'message': f'Event validation failed: {metrics.validation_result}',
                'event_type': metrics.event_type,
                'thread_id': metrics.thread_id,
                'timestamp': current_time,
                'severity': 'ERROR' if metrics.validation_result == ValidationResult.ERROR.value else 'CRITICAL'
            }
            self._trigger_alert(alert)
        
        # Low throughput alert (check every 10 events)
        if len(self.all_events) % 10 == 0 and self.performance_window.events_per_second < self.alert_thresholds['min_events_per_second']:
            alert = {
                'type': 'LOW_THROUGHPUT',
                'message': f'Events per second {self.performance_window.events_per_second:.2f} below threshold {self.alert_thresholds["min_events_per_second"]}',
                'timestamp': current_time,
                'severity': 'WARNING'
            }
            self._trigger_alert(alert)
    
    def _trigger_alert(self, alert: Dict[str, Any]):
        """Trigger an alert and notify callbacks."""
        self.alerts.append(alert)
        
        # Log alert
        logger.warning(f"WEBSOCKET ALERT [{alert['severity']}]: {alert['message']}")
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for alert notifications."""
        self.alert_callbacks.append(callback)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current monitoring metrics."""
        with self._lock:
            if not self.all_events:
                return {"status": "no_data", "message": "No events recorded yet"}
            
            current_time = time.time()
            duration = current_time - self.start_time
            
            # Overall metrics
            total_events = len(self.all_events)
            valid_events = sum(1 for e in self.all_events if e.validation_result == ValidationResult.VALID.value)
            
            # Recent performance (last 100 events)
            recent_latencies = [e.latency_ms for e in self.all_events[-100:]]
            
            return {
                "status": "active" if self.is_active else "stopped",
                "duration_seconds": duration,
                "total_events": total_events,
                "valid_events": valid_events,
                "success_rate_percent": (valid_events / total_events * 100) if total_events > 0 else 0,
                "events_per_second": total_events / duration if duration > 0 else 0,
                "recent_performance": {
                    "avg_latency_ms": statistics.mean(recent_latencies) if recent_latencies else 0,
                    "max_latency_ms": max(recent_latencies) if recent_latencies else 0,
                    "events_per_second": self.performance_window.events_per_second
                },
                "event_counts": dict(self.performance_window.event_counts),
                "active_threads": len(self.thread_sequences),
                "active_users": len(self.user_windows),
                "recent_alerts": len([a for a in self.alerts if current_time - a['timestamp'] < 300])  # Last 5 minutes
            }
    
    def get_user_metrics(self, user_id: str) -> Dict[str, Any]:
        """Get metrics for a specific user."""
        with self._lock:
            if user_id not in self.user_windows:
                return {"status": "no_data", "message": f"No data for user {user_id}"}
            
            window = self.user_windows[user_id]
            user_events = [e for e in self.all_events if e.user_id == user_id]
            
            if not user_events:
                return {"status": "no_data", "message": f"No events for user {user_id}"}
            
            return {
                "user_id": user_id,
                "total_events": len(user_events),
                "avg_latency_ms": window.avg_latency,
                "max_latency_ms": window.max_latency,
                "events_per_second": window.events_per_second,
                "event_counts": dict(window.event_counts),
                "active_threads": len(set(e.thread_id for e in user_events))
            }


# ============================================================================
# EVENT TIMELINE VISUALIZATION
# ============================================================================

class EventTimelineVisualizer:
    """Creates visual timelines and charts for WebSocket events."""
    
    def __init__(self, output_dir: str = "websocket_reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def create_event_timeline(self, events: List[EventMetrics], title: str = "WebSocket Event Timeline") -> str:
        """Create a timeline visualization of events."""
        if not events:
            logger.warning("No events to visualize")
            return None
        
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame([e.to_dict() for e in events])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        
        # Create timeline plot
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 12))
        
        # Events over time
        event_counts = df.groupby([df['datetime'].dt.floor('1s'), 'event_type']).size().unstack(fill_value=0)
        event_counts.plot(kind='area', ax=ax1, alpha=0.7)
        ax1.set_title(f'{title} - Events Over Time')
        ax1.set_ylabel('Events per Second')
        ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Latency over time
        ax2.scatter(df['datetime'], df['latency_ms'], c=df['latency_ms'], cmap='RdYlBu_r', alpha=0.6)
        ax2.axhline(y=100, color='r', linestyle='--', alpha=0.7, label='100ms threshold')
        ax2.set_title('Event Latency Over Time')
        ax2.set_ylabel('Latency (ms)')
        ax2.legend()
        
        # Validation results
        validation_counts = df.groupby([df['datetime'].dt.floor('5s'), 'validation_result']).size().unstack(fill_value=0)
        validation_counts.plot(kind='bar', ax=ax3, stacked=True, alpha=0.8)
        ax3.set_title('Event Validation Results')
        ax3.set_ylabel('Event Count')
        ax3.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        # Save plot
        filename = f"{title.lower().replace(' ', '_')}_{int(time.time())}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Event timeline saved to: {filepath}")
        return filepath
    
    def create_performance_dashboard(self, events: List[EventMetrics], title: str = "WebSocket Performance Dashboard") -> str:
        """Create a comprehensive performance dashboard."""
        if not events:
            logger.warning("No events for performance dashboard")
            return None
        
        df = pd.DataFrame([e.to_dict() for e in events])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        
        # Create dashboard with multiple subplots
        fig = plt.figure(figsize=(20, 16))
        
        # 1. Event distribution pie chart
        ax1 = plt.subplot(3, 3, 1)
        event_type_counts = df['event_type'].value_counts()
        ax1.pie(event_type_counts.values, labels=event_type_counts.index, autopct='%1.1f%%')
        ax1.set_title('Event Type Distribution')
        
        # 2. Latency histogram
        ax2 = plt.subplot(3, 3, 2)
        ax2.hist(df['latency_ms'], bins=50, alpha=0.7, edgecolor='black')
        ax2.axvline(x=100, color='r', linestyle='--', label='100ms threshold')
        ax2.set_title('Latency Distribution')
        ax2.set_xlabel('Latency (ms)')
        ax2.legend()
        
        # 3. Events per user
        ax3 = plt.subplot(3, 3, 3)
        user_counts = df['user_id'].value_counts().head(10)
        ax3.bar(range(len(user_counts)), user_counts.values)
        ax3.set_title('Top 10 Users by Event Count')
        ax3.set_xlabel('Users')
        ax3.set_ylabel('Event Count')
        ax3.set_xticks(range(len(user_counts)))
        ax3.set_xticklabels([f"User {i+1}" for i in range(len(user_counts))])
        
        # 4. Validation success rate over time
        ax4 = plt.subplot(3, 3, 4)
        df['hour'] = df['datetime'].dt.floor('h')
        validation_by_hour = df.groupby('hour')['validation_result'].apply(
            lambda x: (x == 'valid').sum() / len(x) * 100
        )
        ax4.plot(validation_by_hour.index, validation_by_hour.values, marker='o')
        ax4.set_title('Validation Success Rate Over Time')
        ax4.set_ylabel('Success Rate (%)')
        ax4.tick_params(axis='x', rotation=45)
        
        # 5. Thread activity heatmap
        ax5 = plt.subplot(3, 3, 5)
        thread_activity = df.groupby(['thread_id', df['datetime'].dt.floor('5s')]).size().unstack(fill_value=0)
        if len(thread_activity) > 0:
            im = ax5.imshow(thread_activity.values, aspect='auto', cmap='YlOrRd')
            ax5.set_title('Thread Activity Heatmap')
            plt.colorbar(im, ax=ax5)
        
        # 6. Event sequence completeness
        ax6 = plt.subplot(3, 3, 6)
        sequence_lengths = df.groupby('thread_id').size()
        ax6.hist(sequence_lengths, bins=20, alpha=0.7, edgecolor='black')
        ax6.set_title('Event Sequence Lengths')
        ax6.set_xlabel('Events per Thread')
        ax6.set_ylabel('Thread Count')
        
        # 7. Latency by event type
        ax7 = plt.subplot(3, 3, 7)
        latency_by_type = df.groupby('event_type')['latency_ms'].mean().sort_values(ascending=False)
        ax7.bar(range(len(latency_by_type)), latency_by_type.values)
        ax7.set_title('Average Latency by Event Type')
        ax7.set_xlabel('Event Types')
        ax7.set_ylabel('Average Latency (ms)')
        ax7.set_xticks(range(len(latency_by_type)))
        ax7.set_xticklabels(latency_by_type.index, rotation=45, ha='right')
        
        # 8. Content size distribution
        ax8 = plt.subplot(3, 3, 8)
        ax8.scatter(df['content_size_bytes'], df['latency_ms'], alpha=0.5)
        ax8.set_title('Content Size vs Latency')
        ax8.set_xlabel('Content Size (bytes)')
        ax8.set_ylabel('Latency (ms)')
        
        # 9. Event flow timeline
        ax9 = plt.subplot(3, 3, 9)
        for event_type in df['event_type'].unique():
            type_events = df[df['event_type'] == event_type]
            ax9.scatter(type_events['datetime'], [event_type] * len(type_events), 
                       alpha=0.6, label=event_type, s=20)
        ax9.set_title('Event Flow Timeline')
        ax9.set_xlabel('Time')
        ax9.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax9.tick_params(axis='x', rotation=45)
        
        plt.suptitle(title, fontsize=16, y=0.98)
        plt.tight_layout()
        
        # Save dashboard
        filename = f"{title.lower().replace(' ', '_')}_{int(time.time())}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Performance dashboard saved to: {filepath}")
        return filepath


# ============================================================================
# FAILURE PATTERN DETECTION
# ============================================================================

@dataclass
class FailurePattern:
    """Represents a detected failure pattern in WebSocket events."""
    pattern_type: str
    description: str
    frequency: int
    first_occurrence: float
    last_occurrence: float
    affected_events: List[str]
    severity: str
    recommended_action: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_type": self.pattern_type,
            "description": self.description,
            "frequency": self.frequency,
            "first_occurrence": self.first_occurrence,
            "last_occurrence": self.last_occurrence,
            "affected_events": self.affected_events,
            "severity": self.severity,
            "recommended_action": self.recommended_action,
            "duration_minutes": (self.last_occurrence - self.first_occurrence) / 60
        }


class FailurePatternDetector:
    """Detects and analyzes failure patterns in WebSocket events."""
    
    def __init__(self, min_pattern_frequency: int = 3):
        self.min_pattern_frequency = min_pattern_frequency
        self.detected_patterns: List[FailurePattern] = []
    
    def analyze_events(self, events: List[EventMetrics]) -> List[FailurePattern]:
        """Analyze events for failure patterns."""
        self.detected_patterns = []
        
        if not events:
            return self.detected_patterns
        
        # Sort events by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        
        # Detect various failure patterns
        self._detect_high_latency_patterns(sorted_events)
        self._detect_validation_failure_patterns(sorted_events)
        self._detect_missing_event_patterns(sorted_events)
        self._detect_sequence_disruption_patterns(sorted_events)
        self._detect_user_isolation_violations(sorted_events)
        
        # Sort patterns by severity and frequency
        self.detected_patterns.sort(key=lambda p: (
            {'CRITICAL': 3, 'ERROR': 2, 'WARNING': 1}.get(p.severity, 0),
            p.frequency
        ), reverse=True)
        
        return self.detected_patterns
    
    def _detect_high_latency_patterns(self, events: List[EventMetrics]):
        """Detect patterns of consistently high latency."""
        high_latency_events = [e for e in events if e.latency_ms > 100]
        
        if len(high_latency_events) >= self.min_pattern_frequency:
            # Group by time windows to find sustained high latency
            time_windows = defaultdict(list)
            for event in high_latency_events:
                window = int(event.timestamp // 60)  # 1-minute windows
                time_windows[window].append(event)
            
            # Find windows with multiple high-latency events
            problematic_windows = {w: events for w, events in time_windows.items() 
                                 if len(events) >= self.min_pattern_frequency}
            
            if problematic_windows:
                all_affected = [e.thread_id for events in problematic_windows.values() for e in events]
                
                pattern = FailurePattern(
                    pattern_type="HIGH_LATENCY_SUSTAINED",
                    description=f"Sustained high latency detected across {len(problematic_windows)} time windows",
                    frequency=len(high_latency_events),
                    first_occurrence=min(e.timestamp for e in high_latency_events),
                    last_occurrence=max(e.timestamp for e in high_latency_events),
                    affected_events=all_affected,
                    severity="WARNING" if len(high_latency_events) < 10 else "ERROR",
                    recommended_action="Investigate system performance, check for resource bottlenecks"
                )
                self.detected_patterns.append(pattern)
    
    def _detect_validation_failure_patterns(self, events: List[EventMetrics]):
        """Detect patterns of validation failures."""
        failed_events = [e for e in events if e.validation_result != ValidationResult.VALID.value]
        
        if len(failed_events) >= self.min_pattern_frequency:
            # Group by failure type
            failure_types = defaultdict(list)
            for event in failed_events:
                failure_types[event.validation_result].append(event)
            
            for failure_type, type_events in failure_types.items():
                if len(type_events) >= self.min_pattern_frequency:
                    pattern = FailurePattern(
                        pattern_type=f"VALIDATION_FAILURE_{failure_type.upper()}",
                        description=f"Repeated {failure_type} validation failures",
                        frequency=len(type_events),
                        first_occurrence=min(e.timestamp for e in type_events),
                        last_occurrence=max(e.timestamp for e in type_events),
                        affected_events=[e.thread_id for e in type_events],
                        severity="CRITICAL" if failure_type == ValidationResult.ERROR.value else "ERROR",
                        recommended_action=f"Review event structure and validation rules for {failure_type} failures"
                    )
                    self.detected_patterns.append(pattern)
    
    def _detect_missing_event_patterns(self, events: List[EventMetrics]):
        """Detect patterns of missing required events in sequences."""
        # Group events by thread
        thread_events = defaultdict(list)
        for event in events:
            thread_events[event.thread_id].append(event)
        
        required_events = {
            EventType.AGENT_STARTED.value,
            EventType.AGENT_THINKING.value,
            EventType.TOOL_EXECUTING.value,
            EventType.TOOL_COMPLETED.value,
            EventType.AGENT_COMPLETED.value
        }
        
        incomplete_threads = []
        for thread_id, thread_events_list in thread_events.items():
            event_types = {e.event_type for e in thread_events_list}
            missing_events = required_events - event_types
            
            if missing_events and len(thread_events_list) > 1:  # At least some events present
                incomplete_threads.append({
                    'thread_id': thread_id,
                    'missing_events': missing_events,
                    'present_events': event_types,
                    'timestamp': max(e.timestamp for e in thread_events_list)
                })
        
        if len(incomplete_threads) >= self.min_pattern_frequency:
            # Find most common missing event types
            all_missing = [event for thread in incomplete_threads for event in thread['missing_events']]
            common_missing = Counter(all_missing).most_common(3)
            
            pattern = FailurePattern(
                pattern_type="INCOMPLETE_EVENT_SEQUENCES",
                description=f"Incomplete event sequences detected. Common missing: {[f'{event}({count})' for event, count in common_missing]}",
                frequency=len(incomplete_threads),
                first_occurrence=min(thread['timestamp'] for thread in incomplete_threads),
                last_occurrence=max(thread['timestamp'] for thread in incomplete_threads),
                affected_events=[thread['thread_id'] for thread in incomplete_threads],
                severity="CRITICAL",
                recommended_action="Investigate agent execution pipeline for event generation issues"
            )
            self.detected_patterns.append(pattern)
    
    def _detect_sequence_disruption_patterns(self, events: List[EventMetrics]):
        """Detect patterns where event sequences are disrupted or out of order."""
        expected_order = [
            EventType.AGENT_STARTED.value,
            EventType.AGENT_THINKING.value,
            EventType.TOOL_EXECUTING.value,
            EventType.TOOL_COMPLETED.value,
            EventType.AGENT_COMPLETED.value
        ]
        
        # Group by thread and check ordering
        thread_events = defaultdict(list)
        for event in events:
            thread_events[event.thread_id].append(event)
        
        disordered_threads = []
        for thread_id, thread_events_list in thread_events.items():
            # Sort by sequence position
            sorted_events = sorted(thread_events_list, key=lambda e: e.sequence_position)
            
            # Check if events follow expected order
            event_types = [e.event_type for e in sorted_events if e.event_type in expected_order]
            
            if len(event_types) > 1:
                # Find the correct subsequence in expected order
                expected_indices = []
                for event_type in event_types:
                    try:
                        expected_indices.append(expected_order.index(event_type))
                    except ValueError:
                        continue
                
                # Check if indices are in ascending order
                if expected_indices != sorted(expected_indices):
                    disordered_threads.append({
                        'thread_id': thread_id,
                        'actual_order': event_types,
                        'expected_indices': expected_indices,
                        'timestamp': max(e.timestamp for e in thread_events_list)
                    })
        
        if len(disordered_threads) >= self.min_pattern_frequency:
            pattern = FailurePattern(
                pattern_type="EVENT_SEQUENCE_DISORDER",
                description=f"Event sequences out of expected order in {len(disordered_threads)} threads",
                frequency=len(disordered_threads),
                first_occurrence=min(thread['timestamp'] for thread in disordered_threads),
                last_occurrence=max(thread['timestamp'] for thread in disordered_threads),
                affected_events=[thread['thread_id'] for thread in disordered_threads],
                severity="ERROR",
                recommended_action="Review event emission timing and sequence control logic"
            )
            self.detected_patterns.append(pattern)
    
    def _detect_user_isolation_violations(self, events: List[EventMetrics]):
        """Detect potential user isolation violations."""
        # Look for events that might contain data from multiple users
        user_events = defaultdict(list)
        for event in events:
            if event.user_id:
                user_events[event.user_id].append(event)
        
        # Check for suspicious thread sharing between users
        thread_users = defaultdict(set)
        for event in events:
            if event.user_id:
                thread_users[event.thread_id].add(event.user_id)
        
        # Find threads with multiple users (potential isolation violation)
        shared_threads = {tid: users for tid, users in thread_users.items() if len(users) > 1}
        
        if len(shared_threads) >= self.min_pattern_frequency:
            pattern = FailurePattern(
                pattern_type="USER_ISOLATION_VIOLATION",
                description=f"Thread sharing detected between users: {len(shared_threads)} threads affected",
                frequency=len(shared_threads),
                first_occurrence=min(e.timestamp for e in events if e.thread_id in shared_threads),
                last_occurrence=max(e.timestamp for e in events if e.thread_id in shared_threads),
                affected_events=list(shared_threads.keys()),
                severity="CRITICAL",
                recommended_action="IMMEDIATE: Review user context isolation implementation"
            )
            self.detected_patterns.append(pattern)
    
    def generate_pattern_report(self, output_path: str = None) -> str:
        """Generate a comprehensive failure pattern report."""
        if output_path is None:
            output_path = f"failure_pattern_report_{int(time.time())}.json"
        
        report = {
            "analysis_timestamp": time.time(),
            "analysis_datetime": datetime.now(timezone.utc).isoformat(),
            "total_patterns_detected": len(self.detected_patterns),
            "patterns_by_severity": {
                "CRITICAL": len([p for p in self.detected_patterns if p.severity == "CRITICAL"]),
                "ERROR": len([p for p in self.detected_patterns if p.severity == "ERROR"]),
                "WARNING": len([p for p in self.detected_patterns if p.severity == "WARNING"])
            },
            "patterns": [pattern.to_dict() for pattern in self.detected_patterns],
            "summary": self._generate_summary()
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Failure pattern report saved to: {output_path}")
        return output_path
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate a summary of detected patterns."""
        if not self.detected_patterns:
            return {"status": "healthy", "message": "No failure patterns detected"}
        
        critical_patterns = [p for p in self.detected_patterns if p.severity == "CRITICAL"]
        if critical_patterns:
            return {
                "status": "critical",
                "message": f"{len(critical_patterns)} critical patterns require immediate attention",
                "top_critical": critical_patterns[0].description,
                "recommended_action": critical_patterns[0].recommended_action
            }
        
        error_patterns = [p for p in self.detected_patterns if p.severity == "ERROR"]
        if error_patterns:
            return {
                "status": "degraded",
                "message": f"{len(error_patterns)} error patterns detected",
                "top_error": error_patterns[0].description,
                "recommended_action": error_patterns[0].recommended_action
            }
        
        return {
            "status": "warning",
            "message": f"{len(self.detected_patterns)} warning patterns detected",
            "action_required": "Monitor and investigate if patterns persist"
        }


# ============================================================================
# COMPREHENSIVE MONITORING ORCHESTRATOR
# ============================================================================

class WebSocketMonitoringOrchestrator:
    """Orchestrates comprehensive WebSocket monitoring and analysis."""
    
    def __init__(self, output_dir: str = "websocket_monitoring"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize components
        self.real_time_monitor = RealTimeEventMonitor()
        self.visualizer = EventTimelineVisualizer(os.path.join(output_dir, "visualizations"))
        self.pattern_detector = FailurePatternDetector()
        
        # Setup alert logging
        self._setup_alert_logging()
        
        # Monitoring state
        self.monitoring_active = False
        self.report_generation_active = False
    
    def _setup_alert_logging(self):
        """Setup alert logging and callbacks."""
        def alert_logger(alert: Dict[str, Any]):
            alert_log_path = os.path.join(self.output_dir, "alerts.log")
            with open(alert_log_path, "a") as f:
                f.write(f"{datetime.now().isoformat()} - {alert['severity']} - {alert['message']}\n")
        
        self.real_time_monitor.add_alert_callback(alert_logger)
    
    @contextmanager
    def monitor_session(self, session_name: str = None):
        """Context manager for a complete monitoring session."""
        session_name = session_name or f"monitoring_session_{int(time.time())}"
        session_dir = os.path.join(self.output_dir, session_name)
        os.makedirs(session_dir, exist_ok=True)
        
        logger.info(f"Starting monitoring session: {session_name}")
        
        # Start real-time monitoring
        self.real_time_monitor.start_monitoring()
        self.monitoring_active = True
        
        try:
            yield self
        finally:
            # Stop monitoring and generate reports
            self.real_time_monitor.stop_monitoring()
            self.monitoring_active = False
            
            # Generate comprehensive reports
            self._generate_session_reports(session_dir)
            
            logger.info(f"Monitoring session completed: {session_name}")
    
    def record_event(self, validated_event: ValidatedEvent) -> EventMetrics:
        """Record an event during monitoring."""
        if not self.monitoring_active:
            logger.warning("Attempting to record event but monitoring is not active")
            return None
        
        return self.real_time_monitor.record_event(validated_event)
    
    def _generate_session_reports(self, session_dir: str):
        """Generate comprehensive reports for the monitoring session."""
        logger.info("Generating monitoring session reports...")
        
        # Get all recorded events
        all_events = self.real_time_monitor.all_events
        
        if not all_events:
            logger.warning("No events recorded during session")
            return
        
        # Generate visualizations
        timeline_path = self.visualizer.create_event_timeline(
            all_events, "Session Event Timeline"
        )
        dashboard_path = self.visualizer.create_performance_dashboard(
            all_events, "Session Performance Dashboard"
        )
        
        # Detect failure patterns
        patterns = self.pattern_detector.analyze_events(all_events)
        pattern_report_path = self.pattern_detector.generate_pattern_report(
            os.path.join(session_dir, "failure_patterns.json")
        )
        
        # Generate summary report
        summary_report = {
            "session_summary": self.real_time_monitor.get_current_metrics(),
            "visualizations": {
                "timeline": timeline_path,
                "dashboard": dashboard_path
            },
            "failure_analysis": {
                "patterns_detected": len(patterns),
                "pattern_report": pattern_report_path,
                "critical_issues": [p.to_dict() for p in patterns if p.severity == "CRITICAL"]
            },
            "recommendations": self._generate_recommendations(patterns)
        }
        
        # Save summary report
        summary_path = os.path.join(session_dir, "monitoring_summary.json")
        with open(summary_path, 'w') as f:
            json.dump(summary_report, f, indent=2)
        
        logger.info(f"Session reports generated in: {session_dir}")
        logger.info(f"Summary: {summary_path}")
        
        # Log key findings
        self._log_key_findings(summary_report)
    
    def _generate_recommendations(self, patterns: List[FailurePattern]) -> List[str]:
        """Generate actionable recommendations based on detected patterns."""
        recommendations = []
        
        if not patterns:
            recommendations.append("✓ No failure patterns detected - system operating normally")
            return recommendations
        
        critical_patterns = [p for p in patterns if p.severity == "CRITICAL"]
        if critical_patterns:
            recommendations.append("🚨 CRITICAL ISSUES REQUIRE IMMEDIATE ATTENTION:")
            for pattern in critical_patterns[:3]:  # Top 3 critical issues
                recommendations.append(f"  - {pattern.description}: {pattern.recommended_action}")
        
        error_patterns = [p for p in patterns if p.severity == "ERROR"]
        if error_patterns:
            recommendations.append("⚠️ Error patterns requiring investigation:")
            for pattern in error_patterns[:3]:
                recommendations.append(f"  - {pattern.description}: {pattern.recommended_action}")
        
        # General recommendations based on pattern types
        pattern_types = {p.pattern_type for p in patterns}
        
        if any("HIGH_LATENCY" in pt for pt in pattern_types):
            recommendations.append("💡 Performance optimization recommended: Review system resources and optimize slow operations")
        
        if any("VALIDATION_FAILURE" in pt for pt in pattern_types):
            recommendations.append("🔧 Data validation issues: Review event schemas and validation logic")
        
        if any("USER_ISOLATION" in pt for pt in pattern_types):
            recommendations.append("🛡️ Security concern: Urgent review of user context isolation implementation")
        
        if any("INCOMPLETE" in pt for pt in pattern_types):
            recommendations.append("🔄 Event sequence issues: Investigate agent execution pipeline reliability")
        
        return recommendations
    
    def _log_key_findings(self, summary_report: Dict[str, Any]):
        """Log key findings from the monitoring session."""
        session_summary = summary_report["session_summary"]
        failure_analysis = summary_report["failure_analysis"]
        
        logger.info("=" * 60)
        logger.info("WEBSOCKET MONITORING SESSION - KEY FINDINGS")
        logger.info("=" * 60)
        
        logger.info(f"📊 EVENT METRICS:")
        logger.info(f"  Total Events: {session_summary.get('total_events', 0)}")
        logger.info(f"  Success Rate: {session_summary.get('success_rate_percent', 0):.1f}%")
        logger.info(f"  Avg Latency: {session_summary.get('recent_performance', {}).get('avg_latency_ms', 0):.1f}ms")
        logger.info(f"  Active Users: {session_summary.get('active_users', 0)}")
        logger.info(f"  Active Threads: {session_summary.get('active_threads', 0)}")
        
        logger.info(f"\n🔍 FAILURE ANALYSIS:")
        logger.info(f"  Patterns Detected: {failure_analysis.get('patterns_detected', 0)}")
        logger.info(f"  Critical Issues: {len(failure_analysis.get('critical_issues', []))}")
        
        if failure_analysis.get('critical_issues'):
            logger.info(f"  🚨 TOP CRITICAL ISSUE: {failure_analysis['critical_issues'][0].get('description', 'N/A')}")
        
        logger.info(f"\n💡 RECOMMENDATIONS:")
        for rec in summary_report.get("recommendations", [])[:5]:
            logger.info(f"  {rec}")
        
        logger.info("=" * 60)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_monitoring_session(session_name: str = None, output_dir: str = "websocket_monitoring") -> WebSocketMonitoringOrchestrator:
    """Create a new monitoring session."""
    return WebSocketMonitoringOrchestrator(output_dir)


def quick_event_analysis(events: List[EventMetrics], output_dir: str = "quick_analysis") -> Dict[str, Any]:
    """Perform quick analysis on a list of events."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Create visualizer and pattern detector
    visualizer = EventTimelineVisualizer(output_dir)
    pattern_detector = FailurePatternDetector()
    
    # Generate visualizations
    timeline_path = visualizer.create_event_timeline(events, "Quick Analysis Timeline")
    dashboard_path = visualizer.create_performance_dashboard(events, "Quick Analysis Dashboard")
    
    # Detect patterns
    patterns = pattern_detector.analyze_events(events)
    
    # Generate summary
    summary = {
        "analysis_timestamp": time.time(),
        "total_events": len(events),
        "event_types": list(set(e.event_type for e in events)),
        "time_span_minutes": (max(e.timestamp for e in events) - min(e.timestamp for e in events)) / 60 if events else 0,
        "avg_latency_ms": statistics.mean(e.latency_ms for e in events) if events else 0,
        "patterns_detected": len(patterns),
        "critical_patterns": len([p for p in patterns if p.severity == "CRITICAL"]),
        "visualizations": {
            "timeline": timeline_path,
            "dashboard": dashboard_path
        },
        "top_patterns": [p.to_dict() for p in patterns[:5]]
    }
    
    logger.info(f"Quick analysis completed: {len(events)} events analyzed, {len(patterns)} patterns detected")
    return summary


if __name__ == "__main__":
    """Example usage of WebSocket monitoring utilities."""
    logger.info("WebSocket Monitoring Utilities - Example Usage")
    
    # Create a sample monitoring session
    orchestrator = create_monitoring_session("example_session")
    
    # Example of how to use the monitoring session
    with orchestrator.monitor_session("example_monitoring"):
        logger.info("Monitoring session active - ready to record WebSocket events")
        logger.info("Use orchestrator.record_event(validated_event) to record events")
        
        # In a real scenario, events would be recorded here
        # For example:
        # orchestrator.record_event(some_validated_event)
        
        time.sleep(1)  # Simulate some monitoring time
    
    logger.info("Example monitoring session completed")