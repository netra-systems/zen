"""Token budget manager - simplified implementation."""

from .models import CommandBudgetInfo
from typing import Dict, Optional, List

class TokenBudgetManager:
    """Manages token budgets for overall session and individual commands."""

    def __init__(self, overall_budget: Optional[int] = None, enforcement_mode: str = "warn"):
        self.overall_budget = overall_budget
        self.enforcement_mode = enforcement_mode
        self.command_budgets: Dict[str, CommandBudgetInfo] = {}
        self.total_usage: int = 0

    def set_command_budget(self, command_name: str, limit: int):
        """Sets the token budget for a specific command."""
        if command_name not in self.command_budgets:
            self.command_budgets[command_name] = CommandBudgetInfo(limit=limit)

    def record_usage(self, command_name: str, tokens: int):
        """Records token usage for a command and updates the overall total."""
        self.total_usage += tokens
        if command_name in self.command_budgets:
            self.command_budgets[command_name].used += tokens

    def check_budget(self, command_name: str, estimated_tokens: int) -> bool:
        """Checks if a command can run based on its budget and the overall budget."""
        # Check overall budget
        if self.overall_budget is not None and (self.total_usage + estimated_tokens) > self.overall_budget:
            return False

        # Check per-command budget
        if command_name in self.command_budgets:
            command_budget = self.command_budgets[command_name]
            if (command_budget.used + estimated_tokens) > command_budget.limit:
                return False

        return True