"""
Agent Types and Enums - SSOT Module for Issue #1034

This module provides the canonical definitions for all agent-related types and enums.
It serves as the Single Source of Truth (SSOT) for:
- AgentStatus enum
- AgentType enum  
- AgentInfo dataclass

This eliminates the SSOT violation where these types were duplicated between:
- netra_backend.app.agents.registry (deprecated)
- netra_backend.app.agents.supervisor.agent_registry (enhanced)

Business Value Justification (BVJ):
- Segment: Platform Infrastructure
- Business Goal: Eliminate SSOT violations blocking Golden Path
- Value Impact: Enables reliable $500K+ ARR chat functionality
- Strategic Impact: Foundation for consistent agent management

Created: 2025-09-14 (Issue #1034 SSOT consolidation)
"""

from datetime import datetime
from typing import Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class AgentStatus(Enum):
    """Agent status enumeration - SSOT definition."""
    IDLE = "idle"
    BUSY = "busy"
    INITIALIZING = "initializing"
    ERROR = "error"
    OFFLINE = "offline"


class AgentType(Enum):
    """Agent type enumeration - SSOT definition."""
    SUPERVISOR = "supervisor"
    TRIAGE = "triage"
    DATA_HELPER = "data_helper"
    OPTIMIZER = "optimizer"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    SYNTHETIC_DATA = "synthetic_data"
    CORPUS_ADMIN = "corpus_admin"


@dataclass
class AgentInfo:
    """Agent information structure - SSOT definition."""
    agent_id: str
    agent_type: AgentType
    name: str
    description: str
    status: AgentStatus = AgentStatus.IDLE
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    execution_count: int = 0
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "metadata": self.metadata
        }


# Export all public types for SSOT compliance
__all__ = [
    'AgentStatus',
    'AgentType', 
    'AgentInfo'
]