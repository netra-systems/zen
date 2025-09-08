"""
Database Models Module for Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Enable integration tests to create database tables properly
- Value Impact: Fix critical auth integration test database setup failures
- Strategic Impact: Essential for reliable integration testing infrastructure

This module provides a unified import point for database models and Base class
specifically for integration testing. It ensures all SQLAlchemy models are 
accessible and the Base metadata can create all tables properly.

CRITICAL: This module is specifically designed to fix the "no such table: users"
error in auth integration tests by providing the correct Base import path
that the lightweight_services fixture expects.
"""

# Import the Base class from the canonical source
from netra_backend.app.db.base import Base

# Import all database models to ensure they're registered with Base.metadata
from netra_backend.app.db.models_postgres import (
    # User models
    User,
    Secret,
    ToolUsageLog,
    CreditTransaction,
    Subscription,
    
    # Supply models
    Supply,
    SupplyOption,
    AvailabilityStatus,
    AISupplyItem,
    ResearchSessionStatus,
    ResearchSession,
    SupplyUpdateLog,
    
    # Agent models
    AgentExecution,
    Assistant,
    Thread,
    Message,
    Run,
    Step,
    ApexOptimizerAgentRun,
    ApexOptimizerAgentRunReport,
    
    # Agent state models
    AgentStateSnapshot,
    
    # Content models
    CorpusAuditLog,
    Analysis,
    AnalysisResult,
    Reference,
    Corpus,
    
    # MCP Client models
    MCPExternalServer,
    MCPToolExecution,
    MCPResourceAccess
)

# Re-export Base and all models for integration tests
__all__ = [
    # Base class - CRITICAL for table creation
    'Base',
    
    # User models - CRITICAL for auth integration tests
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