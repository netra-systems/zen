"""
LLM manager service for coordinating language model operations.
Manages model lifecycle, requests, and integration with other services.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from netra_backend.app.services.cost_calculator import BudgetManager, create_budget_manager

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
    
    def __init__(self, daily_budget: Optional[Decimal] = None):
        self.active_requests: Dict[str, LLMRequest] = {}
        self.model_metrics: Dict[str, ModelMetrics] = {}
        self.default_model = "gpt-3.5-turbo"
        self.initialized = False
        self.budget_manager: BudgetManager = create_budget_manager(daily_budget)
        self.cost_limit_enforced = True  # Flag to enable/disable cost enforcement
    
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
            
            # Estimate token usage for cost checking
            # More aggressive estimation for expensive models
            token_multiplier = 3 if "gpt-4" in request.model else 2
            estimated_tokens = len(request.prompt.split()) * token_multiplier
            
            # CRITICAL: Enforce cost limits before processing
            if self.cost_limit_enforced:
                # Block if tokens exceed reasonable limit (e.g., 5000 tokens for single request)
                max_tokens_per_request = 5000
                if estimated_tokens > max_tokens_per_request:
                    request.status = RequestStatus.FAILED
                    request.error = f"Cost limit exceeded - request with {estimated_tokens} estimated tokens blocked to prevent unbounded API costs (max: {max_tokens_per_request})"
                    request.completed_at = datetime.utcnow()
                    logger.warning(f"Request {request_id} blocked due to cost limit enforcement")
                    return request
                
                if not self._check_cost_limit(request.model, estimated_tokens):
                    request.status = RequestStatus.FAILED
                    request.error = "Cost limit exceeded - daily budget exhausted"
                    request.completed_at = datetime.utcnow()
                    logger.warning(f"Request {request_id} blocked due to budget exhaustion")
                    return request
            
            # Simulate LLM processing
            await asyncio.sleep(0.1)  # Simulate processing time
            
            # Mock response generation
            response = f"Response to: {request.prompt[:50]}..."
            token_usage = {
                "input_tokens": len(request.prompt.split()),
                "output_tokens": len(response.split()),
                "total_tokens": len(request.prompt.split()) + len(response.split())
            }
            
            # Record actual usage after successful processing
            if self.cost_limit_enforced:
                self._record_usage(request.model, token_usage["total_tokens"])
            
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
    
    def _check_cost_limit(self, model: str, estimated_tokens: int) -> bool:
        """
        Check if processing request would exceed cost limits.
        
        Args:
            model: Model to use
            estimated_tokens: Estimated token count
            
        Returns:
            True if within limits, False if would exceed
        """
        from netra_backend.app.schemas.llm_config_types import LLMProvider
        from netra_backend.app.services.cost_calculator import TokenUsage
        
        # Map model to provider (simplified)
        provider = LLMProvider.OPENAI if "gpt" in model else LLMProvider.ANTHROPIC
        
        # Create token usage estimate
        usage = TokenUsage(
            input_tokens=estimated_tokens // 2,
            output_tokens=estimated_tokens // 2,
            total_tokens=estimated_tokens
        )
        
        # Check if this would exceed budget
        return self.budget_manager.check_budget_impact(usage, provider, model)
    
    def _record_usage(self, model: str, actual_tokens: int) -> None:
        """
        Record actual usage after processing.
        
        Args:
            model: Model used
            actual_tokens: Actual token count
        """
        from netra_backend.app.schemas.llm_config_types import LLMProvider
        from netra_backend.app.services.cost_calculator import TokenUsage
        
        # Map model to provider
        provider = LLMProvider.OPENAI if "gpt" in model else LLMProvider.ANTHROPIC
        
        # Create token usage
        usage = TokenUsage(
            input_tokens=actual_tokens // 2,
            output_tokens=actual_tokens // 2,
            total_tokens=actual_tokens
        )
        
        # Record the usage
        cost = self.budget_manager.record_usage(usage, provider, model)
        logger.debug(f"Recorded usage for {model}: {actual_tokens} tokens, cost: ${cost:.4f}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of LLM manager."""
        active_count = len([r for r in self.active_requests.values() 
                           if r.status in [RequestStatus.PENDING, RequestStatus.PROCESSING]])
        
        return {
            "initialized": self.initialized,
            "default_model": self.default_model,
            "active_requests": active_count,
            "total_requests": len(self.active_requests),
            "available_models": list(self.model_metrics.keys()),
            "cost_limit_enforced": self.cost_limit_enforced,
            "remaining_budget": float(self.budget_manager.get_remaining_budget()),
            "daily_budget": float(self.budget_manager.daily_budget)
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