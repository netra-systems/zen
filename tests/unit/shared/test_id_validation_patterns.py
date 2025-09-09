"""
UNIT TESTS - ID Validation Pattern Bug Reproduction and Fix Validation

These tests specifically target the WebSocket user ID validation bug where the pattern
"e2e-staging_pipeline" fails to match existing validation patterns.

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Bug Fix & System Reliability
- Value Impact: Prevents WebSocket connection failures for deployment users
- Strategic Impact: Ensures consistent ID validation across all environments

ROOT CAUSE: Missing regex pattern ^e2e-[a-zA-Z]+-[a-zA-Z0-9_-]+$ in validation logic

CRITICAL BUG CONTEXT:
- Issue: WebSocket error "Invalid user_id format: e2e-staging_pipeline"
- Location: shared/types/core_types.py:336 and netra_backend/app/core/unified_id_manager.py:716-732
- GitHub Issue: https://github.com/netra-systems/netra-apex/issues/105

EXPECTED BEHAVIOR: 
- Test 1 & 2: MUST FAIL initially (proving bug exists)
- Test 3-5: MUST PASS (proving regression protection)
"""

import pytest
import re
import uuid
from typing import List, Tuple

# CRITICAL: Use absolute imports per CLAUDE.md requirements
from netra_backend.app.core.unified_id_manager import (
    UnifiedIDManager, 
    IDType,
    is_valid_id_format_compatible
)
from shared.types.core_types import ensure_user_id, UserID


class TestIDValidationPatterns:
    """Test suite for ID validation pattern bug reproduction and fix validation."""
    
    @pytest.fixture
    def failing_deployment_patterns(self) -> List[str]:
        """Return deployment user ID patterns that currently FAIL validation."""
        return [
            "e2e-staging_pipeline",        # The specific failing case from bug report
            "e2e-production_deploy",       # Similar production deployment pattern  
            "e2e-test_environment",        # Test environment pattern
            "e2e-dev_pipeline_123",        # Development with numbers
            "e2e-staging_release-v1.2.3",  # Release patterns with hyphens
        ]
    
    @pytest.fixture  
    def valid_existing_patterns(self) -> List[str]:
        """Return patterns that should continue to work (regression prevention)."""
        return [
            "test-user-123",
            "mock-user-test", 
            "concurrent_user_0",
            "user_123",
            "test-session-abc123",
            "ssot-test-user",
            str(uuid.uuid4()),              # Standard UUID
        ]
    
    @pytest.fixture
    def invalid_patterns(self) -> List[str]:
        """Return patterns that should always be rejected."""
        return [
            "",                           # Empty string
            "   ",                       # Whitespace only
            "e2e-",                      # Missing suffix
            "e2e-staging_",              # Missing final part
            "invalid-format-@#$",        # Special characters
            "toolongpattern" * 50,       # Excessively long
        ]

    def test_e2e_staging_pipeline_pattern_fails_before_fix(self):
        """
        TEST 1: CRITICAL - This test MUST FAIL before the fix is applied.
        
        This proves the bug exists. The pattern "e2e-staging_pipeline" should
        be valid but currently fails validation.
        
        EXPECTED: FAILURE (before fix)
        """
        failing_pattern = "e2e-staging_pipeline"
        
        # Test the core validation function directly  
        is_valid = is_valid_id_format_compatible(failing_pattern, IDType.USER)
        
        # This assertion will FAIL initially, proving the bug exists
        assert is_valid, (
            f"CRITICAL BUG: Pattern '{failing_pattern}' should be valid for "
            f"deployment user IDs but validation failed. This proves the "
            f"missing regex pattern ^e2e-[a-zA-Z]+-[a-zA-Z0-9_-]+$ bug exists."
        )
    
    def test_e2e_staging_pipeline_pattern_passes_after_fix(self):
        """
        TEST 2: This test MUST PASS after the fix is applied.
        
        After adding the missing regex pattern, this should validate successfully.
        
        EXPECTED: SUCCESS (after fix)
        """
        failing_pattern = "e2e-staging_pipeline"
        
        # Test through the ensure_user_id function (full path)
        try:
            user_id = ensure_user_id(failing_pattern)
            assert isinstance(user_id, UserID)
            assert str(user_id) == failing_pattern
        except ValueError as e:
            pytest.fail(
                f"CRITICAL: Pattern '{failing_pattern}' should pass validation "
                f"after fix but still fails with: {e}"
            )
    
    def test_existing_patterns_still_work(self, valid_existing_patterns):
        """
        TEST 3: REGRESSION PREVENTION - Ensure existing patterns continue to work.
        
        This validates that our fix doesn't break existing functionality.
        
        EXPECTED: SUCCESS (always)
        """
        for pattern in valid_existing_patterns:
            try:
                user_id = ensure_user_id(pattern)
                assert user_id is not None
                assert str(user_id) == pattern
            except ValueError as e:
                pytest.fail(
                    f"REGRESSION: Previously valid pattern '{pattern}' now "
                    f"fails validation: {e}"
                )
    
    def test_edge_case_deployment_patterns(self, failing_deployment_patterns):
        """
        TEST 4: Validate all deployment-style patterns work after fix.
        
        Tests various deployment user ID formats that should be supported.
        
        EXPECTED: SUCCESS (after fix)  
        """
        for pattern in failing_deployment_patterns:
            try:
                user_id = ensure_user_id(pattern)
                assert user_id is not None
                assert str(user_id) == pattern
            except ValueError as e:
                pytest.fail(
                    f"Deployment pattern '{pattern}' should be valid but "
                    f"validation failed: {e}"
                )
    
    def test_invalid_patterns_still_rejected(self, invalid_patterns):
        """
        TEST 5: Ensure invalid patterns are still properly rejected.
        
        This validates that our fix doesn't make validation too permissive.
        
        EXPECTED: SUCCESS (always) - all patterns should be rejected
        """
        for pattern in invalid_patterns:
            with pytest.raises(ValueError, match=r"Invalid user_id format"):
                ensure_user_id(pattern)
    
    def test_regex_pattern_matching_directly(self):
        """
        TEST 6: Direct regex pattern testing for the missing pattern.
        
        This tests the specific regex pattern that should be added to fix the bug.
        
        EXPECTED: Shows what the regex pattern should match
        """
        # The missing pattern that should be added to fix the bug
        # Fixed: e2e-staging_pipeline has only one hyphen, not two
        missing_pattern = r'^e2e-[a-zA-Z0-9_]+$'
        
        # Test cases that should match this pattern
        should_match = [
            "e2e-staging_pipeline",
            "e2e-production_deploy", 
            "e2e-test_environment",
            "e2e-dev_pipeline_123",
            "e2e-release_v123",
        ]
        
        # Test cases that should NOT match this pattern
        should_not_match = [
            "e2e-",                    # Missing suffix
            "staging_pipeline",        # Missing e2e prefix
            "e2e",                     # Missing hyphen and suffix
            "e2e-staging-pipeline",    # Extra hyphen (different pattern)
            "e2e-@invalid",           # Invalid characters
        ]
        
        for pattern in should_match:
            assert re.match(missing_pattern, pattern), (
                f"Pattern '{pattern}' should match regex '{missing_pattern}' "
                f"but does not. This indicates the regex needs adjustment."
            )
        
        for pattern in should_not_match:
            assert not re.match(missing_pattern, pattern), (
                f"Pattern '{pattern}' should NOT match regex '{missing_pattern}' "
                f"but does. This indicates the regex is too permissive."
            )
    
    def test_validation_performance_with_new_patterns(self):
        """
        TEST 7: Ensure validation performance remains acceptable with fix.
        
        This ensures adding new patterns doesn't significantly impact performance.
        """
        import time
        
        test_patterns = [
            "e2e-staging_pipeline",
            "test-user-123", 
            str(uuid.uuid4()),
            "concurrent_user_0",
        ]
        
        start_time = time.time()
        
        # Run validation 1000 times to measure performance impact
        for _ in range(1000):
            for pattern in test_patterns:
                try:
                    is_valid_id_format_compatible(pattern, IDType.USER)
                except Exception:
                    pass  # Performance test, ignore validation results
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete 4000 validations in under 1 second
        assert duration < 1.0, (
            f"ID validation performance degraded: 4000 validations took "
            f"{duration:.3f}s, should be under 1.0s"
        )


if __name__ == "__main__":
    # Run tests with verbose output to see detailed failure messages
    pytest.main([__file__, "-v", "--tb=short"])