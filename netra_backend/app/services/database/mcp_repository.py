"""MCP Repository Implementation

Provides database operations for MCP clients and tool executions.
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.database.base_repository import BaseRepository

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
        self.created_at = kwargs.get('created_at', datetime.now(UTC))
        self.last_active = kwargs.get('last_active', datetime.now(UTC))


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
        self.created_at = kwargs.get('created_at', datetime.now(UTC))


class MCPClientRepository(BaseRepository[MCPClientModel]):
    """Repository for MCP client operations"""
    
    def __init__(self):
        super().__init__(MCPClientModel)
        self._clients_cache: Dict[str, MCPClientModel] = {}
    
    def _hash_api_key(self, api_key: Optional[str]) -> Optional[str]:
        """Hash API key if provided"""
        if not api_key:
            return None
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def _cache_client(self, client: MCPClientModel, client_type: str) -> None:
        """Cache client and log creation"""
        self._clients_cache[client.id] = client
        logger.info(f"Created MCP client: {client.id} ({client_type})")
    
    async def _create_client_record(
        self,
        db: AsyncSession,
        name: str,
        client_type: str,
        api_key_hash: Optional[str],
        permissions: List[str],
        metadata: Dict[str, Any]
    ) -> Optional[MCPClientModel]:
        """Create client database record"""
        return await self.create(
            db=db,
            name=name,
            client_type=client_type,
            api_key_hash=api_key_hash,
            permissions=permissions or [],
            metadata=metadata or {}
        )
    
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
            api_key_hash = self._hash_api_key(api_key)
            client = await self._create_client_record(
                db, name, client_type, api_key_hash, permissions, metadata
            )
            if client:
                self._cache_client(client, client_type)
            return client
        except Exception as e:
            logger.error(f"Error creating MCP client: {e}")
            return None
    
    def _get_cached_client(self, client_id: str) -> Optional[MCPClientModel]:
        """Get client from cache"""
        return self._clients_cache.get(client_id)
    
    async def _fetch_and_cache_client(
        self, db: AsyncSession, client_id: str
    ) -> Optional[MCPClientModel]:
        """Fetch client from database and cache it"""
        client = await self.get_by_id(db=db, entity_id=client_id)
        if client:
            self._clients_cache[client_id] = client
        return client
    
    async def get_client(
        self,
        db: AsyncSession,
        client_id: str
    ) -> Optional[MCPClientModel]:
        """Get MCP client by ID"""
        cached_client = self._get_cached_client(client_id)
        if cached_client:
            return cached_client
        return await self._fetch_and_cache_client(db, client_id)
    
    def _has_admin_permissions(self, permissions: List[str]) -> bool:
        """Check if client has admin or wildcard permissions"""
        return '*' in permissions or 'admin' in permissions
    
    def _check_specific_permission(
        self, permissions: List[str], required_permission: str
    ) -> bool:
        """Check if client has specific permission"""
        return (
            self._has_admin_permissions(permissions) or
            required_permission in permissions
        )
    
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
        return self._check_specific_permission(client.permissions, required_permission)
    
    async def _update_client_timestamp(
        self, db: AsyncSession, client: MCPClientModel
    ) -> bool:
        """Update client timestamp and commit"""
        client.last_active = datetime.now(UTC)
        await db.commit()
        return True
    
    async def _handle_update_error(
        self, db: AsyncSession, error: Exception
    ) -> bool:
        """Handle update error with rollback"""
        logger.error(f"Error updating client last_active: {error}")
        await db.rollback()
        return False
    
    async def update_last_active(
        self,
        db: AsyncSession,
        client_id: str
    ) -> bool:
        """Update client's last active timestamp"""
        try:
            client = await self.get_client(db, client_id)
            if not client:
                return False
            return await self._update_client_timestamp(db, client)
        except Exception as e:
            return await self._handle_update_error(db, e)
    
    async def find_by_user(self, db: AsyncSession, user_id: str) -> List[MCPClientModel]:
        """Find MCP clients by user ID"""
        try:
            # For now, return all clients as MCP clients aren't user-specific yet
            # In the future, could filter by user permissions or associations
            return list(self._clients_cache.values())
        except Exception as e:
            logger.error(f"Error finding MCP clients by user {user_id}: {e}")
            return []


class MCPToolExecutionRepository(BaseRepository[MCPToolExecutionModel]):
    """Repository for MCP tool execution records"""
    
    def __init__(self):
        super().__init__(MCPToolExecutionModel)
    
    async def _create_execution_record(
        self,
        db: AsyncSession,
        session_id: str,
        client_id: str,
        tool_name: str,
        input_params: Dict[str, Any],
        execution_time_ms: int,
        status: str
    ) -> Optional[MCPToolExecutionModel]:
        """Create execution database record"""
        return await self.create(
            db=db,
            session_id=session_id,
            client_id=client_id,
            tool_name=tool_name,
            input_params=input_params,
            execution_time_ms=execution_time_ms,
            status=status
        )
    
    def _log_execution_success(self, tool_name: str, session_id: str) -> None:
        """Log successful execution creation"""
        logger.info(f"Recorded tool execution: {tool_name} for session {session_id}")
    
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
            execution = await self._create_execution_record(
                db, session_id, client_id, tool_name, input_params, execution_time_ms, status
            )
            if execution:
                self._log_execution_success(tool_name, session_id)
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
            # Query database for session executions
            from sqlalchemy import select

            from netra_backend.app.db.models_mcp import MCPToolExecution
            result = await db.execute(
                select(MCPToolExecution).where(
                    MCPToolExecution.session_id == session_id
                ).order_by(MCPToolExecution.created_at.desc())
            )
            return result.scalars().all()
            
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
            # Query database for client executions
            from sqlalchemy import select

            from netra_backend.app.db.models_mcp import MCPToolExecution
            result = await db.execute(
                select(MCPToolExecution).where(
                    MCPToolExecution.client_id == client_id
                ).order_by(MCPToolExecution.created_at.desc()).limit(limit)
            )
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting client executions: {e}")
            return []
    
    async def find_by_user(self, db: AsyncSession, user_id: str) -> List[MCPToolExecutionModel]:
        """Find MCP tool executions by user ID"""
        try:
            # For now, return empty list as tool executions aren't user-specific yet
            # In the future, could filter by user through client associations
            return []
        except Exception as e:
            logger.error(f"Error finding MCP executions by user {user_id}: {e}")
            return []