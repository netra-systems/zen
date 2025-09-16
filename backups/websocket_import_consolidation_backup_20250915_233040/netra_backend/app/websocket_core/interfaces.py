"""
WebSocket Component Interfaces - Phase 1 Foundation

Business Value Justification:
- Segment: Platform/Infrastructure
- Business Goal: Code maintainability and system stability
- Value Impact: Enable SSOT consolidation without breaking changes
- Strategic Impact: Foundation for reducing 3,891 line unified_manager.py to <2,000 lines

This module defines the canonical interfaces for the 7 identified components
within the unified WebSocket manager, enabling clean separation and SSOT
consolidation while maintaining backwards compatibility.

ISSUE #1047 PHASE 1: Foundation setup for WebSocket SSOT consolidation
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Set, Optional, Union, List
from datetime import datetime

from shared.types.core_types import UserID, ThreadID, ConnectionID
from netra_backend.app.websocket_core.types import WebSocketConnection


class ICoreConnectionManager(ABC):
    """
    Core Connection Manager Interface - Component 1

    Handles the fundamental connection lifecycle management:
    - Connection registration and cleanup
    - Connection state tracking
    - Basic connection queries

    Lines in unified_manager.py: ~548-1020 (472 lines)
    """

    @abstractmethod
    async def add_connection(self, connection: WebSocketConnection) -> None:
        """Add a new WebSocket connection."""
        pass

    @abstractmethod
    async def remove_connection(self, connection_id: Union[str, ConnectionID]) -> None:
        """Remove a WebSocket connection."""
        pass

    @abstractmethod
    def get_connection(self, connection_id: Union[str, ConnectionID]) -> Optional[WebSocketConnection]:
        """Get connection by ID."""
        pass

    @abstractmethod
    def get_user_connections(self, user_id: Union[str, UserID]) -> Set[str]:
        """Get all connection IDs for a user."""
        pass

    @abstractmethod
    def get_connection_thread_id(self, connection_id: Union[str, ConnectionID]) -> Optional[str]:
        """Get thread ID for a connection."""
        pass

    @abstractmethod
    def clear_all_connections(self) -> None:
        """Clear all connections (testing/cleanup)."""
        pass


class IEventBroadcastingService(ABC):
    """
    Event Broadcasting Service Interface - Component 2

    Handles message and event distribution:
    - User-targeted messaging
    - Thread-based messaging
    - System-wide broadcasting
    - Event delivery confirmation

    Lines in unified_manager.py: ~1060-1470 (410 lines)
    """

    @abstractmethod
    async def send_to_user(self, user_id: Union[str, UserID], message: Dict[str, Any]) -> None:
        """Send message to specific user."""
        pass

    @abstractmethod
    async def send_to_thread(self, thread_id: Union[str, ThreadID], message: Dict[str, Any]) -> bool:
        """Send message to specific thread."""
        pass

    @abstractmethod
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connections."""
        pass

    @abstractmethod
    async def emit_critical_event(self, user_id: Union[str, UserID], event_type: str, data: Dict[str, Any]) -> None:
        """Emit business-critical events."""
        pass

    @abstractmethod
    async def send_agent_event(self, user_id: Union[str, UserID], event_type: str, data: Dict[str, Any]) -> None:
        """Send agent-specific events."""
        pass


class IAuthenticationIntegration(ABC):
    """
    Authentication Integration Interface - Component 3

    Handles auth-related WebSocket operations:
    - User context validation
    - Connection authorization
    - User isolation enforcement

    Lines in unified_manager.py: ~334-395 (61 lines)
    """

    @abstractmethod
    def _validate_user_isolation(self, user_id: str, operation: str = "unknown") -> bool:
        """Validate user isolation for operation."""
        pass

    @abstractmethod
    def _prevent_cross_user_event_bleeding(self, event_data: Dict[str, Any], target_user_id: str) -> Dict[str, Any]:
        """Prevent cross-user event contamination."""
        pass


class IUserSessionRegistry(ABC):
    """
    User Session Registry Interface - Component 4

    Handles user session management:
    - Session state tracking
    - User connection mapping
    - Session cleanup and recovery

    Lines in unified_manager.py: ~1668-1840 (172 lines)
    """

    @abstractmethod
    async def connect_user(self, user_id: str, websocket: Any, connection_id: str = None, thread_id: str = None) -> Any:
        """Connect a user with session tracking."""
        pass

    @abstractmethod
    async def disconnect_user(self, user_id: str, websocket: Any, code: int = 1000, reason: str = "Normal closure") -> None:
        """Disconnect user and cleanup session."""
        pass

    @abstractmethod
    def is_user_connected(self, user_id: Union[str, UserID]) -> bool:
        """Check if user has active connections."""
        pass

    @abstractmethod
    async def cleanup_stale_connections(self, max_age_seconds: int = 3600) -> int:
        """Cleanup stale connections."""
        pass


class IPerformanceMonitor(ABC):
    """
    Performance Monitor Interface - Component 5

    Handles performance tracking and health monitoring:
    - Connection statistics
    - Health status reporting
    - Background task monitoring
    - Resource usage tracking

    Lines in unified_manager.py: ~2100-2650 (550 lines)
    """

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get general statistics."""
        pass

    @abstractmethod
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection-specific statistics."""
        pass

    @abstractmethod
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        pass

    @abstractmethod
    async def start_monitored_background_task(self, task_name: str, coro_func, *args, **kwargs) -> str:
        """Start a monitored background task."""
        pass


class IConfigurationProvider(ABC):
    """
    Configuration Provider Interface - Component 6

    Handles configuration management:
    - Mode initialization
    - Configuration validation
    - Environment-specific settings

    Lines in unified_manager.py: ~396-530 (134 lines)
    """

    @abstractmethod
    def _initialize_unified_mode(self):
        """Initialize unified mode configuration."""
        pass

    @abstractmethod
    def _initialize_isolated_mode(self, user_context):
        """Initialize isolated mode configuration."""
        pass

    @abstractmethod
    def _initialize_emergency_mode(self, config: Dict[str, Any]):
        """Initialize emergency mode configuration."""
        pass


class IIntegrationBridge(ABC):
    """
    Integration Bridge Interface - Component 7

    Handles integration with other system components:
    - Transaction coordination
    - External system integration
    - Legacy compatibility
    - Event listener management

    Lines in unified_manager.py: ~3371-3890 (519 lines)
    """

    @abstractmethod
    def add_event_listener(self, listener: callable) -> None:
        """Add event listener."""
        pass

    @abstractmethod
    def remove_event_listener(self, listener: callable) -> None:
        """Remove event listener."""
        pass

    @abstractmethod
    def set_transaction_coordinator(self, coordinator):
        """Set transaction coordinator."""
        pass

    @abstractmethod
    def is_coordination_enabled(self) -> bool:
        """Check if coordination is enabled."""
        pass

    @abstractmethod
    async def send_event_after_commit(self, transaction_id: str, event_type: str, event_data: Dict[str, Any], user_id: str) -> bool:
        """Send event after transaction commit."""
        pass


class IUnifiedWebSocketManager(ICoreConnectionManager, IEventBroadcastingService,
                              IAuthenticationIntegration, IUserSessionRegistry,
                              IPerformanceMonitor, IConfigurationProvider,
                              IIntegrationBridge):
    """
    Unified WebSocket Manager Interface

    Complete interface combining all 7 component interfaces.
    This represents the full contract that the unified manager must implement.

    This interface enables:
    1. Clear component boundaries definition
    2. Component extraction validation
    3. Backwards compatibility verification
    4. SSOT consolidation planning
    """
    pass


# Component validation utilities
class ComponentExtractionValidator:
    """
    Validates component extraction maintains interface compliance.

    Used during Phase 2 to ensure extracted components still satisfy
    the original unified interface contract.
    """

    @staticmethod
    def validate_component_interface(component: Any, interface_class: type) -> bool:
        """Validate that component implements required interface."""
        if not isinstance(component, interface_class):
            return False

        # Check all abstract methods are implemented (if it's an ABC)
        if hasattr(interface_class, '__abstractmethods__'):
            abstract_methods = interface_class.__abstractmethods__
            for method_name in abstract_methods:
                if not hasattr(component, method_name):
                    return False

                method = getattr(component, method_name)
                if not callable(method):
                    return False

        return True

    @staticmethod
    def generate_compliance_report(manager: Any) -> Dict[str, Any]:
        """Generate interface compliance report for manager."""
        interfaces = [
            ('ICoreConnectionManager', ICoreConnectionManager),
            ('IEventBroadcastingService', IEventBroadcastingService),
            ('IAuthenticationIntegration', IAuthenticationIntegration),
            ('IUserSessionRegistry', IUserSessionRegistry),
            ('IPerformanceMonitor', IPerformanceMonitor),
            ('IConfigurationProvider', IConfigurationProvider),
            ('IIntegrationBridge', IIntegrationBridge)
        ]

        report = {
            'overall_compliance': True,
            'component_compliance': {},
            'missing_methods': [],
            'timestamp': datetime.now().isoformat()
        }

        for interface_name, interface_class in interfaces:
            compliant = ComponentExtractionValidator.validate_component_interface(manager, interface_class)
            report['component_compliance'][interface_name] = compliant

            if not compliant:
                report['overall_compliance'] = False
                # Find missing methods (if it's an ABC)
                if hasattr(interface_class, '__abstractmethods__'):
                    for method_name in interface_class.__abstractmethods__:
                        if not hasattr(manager, method_name):
                            report['missing_methods'].append(f"{interface_name}.{method_name}")

        return report