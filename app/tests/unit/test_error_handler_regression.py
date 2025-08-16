"""Regression tests for error handler IndexError issue.

Tests to prevent IndexError when logging SQLAlchemy errors.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.exc import DataError, IntegrityError
from app.core.error_handlers import ApiErrorHandler
from app.core.exceptions_database import ErrorCode


def test_error_handler_sqlalchemy_logging():
    """Test that SQLAlchemy errors are logged without IndexError."""
    # Create error handler with mocked logger
    mock_logger = Mock()
    error_handler = ApiErrorHandler()
    error_handler._logger = mock_logger
    
    # Create a SQLAlchemy DataError with complex message
    error_msg = "INSERT INTO userbase VALUES (%(id)s, %(email)s)"
    orig_error = Exception("13 parameters but 14 expected")
    sql_error = DataError(error_msg, None, orig_error)
    
    # Handle the exception
    response = error_handler._handle_sqlalchemy_error(
        sql_error, 
        trace_id="test-trace-123",
        request_id="req-456"
    )
    
    # Verify logger was called correctly with str(exc)
    mock_logger.error.assert_called()
    call_args = mock_logger.error.call_args[0][0]
    assert "Database error:" in call_args
    assert "INSERT INTO userbase" in call_args or "DataError" in call_args
    
    # Verify response structure
    assert response.error_code == ErrorCode.DATABASE_QUERY_FAILED.value
    assert response.trace_id == "test-trace-123"
    assert response.request_id == "req-456"


def test_error_handler_integrity_error():
    """Test handling IntegrityError with duplicate key."""
    error_handler = ApiErrorHandler()
    mock_logger = Mock()
    error_handler._logger = mock_logger
    
    # Create IntegrityError for duplicate key
    error_msg = "duplicate key value violates unique constraint"
    sql_error = IntegrityError(error_msg, None, None)
    
    response = error_handler._handle_sqlalchemy_error(
        sql_error,
        trace_id="test-trace-789",
        request_id="req-789"
    )
    
    # Should detect as constraint violation (duplicate key is a constraint)
    assert response.error_code == ErrorCode.DATABASE_CONSTRAINT_VIOLATION.value
    assert "data constraints" in response.user_message


def test_error_handler_data_error():
    """Test handling DataError for invalid data."""
    error_handler = ApiErrorHandler()
    mock_logger = Mock()
    error_handler._logger = mock_logger
    
    # Create DataError
    error_msg = "invalid input syntax for type"
    sql_error = DataError(error_msg, None, None)
    
    response = error_handler._handle_sqlalchemy_error(
        sql_error,
        trace_id="test-trace-abc",
        request_id="req-abc"
    )
    
    # DataError falls back to general query failed
    assert response.error_code == ErrorCode.DATABASE_QUERY_FAILED.value
    assert "database error" in response.user_message.lower()


def test_error_handler_general_sqlalchemy():
    """Test handling general SQLAlchemy error."""
    error_handler = ApiErrorHandler()
    mock_logger = Mock()
    error_handler._logger = mock_logger
    
    # Create generic SQLAlchemy error
    from sqlalchemy.exc import SQLAlchemyError
    sql_error = SQLAlchemyError("Something went wrong")
    
    response = error_handler._handle_sqlalchemy_error(
        sql_error,
        trace_id="test-trace-xyz", 
        request_id="req-xyz"
    )
    
    # Should use general error code
    assert response.error_code == ErrorCode.DATABASE_QUERY_FAILED.value
    assert response.message == "Database operation failed"
    
    # Verify logger was called with str conversion
    mock_logger.error.assert_called()
    call_args = mock_logger.error.call_args[0][0]
    assert "Database error:" in call_args
    assert "Something went wrong" in call_args or "SQLAlchemyError" in call_args


def test_error_handler_complex_parameter_error():
    """Test error with complex parameter binding message."""
    error_handler = ApiErrorHandler()
    mock_logger = Mock()
    error_handler._logger = mock_logger
    
    # Create error with % formatting that could cause IndexError
    error_msg = "Error at Row: %(row)s, Column: %(column)s, Value: %(value)s"
    orig = Exception("Parameter binding failed")
    sql_error = DataError(error_msg, None, orig)
    
    # Should not raise IndexError
    response = error_handler._handle_sqlalchemy_error(
        sql_error,
        trace_id="test-trace",
        request_id="req-test"
    )
    
    # Verify it handled correctly
    assert response is not None
    assert response.error_code == ErrorCode.DATABASE_QUERY_FAILED.value
    
    # Logger should have been called without error
    mock_logger.error.assert_called()
    assert mock_logger.error.call_count == 1