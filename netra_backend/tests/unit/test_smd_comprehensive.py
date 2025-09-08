"""
Comprehensive Unit Tests for Startup Module Deterministic (smd.py)

Business Value Justification:
- Revenue Impact: Protects $500K+ ARR by ensuring deterministic startup sequence
- Business Segment: Platform/Internal - Critical Infrastructure Stability
- Value Impact: Prevents catastrophic startup failures that would block chat (90% of business value)
- Strategic Impact: Ensures multi-user system can scale reliably without ambiguous failures

CRITICAL: This file tests the MOST IMPORTANT startup module in the system.
If chat cannot work, the service MUST NOT start - this is core business logic.

Test Coverage Categories:
1. Deterministic startup sequences (7 phases)
2. Critical service failure handling (NO graceful degradation)
3. Chat infrastructure validation (90% of business value protection)
4. Environment configuration and isolation
5. Error handling and fail-fast behavior
6. Service dependency management
7. Health checks and readiness probes
8. Performance and timing requirements
9. Concurrent startup scenarios
10. WebSocket bridge integration requirements
"""

import asyncio
import logging
import time
import unittest
from enum import Enum
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import pytest
from fastapi import FastAPI

from test_framework.ssot.base import BaseTestCase
from netra_backend.app.smd import (
    StartupPhase,
    DeterministicStartupError,
    StartupOrchestrator,
    run_deterministic_startup,
    get_env
)


class TestStartupPhaseEnum(BaseTestCase):
    """
    Test StartupPhase enum for deterministic startup sequence.
    
    BVJ: Platform/Internal - Ensures startup phases are correctly defined
    and ordered for deterministic system initialization.
    """

    def test_startup_phase_enum_values(self):
        """Test that all required startup phases are defined."""
        expected_phases = {
            "init",
            "dependencies",
            "database", 
            "cache",
            "services",
            "websocket",
            "finalize"
        }
        
        actual_phases = {phase.value for phase in StartupPhase}
        
        self.assertEqual(expected_phases, actual_phases)
        self.assertEqual(len(StartupPhase), 7)
    
    def test_startup_phase_ordering_deterministic(self):
        """Test that phases maintain deterministic ordering."""
        phases = list(StartupPhase)
        
        # Verify exact order for deterministic startup
        expected_order = [
            StartupPhase.INIT,
            StartupPhase.DEPENDENCIES,
            StartupPhase.DATABASE,
            StartupPhase.CACHE,
            StartupPhase.SERVICES,
            StartupPhase.WEBSOCKET,
            StartupPhase.FINALIZE
        ]
        
        self.assertEqual(phases, expected_order)
    
    def test_startup_phase_string_representation(self):
        """Test phase string values for logging consistency."""
        self.assertEqual(StartupPhase.INIT.value, "init")
        self.assertEqual(StartupPhase.DEPENDENCIES.value, "dependencies")
        self.assertEqual(StartupPhase.DATABASE.value, "database")
        self.assertEqual(StartupPhase.CACHE.value, "cache")
        self.assertEqual(StartupPhase.SERVICES.value, "services")
        self.assertEqual(StartupPhase.WEBSOCKET.value, "websocket")
        self.assertEqual(StartupPhase.FINALIZE.value, "finalize")


class TestDeterministicStartupError(BaseTestCase):
    """
    Test DeterministicStartupError exception handling.
    
    BVJ: Platform/Internal - Ensures proper error handling for critical
    startup failures that must terminate service startup immediately.
    """

    def test_deterministic_startup_error_creation(self):
        """Test creating DeterministicStartupError with message."""
        error_message = "Critical service failed during startup"
        error = DeterministicStartupError(error_message)
        
        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), error_message)
    
    def test_deterministic_startup_error_inheritance(self):
        """Test that DeterministicStartupError properly inherits from Exception."""
        error = DeterministicStartupError("Test error")
        
        self.assertIsInstance(error, Exception)
        self.assertTrue(issubclass(DeterministicStartupError, Exception))
    
    def test_deterministic_startup_error_with_cause(self):
        """Test error chaining for root cause analysis."""
        original_error = ValueError("Database connection failed")
        try:
            raise DeterministicStartupError("Startup failed") from original_error
        except DeterministicStartupError as startup_error:
            self.assertEqual(startup_error.__cause__, original_error)
            self.assertIsInstance(startup_error.__cause__, ValueError)


class TestStartupOrchestratorInitialization(BaseTestCase):
    """
    Test StartupOrchestrator initialization and state management.
    
    BVJ: Platform/Internal - Ensures startup orchestrator properly initializes
    and tracks state for all critical system components.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.app = FastAPI()
        # CRITICAL: Do not mock the orchestrator - test real initialization
    
    def test_startup_orchestrator_initialization(self):
        """Test orchestrator initializes with proper state tracking."""
        orchestrator = StartupOrchestrator(self.app)
        
        # Verify basic attributes
        self.assertIsInstance(orchestrator.app, FastAPI)
        self.assertIsNotNone(orchestrator.logger)
        self.assertIsInstance(orchestrator.start_time, float)
        
        # Verify state tracking initialization
        self.assertIsNone(orchestrator.current_phase)
        self.assertEqual(orchestrator.phase_timings, {})
        self.assertEqual(orchestrator.completed_phases, set())
        self.assertEqual(orchestrator.failed_phases, set())
    
    def test_startup_state_initialization_on_app(self):
        """Test that app.state is properly initialized for startup tracking."""
        orchestrator = StartupOrchestrator(self.app)
        
        # Verify app state attributes
        self.assertFalse(self.app.state.startup_complete)
        self.assertTrue(self.app.state.startup_in_progress)
        self.assertFalse(self.app.state.startup_failed)
        self.assertIsNone(self.app.state.startup_error)
        self.assertEqual(self.app.state.startup_phase, "init")
        self.assertIsInstance(self.app.state.startup_start_time, float)
        self.assertEqual(self.app.state.startup_phase_timings, {})
        self.assertEqual(self.app.state.startup_completed_phases, [])
        self.assertEqual(self.app.state.startup_failed_phases, [])
    
    def test_startup_orchestrator_logger_configuration(self):
        """Test that logger is properly configured."""
        orchestrator = StartupOrchestrator(self.app)
        
        self.assertIsNotNone(orchestrator.logger)
        # Logger should be configured by central_logger system (may be loguru or logging)
        self.assertTrue(hasattr(orchestrator.logger, 'info'))
        self.assertTrue(hasattr(orchestrator.logger, 'error'))
        self.assertTrue(hasattr(orchestrator.logger, 'critical') or hasattr(orchestrator.logger, 'critical'))


class TestPhaseTransitionAndTiming(BaseTestCase):
    """
    Test phase transition logic and timing validation.
    
    BVJ: Platform/Internal - Ensures deterministic phase transitions
    with accurate timing for startup performance monitoring.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.app = FastAPI()
        self.orchestrator = StartupOrchestrator(self.app)
    
    def test_set_current_phase_first_time(self):
        """Test setting current phase for the first time."""
        start_time = time.time()
        
        self.orchestrator._set_current_phase(StartupPhase.INIT)
        
        # Verify phase transition
        self.assertEqual(self.orchestrator.current_phase, StartupPhase.INIT)
        self.assertEqual(self.app.state.startup_phase, "init")
        
        # Verify timing initialization
        self.assertIn(StartupPhase.INIT, self.orchestrator.phase_timings)
        phase_timing = self.orchestrator.phase_timings[StartupPhase.INIT]
        self.assertIn('start_time', phase_timing)
        self.assertIn('duration', phase_timing)
        self.assertEqual(phase_timing['duration'], 0.0)
        self.assertGreaterEqual(phase_timing['start_time'], start_time)
    
    def test_set_current_phase_transition(self):
        """Test transitioning from one phase to another."""
        # Start with INIT phase
        self.orchestrator._set_current_phase(StartupPhase.INIT)
        
        # Small delay to ensure different timing
        time.sleep(0.01)
        
        # Transition to DEPENDENCIES phase
        self.orchestrator._set_current_phase(StartupPhase.DEPENDENCIES)
        
        # Verify INIT phase was completed
        self.assertIn(StartupPhase.INIT, self.orchestrator.completed_phases)
        self.assertIn(StartupPhase.INIT, self.app.state.startup_completed_phases)
        
        # Verify INIT phase has duration > 0
        init_duration = self.orchestrator.phase_timings[StartupPhase.INIT]['duration']
        self.assertGreater(init_duration, 0.0)
        
        # Verify DEPENDENCIES phase is current
        self.assertEqual(self.orchestrator.current_phase, StartupPhase.DEPENDENCIES)
        self.assertEqual(self.app.state.startup_phase, "dependencies")
    
    def test_complete_phase_timing_calculation(self):
        """Test that phase completion calculates timing correctly."""
        self.orchestrator._set_current_phase(StartupPhase.INIT)
        start_time = self.orchestrator.phase_timings[StartupPhase.INIT]['start_time']
        
        # Small delay
        time.sleep(0.01)
        
        self.orchestrator._complete_phase(StartupPhase.INIT)
        
        # Verify completion state
        self.assertIn(StartupPhase.INIT, self.orchestrator.completed_phases)
        
        # Verify timing calculation
        phase_timing = self.orchestrator.phase_timings[StartupPhase.INIT]
        self.assertGreater(phase_timing['duration'], 0.0)
        
        # Verify app state update
        self.assertIn("init", self.app.state.startup_completed_phases)
        self.assertIn("init", self.app.state.startup_phase_timings)
    
    def test_fail_phase_error_tracking(self):
        """Test phase failure tracking and error recording."""
        self.orchestrator._set_current_phase(StartupPhase.DATABASE)
        test_error = Exception("Database connection failed")
        
        self.orchestrator._fail_phase(StartupPhase.DATABASE, test_error)
        
        # Verify failure tracking
        self.assertIn(StartupPhase.DATABASE, self.orchestrator.failed_phases)
        self.assertIn("database", self.app.state.startup_failed_phases)
        self.assertTrue(self.app.state.startup_failed)
        self.assertEqual(self.app.state.startup_error, "Phase database failed: Database connection failed")
        
        # Verify timing is still calculated for failed phase
        self.assertGreater(self.orchestrator.phase_timings[StartupPhase.DATABASE]['duration'], 0.0)


class TestCriticalServiceValidation(BaseTestCase):
    """
    Test critical service validation logic.
    
    BVJ: Platform/Internal - Ensures all critical services required for
    chat functionality (90% of business value) are properly validated.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.app = FastAPI()
        self.orchestrator = StartupOrchestrator(self.app)
    
    def test_validate_critical_services_exist_success(self):
        """Test successful validation when all critical services exist."""
        # Set up all required services on app.state
        self.app.state.agent_service = Mock()
        self.app.state.thread_service = Mock()
        self.app.state.corpus_service = Mock()
        self.app.state.agent_supervisor = Mock()
        self.app.state.llm_manager = Mock()
        self.app.state.db_session_factory = Mock()
        self.app.state.redis_manager = Mock()
        self.app.state.agent_websocket_bridge = Mock()
        
        # UserContext-based configurations
        self.app.state.tool_classes = [Mock, Mock]
        self.app.state.websocket_bridge_factory = Mock()
        self.app.state.execution_engine_factory = Mock()
        self.app.state.websocket_connection_pool = Mock()
        
        # Should not raise exception
        self.orchestrator._validate_critical_services_exist()
    
    def test_validate_critical_services_missing_service_fails(self):
        """Test that missing critical service causes validation failure."""
        # Set up all services except one critical one
        self.app.state.agent_service = Mock()
        self.app.state.thread_service = Mock()
        self.app.state.corpus_service = Mock()
        self.app.state.agent_supervisor = Mock()
        self.app.state.llm_manager = Mock()
        self.app.state.db_session_factory = Mock()
        self.app.state.redis_manager = Mock()
        # MISSING: agent_websocket_bridge
        
        self.app.state.tool_classes = [Mock, Mock]
        
        # Should raise DeterministicStartupError
        with self.assertRaises(DeterministicStartupError) as context:
            self.orchestrator._validate_critical_services_exist()
        
        self.assertIn("CRITICAL SERVICE VALIDATION FAILED", str(context.exception))
        self.assertIn("agent_websocket_bridge", str(context.exception))
    
    def test_validate_critical_services_none_service_fails(self):
        """Test that None service causes validation failure."""
        # Set up services but make one None
        self.app.state.agent_service = Mock()
        self.app.state.thread_service = Mock()
        self.app.state.corpus_service = Mock()
        self.app.state.agent_supervisor = Mock()
        self.app.state.llm_manager = None  # CRITICAL: This should fail
        self.app.state.db_session_factory = Mock()
        self.app.state.redis_manager = Mock()
        self.app.state.agent_websocket_bridge = Mock()
        
        self.app.state.tool_classes = [Mock, Mock]
        
        # Should raise DeterministicStartupError
        with self.assertRaises(DeterministicStartupError) as context:
            self.orchestrator._validate_critical_services_exist()
        
        self.assertIn("CRITICAL SERVICE VALIDATION FAILED", str(context.exception))
        self.assertIn("llm_manager", str(context.exception))
    
    def test_validate_critical_services_missing_usercontext_config_fails(self):
        """Test that missing UserContext configuration fails validation."""
        # Set up all standard services
        self.app.state.agent_service = Mock()
        self.app.state.thread_service = Mock()
        self.app.state.corpus_service = Mock()
        self.app.state.agent_supervisor = Mock()
        self.app.state.llm_manager = Mock()
        self.app.state.db_session_factory = Mock()
        self.app.state.redis_manager = Mock()
        self.app.state.agent_websocket_bridge = Mock()
        
        # MISSING: tool_classes (critical for UserContext pattern)
        
        # Should raise DeterministicStartupError
        with self.assertRaises(DeterministicStartupError) as context:
            self.orchestrator._validate_critical_services_exist()
        
        self.assertIn("CRITICAL SERVICE VALIDATION FAILED", str(context.exception))
        self.assertIn("tool_classes", str(context.exception))


class TestDeterministicFailureScenarios(BaseTestCase):
    """
    Test deterministic failure scenarios with NO fallbacks or graceful degradation.
    
    BVJ: Platform/Internal - Critical test ensuring system fails fast and hard
    when any critical component fails, preventing silent failures.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.app = FastAPI()
        self.orchestrator = StartupOrchestrator(self.app)
    
    @patch('netra_backend.app.smd.central_logger')
    def test_database_initialization_failure_is_fatal(self, mock_logger):
        """Test that database initialization failure causes fatal startup failure."""
        mock_logger.get_logger.return_value = Mock()
        
        # Mock database initialization to fail
        with patch('netra_backend.app.smd.initialize_postgres', side_effect=Exception("Database connection failed")):
            with patch('asyncio.wait_for', side_effect=Exception("Database connection failed")):
                
                # Database failure should be fatal
                with self.assertRaises(DeterministicStartupError) as context:
                    asyncio.run(self.orchestrator._initialize_database())
                
                self.assertIn("Database initialization failed", str(context.exception))
                self.assertIn("Database connection failed", str(context.exception))
    
    @patch('netra_backend.app.smd.central_logger')
    def test_redis_initialization_failure_is_fatal(self, mock_logger):
        """Test that Redis initialization failure causes fatal startup failure."""
        mock_logger.get_logger.return_value = Mock()
        
        # Mock Redis manager to fail
        mock_redis_manager = Mock()
        mock_redis_manager.initialize = AsyncMock(side_effect=Exception("Redis connection failed"))
        
        with patch('netra_backend.app.smd.redis_manager', mock_redis_manager):
            # Redis failure should be fatal
            with self.assertRaises(Exception) as context:
                asyncio.run(self.orchestrator._initialize_redis())
            
            self.assertIn("Redis connection failed", str(context.exception))
    
    def test_key_manager_failure_is_fatal(self):
        """Test that key manager initialization failure causes fatal startup failure."""
        with patch('netra_backend.app.smd.KeyManager') as mock_key_manager_class:
            mock_key_manager_class.load_from_settings.return_value = None
            
            # Key manager failure should be fatal
            with self.assertRaises(DeterministicStartupError) as context:
                self.orchestrator._initialize_key_manager()
            
            self.assertIn("Key manager initialization failed", str(context.exception))
    
    def test_llm_manager_none_is_fatal(self):
        """Test that LLM manager being None causes fatal validation failure."""
        # Set up partial services
        self.app.state.agent_service = Mock()
        self.app.state.thread_service = Mock()
        self.app.state.corpus_service = Mock()
        self.app.state.agent_supervisor = Mock()
        self.app.state.llm_manager = None  # This should cause failure
        self.app.state.db_session_factory = Mock()
        self.app.state.redis_manager = Mock()
        self.app.state.agent_websocket_bridge = Mock()
        self.app.state.tool_classes = [Mock]
        
        # Should raise DeterministicStartupError - NO graceful degradation
        with self.assertRaises(DeterministicStartupError):
            self.orchestrator._validate_critical_services_exist()
    
    async def test_websocket_bridge_integration_failure_is_fatal(self):
        """Test that WebSocket bridge integration failure is fatal."""
        # Set up mock bridge that fails integration
        mock_bridge = Mock()
        mock_bridge.ensure_integration = AsyncMock(return_value=Mock(success=False, error="Integration failed"))
        
        self.app.state.agent_websocket_bridge = mock_bridge
        self.app.state.agent_supervisor = Mock()
        
        # Integration failure should be fatal
        with self.assertRaises(DeterministicStartupError) as context:
            await self.orchestrator._perform_complete_bridge_integration()
        
        self.assertIn("AgentWebSocketBridge integration failed", str(context.exception))
        self.assertIn("Integration failed", str(context.exception))


class TestChatInfrastructureProtection(BaseTestCase):
    """
    Test chat infrastructure protection (90% of business value).
    
    BVJ: Revenue Protection - Chat delivers 90% of business value.
    If chat infrastructure is broken, the service MUST NOT start.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.app = FastAPI()
        self.orchestrator = StartupOrchestrator(self.app)
    
    def test_agent_supervisor_none_prevents_startup(self):
        """Test that agent supervisor being None prevents startup (chat broken)."""
        # Simulate agent supervisor failing to initialize
        self.app.state.agent_supervisor = None
        self.app.state.thread_service = Mock()
        self.app.state.agent_websocket_bridge = Mock()
        
        # Should raise DeterministicStartupError
        with self.assertRaises(DeterministicStartupError) as context:
            self.orchestrator._validate_critical_services_exist()
        
        self.assertIn("agent_supervisor", str(context.exception))
        self.assertIn("CRITICAL SERVICE VALIDATION FAILED", str(context.exception))
    
    def test_thread_service_none_prevents_startup(self):
        """Test that thread service being None prevents startup (chat broken)."""
        # Simulate thread service failing to initialize
        self.app.state.agent_supervisor = Mock()
        self.app.state.thread_service = None  # Chat is broken
        self.app.state.agent_websocket_bridge = Mock()
        
        # Should raise DeterministicStartupError
        with self.assertRaises(DeterministicStartupError):
            self.orchestrator._validate_critical_services_exist()
    
    def test_websocket_bridge_none_prevents_startup(self):
        """Test that WebSocket bridge being None prevents startup (real-time chat broken)."""
        # Simulate WebSocket bridge failing to initialize
        self.app.state.agent_supervisor = Mock()
        self.app.state.thread_service = Mock()
        self.app.state.agent_websocket_bridge = None  # Real-time chat is broken
        
        # Should raise DeterministicStartupError
        with self.assertRaises(DeterministicStartupError):
            self.orchestrator._validate_critical_services_exist()
    
    async def test_critical_path_validation_chat_breaking_failure_is_fatal(self):
        """Test that chat-breaking critical path failures prevent startup."""
        # Mock critical path validator to return chat-breaking failure
        mock_validation = Mock()
        mock_validation.passed = False
        mock_validation.criticality = Mock()
        mock_validation.criticality.value = "chat_breaking"
        mock_validation.component = "Agent-WebSocket Integration"
        mock_validation.failure_reason = "WebSocket events not being sent"
        mock_validation.remediation = "Fix agent notification system"
        
        with patch('netra_backend.app.smd.validate_critical_paths') as mock_validate:
            mock_validate.return_value = (False, [mock_validation])
            
            # Chat-breaking failure should be fatal
            with self.assertRaises(DeterministicStartupError) as context:
                await self.orchestrator._run_critical_path_validation()
            
            self.assertIn("chat-breaking failures", str(context.exception))
            self.assertIn("Chat functionality is BROKEN", str(context.exception))


class TestWebSocketBridgeIntegration(BaseTestCase):
    """
    Test WebSocket bridge integration requirements for real-time agent events.
    
    BVJ: Revenue Protection - WebSocket events enable real-time agent communication
    which is critical for user experience and retention.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.app = FastAPI()
        self.orchestrator = StartupOrchestrator(self.app)
    
    async def test_websocket_bridge_health_verification_success(self):
        """Test successful WebSocket bridge health verification."""
        # Mock healthy bridge
        mock_bridge = Mock()
        mock_status = {
            'metrics': {
                'health_checks_performed': 10,
                'success_rate': 0.95,
                'total_initializations': 1
            },
            'dependencies': {}
        }
        mock_health = Mock()
        mock_health.state = Mock()
        mock_health.state.value = "ACTIVE"
        mock_health.websocket_manager_healthy = True
        mock_health.registry_healthy = True
        mock_health.consecutive_failures = 0
        
        # Mock the enum comparison
        with patch('netra_backend.app.smd.IntegrationState') as mock_integration_state:
            mock_integration_state.ACTIVE = Mock()
            mock_health.state = mock_integration_state.ACTIVE
            
            mock_bridge.get_status = AsyncMock(return_value=mock_status)
            mock_bridge.health_check = AsyncMock(return_value=mock_health)
            
            self.app.state.agent_websocket_bridge = mock_bridge
            
            # Should not raise exception
            await self.orchestrator._verify_bridge_health()
    
    async def test_websocket_bridge_unhealthy_state_is_fatal(self):
        """Test that unhealthy bridge state causes startup failure."""
        # Mock unhealthy bridge
        mock_bridge = Mock()
        mock_health = Mock()
        mock_health.state = Mock()
        mock_health.state.value = "FAILED"
        mock_health.websocket_manager_healthy = False
        mock_health.registry_healthy = False
        mock_health.consecutive_failures = 5
        
        # Mock the enum to simulate non-ACTIVE state
        with patch('netra_backend.app.smd.IntegrationState') as mock_integration_state:
            mock_integration_state.ACTIVE = Mock()
            # Make the state comparison fail
            mock_bridge.health_check = AsyncMock(return_value=mock_health)
            
            self.app.state.agent_websocket_bridge = mock_bridge
            
            # Should raise DeterministicStartupError
            with self.assertRaises(DeterministicStartupError) as context:
                await self.orchestrator._verify_bridge_health()
            
            self.assertIn("AgentWebSocketBridge not active", str(context.exception))
    
    async def test_websocket_bridge_none_prevents_health_verification(self):
        """Test that missing bridge prevents health verification."""
        self.app.state.agent_websocket_bridge = None
        
        # Should raise DeterministicStartupError
        with self.assertRaises(DeterministicStartupError) as context:
            await self.orchestrator._verify_bridge_health()
        
        self.assertIn("AgentWebSocketBridge is None", str(context.exception))
    
    async def test_websocket_bridge_initialization_creates_instance(self):
        """Test that WebSocket bridge initialization creates proper instance."""
        with patch('netra_backend.app.smd.AgentWebSocketBridge') as mock_bridge_class:
            mock_instance = Mock()
            # Mock required methods
            mock_instance.notify_agent_started = Mock()
            mock_instance.notify_agent_completed = Mock()
            mock_instance.notify_tool_executing = Mock()
            mock_bridge_class.return_value = mock_instance
            
            await self.orchestrator._initialize_agent_websocket_bridge_basic()
            
            # Verify bridge was created and stored
            self.assertEqual(self.app.state.agent_websocket_bridge, mock_instance)
            mock_bridge_class.assert_called_once()
    
    async def test_websocket_bridge_missing_methods_is_fatal(self):
        """Test that bridge missing required methods causes fatal error."""
        with patch('netra_backend.app.smd.AgentWebSocketBridge') as mock_bridge_class:
            mock_instance = Mock()
            # Missing required methods
            del mock_instance.notify_agent_started
            mock_bridge_class.return_value = mock_instance
            
            # Should raise DeterministicStartupError
            with self.assertRaises(DeterministicStartupError) as context:
                await self.orchestrator._initialize_agent_websocket_bridge_basic()
            
            self.assertIn("missing required methods", str(context.exception))
            self.assertIn("notify_agent_started", str(context.exception))


class TestPerformanceAndTimingRequirements(BaseTestCase):
    """
    Test performance requirements and timeout scenarios.
    
    BVJ: Platform/Internal - Ensures startup performance meets requirements
    and fails fast on timeout scenarios to prevent resource exhaustion.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.app = FastAPI()
        self.orchestrator = StartupOrchestrator(self.app)
    
    def test_startup_timing_measurement_accuracy(self):
        """Test that startup timing measurements are accurate."""
        start_time = time.time()
        self.orchestrator._set_current_phase(StartupPhase.INIT)
        
        # Small controlled delay
        time.sleep(0.05)  # 50ms
        
        self.orchestrator._complete_phase(StartupPhase.INIT)
        
        # Verify timing accuracy (within reasonable tolerance)
        measured_duration = self.orchestrator.phase_timings[StartupPhase.INIT]['duration']
        self.assertGreaterEqual(measured_duration, 0.04)  # At least 40ms
        self.assertLessEqual(measured_duration, 0.1)     # No more than 100ms
    
    def test_phase_timing_persists_through_transitions(self):
        """Test that phase timings are preserved through phase transitions."""
        # Complete multiple phases
        self.orchestrator._set_current_phase(StartupPhase.INIT)
        time.sleep(0.01)
        
        self.orchestrator._set_current_phase(StartupPhase.DEPENDENCIES)
        time.sleep(0.01)
        
        self.orchestrator._set_current_phase(StartupPhase.DATABASE)
        
        # Verify all timings are preserved
        self.assertIn(StartupPhase.INIT, self.orchestrator.phase_timings)
        self.assertIn(StartupPhase.DEPENDENCIES, self.orchestrator.phase_timings)
        self.assertIn(StartupPhase.DATABASE, self.orchestrator.phase_timings)
        
        # Verify completed phases have non-zero duration
        self.assertGreater(self.orchestrator.phase_timings[StartupPhase.INIT]['duration'], 0)
        self.assertGreater(self.orchestrator.phase_timings[StartupPhase.DEPENDENCIES]['duration'], 0)
    
    async def test_database_initialization_timeout_handling(self):
        """Test that database initialization timeout is handled correctly."""
        with patch('netra_backend.app.smd.get_database_timeout_config') as mock_config:
            mock_config.return_value = {
                "initialization_timeout": 1,  # Very short timeout
                "table_setup_timeout": 1
            }
            
            with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError("Timeout")):
                # Should raise DeterministicStartupError with timeout information
                with self.assertRaises(DeterministicStartupError) as context:
                    await self.orchestrator._initialize_database()
                
                self.assertIn("Database initialization timeout", str(context.exception))
                self.assertIn("Cloud SQL connection issues", str(context.exception))
    
    def test_startup_completion_requires_all_phases(self):
        """Test that startup completion requires ALL 7 phases to complete."""
        # Complete only 6 of 7 phases
        for phase in list(StartupPhase)[:-1]:  # All except FINALIZE
            self.orchestrator.completed_phases.add(phase)
        
        # Should raise DeterministicStartupError
        with self.assertRaises(DeterministicStartupError) as context:
            self.orchestrator._mark_startup_complete()
        
        self.assertIn("missing phases", str(context.exception))
        self.assertIn("finalize", str(context.exception))
    
    def test_startup_completion_with_failed_phases_prevents_completion(self):
        """Test that failed phases prevent startup completion."""
        # Complete all phases
        self.orchestrator.completed_phases = set(StartupPhase)
        
        # But mark one as failed
        self.orchestrator.failed_phases.add(StartupPhase.DATABASE)
        
        # Should raise DeterministicStartupError
        with self.assertRaises(DeterministicStartupError) as context:
            self.orchestrator._mark_startup_complete()
        
        self.assertIn("failed phases", str(context.exception))
        self.assertIn("database", str(context.exception))


class TestConcurrentStartupScenarios(BaseTestCase):
    """
    Test concurrent startup scenarios and race condition prevention.
    
    BVJ: Platform/Internal - Ensures system handles concurrent initialization
    attempts gracefully and prevents race conditions in multi-instance deployments.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.app = FastAPI()
        self.orchestrator = StartupOrchestrator(self.app)
    
    def test_multiple_phase_transitions_maintain_consistency(self):
        """Test that rapid phase transitions maintain state consistency."""
        # Rapidly transition through phases
        phases = [StartupPhase.INIT, StartupPhase.DEPENDENCIES, StartupPhase.DATABASE]
        
        for phase in phases:
            self.orchestrator._set_current_phase(phase)
            time.sleep(0.001)  # Very small delay
        
        # Verify final state consistency
        self.assertEqual(self.orchestrator.current_phase, StartupPhase.DATABASE)
        self.assertEqual(len(self.orchestrator.completed_phases), 2)  # INIT and DEPENDENCIES completed
        self.assertIn(StartupPhase.INIT, self.orchestrator.completed_phases)
        self.assertIn(StartupPhase.DEPENDENCIES, self.orchestrator.completed_phases)
        self.assertNotIn(StartupPhase.DATABASE, self.orchestrator.completed_phases)  # Still current
    
    def test_concurrent_phase_failure_and_success_handling(self):
        """Test handling of simultaneous phase operations."""
        # Set current phase
        self.orchestrator._set_current_phase(StartupPhase.CACHE)
        
        # Simulate concurrent operations (phase completion vs failure)
        error = Exception("Concurrent error")
        
        # Fail the phase
        self.orchestrator._fail_phase(StartupPhase.CACHE, error)
        
        # Verify failure state is maintained
        self.assertIn(StartupPhase.CACHE, self.orchestrator.failed_phases)
        self.assertTrue(self.app.state.startup_failed)
        self.assertIn("Phase cache failed", self.app.state.startup_error)
    
    def test_startup_state_consistency_during_failure(self):
        """Test that app.state remains consistent during failure scenarios."""
        self.orchestrator._set_current_phase(StartupPhase.SERVICES)
        
        # Simulate failure
        test_error = Exception("Service initialization failed")
        self.orchestrator._fail_phase(StartupPhase.SERVICES, test_error)
        
        # Verify app.state consistency
        self.assertFalse(self.app.state.startup_complete)
        self.assertTrue(self.app.state.startup_failed)
        self.assertEqual(self.app.state.startup_phase, "services")
        self.assertIn("services", self.app.state.startup_failed_phases)
        self.assertEqual(self.app.state.startup_error, "Phase services failed: Service initialization failed")


class TestEnvironmentConfigurationIsolation(BaseTestCase):
    """
    Test environment configuration and isolation requirements.
    
    BVJ: Platform/Internal - Ensures proper environment isolation
    and configuration management across different deployment environments.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.app = FastAPI()
        self.orchestrator = StartupOrchestrator(self.app)
    
    def test_get_env_wrapper_function(self):
        """Test that get_env wrapper function works correctly."""
        # Test with default value
        result = get_env("NONEXISTENT_KEY", "default_value")
        self.assertEqual(result, "default_value")
        
        # Test with empty string default (should return default)
        result = get_env("NONEXISTENT_KEY", "")
        self.assertEqual(result, "")
    
    @patch('netra_backend.app.smd.get_isolated_env')
    def test_environment_isolation_in_get_env(self, mock_get_isolated_env):
        """Test that get_env uses isolated environment."""
        mock_env = Mock()
        mock_env.get.return_value = "test_value"
        mock_get_isolated_env.return_value = mock_env
        
        # Import should trigger the module-level initialization
        from netra_backend.app.smd import get_env as test_get_env
        
        result = test_get_env("TEST_KEY", "default")
        
        # Should have called isolated environment
        mock_get_isolated_env.assert_called()
    
    @patch('netra_backend.app.smd.validate_environment_at_startup')
    def test_environment_validation_called(self, mock_validate):
        """Test that environment validation is called during startup."""
        self.orchestrator._validate_environment()
        mock_validate.assert_called_once()
    
    @patch('netra_backend.app.smd.validate_environment_at_startup')
    def test_environment_validation_failure_propagates(self, mock_validate):
        """Test that environment validation failure propagates correctly."""
        mock_validate.side_effect = Exception("Environment validation failed")
        
        with self.assertRaises(Exception) as context:
            self.orchestrator._validate_environment()
        
        self.assertIn("Environment validation failed", str(context.exception))


class TestStartupCompletionAndFailureHandling(BaseTestCase):
    """
    Test startup completion and comprehensive failure handling.
    
    BVJ: Platform/Internal - Ensures proper startup completion logic
    and comprehensive failure reporting for operational debugging.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.app = FastAPI()
        self.orchestrator = StartupOrchestrator(self.app)
    
    def test_mark_startup_complete_success(self):
        """Test successful startup completion marking."""
        # Complete all phases
        for phase in StartupPhase:
            self.orchestrator.completed_phases.add(phase)
            self.orchestrator.phase_timings[phase] = {
                'start_time': time.time(),
                'duration': 0.1
            }
        
        self.orchestrator.current_phase = StartupPhase.FINALIZE
        
        # Should complete successfully
        self.orchestrator._mark_startup_complete()
        
        # Verify completion state
        self.assertTrue(self.app.state.startup_complete)
        self.assertFalse(self.app.state.startup_in_progress)
        self.assertFalse(self.app.state.startup_failed)
        self.assertIsNone(self.app.state.startup_error)
        self.assertEqual(self.app.state.startup_phase, "complete")
    
    def test_handle_startup_failure_comprehensive_logging(self):
        """Test comprehensive failure logging and state management."""
        # Set up partial completion state
        self.orchestrator._set_current_phase(StartupPhase.DATABASE)
        self.orchestrator.completed_phases.add(StartupPhase.INIT)
        self.orchestrator.failed_phases.add(StartupPhase.DATABASE)
        
        test_error = Exception("Database connection timeout")
        
        self.orchestrator._handle_startup_failure(test_error)
        
        # Verify failure state
        self.assertFalse(self.app.state.startup_complete)
        self.assertFalse(self.app.state.startup_in_progress)
        self.assertTrue(self.app.state.startup_failed)
        self.assertEqual(self.app.state.startup_error, "Database connection timeout")
        self.assertEqual(self.app.state.startup_phase, "database")
    
    @patch('netra_backend.app.smd.central_logger')
    async def test_run_deterministic_startup_success(self, mock_logger):
        """Test successful execution of run_deterministic_startup function."""
        mock_logger_instance = Mock()
        mock_logger.get_logger.return_value = mock_logger_instance
        
        # Mock all initialization methods to succeed
        with patch.multiple(
            'netra_backend.app.smd.StartupOrchestrator',
            _phase1_foundation=AsyncMock(),
            _phase2_core_services=AsyncMock(),
            _phase3_database_setup=AsyncMock(),
            _phase4_cache_setup=AsyncMock(),
            _phase5_services_setup=AsyncMock(),
            _phase6_websocket_setup=AsyncMock(),
            _phase7_finalize=AsyncMock()
        ):
            start_time, logger = await run_deterministic_startup(self.app)
            
            # Verify return values
            self.assertIsInstance(start_time, float)
            self.assertIsNotNone(logger)
            
            # Verify completion state
            self.assertTrue(self.app.state.startup_complete)
    
    @patch('netra_backend.app.smd.central_logger')
    async def test_run_deterministic_startup_failure_propagation(self, mock_logger):
        """Test that startup failures are properly propagated."""
        mock_logger_instance = Mock()
        mock_logger.get_logger.return_value = mock_logger_instance
        
        # Mock phase1 to fail
        with patch.object(StartupOrchestrator, '_phase1_foundation', side_effect=Exception("Foundation failed")):
            
            # Should raise DeterministicStartupError
            with self.assertRaises(DeterministicStartupError) as context:
                await run_deterministic_startup(self.app)
            
            self.assertIn("CRITICAL STARTUP FAILURE", str(context.exception))
            self.assertIn("Foundation failed", str(context.exception))


class TestAuthValidationAndSecurity(BaseTestCase):
    """
    Test auth validation and security requirements during startup.
    
    BVJ: Security/Platform - Ensures auth system is properly validated
    before system becomes operational to prevent security vulnerabilities.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.app = FastAPI()
        self.orchestrator = StartupOrchestrator(self.app)
    
    async def test_auth_configuration_validation_success(self):
        """Test successful auth configuration validation."""
        with patch('netra_backend.app.smd.validate_auth_at_startup') as mock_validate:
            mock_validate.return_value = None  # Success
            
            # Should not raise exception
            await self.orchestrator._validate_auth_configuration()
    
    async def test_auth_configuration_validation_failure_is_fatal(self):
        """Test that auth validation failure causes fatal startup failure."""
        with patch('netra_backend.app.smd.validate_auth_at_startup') as mock_validate:
            mock_validate.side_effect = Exception("Auth validation failed - insecure configuration")
            
            # Should raise DeterministicStartupError
            with self.assertRaises(DeterministicStartupError) as context:
                await self.orchestrator._validate_auth_configuration()
            
            self.assertIn("Auth validation failed", str(context.exception))
            self.assertIn("system cannot start", str(context.exception))
    
    async def test_auth_validation_import_error_is_fatal(self):
        """Test that missing auth validator causes fatal failure."""
        with patch('netra_backend.app.smd.validate_auth_at_startup', side_effect=ImportError("Module not found")):
            
            # Should raise DeterministicStartupError
            with self.assertRaises(DeterministicStartupError) as context:
                await self.orchestrator._validate_auth_configuration()
            
            self.assertIn("Auth validator module not found", str(context.exception))
            self.assertIn("cannot verify auth security", str(context.exception))


if __name__ == '__main__':
    # Run tests with proper async support
    unittest.main()