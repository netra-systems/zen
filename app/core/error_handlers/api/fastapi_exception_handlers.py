"""FastAPI exception handlers.

Provides FastAPI-specific exception handlers that integrate with the
consolidated error handling system.
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.status import (
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.core.exceptions import NetraException, ErrorCode
from .api_error_handler import handle_exception, get_http_status_code


async def netra_exception_handler(request: Request, exc: NetraException) -> JSONResponse:
    """FastAPI exception handler for Netra exceptions."""
    error_response = handle_exception(exc, request)
    code = _convert_code_to_enum(exc.error_details.code)
    status_code = get_http_status_code(code)
    return _create_json_response(status_code, error_response)


async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """FastAPI exception handler for validation errors."""
    error_response = handle_exception(exc, request)
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump()
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """FastAPI exception handler for HTTP exceptions."""
    error_response = handle_exception(exc, request)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """FastAPI exception handler for general exceptions."""
    error_response = handle_exception(exc, request)
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump()
    )


def _convert_code_to_enum(code) -> ErrorCode:
    """Convert error code to ErrorCode enum."""
    if isinstance(code, str):
        return _find_error_code_by_value(code)
    return code


def _find_error_code_by_value(code_value: str) -> ErrorCode:
    """Find ErrorCode enum by string value."""
    try:
        return next(ec for ec in ErrorCode if ec.value == code_value)
    except StopIteration:
        return ErrorCode.INTERNAL_ERROR


def _create_json_response(status_code: int, error_response) -> JSONResponse:
    """Create JSON response for error."""
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump()
    )