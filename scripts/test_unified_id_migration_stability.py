#!/usr/bin/env python3
"""
Unified ID Manager Migration Stability Validation

Tests to prove that the unified ID manager migration changes have maintained
system stability and not introduced breaking changes.
"""

import sys
import pytest
import uuid
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def test_unified_id_manager_core_functionality():
    """Test that core UnifiedIDManager functionality works after migration."""
    from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
    
    manager = UnifiedIDManager()
    
    # Test basic ID generation
    user_id = manager.generate_id(IDType.USER)
    assert user_id is not None
    assert "user" in user_id
    
    # Test thread ID generation
    thread_id = manager.generate_id(IDType.THREAD)
    assert thread_id is not None
    assert "thread" in thread_id
    
    # Test run ID generation with class method
    run_id = UnifiedIDManager.generate_run_id(thread_id)
    assert run_id is not None
    assert "run" in run_id
    
    # Test thread ID extraction
    extracted_thread_id = UnifiedIDManager.extract_thread_id(run_id)
    assert extracted_thread_id is not None


def test_websocket_id_generation_stability():
    """Test that WebSocket ID generation works after migration."""
    from netra_backend.app.websocket_core.utils import generate_connection_id, generate_message_id
    from shared.types.execution_types import UserID
    
    # Test connection ID generation
    user_id = UserID("test_user_123")
    connection_id = generate_connection_id(user_id)
    assert connection_id is not None
    assert str(connection_id).startswith("conn_")
    
    # Test message ID generation
    message_id = generate_message_id()
    assert message_id is not None
    assert len(message_id) > 0


def test_auth_service_id_generation_stability():
    """Test that auth service ID generation works after migration."""
    from auth_service.auth_core.unified_auth_interface import UnifiedAuthInterface
    
    auth_interface = UnifiedAuthInterface()
    
    # Test session creation
    session_id = auth_interface.create_session("test_user", {})
    assert session_id is not None
    assert len(session_id) > 0
    
    # Test secure nonce generation
    nonce = auth_interface.generate_secure_nonce()
    assert nonce is not None
    assert len(nonce) > 0


def test_database_model_id_generation_stability():
    """Test that database models can generate IDs properly after migration."""
    from netra_backend.app.models.agent_execution import AgentExecution
    from auth_service.auth_core.database.models import AuthUser, AuthSession
    
    # Test AgentExecution ID generation
    execution = AgentExecution()
    execution.user_id = "test_user_123"
    execution.agent_id = "test_agent_456"
    assert execution.id is not None
    
    # Test AuthUser ID generation
    auth_user = AuthUser()
    auth_user.email = "test@example.com"
    assert auth_user.id is not None
    
    # Test AuthSession ID generation  
    auth_session = AuthSession()
    auth_session.user_id = "test_user_123"
    assert auth_session.id is not None


def test_unified_id_generator_availability():
    """Test that shared.id_generation.unified_id_generator is available and working."""
    from shared.id_generation.unified_id_generator import UnifiedIdGenerator
    
    # Test basic ID generation
    base_id = UnifiedIdGenerator.generate_base_id("test")
    assert base_id is not None
    assert "test" in base_id
    
    # Test WebSocket connection ID generation
    websocket_id = UnifiedIdGenerator.generate_websocket_connection_id("user_123")
    assert websocket_id is not None
    assert "ws_conn" in websocket_id
    
    # Test session ID generation
    session_id = UnifiedIdGenerator.generate_session_id("user_123", "auth")
    assert session_id is not None
    assert "session" in session_id


def test_backwards_compatibility():
    """Test that existing code patterns still work after migration."""
    from netra_backend.app.core.unified_id_manager import (
        generate_user_id, generate_session_id, generate_request_id,
        generate_agent_id, generate_websocket_id, generate_execution_id,
        generate_thread_id, is_valid_id, is_valid_id_format
    )
    
    # Test convenience functions still work
    user_id = generate_user_id()
    assert user_id is not None
    
    session_id = generate_session_id()
    assert session_id is not None
    
    request_id = generate_request_id()
    assert request_id is not None
    
    # Test validation functions
    assert is_valid_id_format(user_id)
    assert is_valid_id_format(str(uuid.uuid4()))  # Should still accept UUIDs
    
    # Test invalid formats
    assert not is_valid_id_format("")
    assert not is_valid_id_format("invalid")


def test_multi_user_isolation():
    """Test that ID generation maintains multi-user isolation."""
    from shared.id_generation.unified_id_generator import UnifiedIdGenerator
    
    # Generate IDs for different users
    user1_context = UnifiedIdGenerator.generate_websocket_connection_id("user_1")
    user2_context = UnifiedIdGenerator.generate_websocket_connection_id("user_2")
    
    # IDs should be different
    assert user1_context != user2_context
    
    # IDs should contain user identifiers
    assert "user_1" in user1_context
    assert "user_2" in user2_context
    
    # Generate multiple IDs for same user - should be unique
    user1_id1 = UnifiedIdGenerator.generate_base_id("test", True, 8)
    user1_id2 = UnifiedIdGenerator.generate_base_id("test", True, 8)
    
    assert user1_id1 != user1_id2


def test_performance_regression():
    """Test that ID generation performance hasn't regressed significantly."""
    import time
    from netra_backend.app.core.unified_id_manager import generate_user_id
    
    # Time ID generation
    start_time = time.time()
    
    # Generate 1000 IDs
    for _ in range(1000):
        user_id = generate_user_id()
        assert user_id is not None
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Should complete within reasonable time (less than 1 second for 1000 IDs)
    assert duration < 1.0, f"ID generation took too long: {duration:.3f}s for 1000 IDs"


def test_system_imports():
    """Test that all imports work correctly after migration."""
    # Test UnifiedIDManager imports
    from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
    
    # Test shared UnifiedIdGenerator imports
    from shared.id_generation.unified_id_generator import UnifiedIdGenerator
    
    # Test WebSocket utils imports
    from netra_backend.app.websocket_core.utils import generate_connection_id
    
    # Test auth interface imports
    from auth_service.auth_core.unified_auth_interface import UnifiedAuthInterface
    
    # Test model imports
    from netra_backend.app.models.agent_execution import AgentExecution
    from auth_service.auth_core.database.models import AuthUser
    
    # All imports successful
    assert True


if __name__ == "__main__":
    print("Running Unified ID Manager Migration Stability Tests...")
    
    tests = [
        test_unified_id_manager_core_functionality,
        test_websocket_id_generation_stability,
        test_auth_service_id_generation_stability,
        test_database_model_id_generation_stability,
        test_unified_id_generator_availability,
        test_backwards_compatibility,
        test_multi_user_isolation,
        test_performance_regression,
        test_system_imports,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            print(f"Running {test.__name__}...")
            test()
            print(f"[PASS] {test.__name__} PASSED")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__} FAILED: {e}")
            failed += 1
    
    print(f"\n=== STABILITY TEST RESULTS ===")
    print(f"PASSED: {passed}")
    print(f"FAILED: {failed}")
    print(f"TOTAL:  {passed + failed}")
    
    if failed == 0:
        print("\n[SUCCESS] ALL STABILITY TESTS PASSED - Migration maintained system stability!")
        sys.exit(0)
    else:
        print(f"\n[WARNING] {failed} stability tests failed - Migration may have introduced issues")
        sys.exit(1)