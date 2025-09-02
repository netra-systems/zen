"""
Comprehensive test suite for IDManager - SSOT validation.

This test suite ensures the IDManager properly enforces SSOT patterns
for all thread_id and run_id operations.
"""
import pytest
import re
from netra_backend.app.core.id_manager import IDManager, IDPair


class TestIDManagerGeneration:
    """Test ID generation functionality."""
    
    def test_generate_run_id_valid_thread_id(self):
        """Test generating run_id from valid thread_id."""
        thread_id = "test_thread_123"
        run_id = IDManager.generate_run_id(thread_id)
        
        # Verify format
        assert run_id.startswith(f"run_{thread_id}_")
        assert IDManager.validate_run_id(run_id)
        
        # Verify uniqueness - generate multiple IDs
        run_id2 = IDManager.generate_run_id(thread_id)
        assert run_id != run_id2
    
    def test_generate_run_id_empty_thread_id(self):
        """Test that empty thread_id raises error."""
        with pytest.raises(ValueError, match="thread_id cannot be empty"):
            IDManager.generate_run_id("")
    
    def test_generate_run_id_invalid_format(self):
        """Test that invalid thread_id format raises error."""
        invalid_ids = [
            "!invalid",  # Special char at start
            " spaces ",  # Spaces
            "",  # Empty
        ]
        
        for invalid_id in invalid_ids:
            with pytest.raises(ValueError, match="Invalid thread_id format"):
                IDManager.generate_run_id(invalid_id)


class TestIDManagerExtraction:
    """Test ID extraction functionality."""
    
    def test_extract_thread_id_valid_run_id(self):
        """Test extracting thread_id from valid run_id."""
        thread_id = "test_thread_456"
        run_id = f"run_{thread_id}_12345678"
        
        extracted = IDManager.extract_thread_id(run_id)
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
            assert IDManager.extract_thread_id(invalid_id) is None
    
    def test_extract_thread_id_empty(self):
        """Test extraction returns None for empty string."""
        assert IDManager.extract_thread_id("") is None
        assert IDManager.extract_thread_id(None) is None


class TestIDManagerValidation:
    """Test ID validation functionality."""
    
    def test_validate_id_pair_matching(self):
        """Test validation of matching ID pairs."""
        thread_id = "test_thread"
        run_id = f"run_{thread_id}_abcd1234"
        
        assert IDManager.validate_id_pair(run_id, thread_id) is True
    
    def test_validate_id_pair_mismatched(self):
        """Test validation of mismatched ID pairs."""
        thread_id = "thread_one"
        run_id = "run_thread_two_12345678"
        
        assert IDManager.validate_id_pair(run_id, thread_id) is False
    
    def test_validate_id_pair_empty(self):
        """Test validation with empty IDs."""
        assert IDManager.validate_id_pair("", "thread") is False
        assert IDManager.validate_id_pair("run_thread_123", "") is False
        assert IDManager.validate_id_pair("", "") is False
    
    def test_validate_run_id_formats(self):
        """Test run_id format validation."""
        valid_ids = [
            "run_thread_12345678",
            "run_test_thread_abcdef01",
            "run_t1_00000000",
        ]
        
        for valid_id in valid_ids:
            assert IDManager.validate_run_id(valid_id) is True
        
        invalid_ids = [
            "test-run",
            "run_thread",
            "run_thread_",
            "run_thread_xyz",
            "run_thread_123456789",  # Too long suffix
        ]
        
        for invalid_id in invalid_ids:
            assert IDManager.validate_run_id(invalid_id) is False
    
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
            assert IDManager.validate_thread_id(valid_id) is True
        
        invalid_ids = [
            "",
            " spaces ",
            "!invalid",
            "@special",
        ]
        
        for invalid_id in invalid_ids:
            assert IDManager.validate_thread_id(invalid_id) is False


class TestIDPair:
    """Test IDPair dataclass functionality."""
    
    def test_create_valid_pair(self):
        """Test creating valid IDPair."""
        thread_id = "test_thread"
        run_id = f"run_{thread_id}_12345678"
        
        pair = IDPair(thread_id=thread_id, run_id=run_id)
        assert pair.thread_id == thread_id
        assert pair.run_id == run_id
    
    def test_create_invalid_pair_raises(self):
        """Test that mismatched IDs raise error."""
        thread_id = "thread_one"
        run_id = "run_thread_two_12345678"
        
        with pytest.raises(ValueError, match="Inconsistent ID pair"):
            IDPair(thread_id=thread_id, run_id=run_id)
    
    def test_pair_immutable(self):
        """Test that IDPair is immutable."""
        pair = IDManager.create_test_ids()
        
        with pytest.raises(AttributeError):
            pair.thread_id = "new_thread"
        
        with pytest.raises(AttributeError):
            pair.run_id = "new_run"


class TestIDManagerHelpers:
    """Test helper functions."""
    
    def test_parse_run_id_valid(self):
        """Test parsing valid run_id."""
        run_id = "run_test_thread_abcd1234"
        result = IDManager.parse_run_id(run_id)
        
        assert result is not None
        thread_id, suffix = result
        assert thread_id == "test_thread"
        assert suffix == "abcd1234"
    
    def test_parse_run_id_invalid(self):
        """Test parsing invalid run_id returns None."""
        assert IDManager.parse_run_id("invalid") is None
        assert IDManager.parse_run_id("") is None
    
    def test_create_test_ids(self):
        """Test creating test IDs."""
        # Default test IDs
        pair = IDManager.create_test_ids()
        assert pair.thread_id == "test_thread"
        assert pair.run_id.startswith("run_test_thread_")
        
        # Custom thread_id
        custom_pair = IDManager.create_test_ids("custom_thread")
        assert custom_pair.thread_id == "custom_thread"
        assert custom_pair.run_id.startswith("run_custom_thread_")
    
    def test_get_or_generate_run_id_with_existing(self):
        """Test getting existing run_id."""
        existing_run_id = "run_thread_12345678"
        result = IDManager.get_or_generate_run_id(run_id=existing_run_id)
        assert result == existing_run_id
    
    def test_get_or_generate_run_id_generate_new(self):
        """Test generating new run_id from thread_id."""
        thread_id = "new_thread"
        result = IDManager.get_or_generate_run_id(thread_id=thread_id)
        assert result.startswith(f"run_{thread_id}_")
        assert IDManager.validate_run_id(result)
    
    def test_get_or_generate_run_id_invalid_existing(self):
        """Test that invalid existing run_id raises error."""
        with pytest.raises(ValueError, match="Invalid run_id format"):
            IDManager.get_or_generate_run_id(run_id="invalid-run-id")
    
    def test_get_or_generate_run_id_no_inputs(self):
        """Test that no inputs raises error."""
        with pytest.raises(ValueError, match="Either run_id or thread_id must be provided"):
            IDManager.get_or_generate_run_id()
    
    def test_extract_thread_id_with_fallback_priority(self):
        """Test fallback priority for thread_id extraction."""
        # Priority 1: Extract from run_id
        result = IDManager.extract_thread_id_with_fallback(
            run_id="run_from_run_12345678",
            thread_id="direct_thread",
            chat_thread_id="chat_thread"
        )
        assert result == "from_run"
        
        # Priority 2: Use thread_id
        result = IDManager.extract_thread_id_with_fallback(
            run_id="invalid",
            thread_id="direct_thread",
            chat_thread_id="chat_thread"
        )
        assert result == "direct_thread"
        
        # Priority 3: Use chat_thread_id
        result = IDManager.extract_thread_id_with_fallback(
            run_id="invalid",
            thread_id=None,
            chat_thread_id="chat_thread"
        )
        assert result == "chat_thread"
        
        # No valid input
        result = IDManager.extract_thread_id_with_fallback()
        assert result is None


class TestIDManagerRegressionTests:
    """Test for specific regression scenarios from audit."""
    
    def test_legacy_test_run_format(self):
        """Test that legacy 'test-run' format is invalid."""
        # This was a common violation in tests
        assert IDManager.validate_run_id("test-run") is False
        assert IDManager.extract_thread_id("test-run") is None
    
    def test_hyphenated_vs_underscored(self):
        """Test consistency in separator usage."""
        # Underscored format is valid
        assert IDManager.validate_run_id("run_thread_12345678") is True
        
        # Hyphenated format is invalid for run_id
        assert IDManager.validate_run_id("run-thread-12345678") is False
    
    def test_thread_id_in_run_id_with_special_chars(self):
        """Test thread_id with hyphens in run_id."""
        thread_id = "test-thread-123"
        run_id = IDManager.generate_run_id(thread_id)
        
        # Should generate valid run_id
        assert IDManager.validate_run_id(run_id)
        
        # Should extract correctly
        extracted = IDManager.extract_thread_id(run_id)
        assert extracted == thread_id