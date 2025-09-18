"""
System Management Tool Handlers

Contains handlers for system configuration, user administration, and logging tools.
"""
from typing import TYPE_CHECKING, Any, Dict

from netra_backend.app.db.models_postgres import User

if TYPE_CHECKING:
    from netra_backend.app.core.registry.universal_registry import ToolRegistry as UnifiedToolRegistry


class SystemManagementHandlers:
    """Handlers for system management tools"""
    
    async def _system_configurator_handler(self: "UnifiedToolRegistry", arguments: Dict[str, Any], user: User):
        """Handler for system_configurator tool"""
        # ISSUE #667: Use canonical SSOT configuration instead of duplicate
        from netra_backend.app.config import config_manager

        # Create a compatible wrapper for the existing API
        class ConfigurationService:
            def __init__(self, db):
                self.db = db
                self.config_manager = config_manager

            def get_config(self, key: str, default=None):
                return self.config_manager.get_config_value(key, default)

            def set_config(self, key: str, value):
                return self.config_manager.set_config_value(key, value)

            def validate_config(self, key: str = None):
                return self.config_manager.validate_config_value(key)
        config_service = ConfigurationService(self.db)
        action = arguments['action']
        return await self._execute_configuration_action(config_service, action, arguments, user)
    
    async def _execute_configuration_action(self, config_service, action: str, arguments: Dict[str, Any], user: User):
        """Execute configuration action based on type"""
        if action == 'get':
            return await self._handle_config_get_action(config_service, arguments, user)
        elif action == 'set':
            return await self._handle_config_set_action(config_service, arguments, user)
        elif action == 'reset':
            return await self._handle_config_reset_action(config_service, arguments, user)
        else:
            return self._create_unknown_action_response(action)
    
    async def _handle_config_get_action(self, config_service, arguments: Dict[str, Any], user: User):
        """Handle configuration get action"""
        config = await config_service.get_configuration(key=arguments['key'], user_id=user.id)
        return {"type": "text", "text": f"Retrieved configuration: {arguments['key']}", "config": config}
    
    async def _handle_config_set_action(self, config_service, arguments: Dict[str, Any], user: User):
        """Handle configuration set action"""
        await config_service.set_configuration(key=arguments['key'], value=arguments['value'], user_id=user.id)
        return {"type": "text", "text": f"Updated configuration: {arguments['key']}"}
    
    async def _handle_config_reset_action(self, config_service, arguments: Dict[str, Any], user: User):
        """Handle configuration reset action"""
        await config_service.reset_configuration(key=arguments.get('key'), user_id=user.id)
        return {"type": "text", "text": "Configuration reset completed"}
    
    def _create_unknown_action_response(self, action: str):
        """Create response for unknown action"""
        return {"type": "text", "text": f"Unknown action: {action}"}
    
    async def _user_admin_handler(self: "UnifiedToolRegistry", arguments: Dict[str, Any], user: User):
        """Handler for user_admin tool"""
        from netra_backend.app.services.user_service import UserService
        if not user.is_admin:
            return _create_permission_error_response()
        user_service = UserService(self.db)
        action = arguments['action']
        return await _execute_user_admin_action(user_service, action, arguments)


def _create_permission_error_response() -> Dict[str, Any]:
    """Create permission error response for non-admin users."""
    return {"type": "text", "text": "Admin privileges required", "error": True}


async def _execute_user_admin_action(
    user_service: 'UserService', 
    action: str, 
    arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute user admin action based on type."""
    if action == 'create':
        return await _handle_user_create_action(user_service, arguments)
    elif action == 'update':
        return await _handle_user_update_action(user_service, arguments)
    elif action == 'delete':
        return await _handle_user_delete_action(user_service, arguments)
    elif action == 'list':
        return await _handle_user_list_action(user_service, arguments)
    else:
        return _create_unknown_action_response(action)


async def _handle_user_create_action(
    user_service: 'UserService', 
    arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle user creation action."""
    email = arguments['email']
    username = arguments.get('username')
    role = arguments.get('role', 'user')
    new_user = await user_service.create_user(email=email, username=username, role=role)
    return {"type": "text", "text": f"Created user: {new_user.email}", "user_id": new_user.id}


async def _handle_user_update_action(
    user_service: 'UserService', 
    arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle user update action."""
    user_id = arguments['user_id']
    updates = arguments.get('updates', {})
    await user_service.update_user(user_id=user_id, updates=updates)
    return {"type": "text", "text": f"Updated user: {user_id}"}


async def _handle_user_delete_action(
    user_service: 'UserService', 
    arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle user deletion action."""
    user_id = arguments['user_id']
    await user_service.delete_user(user_id=user_id)
    return {"type": "text", "text": f"Deleted user: {user_id}"}


async def _handle_user_list_action(
    user_service: 'UserService', 
    arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle user listing action."""
    filters = arguments.get('filters', {})
    users = await user_service.list_users(filters=filters)
    return {"type": "text", "text": f"Found {len(users)} users", "users": users}


def _create_unknown_action_response(action: str) -> Dict[str, Any]:
    """Create response for unknown action."""
    return {"type": "text", "text": f"Unknown action: {action}"}
    
    async def _log_analyzer_handler(self: "UnifiedToolRegistry", arguments: Dict[str, Any], user: User):
        """Handler for log_analyzer tool"""
        from netra_backend.app.services.log_analysis_service import LogAnalysisService
        log_service = LogAnalysisService(self.db)
        analysis = await _perform_log_analysis(log_service, arguments, user)
        return _create_log_analysis_response(analysis)
    
    async def _debug_panel_handler(self: "UnifiedToolRegistry", arguments: Dict[str, Any], user: User):
        """Handler for debug_panel tool"""
        from netra_backend.app.services.debug_service import DebugService
        debug_service = DebugService(self.db)
        component = arguments.get('component', 'system')
        debug_info = await _get_component_debug_info(debug_service, component, arguments, user)
        return _create_debug_info_response(component, debug_info)


async def _perform_log_analysis(log_service: 'LogAnalysisService', arguments: Dict[str, Any], user: User) -> Dict[str, Any]:
    """Perform log analysis with given parameters."""
    query = arguments.get('query', '')
    time_range = arguments.get('time_range', '1h')
    log_level = arguments.get('log_level')
    service = arguments.get('service')
    return await log_service.analyze_logs(query=query, time_range=time_range, log_level=log_level, service=service, user_id=user.id)


def _create_log_analysis_response(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Create response for log analysis results."""
    base_data = {"type": "text", "text": "Log analysis completed", "analysis": analysis}
    count_data = {"total_logs": analysis.get('total_count', 0), "error_count": analysis.get('error_count', 0), "warning_count": analysis.get('warning_count', 0)}
    return {**base_data, **count_data}


async def _get_component_debug_info(
    debug_service: 'DebugService', 
    component: str, 
    arguments: Dict[str, Any], 
    user: User
) -> Dict[str, Any]:
    """Get debug information for a component."""
    include_metrics = arguments.get('include_metrics', True)
    include_logs = arguments.get('include_logs', False)
    return await debug_service.get_debug_info(component=component, include_metrics=include_metrics, include_logs=include_logs, user_id=user.id)


def _create_debug_info_response(component: str, debug_info: Dict[str, Any]) -> Dict[str, Any]:
    """Create response for debug information."""
    base_data = {"type": "text", "text": f"Debug info for {component}", "debug_info": debug_info}
    status_data = {"timestamp": debug_info.get('timestamp'), "health_status": debug_info.get('health_status', 'unknown')}
    return {**base_data, **status_data}