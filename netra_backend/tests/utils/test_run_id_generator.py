"""
Comprehensive tests for SSOT run ID generator.

Tests cover all aspects of run ID generation, validation, and thread extraction
to ensure WebSocket routing reliability and business continuity.
"""

import pytest
import time
import uuid
from unittest.mock import patch

from netra_backend.app.utils.run_id_generator import (
    generate_run_id,
    extract_thread_id_from_run_id,
    validate_run_id_format,
    is_legacy_run_id,
    migrate_legacy_run_id_to_standard,
    RUN_ID_PREFIX,
    RUN_ID_SEPARATOR,
    UNIQUE_ID_LENGTH
)


class TestGenerateRunId:
    """Test run ID generation functionality."""

    def test_generate_run_id_basic_format(self):
        """Test basic run ID generation follows expected format."""
        thread_id = "user123"
        run_id = generate_run_id(thread_id)
        
        # Should start with prefix
        assert run_id.startswith(RUN_ID_PREFIX)
        
        # Should contain separator
        assert RUN_ID_SEPARATOR in run_id
        
        # Should be able to extract thread_id
        extracted = extract_thread_id_from_run_id(run_id)
        assert extracted == thread_id

    def test_generate_run_id_with_context(self):
        """Test run ID generation with context parameter."""
        thread_id = "session_abc"
        context = "agent_execution"
        
        run_id = generate_run_id(thread_id, context)
        
        # Should still follow format regardless of context
        extracted = extract_thread_id_from_run_id(run_id)
        assert extracted == thread_id

    def test_generate_run_id_with_underscores_in_thread_id(self):
        """Test thread IDs containing underscores are handled correctly."""
        thread_id = "user_123_session_456"
        run_id = generate_run_id(thread_id)
        
        extracted = extract_thread_id_from_run_id(run_id)
        assert extracted == thread_id

    def test_generate_run_id_uniqueness(self):
        """Test that generated run IDs are unique."""
        thread_id = "user123"
        run_ids = set()
        
        # Generate multiple run IDs
        for _ in range(100):
            run_id = generate_run_id(thread_id)
            assert run_id not in run_ids, "Run IDs should be unique"
            run_ids.add(run_id)

    def test_generate_run_id_timestamp_ordering(self):
        """Test that run IDs maintain chronological ordering."""
        thread_id = "user123"
        
        # Mock time to ensure different timestamps
        with patch('time.time') as mock_time:
            mock_time.return_value = 1000.0
            run_id_1 = generate_run_id(thread_id)
            
            mock_time.return_value = 2000.0
            run_id_2 = generate_run_id(thread_id)
            
        # Extract timestamp portions (between separator and final underscore)
        parts_1 = run_id_1.split('_')
        parts_2 = run_id_2.split('_')
        
        # Find timestamp (should be numeric and before unique_id)
        timestamp_1 = int(parts_1[-2])  # Second to last part
        timestamp_2 = int(parts_2[-2])
        
        assert timestamp_1 < timestamp_2, "Later run_id should have later timestamp"

    def test_generate_run_id_empty_thread_id(self):
        """Test validation of empty thread_id."""
        with pytest.raises(ValueError, match="thread_id cannot be empty"):
            generate_run_id("")
        
        with pytest.raises(ValueError, match="thread_id cannot be empty"):
            generate_run_id(None)

    def test_generate_run_id_invalid_thread_id_type(self):
        """Test validation of thread_id type."""
        with pytest.raises(ValueError, match="thread_id must be string"):
            generate_run_id(123)
        
        with pytest.raises(ValueError, match="thread_id must be string"):
            generate_run_id(['thread', 'id'])

    def test_generate_run_id_forbidden_sequences(self):
        """Test validation of forbidden sequences in thread_id."""
        thread_id_with_separator = f"user123{RUN_ID_SEPARATOR}bad"
        
        with pytest.raises(ValueError, match="cannot contain reserved sequence"):
            generate_run_id(thread_id_with_separator)

    def test_generate_run_id_unique_id_length(self):
        """Test that unique ID portion has correct length."""
        thread_id = "user123"
        run_id = generate_run_id(thread_id)
        
        # Split and get unique ID (last part)
        parts = run_id.split('_')
        unique_id = parts[-1]
        
        assert len(unique_id) == UNIQUE_ID_LENGTH


class TestExtractThreadId:
    """Test thread ID extraction functionality."""

    def test_extract_thread_id_basic(self):
        """Test basic thread ID extraction."""
        thread_id = "user123"
        run_id = generate_run_id(thread_id)
        
        extracted = extract_thread_id_from_run_id(run_id)
        assert extracted == thread_id

    def test_extract_thread_id_with_underscores(self):
        """Test extraction with complex thread IDs containing underscores."""
        thread_id = "user_123_session_abc_456"
        run_id = generate_run_id(thread_id)
        
        extracted = extract_thread_id_from_run_id(run_id)
        assert extracted == thread_id

    def test_extract_thread_id_legacy_format(self):
        """Test extraction from legacy run_id formats returns None."""
        legacy_formats = [
            "run_abc123",
            "run_uuid_string", 
            "admin_tool_test_2025",
            "random_format"
        ]
        
        for legacy_run_id in legacy_formats:
            extracted = extract_thread_id_from_run_id(legacy_run_id)
            assert extracted is None, f"Legacy format {legacy_run_id} should return None"

    def test_extract_thread_id_invalid_formats(self):
        """Test extraction from invalid formats."""
        invalid_formats = [
            "",
            None,
            "not_a_run_id",
            "thread_only_prefix",
            "thread__run_123_abc",  # Empty thread_id
            123,  # Non-string
        ]
        
        for invalid_format in invalid_formats:
            extracted = extract_thread_id_from_run_id(invalid_format)
            assert extracted is None, f"Invalid format {invalid_format} should return None"

    def test_extract_thread_id_missing_separator(self):
        """Test extraction when separator is missing."""
        malformed_run_id = "thread_user123_no_separator"
        
        extracted = extract_thread_id_from_run_id(malformed_run_id)
        assert extracted is None

    def test_extract_thread_id_empty_thread_portion(self):
        """Test extraction when thread portion is empty."""
        malformed_run_id = f"{RUN_ID_PREFIX}{RUN_ID_SEPARATOR}123_abc"
        
        extracted = extract_thread_id_from_run_id(malformed_run_id)
        assert extracted is None


class TestValidateRunIdFormat:
    """Test run ID format validation."""

    def test_validate_run_id_format_valid(self):
        """Test validation of valid run ID formats."""
        thread_id = "user123"
        run_id = generate_run_id(thread_id)
        
        assert validate_run_id_format(run_id) is True

    def test_validate_run_id_format_with_expected_thread_id(self):
        """Test validation with expected thread ID matching."""
        thread_id = "user123"
        run_id = generate_run_id(thread_id)
        
        # Should pass when thread_id matches
        assert validate_run_id_format(run_id, thread_id) is True
        
        # Should fail when thread_id doesn't match
        assert validate_run_id_format(run_id, "different_user") is False

    def test_validate_run_id_format_invalid_formats(self):
        """Test validation of invalid formats."""
        invalid_formats = [
            "",
            None,
            "run_legacy_format",
            "not_a_run_id",
            123
        ]
        
        for invalid_format in invalid_formats:
            assert validate_run_id_format(invalid_format) is False

    def test_validate_run_id_format_legacy(self):
        """Test validation of legacy formats."""
        legacy_formats = [
            "run_abc123",
            "admin_tool_test_123"
        ]
        
        for legacy_format in legacy_formats:
            # Legacy formats should be invalid in new validation
            assert validate_run_id_format(legacy_format) is False


class TestIsLegacyRunId:
    """Test legacy run ID detection."""

    def test_is_legacy_run_id_standard_format(self):
        """Test that standard format is not detected as legacy."""
        thread_id = "user123"
        run_id = generate_run_id(thread_id)
        
        assert is_legacy_run_id(run_id) is False

    def test_is_legacy_run_id_legacy_formats(self):
        """Test detection of legacy formats."""
        legacy_formats = [
            "run_abc123",
            "run_uuid_string",
            "admin_tool_test_123",
            "random_format"
        ]
        
        for legacy_format in legacy_formats:
            assert is_legacy_run_id(legacy_format) is True

    def test_is_legacy_run_id_invalid_formats(self):
        """Test that invalid formats are considered legacy."""
        invalid_formats = [
            "",
            None,
            123,
            []
        ]
        
        for invalid_format in invalid_formats:
            assert is_legacy_run_id(invalid_format) is True


class TestMigrateLegacyRunId:
    """Test legacy run ID migration functionality."""

    def test_migrate_legacy_run_id_to_standard(self):
        """Test migration of legacy run ID to standard format."""
        legacy_run_id = "run_abc123"
        thread_id = "user123"
        context = "migration_test"
        
        new_run_id = migrate_legacy_run_id_to_standard(legacy_run_id, thread_id, context)
        
        # New run ID should follow standard format
        assert validate_run_id_format(new_run_id, thread_id) is True
        assert not is_legacy_run_id(new_run_id)
        
        # Should be able to extract thread_id
        extracted = extract_thread_id_from_run_id(new_run_id)
        assert extracted == thread_id


class TestWebSocketIntegration:
    """Test WebSocket integration scenarios."""

    def test_websocket_routing_roundtrip(self):
        """Test complete WebSocket routing scenario."""
        thread_id = "user_123_session_456"
        
        # Generate run_id as would happen in agent execution
        run_id = generate_run_id(thread_id, "agent_execution")
        
        # Extract thread_id as would happen in WebSocket bridge
        extracted_thread_id = extract_thread_id_from_run_id(run_id)
        
        # Should match original thread_id for proper routing
        assert extracted_thread_id == thread_id

    def test_multiple_agents_same_thread(self):
        """Test multiple agents in same thread have different run_ids."""
        thread_id = "user123_session"
        
        run_id_1 = generate_run_id(thread_id, "agent_1")
        run_id_2 = generate_run_id(thread_id, "agent_2")
        
        # Run IDs should be different
        assert run_id_1 != run_id_2
        
        # But both should extract to same thread_id
        assert extract_thread_id_from_run_id(run_id_1) == thread_id
        assert extract_thread_id_from_run_id(run_id_2) == thread_id

    def test_business_critical_thread_ids(self):
        """Test business-critical thread ID patterns work correctly."""
        business_thread_ids = [
            "user_premium_123",
            "admin_session_456", 
            "enterprise_client_789",
            "free_trial_user_abc",
            "support_ticket_xyz123"
        ]
        
        for thread_id in business_thread_ids:
            run_id = generate_run_id(thread_id)
            extracted = extract_thread_id_from_run_id(run_id)
            assert extracted == thread_id, f"Failed for business thread_id: {thread_id}"


class TestPerformanceAndReliability:
    """Test performance and reliability aspects."""

    def test_run_id_generation_performance(self):
        """Test run ID generation performance."""
        thread_id = "performance_test"
        
        # Generate many run IDs and measure basic performance
        start_time = time.time()
        run_ids = []
        
        for i in range(1000):
            run_id = generate_run_id(f"{thread_id}_{i}")
            run_ids.append(run_id)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete reasonably quickly (less than 1 second for 1000 IDs)
        assert duration < 1.0, f"Performance test took too long: {duration}s"
        
        # All run IDs should be unique
        assert len(set(run_ids)) == 1000, "All generated run IDs should be unique"

    def test_thread_extraction_performance(self):
        """Test thread ID extraction performance."""
        # Pre-generate run IDs
        run_ids = []
        for i in range(1000):
            thread_id = f"perf_test_{i}"
            run_id = generate_run_id(thread_id)
            run_ids.append((run_id, thread_id))
        
        # Time extraction process
        start_time = time.time()
        
        for run_id, expected_thread_id in run_ids:
            extracted = extract_thread_id_from_run_id(run_id)
            assert extracted == expected_thread_id
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete quickly (less than 0.5 seconds for 1000 extractions)
        assert duration < 0.5, f"Extraction performance test took too long: {duration}s"

    def test_concurrent_generation_uniqueness(self):
        """Test that concurrent generation maintains uniqueness."""
        import threading
        import queue
        
        thread_id = "concurrent_test"
        result_queue = queue.Queue()
        
        def generate_worker():
            for _ in range(50):
                run_id = generate_run_id(f"{thread_id}_{threading.current_thread().ident}")
                result_queue.put(run_id)
        
        # Start multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=generate_worker)
            thread.start()
            threads.append(thread)
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Collect all results
        run_ids = []
        while not result_queue.empty():
            run_ids.append(result_queue.get())
        
        # All should be unique
        assert len(set(run_ids)) == len(run_ids), "Concurrent generation should maintain uniqueness"


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_malformed_run_id_extraction(self):
        """Test extraction from malformed run IDs doesn't crash."""
        malformed_ids = [
            "thread_",
            "thread__run_",
            "_run_123",
            "thread_user_run_",
            "thread_user_run_timestamp_",
            "thread_user_run_timestamp_toolongid",
        ]
        
        for malformed_id in malformed_ids:
            # Should not raise exception, just return None
            try:
                result = extract_thread_id_from_run_id(malformed_id)
                # Result should be None or valid string, never crash
                assert result is None or isinstance(result, str)
            except Exception as e:
                pytest.fail(f"extract_thread_id_from_run_id should not crash on {malformed_id}: {e}")

    def test_unicode_thread_ids(self):
        """Test handling of unicode characters in thread IDs."""
        unicode_thread_ids = [
            "user_测试",
            "session_🔥", 
            "thread_ñoño",
        ]
        
        for thread_id in unicode_thread_ids:
            try:
                run_id = generate_run_id(thread_id)
                extracted = extract_thread_id_from_run_id(run_id)
                assert extracted == thread_id
            except Exception as e:
                # If unicode not supported, should fail gracefully
                assert isinstance(e, (ValueError, UnicodeError))

    def test_extremely_long_thread_ids(self):
        """Test handling of very long thread IDs."""
        long_thread_id = "user_" + "a" * 1000
        
        # Should either work or fail gracefully
        try:
            run_id = generate_run_id(long_thread_id)
            extracted = extract_thread_id_from_run_id(run_id)
            assert extracted == long_thread_id
        except ValueError:
            # Acceptable to reject very long thread IDs
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])