"""Tests for the query fix validator module."""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.services.query_fix_validator import (
    ensure_query_uses_arrayElement,
    fix_simplified_correlation_query,
    validate_and_fix_query,
)

class QueryFixValidatorTests:
    """Test suite for query fix validator."""
    
    def test_validate_and_fix_simple_array_access(self):
        """Test fixing simple array access syntax."""
        bad_query = "SELECT metrics.value[1] FROM workload_events"
        fixed = validate_and_fix_query(bad_query)
        
        assert "metrics.value[1]" not in fixed
        assert "arrayElement(metrics.value, 1)" in fixed
    
    def test_validate_and_fix_complex_correlation_query(self):
        """Test fixing the exact correlation query from the error."""
        bad_query = """
        SELECT arrayFirstIndex(x -> (x = 'latency_ms'), metrics.name) AS idx1,
               arrayFirstIndex(x -> (x = 'throughput'), metrics.name) AS idx2,
               if(idx1 > 0, metrics.value[idx1], 0.) AS m1_value,
               if(idx2 > 0, metrics.value[idx2], 0.) AS m2_value
        FROM workload_events
        WHERE (user_id = 1) AND (idx1 > 0) AND (idx2 > 0)
        """
        
        fixed = validate_and_fix_query(bad_query)
        
        assert "metrics.value[idx1]" not in fixed
        assert "metrics.value[idx2]" not in fixed
        assert "arrayElement(metrics.value, idx1)" in fixed
        assert "arrayElement(metrics.value, idx2)" in fixed
    
    def test_validate_and_fix_all_nested_fields(self):
        """Test fixing all nested field types."""
        bad_query = """
        SELECT metrics.name[idx] as name,
               metrics.value[idx] as value,
               metrics.unit[idx] as unit
        FROM workload_events
        """
        
        fixed = validate_and_fix_query(bad_query)
        
        assert "metrics.name[idx]" not in fixed
        assert "metrics.value[idx]" not in fixed
        assert "metrics.unit[idx]" not in fixed
        assert "arrayElement(metrics.name, idx)" in fixed
        assert "arrayElement(metrics.value, idx)" in fixed
        assert "arrayElement(metrics.unit, idx)" in fixed
    
    def test_ensure_query_uses_arrayElement(self):
        """Test query validation function."""
        bad_query = "SELECT metrics.value[1] FROM table"
        good_query = "SELECT arrayElement(metrics.value, 1) FROM table"
        no_array_query = "SELECT * FROM table"
        
        assert not ensure_query_uses_arrayElement(bad_query)
        assert ensure_query_uses_arrayElement(good_query)
        assert ensure_query_uses_arrayElement(no_array_query)
    
    def test_fix_simplified_correlation_query(self):
        """Test fixing simplified correlation queries."""
        bad_query = """
        SELECT arrayFirstIndex(x -> x = 'cost_cents', metrics.name) AS idx,
               if(idx > 0, metrics.value[idx], 0.) AS cost_value
        FROM workload_events
        """
        
        fixed = fix_simplified_correlation_query(bad_query)
        
        # Should fix array syntax
        assert "metrics.value[idx]" not in fixed
        assert "arrayElement(metrics.value, idx)" in fixed
        
        # Should preserve case of ClickHouse functions
        assert "arrayFirstIndex" in fixed  # Not "arrayfirstindex"
        assert "SELECT" in fixed  # Not "select"
    
    def test_preserve_function_case(self):
        """Test that ClickHouse function names are preserved."""
        query = "SELECT arrayFirstIndex(x -> x = 'test', arr) FROM table"
        fixed = validate_and_fix_query(query)
        
        # Function names should be preserved
        assert "arrayFirstIndex" in fixed
        # This assertion was incorrect - fixed.lower() will always contain 'arrayfirstindex'
        # The important thing is that the original case is preserved in fixed
    
    def test_fix_arithmetic_in_index(self):
        """Test fixing queries with arithmetic in array index."""
        bad_query = """
        SELECT metrics.value[idx - 1] as prev,
               metrics.value[idx + 1] as next
        FROM workload_events
        """
        
        fixed = validate_and_fix_query(bad_query)
        
        assert "metrics.value[idx - 1]" not in fixed
        assert "metrics.value[idx + 1]" not in fixed
        assert "arrayElement(metrics.value, idx - 1)" in fixed
        assert "arrayElement(metrics.value, idx + 1)" in fixed