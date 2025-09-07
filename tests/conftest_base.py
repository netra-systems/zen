"""
Core test fixtures and basic setup for the test suite.

This module contains the essential fixtures needed by most tests:
- Event loop management
- Basic environment setup
- Common test data
- User context fixtures

Memory Impact: LOW - Core fixtures use minimal memory allocation
"""
import asyncio
import os
import sys
import uuid
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime, timezone

import pytest

# Add project root for imports
from shared.isolated_environment import get_env
from test_framework.environment_isolation import (
    isolated_test_env,
    ensure_test_isolation,
    validate_test_environment
)

# CRITICAL: Do NOT import heavy backend modules at module level
# This causes Docker to crash on Windows during pytest collection
# These will be imported lazily when needed inside fixtures

# Memory profiling decorator
def memory_profile(description: str = ""):
    """Decorator to track memory usage of fixtures."""
    def decorator(func):
        func._memory_description = description
        func._memory_impact = "LOW"  # Default, can be overridden
        return func
    return decorator

# =============================================================================
# CORE ENVIRONMENT SETUP
# Memory Impact: MINIMAL - Just environment variable setup
# =============================================================================

# Set up isolated test environment if we're running tests
if "pytest" in sys.modules or get_env().get("PYTEST_CURRENT_TEST"):
    # Ensure test isolation is enabled
    ensure_test_isolation()

# Re-export test environment fixtures for convenience
__all__ = ['isolated_test_env']

# Enable pytest-asyncio plugin
pytest_plugins = ["pytest_asyncio"]

# =============================================================================
# EVENT LOOP MANAGEMENT
# Memory Impact: LOW - Single event loop policy setup
# =============================================================================

@pytest.fixture(scope="session")
@memory_profile("Consistent event loop policy for all tests")
def event_loop_policy():
    """Set consistent event loop policy for all tests.
    
    Memory Impact: LOW - Sets event loop policy once per session
    """
    import asyncio
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        # Use SelectorEventLoop on Windows for better compatibility
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.get_event_loop_policy()

# =============================================================================
# COMMON TEST DATA FIXTURES
# Memory Impact: MINIMAL - Small static data objects
# =============================================================================

@pytest.fixture
@memory_profile("Basic test user data for all services")
def common_test_user():
    """Common test user data for all services.
    
    Memory Impact: MINIMAL - Single dict with user data
    """
    return {
        "id": "test-user-123",
        "email": "test@example.com", 
        "name": "Test User",
        "is_active": True,
        "is_superuser": False
    }

@pytest.fixture
@memory_profile("Basic sample data for tests")
def sample_data():
    """Basic sample data for tests.
    
    Memory Impact: MINIMAL - Small test data dict
    """
    return {"test": "data", "status": "active"}

# =============================================================================
# USER CONTEXT FIXTURES
# Memory Impact: LOW - Small context objects with UUIDs
# =============================================================================

# Mock User class if app imports fail
try:
    from netra_backend.app.schemas import User
except ImportError:
    class User:
        def __init__(self, id, email, is_active=True, is_superuser=False):
            self.id = id
            self.email = email
            self.is_active = is_active
            self.is_superuser = is_superuser

@pytest.fixture
@memory_profile("Basic test user instance")
def test_user():
    """Create basic test user instance.
    
    Memory Impact: LOW - Single User object
    """
    return User(
        id="test-user-id", 
        email="test@example.com", 
        is_active=True, 
        is_superuser=False
    )

@pytest.fixture
@memory_profile("Enhanced test user with unique identifiers")
def test_user_v2():
    """Enhanced test user fixture with unique identifiers.
    
    Memory Impact: LOW - Single User object with UUID
    """
    return User(
        id=f"test_user_{uuid.uuid4().hex[:8]}", 
        email=f"test_{uuid.uuid4().hex[:8]}@example.com", 
        is_active=True, 
        is_superuser=False
    )

# =============================================================================
# PHASE 0 USER EXECUTION CONTEXT
# Memory Impact: LOW - Context objects with proper validation
# =============================================================================

# Try to import Phase 0 components
try:
    from netra_backend.app.models.user_execution_context import UserExecutionContext
    PHASE0_COMPONENTS_AVAILABLE = True
except ImportError:
    # Mock Phase 0 components if not available
    PHASE0_COMPONENTS_AVAILABLE = False
    
    class UserExecutionContext:
        def __init__(self, user_id, thread_id, run_id, request_id, websocket_connection_id=None):
            self.user_id = user_id
            self.thread_id = thread_id
            self.run_id = run_id
            self.request_id = request_id
            self.websocket_connection_id = websocket_connection_id

@pytest.fixture
@memory_profile("Valid UserExecutionContext with realistic IDs")
def valid_user_execution_context():
    """Create valid UserExecutionContext with realistic IDs (no placeholders).
    
    This fixture provides proper UserExecutionContext instances that pass
    validation and support Phase 0 migration patterns.
    
    Memory Impact: LOW - Single context object with UUID strings
    
    Returns:
        UserExecutionContext: Validated context with real IDs
    """
    return UserExecutionContext(
        user_id=f"test_user_{uuid.uuid4().hex[:8]}",
        thread_id=f"thread_{uuid.uuid4().hex[:8]}",
        run_id=f"run_{uuid.uuid4().hex[:8]}",
        request_id=f"req_{uuid.uuid4().hex[:8]}",
        websocket_connection_id=f"ws_{uuid.uuid4().hex[:8]}" if PHASE0_COMPONENTS_AVAILABLE else None
    )

@pytest.fixture
@memory_profile("Multiple isolated user contexts for concurrent testing")
async def concurrent_user_contexts():
    """Create multiple isolated user contexts for concurrent testing.
    
    This fixture provides multiple UserExecutionContext instances with
    different user IDs for testing concurrent user isolation.
    
    Memory Impact: LOW - List of 3 context objects
    
    Returns:
        List[UserExecutionContext]: List of isolated user contexts
    """
    contexts = []
    for i in range(3):  # Create 3 concurrent users
        context = UserExecutionContext(
            user_id=f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread_{i}_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{i}_{uuid.uuid4().hex[:8]}",
            request_id=f"req_{i}_{uuid.uuid4().hex[:8]}",
            websocket_connection_id=f"ws_{i}_{uuid.uuid4().hex[:8]}" if PHASE0_COMPONENTS_AVAILABLE else None
        )
        contexts.append(context)
    
    return contexts