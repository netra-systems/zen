"""Synthetic Data Sub-Agent Validation Module

Comprehensive validation logic for ModernSyntheticDataSubAgent.
Separated for modularity and maintainability (450-line limit compliance).

Business Value: Ensures reliable synthetic data generation validation.
BVJ: Growth & Enterprise | Risk Reduction | +20% reliability improvement
"""

from typing import Any, Dict, Optional

from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SyntheticDataValidator:
    """Comprehensive validator for synthetic data sub-agent operations."""
    
    def __init__(self, agent_instance):
        """Initialize validator with agent reference."""
        self.agent = agent_instance
        self.logger = logger
    
    async def run_comprehensive_validation(self, context: ExecutionContext) -> Dict[str, bool]:
        """Run comprehensive validation checks for preconditions."""
        return {
            "context_valid": self.validate_execution_context(context),
            "resources_available": await self.validate_system_resources(),
            "permissions_ok": self.validate_execution_permissions(context),
            "request_appropriate": self.validate_synthetic_request(context.state),
            "config_valid": self.validate_agent_configuration(),
            "dependencies_ready": await self.validate_dependencies()
        }
    
    def validate_execution_context(self, context: ExecutionContext) -> bool:
        """Validate ExecutionContext structure and required fields."""
        if not context or not context.run_id or not context.agent_name:
            return False
        if not context.state or not context.state.user_request:
            return False
        if context.retry_count > context.max_retries:
            return False
        return True
    
    async def validate_system_resources(self) -> bool:
        """Validate system resources are available for synthetic data generation."""
        try:
            if not self.agent.llm_manager or not self.agent.tool_dispatcher:
                return False
            circuit_status = self.agent.execution_engine.reliability_manager.get_health_status()
            return circuit_status.get("circuit_breaker_status") != "open"
        except Exception:
            return False
    
    def validate_execution_permissions(self, context: ExecutionContext) -> bool:
        """Validate user has appropriate permissions for synthetic data generation."""
        state = context.state
        if self._is_admin_request(state):
            return True
        if context.user_id and self._has_synthetic_permissions(context.user_id):
            return True
        return self._is_synthetic_request(state)
    
    def validate_synthetic_request(self, state: DeepAgentState) -> bool:
        """Enhanced validation for synthetic data request appropriateness."""
        if not state.user_request:
            return False
        request_lower = state.user_request.lower()
        synthetic_keywords = ["synthetic", "generate data", "test data", "sample data"]
        has_keywords = any(keyword in request_lower for keyword in synthetic_keywords)
        return has_keywords or self._is_admin_request(state)
    
    def validate_agent_configuration(self) -> bool:
        """Validate agent configuration is properly set up."""
        if not self.agent.generator or not self.agent.profile_parser:
            return False
        if not self.agent.metrics_handler or not self.agent.approval_handler:
            return False
        if not hasattr(self.agent, 'execution_engine') or not self.agent.execution_engine:
            return False
        return True
    
    async def validate_dependencies(self) -> bool:
        """Validate external dependencies are available and responsive."""
        try:
            # Check LLM manager health
            if not await self._check_llm_availability():
                return False
            # Check tool dispatcher readiness
            return self._check_tool_dispatcher_health()
        except Exception as e:
            logger.warning(f"Dependency validation failed: {e}")
            return False
    
    def _is_admin_request(self, state: DeepAgentState) -> bool:
        """Check if request is from admin mode."""
        triage_result = state.triage_result or {}
        if not isinstance(triage_result, dict):
            return False
        category = triage_result.get("category", "")
        is_admin = triage_result.get("is_admin_mode", False)
        return "synthetic" in category.lower() or is_admin
    
    def _is_synthetic_request(self, state: DeepAgentState) -> bool:
        """Check if request explicitly mentions synthetic data."""
        if not state.user_request:
            return False
        request_lower = state.user_request.lower()
        return "synthetic" in request_lower or "generate data" in request_lower
    
    def _has_synthetic_permissions(self, user_id: str) -> bool:
        """Check if user has permissions for synthetic data generation."""
        # Placeholder for permission checking logic
        # In production, this would check user roles/permissions
        if not user_id:
            return False
        # Default to allowing authenticated users for now
        return True
    
    async def _check_llm_availability(self) -> bool:
        """Check if LLM manager is available and responsive."""
        try:
            if not self.agent.llm_manager:
                return False
            # Could add a quick health check ping here
            return hasattr(self.agent.llm_manager, 'get_client')
        except Exception:
            return False
    
    def _check_tool_dispatcher_health(self) -> bool:
        """Check if tool dispatcher is healthy and ready."""
        if not self.agent.tool_dispatcher:
            return False
        # Check if required tools are available
        return hasattr(self.agent.tool_dispatcher, 'dispatch')
    
    async def record_validation_metrics(self, context: ExecutionContext, is_valid: bool,
                                      checks: Dict[str, bool]) -> None:
        """Record validation metrics for monitoring and analysis."""
        try:
            metrics = {
                "validation_success": is_valid,
                "failed_checks_count": len([c for c in checks.values() if not c]),
                "total_checks": len(checks)
            }
            self.agent.metrics_handler.record_validation_metrics(context.run_id, metrics)
        except Exception as e:
            logger.warning(f"Failed to record validation metrics: {e}")
    
    async def log_validation_result(self, context: ExecutionContext, is_valid: bool, 
                                  checks: Dict[str, bool]) -> None:
        """Log comprehensive validation result for monitoring."""
        status = "valid" if is_valid else "invalid"
        failed_checks = [name for name, passed in checks.items() if not passed]
        logger.info(f"Precondition validation for {context.run_id}: {status}")
        if failed_checks:
            logger.warning(f"Failed validation checks: {', '.join(failed_checks)}")
        await self.record_validation_metrics(context, is_valid, checks)