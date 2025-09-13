"""Error recovery middleware for handling and recovering from errors."""

from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.exc import OperationalError, DatabaseError
from netra_backend.app.logging_config import central_logger
from shared.isolated_environment import get_env
import os

logger = central_logger.get_logger(__name__)


class ErrorRecoveryMiddleware(BaseHTTPMiddleware):
    """Middleware for error recovery and handling."""
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process the request and handle any errors."""
        try:
            response = await call_next(request)
            return response
        except (OperationalError, DatabaseError) as e:
            logger.error(f"Database error in request processing: {e}")
            return JSONResponse(
                status_code=503,
                content={"error": "Service temporarily unavailable due to database issues"}
            )
        except Exception as e:
            logger.error(f"Error in request processing: {e}")
            # Don't expose error details in production
            if get_env('ENVIRONMENT') == 'production':
                return JSONResponse(
                    status_code=500,
                    content={"error": "Internal server error"}
                )
            else:
                return JSONResponse(
                    status_code=500,
                    content={"error": "Internal server error", "detail": str(e)}
                )