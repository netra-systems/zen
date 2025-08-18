"""MCP Client Repository for database operations.

Handles CRUD operations for MCP external servers, tool executions, and resource access.
Adheres to repository pattern and 300-line limit.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError

from app.services.database.base_repository import BaseRepository
from app.db.models_mcp_client import MCPExternalServer, MCPToolExecution, MCPResourceAccess
from app.schemas.mcp_client import MCPServerConfig, MCPServerInfo
from app.schemas.core_enums import MCPServerStatus, MCPToolExecutionStatus
from app.core.exceptions_database import (
    DatabaseError, DatabaseConstraintError, RecordNotFoundError
)
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MCPClientRepository(BaseRepository[MCPExternalServer]):
    """Repository for MCP client database operations."""
    
    def __init__(self):
        super().__init__(MCPExternalServer)
    
    def _create_server_instance(self, config: MCPServerConfig) -> MCPExternalServer:
        """Create server instance from config."""
        return MCPExternalServer(
            id=str(uuid.uuid4()),
            name=config.name,
            url=config.url,
            transport=config.transport.value,
            auth_type=config.auth.auth_type.value if config.auth else None
        )
    
    def _set_server_credentials_and_metadata(self, server: MCPExternalServer, config: MCPServerConfig):
        """Set credentials and metadata on server instance."""
        server.credentials = self._serialize_credentials(config.auth) if config.auth else None
        server.metadata_ = config.metadata or {}
        server.status = MCPServerStatus.REGISTERED.value
    
    async def create_server(self, db: AsyncSession, config: MCPServerConfig) -> MCPExternalServer:
        """Create a new MCP external server."""
        try:
            server = self._create_server_instance(config)
            self._set_server_credentials_and_metadata(server, config)
            return await self.create(db, server)
        except IntegrityError as e:
            logger.error(f"Server name already exists: {config.name}")
            raise DatabaseConstraintError(f"Server name '{config.name}' already exists")
    
    def _serialize_credentials(self, auth_config) -> Dict[str, Any]:
        """Serialize auth credentials for storage."""
        if not auth_config:
            return {}
        return {
            "api_key": auth_config.api_key,
            "oauth_config": auth_config.oauth_config,
            "environment_vars": auth_config.environment_vars
        }
    
    async def _execute_server_by_name_query(self, db: AsyncSession, name: str):
        """Execute query to find server by name."""
        return await db.execute(
            select(MCPExternalServer).where(MCPExternalServer.name == name)
        )
    
    async def get_server_by_name(self, db: AsyncSession, name: str) -> Optional[MCPExternalServer]:
        """Get server by name."""
        try:
            result = await self._execute_server_by_name_query(db, name)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting server by name: {e}")
            raise DatabaseError(f"Failed to get server: {str(e)}")
    
    async def list_servers(self, db: AsyncSession) -> List[MCPExternalServer]:
        """List all registered servers."""
        try:
            result = await db.execute(select(MCPExternalServer))
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error listing servers: {e}")
            raise DatabaseError(f"Failed to list servers: {str(e)}")
    
    async def _execute_server_status_update(self, db: AsyncSession, server_id: str, status: MCPServerStatus):
        """Execute server status update query."""
        return await db.execute(
            update(MCPExternalServer)
            .where(MCPExternalServer.id == server_id)
            .values(
                status=status.value,
                updated_at=datetime.now(timezone.utc)
            )
        )
    
    async def update_server_status(self, db: AsyncSession, server_id: str, 
                                 status: MCPServerStatus) -> bool:
        """Update server status."""
        try:
            result = await self._execute_server_status_update(db, server_id, status)
            await db.commit()
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating server status: {e}")
            raise DatabaseError(f"Failed to update server status: {str(e)}")
    
    async def _execute_health_check_update(self, db: AsyncSession, server_id: str):
        """Execute health check timestamp update query."""
        return await db.execute(
            update(MCPExternalServer)
            .where(MCPExternalServer.id == server_id)
            .values(last_health_check=datetime.now(timezone.utc))
        )
    
    async def update_health_check(self, db: AsyncSession, server_id: str) -> bool:
        """Update last health check timestamp."""
        try:
            result = await self._execute_health_check_update(db, server_id)
            await db.commit()
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating health check: {e}")
            raise DatabaseError(f"Failed to update health check: {str(e)}")
    
    async def _execute_server_delete(self, db: AsyncSession, server_id: str):
        """Execute server deletion query."""
        return await db.execute(
            delete(MCPExternalServer).where(MCPExternalServer.id == server_id)
        )
    
    async def delete_server(self, db: AsyncSession, server_id: str) -> bool:
        """Delete a server."""
        try:
            result = await self._execute_server_delete(db, server_id)
            await db.commit()
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting server: {e}")
            raise DatabaseError(f"Failed to delete server: {str(e)}")
    
    async def find_by_user(self, db: AsyncSession, user_id: str) -> List[MCPExternalServer]:
        """Find servers by user - returns all servers for now."""
        try:
            # For now, return all servers. In future, could filter by user permissions
            return await self.list_servers(db)
        except Exception as e:
            logger.error(f"Error finding servers by user: {e}")
            raise DatabaseError(f"Failed to find servers by user: {str(e)}")


class MCPToolExecutionRepository:
    """Repository for MCP tool execution tracking."""
    
    def _build_execution_base(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> MCPToolExecution:
        """Build base execution instance."""
        return MCPToolExecution(
            id=str(uuid.uuid4()),
            server_name=server_name,
            tool_name=tool_name,
            arguments=arguments
        )
    
    def _create_execution_instance(self, server_name: str, tool_name: str, 
                                 arguments: Dict[str, Any], user_id: Optional[str]) -> MCPToolExecution:
        """Create tool execution instance."""
        execution = self._build_execution_base(server_name, tool_name, arguments)
        execution.status = MCPToolExecutionStatus.PENDING.value
        execution.user_id = user_id
        return execution
    
    async def _persist_execution(self, db: AsyncSession, execution: MCPToolExecution) -> MCPToolExecution:
        """Persist execution to database."""
        db.add(execution)
        await db.commit()
        await db.refresh(execution)
        return execution
    
    async def create_execution(self, db: AsyncSession, server_name: str, 
                             tool_name: str, arguments: Dict[str, Any],
                             user_id: Optional[str] = None) -> MCPToolExecution:
        """Create a new tool execution record."""
        try:
            execution = self._create_execution_instance(server_name, tool_name, arguments, user_id)
            return await self._persist_execution(db, execution)
        except Exception as e:
            logger.error(f"Error creating tool execution: {e}")
            raise DatabaseError(f"Failed to create tool execution: {str(e)}")
    
    def _build_execution_update_values(self, result: Dict[str, Any], status: MCPToolExecutionStatus,
                                     execution_time_ms: Optional[int], error_message: Optional[str]) -> Dict[str, Any]:
        """Build update values for execution result."""
        return {
            "result": result,
            "status": status.value,
            "execution_time_ms": execution_time_ms,
            "error_message": error_message
        }
    
    async def _execute_execution_result_update(self, db: AsyncSession, execution_id: str, update_values: Dict[str, Any]):
        """Execute execution result update query."""
        return await db.execute(
            update(MCPToolExecution)
            .where(MCPToolExecution.id == execution_id)
            .values(**update_values)
        )
    
    async def update_execution_result(self, db: AsyncSession, execution_id: str,
                                    result: Dict[str, Any], status: MCPToolExecutionStatus,
                                    execution_time_ms: Optional[int] = None,
                                    error_message: Optional[str] = None) -> bool:
        """Update tool execution with result."""
        try:
            update_values = self._build_execution_update_values(result, status, execution_time_ms, error_message)
            query_result = await self._execute_execution_result_update(db, execution_id, update_values)
            await db.commit()
            return query_result.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating execution result: {e}")
            raise DatabaseError(f"Failed to update execution result: {str(e)}")


class MCPResourceAccessRepository:
    """Repository for MCP resource access tracking."""
    
    def _create_access_instance(self, server_name: str, resource_uri: str, user_id: Optional[str]) -> MCPResourceAccess:
        """Create resource access instance."""
        return MCPResourceAccess(
            id=str(uuid.uuid4()),
            server_name=server_name,
            resource_uri=resource_uri,
            status="accessed",
            user_id=user_id
        )
    
    async def _persist_access_record(self, db: AsyncSession, access: MCPResourceAccess) -> MCPResourceAccess:
        """Persist access record to database."""
        db.add(access)
        await db.commit()
        await db.refresh(access)
        return access
    
    async def create_access_record(self, db: AsyncSession, server_name: str,
                                 resource_uri: str, user_id: Optional[str] = None) -> MCPResourceAccess:
        """Create a new resource access record."""
        try:
            access = self._create_access_instance(server_name, resource_uri, user_id)
            return await self._persist_access_record(db, access)
        except Exception as e:
            logger.error(f"Error creating resource access record: {e}")
            raise DatabaseError(f"Failed to create resource access record: {str(e)}")
    
    async def _execute_find_access_by_user_query(self, db: AsyncSession, user_id: str):
        """Execute query to find access records by user."""
        return await db.execute(
            select(MCPResourceAccess).where(MCPResourceAccess.user_id == user_id)
        )
    
    async def find_by_user(self, db: AsyncSession, user_id: str) -> List[MCPResourceAccess]:
        """Find resource access records by user."""
        try:
            result = await self._execute_find_access_by_user_query(db, user_id)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error finding resource access by user: {e}")
            raise DatabaseError(f"Failed to find resource access: {str(e)}")