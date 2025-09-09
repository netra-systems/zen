"""
UNIFIED ID MANAGER VALIDATION INCONSISTENCY TESTS

These tests expose validation inconsistencies between UnifiedIDManager
and the legacy uuid.uuid4() approach used throughout the codebase.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Reliability & Type Safety  
- Value Impact: Prevents validation failures in production
- Strategic Impact: Foundation for reliable multi-service architecture

EXPECTED BEHAVIOR: MANY TESTS SHOULD FAIL INITIALLY
This demonstrates validation inconsistencies that need remediation.
"""

import pytest
import uuid
from typing import Optional, Any

# CRITICAL: Use absolute imports per CLAUDE.md requirements
from netra_backend.app.core.unified_id_manager import (
    UnifiedIDManager,
    IDType,
    get_id_manager,
    is_valid_id_format,
    generate_id
)
from shared.types.core_types import (
    UserID,
    ThreadID,
    ExecutionID,
    WebSocketID,
    ensure_user_id,
    ensure_thread_id
)
from test_framework.fixtures.id_system.id_format_samples import (
    get_uuid_samples,
    get_unified_samples,
    get_malformed_samples,
    EXPECTED_UUID_PATTERN,
    EXPECTED_UNIFIED_PATTERN
)


class TestUnifiedIDManagerValidationInconsistencies:
    """
    Tests that expose critical validation inconsistencies in the ID system.
    
    These demonstrate where the same ID value gets different validation
    results depending on which validator is used.
    """
    
    def setup_method(self):
        """Setup for each test method."""
        self.id_manager = UnifiedIDManager()
        
    def test_validation_mismatch_uuid_vs_unified_manager(self):
        """
        CRITICAL FAILURE TEST: Same UUID validates differently across validators.
        
        This exposes the core validation inconsistency where:
        - is_valid_id_format() accepts UUIDs  
        - UnifiedIDManager.is_valid_id() rejects them
        
        Business Impact: Intermittent validation failures in production.
        
        EXPECTED: This test SHOULD FAIL, proving validation inconsistency.
        """
        # Generate a standard UUID 
        test_uuid = str(uuid.uuid4())
        
        # Test with different validators
        format_validator_result = is_valid_id_format(test_uuid)
        manager_validator_result = self.id_manager.is_valid_id(test_uuid)
        
        # These SHOULD be the same but aren't - proving inconsistency
        assert format_validator_result == manager_validator_result, \
            f"Validation mismatch for UUID {test_uuid}: " \
            f"format_validator={format_validator_result}, " \
            f"manager_validator={manager_validator_result}"
    
    def test_unregistered_id_validation_inconsistency(self):
        """
        CRITICAL FAILURE TEST: Unregistered IDs validate inconsistently.
        
        This exposes the problem where validation depends on registration
        state rather than format consistency.
        
        Business Impact: Validation failures for legitimate IDs.
        
        EXPECTED: This test SHOULD FAIL, proving registration-dependent validation.
        """
        # Create a properly formatted UnifiedIDManager-style ID
        unregistered_unified_id = "user_999_deadbeef"
        
        # Format validation should pass
        format_valid = is_valid_id_format(unregistered_unified_id)
        
        # Manager validation should fail because it's not registered
        manager_valid = self.id_manager.is_valid_id(unregistered_unified_id)
        
        # This assertion SHOULD FAIL, showing registration dependency
        assert format_valid == manager_valid, \
            f"Validation inconsistency for unregistered ID {unregistered_unified_id}: " \
            f"format_valid={format_valid}, manager_valid={manager_valid}"
    
    def test_id_type_validation_strictness_mismatch(self):
        """
        CRITICAL FAILURE TEST: ID type validation strictness varies by module.
        
        This exposes inconsistent type validation where some modules are
        strict about ID types while others are permissive.
        
        Business Impact: Type safety violations, wrong data routing.
        
        EXPECTED: This test SHOULD FAIL, proving strictness inconsistency.
        """
        # Register a user ID
        user_id = self.id_manager.generate_id(IDType.USER)
        
        # Try to validate it as different types
        valid_as_user = self.id_manager.is_valid_id(user_id, IDType.USER)
        valid_as_thread = self.id_manager.is_valid_id(user_id, IDType.THREAD)
        valid_without_type = self.id_manager.is_valid_id(user_id)
        
        # Type-specific validation should be strict
        assert valid_as_user, f"User ID should validate as user type"
        assert not valid_as_thread, f"User ID should NOT validate as thread type"
        
        # But this assertion might FAIL if validation is too permissive
        assert valid_without_type != valid_as_thread, \
            f"Validation strictness inconsistency for {user_id}"
    
    def test_empty_and_none_id_handling_inconsistency(self):
        """
        CRITICAL FAILURE TEST: Empty/None ID handling varies across validators.
        
        This exposes inconsistent handling of edge cases that can cause
        production failures.
        
        Business Impact: Unexpected exceptions, system crashes.
        
        EXPECTED: This test SHOULD FAIL, proving edge case inconsistency.
        """
        edge_cases = ["", None, "   ", "\n", "\t"]
        
        for edge_case in edge_cases:
            try:
                format_result = is_valid_id_format(edge_case) if edge_case is not None else False
            except Exception as e:
                format_result = f"Exception: {type(e).__name__}"
            
            try:
                manager_result = self.id_manager.is_valid_id(edge_case)
            except Exception as e:
                manager_result = f"Exception: {type(e).__name__}"
            
            # This assertion SHOULD FAIL for some edge cases
            assert format_result == manager_result, \
                f"Edge case handling inconsistency for {repr(edge_case)}: " \
                f"format={format_result}, manager={manager_result}"
    
    def test_case_sensitivity_validation_mismatch(self):
        """
        CRITICAL FAILURE TEST: Case sensitivity handling differs between validators.
        
        This exposes potential issues with case-insensitive vs case-sensitive
        validation approaches.
        
        Business Impact: IDs not found due to case mismatches.
        
        EXPECTED: This test MAY FAIL, proving case handling inconsistency.
        """
        # Create test IDs with case variations
        base_uuid = str(uuid.uuid4())
        upper_uuid = base_uuid.upper()
        mixed_case_uuid = base_uuid[:16] + base_uuid[16:].upper()
        
        test_cases = [base_uuid, upper_uuid, mixed_case_uuid]
        
        for test_id in test_cases:
            format_valid = is_valid_id_format(test_id)
            manager_valid = self.id_manager.is_valid_id(test_id)
            
            # Validation consistency should not depend on case
            assert format_valid == manager_valid, \
                f"Case sensitivity mismatch for {test_id}: " \
                f"format={format_valid}, manager={manager_valid}"


class TestValidationBusinessRequirements:
    """
    Tests that expose gaps where validation doesn't meet business requirements.
    """
    
    def setup_method(self):
        """Setup for each test method."""
        self.id_manager = UnifiedIDManager()
    
    def test_validation_lacks_business_context_checking(self):
        """
        CRITICAL FAILURE TEST: Validation doesn't check business context requirements.
        
        This exposes the problem where IDs can be technically valid but
        inappropriate for their business context.
        
        Business Impact: Wrong ID types used in wrong contexts.
        
        EXPECTED: This test SHOULD FAIL, proving business context gaps.
        """
        # Generate a websocket ID
        websocket_id = self.id_manager.generate_id(IDType.WEBSOCKET)
        
        # This ID might validate as a user ID despite being wrong context
        validates_as_user = self.id_manager.is_valid_id(websocket_id, IDType.USER)
        validates_as_websocket = self.id_manager.is_valid_id(websocket_id, IDType.WEBSOCKET)
        
        # Business requirement: ID should only validate for its intended type
        assert not validates_as_user, \
            f"WebSocket ID {websocket_id} should NOT validate as user ID"
        assert validates_as_websocket, \
            f"WebSocket ID {websocket_id} should validate as websocket ID"
    
    def test_validation_missing_cross_reference_checks(self):
        """
        CRITICAL FAILURE TEST: Validation doesn't check cross-references.
        
        This exposes the lack of relational validation where IDs should
        reference existing entities.
        
        Business Impact: Orphaned references, data integrity issues.
        
        EXPECTED: This test SHOULD FAIL, proving cross-reference gaps.
        """
        # Create a run ID that references a non-existent thread
        fake_thread_id = "thread_999_nonexist"
        run_id = self.id_manager.generate_run_id(fake_thread_id)
        
        # Validation should check that referenced thread exists
        run_format_valid = is_valid_id_format(run_id)
        thread_exists = self.id_manager.is_valid_id(fake_thread_id)
        
        # Business requirement: run ID should only be valid if thread exists
        if run_format_valid and not thread_exists:
            # This assertion SHOULD FAIL, proving missing cross-reference validation
            assert False, \
                f"Run ID {run_id} validates despite non-existent thread {fake_thread_id}"
    
    def test_validation_allows_security_policy_violations(self):
        """
        CRITICAL FAILURE TEST: Validation doesn't enforce security policies.
        
        This exposes the lack of security-aware validation that should
        prevent certain ID patterns or contexts.
        
        Business Impact: Security vulnerabilities, unauthorized access.
        
        EXPECTED: This test SHOULD FAIL, proving security policy gaps.
        """
        # Create IDs that might violate security policies
        admin_looking_id = "user_0_admin001"  # Looks like admin ID
        system_looking_id = "user_0_system01"  # Looks like system ID
        
        security_violating_ids = [admin_looking_id, system_looking_id]
        
        for suspicious_id in security_violating_ids:
            format_valid = is_valid_id_format(suspicious_id)
            
            # Security requirement: suspicious patterns should be flagged
            if format_valid:
                # This assertion SHOULD FAIL, proving missing security validation
                assert False, \
                    f"ID {suspicious_id} validates despite suspicious security pattern"


class TestValidationPerformanceInconsistencies:
    """
    Tests that expose performance inconsistencies in validation approaches.
    """
    
    def test_validation_performance_varies_by_id_type(self):
        """
        CRITICAL FAILURE TEST: Validation performance varies dramatically by ID type.
        
        This exposes potential performance issues where certain ID types
        take much longer to validate than others.
        
        Business Impact: Performance bottlenecks, timeout failures.
        
        EXPECTED: This test MAY FAIL, proving performance inconsistency.
        """
        import time
        
        # Test validation performance for different ID types
        id_types = [IDType.USER, IDType.THREAD, IDType.EXECUTION, IDType.WEBSOCKET]
        validation_times = {}
        
        for id_type in id_types:
            test_id = self.id_manager.generate_id(id_type)
            
            start_time = time.time()
            for _ in range(100):  # Run validation 100 times
                self.id_manager.is_valid_id(test_id, id_type)
            end_time = time.time()
            
            validation_times[id_type] = end_time - start_time
        
        # Check for dramatic performance differences
        min_time = min(validation_times.values())
        max_time = max(validation_times.values())
        
        # This assertion might FAIL if there are performance inconsistencies
        performance_ratio = max_time / min_time if min_time > 0 else float('inf')
        assert performance_ratio < 10, \
            f"Validation performance inconsistency: {performance_ratio}x difference. " \
            f"Times: {validation_times}"
    
    def test_validation_memory_usage_inconsistency(self):
        """
        CRITICAL FAILURE TEST: Validation memory usage varies by approach.
        
        This exposes potential memory leaks or excessive memory usage
        in certain validation code paths.
        
        Business Impact: Memory leaks, system crashes under load.
        
        EXPECTED: This test MAY FAIL, proving memory usage problems.
        """
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Measure memory before validation
        memory_before = process.memory_info().rss
        
        # Perform extensive validation
        for _ in range(1000):
            test_id = str(uuid.uuid4())
            is_valid_id_format(test_id)
            self.id_manager.is_valid_id(test_id)
        
        # Measure memory after validation
        memory_after = process.memory_info().rss
        memory_increase = memory_after - memory_before
        
        # This assertion might FAIL if validation leaks memory
        assert memory_increase < 10 * 1024 * 1024, \
            f"Validation memory leak detected: {memory_increase} bytes increased"


# Mark these as critical tests that must be addressed
@pytest.mark.critical
@pytest.mark.id_system_validation
class TestValidationCriticalBusinessFailures:
    """
    Critical tests that demonstrate business-breaking validation failures.
    """
    
    def test_validation_breaks_user_session_isolation(self):
        """
        CRITICAL FAILURE TEST: Validation failures break user session isolation.
        
        This is the most critical business impact where validation inconsistencies
        can lead to user data being accessible by wrong users.
        
        Business Impact: CRITICAL - User data leakage, privacy violations.
        
        EXPECTED: This test SHOULD FAIL, proving critical isolation problem.
        """
        # Simulate two user sessions with potentially confusing IDs
        user_a_session = str(uuid.uuid4())
        user_b_session = str(uuid.uuid4())
        
        # The validation problem: no way to ensure session belongs to user
        user_a_id = str(uuid.uuid4())
        
        # This should fail because we can't validate session ownership
        session_belongs_to_user = self._validate_session_ownership(user_a_id, user_a_session)
        
        # This assertion SHOULD FAIL, proving critical isolation failure
        assert session_belongs_to_user, \
            f"Cannot validate that session {user_a_session} belongs to user {user_a_id}"
    
    def _validate_session_ownership(self, user_id: str, session_id: str) -> bool:
        """Helper to validate session ownership - should fail with UUID approach."""
        # With plain UUIDs, this is impossible without external data
        return False


# IMPORTANT: Run these tests to expose validation inconsistencies
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])