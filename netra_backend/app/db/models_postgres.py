"""PostgreSQL database models integration module.

Main module that imports and exposes all models from focused sub-modules.
Maintains backward compatibility while adhering to modular architecture.
"""

# Import Base class for SQLAlchemy models
from netra_backend.app.db.base import Base

# Import agent and assistant models
from netra_backend.app.db.models_agent import (
    ApexOptimizerAgentRun,
    ApexOptimizerAgentRunReport,
    Assistant,
    Message,
    Run,
    Step,
    Thread,
)

# Import content and corpus models
from netra_backend.app.db.models_content import (
    Analysis,
    AnalysisResult,
    Corpus,
    CorpusAuditLog,
    Reference,
)

# Import MCP client models
from netra_backend.app.db.models_mcp_client import (
    MCPExternalServer,
    MCPResourceAccess,
    MCPToolExecution,
)

# Import supply and research models
from netra_backend.app.db.models_supply import (
    AISupplyItem,
    AvailabilityStatus,
    ResearchSession,
    ResearchSessionStatus,
    Supply,
    SupplyOption,
    SupplyUpdateLog,
)

# Import user and authentication models
from netra_backend.app.db.models_user import Secret, ToolUsageLog, User

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
    'Corpus',
    
    # MCP Client models
    'MCPExternalServer',
    'MCPToolExecution',
    'MCPResourceAccess'
]