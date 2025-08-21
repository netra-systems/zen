"""Transaction management middleware for automatic transaction handling.

Provides automatic transaction management for database operations
with proper rollback and commit handling.
"""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from netra_backend.app.services.transaction_manager import transaction_manager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TransactionMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic transaction management."""
    
    def __init__(self, app):
        """Initialize transaction middleware."""
        super().__init__(app)
        self.transaction_manager = transaction_manager
        self._setup_transactional_paths()
    
    def _setup_transactional_paths(self) -> None:
        """Setup paths that require transaction management."""
        self.transactional_paths = {
            '/api/corpus',
            '/api/synthetic-data',
            '/api/admin',
            '/api/generation'
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with transaction management."""
        if not self._requires_transaction(request):
            return await call_next(request)
        return await self._process_with_transaction(request, call_next)
    
    def _requires_transaction(self, request: Request) -> bool:
        """Check if request requires transaction management."""
        path = request.url.path
        needs_transaction = any(
            path.startswith(tx_path) for tx_path in self.transactional_paths
        )
        return needs_transaction and request.method != 'GET'
    
    async def _process_with_transaction(self, request: Request, call_next: Callable) -> Response:
        """Process request within a database transaction."""
        try:
            return await self._execute_request_in_transaction(request, call_next)
        except Exception as error:
            logger.error(f"Transaction failed: {error}")
            raise error

    async def _execute_request_in_transaction(self, request: Request, call_next: Callable) -> Response:
        """Execute request within transaction context."""
        async with self.transaction_manager.transaction() as transaction_id:
            request.state.transaction_id = transaction_id
            response = await call_next(request)
            response.headers["X-Transaction-ID"] = transaction_id
            return response