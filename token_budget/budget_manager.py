"""Token budget manager - enhanced implementation with cost support."""

from .models import CommandBudgetInfo, BudgetType
from typing import Dict, Optional, List, Union
import sys
from pathlib import Path

# Import ClaudePricingEngine for cost calculations
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from token_transparency import ClaudePricingEngine, TokenUsageData
except ImportError:
    ClaudePricingEngine = None
    TokenUsageData = None

class TokenBudgetManager:
    """Manages budgets for overall session and individual commands with support for both tokens and cost."""

    def __init__(self, overall_budget: Optional[Union[int, float]] = None,
                 enforcement_mode: str = "warn",
                 budget_type: Union[str, BudgetType] = BudgetType.TOKENS,
                 overall_cost_budget: Optional[float] = None):
        """
        Initialize the budget manager.

        Args:
            overall_budget: Overall token budget (backward compatibility)
            enforcement_mode: Action when budget exceeded ("warn" or "block")
            budget_type: Type of budget ("tokens", "cost", or "mixed")
            overall_cost_budget: Overall cost budget in USD
        """
        # Handle backward compatibility
        if overall_cost_budget is not None:
            self.overall_budget = overall_cost_budget
            self.budget_type = BudgetType.COST
        else:
            self.overall_budget = overall_budget
            if isinstance(budget_type, str):
                self.budget_type = BudgetType(budget_type.lower())
            else:
                self.budget_type = budget_type

        self.enforcement_mode = enforcement_mode
        self.command_budgets: Dict[str, CommandBudgetInfo] = {}
        self.total_usage: Union[int, float] = 0.0 if self.is_cost_budget else 0

        # Initialize pricing engine if needed for cost calculations
        self.pricing_engine = None
        if ClaudePricingEngine and (self.is_cost_budget or self.is_mixed_budget):
            self.pricing_engine = ClaudePricingEngine()

    @property
    def is_token_budget(self) -> bool:
        """Check if this is a token-based budget."""
        return self.budget_type == BudgetType.TOKENS

    @property
    def is_cost_budget(self) -> bool:
        """Check if this is a cost-based budget."""
        return self.budget_type == BudgetType.COST

    @property
    def is_mixed_budget(self) -> bool:
        """Check if this is a mixed budget."""
        return self.budget_type == BudgetType.MIXED

    def set_command_budget(self, command_name: str, limit: int):
        """Sets the token budget for a specific command (backward compatibility)."""
        if command_name in self.command_budgets:
            # Preserve existing usage when updating budget limit
            existing_usage = self.command_budgets[command_name].used
            self.command_budgets[command_name] = CommandBudgetInfo(
                limit=limit, used=existing_usage, budget_type=BudgetType.TOKENS)
        else:
            self.command_budgets[command_name] = CommandBudgetInfo(
                limit=limit, budget_type=BudgetType.TOKENS)

    def set_command_cost_budget(self, command_name: str, limit: float):
        """Sets the cost budget for a specific command in USD."""
        if command_name in self.command_budgets:
            # Preserve existing usage when updating budget limit
            existing_usage = self.command_budgets[command_name].used
            self.command_budgets[command_name] = CommandBudgetInfo(
                limit=limit, used=existing_usage, budget_type=BudgetType.COST)
        else:
            self.command_budgets[command_name] = CommandBudgetInfo(
                limit=limit, budget_type=BudgetType.COST)

    def record_usage(self, command_name: str, tokens: int):
        """Records token usage for a command and updates the overall total (backward compatibility)."""
        if self.is_cost_budget and self.pricing_engine:
            # Convert tokens to cost for cost-based budgets
            cost = self.convert_tokens_to_cost(tokens)
            self.record_cost_usage(command_name, cost)
        else:
            # Traditional token usage
            self.total_usage += tokens
            if command_name in self.command_budgets:
                self.command_budgets[command_name].used += tokens

    def record_cost_usage(self, command_name: str, cost: float):
        """Records cost usage for a command and updates the overall total."""
        self.total_usage += cost
        if command_name in self.command_budgets:
            self.command_budgets[command_name].used += cost

    def check_budget(self, command_name: str, estimated_tokens: int) -> tuple[bool, str]:
        """Checks if a command can run based on its budget and the overall budget (backward compatibility).

        Returns:
            tuple: (can_run: bool, reason: str) - reason explains which budget would be exceeded
        """
        if self.is_cost_budget:
            # Convert tokens to cost for cost budget checking
            estimated_cost = self.convert_tokens_to_cost(estimated_tokens)
            return self.check_cost_budget(command_name, estimated_cost)
        else:
            return self._check_token_budget(command_name, estimated_tokens)

    def check_cost_budget(self, command_name: str, estimated_cost: float) -> tuple[bool, str]:
        """Checks if a command can run based on cost budgets.

        Returns:
            tuple: (can_run: bool, reason: str) - reason explains which budget would be exceeded
        """
        # Check overall cost budget FIRST (takes precedence)
        if self.overall_budget is not None and (self.total_usage + estimated_cost) > self.overall_budget:
            projected_total = self.total_usage + estimated_cost
            return False, f"Overall cost budget exceeded: ${projected_total:.4f}/${self.overall_budget:.4f}"

        # Check per-command cost budget
        if command_name in self.command_budgets:
            command_budget = self.command_budgets[command_name]
            if command_budget.is_cost_budget and (command_budget.used + estimated_cost) > command_budget.limit:
                projected_command = command_budget.used + estimated_cost
                return False, f"Command '{command_name}' cost budget exceeded: ${projected_command:.4f}/${command_budget.limit:.4f}"

        return True, "Within cost budget limits"

    def _check_token_budget(self, command_name: str, estimated_tokens: int) -> tuple[bool, str]:
        """Internal method for checking token budgets."""
        # Check overall budget FIRST (takes precedence)
        if self.overall_budget is not None and (self.total_usage + estimated_tokens) > self.overall_budget:
            projected_total = self.total_usage + estimated_tokens
            return False, f"Overall budget exceeded: {projected_total}/{self.overall_budget} tokens"

        # Check per-command budget
        if command_name in self.command_budgets:
            command_budget = self.command_budgets[command_name]
            if command_budget.is_token_budget and (command_budget.used + estimated_tokens) > command_budget.limit:
                projected_command = command_budget.used + estimated_tokens
                return False, f"Command '{command_name}' budget exceeded: {projected_command}/{command_budget.limit} tokens"

        return True, "Within budget limits"

    def convert_tokens_to_cost(self, tokens: int, model: str = "claude-3-5-sonnet") -> float:
        """Convert tokens to cost using the pricing engine."""
        if not self.pricing_engine:
            raise AttributeError("Pricing engine not available for cost conversion")

        # Create usage data for cost calculation
        # Assume equal split between input and output tokens for estimation
        input_tokens = int(tokens * 0.6)  # Estimate 60% input
        output_tokens = tokens - input_tokens  # Remaining 40% output

        usage_data = TokenUsageData(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model
        )

        cost_breakdown = self.pricing_engine.calculate_cost(usage_data)
        return cost_breakdown.total_cost

    def convert_cost_to_tokens(self, cost: float, model: str = "claude-3-5-sonnet") -> int:
        """Convert cost to approximate token count using the pricing engine."""
        if not self.pricing_engine:
            raise AttributeError("Pricing engine not available for cost conversion")

        # Get model pricing
        model_pricing = self.pricing_engine.pricing_config.MODEL_PRICING.get(
            model, self.pricing_engine.pricing_config.MODEL_PRICING["claude-3-5-sonnet"]
        )

        # Use average of input and output pricing for estimation
        avg_price_per_million = (model_pricing["input"] + model_pricing["output"]) / 2
        tokens = int((cost / avg_price_per_million) * 1_000_000)

        return tokens

    def set_budget_parameter_type(self, budget_type: Union[str, BudgetType]):
        """Set the budget parameter type (tokens, cost, or mixed)."""
        if isinstance(budget_type, str):
            self.budget_type = BudgetType(budget_type.lower())
        else:
            self.budget_type = budget_type

        # Initialize pricing engine if switching to cost or mixed mode
        if ClaudePricingEngine and (self.is_cost_budget or self.is_mixed_budget) and not self.pricing_engine:
            self.pricing_engine = ClaudePricingEngine()