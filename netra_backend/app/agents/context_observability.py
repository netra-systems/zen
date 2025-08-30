"""Context Observability Module for Agent Token Management.

Provides observability for agent context windows, token counting,
and prompt size management.
"""

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.metrics.agent_metrics import AgentMetrics

logger = central_logger.get_logger(__name__)


@dataclass
class ContextMetrics:
    """Metrics for agent context tracking."""
    agent_name: str
    run_id: str
    context_size_bytes: int
    context_keys: int
    estimated_tokens: int
    max_tokens_allowed: int
    context_window_limit: int
    timestamp: datetime = field(default_factory=datetime.now)
    largest_key: Optional[str] = None
    usage_percentage: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "agent_name": self.agent_name,
            "run_id": self.run_id,
            "context_size_bytes": self.context_size_bytes,
            "context_keys": self.context_keys,
            "estimated_tokens": self.estimated_tokens,
            "max_tokens_allowed": self.max_tokens_allowed,
            "context_window_limit": self.context_window_limit,
            "timestamp": self.timestamp.isoformat(),
            "largest_key": self.largest_key,
            "usage_percentage": self.usage_percentage
        }


class ContextObservabilityMixin:
    """Mixin for context observability in agents."""
    
    # Model context limits (tokens)
    CONTEXT_LIMITS = {
        "claude-3-opus": 200000,
        "claude-3-sonnet": 200000,
        "claude-3-haiku": 200000,
        "gpt-4": 128000,
        "gpt-3.5-turbo": 16385,
        "default": 128000
    }
    
    # Warning thresholds
    CONTEXT_WARNING_THRESHOLD = 0.75  # Warn at 75% usage
    CONTEXT_ERROR_THRESHOLD = 0.90    # Error at 90% usage
    
    def _estimate_token_count(self, text: str) -> int:
        """Estimate token count for text.
        
        Uses approximation of 4 characters per token for English text.
        """
        if not text:
            return 0
        
        # Handle different types
        if isinstance(text, (dict, list)):
            text = json.dumps(text)
        
        # Rough estimation: ~4 chars per token for English
        # Adjust for special characters and structure
        char_count = len(str(text))
        base_estimate = char_count / 4
        
        # Add overhead for JSON structure
        if "{" in str(text) or "[" in str(text):
            base_estimate *= 1.1
        
        return int(base_estimate)
    
    def _get_context_metrics(self) -> Dict[str, Any]:
        """Get metrics about current context."""
        if not hasattr(self, 'context'):
            return {}
        
        context = self.context
        total_size = sys.getsizeof(json.dumps(context) if isinstance(context, dict) else str(context))
        
        # Find largest key if context is dict
        largest_key = None
        largest_size = 0
        
        if isinstance(context, dict):
            for key, value in context.items():
                size = sys.getsizeof(json.dumps(value) if not isinstance(value, str) else value)
                if size > largest_size:
                    largest_size = size
                    largest_key = key
        
        return {
            "total_size_bytes": total_size,
            "num_keys": len(context) if isinstance(context, dict) else 1,
            "largest_key": largest_key,
            "largest_key_size": largest_size,
            "estimated_tokens": self._estimate_token_count(context)
        }
    
    def _collect_context_metrics(self) -> ContextMetrics:
        """Collect comprehensive context metrics."""
        metrics_data = self._get_context_metrics()
        
        # Get model limits
        model_name = getattr(self, 'model_name', 'default')
        context_limit = self.CONTEXT_LIMITS.get(model_name, self.CONTEXT_LIMITS['default'])
        
        # Calculate usage
        estimated_tokens = metrics_data.get('estimated_tokens', 0)
        usage_percentage = (estimated_tokens / context_limit) * 100 if context_limit > 0 else 0
        
        return ContextMetrics(
            agent_name=getattr(self, 'name', 'unknown'),
            run_id=getattr(self, 'run_id', 'unknown'),
            context_size_bytes=metrics_data.get('total_size_bytes', 0),
            context_keys=metrics_data.get('num_keys', 0),
            estimated_tokens=estimated_tokens,
            max_tokens_allowed=getattr(self, 'max_tokens', 4096),
            context_window_limit=context_limit,
            largest_key=metrics_data.get('largest_key'),
            usage_percentage=usage_percentage
        )
    
    def _report_context_metrics(self) -> None:
        """Report context metrics to monitoring system."""
        try:
            metrics = self._collect_context_metrics()
            
            # Log metrics
            logger.info(
                f"Context metrics for {metrics.agent_name}: "
                f"size={metrics.context_size_bytes} bytes, "
                f"tokens={metrics.estimated_tokens}, "
                f"usage={metrics.usage_percentage:.1f}%"
            )
            
            # Report to metrics system if available
            if hasattr(self, 'metrics_collector'):
                self.metrics_collector.record_metric(
                    "agent_context_size",
                    metrics.context_size_bytes,
                    {"agent": metrics.agent_name, "run_id": metrics.run_id}
                )
                self.metrics_collector.record_metric(
                    "agent_context_tokens",
                    metrics.estimated_tokens,
                    {"agent": metrics.agent_name, "run_id": metrics.run_id}
                )
                self.metrics_collector.record_metric(
                    "agent_context_usage_percentage",
                    metrics.usage_percentage,
                    {"agent": metrics.agent_name, "run_id": metrics.run_id}
                )
            
            # Check thresholds and alert
            self._check_context_thresholds(metrics)
            
        except Exception as e:
            logger.error(f"Failed to report context metrics: {e}")
    
    def _check_context_thresholds(self, metrics: ContextMetrics) -> None:
        """Check context usage against thresholds and alert."""
        usage_ratio = metrics.usage_percentage / 100
        
        if usage_ratio >= self.CONTEXT_ERROR_THRESHOLD:
            logger.error(
                f"CRITICAL: Context usage at {metrics.usage_percentage:.1f}% "
                f"for {metrics.agent_name} (run_id={metrics.run_id}). "
                f"Tokens: {metrics.estimated_tokens}/{metrics.context_window_limit}"
            )
        elif usage_ratio >= self.CONTEXT_WARNING_THRESHOLD:
            logger.warning(
                f"Context usage at {metrics.usage_percentage:.1f}% "
                f"for {metrics.agent_name} (run_id={metrics.run_id}). "
                f"Consider truncating context."
            )
    
    def _check_context_limit_proximity(self) -> bool:
        """Check if context is approaching limits."""
        metrics = self._collect_context_metrics()
        usage_ratio = metrics.usage_percentage / 100
        
        if usage_ratio >= self.CONTEXT_WARNING_THRESHOLD:
            logger.warning(
                f"Context approaching limit: {metrics.usage_percentage:.1f}% used "
                f"({metrics.estimated_tokens}/{metrics.context_window_limit} tokens)"
            )
            return True
        return False
    
    def _validate_context_window_size(self, prompt: str) -> None:
        """Validate that prompt fits within context window.
        
        Raises:
            ValueError: If prompt exceeds context window limit.
        """
        token_count = self._estimate_token_count(prompt)
        model_name = getattr(self, 'model_name', 'default')
        limit = self.CONTEXT_LIMITS.get(model_name, self.CONTEXT_LIMITS['default'])
        
        if token_count > limit:
            raise ValueError(
                f"Context window exceeded: {token_count} tokens > {limit} token limit "
                f"for model {model_name}"
            )
    
    def _truncate_context_if_needed(self, context: Dict[str, Any], 
                                   max_size: int = 10000) -> Dict[str, Any]:
        """Truncate context if it exceeds size limit."""
        context_str = json.dumps(context) if isinstance(context, dict) else str(context)
        
        if len(context_str) <= max_size:
            return context
        
        # Truncate large values
        truncated = {}
        for key, value in context.items() if isinstance(context, dict) else [("data", context)]:
            value_str = json.dumps(value) if not isinstance(value, str) else value
            
            if len(value_str) > max_size // 4:  # If single value is too large
                if isinstance(value, list):
                    # Keep first few items
                    truncated[key] = value[:5] + ["... truncated"]
                elif isinstance(value, str):
                    # Truncate string
                    truncated[key] = value[:max_size // 4] + "... (truncated)"
                else:
                    # Keep as is but mark
                    truncated[key] = {"truncated": True, "original_size": len(value_str)}
            else:
                truncated[key] = value
        
        return truncated
    
    def _prepare_context_for_llm(self, context: Dict[str, Any], 
                                max_history: int = 10) -> Dict[str, Any]:
        """Prepare context for LLM, handling history and size limits."""
        prepared = {}
        
        for key, value in context.items():
            if key == "conversation_history" and isinstance(value, list):
                # Keep only recent history
                prepared[key] = value[-max_history:] if len(value) > max_history else value
            elif key in ["corpus_data", "documents"] and isinstance(value, list):
                # Limit large data arrays
                prepared[key] = value[:100] if len(value) > 100 else value
            else:
                prepared[key] = value
        
        return prepared
    
    def _calculate_output_tokens(self, context: Dict[str, Any]) -> int:
        """Calculate available output tokens based on context size."""
        context_tokens = self._estimate_token_count(context)
        model_name = getattr(self, 'model_name', 'default')
        window_limit = self.CONTEXT_LIMITS.get(model_name, self.CONTEXT_LIMITS['default'])
        
        # Reserve tokens for output (at least 1000, up to 4096)
        available = window_limit - context_tokens
        return min(max(available, 1000), 4096)
    
    def _generate_with_limit(self, prompt: str, max_tokens: Optional[int] = None) -> Any:
        """Generate with token limit enforcement."""
        if max_tokens is None:
            max_tokens = self._calculate_output_tokens({"prompt": prompt})
        
        # Call LLM with limit
        if hasattr(self, 'llm_manager'):
            return self.llm_manager.generate(prompt, max_tokens=max_tokens)
        return None
    
    def _execute_with_fallback(self, prompt: str, context: Dict[str, Any]) -> str:
        """Execute with fallback on context overflow."""
        try:
            self._validate_context_window_size(prompt)
            if hasattr(self, 'llm_manager'):
                return self.llm_manager.generate(prompt)
            return "No LLM manager available"
        except (ValueError, Exception) as e:
            if "context" in str(e).lower():
                logger.error(f"Context overflow, using fallback: {e}")
                # Try with truncated context
                truncated = self._truncate_context_if_needed(context, max_size=5000)
                truncated_prompt = f"[Truncated context]\n{prompt[:10000]}"
                if hasattr(self, 'llm_manager'):
                    return self.llm_manager.generate(truncated_prompt)
                return "Fallback: Context too large"
            raise
    
    def _batch_process_documents(self, documents: List[Dict], batch_size: int = 100) -> Dict[str, Any]:
        """Process documents in batches to avoid context overflow."""
        results = {"processed": 0, "batches": []}
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            # Process batch (placeholder)
            results["batches"].append({"batch_id": i // batch_size, "count": len(batch)})
            results["processed"] += len(batch)
        
        return results
    
    def _log_prompt_size_with_tokens(self, prompt: str, run_id: str) -> None:
        """Log prompt size with token count."""
        size_mb = len(prompt) / (1024 * 1024)
        token_count = self._estimate_token_count(prompt)
        
        logger.info(
            f"Prompt for {run_id}: {size_mb:.2f}MB, ~{token_count} tokens"
        )
        
        # Warn if large
        if token_count > 50000:
            logger.warning(f"Large prompt detected: {token_count} tokens for {run_id}")


class AgentContextObserver:
    """Observer for agent context metrics across the system."""
    
    def __init__(self):
        self.metrics_history: List[ContextMetrics] = []
        self.agent_metrics: Dict[str, List[ContextMetrics]] = {}
    
    def record_metrics(self, metrics: ContextMetrics) -> None:
        """Record context metrics."""
        self.metrics_history.append(metrics)
        
        if metrics.agent_name not in self.agent_metrics:
            self.agent_metrics[metrics.agent_name] = []
        self.agent_metrics[metrics.agent_name].append(metrics)
        
        # Keep only recent history (last 100 per agent)
        if len(self.agent_metrics[metrics.agent_name]) > 100:
            self.agent_metrics[metrics.agent_name] = self.agent_metrics[metrics.agent_name][-100:]
    
    def get_agent_summary(self, agent_name: str) -> Dict[str, Any]:
        """Get summary metrics for an agent."""
        if agent_name not in self.agent_metrics:
            return {}
        
        metrics_list = self.agent_metrics[agent_name]
        if not metrics_list:
            return {}
        
        # Calculate averages
        avg_size = sum(m.context_size_bytes for m in metrics_list) / len(metrics_list)
        avg_tokens = sum(m.estimated_tokens for m in metrics_list) / len(metrics_list)
        avg_usage = sum(m.usage_percentage for m in metrics_list) / len(metrics_list)
        max_tokens = max(m.estimated_tokens for m in metrics_list)
        
        return {
            "agent_name": agent_name,
            "samples": len(metrics_list),
            "avg_context_size_bytes": avg_size,
            "avg_estimated_tokens": avg_tokens,
            "avg_usage_percentage": avg_usage,
            "max_tokens_seen": max_tokens,
            "last_update": metrics_list[-1].timestamp.isoformat()
        }
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get system-wide context metrics summary."""
        summaries = {}
        for agent_name in self.agent_metrics:
            summaries[agent_name] = self.get_agent_summary(agent_name)
        
        return {
            "agents": summaries,
            "total_samples": len(self.metrics_history),
            "timestamp": datetime.now().isoformat()
        }


# Global observer instance
context_observer = AgentContextObserver()