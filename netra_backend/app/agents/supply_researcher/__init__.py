"""
Supply Researcher Agent Module

Autonomous AI supply information research and updates with modular architecture.
Split into focused components under 450-line limit.
"""

# FIXME: from netra_backend.app.agents.supply_researcher.agent import SupplyResearcherAgent
from netra_backend.app.services.apex_optimizer_agent.models import ResearchType
from netra_backend.app.agents.corpus_admin.parsers import SupplyRequestParser
from netra_backend.app.agents.supply_researcher.research_engine import SupplyResearchEngine
from netra_backend.app.agents.supply_researcher.data_extractor import SupplyDataExtractor
from netra_backend.app.agents.supply_researcher.database_manager import SupplyDatabaseManager

__all__ = [
    # FIXME: "SupplyResearcherAgent",
    "ResearchType",
    "SupplyRequestParser", 
    "SupplyResearchEngine",
    "SupplyDataExtractor",
    "SupplyDatabaseManager"
]