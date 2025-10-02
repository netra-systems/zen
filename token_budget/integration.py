"""Integration utilities for adaptive budget management with zen orchestrator."""

import logging
from typing import Dict, Optional, Union, Any
from .budget_manager import TokenBudgetManager
from .adaptive_models import AdaptiveConfig, ExecutionResult


logger = logging.getLogger(__name__)


class BudgetManagerFactory:
    """Factory for creating appropriate budget managers based on configuration."""

    @staticmethod
    def create_budget_manager(
        overall_budget: Optional[Union[int, float]] = None,
        overall_cost_budget: Optional[float] = None,
        budget_type: str = "tokens",
        enforcement_mode: str = "warn",
        adaptive_enabled: bool = False,
        adaptive_config: Optional[AdaptiveConfig] = None,
        **adaptive_kwargs
    ) -> Union[TokenBudgetManager, 'AdaptiveBudgetController']:
        """
        Create the appropriate budget manager based on configuration.

        Args:
            overall_budget: Overall token budget
            overall_cost_budget: Overall cost budget in USD
            budget_type: Type of budget ("tokens", "cost", "mixed")
            enforcement_mode: Enforcement mode ("warn" or "block")
            adaptive_enabled: Enable adaptive features
            adaptive_config: Adaptive configuration object
            **adaptive_kwargs: Additional adaptive configuration parameters

        Returns:
            TokenBudgetManager or AdaptiveBudgetController based on configuration
        """
        # Validate configuration
        config_issues = BudgetManagerFactory.validate_configuration(
            overall_budget, overall_cost_budget, enforcement_mode, adaptive_enabled
        )

        if config_issues:
            logger.warning(f"Budget configuration issues: {config_issues}")

        # Block mode supersedes adaptive features
        if enforcement_mode == "block" and adaptive_enabled:
            logger.warning("Block enforcement mode supersedes adaptive budget management. Disabling adaptive features.")
            adaptive_enabled = False

        # Determine total budget for adaptive controller
        total_budget = overall_cost_budget if overall_cost_budget is not None else overall_budget

        if adaptive_enabled and total_budget and enforcement_mode != "block":
            # Create adaptive controller
            logger.info("Creating AdaptiveBudgetController")

            # Import here to avoid circular import
            from .adaptive_controller import AdaptiveBudgetController

            # Merge configuration
            config = adaptive_config or AdaptiveConfig()
            for key, value in adaptive_kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)

            return AdaptiveBudgetController(
                total_budget=total_budget,
                adaptive_mode=True,
                enforcement_mode=enforcement_mode,
                config=config,
                **{k: v for k, v in adaptive_kwargs.items()
                   if k in ['restart_threshold', 'checkpoint_intervals', 'min_completion_probability']}
            )

        else:
            # Create standard budget manager
            logger.info("Creating standard TokenBudgetManager")

            if overall_cost_budget is not None:
                return TokenBudgetManager(
                    overall_cost_budget=overall_cost_budget,
                    enforcement_mode=enforcement_mode,
                    budget_type=budget_type
                )
            else:
                return TokenBudgetManager(
                    overall_budget=overall_budget,
                    enforcement_mode=enforcement_mode,
                    budget_type=budget_type
                )

    @staticmethod
    def validate_configuration(
        overall_budget: Optional[Union[int, float]],
        overall_cost_budget: Optional[float],
        enforcement_mode: str,
        adaptive_enabled: bool
    ) -> list:
        """Validate budget configuration and return any issues."""
        issues = []

        # Check if budget is specified
        if not overall_budget and not overall_cost_budget:
            issues.append("No budget specified (overall_budget or overall_cost_budget)")

        # Check enforcement mode
        if enforcement_mode not in ["warn", "block"]:
            issues.append(f"Invalid enforcement mode: {enforcement_mode}")

        # Check adaptive compatibility
        if adaptive_enabled and enforcement_mode == "block":
            issues.append("Adaptive budget management cannot be used with block enforcement mode")

        return issues


class AdaptiveIntegration:
    """Integration utilities for adaptive budget management."""

    def __init__(self, budget_manager: Union[TokenBudgetManager, Any]):
        self.budget_manager = budget_manager
        # Check if it's adaptive by looking for the method
        self.is_adaptive = hasattr(budget_manager, 'execute_adaptive_command')

    def execute_command(self, command: str, context: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """
        Execute a command using appropriate budget management.

        Args:
            command: Command to execute
            context: Additional context for command execution

        Returns:
            ExecutionResult with execution details
        """
        context = context or {}

        if self.is_adaptive:
            logger.info(f"Executing command with adaptive budget management: {command}")
            return self.budget_manager.execute_adaptive_command(command, context)
        else:
            logger.info(f"Executing command with standard budget management: {command}")
            # For standard budget manager, we need to simulate execution
            # In real integration, this would connect to the actual command execution system
            return ExecutionResult(
                success=True,
                todos_completed=[],
                total_tokens_used=0
            )

    def get_budget_status(self) -> Dict[str, Any]:
        """Get current budget status and statistics."""
        if self.is_adaptive:
            return self.budget_manager.get_execution_statistics()
        else:
            return {
                'total_budget': getattr(self.budget_manager, 'overall_budget', 0),
                'total_usage': self.budget_manager.total_usage,
                'enforcement_mode': self.budget_manager.enforcement_mode,
                'command_budgets': {
                    name: {
                        'limit': info.limit,
                        'used': info.used,
                        'remaining': info.remaining,
                        'percentage': info.percentage
                    }
                    for name, info in self.budget_manager.command_budgets.items()
                }
            }

    def reset_for_new_session(self):
        """Reset budget manager for a new session."""
        if self.is_adaptive:
            self.budget_manager.reset_for_new_session()
        else:
            # Reset standard budget manager
            self.budget_manager.total_usage = 0
            for command_budget in self.budget_manager.command_budgets.values():
                command_budget.used = 0

    def validate_and_optimize(self) -> Dict[str, Any]:
        """Validate configuration and suggest optimizations."""
        if self.is_adaptive:
            issues = self.budget_manager.validate_configuration()
            optimized_config = self.budget_manager.optimize_configuration()

            return {
                'validation_issues': issues,
                'optimized_config': optimized_config,
                'current_statistics': self.budget_manager.get_execution_statistics()
            }
        else:
            return {
                'validation_issues': [],
                'message': 'Standard budget manager - no adaptive optimizations available'
            }


def create_zen_orchestrator_integration(
    workspace_dir,
    overall_budget: Optional[Union[int, float]] = None,
    overall_cost_budget: Optional[float] = None,
    budget_type: str = "tokens",
    enforcement_mode: str = "warn",
    adaptive_enabled: bool = False,
    **orchestrator_kwargs
) -> tuple:
    """
    Create zen orchestrator with integrated adaptive budget management.

    Args:
        workspace_dir: Workspace directory
        overall_budget: Overall token budget
        overall_cost_budget: Overall cost budget
        budget_type: Budget type ("tokens", "cost", "mixed")
        enforcement_mode: Enforcement mode ("warn", "block")
        adaptive_enabled: Enable adaptive features
        **orchestrator_kwargs: Additional orchestrator arguments

    Returns:
        Tuple of (orchestrator_config, adaptive_integration)
    """
    # Create appropriate budget manager
    budget_manager = BudgetManagerFactory.create_budget_manager(
        overall_budget=overall_budget,
        overall_cost_budget=overall_cost_budget,
        budget_type=budget_type,
        enforcement_mode=enforcement_mode,
        adaptive_enabled=adaptive_enabled
    )

    # Create integration wrapper
    integration = AdaptiveIntegration(budget_manager)

    # Prepare orchestrator configuration
    orchestrator_config = {
        'workspace_dir': workspace_dir,
        'overall_token_budget': overall_budget,
        'overall_cost_budget': overall_cost_budget,
        'budget_type': budget_type,
        'budget_enforcement_mode': enforcement_mode,
        **orchestrator_kwargs
    }

    # Add adaptive-specific configuration
    if adaptive_enabled and isinstance(budget_manager, AdaptiveBudgetController):
        orchestrator_config.update({
            'adaptive_budget_enabled': True,
            'adaptive_controller': budget_manager
        })

    logger.info(f"Created zen orchestrator integration with {'adaptive' if adaptive_enabled else 'standard'} budget management")

    return orchestrator_config, integration


def example_usage():
    """Example of how to use the adaptive budget integration."""
    from pathlib import Path

    # Example 1: Standard budget management
    config, integration = create_zen_orchestrator_integration(
        workspace_dir=Path("/tmp/workspace"),
        overall_budget=1000,
        enforcement_mode="warn"
    )

    # Example 2: Adaptive budget management
    adaptive_config, adaptive_integration = create_zen_orchestrator_integration(
        workspace_dir=Path("/tmp/workspace"),
        overall_budget=2000,
        enforcement_mode="warn",
        adaptive_enabled=True,
        restart_threshold=0.85,
        checkpoint_intervals=[0.25, 0.5, 0.75, 1.0],
        min_completion_probability=0.6
    )

    # Execute a command
    result = adaptive_integration.execute_command("/analyze-code", {"focus": "performance"})
    print(f"Execution result: {result.success}, tokens used: {result.total_tokens_used}")

    # Get budget status
    status = adaptive_integration.get_budget_status()
    print(f"Budget status: {status}")

    return config, integration, adaptive_config, adaptive_integration


if __name__ == "__main__":
    # Run example usage
    example_usage()