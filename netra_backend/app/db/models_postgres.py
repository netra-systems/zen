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

# Import agent state models
from netra_backend.app.db.models_agent_state import (
    AgentStateSnapshot,
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

# Import agent execution model
from netra_backend.app.models.agent_execution import AgentExecution

# Stub models for compatibility
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

class CreditTransaction(Base):
    """Credit transaction model stub."""
    __tablename__ = 'credit_transactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'))  # FIX: Changed from Integer to String to match User.id type
    amount = Column(Float, nullable=False)
    transaction_type = Column(String(50), nullable=False)  # 'credit' or 'debit'
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="credit_transactions")

class Subscription(Base):
    """Subscription model stub."""
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'))  # FIX: Changed from Integer to String to match User.id type
    plan_name = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default='active')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    
    user = relationship("User", back_populates="subscriptions")

# Re-export all models for backward compatibility
__all__ = [
    # Base class
    'Base',
    
    # User models
    'User',
    'Secret',
    'ToolUsageLog',
    'CreditTransaction',
    'Subscription',
    
    # Supply models
    'Supply',
    'SupplyOption',
    'AvailabilityStatus',
    'AISupplyItem',
    'ResearchSessionStatus',
    'ResearchSession',
    'SupplyUpdateLog',
    
    # Agent models
    'AgentExecution',
    'Assistant',
    'Thread',
    'Message',
    'Run',
    'Step',
    'ApexOptimizerAgentRun',
    'ApexOptimizerAgentRunReport',
    
    # Agent state models
    'AgentStateSnapshot',
    
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