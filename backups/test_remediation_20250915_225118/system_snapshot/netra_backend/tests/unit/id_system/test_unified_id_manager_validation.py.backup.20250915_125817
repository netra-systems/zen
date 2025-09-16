"""
UNIFIED ID MANAGER VALIDATION CONSISTENCY TESTS

These tests validate that the UnifiedIDManager provides consistent validation
behavior across different validators and handles all scenarios properly.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Reliability & Type Safety  
- Value Impact: Ensures consistent validation behavior in production
- Strategic Impact: Foundation for reliable multi-service architecture

EXPECTED BEHAVIOR: ALL TESTS SHOULD PASS
This demonstrates validation consistency and proper behavior.
"""
import pytest
import uuid
from typing import Optional, Any
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType, get_id_manager, is_valid_id_format, generate_id
from shared.types.core_types import UserID, ThreadID, ExecutionID, WebSocketID, ensure_user_id, ensure_thread_id
from test_framework.fixtures.id_system.id_format_samples import get_uuid_samples, get_unified_samples, get_malformed_samples, EXPECTED_UUID_PATTERN, EXPECTED_UNIFIED_PATTERN

class TestUnifiedIDManagerValidationConsistency:
    """
    Tests that validate critical validation consistency in the ID system.
    
    These demonstrate that the same ID value gets consistent validation
    results across different validators and usage contexts.
    """

    def setup_method(self):
        """Setup for each test method."""
        self.id_manager = UnifiedIDManager()

    def test_validation_consistency_uuid_and_unified_manager(self):
        """
        CONSISTENCY TEST: Same UUID validates consistently across different validators.
        
        This validates that both `is_valid_id_format()` and `UnifiedIDManager`
        provide consistent results for UUID format IDs.
        
        Business Impact: Consistent validation behavior prevents production failures.
        
        EXPECTED: This test SHOULD PASS, proving validation consistency.
        """
        test_uuid = str(uuid.uuid4())
        format_validator_result = is_valid_id_format(test_uuid)
        manager_compatibility_result = self.id_manager.is_valid_id_format_compatible(test_uuid)
        assert format_validator_result, f'is_valid_id_format should accept UUID: {test_uuid}'
        assert manager_compatibility_result, f'UnifiedIDManager should accept UUID format: {test_uuid}'
        structured_id = self.id_manager.generate_id(IDType.USER)
        struct_format_valid = is_valid_id_format(structured_id)
        struct_manager_valid = self.id_manager.is_valid_id(structured_id)
        assert struct_format_valid, f'is_valid_id_format should accept structured ID: {structured_id}'
        assert struct_manager_valid, f'UnifiedIDManager should validate its own IDs: {structured_id}'

    def test_registered_id_validation_behavior(self):
        """
        CONSISTENCY TEST: Registered IDs validate consistently across contexts.
        
        This validates that once an ID is registered, it validates consistently
        regardless of which validation method is used.
        
        Business Impact: Predictable validation behavior for registered IDs.
        
        EXPECTED: This test SHOULD PASS, proving consistent registered ID behavior.
        """
        test_unified_id = 'user_999_deadbeef'
        success = self.id_manager.register_existing_id(test_unified_id, IDType.USER)
        assert success, f'ID should register successfully: {test_unified_id}'
        format_valid = is_valid_id_format(test_unified_id)
        manager_valid = self.id_manager.is_valid_id(test_unified_id)
        compatibility_valid = self.id_manager.is_valid_id_format_compatible(test_unified_id)
        assert format_valid, f'Registered ID should pass format validation: {test_unified_id}'
        assert manager_valid, f'Registered ID should pass manager validation: {test_unified_id}'
        assert compatibility_valid, f'Registered ID should pass compatibility validation: {test_unified_id}'

    def test_id_type_validation_strictness_consistency(self):
        """
        CONSISTENCY TEST: ID type validation strictness is appropriate and consistent.
        
        This validates that type validation works correctly when type information
        is provided, while being appropriately permissive for format validation.
        
        Business Impact: Proper type safety without overly restrictive validation.
        
        EXPECTED: This test SHOULD PASS, proving appropriate validation strictness.
        """
        user_id = self.id_manager.generate_id(IDType.USER)
        valid_as_user = self.id_manager.is_valid_id(user_id, IDType.USER)
        valid_as_thread = self.id_manager.is_valid_id(user_id, IDType.THREAD)
        valid_without_type = self.id_manager.is_valid_id(user_id)
        assert valid_as_user, f'User ID should validate as user type: {user_id}'
        assert not valid_as_thread, f'User ID should NOT validate as thread type: {user_id}'
        assert valid_without_type, f'User ID should validate without type constraint: {user_id}'
        format_valid = is_valid_id_format(user_id)
        compatibility_valid = self.id_manager.is_valid_id_format_compatible(user_id, IDType.USER)
        assert format_valid, f'User ID should pass format validation: {user_id}'
        assert compatibility_valid, f'User ID should be compatible with its type: {user_id}'

    def test_empty_and_none_id_handling_consistency(self):
        """
        CONSISTENCY TEST: Empty/None ID handling is consistent across validators.
        
        This validates that edge cases are handled consistently and predictably
        across all validation methods.
        
        Business Impact: Predictable behavior prevents unexpected exceptions.
        
        EXPECTED: This test SHOULD PASS, proving consistent edge case handling.
        """
        edge_cases = ['', None, '   ', '\n', '\t']
        for edge_case in edge_cases:
            try:
                format_result = is_valid_id_format(edge_case) if edge_case is not None else False
            except Exception:
                format_result = False
            try:
                manager_result = self.id_manager.is_valid_id(edge_case)
            except Exception:
                manager_result = False
            try:
                compatibility_result = self.id_manager.is_valid_id_format_compatible(edge_case)
            except Exception:
                compatibility_result = False
            assert not format_result, f'Format validator should reject edge case: {repr(edge_case)}'
            assert not manager_result, f'Manager validator should reject edge case: {repr(edge_case)}'
            assert not compatibility_result, f'Compatibility validator should reject edge case: {repr(edge_case)}'

    def test_case_sensitivity_validation_consistency(self):
        """
        CONSISTENCY TEST: Case sensitivity handling is consistent across validators.
        
        This validates that case handling is consistent and appropriate
        across different validation approaches.
        
        Business Impact: Predictable ID matching regardless of case variations.
        
        EXPECTED: This test SHOULD PASS, proving consistent case handling.
        """
        base_uuid = str(uuid.uuid4()).lower()
        upper_uuid = base_uuid.upper()
        mixed_case_uuid = base_uuid[:16] + base_uuid[16:].upper()
        test_cases = [base_uuid, upper_uuid, mixed_case_uuid]
        for test_id in test_cases:
            format_valid = is_valid_id_format(test_id)
            compatibility_valid = self.id_manager.is_valid_id_format_compatible(test_id)
            assert format_valid, f'Format validator should accept UUID case variation: {test_id}'
            assert compatibility_valid, f'Compatibility validator should accept UUID case variation: {test_id}'

class TestValidationBusinessRequirementsSupport:
    """
    Tests that validate the ID system properly supports business requirements.
    """

    def setup_method(self):
        """Setup for each test method."""
        self.id_manager = UnifiedIDManager()

    def test_validation_supports_business_context_checking(self):
        """
        BUSINESS TEST: Validation properly supports business context requirements.
        
        This validates that the ID system can enforce business context rules
        through proper type validation and metadata checks.
        
        Business Impact: Ensures IDs are used in appropriate business contexts.
        
        EXPECTED: This test SHOULD PASS, proving business context support.
        """
        websocket_id = self.id_manager.generate_id(IDType.WEBSOCKET, context={'connection_type': 'client_websocket'})
        user_id = self.id_manager.generate_id(IDType.USER, context={'user_type': 'authenticated'})
        websocket_validates_as_websocket = self.id_manager.is_valid_id(websocket_id, IDType.WEBSOCKET)
        websocket_validates_as_user = self.id_manager.is_valid_id(websocket_id, IDType.USER)
        user_validates_as_user = self.id_manager.is_valid_id(user_id, IDType.USER)
        user_validates_as_websocket = self.id_manager.is_valid_id(user_id, IDType.WEBSOCKET)
        assert websocket_validates_as_websocket, f'WebSocket ID {websocket_id} should validate as websocket ID'
        assert not websocket_validates_as_user, f'WebSocket ID {websocket_id} should NOT validate as user ID'
        assert user_validates_as_user, f'User ID {user_id} should validate as user ID'
        assert not user_validates_as_websocket, f'User ID {user_id} should NOT validate as websocket ID'

    def test_validation_supports_cross_reference_checking(self):
        """
        BUSINESS TEST: Validation can support cross-reference checks through metadata.
        
        This validates that the system can support relational validation where
        IDs reference existing entities through proper metadata management.
        
        Business Impact: Enables referential integrity checks in business logic.
        
        EXPECTED: This test SHOULD PASS, proving cross-reference capability.
        """
        thread_id = self.id_manager.generate_id(IDType.THREAD, context={'thread_type': 'user_session'})
        run_id = self.id_manager.generate_run_id(thread_id)
        success = self.id_manager.register_existing_id(run_id, IDType.EXECUTION, context={'parent_thread_id': thread_id})
        assert success, f'Run ID should register with thread reference: {run_id}'
        thread_valid = self.id_manager.is_valid_id(thread_id, IDType.THREAD)
        run_format_valid = is_valid_id_format(run_id)
        run_registered_valid = self.id_manager.is_valid_id(run_id, IDType.EXECUTION)
        assert thread_valid, f'Thread ID should validate: {thread_id}'
        assert run_format_valid, f'Run ID should have valid format: {run_id}'
        assert run_registered_valid, f'Run ID should validate as execution: {run_id}'
        run_metadata = self.id_manager.get_id_metadata(run_id)
        referenced_thread = run_metadata.context.get('parent_thread_id')
        assert referenced_thread == thread_id, f'Run ID metadata should reference correct thread: {referenced_thread} != {thread_id}'

    def test_validation_enforces_security_policy_compliance(self):
        """
        BUSINESS TEST: Validation can enforce security policy compliance through metadata.
        
        This validates that security policies can be enforced through proper
        ID registration and context metadata validation.
        
        Business Impact: Enables security compliance and access control.
        
        EXPECTED: This test SHOULD PASS, proving security policy support.
        """
        standard_user_id = self.id_manager.generate_id(IDType.USER, context={'security_level': 'standard', 'access_tier': 'basic'})
        admin_user_id = self.id_manager.generate_id(IDType.USER, context={'security_level': 'elevated', 'access_tier': 'admin'})
        standard_valid = self.id_manager.is_valid_id(standard_user_id, IDType.USER)
        admin_valid = self.id_manager.is_valid_id(admin_user_id, IDType.USER)
        assert standard_valid, f'Standard user ID should validate: {standard_user_id}'
        assert admin_valid, f'Admin user ID should validate: {admin_user_id}'
        standard_metadata = self.id_manager.get_id_metadata(standard_user_id)
        admin_metadata = self.id_manager.get_id_metadata(admin_user_id)
        assert standard_metadata.context['security_level'] == 'standard', 'Standard user should have standard security level'
        assert admin_metadata.context['security_level'] == 'elevated', 'Admin user should have elevated security level'

        def check_admin_access(user_id: str) -> bool:
            metadata = self.id_manager.get_id_metadata(user_id)
            if not metadata:
                return False
            return metadata.context.get('access_tier') == 'admin'
        assert not check_admin_access(standard_user_id), 'Standard user should not have admin access'
        assert check_admin_access(admin_user_id), 'Admin user should have admin access'

class TestValidationPerformanceConsistency:
    """
    Tests that validate consistent performance across validation approaches.
    """

    def setup_method(self):
        """Setup for each test method."""
        self.id_manager = UnifiedIDManager()

    def test_validation_performance_consistent_across_id_types(self):
        """
        PERFORMANCE TEST: Validation performance is consistent across ID types.
        
        This validates that validation performance is reasonable and consistent
        regardless of ID type or format.
        
        Business Impact: Predictable system performance under load.
        
        EXPECTED: This test SHOULD PASS, proving consistent performance.
        """
        import time
        id_types = [IDType.USER, IDType.THREAD, IDType.EXECUTION, IDType.WEBSOCKET]
        validation_times = {}
        for id_type in id_types:
            test_id = self.id_manager.generate_id(id_type)
            start_time = time.time()
            for _ in range(100):
                self.id_manager.is_valid_id(test_id, id_type)
            end_time = time.time()
            validation_times[id_type] = end_time - start_time
        for id_type, validation_time in validation_times.items():
            assert validation_time < 1.0, f'Validation should be fast for {id_type.value}: {validation_time}s for 100 validations'
        min_time = min(validation_times.values())
        max_time = max(validation_times.values())
        performance_ratio = max_time / min_time if min_time > 0 else 1.0
        assert performance_ratio < 5, f'Validation performance should be consistent: {performance_ratio}x difference. Times: {validation_times}'

    def test_validation_memory_usage_efficient(self):
        """
        PERFORMANCE TEST: Validation operations have reasonable memory usage.
        
        This validates that validation operations don't cause excessive memory usage
        or memory leaks that could impact system performance.
        
        Business Impact: System stability under sustained load.
        
        EXPECTED: This test SHOULD PASS, proving efficient memory usage.
        """
        import psutil
        import os
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss
        for i in range(1000):
            if i % 2 == 0:
                test_id = str(uuid.uuid4())
                is_valid_id_format(test_id)
                self.id_manager.is_valid_id_format_compatible(test_id)
            else:
                test_id = self.id_manager.generate_id(IDType.USER)
                self.id_manager.is_valid_id(test_id)
                is_valid_id_format(test_id)
        memory_after = process.memory_info().rss
        memory_increase = memory_after - memory_before
        assert memory_increase < 10 * 1024 * 1024, f'Validation should not cause memory leaks: {memory_increase} bytes increased'

@pytest.mark.critical
@pytest.mark.id_system_validation
class TestValidationBusinessCriticalOperations:
    """
    Critical tests that demonstrate business-critical validation operations work correctly.
    """

    def setup_method(self):
        """Setup for each test method."""
        self.id_manager = UnifiedIDManager()

    def test_validation_enables_user_session_isolation(self):
        """
        CRITICAL TEST: Validation enables proper user session isolation.
        
        This validates that the validation system properly supports user session
        isolation, preventing cross-user data access.
        
        Business Impact: Prevents user data leakage and privacy violations.
        
        EXPECTED: This test SHOULD PASS, proving session isolation capability.
        """
        user_a_session = self.id_manager.generate_id(IDType.SESSION, context={'user_tenant': 'tenant_a'})
        user_b_session = self.id_manager.generate_id(IDType.SESSION, context={'user_tenant': 'tenant_b'})
        user_a_valid = self.id_manager.is_valid_id(user_a_session, IDType.SESSION)
        user_b_valid = self.id_manager.is_valid_id(user_b_session, IDType.SESSION)
        assert user_a_valid, f'User A session should validate: {user_a_session}'
        assert user_b_valid, f'User B session should validate: {user_b_session}'
        session_isolation_valid = self._validate_session_isolation(user_a_session, user_b_session)
        assert session_isolation_valid, f'Should be able to validate session isolation between {user_a_session} and {user_b_session}'

    def _validate_session_isolation(self, session_a: str, session_b: str) -> bool:
        """Validate session isolation through metadata analysis."""
        metadata_a = self.id_manager.get_id_metadata(session_a)
        metadata_b = self.id_manager.get_id_metadata(session_b)
        if not metadata_a or not metadata_b:
            return False
        tenant_a = metadata_a.context.get('user_tenant')
        tenant_b = metadata_b.context.get('user_tenant')
        return tenant_a != tenant_b and tenant_a is not None and (tenant_b is not None)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')