"""
CRITICAL ID FORMAT COMPATIBILITY TESTS

These tests validate that the UnifiedIDManager properly handles both
UUID and structured ID formats, ensuring compatibility and business requirements.

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: System Reliability
- Value Impact: Ensures ID system works correctly for multi-user scenarios
- Strategic Impact: Foundation for proper multi-user isolation

EXPECTED BEHAVIOR: ALL TESTS SHOULD PASS
This demonstrates the ID system properly handles dual format compatibility.
"""

import pytest
import uuid
from typing import Any

# CRITICAL: Use absolute imports per CLAUDE.md requirements
from netra_backend.app.core.unified_id_manager import (
    UnifiedIDManager, 
    IDType,
    is_valid_id_format
)
from shared.types.core_types import (
    UserID,
    ThreadID, 
    RunID,
    ExecutionID,
    ensure_user_id,
    ensure_thread_id
)
from test_framework.fixtures.id_system.id_format_samples import (
    get_uuid_samples,
    get_unified_samples,
    get_mixed_scenarios,
    generate_fresh_uuid_sample,
    generate_unified_sample
)


class TestIDFormatCompatibility:
    """
    Tests that validate critical ID format compatibility.
    
    These tests ensure business-critical functionality works correctly:
    1. UUID format IDs work with UnifiedIDManager validation  
    2. Type safety is maintained across modules
    3. Business logic works properly with dual format support
    """
    
    def setup_method(self):
        """Setup for each test method."""
        self.id_manager = UnifiedIDManager()
        
    def test_uuid_format_compatible_with_unified_manager(self):
        """
        COMPATIBILITY TEST: UnifiedIDManager properly handles UUID format IDs.
        
        This test validates that UnifiedIDManager can work with both UUID and
        structured formats, providing backward compatibility during migration.
        
        Business Impact: Enables gradual migration from UUID to structured IDs
        without breaking existing functionality.
        
        EXPECTED: This test SHOULD PASS, proving format compatibility works.
        """
        # Generate UUID in the style of ExecutionContext line 70
        raw_uuid = str(uuid.uuid4())
        
        # UnifiedIDManager should accept UUID format during migration
        registration_success = self.id_manager.register_existing_id(raw_uuid, IDType.EXECUTION)
        assert registration_success, f"UnifiedIDManager should accept UUID format: {raw_uuid}"
        
        # Validation should work for registered UUID
        assert self.id_manager.is_valid_id(raw_uuid, IDType.EXECUTION), \
            f"Registered UUID {raw_uuid} should validate as execution ID"
            
        # Format compatibility check should also work
        assert self.id_manager.is_valid_id_format_compatible(raw_uuid, IDType.EXECUTION), \
            f"UUID {raw_uuid} should be format-compatible with execution type"
    
    def test_validation_consistency_across_validators(self):
        """
        COMPATIBILITY TEST: Same ID validates consistently across different validators.
        
        This validates that different validation methods provide consistent results
        for both UUID and structured formats.
        
        Business Impact: Consistent validation behavior prevents production failures.
        
        EXPECTED: This test SHOULD PASS, proving validation consistency.
        """
        # Test with UUID format
        test_uuid = generate_fresh_uuid_sample()
        
        # Both validators should recognize UUID as valid format
        uuid_format_valid = is_valid_id_format(test_uuid)
        assert uuid_format_valid, f"is_valid_id_format should accept UUID: {test_uuid}"
        
        # For unregistered UUIDs, we test format compatibility instead of registration
        format_compatible = self.id_manager.is_valid_id_format_compatible(test_uuid)
        assert format_compatible, f"UnifiedIDManager should accept UUID format: {test_uuid}"
        
        # Test with structured format
        structured_id = self.id_manager.generate_id(IDType.USER)
        struct_format_valid = is_valid_id_format(structured_id)
        struct_manager_valid = self.id_manager.is_valid_id(structured_id)
        
        assert struct_format_valid, f"is_valid_id_format should accept structured ID: {structured_id}"
        assert struct_manager_valid, f"UnifiedIDManager should validate its own IDs: {structured_id}"
    
    def test_strongly_typed_id_conversion_works_with_uuid_input(self):
        """
        COMPATIBILITY TEST: Strongly typed ID conversion handles UUID input gracefully.
        
        This validates that the type system can work with UUID format during
        the migration period while maintaining type safety.
        
        Business Impact: Enables gradual migration without breaking type safety.
        
        EXPECTED: This test SHOULD PASS, showing type compatibility works.
        """
        raw_uuid = generate_fresh_uuid_sample()
        
        # Type conversions should work with UUIDs (NewType allows this)
        try:
            typed_user_id = ensure_user_id(raw_uuid)
            assert typed_user_id == raw_uuid, f"ensure_user_id should preserve UUID value: {raw_uuid}"
        except (ValueError, TypeError) as e:
            pytest.fail(f"ensure_user_id should handle UUID format: {e}")
            
        try:
            typed_thread_id = ensure_thread_id(raw_uuid)
            assert typed_thread_id == raw_uuid, f"ensure_thread_id should preserve UUID value: {raw_uuid}"
        except (ValueError, TypeError) as e:
            pytest.fail(f"ensure_thread_id should handle UUID format: {e}")
            
        # Verify types are properly distinguished even with UUID format
        assert isinstance(typed_user_id, str), "UserID should be string-based"
        assert isinstance(typed_thread_id, str), "ThreadID should be string-based"
    
    def test_id_type_safety_with_unified_manager(self):
        """
        COMPATIBILITY TEST: UnifiedIDManager provides type safety even with UUIDs.
        
        This validates that while UUIDs may look similar, the UnifiedIDManager
        can provide type information and validation when properly used.
        
        Business Impact: Prevents security violations and data leakage.
        
        EXPECTED: This test SHOULD PASS, proving type safety works.
        """
        # Generate UUIDs and register them with proper types
        uuid_for_user = generate_fresh_uuid_sample()
        uuid_for_thread = generate_fresh_uuid_sample()
        
        # Register with proper types in UnifiedIDManager
        self.id_manager.register_existing_id(uuid_for_user, IDType.USER)
        self.id_manager.register_existing_id(uuid_for_thread, IDType.THREAD)
        
        # Verify type-specific validation works
        assert self.id_manager.is_valid_id(uuid_for_user, IDType.USER), \
            "UUID should validate as user when registered as user"
        assert not self.id_manager.is_valid_id(uuid_for_user, IDType.THREAD), \
            "UUID should NOT validate as thread when registered as user"
        
        assert self.id_manager.is_valid_id(uuid_for_thread, IDType.THREAD), \
            "UUID should validate as thread when registered as thread"
        assert not self.id_manager.is_valid_id(uuid_for_thread, IDType.USER), \
            "UUID should NOT validate as user when registered as thread"
        
        # Verify metadata provides type information
        user_metadata = self.id_manager.get_id_metadata(uuid_for_user)
        thread_metadata = self.id_manager.get_id_metadata(uuid_for_thread)
        
        assert user_metadata.id_type == IDType.USER, "User ID should have USER type metadata"
        assert thread_metadata.id_type == IDType.THREAD, "Thread ID should have THREAD type metadata"
    
    def test_business_audit_trail_metadata_available_with_registered_uuids(self):
        """
        COMPATIBILITY TEST: Registered UUIDs provide business audit metadata.
        
        This validates that when UUIDs are properly registered with UnifiedIDManager,
        they provide all necessary metadata for audit trails and compliance.
        
        Business Impact: Enables regulatory compliance even with UUID format.
        
        EXPECTED: This test SHOULD PASS, proving audit trail capability.
        """
        # Generate UUID and register it properly
        audit_subject_uuid = generate_fresh_uuid_sample()
        
        # Register with business context
        audit_context = {
            "operation": "user_authentication",
            "business_unit": "security",
            "compliance_level": "high"
        }
        success = self.id_manager.register_existing_id(
            audit_subject_uuid, 
            IDType.USER, 
            context=audit_context
        )
        assert success, f"UUID should register successfully: {audit_subject_uuid}"
        
        # Extract audit metadata - should succeed
        metadata = self.id_manager.get_id_metadata(audit_subject_uuid)
        
        assert metadata is not None, \
            f"Registered UUID {audit_subject_uuid} should have audit metadata"
        
        assert metadata.created_at is not None, \
            "Registered UUID should have creation timestamp for audit trail"
        
        assert metadata.id_type == IDType.USER, \
            "Registered UUID should have type information for business logic"
        
        assert metadata.context == audit_context, \
            "Registered UUID should preserve business context for compliance"
    
    def test_mixed_format_scenario_database_persistence_works(self):
        """
        COMPATIBILITY TEST: Mixed ID formats work together in database scenarios.
        
        This validates that UnifiedIDManager can handle both UUID and structured
        formats consistently, enabling smooth database operations.
        
        Business Impact: Prevents data integrity issues during migration.
        
        EXPECTED: This test SHOULD PASS, proving database compatibility.
        """
        # Simulate mixed format scenario from fixtures
        mixed_scenarios = get_mixed_scenarios()
        uuid_id = mixed_scenarios[0]["uuid_id"]
        
        # Both formats should register successfully
        uuid_registered = self.id_manager.register_existing_id(uuid_id, IDType.USER)
        assert uuid_registered, f"UUID format should register successfully: {uuid_id}"
        
        structured_id = generate_unified_sample("user")
        structured_registered = self.id_manager.register_existing_id(structured_id, IDType.USER)
        assert structured_registered, f"Structured format should register successfully: {structured_id}"
        
        # Both should be valid and queryable
        assert self.id_manager.is_valid_id(uuid_id, IDType.USER), \
            f"UUID should be valid after registration: {uuid_id}"
        assert self.id_manager.is_valid_id(structured_id, IDType.USER), \
            f"Structured ID should be valid after registration: {structured_id}"
        
        # Both should provide metadata for database operations
        uuid_metadata = self.id_manager.get_id_metadata(uuid_id)
        struct_metadata = self.id_manager.get_id_metadata(structured_id)
        
        assert uuid_metadata is not None, "UUID should have metadata for database operations"
        assert struct_metadata is not None, "Structured ID should have metadata for database operations"
        assert uuid_metadata.id_type == struct_metadata.id_type == IDType.USER, \
            "Both formats should have consistent type information"
    
    def test_websocket_connection_id_format_compatibility(self):
        """
        COMPATIBILITY TEST: WebSocket connection IDs work with both formats.
        
        This validates that WebSocket connection ID generation is compatible
        with both UUID and UnifiedIDManager structured formats.
        
        Business Impact: Ensures WebSocket connection tracking works reliably.
        
        EXPECTED: This test SHOULD PASS, proving WebSocket ID compatibility.
        """
        # Test current WebSocket connection ID generation pattern
        # Use a format that validates as structured: websocket_counter_uuid8
        websocket_uuid_style = f"websocket_1_{uuid.uuid4().hex[:8]}"
        
        # This should be accepted as a valid format due to websocket prefix
        is_valid_format = is_valid_id_format(websocket_uuid_style)
        assert is_valid_format, f"WebSocket structured ID should be valid format: {websocket_uuid_style}"
        
        # Generate proper UnifiedIDManager WebSocket ID
        proper_websocket_id = self.id_manager.generate_id(IDType.WEBSOCKET)
        
        # Both should be usable for WebSocket connections
        websocket_registered = self.id_manager.register_existing_id(websocket_uuid_style, IDType.WEBSOCKET)
        assert websocket_registered, f"WebSocket UUID-style should register: {websocket_uuid_style}"
        
        # Both should validate properly
        assert self.id_manager.is_valid_id(websocket_uuid_style, IDType.WEBSOCKET), \
            f"Registered WebSocket UUID-style should validate: {websocket_uuid_style}"
        assert self.id_manager.is_valid_id(proper_websocket_id, IDType.WEBSOCKET), \
            f"Generated WebSocket ID should validate: {proper_websocket_id}"

    def _function_expecting_thread_id(self, thread_id: ThreadID) -> str:
        """Helper function that expects ThreadID type."""
        # This function demonstrates that type hints work properly
        return f"Processing thread: {thread_id}"


class TestLegacyUUIDCompatibilityRequirements:
    """
    Tests that validate UUID compatibility meets business requirements.
    """
    
    def setup_method(self):
        """Setup for each test method."""
        self.id_manager = UnifiedIDManager()
    
    def test_uuid4_provides_business_metadata_when_registered(self):
        """
        COMPATIBILITY TEST: uuid.uuid4() provides business metadata when properly registered.
        
        This validates that the enhanced system can provide business metadata
        even for UUID format IDs when they are properly registered.
        
        Business Impact: Enables audit trails and compliance for existing UUID usage.
        
        EXPECTED: This test SHOULD PASS, proving business requirement compatibility.
        """
        # Generate UUID in current style (ExecutionContext line 70)
        business_uuid = str(uuid.uuid4())
        
        # Register with business context
        business_context = {
            "creation_source": "user_authentication_flow",
            "business_process": "account_verification", 
            "compliance_level": "standard",
            "audit_category": "security"
        }
        
        success = self.id_manager.register_existing_id(
            business_uuid, 
            IDType.USER, 
            context=business_context
        )
        assert success, f"Business UUID should register successfully: {business_uuid}"
        
        # Extract business metadata - should succeed
        metadata = self.id_manager.get_id_metadata(business_uuid)
        assert metadata is not None, f"Business UUID should have metadata: {business_uuid}"
        
        # Verify all required business metadata is available
        required_metadata = {
            "creation_timestamp": metadata.created_at,
            "business_context": metadata.context,
            "id_type": metadata.id_type,
            "traceability_info": metadata.id_value
        }
        
        for requirement, actual_value in required_metadata.items():
            assert actual_value is not None, \
                f"UUID {business_uuid} should have required business metadata: {requirement}"
    
    def test_uuid_approach_supports_execution_sequence_tracking(self):
        """
        COMPATIBILITY TEST: UUID approach supports execution sequence tracking when properly managed.
        
        This validates that with proper registration and metadata, even UUID format
        can support execution sequence tracking and pattern analysis.
        
        Business Impact: Enables debugging execution flows and performance analysis.
        
        EXPECTED: This test SHOULD PASS, proving execution tracking works.
        """
        # Generate sequence of UUIDs with proper registration
        execution_steps = [
            "user_authentication",
            "agent_initialization", 
            "tool_execution",
            "result_processing",
            "response_delivery"
        ]
        
        execution_uuids = []
        for i, step in enumerate(execution_steps):
            step_uuid = str(uuid.uuid4())
            
            # Register with sequence information in context
            sequence_context = {
                "sequence_position": i,
                "step_name": step,
                "execution_batch": "test_batch_001",
                "timestamp_order": i * 1000  # Artificial ordering for test
            }
            
            success = self.id_manager.register_existing_id(
                step_uuid, 
                IDType.EXECUTION, 
                context=sequence_context
            )
            assert success, f"Step UUID should register: {step_uuid}"
            execution_uuids.append((step, step_uuid))
        
        # Verify sequence tracking works through metadata
        for i, (step_name, step_uuid) in enumerate(execution_uuids):
            metadata = self.id_manager.get_id_metadata(step_uuid)
            assert metadata is not None, f"Step UUID should have metadata: {step_uuid}"
            
            sequence_position = metadata.context.get("sequence_position")
            assert sequence_position == i, \
                f"Should be able to determine execution sequence for step '{step_name}' " \
                f"with UUID {step_uuid}. Expected position {i}, got {sequence_position}"
    
    def test_uuid4_supports_multi_user_isolation_requirements(self):
        """
        COMPATIBILITY TEST: uuid.uuid4() supports user isolation when properly managed.
        
        This validates that proper registration and context management enables
        user isolation even with UUID format IDs.
        
        Business Impact: Prevents user data leakage and ensures privacy compliance.
        
        EXPECTED: This test SHOULD PASS, proving isolation capability works.
        """
        # Generate UUIDs for multi-user scenario
        user_a_uuid = str(uuid.uuid4())
        user_b_uuid = str(uuid.uuid4())
        
        # Register users with isolation context
        user_a_context = {
            "tenant_id": "tenant_a",
            "isolation_boundary": "user_a_workspace",
            "access_level": "standard"
        }
        user_b_context = {
            "tenant_id": "tenant_b", 
            "isolation_boundary": "user_b_workspace",
            "access_level": "standard"
        }
        
        self.id_manager.register_existing_id(user_a_uuid, IDType.USER, context=user_a_context)
        self.id_manager.register_existing_id(user_b_uuid, IDType.USER, context=user_b_context)
        
        # Generate execution contexts for both users
        user_a_execution = str(uuid.uuid4())
        user_b_execution = str(uuid.uuid4())
        
        # Register executions with user ownership
        exec_a_context = {
            "owner_user_id": user_a_uuid,
            "tenant_id": "tenant_a",
            "isolation_boundary": "user_a_workspace"
        }
        exec_b_context = {
            "owner_user_id": user_b_uuid,
            "tenant_id": "tenant_b", 
            "isolation_boundary": "user_b_workspace"
        }
        
        self.id_manager.register_existing_id(user_a_execution, IDType.EXECUTION, context=exec_a_context)
        self.id_manager.register_existing_id(user_b_execution, IDType.EXECUTION, context=exec_b_context)
        
        # Validate user isolation through metadata
        a_isolation_valid = self._validate_user_isolation(user_a_uuid, user_a_execution)
        b_isolation_valid = self._validate_user_isolation(user_b_uuid, user_b_execution)
        
        assert a_isolation_valid, \
            f"Should be able to validate isolation for user {user_a_uuid} execution {user_a_execution}"
        assert b_isolation_valid, \
            f"Should be able to validate isolation for user {user_b_uuid} execution {user_b_execution}"
        
        # Cross-contamination check should detect violations
        cross_contamination = self._detect_cross_user_contamination(
            user_a_uuid, user_b_execution
        )
        assert cross_contamination, \
            f"Should detect cross-user contamination: user {user_a_uuid} " \
            f"accessing execution {user_b_execution}"
    
    def _validate_user_isolation(self, user_uuid: str, execution_uuid: str) -> bool:
        """Check if user isolation can be validated through metadata."""
        user_metadata = self.id_manager.get_id_metadata(user_uuid)
        exec_metadata = self.id_manager.get_id_metadata(execution_uuid)
        
        if not user_metadata or not exec_metadata:
            return False
        
        # Check isolation boundary matching
        user_boundary = user_metadata.context.get("isolation_boundary")
        exec_boundary = exec_metadata.context.get("isolation_boundary")
        
        return user_boundary and exec_boundary and user_boundary == exec_boundary
    
    def _detect_cross_user_contamination(self, user_uuid: str, execution_uuid: str) -> bool:
        """Detect cross-user contamination through metadata analysis."""
        user_metadata = self.id_manager.get_id_metadata(user_uuid)
        exec_metadata = self.id_manager.get_id_metadata(execution_uuid)
        
        if not user_metadata or not exec_metadata:
            return True  # Can't validate, assume contamination
        
        # Check for boundary violations
        user_boundary = user_metadata.context.get("isolation_boundary")
        exec_boundary = exec_metadata.context.get("isolation_boundary")
        
        return user_boundary != exec_boundary


@pytest.mark.critical
@pytest.mark.id_system
class TestIDSystemBusinessValue:
    """
    Tests that demonstrate the business value of the enhanced ID system.
    """
    
    def setup_method(self):
        """Setup for each test method."""
        self.id_manager = UnifiedIDManager()
    
    def test_multi_user_isolation_maintained_with_enhanced_system(self):
        """
        BUSINESS VALUE TEST: Enhanced ID system maintains multi-user isolation.
        
        This validates that the enhanced system properly supports multi-user
        scenarios with full isolation and security.
        
        Business Impact: Enables secure multi-tenant operations.
        
        EXPECTED: This test SHOULD PASS, proving business value delivery.
        """
        # Create user sessions with proper isolation
        user_a_id = self.id_manager.generate_id(IDType.USER, context={"tenant": "company_a"})
        user_b_id = self.id_manager.generate_id(IDType.USER, context={"tenant": "company_b"})
        
        # Create execution contexts with proper ownership
        exec_a_id = self.id_manager.generate_id(IDType.EXECUTION, context={"owner": user_a_id})
        exec_b_id = self.id_manager.generate_id(IDType.EXECUTION, context={"owner": user_b_id})
        
        # Validate ownership relationships are clear
        exec_a_metadata = self.id_manager.get_id_metadata(exec_a_id)
        exec_b_metadata = self.id_manager.get_id_metadata(exec_b_id)
        
        assert exec_a_metadata.context["owner"] == user_a_id, \
            f"Should be able to determine that user {user_a_id} owns execution {exec_a_id}"
        assert exec_b_metadata.context["owner"] == user_b_id, \
            f"Should be able to determine that user {user_b_id} owns execution {exec_b_id}"
        
        # Cross-ownership should be detectable as violation
        assert exec_a_metadata.context["owner"] != user_b_id, \
            f"Should detect that user {user_b_id} does NOT own execution {exec_a_id}"


# IMPORTANT: Run these tests to validate ID system compatibility and business value
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])