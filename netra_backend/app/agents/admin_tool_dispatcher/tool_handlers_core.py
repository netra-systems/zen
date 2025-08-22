# AI AGENT MODIFICATION METADATA - AGT-003
# ===============================================
# Timestamp: 2025-08-18T12:15:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514  
# Context: Split tool_handlers.py into modular components
# Git: 8-18-25-AM | Admin tool dispatcher modernization
# Change: Modernize | Scope: Module | Risk: Low
# Session: admin-tool-modernization | Seq: 003
# Review: Pending | Score: 98
# ===============================================
"""
Core Tool Handler Infrastructure

Base classes and interfaces for modern admin tool handlers.
Provides standardized execution patterns with reliability management.

Business Value: Standardizes tool execution across all admin operations.
Target Segments: Growth & Enterprise (improved admin reliability).
"""
from typing import Any, Callable, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
from netra_backend.app.agents.base.error_handler import ExecutionErrorHandler
from netra_backend.app.agents.base.interface import (
    AgentExecutionMixin,
    BaseExecutionInterface,
    ExecutionContext,
    ExecutionResult,
)
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.db.models_postgres import User
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.shared_types import RetryConfig

logger = central_logger


class ModernToolHandler(BaseExecutionInterface, AgentExecutionMixin):
    """Modern tool handler with BaseExecutionInterface pattern."""
    
    def __init__(self, tool_name: str, websocket_manager=None):
        super().__init__(f"tool_handler_{tool_name}", websocket_manager)
        self.tool_name = tool_name
        self.reliability_manager = self._create_reliability_manager()
        self.monitor = ExecutionMonitor()
        self.error_handler = ExecutionErrorHandler()
    
    def _create_reliability_manager(self) -> ReliabilityManager:
        """Create reliability manager for tool execution."""
        circuit_config = CircuitBreakerConfig(
            name=f"tool_{self.tool_name}",
            failure_threshold=5,
            recovery_timeout=30
        )
        retry_config = RetryConfig(max_retries=3, base_delay=1.0, max_delay=10.0)
        return ReliabilityManager(circuit_config, retry_config)


class CorpusManagerHandler(ModernToolHandler):
    """Corpus manager tool handler with modern patterns."""
    
    def __init__(self, websocket_manager=None):
        super().__init__("corpus_manager", websocket_manager)
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate corpus manager execution preconditions."""
        required_params = ['action', 'user', 'db']
        return all(param in context.state.params for param in required_params)
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute corpus manager core logic."""
        params = context.state.params
        action = params['action']
        user = params['user']
        db = params['db']
        
        action_handlers = self._get_corpus_action_handlers()
        handler = action_handlers.get(action)
        if handler:
            return await handler(user, db, **params.get('kwargs', {}))
        return {"error": f"Unknown corpus action: {action}"}
    
    def _get_corpus_action_handlers(self) -> Dict[str, Callable]:
        """Get mapping of corpus actions to handlers."""
        return {
            'create': self._handle_corpus_create,
            'list': lambda user, db, **kwargs: self._handle_corpus_list(db),
            'validate': lambda user, db, **kwargs: self._handle_corpus_validate(**kwargs)
        }
    
    async def _handle_corpus_create(self, user: User, db: AsyncSession, **kwargs) -> Dict[str, Any]:
        """Handle corpus creation"""
        params = extract_corpus_create_params(kwargs, user)
        result = await _execute_corpus_creation(params, db)
        return _create_corpus_response(result)
    
    async def _handle_corpus_list(self, db: AsyncSession) -> Dict[str, Any]:
        """Handle corpus listing"""
        from netra_backend.app.core.configuration.services import corpus_service

        from netra_backend.app.agents.admin_tool_dispatcher.tool_handler_helpers import create_corpus_list_response
        corpora = await corpus_service.list_corpora(db)
        return create_corpus_list_response(corpora)
    
    async def _handle_corpus_validate(self, **kwargs) -> Dict[str, Any]:
        """Handle corpus validation"""
        from .tool_handler_helpers import (
            check_corpus_id_required,
            create_corpus_validation_response,
        )
        corpus_id = kwargs.get('corpus_id')
        check_corpus_id_required(corpus_id)
        return create_corpus_validation_response(corpus_id)


class SyntheticGeneratorHandler(ModernToolHandler):
    """Synthetic generator tool handler with modern patterns."""
    
    def __init__(self, websocket_manager=None):
        super().__init__("synthetic_generator", websocket_manager)
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate synthetic generator execution preconditions."""
        required_params = ['action', 'user', 'db']
        return all(param in context.state.params for param in required_params)
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute synthetic generator core logic."""
        params = context.state.params
        action = params['action']
        user = params['user']
        db = params['db']
        
        action_handlers = self._get_synthetic_action_handlers()
        handler = action_handlers.get(action)
        if handler:
            return await handler(user, db, **params.get('kwargs', {}))
        return {"error": f"Unknown synthetic generator action: {action}"}
    
    def _get_synthetic_action_handlers(self) -> Dict[str, Callable]:
        """Get mapping of synthetic actions to handlers."""
        return {
            'generate': self._handle_synthetic_generate,
            'list_presets': lambda user, db, **kwargs: self._handle_synthetic_list_presets(db)
        }
    
    async def _handle_synthetic_generate(self, user: User, db: AsyncSession, **kwargs) -> Dict[str, Any]:
        """Handle synthetic data generation"""
        synthetic_service = _create_synthetic_service(db)
        params = extract_synthetic_params(kwargs, user)
        result = await synthetic_service.generate_synthetic_data(**params)
        return _create_synthetic_response(result)
    
    async def _handle_synthetic_list_presets(self, db: AsyncSession) -> Dict[str, Any]:
        """Handle listing synthetic data presets"""
        from netra_backend.app.services.synthetic_data_service import (
            SyntheticDataService,
        )

        from netra_backend.app.agents.admin_tool_dispatcher.tool_handler_helpers import create_presets_list_response
        synthetic_service = SyntheticDataService(db)
        presets = await synthetic_service.list_presets()
        return create_presets_list_response(presets)


class UserAdminHandler(ModernToolHandler):
    """User admin tool handler with modern patterns."""
    
    def __init__(self, websocket_manager=None):
        super().__init__("user_admin", websocket_manager)
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate user admin execution preconditions."""
        required_params = ['action', 'user', 'db']
        return all(param in context.state.params for param in required_params)
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute user admin core logic."""
        params = context.state.params
        action = params['action']
        db = params['db']
        
        action_handlers = self._get_user_admin_handlers()
        handler = action_handlers.get(action)
        if handler:
            return await handler(db, **params.get('kwargs', {}))
        return {"error": f"Unknown user admin action: {action}"}
    
    def _get_user_admin_handlers(self) -> Dict[str, Callable]:
        """Get mapping of user admin actions to handlers."""
        return {
            'create_user': self._handle_user_create,
            'grant_permission': self._handle_user_grant_permission
        }
    
    async def _handle_user_create(self, db: AsyncSession, **kwargs) -> Dict[str, Any]:
        """Handle user creation"""
        from netra_backend.app.agents.admin_tool_dispatcher.tool_handler_helpers import check_email_required
        email = kwargs.get('email')
        check_email_required(email)
        params = _prepare_user_create_params(kwargs, db)
        result = await _execute_user_creation(params)
        return _create_user_response(result)
    
    async def _handle_user_grant_permission(self, db: AsyncSession, **kwargs) -> Dict[str, Any]:
        """Handle granting user permissions"""
        from netra_backend.app.agents.admin_tool_dispatcher.tool_handler_helpers import check_user_permission_params
        user_email, permission = _extract_permission_params(kwargs)
        check_user_permission_params(user_email, permission)
        success = await _grant_user_permission(user_email, permission, db)
        return _create_permission_response(success)


class SystemConfiguratorHandler(ModernToolHandler):
    """System configurator tool handler with modern patterns."""
    
    def __init__(self, websocket_manager=None):
        super().__init__("system_configurator", websocket_manager)
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate system configurator execution preconditions."""
        required_params = ['action']
        return all(param in context.state.params for param in required_params)
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute system configurator core logic."""
        params = context.state.params
        action = params['action']
        
        if action == 'update_setting':
            return await self._handle_system_update_setting(**params.get('kwargs', {}))
        return {"error": f"Unknown system configurator action: {action}"}
    
    async def _handle_system_update_setting(self, **kwargs) -> Dict[str, Any]:
        """Handle system setting update"""
        from .tool_handler_helpers import (
            check_setting_name_required,
            create_setting_update_result,
        )
        setting_name = kwargs.get('setting_name')
        value = kwargs.get('value')
        check_setting_name_required(setting_name)
        return create_setting_update_result(setting_name, value)


class LogAnalyzerHandler(ModernToolHandler):
    """Log analyzer tool handler with modern patterns."""
    
    def __init__(self, websocket_manager=None):
        super().__init__("log_analyzer", websocket_manager)
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate log analyzer execution preconditions."""
        required_params = ['action', 'user', 'db']
        return all(param in context.state.params for param in required_params)
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute log analyzer core logic."""
        params = context.state.params
        action = params['action']
        
        if action == 'analyze':
            user = params['user']
            db = params['db']
            return await self._handle_log_analyze(user, db, **params.get('kwargs', {}))
        return {"error": f"Unknown log analyzer action: {action}"}
    
    async def _handle_log_analyze(self, user: User, db: AsyncSession, **kwargs) -> Dict[str, Any]:
        """Handle log analysis"""
        from netra_backend.app.agents.admin_tool_dispatcher.tool_handler_helpers import extract_log_analysis_params
        query, time_range = extract_log_analysis_params(kwargs)
        result = await _execute_debug_analysis(db, user)
        return _create_log_analysis_response(query, time_range, result)


# Modern tool executor factory
def create_modern_tool_handler(tool_name: str, websocket_manager=None) -> ModernToolHandler:
    """Create modern tool handler instance."""
    handler_map = {
        'corpus_manager': CorpusManagerHandler,
        'synthetic_generator': SyntheticGeneratorHandler,
        'user_admin': UserAdminHandler,
        'system_configurator': SystemConfiguratorHandler,
        'log_analyzer': LogAnalyzerHandler
    }
    handler_class = handler_map.get(tool_name, ModernToolHandler)
    return handler_class(websocket_manager) if tool_name in handler_map else handler_class(tool_name, websocket_manager)


# Import essential helper functions from other modules
from netra_backend.app.agents.admin_tool_dispatcher.tool_handler_operations import (
    _create_corpus_response,
    _create_log_analysis_response,
    _create_permission_response,
    _create_synthetic_response,
    _create_synthetic_service,
    _create_user_response,
    _execute_corpus_creation,
    _execute_debug_analysis,
    _execute_user_creation,
    _extract_permission_params,
    _grant_user_permission,
    _prepare_user_create_params,
    extract_corpus_create_params,
    extract_synthetic_params,
)
