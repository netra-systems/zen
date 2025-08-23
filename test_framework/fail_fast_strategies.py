#!/usr/bin/env python3
"""
Fail-Fast Strategies Module - Intelligent failure handling and early termination
Provides comprehensive fail-fast strategies with dependency-based skipping
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Callable, Any
import statistics


class FailFastMode(Enum):
    """Fail-fast execution modes"""
    DISABLED = "disabled"           # No fail-fast behavior
    FIRST_FAILURE = "first_failure" # Stop on first test failure
    CATEGORY_FAILURE = "category_failure" # Stop category on first failure in that category
    CRITICAL_FAILURE = "critical_failure" # Stop only on critical test failures
    THRESHOLD_BASED = "threshold_based" # Stop when failure rate exceeds threshold
    SMART_ADAPTIVE = "smart_adaptive" # Adaptive fail-fast based on historical data
    DEPENDENCY_AWARE = "dependency_aware" # Stop based on dependency impact


class FailureImpact(Enum):
    """Impact levels of test failures"""
    LOW = "low"           # Minor failures, continue execution
    MEDIUM = "medium"     # Moderate failures, consider stopping
    HIGH = "high"         # Major failures, likely to stop
    CRITICAL = "critical" # Critical failures, must stop


class SkipReason(Enum):
    """Reasons for skipping tests"""
    DEPENDENCY_FAILED = "dependency_failed"
    CATEGORY_FAILED = "category_failed"
    THRESHOLD_EXCEEDED = "threshold_exceeded"
    CRITICAL_FAILURE = "critical_failure"
    RESOURCE_UNAVAILABLE = "resource_unavailable"
    TIME_LIMIT_EXCEEDED = "time_limit_exceeded"
    USER_CANCELLED = "user_cancelled"
    ENVIRONMENT_ERROR = "environment_error"


@dataclass
class FailureEvent:
    """Represents a test failure event"""
    test_name: str
    category: str
    failure_time: datetime
    error_message: str
    error_type: str
    
    # Impact assessment
    impact_level: FailureImpact = FailureImpact.MEDIUM
    affects_categories: Set[str] = field(default_factory=set)
    affects_dependencies: Set[str] = field(default_factory=set)
    
    # Context information
    execution_duration: timedelta = field(default_factory=lambda: timedelta(0))
    retry_count: int = 0
    max_retries: int = 0
    
    # Additional metadata
    tags: Set[str] = field(default_factory=set)
    markers: Set[str] = field(default_factory=set)
    stack_trace: Optional[str] = None
    
    def __post_init__(self):
        """Initialize computed properties"""
        if isinstance(self.affects_categories, (list, tuple)):
            self.affects_categories = set(self.affects_categories)
        if isinstance(self.affects_dependencies, (list, tuple)):
            self.affects_dependencies = set(self.affects_dependencies)
        if isinstance(self.tags, (list, tuple)):
            self.tags = set(self.tags)
        if isinstance(self.markers, (list, tuple)):
            self.markers = set(self.markers)
    
    @property
    def is_retriable(self) -> bool:
        """Check if this failure is retriable"""
        return (self.retry_count < self.max_retries and 
                self.impact_level in [FailureImpact.LOW, FailureImpact.MEDIUM] and
                "flaky" in self.tags)
    
    @property
    def is_critical(self) -> bool:
        """Check if this is a critical failure"""
        return (self.impact_level == FailureImpact.CRITICAL or
                "critical" in self.markers or
                "smoke" in self.markers)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "test_name": self.test_name,
            "category": self.category,
            "failure_time": self.failure_time.isoformat(),
            "error_message": self.error_message,
            "error_type": self.error_type,
            "impact_level": self.impact_level.value,
            "affects_categories": list(self.affects_categories),
            "affects_dependencies": list(self.affects_dependencies),
            "execution_duration": self.execution_duration.total_seconds(),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "tags": list(self.tags),
            "markers": list(self.markers),
            "stack_trace": self.stack_trace,
            "is_retriable": self.is_retriable,
            "is_critical": self.is_critical
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FailureEvent':
        """Create from dictionary"""
        event = cls(
            test_name=data["test_name"],
            category=data["category"],
            failure_time=datetime.fromisoformat(data["failure_time"]),
            error_message=data["error_message"],
            error_type=data["error_type"],
            impact_level=FailureImpact(data.get("impact_level", "medium")),
            affects_categories=set(data.get("affects_categories", [])),
            affects_dependencies=set(data.get("affects_dependencies", [])),
            execution_duration=timedelta(seconds=data.get("execution_duration", 0)),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 0),
            tags=set(data.get("tags", [])),
            markers=set(data.get("markers", [])),
            stack_trace=data.get("stack_trace")
        )
        
        return event


@dataclass
class SkipDecision:
    """Decision to skip tests with reasoning"""
    tests_to_skip: Set[str] = field(default_factory=set)
    categories_to_skip: Set[str] = field(default_factory=set)
    reason: SkipReason = SkipReason.DEPENDENCY_FAILED
    reasoning: str = ""
    
    # Impact assessment
    estimated_time_saved: timedelta = field(default_factory=lambda: timedelta(0))
    tests_affected: int = 0
    
    # Decision metadata
    decided_at: datetime = field(default_factory=datetime.now)
    confidence_score: float = 1.0  # How confident are we in this decision (0-1)
    
    def __post_init__(self):
        """Initialize computed properties"""
        if isinstance(self.tests_to_skip, (list, tuple)):
            self.tests_to_skip = set(self.tests_to_skip)
        if isinstance(self.categories_to_skip, (list, tuple)):
            self.categories_to_skip = set(self.categories_to_skip)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "tests_to_skip": list(self.tests_to_skip),
            "categories_to_skip": list(self.categories_to_skip),
            "reason": self.reason.value,
            "reasoning": self.reasoning,
            "estimated_time_saved": self.estimated_time_saved.total_seconds(),
            "tests_affected": self.tests_affected,
            "decided_at": self.decided_at.isoformat(),
            "confidence_score": self.confidence_score
        }


@dataclass
class ThresholdConfig:
    """Configuration for threshold-based fail-fast"""
    failure_rate_threshold: float = 0.3  # Stop if failure rate exceeds 30%
    critical_failure_count: int = 1      # Stop after 1 critical failure
    consecutive_failures: int = 5        # Stop after 5 consecutive failures
    time_window: timedelta = field(default_factory=lambda: timedelta(minutes=5))  # Evaluation window
    
    # Category-specific thresholds
    category_thresholds: Dict[str, float] = field(default_factory=dict)
    
    # Minimum sample size before applying thresholds
    min_sample_size: int = 10
    
    def get_threshold_for_category(self, category: str) -> float:
        """Get failure rate threshold for specific category"""
        return self.category_thresholds.get(category, self.failure_rate_threshold)


class FailFastStrategy:
    """Comprehensive fail-fast strategy implementation"""
    
    def __init__(self, project_root: Path, mode: FailFastMode = FailFastMode.SMART_ADAPTIVE):
        self.project_root = project_root
        self.mode = mode
        self.threshold_config = ThresholdConfig()
        
        # State tracking
        self.failure_events: List[FailureEvent] = []
        self.skip_decisions: List[SkipDecision] = []
        self.category_failures: Dict[str, List[FailureEvent]] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}
        
        # Historical data
        self.historical_data_file = project_root / "test_reports" / "failure_history.json"
        self.historical_data: Dict[str, Dict] = {}
        self._load_historical_data()
        
        # Callbacks
        self._failure_callbacks: List[Callable[[FailureEvent], None]] = []
        self._skip_callbacks: List[Callable[[SkipDecision], None]] = []
    
    def _load_historical_data(self):
        """Load historical failure data"""
        if not self.historical_data_file.exists():
            return
        
        try:
            with open(self.historical_data_file) as f:
                self.historical_data = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load failure history: {e}")
            self.historical_data = {}
    
    def _save_historical_data(self):
        """Save historical failure data"""
        try:
            self.historical_data_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.historical_data_file, 'w') as f:
                json.dump(self.historical_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save failure history: {e}")
    
    def set_dependency_graph(self, dependencies: Dict[str, Set[str]]):
        """Set the test dependency graph"""
        self.dependency_graph = dependencies
    
    def set_threshold_config(self, config: ThresholdConfig):
        """Set threshold configuration"""
        self.threshold_config = config
    
    def add_failure_callback(self, callback: Callable[[FailureEvent], None]):
        """Add callback for failure events"""
        self._failure_callbacks.append(callback)
    
    def add_skip_callback(self, callback: Callable[[SkipDecision], None]):
        """Add callback for skip decisions"""
        self._skip_callbacks.append(callback)
    
    def record_failure(self, test_name: str, category: str, error_message: str,
                      error_type: str, execution_duration: timedelta = None,
                      stack_trace: str = None, tags: Set[str] = None,
                      markers: Set[str] = None) -> FailureEvent:
        """Record a test failure and assess its impact"""
        
        # Create failure event
        failure_event = FailureEvent(
            test_name=test_name,
            category=category,
            failure_time=datetime.now(),
            error_message=error_message,
            error_type=error_type,
            execution_duration=execution_duration or timedelta(0),
            tags=tags or set(),
            markers=markers or set(),
            stack_trace=stack_trace
        )
        
        # Assess impact level
        failure_event.impact_level = self._assess_failure_impact(failure_event)
        
        # Determine affected categories and dependencies
        failure_event.affects_categories = self._get_affected_categories(failure_event)
        failure_event.affects_dependencies = self._get_affected_dependencies(test_name)
        
        # Store failure event
        self.failure_events.append(failure_event)
        
        # Update category failures
        if category not in self.category_failures:
            self.category_failures[category] = []
        self.category_failures[category].append(failure_event)
        
        # Update historical data
        self._update_historical_data(failure_event)
        
        # Notify callbacks
        for callback in self._failure_callbacks:
            try:
                callback(failure_event)
            except Exception as e:
                print(f"Error in failure callback: {e}")
        
        return failure_event
    
    def should_fail_fast(self, current_stats: Dict[str, Any] = None) -> Tuple[bool, Optional[SkipDecision]]:
        """Determine if execution should stop and what to skip"""
        
        if self.mode == FailFastMode.DISABLED:
            return False, None
        
        # Get current execution statistics
        stats = current_stats or self._calculate_current_stats()
        
        # Apply strategy-specific logic
        if self.mode == FailFastMode.FIRST_FAILURE:
            return self._check_first_failure()
        elif self.mode == FailFastMode.CATEGORY_FAILURE:
            return self._check_category_failure()
        elif self.mode == FailFastMode.CRITICAL_FAILURE:
            return self._check_critical_failure()
        elif self.mode == FailFastMode.THRESHOLD_BASED:
            return self._check_threshold_based(stats)
        elif self.mode == FailFastMode.SMART_ADAPTIVE:
            return self._check_smart_adaptive(stats)
        elif self.mode == FailFastMode.DEPENDENCY_AWARE:
            return self._check_dependency_aware(stats)
        else:
            return False, None
    
    def _assess_failure_impact(self, failure_event: FailureEvent) -> FailureImpact:
        """Assess the impact level of a failure"""
        
        # Critical markers indicate critical impact
        if any(marker in failure_event.markers for marker in ['critical', 'smoke', 'startup']):
            return FailureImpact.CRITICAL
        
        # Check error type patterns
        critical_patterns = [
            'connectionerror', 'databaseerror', 'systemerror', 
            'importerror', 'syntaxerror', 'indentationerror'
        ]
        
        error_lower = failure_event.error_message.lower()
        if any(pattern in error_lower for pattern in critical_patterns):
            return FailureImpact.HIGH
        
        # Check historical failure patterns
        test_history = self.historical_data.get(failure_event.test_name, {})
        if test_history.get('failure_rate', 0) > 0.8:  # Consistently failing
            return FailureImpact.HIGH
        elif test_history.get('flaky', False):
            return FailureImpact.LOW
        
        # Check category context
        category_history = self._get_category_failure_stats(failure_event.category)
        if category_history['recent_failure_rate'] > 0.5:
            return FailureImpact.HIGH
        
        # Default to medium impact
        return FailureImpact.MEDIUM
    
    def _get_affected_categories(self, failure_event: FailureEvent) -> Set[str]:
        """Determine which categories are affected by this failure"""
        affected = {failure_event.category}
        
        # If it's a critical infrastructure failure, it might affect multiple categories
        if failure_event.impact_level == FailureImpact.CRITICAL:
            critical_patterns = {
                'database': {'database', 'integration', 'api'},
                'redis': {'websocket', 'api', 'integration'},
                'network': {'integration', 'api', 'e2e'},
                'auth': {'security', 'api', 'integration'},
                'startup': {'smoke', 'unit', 'integration', 'api'}
            }
            
            error_lower = failure_event.error_message.lower()
            for pattern, categories in critical_patterns.items():
                if pattern in error_lower:
                    affected.update(categories)
                    break
        
        return affected
    
    def _get_affected_dependencies(self, test_name: str) -> Set[str]:
        """Get tests that depend on the failed test"""
        affected = set()
        
        # Direct dependencies
        for test, deps in self.dependency_graph.items():
            if test_name in deps:
                affected.add(test)
        
        # Transitive dependencies (one level)
        for dependent in affected.copy():
            for test, deps in self.dependency_graph.items():
                if dependent in deps:
                    affected.add(test)
        
        return affected
    
    def _calculate_current_stats(self) -> Dict[str, Any]:
        """Calculate current execution statistics"""
        if not self.failure_events:
            return {
                'total_failures': 0,
                'failure_rate': 0.0,
                'critical_failures': 0,
                'consecutive_failures': 0,
                'category_stats': {}
            }
        
        recent_window = datetime.now() - self.threshold_config.time_window
        recent_failures = [f for f in self.failure_events if f.failure_time >= recent_window]
        
        # Calculate consecutive failures
        consecutive = 0
        for event in reversed(self.failure_events):
            if event.failure_time >= recent_window:
                consecutive += 1
            else:
                break
        
        # Category statistics
        category_stats = {}
        for category, failures in self.category_failures.items():
            recent_cat_failures = [f for f in failures if f.failure_time >= recent_window]
            category_stats[category] = {
                'total_failures': len(failures),
                'recent_failures': len(recent_cat_failures),
                'critical_failures': len([f for f in failures if f.is_critical]),
                'last_failure_time': max((f.failure_time for f in failures), default=None)
            }
        
        return {
            'total_failures': len(self.failure_events),
            'recent_failures': len(recent_failures),
            'critical_failures': len([f for f in self.failure_events if f.is_critical]),
            'consecutive_failures': consecutive,
            'category_stats': category_stats,
            'last_failure_time': max((f.failure_time for f in self.failure_events), default=None)
        }
    
    def _check_first_failure(self) -> Tuple[bool, Optional[SkipDecision]]:
        """Check first failure strategy"""
        if self.failure_events:
            decision = SkipDecision(
                reason=SkipReason.CRITICAL_FAILURE,
                reasoning="First failure detected - stopping execution",
                confidence_score=1.0
            )
            return True, decision
        return False, None
    
    def _check_category_failure(self) -> Tuple[bool, Optional[SkipDecision]]:
        """Check category failure strategy"""
        for category, failures in self.category_failures.items():
            if failures:  # Any failure in category
                decision = SkipDecision(
                    categories_to_skip={category},
                    reason=SkipReason.CATEGORY_FAILED,
                    reasoning=f"Category '{category}' has failures - skipping remaining tests in category",
                    confidence_score=0.8
                )
                return True, decision
        return False, None
    
    def _check_critical_failure(self) -> Tuple[bool, Optional[SkipDecision]]:
        """Check critical failure strategy"""
        critical_failures = [f for f in self.failure_events if f.is_critical]
        
        if len(critical_failures) >= self.threshold_config.critical_failure_count:
            decision = SkipDecision(
                reason=SkipReason.CRITICAL_FAILURE,
                reasoning=f"Critical failure detected: {critical_failures[-1].test_name}",
                confidence_score=1.0
            )
            return True, decision
        
        return False, None
    
    def _check_threshold_based(self, stats: Dict[str, Any]) -> Tuple[bool, Optional[SkipDecision]]:
        """Check threshold-based strategy"""
        
        # Check overall failure rate (need minimum sample size)
        if stats['recent_failures'] >= self.threshold_config.min_sample_size:
            # Approximate failure rate (assuming some tests passed)
            estimated_total_tests = stats['recent_failures'] * 2  # Conservative estimate
            failure_rate = stats['recent_failures'] / estimated_total_tests
            
            if failure_rate > self.threshold_config.failure_rate_threshold:
                decision = SkipDecision(
                    reason=SkipReason.THRESHOLD_EXCEEDED,
                    reasoning=f"Failure rate {failure_rate:.2%} exceeds threshold {self.threshold_config.failure_rate_threshold:.2%}",
                    confidence_score=0.9
                )
                return True, decision
        
        # Check consecutive failures
        if stats['consecutive_failures'] >= self.threshold_config.consecutive_failures:
            decision = SkipDecision(
                reason=SkipReason.THRESHOLD_EXCEEDED,
                reasoning=f"Too many consecutive failures: {stats['consecutive_failures']}",
                confidence_score=0.9
            )
            return True, decision
        
        # Check critical failure count
        if stats['critical_failures'] >= self.threshold_config.critical_failure_count:
            decision = SkipDecision(
                reason=SkipReason.CRITICAL_FAILURE,
                reasoning=f"Critical failure count exceeded: {stats['critical_failures']}",
                confidence_score=1.0
            )
            return True, decision
        
        return False, None
    
    def _check_smart_adaptive(self, stats: Dict[str, Any]) -> Tuple[bool, Optional[SkipDecision]]:
        """Check smart adaptive strategy"""
        
        # Combine multiple strategies with confidence weighting
        strategies_results = [
            self._check_critical_failure(),
            self._check_threshold_based(stats),
            self._check_dependency_aware(stats)
        ]
        
        # If any critical strategy says stop, stop immediately
        for should_stop, decision in strategies_results:
            if should_stop and decision and decision.reason == SkipReason.CRITICAL_FAILURE:
                decision.confidence_score = min(1.0, decision.confidence_score + 0.1)
                return True, decision
        
        # Use weighted decision making for non-critical cases
        stop_votes = sum(1 for should_stop, _ in strategies_results if should_stop)
        total_confidence = sum(decision.confidence_score for should_stop, decision in strategies_results 
                             if should_stop and decision)
        
        if stop_votes >= 2 or (stop_votes >= 1 and total_confidence > 0.8):
            # Choose the decision with highest confidence
            best_decision = max((decision for should_stop, decision in strategies_results 
                               if should_stop and decision), 
                              key=lambda d: d.confidence_score, default=None)
            
            if best_decision:
                best_decision.reasoning = f"Smart adaptive: {best_decision.reasoning}"
                return True, best_decision
        
        return False, None
    
    def _check_dependency_aware(self, stats: Dict[str, Any]) -> Tuple[bool, Optional[SkipDecision]]:
        """Check dependency-aware strategy"""
        
        # Find tests that should be skipped due to dependency failures
        tests_to_skip = set()
        categories_to_skip = set()
        
        for failure in self.failure_events:
            # Skip tests that depend on failed tests
            dependent_tests = self._get_affected_dependencies(failure.test_name)
            tests_to_skip.update(dependent_tests)
            
            # Skip categories affected by critical failures
            if failure.impact_level in [FailureImpact.HIGH, FailureImpact.CRITICAL]:
                categories_to_skip.update(failure.affects_categories)
        
        if tests_to_skip or categories_to_skip:
            decision = SkipDecision(
                tests_to_skip=tests_to_skip,
                categories_to_skip=categories_to_skip,
                reason=SkipReason.DEPENDENCY_FAILED,
                reasoning=f"Skipping {len(tests_to_skip)} tests and {len(categories_to_skip)} categories due to dependency failures",
                tests_affected=len(tests_to_skip),
                confidence_score=0.7
            )
            
            # Don't fail fast completely, just skip affected tests
            return False, decision
        
        return False, None
    
    def _get_category_failure_stats(self, category: str) -> Dict[str, float]:
        """Get failure statistics for a category"""
        failures = self.category_failures.get(category, [])
        
        if not failures:
            return {
                'total_failures': 0,
                'recent_failure_rate': 0.0,
                'avg_time_between_failures': 0.0
            }
        
        recent_window = datetime.now() - self.threshold_config.time_window
        recent_failures = [f for f in failures if f.failure_time >= recent_window]
        
        # Estimate failure rate (conservative)
        recent_failure_rate = len(recent_failures) / max(10, len(recent_failures) * 2)
        
        # Calculate average time between failures
        avg_time_between = timedelta(0)
        if len(failures) > 1:
            time_diffs = []
            for i in range(1, len(failures)):
                time_diff = failures[i].failure_time - failures[i-1].failure_time
                time_diffs.append(time_diff.total_seconds())
            avg_time_between = timedelta(seconds=statistics.mean(time_diffs))
        
        return {
            'total_failures': len(failures),
            'recent_failures': len(recent_failures),
            'recent_failure_rate': recent_failure_rate,
            'avg_time_between_failures': avg_time_between.total_seconds()
        }
    
    def _update_historical_data(self, failure_event: FailureEvent):
        """Update historical failure data"""
        test_name = failure_event.test_name
        
        if test_name not in self.historical_data:
            self.historical_data[test_name] = {
                'total_runs': 0,
                'total_failures': 0,
                'last_failure_time': None,
                'failure_types': {},
                'avg_failure_duration': 0,
                'flaky': False
            }
        
        history = self.historical_data[test_name]
        history['total_runs'] += 1
        history['total_failures'] += 1
        history['last_failure_time'] = failure_event.failure_time.isoformat()
        
        # Track failure types
        error_type = failure_event.error_type
        if error_type not in history['failure_types']:
            history['failure_types'][error_type] = 0
        history['failure_types'][error_type] += 1
        
        # Update failure rate
        history['failure_rate'] = history['total_failures'] / history['total_runs']
        
        # Update average failure duration
        current_avg = history.get('avg_failure_duration', 0)
        new_duration = failure_event.execution_duration.total_seconds()
        history['avg_failure_duration'] = (current_avg + new_duration) / 2
        
        # Detect flaky tests
        if (history['total_runs'] >= 5 and 
            0.2 < history['failure_rate'] < 0.8 and
            len(history['failure_types']) > 1):
            history['flaky'] = True
        
        # Periodically save
        if len(self.failure_events) % 10 == 0:
            self._save_historical_data()
    
    def make_skip_decision(self, skip_decision: SkipDecision):
        """Execute a skip decision"""
        self.skip_decisions.append(skip_decision)
        
        # Notify callbacks
        for callback in self._skip_callbacks:
            try:
                callback(skip_decision)
            except Exception as e:
                print(f"Error in skip callback: {e}")
    
    def get_failure_summary(self) -> Dict[str, Any]:
        """Get comprehensive failure summary"""
        if not self.failure_events:
            return {
                'total_failures': 0,
                'categories_affected': 0,
                'critical_failures': 0,
                'skip_decisions_made': len(self.skip_decisions)
            }
        
        critical_failures = [f for f in self.failure_events if f.is_critical]
        
        # Group failures by error type
        error_types = {}
        for failure in self.failure_events:
            error_type = failure.error_type
            if error_type not in error_types:
                error_types[error_type] = []
            error_types[error_type].append(failure)
        
        # Most common failure patterns
        failure_patterns = {}
        for failure in self.failure_events:
            # Extract pattern from error message
            pattern = self._extract_error_pattern(failure.error_message)
            if pattern not in failure_patterns:
                failure_patterns[pattern] = 0
            failure_patterns[pattern] += 1
        
        return {
            'total_failures': len(self.failure_events),
            'categories_affected': len(self.category_failures),
            'critical_failures': len(critical_failures),
            'skip_decisions_made': len(self.skip_decisions),
            'failure_by_category': {
                category: len(failures) 
                for category, failures in self.category_failures.items()
            },
            'failure_by_error_type': {
                error_type: len(failures)
                for error_type, failures in error_types.items()
            },
            'common_failure_patterns': dict(sorted(failure_patterns.items(), 
                                                 key=lambda x: x[1], reverse=True)[:10]),
            'first_failure_time': min((f.failure_time for f in self.failure_events), default=None),
            'last_failure_time': max((f.failure_time for f in self.failure_events), default=None),
            'average_failure_duration': statistics.mean(
                [f.execution_duration.total_seconds() for f in self.failure_events if f.execution_duration]
            ) if any(f.execution_duration for f in self.failure_events) else 0
        }
    
    def _extract_error_pattern(self, error_message: str) -> str:
        """Extract a pattern from error message for grouping"""
        # Simple pattern extraction - can be enhanced
        error_lower = error_message.lower()
        
        common_patterns = [
            ('connection', 'connection error'),
            ('timeout', 'timeout error'),
            ('assertion', 'assertion error'),
            ('import', 'import error'),
            ('syntax', 'syntax error'),
            ('indentation', 'indentation error'),
            ('attribute', 'attribute error'),
            ('key', 'key error'),
            ('type', 'type error'),
            ('value', 'value error')
        ]
        
        for pattern, description in common_patterns:
            if pattern in error_lower:
                return description
        
        return 'other error'
    
    def export_failure_report(self, output_path: Path):
        """Export detailed failure report"""
        report = {
            'summary': self.get_failure_summary(),
            'failure_events': [event.to_dict() for event in self.failure_events],
            'skip_decisions': [decision.to_dict() for decision in self.skip_decisions],
            'category_failures': {
                category: [event.to_dict() for event in events]
                for category, events in self.category_failures.items()
            },
            'strategy_config': {
                'mode': self.mode.value,
                'threshold_config': {
                    'failure_rate_threshold': self.threshold_config.failure_rate_threshold,
                    'critical_failure_count': self.threshold_config.critical_failure_count,
                    'consecutive_failures': self.threshold_config.consecutive_failures,
                    'time_window': self.threshold_config.time_window.total_seconds(),
                    'min_sample_size': self.threshold_config.min_sample_size
                }
            },
            'generated_at': datetime.now().isoformat()
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
    
    def reset(self):
        """Reset strategy state for new test run"""
        self.failure_events.clear()
        self.skip_decisions.clear()
        self.category_failures.clear()
    
    def get_recommended_retries(self, test_name: str) -> int:
        """Get recommended retry count for a test based on historical data"""
        history = self.historical_data.get(test_name, {})
        
        if history.get('flaky', False):
            return min(3, max(1, int(1 / max(0.1, history.get('failure_rate', 0.5)))))
        elif history.get('failure_rate', 0) > 0.8:
            return 0  # Don't retry consistently failing tests
        else:
            return 1  # Default retry once
    
    def should_retry_test(self, test_name: str, current_attempt: int) -> bool:
        """Determine if a test should be retried"""
        max_retries = self.get_recommended_retries(test_name)
        
        if current_attempt >= max_retries:
            return False
        
        # Don't retry if we're in critical failure mode
        if any(f.test_name == test_name and f.is_critical for f in self.failure_events):
            return False
        
        # Check if test has failed too recently
        recent_failures = [f for f in self.failure_events 
                         if f.test_name == test_name and 
                         f.failure_time > datetime.now() - timedelta(minutes=5)]
        
        return len(recent_failures) <= max_retries