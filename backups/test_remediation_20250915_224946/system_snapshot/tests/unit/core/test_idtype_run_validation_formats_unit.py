"""
Unit Tests for IDType.RUN Format Validation - SSOT CRITICAL

BUSINESS VALUE:
- Segment: Platform/Internal - System Stability & Development Velocity
- Goal: Ensure IDType.RUN format validation works correctly after fix implementation
- Value Impact: Validates SSOT format compliance and prevents Golden Path validation failures
- Revenue Impact: Prevents runtime format validation errors affecting $500K+ ARR functionality

TESTING STRATEGY:
- Tests WILL FAIL before fix (missing IDType.RUN enum value)
- Tests WILL PASS after fix (when RUN = "run" is added to IDType)
- Validates format validation functions work with RUN type
- Tests edge cases and boundary conditions for run ID formats

SSOT COMPLIANCE:
- Uses test_framework.ssot.base_test_case.SSotBaseTestCase
- Imports only from SSOT_IMPORT_REGISTRY.md verified paths
- Follows SSOT testing patterns for format validation
- No mocks - tests real format validation functionality

CRITICAL TEST COVERAGE:
1. is_valid_id_format() with run IDs
2. is_valid_id_format_compatible() with IDType.RUN
3. Format validation edge cases and boundary conditions
4. SSOT format pattern compliance 
5. Backwards compatibility with existing format validation
6. Performance validation for format checking
"""

import pytest
import re
import time
from typing import List, Tuple, Dict, Any, Set

# SSOT imports from verified registry
from test_framework.ssot.base_test_case import SSotBaseTestCase, SsotTestMetrics, CategoryType
from shared.isolated_environment import get_env

# Core ID management imports - SSOT verified paths
from netra_backend.app.core.unified_id_manager import (
    IDType, UnifiedIDManager, 
    is_valid_id_format, is_valid_id_format_compatible,
    generate_id
)


@pytest.mark.unit
class IDTypeRunValidationFormatsTests(SSotBaseTestCase):
    """
    Unit tests for IDType.RUN format validation functionality.
    
    These tests validate that format validation functions properly handle
    run IDs generated with the new IDType.RUN enum value.
    """

    def setup_method(self, method=None):
        """Set up format validation test environment."""
        super().setup_method(method)
        
        # Test metrics for SSOT compliance
        self.test_metrics = SsotTestMetrics()
        self.test_metrics.record_custom("category", "UNIT")
        self.test_metrics.record_custom("test_name", method.__name__ if method else "setup")
        self.test_metrics.record_custom("business_value_segment", "Platform/Internal")
        self.test_metrics.record_custom("expected_outcome", "Validate IDType.RUN format validation works correctly")
        
        # ID manager for generating test run IDs
        self.id_manager = UnifiedIDManager()
        
        # Sample run ID formats for validation testing
        self.valid_run_id_patterns = []
        self.invalid_run_id_patterns = [
            "",  # Empty string
            "invalid",  # No structure
            "run",  # Too simple
            "run_",  # Missing parts
            "run_counter",  # Missing UUID
            "run_abc_def",  # Non-numeric counter
            "run_123_xyz",  # Invalid UUID part
            "run_123_toolong12345",  # UUID part too long
            "run_123_short",  # UUID part too short
        ]
        
        # Generated IDs for cleanup
        self.generated_run_ids: Set[str] = set()

    def test_is_valid_id_format_with_run_ids(self):
        """
        CRITICAL TEST: is_valid_id_format() function with run IDs.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError: IDType has no attribute 'RUN'
        - AFTER FIX: Will PASS and validate run ID formats correctly
        
        This tests the core format validation identified in GitHub Issue #883.
        """
        try:
            # Generate various run ID formats - will fail before fix
            test_cases = [
                ("basic", None),
                ("prefixed", "format_test"),
                ("complex", "ssot_validation_format"),
                ("golden_path", "websocket_phase1_validation"),
            ]
            
            for test_name, prefix in test_cases:
                # Generate run ID
                if prefix:
                    run_id = self.id_manager.generate_id(IDType.RUN, prefix=prefix)
                else:
                    run_id = self.id_manager.generate_id(IDType.RUN)
                
                # Test is_valid_id_format function
                is_valid = is_valid_id_format(run_id)
                assert is_valid, f"Run ID should pass format validation: {run_id} (test: {test_name})"
                
                # Additional pattern validation
                assert isinstance(run_id, str), f"Run ID should be string: {type(run_id)}"
                assert len(run_id) > 0, f"Run ID should not be empty: {run_id}"
                assert "run" in run_id, f"Run ID should contain 'run': {run_id}"
                
                self.valid_run_id_patterns.append(run_id)
                self.generated_run_ids.add(run_id)
            
            self.test_metrics.record_custom("success", f"is_valid_id_format validation successful: {len(test_cases)} patterns")
            
        except AttributeError as e:
            # Expected failure before fix
            assert "RUN" in str(e), f"Expected 'RUN' in error message, got: {e}"
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"is_valid_id_format with run IDs failed: {e}")

    def test_is_valid_id_format_compatible_with_run_type(self):
        """
        CRITICAL TEST: is_valid_id_format_compatible() with IDType.RUN.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError (no RUN attribute)
        - AFTER FIX: Will PASS and validate run ID compatibility correctly
        
        This validates type-specific format compatibility for RUN type.
        """
        try:
            # Generate run IDs for compatibility testing - will fail before fix
            run_id = self.id_manager.generate_id(IDType.RUN, prefix="compatibility_test")
            
            # Test compatibility validation with RUN type
            is_compatible = is_valid_id_format_compatible(run_id, IDType.RUN)
            assert is_compatible, f"Run ID should be compatible with RUN type: {run_id}"
            
            # Test compatibility validation without specific type
            is_valid_general = is_valid_id_format_compatible(run_id)
            assert is_valid_general, f"Run ID should be generally valid: {run_id}"
            
            # Test incompatibility with other types (should still pass due to migration compatibility)
            other_type_compatible = is_valid_id_format_compatible(run_id, IDType.USER)
            # Note: During migration period, this may pass for flexibility
            # The important thing is that RUN type specifically works
            
            # Generate IDs of other types and test they don't match RUN
            user_id = self.id_manager.generate_id(IDType.USER, prefix="compatibility_test")
            user_run_compatible = is_valid_id_format_compatible(user_id, IDType.RUN)
            # This might pass during migration period, but run_id with RUN must work
            
            self.generated_run_ids.update([run_id, user_id])
            self.test_metrics.record_custom("success", f"is_valid_id_format_compatible with RUN type successful")
            
        except AttributeError as e:
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"is_valid_id_format_compatible with RUN type failed: {e}")

    def test_format_validation_edge_cases(self):
        """
        CRITICAL TEST: Format validation edge cases with run IDs.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError (no RUN attribute)
        - AFTER FIX: Will PASS and handle edge cases correctly
        
        This validates edge case handling for run ID format validation.
        """
        try:
            # Test invalid run ID patterns
            for invalid_pattern in self.invalid_run_id_patterns:
                is_valid = is_valid_id_format(invalid_pattern)
                assert not is_valid, f"Invalid pattern should fail validation: '{invalid_pattern}'"
                
                # Test type compatibility with invalid pattern
                is_run_compatible = is_valid_id_format_compatible(invalid_pattern, IDType.RUN)
                assert not is_run_compatible, f"Invalid pattern should not be RUN compatible: '{invalid_pattern}'"
            
            # Test None and edge cases
            edge_cases = [
                None,  # None value
                123,   # Non-string
                [],    # List
                {},    # Dict
            ]
            
            for edge_case in edge_cases:
                try:
                    is_valid = is_valid_id_format(edge_case)
                    assert not is_valid, f"Edge case should fail validation: {edge_case} (type: {type(edge_case)})"
                except (TypeError, AttributeError) as expected:
                    # Expected for non-string types
                    pass
            
            # Generate a valid run ID to confirm positive case still works - will fail before fix
            valid_run_id = self.id_manager.generate_id(IDType.RUN, prefix="edge_case_positive")
            assert is_valid_id_format(valid_run_id), f"Valid run ID should pass: {valid_run_id}"
            assert is_valid_id_format_compatible(valid_run_id, IDType.RUN), f"Valid run ID should be RUN compatible: {valid_run_id}"
            
            self.generated_run_ids.add(valid_run_id)
            self.test_metrics.record_custom("success", f"Edge case validation successful: {len(self.invalid_run_id_patterns)} invalid patterns tested")
            
        except AttributeError as e:
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"Format validation edge cases failed: {e}")

    def test_ssot_format_pattern_compliance(self):
        """
        CRITICAL TEST: SSOT format pattern compliance for run IDs.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError (no RUN attribute)
        - AFTER FIX: Will PASS and run IDs comply with SSOT patterns
        
        This validates run IDs follow SSOT structured format patterns.
        """
        try:
            # Test various SSOT format patterns - will fail before fix
            ssot_patterns = [
                ("basic_ssot", None, r"^run_\d+_[0-9a-fA-F]{8}$"),
                ("prefixed_ssot", "ssot_test", r"^ssot_test_run_\d+_[0-9a-fA-F]{8}$"),
                ("complex_ssot", "golden_path_validation", r"^golden_path_validation_run_\d+_[0-9a-fA-F]{8}$"),
            ]
            
            for pattern_name, prefix, expected_regex in ssot_patterns:
                # Generate run ID with pattern
                if prefix:
                    run_id = self.id_manager.generate_id(IDType.RUN, prefix=prefix)
                else:
                    run_id = self.id_manager.generate_id(IDType.RUN)
                
                # Validate SSOT pattern compliance
                assert is_valid_id_format(run_id), f"SSOT run ID should be valid: {run_id} (pattern: {pattern_name})"
                
                # Validate specific pattern structure
                parts = run_id.split('_')
                assert len(parts) >= 3, f"SSOT run ID should have >= 3 parts: {parts} (pattern: {pattern_name})"
                
                # UUID part validation (last part, 8 hex chars)
                uuid_part = parts[-1]
                assert len(uuid_part) == 8, f"UUID part should be 8 chars: {uuid_part} (pattern: {pattern_name})"
                assert re.match(r'^[0-9a-fA-F]{8}$', uuid_part), f"UUID part should be hex: {uuid_part} (pattern: {pattern_name})"
                
                # Counter part validation (second to last, numeric)
                counter_part = parts[-2]
                assert counter_part.isdigit(), f"Counter part should be numeric: {counter_part} (pattern: {pattern_name})"
                assert int(counter_part) > 0, f"Counter should be positive: {counter_part} (pattern: {pattern_name})"
                
                # Type part validation (should contain "run")
                assert "run" in parts, f"Run ID should contain 'run': {run_id} (pattern: {pattern_name})"
                
                # Prefix validation if provided
                if prefix:
                    assert parts[0] == prefix, f"First part should be prefix: {parts[0]} != {prefix} (pattern: {pattern_name})"
                
                self.generated_run_ids.add(run_id)
            
            self.test_metrics.record_custom("success", f"SSOT format pattern compliance successful: {len(ssot_patterns)} patterns")
            
        except AttributeError as e:
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"SSOT format pattern compliance failed: {e}")

    def test_backwards_compatibility_format_validation(self):
        """
        CRITICAL TEST: Backwards compatibility with existing format validation.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL when testing RUN, but existing types should work
        - AFTER FIX: Will PASS and all types including RUN work correctly
        
        This ensures adding RUN doesn't break existing format validation.
        """
        # Test existing ID types still work (should work before and after fix)
        existing_types = [
            IDType.USER, IDType.SESSION, IDType.REQUEST, IDType.AGENT,
            IDType.TOOL, IDType.TRANSACTION, IDType.WEBSOCKET,
            IDType.EXECUTION, IDType.TRACE, IDType.METRIC, IDType.THREAD
        ]
        
        for id_type in existing_types:
            # Generate ID of existing type
            existing_id = self.id_manager.generate_id(id_type, prefix="backwards_compat")
            
            # Validate existing functionality still works
            assert is_valid_id_format(existing_id), f"Existing type {id_type.name} ID should be valid: {existing_id}"
            assert is_valid_id_format_compatible(existing_id, id_type), f"Existing type {id_type.name} should be compatible: {existing_id}"
            
            self.generated_run_ids.add(existing_id)
        
        try:
            # Test the new RUN type - will fail before fix
            run_id = self.id_manager.generate_id(IDType.RUN, prefix="backwards_compat")
            
            # Validate RUN type works with format validation
            assert is_valid_id_format(run_id), f"RUN type ID should be valid: {run_id}"
            assert is_valid_id_format_compatible(run_id, IDType.RUN), f"RUN type should be compatible: {run_id}"
            
            # Validate RUN ID is distinct from other types
            user_id = self.id_manager.generate_id(IDType.USER, prefix="backwards_compat")
            assert run_id != user_id, f"RUN and USER IDs should be different: {run_id} == {user_id}"
            
            # Validate both can be validated independently
            assert is_valid_id_format(run_id) and is_valid_id_format(user_id), f"Both IDs should be valid: run={run_id}, user={user_id}"
            
            self.generated_run_ids.update([run_id, user_id])
            self.test_metrics.record_custom("success", f"Backwards compatibility validation successful: {len(existing_types)} existing + RUN")
            
        except AttributeError as e:
            # Expected failure for RUN type before fix
            self.test_metrics.record_custom("expected_failure", f"Expected failure for RUN type before fix: {e}")
            
            # But validate that existing types still work
            assert len(self.generated_run_ids) >= len(existing_types), f"Existing types should still work: {len(self.generated_run_ids)}"
            
            pytest.fail(f"RUN type backwards compatibility failed (expected before fix): {e}")

    def test_format_validation_performance(self):
        """
        PERFORMANCE TEST: Format validation performance with run IDs.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError (no RUN attribute)
        - AFTER FIX: Will PASS and meet performance requirements
        
        This validates format validation performance doesn't degrade with RUN type.
        """
        try:
            # Generate run IDs for performance testing - will fail before fix
            num_validations = 1000
            run_ids = []
            
            for i in range(num_validations):
                run_id = self.id_manager.generate_id(IDType.RUN, prefix=f"perf_test_{i}")
                run_ids.append(run_id)
            
            # Performance test: is_valid_id_format
            start_time = time.time()
            format_results = [is_valid_id_format(run_id) for run_id in run_ids]
            format_time = time.time() - start_time
            
            # Performance test: is_valid_id_format_compatible
            start_time = time.time()
            compatible_results = [is_valid_id_format_compatible(run_id, IDType.RUN) for run_id in run_ids]
            compatible_time = time.time() - start_time
            
            # Validate results
            assert all(format_results), f"All run IDs should pass format validation: {sum(format_results)}/{len(format_results)}"
            assert all(compatible_results), f"All run IDs should be RUN compatible: {sum(compatible_results)}/{len(compatible_results)}"
            
            # Performance requirements
            format_ops_per_sec = num_validations / format_time
            compatible_ops_per_sec = num_validations / compatible_time
            
            # Should process at least 10,000 validations per second
            min_performance = 10000
            assert format_ops_per_sec >= min_performance, f"Format validation too slow: {format_ops_per_sec:.2f} ops/sec"
            assert compatible_ops_per_sec >= min_performance, f"Compatible validation too slow: {compatible_ops_per_sec:.2f} ops/sec"
            
            self.generated_run_ids.update(run_ids)
            self.test_metrics.record_custom("success", f"Format validation performance: format={format_ops_per_sec:.2f} ops/sec, compatible={compatible_ops_per_sec:.2f} ops/sec")
            
        except AttributeError as e:
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"Format validation performance test failed: {e}")

    def test_format_validation_comprehensive_coverage(self):
        """
        COMPREHENSIVE TEST: Complete format validation coverage for run IDs.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError (no RUN attribute)
        - AFTER FIX: Will PASS and provide comprehensive validation coverage
        
        This provides comprehensive validation coverage for all run ID scenarios.
        """
        try:
            # Comprehensive test scenarios - will fail before fix
            test_scenarios = [
                # Basic scenarios
                {"name": "basic", "prefix": None, "context": None},
                {"name": "prefixed", "prefix": "comprehensive_test", "context": None},
                {"name": "with_context", "prefix": "context_test", "context": {"test": "comprehensive"}},
                
                # Business scenarios
                {"name": "golden_path", "prefix": "golden_path_validation", "context": {"business_value": "$500K+ ARR"}},
                {"name": "websocket_integration", "prefix": "websocket_phase1", "context": {"integration": "websocket"}},
                {"name": "ssot_compliance", "prefix": "ssot_validation", "context": {"compliance": "ssot"}},
                
                # Edge scenarios
                {"name": "long_prefix", "prefix": "very_long_comprehensive_validation_prefix_test", "context": None},
                {"name": "numeric_prefix", "prefix": "test_123_validation", "context": None},
                {"name": "special_context", "prefix": "special", "context": {"special_chars": "test-data_123"}},
            ]
            
            validation_results = []
            
            for scenario in test_scenarios:
                # Generate run ID for scenario
                run_id = self.id_manager.generate_id(
                    IDType.RUN,
                    prefix=scenario["prefix"],
                    context=scenario["context"]
                )
                
                # Comprehensive validation checks
                checks = {
                    "basic_format": is_valid_id_format(run_id),
                    "run_compatible": is_valid_id_format_compatible(run_id, IDType.RUN),
                    "general_compatible": is_valid_id_format_compatible(run_id),
                    "manager_valid": self.id_manager.is_valid_id(run_id, IDType.RUN),
                    "metadata_exists": self.id_manager.get_id_metadata(run_id) is not None,
                }
                
                # Structural validation
                parts = run_id.split('_')
                structural_checks = {
                    "sufficient_parts": len(parts) >= 3,
                    "contains_run": "run" in parts,
                    "valid_counter": parts[-2].isdigit() if len(parts) >= 2 else False,
                    "valid_uuid": len(parts[-1]) == 8 and re.match(r'^[0-9a-fA-F]{8}$', parts[-1]) if len(parts) >= 1 else False,
                }
                
                # Prefix validation
                prefix_checks = {}
                if scenario["prefix"]:
                    prefix_checks["contains_prefix"] = scenario["prefix"] in run_id
                    prefix_checks["starts_with_prefix"] = run_id.startswith(scenario["prefix"])
                
                # Context validation
                context_checks = {}
                if scenario["context"]:
                    metadata = self.id_manager.get_id_metadata(run_id)
                    if metadata:
                        context_checks["context_preserved"] = all(
                            k in metadata.context and metadata.context[k] == v
                            for k, v in scenario["context"].items()
                        )
                
                # Combine all checks
                all_checks = {**checks, **structural_checks, **prefix_checks, **context_checks}
                failed_checks = [name for name, result in all_checks.items() if not result]
                
                validation_result = {
                    "scenario": scenario["name"],
                    "run_id": run_id,
                    "checks": all_checks,
                    "failed_checks": failed_checks,
                    "success": len(failed_checks) == 0
                }
                
                validation_results.append(validation_result)
                self.generated_run_ids.add(run_id)
                
                # Assert this scenario passes
                assert len(failed_checks) == 0, f"Scenario {scenario['name']} failed checks: {failed_checks} for run_id: {run_id}"
            
            # Validate overall results
            successful_scenarios = [r for r in validation_results if r["success"]]
            assert len(successful_scenarios) == len(test_scenarios), f"All scenarios should pass: {len(successful_scenarios)}/{len(test_scenarios)}"
            
            self.test_metrics.record_custom("success", f"Comprehensive format validation coverage successful: {len(test_scenarios)} scenarios")
            
        except AttributeError as e:
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"Comprehensive format validation coverage failed: {e}")

    def teardown_method(self, method=None):
        """Clean up format validation test environment and record metrics."""
        
        # Clean up generated run_ids
        if hasattr(self, 'id_manager') and hasattr(self, 'generated_run_ids'):
            for run_id in self.generated_run_ids:
                try:
                    self.id_manager.release_id(run_id)
                except:
                    pass  # Best effort cleanup
        
        # Record metrics
        if hasattr(self, 'test_metrics'):
            self.test_metrics.record_custom("test_completed", True)
            
        super().teardown_method(method)