"""PostgreSQL database models integration module.

Main module that imports and exposes all models from focused sub-modules.
Maintains backward compatibility while adhering to modular architecture.
"""

# Import Base class for SQLAlchemy models
from .base import Base

# Import user and authentication models
from .models_user import (
    User,
    Secret,
    ToolUsageLog
)

# Import supply and research models
from .models_supply import (
    Supply,
    SupplyOption,
    AvailabilityStatus,
    AISupplyItem,
    ResearchSessionStatus,
    ResearchSession,
    SupplyUpdateLog
)

# Import agent and assistant models
from .models_agent import (
    Assistant,
    Thread,
    Message,
    Run,
    Step,
    ApexOptimizerAgentRun,
    ApexOptimizerAgentRunReport
)

# Import content and corpus models
from .models_content import (
    CorpusAuditLog,
    Analysis,
    AnalysisResult,
    Reference,
    Corpus
)

# Re-export all models for backward compatibility
__all__ = [
    # Base class
    'Base',
    
    # User models
    'User',
    'Secret',
    'ToolUsageLog',
    
    # Supply models
    'Supply',
    'SupplyOption',
    'AvailabilityStatus',
    'AISupplyItem',
    'ResearchSessionStatus',
    'ResearchSession',
    'SupplyUpdateLog',
    
    # Agent models
    'Assistant',
    'Thread',
    'Message',
    'Run',
    'Step',
    'ApexOptimizerAgentRun',
    'ApexOptimizerAgentRunReport',
    
    # Content models
    'CorpusAuditLog',
    'Analysis',
    'AnalysisResult',
    'Reference',
    'Corpus'
]