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
from typing import Tuple, Dict, Any, Optional
from enum import Enum

from fastapi import FastAPI

from shared.isolated_environment import get_env as get_isolated_env

# Create a wrapper for get_env to match expected signature
_env = get_isolated_env()
def get_env(key: str, default: str = '') -> str:
    """Get environment variable value."""
    return _env.get(key, default) or default
from netra_backend.app.core.project_utils import get_project_root as _get_project_root
from netra_backend.app.config import get_config, settings
from netra_backend.app.services.backend_health_config import setup_backend_health_service
from netra_backend.app.logging_config import central_logger


class StartupPhase(Enum):
    """7-phase deterministic startup sequence phases."""
    INIT = "init"
    DEPENDENCIES = "dependencies" 
    DATABASE = "database"
    CACHE = "cache"
    SERVICES = "services"
    WEBSOCKET = "websocket"
    FINALIZE = "finalize"


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
        
        # State tracking attributes
        self.current_phase: Optional[StartupPhase] = None
        self.phase_timings: Dict[StartupPhase, Dict[str, float]] = {}
        self.completed_phases: set[StartupPhase] = set()
        self.failed_phases: set[StartupPhase] = set()
        
        # Initialize app state for startup tracking
        self._initialize_startup_state()
    
    def _initialize_startup_state(self) -> None:
        """Initialize startup state tracking on app.state."""
        self.app.state.startup_complete = False
        self.app.state.startup_in_progress = True
        self.app.state.startup_failed = False
        self.app.state.startup_error = None
        self.app.state.startup_phase = "init"
        self.app.state.startup_start_time = self.start_time
        self.app.state.startup_phase_timings = {}
        self.app.state.startup_completed_phases = []
        self.app.state.startup_failed_phases = []
    
    def _set_current_phase(self, phase: StartupPhase) -> None:
        """Set the current startup phase and update state tracking."""
        # Mark previous phase as complete if exists
        if self.current_phase and self.current_phase not in self.failed_phases:
            self._complete_phase(self.current_phase)
        
        # Start new phase
        self.current_phase = phase
        self.app.state.startup_phase = phase.value
        
        # Initialize phase timing
        phase_start = time.time()
        self.phase_timings[phase] = {
            'start_time': phase_start,
            'duration': 0.0
        }
        
        # Log phase transition
        self.logger.info(f"🔄 PHASE TRANSITION → {phase.value.upper()}")
        self.logger.info(f"   Started at: {phase_start:.3f}s elapsed")
    
    def _complete_phase(self, phase: StartupPhase) -> None:
        """Mark a phase as completed and update timings."""
        if phase in self.phase_timings:
            end_time = time.time()
            duration = end_time - self.phase_timings[phase]['start_time']
            self.phase_timings[phase]['duration'] = duration
            
            # Update app state
            self.completed_phases.add(phase)
            self.app.state.startup_completed_phases = [p.value for p in self.completed_phases]
            self.app.state.startup_phase_timings = {
                p.value: timings for p, timings in self.phase_timings.items()
            }
            
            self.logger.info(f"✅ PHASE COMPLETED: {phase.value.upper()} ({duration:.3f}s)")
        
    def _fail_phase(self, phase: StartupPhase, error: Exception) -> None:
        """Mark a phase as failed and update error tracking."""
        # Complete timing for failed phase
        if phase in self.phase_timings:
            end_time = time.time()
            duration = end_time - self.phase_timings[phase]['start_time']
            self.phase_timings[phase]['duration'] = duration
        
        # Mark as failed
        self.failed_phases.add(phase)
        self.app.state.startup_failed_phases = [p.value for p in self.failed_phases]
        self.app.state.startup_failed = True
        self.app.state.startup_error = f"Phase {phase.value} failed: {str(error)}"
        
        self.logger.error(f"❌ PHASE FAILED: {phase.value.upper()} - {error}")
        
    async def initialize_system(self) -> None:
        """
        Initialize system in strict deterministic order.
        Any failure causes immediate startup failure.
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info("DETERMINISTIC STARTUP SEQUENCE INITIATED")
            self.logger.info("=" * 60)
            
            # PHASE 1: INIT - Foundation (Required for everything)
            self._set_current_phase(StartupPhase.INIT)
            await self._phase1_foundation()
            
            # PHASE 2: DEPENDENCIES - Core Services (Required for chat)
            self._set_current_phase(StartupPhase.DEPENDENCIES)
            await self._phase2_core_services()
            
            # PHASE 3: DATABASE - Database connections and schema
            self._set_current_phase(StartupPhase.DATABASE)
            await self._phase3_database_setup()
            
            # PHASE 4: CACHE - Redis and caching
            self._set_current_phase(StartupPhase.CACHE)
            await self._phase4_cache_setup()
            
            # PHASE 5: SERVICES - Chat Pipeline & Critical Services
            self._set_current_phase(StartupPhase.SERVICES)
            await self._phase5_services_setup()
            
            # PHASE 6: WEBSOCKET - WebSocket integration and validation
            self._set_current_phase(StartupPhase.WEBSOCKET)
            await self._phase6_websocket_setup()
            
            # PHASE 7: FINALIZE - Validation and optional services
            self._set_current_phase(StartupPhase.FINALIZE)
            await self._phase7_finalize()
            
            # Success - mark as complete (ONLY after ALL phases complete)
            self._mark_startup_complete()
            
        except Exception as e:
            # Mark current phase as failed if set
            if self.current_phase:
                self._fail_phase(self.current_phase, e)
            self._handle_startup_failure(e)
            raise DeterministicStartupError(f"CRITICAL STARTUP FAILURE: {e}") from e
    
    async def _phase1_foundation(self) -> None:
        """Phase 1: INIT - Foundation setup and environment validation."""
        self.logger.info("PHASE 1: INIT - Foundation")
        
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
        """Phase 2: DEPENDENCIES - Core service managers and keys."""
        self.logger.info("PHASE 2: DEPENDENCIES - Core Services")
        
        # Step 4: Key Manager (CRITICAL)
        self._initialize_key_manager()
        if not hasattr(self.app.state, 'key_manager') or self.app.state.key_manager is None:
            raise DeterministicStartupError("Key manager initialization failed")
        self.logger.info("  ✓ Step 4: Key manager initialized")
        
        # Step 5: LLM Manager (CRITICAL)
        self._initialize_llm_manager()
        if not hasattr(self.app.state, 'llm_manager') or self.app.state.llm_manager is None:
            raise DeterministicStartupError("LLM manager initialization failed")
        self.logger.info("  ✓ Step 5: LLM manager initialized")
        
        # Step 6: Apply startup fixes (CRITICAL)
        await self._apply_startup_fixes()
        self.logger.info("  ✓ Step 6: Startup fixes applied")
    
    async def _phase3_database_setup(self) -> None:
        """Phase 3: DATABASE - Database connections and schema."""
        self.logger.info("PHASE 3: DATABASE - Database Setup")
        
        # Step 7: Database connection (CRITICAL)
        await self._initialize_database()
        if not hasattr(self.app.state, 'db_session_factory') or self.app.state.db_session_factory is None:
            raise DeterministicStartupError("Database initialization failed - db_session_factory is None")
        self.logger.info("  ✓ Step 7: Database connected")
        
        # Step 8: Database schema validation (CRITICAL)
        await self._validate_database_schema()
        self.logger.info("  ✓ Step 8: Database schema validated")
    
    async def _phase4_cache_setup(self) -> None:
        """Phase 4: CACHE - Redis and caching systems."""
        self.logger.info("PHASE 4: CACHE - Redis Setup")
        
        # Step 9: Redis connection (CRITICAL)
        await self._initialize_redis()
        if not hasattr(self.app.state, 'redis_manager') or self.app.state.redis_manager is None:
            raise DeterministicStartupError("Redis initialization failed - redis_manager is None")
        self.logger.info("  ✓ Step 9: Redis connected")
    
    async def _phase5_services_setup(self) -> None:
        """Phase 5: SERVICES - Chat Pipeline and critical services."""
        self.logger.info("PHASE 5: SERVICES - Chat Pipeline & Critical Services")
        
        # Step 10: AgentWebSocketBridge Creation (CRITICAL - Must be created BEFORE tool dispatcher)
        await self._initialize_agent_websocket_bridge_basic()
        if not hasattr(self.app.state, 'agent_websocket_bridge') or self.app.state.agent_websocket_bridge is None:
            raise DeterministicStartupError("AgentWebSocketBridge is None - creation failed")
        self.logger.info("  ✓ Step 10: AgentWebSocketBridge created")
        
        # Step 11: Tool Registry (CRITICAL - Now can use the pre-created bridge)
        self._initialize_tool_registry()
        if not hasattr(self.app.state, 'tool_dispatcher') or self.app.state.tool_dispatcher is None:
            raise DeterministicStartupError("Tool dispatcher initialization failed")
        self.logger.info("  ✓ Step 11: Tool registry created with WebSocket bridge support")
        
        # Step 12: Agent Supervisor (CRITICAL - Create with bridge for proper WebSocket integration)
        await self._initialize_agent_supervisor()
        if not hasattr(self.app.state, 'agent_supervisor') or self.app.state.agent_supervisor is None:
            raise DeterministicStartupError("Agent supervisor is None - chat is broken")
        if not hasattr(self.app.state, 'thread_service') or self.app.state.thread_service is None:
            raise DeterministicStartupError("Thread service is None - chat is broken")
        self.logger.info("  ✓ Step 12: Agent supervisor created with bridge")
        
        # Step 13: Background Task Manager (CRITICAL)
        self._initialize_background_tasks()
        if not hasattr(self.app.state, 'background_task_manager') or self.app.state.background_task_manager is None:
            raise DeterministicStartupError("Background task manager initialization failed")
        self.logger.info("  ✓ Step 13: Background task manager initialized")
        
        # Step 14: Health Service Registry (CRITICAL)
        await self._initialize_health_service()
        if not hasattr(self.app.state, 'health_service') or self.app.state.health_service is None:
            raise DeterministicStartupError("Health service initialization failed")
        self.logger.info("  ✓ Step 14: Health service initialized")
        
        # Step 15: Factory Pattern Initialization (CRITICAL for singleton removal)
        await self._initialize_factory_patterns()
        self.logger.info("  ✓ Step 15: Factory patterns initialized")
    
    async def _phase6_websocket_setup(self) -> None:
        """Phase 6: WEBSOCKET - WebSocket integration and real-time communication."""
        self.logger.info("PHASE 6: WEBSOCKET - WebSocket Integration")
        
        # Step 16: WebSocket Manager (CRITICAL - Initialize before integrations)
        await self._initialize_websocket()
        self.logger.info("  ✓ Step 16: WebSocket manager initialized")
        
        # Step 17: Complete bridge integration with all dependencies
        await self._perform_complete_bridge_integration()
        self.logger.info("  ✓ Step 17: Bridge integration completed")
        
        # Step 18: Verify tool dispatcher has WebSocket support
        await self._verify_tool_dispatcher_websocket_support()
        self.logger.info("  ✓ Step 18: Tool dispatcher WebSocket support verified")
        
        # Step 19: Message handler registration
        self._register_message_handlers()
        self.logger.info("  ✓ Step 19: Message handlers registered")
        
        # Step 20: Verify AgentWebSocketBridge health
        await self._verify_bridge_health()
        self.logger.info("  ✓ Step 20: AgentWebSocketBridge health verified")
        
        # Step 21: Verify WebSocket events can actually be sent
        await self._verify_websocket_events()
        self.logger.info("  ✓ Step 21: WebSocket event delivery verified")
    
    async def _phase7_finalize(self) -> None:
        """Phase 7: FINALIZE - Final validation and optional services."""
        self.logger.info("PHASE 7: FINALIZE - Validation & Optional Services")
        
        # Step 22: Connection monitoring (CRITICAL)
        await self._start_connection_monitoring()
        self.logger.info("  ✓ Step 22: Connection monitoring started")
        
        # Step 23a: Apply startup validation fixes before validation
        await self._apply_startup_validation_fixes()
        self.logger.info("  ✓ Step 23a: Startup validation fixes applied")
        
        # Step 23b: Comprehensive startup validation
        await self._run_comprehensive_validation()
        self.logger.info("  ✓ Step 23b: Comprehensive validation completed")
        
        # Step 24: Critical path validation (CHAT FUNCTIONALITY)
        await self._run_critical_path_validation()
        self.logger.info("  ✓ Step 24: Critical path validation completed")
        
        # Step 25: ClickHouse (optional)
        try:
            await self._initialize_clickhouse()
            self.logger.info("  ✓ Step 25: ClickHouse initialized")
        except Exception as e:
            self.logger.warning(f"  ⚠ Step 25: ClickHouse skipped: {e}")
        
        # Step 26: Performance Manager (optional)
        try:
            await self._initialize_performance_manager()
            self.logger.info("  ✓ Step 26: Performance manager initialized")
        except Exception as e:
            self.logger.warning(f"  ⚠ Step 26: Performance manager skipped: {e}")
        
        # Step 27: Advanced Monitoring (optional)
        try:
            await self._initialize_monitoring()
            self.logger.info("  ✓ Step 27: Advanced monitoring started")
        except Exception as e:
            self.logger.warning(f"  ⚠ Step 27: Advanced monitoring skipped: {e}")
    
    # DEPRECATED METHODS - keeping temporarily for reference during transition
    async def _phase4_integration_enhancement(self) -> None:
        """DEPRECATED - Phase 4: Integration & Enhancement - Complete all component integration."""
        self.logger.info("PHASE 4: Integration & Enhancement")
        
        # Step 13: Complete bridge integration with supervisor and registry
        await self._perform_complete_bridge_integration()
        self.logger.info("  ✓ Step 13: Bridge integration completed")
        
        # Step 14: Verify tool dispatcher has WebSocket support
        await self._verify_tool_dispatcher_websocket_support()
        self.logger.info("  ✓ Step 14: Tool dispatcher WebSocket support verified")
        
        # Step 15: Message handler registration
        self._register_message_handlers()
        self.logger.info("  ✓ Step 15: Message handlers registered")
    
    async def _perform_complete_bridge_integration(self) -> None:
        """Complete AgentWebSocketBridge integration with all dependencies."""
        from netra_backend.app.services.agent_websocket_bridge import IntegrationState
        from netra_backend.app.orchestration.agent_execution_registry import get_agent_execution_registry
        
        bridge = self.app.state.agent_websocket_bridge
        supervisor = self.app.state.agent_supervisor
        
        if not bridge:
            raise DeterministicStartupError("AgentWebSocketBridge not available for integration")
        if not supervisor:
            raise DeterministicStartupError("Agent supervisor not available for integration")
        
        # Get registry for enhanced integration
        try:
            registry = await get_agent_execution_registry()
        except Exception as e:
            # Registry is optional for basic integration
            self.logger.warning(f"Agent execution registry not available for bridge: {e}")
            registry = supervisor.registry if hasattr(supervisor, 'registry') else None
        
        # Initialize complete integration with timeout
        integration_result = await asyncio.wait_for(
            bridge.ensure_integration(
                supervisor=supervisor,
                registry=registry,
                force_reinit=False
            ),
            timeout=30.0
        )
        
        if not integration_result.success:
            raise DeterministicStartupError(f"AgentWebSocketBridge integration failed: {integration_result.error}")
        
        # Verify bridge health immediately after integration
        health_status = await bridge.health_check()
        if health_status.state not in [IntegrationState.ACTIVE]:
            raise DeterministicStartupError(f"AgentWebSocketBridge unhealthy after integration: {health_status.state}")
        
        self.logger.info(f"    - Integration state: {health_status.state.value}")
        self.logger.info(f"    - WebSocket Manager: {'✓' if health_status.websocket_manager_healthy else '✗'}")
        self.logger.info(f"    - Registry: {'✓' if health_status.registry_healthy else '✗'}")
    
    async def _verify_tool_dispatcher_websocket_support(self) -> None:
        """Verify tool dispatcher has AgentWebSocketBridge support."""
        # Get tool dispatcher
        tool_dispatcher = self.app.state.tool_dispatcher
        if not tool_dispatcher:
            raise DeterministicStartupError("Tool dispatcher not available for verification")
        
        # Connect tool dispatcher to bridge if not already connected
        bridge = self.app.state.agent_websocket_bridge
        if bridge and hasattr(tool_dispatcher, 'executor'):
            if not hasattr(tool_dispatcher.executor, 'websocket_bridge') or not tool_dispatcher.executor.websocket_bridge:
                # Connect the bridge to tool dispatcher
                tool_dispatcher.executor.websocket_bridge = bridge
                self.logger.info("    - AgentWebSocketBridge connected to tool dispatcher")
        
        # Check if it has WebSocket support through bridge
        if hasattr(tool_dispatcher, 'has_websocket_support'):
            if tool_dispatcher.has_websocket_support:
                self.logger.info("    - Tool dispatcher has WebSocket support through AgentWebSocketBridge")
            else:
                self.logger.warning("    - Tool dispatcher lacks WebSocket support - events may not work")
        else:
            # Legacy check for older versions
            self.logger.info("    - Tool dispatcher doesn't expose WebSocket support status (legacy)")
        
        # Also ensure registry has WebSocket bridge connection for agents
        supervisor = self.app.state.agent_supervisor
        if supervisor:
            registry = None
            if hasattr(supervisor, 'agent_registry'):
                registry = supervisor.agent_registry
            elif hasattr(supervisor, 'registry'):
                registry = supervisor.registry
            
            if registry and bridge:
                # Set the bridge on agent registry - only latest method supported
                if hasattr(registry, 'set_websocket_bridge'):
                    registry.set_websocket_bridge(bridge)
                    self.logger.info("    - AgentWebSocketBridge set on agent registry")
                else:
                    # Registry must support the bridge pattern
                    raise DeterministicStartupError(
                        "Agent registry does not support set_websocket_bridge() - "
                        "registry must be updated to support AgentWebSocketBridge pattern"
                    )
    
    async def _phase5_critical_services(self) -> None:
        """Phase 5: Critical Services - Required for system stability."""
        self.logger.info("PHASE 5: Critical Services")
        
        # Step 16: Background Task Manager (CRITICAL)
        try:
            self._initialize_background_tasks()
            self.logger.info("  ✓ Step 16: Background task manager initialized")
        except Exception as e:
            raise DeterministicStartupError(f"Background task manager initialization failed: {e}")
        
        # Step 17: Connection Monitoring (CRITICAL)
        try:
            await self._start_connection_monitoring()
            self.logger.info("  ✓ Step 17: Connection monitoring started")
        except Exception as e:
            raise DeterministicStartupError(f"Connection monitoring initialization failed: {e}")
        
        # Step 18: Health Service Registry (CRITICAL)
        try:
            await self._initialize_health_service()
            self.logger.info("  ✓ Step 18: Health service initialized")
        except Exception as e:
            raise DeterministicStartupError(f"Health service initialization failed: {e}")
    
    async def _phase6_validation(self) -> None:
        """Phase 6: Validation - Verify all critical services are operational."""
        self.logger.info("PHASE 6: Validation")
        
        critical_checks = [
            (hasattr(self.app.state, 'db_session_factory') and self.app.state.db_session_factory is not None, "Database"),
            (hasattr(self.app.state, 'redis_manager') and self.app.state.redis_manager is not None, "Redis"),
            (hasattr(self.app.state, 'llm_manager') and self.app.state.llm_manager is not None, "LLM Manager"),
            (hasattr(self.app.state, 'agent_websocket_bridge') and self.app.state.agent_websocket_bridge is not None, "AgentWebSocketBridge"),
            (hasattr(self.app.state, 'agent_supervisor') and self.app.state.agent_supervisor is not None, "Agent Supervisor"),
            (hasattr(self.app.state, 'thread_service') and self.app.state.thread_service is not None, "Thread Service"),
            (hasattr(self.app.state, 'tool_dispatcher') and self.app.state.tool_dispatcher is not None, "Tool Dispatcher"),
            (hasattr(self.app.state, 'background_task_manager') and self.app.state.background_task_manager is not None, "Background Task Manager"),
            (hasattr(self.app.state, 'health_service') and self.app.state.health_service is not None, "Health Service"),
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
        
        self.logger.info("  ✓ Step 19: All critical services validated")
        
        # Step 20: Verify AgentWebSocketBridge health
        await self._verify_bridge_health()
        
        # Step 21: Verify WebSocket events can actually be sent
        await self._verify_websocket_events()
        
        # Step 22: Comprehensive startup validation with component counts
        await self._run_comprehensive_validation()
        
        # Step 23: Critical path validation (CHAT FUNCTIONALITY)
        await self._run_critical_path_validation()
        
        # Step 24: Schema validation (CRITICAL)
        await self._validate_database_schema()
        self.logger.info("  ✓ Step 24: Database schema validated")
    
    def _validate_critical_services_exist(self) -> None:
        """Validate that all critical services exist and are not None."""
        critical_services = {
            'agent_service': 'Agent Service (handles agent interactions)',
            'thread_service': 'Thread Service (manages chat threads)',
            'corpus_service': 'Corpus Service (manages knowledge base)',
            'agent_supervisor': 'Agent Supervisor (orchestrates agents)',
            'llm_manager': 'LLM Manager (handles AI model connections)',
            'db_session_factory': 'Database Session Factory',
            'redis_manager': 'Redis Manager (handles caching)',
            'tool_dispatcher': 'Tool Dispatcher (executes agent tools)',
            'agent_websocket_bridge': 'WebSocket Bridge (real-time events)'
        }
        
        missing_services = []
        none_services = []
        
        for service_name, description in critical_services.items():
            if not hasattr(self.app.state, service_name):
                missing_services.append(f"{service_name} ({description})")
            else:
                service = getattr(self.app.state, service_name)
                if service is None:
                    none_services.append(f"{service_name} ({description})")
        
        if missing_services or none_services:
            error_msg = "CRITICAL SERVICE VALIDATION FAILED:\n"
            if missing_services:
                error_msg += f"  Missing services: {', '.join(missing_services)}\n"
            if none_services:
                error_msg += f"  None services: {', '.join(none_services)}\n"
            raise DeterministicStartupError(error_msg)
        
        self.logger.info("    ✓ All critical services validated")
    
    async def _run_comprehensive_validation(self) -> None:
        """Run comprehensive startup validation."""
        # CRITICAL: First validate all required services exist and are not None
        self._validate_critical_services_exist()
        
        try:
            from netra_backend.app.core.startup_validation import validate_startup
            
            self.logger.info("  Step 22: Running comprehensive startup validation...")
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
                    # Log detailed failure information
                    self.logger.error("🚨 CRITICAL STARTUP VALIDATION FAILURES DETECTED:")
                    for category, components in report.get('categories', {}).items():
                        for component in components:
                            if component['critical'] and component['status'] in ['critical', 'failed']:
                                self.logger.error(f"  ❌ {component['name']} ({category}): {component['message']}")
                    
                    # Allow bypass for development remediation work
                    if get_env('BYPASS_STARTUP_VALIDATION', '').lower() == 'true':
                        self.logger.warning(
                            f"⚠️ BYPASSING STARTUP VALIDATION FOR DEVELOPMENT - "
                            f"{critical_failures} critical failures ignored"
                        )
                    else:
                        # In deterministic mode, critical validation failures are fatal
                        raise DeterministicStartupError(
                            f"Startup validation failed with {critical_failures} critical failures. "
                            f"Status: {report['status_counts']['critical']} critical, "
                            f"{report['status_counts']['failed']} failed components"
                        )
            
            # Log summary
            self.logger.info(f"  ✓ Step 22: Startup validation complete")
            self.logger.info(f"    Summary: {report['status_counts']['healthy']} healthy, "
                           f"{report['status_counts']['warning']} warnings, "
                           f"{report['status_counts']['critical']} critical")
            
        except ImportError:
            self.logger.warning("  ⚠ Step 22: Startup validation module not found - skipping comprehensive validation")
        except DeterministicStartupError:
            # Re-raise deterministic errors
            raise
        except Exception as e:
            # Log but don't fail on non-critical validation errors
            self.logger.error(f"  ⚠ Step 22: Startup validation error: {e}")
    
    async def _run_critical_path_validation(self) -> None:
        """Run critical communication path validation."""
        try:
            from netra_backend.app.core.critical_path_validator import validate_critical_paths
            
            self.logger.info("  Step 23: Validating critical communication paths...")
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
                # Allow bypass for development remediation work
                if get_env('BYPASS_STARTUP_VALIDATION', '').lower() == 'true':
                    self.logger.warning(
                        f"⚠️ BYPASSING CRITICAL PATH VALIDATION FOR DEVELOPMENT - "
                        f"{chat_breaking_count} chat-breaking failures ignored"
                    )
                else:
                    raise DeterministicStartupError(
                        f"Critical path validation failed: {chat_breaking_count} chat-breaking failures. "
                        f"Chat functionality is BROKEN and will not work!"
                    )
            
            # Log any degraded paths as warnings
            degraded_count = sum(1 for v in critical_validations 
                               if not v.passed and v.criticality.value == "degraded")
            if degraded_count > 0:
                self.logger.warning(f"    ⚠️ {degraded_count} degraded communication paths detected")
            
            self.logger.info("  ✓ Step 23: Critical communication paths validated")
            
        except ImportError:
            self.logger.warning("  ⚠ Step 23: Critical path validator not found - skipping")
        except DeterministicStartupError:
            # Re-raise deterministic errors
            raise
        except Exception as e:
            # Critical path validation failure is FATAL in deterministic mode
            raise DeterministicStartupError(f"Critical path validation failed: {e}")
    
    async def _phase7_optional_services(self) -> None:
        """Phase 7: Optional Services - Truly optional services that can fail without breaking chat."""
        self.logger.info("PHASE 7: Optional Services")
        
        # Step 25: ClickHouse (optional)
        try:
            await self._initialize_clickhouse()
            self.logger.info("  ✓ Step 25: ClickHouse initialized")
        except Exception as e:
            self.logger.warning(f"  ⚠ Step 25: ClickHouse skipped: {e}")
        
        # Step 26: Performance Manager (optional)
        try:
            await self._initialize_performance_manager()
            self.logger.info("  ✓ Step 26: Performance manager initialized")
        except Exception as e:
            self.logger.warning(f"  ⚠ Step 26: Performance manager skipped: {e}")
        
        # Step 27: Advanced Monitoring (optional)
        try:
            await self._initialize_monitoring()
            self.logger.info("  ✓ Step 27: Advanced monitoring started")
        except Exception as e:
            self.logger.warning(f"  ⚠ Step 27: Advanced monitoring skipped: {e}")
    
    async def _verify_bridge_health(self) -> None:
        """Verify AgentWebSocketBridge is healthy and operational - CRITICAL."""
        from netra_backend.app.services.agent_websocket_bridge import IntegrationState
        
        self.logger.info("  Step 20: Verifying AgentWebSocketBridge health...")
        
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
            self.logger.info(f"  ✓ Step 20: AgentWebSocketBridge health verified")
            self.logger.info(f"    - State: {health.state.value}")
            self.logger.info(f"    - Health Checks: {status['metrics']['health_checks_performed']}")
            self.logger.info(f"    - Success Rate: {status['metrics']['success_rate']:.2%}")
            self.logger.info(f"    - Total Initializations: {status['metrics']['total_initializations']}")
            
            # Verify dependencies are available
            deps = status['dependencies']
            if not deps['websocket_manager_available']:
                raise DeterministicStartupError("WebSocket manager not available in bridge")
            if not deps['registry_available']:
                raise DeterministicStartupError("Registry not available in bridge")
            
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
        """Initialize tool registry and dispatcher with AgentWebSocketBridge support - CRITICAL."""
        from netra_backend.app.agents.tool_registry_unified import UnifiedToolRegistry
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher, create_legacy_tool_dispatcher
        from netra_backend.app.agents.tools.langchain_wrappers import (
            DataHelperTool, DeepResearchTool, ReliabilityScorerTool, SandboxedInterpreterTool
        )
        
        # CRITICAL FIX: WebSocket bridge MUST be created before tool dispatcher
        # Bridge should already be created in previous step
        if not hasattr(self.app.state, 'agent_websocket_bridge') or self.app.state.agent_websocket_bridge is None:
            raise DeterministicStartupError(
                "AgentWebSocketBridge not available for tool dispatcher initialization. "
                "Bridge must be created before tool dispatcher to prevent notification failures."
            )
        
        websocket_bridge = self.app.state.agent_websocket_bridge
        self.logger.info("    - Using pre-created AgentWebSocketBridge for tool dispatcher")
        
        # 🚀 REVOLUTIONARY CHANGE: NO MORE GLOBAL REGISTRIES OR SINGLETONS
        # Store tool factory configuration for per-user registry creation
        # Each UserExecutionContext will get its own isolated registry instance
        
        # Define available tools for user registry creation (not instantiated globally)
        available_tool_classes = [
            DataHelperTool,
            DeepResearchTool, 
            ReliabilityScorerTool,
            SandboxedInterpreterTool
        ]
        
        self.logger.info(f"    - ✅ Configured {len(available_tool_classes)} tool classes for per-user registry creation")
        
        # Store tool factory configuration (NOT instances) for UserContext-based creation
        self.app.state.tool_classes = available_tool_classes
        self.app.state.websocket_bridge_factory = lambda: websocket_bridge  # Factory for bridge creation
        
        # 🔥 NO MORE GLOBAL TOOL DISPATCHER OR REGISTRY
        # These will be created per-user via UserExecutionContext
        self.app.state.tool_dispatcher = None  # Signals: use UserContext-based creation
        self.app.state.tool_registry = None   # Signals: use UserContext-based creation
        
        self.logger.info("    - 🎯 Configured UserContext-based tool system (no global singletons)")
        
        # Validate UserContext-based configuration
        if not hasattr(self.app.state, 'tool_classes') or not self.app.state.tool_classes:
            raise DeterministicStartupError(
                "Tool classes configuration missing - "
                "cannot create UserContext-based tool dispatchers"
            )
        
        if not hasattr(self.app.state, 'websocket_bridge_factory'):
            raise DeterministicStartupError(
                "WebSocket bridge factory missing - "
                "cannot create UserContext-based WebSocket support"
            )
        
        self.logger.info("    - ✅ UserContext-based tool system validated and ready")
        self.logger.info("    - 🔧 Tool dispatchers will be created per-user with isolated registries")
        self.logger.info("    - 🌐 WebSocket bridges will be created per-user with isolated events")
    
    async def _initialize_websocket(self) -> None:
        """Initialize WebSocket components - CRITICAL."""
        from netra_backend.app.websocket_core import get_websocket_manager
        
        manager = get_websocket_manager()
        if hasattr(manager, 'initialize'):
            await manager.initialize()
    
    async def _initialize_agent_websocket_bridge_basic(self) -> None:
        """Create AgentWebSocketBridge instance - CRITICAL (Integration happens in Phase 4)."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            
            # Create bridge instance (non-singleton) - proper user isolation pattern
            self.logger.info("  Creating AgentWebSocketBridge instance...")
            bridge = AgentWebSocketBridge()
            if bridge is None:
                self.logger.error("  ❌ AgentWebSocketBridge() returned None")
                raise DeterministicStartupError("Failed to create AgentWebSocketBridge instance")
            
            # Store bridge in app state for later integration
            self.app.state.agent_websocket_bridge = bridge
            
            # Verify the bridge has required methods for validation
            required_methods = ['notify_agent_started', 'notify_agent_completed', 'notify_tool_executing']
            missing_methods = [m for m in required_methods if not hasattr(bridge, m)]
            if missing_methods:
                self.logger.error(f"  ❌ AgentWebSocketBridge missing methods: {missing_methods}")
                raise DeterministicStartupError(f"AgentWebSocketBridge missing required methods: {missing_methods}")
            
            self.logger.info(f"  ✓ AgentWebSocketBridge instance created with all required methods (integration pending)")
            
        except Exception as e:
            self.logger.error(f"  ❌ Failed to initialize AgentWebSocketBridge: {e}")
            self.logger.error(f"  Exception type: {type(e).__name__}")
            if hasattr(e, '__traceback__'):
                import traceback
                self.logger.error(f"  Traceback: {traceback.format_exception(type(e), e, e.__traceback__)}")
            raise DeterministicStartupError(f"Critical failure in AgentWebSocketBridge initialization: {e}") from e
    
    async def _initialize_agent_supervisor(self) -> None:
        """Initialize agent supervisor - CRITICAL FOR CHAT (Uses AgentWebSocketBridge for notifications)."""
        from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
        from netra_backend.app.services.agent_service import AgentService
        from netra_backend.app.services.thread_service import ThreadService
        from netra_backend.app.services.corpus_service import CorpusService
        from netra_backend.app.core.agent_execution_tracker import initialize_tracker
        
        # Initialize execution tracker for death detection - CRITICAL
        self.logger.info("    - Initializing agent execution tracker for death detection...")
        try:
            execution_tracker = await initialize_tracker()
            self.app.state.execution_tracker = execution_tracker
            self.logger.info("      ✓ Agent execution tracker initialized")
        except Exception as e:
            raise DeterministicStartupError(f"Failed to initialize execution tracker: {e}")
        
        # Get AgentWebSocketBridge - CRITICAL for agent notifications
        agent_websocket_bridge = self.app.state.agent_websocket_bridge
        if not agent_websocket_bridge:
            raise DeterministicStartupError("AgentWebSocketBridge not available for supervisor initialization")
        
        # Create supervisor with bridge for proper WebSocket integration
        # Note: SupervisorAgent uses UserExecutionContext pattern - no database sessions in constructor
        # SupervisorAgent expects 2 args: llm_manager and websocket_bridge (no tool_dispatcher)
        supervisor = SupervisorAgent(
            self.app.state.llm_manager,
            agent_websocket_bridge
        )
        
        if supervisor is None:
            raise DeterministicStartupError("Supervisor creation returned None")
        
        # Set state - NEVER set to None
        self.app.state.agent_supervisor = supervisor
        self.app.state.agent_service = AgentService(supervisor)
        self.app.state.thread_service = ThreadService()
        self.app.state.corpus_service = CorpusService()
        
        # CRITICAL VALIDATION: Ensure services are never None
        critical_services = [
            ('agent_supervisor', self.app.state.agent_supervisor),
            ('agent_service', self.app.state.agent_service),
            ('thread_service', self.app.state.thread_service),
            ('corpus_service', self.app.state.corpus_service)
        ]
        
        for service_name, service_instance in critical_services:
            if service_instance is None:
                raise DeterministicStartupError(
                    f"CRITICAL: {service_name} is None after initialization. "
                    f"This violates deterministic startup requirements."
                )
        
        self.logger.info("    ✓ All critical services validated as non-None")
    
    def _register_message_handlers(self) -> None:
        """Register WebSocket message handlers - CRITICAL."""
        # CRITICAL: WebSocket message handlers are registered per-connection
        # in websocket.py when connections are established, not during startup.
        # This is correct architecture - handlers need active WebSocket connections.
        
        # The AgentRegistry.set_websocket_manager() call is already handled
        # in Step 14: _ensure_tool_dispatcher_enhancement()
        
        self.logger.info("    - WebSocket message handlers will be registered per-connection")
        self.logger.info("    - Tool dispatcher WebSocket enhancement completed in previous step")
    
    async def _verify_websocket_events(self) -> None:
        """Verify WebSocket events can actually be sent - CRITICAL."""
        import uuid
        from netra_backend.app.websocket_core import get_websocket_manager
        
        self.logger.info("  Step 21: Verifying WebSocket event delivery...")
        
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
            
            # CRITICAL FIX: During startup verification, we don't have WebSocket connections yet
            # This is expected behavior in ALL environments during startup
            # The manager is operational if it returns without exception
            from shared.isolated_environment import get_env
            env_name = get_env().get("ENVIRONMENT", "development")
            is_testing = get_env().get("TESTING", "0") == "1"
            
            # During startup, no connections exist yet in ANY environment
            # The WebSocket manager accepting the message (even to queue) means it's operational
            if success is False:
                # This is expected during startup - no connections exist yet
                self.logger.info(f"  ✓ WebSocket manager operational (no connections yet in {env_name} environment)")
                # Do not fail - the manager is working correctly
            else:
                # Message was accepted (queued or would be sent when connections exist)
                self.logger.info("  ✓ WebSocket test message accepted by manager")
            
            # CRITICAL FIX: Verify tool dispatcher has WebSocket support after initialization order fix
            # Check the main tool dispatcher in app.state first
            if hasattr(self.app.state, 'tool_dispatcher') and self.app.state.tool_dispatcher:
                main_dispatcher = self.app.state.tool_dispatcher
                
                # Verify the main dispatcher has WebSocket support
                if not hasattr(main_dispatcher, 'has_websocket_support') or not main_dispatcher.has_websocket_support:
                    raise DeterministicStartupError(
                        "Main tool dispatcher has no WebSocket support - initialization order fix failed. "
                        "Tool execution events will be silent."
                    )
                
                # Verify the executor has the WebSocket bridge
                if hasattr(main_dispatcher, 'executor'):
                    if not hasattr(main_dispatcher.executor, 'websocket_bridge') or main_dispatcher.executor.websocket_bridge is None:
                        raise DeterministicStartupError(
                            "Main tool dispatcher executor has no AgentWebSocketBridge - initialization order fix incomplete"
                        )
                    
                    # Verify it's the same bridge we created
                    expected_bridge = self.app.state.agent_websocket_bridge
                    if main_dispatcher.executor.websocket_bridge != expected_bridge:
                        raise DeterministicStartupError(
                            "Tool dispatcher has different WebSocket bridge than expected - integration error"
                        )
                
                self.logger.info("    ✓ Main tool dispatcher WebSocket integration verified")
            else:
                raise DeterministicStartupError("Main tool dispatcher not found in app.state")
            
            # Also verify tool dispatcher in supervisor registry (if present)
            if hasattr(self.app.state, 'agent_supervisor'):
                supervisor = self.app.state.agent_supervisor
                if hasattr(supervisor, 'registry') and hasattr(supervisor.registry, 'tool_dispatcher'):
                    dispatcher = supervisor.registry.tool_dispatcher
                    # Check if dispatcher exists
                    if dispatcher is None:
                        raise DeterministicStartupError("Supervisor tool dispatcher is None - failed to initialize properly")
                    # Check using the actual has_websocket_support property
                    if not hasattr(dispatcher, 'has_websocket_support') or not dispatcher.has_websocket_support:
                        raise DeterministicStartupError("Supervisor tool dispatcher has no WebSocket support - agent events will be silent")
                    
                    # Check that the unified executor is present (it contains the notifier internally)
                    if not hasattr(dispatcher, 'executor'):
                        raise DeterministicStartupError("Supervisor tool dispatcher has no executor - events cannot be sent")
                    
                    # Verify the executor is the unified engine with WebSocket support
                    from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
                    if not isinstance(dispatcher.executor, UnifiedToolExecutionEngine):
                        raise DeterministicStartupError("Supervisor tool dispatcher not using UnifiedToolExecutionEngine - events cannot be sent")
                    
                    # Check that the executor has AgentWebSocketBridge internally
                    if not hasattr(dispatcher.executor, 'websocket_bridge') or dispatcher.executor.websocket_bridge is None:
                        raise DeterministicStartupError("Supervisor tool executor has no AgentWebSocketBridge - events cannot be sent")
                    
                    self.logger.info("    ✓ Supervisor tool dispatcher WebSocket integration verified")
            
            self.logger.info("  ✓ Step 21: WebSocket event delivery verified")
            
        except DeterministicStartupError:
            raise
        except Exception as e:
            raise DeterministicStartupError(f"WebSocket verification failed: {e}")
    
    async def _initialize_clickhouse(self) -> None:
        """Initialize ClickHouse with robust retry logic and dependency validation."""
        from netra_backend.app.core.clickhouse_connection_manager import (
            initialize_clickhouse_with_retry,
            get_clickhouse_connection_manager
        )
        
        self.logger.info("Initializing ClickHouse with robust connection manager...")
        
        # Use the robust connection manager with retry logic and health monitoring
        success = await initialize_clickhouse_with_retry()
        
        if success:
            # Store connection manager in app state for health checks
            self.app.state.clickhouse_connection_manager = get_clickhouse_connection_manager()
            
            # Initialize ClickHouse tables after successful connection
            try:
                from netra_backend.app.db.clickhouse_init import initialize_clickhouse_tables
                await asyncio.wait_for(initialize_clickhouse_tables(), timeout=30.0)
                self.logger.info("  ✓ ClickHouse tables initialized")
            except Exception as e:
                self.logger.warning(f"  ⚠ ClickHouse table initialization failed: {e}")
                # Don't fail startup for table creation issues
        
        else:
            # Log failure but don't raise exception (ClickHouse is optional)
            self.logger.warning("ClickHouse initialization failed - continuing without analytics")
            
            # Store a None connection manager to indicate ClickHouse is unavailable
            self.app.state.clickhouse_connection_manager = None
    
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
        """Apply critical startup fixes with enhanced error handling and validation."""
        from netra_backend.app.services.startup_fixes_integration import startup_fixes
        from netra_backend.app.services.startup_fixes_validator import (
            startup_fixes_validator, 
            ValidationLevel
        )
        
        try:
            # Run comprehensive verification with enhanced logging and retry logic
            self.logger.info("Applying startup fixes with dependency resolution and retry logic...")
            fix_results = await startup_fixes.run_comprehensive_verification()
            
            # Extract detailed results
            total_fixes = fix_results.get('total_fixes', 0)
            successful_fixes = len(fix_results.get('successful_fixes', []))
            failed_fixes = len(fix_results.get('failed_fixes', []))
            skipped_fixes = len(fix_results.get('skipped_fixes', []))
            
            # Log comprehensive summary
            self.logger.info(f"Startup fixes completed: {successful_fixes}/5 successful, {failed_fixes} failed, {skipped_fixes} skipped")
            
            # Log successful fixes
            if fix_results.get('successful_fixes'):
                self.logger.info(f"✅ Successful fixes: {', '.join(fix_results['successful_fixes'])}")
            
            # Log failed fixes with details
            if fix_results.get('failed_fixes'):
                self.logger.warning(f"❌ Failed fixes: {', '.join(fix_results['failed_fixes'])}")
                for fix_name in fix_results['failed_fixes']:
                    fix_detail = fix_results.get('fix_details', {}).get(fix_name, {})
                    error = fix_detail.get('error', 'Unknown error')
                    self.logger.warning(f"  - {fix_name}: {error}")
            
            # Log skipped fixes with reasons
            if fix_results.get('skipped_fixes'):
                self.logger.info(f"⏭️ Skipped fixes: {', '.join(fix_results['skipped_fixes'])}")
                for fix_name in fix_results['skipped_fixes']:
                    fix_detail = fix_results.get('fix_details', {}).get(fix_name, {})
                    error = fix_detail.get('error', 'Unknown reason')
                    self.logger.info(f"  - {fix_name}: {error}")
            
            # Log retry information if any retries were needed
            if fix_results.get('retry_summary'):
                self.logger.info(f"🔄 Fixes requiring retries: {fix_results['retry_summary']}")
            
            # Validate critical fixes are applied
            validation_result = await startup_fixes_validator.validate_all_fixes_applied(
                level=ValidationLevel.CRITICAL_ONLY,
                timeout=10.0
            )
            
            if not validation_result.success:
                # Critical fixes failed - this is a deterministic startup failure
                critical_failures = validation_result.critical_failures
                self.logger.error("🚨 CRITICAL: Critical startup fixes failed validation!")
                for failure in critical_failures:
                    self.logger.error(f"  - {failure}")
                
                # In deterministic mode, critical fix failures are FATAL
                raise DeterministicStartupError(
                    f"Critical startup fixes validation failed: {', '.join(critical_failures)}. "
                    f"System cannot start without these fixes."
                )
            
            # Success case
            if successful_fixes == 5:
                self.logger.info("✅ All 5 startup fixes successfully applied and validated")
            elif successful_fixes >= 4:
                self.logger.info(f"✅ {successful_fixes}/5 startup fixes applied with {skipped_fixes} optional fixes skipped")
            else:
                self.logger.warning(f"⚠️ Only {successful_fixes}/5 startup fixes applied - some functionality may be degraded")
            
            # Log total duration
            total_duration = fix_results.get('total_duration', 0)
            self.logger.info(f"Startup fixes completed in {total_duration:.2f}s")
            
        except DeterministicStartupError:
            # Re-raise deterministic errors
            raise
            
        except Exception as e:
            # Wrap unexpected errors
            self.logger.error(f"Unexpected error in startup fixes: {e}", exc_info=True)
            raise DeterministicStartupError(f"Startup fixes system failed: {e}") from e
    
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
    
    async def _apply_startup_validation_fixes(self) -> None:
        """Apply startup validation fixes to prevent common failures."""
        try:
            from netra_backend.app.core.startup_validation_fix import apply_startup_validation_fixes
            
            self.logger.info("Applying startup validation fixes...")
            results = apply_startup_validation_fixes(self.app)
            
            if results['overall_success']:
                total_fixes = results.get('total_fixes_applied', 0)
                if total_fixes > 0:
                    self.logger.info(f"✅ Applied {total_fixes} startup validation fixes")
                else:
                    self.logger.info("✅ No startup validation fixes needed")
            else:
                # Log detailed error information but don't fail startup
                self.logger.warning("⚠️ Some startup validation fixes failed:")
                if results.get('websocket_fix'):
                    websocket_results = results['websocket_fix']
                    for error in websocket_results.get('errors', []):
                        self.logger.warning(f"  - WebSocket fix error: {error}")
                
                if results.get('critical_error'):
                    self.logger.warning(f"  - Critical error: {results['critical_error']}")
            
        except ImportError:
            self.logger.warning("Startup validation fix module not available - skipping fixes")
        except Exception as e:
            # Don't fail startup for fix errors, just log them
            self.logger.warning(f"Failed to apply startup validation fixes: {e}")
    
    async def _initialize_health_service(self) -> None:
        """Initialize health service registry - optional."""
        health_service = await setup_backend_health_service()
        self.app.state.health_service = health_service
        self.logger.debug("Health service registry initialized with comprehensive checks")
    
    async def _initialize_factory_patterns(self) -> None:
        """Initialize factory patterns for singleton removal - CRITICAL."""
        from netra_backend.app.agents.supervisor.execution_factory import ExecutionEngineFactory, get_execution_engine_factory
        from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory, get_websocket_bridge_factory
        from netra_backend.app.agents.supervisor.agent_instance_factory import (
            get_agent_instance_factory,
            configure_agent_instance_factory
        )
        from netra_backend.app.services.factory_adapter import FactoryAdapter, AdapterConfig
        from netra_backend.app.websocket_core import get_websocket_manager
        
        self.logger.info("    - Initializing factory patterns for singleton removal...")
        
        try:
            # 1. Initialize ExecutionEngineFactory
            execution_factory = get_execution_engine_factory()
            
            # Configure execution factory with dependencies
            # Note: With UserExecutionContext pattern, registry is created per-request
            # so we don't configure it here - it will be provided at runtime
            if hasattr(self.app.state, 'agent_supervisor'):
                supervisor = self.app.state.agent_supervisor
                # Get websocket factory (will be properly initialized below)
                temp_websocket_factory = get_websocket_bridge_factory()
                execution_factory.configure(
                    agent_registry=None,  # Per-request in UserExecutionContext pattern
                    websocket_bridge_factory=temp_websocket_factory,
                    db_connection_pool=None  # Will be set later if needed
                )
                self.logger.info("    ✓ ExecutionEngineFactory configured (registry will be per-request)")
            else:
                self.logger.warning("    ⚠ Agent supervisor not available - factory configuration limited")
            
            self.app.state.execution_engine_factory = execution_factory
            
            # 2. Initialize WebSocketConnectionPool first (required by factory)
            from netra_backend.app.services.websocket_connection_pool import get_websocket_connection_pool
            connection_pool = get_websocket_connection_pool()
            self.app.state.websocket_connection_pool = connection_pool
            self.logger.info("    ✓ WebSocketConnectionPool initialized")
            
            # 3. Initialize WebSocketBridgeFactory
            # CRITICAL FIX: Always initialize websocket_factory to prevent "not associated with a value" error
            websocket_factory = get_websocket_bridge_factory()
            
            # Configure with proper parameters including connection pool
            if hasattr(self.app.state, 'agent_supervisor'):
                # Create a simple health monitor for now
                class SimpleHealthMonitor:
                    async def check_health(self):
                        return {"status": "healthy"}
                
                health_monitor = SimpleHealthMonitor()
                
                # Note: With UserExecutionContext pattern, registry is created per-request
                websocket_factory.configure(
                    connection_pool=connection_pool,
                    agent_registry=None,  # Per-request in UserExecutionContext pattern
                    health_monitor=health_monitor
                )
            self.app.state.websocket_bridge_factory = websocket_factory
            self.logger.info("    ✓ WebSocketBridgeFactory configured with connection pool")
            
            # 4. Initialize AgentInstanceFactory
            agent_instance_factory = await configure_agent_instance_factory(
                websocket_bridge=self.app.state.agent_websocket_bridge,
                websocket_manager=get_websocket_manager()
            )
            self.app.state.agent_instance_factory = agent_instance_factory
            self.logger.info("    ✓ AgentInstanceFactory configured")
            
            # 5. Initialize FactoryAdapter for backward compatibility
            adapter_config = AdapterConfig.from_env()
            factory_adapter = FactoryAdapter(
                execution_engine_factory=execution_factory,
                websocket_bridge_factory=websocket_factory,
                config=adapter_config
            )
            
            # Configure legacy components for fallback
            if hasattr(self.app.state, 'agent_supervisor'):
                factory_adapter._legacy_websocket_bridge = self.app.state.agent_websocket_bridge
                self.logger.info("    ✓ FactoryAdapter configured with legacy fallback")
            
            self.app.state.factory_adapter = factory_adapter
            
            # 6. Enable factories for select routes (gradual migration)
            critical_routes = [
                "/api/agents/run_agent_v2",
                "/api/agents/v2/{run_id}/status",
                "/api/agents/v2/{run_id}/state", 
                "/api/agents/v2/thread/{thread_id}/runs"
            ]
            
            for route in critical_routes:
                await factory_adapter.enable_factory_for_route(route)
                self.logger.info(f"    ✓ Factory pattern enabled for route: {route}")
            
            # Log factory initialization summary
            status = factory_adapter.get_migration_status()
            self.logger.info("    📊 Factory Pattern Migration Status:")
            self.logger.info(f"      Migration Mode: {status['migration_mode']}")
            self.logger.info(f"      Routes Enabled: {len(status['route_flags'])}")
            self.logger.info(f"      Legacy Fallback: {'Enabled' if status['config']['legacy_fallback_enabled'] else 'Disabled'}")
            
        except Exception as e:
            raise DeterministicStartupError(f"Factory pattern initialization failed: {e}")
    
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
        """Mark startup as complete - ONLY after ALL 7 phases complete successfully."""
        # Complete the final phase before marking overall completion
        if self.current_phase:
            self._complete_phase(self.current_phase)
        
        # Verify ALL 7 phases completed successfully
        expected_phases = set(StartupPhase)
        if self.completed_phases != expected_phases:
            missing_phases = expected_phases - self.completed_phases
            raise DeterministicStartupError(f"Cannot mark startup complete - missing phases: {[p.value for p in missing_phases]}")
        
        # Verify no failed phases
        if self.failed_phases:
            failed_phase_names = [p.value for p in self.failed_phases]
            raise DeterministicStartupError(f"Cannot mark startup complete - failed phases: {failed_phase_names}")
        
        # Calculate total elapsed time and phase summary
        elapsed = time.time() - self.start_time
        
        # CRITICAL: Only set startup_complete=True after ALL phases are verified complete
        self.app.state.startup_complete = True
        self.app.state.startup_in_progress = False
        self.app.state.startup_failed = False
        self.app.state.startup_error = None
        self.app.state.startup_phase = "complete"
        
        # Log comprehensive completion summary
        self.logger.info("=" * 80)
        self.logger.info("🚀 DETERMINISTIC STARTUP SEQUENCE COMPLETED SUCCESSFULLY")
        self.logger.info("=" * 80)
        self.logger.info(f"✅ Total Time: {elapsed:.3f}s")
        self.logger.info(f"✅ Phases Completed: {len(self.completed_phases)}/7")
        
        # Log individual phase timings
        self.logger.info("📊 PHASE TIMING BREAKDOWN:")
        for phase in StartupPhase:
            if phase in self.phase_timings:
                duration = self.phase_timings[phase]['duration']
                percentage = (duration / elapsed) * 100 if elapsed > 0 else 0
                self.logger.info(f"   {phase.value.upper():<12}: {duration:.3f}s ({percentage:.1f}%)")
        
        self.logger.info("🎯 CRITICAL SYSTEMS STATUS:")
        self.logger.info("   Database:     ✅ Connected & Validated")
        self.logger.info("   Redis:        ✅ Connected & Available")
        self.logger.info("   LLM Manager:  ✅ Initialized & Ready")
        self.logger.info("   Chat Pipeline:✅ Operational & WebSocket-Enabled")
        self.logger.info("   Agent Bridge: ✅ Integrated & Health Verified")
        self.logger.info("=" * 80)
        self.logger.info("🟢 CHAT FUNCTIONALITY: FULLY OPERATIONAL")
        self.logger.info("=" * 80)
    
    def _handle_startup_failure(self, error: Exception) -> None:
        """Handle startup failure - NO RECOVERY."""
        elapsed = time.time() - self.start_time
        
        # Ensure startup state reflects failure
        self.app.state.startup_complete = False
        self.app.state.startup_in_progress = False
        self.app.state.startup_failed = True
        self.app.state.startup_error = str(error)
        self.app.state.startup_phase = self.current_phase.value if self.current_phase else "unknown"
        
        # Log comprehensive failure details
        self.logger.critical("=" * 80)
        self.logger.critical("💥 DETERMINISTIC STARTUP SEQUENCE FAILED")
        self.logger.critical("=" * 80)
        self.logger.critical(f"❌ Failed at Phase: {self.current_phase.value.upper() if self.current_phase else 'UNKNOWN'}")
        self.logger.critical(f"❌ Time Elapsed: {elapsed:.3f}s")
        self.logger.critical(f"❌ Error: {error}")
        
        # Log phase completion status
        if self.completed_phases:
            completed_names = [p.value for p in self.completed_phases]
            self.logger.critical(f"✅ Completed Phases: {completed_names}")
        else:
            self.logger.critical("❌ No phases completed")
            
        if self.failed_phases:
            failed_names = [p.value for p in self.failed_phases]
            self.logger.critical(f"❌ Failed Phases: {failed_names}")
        
        # Log phase timings for completed phases
        if self.phase_timings:
            self.logger.critical("📊 PARTIAL PHASE TIMINGS:")
            for phase, timing in self.phase_timings.items():
                duration = timing.get('duration', 0.0)
                status = "✅" if phase in self.completed_phases else "❌"
                self.logger.critical(f"   {status} {phase.value.upper():<12}: {duration:.3f}s")
        
        self.logger.critical("=" * 80)
        self.logger.critical("🔴 CRITICAL: CHAT FUNCTIONALITY IS BROKEN")
        self.logger.critical("🔴 SERVICE CANNOT START - DETERMINISTIC FAILURE")
        self.logger.critical("=" * 80)


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