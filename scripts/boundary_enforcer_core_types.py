#!/usr/bin/env python3
"""
Core type definitions for boundary enforcement system.
Contains all dataclasses and type definitions used across modules.
"""

import time
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Union


@dataclass
class BoundaryViolation:
    """Enhanced violation with boundary context"""
    file_path: str
    violation_type: str
    severity: str
    boundary_name: str
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    actual_value: Optional[int] = None
    expected_value: Optional[int] = None
    description: str = ""
    fix_suggestion: str = ""
    auto_split_suggestion: Optional[str] = None
    impact_score: int = 1  # 1-10 scale

@dataclass
class SystemBoundaries:
    """System-wide boundary definitions"""
    max_file_lines: int = 300
    max_function_lines: int = 8
    max_module_count: int = 700
    max_total_loc: int = 200000
    max_complexity_score: float = 3.0
    max_duplicate_types: int = 0
    max_test_stubs: int = 0

@dataclass
class BoundaryReport:
    """Complete boundary enforcement report"""
    total_violations: int
    boundary_compliance_score: float
    growth_risk_level: str
    timestamp: str
    violations_by_boundary: Dict[str, int]
    violations: List[BoundaryViolation]
    system_metrics: Dict[str, Union[int, float, str]]
    remediation_plan: List[str]
    emergency_actions: List[str]

def create_timestamp() -> str:
    """Create formatted timestamp for reports"""
    return time.strftime("%Y-%m-%d %H:%M:%S")

def get_file_patterns() -> List[str]:
    """Get standard file patterns for boundary checks"""
    return [
        'app/**/*.py', 
        'frontend/**/*.tsx', 
        'frontend/**/*.ts', 
        'scripts/**/*.py', 
        'test_framework/**/*.py'
    ]

def get_skip_patterns() -> List[str]:
    """Get patterns for files to skip during analysis"""
    return [
        '__pycache__', 'node_modules', '.git', 'migrations',
        'test_reports', 'docs', '.pytest_cache', 'venv',
        '.venv', 'env', '.env', 'dist', 'build'
    ]

def should_skip_file(filepath: str) -> bool:
    """Check if file should be skipped from analysis"""
    skip_patterns = get_skip_patterns()
    return any(pattern in filepath for pattern in skip_patterns)

def get_test_stub_patterns() -> List[tuple]:
    """Get patterns that indicate test stubs in production code"""
    return [
        (r'# Mock implementation', 'Mock implementation comment'),
        (r'# Test stub', 'Test stub comment'),
        (r'# TODO.*implement', 'TODO implementation comment'),
        (r'return \[{"id": "1"', 'Hardcoded test data'),
        (r'raise NotImplementedError', 'Not implemented error')
    ]