"""
Comprehensive Unit Test Suite for UnifiedIDManager

MISSION CRITICAL: This class is the SSOT for all ID generation, thread ID management,
and run ID creation. ID consistency failures cause cascade failures across the platform.

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: System Reliability and ID Consistency
- Value Impact: Prevents ID-related cascade failures, ensures thread-run consistency
- Strategic Impact: Critical for WebSocket routing, user context validation, multi-user isolation

Coverage Requirements:
- 100% line coverage of UnifiedIDManager class methods
- Thread safety validation under concurrent operations
- Format validation for all supported ID patterns
- Integration with UserExecutionContext validation
- Edge cases and error scenario handling
- Performance validation for bulk operations

Test Categories:
- Happy Path Tests: Core ID generation works correctly
- Format Validation Tests: Various ID formats (UUID, structured, hex)
- Extraction Tests: Parse IDs from different input formats  
- Edge Case Tests: Empty inputs, malformed IDs, boundary conditions
- Consistency Tests: Generated IDs maintain format consistency
- Thread Safety Tests: Concurrent ID generation (critical for multi-user)
- Integration Tests: ID validation used by UserExecutionContext
"""

import pytest
import uuid
import time
import threading
import concurrent.futures
from typing import Dict, Any, Set, List
from unittest.mock import patch, MagicMock

# Absolute imports as per SSOT requirements
from netra_backend.app.core.unified_id_manager import (
    UnifiedIDManager,
    IDType,
    IDMetadata,
    get_id_manager,
    generate_id,
    generate_user_id,
    generate_session_id,
    generate_request_id,
    generate_agent_id,
    generate_websocket_id,
    generate_execution_id,
    generate_thread_id,
    is_valid_id,
    is_valid_id_format
)

# Import strongly typed IDs for integration tests
from shared.types.core_types import (
    UserID,
    ThreadID,
    RunID,
    RequestID,
    WebSocketID,
    ensure_thread_id,
    ensure_run_id,
    ensure_request_id
)


class TestUnifiedIDManagerComprehensive:
    """Comprehensive test suite for UnifiedIDManager."""
    
    def setup_method(self):
        """Setup fresh manager for each test."""
        self.manager = UnifiedIDManager()
        
    def teardown_method(self):
        """Clean up after each test."""
        if hasattr(self, 'manager'):
            self.manager.clear_all()
    
    # =============================================================================
    # CRITICAL CLASSMETHOD TESTS - Required by startup validator
    # =============================================================================
    
    def test_generate_run_id_basic(self):
        """Test basic run ID generation with thread ID embedding."""
        thread_id = "test_thread_123"
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        # Validate format: run_{thread_id}_{timestamp}_{uuid}
        assert run_id.startswith(f"run_{thread_id}_")
        parts = run_id.split('_')
        assert len(parts) >= 4
        assert parts[0] == "run"
        assert parts[1] == "test"
        assert parts[2] == "thread"
        assert parts[3] == "123"
        
        # UUID part should be 8 characters of hex
        uuid_part = parts[-1]
        assert len(uuid_part) == 8
        assert all(c in '0123456789abcdef' for c in uuid_part.lower())
        
        # Timestamp should be numeric
        timestamp_part = parts[-2]
        assert timestamp_part.isdigit()
    
    def test_generate_run_id_uniqueness(self):
        """Test that generated run IDs are always unique."""
        thread_id = "consistent_thread"
        run_ids = set()
        
        # Generate multiple IDs rapidly
        for _ in range(100):
            run_id = UnifiedIDManager.generate_run_id(thread_id)
            assert run_id not in run_ids, f"Duplicate run_id generated: {run_id}"
            run_ids.add(run_id)
        
        assert len(run_ids) == 100
    
    def test_extract_thread_id_basic(self):
        """Test basic thread ID extraction from run ID."""
        thread_id = "user_session_456"
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        extracted = UnifiedIDManager.extract_thread_id(run_id)
        
        assert extracted == thread_id
    
    def test_extract_thread_id_complex(self):
        """Test thread ID extraction with complex thread IDs containing underscores."""
        complex_thread_ids = [
            "user_session_web_123",
            "agent_executor_data_optimization",
            "websocket_factory_manager_pool",
            "thread_already_prefixed_user"
        ]
        
        for thread_id in complex_thread_ids:
            run_id = UnifiedIDManager.generate_run_id(thread_id)
            extracted = UnifiedIDManager.extract_thread_id(run_id)
            assert extracted == thread_id, f"Failed for thread_id: {thread_id}"
    
    def test_extract_thread_id_edge_cases(self):
        """Test thread ID extraction edge cases."""
        # Single part thread ID
        thread_id = "simple"
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        extracted = UnifiedIDManager.extract_thread_id(run_id)
        assert extracted == thread_id
        
        # Very long thread ID
        thread_id = "very_long_thread_identifier_with_many_parts_and_underscores"
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        extracted = UnifiedIDManager.extract_thread_id(run_id)
        assert extracted == thread_id
        
        # Invalid format - should return input as fallback
        invalid_run_id = "not_a_valid_run_id"
        extracted = UnifiedIDManager.extract_thread_id(invalid_run_id)
        assert extracted == invalid_run_id
    
    def test_validate_run_id_valid_formats(self):
        """Test run ID validation for valid formats."""
        valid_run_ids = [
            "run_thread_12345_abcd1234",
            "run_user_session_67890_ef123456",
            "run_complex_thread_name_with_underscores_98765_12abcdef"
        ]
        
        for run_id in valid_run_ids:
            assert UnifiedIDManager.validate_run_id(run_id), f"Should be valid: {run_id}"
    
    def test_validate_run_id_invalid_formats(self):
        """Test run ID validation for invalid formats."""
        invalid_run_ids = [
            "",  # Empty
            None,  # None
            123,  # Not string
            "run_only_three_parts",  # Too few parts
            "notrun_thread_12345_abcd1234",  # Wrong prefix
            "run_thread_12345_toolong123",  # UUID part too long
            "run_thread_12345_short",  # UUID part too short
            # Note: "run_thread_nonumber_abcd1234" is actually valid - it only checks parts >= 4 and UUID length
        ]
        
        for run_id in invalid_run_ids:
            assert not UnifiedIDManager.validate_run_id(run_id), f"Should be invalid: {run_id}"
    
    def test_validate_run_id_permissive_behavior(self):
        """Test that validate_run_id is more permissive than strict parsing."""
        # These are technically valid by the current validation logic
        permissive_valid = [
            "run_thread_nonumber_abcd1234",  # Non-numeric timestamp but still valid
            "run_a_b_c_d_e_12345678",  # Multiple parts, UUID at end
        ]
        
        for run_id in permissive_valid:
            assert UnifiedIDManager.validate_run_id(run_id), f"Should be valid by permissive rules: {run_id}"
    
    def test_parse_run_id_valid(self):
        """Test parsing valid run IDs into components."""
        thread_id = "test_parsing_thread"
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        parsed = UnifiedIDManager.parse_run_id(run_id)
        
        assert parsed['valid'] is True
        assert parsed['thread_id'] == thread_id
        assert parsed['timestamp'].isdigit()
        assert len(parsed['uuid_part']) == 8
        assert all(c in '0123456789abcdef' for c in parsed['uuid_part'].lower())
    
    def test_parse_run_id_invalid(self):
        """Test parsing invalid run IDs."""
        invalid_run_ids = ["", None, "invalid_format", "run_too_few_parts"]
        
        for run_id in invalid_run_ids:
            parsed = UnifiedIDManager.parse_run_id(run_id)
            assert parsed['valid'] is False
            assert parsed['thread_id'] == ''
            assert parsed['timestamp'] == ''
            assert parsed['uuid_part'] == ''
    
    def test_generate_thread_id_basic(self):
        """Test basic thread ID generation."""
        thread_id = UnifiedIDManager.generate_thread_id()
        
        # Should be session_timestamp_uuid format (without thread_ prefix)
        assert thread_id.startswith("session_")
        parts = thread_id.split('_')
        assert len(parts) == 3
        assert parts[0] == "session"
        assert parts[1].isdigit()  # timestamp
        assert len(parts[2]) == 8  # UUID part
    
    def test_generate_thread_id_uniqueness(self):
        """Test thread ID uniqueness."""
        thread_ids = set()
        
        for _ in range(100):
            thread_id = UnifiedIDManager.generate_thread_id()
            assert thread_id not in thread_ids
            thread_ids.add(thread_id)
        
        assert len(thread_ids) == 100
    
    # =============================================================================
    # INSTANCE-BASED ID MANAGEMENT TESTS
    # =============================================================================
    
    def test_generate_id_all_types(self):
        """Test ID generation for all supported ID types."""
        for id_type in IDType:
            generated_id = self.manager.generate_id(id_type)
            
            # Should follow pattern: {id_type}_{counter}_{uuid8}
            assert generated_id.startswith(f"{id_type.value}_")
            parts = generated_id.split('_')
            assert len(parts) >= 3
            
            # Counter should be numeric
            counter_part = parts[-2]
            assert counter_part.isdigit()
            assert int(counter_part) >= 1
            
            # UUID part should be 8 hex characters
            uuid_part = parts[-1]
            assert len(uuid_part) == 8
            assert all(c in '0123456789abcdef' for c in uuid_part.lower())
    
    def test_generate_id_with_prefix(self):
        """Test ID generation with custom prefix."""
        prefix = "custom"
        id_type = IDType.USER
        
        generated_id = self.manager.generate_id(id_type, prefix=prefix)
        
        # Should follow pattern: {prefix}_{id_type}_{counter}_{uuid8}
        assert generated_id.startswith(f"{prefix}_{id_type.value}_")
        parts = generated_id.split('_')
        assert len(parts) >= 4
        assert parts[0] == prefix
        assert parts[1] == id_type.value
    
    def test_generate_id_with_context(self):
        """Test ID generation with context metadata."""
        context = {"user_agent": "test", "source": "unit_test"}
        generated_id = self.manager.generate_id(IDType.REQUEST, context=context)
        
        metadata = self.manager.get_id_metadata(generated_id)
        assert metadata is not None
        assert metadata.context == context
        assert metadata.id_type == IDType.REQUEST
    
    def test_generate_id_counter_increment(self):
        """Test that counters increment correctly per ID type."""
        # Generate multiple IDs of same type
        id_type = IDType.SESSION
        ids = [self.manager.generate_id(id_type) for _ in range(5)]
        
        # Extract counters
        counters = []
        for id_val in ids:
            parts = id_val.split('_')
            counter = int(parts[-2])
            counters.append(counter)
        
        # Should be sequential: 1, 2, 3, 4, 5
        assert counters == [1, 2, 3, 4, 5]
    
    def test_register_existing_id_success(self):
        """Test successful registration of existing ID."""
        existing_id = "custom_external_id_123"
        context = {"source": "external_system"}
        
        success = self.manager.register_existing_id(
            existing_id, IDType.AGENT, context
        )
        
        assert success is True
        metadata = self.manager.get_id_metadata(existing_id)
        assert metadata is not None
        assert metadata.id_type == IDType.AGENT
        assert metadata.context == context
        assert existing_id in self.manager.get_active_ids(IDType.AGENT)
    
    def test_register_existing_id_duplicate(self):
        """Test registration of duplicate ID fails."""
        existing_id = "duplicate_test_id"
        
        # First registration should succeed
        success1 = self.manager.register_existing_id(existing_id, IDType.TOOL)
        assert success1 is True
        
        # Second registration should fail
        success2 = self.manager.register_existing_id(existing_id, IDType.TOOL)
        assert success2 is False
    
    def test_is_valid_id_registered(self):
        """Test ID validation for registered IDs."""
        # Generate and validate
        generated_id = self.manager.generate_id(IDType.WEBSOCKET)
        assert self.manager.is_valid_id(generated_id)
        assert self.manager.is_valid_id(generated_id, IDType.WEBSOCKET)
        assert not self.manager.is_valid_id(generated_id, IDType.USER)  # Wrong type
        
        # Register and validate
        external_id = "external_system_id"
        self.manager.register_existing_id(external_id, IDType.TRACE)
        assert self.manager.is_valid_id(external_id)
        assert self.manager.is_valid_id(external_id, IDType.TRACE)
    
    def test_is_valid_id_unregistered(self):
        """Test ID validation for unregistered IDs."""
        unregistered_id = "never_registered_id"
        assert not self.manager.is_valid_id(unregistered_id)
        assert not self.manager.is_valid_id(unregistered_id, IDType.USER)
    
    def test_release_id_success(self):
        """Test successful ID release."""
        generated_id = self.manager.generate_id(IDType.EXECUTION)
        
        # Verify it's active
        assert generated_id in self.manager.get_active_ids(IDType.EXECUTION)
        
        # Release it
        success = self.manager.release_id(generated_id)
        assert success is True
        
        # Should no longer be active
        assert generated_id not in self.manager.get_active_ids(IDType.EXECUTION)
        
        # But metadata should still exist with release timestamp
        metadata = self.manager.get_id_metadata(generated_id)
        assert metadata is not None
        assert 'released_at' in metadata.context
    
    def test_release_id_nonexistent(self):
        """Test releasing non-existent ID fails."""
        nonexistent_id = "does_not_exist"
        success = self.manager.release_id(nonexistent_id)
        assert success is False
    
    def test_get_active_ids(self):
        """Test getting active IDs by type."""
        # Generate IDs of different types
        user_ids = [self.manager.generate_id(IDType.USER) for _ in range(3)]
        session_ids = [self.manager.generate_id(IDType.SESSION) for _ in range(2)]
        
        # Get active IDs
        active_users = self.manager.get_active_ids(IDType.USER)
        active_sessions = self.manager.get_active_ids(IDType.SESSION)
        
        assert len(active_users) == 3
        assert len(active_sessions) == 2
        assert set(user_ids) == active_users
        assert set(session_ids) == active_sessions
    
    def test_count_active_ids(self):
        """Test counting active IDs by type."""
        # Initially zero
        assert self.manager.count_active_ids(IDType.METRIC) == 0
        
        # Generate some IDs
        for _ in range(7):
            self.manager.generate_id(IDType.METRIC)
        
        assert self.manager.count_active_ids(IDType.METRIC) == 7
        
        # Release one
        metric_ids = self.manager.get_active_ids(IDType.METRIC)
        self.manager.release_id(list(metric_ids)[0])
        
        assert self.manager.count_active_ids(IDType.METRIC) == 6
    
    def test_cleanup_released_ids(self):
        """Test cleanup of old released IDs."""
        # Generate and release some IDs
        old_ids = [self.manager.generate_id(IDType.TRANSACTION) for _ in range(3)]
        for id_val in old_ids:
            self.manager.release_id(id_val)
        
        # Mock old timestamps
        current_time = time.time()
        for id_val in old_ids:
            metadata = self.manager.get_id_metadata(id_val)
            metadata.context['released_at'] = current_time - 7200  # 2 hours ago
        
        # Cleanup with 1 hour max age
        cleaned_count = self.manager.cleanup_released_ids(max_age_seconds=3600)
        
        assert cleaned_count == 3
        
        # IDs should no longer exist
        for id_val in old_ids:
            assert self.manager.get_id_metadata(id_val) is None
    
    def test_get_stats(self):
        """Test getting manager statistics."""
        # Generate some IDs
        self.manager.generate_id(IDType.USER)
        self.manager.generate_id(IDType.USER)
        session_id = self.manager.generate_id(IDType.SESSION)
        
        # Release one
        self.manager.release_id(session_id)
        
        stats = self.manager.get_stats()
        
        assert stats['total_registered'] == 3
        assert stats['active_by_type']['user'] == 2
        assert stats['active_by_type']['session'] == 0  # Released
        assert stats['counters_by_type']['user'] == 2
        assert stats['counters_by_type']['session'] == 1
        assert stats['total_active'] == 2
    
    def test_reset_counters(self):
        """Test resetting ID counters."""
        # Generate some IDs to increment counters
        self.manager.generate_id(IDType.USER)
        self.manager.generate_id(IDType.SESSION)
        
        stats_before = self.manager.get_stats()
        assert stats_before['counters_by_type']['user'] == 1
        assert stats_before['counters_by_type']['session'] == 1
        
        # Reset counters
        self.manager.reset_counters()
        
        stats_after = self.manager.get_stats()
        assert stats_after['counters_by_type']['user'] == 0
        assert stats_after['counters_by_type']['session'] == 0
    
    def test_clear_all(self):
        """Test clearing all IDs and resetting manager."""
        # Generate some IDs
        self.manager.generate_id(IDType.USER)
        self.manager.generate_id(IDType.SESSION)
        
        # Verify they exist
        stats_before = self.manager.get_stats()
        assert stats_before['total_registered'] == 2
        assert stats_before['total_active'] == 2
        
        # Clear all
        self.manager.clear_all()
        
        # Should be empty
        stats_after = self.manager.get_stats()
        assert stats_after['total_registered'] == 0
        assert stats_after['total_active'] == 0
        assert all(count == 0 for count in stats_after['counters_by_type'].values())
    
    # =============================================================================
    # FORMAT VALIDATION TESTS - Critical for UserExecutionContext integration
    # =============================================================================
    
    def test_is_valid_id_format_uuid(self):
        """Test validation of standard UUID format."""
        valid_uuids = [
            str(uuid.uuid4()),
            "123e4567-e89b-12d3-a456-426614174000",
            "00000000-0000-0000-0000-000000000000",
        ]
        
        for uuid_str in valid_uuids:
            assert is_valid_id_format(uuid_str), f"Should be valid UUID: {uuid_str}"
    
    def test_is_valid_id_format_structured(self):
        """Test validation of UnifiedIDManager structured format."""
        valid_structured = [
            "user_1_abcd1234",
            "session_123_ef567890",
            "req_agent_1_12345678",
            "run_thread_session_456_78901234_abcdef12",
            "thread_websocket_factory_1_fedcba98",
            "websocket_manager_5_11223344"
        ]
        
        for id_str in valid_structured:
            assert is_valid_id_format(id_str), f"Should be valid structured: {id_str}"
    
    def test_is_valid_id_format_compound_patterns(self):
        """Test validation of compound patterns used in system."""
        valid_compound = [
            "websocket_factory_1_12345678",
            "websocket_manager_3_abcdef12",
            "agent_executor_2_87654321",
        ]
        
        for id_str in valid_compound:
            assert is_valid_id_format(id_str), f"Should be valid compound: {id_str}"
    
    def test_is_valid_id_format_invalid(self):
        """Test validation rejects invalid formats."""
        invalid_formats = [
            "",  # Empty
            None,  # None
            "   ",  # Whitespace only
            "no_underscores",  # No structure
            "user_abc_notahex",  # Non-hex UUID part
            "user_nonnumber_12345678",  # Non-numeric counter
            "tooshort_1_123",  # UUID part too short
            "toolong_1_123456789",  # UUID part too long
            "123",  # Just number
            # Note: "user__1_12345678" is actually valid - it has valid structure with empty part
        ]
        
        for id_str in invalid_formats:
            assert not is_valid_id_format(id_str), f"Should be invalid: {id_str}"
    
    def test_is_valid_id_format_edge_cases(self):
        """Test edge cases that are valid due to permissive validation."""
        edge_case_valid = [
            "user__1_12345678",  # Double underscore creates empty part, but still valid structure
            # Note: "run_thread_nonnumber_abcd1234" requires numeric counter, so it's invalid
        ]
        
        for id_str in edge_case_valid:
            assert is_valid_id_format(id_str), f"Should be valid edge case: {id_str}"
        
        # Test that run IDs specifically require known patterns even if structure is right
        run_pattern_invalid = [
            "run_thread_nonnumber_abcd1234",  # Non-numeric counter makes it invalid
        ]
        
        for id_str in run_pattern_invalid:
            assert not is_valid_id_format(id_str), f"Should be invalid due to validation rules: {id_str}"
    
    # =============================================================================
    # CONVENIENCE FUNCTION TESTS
    # =============================================================================
    
    def test_convenience_functions(self):
        """Test convenience functions for ID generation."""
        # Test each convenience function
        user_id = generate_user_id()
        session_id = generate_session_id()
        request_id = generate_request_id()
        agent_id = generate_agent_id()
        websocket_id = generate_websocket_id()
        execution_id = generate_execution_id()
        thread_id = generate_thread_id()
        
        # Validate formats
        assert user_id.startswith("user_")
        assert session_id.startswith("session_")
        assert request_id.startswith("request_")
        assert agent_id.startswith("agent_")
        assert websocket_id.startswith("websocket_")
        assert execution_id.startswith("execution_")
        assert thread_id.startswith("thread_")
        
        # Test convenience validation function
        assert is_valid_id(user_id)
        assert is_valid_id(user_id, IDType.USER)
        assert not is_valid_id(user_id, IDType.SESSION)
    
    def test_global_id_manager_singleton(self):
        """Test global ID manager singleton behavior."""
        manager1 = get_id_manager()
        manager2 = get_id_manager()
        
        # Should be same instance
        assert manager1 is manager2
        
        # Generate ID with one, retrieve with other
        test_id = manager1.generate_id(IDType.USER)
        assert manager2.is_valid_id(test_id)
    
    # =============================================================================
    # THREAD SAFETY TESTS - Critical for multi-user system
    # =============================================================================
    
    def test_concurrent_id_generation(self):
        """Test thread safety of concurrent ID generation."""
        num_threads = 10
        ids_per_thread = 50
        all_ids = []
        thread_results = []
        
        def generate_ids_worker():
            """Worker function for concurrent ID generation."""
            local_ids = []
            for _ in range(ids_per_thread):
                id_val = self.manager.generate_id(IDType.REQUEST)
                local_ids.append(id_val)
                time.sleep(0.001)  # Small delay to increase concurrency stress
            return local_ids
        
        # Launch concurrent threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(generate_ids_worker) for _ in range(num_threads)]
            
            for future in concurrent.futures.as_completed(futures):
                thread_ids = future.result()
                thread_results.extend(thread_ids)
                all_ids.extend(thread_ids)
        
        # Validate results
        total_expected = num_threads * ids_per_thread
        assert len(all_ids) == total_expected
        
        # All IDs should be unique
        unique_ids = set(all_ids)
        assert len(unique_ids) == total_expected, f"Expected {total_expected} unique IDs, got {len(unique_ids)}"
        
        # All should be valid
        for id_val in all_ids:
            assert self.manager.is_valid_id(id_val)
            assert self.manager.is_valid_id(id_val, IDType.REQUEST)
    
    def test_concurrent_run_id_generation(self):
        """Test thread safety of classmethod run ID generation."""
        num_threads = 20
        ids_per_thread = 25
        all_run_ids = []
        
        def generate_run_ids_worker(thread_name):
            """Worker for concurrent run ID generation."""
            local_run_ids = []
            for i in range(ids_per_thread):
                thread_id = f"{thread_name}_session_{i}"
                run_id = UnifiedIDManager.generate_run_id(thread_id)
                local_run_ids.append(run_id)
            return local_run_ids
        
        # Launch concurrent threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(generate_run_ids_worker, f"thread_{i}")
                for i in range(num_threads)
            ]
            
            for future in concurrent.futures.as_completed(futures):
                thread_run_ids = future.result()
                all_run_ids.extend(thread_run_ids)
        
        # Validate uniqueness
        total_expected = num_threads * ids_per_thread
        assert len(all_run_ids) == total_expected
        
        unique_run_ids = set(all_run_ids)
        assert len(unique_run_ids) == total_expected
        
        # Validate all are proper format
        for run_id in all_run_ids:
            assert UnifiedIDManager.validate_run_id(run_id)
            # Should be able to extract thread_id
            extracted = UnifiedIDManager.extract_thread_id(run_id)
            assert extracted  # Should not be empty
    
    def test_concurrent_registration_and_release(self):
        """Test thread safety of ID registration and release operations."""
        num_operations = 100
        results = []
        
        def register_and_release_worker(worker_id):
            """Worker for concurrent register/release operations."""
            successes = 0
            for i in range(10):
                # Register
                test_id = f"worker_{worker_id}_id_{i}"
                if self.manager.register_existing_id(test_id, IDType.TOOL):
                    successes += 1
                    
                    # Validate
                    if self.manager.is_valid_id(test_id):
                        # Release
                        if self.manager.release_id(test_id):
                            pass  # Success
                        
            return successes
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(register_and_release_worker, i)
                for i in range(10)
            ]
            
            for future in concurrent.futures.as_completed(futures):
                successes = future.result()
                results.append(successes)
        
        # All workers should have succeeded in registering their unique IDs
        assert all(success == 10 for success in results)
    
    # =============================================================================
    # INTEGRATION TESTS - UserExecutionContext validation patterns
    # =============================================================================
    
    def test_integration_with_strongly_typed_ids(self):
        """Test integration with strongly typed ID system."""
        # Generate IDs that will be used in strongly typed contexts
        thread_id_str = UnifiedIDManager.generate_thread_id()
        run_id_str = UnifiedIDManager.generate_run_id(thread_id_str)
        request_id_str = generate_request_id()
        
        # Convert to strongly typed
        thread_id_typed = ensure_thread_id(thread_id_str)
        run_id_typed = ensure_run_id(run_id_str)
        request_id_typed = ensure_request_id(request_id_str)
        
        # Validate they work with validation functions
        assert is_valid_id_format(str(thread_id_typed))
        assert is_valid_id_format(str(run_id_typed))
        assert is_valid_id_format(str(request_id_typed))
        
        # Validate run/thread relationship
        extracted = UnifiedIDManager.extract_thread_id(str(run_id_typed))
        assert extracted == str(thread_id_typed)
    
    def test_userexecutioncontext_validation_patterns(self):
        """Test validation patterns used by UserExecutionContext."""
        # Test patterns that UserExecutionContext.validate_field uses
        test_cases = [
            # Standard UUID format (common in legacy)
            str(uuid.uuid4()),
            
            # UnifiedIDManager generated IDs
            generate_request_id(),
            generate_user_id(),
            
            # Run IDs
            UnifiedIDManager.generate_run_id("test_thread"),
            
            # WebSocket IDs
            generate_websocket_id(),
            
            # Complex structured IDs
            "req_websocket_factory_1_abcd1234",
            "thread_user_session_web_123_2_ef567890"
        ]
        
        for test_id in test_cases:
            # This is the exact validation pattern used in UserExecutionContext
            assert is_valid_id_format(test_id), f"UserExecutionContext pattern failed for: {test_id}"
    
    # =============================================================================
    # PERFORMANCE AND BULK OPERATION TESTS
    # =============================================================================
    
    def test_bulk_id_generation_performance(self):
        """Test performance of bulk ID generation."""
        start_time = time.time()
        
        # Generate large number of IDs
        num_ids = 1000
        generated_ids = []
        
        for _ in range(num_ids):
            id_val = self.manager.generate_id(IDType.REQUEST)
            generated_ids.append(id_val)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (adjust threshold as needed)
        assert duration < 1.0, f"Bulk generation took too long: {duration}s"
        
        # All should be unique and valid
        assert len(set(generated_ids)) == num_ids
        for id_val in generated_ids:
            assert self.manager.is_valid_id(id_val)
    
    def test_bulk_classmethod_performance(self):
        """Test performance of bulk classmethod operations."""
        start_time = time.time()
        
        num_runs = 1000
        thread_ids = []
        run_ids = []
        
        for i in range(num_runs):
            thread_id = f"performance_test_thread_{i}"
            run_id = UnifiedIDManager.generate_run_id(thread_id)
            
            thread_ids.append(thread_id)
            run_ids.append(run_id)
        
        # Validate all extractions
        for i, run_id in enumerate(run_ids):
            extracted = UnifiedIDManager.extract_thread_id(run_id)
            assert extracted == thread_ids[i]
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time
        assert duration < 2.0, f"Bulk classmethod operations took too long: {duration}s"
    
    # =============================================================================
    # EDGE CASES AND ERROR SCENARIOS
    # =============================================================================
    
    def test_edge_case_empty_and_none_inputs(self):
        """Test handling of empty and None inputs."""
        # Empty string inputs
        assert not UnifiedIDManager.validate_run_id("")
        assert not is_valid_id_format("")
        assert UnifiedIDManager.extract_thread_id("") == ""
        
        # None inputs  
        assert not UnifiedIDManager.validate_run_id(None)
        assert not is_valid_id_format(None)
        
        # Whitespace-only
        assert not is_valid_id_format("   ")
        assert not is_valid_id_format("\t\n")
    
    def test_edge_case_malformed_inputs(self):
        """Test handling of malformed inputs."""
        malformed_inputs = [
            "run_",  # Incomplete
            "run_thread",  # Missing parts
            "run_thread_",  # Trailing underscore
            "_run_thread_123_abcd1234",  # Leading underscore
            "run__thread_123_abcd1234",  # Double underscore
            "run_thread_123_",  # Missing UUID
            "run_thread__123_abcd1234",  # Empty thread part
        ]
        
        for malformed in malformed_inputs:
            # Should handle gracefully without crashing
            try:
                result = UnifiedIDManager.extract_thread_id(malformed)
                # Result may be the input itself or empty, but should not crash
                assert isinstance(result, str)
            except Exception as e:
                pytest.fail(f"Should handle malformed input gracefully: {malformed}, error: {e}")
    
    def test_edge_case_extreme_lengths(self):
        """Test handling of extremely long inputs."""
        # Very long thread ID
        very_long_thread = "x" * 1000  # 1000 characters
        run_id = UnifiedIDManager.generate_run_id(very_long_thread)
        extracted = UnifiedIDManager.extract_thread_id(run_id)
        assert extracted == very_long_thread
        
        # Very long existing ID
        very_long_id = "y" * 500
        success = self.manager.register_existing_id(very_long_id, IDType.USER)
        assert success is True
        assert self.manager.is_valid_id(very_long_id)
    
    def test_edge_case_unicode_and_special_characters(self):
        """Test handling of Unicode and special characters."""
        special_thread_ids = [
            "thread_with_unicode_测试",
            "thread-with-hyphens",
            "thread.with.dots",
            "thread with spaces",  # Note: may not be ideal but should handle gracefully
            "thread_with_numbers_123_and_symbols_@#",
        ]
        
        for special_thread in special_thread_ids:
            try:
                run_id = UnifiedIDManager.generate_run_id(special_thread)
                extracted = UnifiedIDManager.extract_thread_id(run_id)
                # Should extract the same thread ID back
                assert extracted == special_thread
            except Exception as e:
                # If it fails, it should fail gracefully
                assert isinstance(e, (ValueError, TypeError))
    
    # =============================================================================
    # REGRESSION TESTS - Based on known issues
    # =============================================================================
    
    def test_regression_double_prefix_prevention(self):
        """Test prevention of double-prefixing as seen in demo."""
        prefixed_thread_id = "thread_already_prefixed_user"
        run_id = UnifiedIDManager.generate_run_id(prefixed_thread_id)
        
        # Should not create double prefixes like thread_thread_
        assert not run_id.startswith("thread_thread_")
        
        # Should properly extract the original thread ID
        extracted = UnifiedIDManager.extract_thread_id(run_id)
        assert extracted == prefixed_thread_id
    
    def test_regression_websocket_routing_fix(self):
        """Test that WebSocket routing scenarios work correctly."""
        # Simulate WebSocket routing scenarios that were failing
        websocket_scenarios = [
            "websocket_factory_session_123",
            "websocket_manager_pool_user_456",
            "agent_websocket_bridge_789",
        ]
        
        for thread_id in websocket_scenarios:
            # Generate run ID (as would happen in WebSocket routing)
            run_id = UnifiedIDManager.generate_run_id(thread_id)
            
            # Extract thread ID (critical for routing)
            extracted = UnifiedIDManager.extract_thread_id(run_id)
            
            # Should be able to route back to original thread
            assert extracted == thread_id
            
            # Should validate properly
            assert UnifiedIDManager.validate_run_id(run_id)
    
    def test_regression_startup_validator_requirements(self):
        """Test all methods required by startup validator work correctly."""
        # These are the class methods that startup validator depends on
        thread_id = "startup_validation_thread"
        
        # generate_run_id must work
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        assert run_id is not None
        assert isinstance(run_id, str)
        
        # extract_thread_id must work  
        extracted = UnifiedIDManager.extract_thread_id(run_id)
        assert extracted == thread_id
        
        # validate_run_id must work
        assert UnifiedIDManager.validate_run_id(run_id) is True
        
        # parse_run_id must work
        parsed = UnifiedIDManager.parse_run_id(run_id)
        assert parsed['valid'] is True
        assert parsed['thread_id'] == thread_id