"""Token budget data models - enhanced implementation with cost support."""

from typing import Dict, Optional, Union
from enum import Enum

class BudgetType(Enum):
    """Types of budget tracking supported."""
    TOKENS = "tokens"
    COST = "cost"
    MIXED = "mixed"

class CommandBudgetInfo:
    """Tracks the budget status for a single command with support for both tokens and cost."""

    def __init__(self, limit: Union[int, float], used: Union[int, float] = 0,
                 budget_type: BudgetType = BudgetType.TOKENS):
        """
        Initialize command budget info.

        Args:
            limit: Budget limit (tokens as int, cost as float)
            used: Current usage (tokens as int, cost as float)
            budget_type: Type of budget (tokens, cost, or mixed)
        """
        self.limit = limit
        self.used = used
        self.budget_type = budget_type

    @property
    def remaining(self) -> Union[int, float]:
        """Get remaining budget amount."""
        return self.limit - self.used

    @property
    def percentage(self) -> float:
        """Get percentage of budget used."""
        return (self.used / self.limit * 100) if self.limit > 0 else 0

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
        """Check if this is a mixed budget (both tokens and cost)."""
        return self.budget_type == BudgetType.MIXED

    def format_limit(self) -> str:
        """Format the limit for display."""
        if self.is_cost_budget:
            return f"${self.limit:.4f}"
        else:
            return f"{int(self.limit)} tokens"

    def format_used(self) -> str:
        """Format the used amount for display."""
        if self.is_cost_budget:
            return f"${self.used:.4f}"
        else:
            return f"{int(self.used)} tokens"

    def format_remaining(self) -> str:
        """Format the remaining amount for display."""
        remaining = self.remaining
        if self.is_cost_budget:
            return f"${remaining:.4f}"
        else:
            return f"{int(remaining)} tokens"