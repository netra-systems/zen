"""
Unit Tests for IDType.RUN ID Generation - SSOT CRITICAL

BUSINESS VALUE:
- Segment: Platform/Internal - System Stability & Development Velocity  
- Goal: Ensure generate_id(IDType.RUN) produces valid run IDs after fix implementation
- Value Impact: Validates Golden Path WebSocket run ID generation for $500K+ ARR functionality
- Revenue Impact: Prevents runtime failures in production run ID generation patterns

TESTING STRATEGY:
- Tests WILL FAIL before fix (missing IDType.RUN enum value)
- Tests WILL PASS after fix (when RUN = "run" is added to IDType)
- Validates run ID generation patterns, uniqueness, and SSOT compliance
- Tests both instance and class method ID generation patterns

SSOT COMPLIANCE:
- Uses test_framework.ssot.base_test_case.SSotBaseTestCase  
- Imports only from SSOT_IMPORT_REGISTRY.md verified paths
- Follows SSOT testing patterns for ID generation
- No mocks - tests real ID generation functionality

CRITICAL TEST COVERAGE:
1. Basic run ID generation with IDType.RUN
2. Run ID generation with prefixes and context
3. Run ID uniqueness validation
4. Run ID format compliance with SSOT patterns
5. Integration with existing ID generation methods
6. Performance and scalability validation
"""

import pytest
import time
import uuid
from typing import Set, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# SSOT imports from verified registry
from test_framework.ssot.base_test_case import SSotBaseTestCase, SsotTestMetrics, CategoryType
from shared.isolated_environment import get_env

# Core ID management imports - SSOT verified paths
from netra_backend.app.core.unified_id_manager import (
    IDType, UnifiedIDManager, generate_id, IDMetadata,
    is_valid_id_format, is_valid_id_format_compatible
)


@pytest.mark.unit
class IDTypeRunGenerationTests(SSotBaseTestCase):
    """
    Unit tests for IDType.RUN ID generation functionality.
    
    These tests validate that run ID generation works correctly with the
    new IDType.RUN enum value and follows SSOT patterns.
    """

    def setup_method(self, method=None):
        """Set up test environment with fresh ID manager."""
        super().setup_method(method)
        
        # Test metrics for SSOT compliance
        self.test_metrics = SsotTestMetrics()
        self.test_metrics.record_custom("category", "UNIT")
        self.test_metrics.record_custom("test_name", method.__name__ if method else "setup")
        self.test_metrics.record_custom("business_value_segment", "Platform/Internal")
        self.test_metrics.record_custom("expected_outcome", "Validate IDType.RUN ID generation works correctly")
        
        # Fresh ID manager for each test
        self.id_manager = UnifiedIDManager()
        
        # Test data for validation
        self.generated_ids: Set[str] = set()
        self.test_prefixes = ["ssot_test", "run_validation", "unit_test"]

    def test_basic_run_id_generation(self):
        """
        CRITICAL TEST: Basic run ID generation with IDType.RUN.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError: IDType has no attribute 'RUN'
        - AFTER FIX: Will PASS and generate valid run ID with correct format
        
        This tests the core functionality identified in GitHub Issue #883.
        """
        try:
            # Generate basic run ID - will fail before fix
            run_id = self.id_manager.generate_id(IDType.RUN)
            
            # Validate generated ID
            assert run_id is not None, "Generated run ID should not be None"
            assert isinstance(run_id, str), f"Run ID should be string, got: {type(run_id)}"
            assert len(run_id) > 0, "Run ID should not be empty"
            
            # Validate SSOT format pattern: idtype_counter_uuid8
            parts = run_id.split('_')
            assert len(parts) >= 3, f"Run ID should have at least 3 parts, got: {parts}"
            assert "run" in parts, f"Run ID should contain 'run' identifier, got: {run_id}"
            
            # Validate UUID part (last 8 characters should be hex)
            uuid_part = parts[-1]
            assert len(uuid_part) == 8, f"UUID part should be 8 chars, got: {len(uuid_part)}"
            assert all(c in '0123456789abcdefABCDEF' for c in uuid_part), f"Invalid UUID part: {uuid_part}"
            
            # Validate counter part (second to last should be numeric)
            counter_part = parts[-2]
            assert counter_part.isdigit(), f"Counter part should be numeric, got: {counter_part}"
            
            self.generated_ids.add(run_id)
            self.test_metrics.record_custom("success", f"Basic run ID generated successfully: {run_id}")
            
        except AttributeError as e:
            # Expected failure before fix
            assert "RUN" in str(e), f"Expected 'RUN' in error message, got: {e}"
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"IDType.RUN ID generation failed (expected before fix): {e}")

    def test_run_id_generation_with_prefix(self):
        """
        CRITICAL TEST: Run ID generation with custom prefix.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError (no RUN attribute)
        - AFTER FIX: Will PASS and generate run ID with custom prefix
        
        This validates prefix functionality works with RUN type.
        """
        try:
            for prefix in self.test_prefixes:
                # Generate run ID with prefix - will fail before fix
                run_id = self.id_manager.generate_id(IDType.RUN, prefix=prefix)
                
                # Validate prefix is included
                assert prefix in run_id, f"Run ID should contain prefix '{prefix}', got: {run_id}"
                assert run_id.startswith(prefix), f"Run ID should start with prefix '{prefix}', got: {run_id}"
                
                # Validate SSOT format: prefix_run_counter_uuid8
                parts = run_id.split('_')
                assert len(parts) >= 4, f"Prefixed run ID should have at least 4 parts, got: {parts}"
                assert parts[0] == prefix, f"First part should be prefix '{prefix}', got: {parts[0]}"
                assert "run" in parts, f"Run ID should contain 'run' type, got: {run_id}"
                
                self.generated_ids.add(run_id)
            
            self.test_metrics.record_custom("success", f"Run IDs with prefixes generated successfully: {len(self.test_prefixes)} variants")
            
        except AttributeError as e:
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"IDType.RUN prefixed generation failed: {e}")

    def test_run_id_generation_with_context(self):
        """
        CRITICAL TEST: Run ID generation with context metadata.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError (no RUN attribute)  
        - AFTER FIX: Will PASS and generate run ID with context stored
        
        This validates context functionality works with RUN type.
        """
        try:
            # Test context data
            context_data = {
                "test_type": "unit_test",
                "business_value": "Golden Path validation",
                "created_by": "ssot_test_suite",
                "priority": "critical"
            }
            
            # Generate run ID with context - will fail before fix
            run_id = self.id_manager.generate_id(IDType.RUN, prefix="context_test", context=context_data)
            
            # Validate ID generation
            assert run_id is not None, "Context run ID should not be None"
            assert "context_test" in run_id, f"Run ID should contain context prefix, got: {run_id}"
            
            # Validate context is stored
            metadata = self.id_manager.get_id_metadata(run_id)
            assert metadata is not None, f"Metadata should exist for run ID: {run_id}"
            assert metadata.id_type == IDType.RUN, f"Metadata type should be RUN, got: {metadata.id_type}"
            assert metadata.context == context_data, f"Context mismatch. Expected: {context_data}, got: {metadata.context}"
            
            self.generated_ids.add(run_id)
            self.test_metrics.record_custom("success", f"Run ID with context generated and stored successfully")
            
        except AttributeError as e:
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"IDType.RUN context generation failed: {e}")

    def test_run_id_uniqueness_validation(self):
        """
        CRITICAL TEST: Validate run ID uniqueness across multiple generations.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError (no RUN attribute)
        - AFTER FIX: Will PASS and all generated run IDs are unique
        
        This ensures run ID generation doesn't create duplicates.
        """
        try:
            num_ids = 100
            generated_run_ids = set()
            
            # Generate multiple run IDs - will fail before fix
            for i in range(num_ids):
                run_id = self.id_manager.generate_id(IDType.RUN, prefix=f"unique_test_{i}")
                
                # Validate uniqueness
                assert run_id not in generated_run_ids, f"Duplicate run ID generated: {run_id}"
                generated_run_ids.add(run_id)
                
                # Validate basic format
                assert "run" in run_id, f"Run ID missing 'run' identifier: {run_id}"
                assert f"unique_test_{i}" in run_id, f"Run ID missing expected prefix: {run_id}"
            
            # Validate all IDs are unique
            assert len(generated_run_ids) == num_ids, f"Expected {num_ids} unique IDs, got {len(generated_run_ids)}"
            
            self.generated_ids.update(generated_run_ids)
            self.test_metrics.record_custom("success", f"Generated {num_ids} unique run IDs successfully")
            
        except AttributeError as e:
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"IDType.RUN uniqueness validation failed: {e}")

    def test_run_id_format_compliance(self):
        """
        CRITICAL TEST: Validate run ID format compliance with SSOT standards.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError (no RUN attribute)
        - AFTER FIX: Will PASS and all run IDs pass format validation
        
        This ensures generated run IDs comply with SSOT format standards.
        """
        try:
            # Generate various run ID formats
            test_cases = [
                ("basic", None),
                ("with_prefix", "ssot_test"),
                ("complex_prefix", "golden_path_validation"),
                ("numeric_prefix", "test_123"),
            ]
            
            for test_name, prefix in test_cases:
                # Generate run ID - will fail before fix
                if prefix:
                    run_id = self.id_manager.generate_id(IDType.RUN, prefix=prefix)
                else:
                    run_id = self.id_manager.generate_id(IDType.RUN)
                
                # Validate against SSOT format validation
                assert is_valid_id_format(run_id), f"Run ID failed format validation: {run_id}"
                assert is_valid_id_format_compatible(run_id, IDType.RUN), f"Run ID failed RUN type validation: {run_id}"
                
                # Additional SSOT format checks
                parts = run_id.split('_')
                assert len(parts) >= 3, f"Run ID insufficient parts: {run_id}"
                
                # UUID part validation
                uuid_part = parts[-1]
                assert len(uuid_part) == 8, f"Invalid UUID part length: {uuid_part}"
                
                # Counter validation
                counter_part = parts[-2]
                assert counter_part.isdigit(), f"Invalid counter part: {counter_part}"
                
                self.generated_ids.add(run_id)
            
            self.test_metrics.record_custom("success", f"All run ID formats passed SSOT compliance validation")
            
        except AttributeError as e:
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"IDType.RUN format compliance failed: {e}")

    def test_run_id_integration_with_existing_methods(self):
        """
        CRITICAL TEST: Validate RUN type integrates with existing ID management methods.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError (no RUN attribute)
        - AFTER FIX: Will PASS and RUN type works with all ID management methods
        
        This ensures backwards compatibility and integration.
        """
        try:
            # Generate run ID - will fail before fix
            run_id = self.id_manager.generate_id(IDType.RUN, prefix="integration_test")
            
            # Test validation methods
            assert self.id_manager.is_valid_id(run_id), f"Run ID should be valid: {run_id}"
            assert self.id_manager.is_valid_id(run_id, IDType.RUN), f"Run ID should be valid for RUN type: {run_id}"
            
            # Test metadata retrieval
            metadata = self.id_manager.get_id_metadata(run_id)
            assert metadata is not None, f"Metadata should exist: {run_id}"
            assert metadata.id_type == IDType.RUN, f"Metadata type should be RUN: {metadata.id_type}"
            
            # Test active IDs tracking
            active_run_ids = self.id_manager.get_active_ids(IDType.RUN)
            assert run_id in active_run_ids, f"Run ID should be in active IDs: {run_id}"
            
            # Test ID counting
            run_count = self.id_manager.count_active_ids(IDType.RUN)
            assert run_count >= 1, f"RUN ID count should be >= 1, got: {run_count}"
            
            # Test ID release
            release_success = self.id_manager.release_id(run_id)
            assert release_success, f"Run ID release should succeed: {run_id}"
            
            # Test stats include RUN type
            stats = self.id_manager.get_stats()
            assert "run" in stats["active_by_type"], f"Stats should include RUN type: {stats}"
            assert "run" in stats["counters_by_type"], f"Stats should include RUN counters: {stats}"
            
            self.generated_ids.add(run_id)
            self.test_metrics.record_custom("success", f"Run ID integration with existing methods validated")
            
        except AttributeError as e:
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"IDType.RUN integration test failed: {e}")

    def test_concurrent_run_id_generation(self):
        """
        CRITICAL TEST: Validate run ID generation under concurrent load.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError (no RUN attribute)
        - AFTER FIX: Will PASS and handle concurrent generation safely
        
        This validates thread safety and performance with RUN type.
        """
        try:
            num_threads = 10
            ids_per_thread = 20
            all_run_ids = set()
            
            def generate_run_ids_batch(thread_id: int) -> List[str]:
                """Generate a batch of run IDs in a thread."""
                batch_ids = []
                for i in range(ids_per_thread):
                    # This will fail before fix
                    run_id = self.id_manager.generate_id(IDType.RUN, prefix=f"thread_{thread_id}_id_{i}")
                    batch_ids.append(run_id)
                return batch_ids
            
            # Execute concurrent generation
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(generate_run_ids_batch, i) for i in range(num_threads)]
                
                for future in as_completed(futures):
                    batch_ids = future.result()
                    
                    # Validate no duplicates in batch
                    assert len(batch_ids) == len(set(batch_ids)), f"Duplicates found in batch: {batch_ids}"
                    
                    # Add to global set
                    for run_id in batch_ids:
                        assert run_id not in all_run_ids, f"Global duplicate found: {run_id}"
                        all_run_ids.add(run_id)
            
            # Validate total uniqueness
            expected_total = num_threads * ids_per_thread
            assert len(all_run_ids) == expected_total, f"Expected {expected_total} unique IDs, got {len(all_run_ids)}"
            
            # Validate all IDs are valid
            for run_id in list(all_run_ids)[:10]:  # Sample validation
                assert is_valid_id_format(run_id), f"Invalid concurrent run ID: {run_id}"
                assert "run" in run_id, f"Run ID missing 'run' identifier: {run_id}"
            
            self.generated_ids.update(all_run_ids)
            self.test_metrics.record_custom("success", f"Concurrent run ID generation successful: {len(all_run_ids)} unique IDs")
            
        except AttributeError as e:
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"IDType.RUN concurrent generation failed: {e}")

    def test_run_id_performance_baseline(self):
        """
        PERFORMANCE TEST: Validate run ID generation performance baseline.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError (no RUN attribute)
        - AFTER FIX: Will PASS and meet performance requirements
        
        This ensures RUN ID generation meets performance standards.
        """
        try:
            num_generations = 1000
            start_time = time.time()
            
            # Generate IDs and measure performance - will fail before fix
            for i in range(num_generations):
                run_id = self.id_manager.generate_id(IDType.RUN, prefix=f"perf_test_{i}")
                
                # Basic validation
                assert run_id is not None, f"Run ID should not be None: iteration {i}"
                assert "run" in run_id, f"Run ID missing 'run': {run_id}"
            
            end_time = time.time()
            total_time = end_time - start_time
            ids_per_second = num_generations / total_time
            
            # Performance requirements (should generate at least 1000 IDs/sec)
            min_performance = 1000
            assert ids_per_second >= min_performance, f"Performance too slow: {ids_per_second:.2f} IDs/sec, expected >= {min_performance}"
            
            self.test_metrics.record_custom("success", f"Run ID performance: {ids_per_second:.2f} IDs/sec")
            
        except AttributeError as e:
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"IDType.RUN performance test failed: {e}")

    def teardown_method(self, method=None):
        """Clean up test environment and record metrics."""
        
        # Clean up generated IDs
        if hasattr(self, 'id_manager') and hasattr(self, 'generated_ids'):
            for run_id in self.generated_ids:
                try:
                    self.id_manager.release_id(run_id)
                except:
                    pass  # Best effort cleanup
        
        # Record metrics
        if hasattr(self, 'test_metrics'):
            self.test_metrics.record_custom("test_completed", True)
            
        super().teardown_method(method)