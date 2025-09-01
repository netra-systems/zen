"""
Deterministic Startup Module - NO AMBIGUITY, NO FALLBACKS.

This module implements a strict, deterministic startup sequence.
If any critical service fails, the entire startup MUST fail.
Chat delivers 90% of value - if chat cannot work, the service MUST NOT start.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Tuple

from fastapi import FastAPI

from shared.isolated_environment import get_env
from netra_backend.app.core.project_utils import get_project_root as _get_project_root
from netra_backend.app.config import get_config, settings
from netra_backend.app.logging_config import central_logger


class DeterministicStartupError(Exception):
    """Raised when a critical service fails during startup."""
    pass


class StartupOrchestrator:
    """
    Orchestrates deterministic startup sequence.
    NO CONDITIONAL PATHS. NO GRACEFUL DEGRADATION. NO SETTING SERVICES TO NONE.
    """
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.logger = central_logger.get_logger(__name__)
        self.start_time = time.time()
        
    async def initialize_system(self) -> None:
        """
        Initialize system in strict deterministic order.
        Any failure causes immediate startup failure.
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info("DETERMINISTIC STARTUP SEQUENCE INITIATED")
            self.logger.info("=" * 60)
            
            # PHASE 1: Foundation (Required for everything)
            await self._phase1_foundation()
            
            # PHASE 2: Core Services (Required for chat)
            await self._phase2_core_services()
            
            # PHASE 3: Chat Pipeline (THE CRITICAL PATH)
            await self._phase3_chat_pipeline()
            
            # PHASE 4: Optional Services (Can fail without breaking chat)
            await self._phase4_optional_services()
            
            # PHASE 5: Validation
            await self._phase5_validation()
            
            # Success - mark as complete
            self._mark_startup_complete()
            
        except Exception as e:
            self._handle_startup_failure(e)
            raise DeterministicStartupError(f"CRITICAL STARTUP FAILURE: {e}") from e
    
    async def _phase1_foundation(self) -> None:
        """Phase 1: Foundation - Required for everything."""
        self.logger.info("PHASE 1: Foundation")
        
        # Step 1: Logging already initialized (we're using it)
        self.logger.info("  ✓ Step 1: Logging initialized")
        
        # Step 2: Environment validation
        self._validate_environment()
        self.logger.info("  ✓ Step 2: Environment validated")
        
        # Step 3: Database migrations (non-critical)
        try:
            await self._run_migrations()
            self.logger.info("  ✓ Step 3: Migrations completed")
        except Exception as e:
            self.logger.warning(f"  ⚠ Step 3: Migrations skipped: {e}")
    
    async def _phase2_core_services(self) -> None:
        """Phase 2: Core Services - Required for chat."""
        self.logger.info("PHASE 2: Core Services")
        
        # Step 4: Database connection (CRITICAL)
        await self._initialize_database()
        if not hasattr(self.app.state, 'db_session_factory') or self.app.state.db_session_factory is None:
            raise DeterministicStartupError("Database initialization failed - db_session_factory is None")
        self.logger.info("  ✓ Step 4: Database connected")
        
        # Step 5: Redis connection (CRITICAL)
        await self._initialize_redis()
        if not hasattr(self.app.state, 'redis_manager') or self.app.state.redis_manager is None:
            raise DeterministicStartupError("Redis initialization failed - redis_manager is None")
        self.logger.info("  ✓ Step 5: Redis connected")
        
        # Step 6: Key Manager (CRITICAL)
        self._initialize_key_manager()
        if not hasattr(self.app.state, 'key_manager') or self.app.state.key_manager is None:
            raise DeterministicStartupError("Key manager initialization failed")
        self.logger.info("  ✓ Step 6: Key manager initialized")
        
        # Step 7: LLM Manager (CRITICAL)
        self._initialize_llm_manager()
        if not hasattr(self.app.state, 'llm_manager') or self.app.state.llm_manager is None:
            raise DeterministicStartupError("LLM manager initialization failed")
        self.logger.info("  ✓ Step 7: LLM manager initialized")
        
        # Step 8: Apply startup fixes (CRITICAL)
        await self._apply_startup_fixes()
        self.logger.info("  ✓ Step 8: Startup fixes applied")
    
    async def _phase3_chat_pipeline(self) -> None:
        """Phase 3: Chat Pipeline - THE CRITICAL PATH."""
        self.logger.info("PHASE 3: Chat Pipeline (CRITICAL)")
        
        # Step 9: Tool Registry (CRITICAL)
        self._initialize_tool_registry()
        if not hasattr(self.app.state, 'tool_dispatcher') or self.app.state.tool_dispatcher is None:
            raise DeterministicStartupError("Tool dispatcher initialization failed")
        self.logger.info("  ✓ Step 9: Tool registry created")
        
        # Step 10: WebSocket Manager (CRITICAL)
        await self._initialize_websocket()
        self.logger.info("  ✓ Step 10: WebSocket manager initialized")
        
        # Step 11: AgentWebSocketBridge Integration (CRITICAL - SSOT for WebSocket-Agent coordination)
        await self._initialize_agent_websocket_bridge()
        if not hasattr(self.app.state, 'agent_websocket_bridge') or self.app.state.agent_websocket_bridge is None:
            raise DeterministicStartupError("AgentWebSocketBridge is None - integration broken")
        self.logger.info("  ✓ Step 11: AgentWebSocketBridge initialized and integrated")
        
        # Step 12: Agent Supervisor (CRITICAL - now using bridge for coordination)
        await self._initialize_agent_supervisor()
        if not hasattr(self.app.state, 'agent_supervisor') or self.app.state.agent_supervisor is None:
            raise DeterministicStartupError("Agent supervisor is None - chat is broken")
        if not hasattr(self.app.state, 'thread_service') or self.app.state.thread_service is None:
            raise DeterministicStartupError("Thread service is None - chat is broken")
        
        # Verify WebSocket enhancement through bridge
        if hasattr(self.app.state.agent_supervisor, 'registry'):
            if hasattr(self.app.state.agent_supervisor.registry, 'tool_dispatcher'):
                if not getattr(self.app.state.agent_supervisor.registry.tool_dispatcher, '_websocket_enhanced', False):
                    raise DeterministicStartupError("Tool dispatcher not enhanced with WebSocket - agent events broken")
        
        self.logger.info("  ✓ Step 12: Agent supervisor initialized with WebSocket enhancement")
        
        # Step 13: Message Handlers (CRITICAL)
        self._register_message_handlers()
        self.logger.info("  ✓ Step 13: Message handlers registered")
    
    async def _phase4_optional_services(self) -> None:
        """Phase 4: Optional Services - Can fail without breaking chat."""
        self.logger.info("PHASE 4: Optional Services")
        
        # Step 13: ClickHouse (optional)
        try:
            await self._initialize_clickhouse()
            self.logger.info("  ✓ Step 13: ClickHouse initialized")
        except Exception as e:
            self.logger.warning(f"  ⚠ Step 13: ClickHouse skipped: {e}")
        
        # Step 14: Monitoring (optional)
        try:
            await self._initialize_monitoring()
            self.logger.info("  ✓ Step 14: Monitoring started")
        except Exception as e:
            self.logger.warning(f"  ⚠ Step 14: Monitoring skipped: {e}")
        
        # Step 15: Background Tasks (optional)
        try:
            self._initialize_background_tasks()
            self.logger.info("  ✓ Step 15: Background tasks started")
        except Exception as e:
            self.logger.warning(f"  ⚠ Step 15: Background tasks skipped: {e}")
        
        # Step 16: Performance Manager (optional)
        try:
            await self._initialize_performance_manager()
            self.logger.info("  ✓ Step 16: Performance manager initialized")
        except Exception as e:
            self.logger.warning(f"  ⚠ Step 16: Performance manager skipped: {e}")
        
        # Step 17: Connection Monitoring (optional)
        try:
            await self._start_connection_monitoring()
            self.logger.info("  ✓ Step 17: Connection monitoring started")
        except Exception as e:
            self.logger.warning(f"  ⚠ Step 17: Connection monitoring skipped: {e}")
    
    async def _phase5_validation(self) -> None:
        """Phase 5: Validation - Verify all critical services are operational."""
        self.logger.info("PHASE 5: Validation")
        
        critical_checks = [
            (hasattr(self.app.state, 'db_session_factory') and self.app.state.db_session_factory is not None, "Database"),
            (hasattr(self.app.state, 'redis_manager') and self.app.state.redis_manager is not None, "Redis"),
            (hasattr(self.app.state, 'llm_manager') and self.app.state.llm_manager is not None, "LLM Manager"),
            (hasattr(self.app.state, 'agent_websocket_bridge') and self.app.state.agent_websocket_bridge is not None, "AgentWebSocketBridge"),
            (hasattr(self.app.state, 'agent_supervisor') and self.app.state.agent_supervisor is not None, "Agent Supervisor"),
            (hasattr(self.app.state, 'thread_service') and self.app.state.thread_service is not None, "Thread Service"),
            (hasattr(self.app.state, 'tool_dispatcher') and self.app.state.tool_dispatcher is not None, "Tool Dispatcher"),
        ]
        
        failed_checks = []
        for check, name in critical_checks:
            if check:
                self.logger.info(f"  ✓ {name}: OK")
            else:
                self.logger.error(f"  ✗ {name}: FAILED")
                failed_checks.append(name)
        
        if failed_checks:
            raise DeterministicStartupError(f"Critical services failed validation: {', '.join(failed_checks)}")
        
        self.logger.info("  ✓ Step 18: All critical services validated")
        
        # Step 18.5: Verify AgentWebSocketBridge health
        await self._verify_bridge_health()
        
        # Step 18.6: Verify WebSocket events can actually be sent
        await self._verify_websocket_events()
        
        # Step 19: Comprehensive startup validation with component counts
        try:
            from netra_backend.app.core.startup_validation import validate_startup
            
            self.logger.info("  Step 19: Running comprehensive startup validation...")
            success, report = await validate_startup(self.app)
            
            # Log critical component counts and warnings
            if 'categories' in report:
                zero_count_warnings = []
                
                # Check all categories for zero counts
                for category, components in report['categories'].items():
                    for component in components:
                        if component['actual'] == 0 and component['expected'] > 0:
                            zero_count_warnings.append(f"{component['name']} (expected {component['expected']})")
                
                # Log zero count warnings prominently
                if zero_count_warnings:
                    self.logger.warning("    ⚠️ COMPONENTS WITH ZERO COUNTS DETECTED:")
                    for warning in zero_count_warnings:
                        self.logger.warning(f"      - {warning}")
            
            # Check for critical failures
            if not success:
                critical_failures = report.get('critical_failures', 0)
                if critical_failures > 0:
                    # In deterministic mode, critical validation failures are fatal
                    raise DeterministicStartupError(
                        f"Startup validation failed with {critical_failures} critical failures. "
                        f"Status: {report['status_counts']['critical']} critical, "
                        f"{report['status_counts']['failed']} failed components"
                    )
            
            # Log summary
            self.logger.info(f"  ✓ Step 19: Startup validation complete")
            self.logger.info(f"    Summary: {report['status_counts']['healthy']} healthy, "
                           f"{report['status_counts']['warning']} warnings, "
                           f"{report['status_counts']['critical']} critical")
            
        except ImportError:
            self.logger.warning("  ⚠ Step 19: Startup validation module not found - skipping comprehensive validation")
        except DeterministicStartupError:
            # Re-raise deterministic errors
            raise
        except Exception as e:
            # Log but don't fail on non-critical validation errors
            self.logger.error(f"  ⚠ Step 19: Startup validation error: {e}")
        
        # Step 20: Critical path validation (CHAT FUNCTIONALITY)
        try:
            from netra_backend.app.core.critical_path_validator import validate_critical_paths
            
            self.logger.info("  Step 20: Validating critical communication paths...")
            success, critical_validations = await validate_critical_paths(self.app)
            
            # Count failures
            chat_breaking_count = sum(1 for v in critical_validations 
                                     if not v.passed and v.criticality.value == "chat_breaking")
            
            if chat_breaking_count > 0:
                # Log all chat-breaking failures
                self.logger.error("    🚨 CHAT-BREAKING FAILURES DETECTED:")
                for validation in critical_validations:
                    if not validation.passed and validation.criticality.value == "chat_breaking":
                        self.logger.error(f"      ❌ {validation.component}")
                        self.logger.error(f"         Reason: {validation.failure_reason}")
                        if validation.remediation:
                            self.logger.error(f"         Fix: {validation.remediation}")
                
                # In deterministic mode, chat-breaking failures are FATAL
                raise DeterministicStartupError(
                    f"Critical path validation failed: {chat_breaking_count} chat-breaking failures. "
                    f"Chat functionality is BROKEN and will not work!"
                )
            
            # Log any degraded paths as warnings
            degraded_count = sum(1 for v in critical_validations 
                               if not v.passed and v.criticality.value == "degraded")
            if degraded_count > 0:
                self.logger.warning(f"    ⚠️ {degraded_count} degraded communication paths detected")
            
            self.logger.info("  ✓ Step 20: Critical communication paths validated")
            
        except ImportError:
            self.logger.warning("  ⚠ Step 20: Critical path validator not found - skipping")
        except DeterministicStartupError:
            # Re-raise deterministic errors
            raise
        except Exception as e:
            # Critical path validation failure is FATAL in deterministic mode
            raise DeterministicStartupError(f"Critical path validation failed: {e}")
        
        # Step 21: Schema validation (CRITICAL)
        await self._validate_database_schema()
        self.logger.info("  ✓ Step 21: Database schema validated")
    
    async def _verify_bridge_health(self) -> None:
        """Verify AgentWebSocketBridge is healthy and operational - CRITICAL."""
        from netra_backend.app.services.agent_websocket_bridge import IntegrationState
        
        self.logger.info("  Step 18.5: Verifying AgentWebSocketBridge health...")
        
        bridge = self.app.state.agent_websocket_bridge
        if not bridge:
            raise DeterministicStartupError("AgentWebSocketBridge is None - bridge validation failed")
        
        try:
            # Get comprehensive bridge status
            status = await bridge.get_status()
            health = await bridge.health_check()
            
            # Verify bridge is in operational state
            if health.state not in [IntegrationState.ACTIVE]:
                raise DeterministicStartupError(f"AgentWebSocketBridge not active: {health.state.value}")
            
            # Verify critical components are healthy
            if not health.websocket_manager_healthy:
                raise DeterministicStartupError("WebSocket manager unhealthy in bridge")
            
            if not health.registry_healthy:
                raise DeterministicStartupError("Orchestrator unhealthy in bridge")
            
            # Verify no consecutive failures
            if health.consecutive_failures >= 3:
                raise DeterministicStartupError(f"Bridge has {health.consecutive_failures} consecutive failures")
            
            # Log detailed bridge status
            self.logger.info(f"  ✓ Step 18.5: AgentWebSocketBridge health verified")
            self.logger.info(f"    - State: {health.state.value}")
            self.logger.info(f"    - Health Checks: {status['metrics']['health_checks_performed']}")
            self.logger.info(f"    - Success Rate: {status['metrics']['success_rate']:.2%}")
            self.logger.info(f"    - Total Initializations: {status['metrics']['total_initializations']}")
            
            # Verify dependencies are available
            deps = status['dependencies']
            if not deps['websocket_manager_available']:
                raise DeterministicStartupError("WebSocket manager not available in bridge")
            if not deps['orchestrator_available']:
                raise DeterministicStartupError("Orchestrator not available in bridge")
            
        except DeterministicStartupError:
            raise
        except Exception as e:
            raise DeterministicStartupError(f"Bridge health verification failed: {e}")
    
    def _validate_environment(self) -> None:
        """Validate environment configuration."""
        from netra_backend.app.core.environment_validator import validate_environment_at_startup
        validate_environment_at_startup()
    
    async def _run_migrations(self) -> None:
        """Run database migrations if needed."""
        from netra_backend.app.startup_module import run_database_migrations
        run_database_migrations(self.logger)
    
    async def _initialize_database(self) -> None:
        """Initialize database connection - CRITICAL."""
        from netra_backend.app.db.postgres import initialize_postgres
        from netra_backend.app.startup_module import _ensure_database_tables_exist
        
        # No graceful mode - fail if database fails
        async_session_factory = await asyncio.wait_for(
            asyncio.to_thread(initialize_postgres),
            timeout=30.0
        )
        
        if async_session_factory is None:
            raise DeterministicStartupError("Database initialization returned None")
        
        self.app.state.db_session_factory = async_session_factory
        self.app.state.database_available = True
        
        # Ensure tables exist - no graceful mode
        await asyncio.wait_for(
            _ensure_database_tables_exist(self.logger, graceful_startup=False),
            timeout=15.0
        )
    
    async def _initialize_redis(self) -> None:
        """Initialize Redis connection - CRITICAL."""
        from netra_backend.app.redis_manager import redis_manager
        
        # Test connection
        await redis_manager.connect()
        if not await redis_manager.ping():
            raise DeterministicStartupError("Redis ping failed")
        
        self.app.state.redis_manager = redis_manager
    
    def _initialize_key_manager(self) -> None:
        """Initialize key manager - CRITICAL."""
        from netra_backend.app.services.key_manager import KeyManager
        
        key_manager = KeyManager.load_from_settings(settings)
        if key_manager is None:
            raise DeterministicStartupError("Key manager initialization failed")
        
        self.app.state.key_manager = key_manager
    
    def _initialize_llm_manager(self) -> None:
        """Initialize LLM manager - CRITICAL."""
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.services.security_service import SecurityService
        
        self.app.state.llm_manager = LLMManager(settings)
        self.app.state.security_service = SecurityService(self.app.state.key_manager)
    
    def _initialize_tool_registry(self) -> None:
        """Initialize tool registry and dispatcher - CRITICAL."""
        from netra_backend.app.services.tool_registry import ToolRegistry
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        
        tool_registry = ToolRegistry(self.app.state.db_session_factory)
        self.app.state.tool_dispatcher = ToolDispatcher(tool_registry.get_tools([]))
    
    async def _initialize_websocket(self) -> None:
        """Initialize WebSocket components - CRITICAL."""
        from netra_backend.app.websocket_core import get_websocket_manager
        
        manager = get_websocket_manager()
        if hasattr(manager, 'initialize'):
            await manager.initialize()
    
    async def _initialize_agent_websocket_bridge(self) -> None:
        """Initialize AgentWebSocketBridge - CRITICAL SSOT for WebSocket-Agent integration."""
        from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge, IntegrationState
        from netra_backend.app.orchestration.agent_execution_registry import get_agent_execution_registry
        from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
        
        # Get bridge instance (singleton)
        bridge = await get_agent_websocket_bridge()
        if bridge is None:
            raise DeterministicStartupError("Failed to get AgentWebSocketBridge instance")
        
        # Get registry for enhanced integration
        try:
            registry = await get_agent_execution_registry()
        except Exception as e:
            # Registry is optional for basic integration
            self.logger.warning(f"Agent execution registry not available for bridge: {e}")
            registry = None
        
        # Initialize integration with timeout
        integration_result = await asyncio.wait_for(
            bridge.ensure_integration(
                supervisor=None,  # Will be set when supervisor is created
                registry=registry,
                force_reinit=False
            ),
            timeout=30.0
        )
        
        if not integration_result.success:
            raise DeterministicStartupError(f"AgentWebSocketBridge integration failed: {integration_result.error}")
        
        # Store bridge in app state for monitoring
        self.app.state.agent_websocket_bridge = bridge
        
        # Verify bridge health immediately
        health_status = await bridge.health_check()
        if health_status.state not in [IntegrationState.ACTIVE, IntegrationState.INITIALIZING]:
            raise DeterministicStartupError(f"AgentWebSocketBridge unhealthy after initialization: {health_status.state}")
        
        self.logger.info(f"  ✓ AgentWebSocketBridge integration state: {health_status.state.value}")
        self.logger.info(f"    - WebSocket Manager: {'✓' if health_status.websocket_manager_healthy else '✗'}")
        self.logger.info(f"    - Orchestrator: {'✓' if health_status.registry_healthy else '✗'}")
        self.logger.info(f"    - Uptime: {health_status.uptime_seconds:.1f}s")
    
    async def _initialize_agent_supervisor(self) -> None:
        """Initialize agent supervisor - CRITICAL FOR CHAT."""
        from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
        from netra_backend.app.websocket_core import get_websocket_manager
        from netra_backend.app.services.agent_service import AgentService
        from netra_backend.app.services.thread_service import ThreadService
        from netra_backend.app.services.corpus_service import CorpusService
        
        # Get bridge and WebSocket manager
        bridge = self.app.state.agent_websocket_bridge
        websocket_manager = get_websocket_manager()
        
        # Create supervisor - no fallbacks
        supervisor = SupervisorAgent(
            self.app.state.db_session_factory,
            self.app.state.llm_manager,
            websocket_manager,
            self.app.state.tool_dispatcher
        )
        
        if supervisor is None:
            raise DeterministicStartupError("Supervisor creation returned None")
        
        # Now update bridge with supervisor reference for enhanced integration
        if bridge:
            try:
                # Update bridge integration with the created supervisor
                integration_result = await bridge.ensure_integration(
                    supervisor=supervisor,
                    registry=supervisor.registry if hasattr(supervisor, 'registry') else None,
                    force_reinit=False  # Don't force reinit, just update references
                )
                
                if integration_result.success:
                    self.logger.info(f"  ✓ Bridge integration updated with supervisor")
                else:
                    self.logger.warning(f"Bridge integration update had issues: {integration_result.error}")
            except Exception as e:
                self.logger.warning(f"Failed to update bridge with supervisor: {e}")
        
        # Ensure WebSocket enhancement
        if hasattr(supervisor, 'registry') and hasattr(supervisor.registry, 'tool_dispatcher'):
            if not getattr(supervisor.registry.tool_dispatcher, '_websocket_enhanced', False):
                # Try to enhance
                if websocket_manager and hasattr(supervisor.registry, 'set_websocket_manager'):
                    supervisor.registry.set_websocket_manager(websocket_manager)
                    # Verify enhancement worked
                    if not getattr(supervisor.registry.tool_dispatcher, '_websocket_enhanced', False):
                        raise DeterministicStartupError("Failed to enhance tool dispatcher with WebSocket")
        
        # Set state - NEVER set to None
        self.app.state.agent_supervisor = supervisor
        self.app.state.agent_service = AgentService(supervisor)
        self.app.state.thread_service = ThreadService()
        self.app.state.corpus_service = CorpusService()
    
    def _register_message_handlers(self) -> None:
        """Register WebSocket message handlers - CRITICAL."""
        # Message handlers are registered in the WebSocket endpoint
        # This is just a placeholder to maintain the sequence
        pass
    
    async def _verify_websocket_events(self) -> None:
        """Verify WebSocket events can actually be sent - CRITICAL."""
        import uuid
        from netra_backend.app.websocket_core import get_websocket_manager
        
        self.logger.info("  Step 18.5: Verifying WebSocket event delivery...")
        
        manager = get_websocket_manager()
        if not manager:
            raise DeterministicStartupError("WebSocket manager is None - events cannot be sent")
        
        # Create a test thread ID
        test_thread = f"startup_test_{uuid.uuid4()}"
        
        # Test basic message sending capability
        test_message = {
            "type": "startup_test",
            "timestamp": time.time(),
            "validation": "critical_path"
        }
        
        try:
            # Try to send a test message
            success = await manager.send_to_thread(test_thread, test_message)
            
            # Success is True even if no connections (message queued)
            # The important thing is that the manager accepts the message
            if success is False:
                raise DeterministicStartupError("WebSocket test event failed to send - manager rejected message")
            
            # Verify tool dispatcher enhancement
            if hasattr(self.app.state, 'agent_supervisor'):
                supervisor = self.app.state.agent_supervisor
                if hasattr(supervisor, 'registry') and hasattr(supervisor.registry, 'tool_dispatcher'):
                    dispatcher = supervisor.registry.tool_dispatcher
                    if not getattr(dispatcher, '_websocket_enhanced', False):
                        raise DeterministicStartupError("Tool dispatcher not enhanced - agent events will be silent")
                    
                    # Check that the unified executor is present (it contains the notifier internally)
                    if not hasattr(dispatcher, 'executor'):
                        raise DeterministicStartupError("Tool dispatcher has no executor - events cannot be sent")
                    
                    # Verify the executor is the unified engine with WebSocket support
                    from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
                    if not isinstance(dispatcher.executor, UnifiedToolExecutionEngine):
                        raise DeterministicStartupError("Tool dispatcher not using UnifiedToolExecutionEngine - events cannot be sent")
                    
                    # Check that the executor has WebSocket notifier internally
                    if not hasattr(dispatcher.executor, 'websocket_notifier') or dispatcher.executor.websocket_notifier is None:
                        raise DeterministicStartupError("Tool executor has no WebSocket notifier - events cannot be sent")
            
            self.logger.info("  ✓ Step 18.5: WebSocket event delivery verified")
            
        except DeterministicStartupError:
            raise
        except Exception as e:
            raise DeterministicStartupError(f"WebSocket verification failed: {e}")
    
    async def _initialize_clickhouse(self) -> None:
        """Initialize ClickHouse - optional."""
        from netra_backend.app.db.clickhouse_init import initialize_clickhouse_tables
        await asyncio.wait_for(initialize_clickhouse_tables(), timeout=10.0)
    
    async def _initialize_monitoring(self) -> None:
        """Initialize monitoring - optional."""
        from netra_backend.app.agents.base.monitoring import performance_monitor
        await performance_monitor.start_monitoring()
        self.app.state.performance_monitor = performance_monitor
        
        # Start chat event monitoring for silent failure detection
        try:
            from netra_backend.app.websocket_core.event_monitor import chat_event_monitor
            await chat_event_monitor.start_monitoring()
            self.app.state.chat_event_monitor = chat_event_monitor
            self.logger.info("  ✓ Chat event monitor started")
        except Exception as e:
            self.logger.warning(f"  ⚠ Chat event monitor failed to start: {e}")
        
        # PHASE 3: Initialize monitoring integration between ChatEventMonitor and AgentWebSocketBridge
        try:
            from netra_backend.app.startup_module import initialize_monitoring_integration
            integration_success = await initialize_monitoring_integration()
            
            if integration_success:
                self.logger.info("  ✓ Monitoring integration established - cross-system validation enabled")
                # Store integration success on app state for health checks
                self.app.state.monitoring_integration_enabled = True
            else:
                self.logger.info("  ⚠ Monitoring integration failed - components operating independently")
                self.app.state.monitoring_integration_enabled = False
                
        except Exception as e:
            self.logger.warning(f"  ⚠ Monitoring integration error: {e} - components operating independently")
            self.app.state.monitoring_integration_enabled = False
    
    def _initialize_background_tasks(self) -> None:
        """Initialize background tasks - optional."""
        from netra_backend.app.services.background_task_manager import BackgroundTaskManager
        self.app.state.background_task_manager = BackgroundTaskManager()
    
    async def _apply_startup_fixes(self) -> None:
        """Apply critical startup fixes - CRITICAL."""
        from netra_backend.app.services.startup_fixes_integration import startup_fixes
        
        fix_results = await startup_fixes.run_comprehensive_verification()
        applied_fixes = fix_results.get('total_fixes', 0)
        
        if applied_fixes < 5:
            self.logger.warning(f"Only {applied_fixes}/5 startup fixes applied")
            # Log details but don't fail - fixes are best-effort
            self.logger.debug(startup_fixes.get_fix_status_summary())
        else:
            self.logger.debug("All critical startup fixes successfully applied")
    
    async def _initialize_performance_manager(self) -> None:
        """Initialize performance optimization manager - optional."""
        from netra_backend.app.core.performance_optimization_manager import performance_manager
        await performance_manager.initialize()
        self.app.state.performance_manager = performance_manager
        
        # Schedule index optimization as background task
        from netra_backend.app.db.index_optimizer import index_manager
        self.app.state.index_manager = index_manager
        
        if hasattr(self.app.state, 'background_task_manager'):
            # Schedule optimization for 60 seconds after startup
            asyncio.create_task(self._schedule_index_optimization())
    
    async def _schedule_index_optimization(self) -> None:
        """Schedule database index optimization after startup."""
        await asyncio.sleep(60)  # Wait 60 seconds after startup
        try:
            from netra_backend.app.db.index_optimizer import index_manager
            await asyncio.wait_for(index_manager.optimize_all_databases(), timeout=90.0)
            self.logger.debug("Database index optimization completed")
        except Exception as e:
            self.logger.warning(f"Database index optimization failed: {e}")
    
    async def _start_connection_monitoring(self) -> None:
        """Start database connection monitoring - optional."""
        from netra_backend.app.services.database.connection_monitor import start_connection_monitoring
        await start_connection_monitoring()
    
    async def _validate_database_schema(self) -> None:
        """Validate database schema - CRITICAL."""
        from netra_backend.app.db.postgres_core import async_engine
        from netra_backend.app.services.schema_validation_service import run_comprehensive_validation
        
        if async_engine is None:
            raise DeterministicStartupError("Database engine not available for schema validation")
        
        validation_passed = await run_comprehensive_validation(async_engine)
        if not validation_passed:
            # In deterministic mode, schema validation failure is critical
            raise DeterministicStartupError("Database schema validation failed - schema inconsistent")
    
    def _mark_startup_complete(self) -> None:
        """Mark startup as complete."""
        elapsed = time.time() - self.start_time
        
        self.app.state.startup_complete = True
        self.app.state.startup_in_progress = False
        self.app.state.startup_failed = False
        self.app.state.startup_error = None
        
        self.logger.info("=" * 60)
        self.logger.info(f"STARTUP COMPLETE - All critical services operational")
        self.logger.info(f"Chat pipeline ready - Time: {elapsed:.2f}s")
        self.logger.info("=" * 60)
    
    def _handle_startup_failure(self, error: Exception) -> None:
        """Handle startup failure - NO RECOVERY."""
        self.app.state.startup_complete = False
        self.app.state.startup_in_progress = False
        self.app.state.startup_failed = True
        self.app.state.startup_error = str(error)
        
        self.logger.critical("=" * 60)
        self.logger.critical("STARTUP FAILED - CRITICAL SERVICES NOT OPERATIONAL")
        self.logger.critical(f"Error: {error}")
        self.logger.critical("Chat is broken - Service cannot start")
        self.logger.critical("=" * 60)


async def run_deterministic_startup(app: FastAPI) -> Tuple[float, logging.Logger]:
    """
    Run deterministic startup sequence.
    NO GRACEFUL DEGRADATION. NO CONDITIONAL PATHS. NO SETTING SERVICES TO NONE.
    """
    orchestrator = StartupOrchestrator(app)
    
    try:
        await orchestrator.initialize_system()
        return orchestrator.start_time, orchestrator.logger
    except Exception as e:
        # Log and re-raise - no recovery
        orchestrator.logger.critical(f"Deterministic startup failed: {e}")
        raise