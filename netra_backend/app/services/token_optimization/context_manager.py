"""Token Optimization Context Manager

This module provides proper UserExecutionContext integration for token optimization
without violating the frozen dataclass constraints. It uses immutable patterns
to enhance context with token data while respecting SSOT principles.

CRITICAL: Never mutate frozen UserExecutionContext - always create new instances.
"""

from typing import Dict, Any, Optional
from dataclasses import replace
from datetime import datetime, timezone

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.billing.token_counter import TokenCounter, TokenCount
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TokenOptimizationContextManager:
    """Manages token optimization data within UserExecutionContext using immutable patterns.
    
    This class ensures that token data is properly stored in UserExecutionContext
    without violating the frozen=True constraint by always creating new context instances.
    
    Key Design Principles:
    - NEVER mutate existing UserExecutionContext 
    - Always use dataclass.replace() for immutable updates
    - Store token data in metadata field using structured keys
    - Maintain user isolation through proper context scoping
    """
    
    def __init__(self, token_counter: TokenCounter):
        """Initialize with existing TokenCounter instance (SSOT compliance)."""
        self.token_counter = token_counter
        self._session_data = {}  # Per-session token tracking
    
    def track_agent_usage(
        self, 
        context: UserExecutionContext,
        agent_name: str,
        input_tokens: int,
        output_tokens: int,
        model: str,
        operation_type: str = "execution"
    ) -> UserExecutionContext:
        """Track agent token usage and return enhanced context.
        
        CRITICAL: This method respects frozen dataclass by creating new context.
        
        Args:
            context: Original UserExecutionContext (immutable)
            agent_name: Name of the agent
            input_tokens: Input tokens used
            output_tokens: Output tokens generated
            model: Model used
            operation_type: Type of operation
            
        Returns:
            New UserExecutionContext with token data in metadata
        """
        # Track usage in TokenCounter (existing SSOT component)
        tracking_result = self.token_counter.track_agent_usage(
            agent_name=agent_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            operation_type=operation_type
        )
        
        # Create enhanced metadata WITHOUT mutating original
        enhanced_metadata = self._create_enhanced_metadata(
            context.metadata,
            tracking_result,
            agent_name,
            operation_type
        )
        
        # Return new context with enhanced metadata (immutable pattern)
        return replace(context, metadata=enhanced_metadata)
    
    def optimize_prompt_for_context(
        self,
        context: UserExecutionContext,
        agent_name: str,
        prompt: str,
        target_reduction: int = 20
    ) -> tuple[UserExecutionContext, str]:
        """Optimize prompt and return enhanced context with metrics.
        
        Args:
            context: Original UserExecutionContext
            agent_name: Agent performing optimization
            prompt: Prompt to optimize
            target_reduction: Target percentage reduction
            
        Returns:
            Tuple of (enhanced_context, optimized_prompt)
        """
        # Use existing TokenCounter optimization (SSOT compliance)
        optimization_result = self.token_counter.optimize_prompt(
            prompt=prompt,
            target_reduction_percent=target_reduction
        )
        
        # Create enhanced metadata with optimization data
        enhanced_metadata = self._add_optimization_data(
            context.metadata,
            agent_name,
            optimization_result
        )
        
        # Return enhanced context and optimized prompt
        enhanced_context = replace(context, metadata=enhanced_metadata)
        return enhanced_context, optimization_result["optimized_prompt"]
    
    def add_cost_suggestions(
        self,
        context: UserExecutionContext,
        agent_name: str
    ) -> UserExecutionContext:
        """Add cost optimization suggestions to context metadata.
        
        Args:
            context: Original UserExecutionContext
            agent_name: Agent requesting suggestions
            
        Returns:
            Enhanced UserExecutionContext with suggestions
        """
        # Get suggestions from existing TokenCounter
        suggestions = self.token_counter.get_optimization_suggestions()
        
        # Create enhanced metadata with suggestions
        enhanced_metadata = self._add_suggestions_data(
            context.metadata,
            agent_name,
            suggestions
        )
        
        return replace(context, metadata=enhanced_metadata)
    
    def get_token_usage_summary(
        self,
        context: UserExecutionContext,
        agent_name: str
    ) -> Dict[str, Any]:
        """Get token usage summary for current context and agent.
        
        Args:
            context: UserExecutionContext to analyze
            agent_name: Agent to get summary for
            
        Returns:
            Token usage summary dictionary
        """
        # Get overall agent summary from TokenCounter
        summary = self.token_counter.get_agent_usage_summary()
        
        # Add current session data from context metadata
        token_usage = context.metadata.get("token_usage", {})
        if token_usage:
            session_operations = token_usage.get("operations", [])
            agent_operations = [op for op in session_operations if op.get("agent") == agent_name]
            
            if agent_operations:
                session_cost = sum(op.get("cost", 0) for op in agent_operations)
                session_tokens = sum(
                    op.get("input_tokens", 0) + op.get("output_tokens", 0) 
                    for op in agent_operations
                )
                
                summary["current_session"] = {
                    "operations_count": len(agent_operations),
                    "total_cost": session_cost,
                    "total_tokens": session_tokens,
                    "agent_name": agent_name
                }
        
        return summary
    
    def _create_enhanced_metadata(
        self,
        original_metadata: Dict[str, Any],
        tracking_result: Dict[str, Any],
        agent_name: str,
        operation_type: str
    ) -> Dict[str, Any]:
        """Create enhanced metadata with token tracking data.
        
        CRITICAL: Creates new dictionary - never mutates original.
        """
        # Create copy of original metadata
        enhanced = original_metadata.copy()
        
        # Initialize token_usage structure if not present
        if "token_usage" not in enhanced:
            enhanced["token_usage"] = {
                "operations": [],
                "cumulative_cost": 0.0,
                "cumulative_tokens": 0,
                "session_start": datetime.now(timezone.utc).isoformat()
            }
        else:
            # Copy existing token_usage to avoid mutation
            enhanced["token_usage"] = enhanced["token_usage"].copy()
            enhanced["token_usage"]["operations"] = enhanced["token_usage"]["operations"].copy()
        
        # Add new operation if tracking was successful
        if tracking_result.get("tracking_enabled"):
            current_op = tracking_result["current_operation"]
            cumulative = tracking_result["cumulative_stats"]
            
            enhanced["token_usage"]["operations"].append({
                "agent": agent_name,
                "operation_type": operation_type,
                "input_tokens": current_op["input_tokens"],
                "output_tokens": current_op["output_tokens"],
                "model": current_op["model"],
                "cost": current_op["cost"],
                "timestamp": tracking_result["timestamp"]
            })
            
            # Update cumulative metrics from TokenCounter
            enhanced["token_usage"]["cumulative_cost"] = cumulative["total_cost"]
            enhanced["token_usage"]["cumulative_tokens"] = cumulative["total_tokens"]
        
        return enhanced
    
    def _add_optimization_data(
        self,
        original_metadata: Dict[str, Any],
        agent_name: str,
        optimization_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add prompt optimization data to metadata."""
        enhanced = original_metadata.copy()
        
        if "prompt_optimizations" not in enhanced:
            enhanced["prompt_optimizations"] = []
        else:
            enhanced["prompt_optimizations"] = enhanced["prompt_optimizations"].copy()
        
        enhanced["prompt_optimizations"].append({
            "agent": agent_name,
            "original_tokens": optimization_result["original_tokens"],
            "optimized_tokens": optimization_result["optimized_tokens"],
            "tokens_saved": optimization_result["tokens_saved"],
            "reduction_percent": optimization_result["reduction_percent"],
            "cost_savings": float(optimization_result["cost_savings"]),
            "optimizations_applied": optimization_result["optimization_applied"],
            "target_achieved": optimization_result["target_achieved"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return enhanced
    
    def _add_suggestions_data(
        self,
        original_metadata: Dict[str, Any],
        agent_name: str,
        suggestions: list
    ) -> Dict[str, Any]:
        """Add cost optimization suggestions to metadata."""
        enhanced = original_metadata.copy()
        
        # Store suggestions with agent context
        enhanced["cost_optimization_suggestions"] = {
            "agent_name": agent_name,
            "suggestions": suggestions,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "high_priority_count": len([s for s in suggestions if s.get("priority") == "high"])
        }
        
        return enhanced
    
    def create_token_aware_context(
        self,
        base_context: UserExecutionContext,
        enable_optimization: bool = True,
        cost_threshold: Optional[float] = None
    ) -> UserExecutionContext:
        """Create a token-aware context with optimization flags.
        
        Args:
            base_context: Base UserExecutionContext
            enable_optimization: Whether to enable token optimization
            cost_threshold: Cost threshold for optimization alerts
            
        Returns:
            Enhanced UserExecutionContext with token optimization metadata
        """
        # Create token optimization metadata
        token_optimization_config = {
            "token_optimization_enabled": enable_optimization,
            "cost_threshold": cost_threshold or 1.0,
            "session_id": f"token_session_{base_context.request_id}",
            "initialized_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Enhance metadata with optimization config
        enhanced_metadata = base_context.metadata.copy()
        enhanced_metadata["token_optimization"] = token_optimization_config
        
        # Return new context with enhanced metadata
        return replace(base_context, metadata=enhanced_metadata)