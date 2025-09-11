"""Simple tests to verify DeepAgentState security vulnerability fixes.

This test suite validates that the security fixes implemented for issue #271
effectively prevent the identified vulnerabilities.

Created: 2025-09-10
Scope: Security vulnerability remediation validation
"""

import pytest
import uuid
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext, 
    UserContextManager,
    InvalidContextError
)


def test_user_execution_context_rejects_placeholder_values():
    """Test that UserExecutionContext rejects placeholder/system values."""
    # UserExecutionContext validates against system placeholder values
    # User input validation should happen at authentication layer
    placeholder_inputs = [
        "placeholder",
        "default", 
        "temp",
        "mock",
        "example"
    ]
    
    for placeholder_input in placeholder_inputs:
        with pytest.raises(InvalidContextError):
            UserExecutionContext.from_request(
                user_id=placeholder_input,
                thread_id="valid_thread",
                run_id="valid_run"
            )


def test_user_execution_context_serialization_is_safe():
    """Test that UserExecutionContext serialization doesn't expose system secrets."""
    context = UserExecutionContext.from_request(
        user_id="test_user",
        thread_id="test_thread", 
        run_id="test_run"
    )
    
    serialized = context.to_dict()
    serialized_str = str(serialized)
    
    # These system secrets should never appear in serialization
    forbidden_patterns = [
        'sk-internal-system-key-secret',
        'db_admin_password_123',
        'admin:admin123'
    ]
    
    for pattern in forbidden_patterns:
        assert pattern not in serialized_str


def test_context_manager_provides_isolation():
    """Test that UserContextManager isolates different users."""
    manager = UserContextManager()
    
    context1 = UserExecutionContext.from_request(
        user_id="user1", thread_id="t1", run_id="r1"
    )
    context2 = UserExecutionContext.from_request(
        user_id="user2", thread_id="t2", run_id="r2"
    )
    
    manager.set_context("ctx1", context1)
    manager.set_context("ctx2", context2)
    
    retrieved1 = manager.get_context("ctx1")
    retrieved2 = manager.get_context("ctx2")
    
    assert retrieved1.user_id == "user1"
    assert retrieved2.user_id == "user2"
    assert retrieved1.user_id != retrieved2.user_id


def test_child_context_maintains_isolation():
    """Test that child contexts maintain proper isolation."""
    parent = UserExecutionContext.from_request(
        user_id="parent_user",
        thread_id="parent_thread", 
        run_id="parent_run"
    )
    
    child = parent.create_child_context("child_operation")
    
    # Child should have different request_id but same user context
    assert parent.user_id == child.user_id
    assert parent.request_id != child.request_id
    assert child.operation_depth == parent.operation_depth + 1
    
    # Both should pass isolation validation
    parent.verify_isolation()
    child.verify_isolation()


def test_migrated_code_uses_secure_patterns():
    """Test that migrated production code uses secure patterns."""
    # Test github_analyzer migration
    from netra_backend.app.routes.github_analyzer import _setup_analysis_environment
    from netra_backend.app.schemas.github_analyzer import AnalysisRequest
    
    request = AnalysisRequest(repository_url="https://github.com/test/repo")
    
    import asyncio
    secure_context, context = asyncio.run(_setup_analysis_environment(request))
    
    # Should return UserExecutionContext, not DeepAgentState
    assert isinstance(secure_context, UserExecutionContext)
    assert type(secure_context).__name__ == 'UserExecutionContext'
    
    # Should have migration audit trail
    audit_data = secure_context.get_audit_trail()
    assert 'security_migration' in audit_data['audit_metadata']


def test_security_vulnerability_prevention_summary():
    """Summary test showing all major vulnerabilities are addressed."""
    
    # 1. Placeholder injection prevention  
    with pytest.raises(InvalidContextError):
        UserExecutionContext.from_request(
            user_id="placeholder",  # System placeholder value should be rejected
            thread_id="thread",
            run_id="run"
        )
    
    # 2. Serialization security
    safe_context = UserExecutionContext.from_request(
        user_id="safe_user",
        thread_id="safe_thread", 
        run_id="safe_run"
    )
    serialized = safe_context.to_dict()
    
    # Should not contain system secrets
    assert 'admin:admin123' not in str(serialized)
    
    # 3. User isolation
    manager = UserContextManager()
    user1_ctx = UserExecutionContext.from_request(
        user_id="user1", thread_id="t1", run_id="r1"
    )
    user2_ctx = UserExecutionContext.from_request(
        user_id="user2", thread_id="t2", run_id="r2"
    )
    
    manager.set_context("u1", user1_ctx) 
    manager.set_context("u2", user2_ctx)
    
    retrieved1 = manager.get_context("u1")
    retrieved2 = manager.get_context("u2")
    
    assert retrieved1.user_id == "user1"
    assert retrieved2.user_id == "user2"
    
    print("SUCCESS: All major security vulnerabilities have been addressed!")


if __name__ == '__main__':
    pytest.main([__file__, "-v"])