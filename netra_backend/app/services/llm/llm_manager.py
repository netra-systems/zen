"""
LLM manager service for coordinating language model operations.
Manages model lifecycle, requests, and integration with other services.
"""

from typing import Dict, List, Optional, Any, Union
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class RequestStatus(Enum):
    """Status of LLM requests."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class LLMRequest:
    """Represents an LLM request."""
    id: str
    model: str
    prompt: str
    parameters: Dict[str, Any]
    status: RequestStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    response: Optional[str] = None
    error: Optional[str] = None
    token_usage: Optional[Dict[str, int]] = None


@dataclass
class ModelMetrics:
    """Metrics for model usage."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_tokens: int
    average_latency: float
    error_rate: float


class LLMManager:
    """
    Service for managing LLM operations and coordination.
    Handles request lifecycle, model switching, and performance monitoring.
    """
    
    def __init__(self):
        self.active_requests: Dict[str, LLMRequest] = {}
        self.model_metrics: Dict[str, ModelMetrics] = {}
        self.default_model = "gpt-3.5-turbo"
        self.initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the LLM manager service."""
        try:
            # Initialize model metrics
            self._initialize_metrics()
            self.initialized = True
            logger.info("LLM Manager initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize LLM Manager: {e}")
            return False
    
    def _initialize_metrics(self) -> None:
        """Initialize metrics for available models."""
        models = ["gpt-4", "gpt-3.5-turbo", "claude-3-sonnet", "claude-3-haiku"]
        for model in models:
            self.model_metrics[model] = ModelMetrics(
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                total_tokens=0,
                average_latency=0.0,
                error_rate=0.0
            )
    
    async def create_request(
        self,
        prompt: str,
        model: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new LLM request.
        
        Args:
            prompt: Input prompt
            model: Model to use (optional, uses default if not specified)
            parameters: Additional parameters for the request
            
        Returns:
            Request ID
        """
        if not self.initialized:
            raise RuntimeError("LLM Manager not initialized")
        
        request_id = f"req_{datetime.utcnow().timestamp()}"
        model = model or self.default_model
        parameters = parameters or {}
        
        request = LLMRequest(
            id=request_id,
            model=model,
            prompt=prompt,
            parameters=parameters,
            status=RequestStatus.PENDING,
            created_at=datetime.utcnow()
        )
        
        self.active_requests[request_id] = request
        logger.debug(f"Created LLM request {request_id} for model {model}")
        
        return request_id
    
    async def process_request(self, request_id: str) -> Optional[LLMRequest]:
        """
        Process an LLM request.
        
        Args:
            request_id: ID of request to process
            
        Returns:
            Updated request object or None if not found
        """
        if request_id not in self.active_requests:
            logger.error(f"Request {request_id} not found")
            return None
        
        request = self.active_requests[request_id]
        
        try:
            # Update status
            request.status = RequestStatus.PROCESSING
            
            # Simulate LLM processing
            await asyncio.sleep(0.1)  # Simulate processing time
            
            # Mock response generation
            response = f"Response to: {request.prompt[:50]}..."
            token_usage = {
                "input_tokens": len(request.prompt.split()),
                "output_tokens": len(response.split()),
                "total_tokens": len(request.prompt.split()) + len(response.split())
            }
            
            # Update request
            request.status = RequestStatus.COMPLETED
            request.completed_at = datetime.utcnow()
            request.response = response
            request.token_usage = token_usage
            
            # Update metrics
            self._update_metrics(request)
            
            logger.debug(f"Completed request {request_id}")
            return request
            
        except Exception as e:
            logger.error(f"Failed to process request {request_id}: {e}")
            request.status = RequestStatus.FAILED
            request.error = str(e)
            request.completed_at = datetime.utcnow()
            
            # Update metrics
            self._update_metrics(request)
            
            return request
    
    def _update_metrics(self, request: LLMRequest) -> None:
        """Update metrics for the model used in the request."""
        model = request.model
        if model not in self.model_metrics:
            return
        
        metrics = self.model_metrics[model]
        metrics.total_requests += 1
        
        if request.status == RequestStatus.COMPLETED:
            metrics.successful_requests += 1
            if request.token_usage:
                metrics.total_tokens += request.token_usage["total_tokens"]
        elif request.status == RequestStatus.FAILED:
            metrics.failed_requests += 1
        
        # Update error rate
        metrics.error_rate = metrics.failed_requests / metrics.total_requests
        
        # Update average latency (simplified calculation)
        if request.completed_at and request.created_at:
            latency = (request.completed_at - request.created_at).total_seconds()
            metrics.average_latency = (
                (metrics.average_latency * (metrics.total_requests - 1) + latency) /
                metrics.total_requests
            )
    
    async def get_request_status(self, request_id: str) -> Optional[RequestStatus]:
        """Get the status of a request."""
        request = self.active_requests.get(request_id)
        return request.status if request else None
    
    async def get_request(self, request_id: str) -> Optional[LLMRequest]:
        """Get a request by ID."""
        return self.active_requests.get(request_id)
    
    async def cancel_request(self, request_id: str) -> bool:
        """Cancel a pending or processing request."""
        request = self.active_requests.get(request_id)
        if not request:
            return False
        
        if request.status in [RequestStatus.PENDING, RequestStatus.PROCESSING]:
            request.status = RequestStatus.CANCELLED
            request.completed_at = datetime.utcnow()
            logger.info(f"Cancelled request {request_id}")
            return True
        
        return False
    
    async def get_model_metrics(self, model: str) -> Optional[ModelMetrics]:
        """Get metrics for a specific model."""
        return self.model_metrics.get(model)
    
    async def get_all_metrics(self) -> Dict[str, ModelMetrics]:
        """Get metrics for all models."""
        return self.model_metrics.copy()
    
    async def switch_default_model(self, model: str) -> bool:
        """Switch the default model."""
        if model in self.model_metrics:
            old_model = self.default_model
            self.default_model = model
            logger.info(f"Switched default model from {old_model} to {model}")
            return True
        
        logger.error(f"Model {model} not available")
        return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of LLM manager."""
        active_count = len([r for r in self.active_requests.values() 
                           if r.status in [RequestStatus.PENDING, RequestStatus.PROCESSING]])
        
        return {
            "initialized": self.initialized,
            "default_model": self.default_model,
            "active_requests": active_count,
            "total_requests": len(self.active_requests),
            "available_models": list(self.model_metrics.keys())
        }
    
    async def cleanup_completed_requests(self, max_age_hours: int = 24) -> int:
        """Clean up old completed requests."""
        cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        
        to_remove = []
        for request_id, request in self.active_requests.items():
            if (request.status in [RequestStatus.COMPLETED, RequestStatus.FAILED, RequestStatus.CANCELLED] and
                request.created_at.timestamp() < cutoff_time):
                to_remove.append(request_id)
        
        for request_id in to_remove:
            del self.active_requests[request_id]
        
        logger.info(f"Cleaned up {len(to_remove)} old requests")
        return len(to_remove)


# Global instance
llm_manager = LLMManager()