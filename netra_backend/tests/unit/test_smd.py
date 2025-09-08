"""
Comprehensive Unit Tests for Deterministic Startup Module (SMD)

Business Value Justification (BVJ):
- Segment: Platform/Internal - Mission Critical Infrastructure
- Business Goal: Ensure deterministic startup prevents chat functionality failures (90% of value)
- Value Impact: Zero-tolerance startup failures across all environments
- Strategic Impact: $5M+ ARR protection through elimination of startup-related outages

This test suite covers the Deterministic Startup Module (smd.py) which implements
NO AMBIGUITY, NO FALLBACKS startup logic. Every test failure here indicates
potential complete service failure with massive business impact.

Test Coverage Areas:
1. StartupPhase enum and phase transitions
2. DeterministicStartupError handling 
3. StartupOrchestrator state management
4. 7-phase deterministic startup sequence
5. Phase timing and performance validation
6. Critical service validation (chat requirements)
7. WebSocket integration for agent events
8. Authentication validation (SSOT auth)
9. Database and Redis initialization (no graceful mode)
10. Agent supervisor creation with WebSocket bridge
11. Factory pattern initialization
12. Health validation and critical path checks  
13. Error handling and failure scenarios
14. Performance optimization and monitoring
15. Startup completion validation and metrics

CRITICAL REQUIREMENTS:
- NO graceful degradation allowed - test strict deterministic behavior
- ALL tests MUST fail hard when system breaks - NO exception masking
- Use SSOT patterns and absolute imports per CLAUDE.md
- Validate chat-critical paths (90% business value dependency)
- Test multi-user isolation and factory patterns
"""

import asyncio
import logging
import os
import sys
import time
import unittest
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call

import pytest
from fastapi import FastAPI

# SSOT imports following CLAUDE.md absolute import requirements
from test_framework.ssot.base import BaseTestCase
from shared.isolated_environment import get_env

# Import modules under test
from netra_backend.app import smd
from netra_backend.app.smd import (
    StartupPhase, 
    DeterministicStartupError, 
    StartupOrchestrator,
    run_deterministic_startup
)


class TestStartupPhaseEnum(BaseTestCase):
    """Test StartupPhase enum defines correct business-critical phases."""
    
    def test_startup_phases_cover_all_business_requirements(self):
        """Test startup phases cover all business-critical requirements."""
        expected_phases = {
            'INIT': 'Foundation and environment setup',
            'DEPENDENCIES': 'Core services (auth, keys, LLM)',  
            'DATABASE': 'Database connections and schema',
            'CACHE': 'Redis and caching systems',
            'SERVICES': 'Chat pipeline and critical services',
            'WEBSOCKET': 'WebSocket integration (chat events)',
            'FINALIZE': 'Validation and optional services'
        }
        
        actual_phases = {phase.name: phase.value for phase in StartupPhase}
        
        # Verify all expected phases exist
        for phase_name, description in expected_phases.items():
            self.assertIn(
                phase_name, actual_phases,
                f"CRITICAL BUSINESS FAILURE: Missing startup phase {phase_name} ({description})"
            )
        
        # Verify phase count matches business requirements (exactly 7 phases)
        self.assertEqual(
            len(actual_phases), 7,
            f"BUSINESS ARCHITECTURE FAILURE: Expected exactly 7 startup phases, got {len(actual_phases)}. "
            f"7-phase architecture is designed for optimal business value delivery."
        )
    
    def test_startup_phases_maintain_business_critical_order(self):
        """Test startup phases maintain business-critical dependency order."""
        phase_list = list(StartupPhase)
        
        # Define business-critical dependencies
        critical_order = [
            StartupPhase.INIT,        # Must be first - foundation
            StartupPhase.DEPENDENCIES, # Core services before data layer  
            StartupPhase.DATABASE,    # Database before cache
            StartupPhase.CACHE,       # Cache before services
            StartupPhase.SERVICES,    # Services before WebSocket  
            StartupPhase.WEBSOCKET,   # WebSocket before finalization
            StartupPhase.FINALIZE     # Must be last - validation
        ]
        
        self.assertEqual(
            phase_list, critical_order,
            f"CRITICAL BUSINESS FAILURE: Startup phase order is incorrect. "
            f"Wrong order can cause cascade failures in chat functionality. "
            f"Expected: {[p.name for p in critical_order]}, "
            f"Got: {[p.name for p in phase_list]}"
        )


class TestDeterministicStartupError(BaseTestCase):
    """Test DeterministicStartupError provides proper business context."""
    
    def test_deterministic_startup_error_inheritance(self):
        """Test DeterministicStartupError inherits from Exception properly."""
        error = DeterministicStartupError("Test failure")
        
        self.assertIsInstance(error, Exception)
        self.assertIsInstance(error, DeterministicStartupError)
        
    def test_deterministic_startup_error_message_handling(self):
        """Test error messages provide business-actionable information."""
        test_scenarios = [
            "Database connection failed - check POSTGRES_HOST configuration",
            "Agent supervisor initialization failed - WebSocket bridge missing",
            "Authentication validation failed - JWT_SECRET_KEY invalid",
            "Redis connection timeout - check REDIS_URL and service availability"
        ]
        
        for error_message in test_scenarios:
            with self.subTest(message=error_message):
                error = DeterministicStartupError(error_message)
                
                self.assertEqual(str(error), error_message)
                self.assertGreater(
                    len(str(error)), 20,
                    f"Error message too short for operational debugging: {error_message}"
                )


class TestStartupOrchestrator(BaseTestCase):
    """Test StartupOrchestrator manages deterministic startup with business validation."""
    
    REQUIRES_DATABASE = False  # Unit tests mock database  
    REQUIRES_REDIS = False     # Unit tests mock Redis
    ISOLATION_ENABLED = True   # Critical for testing isolation
    AUTO_CLEANUP = True        # Clean up mocks
    
    def setUp(self):
        """Set up StartupOrchestrator test environment."""
        super().setUp()
        
        # Create mock FastAPI app
        self.mock_app = Mock(spec=FastAPI)
        self.mock_app.state = Mock()
        
        # Initialize app state attributes to prevent AttributeError
        self._initialize_app_state()
        
        # Set up test environment
        with self.isolated_environment(
            ENVIRONMENT="test",
            TESTING="true",
            JWT_SECRET_KEY="test-jwt-secret-deterministic-startup",
            DATABASE_URL="postgresql://test:test@localhost:5432/test_netra_smd",
            REDIS_URL="redis://localhost:6379/2"
        ):
            pass
        
        # Create orchestrator for testing
        self.orchestrator = StartupOrchestrator(self.mock_app)
        
        # Performance tracking for business requirements
        self.test_start_time = time.time()
    
    def _initialize_app_state(self):
        """Initialize app state with all expected attributes."""
        # Startup tracking attributes
        self.mock_app.state.startup_complete = False
        self.mock_app.state.startup_in_progress = False
        self.mock_app.state.startup_failed = False  
        self.mock_app.state.startup_error = None
        self.mock_app.state.startup_phase = "init"
        self.mock_app.state.startup_start_time = None
        self.mock_app.state.startup_phase_timings = {}
        self.mock_app.state.startup_completed_phases = []
        self.mock_app.state.startup_failed_phases = []
        
        # Service attributes
        critical_services = [
            'db_session_factory', 'redis_manager', 'llm_manager', 'key_manager',
            'security_service', 'agent_supervisor', 'agent_service', 'thread_service', 
            'corpus_service', 'agent_websocket_bridge', 'background_task_manager',
            'health_service', 'tool_classes', 'agent_class_registry'
        ]
        
        for service in critical_services:
            setattr(self.mock_app.state, service, None)

    def test_orchestrator_initialization_sets_business_critical_state(self):
        """Test orchestrator initialization sets all business-critical state."""
        # Verify orchestrator was initialized properly
        self.assertIsNotNone(self.orchestrator)
        self.assertEqual(self.orchestrator.app, self.mock_app)
        self.assertIsNotNone(self.orchestrator.logger)
        self.assertIsInstance(self.orchestrator.start_time, float)
        
        # Verify business-critical tracking attributes
        self.assertIsNone(self.orchestrator.current_phase)
        self.assertIsInstance(self.orchestrator.phase_timings, dict)
        self.assertIsInstance(self.orchestrator.completed_phases, set)
        self.assertIsInstance(self.orchestrator.failed_phases, set)
        
        # Verify app state was initialized for business tracking
        self.assertFalse(self.mock_app.state.startup_complete)
        self.assertTrue(self.mock_app.state.startup_in_progress)  
        self.assertFalse(self.mock_app.state.startup_failed)
        self.assertIsNone(self.mock_app.state.startup_error)
        self.assertEqual(self.mock_app.state.startup_phase, "init")
        
    def test_phase_transition_tracking_for_business_monitoring(self):
        """Test phase transition tracking provides business monitoring data."""
        # Test phase transition
        test_phase = StartupPhase.DATABASE
        
        start_time = time.time()
        self.orchestrator._set_current_phase(test_phase)
        transition_time = time.time() - start_time
        
        # Verify transition performance (business requirement)
        self.assertLess(
            transition_time, 0.01,
            f"Phase transition too slow ({transition_time:.4f}s). "
            f"Must be fast for business monitoring accuracy."
        )
        
        # Verify phase tracking
        self.assertEqual(self.orchestrator.current_phase, test_phase)
        self.assertEqual(self.mock_app.state.startup_phase, test_phase.value)
        self.assertIn(test_phase, self.orchestrator.phase_timings)
        
        # Verify timing structure for business metrics
        timing_data = self.orchestrator.phase_timings[test_phase]
        self.assertIn('start_time', timing_data)
        self.assertIn('duration', timing_data)
        self.assertEqual(timing_data['duration'], 0.0)  # Not completed yet

    def test_phase_completion_updates_business_metrics(self):
        """Test phase completion updates business monitoring metrics."""
        test_phase = StartupPhase.SERVICES
        
        # Set up phase 
        self.orchestrator._set_current_phase(test_phase)
        
        # Simulate some work time
        time.sleep(0.01)
        
        # Complete phase
        self.orchestrator._complete_phase(test_phase)
        
        # Verify completion tracking
        self.assertIn(test_phase, self.orchestrator.completed_phases)
        self.assertIn(test_phase.value, self.mock_app.state.startup_completed_phases)
        
        # Verify timing was recorded for business analysis
        timing_data = self.orchestrator.phase_timings[test_phase]
        self.assertGreater(timing_data['duration'], 0.0)
        self.assertLess(timing_data['duration'], 1.0)  # Should be very quick

    def test_phase_failure_tracking_for_business_incident_response(self):
        """Test phase failure tracking supports business incident response."""
        test_phase = StartupPhase.WEBSOCKET
        test_error = Exception("WebSocket initialization failed - chat will be broken")
        
        # Set up phase
        self.orchestrator._set_current_phase(test_phase)
        
        # Fail phase
        self.orchestrator._fail_phase(test_phase, test_error)
        
        # Verify failure tracking for incident response
        self.assertIn(test_phase, self.orchestrator.failed_phases)
        self.assertIn(test_phase.value, self.mock_app.state.startup_failed_phases)
        self.assertTrue(self.mock_app.state.startup_failed)
        
        # Verify error context for business debugging
        self.assertIn("WebSocket", self.mock_app.state.startup_error)
        self.assertIn("phase", self.mock_app.state.startup_error.lower())

    def test_startup_completion_validation_enforces_business_requirements(self):
        """Test startup completion validation enforces all business requirements."""
        # Set up all phases as completed (business requirement)
        all_phases = set(StartupPhase)
        self.orchestrator.completed_phases = all_phases.copy()
        self.orchestrator.failed_phases = set()  # No failures allowed
        
        # Mock phase timings for all phases
        for phase in all_phases:
            self.orchestrator.phase_timings[phase] = {
                'start_time': time.time() - 1.0,
                'duration': 0.1
            }
        
        # Test successful completion  
        self.orchestrator._mark_startup_complete()
        
        # Verify business-critical completion state
        self.assertTrue(self.mock_app.state.startup_complete)
        self.assertFalse(self.mock_app.state.startup_in_progress)
        self.assertFalse(self.mock_app.state.startup_failed)
        self.assertIsNone(self.mock_app.state.startup_error)
        self.assertEqual(self.mock_app.state.startup_phase, "complete")

    def test_startup_completion_fails_with_missing_phases(self):
        """Test startup completion fails if business-critical phases are missing."""
        # Set up incomplete phases (missing critical WEBSOCKET phase)
        incomplete_phases = {StartupPhase.INIT, StartupPhase.DEPENDENCIES, StartupPhase.DATABASE}
        self.orchestrator.completed_phases = incomplete_phases
        self.orchestrator.failed_phases = set()
        
        # Test completion validation
        with self.assertRaises(DeterministicStartupError) as cm:
            self.orchestrator._mark_startup_complete()
        
        # Verify error indicates missing phases  
        error_message = str(cm.exception)
        self.assertIn("missing phases", error_message.lower())
        
        # Verify WEBSOCKET phase is mentioned (critical for chat)
        self.assertIn("websocket", error_message.lower())

    def test_startup_failure_handling_provides_business_context(self):
        """Test startup failure handling provides comprehensive business context."""
        test_error = RuntimeError("Critical service initialization failed")
        current_phase = StartupPhase.SERVICES
        
        # Set up failure scenario
        self.orchestrator.current_phase = current_phase
        self.orchestrator.completed_phases = {StartupPhase.INIT, StartupPhase.DEPENDENCIES}
        
        # Test failure handling  
        self.orchestrator._handle_startup_failure(test_error)
        
        # Verify business-critical failure state
        self.assertFalse(self.mock_app.state.startup_complete)
        self.assertFalse(self.mock_app.state.startup_in_progress)
        self.assertTrue(self.mock_app.state.startup_failed)
        self.assertIsNotNone(self.mock_app.state.startup_error)
        self.assertEqual(self.mock_app.state.startup_phase, current_phase.value)
        
        # Verify error context for business incident response
        error_context = self.mock_app.state.startup_error
        self.assertIn("service", error_context.lower())
        self.assertIn("failed", error_context.lower())


class TestDeterministicStartupPhases(BaseTestCase):
    """Test each phase of deterministic startup for business requirements."""
    
    REQUIRES_DATABASE = False
    REQUIRES_REDIS = False
    ISOLATION_ENABLED = True
    AUTO_CLEANUP = True
    
    def setUp(self):
        """Set up phase testing environment."""
        super().setUp()
        
        self.mock_app = Mock(spec=FastAPI)
        self.mock_app.state = Mock()
        
        # Initialize app state
        self._initialize_app_state()
        
        # Set up test environment
        with self.isolated_environment(
            ENVIRONMENT="test",
            TESTING="true",
            JWT_SECRET_KEY="test-jwt-deterministic-phase-testing",
            DATABASE_URL="postgresql://test:test@localhost:5432/test_phases",
            REDIS_URL="redis://localhost:6379/3"
        ):
            pass
            
        self.orchestrator = StartupOrchestrator(self.mock_app)
    
    def _initialize_app_state(self):
        """Initialize app state for phase testing."""
        # All the app state setup from main test class
        self.mock_app.state.startup_complete = False
        self.mock_app.state.startup_in_progress = True
        self.mock_app.state.startup_failed = False
        self.mock_app.state.startup_error = None
        
        # Initialize service attributes
        services = [
            'db_session_factory', 'redis_manager', 'llm_manager', 'key_manager',
            'security_service', 'agent_supervisor', 'agent_service', 'thread_service',
            'corpus_service', 'agent_websocket_bridge', 'background_task_manager', 
            'health_service', 'tool_classes', 'agent_class_registry'
        ]
        
        for service in services:
            setattr(self.mock_app.state, service, None)

    @pytest.mark.asyncio
    async def test_phase1_foundation_validates_business_environment(self):
        """Test Phase 1 (INIT) validates business-critical foundation requirements."""
        with patch.object(self.orchestrator, '_validate_environment') as mock_validate_env, \
             patch.object(self.orchestrator, '_run_migrations') as mock_run_migrations:
            
            # Test Phase 1 execution
            await self.orchestrator._phase1_foundation()
            
            # Verify business environment validation  
            mock_validate_env.assert_called_once()
            
            # Verify migrations were attempted (database readiness)
            mock_run_migrations.assert_called_once()

    @pytest.mark.asyncio
    async def test_phase2_dependencies_initializes_chat_critical_services(self):
        """Test Phase 2 (DEPENDENCIES) initializes all chat-critical services."""
        with patch.object(self.orchestrator, '_validate_auth_configuration') as mock_validate_auth, \
             patch.object(self.orchestrator, '_initialize_key_manager') as mock_init_keys, \
             patch.object(self.orchestrator, '_initialize_llm_manager') as mock_init_llm, \
             patch.object(self.orchestrator, '_apply_startup_fixes') as mock_apply_fixes:
            
            # Mock successful service initialization
            self.mock_app.state.key_manager = Mock()
            self.mock_app.state.llm_manager = Mock()
            
            # Test Phase 2 execution
            await self.orchestrator._phase2_core_services()
            
            # Verify chat-critical services were initialized
            mock_validate_auth.assert_called_once()  # Critical for multi-user chat
            mock_init_keys.assert_called_once()      # Critical for encryption
            mock_init_llm.assert_called_once()       # Critical for AI responses  
            mock_apply_fixes.assert_called_once()    # Critical for stability

    @pytest.mark.asyncio
    async def test_phase2_fails_without_chat_critical_services(self):
        """Test Phase 2 fails deterministically without chat-critical services."""
        with patch.object(self.orchestrator, '_validate_auth_configuration'), \
             patch.object(self.orchestrator, '_initialize_key_manager'), \
             patch.object(self.orchestrator, '_initialize_llm_manager'), \
             patch.object(self.orchestrator, '_apply_startup_fixes'):
            
            # Simulate key manager failure (chat-critical)
            self.mock_app.state.key_manager = None  # Failure condition
            self.mock_app.state.llm_manager = Mock()
            
            # Test Phase 2 failure
            with self.assertRaises(DeterministicStartupError) as cm:
                await self.orchestrator._phase2_core_services()
            
            # Verify error indicates key manager failure
            error_message = str(cm.exception)
            self.assertIn("key manager", error_message.lower())

    @pytest.mark.asyncio  
    async def test_phase3_database_enforces_strict_requirements(self):
        """Test Phase 3 (DATABASE) enforces strict business requirements."""
        with patch.object(self.orchestrator, '_initialize_database') as mock_init_db, \
             patch.object(self.orchestrator, '_validate_database_schema') as mock_validate_schema:
            
            # Mock successful database initialization
            self.mock_app.state.db_session_factory = Mock()
            
            # Test Phase 3 execution
            await self.orchestrator._phase3_database_setup()
            
            # Verify strict database requirements
            mock_init_db.assert_called_once()
            mock_validate_schema.assert_called_once()

    @pytest.mark.asyncio
    async def test_phase3_fails_without_database_session_factory(self):
        """Test Phase 3 fails deterministically without database session factory."""
        with patch.object(self.orchestrator, '_initialize_database'), \
             patch.object(self.orchestrator, '_validate_database_schema'):
            
            # Simulate database initialization failure  
            self.mock_app.state.db_session_factory = None  # Failure condition
            
            # Test Phase 3 failure
            with self.assertRaises(DeterministicStartupError) as cm:
                await self.orchestrator._phase3_database_setup()
            
            # Verify error indicates database failure
            error_message = str(cm.exception) 
            self.assertIn("database", error_message.lower())
            self.assertIn("none", error_message.lower())

    @pytest.mark.asyncio
    async def test_phase4_cache_enforces_redis_requirements(self):
        """Test Phase 4 (CACHE) enforces Redis requirements for chat performance."""
        with patch.object(self.orchestrator, '_initialize_redis') as mock_init_redis:
            
            # Mock successful Redis initialization
            self.mock_app.state.redis_manager = Mock()
            
            # Test Phase 4 execution
            await self.orchestrator._phase4_cache_setup()
            
            # Verify Redis initialization
            mock_init_redis.assert_called_once()

    @pytest.mark.asyncio
    async def test_phase4_fails_without_redis_manager(self):
        """Test Phase 4 fails deterministically without Redis manager."""
        with patch.object(self.orchestrator, '_initialize_redis'):
            
            # Simulate Redis initialization failure
            self.mock_app.state.redis_manager = None  # Failure condition
            
            # Test Phase 4 failure
            with self.assertRaises(DeterministicStartupError) as cm:
                await self.orchestrator._phase4_cache_setup()
            
            # Verify error indicates Redis failure
            error_message = str(cm.exception)
            self.assertIn("redis", error_message.lower()) 

    @pytest.mark.asyncio
    async def test_phase5_services_initializes_complete_chat_pipeline(self):
        """Test Phase 5 (SERVICES) initializes complete chat pipeline."""
        with patch.object(self.orchestrator, '_initialize_agent_class_registry') as mock_init_registry, \
             patch.object(self.orchestrator, '_initialize_agent_websocket_bridge_basic') as mock_init_bridge, \
             patch.object(self.orchestrator, '_initialize_tool_registry') as mock_init_tools, \
             patch.object(self.orchestrator, '_initialize_agent_supervisor') as mock_init_supervisor, \
             patch.object(self.orchestrator, '_initialize_background_tasks') as mock_init_tasks, \
             patch.object(self.orchestrator, '_initialize_health_service') as mock_init_health, \
             patch.object(self.orchestrator, '_initialize_factory_patterns') as mock_init_factory:
            
            # Mock successful service initialization
            self.mock_app.state.agent_websocket_bridge = Mock()
            self.mock_app.state.tool_classes = ["Tool1", "Tool2"]
            self.mock_app.state.agent_supervisor = Mock()
            self.mock_app.state.thread_service = Mock()
            self.mock_app.state.background_task_manager = Mock() 
            self.mock_app.state.health_service = Mock()
            
            # Test Phase 5 execution  
            await self.orchestrator._phase5_services_setup()
            
            # Verify complete chat pipeline initialization
            mock_init_registry.assert_called_once()    # Agent classes
            mock_init_bridge.assert_called_once()      # WebSocket events
            mock_init_tools.assert_called_once()       # Tool execution
            mock_init_supervisor.assert_called_once()  # Agent orchestration
            mock_init_tasks.assert_called_once()       # Background processing
            mock_init_health.assert_called_once()      # System monitoring
            mock_init_factory.assert_called_once()     # Factory patterns

    @pytest.mark.asyncio
    async def test_phase6_websocket_enables_realtime_chat_events(self):
        """Test Phase 6 (WEBSOCKET) enables real-time chat events."""
        with patch.object(self.orchestrator, '_initialize_websocket') as mock_init_ws, \
             patch.object(self.orchestrator, '_perform_complete_bridge_integration') as mock_bridge_integration, \
             patch.object(self.orchestrator, '_verify_tool_dispatcher_websocket_support') as mock_verify_tools, \
             patch.object(self.orchestrator, '_register_message_handlers') as mock_register_handlers, \
             patch.object(self.orchestrator, '_verify_bridge_health') as mock_verify_bridge, \
             patch.object(self.orchestrator, '_verify_websocket_events') as mock_verify_events:
            
            # Mock WebSocket bridge for integration
            self.mock_app.state.agent_websocket_bridge = Mock()
            
            # Test Phase 6 execution
            await self.orchestrator._phase6_websocket_setup()
            
            # Verify real-time chat event infrastructure
            mock_init_ws.assert_called_once()           # WebSocket manager
            mock_bridge_integration.assert_called_once()  # Bridge integration
            mock_verify_tools.assert_called_once()      # Tool dispatcher support
            mock_register_handlers.assert_called_once() # Message handlers
            mock_verify_bridge.assert_called_once()     # Bridge health
            mock_verify_events.assert_called_once()     # Event delivery

    @pytest.mark.asyncio
    async def test_phase7_finalize_validates_complete_system(self):
        """Test Phase 7 (FINALIZE) validates complete system for business operation."""
        with patch.object(self.orchestrator, '_start_connection_monitoring') as mock_start_monitoring, \
             patch('netra_backend.app.startup_health_checks.validate_startup_health') as mock_health_checks, \
             patch.object(self.orchestrator, '_run_comprehensive_validation') as mock_comprehensive, \
             patch.object(self.orchestrator, '_run_critical_path_validation') as mock_critical_path, \
             patch.object(self.orchestrator, '_initialize_clickhouse') as mock_clickhouse, \
             patch.object(self.orchestrator, '_initialize_performance_manager') as mock_performance, \
             patch.object(self.orchestrator, '_initialize_monitoring') as mock_monitoring:
            
            # Mock successful health checks
            mock_health_checks.return_value = True
            
            # Test Phase 7 execution
            await self.orchestrator._phase7_finalize()
            
            # Verify complete system validation
            mock_start_monitoring.assert_called_once()   # Connection monitoring
            mock_health_checks.assert_called_once()      # Health validation
            mock_comprehensive.assert_called_once()      # Comprehensive validation
            mock_critical_path.assert_called_once()      # Critical path validation
            
            # Optional services should be attempted but allowed to fail
            mock_clickhouse.assert_called_once()
            mock_performance.assert_called_once()
            mock_monitoring.assert_called_once()


class TestDeterministicStartupIntegration(BaseTestCase):
    """Test complete deterministic startup integration for business scenarios."""
    
    REQUIRES_DATABASE = False
    REQUIRES_REDIS = False
    ISOLATION_ENABLED = True
    AUTO_CLEANUP = True
    
    def setUp(self):
        """Set up integration test environment."""
        super().setUp()
        
        self.mock_app = Mock(spec=FastAPI)
        self.mock_app.state = Mock()
        
        # Initialize comprehensive app state
        self._initialize_comprehensive_app_state()
    
    def _initialize_comprehensive_app_state(self):
        """Initialize comprehensive app state for integration testing."""
        # Startup state
        self.mock_app.state.startup_complete = False
        self.mock_app.state.startup_in_progress = False
        self.mock_app.state.startup_failed = False
        self.mock_app.state.startup_error = None
        
        # All critical services for business operation
        critical_services = [
            'db_session_factory', 'redis_manager', 'llm_manager', 'key_manager',
            'security_service', 'agent_supervisor', 'agent_service', 'thread_service',
            'corpus_service', 'agent_websocket_bridge', 'background_task_manager',
            'health_service', 'tool_classes', 'agent_class_registry', 'execution_tracker'
        ]
        
        for service in critical_services:
            setattr(self.mock_app.state, service, None)

    @patch('netra_backend.app.smd.StartupOrchestrator')
    @pytest.mark.asyncio
    async def test_run_deterministic_startup_creates_orchestrator_properly(self, mock_orchestrator_class):
        """Test run_deterministic_startup creates orchestrator with proper business context."""
        # Mock orchestrator instance
        mock_orchestrator = Mock()
        mock_orchestrator.initialize_system = AsyncMock()
        mock_orchestrator.start_time = time.time()
        mock_orchestrator.logger = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Test deterministic startup
        result = await run_deterministic_startup(self.mock_app)
        
        # Verify orchestrator was created with app
        mock_orchestrator_class.assert_called_once_with(self.mock_app)
        
        # Verify system initialization was called
        mock_orchestrator.initialize_system.assert_called_once()
        
        # Verify return format for business metrics
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        start_time, logger = result
        self.assertEqual(start_time, mock_orchestrator.start_time)
        self.assertEqual(logger, mock_orchestrator.logger)

    @patch('netra_backend.app.smd.StartupOrchestrator')
    @pytest.mark.asyncio
    async def test_run_deterministic_startup_handles_business_critical_failures(self, mock_orchestrator_class):
        """Test run_deterministic_startup handles business-critical failures properly."""
        # Mock orchestrator with initialization failure
        mock_orchestrator = Mock()
        critical_error = RuntimeError("WebSocket bridge initialization failed - chat will not work")
        mock_orchestrator.initialize_system = AsyncMock(side_effect=critical_error)
        mock_orchestrator.logger = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Test startup failure handling
        with self.assertRaises(Exception) as cm:
            await run_deterministic_startup(self.mock_app)
        
        # Verify failure was logged for business incident response
        mock_orchestrator.logger.critical.assert_called()
        
        # Verify error provides business context
        logged_error = mock_orchestrator.logger.critical.call_args[0][0]
        self.assertIn("deterministic startup failed", logged_error.lower())

    @pytest.mark.asyncio
    async def test_complete_deterministic_startup_sequence_performance(self):
        """Test complete deterministic startup sequence meets business performance requirements."""
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
            # Test complete startup sequence timing
            start_time = time.time()
            
            orchestrator = StartupOrchestrator(self.mock_app)
            await orchestrator.initialize_system()
            
            total_time = time.time() - start_time
            
            # Business requirement: Complete startup under 30 seconds
            self.assertLess(
                total_time, 30.0,
                f"BUSINESS PERFORMANCE FAILURE: Complete startup took {total_time:.3f}s, "
                f"exceeds 30s business requirement. Slow startup reduces user satisfaction."
            )
            
            # Verify all phases completed
            expected_phases = set(StartupPhase)
            self.assertEqual(
                orchestrator.completed_phases, expected_phases,
                f"Not all phases completed. Missing: {expected_phases - orchestrator.completed_phases}"
            )
            
            # Verify startup completion state
            self.assertTrue(self.mock_app.state.startup_complete)
            self.assertFalse(self.mock_app.state.startup_in_progress)
            self.assertFalse(self.mock_app.state.startup_failed)

    def tearDown(self):
        """Clean up integration test environment."""  
        # Log test performance for business monitoring
        test_duration = time.time() - getattr(self, 'test_start_time', time.time())
        if test_duration > 5.0:
            print(f"PERFORMANCE WARNING: Integration test took {test_duration:.3f}s")
        
        super().tearDown()


class TestBusinessCriticalValidation(BaseTestCase):
    """Test business-critical validation patterns in deterministic startup."""
    
    def test_startup_phase_enum_business_completeness(self):
        """Test StartupPhase enum covers all business-critical startup aspects."""
        phase_business_mapping = {
            StartupPhase.INIT: {
                'purpose': 'Foundation and environment setup',
                'business_impact': 'Configuration errors prevent all functionality',
                'required_for_chat': True
            },
            StartupPhase.DEPENDENCIES: {
                'purpose': 'Core services (auth, keys, LLM)',
                'business_impact': 'Missing dependencies break authentication and AI',
                'required_for_chat': True  
            },
            StartupPhase.DATABASE: {
                'purpose': 'Database connections and schema',
                'business_impact': 'No database means no conversation persistence',
                'required_for_chat': True
            },
            StartupPhase.CACHE: {
                'purpose': 'Redis and caching systems', 
                'business_impact': 'No cache reduces performance and scalability',
                'required_for_chat': True
            },
            StartupPhase.SERVICES: {
                'purpose': 'Chat pipeline and critical services',
                'business_impact': 'Missing services break core chat functionality',
                'required_for_chat': True
            },
            StartupPhase.WEBSOCKET: {
                'purpose': 'WebSocket integration for real-time events',
                'business_impact': 'No real-time events breaks chat user experience',
                'required_for_chat': True
            },
            StartupPhase.FINALIZE: {
                'purpose': 'Validation and optional services',
                'business_impact': 'No validation means unreliable service',
                'required_for_chat': True
            }
        }
        
        # Verify all phases have business justification
        for phase, mapping in phase_business_mapping.items():
            with self.subTest(phase=phase.name):
                self.assertIsInstance(mapping['purpose'], str)
                self.assertGreater(len(mapping['purpose']), 10)
                self.assertIsInstance(mapping['business_impact'], str) 
                self.assertGreater(len(mapping['business_impact']), 20)
                self.assertTrue(mapping['required_for_chat'])  # All phases required for chat
                
        # Verify comprehensive coverage
        self.assertEqual(
            len(phase_business_mapping), len(StartupPhase),
            "All startup phases must have business justification"
        )

    def test_deterministic_startup_error_business_context(self):
        """Test DeterministicStartupError provides sufficient business context."""
        business_error_scenarios = [
            ("Database connection failed", ["database", "connection"], "data_layer"),
            ("Agent supervisor missing WebSocket bridge", ["agent", "websocket", "bridge"], "chat_layer"),
            ("Authentication validation failed", ["auth", "validation"], "security_layer"),
            ("Redis connection timeout", ["redis", "timeout"], "cache_layer"),
            ("Critical service initialization failed", ["service", "initialization"], "service_layer")
        ]
        
        for error_msg, required_keywords, layer in business_error_scenarios:
            with self.subTest(error=error_msg, layer=layer):
                error = DeterministicStartupError(error_msg)
                
                # Verify error contains business-actionable keywords
                error_text = str(error).lower()
                for keyword in required_keywords:
                    self.assertIn(
                        keyword, error_text,
                        f"Business error missing keyword '{keyword}' for {layer} debugging"
                    )
                
                # Verify error message length is sufficient for business context
                self.assertGreater(
                    len(str(error)), 15,
                    f"Error message too short for business debugging: {error_msg}"
                )

    def test_startup_orchestrator_business_state_tracking(self):
        """Test StartupOrchestrator tracks all business-required state."""
        # Create mock FastAPI app with state attribute
        mock_app = Mock(spec=FastAPI)
        mock_app.state = Mock()
        
        orchestrator = StartupOrchestrator(mock_app)
        
        # Verify business-critical tracking attributes exist
        business_tracking_attributes = [
            'current_phase',      # Current business operation
            'phase_timings',      # Performance metrics
            'completed_phases',   # Success tracking
            'failed_phases',      # Failure tracking  
            'start_time',         # Performance baseline
            'logger'              # Operational debugging
        ]
        
        for attr in business_tracking_attributes:
            with self.subTest(attribute=attr):
                self.assertTrue(
                    hasattr(orchestrator, attr),
                    f"Business tracking attribute '{attr}' missing from orchestrator"
                )
                
                attr_value = getattr(orchestrator, attr)
                
                # current_phase is intentionally None on initialization
                if attr == 'current_phase':
                    self.assertIsNone(
                        attr_value,
                        f"Business tracking attribute '{attr}' should be None on initialization"
                    )
                else:
                    self.assertIsNotNone(
                        attr_value,
                        f"Business tracking attribute '{attr}' not initialized"
                    )


if __name__ == '__main__':
    # Run comprehensive SMD test suite with business focus
    unittest.main(verbosity=2, buffer=True)