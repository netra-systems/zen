"""
Supply Researcher Agent Module

Autonomous AI supply information research and updates with modular architecture.
Split into focused components under 450-line limit.
"""

from netra_backend.app.agent import SupplyResearcherAgent
from netra_backend.app.models import ResearchType
from netra_backend.app.parsers import SupplyRequestParser
from netra_backend.app.research_engine import SupplyResearchEngine
from netra_backend.app.data_extractor import SupplyDataExtractor
from netra_backend.app.database_manager import SupplyDatabaseManager

__all__ = [
    "SupplyResearcherAgent",
    "ResearchType",
    "SupplyRequestParser", 
    "SupplyResearchEngine",
    "SupplyDataExtractor",
    "SupplyDatabaseManager"
]