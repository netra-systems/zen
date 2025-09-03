"""
Comprehensive tests for UnifiedIDManager - SSOT for all ID generation.

These tests ensure backward compatibility with ALL legacy formats while
validating the new canonical format works correctly.

Critical test coverage:
1. Canonical format generation and parsing
2. Legacy IDManager format parsing 
3. Thread ID extraction across all formats
4. Double prefix prevention
5. WebSocket routing compatibility
6. Migration utilities
7. Error handling and edge cases
"""

import pytest
import re
import time
from unittest.mock import patch

from netra_backend.app.core.unified_id_manager import (
    UnifiedIDManager, 
    ParsedRunID, 
    IDFormat,
    generate_run_id,  # Deprecated function
    extract_thread_id_from_run_id  # Deprecated function  
)


class TestUnifiedIDManagerCanonicalFormat:
    """Test canonical format generation and parsing."""
    
    def test_generate_run_id_canonical_format(self):
        """Test canonical run_id generation format."""
        thread_id = "user_session_123"
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        # Verify canonical format: thread_{thread_id}_run_{timestamp}_{8_hex_uuid}
        pattern = r'^thread_user_session_123_run_\d+_[a-f0-9]{8}$'
        assert re.match(pattern, run_id), f"Generated run_id doesn't match canonical format: {run_id}"
        
        # Verify thread_id extraction works
        extracted_thread_id = UnifiedIDManager.extract_thread_id(run_id)
        assert extracted_thread_id == thread_id
    
    def test_generate_run_id_uniqueness(self):
        """Test that generated run_ids are unique."""
        thread_id = "test_user"
        run_ids = [UnifiedIDManager.generate_run_id(thread_id) for _ in range(10)]
        
        # All should be unique
        assert len(set(run_ids)) == len(run_ids), "Generated run_ids are not unique"
        
        # All should have same thread_id
        for run_id in run_ids:
            assert UnifiedIDManager.extract_thread_id(run_id) == thread_id
    
    def test_generate_run_id_timestamp_ordering(self):
        """Test that run_ids have chronological timestamps."""
        thread_id = "test_user"
        
        # Generate with small delay
        run_id1 = UnifiedIDManager.generate_run_id(thread_id)
        time.sleep(0.001)  # 1ms delay
        run_id2 = UnifiedIDManager.generate_run_id(thread_id)
        
        # Parse timestamps
        parsed1 = UnifiedIDManager.parse_run_id(run_id1)
        parsed2 = UnifiedIDManager.parse_run_id(run_id2)
        
        assert parsed1.timestamp <= parsed2.timestamp, "Timestamps not in chronological order"
    
    def test_parse_canonical_format(self):
        """Test parsing canonical format run_ids."""
        canonical_run_id = "thread_user123_run_1693430400000_a1b2c3d4"
        parsed = UnifiedIDManager.parse_run_id(canonical_run_id)
        
        assert parsed is not None
        assert parsed.thread_id == "user123"
        assert parsed.timestamp == 1693430400000
        assert parsed.uuid_suffix == "a1b2c3d4"
        assert parsed.format_version == IDFormat.CANONICAL
        assert parsed.original_run_id == canonical_run_id
        assert not parsed.is_legacy()


class TestUnifiedIDManagerLegacySupport:
    """Test backward compatibility with legacy formats."""
    
    def test_parse_legacy_idmanager_format(self):
        """Test parsing legacy IDManager format: run_{thread_id}_{uuid}."""
        legacy_run_id = "run_user123_a1b2c3d4"
        parsed = UnifiedIDManager.parse_run_id(legacy_run_id)
        
        assert parsed is not None
        assert parsed.thread_id == "user123"
        assert parsed.timestamp is None  # Legacy doesn't have timestamp
        assert parsed.uuid_suffix == "a1b2c3d4"
        assert parsed.format_version == IDFormat.LEGACY_IDMANAGER
        assert parsed.original_run_id == legacy_run_id
        assert parsed.is_legacy()
    
    def test_extract_thread_id_legacy_formats(self):
        """Test thread_id extraction from all legacy formats."""
        test_cases = [
            # Legacy IDManager format
            ("run_simple_user_a1b2c3d4", "simple_user"),
            ("run_user_with_underscores_e5f6a7b8", "user_with_underscores"),
            ("run_complex_user_session_123_b2c3d4e5", "complex_user_session_123"),
        ]
        
        for run_id, expected_thread_id in test_cases:
            extracted = UnifiedIDManager.extract_thread_id(run_id)
            assert extracted == expected_thread_id, f"Failed to extract '{expected_thread_id}' from '{run_id}'"
    
    def test_validate_legacy_formats(self):
        """Test validation of legacy format run_ids."""
        valid_legacy_ids = [
            "run_user123_a1b2c3d4",
            "run_session_with_underscores_e5f6a7b8", 
            "run_complex_user_session_123_b2c3d4e5"
        ]
        
        for run_id in valid_legacy_ids:
            assert UnifiedIDManager.validate_run_id(run_id), f"Legacy format should be valid: {run_id}"


class TestUnifiedIDManagerThreadIDHandling:
    """Test thread ID normalization and validation."""
    
    def test_normalize_thread_id_removes_single_prefix(self):
        """Test removing single thread_ prefix."""
        test_cases = [
            ("thread_user123", "user123"),
            ("user123", "user123"),  # No prefix
            ("thread_", ""),  # Edge case
        ]
        
        for input_id, expected in test_cases:
            result = UnifiedIDManager.normalize_thread_id(input_id)
            assert result == expected, f"normalize_thread_id('{input_id}') should be '{expected}', got '{result}'"
    
    def test_normalize_thread_id_removes_multiple_prefixes(self):
        """Test removing multiple thread_ prefixes (double prefix bug fix)."""
        test_cases = [
            ("thread_thread_user123", "user123"),
            ("thread_thread_thread_user123", "user123"),
            ("thread_thread_session_abc", "session_abc"),
        ]
        
        for input_id, expected in test_cases:
            result = UnifiedIDManager.normalize_thread_id(input_id)
            assert result == expected, f"Should remove all prefixes: '{input_id}' -> '{expected}', got '{result}'"
    
    def test_generate_run_id_prevents_double_prefix(self):
        """Test that generate_run_id prevents double prefixing."""
        # Test with already prefixed thread_id
        thread_id_with_prefix = "thread_user123"
        run_id = UnifiedIDManager.generate_run_id(thread_id_with_prefix)
        
        # Should NOT have double prefix
        assert not run_id.startswith("thread_thread_"), f"Double prefix detected: {run_id}"
        
        # Should still extract correct thread_id
        extracted = UnifiedIDManager.extract_thread_id(run_id)
        assert extracted == "user123", f"Should extract 'user123', got '{extracted}'"
    
    def test_validate_thread_id_formats(self):
        """Test thread_id format validation."""
        valid_thread_ids = [
            "user123",
            "session_abc_123",
            "user-session-123",
            "a",  # Single character
            "user_123_session_abc"
        ]
        
        invalid_thread_ids = [
            "",  # Empty
            "_user123",  # Starts with underscore
            "user123_run_",  # Contains forbidden sequence
            "user_run_123",  # Contains forbidden sequence
            123,  # Wrong type
            None  # None type
        ]
        
        for thread_id in valid_thread_ids:
            assert UnifiedIDManager.validate_thread_id(thread_id), f"Should be valid: '{thread_id}'"
        
        for thread_id in invalid_thread_ids:
            assert not UnifiedIDManager.validate_thread_id(thread_id), f"Should be invalid: '{thread_id}'"


class TestUnifiedIDManagerValidation:
    """Test validation and consistency checking."""
    
    def test_validate_id_pair_canonical(self):
        """Test ID pair validation with canonical format."""
        thread_id = "user123"
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        # Should validate successfully
        assert UnifiedIDManager.validate_id_pair(run_id, thread_id)
        assert UnifiedIDManager.validate_id_pair(run_id, "thread_user123")  # With prefix
        
        # Should fail with wrong thread_id
        assert not UnifiedIDManager.validate_id_pair(run_id, "wrong_user")
    
    def test_validate_id_pair_legacy(self):
        """Test ID pair validation with legacy format."""
        legacy_run_id = "run_user123_a1b2c3d4"
        
        assert UnifiedIDManager.validate_id_pair(legacy_run_id, "user123")
        assert UnifiedIDManager.validate_id_pair(legacy_run_id, "thread_user123")  # With prefix
        assert not UnifiedIDManager.validate_id_pair(legacy_run_id, "wrong_user")
    
    def test_validate_run_id_invalid_formats(self):
        """Test validation of invalid run_id formats."""
        invalid_run_ids = [
            "",
            "invalid_format", 
            "thread_only_prefix",
            "run_incomplete",
            "thread__run_1693430400000_a1b2c3d4",  # Double underscore
            "thread_user_run_",  # Missing timestamp and uuid
            "thread_user_run_timestamp",  # Missing uuid
            None
        ]
        
        for run_id in invalid_run_ids:
            assert not UnifiedIDManager.validate_run_id(run_id), f"Should be invalid: '{run_id}'"


class TestUnifiedIDManagerUtilities:
    """Test utility methods and migration functions."""
    
    def test_get_format_info_canonical(self):
        """Test format info for canonical format."""
        run_id = "thread_user123_run_1693430400000_a1b2c3d4"
        info = UnifiedIDManager.get_format_info(run_id)
        
        expected_info = {
            'format_version': 'canonical',
            'thread_id': 'user123',
            'has_timestamp': True,
            'timestamp': 1693430400000,
            'uuid_suffix': 'a1b2c3d4',
            'is_legacy': False,
            'original_run_id': run_id
        }
        
        assert info == expected_info
    
    def test_get_format_info_legacy(self):
        """Test format info for legacy format."""
        run_id = "run_user123_a1b2c3d4"
        info = UnifiedIDManager.get_format_info(run_id)
        
        expected_info = {
            'format_version': 'legacy_idmanager',
            'thread_id': 'user123',
            'has_timestamp': False,
            'timestamp': None,
            'uuid_suffix': 'a1b2c3d4',
            'is_legacy': True,
            'original_run_id': run_id
        }
        
        assert info == expected_info
    
    def test_migrate_to_canonical(self):
        """Test migration from legacy to canonical format."""
        legacy_run_id = "run_user123_a1b2c3d4"
        
        # Migrate to canonical
        canonical_run_id = UnifiedIDManager.migrate_to_canonical(legacy_run_id)
        assert canonical_run_id is not None
        
        # Should be canonical format
        assert canonical_run_id.startswith("thread_user123_run_")
        
        # Should extract same thread_id
        original_thread_id = UnifiedIDManager.extract_thread_id(legacy_run_id)
        migrated_thread_id = UnifiedIDManager.extract_thread_id(canonical_run_id)
        assert original_thread_id == migrated_thread_id
    
    def test_migrate_to_canonical_already_canonical(self):
        """Test migration of already canonical format."""
        canonical_run_id = "thread_user123_run_1693430400000_a1b2c3d4"
        
        # Should return same ID (no migration needed)
        result = UnifiedIDManager.migrate_to_canonical(canonical_run_id)
        assert result == canonical_run_id
    
    def test_create_test_ids(self):
        """Test creation of test ID pairs."""
        thread_id, run_id = UnifiedIDManager.create_test_ids("test_user")
        
        # Should be valid pair
        assert UnifiedIDManager.validate_id_pair(run_id, thread_id)
        
        # Thread ID should be normalized
        assert thread_id == "test_user"
        
        # Run ID should be canonical format
        assert run_id.startswith("thread_test_user_run_")


class TestUnifiedIDManagerFallbackExtraction:
    """Test fallback thread_id extraction logic."""
    
    def test_extract_thread_id_with_fallback_priority(self):
        """Test priority order for thread_id extraction."""
        canonical_run_id = "thread_from_run_id_run_1693430400000_a1b2c3d4"
        
        # Priority 1: run_id extraction (should win)
        result = UnifiedIDManager.extract_thread_id_with_fallback(
            run_id=canonical_run_id,
            thread_id="fallback_thread",
            chat_thread_id="legacy_chat_thread"
        )
        assert result == "from_run_id"
        
        # Priority 2: thread_id fallback
        result = UnifiedIDManager.extract_thread_id_with_fallback(
            run_id=None,
            thread_id="direct_thread",
            chat_thread_id="legacy_chat_thread"
        )
        assert result == "direct_thread"
        
        # Priority 3: chat_thread_id fallback
        result = UnifiedIDManager.extract_thread_id_with_fallback(
            run_id=None,
            thread_id=None,
            chat_thread_id="legacy_chat_thread"
        )
        assert result == "legacy_chat_thread"
        
        # No sources available
        result = UnifiedIDManager.extract_thread_id_with_fallback()
        assert result is None


class TestUnifiedIDManagerErrorHandling:
    """Test error handling and edge cases."""
    
    def test_generate_run_id_empty_thread_id(self):
        """Test error handling for empty thread_id."""
        with pytest.raises(ValueError, match="thread_id cannot be empty"):
            UnifiedIDManager.generate_run_id("")
        
        with pytest.raises(ValueError, match="thread_id cannot be empty"):
            UnifiedIDManager.generate_run_id(None)
    
    def test_generate_run_id_invalid_thread_id_type(self):
        """Test error handling for wrong thread_id type."""
        with pytest.raises(ValueError, match="thread_id must be string"):
            UnifiedIDManager.generate_run_id(123)
        
        with pytest.raises(ValueError, match="thread_id must be string"):
            UnifiedIDManager.generate_run_id(['list'])
    
    def test_generate_run_id_forbidden_sequences(self):
        """Test error handling for forbidden sequences in thread_id."""
        with pytest.raises(ValueError, match="cannot contain reserved sequence"):
            UnifiedIDManager.generate_run_id("user_run_123")  # Contains _run_
    
    def test_generate_run_id_empty_after_prefix_removal(self):
        """Test error handling when thread_id becomes empty after normalization."""
        with pytest.raises(ValueError, match="cannot be empty after removing prefix"):
            UnifiedIDManager.generate_run_id("thread_")
    
    def test_parse_run_id_invalid_inputs(self):
        """Test parsing with invalid inputs."""
        invalid_inputs = [None, "", 123, [], {}]
        
        for invalid_input in invalid_inputs:
            result = UnifiedIDManager.parse_run_id(invalid_input)
            assert result is None, f"Should return None for invalid input: {invalid_input}"
    
    def test_extract_thread_id_malformed_run_ids(self):
        """Test thread_id extraction from malformed run_ids."""
        malformed_run_ids = [
            "thread_",  # Missing separator and content
            "thread__run_123_abc",  # Double underscore
            "thread_user_run_",  # Missing timestamp
            "thread_user_run_abc",  # Invalid timestamp
            "run_",  # Legacy but incomplete
            "random_string"  # Unknown format
        ]
        
        for run_id in malformed_run_ids:
            result = UnifiedIDManager.extract_thread_id(run_id)
            assert result is None, f"Should return None for malformed run_id: {run_id}"


class TestUnifiedIDManagerBackwardCompatibility:
    """Test deprecated functions for backward compatibility."""
    
    def test_deprecated_generate_run_id_function(self):
        """Test deprecated generate_run_id function."""
        with patch('netra_backend.app.core.unified_id_manager.logger') as mock_logger:
            run_id = generate_run_id("test_user", "some_context")
            
            # Should work same as new method
            assert run_id.startswith("thread_test_user_run_")
            
            # Should log deprecation warning
            mock_logger.warning.assert_called_once()
            assert "deprecated" in mock_logger.warning.call_args[0][0]
    
    def test_deprecated_extract_function(self):
        """Test deprecated extract_thread_id_from_run_id function."""
        run_id = "thread_test_user_run_1693430400000_a1b2c3d4"
        
        with patch('netra_backend.app.core.unified_id_manager.logger') as mock_logger:
            thread_id = extract_thread_id_from_run_id(run_id)
            
            # Should work same as new method
            assert thread_id == "test_user"
            
            # Should log deprecation warning
            mock_logger.warning.assert_called_once()
            assert "deprecated" in mock_logger.warning.call_args[0][0]


class TestUnifiedIDManagerWebSocketCompatibility:
    """Test WebSocket routing compatibility across all formats."""
    
    def test_websocket_routing_canonical_format(self):
        """Test WebSocket routing with canonical format."""
        thread_id = "user_session_123"
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        # WebSocket bridge should be able to extract thread_id
        extracted = UnifiedIDManager.extract_thread_id(run_id)
        assert extracted == thread_id
        
        # Should validate as consistent pair
        assert UnifiedIDManager.validate_id_pair(run_id, thread_id)
    
    def test_websocket_routing_legacy_formats(self):
        """Test WebSocket routing with legacy formats."""
        legacy_formats = [
            ("run_user123_a1b2c3d4", "user123"),
            ("run_complex_user_session_abc_b2c3d4e5", "complex_user_session_abc")
        ]
        
        for run_id, expected_thread_id in legacy_formats:
            # Should extract thread_id for routing
            extracted = UnifiedIDManager.extract_thread_id(run_id)
            assert extracted == expected_thread_id
            
            # Should validate consistency
            assert UnifiedIDManager.validate_id_pair(run_id, expected_thread_id)
    
    def test_websocket_routing_mixed_formats_consistency(self):
        """Test that both formats extract same thread_id for same user."""
        thread_id = "user123"
        
        # Generate canonical format
        canonical_run_id = UnifiedIDManager.generate_run_id(thread_id)
        canonical_extracted = UnifiedIDManager.extract_thread_id(canonical_run_id)
        
        # Simulate legacy format
        legacy_run_id = "run_user123_a1b2c3d4"
        legacy_extracted = UnifiedIDManager.extract_thread_id(legacy_run_id)
        
        # Both should extract same thread_id for WebSocket routing
        assert canonical_extracted == legacy_extracted == thread_id


# Integration test for critical WebSocket routing scenario
class TestWebSocketCriticalIntegration:
    """Critical test for WebSocket routing failure scenario."""
    
    def test_websocket_routing_failure_fix(self):
        """
        Test the exact scenario that was causing 40% WebSocket failures.
        
        This test simulates the production issue where WebSocket bridge
        couldn't extract thread_id from run_id for event routing.
        """
        # Simulate different run_id formats that occur in production
        production_scenarios = [
            # New canonical format
            ("thread_user_session_abc123_run_1693430400000_a1b2c3d4", "user_session_abc123"),
            
            # Legacy IDManager format  
            ("run_legacy_user_session_abc_b2c3d4e5", "legacy_user_session_abc"),
            
            # Complex thread_ids with multiple underscores
            ("thread_user_123_session_456_conversation_789_run_1693430400000_c3d4e5f6", "user_123_session_456_conversation_789"),
            
            # Thread IDs that were already prefixed (double prefix prevention)
            ("thread_already_prefixed_user_run_1693430400000_d4e5f6a7", "already_prefixed_user")
        ]
        
        for run_id, expected_thread_id in production_scenarios:
            # Critical: WebSocket bridge MUST be able to extract thread_id
            extracted_thread_id = UnifiedIDManager.extract_thread_id(run_id)
            assert extracted_thread_id is not None, f"Failed to extract thread_id from {run_id}"
            assert extracted_thread_id == expected_thread_id, f"Wrong thread_id extracted from {run_id}"
            
            # Critical: ID pair validation MUST work for consistency checks
            assert UnifiedIDManager.validate_id_pair(run_id, expected_thread_id), f"ID pair validation failed for {run_id}"
            
            # Critical: Format MUST be recognized as valid
            assert UnifiedIDManager.validate_run_id(run_id), f"Format validation failed for {run_id}"
        
        # Success: All production scenarios now work with unified SSOT