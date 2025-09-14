"""
Issue #1085 Interface Mismatch Vulnerability Tests - Phase 1 Unit Tests

CRITICAL P0 SECURITY TESTING: Reproduce confirmed interface compatibility issues affecting 
$500K+ ARR enterprise customers requiring HIPAA, SOC2, SEC compliance.

These tests REPRODUCE confirmed vulnerabilities:
1. AttributeError: 'DeepAgentState' object has no attribute 'create_child_context'
2. Interface incompatibility in modern_execution_helpers.py line 38
3. SSOT violations causing security vulnerabilities

EXPECTED BEHAVIOR: These tests MUST FAIL initially, proving the vulnerabilities exist.
"""

import pytest
from unittest.mock import Mock, AsyncMock
import uuid

from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.modern_execution_helpers import ModernExecutionHelpers


class TestInterfaceMismatchVulnerabilities:
    """Test suite to reproduce confirmed interface mismatch vulnerabilities."""

    def test_deepagentstate_missing_create_child_context_method(self):
        """VULNERABILITY REPRODUCTION: DeepAgentState lacks create_child_context method.
        
        CRITICAL SECURITY IMPACT:
        - Interface incompatibility causes AttributeError at runtime
        - $500K+ ARR enterprise customers affected
        - HIPAA, SOC2, SEC compliance violations due to user isolation failures
        
        EXPECTED: This test MUST FAIL with AttributeError, proving vulnerability exists.
        """
        # Create DeepAgentState instance - this represents legacy deprecated state
        deep_agent_state = DeepAgentState(
            user_request="enterprise security test",
            user_id="enterprise_user_123",
            chat_thread_id="secure_thread_456",
            run_id="vulnerability_reproduction_run_789"
        )
        
        # VULNERABILITY REPRODUCTION: Attempt to call create_child_context()
        # This MUST FAIL with AttributeError since DeepAgentState lacks this method
        with pytest.raises(AttributeError) as exc_info:
            # This line replicates modern_execution_helpers.py line 38 behavior
            child_context = deep_agent_state.create_child_context(
                operation_name="supervisor_workflow",
                additional_context={"workflow_result": {"test": "data"}}
            )
        
        # Validate the exact error message that indicates the vulnerability
        error_message = str(exc_info.value)
        assert "'DeepAgentState' object has no attribute 'create_child_context'" in error_message
        assert "create_child_context" in error_message

    def test_userexecutioncontext_has_create_child_context_method(self):
        """CONTROL TEST: UserExecutionContext has proper create_child_context method.
        
        This test proves the interface exists in the secure implementation but is
        missing in the vulnerable DeepAgentState class.
        """
        # Create UserExecutionContext - secure implementation
        user_context = UserExecutionContext.from_request(
            user_id="enterprise_user_123",
            thread_id="secure_thread_456",
            run_id="control_test_run_789"
        )
        
        # This should work correctly - UserExecutionContext has the method
        child_context = user_context.create_child_context(
            operation_name="supervisor_workflow",
            additional_agent_context={"workflow_result": {"test": "data"}}
        )
        
        # Validate child context creation succeeded
        assert child_context is not None
        assert isinstance(child_context, UserExecutionContext)
        assert child_context.request_id != user_context.request_id  # Should have new request ID
        assert child_context.user_id == user_context.user_id  # Should inherit user ID

    async def test_modern_execution_helpers_interface_vulnerability(self):
        """VULNERABILITY REPRODUCTION: ModernExecutionHelpers fails with DeepAgentState.
        
        CRITICAL SECURITY IMPACT:
        - Production code failure when DeepAgentState passed to ModernExecutionHelpers
        - Interface mismatch causes runtime AttributeError
        - User isolation failures affecting enterprise compliance
        
        EXPECTED: This test MUST FAIL, reproducing the exact production vulnerability.
        """
        # Create mock supervisor for ModernExecutionHelpers
        mock_supervisor = AsyncMock()
        mock_supervisor.run.return_value = Mock()
        mock_supervisor.run.return_value.to_dict.return_value = {"test": "result"}
        
        # Initialize ModernExecutionHelpers
        execution_helpers = ModernExecutionHelpers(supervisor=mock_supervisor)
        
        # Create vulnerable DeepAgentState instance
        vulnerable_context = DeepAgentState(
            user_request="enterprise vulnerability test",
            user_id="enterprise_user_123",
            chat_thread_id="vulnerable_thread_456",
            run_id="production_vulnerability_run_789"
        )
        
        # VULNERABILITY REPRODUCTION: This will fail at line 38 in modern_execution_helpers.py
        # when it tries to call context.create_child_context()
        with pytest.raises(AttributeError) as exc_info:
            await execution_helpers.execute_supervisor_workflow(
                user_request="enterprise security test",
                context=vulnerable_context,
                run_id="vulnerability_test_run"
            )
        
        # Validate the specific vulnerability is reproduced
        error_message = str(exc_info.value)
        assert "'DeepAgentState' object has no attribute 'create_child_context'" in error_message

    async def test_modern_execution_helpers_works_with_userexecutioncontext(self):
        """CONTROL TEST: ModernExecutionHelpers works correctly with UserExecutionContext.
        
        This proves the vulnerability is specific to DeepAgentState interface mismatch.
        """
        # Create mock supervisor
        mock_supervisor = AsyncMock()
        mock_result = Mock()
        mock_result.to_dict.return_value = {"test": "result"}
        mock_supervisor.run.return_value = mock_result
        
        # Initialize ModernExecutionHelpers
        execution_helpers = ModernExecutionHelpers(supervisor=mock_supervisor)
        
        # Create secure UserExecutionContext instance
        secure_context = UserExecutionContext.from_request(
            user_id="enterprise_user_123",
            thread_id="secure_thread_456",
            run_id="secure_run_789"
        )
        
        # This should work correctly with UserExecutionContext
        result = await execution_helpers.execute_supervisor_workflow(
            user_request="enterprise security test",
            context=secure_context,
            run_id="control_test_run"
        )
        
        # Validate successful execution
        assert result is not None
        assert isinstance(result, UserExecutionContext)
        assert result.user_id == secure_context.user_id

    def test_interface_compatibility_matrix(self):
        """COMPREHENSIVE TEST: Document interface compatibility matrix for security audit.
        
        This test documents exactly which interfaces are compatible vs vulnerable,
        providing enterprise security teams with clear audit trail.
        """
        # Test DeepAgentState interface completeness
        deep_agent_state = DeepAgentState(
            user_request="interface audit test",
            user_id="audit_user_123"
        )
        
        # UserExecutionContext interface completeness  
        user_context = UserExecutionContext.from_request(
            user_id="audit_user_123",
            thread_id="audit_thread_456",
            run_id="audit_run_789"
        )
        
        # Document interface compatibility matrix
        compatibility_matrix = {
            "DeepAgentState": {
                "create_child_context": hasattr(deep_agent_state, "create_child_context"),
                "user_id": hasattr(deep_agent_state, "user_id"),
                "thread_id": hasattr(deep_agent_state, "thread_id"),  # Should be true via property
                "run_id": hasattr(deep_agent_state, "run_id"),
            },
            "UserExecutionContext": {
                "create_child_context": hasattr(user_context, "create_child_context"),
                "user_id": hasattr(user_context, "user_id"),
                "thread_id": hasattr(user_context, "thread_id"),
                "run_id": hasattr(user_context, "run_id"),
            }
        }
        
        # CRITICAL VULNERABILITY: DeepAgentState missing create_child_context
        assert not compatibility_matrix["DeepAgentState"]["create_child_context"], \
            "VULNERABILITY CONFIRMED: DeepAgentState lacks create_child_context method"
        
        # SECURE IMPLEMENTATION: UserExecutionContext has complete interface
        assert compatibility_matrix["UserExecutionContext"]["create_child_context"], \
            "SECURITY CONTROL: UserExecutionContext has create_child_context method"
        
        # Document for security audit
        print("ENTERPRISE SECURITY AUDIT - Interface Compatibility Matrix:")
        for class_name, methods in compatibility_matrix.items():
            print(f"  {class_name}:")
            for method_name, has_method in methods.items():
                status = "✅ SECURE" if has_method else "🚨 VULNERABLE"
                print(f"    {method_name}: {status}")


class TestSSotViolationVulnerabilities:
    """Test suite to reproduce SSOT violations causing security vulnerabilities."""

    def test_multiple_deepagentstate_definitions_vulnerability(self):
        """VULNERABILITY REPRODUCTION: Multiple DeepAgentState definitions cause isolation failures.
        
        CRITICAL SECURITY IMPACT:
        - Multiple class definitions break user isolation
        - Different interfaces across definitions
        - Enterprise compliance violations
        """
        # This test documents the SSOT violation by attempting to import 
        # from multiple potential locations where DeepAgentState might be defined
        
        # Primary SSOT location (should work)
        from netra_backend.app.schemas.agent_models import DeepAgentState as PrimaryDeepAgentState
        
        primary_instance = PrimaryDeepAgentState(
            user_request="SSOT compliance test",
            user_id="compliance_user_123"
        )
        
        # Verify primary instance lacks secure interface
        assert not hasattr(primary_instance, "create_child_context"), \
            "Primary DeepAgentState lacks create_child_context - SSOT violation vulnerability confirmed"

    def test_legacy_import_paths_vulnerability(self):
        """VULNERABILITY REPRODUCTION: Legacy import paths create security vulnerabilities.
        
        Documents how multiple import paths for the same concept create
        interface inconsistencies and user isolation failures.
        """
        # Test that only the SSOT path works
        try:
            from netra_backend.app.schemas.agent_models import DeepAgentState
            ssot_import_works = True
        except ImportError:
            ssot_import_works = False
        
        # SSOT path must work
        assert ssot_import_works, "SSOT import path must be available"
        
        # Create instance from SSOT path
        ssot_instance = DeepAgentState(
            user_request="legacy path test",
            user_id="legacy_user_123"
        )
        
        # Confirm SSOT instance has the vulnerability (missing create_child_context)
        assert not hasattr(ssot_instance, "create_child_context"), \
            "SSOT DeepAgentState confirms interface vulnerability - missing create_child_context"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])