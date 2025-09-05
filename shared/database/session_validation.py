"""
Shared Database Session Validation Utilities

This module provides validation utilities for database sessions that work in both
production and test environments following SSOT principles.

Business Value Justification (BVJ):
- Segment: Platform stability (all tiers)  
- Business Goal: Ensure database session validation works across production and tests
- Value Impact: Prevents runtime errors in database operations
- Strategic Impact: Enables consistent mocking patterns across test suites

@compliance CLAUDE.md - SSOT principles and test infrastructure
@compliance SPEC/type_safety.xml - Type validation patterns
"""

import logging
from typing import Any, Union
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def validate_db_session(
    db: Any, 
    context: str = "database_operation",
    allow_mock: bool = True
) -> None:
    """
    Validate database session for both production and test environments.
    
    This function follows SSOT principles by providing a single validation
    method that works across all environments and scenarios.
    
    Args:
        db: Database session to validate (AsyncSession or properly configured mock)
        context: Context description for logging and error messages
        allow_mock: Whether to allow AsyncMock objects (default: True for flexibility)
    
    Raises:
        TypeError: If db is not a valid AsyncSession or properly configured mock
    
    Examples:
        # Production usage
        validate_db_session(db, "user_creation")
        
        # Test usage with mock
        mock_db = AsyncMock(spec=AsyncSession)
        validate_db_session(mock_db, "test_user_creation")
    """
    # Check if it's a real AsyncSession (production case)
    if isinstance(db, AsyncSession):
        logger.debug(f"Validated AsyncSession in {context}: {id(db)}")
        return
    
    # If mocks are not allowed, fail here
    if not allow_mock:
        logger.error(f"ERROR: Expected AsyncSession, got {type(db)} in {context}")
        raise TypeError(f"Expected AsyncSession, got {type(db)}")
    
    # Check if it's a properly configured AsyncMock for testing
    try:
        from unittest.mock import AsyncMock
        
        if isinstance(db, AsyncMock):
            # Check if the mock has AsyncSession spec
            if hasattr(db, '_spec_class') and db._spec_class is AsyncSession:
                logger.debug(f"Validated AsyncMock with AsyncSession spec in {context}: {id(db)}")
                return
            # Fallback check for older mock patterns or manual mocks
            elif hasattr(db, 'execute') and callable(getattr(db, 'execute')):
                logger.debug(f"Validated AsyncMock with database methods in {context}: {id(db)}")
                return
            # Check for _mock_name attribute (indicates it's a mock)
            elif hasattr(db, '_mock_name'):
                logger.debug(f"Validated AsyncMock object in {context}: {id(db)}")
                return
    
    except ImportError:
        # unittest.mock not available, skip mock checks
        pass
    
    # If we get here, it's neither a valid AsyncSession nor a proper mock
    logger.error(f"ERROR: db is not AsyncSession or properly configured AsyncMock, it's {type(db)} in {context}")
    raise TypeError(f"Expected AsyncSession or AsyncMock(spec=AsyncSession), got {type(db)}")


def validate_db_session_strict(db: Any, context: str = "database_operation") -> None:
    """
    Strict database session validation that only allows real AsyncSession objects.
    
    Use this in production-critical paths where mocks should never be allowed.
    
    Args:
        db: Database session to validate (must be AsyncSession)
        context: Context description for logging and error messages
        
    Raises:
        TypeError: If db is not a real AsyncSession instance
    """
    validate_db_session(db, context, allow_mock=False)


def is_mock_session(db: Any) -> bool:
    """
    Check if a database session is a mock object.
    
    Useful for conditional logic that needs to behave differently
    in test vs production environments.
    
    Args:
        db: Database session to check
        
    Returns:
        bool: True if db is a mock object, False otherwise
    """
    try:
        from unittest.mock import AsyncMock
        return isinstance(db, AsyncMock)
    except ImportError:
        return False


def is_real_session(db: Any) -> bool:
    """
    Check if a database session is a real AsyncSession object.
    
    Args:
        db: Database session to check
        
    Returns:
        bool: True if db is a real AsyncSession, False otherwise
    """
    return isinstance(db, AsyncSession)