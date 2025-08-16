"""
E2E Test Edge Cases Generator

This module provides edge case generators for comprehensive testing:
- Boundary value testing
- Null and empty value handling
- Extreme size scenarios
- Error condition simulation

ARCHITECTURAL COMPLIANCE:
- Maximum file size: 300 lines
- Maximum function size: 8 lines
- Single responsibility: Edge case generation
- Strong typing: All functions typed
- Modular design: Composable edge case generators

Usage:
    from app.tests.e2e.data.edge_cases_temporal import (
        EdgeCaseGenerator,
        ErrorConditionSimulator
    )
"""

from typing import Dict, List, Optional, Union, Any, Iterator
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import random
import numpy as np
from enum import Enum


class EdgeCaseCategory(Enum):
    """Categories of edge cases."""
    BOUNDARY_VALUES = "boundary_values"
    NULL_EMPTY = "null_empty"
    EXTREME_SIZES = "extreme_sizes"
    CONCURRENT_LIMITS = "concurrent_limits"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


@dataclass
class EdgeCase:
    """Edge case configuration."""
    category: EdgeCaseCategory
    description: str
    test_values: List[Any]
    expected_behavior: str


class EdgeCaseGenerator:
    """Generates edge case test scenarios."""
    
    def __init__(self):
        self.edge_cases = self._initialize_edge_cases()
    
    def generate_boundary_values(self) -> Iterator[Dict[str, Any]]:
        """Generate boundary value test cases."""
        boundary_cases = self._get_boundary_cases()
        for case in boundary_cases:
            yield self._create_boundary_test(case)
    
    def generate_null_empty_cases(self) -> Iterator[Dict[str, Any]]:
        """Generate null and empty value test cases."""
        null_cases = self._get_null_empty_cases()
        for case in null_cases:
            yield self._create_null_test(case)
    
    def generate_extreme_size_cases(self) -> Iterator[Dict[str, Any]]:
        """Generate extreme size test cases."""
        size_cases = self._get_extreme_size_cases()
        for case in size_cases:
            yield self._create_size_test(case)
    
    def _initialize_edge_cases(self) -> Dict[EdgeCaseCategory, List[EdgeCase]]:
        """Initialize edge case definitions."""
        return {
            EdgeCaseCategory.BOUNDARY_VALUES: self._create_boundary_cases(),
            EdgeCaseCategory.NULL_EMPTY: self._create_null_empty_cases(),
            EdgeCaseCategory.EXTREME_SIZES: self._create_extreme_size_cases(),
            EdgeCaseCategory.CONCURRENT_LIMITS: self._create_concurrent_cases(),
            EdgeCaseCategory.RESOURCE_EXHAUSTION: self._create_resource_cases()
        }




class ErrorConditionSimulator:
    """Simulates error conditions for testing."""
    
    def __init__(self, error_rate: float = 0.02):
        self.error_rate = error_rate
        self.error_types = self._initialize_error_types()
    
    def inject_random_errors(self, data: List[Dict]) -> List[Dict]:
        """Inject random errors into data stream."""
        for item in data:
            if random.random() < self.error_rate:
                item = self._corrupt_data_item(item)
            yield item
    
    def inject_timeout_errors(self, duration_ms: int) -> Dict[str, Any]:
        """Inject timeout error conditions."""
        return {
            "error_type": "timeout",
            "duration_ms": duration_ms,
            "expected_handling": "graceful_degradation"
        }
    
    def inject_rate_limit_errors(self, requests_per_second: int) -> Dict[str, Any]:
        """Inject rate limiting conditions."""
        return {
            "error_type": "rate_limit",
            "requests_per_second": requests_per_second,
            "expected_handling": "request_queuing"
        }
    
    def _initialize_error_types(self) -> List[str]:
        """Initialize error type definitions."""
        return [
            "timeout", "rate_limit", "data_corruption",
            "resource_exhaustion", "network_failure"
        ]


# Helper functions for edge case testing


# Edge case creator functions
def _create_boundary_cases() -> List[EdgeCase]:
    """Create boundary value edge cases."""
    return [
        EdgeCase(
            EdgeCaseCategory.BOUNDARY_VALUES,
            "Integer overflow boundaries",
            [0, 1, -1, 2147483647, -2147483648],
            "handle_overflow_gracefully"
        ),
        EdgeCase(
            EdgeCaseCategory.BOUNDARY_VALUES,
            "Float precision boundaries",
            [0.0, 1e-10, 1e10, float('inf'), float('-inf')],
            "handle_precision_limits"
        )
    ]


def _create_null_empty_cases() -> List[EdgeCase]:
    """Create null and empty value edge cases."""
    return [
        EdgeCase(
            EdgeCaseCategory.NULL_EMPTY,
            "Null and None values",
            [None, "", {}, []], 
            "validate_required_fields"
        ),
        EdgeCase(
            EdgeCaseCategory.NULL_EMPTY,
            "Whitespace-only strings",
            [" ", "\t", "\n", "   "],
            "sanitize_whitespace"
        )
    ]


def _create_extreme_size_cases() -> List[EdgeCase]:
    """Create extreme size edge cases."""
    return [
        EdgeCase(
            EdgeCaseCategory.EXTREME_SIZES,
            "Large string inputs",
            ["a" * 1000000, "x" * 10000000],
            "handle_large_inputs"
        ),
        EdgeCase(
            EdgeCaseCategory.EXTREME_SIZES,
            "Deeply nested structures",
            [{"a": {"b": {"c": {"d": "deep"}}} * 1000}],
            "prevent_stack_overflow"
        )
    ]


def _create_concurrent_cases() -> List[EdgeCase]:
    """Create concurrent access edge cases."""
    return [
        EdgeCase(
            EdgeCaseCategory.CONCURRENT_LIMITS,
            "Maximum concurrent connections",
            [1000, 5000, 10000],
            "graceful_connection_limiting"
        )
    ]


def _create_resource_cases() -> List[EdgeCase]:
    """Create resource exhaustion edge cases."""
    return [
        EdgeCase(
            EdgeCaseCategory.RESOURCE_EXHAUSTION,
            "Memory pressure scenarios",
            ["high_memory_usage", "memory_leak_simulation"],
            "memory_management_fallback"
        )
    ]


# Data corruption helpers
def _corrupt_data_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Corrupt a data item to simulate errors."""
    corruption_type = random.choice(["missing_field", "wrong_type", "invalid_value"])
    if corruption_type == "missing_field" and len(item) > 1:
        key = random.choice(list(item.keys()))
        del item[key]
    elif corruption_type == "wrong_type":
        key = random.choice(list(item.keys()))
        item[key] = "corrupted_value"
    return item


# Test case builders
def _create_boundary_test(case: EdgeCase) -> Dict[str, Any]:
    """Create boundary value test case."""
    return {
        "type": "boundary_test",
        "category": case.category.value,
        "test_values": case.test_values,
        "expected_behavior": case.expected_behavior
    }


def _create_null_test(case: EdgeCase) -> Dict[str, Any]:
    """Create null/empty test case."""
    return {
        "type": "null_test",
        "category": case.category.value,
        "test_values": case.test_values,
        "expected_behavior": case.expected_behavior
    }


def _create_size_test(case: EdgeCase) -> Dict[str, Any]:
    """Create extreme size test case."""
    return {
        "type": "size_test",
        "category": case.category.value,
        "test_values": case.test_values,
        "expected_behavior": case.expected_behavior
    }


# Helper accessors for edge case categories
def _get_boundary_cases() -> List[EdgeCase]:
    """Get boundary value cases."""
    return _create_boundary_cases()

def _get_null_empty_cases() -> List[EdgeCase]:
    """Get null/empty cases."""
    return _create_null_empty_cases()

def _get_extreme_size_cases() -> List[EdgeCase]:
    """Get extreme size cases."""
    return _create_extreme_size_cases()