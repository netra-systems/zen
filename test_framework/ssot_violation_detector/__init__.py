"""
SSOT Violation Detection Infrastructure

This module provides utilities for detecting and reporting SSOT violations
across the codebase, with specific focus on the test framework violation.

Primary Target: test_framework/ssot/database.py:596 - Direct session.add() violation
"""

from .violation_detector import SSotViolationDetector
from .message_pattern_analyzer import MessagePatternAnalyzer  
from .violation_reporter import ViolationReporter

__all__ = [
    "SSotViolationDetector",
    "MessagePatternAnalyzer", 
    "ViolationReporter"
]