"""Token budget data models - simplified implementation."""

from typing import Dict, Optional

class CommandBudgetInfo:
    """Tracks the budget status for a single command."""

    def __init__(self, limit: int):
        self.limit = limit
        self.used = 0

    @property
    def remaining(self) -> int:
        return self.limit - self.used

    @property
    def percentage(self) -> float:
        return (self.used / self.limit * 100) if self.limit > 0 else 0