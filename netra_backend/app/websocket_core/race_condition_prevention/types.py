"""
WebSocket Race Condition Prevention Types

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide foundational types for race condition detection
- Value Impact: Enables systematic race condition pattern tracking
- Strategic/Revenue Impact: Foundation for protecting $500K+ ARR through reliable connections

This module defines core types used for WebSocket race condition detection and prevention.

CRITICAL TYPES:
1. ApplicationConnectionState - Tracks connection readiness and prevents race conditions
2. RaceConditionPattern - Represents detected race condition patterns for analysis

ROOT CAUSE ADDRESSED:
- Missing structured state tracking for WebSocket connection lifecycle
- No systematic way to detect and categorize race condition patterns
- Need for environment-aware connection state management
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ApplicationConnectionState(Enum):
    """
    Connection states for WebSocket race condition detection.
    
    This enum tracks connection readiness and prevents race conditions
    by providing clear state transitions that applications can rely on.
    
    States are ordered from least ready to most ready:
    1. INITIALIZING - Connection object created but handshake not started
    2. HANDSHAKE_PENDING - accept() called but handshake not yet complete  
    3. CONNECTED - Transport-level connection established
    4. READY_FOR_MESSAGES - Application-level ready state, safe for message handling
    5. ERROR - Connection in error state, not safe for operations
    6. CLOSED - Connection cleanly closed
    """
    INITIALIZING = "initializing"
    HANDSHAKE_PENDING = "handshake_pending" 
    CONNECTED = "connected"
    READY_FOR_MESSAGES = "ready_for_messages"
    ERROR = "error"
    CLOSED = "closed"

    def is_ready_for_messages(self) -> bool:
        """Check if state allows message processing."""
        return self == ApplicationConnectionState.READY_FOR_MESSAGES
    
    def is_operational(self) -> bool:
        """Check if state allows any operations."""
        return self in [
            ApplicationConnectionState.CONNECTED,
            ApplicationConnectionState.READY_FOR_MESSAGES
        ]
    
    def is_terminal(self) -> bool:
        """Check if state is terminal (no further transitions possible)."""
        return self in [
            ApplicationConnectionState.ERROR,
            ApplicationConnectionState.CLOSED
        ]


class RaceConditionPattern:
    """
    Represents detected race condition patterns in WebSocket connections.
    
    This class captures information about race condition occurrences
    to enable systematic analysis and prevention.
    
    Attributes:
        pattern_type: Type of race condition detected (e.g. "handshake_timing_violation")
        severity: Severity level ("warning", "critical", "fatal")
        environment: Environment where pattern was detected
        detected_at: Timestamp when pattern was detected
        details: Additional context about the pattern
    """
    
    def __init__(self, pattern_type: str, severity: str, environment: str, 
                 details: Optional[dict] = None):
        self.pattern_type = pattern_type
        self.severity = severity
        self.environment = environment
        self.detected_at = datetime.now(timezone.utc)
        self.details = details or {}
    
    def __str__(self) -> str:
        return f"RaceConditionPattern({self.pattern_type}, {self.severity}, {self.environment})"
    
    def __repr__(self) -> str:
        return (f"RaceConditionPattern(pattern_type='{self.pattern_type}', "
                f"severity='{self.severity}', environment='{self.environment}', "
                f"detected_at={self.detected_at.isoformat()})")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "pattern_type": self.pattern_type,
            "severity": self.severity,
            "environment": self.environment,
            "detected_at": self.detected_at.isoformat(),
            "details": self.details
        }
    
    def is_critical(self) -> bool:
        """Check if this is a critical severity pattern."""
        return self.severity.lower() in ["critical", "fatal"]
    
    def age_seconds(self) -> float:
        """Get age of pattern in seconds."""
        return (datetime.now(timezone.utc) - self.detected_at).total_seconds()