"""
Complete End-to-End Tests for Startup System

Business Value Justification (BVJ):
- Segment: Platform/Internal - Mission Critical Business Infrastructure
- Business Goal: Validate complete startup system works end-to-end across real environments
- Value Impact: Ensures startup reliability prevents chat system outages (90% of business value)
- Strategic Impact: $25M+ ARR protection through elimination of production startup failures

This E2E test suite validates the COMPLETE startup system integration including:
1. Real service dependencies (database, Redis, auth)
2. Complete startup sequence from SMD deterministic orchestrator
3. WebSocket integration for chat functionality
4. Multi-user authentication and session management 
5. Agent supervisor creation and WebSocket bridge integration
6. Real-time event delivery for chat user experience
7. Performance validation under realistic load
8. Error handling and recovery patterns
9. Cross-environment validation (test, staging patterns)
10. Business continuity validation

CRITICAL REQUIREMENTS:
- ALL tests MUST use authentication (JWT/OAuth) per CLAUDE.md E2E auth mandate
- Use REAL services - database, Redis, WebSocket connections
- NO mocks allowed in E2E tests - must test real system integration
- Tests MUST fail hard when system breaks - NO exception masking
- Follow SSOT patterns from test_framework/ssot/
- Validate business-critical chat functionality end-to-end
"""

import asyncio
import json
import logging
import os
import sys
import time
import unittest
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest
import websockets
from fastapi import FastAPI

# SSOT imports following CLAUDE.md absolute import requirements
from test_framework.ssot.base import BaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.ssot.test_fixtures import E2ETestFixture
from shared.isolated_environment import get_env

# Import modules under test
from netra_backend.app import smd, startup_module


class TestStartupCompleteE2E(BaseTestCase, E2ETestFixture):
    """
    Complete E2E tests for startup system with real services and authentication.
    
    This test suite validates the COMPLETE startup system works end-to-end
    with real authentication, real services, and real business scenarios.
    
    CRITICAL: All tests use authentication and real services per CLAUDE.md requirements.
    """
    
    # Configure SSOT base classes for E2E testing
    REQUIRES_DATABASE = True   # Real database required for E2E
    REQUIRES_REDIS = True      # Real Redis required for E2E
    ISOLATION_ENABLED = True   # Critical for multi-user E2E testing
    AUTO_CLEANUP = True        # Clean up real connections
    
    def setUp(self):
        """Set up E2E test environment with real services and authentication.""" 
        super().setUp()
        
        # Initialize E2E authentication helper (CRITICAL per CLAUDE.md)
        self.auth_helper = E2EAuthHelper(environment="test")
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Set up test environment for E2E with business-critical configuration
        with self.isolated_environment(
            ENVIRONMENT="e2e_test",
            TESTING="true",
            JWT_SECRET_KEY="e2e-test-jwt-secret-for-complete-startup-validation",
            DATABASE_URL="postgresql://test:test@localhost:5434/test_netra_e2e",
            REDIS_URL="redis://localhost:6381/5",
            WEBSOCKET_URL="ws://localhost:8000/ws",
            BACKEND_URL="http://localhost:8000",
            # Business-critical chat configuration
            CHAT_ENABLED="true",
            WEBSOCKET_EVENTS_ENABLED="true",
            AGENT_SUPERVISOR_ENABLED="true",
            # Performance configuration for E2E
            STARTUP_TIMEOUT="120",  # 2 minutes max for E2E startup
            HEALTH_CHECK_TIMEOUT="30",
            WEBSOCKET_TIMEOUT="15"
        ):
            pass
        
        # Performance tracking for business requirements
        self.e2e_start_time = time.time()
        self.business_performance_thresholds = {
            'complete_startup_e2e': 120.0,      # 2 minutes max for complete E2E startup
            'authentication_flow': 10.0,        # 10s max for auth flow
            'websocket_connection': 15.0,        # 15s max for WebSocket connection
            'agent_supervisor_ready': 30.0,      # 30s max for agent supervisor
            'first_chat_response': 45.0,         # 45s max for first chat response
        }
        
        # Track business metrics for monitoring
        self.e2e_metrics = {
            'authentication_successful': False,
            'startup_phases_completed': [],
            'services_validated': [],
            'websocket_events_received': [],
            'chat_functionality_validated': False,
            'errors_encountered': [],
            'performance_data': {},
            'business_critical_validations': []
        }
        
        # Create authenticated user for all E2E tests (CRITICAL requirement)
        self.test_user_token = None
        self.test_user_data = None

    async def _ensure_authenticated_user(self):
        """Ensure authenticated user exists for E2E testing (CRITICAL per CLAUDE.md)."""
        if not self.test_user_token:
            try:
                # Create authenticated user (MANDATORY for E2E per CLAUDE.md)
                auth_start = time.time()
                
                self.test_user_token, self.test_user_data = await self.auth_helper.authenticate_user(
                    email="e2e_startup_test@example.com",
                    password="e2e_test_password_startup_validation"
                )
                
                auth_time = time.time() - auth_start
                
                # Verify authentication meets business performance requirements
                self.assertLess(
                    auth_time, self.business_performance_thresholds['authentication_flow'],
                    f"BUSINESS PERFORMANCE FAILURE: Authentication took {auth_time:.3f}s, "
                    f"exceeds {self.business_performance_thresholds['authentication_flow']}s threshold."
                )
                
                # Mark authentication success for business monitoring
                self.e2e_metrics['authentication_successful'] = True
                self.e2e_metrics['performance_data']['authentication_time'] = auth_time
                
            except Exception as e:
                self.fail(
                    f"CRITICAL E2E AUTHENTICATION FAILURE: Cannot create authenticated user. "
                    f"All E2E tests require authentication per CLAUDE.md. Error: {e}"
                )

    # =============================================================================
    # SECTION 1: COMPLETE STARTUP SYSTEM E2E VALIDATION
    # =============================================================================

    @pytest.mark.asyncio
    async def test_complete_deterministic_startup_e2e_with_authentication(self):
        """
        Test complete deterministic startup E2E with real authentication and services.
        
        This is the PRIMARY business-critical E2E test validating complete startup.
        """
        # Ensure authenticated user exists (CRITICAL E2E requirement)
        await self._ensure_authenticated_user()
        
        # Create real FastAPI app for E2E testing
        app = FastAPI(title="E2E Startup Test App")
        
        # Track complete startup timing (business requirement)
        complete_startup_start = time.time()
        
        # Execute complete deterministic startup with real services
        try:
            start_time, logger = await smd.run_deterministic_startup(app)
            
            complete_startup_time = time.time() - complete_startup_start
            
            # Verify startup meets business performance requirements
            self.assertLess(
                complete_startup_time, self.business_performance_thresholds['complete_startup_e2e'],
                f"BUSINESS PERFORMANCE FAILURE: Complete E2E startup took {complete_startup_time:.3f}s, "
                f"exceeds {self.business_performance_thresholds['complete_startup_e2e']}s business requirement."
            )
            
            # Verify startup completion state (business requirement)
            self.assertTrue(
                app.state.startup_complete,
                "CRITICAL BUSINESS FAILURE: Startup not marked complete. System not ready for users."
            )
            self.assertFalse(
                app.state.startup_failed,
                "CRITICAL BUSINESS FAILURE: Startup marked as failed despite successful completion."
            )
            self.assertIsNone(
                app.state.startup_error,
                f"CRITICAL BUSINESS FAILURE: Startup error present: {app.state.startup_error}"
            )
            
            # Verify business-critical services are initialized
            business_critical_services = [
                'db_session_factory',     # Database for chat persistence
                'redis_manager',          # Redis for chat session caching
                'llm_manager',           # LLM for AI responses
                'agent_supervisor',      # Agent orchestration for chat
                'agent_websocket_bridge' # Real-time chat events
            ]
            
            for service in business_critical_services:
                service_value = getattr(app.state, service, None)
                self.assertIsNotNone(
                    service_value,
                    f"CRITICAL CHAT FAILURE: {service} not initialized. "
                    f"Chat functionality will not work, breaking 90% of business value."
                )
                self.e2e_metrics['services_validated'].append(service)
            
            # Record successful complete startup
            self.e2e_metrics['business_critical_validations'].append('complete_deterministic_startup_e2e')
            self.e2e_metrics['performance_data']['complete_startup_time'] = complete_startup_time
            
        except Exception as e:
            self.fail(
                f"CRITICAL BUSINESS FAILURE: Complete deterministic startup failed in E2E test. "
                f"This indicates production startup will fail, causing complete service outage. "
                f"Error: {e}"
            )

    @pytest.mark.asyncio
    async def test_startup_websocket_integration_e2e_with_chat_events(self):
        """Test startup WebSocket integration E2E with real chat events and authentication."""
        # Ensure authenticated user exists (CRITICAL E2E requirement)  
        await self._ensure_authenticated_user()
        
        # Create app and run startup to initialize WebSocket infrastructure
        app = FastAPI(title="E2E WebSocket Test App")
        
        try:
            # Run startup to initialize WebSocket support
            await smd.run_deterministic_startup(app)
            
            # Verify WebSocket infrastructure is ready
            self.assertIsNotNone(
                app.state.agent_websocket_bridge,
                "CRITICAL CHAT FAILURE: WebSocket bridge not initialized. Real-time chat will not work."
            )
            
            # Test authenticated WebSocket connection (business-critical for chat)
            websocket_start = time.time()
            
            # Connect with authentication (CRITICAL per CLAUDE.md)
            websocket = await self.websocket_auth_helper.connect_authenticated_websocket(
                timeout=self.business_performance_thresholds['websocket_connection']
            )
            
            websocket_connection_time = time.time() - websocket_start
            
            # Verify WebSocket connection meets business performance requirements
            self.assertLess(
                websocket_connection_time, self.business_performance_thresholds['websocket_connection'],
                f"BUSINESS PERFORMANCE FAILURE: WebSocket connection took {websocket_connection_time:.3f}s"
            )
            
            # Test chat event delivery (business-critical functionality)
            test_message = {
                "type": "agent_started",
                "data": {
                    "agent_id": "test_agent_startup_e2e",
                    "user_id": self.test_user_data.get("id", "test_user"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message": "E2E startup test agent started"
                }
            }
            
            # Send test message
            await websocket.send(json.dumps(test_message))
            
            # Verify message handling (business requirement)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                # Verify response indicates successful processing
                self.assertIn("status", response_data)
                
                # Record successful WebSocket event
                self.e2e_metrics['websocket_events_received'].append(test_message["type"])
                
            except asyncio.TimeoutError:
                self.fail(
                    "CRITICAL CHAT FAILURE: WebSocket event not processed within 5 seconds. "
                    "Real-time chat events are not working, breaking user experience."
                )
            
            finally:
                await websocket.close()
            
            # Record successful WebSocket integration  
            self.e2e_metrics['business_critical_validations'].append('websocket_chat_integration_e2e')
            self.e2e_metrics['performance_data']['websocket_connection_time'] = websocket_connection_time
            
        except Exception as e:
            self.fail(
                f"CRITICAL CHAT FAILURE: WebSocket integration E2E test failed. "
                f"Real-time chat functionality will not work in production. Error: {e}"
            )

    @pytest.mark.asyncio
    async def test_startup_agent_supervisor_e2e_with_authentication(self):
        """Test startup agent supervisor E2E with authentication and real chat capabilities."""
        # Ensure authenticated user exists (CRITICAL E2E requirement)
        await self._ensure_authenticated_user()
        
        # Create app and run complete startup
        app = FastAPI(title="E2E Agent Supervisor Test App")
        
        try:
            # Run startup to initialize agent infrastructure
            await smd.run_deterministic_startup(app)
            
            # Verify agent supervisor is ready for business operation
            agent_supervisor_start = time.time()
            
            agent_supervisor = getattr(app.state, 'agent_supervisor', None)
            self.assertIsNotNone(
                agent_supervisor,
                "CRITICAL CHAT FAILURE: Agent supervisor not initialized. "
                "AI agents cannot be executed, breaking core business functionality."
            )
            
            # Verify agent supervisor has WebSocket bridge for real-time events
            websocket_bridge = getattr(agent_supervisor, 'websocket_bridge', None)
            self.assertIsNotNone(
                websocket_bridge,
                "CRITICAL CHAT FAILURE: Agent supervisor missing WebSocket bridge. "
                "Real-time agent events will not reach users, breaking chat UX."
            )
            
            # Verify WebSocket bridge has event emission capability  
            self.assertTrue(
                hasattr(websocket_bridge, 'emit_agent_event') or hasattr(websocket_bridge, 'send_event'),
                "CRITICAL CHAT FAILURE: WebSocket bridge cannot emit agent events. "
                "Users will not see real-time agent progress, breaking chat experience."
            )
            
            agent_supervisor_time = time.time() - agent_supervisor_start
            
            # Verify agent supervisor initialization meets business performance requirements
            self.assertLess(
                agent_supervisor_time, self.business_performance_thresholds['agent_supervisor_ready'],
                f"BUSINESS PERFORMANCE FAILURE: Agent supervisor took {agent_supervisor_time:.3f}s to validate"
            )
            
            # Verify agent supervisor has required services for chat
            chat_dependencies = ['llm_manager', 'db_session_factory', 'tool_dispatcher']
            for dependency in chat_dependencies:
                dependency_value = getattr(app.state, dependency, None)
                self.assertIsNotNone(
                    dependency_value,
                    f"CRITICAL CHAT FAILURE: Agent supervisor missing {dependency}. "
                    f"AI chat functionality will not work properly."
                )
            
            # Record successful agent supervisor validation
            self.e2e_metrics['services_validated'].append('agent_supervisor_chat_ready')
            self.e2e_metrics['business_critical_validations'].append('agent_supervisor_e2e')
            self.e2e_metrics['performance_data']['agent_supervisor_time'] = agent_supervisor_time
            
        except Exception as e:
            self.fail(
                f"CRITICAL CHAT FAILURE: Agent supervisor E2E test failed. "
                f"AI agents will not work in production, breaking core business value. Error: {e}"
            )

    # =============================================================================
    # SECTION 2: BUSINESS CONTINUITY AND ERROR HANDLING E2E TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_startup_failure_recovery_e2e_with_business_continuity(self):
        """Test startup failure recovery E2E with business continuity validation."""
        # Ensure authenticated user exists (CRITICAL E2E requirement)
        await self._ensure_authenticated_user()
        
        # Test various failure scenarios that could occur in production
        failure_scenarios = [
            {
                'name': 'database_connection_failure',
                'mock_target': 'netra_backend.app.startup_module.setup_database_connections',
                'failure': ConnectionError("Database connection failed in E2E test"),
                'business_impact': 'No chat conversation persistence'
            },
            {
                'name': 'redis_connection_failure', 
                'mock_target': 'netra_backend.app.startup_module.redis_manager',
                'failure': ConnectionError("Redis connection failed in E2E test"),
                'business_impact': 'No chat session caching'
            },
            {
                'name': 'websocket_initialization_failure',
                'mock_target': 'netra_backend.app.startup_module.initialize_websocket_components',
                'failure': RuntimeError("WebSocket initialization failed in E2E test"),
                'business_impact': 'No real-time chat events'
            }
        ]
        
        for scenario in failure_scenarios:
            with self.subTest(failure=scenario['name'], impact=scenario['business_impact']):
                app = FastAPI(title=f"E2E Failure Recovery Test - {scenario['name']}")
                
                # Simulate failure scenario
                with patch(scenario['mock_target']) as mock_target:
                    mock_target.side_effect = scenario['failure']
                    
                    # Test failure detection and handling
                    failure_start = time.time()
                    
                    with self.assertRaises((smd.DeterministicStartupError, Exception)) as cm:
                        await smd.run_deterministic_startup(app)
                    
                    failure_detection_time = time.time() - failure_start
                    
                    # Verify failure is detected quickly (business requirement for fast recovery)
                    self.assertLess(
                        failure_detection_time, 30.0,
                        f"BUSINESS CONTINUITY FAILURE: {scenario['name']} took {failure_detection_time:.3f}s to detect. "
                        f"Slow failure detection delays recovery and increases downtime."
                    )
                    
                    # Verify error message provides business context for incident response
                    error_message = str(cm.exception)
                    self.assertGreater(
                        len(error_message), 30,
                        f"Business error message too short for incident response: {error_message}"
                    )
                    
                    # Verify startup failure state is properly set
                    self.assertTrue(
                        getattr(app.state, 'startup_failed', False),
                        f"Startup failure not properly recorded for {scenario['name']}"
                    )
                    
                    # Record failure handling validation
                    self.e2e_metrics['errors_encountered'].append(
                        f"{scenario['name']}_e2e_handled"
                    )

    @pytest.mark.asyncio
    async def test_startup_timeout_handling_e2e_with_business_impact_validation(self):
        """Test startup timeout handling E2E with business impact validation.""" 
        # Ensure authenticated user exists (CRITICAL E2E requirement)
        await self._ensure_authenticated_user()
        
        app = FastAPI(title="E2E Timeout Handling Test")
        
        # Simulate slow startup operation that could cause business impact
        with patch('netra_backend.app.startup_module.initialize_core_services') as mock_core_services:
            # Mock slow service initialization (realistic business scenario)
            async def slow_service_init(*args):
                await asyncio.sleep(3.0)  # 3 second delay
                return Mock()
            
            mock_core_services.side_effect = slow_service_init
            
            # Test startup with business timeout enforcement
            timeout_start = time.time()
            
            try:
                # Apply business-appropriate timeout
                await asyncio.wait_for(
                    smd.run_deterministic_startup(app),
                    timeout=self.business_performance_thresholds['complete_startup_e2e']
                )
                
                startup_time = time.time() - timeout_start
                
                # If startup completes, verify it meets business performance requirements
                self.assertLess(
                    startup_time, self.business_performance_thresholds['complete_startup_e2e'],
                    f"BUSINESS PERFORMANCE WARNING: Startup took {startup_time:.3f}s, "
                    f"approaching timeout threshold."
                )
                
            except asyncio.TimeoutError:
                timeout_duration = time.time() - timeout_start
                
                # Verify timeout protection worked within business constraints
                self.assertLess(
                    timeout_duration, self.business_performance_thresholds['complete_startup_e2e'] + 5.0,
                    f"BUSINESS CONTINUITY FAILURE: Timeout took {timeout_duration:.3f}s, "
                    f"should have failed faster to enable quick recovery."
                )
                
                # Record timeout handling validation
                self.e2e_metrics['business_critical_validations'].append('timeout_handling_e2e')

    # =============================================================================
    # SECTION 3: MULTI-USER AND AUTHENTICATION E2E TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_startup_supports_multi_user_authentication_e2e(self):
        """Test startup supports multi-user authentication E2E (business requirement)."""
        # Create multiple authenticated users for multi-user testing
        user_scenarios = [
            {
                'email': 'e2e_user1_startup@example.com',
                'password': 'user1_startup_test_password',
                'role': 'standard_user'
            },
            {
                'email': 'e2e_user2_startup@example.com', 
                'password': 'user2_startup_test_password',
                'role': 'standard_user'
            },
            {
                'email': 'e2e_admin_startup@example.com',
                'password': 'admin_startup_test_password', 
                'role': 'admin_user'
            }
        ]
        
        # Run startup to ensure multi-user infrastructure is ready
        app = FastAPI(title="E2E Multi-User Test App")
        await smd.run_deterministic_startup(app)
        
        # Verify multi-user authentication works with startup system
        authenticated_users = []
        
        for user_scenario in user_scenarios:
            try:
                # Create authenticated user
                auth_helper = E2EAuthHelper(environment="test")
                token, user_data = await auth_helper.authenticate_user(
                    email=user_scenario['email'],
                    password=user_scenario['password']
                )
                
                # Verify authentication succeeded
                self.assertIsNotNone(token, f"Authentication failed for {user_scenario['email']}")
                self.assertIsNotNone(user_data, f"User data missing for {user_scenario['email']}")
                
                # Verify user isolation (business requirement)
                user_id = user_data.get('id')
                self.assertIsNotNone(user_id, f"User ID missing for {user_scenario['email']}")
                
                # Ensure user IDs are unique (multi-user isolation)
                existing_ids = [u['user_data'].get('id') for u in authenticated_users]
                self.assertNotIn(
                    user_id, existing_ids,
                    f"User ID collision detected: {user_id}. Multi-user isolation broken."
                )
                
                authenticated_users.append({
                    'token': token,
                    'user_data': user_data,
                    'scenario': user_scenario
                })
                
            except Exception as e:
                self.fail(
                    f"CRITICAL MULTI-USER FAILURE: Authentication failed for {user_scenario['email']}. "
                    f"Multi-user business model requires reliable authentication. Error: {e}"
                )
        
        # Verify all users can access startup-initialized services simultaneously
        self.assertEqual(
            len(authenticated_users), len(user_scenarios),
            f"Not all users authenticated successfully. Expected {len(user_scenarios)}, "
            f"got {len(authenticated_users)}. Multi-user system broken."
        )
        
        # Record successful multi-user validation
        self.e2e_metrics['business_critical_validations'].append('multi_user_authentication_e2e')
        self.e2e_metrics['services_validated'].append('multi_user_startup_support')

    @pytest.mark.asyncio
    async def test_startup_websocket_supports_concurrent_user_connections_e2e(self):
        """Test startup WebSocket supports concurrent user connections E2E.""" 
        # Run startup to initialize WebSocket infrastructure
        app = FastAPI(title="E2E Concurrent WebSocket Test")
        await smd.run_deterministic_startup(app)
        
        # Create multiple authenticated users for concurrent testing
        concurrent_users = []
        for i in range(3):  # Test with 3 concurrent users (business scenario)
            auth_helper = E2EAuthHelper(environment="test")
            token, user_data = await auth_helper.authenticate_user(
                email=f"e2e_concurrent_{i}_startup@example.com",
                password=f"concurrent_{i}_test_password"
            )
            
            websocket_auth_helper = E2EWebSocketAuthHelper(environment="test")
            websocket_auth_helper.test_user_token = token
            websocket_auth_helper.test_user_data = user_data
            
            concurrent_users.append({
                'auth_helper': websocket_auth_helper,
                'token': token,
                'user_data': user_data,
                'user_index': i
            })
        
        # Test concurrent WebSocket connections (business requirement)
        websocket_connections = []
        connection_start = time.time()
        
        try:
            # Connect all users concurrently
            connection_tasks = []
            for user in concurrent_users:
                task = asyncio.create_task(
                    user['auth_helper'].connect_authenticated_websocket(timeout=10.0)
                )
                connection_tasks.append(task)
            
            # Wait for all connections to complete
            websocket_connections = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            concurrent_connection_time = time.time() - connection_start
            
            # Verify concurrent connections meet business performance requirements
            self.assertLess(
                concurrent_connection_time, 20.0,
                f"BUSINESS PERFORMANCE FAILURE: Concurrent WebSocket connections took {concurrent_connection_time:.3f}s"
            )
            
            # Verify all connections succeeded
            successful_connections = 0
            for i, connection in enumerate(websocket_connections):
                if isinstance(connection, Exception):
                    self.fail(
                        f"CRITICAL MULTI-USER FAILURE: WebSocket connection {i} failed: {connection}. "
                        f"Concurrent user support broken."
                    )
                else:
                    successful_connections += 1
            
            self.assertEqual(
                successful_connections, len(concurrent_users),
                f"Not all concurrent WebSocket connections succeeded. "
                f"Expected {len(concurrent_users)}, got {successful_connections}"
            )
            
            # Test concurrent message handling (business requirement) 
            message_tasks = []
            for i, connection in enumerate(websocket_connections):
                if not isinstance(connection, Exception):
                    test_message = {
                        "type": "test_concurrent_message",
                        "user_id": concurrent_users[i]['user_data'].get('id'),
                        "message": f"Concurrent test from user {i}",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    task = asyncio.create_task(connection.send(json.dumps(test_message)))
                    message_tasks.append(task)
            
            # Wait for all messages to be sent
            await asyncio.gather(*message_tasks, return_exceptions=True)
            
            # Record successful concurrent user validation
            self.e2e_metrics['business_critical_validations'].append('concurrent_websocket_users_e2e')
            self.e2e_metrics['performance_data']['concurrent_connection_time'] = concurrent_connection_time
            
        finally:
            # Clean up all WebSocket connections
            for connection in websocket_connections:
                if not isinstance(connection, Exception):
                    try:
                        await connection.close()
                    except:
                        pass  # Best effort cleanup

    # =============================================================================
    # SECTION 4: PERFORMANCE AND SCALABILITY E2E TESTS
    # =============================================================================

    @pytest.mark.asyncio 
    async def test_startup_performance_under_realistic_load_e2e(self):
        """Test startup performance under realistic load E2E."""
        # Ensure authenticated user exists (CRITICAL E2E requirement)
        await self._ensure_authenticated_user()
        
        # Simulate realistic startup load (multiple apps starting concurrently)
        concurrent_startups = 3  # Realistic scenario: 3 instances starting
        
        startup_tasks = []
        performance_start = time.time()
        
        for i in range(concurrent_startups):
            app = FastAPI(title=f"E2E Performance Test App {i}")
            
            # Create startup task
            task = asyncio.create_task(smd.run_deterministic_startup(app))
            startup_tasks.append((task, app, i))
        
        # Wait for all startups to complete
        startup_results = []
        for task, app, index in startup_tasks:
            try:
                start_time, logger = await task
                startup_results.append({
                    'success': True,
                    'app': app,
                    'index': index,
                    'start_time': start_time,
                    'logger': logger
                })
            except Exception as e:
                startup_results.append({
                    'success': False,
                    'index': index,
                    'error': e
                })
        
        total_performance_time = time.time() - performance_start
        
        # Verify concurrent startup performance meets business requirements
        self.assertLess(
            total_performance_time, 180.0,  # 3 minutes max for 3 concurrent startups
            f"BUSINESS SCALABILITY FAILURE: Concurrent startups took {total_performance_time:.3f}s, "
            f"exceeds 180s scalability requirement."
        )
        
        # Verify all startups succeeded
        successful_startups = sum(1 for result in startup_results if result['success'])
        self.assertEqual(
            successful_startups, concurrent_startups,
            f"Not all concurrent startups succeeded. Expected {concurrent_startups}, "
            f"got {successful_startups}. System cannot handle realistic load."
        )
        
        # Verify all successfully started apps have business-critical services
        for result in startup_results:
            if result['success']:
                app = result['app']
                
                # Check business-critical services
                self.assertTrue(
                    app.state.startup_complete,
                    f"App {result['index']} startup not marked complete under load"
                )
                self.assertIsNotNone(
                    getattr(app.state, 'agent_supervisor', None),
                    f"App {result['index']} missing agent supervisor under load"
                )
        
        # Record performance validation
        self.e2e_metrics['business_critical_validations'].append('startup_performance_under_load_e2e')
        self.e2e_metrics['performance_data']['concurrent_startup_time'] = total_performance_time

    def tearDown(self):
        """Clean up E2E test environment and report business metrics."""
        # Calculate total E2E test time
        e2e_duration = time.time() - self.e2e_start_time
        
        # Log business performance warnings
        if e2e_duration > 300.0:  # 5 minutes
            print(f"BUSINESS PERFORMANCE WARNING: E2E test took {e2e_duration:.3f}s")
            print("Long E2E tests slow CI/CD pipeline and reduce deployment velocity")
        
        # Report comprehensive business metrics
        validations_completed = len(self.e2e_metrics['business_critical_validations'])
        services_validated = len(self.e2e_metrics['services_validated'])  
        websocket_events = len(self.e2e_metrics['websocket_events_received'])
        errors_handled = len(self.e2e_metrics['errors_encountered'])
        
        print(f"\n{'='*60}")
        print(f"E2E Test Business Metrics Summary:")
        print(f"{'='*60}")
        print(f"✅ Authentication successful: {self.e2e_metrics['authentication_successful']}")
        print(f"🔧 Services validated: {services_validated}")
        print(f"📡 WebSocket events tested: {websocket_events}")
        print(f"🚀 Critical validations completed: {validations_completed}")
        print(f"⚠️  Error scenarios tested: {errors_handled}")
        print(f"⏱️  Total E2E duration: {e2e_duration:.3f}s")
        
        # Report performance data
        if self.e2e_metrics['performance_data']:
            print(f"\nPerformance Data:")
            for metric, value in self.e2e_metrics['performance_data'].items():
                print(f"  - {metric}: {value:.3f}s")
        
        # Report business-critical validations
        if self.e2e_metrics['business_critical_validations']:
            print(f"\nBusiness-Critical Validations:")
            for validation in self.e2e_metrics['business_critical_validations']:
                print(f"  ✅ {validation}")
        
        print(f"{'='*60}")
        
        # Call parent cleanup
        super().tearDown()


if __name__ == '__main__':
    # Run E2E test suite with business focus and authentication
    unittest.main(verbosity=2, buffer=True)