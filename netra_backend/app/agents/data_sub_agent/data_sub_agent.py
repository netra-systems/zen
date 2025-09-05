"""
Backward compatibility module for DataSubAgent.

The DataSubAgent has been consolidated into UnifiedDataAgent.
This module provides backward compatibility for existing imports.
"""

# Backward compatibility imports - redirecting to unified agent
from netra_backend.app.agents.data.unified_data_agent import UnifiedDataAgent

# Legacy class alias for backward compatibility
DataSubAgent = UnifiedDataAgent

# Export for backward compatibility
__all__ = ["DataSubAgent"]