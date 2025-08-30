"""Error recovery middleware for handling and recovering from errors."""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from netra_backend.app.logging_config import central_logger

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
        except Exception as e:
            logger.error(f"Error in request processing: {e}")
            raise