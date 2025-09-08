"""Token Optimization Integration Service

This module provides the main integration service that brings together all token optimization
components while maintaining SSOT compliance and user isolation.

CRITICAL: This is the primary interface for token optimization functionality.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.billing.token_counter import TokenCounter
from netra_backend.app.services.token_optimization.context_manager import TokenOptimizationContextManager
from netra_backend.app.services.token_optimization.session_factory import TokenOptimizationSessionFactory
from netra_backend.app.services.token_optimization.config_manager import TokenOptimizationConfigManager
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TokenOptimizationIntegrationService:
    """Main integration service for token optimization functionality.
    
    This service provides a unified interface for all token optimization features
    while ensuring SSOT compliance, user isolation, and proper architecture patterns.
    
    Key Features:
    - Unified interface for all token optimization functionality
    - Complete user isolation through factory patterns
    - Configuration-driven pricing and settings
    - WebSocket integration for real-time updates
    - Comprehensive cost analysis and optimization
    """
    
    def __init__(self, websocket_manager: Optional[UnifiedWebSocketManager] = None):
        """Initialize integration service with all SSOT components.
        
        Args:
            websocket_manager: Optional WebSocket manager for real-time updates
        """
        
        # Initialize SSOT components
        self.token_counter = TokenCounter()  # Existing SSOT component
        self.context_manager = TokenOptimizationContextManager(self.token_counter)
        self.session_factory = TokenOptimizationSessionFactory()
        self.config_manager = TokenOptimizationConfigManager()
        
        # WebSocket integration for real-time updates
        self.websocket_manager = websocket_manager
        
        # Initialize service with configuration
        self._initialize_service()
        
        logger.info("✅ Initialized TokenOptimizationIntegrationService with all SSOT components")
    
    def _initialize_service(self) -> None:
        """Initialize service with current configuration."""
        
        # Update TokenCounter with configuration-driven pricing
        pricing_config = self.config_manager.get_model_pricing()
        
        for model, prices in pricing_config.items():
            if model != "default":  # Skip default entry for individual updates
                self.token_counter.update_model_pricing(
                    model=model,
                    input_price=prices["input"],
                    output_price=prices["output"]
                )
        
        logger.debug("Updated TokenCounter with configuration-driven pricing")
    
    async def track_agent_usage(
        self,
        context: UserExecutionContext,
        agent_name: str,
        input_tokens: int,
        output_tokens: int,
        model: str,
        operation_type: str = "execution"
    ) -> Tuple[UserExecutionContext, Dict[str, Any]]:
        """Track agent token usage with complete integration.
        
        Args:
            context: UserExecutionContext (immutable)
            agent_name: Name of the agent
            input_tokens: Input tokens used
            output_tokens: Output tokens generated
            model: Model used
            operation_type: Type of operation
            
        Returns:
            Tuple of (enhanced_context, tracking_result)
        """
        
        # Check if optimization is enabled for user
        if not self.config_manager.is_optimization_enabled_for_user(context.user_id):
            logger.debug(f"Token optimization disabled for user {context.user_id}")
            return context, {"optimization_enabled": False}
        
        # Get or create session for user isolation
        session = self.session_factory.create_session(context)
        
        # Track usage in session (user-isolated)
        session_result = session.track_usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            operation_type=operation_type
        )
        
        # Enhance context with token data (immutable pattern)
        enhanced_context = self.context_manager.track_agent_usage(
            context=context,
            agent_name=agent_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            operation_type=operation_type
        )
        
        # Check cost thresholds for alerts
        cost_thresholds = self.config_manager.get_cost_alert_thresholds()
        operation_cost = session_result["operation_result"]["current_operation"]["cost"]
        
        # Emit WebSocket event if configured
        if self.websocket_manager:
            await self._emit_usage_update(
                context=enhanced_context,
                agent_name=agent_name,
                operation_cost=operation_cost,
                total_cost=session_result["session_totals"]["total_cost"],
                thresholds=cost_thresholds
            )
        
        # Prepare integration result
        integration_result = {
            "optimization_enabled": True,
            "session_result": session_result,
            "operation_cost": operation_cost,
            "cost_alerts": self._check_cost_alerts(operation_cost, cost_thresholds),
            "model_used": model,
            "agent_name": agent_name,
            "operation_type": operation_type
        }
        
        return enhanced_context, integration_result
    
    async def optimize_prompt(
        self,
        context: UserExecutionContext,
        agent_name: str,
        prompt: str,
        target_reduction: Optional[int] = None
    ) -> Tuple[UserExecutionContext, str, Dict[str, Any]]:
        """Optimize prompt with complete integration.
        
        Args:
            context: UserExecutionContext (immutable)
            agent_name: Agent requesting optimization
            prompt: Prompt to optimize
            target_reduction: Target reduction percentage (from config if None)
            
        Returns:
            Tuple of (enhanced_context, optimized_prompt, optimization_result)
        """
        
        # Get target reduction from configuration if not specified
        if target_reduction is None:
            optimization_settings = self.config_manager.get_optimization_settings()
            target_reduction = optimization_settings.get("TOKEN_OPTIMIZATION_DEFAULT_TARGET_REDUCTION", 20)
        
        # Get session for user isolation
        session = self.session_factory.get_session(context)
        if not session:
            session = self.session_factory.create_session(context)
        
        # Optimize prompt in session
        session_optimization = session.optimize_prompt(
            prompt=prompt,
            target_reduction=target_reduction
        )
        
        # Enhance context with optimization data (immutable pattern)
        enhanced_context, optimized_prompt = self.context_manager.optimize_prompt_for_context(
            context=context,
            agent_name=agent_name,
            prompt=prompt,
            target_reduction=target_reduction
        )
        
        # Emit WebSocket event for optimization
        if self.websocket_manager:
            await self._emit_optimization_update(
                context=enhanced_context,
                agent_name=agent_name,
                optimization_result=session_optimization
            )
        
        # Prepare integration result
        integration_result = {
            "optimization_applied": len(session_optimization.get("optimization_applied", [])) > 0,
            "tokens_saved": session_optimization.get("tokens_saved", 0),
            "cost_savings": float(session_optimization.get("cost_savings", 0)),
            "reduction_achieved": session_optimization.get("reduction_percent", 0),
            "target_achieved": session_optimization.get("target_achieved", False),
            "optimizations_applied": session_optimization.get("optimization_applied", [])
        }
        
        return enhanced_context, optimized_prompt, integration_result
    
    async def get_cost_analysis(
        self,
        context: UserExecutionContext,
        agent_name: str
    ) -> Tuple[UserExecutionContext, Dict[str, Any]]:
        """Get comprehensive cost analysis with suggestions.
        
        Args:
            context: UserExecutionContext (immutable)
            agent_name: Agent requesting analysis
            
        Returns:
            Tuple of (enhanced_context, cost_analysis)
        """
        
        # Get session for user-isolated data
        session = self.session_factory.get_session(context)
        if not session:
            # Create session if it doesn't exist
            session = self.session_factory.create_session(context)
        
        # Get optimization suggestions from session
        suggestions = session.get_suggestions()
        
        # Enhance context with suggestions (immutable pattern)
        enhanced_context = self.context_manager.add_cost_suggestions(
            context=context,
            agent_name=agent_name
        )
        
        # Get usage summary from context manager
        usage_summary = self.context_manager.get_token_usage_summary(
            context=enhanced_context,
            agent_name=agent_name
        )
        
        # Get cost thresholds for analysis
        cost_thresholds = self.config_manager.get_cost_alert_thresholds()
        current_cost = usage_summary.get("current_session", {}).get("total_cost", 0.0)
        
        # Prepare comprehensive cost analysis
        cost_analysis = {
            "usage_summary": usage_summary,
            "optimization_suggestions": suggestions,
            "cost_thresholds": {k: float(v) for k, v in cost_thresholds.items()},
            "current_cost": current_cost,
            "cost_alerts": self._check_cost_alerts(current_cost, cost_thresholds),
            "session_info": {
                "session_id": session.session_id,
                "operations_count": session.operations_count,
                "total_tokens": session.total_tokens,
                "average_cost_per_operation": current_cost / max(session.operations_count, 1)
            },
            "recommendations": self._generate_cost_recommendations(current_cost, suggestions),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Emit WebSocket event for cost analysis
        if self.websocket_manager:
            await self._emit_cost_analysis_update(
                context=enhanced_context,
                agent_name=agent_name,
                cost_analysis=cost_analysis
            )
        
        return enhanced_context, cost_analysis
    
    async def finalize_user_session(
        self,
        context: UserExecutionContext
    ) -> Optional[Dict[str, Any]]:
        """Finalize user session and return comprehensive summary.
        
        Args:
            context: UserExecutionContext to finalize
            
        Returns:
            Session summary or None if no session found
        """
        
        summary = self.session_factory.finalize_session(context)
        
        if summary and self.websocket_manager:
            await self._emit_session_finalized(context, summary)
        
        return summary
    
    def get_user_optimization_status(
        self,
        context: UserExecutionContext
    ) -> Dict[str, Any]:
        """Get current optimization status for user.
        
        Args:
            context: UserExecutionContext to check
            
        Returns:
            Dictionary with user's optimization status
        """
        
        # Check if optimization is enabled
        optimization_enabled = self.config_manager.is_optimization_enabled_for_user(context.user_id)
        
        # Get active sessions for user
        active_sessions = self.session_factory.get_active_sessions_for_user(context.user_id)
        
        # Get cost budget if configured
        cost_budget = self.config_manager.get_cost_budget_for_user(context.user_id)
        
        # Get current session if exists
        current_session = self.session_factory.get_session(context)
        
        status = {
            "user_id": context.user_id,
            "optimization_enabled": optimization_enabled,
            "active_sessions_count": len(active_sessions),
            "current_session": {
                "exists": current_session is not None,
                "session_id": current_session.session_id if current_session else None,
                "operations_count": current_session.operations_count if current_session else 0,
                "total_cost": current_session.total_cost if current_session else 0.0
            } if current_session else None,
            "cost_budget": {
                "has_budget": cost_budget is not None,
                "daily_limit": float(cost_budget) if cost_budget else None
            },
            "configuration": {
                "optimization_settings": self.config_manager.get_optimization_settings(),
                "cost_thresholds": {k: float(v) for k, v in self.config_manager.get_cost_alert_thresholds().items()}
            }
        }
        
        return status
    
    def get_service_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of the integration service.
        
        Returns:
            Dictionary with service health information
        """
        
        try:
            # Get component health
            token_counter_stats = self.token_counter.get_stats()
            factory_stats = self.session_factory.get_factory_stats()
            config_summary = self.config_manager.get_all_config_summary()
            
            health_status = {
                "service_type": "TokenOptimizationIntegrationService",
                "overall_health": "healthy",
                "components": {
                    "token_counter": {
                        "status": "healthy" if token_counter_stats.get("enabled") else "disabled",
                        "stats": token_counter_stats
                    },
                    "session_factory": {
                        "status": "healthy",
                        "stats": factory_stats
                    },
                    "config_manager": {
                        "status": "healthy",
                        "cache_status": config_summary.get("cache_status", {})
                    },
                    "context_manager": {
                        "status": "healthy",
                        "type": "TokenOptimizationContextManager"
                    },
                    "websocket_integration": {
                        "status": "available" if self.websocket_manager else "disabled"
                    }
                },
                "architecture_compliance": {
                    "uses_ssot_components": True,
                    "user_isolation_enabled": True,
                    "frozen_dataclass_compliant": True,
                    "configuration_driven": True,
                    "factory_pattern_implemented": True
                },
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Error getting service health status: {e}")
            return {
                "service_type": "TokenOptimizationIntegrationService",
                "overall_health": "degraded",
                "error": str(e),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
    
    # Private helper methods
    
    def _check_cost_alerts(
        self, 
        cost: float, 
        thresholds: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Check cost against thresholds and generate alerts."""
        
        alerts = []
        
        if cost >= float(thresholds.get("critical", 25.0)):
            alerts.append({
                "level": "critical",
                "message": f"Critical cost threshold exceeded: ${cost:.4f}",
                "threshold": float(thresholds["critical"]),
                "actual_cost": cost
            })
        elif cost >= float(thresholds.get("high", 5.0)):
            alerts.append({
                "level": "high", 
                "message": f"High cost threshold exceeded: ${cost:.4f}",
                "threshold": float(thresholds["high"]),
                "actual_cost": cost
            })
        elif cost >= float(thresholds.get("medium", 1.0)):
            alerts.append({
                "level": "medium",
                "message": f"Medium cost threshold exceeded: ${cost:.4f}",
                "threshold": float(thresholds["medium"]),
                "actual_cost": cost
            })
        
        return alerts
    
    def _generate_cost_recommendations(
        self,
        current_cost: float,
        suggestions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate actionable cost recommendations."""
        
        recommendations = []
        
        # High-priority suggestions become recommendations
        high_priority = [s for s in suggestions if s.get("priority") == "high"]
        for suggestion in high_priority[:3]:  # Limit to top 3
            recommendations.append({
                "priority": "high",
                "action": suggestion.get("recommendation", "Optimize token usage"),
                "potential_savings": suggestion.get("potential_savings", "N/A"),
                "type": suggestion.get("type", "optimization")
            })
        
        # Cost-based recommendations
        if current_cost > 10.0:
            recommendations.append({
                "priority": "high",
                "action": "Consider implementing result caching for repeated operations",
                "potential_savings": f"${current_cost * 0.3:.2f} (30% reduction)",
                "type": "caching"
            })
        
        if current_cost > 1.0:
            recommendations.append({
                "priority": "medium",
                "action": "Review prompt efficiency and remove unnecessary verbosity",
                "potential_savings": f"${current_cost * 0.15:.2f} (15% reduction)",
                "type": "prompt_optimization"
            })
        
        return recommendations
    
    # WebSocket event emission methods
    
    async def _emit_usage_update(
        self,
        context: UserExecutionContext,
        agent_name: str,
        operation_cost: float,
        total_cost: float,
        thresholds: Dict[str, Any]
    ) -> None:
        """Emit usage update via WebSocket."""
        
        if not self.websocket_manager:
            return
        
        try:
            await self.websocket_manager.emit_critical_event(
                user_id=context.user_id,
                event_type="agent_thinking",  # Existing event type
                event_data={
                    "message": f"Token usage tracked for {agent_name}",
                    "cost_analysis": {
                        "operation_cost": operation_cost,
                        "total_session_cost": total_cost,
                        "alerts": self._check_cost_alerts(operation_cost, thresholds)
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to emit usage update WebSocket event: {e}")
    
    async def _emit_optimization_update(
        self,
        context: UserExecutionContext,
        agent_name: str,
        optimization_result: Dict[str, Any]
    ) -> None:
        """Emit optimization update via WebSocket."""
        
        if not self.websocket_manager:
            return
        
        try:
            await self.websocket_manager.emit_critical_event(
                user_id=context.user_id,
                event_type="agent_thinking",  # Existing event type
                event_data={
                    "message": f"Prompt optimized for {agent_name}",
                    "optimization_details": {
                        "tokens_saved": optimization_result.get("tokens_saved", 0),
                        "cost_savings": float(optimization_result.get("cost_savings", 0)),
                        "reduction_percent": optimization_result.get("reduction_percent", 0)
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to emit optimization update WebSocket event: {e}")
    
    async def _emit_cost_analysis_update(
        self,
        context: UserExecutionContext,
        agent_name: str,
        cost_analysis: Dict[str, Any]
    ) -> None:
        """Emit cost analysis update via WebSocket."""
        
        if not self.websocket_manager:
            return
        
        try:
            await self.websocket_manager.emit_critical_event(
                user_id=context.user_id,
                event_type="agent_completed",  # Existing event type
                event_data={
                    "message": f"Cost analysis completed for {agent_name}",
                    "cost_analysis": {
                        "current_cost": cost_analysis["current_cost"],
                        "suggestions_count": len(cost_analysis["optimization_suggestions"]),
                        "alerts": cost_analysis["cost_alerts"]
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to emit cost analysis WebSocket event: {e}")
    
    async def _emit_session_finalized(
        self,
        context: UserExecutionContext,
        session_summary: Dict[str, Any]
    ) -> None:
        """Emit session finalization event via WebSocket."""
        
        if not self.websocket_manager:
            return
        
        try:
            await self.websocket_manager.emit_critical_event(
                user_id=context.user_id,
                event_type="agent_completed",  # Existing event type
                event_data={
                    "message": "Token optimization session completed",
                    "session_summary": {
                        "total_operations": session_summary["operations_performed"],
                        "total_cost": session_summary["total_cost"],
                        "duration_minutes": round(session_summary["duration_seconds"] / 60, 2)
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to emit session finalized WebSocket event: {e}")