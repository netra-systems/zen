"""
AgentExecution Model for Database Operations

This module provides the database model for agent execution tracking
and persistence across the Netra platform.

Business Value:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Agent execution audit trail and analytics
- Value Impact: Enables execution monitoring and optimization
- Strategic Impact: Foundation for execution insights and billing
"""

from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, Float
from sqlalchemy.sql import func
from netra_backend.app.db.database import Base
from typing import Dict, Any, Optional
from datetime import datetime
import uuid


class AgentExecution(Base):
    """Model for tracking agent execution records."""
    
    __tablename__ = "agent_executions"
    
    # Primary identification
    id = Column(String(50), primary_key=True, default=lambda: f"exec_{uuid.uuid4().hex[:12]}")
    user_id = Column(String(50), nullable=False, index=True)
    agent_id = Column(String(100), nullable=False, index=True)
    
    # Execution metadata
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending, running, completed, failed
    start_time = Column(DateTime(timezone=True), nullable=False, default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Execution details
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Performance metrics
    tokens_used = Column(Integer, nullable=True, default=0)
    api_calls_made = Column(Integer, nullable=True, default=0)
    cost_cents = Column(Integer, nullable=True, default=0)
    
    # Context and tracking
    thread_id = Column(String(50), nullable=True, index=True)
    workflow_id = Column(String(50), nullable=True, index=True)
    execution_context = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent execution to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "tokens_used": self.tokens_used,
            "api_calls_made": self.api_calls_made,
            "cost_cents": self.cost_cents,
            "thread_id": self.thread_id,
            "workflow_id": self.workflow_id,
            "execution_context": self.execution_context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def create_execution_record(
        cls,
        user_id: str,
        agent_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        thread_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> "AgentExecution":
        """Create a new agent execution record."""
        return cls(
            user_id=user_id,
            agent_id=agent_id,
            input_data=input_data,
            thread_id=thread_id,
            workflow_id=workflow_id,
            execution_context=execution_context,
            status="pending"
        )
    
    def mark_started(self):
        """Mark execution as started."""
        self.status = "running"
        self.start_time = datetime.utcnow()
    
    def mark_completed(
        self,
        output_data: Optional[Dict[str, Any]] = None,
        tokens_used: int = 0,
        api_calls_made: int = 0,
        cost_cents: int = 0
    ):
        """Mark execution as completed."""
        self.status = "completed"
        self.end_time = datetime.utcnow()
        if self.start_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        
        if output_data:
            self.output_data = output_data
        
        self.tokens_used = tokens_used
        self.api_calls_made = api_calls_made
        self.cost_cents = cost_cents
    
    def mark_failed(self, error_message: str):
        """Mark execution as failed."""
        self.status = "failed"
        self.end_time = datetime.utcnow()
        if self.start_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        
        self.error_message = error_message
    
    def __repr__(self):
        return f"<AgentExecution(id='{self.id}', user_id='{self.user_id}', agent_id='{self.agent_id}', status='{self.status}')>"