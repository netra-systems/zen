"""
MCP Service

Main service layer for MCP server integration with Netra platform using FastMCP 2.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, UTC
import json
import uuid
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from fastmcp import FastMCP

from app.logging_config import CentralLogger
from app.core.exceptions_base import NetraException
from app.services.service_interfaces import IMCPService
from app.services.agent_service import AgentService
from app.services.thread_service import ThreadService
from app.services.corpus_service import CorpusService
from app.services.synthetic_data_service import SyntheticDataService
from app.services.security_service import SecurityService
from app.services.supply_catalog_service import SupplyCatalogService
from app.services.database.mcp_repository import MCPClientRepository, MCPToolExecutionRepository
from app.schemas import UserInDB
from app.netra_mcp.netra_mcp_server import NetraMCPServer
from .mcp_models import MCPClient, MCPToolExecution

logger = CentralLogger()


class MCPService(IMCPService):
    """
    Main service for MCP server operations using FastMCP 2
    
    Integrates MCP functionality with existing Netra services.
    """
    
    def _assign_primary_services(self, agent_service, thread_service, corpus_service, synthetic_data_service):
        """Assign primary services to instance variables."""
        self.agent_service = agent_service
        self.thread_service = thread_service
        self.corpus_service = corpus_service
        self.synthetic_data_service = synthetic_data_service

    def _assign_secondary_services(self, security_service, supply_catalog_service, llm_manager):
        """Assign secondary services to instance variables."""
        self.security_service = security_service
        self.supply_catalog_service = supply_catalog_service
        self.llm_manager = llm_manager

    def _assign_core_services(self, agent_service, thread_service, corpus_service, 
                             synthetic_data_service, security_service, supply_catalog_service, llm_manager):
        """Assign core services to instance variables."""
        self._assign_primary_services(agent_service, thread_service, corpus_service, synthetic_data_service)
        self._assign_secondary_services(security_service, supply_catalog_service, llm_manager)

    def _initialize_repositories(self):
        """Initialize MCP repositories."""
        self.client_repository = MCPClientRepository()
        self.execution_repository = MCPToolExecutionRepository()

    def _create_mcp_server(self):
        """Create and configure MCP server."""
        self.mcp_server = NetraMCPServer(
            name="netra-mcp-server",
            version="2.0.0"
        )

    def _prepare_service_params(self):
        """Prepare service parameters for MCP server."""
        return {
            'agent_service': self.agent_service,
            'thread_service': self.thread_service,
            'corpus_service': self.corpus_service,
            'synthetic_data_service': self.synthetic_data_service,
            'security_service': self.security_service,
            'supply_catalog_service': self.supply_catalog_service,
            'llm_manager': self.llm_manager
        }

    def _inject_services_to_server(self):
        """Inject services into MCP server."""
        service_params = self._prepare_service_params()
        self.mcp_server.set_services(**service_params)

    def _initialize_session_storage(self):
        """Initialize active session storage."""
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        logger.info("MCP Service initialized with FastMCP 2")

    def __init__(
        self,
        agent_service: AgentService,
        thread_service: ThreadService,
        corpus_service: CorpusService,
        synthetic_data_service: SyntheticDataService,
        security_service: SecurityService,
        supply_catalog_service: SupplyCatalogService,
        llm_manager=None
    ):
        self._setup_mcp_service_components(
            agent_service, thread_service, corpus_service, 
            synthetic_data_service, security_service, supply_catalog_service, llm_manager
        )
    
    def _setup_mcp_service_components(
        self, agent_service, thread_service, corpus_service,
        synthetic_data_service, security_service, supply_catalog_service, llm_manager
    ):
        """Setup all MCP service components"""
        self._assign_core_services(agent_service, thread_service, corpus_service, 
                                 synthetic_data_service, security_service, supply_catalog_service, llm_manager)
        self._setup_infrastructure_components()
    
    def _setup_infrastructure_components(self):
        """Setup infrastructure components"""
        self._initialize_repositories()
        self._create_mcp_server()
        self._inject_services_to_server()
        self._initialize_session_storage()
    
    async def _hash_api_key(self, api_key: Optional[str]) -> Optional[str]:
        """Hash API key if provided."""
        if api_key:
            return self.security_service.hash_password(api_key)
        return None

    async def _store_client_in_db(self, db_session: AsyncSession, name: str, client_type: str, 
                                 api_key: Optional[str], permissions: Optional[List[str]], 
                                 metadata: Optional[Dict[str, Any]]):
        """Store client in database."""
        return await self.client_repository.create_client(
            db=db_session, name=name, client_type=client_type,
            api_key=api_key, permissions=permissions, metadata=metadata
        )

    def _convert_to_mcp_client(self, db_client) -> MCPClient:
        """Convert database client to MCPClient model."""
        return MCPClient(
            id=db_client.id, name=db_client.name, client_type=db_client.client_type,
            api_key_hash=db_client.api_key_hash, permissions=db_client.permissions,
            metadata=db_client.metadata, created_at=db_client.created_at, last_active=db_client.last_active
        )

    async def _log_registration_success(self, client: MCPClient, client_type: str):
        """Log successful client registration."""
        logger.info(f"Registered MCP client: {client.id} ({client_type})")

    async def _validate_and_create_client(self, db_session: AsyncSession, name: str, client_type: str, 
                                         api_key: Optional[str], permissions: Optional[List[str]], 
                                         metadata: Optional[Dict[str, Any]]):
        """Validate and create client in database."""
        api_key_hash = await self._hash_api_key(api_key)
        db_client = await self._store_client_in_db(db_session, name, client_type, api_key, permissions, metadata)
        if not db_client:
            raise NetraException("Failed to create MCP client in database")
        return db_client

    async def _finalize_client_registration(self, db_client, client_type: str):
        """Finalize client registration with logging."""
        client = self._convert_to_mcp_client(db_client)
        await self._log_registration_success(client, client_type)
        return client

    async def register_client(
        self,
        db_session: AsyncSession,
        name: str,
        client_type: str,
        api_key: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MCPClient:
        """Register a new MCP client"""
        try:
            db_client = await self._validate_and_create_client(db_session, name, client_type, api_key, permissions, metadata)
            return await self._finalize_client_registration(db_client, client_type)
        except Exception as e:
            logger.error(f"Error registering MCP client: {e}", exc_info=True)
            raise NetraException(f"Failed to register MCP client: {str(e)}")
    
    async def _check_client_permission(self, db_session: AsyncSession, client_id: str, required_permission: str):
        """Check client permission from database."""
        return await self.client_repository.validate_client_permission(
            db=db_session,
            client_id=client_id,
            required_permission=required_permission
        )

    async def _update_client_activity(self, db_session: AsyncSession, client_id: str, has_permission: bool):
        """Update client activity if permission granted."""
        if has_permission:
            await self.client_repository.update_last_active(db_session, client_id)
        return has_permission

    async def validate_client_access(
        self,
        db_session: AsyncSession,
        client_id: str,
        required_permission: str
    ) -> bool:
        """Validate client has required permission"""
        try:
            has_permission = await self._check_client_permission(db_session, client_id, required_permission)
            return await self._update_client_activity(db_session, client_id, has_permission)
        except Exception as e:
            logger.error(f"Error validating client access: {e}", exc_info=True)
            return False
    
    async def _store_execution_record(self, db_session: AsyncSession, execution: MCPToolExecution):
        """Store initial execution record in database."""
        return await self.execution_repository.record_execution(
            db=db_session,
            session_id=execution.session_id,
            client_id=execution.client_id or 'system',
            tool_name=execution.tool_name,
            input_params=execution.input_params,
            execution_time_ms=execution.execution_time_ms,
            status=execution.status
        )

    async def _update_execution_with_result(self, db_session: AsyncSession, execution: MCPToolExecution, db_execution):
        """Update execution record with result if available."""
        if execution.output_result and db_execution:
            await self.execution_repository.update_execution_result(
                db=db_session,
                execution_id=db_execution.id,
                output_result=execution.output_result,
                execution_time_ms=execution.execution_time_ms,
                status=execution.status,
                error=execution.error
            )

    async def _log_execution_completion(self, execution: MCPToolExecution):
        """Log completion of tool execution."""
        logger.info(f"Recorded tool execution: {execution.tool_name} ({execution.status})")

    async def record_tool_execution(
        self,
        db_session: AsyncSession,
        execution: MCPToolExecution
    ):
        """Record tool execution in database"""
        try:
            db_execution = await self._store_execution_record(db_session, execution)
            await self._update_execution_with_result(db_session, execution, db_execution)
            await self._log_execution_completion(execution)
        except Exception as e:
            logger.error(f"Error recording tool execution: {e}", exc_info=True)
    
    def _generate_session_data(self, session_id: str, client_id: Optional[str], metadata: Optional[Dict[str, Any]]):
        """Generate session data structure."""
        current_time = datetime.now(UTC)
        return {
            "id": session_id,
            "client_id": client_id,
            "created_at": current_time,
            "last_activity": current_time,
            "metadata": metadata or {},
            "request_count": 0
        }

    def _store_session(self, session_id: str, session_data: Dict[str, Any]):
        """Store session in active sessions."""
        self.active_sessions[session_id] = session_data
        logger.info(f"Created MCP session: {session_id}")

    async def create_session(
        self,
        client_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new MCP session"""
        session_id = str(uuid.uuid4())
        session_data = self._generate_session_data(session_id, client_id, metadata)
        self._store_session(session_id, session_data)
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        return self.active_sessions.get(session_id)
    
    async def update_session_activity(self, session_id: str):
        """Update session last activity timestamp"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["last_activity"] = datetime.now(UTC)
            self.active_sessions[session_id]["request_count"] += 1
    
    async def close_session(self, session_id: str):
        """Close an MCP session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Closed MCP session: {session_id}")
    
    def _identify_inactive_sessions(self, timeout_minutes: int):
        """Identify sessions that exceed timeout."""
        now = datetime.now(UTC)
        sessions_to_remove = []
        for session_id, session in self.active_sessions.items():
            time_since_activity = (now - session["last_activity"]).total_seconds() / 60
            if time_since_activity > timeout_minutes:
                sessions_to_remove.append(session_id)
        return sessions_to_remove

    async def _remove_inactive_sessions(self, sessions_to_remove: List[str]):
        """Remove inactive sessions and log cleanup."""
        for session_id in sessions_to_remove:
            await self.close_session(session_id)
        if sessions_to_remove:
            logger.info(f"Cleaned up {len(sessions_to_remove)} inactive sessions")

    async def cleanup_inactive_sessions(self, timeout_minutes: int = 60):
        """Clean up inactive sessions"""
        sessions_to_remove = self._identify_inactive_sessions(timeout_minutes)
        await self._remove_inactive_sessions(sessions_to_remove)
    
    def get_mcp_server(self) -> NetraMCPServer:
        """Get MCP server instance"""
        return self.mcp_server
    
    def get_fastmcp_app(self) -> FastMCP:
        """Get FastMCP app instance for running"""
        return self.mcp_server.get_app()
    
    def _get_basic_server_info(self):
        """Get basic server information."""
        return {
            "name": "Netra MCP Server",
            "version": "2.0.0",
            "protocol": "MCP",
            "implementation": "FastMCP 2"
        }

    def _get_server_capabilities(self):
        """Get server capabilities."""
        return {
            "tools": True,
            "resources": True,
            "prompts": True,
            "sampling": False  # Will be implemented with LLM manager
        }

    def _get_available_tools(self):
        """Get list of available tools."""
        return [
            "run_agent",
            "get_agent_status",
            "list_agents",
            "analyze_workload",
            "optimize_prompt",
            "execute_optimization_pipeline",
            "query_corpus",
            "generate_synthetic_data",
            "create_thread",
            "get_thread_history",
            "get_supply_catalog"
        ]

    def _get_available_resources(self):
        """Get list of available resources."""
        return [
            "netra://optimization/history",
            "netra://config/models",
            "netra://agents/catalog",
            "netra://metrics/current"
        ]

    def _get_available_prompts(self):
        """Get list of available prompts."""
        return [
            "optimization_request",
            "prompt_optimization",
            "model_selection"
        ]

    def _compile_server_info(self):
        """Compile complete server information."""
        info = self._get_basic_server_info()
        info["capabilities"] = self._get_server_capabilities()
        info["active_sessions"] = len(self.active_sessions)
        info["tools_available"] = self._get_available_tools()
        info["resources_available"] = self._get_available_resources()
        info["prompts_available"] = self._get_available_prompts()
        return info

    async def get_server_info(self) -> Dict[str, Any]:
        """Get MCP server information"""
        return self._compile_server_info()

    # Interface implementation methods
    async def initialize(self, config: Dict[str, Any] = None):
        """Initialize the MCP service with optional configuration."""
        # Basic initialization - could extend with config parameters
        await self.cleanup_inactive_sessions()
        logger.info("MCP Service initialized")

    def _extract_context_info(self, user_context: Dict[str, Any]):
        """Extract session and client info from user context."""
        session_id = user_context.get("session_id") if user_context else None
        client_id = user_context.get("client_id") if user_context else None
        return session_id, client_id

    def _create_tool_execution(self, tool_name: str, parameters: Dict[str, Any], session_id: str, client_id: str):
        """Create tool execution record."""
        return MCPToolExecution(
            session_id=session_id or "default",
            client_id=client_id,
            tool_name=tool_name,
            input_params=parameters,
            status="executing"
        )

    async def _execute_tool_logic(self, tool_name: str, parameters: Dict[str, Any]):
        """Execute the actual tool logic."""
        # This would integrate with the actual MCP server tool execution
        # For now, return a basic response
        return {"tool": tool_name, "status": "executed", "parameters": parameters}

    async def _handle_successful_execution(self, execution: MCPToolExecution, result: Dict[str, Any]):
        """Handle successful tool execution."""
        execution.status = "completed"
        execution.result = result
        await self.record_tool_execution(execution)
        return result

    async def _handle_failed_execution(self, execution: MCPToolExecution, error: Exception):
        """Handle failed tool execution."""
        execution.status = "failed"
        execution.error = str(error)
        await self.record_tool_execution(execution)
        raise NetraException(f"Tool execution failed: {error}")

    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any], user_context: Dict[str, Any] = None):
        """Execute an MCP tool with the given parameters and user context."""
        session_id, client_id = self._extract_context_info(user_context)
        execution = self._create_tool_execution(tool_name, parameters, session_id, client_id)
        try:
            result = await self._execute_tool_logic(tool_name, parameters)
            return await self._handle_successful_execution(execution, result)
        except Exception as e:
            await self._handle_failed_execution(execution, e)


# Import request handler from separate module for modularity
from .mcp_request_handler import handle_request