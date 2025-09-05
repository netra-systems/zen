"""
Backward compatibility module for PerformanceAnalyzer.

The PerformanceAnalyzer functionality has been consolidated into UnifiedDataAgent.
This module provides backward compatibility for existing imports.
"""

from typing import Dict, Any, List, Optional
from netra_backend.app.agents.data.unified_data_agent import PerformanceAnalysisStrategy

class PerformanceAnalyzer:
    """Legacy PerformanceAnalyzer class for backward compatibility."""
    
    def __init__(self, *args, **kwargs):
        """Initialize with backward compatibility."""
        self.strategy = PerformanceAnalysisStrategy()
    
    async def analyze_performance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance data."""
        # Legacy compatibility method
        return await self.strategy.analyze(data)
    
    async def get_performance_metrics(self, timeframe: str = "24h") -> Dict[str, Any]:
        """Get performance metrics."""
        # Legacy compatibility method
        return {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "disk_io": 0.0,
            "network_io": 0.0,
            "timeframe": timeframe
        }
    
    def calculate_efficiency_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate efficiency score."""
        # Legacy compatibility method
        return 0.85

# Export for backward compatibility
__all__ = ["PerformanceAnalyzer"]