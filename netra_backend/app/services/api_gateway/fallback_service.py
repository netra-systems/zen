"""API Gateway Fallback Service - handles circuit breaker fallback responses."""

import asyncio
from typing import Any, Dict, Optional

from fastapi import Request, Response


class ApiFallbackService:
    """Service to handle fallback responses when endpoints are circuit-broken."""
    
    def __init__(self):
        self.default_fallback_response = {
            "error": "Service temporarily unavailable",
            "message": "The service is currently experiencing issues. Please try again later.",
            "status": "circuit_breaker_open"
        }
    
    async def get_fallback_response(
        self, 
        endpoint: str, 
        request: Optional[Request] = None,
        circuit_breaker_state: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get appropriate fallback response for the given endpoint."""
        return {
            **self.default_fallback_response,
            "endpoint": endpoint,
            "circuit_breaker_state": circuit_breaker_state or "open"
        }
    
    async def create_fallback_response(
        self,
        endpoint: str,
        status_code: int = 503,
        **kwargs
    ) -> Response:
        """Create a FastAPI Response object for fallback."""
        fallback_data = await self.get_fallback_response(endpoint, **kwargs)
        return Response(
            content=str(fallback_data),
            status_code=status_code,
            media_type="application/json"
        )