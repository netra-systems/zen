"""Technical debt metrics calculator.

Calculates code smells, duplication, and complexity metrics.
Follows 450-line limit with 25-line function limit.

This module imports from the canonical TechnicalDebtCalculator implementation.
"""

# Import from canonical source
from netra_backend.app.technical_debt_calculator import TechnicalDebtCalculator

# Re-export for backwards compatibility
__all__ = ['TechnicalDebtCalculator']