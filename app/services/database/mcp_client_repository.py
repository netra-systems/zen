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
    
    async def create_server(self, db: AsyncSession, config: MCPServerConfig) -> MCPExternalServer:
        """Create a new MCP external server."""
        try:
            server = MCPExternalServer(
                id=str(uuid.uuid4()),
                name=config.name,
                url=config.url,
                transport=config.transport.value,
                auth_type=config.auth.auth_type.value if config.auth else None,
                credentials=self._serialize_credentials(config.auth) if config.auth else None,
                metadata_=config.metadata or {},
                status=MCPServerStatus.REGISTERED.value
            )
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
    
    async def get_server_by_name(self, db: AsyncSession, name: str) -> Optional[MCPExternalServer]:
        """Get server by name."""
        try:
            result = await db.execute(
                select(MCPExternalServer).where(MCPExternalServer.name == name)
            )
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
    
    async def update_server_status(self, db: AsyncSession, server_id: str, 
                                 status: MCPServerStatus) -> bool:
        """Update server status."""
        try:
            result = await db.execute(
                update(MCPExternalServer)
                .where(MCPExternalServer.id == server_id)
                .values(
                    status=status.value,
                    updated_at=datetime.now(timezone.utc)
                )
            )
            await db.commit()
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating server status: {e}")
            raise DatabaseError(f"Failed to update server status: {str(e)}")
    
    async def update_health_check(self, db: AsyncSession, server_id: str) -> bool:
        """Update last health check timestamp."""
        try:
            result = await db.execute(
                update(MCPExternalServer)
                .where(MCPExternalServer.id == server_id)
                .values(last_health_check=datetime.now(timezone.utc))
            )
            await db.commit()
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating health check: {e}")
            raise DatabaseError(f"Failed to update health check: {str(e)}")
    
    async def delete_server(self, db: AsyncSession, server_id: str) -> bool:
        """Delete a server."""
        try:
            result = await db.execute(
                delete(MCPExternalServer).where(MCPExternalServer.id == server_id)
            )
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
    
    async def create_execution(self, db: AsyncSession, server_name: str, 
                             tool_name: str, arguments: Dict[str, Any],
                             user_id: Optional[str] = None) -> MCPToolExecution:
        """Create a new tool execution record."""
        try:
            execution = MCPToolExecution(
                id=str(uuid.uuid4()),
                server_name=server_name,
                tool_name=tool_name,
                arguments=arguments,
                status=MCPToolExecutionStatus.PENDING.value,
                user_id=user_id
            )
            db.add(execution)
            await db.commit()
            await db.refresh(execution)
            return execution
        except Exception as e:
            logger.error(f"Error creating tool execution: {e}")
            raise DatabaseError(f"Failed to create tool execution: {str(e)}")
    
    async def update_execution_result(self, db: AsyncSession, execution_id: str,
                                    result: Dict[str, Any], status: MCPToolExecutionStatus,
                                    execution_time_ms: Optional[int] = None,
                                    error_message: Optional[str] = None) -> bool:
        """Update tool execution with result."""
        try:
            update_values = {
                "result": result,
                "status": status.value,
                "execution_time_ms": execution_time_ms,
                "error_message": error_message
            }
            result = await db.execute(
                update(MCPToolExecution)
                .where(MCPToolExecution.id == execution_id)
                .values(**update_values)
            )
            await db.commit()
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating execution result: {e}")
            raise DatabaseError(f"Failed to update execution result: {str(e)}")


class MCPResourceAccessRepository:
    """Repository for MCP resource access tracking."""
    
    async def create_access_record(self, db: AsyncSession, server_name: str,
                                 resource_uri: str, user_id: Optional[str] = None) -> MCPResourceAccess:
        """Create a new resource access record."""
        try:
            access = MCPResourceAccess(
                id=str(uuid.uuid4()),
                server_name=server_name,
                resource_uri=resource_uri,
                status="accessed",
                user_id=user_id
            )
            db.add(access)
            await db.commit()
            await db.refresh(access)
            return access
        except Exception as e:
            logger.error(f"Error creating resource access record: {e}")
            raise DatabaseError(f"Failed to create resource access record: {str(e)}")
    
    async def find_by_user(self, db: AsyncSession, user_id: str) -> List[MCPResourceAccess]:
        """Find resource access records by user."""
        try:
            result = await db.execute(
                select(MCPResourceAccess).where(MCPResourceAccess.user_id == user_id)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error finding resource access by user: {e}")
            raise DatabaseError(f"Failed to find resource access: {str(e)}")