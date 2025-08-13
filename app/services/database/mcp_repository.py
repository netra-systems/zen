"""MCP Repository Implementation

Provides database operations for MCP clients and tool executions.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from app.services.database.base_repository import BaseRepository
from app.logging_config import central_logger
import hashlib
import json

logger = central_logger.get_logger(__name__)


class MCPClientModel:
    """Database model for MCP clients"""
    __tablename__ = 'mcp_clients'
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.name = kwargs.get('name')
        self.client_type = kwargs.get('client_type')
        self.api_key_hash = kwargs.get('api_key_hash')
        self.permissions = kwargs.get('permissions', [])
        self.metadata = kwargs.get('metadata', {})
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.last_active = kwargs.get('last_active', datetime.utcnow())


class MCPToolExecutionModel:
    """Database model for MCP tool executions"""
    __tablename__ = 'mcp_tool_executions'
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.session_id = kwargs.get('session_id')
        self.client_id = kwargs.get('client_id')
        self.tool_name = kwargs.get('tool_name')
        self.input_params = kwargs.get('input_params', {})
        self.output_result = kwargs.get('output_result')
        self.execution_time_ms = kwargs.get('execution_time_ms', 0)
        self.status = kwargs.get('status', 'pending')
        self.error = kwargs.get('error')
        self.created_at = kwargs.get('created_at', datetime.utcnow())


class MCPClientRepository(BaseRepository[MCPClientModel]):
    """Repository for MCP client operations"""
    
    def __init__(self):
        super().__init__(MCPClientModel)
        self._clients_cache: Dict[str, MCPClientModel] = {}
    
    async def create_client(
        self,
        db: AsyncSession,
        name: str,
        client_type: str,
        api_key: Optional[str] = None,
        permissions: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Optional[MCPClientModel]:
        """Create a new MCP client"""
        try:
            # Hash API key if provided
            api_key_hash = None
            if api_key:
                api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            client = await self.create(
                db=db,
                name=name,
                client_type=client_type,
                api_key_hash=api_key_hash,
                permissions=permissions or [],
                metadata=metadata or {}
            )
            
            if client:
                self._clients_cache[client.id] = client
                logger.info(f"Created MCP client: {client.id} ({client_type})")
            
            return client
            
        except Exception as e:
            logger.error(f"Error creating MCP client: {e}")
            return None
    
    async def get_client(
        self,
        db: AsyncSession,
        client_id: str
    ) -> Optional[MCPClientModel]:
        """Get MCP client by ID"""
        # Check cache first
        if client_id in self._clients_cache:
            return self._clients_cache[client_id]
        
        client = await self.get_by_id(db=db, entity_id=client_id)
        if client:
            self._clients_cache[client_id] = client
        
        return client
    
    async def validate_client_permission(
        self,
        db: AsyncSession,
        client_id: str,
        required_permission: str
    ) -> bool:
        """Check if client has required permission"""
        client = await self.get_client(db, client_id)
        
        if not client:
            return False
        
        # Check for wildcard permission
        if '*' in client.permissions or 'admin' in client.permissions:
            return True
        
        # Check specific permission
        return required_permission in client.permissions
    
    async def update_last_active(
        self,
        db: AsyncSession,
        client_id: str
    ) -> bool:
        """Update client's last active timestamp"""
        try:
            client = await self.get_client(db, client_id)
            if client:
                client.last_active = datetime.utcnow()
                await db.commit()
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error updating client last_active: {e}")
            await db.rollback()
            return False


class MCPToolExecutionRepository(BaseRepository[MCPToolExecutionModel]):
    """Repository for MCP tool execution records"""
    
    def __init__(self):
        super().__init__(MCPToolExecutionModel)
    
    async def record_execution(
        self,
        db: AsyncSession,
        session_id: str,
        client_id: str,
        tool_name: str,
        input_params: Dict[str, Any],
        execution_time_ms: int = 0,
        status: str = 'pending'
    ) -> Optional[MCPToolExecutionModel]:
        """Record a tool execution"""
        try:
            execution = await self.create(
                db=db,
                session_id=session_id,
                client_id=client_id,
                tool_name=tool_name,
                input_params=input_params,
                execution_time_ms=execution_time_ms,
                status=status
            )
            
            if execution:
                logger.info(f"Recorded tool execution: {tool_name} for session {session_id}")
            
            return execution
            
        except Exception as e:
            logger.error(f"Error recording tool execution: {e}")
            return None
    
    async def update_execution_result(
        self,
        db: AsyncSession,
        execution_id: str,
        output_result: Dict[str, Any],
        execution_time_ms: int,
        status: str = 'completed',
        error: str = None
    ) -> bool:
        """Update execution with result"""
        try:
            execution = await self.get_by_id(db=db, entity_id=execution_id)
            if execution:
                execution.output_result = output_result
                execution.execution_time_ms = execution_time_ms
                execution.status = status
                execution.error = error
                await db.commit()
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error updating execution result: {e}")
            await db.rollback()
            return False
    
    async def get_session_executions(
        self,
        db: AsyncSession,
        session_id: str
    ) -> List[MCPToolExecutionModel]:
        """Get all executions for a session"""
        try:
            # In production, this would use SQLAlchemy query
            # For now, return empty list as placeholder
            return []
            
        except Exception as e:
            logger.error(f"Error getting session executions: {e}")
            return []
    
    async def get_client_executions(
        self,
        db: AsyncSession,
        client_id: str,
        limit: int = 100
    ) -> List[MCPToolExecutionModel]:
        """Get recent executions for a client"""
        try:
            # In production, this would use SQLAlchemy query
            # For now, return empty list as placeholder
            return []
            
        except Exception as e:
            logger.error(f"Error getting client executions: {e}")
            return []