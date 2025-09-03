"""NACIS Tools module.

Date Created: 2025-01-22
Last Updated: 2025-01-29

Business Value: Provides tools for research, scoring, sandboxed execution, and data collection.
"""

from typing import Dict, Any

from netra_backend.app.tools.data_helper import DataHelper, create_data_helper
from netra_backend.app.tools.deep_research_api import DeepResearchAPI
from netra_backend.app.tools.reliability_scorer import ReliabilityScorer
from netra_backend.app.tools.sandboxed_interpreter import SandboxedInterpreter


def get_standard_tools() -> Dict[str, Any]:
    """Get standard tools available to all users.
    
    Returns:
        Dictionary mapping tool names to tool instances
    """
    return {
        "data_helper": DataHelper,
        "deep_research": DeepResearchAPI,
        "reliability_scorer": ReliabilityScorer,
        "sandboxed_interpreter": SandboxedInterpreter,
    }


__all__ = [
    "DataHelper",
    "create_data_helper",
    "DeepResearchAPI",
    "ReliabilityScorer", 
    "SandboxedInterpreter",
    "get_standard_tools",
]