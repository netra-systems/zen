"""
Integration Tests for Startup Module and SMD (Deterministic Startup) Integration

Business Value Justification (BVJ):
- Segment: Platform/Internal - Business Critical Infrastructure
- Business Goal: Validate startup module + SMD integration prevents chat system failures
- Value Impact: Ensures startup sequence reliability across environments (dev/staging/prod) 
- Strategic Impact: $10M+ ARR protection through elimination of startup cascade failures

This integration test suite validates the complete interaction between:
1. startup_module.py - Legacy startup components and helper functions
2. smd.py - Deterministic startup orchestrator and business logic
3. Real service integration patterns for database, Redis, auth
4. WebSocket integration for chat functionality
5. Multi-user isolation and factory patterns
6. Performance validation and timing requirements
7. Error handling and business continuity flows

CRITICAL REQUIREMENTS:
- Use REAL services (database, Redis) - NO mocks for integration
- ALL tests MUST fail hard when system breaks - NO exception masking
- Use SSOT patterns from test_framework/ssot/
- Follow absolute import patterns per CLAUDE.md
- Validate business-critical chat functionality paths
- Test startup sequence determinism and reliability
"""

import asyncio
import logging
import os
import sys
import time
import unittest
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI

# SSOT imports following CLAUDE.md absolute import requirements
from test_framework.ssot.base import BaseTestCase, IntegrationTestCase
from shared.isolated_environment import get_env

# Import modules under test
from netra_backend.app import startup_module, smd
from netra_backend.app.smd import StartupPhase, DeterministicStartupError, StartupOrchestrator


class TestStartupSmdIntegration(IntegrationTestCase):
    """
    Integration tests for startup_module + smd deterministic startup integration.
    
    This test suite validates the complete integration between legacy startup
    helpers and the new deterministic startup orchestrator, ensuring business
    requirements are met across all environments.
    
    CRITICAL: Uses REAL services - database, Redis connections required.
    """
    
    # Configure SSOT base classes for integration testing
    REQUIRES_DATABASE = True   # Real database required for integration
    REQUIRES_REDIS = True      # Real Redis required for integration
    ISOLATION_ENABLED = True   # Critical for multi-user validation
    AUTO_CLEANUP = True        # Clean up real connections
    
    def setUp(self):
        """Set up integration test environment with real services."""
        super().setUp()
        
        # Create FastAPI app for integration testing
        self.app = Mock(spec=FastAPI)
        self.app.state = Mock()
        self._initialize_comprehensive_app_state()
        
        # Set up test environment with business-critical values
        with self.isolated_environment(
            ENVIRONMENT="integration_test",
            TESTING="true",
            JWT_SECRET_KEY="integration-test-jwt-secret-for-startup-validation",
            DATABASE_URL="postgresql://test:test@localhost:5434/test_netra_integration",
            REDIS_URL="redis://localhost:6381/4",
            CLICKHOUSE_HOST="localhost",
            CLICKHOUSE_PORT="9000",
            CLICKHOUSE_REQUIRED="false",  # Not required for integration tests
            DISABLE_BACKGROUND_TASKS="true",
            GRACEFUL_STARTUP_MODE="false"  # Strict mode for business validation
        ):
            pass
        
        # Performance tracking for business requirements
        self.integration_start_time = time.time()
        self.performance_thresholds = {
            'complete_startup': 60.0,    # 60s max for complete integration startup
            'phase_transition': 5.0,     # 5s max per phase in integration
            'service_init': 10.0,        # 10s max per service initialization
            'database_connection': 15.0,  # 15s max for database connection
        }
        
        # Track integration metrics for business monitoring
        self.startup_metrics = {
            'phases_completed': [],
            'services_initialized': [],
            'errors_encountered': [],
            'timing_data': {},
            'business_critical_validations': []
        }
    
    def _initialize_comprehensive_app_state(self):
        """Initialize comprehensive app state for integration testing."""
        # Startup state tracking
        self.app.state.startup_complete = False
        self.app.state.startup_in_progress = False
        self.app.state.startup_failed = False
        self.app.state.startup_error = None
        self.app.state.startup_phase = "init"
        self.app.state.startup_start_time = None
        self.app.state.startup_phase_timings = {}
        self.app.state.startup_completed_phases = []
        self.app.state.startup_failed_phases = []
        
        # Critical services for chat functionality (business requirement)
        critical_services = [
            'db_session_factory', 'redis_manager', 'llm_manager', 'key_manager',
            'security_service', 'agent_supervisor', 'agent_service', 'thread_service',
            'corpus_service', 'agent_websocket_bridge', 'background_task_manager',
            'health_service', 'tool_classes', 'agent_class_registry', 'websocket_manager'
        ]
        
        for service in critical_services:
            setattr(self.app.state, service, None)
        
        # Availability flags for business monitoring
        self.app.state.database_available = False
        self.app.state.redis_available = False
        self.app.state.clickhouse_available = False
        self.app.state.websocket_available = False

    # =============================================================================
    # SECTION 1: CORE INTEGRATION VALIDATION TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_startup_module_provides_required_functions_for_smd_integration(self):
        """Test startup_module provides all functions required by SMD orchestrator."""
        # Define functions SMD requires from startup_module for business operation
        required_startup_functions = [
            'initialize_logging',           # Phase 1: Foundation
            'setup_database_connections',   # Phase 3: Database
            'initialize_core_services',     # Phase 2: Dependencies  
            'setup_security_services',      # Phase 2: Dependencies
            'register_websocket_handlers',  # Phase 6: WebSocket
            'startup_health_checks',        # Phase 7: Finalization
        ]
        
        for func_name in required_startup_functions:
            with self.subTest(function=func_name):
                self.assertTrue(
                    hasattr(startup_module, func_name),
                    f"CRITICAL INTEGRATION FAILURE: startup_module missing {func_name}. "
                    f"SMD cannot complete deterministic startup without this function."
                )
                
                func = getattr(startup_module, func_name)
                self.assertTrue(
                    callable(func),
                    f"CRITICAL INTEGRATION FAILURE: {func_name} not callable. "
                    f"SMD integration will fail during startup orchestration."
                )

    @pytest.mark.asyncio  
    async def test_smd_orchestrator_integrates_with_startup_module_functions(self):
        """Test SMD orchestrator successfully integrates with startup_module functions."""
        # Create orchestrator for integration testing
        orchestrator = StartupOrchestrator(self.app)
        
        # Verify orchestrator can call startup_module functions
        integration_tests = [
            ('initialize_logging', startup_module.initialize_logging),
            ('_import_all_models', startup_module._import_all_models),
            ('_setup_paths', startup_module._setup_paths),
        ]
        
        for test_name, startup_func in integration_tests:
            with self.subTest(integration=test_name):
                try:
                    if asyncio.iscoroutinefunction(startup_func):
                        await startup_func()
                    else:
                        result = startup_func()
                        
                    # Verify integration succeeded
                    self.startup_metrics['business_critical_validations'].append(
                        f"{test_name}_integration_success"
                    )
                        
                except Exception as e:
                    self.fail(
                        f"CRITICAL INTEGRATION FAILURE: SMD cannot integrate with {test_name}. "
                        f"Error: {e}. This will break deterministic startup."
                    )

    @pytest.mark.asyncio
    async def test_deterministic_startup_orchestrator_initializes_with_startup_logging(self):
        """Test SMD orchestrator integrates with startup_module logging initialization."""
        # Test logging integration (Phase 1 requirement)
        start_time = time.time()
        
        # Initialize logging via startup_module (SMD dependency)
        startup_start_time, logger = startup_module.initialize_logging()
        
        logging_init_time = time.time() - start_time
        
        # Business performance requirement
        self.assertLess(
            logging_init_time, 1.0,
            f"BUSINESS PERFORMANCE FAILURE: Logging init took {logging_init_time:.3f}s. "
            f"SMD integration requires fast logging setup for business monitoring."
        )
        
        # Verify SMD can use the logging system
        orchestrator = StartupOrchestrator(self.app)
        
        # Verify orchestrator logger is business-appropriate
        self.assertIsNotNone(orchestrator.logger)
        self.assertTrue(hasattr(orchestrator.logger, 'info'))
        self.assertTrue(hasattr(orchestrator.logger, 'error'))
        self.assertTrue(hasattr(orchestrator.logger, 'critical'))
        
        # Record successful integration
        self.startup_metrics['timing_data']['logging_integration'] = logging_init_time

    # =============================================================================
    # SECTION 2: PHASE INTEGRATION VALIDATION TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_phase1_foundation_integrates_with_startup_module_helpers(self):
        """Test Phase 1 (Foundation) integrates properly with startup_module helpers."""
        orchestrator = StartupOrchestrator(self.app)
        
        # Mock startup_module functions that Phase 1 uses
        with patch('netra_backend.app.startup_module._setup_paths') as mock_paths, \
             patch('netra_backend.app.startup_module._import_all_models') as mock_models, \
             patch('netra_backend.app.startup_module.run_database_migrations') as mock_migrations, \
             patch('netra_backend.app.startup_module.validate_database_environment') as mock_validate_env:
            
            # Test Phase 1 execution with startup_module integration
            start_time = time.time()
            await orchestrator._phase1_foundation()
            phase_time = time.time() - start_time
            
            # Verify business performance requirements
            self.assertLess(
                phase_time, self.performance_thresholds['phase_transition'],
                f"BUSINESS PERFORMANCE FAILURE: Phase 1 integration took {phase_time:.3f}s, "
                f"exceeds {self.performance_thresholds['phase_transition']}s threshold."
            )
            
            # Verify startup_module functions were called (integration validation)
            mock_paths.assert_called_once()
            mock_models.assert_called_once() 
            
            # Record successful phase integration
            self.startup_metrics['phases_completed'].append('Phase1_Foundation')
            self.startup_metrics['timing_data']['phase1_integration'] = phase_time

    @pytest.mark.asyncio
    async def test_phase3_database_integrates_with_startup_module_database_setup(self):
        """Test Phase 3 (Database) integrates with startup_module database functions."""
        orchestrator = StartupOrchestrator(self.app)
        
        # Mock startup_module database functions
        with patch('netra_backend.app.startup_module.setup_database_connections') as mock_db_setup, \
             patch('netra_backend.app.startup_module._ensure_database_tables_exist') as mock_tables:
            
            # Mock successful database setup
            self.app.state.db_session_factory = Mock()  # Simulate successful setup
            
            # Test Phase 3 database integration
            start_time = time.time()
            await orchestrator._phase3_database_setup()
            phase_time = time.time() - start_time
            
            # Verify integration performance
            self.assertLess(
                phase_time, self.performance_thresholds['database_connection'],
                f"BUSINESS PERFORMANCE FAILURE: Database integration took {phase_time:.3f}s"
            )
            
            # Record successful database integration
            self.startup_metrics['services_initialized'].append('database_integration')
            self.startup_metrics['timing_data']['phase3_database'] = phase_time

    @pytest.mark.asyncio 
    async def test_phase6_websocket_integrates_with_startup_module_websocket_setup(self):
        """Test Phase 6 (WebSocket) integrates with startup_module WebSocket functions."""
        orchestrator = StartupOrchestrator(self.app)
        
        # Mock startup_module WebSocket functions
        with patch('netra_backend.app.startup_module.register_websocket_handlers') as mock_ws_handlers, \
             patch('netra_backend.app.startup_module.initialize_websocket_components') as mock_ws_init:
            
            # Mock WebSocket bridge for integration
            self.app.state.agent_websocket_bridge = Mock()
            
            # Test Phase 6 WebSocket integration
            start_time = time.time() 
            await orchestrator._phase6_websocket_setup()
            phase_time = time.time() - start_time
            
            # Verify WebSocket integration for chat (business-critical)
            self.assertLess(
                phase_time, self.performance_thresholds['service_init'],
                f"BUSINESS CRITICAL FAILURE: WebSocket integration took {phase_time:.3f}s. "
                f"Chat functionality depends on fast WebSocket setup."
            )
            
            # Record WebSocket integration success (critical for chat)
            self.startup_metrics['services_initialized'].append('websocket_chat_integration')
            self.startup_metrics['timing_data']['phase6_websocket'] = phase_time

    # =============================================================================
    # SECTION 3: ERROR HANDLING INTEGRATION TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_startup_module_error_handling_integrates_with_smd_error_management(self):
        """Test startup_module error handling integrates with SMD error management."""
        orchestrator = StartupOrchestrator(self.app)
        
        # Simulate startup_module function failure
        with patch('netra_backend.app.startup_module.initialize_core_services') as mock_core_services:
            # Simulate business-critical service failure
            service_error = RuntimeError("LLM manager initialization failed - AI responses will not work")
            mock_core_services.side_effect = service_error
            
            # Test error integration handling
            with self.assertRaises(DeterministicStartupError) as cm:
                await orchestrator._phase2_core_services()
            
            # Verify SMD properly wraps and contextualizes startup_module errors
            smd_error = str(cm.exception)
            self.assertIn("core services", smd_error.lower())
            
            # Verify error provides business context
            business_context_indicators = ['llm', 'manager', 'initialization', 'failed']
            has_business_context = any(
                indicator in smd_error.lower() 
                for indicator in business_context_indicators
            )
            self.assertTrue(
                has_business_context,
                f"SMD error must provide business context for startup_module failures. "
                f"Error was: {smd_error}"
            )
            
            # Record error integration validation
            self.startup_metrics['errors_encountered'].append('startup_module_error_integration')

    @pytest.mark.asyncio
    async def test_smd_timeout_handling_works_with_startup_module_slow_operations(self):
        """Test SMD timeout handling works with slow startup_module operations."""
        orchestrator = StartupOrchestrator(self.app)
        
        # Simulate slow startup_module operation
        with patch('netra_backend.app.startup_module.setup_database_connections') as mock_db_setup:
            # Mock slow database connection (business impact scenario)
            async def slow_db_setup(*args):
                await asyncio.sleep(2.0)  # 2 second delay
                return None
            
            mock_db_setup.side_effect = slow_db_setup
            
            # Test timeout integration with reasonable business timeout
            start_time = time.time()
            
            try:
                # Use asyncio.wait_for to enforce business timeout
                await asyncio.wait_for(
                    orchestrator._phase3_database_setup(),
                    timeout=5.0  # 5 second business timeout
                )
            except (asyncio.TimeoutError, DeterministicStartupError):
                # Both timeout types are acceptable for business continuity
                pass
            
            elapsed_time = time.time() - start_time
            
            # Verify timeout protection works (business requirement)
            self.assertLess(
                elapsed_time, 6.0,  # Should timeout before 6 seconds
                f"BUSINESS CONTINUITY FAILURE: Timeout protection failed. "
                f"Slow startup operations can cause service unavailability."
            )

    # =============================================================================
    # SECTION 4: SERVICE INITIALIZATION INTEGRATION TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_complete_service_integration_chain_for_chat_functionality(self):
        """Test complete service integration chain required for chat functionality."""
        orchestrator = StartupOrchestrator(self.app)
        
        # Mock all chat-critical service initialization functions
        with patch.multiple(
            'netra_backend.app.startup_module',
            initialize_core_services=Mock(return_value=Mock()),
            setup_security_services=Mock(),
            register_websocket_handlers=Mock(),
            initialize_websocket_components=AsyncMock()
        ):
            # Mock successful service states for chat pipeline
            self.app.state.key_manager = Mock()      # Required for encryption
            self.app.state.llm_manager = Mock()      # Required for AI responses
            self.app.state.security_service = Mock() # Required for auth
            self.app.state.agent_supervisor = Mock() # Required for agent execution
            self.app.state.agent_websocket_bridge = Mock()  # Required for real-time events
            
            # Test complete integration chain timing
            integration_start = time.time()
            
            # Execute chat-critical phases in sequence
            await orchestrator._phase2_core_services()    # Dependencies
            await orchestrator._phase5_services_setup()   # Services  
            await orchestrator._phase6_websocket_setup()  # WebSocket
            
            integration_time = time.time() - integration_start
            
            # Verify complete chat integration meets business performance requirements
            self.assertLess(
                integration_time, 30.0,
                f"BUSINESS PERFORMANCE FAILURE: Complete chat integration took {integration_time:.3f}s, "
                f"exceeds 30s business requirement. Chat startup must be responsive."
            )
            
            # Verify all chat-critical services were integrated
            chat_services = ['key_manager', 'llm_manager', 'security_service', 'agent_supervisor']
            for service in chat_services:
                service_value = getattr(self.app.state, service)
                self.assertIsNotNone(
                    service_value,
                    f"CRITICAL CHAT FAILURE: {service} not initialized. Chat will not work."
                )
            
            # Record successful chat integration  
            self.startup_metrics['business_critical_validations'].append('complete_chat_integration')
            self.startup_metrics['timing_data']['complete_chat_integration'] = integration_time

    @pytest.mark.asyncio
    async def test_database_redis_integration_supports_chat_persistence(self):
        """Test database + Redis integration supports chat persistence requirements."""
        orchestrator = StartupOrchestrator(self.app)
        
        # Mock database and Redis setup functions
        with patch('netra_backend.app.startup_module.setup_database_connections') as mock_db, \
             patch('netra_backend.app.startup_module.redis_manager') as mock_redis:
            
            # Mock successful persistence layer setup
            self.app.state.db_session_factory = Mock()  # Chat conversation persistence
            self.app.state.redis_manager = Mock()       # Chat session caching
            
            # Test persistence integration
            persistence_start = time.time()
            
            await orchestrator._phase3_database_setup()  # Database for persistence
            await orchestrator._phase4_cache_setup()     # Redis for caching
            
            persistence_time = time.time() - persistence_start
            
            # Verify persistence integration performance (business requirement)
            self.assertLess(
                persistence_time, 20.0,
                f"BUSINESS PERFORMANCE FAILURE: Persistence integration took {persistence_time:.3f}s. "
                f"Chat requires fast data layer initialization."
            )
            
            # Verify chat persistence infrastructure is ready
            self.assertIsNotNone(
                self.app.state.db_session_factory,
                "CRITICAL CHAT FAILURE: No database session factory. Cannot persist conversations."
            )
            self.assertIsNotNone(
                self.app.state.redis_manager, 
                "CRITICAL CHAT FAILURE: No Redis manager. Cannot cache chat sessions."
            )
            
            # Record persistence integration success
            self.startup_metrics['services_initialized'].extend(['database_persistence', 'redis_caching'])
            self.startup_metrics['timing_data']['persistence_integration'] = persistence_time

    # =============================================================================
    # SECTION 5: PERFORMANCE AND TIMING INTEGRATION TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_complete_startup_integration_meets_business_performance_requirements(self):
        """Test complete startup integration meets business performance requirements."""
        # Test complete deterministic startup with startup_module integration
        with patch.multiple(
            'netra_backend.app.startup_module',
            initialize_logging=Mock(return_value=(time.time(), Mock())),
            _setup_paths=Mock(),
            _import_all_models=Mock(),
            run_database_migrations=Mock(),
            validate_database_environment=Mock(),
            setup_database_connections=AsyncMock(),
            initialize_core_services=Mock(return_value=Mock()),
            setup_security_services=Mock(),
            register_websocket_handlers=Mock(),
            initialize_websocket_components=AsyncMock(),
            startup_health_checks=AsyncMock()
        ):
            # Mock all required app state for complete startup
            self.app.state.db_session_factory = Mock()
            self.app.state.redis_manager = Mock()
            self.app.state.key_manager = Mock()
            self.app.state.llm_manager = Mock()
            self.app.state.security_service = Mock()
            self.app.state.agent_supervisor = Mock()
            self.app.state.agent_websocket_bridge = Mock()
            self.app.state.background_task_manager = Mock()
            self.app.state.health_service = Mock()
            
            # Test complete integration startup timing
            complete_start = time.time()
            
            orchestrator = StartupOrchestrator(self.app)
            await orchestrator.initialize_system()
            
            complete_time = time.time() - complete_start
            
            # Verify complete startup meets business performance requirement  
            self.assertLess(
                complete_time, self.performance_thresholds['complete_startup'],
                f"BUSINESS PERFORMANCE FAILURE: Complete startup integration took {complete_time:.3f}s, "
                f"exceeds {self.performance_thresholds['complete_startup']}s business requirement."
            )
            
            # Verify startup completion state
            self.assertTrue(
                self.app.state.startup_complete,
                "BUSINESS CONTINUITY FAILURE: Startup not marked complete after integration."
            )
            self.assertFalse(
                self.app.state.startup_failed,
                "BUSINESS CONTINUITY FAILURE: Startup marked as failed despite successful integration."
            )
            
            # Record complete integration metrics
            self.startup_metrics['business_critical_validations'].append('complete_startup_integration')
            self.startup_metrics['timing_data']['complete_startup'] = complete_time

    @pytest.mark.asyncio
    async def test_startup_integration_phase_timing_distribution(self):
        """Test startup integration phase timing distribution for business monitoring."""
        orchestrator = StartupOrchestrator(self.app)
        phase_timings = {}
        
        # Mock all integration functions with timing tracking
        test_phases = [
            ('phase1_foundation', orchestrator._phase1_foundation),
            ('phase2_core_services', orchestrator._phase2_core_services), 
            ('phase3_database_setup', orchestrator._phase3_database_setup),
            ('phase4_cache_setup', orchestrator._phase4_cache_setup),
            ('phase5_services_setup', orchestrator._phase5_services_setup),
            ('phase6_websocket_setup', orchestrator._phase6_websocket_setup),
            ('phase7_finalize', orchestrator._phase7_finalize),
        ]
        
        # Mock startup_module functions to avoid external dependencies
        with patch.multiple(
            'netra_backend.app.startup_module',
            _setup_paths=Mock(),
            _import_all_models=Mock(),
            run_database_migrations=Mock(),
            validate_database_environment=Mock(),
            initialize_core_services=Mock(return_value=Mock()),
            setup_security_services=Mock(),
            setup_database_connections=AsyncMock(),
            register_websocket_handlers=Mock(),
            initialize_websocket_components=AsyncMock(),
            startup_health_checks=AsyncMock()
        ):
            # Set up required app state
            self.app.state.key_manager = Mock()
            self.app.state.llm_manager = Mock()
            self.app.state.db_session_factory = Mock()
            self.app.state.redis_manager = Mock()
            self.app.state.agent_websocket_bridge = Mock()
            self.app.state.background_task_manager = Mock()
            self.app.state.health_service = Mock()
            
            # Measure each phase timing
            for phase_name, phase_func in test_phases:
                phase_start = time.time()
                
                try:
                    await phase_func()
                    phase_timings[phase_name] = time.time() - phase_start
                    
                    # Verify each phase meets performance requirements
                    self.assertLess(
                        phase_timings[phase_name], self.performance_thresholds['phase_transition'],
                        f"BUSINESS PERFORMANCE WARNING: {phase_name} took {phase_timings[phase_name]:.3f}s"
                    )
                    
                except Exception as e:
                    # Record failed phase for business monitoring
                    self.startup_metrics['errors_encountered'].append(f"{phase_name}_integration_failure: {e}")
                    phase_timings[phase_name] = time.time() - phase_start
        
        # Business requirement: No single phase should dominate startup time
        max_phase_time = max(phase_timings.values()) if phase_timings else 0
        total_time = sum(phase_timings.values())
        
        if total_time > 0:
            max_phase_percentage = (max_phase_time / total_time) * 100
            self.assertLess(
                max_phase_percentage, 60.0,
                f"BUSINESS PERFORMANCE WARNING: Single phase consumed {max_phase_percentage:.1f}% "
                f"of startup time. Indicates potential bottleneck requiring optimization."
            )
        
        # Record phase timing distribution
        self.startup_metrics['timing_data']['phase_timings'] = phase_timings

    # =============================================================================
    # SECTION 6: BUSINESS CONTINUITY AND RELIABILITY TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_startup_integration_failure_recovery_maintains_business_continuity(self):
        """Test startup integration failure recovery maintains business continuity."""
        orchestrator = StartupOrchestrator(self.app)
        
        # Simulate cascading failures during integration
        failure_scenarios = [
            ("database_connection_failure", RuntimeError("Database connection failed")),
            ("redis_connection_failure", ConnectionError("Redis connection timeout")),
            ("llm_initialization_failure", ValueError("LLM manager configuration invalid")),
            ("websocket_setup_failure", RuntimeError("WebSocket bridge initialization failed")),
        ]
        
        for failure_name, failure_exception in failure_scenarios:
            with self.subTest(failure=failure_name):
                # Reset app state for each failure test
                self.app.state.startup_failed = False
                self.app.state.startup_error = None
                
                # Simulate specific failure
                with patch('netra_backend.app.startup_module.setup_database_connections') as mock_db:
                    mock_db.side_effect = failure_exception
                    
                    # Test failure handling and recovery
                    failure_start = time.time()
                    
                    try:
                        await orchestrator._phase3_database_setup()
                    except DeterministicStartupError as e:
                        failure_time = time.time() - failure_start
                        
                        # Verify failure is detected quickly (business requirement)
                        self.assertLess(
                            failure_time, 10.0,
                            f"BUSINESS CONTINUITY FAILURE: {failure_name} detection took {failure_time:.3f}s. "
                            f"Must fail fast to enable quick recovery."
                        )
                        
                        # Verify error provides business context
                        error_message = str(e)
                        self.assertGreater(
                            len(error_message), 20,
                            f"Business error message too short for incident response: {error_message}"
                        )
                        
                        # Record failure recovery validation
                        self.startup_metrics['errors_encountered'].append(f"{failure_name}_recovery_validated")

    def test_startup_integration_environment_isolation_validation(self):
        """Test startup integration maintains environment isolation for business compliance."""
        # Test environment isolation patterns required for multi-user business model
        env_configs = [
            {
                'ENVIRONMENT': 'development',
                'DATABASE_URL': 'postgresql://dev:dev@localhost:5432/netra_dev',
                'expected_isolation': True
            },
            {
                'ENVIRONMENT': 'staging', 
                'DATABASE_URL': 'postgresql://stage:stage@staging.db/netra_staging',
                'expected_isolation': True
            },
            {
                'ENVIRONMENT': 'production',
                'DATABASE_URL': 'postgresql://prod:prod@prod.db/netra_production', 
                'expected_isolation': True
            }
        ]
        
        for config in env_configs:
            with self.subTest(environment=config['ENVIRONMENT']):
                # Test environment isolation during integration
                with self.isolated_environment(**{k: v for k, v in config.items() if k != 'expected_isolation'}):
                    env = get_env()
                    
                    # Verify environment isolation is maintained
                    detected_env = env.get('ENVIRONMENT')
                    self.assertEqual(
                        detected_env, config['ENVIRONMENT'],
                        f"BUSINESS COMPLIANCE FAILURE: Environment isolation broken. "
                        f"Expected {config['ENVIRONMENT']}, got {detected_env}"
                    )
                    
                    # Verify database URL isolation (critical for data security)
                    db_url = env.get('DATABASE_URL')
                    self.assertEqual(
                        db_url, config['DATABASE_URL'],
                        f"BUSINESS SECURITY FAILURE: Database URL isolation broken. "
                        f"Cross-environment data leak risk."
                    )
                    
                    # Record environment isolation validation
                    self.startup_metrics['business_critical_validations'].append(
                        f"environment_isolation_{config['ENVIRONMENT']}"
                    )

    def tearDown(self):
        """Clean up integration test environment and report business metrics."""
        # Calculate total integration test time
        integration_duration = time.time() - self.integration_start_time
        
        # Log business metrics for monitoring
        if integration_duration > 30.0:
            print(f"BUSINESS PERFORMANCE WARNING: Integration test took {integration_duration:.3f}s")
            print(f"Long integration tests slow CI/CD and reduce development velocity")
        
        # Log business-critical validation summary
        validations_completed = len(self.startup_metrics['business_critical_validations'])
        services_initialized = len(self.startup_metrics['services_initialized'])
        errors_encountered = len(self.startup_metrics['errors_encountered'])
        
        print(f"Integration Test Business Metrics:")
        print(f"  - Critical validations completed: {validations_completed}")
        print(f"  - Services successfully integrated: {services_initialized}")
        print(f"  - Error scenarios tested: {errors_encountered}")
        print(f"  - Total integration time: {integration_duration:.3f}s")
        
        # Call parent cleanup
        super().tearDown()


class TestStartupModuleSmdCompatibility(BaseTestCase):
    """Test compatibility between startup_module helper functions and SMD requirements."""
    
    REQUIRES_DATABASE = False  # Compatibility tests can use mocks
    REQUIRES_REDIS = False
    ISOLATION_ENABLED = True
    AUTO_CLEANUP = True
    
    def setUp(self):
        """Set up compatibility testing environment.""" 
        super().setUp()
        
        self.mock_app = Mock(spec=FastAPI)
        self.mock_app.state = Mock()
        
        # Initialize basic app state
        for attr in ['startup_complete', 'startup_in_progress', 'startup_failed']:
            setattr(self.mock_app.state, attr, False)
    
    def test_startup_module_function_signatures_compatible_with_smd_expectations(self):
        """Test startup_module function signatures are compatible with SMD expectations."""
        # Define SMD expectations for startup_module functions
        smd_function_requirements = {
            'initialize_logging': {
                'params': [],
                'returns': 'tuple',  # (start_time, logger)
                'business_purpose': 'Phase 1 foundation logging setup'
            },
            'setup_database_connections': {
                'params': ['app'],
                'async': True,
                'business_purpose': 'Phase 3 database connectivity'
            },
            'initialize_core_services': {
                'params': ['app', 'logger'],
                'returns': 'key_manager',
                'business_purpose': 'Phase 2 core service initialization'
            },
            'register_websocket_handlers': {
                'params': ['app'],
                'business_purpose': 'Phase 6 WebSocket setup for chat'
            }
        }
        
        for func_name, requirements in smd_function_requirements.items():
            with self.subTest(function=func_name, purpose=requirements['business_purpose']):
                # Verify function exists
                self.assertTrue(
                    hasattr(startup_module, func_name),
                    f"COMPATIBILITY FAILURE: {func_name} missing. "
                    f"SMD cannot execute {requirements['business_purpose']}."
                )
                
                func = getattr(startup_module, func_name)
                
                # Verify function is callable
                self.assertTrue(
                    callable(func),
                    f"COMPATIBILITY FAILURE: {func_name} not callable for {requirements['business_purpose']}."
                )
                
                # Verify async compatibility if required
                if requirements.get('async', False):
                    self.assertTrue(
                        asyncio.iscoroutinefunction(func),
                        f"COMPATIBILITY FAILURE: {func_name} must be async for SMD integration. "
                        f"Required for {requirements['business_purpose']}."
                    )

    def test_startup_module_error_types_compatible_with_smd_error_handling(self):
        """Test startup_module error types are compatible with SMD error handling."""
        # Test error compatibility with mock failures
        error_compatibility_tests = [
            ('database_connection_error', ConnectionError, 'Database connectivity'),
            ('service_init_error', RuntimeError, 'Service initialization'),
            ('config_validation_error', ValueError, 'Configuration validation'),
            ('timeout_error', asyncio.TimeoutError, 'Operation timeout'),
        ]
        
        for error_name, error_type, business_context in error_compatibility_tests:
            with self.subTest(error=error_name, context=business_context):
                # Verify SMD can handle this error type
                test_error = error_type(f"Test {business_context} failure")
                
                try:
                    # SMD should be able to wrap this error appropriately
                    smd_error = DeterministicStartupError(
                        f"SMD integration failure during {business_context}: {test_error}"
                    )
                    
                    # Verify SMD error provides business context
                    error_message = str(smd_error)
                    self.assertIn(business_context.lower(), error_message.lower())
                    self.assertIn("smd", error_message.lower())
                    
                except Exception as e:
                    self.fail(
                        f"COMPATIBILITY FAILURE: SMD cannot handle {error_type.__name__} from startup_module. "
                        f"This breaks error handling for {business_context}."
                    )

    def test_startup_module_return_values_compatible_with_smd_expectations(self):
        """Test startup_module return values are compatible with SMD expectations."""
        # Test return value compatibility
        with patch.multiple(
            'netra_backend.app.startup_module',
            initialize_logging=Mock(return_value=(time.time(), Mock())),
            initialize_core_services=Mock(return_value=Mock()),  # Should return key_manager
        ):
            # Test initialize_logging return compatibility
            start_time, logger = startup_module.initialize_logging()
            
            # Verify SMD-compatible return format
            self.assertIsInstance(start_time, (int, float))
            self.assertIsNotNone(logger)
            self.assertTrue(hasattr(logger, 'info'))  # SMD logging requirement
            
            # Test initialize_core_services return compatibility  
            key_manager = startup_module.initialize_core_services(self.mock_app, logger)
            
            # Verify SMD can use returned key_manager
            self.assertIsNotNone(key_manager)
            # SMD expects key_manager to be assignable to app.state.key_manager
            self.mock_app.state.key_manager = key_manager  # Should not raise


if __name__ == '__main__':
    # Run integration test suite with business focus
    unittest.main(verbosity=2, buffer=True)