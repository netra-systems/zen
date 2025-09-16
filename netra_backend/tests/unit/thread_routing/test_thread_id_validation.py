"""
Test Thread ID Validation Unit Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure thread routing integrity and user isolation
- Value Impact: Thread ID validation prevents routing failures and user data leakage
- Strategic Impact: Core platform stability and security foundation

Tests the thread ID validation functionality including format validation,
UUID compliance, and user ownership validation. These tests ensure that
thread IDs are properly formatted and validated throughout the system.
"""
import pytest
import uuid
from unittest.mock import Mock, patch
from typing import Dict, Any, Optional
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType, is_valid_id_format
from netra_backend.app.websocket_core.protocols import ensure_thread_id_type
from netra_backend.app.core.user_execution_context import UserExecutionContext
from netra_backend.app.services.user_execution_context import InvalidContextError
from shared.types import ThreadID, UserID, ensure_thread_id, ensure_user_id
from test_framework.ssot.base_test_case import SSotBaseTestCase

class ThreadIDValidationTests(SSotBaseTestCase):
    """Test thread ID validation with SSOT patterns."""

    def setup_method(self, method=None) -> None:
        """Set up test fixtures following SSOT patterns."""
        super().setup_method(method)
        self.id_manager = UnifiedIDManager()
        self.test_user_id = 'user_test_12345'
        self.test_thread_id = 'thread_test_67890'

    def teardown_method(self, method=None) -> None:
        """Clean up test resources."""
        self.id_manager.clear_all()
        super().teardown_method(method)

    def test_valid_uuid_format_accepted(self):
        """Test that valid UUID format is accepted."""
        valid_uuid = str(uuid.uuid4())
        result = is_valid_id_format(valid_uuid)
        assert result, 'Valid UUID should be accepted as valid thread ID format'

    def test_valid_structured_format_accepted(self):
        """Test that structured ID format is accepted."""
        structured_id = 'thread_123_abc12345'
        result = is_valid_id_format(structured_id)
        assert result, 'Structured thread ID format should be accepted'

    def test_empty_string_rejected(self):
        """Test that empty string is rejected."""
        result = is_valid_id_format('')
        assert not result, 'Empty string should be rejected as thread ID'

    def test_none_value_rejected(self):
        """Test that None value is rejected."""
        result = is_valid_id_format(None)
        assert not result, 'None should be rejected as thread ID'

    def test_whitespace_only_rejected(self):
        """Test that whitespace-only string is rejected."""
        result = is_valid_id_format('   ')
        assert not result, 'Whitespace-only string should be rejected'

    def test_malformed_structured_id_rejected(self):
        """Test that malformed structured ID is rejected."""
        malformed_id = 'thread_abc_xyz'
        result = is_valid_id_format(malformed_id)
        assert not result, 'Malformed structured ID should be rejected'

    def test_uuid_compliance_validation(self):
        """Test that UUID compliance is properly validated."""
        test_cases = [('550e8400-e29b-41d4-a716-446655440000', True), ('550e8400e29b41d4a716446655440000', True), ('550e8400-e29b-41d4-a716', False), ('not-a-uuid-at-all', False)]
        for test_id, expected in test_cases:
            try:
                uuid.UUID(test_id)
                is_uuid = True
            except ValueError:
                is_uuid = False
            assert is_uuid == expected, f'UUID compliance for {test_id} should be {expected}'

    def test_unified_id_manager_format_validation(self):
        """Test UnifiedIDManager structured format validation."""
        test_cases = [('thread_123_abcd1234', True), ('thread_456_abcd5678', True), ('thread_abc_1234abcd', False), ('thread_123', True), ('thread_123_toolong12345', False)]
        for test_id, expected in test_cases:
            result = is_valid_id_format(test_id)
            assert result == expected, f'Structured format validation for {test_id} should be {expected}'

    def test_generate_thread_id_format_compliance(self):
        """Test that generated thread IDs are format compliant."""
        generated_id = self.id_manager.generate_id(IDType.THREAD)
        is_valid = is_valid_id_format(generated_id)
        assert is_valid, 'Generated thread ID should pass format validation'
        metadata = self.id_manager.get_id_metadata(generated_id)
        assert metadata is not None, 'Generated thread ID should have metadata'
        assert metadata.id_type == IDType.THREAD, 'Generated ID should have correct type'

    def test_generate_multiple_unique_thread_ids(self):
        """Test that multiple generated thread IDs are unique."""
        generated_ids = set()
        for _ in range(100):
            thread_id = self.id_manager.generate_id(IDType.THREAD)
            assert thread_id not in generated_ids, 'Generated thread IDs must be unique'
            generated_ids.add(thread_id)

    def test_ensure_thread_id_type_string_conversion(self):
        """Test string to ThreadID type conversion."""
        test_thread_id = 'thread_test_12345'
        result = ensure_thread_id_type(test_thread_id)
        typed_result = ensure_thread_id(result)
        assert str(typed_result) == test_thread_id, 'Converted ThreadID should preserve original value'

    def test_ensure_thread_id_type_already_typed(self):
        """Test that already typed ThreadID is returned unchanged."""
        original_thread_id = ensure_thread_id('thread_test_67890')
        result = ensure_thread_id_type(original_thread_id)
        assert str(result) == str(original_thread_id), 'Already typed ThreadID should preserve value'

    def test_thread_id_user_context_validation(self):
        """Test thread ID validation within user execution context."""
        user_context = UserExecutionContext(user_id=ensure_user_id(self.test_user_id), thread_id=ensure_thread_id(self.test_thread_id), run_id='run_test_11111')
        assert str(user_context.user_id) == self.test_user_id, 'User context should preserve user ID'
        assert str(user_context.thread_id) == self.test_thread_id, 'User context should preserve thread ID'

    def test_invalid_thread_id_in_context_raises_error(self):
        """Test that invalid thread ID in context raises appropriate error."""
        with pytest.raises(InvalidContextError, match="Required field 'thread_id' must be a non-empty string"):
            UserExecutionContext(user_id=ensure_user_id(self.test_user_id), thread_id=None, run_id='run_test_22222')

    def test_sql_injection_attempt_rejected(self):
        """Test that potential SQL injection attempts are rejected."""
        malicious_inputs = ["'; DROP TABLE threads; --", "thread_id' OR '1'='1", "thread_id'; DELETE FROM users; --", "<script>alert('xss')</script>"]
        for malicious_input in malicious_inputs:
            result = is_valid_id_format(malicious_input)
            assert not result, f"Malicious input '{malicious_input}' should be rejected"

    def test_extremely_long_thread_id_rejected(self):
        """Test that extremely long thread IDs are rejected."""
        long_id = 'thread_' + 'a' * 10000
        result = is_valid_id_format(long_id)
        assert not result, 'Extremely long thread ID should be rejected'

    def test_special_characters_handling(self):
        """Test handling of special characters in thread IDs."""
        special_chars = ['thread_123_caf[U+00E9]', 'thread_123_Jos[U+00E9]', 'thread_123_[U+0444]a[U+0439][U+043B]', 'thread_123_[U+6D4B][U+8BD5]']
        for special_id in special_chars:
            result = is_valid_id_format(special_id)
            assert not result, f'Thread ID with special characters should be rejected: {special_id}'

    def test_validation_performance(self):
        """Test that validation performs within acceptable time limits."""
        import time
        test_ids = [str(uuid.uuid4()) for _ in range(1000)] + [f'thread_{i}_{uuid.uuid4().hex[:8]}' for i in range(1000)]
        start_time = time.time()
        for test_id in test_ids:
            is_valid_id_format(test_id)
        end_time = time.time()
        validation_time = end_time - start_time
        assert validation_time < 1.0, 'Thread ID validation should complete within performance limits'

    def test_run_id_thread_id_extraction(self):
        """Test thread ID extraction from run IDs."""
        test_thread_id = 'thread_session_98765'
        run_id = UnifiedIDManager.generate_run_id(test_thread_id)
        extracted_thread_id = UnifiedIDManager.extract_thread_id(run_id)
        assert extracted_thread_id == test_thread_id, 'Extracted thread ID should match original'

    def test_run_id_validation(self):
        """Test run ID format validation."""
        valid_run_id = 'run_thread_test_12345_67890_abcd1234'
        invalid_run_id = 'invalid_run_format'
        assert UnifiedIDManager.validate_run_id(valid_run_id), 'Valid run ID should pass validation'
        assert not UnifiedIDManager.validate_run_id(invalid_run_id), 'Invalid run ID should fail validation'

    def test_run_id_parsing(self):
        """Test run ID parsing into components."""
        test_thread_id = 'thread_session_12345'
        run_id = UnifiedIDManager.generate_run_id(test_thread_id)
        parsed = UnifiedIDManager.parse_run_id(run_id)
        assert parsed['valid'], 'Parsed run ID should be marked as valid'
        assert parsed['thread_id'] == test_thread_id, 'Parsed thread ID should match original'
        assert parsed['timestamp'].isdigit(), 'Parsed timestamp should be numeric'
        assert len(parsed['uuid_part']) == 8, 'Parsed UUID part should be 8 characters'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')