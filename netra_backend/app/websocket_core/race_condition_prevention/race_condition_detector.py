"""
WebSocket Race Condition Detector

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Detect and prevent WebSocket race conditions before they cause failures
- Value Impact: Proactive race condition detection prevents customer experience disruption
- Strategic/Revenue Impact: Protects $500K+ ARR by identifying timing violations early

This module implements race condition detection logic for WebSocket connections,
with environment-specific timing thresholds and progressive delay calculation.

CRITICAL FEATURES:
1. Environment-aware timing thresholds (testing: 5ms, staging/production: 25ms)
2. Progressive delay calculation for race condition mitigation
3. Timing violation detection for operations
4. Connection readiness validation
5. Race condition pattern recording and analysis

ROOT CAUSE ADDRESSED:
- Missing timing validation for different deployment environments
- No systematic detection of race condition patterns
- Lack of progressive delay logic for Cloud Run environments
- Missing connection readiness validation before message processing
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.race_condition_prevention.types import (
    ApplicationConnectionState,
    RaceConditionPattern
)
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


class RaceConditionDetector:
    """
    Race condition detector that identifies and prevents WebSocket timing issues.
    
    This class implements environment-aware race condition detection with:
    1. Timing violation detection for different environments
    2. Pattern recognition for common race conditions  
    3. Progressive delay calculation logic
    4. Connection readiness validation
    5. Pattern recording for systematic analysis
    
    Environment-Specific Timing:
    - testing: 5ms delays, 100ms handshake timeout
    - development: 10ms delays, 200ms handshake timeout  
    - staging: 25ms delays, 500ms handshake timeout (Cloud Run optimized)
    - production: 25ms delays, 1000ms handshake timeout (Cloud Run optimized)
    """
    
    def __init__(self, environment: Optional[str] = None):
        """
        Initialize race condition detector.
        
        Args:
            environment: Target environment (testing, development, staging, production)
                        If None, will be detected from isolated environment
        """
        if environment is None:
            env = get_env()
            environment = env.get("ENVIRONMENT", "development").lower()
        
        self.environment = environment.lower()
        self.timing_thresholds = self._get_environment_timing_thresholds()
        self.detected_patterns: List[RaceConditionPattern] = []
        
        logger.debug(f"RaceConditionDetector initialized for {self.environment} environment")
        logger.debug(f"Timing thresholds: {self.timing_thresholds}")
    
    def _get_environment_timing_thresholds(self) -> Dict[str, float]:
        """
        Get timing thresholds for race condition detection by environment.
        
        Returns environment-specific timing configuration optimized for
        the deployment characteristics of each environment.
        """
        thresholds = {
            "testing": {
                "handshake_timeout": 0.1,  # 100ms - fast feedback for tests
                "message_delay": 0.005     # 5ms - minimal delay for speed
            },
            "development": {
                "handshake_timeout": 0.2,  # 200ms - reasonable for dev
                "message_delay": 0.01      # 10ms - balance of speed and reliability
            },
            "staging": {
                "handshake_timeout": 0.5,  # 500ms - Cloud Run network latency
                "message_delay": 0.025     # 25ms - Cloud Run optimized timing
            },
            "production": {
                "handshake_timeout": 1.0,  # 1000ms - conservative for production
                "message_delay": 0.025     # 25ms - Cloud Run optimized timing
            }
        }
        
        return thresholds.get(self.environment, thresholds["development"])
    
    def calculate_progressive_delay(self, attempt: int) -> float:
        """
        Calculate progressive delay for race condition mitigation.
        
        Implements environment-aware progressive delays that increase with
        each attempt to handle persistent race conditions.
        
        Args:
            attempt: Attempt number (0-based)
            
        Returns:
            Delay in seconds for this attempt
            
        Environment-Specific Logic:
        - staging/production: 25ms base with linear progression (25ms, 50ms, 75ms)
        - testing: Fixed 5ms for fast test execution  
        - development: Fixed 10ms for balanced development experience
        """
        if self.environment in ["staging", "production"]:
            # Cloud Run environments need progressive delays
            base_delay = 0.025  # 25ms base for Cloud Run
            return base_delay * (attempt + 1)  # Linear progression: 25ms, 50ms, 75ms
        elif self.environment == "testing":
            # Testing environment uses minimal delay for speed
            return 0.005  # 5ms minimal delay for tests
        else:
            # Development environment uses fixed moderate delay
            return 0.01  # 10ms for development
    
    def detect_timing_violation(self, operation_start: datetime, operation_end: datetime, 
                              expected_max_duration: float) -> bool:
        """
        Detect if an operation took longer than expected (potential race condition).
        
        This method identifies operations that exceed expected timing thresholds,
        which can indicate race conditions or performance issues.
        
        Args:
            operation_start: When operation started (UTC datetime)
            operation_end: When operation ended (UTC datetime)
            expected_max_duration: Maximum expected duration in seconds
            
        Returns:
            True if operation exceeded expected duration (timing violation detected)
        """
        try:
            actual_duration = (operation_end - operation_start).total_seconds()
            is_violation = actual_duration > expected_max_duration
            
            if is_violation:
                logger.warning(f"Timing violation detected: {actual_duration:.3f}s > {expected_max_duration:.3f}s")
                
                # Record the timing violation pattern
                self.add_detected_pattern(
                    "timing_violation",
                    "warning",
                    details={
                        "actual_duration_ms": actual_duration * 1000,
                        "expected_max_duration_ms": expected_max_duration * 1000,
                        "violation_margin_ms": (actual_duration - expected_max_duration) * 1000
                    }
                )
            
            return is_violation
            
        except Exception as e:
            logger.error(f"Error detecting timing violation: {e}")
            return False
    
    def validate_connection_readiness(self, state: ApplicationConnectionState) -> bool:
        """
        Validate that connection is ready for message processing.
        
        This is the core validation that prevents race conditions by ensuring
        connections are in the correct state before allowing message handling.
        
        Args:
            state: Current application connection state
            
        Returns:
            True only if connection is ready for messages (prevents race conditions)
        """
        is_ready = state == ApplicationConnectionState.READY_FOR_MESSAGES
        
        if not is_ready:
            logger.debug(f"Connection not ready for messages: state={state.value}")
            
            # Record pattern if connection is being used before ready
            if state in [ApplicationConnectionState.INITIALIZING, 
                        ApplicationConnectionState.HANDSHAKE_PENDING]:
                self.add_detected_pattern(
                    "premature_message_handling",
                    "critical",
                    details={
                        "current_state": state.value,
                        "required_state": ApplicationConnectionState.READY_FOR_MESSAGES.value
                    }
                )
        
        return is_ready
    
    def add_detected_pattern(self, pattern_type: str, severity: str = "warning",
                           details: Optional[Dict] = None):
        """
        Record a detected race condition pattern.
        
        This method builds a database of race condition patterns for
        systematic analysis and prevention improvement.
        
        Args:
            pattern_type: Type of race condition pattern
            severity: Severity level (warning, critical, fatal)
            details: Additional context about the pattern
        """
        pattern = RaceConditionPattern(
            pattern_type=pattern_type,
            severity=severity,
            environment=self.environment,
            details=details
        )
        
        self.detected_patterns.append(pattern)
        
        # Log critical patterns immediately
        if pattern.is_critical():
            logger.error(f"Critical race condition pattern detected: {pattern}")
        else:
            logger.info(f"Race condition pattern detected: {pattern}")
    
    def get_detected_patterns(self, since: Optional[datetime] = None,
                            pattern_type: Optional[str] = None,
                            severity: Optional[str] = None) -> List[RaceConditionPattern]:
        """
        Get detected patterns with optional filtering.
        
        Args:
            since: Only return patterns detected after this time
            pattern_type: Filter by pattern type
            severity: Filter by severity level
            
        Returns:
            List of patterns matching the criteria
        """
        patterns = self.detected_patterns
        
        if since:
            patterns = [p for p in patterns if p.detected_at >= since]
        
        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]
        
        if severity:
            patterns = [p for p in patterns if p.severity == severity]
        
        return patterns
    
    def get_pattern_summary(self) -> Dict:
        """
        Get summary of detected patterns for analysis.
        
        Returns:
            Dictionary with pattern statistics and summaries
        """
        if not self.detected_patterns:
            return {
                "total_patterns": 0,
                "by_type": {},
                "by_severity": {},
                "recent_patterns": 0
            }
        
        # Count patterns by type and severity
        by_type = {}
        by_severity = {}
        
        for pattern in self.detected_patterns:
            by_type[pattern.pattern_type] = by_type.get(pattern.pattern_type, 0) + 1
            by_severity[pattern.severity] = by_severity.get(pattern.severity, 0) + 1
        
        # Count recent patterns (last 5 minutes)
        recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        recent_patterns = len([p for p in self.detected_patterns if p.detected_at >= recent_cutoff])
        
        return {
            "total_patterns": len(self.detected_patterns),
            "by_type": by_type,
            "by_severity": by_severity,
            "recent_patterns": recent_patterns,
            "environment": self.environment,
            "timing_thresholds": self.timing_thresholds
        }
    
    def clear_old_patterns(self, max_age_hours: int = 24):
        """
        Clear old patterns to prevent memory growth.
        
        Args:
            max_age_hours: Maximum age of patterns to keep (default 24 hours)
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        initial_count = len(self.detected_patterns)
        
        self.detected_patterns = [p for p in self.detected_patterns if p.detected_at >= cutoff_time]
        
        cleared_count = initial_count - len(self.detected_patterns)
        if cleared_count > 0:
            logger.info(f"Cleared {cleared_count} old race condition patterns (older than {max_age_hours} hours)")
    
    def reset_patterns(self):
        """Reset all detected patterns (for testing)."""
        self.detected_patterns.clear()
        logger.debug("All race condition patterns reset")