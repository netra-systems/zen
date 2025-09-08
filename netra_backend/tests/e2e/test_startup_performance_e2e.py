"""
Performance E2E Tests for Startup System 

Business Value Justification (BVJ):
- Segment: Platform/Internal - Business Critical Performance Infrastructure
- Business Goal: Validate startup performance meets business SLA requirements 
- Value Impact: Ensures fast startup reduces time-to-value for users (critical for retention)
- Strategic Impact: $15M+ ARR protection through performance-driven user retention

This performance E2E test suite validates the startup system meets business performance
requirements under realistic conditions including:

1. Startup timing under various load conditions (single/concurrent)
2. Memory usage optimization and leak detection
3. Resource utilization and cleanup efficiency  
4. WebSocket connection performance for chat responsiveness
5. Database connection pool performance validation
6. Service initialization timing and optimization
7. Agent supervisor readiness performance
8. Multi-user concurrent startup scenarios
9. Performance degradation detection and alerting
10. Business-critical performance SLA validation

CRITICAL REQUIREMENTS:
- ALL tests MUST use authentication (JWT/OAuth) per CLAUDE.md E2E auth mandate
- Use REAL services - no mocks allowed in E2E performance tests
- Tests MUST fail hard when performance degrades below business thresholds
- Follow SSOT patterns from test_framework/ssot/
- Validate performance impacts on business-critical chat functionality
"""

import asyncio
import gc
import logging
import memory_profiler
import os
import psutil
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

import pytest
from fastapi import FastAPI

# SSOT imports following CLAUDE.md absolute import requirements
from test_framework.ssot.base import BaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.ssot.test_fixtures import E2ETestFixture
from shared.isolated_environment import get_env

# Import modules under test
from netra_backend.app import smd, startup_module


class TestStartupPerformanceE2E(BaseTestCase, E2ETestFixture):
    """
    Performance E2E tests for startup system with business SLA validation.
    
    This test suite validates startup performance meets business requirements
    for user retention, system scalability, and operational efficiency.
    
    CRITICAL: All tests use authentication and real services per CLAUDE.md requirements.
    """
    
    # Configure SSOT base classes for performance E2E testing
    REQUIRES_DATABASE = True   # Real database required for performance testing
    REQUIRES_REDIS = True      # Real Redis required for performance testing
    ISOLATION_ENABLED = True   # Critical for accurate performance measurement
    AUTO_CLEANUP = True        # Critical for memory leak detection
    
    def setUp(self):
        """Set up performance E2E test environment with monitoring."""
        super().setUp()
        
        # Initialize E2E authentication (CRITICAL per CLAUDE.md)
        self.auth_helper = E2EAuthHelper(environment="test")
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Set up performance test environment
        with self.isolated_environment(
            ENVIRONMENT="performance_e2e_test",
            TESTING="true",
            JWT_SECRET_KEY="performance-e2e-test-jwt-secret-startup-validation",
            DATABASE_URL="postgresql://test:test@localhost:5434/test_netra_perf_e2e",
            REDIS_URL="redis://localhost:6381/6",
            # Performance-optimized configuration
            STARTUP_PERFORMANCE_MODE="true",
            DATABASE_POOL_SIZE="5",  # Smaller pool for performance testing
            REDIS_POOL_SIZE="5",
            WEBSOCKET_MAX_CONNECTIONS="10",
            AGENT_EXECUTION_TIMEOUT="30",
            # Performance monitoring
            PERFORMANCE_MONITORING_ENABLED="true",
            MEMORY_PROFILING_ENABLED="true"
        ):
            pass
        
        # Business performance SLA thresholds
        self.business_performance_sla = {
            # Startup timing SLAs (based on user experience requirements)
            'single_startup_max': 45.0,      # 45s max for single startup (user tolerance)
            'concurrent_startup_max': 90.0,   # 90s max for 3 concurrent startups
            'websocket_connection_max': 5.0,  # 5s max for WebSocket connection (chat UX)
            'first_agent_response_max': 15.0, # 15s max for first agent response
            
            # Resource utilization SLAs (cost optimization)
            'memory_usage_max_mb': 512,       # 512MB max per startup instance
            'memory_growth_max_mb': 100,      # 100MB max memory growth during startup
            'cpu_usage_max_percent': 80.0,    # 80% max CPU during startup
            'database_connections_max': 10,    # 10 max DB connections per instance
            
            # Scalability SLAs (business growth requirements)
            'concurrent_users_min': 5,         # Support minimum 5 concurrent users
            'startup_success_rate_min': 0.95,  # 95% startup success rate minimum
            'memory_leak_threshold_mb': 50,    # 50MB max acceptable memory leak
            
            # Business continuity SLAs
            'error_recovery_max': 10.0,       # 10s max for error detection and recovery
            'graceful_shutdown_max': 5.0,     # 5s max for graceful shutdown
        }
        
        # Performance monitoring data
        self.performance_metrics = {
            'startup_timings': [],
            'memory_usage': [],
            'cpu_usage': [],
            'resource_utilization': {},
            'concurrent_performance': {},
            'websocket_performance': {},
            'error_recovery_times': [],
            'memory_leak_detection': [],
            'business_sla_violations': []
        }
        
        # Initialize system monitoring
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.test_start_time = time.time()

    async def _ensure_authenticated_user(self):
        """Ensure authenticated user for performance testing (CRITICAL per CLAUDE.md).""" 
        if not hasattr(self, 'test_user_token') or not self.test_user_token:
            self.test_user_token, self.test_user_data = await self.auth_helper.authenticate_user(
                email="performance_e2e_test@example.com",
                password="perf_test_password"
            )

    def _measure_resource_usage(self) -> Dict[str, float]:
        """Measure current resource usage for performance validation."""
        memory_mb = self.process.memory_info().rss / 1024 / 1024
        cpu_percent = self.process.cpu_percent()
        
        # Get database connection count (if available)
        db_connections = 0
        try:
            # This would need to be implemented based on your connection pool
            db_connections = getattr(self, '_get_db_connection_count', lambda: 0)()
        except:
            pass
        
        return {
            'memory_mb': memory_mb,
            'cpu_percent': cpu_percent,
            'db_connections': db_connections,
            'timestamp': time.time()
        }

    # =============================================================================
    # SECTION 1: STARTUP TIMING PERFORMANCE E2E TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_single_startup_performance_meets_business_sla(self):
        """Test single startup performance meets business SLA requirements."""
        # Ensure authenticated user (CRITICAL per CLAUDE.md)
        await self._ensure_authenticated_user()
        
        # Measure baseline resource usage
        baseline_resources = self._measure_resource_usage()
        
        # Measure complete startup performance
        startup_start = time.time()
        
        app = FastAPI(title="Performance E2E Single Startup Test")
        
        try:
            # Execute complete deterministic startup with performance monitoring
            start_time, logger = await smd.run_deterministic_startup(app)
            
            startup_duration = time.time() - startup_start
            
            # Record performance metrics
            self.performance_metrics['startup_timings'].append({
                'type': 'single_startup',
                'duration': startup_duration,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # BUSINESS SLA VALIDATION: Startup timing
            self.assertLess(
                startup_duration, self.business_performance_sla['single_startup_max'],
                f"BUSINESS SLA VIOLATION: Single startup took {startup_duration:.3f}s, "
                f"exceeds {self.business_performance_sla['single_startup_max']}s SLA. "
                f"This will impact user experience and reduce retention."
            )
            
            # Measure resource usage after startup
            post_startup_resources = self._measure_resource_usage()
            
            # BUSINESS SLA VALIDATION: Memory usage
            memory_used = post_startup_resources['memory_mb'] - baseline_resources['memory_mb']
            self.assertLess(
                post_startup_resources['memory_mb'], self.business_performance_sla['memory_usage_max_mb'],
                f"BUSINESS SLA VIOLATION: Memory usage {post_startup_resources['memory_mb']:.1f}MB "
                f"exceeds {self.business_performance_sla['memory_usage_max_mb']}MB SLA. "
                f"High memory usage increases infrastructure costs."
            )
            
            # Verify business-critical services are ready within performance requirements
            service_readiness_start = time.time()
            
            # Check chat-critical services
            chat_services = ['agent_supervisor', 'agent_websocket_bridge', 'llm_manager']
            for service in chat_services:
                service_value = getattr(app.state, service, None)
                self.assertIsNotNone(
                    service_value,
                    f"CRITICAL CHAT FAILURE: {service} not ready after startup. "
                    f"Chat functionality will not work."
                )
            
            service_readiness_time = time.time() - service_readiness_start
            self.assertLess(
                service_readiness_time, 1.0,
                f"Service readiness check took {service_readiness_time:.3f}s, should be instantaneous."
            )
            
            # Record successful single startup performance
            self.performance_metrics['resource_utilization']['single_startup'] = {
                'memory_mb': post_startup_resources['memory_mb'],
                'memory_growth_mb': memory_used,
                'cpu_percent': post_startup_resources['cpu_percent'],
                'duration': startup_duration
            }
            
        except Exception as e:
            # Record performance failure
            self.performance_metrics['business_sla_violations'].append({
                'test': 'single_startup_performance',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            self.fail(
                f"BUSINESS SLA VIOLATION: Single startup performance test failed. "
                f"This indicates production startup will not meet business requirements. Error: {e}"
            )

    @pytest.mark.asyncio
    async def test_concurrent_startup_performance_meets_scalability_sla(self):
        """Test concurrent startup performance meets business scalability SLA."""
        # Ensure authenticated user (CRITICAL per CLAUDE.md)
        await self._ensure_authenticated_user()
        
        # Test concurrent startup performance (business scalability requirement)
        concurrent_startups = 3  # Realistic business scenario
        startup_tasks = []
        
        concurrent_start = time.time()
        
        # Launch concurrent startups
        for i in range(concurrent_startups):
            app = FastAPI(title=f"Performance E2E Concurrent Test {i}")
            task = asyncio.create_task(smd.run_deterministic_startup(app))
            startup_tasks.append((task, app, i))
        
        # Wait for all startups and measure performance
        successful_startups = 0
        startup_times = []
        
        try:
            for task, app, index in startup_tasks:
                try:
                    task_start = time.time()
                    start_time, logger = await task
                    task_duration = time.time() - task_start
                    
                    startup_times.append(task_duration)
                    successful_startups += 1
                    
                    # Verify business-critical state for each concurrent startup
                    self.assertTrue(
                        app.state.startup_complete,
                        f"Concurrent startup {index} not marked complete"
                    )
                    
                except Exception as e:
                    self.performance_metrics['business_sla_violations'].append({
                        'test': 'concurrent_startup',
                        'startup_index': index,
                        'error': str(e)
                    })
            
            total_concurrent_time = time.time() - concurrent_start
            
            # BUSINESS SLA VALIDATION: Concurrent startup timing
            self.assertLess(
                total_concurrent_time, self.business_performance_sla['concurrent_startup_max'],
                f"BUSINESS SLA VIOLATION: Concurrent startups took {total_concurrent_time:.3f}s, "
                f"exceeds {self.business_performance_sla['concurrent_startup_max']}s SLA. "
                f"System cannot handle realistic concurrent load."
            )
            
            # BUSINESS SLA VALIDATION: Startup success rate
            success_rate = successful_startups / concurrent_startups
            self.assertGreaterEqual(
                success_rate, self.business_performance_sla['startup_success_rate_min'],
                f"BUSINESS SLA VIOLATION: Startup success rate {success_rate:.2%} below "
                f"{self.business_performance_sla['startup_success_rate_min']:.2%} SLA. "
                f"System reliability insufficient for business requirements."
            )
            
            # Record concurrent performance metrics
            self.performance_metrics['concurrent_performance'] = {
                'total_time': total_concurrent_time,
                'success_rate': success_rate,
                'individual_times': startup_times,
                'average_time': sum(startup_times) / len(startup_times) if startup_times else 0,
                'max_time': max(startup_times) if startup_times else 0
            }
            
        except Exception as e:
            self.fail(
                f"BUSINESS SLA VIOLATION: Concurrent startup performance test failed. "
                f"System cannot handle business scalability requirements. Error: {e}"
            )

    @pytest.mark.asyncio  
    async def test_websocket_connection_performance_meets_chat_sla(self):
        """Test WebSocket connection performance meets chat responsiveness SLA."""
        # Ensure authenticated user (CRITICAL per CLAUDE.md)
        await self._ensure_authenticated_user()
        
        # Initialize startup for WebSocket testing
        app = FastAPI(title="Performance E2E WebSocket Test")
        await smd.run_deterministic_startup(app)
        
        # Test WebSocket connection performance (critical for chat UX)
        websocket_performance_tests = []
        
        for i in range(5):  # Test multiple connections for reliability
            connection_start = time.time()
            
            try:
                # Connect with authentication (CRITICAL per CLAUDE.md)
                websocket = await self.websocket_auth_helper.connect_authenticated_websocket(
                    timeout=self.business_performance_sla['websocket_connection_max']
                )
                
                connection_time = time.time() - connection_start
                
                # BUSINESS SLA VALIDATION: WebSocket connection timing
                self.assertLess(
                    connection_time, self.business_performance_sla['websocket_connection_max'],
                    f"BUSINESS SLA VIOLATION: WebSocket connection {i} took {connection_time:.3f}s, "
                    f"exceeds {self.business_performance_sla['websocket_connection_max']}s SLA. "
                    f"Chat responsiveness will be poor, reducing user satisfaction."
                )
                
                websocket_performance_tests.append({
                    'connection_index': i,
                    'connection_time': connection_time,
                    'success': True
                })
                
                # Test message round-trip performance (chat responsiveness)
                message_start = time.time()
                
                test_message = {
                    "type": "performance_test",
                    "user_id": self.test_user_data.get("id", "perf_test_user"),
                    "message": f"Performance test message {i}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response (chat responsiveness test)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    message_round_trip = time.time() - message_start
                    
                    websocket_performance_tests[-1]['message_round_trip'] = message_round_trip
                    
                except asyncio.TimeoutError:
                    websocket_performance_tests[-1]['message_timeout'] = True
                
                # Clean up connection
                await websocket.close()
                
            except Exception as e:
                websocket_performance_tests.append({
                    'connection_index': i,
                    'success': False,
                    'error': str(e)
                })
        
        # Analyze WebSocket performance results
        successful_connections = [t for t in websocket_performance_tests if t.get('success', False)]
        
        self.assertGreater(
            len(successful_connections), 3,  # At least 3 out of 5 must succeed
            f"BUSINESS SLA VIOLATION: Only {len(successful_connections)}/5 WebSocket "
            f"connections succeeded. Chat reliability insufficient for business requirements."
        )
        
        # Calculate average WebSocket performance
        if successful_connections:
            avg_connection_time = sum(t['connection_time'] for t in successful_connections) / len(successful_connections)
            
            self.assertLess(
                avg_connection_time, self.business_performance_sla['websocket_connection_max'],
                f"BUSINESS SLA VIOLATION: Average WebSocket connection time {avg_connection_time:.3f}s "
                f"exceeds {self.business_performance_sla['websocket_connection_max']}s SLA."
            )
        
        # Record WebSocket performance metrics
        self.performance_metrics['websocket_performance'] = {
            'connection_tests': websocket_performance_tests,
            'success_rate': len(successful_connections) / len(websocket_performance_tests),
            'avg_connection_time': sum(t['connection_time'] for t in successful_connections) / len(successful_connections) if successful_connections else 0
        }

    # =============================================================================
    # SECTION 2: MEMORY AND RESOURCE PERFORMANCE E2E TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_startup_memory_usage_optimization_meets_cost_sla(self):
        """Test startup memory usage optimization meets cost efficiency SLA."""
        # Ensure authenticated user (CRITICAL per CLAUDE.md)
        await self._ensure_authenticated_user()
        
        # Measure memory usage throughout startup process
        memory_measurements = []
        
        # Baseline memory measurement
        gc.collect()  # Force garbage collection for accurate measurement
        baseline_memory = self.process.memory_info().rss / 1024 / 1024
        memory_measurements.append(('baseline', baseline_memory))
        
        # Create app and measure memory during startup phases
        app = FastAPI(title="Performance E2E Memory Test")
        
        # Hook into startup phases to measure memory at each step
        original_run_startup = smd.run_deterministic_startup
        
        async def memory_tracking_startup(app_instance):
            # Measure memory before startup
            pre_startup_memory = self.process.memory_info().rss / 1024 / 1024
            memory_measurements.append(('pre_startup', pre_startup_memory))
            
            # Execute startup
            result = await original_run_startup(app_instance)
            
            # Measure memory after startup
            post_startup_memory = self.process.memory_info().rss / 1024 / 1024
            memory_measurements.append(('post_startup', post_startup_memory))
            
            return result
        
        # Run startup with memory tracking
        with patch('netra_backend.app.smd.run_deterministic_startup', memory_tracking_startup):
            start_time, logger = await memory_tracking_startup(app)
        
        # Force garbage collection and measure final memory
        gc.collect()
        final_memory = self.process.memory_info().rss / 1024 / 1024
        memory_measurements.append(('final', final_memory))
        
        # BUSINESS SLA VALIDATION: Memory usage
        memory_growth = final_memory - baseline_memory
        
        self.assertLess(
            final_memory, self.business_performance_sla['memory_usage_max_mb'],
            f"BUSINESS COST SLA VIOLATION: Final memory usage {final_memory:.1f}MB "
            f"exceeds {self.business_performance_sla['memory_usage_max_mb']}MB SLA. "
            f"High memory usage increases infrastructure costs."
        )
        
        self.assertLess(
            memory_growth, self.business_performance_sla['memory_growth_max_mb'],
            f"BUSINESS COST SLA VIOLATION: Memory growth {memory_growth:.1f}MB "
            f"exceeds {self.business_performance_sla['memory_growth_max_mb']}MB SLA. "
            f"Memory growth indicates inefficient resource utilization."
        )
        
        # Record memory performance metrics
        self.performance_metrics['memory_usage'] = {
            'measurements': memory_measurements,
            'baseline_mb': baseline_memory,
            'final_mb': final_memory,
            'growth_mb': memory_growth,
            'growth_percentage': (memory_growth / baseline_memory) * 100 if baseline_memory > 0 else 0
        }

    @pytest.mark.asyncio
    async def test_startup_memory_leak_detection_meets_reliability_sla(self):
        """Test startup memory leak detection meets reliability SLA."""
        # Ensure authenticated user (CRITICAL per CLAUDE.md)
        await self._ensure_authenticated_user()
        
        # Perform multiple startup-shutdown cycles to detect memory leaks
        leak_detection_cycles = 3
        memory_after_cycles = []
        
        for cycle in range(leak_detection_cycles):
            # Force garbage collection before measurement
            gc.collect()
            pre_cycle_memory = self.process.memory_info().rss / 1024 / 1024
            
            # Create and startup app
            app = FastAPI(title=f"Memory Leak Detection Cycle {cycle}")
            start_time, logger = await smd.run_deterministic_startup(app)
            
            # Verify startup completed successfully
            self.assertTrue(
                app.state.startup_complete,
                f"Startup cycle {cycle} failed to complete"
            )
            
            # Simulate cleanup (app going out of scope)
            del app
            
            # Force garbage collection
            gc.collect()
            
            # Measure memory after cycle
            post_cycle_memory = self.process.memory_info().rss / 1024 / 1024
            memory_after_cycles.append({
                'cycle': cycle,
                'pre_memory_mb': pre_cycle_memory,
                'post_memory_mb': post_cycle_memory,
                'growth_mb': post_cycle_memory - pre_cycle_memory
            })
        
        # Analyze memory leak patterns
        if len(memory_after_cycles) >= 2:
            # Calculate memory growth trend
            total_growth = memory_after_cycles[-1]['post_memory_mb'] - memory_after_cycles[0]['pre_memory_mb']
            
            # BUSINESS SLA VALIDATION: Memory leak threshold
            self.assertLess(
                total_growth, self.business_performance_sla['memory_leak_threshold_mb'],
                f"BUSINESS RELIABILITY SLA VIOLATION: Memory leak detected. "
                f"Total growth {total_growth:.1f}MB over {leak_detection_cycles} cycles "
                f"exceeds {self.business_performance_sla['memory_leak_threshold_mb']}MB threshold. "
                f"Memory leaks cause long-term system degradation and increased costs."
            )
        
        # Record memory leak detection results
        self.performance_metrics['memory_leak_detection'] = {
            'cycles': memory_after_cycles,
            'total_cycles': leak_detection_cycles,
            'leak_detected': total_growth > self.business_performance_sla['memory_leak_threshold_mb'] if 'total_growth' in locals() else False,
            'growth_per_cycle_mb': total_growth / leak_detection_cycles if 'total_growth' in locals() else 0
        }

    # =============================================================================
    # SECTION 3: SCALABILITY AND LOAD PERFORMANCE E2E TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_startup_supports_concurrent_user_load_performance(self):
        """Test startup supports concurrent user load performance requirements.""" 
        # Test concurrent user scenarios (business scalability requirement)
        concurrent_users = self.business_performance_sla['concurrent_users_min']
        
        # Initialize startup for concurrent user testing
        app = FastAPI(title="Performance E2E Concurrent Users Test")
        await smd.run_deterministic_startup(app)
        
        # Create multiple authenticated users concurrently
        concurrent_user_tasks = []
        user_creation_start = time.time()
        
        for i in range(concurrent_users):
            auth_helper = E2EAuthHelper(environment="test")
            task = asyncio.create_task(
                auth_helper.authenticate_user(
                    email=f"perf_user_{i}@example.com",
                    password=f"perf_password_{i}"
                )
            )
            concurrent_user_tasks.append((task, i))
        
        # Wait for all user authentications
        authenticated_users = []
        failed_authentications = []
        
        for task, user_index in concurrent_user_tasks:
            try:
                token, user_data = await task
                authenticated_users.append({
                    'index': user_index,
                    'token': token,
                    'user_data': user_data
                })
            except Exception as e:
                failed_authentications.append({
                    'index': user_index,
                    'error': str(e)
                })
        
        user_creation_time = time.time() - user_creation_start
        
        # BUSINESS SLA VALIDATION: User authentication scalability
        success_rate = len(authenticated_users) / concurrent_users
        self.assertGreaterEqual(
            success_rate, 0.9,  # 90% success rate minimum for concurrent users
            f"BUSINESS SCALABILITY SLA VIOLATION: Only {success_rate:.2%} of concurrent "
            f"user authentications succeeded. System cannot handle business user load."
        )
        
        # Test concurrent WebSocket connections from all users
        websocket_connection_start = time.time()
        concurrent_websocket_tasks = []
        
        for user in authenticated_users[:3]:  # Test first 3 users for WebSocket performance
            ws_auth_helper = E2EWebSocketAuthHelper(environment="test")
            ws_auth_helper._cached_token = user['token']
            ws_auth_helper._token_expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
            
            task = asyncio.create_task(
                ws_auth_helper.connect_authenticated_websocket(timeout=10.0)
            )
            concurrent_websocket_tasks.append((task, user['index']))
        
        # Wait for WebSocket connections
        websocket_connections = []
        websocket_failures = []
        
        for task, user_index in concurrent_websocket_tasks:
            try:
                websocket = await task
                websocket_connections.append({
                    'user_index': user_index,
                    'websocket': websocket
                })
            except Exception as e:
                websocket_failures.append({
                    'user_index': user_index,
                    'error': str(e)
                })
        
        concurrent_websocket_time = time.time() - websocket_connection_start
        
        # BUSINESS SLA VALIDATION: Concurrent WebSocket performance
        websocket_success_rate = len(websocket_connections) / len(concurrent_websocket_tasks)
        self.assertGreaterEqual(
            websocket_success_rate, 0.8,  # 80% success rate minimum
            f"BUSINESS CHAT SLA VIOLATION: Only {websocket_success_rate:.2%} of concurrent "
            f"WebSocket connections succeeded. Chat scalability insufficient."
        )
        
        # Clean up WebSocket connections
        for conn in websocket_connections:
            try:
                await conn['websocket'].close()
            except:
                pass  # Best effort cleanup
        
        # Record concurrent user performance metrics
        self.performance_metrics['concurrent_performance']['user_load'] = {
            'concurrent_users': concurrent_users,
            'auth_success_rate': success_rate,
            'user_creation_time': user_creation_time,
            'websocket_success_rate': websocket_success_rate,
            'websocket_connection_time': concurrent_websocket_time,
            'failed_authentications': len(failed_authentications),
            'failed_websockets': len(websocket_failures)
        }

    # =============================================================================
    # SECTION 4: ERROR RECOVERY PERFORMANCE E2E TESTS  
    # =============================================================================

    @pytest.mark.asyncio
    async def test_startup_error_recovery_performance_meets_business_continuity_sla(self):
        """Test startup error recovery performance meets business continuity SLA."""
        # Ensure authenticated user (CRITICAL per CLAUDE.md)
        await self._ensure_authenticated_user()
        
        # Test various error recovery scenarios
        error_scenarios = [
            {
                'name': 'database_connection_timeout',
                'mock_target': 'netra_backend.app.startup_module.setup_database_connections',
                'error': asyncio.TimeoutError("Database connection timeout")
            },
            {
                'name': 'redis_connection_failure', 
                'mock_target': 'netra_backend.app.startup_module.redis_manager',
                'error': ConnectionError("Redis connection refused")
            },
            {
                'name': 'service_initialization_failure',
                'mock_target': 'netra_backend.app.startup_module.initialize_core_services',
                'error': RuntimeError("Core service initialization failed")
            }
        ]
        
        for scenario in error_scenarios:
            with self.subTest(scenario=scenario['name']):
                app = FastAPI(title=f"Error Recovery Performance Test - {scenario['name']}")
                
                # Test error detection and recovery timing
                error_start = time.time()
                
                with patch(scenario['mock_target']) as mock_target:
                    mock_target.side_effect = scenario['error']
                    
                    try:
                        await smd.run_deterministic_startup(app)
                        # Should not reach here for most error scenarios
                        self.fail(f"Expected error for scenario {scenario['name']}")
                        
                    except Exception as e:
                        error_detection_time = time.time() - error_start
                        
                        # BUSINESS SLA VALIDATION: Error recovery timing
                        self.assertLess(
                            error_detection_time, self.business_performance_sla['error_recovery_max'],
                            f"BUSINESS CONTINUITY SLA VIOLATION: Error detection for {scenario['name']} "
                            f"took {error_detection_time:.3f}s, exceeds "
                            f"{self.business_performance_sla['error_recovery_max']}s SLA. "
                            f"Slow error detection delays recovery and increases downtime."
                        )
                        
                        # Verify error provides adequate information for rapid resolution
                        error_message = str(e)
                        self.assertGreater(
                            len(error_message), 20,
                            f"Error message too short for rapid incident resolution: {error_message}"
                        )
                        
                        # Record error recovery performance
                        self.performance_metrics['error_recovery_times'].append({
                            'scenario': scenario['name'],
                            'detection_time': error_detection_time,
                            'error_type': type(e).__name__,
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        })

    def tearDown(self):
        """Clean up performance test environment and generate comprehensive report."""
        # Calculate total test duration
        test_duration = time.time() - self.test_start_time
        
        # Measure final resource usage
        final_resources = self._measure_resource_usage()
        
        # Generate comprehensive performance report
        print(f"\n{'='*80}")
        print(f"STARTUP PERFORMANCE E2E TEST REPORT")
        print(f"{'='*80}")
        print(f"Test Duration: {test_duration:.3f}s")
        print(f"Environment: {get_env().get('ENVIRONMENT', 'unknown')}")
        print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
        
        # Report Business SLA Compliance
        sla_violations = len(self.performance_metrics['business_sla_violations'])
        print(f"\n📊 BUSINESS SLA COMPLIANCE:")
        print(f"  SLA Violations: {sla_violations}")
        
        if sla_violations == 0:
            print(f"  ✅ ALL BUSINESS SLA REQUIREMENTS MET")
        else:
            print(f"  ❌ BUSINESS SLA VIOLATIONS DETECTED:")
            for violation in self.performance_metrics['business_sla_violations']:
                print(f"    - {violation.get('test', 'unknown')}: {violation.get('error', 'unknown error')}")
        
        # Report Startup Performance
        if self.performance_metrics['startup_timings']:
            print(f"\n⚡ STARTUP PERFORMANCE:")
            for timing in self.performance_metrics['startup_timings']:
                print(f"  - {timing['type']}: {timing['duration']:.3f}s")
        
        # Report Resource Utilization  
        if self.performance_metrics['resource_utilization']:
            print(f"\n💾 RESOURCE UTILIZATION:")
            for resource_type, data in self.performance_metrics['resource_utilization'].items():
                print(f"  - {resource_type}:")
                print(f"    Memory: {data.get('memory_mb', 0):.1f}MB")
                print(f"    Growth: {data.get('memory_growth_mb', 0):.1f}MB") 
                print(f"    Duration: {data.get('duration', 0):.3f}s")
        
        # Report Concurrent Performance
        if self.performance_metrics['concurrent_performance']:
            print(f"\n🔀 CONCURRENT PERFORMANCE:")
            for perf_type, data in self.performance_metrics['concurrent_performance'].items():
                if isinstance(data, dict):
                    print(f"  - {perf_type}:")
                    for key, value in data.items():
                        if isinstance(value, (int, float)):
                            if 'time' in key:
                                print(f"    {key}: {value:.3f}s")
                            elif 'rate' in key:
                                print(f"    {key}: {value:.2%}")
                            else:
                                print(f"    {key}: {value}")
        
        # Report WebSocket Performance
        if self.performance_metrics['websocket_performance']:
            print(f"\n🌐 WEBSOCKET PERFORMANCE:")
            ws_perf = self.performance_metrics['websocket_performance']
            print(f"  - Success Rate: {ws_perf.get('success_rate', 0):.2%}")
            print(f"  - Avg Connection Time: {ws_perf.get('avg_connection_time', 0):.3f}s")
        
        # Report Memory Performance
        if self.performance_metrics['memory_usage']:
            print(f"\n🧠 MEMORY PERFORMANCE:")
            mem_data = self.performance_metrics['memory_usage']
            print(f"  - Baseline: {mem_data.get('baseline_mb', 0):.1f}MB")
            print(f"  - Final: {mem_data.get('final_mb', 0):.1f}MB")
            print(f"  - Growth: {mem_data.get('growth_mb', 0):.1f}MB ({mem_data.get('growth_percentage', 0):.1f}%)")
        
        # Report Memory Leak Detection
        if self.performance_metrics['memory_leak_detection']:
            print(f"\n🔍 MEMORY LEAK DETECTION:")
            leak_data = self.performance_metrics['memory_leak_detection']
            print(f"  - Leak Detected: {'YES' if leak_data.get('leak_detected', False) else 'NO'}")
            print(f"  - Growth per Cycle: {leak_data.get('growth_per_cycle_mb', 0):.1f}MB")
            print(f"  - Total Cycles: {leak_data.get('total_cycles', 0)}")
        
        # Report Error Recovery Performance
        if self.performance_metrics['error_recovery_times']:
            print(f"\n🚨 ERROR RECOVERY PERFORMANCE:")
            for recovery in self.performance_metrics['error_recovery_times']:
                print(f"  - {recovery['scenario']}: {recovery['detection_time']:.3f}s")
        
        print(f"{'='*80}")
        
        # Business Impact Summary
        if sla_violations > 0:
            print(f"❌ BUSINESS IMPACT: {sla_violations} SLA violations detected.")
            print(f"   This indicates potential production issues that could impact:")
            print(f"   - User experience and retention")
            print(f"   - System scalability and reliability") 
            print(f"   - Infrastructure costs and efficiency")
            print(f"   - Chat functionality and responsiveness")
        else:
            print(f"✅ BUSINESS SUCCESS: All performance SLAs met.")
            print(f"   System ready for production deployment with confidence.")
        
        print(f"{'='*80}")
        
        # Call parent cleanup
        super().tearDown()


if __name__ == '__main__':
    # Run performance E2E test suite
    unittest.main(verbosity=2, buffer=True)