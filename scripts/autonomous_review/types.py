#!/usr/bin/env python3
"""
Autonomous Test Review System - Type Definitions
Data types and enums for the autonomous test review system
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class TestAnalysis:
    """Comprehensive test analysis results"""
    coverage_percentage: float = 0.0
    missing_tests: List[str] = field(default_factory=list)
    legacy_tests: List[str] = field(default_factory=list)
    flaky_tests: List[str] = field(default_factory=list)
    slow_tests: List[str] = field(default_factory=list)
    redundant_tests: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    critical_gaps: List[str] = field(default_factory=list)
    test_debt: int = 0


class ReviewMode(Enum):
    """Test review execution modes"""
    AUTO = "auto"
    QUICK = "quick"
    FULL_ANALYSIS = "full-analysis"
    SMART_GENERATE = "smart-generate"
    CONTINUOUS = "continuous"
    ULTRA_THINK = "ultra-think"


class TestPattern(Enum):
    """Common test patterns to detect"""
    DEPRECATED_MOCK = "deprecated_mock"
    MISSING_ASSERTION = "missing_assertion"
    HARDCODED_WAIT = "hardcoded_wait"
    DUPLICATE_TEST = "duplicate_test"
    NO_COVERAGE = "no_coverage"
    FLAKY_PATTERN = "flaky_pattern"
    SLOW_SETUP = "slow_setup"
    LEGACY_FRAMEWORK = "legacy_framework"


@dataclass
class TestMetadata:
    """Metadata for a test file or function"""
    file_path: Path
    test_name: str
    category: str = "unknown"
    execution_time: float = 0.0
    failure_rate: float = 0.0
    assertions: int = 0
    dependencies: List[str] = field(default_factory=list)
    coverage_lines: int = 0
    quality_issues: List[str] = field(default_factory=list)