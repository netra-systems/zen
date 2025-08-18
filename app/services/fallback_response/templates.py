"""Fallback Response Templates - Public interface for modular template system.

This module provides backward compatibility while delegating to the new modular
architecture with strong typing and 8-line function compliance.
"""

from .templates_core import TemplateManager

# Re-export the main class for backward compatibility
__all__ = ['TemplateManager']