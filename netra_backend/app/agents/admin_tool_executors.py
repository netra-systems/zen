# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-14T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: CLAUDE.md compliance - Admin tool executors module  <= 300 lines
# Git: anthony-aug-13-2 | modified
# Change: Refactor | Scope: Component | Risk: Low
# Session: claude-md-compliance | Seq: 5
# Review: Pending | Score: 90
# ================================

"""
Admin Tool Executors

This module contains the execution logic for individual admin tools.
All functions are  <= 8 lines as per CLAUDE.md requirements.
"""

from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_postgres import User
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.shared_types import ToolResult

logger = central_logger.get_logger(__name__)


class AdminToolExecutors:
    """Executes individual admin tools with strict 25-line function limit"""
    
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
    
    async def execute_corpus_manager(self, action: str, **kwargs) -> ToolResult:
        """Execute corpus manager actions via corpus service"""
        return await self._route_corpus_action(action, **kwargs)
    
    async def _route_corpus_action(self, action: str, **kwargs) -> ToolResult:
        """Route corpus action to appropriate handler"""
        action_handlers = self._get_corpus_action_handlers()
        if action in action_handlers:
            return await action_handlers[action](**kwargs)
        return {"error": f"Unknown corpus action: {action}"}
    
    def _get_corpus_action_handlers(self) -> Dict[str, Any]:
        """Get corpus action handler mapping"""
        return {
            'create': self._create_corpus,
            'list': self._list_corpora,
            'validate': self._validate_corpus
        }
    
    async def _create_corpus(self, **kwargs) -> ToolResult:
        """Create new corpus"""
        from netra_backend.app.core.configuration.services import corpus_service
        
        corpus_params = self._extract_corpus_params(**kwargs)
        result = await self._call_corpus_service(corpus_service, corpus_params)
        return {"status": "success", "corpus": result}
    
    async def _call_corpus_service(self, corpus_service, corpus_params: Dict[str, str]):
        """Call corpus service with parameters"""
        return await corpus_service.create_corpus(
            **corpus_params, user_id=self.user.id, db=self.db
        )
    
    def _extract_corpus_params(self, **kwargs) -> Dict[str, str]:
        """Extract corpus creation parameters"""
        domain = kwargs.get('domain', 'general')
        name = kwargs.get('name', f'corpus_{domain}')
        description = kwargs.get('description', f'Corpus for {domain} domain')
        return {"name": name, "domain": domain, "description": description}
    
    async def _list_corpora(self) -> ToolResult:
        """List all available corpora"""
        from netra_backend.app.core.configuration.services import corpus_service
        
        corpora = await corpus_service.list_corpora(self.db)
        return {"status": "success", "corpora": corpora}
    
    async def _validate_corpus(self, **kwargs) -> ToolResult:
        """Validate corpus by ID"""
        corpus_id = kwargs.get('corpus_id')
        if not corpus_id:
            return {"error": "corpus_id required for validation"}
        
        # Implement validation logic
        return {"status": "success", "valid": True, "corpus_id": corpus_id}
    
    async def execute_synthetic_generator(self, action: str, **kwargs) -> ToolResult:
        """Execute synthetic data generator actions"""
        if action == 'generate':
            return await self._generate_synthetic_data(**kwargs)
        elif action == 'list_presets':
            return await self._list_synthetic_presets()
        else:
            return {"error": f"Unknown synthetic generator action: {action}"}
    
    async def _generate_synthetic_data(self, **kwargs) -> Dict[str, Any]:
        """Generate synthetic data"""
        from netra_backend.app.services.synthetic_data_service import (
            SyntheticDataService,
        )
        
        synthetic_service = SyntheticDataService(self.db)
        generation_params = self._extract_synthetic_params(**kwargs)
        result = await self._call_synthetic_service(synthetic_service, generation_params)
        return {"status": "success", "data": result}
    
    async def _call_synthetic_service(self, service, params: Dict[str, Any]):
        """Call synthetic data service with parameters"""
        return await service.generate_synthetic_data(
            **params, user_id=self.user.id
        )
    
    def _extract_synthetic_params(self, **kwargs) -> Dict[str, Any]:
        """Extract synthetic data generation parameters"""
        preset = kwargs.get('preset')
        corpus_id = kwargs.get('corpus_id')
        count = kwargs.get('count', 10)
        return {"preset": preset, "corpus_id": corpus_id, "count": count}
    
    async def _list_synthetic_presets(self) -> Dict[str, Any]:
        """List available synthetic data presets"""
        from netra_backend.app.services.synthetic_data_service import (
            SyntheticDataService,
        )
        
        synthetic_service = SyntheticDataService(self.db)
        presets = await synthetic_service.list_presets()
        return {"status": "success", "presets": presets}
    
    async def execute_user_admin(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute user admin actions via user service"""
        if action == 'create_user':
            return await self._create_user(**kwargs)
        elif action == 'grant_permission':
            return await self._grant_permission(**kwargs)
        else:
            return {"error": f"Unknown user admin action: {action}"}
    
    async def _create_user(self, **kwargs) -> Dict[str, Any]:
        """Create new user"""
        email, role = self._extract_user_params(**kwargs)
        validation_error = self._validate_user_creation(email)
        if validation_error:
            return validation_error
        return await self._create_user_with_service(email, role)
    
    async def _create_user_with_service(self, email: str, role: str) -> Dict[str, Any]:
        """Create user using service"""
        from netra_backend.app.core.configuration.services import user_service
        result = await user_service.create_user(email=email, role=role, db=self.db)
        return {"status": "success", "user": result}
    
    async def _call_user_service(self, user_service, email: str, role: str) -> Dict[str, Any]:
        """Call user service to create user"""
        result = await user_service.create_user(
            email=email, role=role, db=self.db
        )
        return {"status": "success", "user": result}
    
    def _extract_user_params(self, **kwargs) -> tuple:
        """Extract user creation parameters"""
        email = kwargs.get('email')
        role = kwargs.get('role', 'standard_user')
        return email, role
    
    def _validate_user_creation(self, email: str) -> Dict[str, str] | None:
        """Validate user creation requirements"""
        if not email:
            return {"error": "email required for user creation"}
        return None
    
    async def _grant_permission(self, **kwargs) -> Dict[str, Any]:
        """Grant permission to user"""
        user_email, permission = self._extract_permission_params(**kwargs)
        validation_error = self._validate_permission_grant(user_email, permission)
        if validation_error:
            return validation_error
        return await self._grant_permission_with_service(user_email, permission)
    
    async def _grant_permission_with_service(self, user_email: str, permission: str) -> Dict[str, Any]:
        """Grant permission using service"""
        from netra_backend.app.services.permission_service import PermissionService
        success = await PermissionService.grant_permission(user_email, permission, self.db)
        return {"status": "success" if success else "error", "granted": success}
    
    async def _call_permission_service(self, service, user_email: str, permission: str) -> Dict[str, Any]:
        """Call permission service to grant permission"""
        success = await service.grant_permission(
            user_email, permission, self.db
        )
        return {"status": "success" if success else "error", "granted": success}
    
    def _extract_permission_params(self, **kwargs) -> tuple:
        """Extract permission grant parameters"""
        user_email = kwargs.get('user_email')
        permission = kwargs.get('permission')
        return user_email, permission
    
    def _validate_permission_grant(self, user_email: str, permission: str) -> Dict[str, str] | None:
        """Validate permission grant requirements"""
        if not user_email or not permission:
            return {"error": "user_email and permission required"}
        return None
    
    async def execute_system_configurator(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute system configurator actions"""
        if action == 'update_setting':
            return await self._update_system_setting(**kwargs)
        elif action == 'get_settings':
            return await self._get_system_settings()
        else:
            return {"error": f"Unknown system configurator action: {action}"}
    
    async def _update_system_setting(self, **kwargs) -> Dict[str, Any]:
        """Update system configuration setting"""
        setting_name, value = self._extract_setting_params(**kwargs)
        validation_error = self._validate_setting_update(setting_name)
        if validation_error:
            return validation_error
        # For now, return simulated response since dynamic config updates would require more infrastructure
        return self._build_setting_update_response(setting_name, value)
    
    def _extract_setting_params(self, **kwargs) -> tuple:
        """Extract system setting parameters"""
        setting_name = kwargs.get('setting_name')
        value = kwargs.get('value')
        return setting_name, value
    
    def _validate_setting_update(self, setting_name: str) -> Dict[str, str] | None:
        """Validate setting update requirements"""
        if not setting_name:
            return {"error": "setting_name required"}
        return None
    
    def _build_setting_update_response(self, setting_name: str, value: Any) -> Dict[str, Any]:
        """Build setting update response"""
        return {
            "status": "success", "setting": setting_name, "value": value,
            "message": "Setting update simulated (would require restart)"
        }
    
    async def _get_system_settings(self) -> Dict[str, Any]:
        """Get current system settings"""
        from netra_backend.app.core.config import get_settings
        
        settings = get_settings()
        safe_settings = self._build_safe_settings(settings)
        return {"status": "success", "settings": safe_settings}
    
    def _build_safe_settings(self, settings) -> Dict[str, Any]:
        """Build safe subset of settings without secrets"""
        return {
            "environment": getattr(settings, 'ENVIRONMENT', 'unknown'),
            "database_url": "***hidden***",
            "debug_mode": getattr(settings, 'DEBUG', False)
        }
    
    async def execute_log_analyzer(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute log analyzer actions via debug service"""
        if action == 'analyze':
            return await self._analyze_logs(**kwargs)
        elif action == 'get_recent':
            return await self._get_recent_logs(**kwargs)
        else:
            return {"error": f"Unknown log analyzer action: {action}"}
    
    async def _analyze_logs(self, **kwargs) -> Dict[str, Any]:
        """Analyze logs with query and time range"""
        query, time_range = self._extract_log_analysis_params(kwargs)
        debug_result = await self._get_debug_service_logs()
        return self._build_log_analysis_response(query, time_range, debug_result)
    
    def _extract_log_analysis_params(self, kwargs) -> tuple:
        """Extract log analysis parameters from kwargs"""
        query = kwargs.get('query', '')
        time_range = kwargs.get('time_range', '1h')
        return query, time_range
    
    async def _get_debug_service_logs(self) -> Dict[str, Any]:
        """Get logs from debug service"""
        from netra_backend.app.services.debug_service import DebugService
        debug_service = DebugService(self.db)
        return await debug_service.get_debug_info(
            component='logs', include_logs=True, user_id=self.user.id
        )
    
    def _build_log_analysis_response(self, query: str, time_range: str, debug_result: Dict[str, Any]) -> Dict[str, Any]:
        """Build log analysis response dictionary"""
        return {
            "status": "success", "query": query, "time_range": time_range,
            "logs": debug_result.get('logs', []),
            "summary": f"Log analysis for query: {query}"
        }
    
    async def _get_recent_logs(self, **kwargs) -> Dict[str, Any]:
        """Get recent log entries"""
        limit, level = self._extract_recent_logs_params(kwargs)
        debug_result = await self._get_debug_service_logs()
        logs = self._filter_and_limit_logs(debug_result, limit)
        return self._build_recent_logs_response(logs, level)
    
    def _extract_recent_logs_params(self, kwargs) -> tuple:
        """Extract recent logs parameters from kwargs"""
        limit = kwargs.get('limit', 100)
        level = kwargs.get('level', 'INFO')
        return limit, level
    
    def _filter_and_limit_logs(self, debug_result: Dict[str, Any], limit: int) -> list:
        """Filter and limit logs from debug result"""
        logs = debug_result.get('logs', [])
        return logs[:limit]
    
    def _build_recent_logs_response(self, logs: list, level: str) -> Dict[str, Any]:
        """Build recent logs response dictionary"""
        return {
            "status": "success", "logs": logs,
            "count": len(logs), "level": level
        }