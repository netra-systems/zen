"""
System Management Tool Handlers

Contains handlers for system configuration, user administration, and logging tools.
"""
from typing import Dict, Any, TYPE_CHECKING
from app.db.models_postgres import User

if TYPE_CHECKING:
    from .registry import UnifiedToolRegistry


class SystemManagementHandlers:
    """Handlers for system management tools"""
    
    async def _system_configurator_handler(self: "UnifiedToolRegistry", arguments: Dict[str, Any], user: User):
        """Handler for system_configurator tool"""
        from app.services.configuration_service import ConfigurationService
        
        config_service = ConfigurationService(self.db)
        action = arguments['action']
        
        if action == 'get':
            config = await config_service.get_configuration(
                key=arguments['key'],
                user_id=user.id
            )
            return {
                "type": "text", 
                "text": f"Retrieved configuration: {arguments['key']}",
                "config": config
            }
        elif action == 'set':
            await config_service.set_configuration(
                key=arguments['key'],
                value=arguments['value'],
                user_id=user.id
            )
            return {
                "type": "text", 
                "text": f"Updated configuration: {arguments['key']}"
            }
        elif action == 'reset':
            await config_service.reset_configuration(
                key=arguments.get('key'),
                user_id=user.id
            )
            return {
                "type": "text", 
                "text": "Configuration reset completed"
            }
        else:
            return {
                "type": "text",
                "text": f"Unknown action: {action}"
            }
    
    async def _user_admin_handler(self: "UnifiedToolRegistry", arguments: Dict[str, Any], user: User):
        """Handler for user_admin tool"""
        from app.services.user_service import UserService
        
        if not user.is_admin:
            return _create_permission_error_response()
        
        user_service = UserService(self.db)
        action = arguments['action']
        return await _execute_user_admin_action(user_service, action, arguments)


def _create_permission_error_response() -> Dict[str, Any]:
    """Create permission error response for non-admin users."""
    return {
        "type": "text",
        "text": "Admin privileges required",
        "error": True
    }


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
    new_user = await user_service.create_user(
        email=arguments['email'],
        username=arguments.get('username'),
        role=arguments.get('role', 'user')
    )
    return {
        "type": "text",
        "text": f"Created user: {new_user.email}",
        "user_id": new_user.id
    }


async def _handle_user_update_action(
    user_service: 'UserService', 
    arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle user update action."""
    await user_service.update_user(
        user_id=arguments['user_id'],
        updates=arguments.get('updates', {})
    )
    return {
        "type": "text",
        "text": f"Updated user: {arguments['user_id']}"
    }


async def _handle_user_delete_action(
    user_service: 'UserService', 
    arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle user deletion action."""
    await user_service.delete_user(user_id=arguments['user_id'])
    return {
        "type": "text",
        "text": f"Deleted user: {arguments['user_id']}"
    }


async def _handle_user_list_action(
    user_service: 'UserService', 
    arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle user listing action."""
    users = await user_service.list_users(
        filters=arguments.get('filters', {})
    )
    return {
        "type": "text",
        "text": f"Found {len(users)} users",
        "users": users
    }


def _create_unknown_action_response(action: str) -> Dict[str, Any]:
    """Create response for unknown action."""
    return {
        "type": "text",
        "text": f"Unknown action: {action}"
    }
    
    async def _log_analyzer_handler(self: "UnifiedToolRegistry", arguments: Dict[str, Any], user: User):
        """Handler for log_analyzer tool"""
        from app.services.log_analysis_service import LogAnalysisService
        
        log_service = LogAnalysisService(self.db)
        
        analysis = await log_service.analyze_logs(
            query=arguments.get('query', ''),
            time_range=arguments.get('time_range', '1h'),
            log_level=arguments.get('log_level'),
            service=arguments.get('service'),
            user_id=user.id
        )
        
        return {
            "type": "text",
            "text": f"Log analysis completed",
            "analysis": analysis,
            "total_logs": analysis.get('total_count', 0),
            "error_count": analysis.get('error_count', 0),
            "warning_count": analysis.get('warning_count', 0)
        }
    
    async def _debug_panel_handler(self: "UnifiedToolRegistry", arguments: Dict[str, Any], user: User):
        """Handler for debug_panel tool"""
        from app.services.debug_service import DebugService
        
        debug_service = DebugService(self.db)
        component = arguments.get('component', 'system')
        
        debug_info = await debug_service.get_debug_info(
            component=component,
            include_metrics=arguments.get('include_metrics', True),
            include_logs=arguments.get('include_logs', False),
            user_id=user.id
        )
        
        return {
            "type": "text",
            "text": f"Debug info for {component}",
            "debug_info": debug_info,
            "timestamp": debug_info.get('timestamp'),
            "health_status": debug_info.get('health_status', 'unknown')
        }