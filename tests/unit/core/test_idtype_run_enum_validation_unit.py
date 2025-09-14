"""
Unit Tests for IDType.RUN Enum Validation - SSOT CRITICAL

BUSINESS VALUE:
- Segment: Platform/Internal - System Stability & Development Velocity  
- Goal: Ensure IDType.RUN enum exists and works correctly before implementing fix
- Value Impact: Validates Golden Path WebSocket validation and $500K+ ARR functionality testing
- Revenue Impact: Prevents runtime errors in production from missing enum values

TESTING STRATEGY:
- Tests WILL FAIL before fix (missing IDType.RUN enum value)
- Tests WILL PASS after fix (when RUN = "run" is added to IDType)
- Validates enum completeness, backwards compatibility, and SSOT patterns

SSOT COMPLIANCE:
- Uses test_framework.ssot.base_test_case.SSotBaseTestCase  
- Imports only from SSOT_IMPORT_REGISTRY.md verified paths
- Follows SSOT testing patterns for enum validation
- No mocks - tests real enum functionality

CRITICAL TEST COVERAGE:
1. IDType.RUN enum existence validation
2. IDType.RUN enum value verification ("run")
3. IDType enum completeness with RUN added
4. Backwards compatibility validation
5. SSOT ID generation patterns with RUN type
"""

import pytest
from enum import Enum
from typing import Set, List, Any

# SSOT imports from verified registry
from test_framework.ssot.base_test_case import SSotBaseTestCase, SsotTestMetrics, CategoryType
from shared.isolated_environment import get_env

# Core ID management imports - SSOT verified paths
from netra_backend.app.core.unified_id_manager import IDType, UnifiedIDManager, generate_id


class TestIDTypeRunEnumValidation(SSotBaseTestCase):
    """
    Unit tests for IDType.RUN enum validation and completeness.
    
    These tests validate that the IDType enum contains the required RUN value
    and that all enum functionality works correctly with the RUN type.
    """

    def setup_method(self, method=None):
        """Set up test environment."""
        super().setup_method(method)
        
        # Record test metadata in custom metrics
        if hasattr(self, '_metrics'):
            self._metrics.record_custom("test_category", "unit")
            self._metrics.record_custom("business_value", "Platform/Internal")
            self._metrics.record_custom("expected_outcome", "Validate IDType.RUN enum exists and works correctly")
        
        # Expected IDType values (including RUN after fix)
        self.expected_id_types = {
            "USER", "SESSION", "REQUEST", "AGENT", "TOOL", 
            "TRANSACTION", "WEBSOCKET", "EXECUTION", "TRACE", 
            "METRIC", "THREAD", "RUN"  # RUN should be added
        }

    def test_idtype_enum_contains_run_value(self):
        """
        CRITICAL TEST: Validate IDType enum contains RUN value.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError: IDType has no attribute 'RUN'
        - AFTER FIX: Will PASS when RUN = "run" is added to IDType enum
        
        This test validates the core missing functionality identified in GitHub Issue #883.
        """
        try:
            # Attempt to access IDType.RUN - this will fail before fix
            run_enum_value = IDType.RUN
            
            # If we get here, the fix has been applied
            assert run_enum_value is not None, "IDType.RUN should not be None"
            assert isinstance(run_enum_value, IDType), "IDType.RUN should be an IDType enum instance"
            
            if hasattr(self, '_metrics'):
                self._metrics.record_custom("success", "IDType.RUN enum value exists and is valid")
            
        except AttributeError as e:
            # Expected failure before fix
            assert "RUN" in str(e), f"Expected 'RUN' in error message, got: {e}"
            self.test_metrics.record_expected_failure(f"Expected failure before fix: {e}")
            
            # Re-raise to make test fail (as expected before fix)
            pytest.fail(f"IDType.RUN is missing from enum definition: {e}")

    def test_idtype_run_enum_value_equals_run_string(self):
        """
        CRITICAL TEST: Validate IDType.RUN.value equals "run".
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError (no RUN attribute)
        - AFTER FIX: Will PASS and validate RUN.value == "run"
        
        This ensures SSOT pattern consistency where enum values match lowercase strings.
        """
        try:
            # Access IDType.RUN value - will fail before fix
            run_value = IDType.RUN.value
            
            # Validate the value matches expected SSOT pattern
            assert run_value == "run", f"IDType.RUN.value should be 'run', got: '{run_value}'"
            assert isinstance(run_value, str), f"IDType.RUN.value should be string, got: {type(run_value)}"
            
            self.test_metrics.record_success(f"IDType.RUN.value correctly equals 'run'")
            
        except AttributeError as e:
            # Expected failure before fix
            self.test_metrics.record_expected_failure(f"Expected failure before fix: {e}")
            pytest.fail(f"IDType.RUN enum value is missing: {e}")

    def test_idtype_enum_completeness_with_run(self):
        """
        CRITICAL TEST: Validate IDType enum completeness including RUN.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL missing RUN in enum values
        - AFTER FIX: Will PASS with all expected enum values present
        
        This validates that adding RUN doesn't break existing enum functionality.
        """
        # Get all current IDType values
        current_values = {item.value for item in IDType}
        current_names = {item.name for item in IDType}
        
        try:
            # Check if RUN is present - will fail before fix
            assert "RUN" in current_names, f"IDType enum missing 'RUN' name. Current names: {current_names}"
            assert "run" in current_values, f"IDType enum missing 'run' value. Current values: {current_values}"
            
            # Validate all expected types are present
            missing_names = self.expected_id_types - current_names
            assert not missing_names, f"IDType enum missing expected names: {missing_names}"
            
            # Validate enum has reasonable count (should be 12 with RUN)
            assert len(current_names) >= 12, f"IDType enum too small, expected >= 12, got: {len(current_names)}"
            
            self.test_metrics.record_success(f"IDType enum complete with {len(current_names)} values including RUN")
            
        except AssertionError as e:
            self.test_metrics.record_expected_failure(f"Expected failure before fix: {e}")
            pytest.fail(f"IDType enum completeness validation failed: {e}")

    def test_idtype_run_backwards_compatibility(self):
        """
        CRITICAL TEST: Validate adding IDType.RUN doesn't break existing functionality.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL when trying to use IDType.RUN
        - AFTER FIX: Will PASS and all existing IDType values still work
        
        This ensures the fix maintains backward compatibility.
        """
        # Test all existing IDType values still work
        existing_types = [
            IDType.USER, IDType.SESSION, IDType.REQUEST, IDType.AGENT,
            IDType.TOOL, IDType.TRANSACTION, IDType.WEBSOCKET, 
            IDType.EXECUTION, IDType.TRACE, IDType.METRIC, IDType.THREAD
        ]
        
        for id_type in existing_types:
            assert id_type.value is not None, f"Existing IDType {id_type.name} value should not be None"
            assert isinstance(id_type.value, str), f"Existing IDType {id_type.name} value should be string"
        
        try:
            # Test the new RUN type - will fail before fix
            run_type = IDType.RUN
            assert run_type.value == "run", f"IDType.RUN should have value 'run'"
            
            # Test RUN type in list operations
            all_types = list(IDType)
            assert IDType.RUN in all_types, "IDType.RUN should be in list of all types"
            
            self.test_metrics.record_success("IDType.RUN backwards compatibility validated")
            
        except AttributeError as e:
            self.test_metrics.record_expected_failure(f"Expected failure before fix: {e}")
            pytest.fail(f"IDType.RUN backwards compatibility test failed: {e}")

    def test_idtype_run_in_unified_id_manager_initialization(self):
        """
        CRITICAL TEST: Validate UnifiedIDManager can initialize with IDType.RUN.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL when UnifiedIDManager tries to initialize with missing RUN
        - AFTER FIX: Will PASS and RUN type properly handled in manager initialization
        
        This validates the fix resolves the core UnifiedIDManager integration issue.
        """
        try:
            # Create UnifiedIDManager - this uses IDType for initialization
            id_manager = UnifiedIDManager()
            
            # Validate RUN type is handled in manager initialization
            # The manager creates sets for each IDType in __init__
            run_active_ids = id_manager.get_active_ids(IDType.RUN)
            assert run_active_ids is not None, "Manager should have active IDs set for RUN type"
            assert isinstance(run_active_ids, set), "Active IDs for RUN should be a set"
            assert len(run_active_ids) == 0, "New manager should have empty RUN active IDs"
            
            # Validate RUN counter is initialized
            run_count = id_manager.count_active_ids(IDType.RUN)
            assert run_count == 0, "New manager should have zero RUN IDs"
            
            self.test_metrics.record_success("UnifiedIDManager properly handles IDType.RUN initialization")
            
        except Exception as e:
            self.test_metrics.record_expected_failure(f"Expected failure before fix: {e}")
            pytest.fail(f"UnifiedIDManager IDType.RUN initialization failed: {e}")

    def test_idtype_run_enum_iteration_completeness(self):
        """
        TEST: Validate IDType enum iteration includes RUN.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with RUN missing from iteration
        - AFTER FIX: Will PASS with RUN included in complete enum iteration
        
        This ensures RUN is properly integrated into enum iteration patterns.
        """
        try:
            # Test enum iteration includes RUN
            all_names = [item.name for item in IDType]
            all_values = [item.value for item in IDType]
            
            assert "RUN" in all_names, f"IDType iteration missing 'RUN' name. Found: {all_names}"
            assert "run" in all_values, f"IDType iteration missing 'run' value. Found: {all_values}"
            
            # Test specific RUN access during iteration
            run_found = False
            for id_type in IDType:
                if id_type.name == "RUN":
                    run_found = True
                    assert id_type.value == "run", f"RUN enum should have value 'run', got: {id_type.value}"
                    break
            
            assert run_found, "IDType.RUN should be found during enum iteration"
            
            self.test_metrics.record_success("IDType enum iteration properly includes RUN")
            
        except Exception as e:
            self.test_metrics.record_expected_failure(f"Expected failure before fix: {e}")
            pytest.fail(f"IDType enum iteration test failed: {e}")

    def teardown_method(self, method=None):
        """Clean up test environment and record metrics."""
        if hasattr(self, 'test_metrics'):
            self.test_metrics.finalize()
        super().teardown_method(method)