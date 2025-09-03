"""
Comprehensive test suite for UnifiedUnifiedIDManager - SSOT validation.

This test suite ensures the UnifiedUnifiedIDManager properly enforces SSOT patterns
for all thread_id and run_id operations.
"""
import pytest
import re
from netra_backend.app.core.unified_id_manager import UnifiedUnifiedIDManager


class TestUnifiedUnifiedIDManagerGeneration:
    """Test ID generation functionality."""
    
    def test_generate_run_id_valid_thread_id(self):
        """Test generating run_id from valid thread_id."""
        thread_id = "test_thread_123"
        run_id = UnifiedUnifiedIDManager.generate_run_id(thread_id)
        
        # Verify format
        assert run_id.startswith(f"run_{thread_id}_")
        assert UnifiedUnifiedIDManager.validate_run_id(run_id)
        
        # Verify uniqueness - generate multiple IDs
        run_id2 = UnifiedUnifiedIDManager.generate_run_id(thread_id)
        assert run_id != run_id2
    
    def test_generate_run_id_empty_thread_id(self):
        """Test that empty thread_id raises error."""
        with pytest.raises(ValueError, match="thread_id cannot be empty"):
            UnifiedUnifiedIDManager.generate_run_id("")
    
    def test_generate_run_id_invalid_format(self):
        """Test that invalid thread_id format raises error."""
        invalid_ids = [
            "!invalid",  # Special char at start
            " spaces ",  # Spaces
            "",  # Empty
        ]
        
        for invalid_id in invalid_ids:
            with pytest.raises(ValueError, match="Invalid thread_id format"):
                UnifiedUnifiedIDManager.generate_run_id(invalid_id)


class TestUnifiedUnifiedIDManagerExtraction:
    """Test ID extraction functionality."""
    
    def test_extract_thread_id_valid_run_id(self):
        """Test extracting thread_id from valid run_id."""
        thread_id = "test_thread_456"
        run_id = f"run_{thread_id}_12345678"
        
        extracted = UnifiedUnifiedIDManager.extract_thread_id(run_id)
        assert extracted == thread_id
    
    def test_extract_thread_id_invalid_format(self):
        """Test extraction returns None for invalid formats."""
        invalid_run_ids = [
            "test-run",  # Missing prefix
            "run_thread",  # Missing suffix
            "run_thread_",  # Empty suffix
            "run__12345678",  # Empty thread_id
            "RUN_thread_12345678",  # Wrong case
            "run_thread_xyz",  # Invalid suffix format
        ]
        
        for invalid_id in invalid_run_ids:
            assert UnifiedUnifiedIDManager.extract_thread_id(invalid_id) is None
    
    def test_extract_thread_id_empty(self):
        """Test extraction returns None for empty string."""
        assert UnifiedUnifiedIDManager.extract_thread_id("") is None
        assert UnifiedUnifiedIDManager.extract_thread_id(None) is None


class TestUnifiedIDManagerValidation:
    """Test ID validation functionality."""
    
    def test_validate_id_pair_matching(self):
        """Test validation of matching ID pairs."""
        thread_id = "test_thread"
        run_id = f"run_{thread_id}_abcd1234"
        
        assert UnifiedIDManager.validate_id_pair(run_id, thread_id) is True
    
    def test_validate_id_pair_mismatched(self):
        """Test validation of mismatched ID pairs."""
        thread_id = "thread_one"
        run_id = "run_thread_two_12345678"
        
        assert UnifiedIDManager.validate_id_pair(run_id, thread_id) is False
    
    def test_validate_id_pair_empty(self):
        """Test validation with empty IDs."""
        assert UnifiedIDManager.validate_id_pair("", "thread") is False
        assert UnifiedIDManager.validate_id_pair("run_thread_123", "") is False
        assert UnifiedIDManager.validate_id_pair("", "") is False
    
    def test_validate_run_id_formats(self):
        """Test run_id format validation."""
        valid_ids = [
            "run_thread_12345678",
            "run_test_thread_abcdef01",
            "run_t1_00000000",
        ]
        
        for valid_id in valid_ids:
            assert UnifiedIDManager.validate_run_id(valid_id) is True
        
        invalid_ids = [
            "test-run",
            "run_thread",
            "run_thread_",
            "run_thread_xyz",
            "run_thread_123456789",  # Too long suffix
        ]
        
        for invalid_id in invalid_ids:
            assert UnifiedIDManager.validate_run_id(invalid_id) is False
    
    def test_validate_thread_id_formats(self):
        """Test thread_id format validation."""
        valid_ids = [
            "thread_123",
            "test-thread",
            "thread",
            "t1",
            "ABC_123-xyz",
        ]
        
        for valid_id in valid_ids:
            assert UnifiedIDManager.validate_thread_id(valid_id) is True
        
        invalid_ids = [
            "",
            " spaces ",
            "!invalid",
            "@special",
        ]
        
        for invalid_id in invalid_ids:
            assert UnifiedIDManager.validate_thread_id(invalid_id) is False


class TestUnifiedIDManagerParsing:
    """Test parsing functionality."""
    
    def test_create_test_ids(self):
        """Test creating test IDs."""
        # Default test IDs
        thread_id, run_id = UnifiedIDManager.create_test_ids()
        assert thread_id == "test_session"
        assert run_id.startswith("thread_test_session_run_")
        
        # Custom thread_id
        custom_thread, custom_run = UnifiedIDManager.create_test_ids("custom_thread")
        assert custom_thread == "custom_thread"
        assert custom_run.startswith("thread_custom_thread_run_")
    
    def test_parse_run_id_valid(self):
        """Test parsing valid run_id."""
        run_id = "thread_test_thread_run_1234567890_abcd1234"
        parsed = UnifiedIDManager.parse_run_id(run_id)
        
        assert parsed is not None
        assert parsed.thread_id == "test_thread"
        assert parsed.format_version.name in ["CANONICAL", "LEGACY_IDMANAGER"]
    
    def test_parse_run_id_invalid(self):
        """Test parsing invalid run_id returns None."""
        assert UnifiedIDManager.parse_run_id("invalid") is None
        assert UnifiedIDManager.parse_run_id("") is None
        assert UnifiedIDManager.parse_run_id(None) is None


class TestUnifiedIDManagerHelpers:
    """Test helper functions."""
    
    def test_extract_thread_id_with_fallback_priority(self):
        """Test fallback priority for thread_id extraction."""
        # Priority 1: Extract from run_id
        result = UnifiedIDManager.extract_thread_id_with_fallback(
            run_id="run_from_run_12345678",
            thread_id="direct_thread",
            chat_thread_id="chat_thread"
        )
        assert result == "from_run"
        
        # Priority 2: Use thread_id
        result = UnifiedIDManager.extract_thread_id_with_fallback(
            run_id="invalid",
            thread_id="direct_thread",
            chat_thread_id="chat_thread"
        )
        assert result == "direct_thread"
        
        # Priority 3: Use chat_thread_id
        result = UnifiedIDManager.extract_thread_id_with_fallback(
            run_id="invalid",
            thread_id=None,
            chat_thread_id="chat_thread"
        )
        assert result == "chat_thread"
        
        # No valid input
        result = UnifiedIDManager.extract_thread_id_with_fallback()
        assert result is None
    
    def test_normalize_thread_id(self):
        """Test thread_id normalization."""
        # Test cases
        assert UnifiedIDManager.normalize_thread_id("test_thread") == "test_thread"
        assert UnifiedIDManager.normalize_thread_id("Thread_123") == "Thread_123"
        
    def test_get_format_info(self):
        """Test format information extraction."""
        # Test canonical format
        canonical_run_id = "thread_test_run_1234567890_abcd1234"
        info = UnifiedIDManager.get_format_info(canonical_run_id)
        assert info['format'] == 'canonical'
        
        # Test legacy format
        legacy_run_id = "run_test_thread_abcd1234"
        info = UnifiedIDManager.get_format_info(legacy_run_id)
        assert info['format'] == 'legacy_idmanager'


class TestUnifiedIDManagerRegressionTests:
    """Test for specific regression scenarios from audit."""
    
    def test_legacy_test_run_format(self):
        """Test that legacy 'test-run' format is invalid."""
        # This was a common violation in tests
        assert UnifiedIDManager.validate_run_id("test-run") is False
        assert UnifiedIDManager.extract_thread_id("test-run") is None
    
    def test_hyphenated_vs_underscored(self):
        """Test consistency in separator usage."""
        # Underscored format is valid
        assert UnifiedIDManager.validate_run_id("run_thread_12345678") is True
        
        # Hyphenated format is invalid for run_id
        assert UnifiedIDManager.validate_run_id("run-thread-12345678") is False
    
    def test_thread_id_in_run_id_with_special_chars(self):
        """Test thread_id with hyphens in run_id."""
        thread_id = "test-thread-123"
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        # Should generate valid run_id
        assert UnifiedIDManager.validate_run_id(run_id)
        
        # Should extract correctly
        extracted = UnifiedIDManager.extract_thread_id(run_id)
        assert extracted == thread_id