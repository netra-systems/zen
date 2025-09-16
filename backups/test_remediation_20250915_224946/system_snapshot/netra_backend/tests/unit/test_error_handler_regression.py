"""Regression tests for error handler IndexError issue.

Tests to prevent IndexError when logging SQLAlchemy errors.
"""

import sys
from pathlib import Path
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment

import pytest
from sqlalchemy.exc import DataError, IntegrityError

from netra_backend.app.core.unified_error_handler import api_error_handler as ApiErrorHandler
from netra_backend.app.core.exceptions_database import ErrorCode


def test_error_handler_sqlalchemy_logging():
    """Test that SQLAlchemy errors are logged without IndexError."""
    # Create error handler 
    error_handler = ApiErrorHandler()
    
    # Create a SQLAlchemy DataError with complex message
    error_msg = "INSERT INTO userbase VALUES (%(id)s, %(email)s)"
    orig_error = Exception("13 parameters but 14 expected")
    sql_error = DataError(error_msg, None, orig_error)
    
    # Handle the exception using public API - should not raise IndexError
    response = error_handler.handle_exception(
        sql_error, 
        trace_id="test-trace-123"
    )
    
    # Verify response structure
    assert response is not None
    assert response.error_code == ErrorCode.DATABASE_ERROR.value
    assert response.trace_id == "test-trace-123"


def test_error_handler_integrity_error():
    """Test handling IntegrityError with duplicate key."""
    error_handler = ApiErrorHandler()
    
    # Create IntegrityError for duplicate key
    error_msg = "duplicate key value violates unique constraint"
    sql_error = IntegrityError(error_msg, None, None)
    
    response = error_handler.handle_exception(
        sql_error,
        trace_id="test-trace-789"
    )
    
    # Should detect as database error
    assert response.error_code == ErrorCode.DATABASE_ERROR.value
    assert "error occurred" in response.user_message.lower()


def test_error_handler_data_error():
    """Test handling DataError for invalid data."""
    error_handler = ApiErrorHandler()
    
    # Create DataError
    error_msg = "invalid input syntax for type"
    sql_error = DataError(error_msg, None, None)
    
    response = error_handler.handle_exception(
        sql_error,
        trace_id="test-trace-abc"
    )
    
    # DataError falls back to database error
    assert response.error_code == ErrorCode.DATABASE_ERROR.value
    assert "error occurred" in response.user_message.lower()


def test_error_handler_general_sqlalchemy():
    """Test handling general SQLAlchemy error."""
    error_handler = ApiErrorHandler()
    
    # Create generic SQLAlchemy error
    from sqlalchemy.exc import SQLAlchemyError
    sql_error = SQLAlchemyError("Something went wrong")
    
    response = error_handler.handle_exception(
        sql_error,
        trace_id="test-trace-xyz"
    )
    
    # Should use general error code
    assert response.error_code == ErrorCode.DATABASE_ERROR.value
    assert "operation" in response.message.lower() or "error" in response.message.lower()


def test_error_handler_complex_parameter_error():
    """Test error with complex parameter binding message."""
    error_handler = ApiErrorHandler()
    
    # Create error with % formatting that could cause IndexError
    error_msg = "Error at Row: %(row)s, Column: %(column)s, Value: %(value)s"
    orig = Exception("Parameter binding failed")
    sql_error = DataError(error_msg, None, orig)
    
    # Should not raise IndexError
    response = error_handler.handle_exception(
        sql_error,
        trace_id="test-trace"
    )
    
    # Verify it handled correctly
    assert response is not None
    assert response.error_code == ErrorCode.DATABASE_ERROR.value