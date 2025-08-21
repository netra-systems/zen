"""Output Formatter Module.

Backwards compatibility import for refactored output formatters.
This module now delegates to the modular components.
"""

# Import the refactored formatter for backwards compatibility
from netra_backend.app.agents.github_analyzer.output_formatters import AIOperationsMapFormatter

# Maintain the same interface for existing code
__all__ = ['AIOperationsMapFormatter']