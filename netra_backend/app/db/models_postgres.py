"""PostgreSQL database models integration module.

Main module that imports and exposes all models from focused sub-modules.
Maintains backward compatibility while adhering to modular architecture.
"""

# Import Base class for SQLAlchemy models
from netra_backend.app.base import Base

# Import user and authentication models
from netra_backend.app.models_user import (
    User,
    Secret,
    ToolUsageLog
)

# Import supply and research models
from netra_backend.app.models_supply import (
    Supply,
    SupplyOption,
    AvailabilityStatus,
    AISupplyItem,
    ResearchSessionStatus,
    ResearchSession,
    SupplyUpdateLog
)

# Import agent and assistant models
from netra_backend.app.models_agent import (
    Assistant,
    Thread,
    Message,
    Run,
    Step,
    ApexOptimizerAgentRun,
    ApexOptimizerAgentRunReport
)

# Import content and corpus models
from netra_backend.app.models_content import (
    CorpusAuditLog,
    Analysis,
    AnalysisResult,
    Reference,
    Corpus
)

# Import MCP client models
from netra_backend.app.models_mcp_client import (
    MCPExternalServer,
    MCPToolExecution,
    MCPResourceAccess
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
    'Corpus',
    
    # MCP Client models
    'MCPExternalServer',
    'MCPToolExecution',
    'MCPResourceAccess'
]