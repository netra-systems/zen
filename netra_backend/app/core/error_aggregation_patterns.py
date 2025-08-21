"""Error trend analysis and pattern detection - Backward Compatibility Module.

This module maintains backward compatibility while using the new modular 
architecture. Import from this module will work as before but use the 
optimized component modules underneath.
"""

# Re-export the main analyzer from the new modular structure
from app.core.error_trend_analyzer import ErrorTrendAnalyzer

# Maintain backward compatibility
__all__ = ['ErrorTrendAnalyzer']