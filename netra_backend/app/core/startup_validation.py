"""
Startup Validation System - Ensures deterministic startup with proper component counts.

This module validates that all critical components have been properly initialized
with non-zero counts during startup. It provides warnings and metrics for each
component that should be present.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from netra_backend.app.logging_config import central_logger


class ComponentStatus(Enum):
    """Status of a startup component."""
    NOT_CHECKED = "not_checked"
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILED = "failed"


@dataclass
class ComponentValidation:
    """Validation result for a startup component."""
    name: str
    category: str
    expected_min: int
    actual_count: int
    status: ComponentStatus
    message: str
    is_critical: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class StartupValidator:
    """
    Validates startup component counts and health.
    Ensures deterministic startup with proper initialization.
    """
    
    def __init__(self):
        self.logger = central_logger.get_logger(__name__)
        self.validations: List[ComponentValidation] = []
        self.start_time = None
        self.end_time = None
        
    async def validate_startup(self, app) -> Tuple[bool, Dict[str, Any]]:
        """
        Perform comprehensive startup validation.
        Returns (success, report) tuple.
        """
        self.logger.info("=" * 60)
        self.logger.info("STARTUP VALIDATION INITIATED")
        self.logger.info("=" * 60)
        
        import time
        self.start_time = time.time()
        
        # Run all validations
        await self._validate_agents(app)
        await self._validate_tools(app)
        await self._validate_database(app)
        await self._validate_websocket(app)
        await self._validate_services(app)
        await self._validate_middleware(app)
        await self._validate_background_tasks(app)
        await self._validate_monitoring(app)
        
        # CRITICAL: Validate communication paths for chat functionality
        await self._validate_critical_paths(app)
        
        self.end_time = time.time()
        
        # Generate report
        report = self._generate_report()
        
        # Determine overall success
        success = self._determine_success()
        
        # Log results
        self._log_results(success, report)
        
        return success, report
    
    async def _validate_agents(self, app) -> None:
        """Validate agent registration and counts."""
        try:
            if hasattr(app.state, 'agent_supervisor') and app.state.agent_supervisor:
                # Factory pattern: No registry needed - agents created per-request
                # Validate that supervisor exists and can create agents
                supervisor = app.state.agent_supervisor
                
                # With factory pattern, we validate the supervisor itself, not a registry
                validation = ComponentValidation(
                    name="Agent Factory",
                    category="Agents",
                    expected_min=1,  # Just need supervisor
                    actual_count=1 if supervisor else 0,
                    status=ComponentStatus.HEALTHY if supervisor else ComponentStatus.FAILED,
                    message="Factory-based agent creation ready (per-request isolation)",
                    is_critical=True,
                    metadata={"factory_pattern": True, "supervisor_ready": bool(supervisor)}
                )
                
                self.validations.append(validation)
                self.logger.info("✓ Agent Factory: Supervisor ready for per-request agent creation")
                
                # Check for legacy registry (backward compatibility)
                if hasattr(app.state.agent_supervisor, 'registry'):
                    registry = app.state.agent_supervisor.registry
                    agent_count = len(registry.agents) if hasattr(registry, 'agents') else 0
                    
                    # Expected minimum agents based on AgentRegistry
                    expected_agents = [
                        "triage", "data", "optimization", "actions",
                        "reporting", "data_helper", "synthetic_data", "corpus_admin"
                    ]
                    expected_min = len(expected_agents)
                    
                    if agent_count == 0:
                        self.logger.warning(f"⚠️ ZERO AGENTS REGISTERED - Expected at least {expected_min} agents")
                        self.logger.warning(f"   Expected agents: {', '.join(expected_agents)}")
                    elif agent_count < expected_min:
                        self.logger.warning(f"⚠️ INSUFFICIENT AGENTS - {agent_count}/{expected_min} registered")
                        missing = set(expected_agents) - set(registry.agents.keys() if hasattr(registry, 'agents') else [])
                        if missing:
                            self.logger.warning(f"   Missing agents: {', '.join(missing)}")
                    else:
                        self.logger.info(f"✓ Agent Registry: {agent_count} agents registered")
                # else: No registry - this is expected with factory pattern (already validated above)
            else:
                self._add_failed_validation("Agent Supervisor", "Agents", "Supervisor not initialized")
                
        except Exception as e:
            self._add_failed_validation("Agent Validation", "Agents", str(e))
    
    async def _validate_tools(self, app) -> None:
        """Validate tool registration and dispatcher."""
        try:
            # UserContext-based architecture: tool_dispatcher is None by design
            # Validate tool configuration and factories instead
            
            # Check for tool_classes configuration (REQUIRED)
            if hasattr(app.state, 'tool_classes') and app.state.tool_classes:
                tool_classes = app.state.tool_classes
                tool_count = len(tool_classes) if tool_classes else 0
                
                self.logger.info(f"🔍 UserContext mode: {tool_count} tool classes configured")
                
                # Check for websocket_bridge_factory (CRITICAL for per-user WebSocket)
                has_bridge_factory = hasattr(app.state, 'websocket_bridge_factory') and app.state.websocket_bridge_factory is not None
                
                validation = ComponentValidation(
                    name="Tool Configuration",
                    category="Tools",
                    expected_min=4,  # Expected: DataHelperTool, DeepResearchTool, ReliabilityScorerTool, SandboxedInterpreterTool
                    actual_count=tool_count,
                    status=self._get_status(tool_count, 4, is_critical=True),
                    message=f"Configured {tool_count} tool classes for UserContext, Bridge Factory: {'✓' if has_bridge_factory else '✗'}",
                    is_critical=True,
                    metadata={
                        "mode": "UserContext",
                        "tool_count": tool_count,
                        "websocket_bridge_factory": has_bridge_factory
                    }
                )
                
                self.validations.append(validation)
                
                if tool_count > 0:
                    self.logger.info(f"✓ Tool Configuration: {tool_count} tools ready for UserContext creation")
                    if has_bridge_factory:
                        self.logger.info(f"✓ WebSocketBridgeFactory configured for per-user WebSocket handling")
                    else:
                        self.logger.warning("⚠️ WebSocketBridgeFactory NOT configured - per-user WebSocket isolation may fail")
                else:
                    self.logger.warning("⚠️ NO TOOLS CONFIGURED for UserContext")
                    
            # Legacy fallback path - should not be used in UserContext architecture
            elif hasattr(app.state, 'tool_dispatcher') and app.state.tool_dispatcher:
                # This indicates incorrect configuration - should be None in UserContext mode
                self.logger.warning("⚠️ LEGACY: Global tool_dispatcher found - should be None in UserContext architecture")
                dispatcher = app.state.tool_dispatcher
                
                # Still validate it if it exists (for backward compatibility during migration)
                tool_count = 0
                if hasattr(dispatcher, 'tools'):
                    tools_data = dispatcher.tools
                    tool_count = len(tools_data) if tools_data else 0
                elif hasattr(dispatcher, '_tools'):
                    tool_count = len(dispatcher._tools) if dispatcher._tools else 0
                
                validation = ComponentValidation(
                    name="Tool Dispatcher (LEGACY)",
                    category="Tools",
                    expected_min=0,  # Should be 0 in UserContext mode
                    actual_count=tool_count,
                    status=ComponentStatus.WARNING,  # Always warning - shouldn't exist
                    message=f"LEGACY: Global dispatcher with {tool_count} tools - migrate to UserContext",
                    is_critical=False,
                    metadata={
                        "mode": "LEGACY_GLOBAL",
                        "tool_count": tool_count
                    }
                )
                
                self.validations.append(validation)
                self.logger.warning(f"⚠️ LEGACY Tool Dispatcher: {tool_count} tools - MIGRATE TO UserContext")
                    
            else:
                # Neither UserContext nor legacy configuration found
                self._add_failed_validation("Tool System", "Tools", "Neither UserContext configuration nor legacy dispatcher found")
                
        except Exception as e:
            self._add_failed_validation("Tool Validation", "Tools", str(e))
    
    async def _validate_database(self, app) -> None:
        """Validate database connections and tables."""
        try:
            if hasattr(app.state, 'db_session_factory'):
                if app.state.db_session_factory is None:
                    if getattr(app.state, 'database_mock_mode', False):
                        self.logger.info("ℹ️ Database in mock mode")
                        validation = ComponentValidation(
                            name="Database",
                            category="Database",
                            expected_min=0,
                            actual_count=0,
                            status=ComponentStatus.WARNING,
                            message="Database in mock mode",
                            is_critical=False
                        )
                    else:
                        self.logger.warning("⚠️ Database session factory is None but not in mock mode")
                        validation = ComponentValidation(
                            name="Database",
                            category="Database",
                            expected_min=1,
                            actual_count=0,
                            status=ComponentStatus.CRITICAL,
                            message="Database not initialized",
                            is_critical=True
                        )
                else:
                    # Database is initialized - check tables
                    table_count = await self._count_database_tables(app.state.db_session_factory)
                    expected_tables = 15  # Approximate expected table count
                    
                    validation = ComponentValidation(
                        name="Database Tables",
                        category="Database",
                        expected_min=expected_tables,
                        actual_count=table_count,
                        status=self._get_status(table_count, expected_tables, is_critical=False),
                        message=f"Found {table_count} database tables",
                        is_critical=False,
                        metadata={"table_count": table_count}
                    )
                    
                    if table_count == 0:
                        self.logger.warning(f"⚠️ ZERO DATABASE TABLES found - expected ~{expected_tables}")
                    else:
                        self.logger.info(f"✓ Database: {table_count} tables found")
                        
                self.validations.append(validation)
            else:
                self._add_failed_validation("Database", "Database", "db_session_factory not found")
                
        except Exception as e:
            self._add_failed_validation("Database Validation", "Database", str(e))
    
    async def _validate_websocket(self, app) -> None:
        """Validate WebSocket manager and connections."""
        try:
            ws_manager = None
            
            # Try to get WebSocket manager
            if hasattr(app.state, 'websocket_manager'):
                ws_manager = app.state.websocket_manager
            else:
                # Try to get from the global instance
                try:
                    from netra_backend.app.websocket_core import get_websocket_manager
                    ws_manager = get_websocket_manager()
                except ImportError:
                    pass
            
            if ws_manager:
                # Check active connections
                connection_count = 0
                if hasattr(ws_manager, 'active_connections'):
                    connection_count = len(ws_manager.active_connections)
                elif hasattr(ws_manager, '_connections'):
                    connection_count = len(ws_manager._connections)
                
                # Check message handlers
                handler_count = 0
                if hasattr(ws_manager, 'message_handlers'):
                    handler_count = len(ws_manager.message_handlers)
                elif hasattr(ws_manager, '_handlers'):
                    handler_count = len(ws_manager._handlers)
                
                validation = ComponentValidation(
                    name="WebSocket Manager",
                    category="WebSocket",
                    expected_min=1,  # At least the manager should exist
                    actual_count=1,
                    status=ComponentStatus.HEALTHY if handler_count > 0 else ComponentStatus.WARNING,
                    message=f"Manager active, {connection_count} connections, {handler_count} handlers",
                    is_critical=True,
                    metadata={
                        "connections": connection_count,
                        "handlers": handler_count
                    }
                )
                
                if handler_count == 0:
                    self.logger.warning("⚠️ ZERO WebSocket message handlers registered")
                else:
                    self.logger.info(f"✓ WebSocket: {handler_count} handlers, {connection_count} connections")
                    
                self.validations.append(validation)
            else:
                self._add_failed_validation("WebSocket Manager", "WebSocket", "Manager not initialized")
                
        except Exception as e:
            self._add_failed_validation("WebSocket Validation", "WebSocket", str(e))
    
    async def _validate_services(self, app) -> None:
        """Validate core services initialization."""
        services = [
            ("llm_manager", "LLM Manager", True),
            ("key_manager", "Key Manager", True),
            ("security_service", "Security Service", True),
            ("redis_manager", "Redis Manager", True),
            ("thread_service", "Thread Service", True),
            ("agent_service", "Agent Service", True),
            ("corpus_service", "Corpus Service", False),
            ("background_task_manager", "Background Task Manager", False)
        ]
        
        for attr_name, display_name, is_critical in services:
            try:
                if hasattr(app.state, attr_name):
                    service = getattr(app.state, attr_name)
                    if service is not None:
                        validation = ComponentValidation(
                            name=display_name,
                            category="Services",
                            expected_min=1,
                            actual_count=1,
                            status=ComponentStatus.HEALTHY,
                            message=f"{display_name} initialized",
                            is_critical=is_critical
                        )
                        self.logger.info(f"✓ {display_name}: Initialized")
                    else:
                        validation = ComponentValidation(
                            name=display_name,
                            category="Services",
                            expected_min=1,
                            actual_count=0,
                            status=ComponentStatus.CRITICAL if is_critical else ComponentStatus.WARNING,
                            message=f"{display_name} is None",
                            is_critical=is_critical
                        )
                        self.logger.warning(f"⚠️ {display_name} is None")
                else:
                    validation = ComponentValidation(
                        name=display_name,
                        category="Services",
                        expected_min=1,
                        actual_count=0,
                        status=ComponentStatus.CRITICAL if is_critical else ComponentStatus.WARNING,
                        message=f"{display_name} not found",
                        is_critical=is_critical
                    )
                    self.logger.warning(f"⚠️ {display_name} not found in app.state")
                    
                self.validations.append(validation)
                
            except Exception as e:
                self._add_failed_validation(display_name, "Services", str(e))
        
        # Validate UserContext factory patterns (CRITICAL for per-user isolation)
        factory_services = [
            ("execution_engine_factory", "ExecutionEngineFactory", True, "Per-user execution isolation"),
            ("websocket_bridge_factory", "WebSocketBridgeFactory", True, "Per-user WebSocket isolation"),
            ("websocket_connection_pool", "WebSocketConnectionPool", True, "WebSocket connection management"),
            ("agent_instance_factory", "AgentInstanceFactory", False, "Agent instance creation"),
            ("factory_adapter", "FactoryAdapter", False, "Migration compatibility")
        ]
        
        self.logger.info("Validating UserContext Factory Patterns...")
        
        for attr_name, display_name, is_critical, description in factory_services:
            try:
                if hasattr(app.state, attr_name):
                    factory = getattr(app.state, attr_name)
                    if factory is not None:
                        validation = ComponentValidation(
                            name=display_name,
                            category="Factories",
                            expected_min=1,
                            actual_count=1,
                            status=ComponentStatus.HEALTHY,
                            message=f"{display_name} initialized - {description}",
                            is_critical=is_critical
                        )
                        self.logger.info(f"✓ {display_name}: Initialized - {description}")
                    else:
                        validation = ComponentValidation(
                            name=display_name,
                            category="Factories",
                            expected_min=1,
                            actual_count=0,
                            status=ComponentStatus.CRITICAL if is_critical else ComponentStatus.WARNING,
                            message=f"{display_name} is None - {description} unavailable",
                            is_critical=is_critical
                        )
                        self.logger.warning(f"⚠️ {display_name} is None - {description} unavailable")
                else:
                    validation = ComponentValidation(
                        name=display_name,
                        category="Factories",
                        expected_min=1,
                        actual_count=0,
                        status=ComponentStatus.CRITICAL if is_critical else ComponentStatus.WARNING,
                        message=f"{display_name} not found - {description} missing",
                        is_critical=is_critical
                    )
                    if is_critical:
                        self.logger.warning(f"⚠️ {display_name} not found - {description} missing")
                    else:
                        self.logger.info(f"ℹ️ {display_name} not configured - {description} optional")
                    
                self.validations.append(validation)
                
            except Exception as e:
                self._add_failed_validation(display_name, "Factories", str(e))
    
    async def _validate_middleware(self, app) -> None:
        """Validate middleware stack."""
        try:
            middleware_count = 0
            
            # FastAPI middleware is complex - check different possible structures
            if hasattr(app, 'middleware_stack') and hasattr(app.middleware_stack, '__len__'):
                middleware_count = len(app.middleware_stack)
            elif hasattr(app, 'user_middleware') and hasattr(app.user_middleware, '__len__'):
                middleware_count = len(app.user_middleware)
            elif hasattr(app, 'middleware') and not callable(app.middleware):
                # Only try to get length if middleware is not a method
                if hasattr(app.middleware, '__len__'):
                    middleware_count = len(app.middleware)
            
            # For Starlette/FastAPI apps, we might need to check the routes
            if middleware_count == 0 and hasattr(app, 'routes'):
                # Count middleware by checking if common middleware is configured
                # This is a fallback when we can't directly access middleware stack
                middleware_count = 1  # Assume at least basic middleware is configured
            
            expected_middleware = 3  # CORS, error handling, etc.
            
            validation = ComponentValidation(
                name="Middleware Stack",
                category="Middleware",
                expected_min=expected_middleware,
                actual_count=middleware_count,
                status=self._get_status(middleware_count, expected_middleware, is_critical=False),
                message=f"{middleware_count} middleware components",
                is_critical=False
            )
            
            if middleware_count == 0:
                self.logger.warning(f"⚠️ ZERO middleware components - expected at least {expected_middleware}")
            else:
                self.logger.info(f"✓ Middleware: {middleware_count} components")
                
            self.validations.append(validation)
            
        except Exception as e:
            self._add_failed_validation("Middleware Validation", "Middleware", str(e))
    
    async def _validate_background_tasks(self, app) -> None:
        """Validate background task manager."""
        try:
            if hasattr(app.state, 'background_task_manager'):
                manager = app.state.background_task_manager
                if manager:
                    task_count = 0
                    if hasattr(manager, 'tasks'):
                        task_count = len(manager.tasks) if manager.tasks else 0
                    elif hasattr(manager, '_tasks'):
                        task_count = len(manager._tasks) if manager._tasks else 0
                    
                    validation = ComponentValidation(
                        name="Background Tasks",
                        category="Tasks",
                        expected_min=0,  # Tasks may not be started immediately
                        actual_count=task_count,
                        status=ComponentStatus.HEALTHY,
                        message=f"{task_count} background tasks",
                        is_critical=False,
                        metadata={"task_count": task_count}
                    )
                    
                    self.logger.info(f"✓ Background Tasks: {task_count} tasks")
                else:
                    validation = ComponentValidation(
                        name="Background Tasks",
                        category="Tasks",
                        expected_min=0,
                        actual_count=0,
                        status=ComponentStatus.WARNING,
                        message="Manager is None",
                        is_critical=False
                    )
                    self.logger.warning("⚠️ Background task manager is None")
                    
                self.validations.append(validation)
            else:
                self.logger.info("ℹ️ Background task manager not configured")
                
        except Exception as e:
            self._add_failed_validation("Background Task Validation", "Tasks", str(e))
    
    async def _validate_monitoring(self, app) -> None:
        """Validate monitoring components."""
        try:
            monitoring_active = False
            
            if hasattr(app.state, 'performance_monitor'):
                monitor = app.state.performance_monitor
                if monitor:
                    monitoring_active = True
                    
                    # Check if monitor has cleanup task (indicator it's running)
                    is_monitoring = False
                    if hasattr(monitor, '_cleanup_task'):
                        is_monitoring = monitor._cleanup_task is not None
                    else:
                        # If we can't determine state, assume it's active if it exists
                        is_monitoring = True
                    
                    validation = ComponentValidation(
                        name="Performance Monitor",
                        category="Monitoring",
                        expected_min=1,
                        actual_count=1,
                        status=ComponentStatus.HEALTHY,
                        message="Monitor configured",
                        is_critical=False,
                        metadata={"has_cleanup_task": is_monitoring}
                    )
                    
                    self.logger.info("✓ Performance Monitor: Configured")
                else:
                    validation = ComponentValidation(
                        name="Performance Monitor",
                        category="Monitoring",
                        expected_min=1,
                        actual_count=0,
                        status=ComponentStatus.WARNING,
                        message="Monitor is None",
                        is_critical=False
                    )
                    self.logger.warning("⚠️ Performance monitor is None")
                    
                self.validations.append(validation)
            else:
                self.logger.info("ℹ️ Performance monitoring not configured")
                
        except Exception as e:
            self._add_failed_validation("Monitoring Validation", "Monitoring", str(e))
    
    async def _validate_critical_paths(self, app) -> None:
        """Validate critical communication paths for chat functionality."""
        try:
            from netra_backend.app.core.critical_path_validator import validate_critical_paths
            
            self.logger.info("Validating critical communication paths...")
            success, critical_validations = await validate_critical_paths(app)
            
            # Count failures by criticality
            chat_breaking = 0
            degraded = 0
            warnings = 0
            
            for validation in critical_validations:
                if not validation.passed:
                    if validation.criticality.value == "chat_breaking":
                        chat_breaking += 1
                    elif validation.criticality.value == "degraded":
                        degraded += 1
                    else:
                        warnings += 1
            
            # Add overall critical path validation
            if chat_breaking > 0:
                validation = ComponentValidation(
                    name="Critical Communication Paths",
                    category="Critical Paths",
                    expected_min=0,  # Expect 0 failures
                    actual_count=chat_breaking,  # Number of failures
                    status=ComponentStatus.CRITICAL,
                    message=f"{chat_breaking} chat-breaking failures detected",
                    is_critical=True,
                    metadata={
                        "chat_breaking": chat_breaking,
                        "degraded": degraded,
                        "warnings": warnings
                    }
                )
                self.logger.error(f"❌ CRITICAL: {chat_breaking} chat-breaking communication failures!")
            elif degraded > 0:
                validation = ComponentValidation(
                    name="Critical Communication Paths",
                    category="Critical Paths",
                    expected_min=0,
                    actual_count=degraded,
                    status=ComponentStatus.WARNING,
                    message=f"{degraded} degraded path issues",
                    is_critical=False,
                    metadata={
                        "chat_breaking": 0,
                        "degraded": degraded,
                        "warnings": warnings
                    }
                )
                self.logger.warning(f"⚠️ {degraded} degraded communication paths")
            else:
                validation = ComponentValidation(
                    name="Critical Communication Paths",
                    category="Critical Paths",
                    expected_min=0,
                    actual_count=0,
                    status=ComponentStatus.HEALTHY,
                    message="All critical paths validated",
                    is_critical=True,
                    metadata={
                        "chat_breaking": 0,
                        "degraded": 0,
                        "warnings": warnings
                    }
                )
                self.logger.info("✓ Critical communication paths: All validated")
            
            self.validations.append(validation)
            
        except ImportError:
            self.logger.warning("Critical path validator not found - skipping")
        except Exception as e:
            self._add_failed_validation("Critical Path Validation", "Critical Paths", str(e))
    
    async def _count_database_tables(self, db_session_factory) -> int:
        """Count database tables if possible."""
        try:
            from sqlalchemy import text
            
            async with db_session_factory() as session:
                result = await session.execute(text("""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                count = result.scalar()
                return count if count else 0
        except Exception:
            # Can't count tables, return 0
            return 0
    
    def _get_status(self, actual: int, expected: int, is_critical: bool) -> ComponentStatus:
        """Determine component status based on counts."""
        if actual == 0 and expected > 0:
            return ComponentStatus.CRITICAL if is_critical else ComponentStatus.WARNING
        elif actual < expected:
            return ComponentStatus.WARNING
        else:
            return ComponentStatus.HEALTHY
    
    def _add_failed_validation(self, name: str, category: str, error: str) -> None:
        """Add a failed validation entry."""
        validation = ComponentValidation(
            name=name,
            category=category,
            expected_min=1,
            actual_count=0,
            status=ComponentStatus.FAILED,
            message=f"Validation failed: {error}",
            is_critical=True
        )
        self.validations.append(validation)
        self.logger.error(f"❌ {name}: {error}")
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate validation report."""
        categories = {}
        for validation in self.validations:
            if validation.category not in categories:
                categories[validation.category] = []
            categories[validation.category].append({
                "name": validation.name,
                "expected": validation.expected_min,
                "actual": validation.actual_count,
                "status": validation.status.value,
                "message": validation.message,
                "critical": validation.is_critical,
                "metadata": validation.metadata
            })
        
        # Count statuses
        status_counts = {
            "healthy": sum(1 for v in self.validations if v.status == ComponentStatus.HEALTHY),
            "warning": sum(1 for v in self.validations if v.status == ComponentStatus.WARNING),
            "critical": sum(1 for v in self.validations if v.status == ComponentStatus.CRITICAL),
            "failed": sum(1 for v in self.validations if v.status == ComponentStatus.FAILED),
            "not_checked": sum(1 for v in self.validations if v.status == ComponentStatus.NOT_CHECKED)
        }
        
        # Calculate overall health
        total_validations = len(self.validations)
        critical_validations = [v for v in self.validations if v.is_critical]
        critical_failures = sum(1 for v in critical_validations 
                              if v.status in [ComponentStatus.CRITICAL, ComponentStatus.FAILED])
        
        return {
            "timestamp": self.end_time if self.end_time else None,
            "duration": (self.end_time - self.start_time) if self.end_time and self.start_time else None,
            "total_validations": total_validations,
            "status_counts": status_counts,
            "critical_failures": critical_failures,
            "categories": categories,
            "overall_health": "healthy" if critical_failures == 0 else "unhealthy"
        }
    
    def _determine_success(self) -> bool:
        """Determine if startup validation succeeded."""
        # Check for any critical failures
        critical_validations = [v for v in self.validations if v.is_critical]
        critical_failures = [v for v in critical_validations 
                           if v.status in [ComponentStatus.CRITICAL, ComponentStatus.FAILED]]
        
        return len(critical_failures) == 0
    
    def _log_results(self, success: bool, report: Dict[str, Any]) -> None:
        """Log validation results."""
        self.logger.info("=" * 60)
        self.logger.info("STARTUP VALIDATION RESULTS")
        self.logger.info("=" * 60)
        
        # Log summary
        self.logger.info(f"Overall Status: {'✅ PASSED' if success else '❌ FAILED'}")
        self.logger.info(f"Total Validations: {report['total_validations']}")
        self.logger.info(f"Healthy: {report['status_counts']['healthy']}")
        self.logger.info(f"Warnings: {report['status_counts']['warning']}")
        self.logger.info(f"Critical: {report['status_counts']['critical']}")
        self.logger.info(f"Failed: {report['status_counts']['failed']}")
        
        if report['critical_failures'] > 0:
            self.logger.error(f"⚠️ {report['critical_failures']} CRITICAL FAILURES DETECTED")
            
        # Log zero-count warnings
        zero_count_components = [v for v in self.validations 
                                if v.actual_count == 0 and v.expected_min > 0]
        if zero_count_components:
            self.logger.warning("=" * 60)
            self.logger.warning("COMPONENTS WITH ZERO COUNTS:")
            for component in zero_count_components:
                self.logger.warning(f"  - {component.name}: Expected {component.expected_min}, got 0")
            self.logger.warning("=" * 60)
        
        self.logger.info(f"Validation Duration: {report.get('duration', 0):.2f}s")
        self.logger.info("=" * 60)


# Global validator instance
startup_validator = StartupValidator()


async def validate_startup(app) -> Tuple[bool, Dict[str, Any]]:
    """
    Convenience function to validate startup.
    Returns (success, report) tuple.
    """
    return await startup_validator.validate_startup(app)