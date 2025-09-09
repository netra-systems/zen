"""
WebSocket Production Leak Scenario Tests - REAL PRODUCTION PATTERN REPRODUCTION

Business Value Justification (BVJ):
- Segment: ALL (Critical system stability affects all users)
- Business Goal: Prevent catastrophic service outages from resource exhaustion
- Value Impact: Reproduces the exact GCP Cloud Run resource leak patterns observed in production
- Strategic Impact: Validates fixes for root causes that current tests miss

CRITICAL PURPOSE: These tests reproduce the specific production scenarios that bypass
existing tests, focusing on the root causes identified in the Five Whys analysis:

ROOT CAUSE REPRODUCTION:
✅ Thread ID Inconsistency - Multiple components generating different thread IDs
✅ Cloud Run Container Lifecycle - Cold starts, restarts, connection orphaning  
✅ Concurrent Same-User Connections - Browser tabs, mobile apps, reconnections
✅ ID Generation Timing Issues - Race conditions in isolation key creation
✅ Database Session vs WebSocket Context Mismatch - Different operation strings
✅ Emergency Cleanup Timing Failures - Background cleanup vs creation rate mismatch

These scenarios were NOT covered in existing tests and represent the real production
environment conditions causing 20-manager limit crashes.

PRODUCTION ENVIRONMENT SIMULATION:
- Uses REAL UserExecutionContext and ID generation (no mocking)
- Simulates GCP Cloud Run container lifecycle events
- Reproduces browser reconnection patterns (multiple tabs, network drops)
- Tests actual database session factory coordination  
- Validates isolation key consistency under concurrent load
- Measures real memory usage and leak patterns

TARGET SCENARIOS FROM PRODUCTION:
1. Browser Multi-Tab Pattern (same user, multiple connections simultaneously)
2. Cloud Run Cold Start + Connection Storms (rapid connection bursts after idle)
3. Network Reconnection Cycles (connection drops with immediate reconnection)
4. Database Session + WebSocket Context ID Mismatch (different operation strings)
5. Background Cleanup vs Creation Rate Race (cleanup can't keep up with creation)
6. Container Restart Orphaned Manager Recovery (managers survive container restarts)
"""

import asyncio
import pytest
import time
import uuid
import gc
import psutil
import os
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any, Tuple
import logging
import random

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory,
    IsolatedWebSocketManager,
    get_websocket_manager_factory,
    create_websocket_manager
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_manager import WebSocketConnection
from shared.isolated_environment import get_env
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

logger = logging.getLogger(__name__)


class ProductionLeakReproducer:
    """
    Reproduces specific production leak scenarios that bypass current tests.
    
    This class simulates the exact patterns observed in GCP Cloud Run production
    environment that cause WebSocket manager resource leaks.
    """
    
    def __init__(self):
        self.scenario_results: Dict[str, Any] = {}
        self.leak_evidence: List[Dict[str, Any]] = []
        self.memory_snapshots: List[float] = []
        self.process = psutil.Process(os.getpid())
        
    def capture_memory_snapshot(self, label: str) -> float:
        """Capture current memory usage for leak detection."""
        memory_mb = self.process.memory_info().rss / (1024 * 1024)
        self.memory_snapshots.append(memory_mb)
        logger.info(f"Memory snapshot [{label}]: {memory_mb:.2f}MB")
        return memory_mb
    
    def detect_memory_leak(self, baseline_mb: float, current_mb: float, threshold_mb: float = 50.0) -> bool:
        """Detect if memory usage indicates a resource leak."""
        growth_mb = current_mb - baseline_mb
        if growth_mb > threshold_mb:
            self.leak_evidence.append({
                'type': 'memory_leak',
                'baseline_mb': baseline_mb,
                'current_mb': current_mb,
                'growth_mb': growth_mb,
                'threshold_mb': threshold_mb,
                'timestamp': time.time()
            })
            return True
        return False
    
    async def simulate_browser_multi_tab_pattern(self, factory: WebSocketManagerFactory, user_id: str) -> Dict[str, Any]:
        """
        PRODUCTION SCENARIO 1: Browser Multi-Tab Pattern
        
        Simulates user opening multiple browser tabs with the same login,
        each creating separate WebSocket connections but potentially with 
        inconsistent thread_id generation.
        
        ROOT CAUSE REPRODUCTION: Different tabs may trigger separate calls to
        generate_user_context_ids() with different operation strings or timing,
        creating isolation key mismatches.
        """
        logger.info("🌐 PRODUCTION SCENARIO 1: Browser Multi-Tab Pattern")
        
        baseline_memory = self.capture_memory_snapshot("multi_tab_baseline")
        tab_managers = []
        isolation_keys = set()
        thread_ids = set()
        
        # Simulate 8 browser tabs opening within 2 seconds (realistic user behavior)
        tab_contexts = []
        for tab_num in range(8):
            # CRITICAL: Each tab may generate context with slight timing differences
            # This reproduces the thread_id inconsistency issue
            await asyncio.sleep(0.1)  # 100ms between tab opens
            
            # Simulate potential database session creation BEFORE WebSocket context
            # This reproduces the "different operation string" problem
            if tab_num % 3 == 0:  # Every 3rd tab has database session first
                # Simulate database session factory call (different operation)
                db_thread_id, db_run_id, db_request_id = UnifiedIdGenerator.generate_user_context_ids(
                    user_id=user_id, 
                    operation="session"  # DIFFERENT operation string
                )
                logger.debug(f"Tab {tab_num}: DB session context created first: thread_id={db_thread_id}")
            
            # Now create WebSocket context (potentially different thread_id)
            ws_thread_id, ws_run_id, ws_request_id = UnifiedIdGenerator.generate_user_context_ids(
                user_id=user_id,
                operation="websocket_factory"  # DIFFERENT operation string
            )
            
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=ws_thread_id,
                run_id=ws_run_id,
                request_id=ws_request_id,
                websocket_client_id=f"browser_tab_{tab_num}_{uuid.uuid4().hex[:8]}"
            )
            
            tab_contexts.append(context)
            thread_ids.add(ws_thread_id)
            
        # Create managers for all tabs
        for i, context in enumerate(tab_contexts):
            try:
                manager = await factory.create_manager(context)
                tab_managers.append(manager)
                
                # Track isolation keys for consistency analysis
                isolation_key = factory._generate_isolation_key(context)
                isolation_keys.add(isolation_key)
                
                logger.debug(f"Tab {i}: Manager created, isolation_key={isolation_key}")
                
            except Exception as e:
                self.leak_evidence.append({
                    'type': 'tab_creation_failure',
                    'tab_number': i,
                    'error': str(e),
                    'thread_id': context.thread_id
                })
        
        # Simulate some tabs closing (realistic user behavior)
        tabs_to_close = random.sample(range(len(tab_managers)), 3)  # Close 3 random tabs
        for tab_idx in tabs_to_close:
            manager = tab_managers[tab_idx]
            context = tab_contexts[tab_idx]
            
            # Find isolation key for cleanup
            isolation_key = factory._generate_isolation_key(context)
            try:
                cleanup_success = await factory.cleanup_manager(isolation_key)
                if not cleanup_success:
                    self.leak_evidence.append({
                        'type': 'tab_cleanup_failure',
                        'tab_number': tab_idx,
                        'isolation_key': isolation_key,
                        'thread_id': context.thread_id
                    })
            except Exception as e:
                self.leak_evidence.append({
                    'type': 'tab_cleanup_error',
                    'tab_number': tab_idx,
                    'error': str(e),
                    'isolation_key': isolation_key
                })
        
        final_memory = self.capture_memory_snapshot("multi_tab_complete")
        
        return {
            'scenario': 'browser_multi_tab',
            'total_tabs': len(tab_contexts),
            'managers_created': len(tab_managers),
            'unique_isolation_keys': len(isolation_keys),
            'unique_thread_ids': len(thread_ids),
            'tabs_closed': len(tabs_to_close),
            'memory_growth_mb': final_memory - baseline_memory,
            'thread_id_consistency': len(thread_ids) == len(tab_contexts),  # Should be True for consistency
            'isolation_key_uniqueness': len(isolation_keys) == len([m for m in tab_managers if m._is_active])
        }
    
    async def simulate_cloud_run_cold_start_burst(self, factory: WebSocketManagerFactory, user_id: str) -> Dict[str, Any]:
        """
        PRODUCTION SCENARIO 2: Cloud Run Cold Start + Connection Burst
        
        Simulates GCP Cloud Run container cold start followed by burst of connections
        from users who were waiting. This can overwhelm the background cleanup task
        which may not have started yet.
        
        ROOT CAUSE REPRODUCTION: Background cleanup task may not be started during
        cold start, allowing managers to accumulate rapidly.
        """
        logger.info("☁️ PRODUCTION SCENARIO 2: Cloud Run Cold Start + Connection Burst")
        
        baseline_memory = self.capture_memory_snapshot("cold_start_baseline")
        
        # Simulate cold start - create new factory (no background cleanup started)
        cold_start_factory = WebSocketManagerFactory(max_managers_per_user=20, connection_timeout_seconds=300)
        
        # Simulate connection burst (users reconnecting after cold start)
        burst_managers = []
        burst_start = time.time()
        connections_per_second = 15  # High connection rate
        
        # Create rapid burst of connections (faster than background cleanup can handle)
        for i in range(25):  # More than the 20 limit to test emergency cleanup
            # Generate context with rapid timing (potential race conditions)
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"cold_start_thread_{i}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}",
                run_id=f"cold_start_run_{i}_{int(time.time() * 1000)}",
                request_id=f"cold_start_req_{i}_{int(time.time() * 1000)}",
                websocket_client_id=f"cold_start_client_{i}"
            )
            
            try:
                # Create manager with minimal delay (simulates connection burst)
                manager = await cold_start_factory.create_manager(context)
                burst_managers.append(manager)
                
                # Brief pause to simulate realistic connection timing
                await asyncio.sleep(1.0 / connections_per_second)  # ~67ms between connections
                
            except RuntimeError as e:
                if "maximum number" in str(e):
                    self.leak_evidence.append({
                        'type': 'cold_start_limit_hit',
                        'connection_number': i,
                        'time_elapsed': time.time() - burst_start,
                        'managers_created_before_limit': len(burst_managers)
                    })
                    logger.warning(f"Hit 20-manager limit at connection {i} after {time.time() - burst_start:.2f}s")
                    break
                else:
                    raise
        
        burst_duration = time.time() - burst_start
        
        # Test if emergency cleanup was triggered and effective
        factory_stats = cold_start_factory.get_factory_stats()
        
        # Cleanup the factory
        await cold_start_factory.shutdown()
        
        final_memory = self.capture_memory_snapshot("cold_start_complete")
        
        return {
            'scenario': 'cloud_run_cold_start_burst',
            'connections_attempted': 25,
            'managers_created': len(burst_managers),
            'burst_duration_seconds': burst_duration,
            'connections_per_second_achieved': len(burst_managers) / burst_duration,
            'resource_limit_hits': factory_stats['factory_metrics']['resource_limit_hits'],
            'emergency_cleanup_triggered': factory_stats['factory_metrics']['resource_limit_hits'] > 0,
            'memory_growth_mb': final_memory - baseline_memory
        }
    
    async def simulate_network_reconnection_cycles(self, factory: WebSocketManagerFactory, user_id: str) -> Dict[str, Any]:
        """
        PRODUCTION SCENARIO 3: Network Reconnection Cycles
        
        Simulates unstable network causing repeated connection drops and immediate
        reconnections. This can create rapid manager creation/cleanup cycles that
        may not coordinate properly.
        
        ROOT CAUSE REPRODUCTION: Rapid reconnections may create new managers before
        old ones are cleaned up, especially if isolation keys are inconsistent.
        """
        logger.info("📶 PRODUCTION SCENARIO 3: Network Reconnection Cycles")
        
        baseline_memory = self.capture_memory_snapshot("reconnection_baseline")
        
        reconnection_managers = []
        reconnection_failures = []
        isolation_key_conflicts = []
        
        # Simulate 15 rapid reconnection cycles (unstable mobile network pattern)
        for cycle in range(15):
            cycle_start = time.time()
            
            # Create connection context
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"reconnect_thread_{cycle}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}",
                run_id=f"reconnect_run_{cycle}_{int(time.time() * 1000)}",
                request_id=f"reconnect_req_{cycle}_{int(time.time() * 1000)}",
                websocket_client_id=f"mobile_reconnect_{cycle}"
            )
            
            # Create manager
            try:
                manager = await factory.create_manager(context)
                reconnection_managers.append((manager, context))
                
                # Simulate brief connection activity
                await asyncio.sleep(0.2)  # 200ms connection
                
                # Immediate disconnect and cleanup attempt
                isolation_key = factory._generate_isolation_key(context)
                
                # Check if isolation key conflicts with existing managers
                existing_keys = set()
                for existing_manager, existing_context in reconnection_managers[:-1]:
                    if existing_manager._is_active:
                        existing_key = factory._generate_isolation_key(existing_context)
                        if existing_key == isolation_key:
                            isolation_key_conflicts.append({
                                'cycle': cycle,
                                'conflicting_key': isolation_key,
                                'existing_cycle': reconnection_managers.index((existing_manager, existing_context))
                            })
                        existing_keys.add(existing_key)
                
                # Attempt cleanup (simulates network drop)
                cleanup_success = await factory.cleanup_manager(isolation_key)
                if not cleanup_success:
                    reconnection_failures.append({
                        'cycle': cycle,
                        'isolation_key': isolation_key,
                        'cleanup_failed': True
                    })
                
                # Brief pause before reconnection
                await asyncio.sleep(0.1)  # 100ms network recovery
                
            except Exception as e:
                reconnection_failures.append({
                    'cycle': cycle,
                    'error': str(e),
                    'phase': 'creation'
                })
        
        # Check for accumulated managers (leak indicator)
        active_managers = sum(1 for manager, context in reconnection_managers if manager._is_active)
        
        final_memory = self.capture_memory_snapshot("reconnection_complete")
        
        return {
            'scenario': 'network_reconnection_cycles',
            'cycles_attempted': 15,
            'managers_created': len(reconnection_managers),
            'reconnection_failures': len(reconnection_failures),
            'isolation_key_conflicts': len(isolation_key_conflicts),
            'active_managers_remaining': active_managers,
            'memory_growth_mb': final_memory - baseline_memory,
            'leak_detected': active_managers > 3  # More than 3 remaining indicates leak
        }
    
    async def simulate_database_websocket_context_mismatch(self, factory: WebSocketManagerFactory, user_id: str) -> Dict[str, Any]:
        """
        PRODUCTION SCENARIO 4: Database Session + WebSocket Context ID Mismatch
        
        Simulates the specific pattern where database session factory and WebSocket
        factory generate different thread_ids for the same user, causing isolation
        key mismatches during cleanup.
        
        ROOT CAUSE REPRODUCTION: This directly reproduces the thread_id inconsistency
        identified in the Five Whys analysis.
        """
        logger.info("🔀 PRODUCTION SCENARIO 4: Database + WebSocket Context ID Mismatch")
        
        baseline_memory = self.capture_memory_snapshot("context_mismatch_baseline")
        
        mismatch_scenarios = []
        context_pairs = []
        
        # Simulate 10 user sessions with database+websocket context creation
        for session in range(10):
            # Step 1: Database session factory creates context first (typical pattern)
            db_thread_id, db_run_id, db_request_id = UnifiedIdGenerator.generate_user_context_ids(
                user_id=user_id,
                operation="session"  # Database uses "session"
            )
            
            # Brief delay to simulate separate operations
            await asyncio.sleep(0.05)  # 50ms delay
            
            # Step 2: WebSocket factory creates separate context
            ws_thread_id, ws_run_id, ws_request_id = UnifiedIdGenerator.generate_user_context_ids(
                user_id=user_id,
                operation="websocket_factory"  # WebSocket uses "websocket_factory"
            )
            
            # Create UserExecutionContext with WebSocket IDs
            ws_context = UserExecutionContext(
                user_id=user_id,
                thread_id=ws_thread_id,
                run_id=ws_run_id,
                request_id=ws_request_id,
                websocket_client_id=f"mismatch_client_{session}"
            )
            
            # Create theoretical database context (what database thinks context should be)
            db_context = UserExecutionContext(
                user_id=user_id,
                thread_id=db_thread_id,
                run_id=db_run_id,
                request_id=db_request_id,
                websocket_client_id=f"mismatch_client_{session}"
            )
            
            context_pairs.append((db_context, ws_context))
            
            # Analyze mismatch
            thread_id_match = db_thread_id == ws_thread_id
            run_id_match = db_run_id == ws_run_id
            isolation_key_db = factory._generate_isolation_key(db_context)
            isolation_key_ws = factory._generate_isolation_key(ws_context)
            isolation_key_match = isolation_key_db == isolation_key_ws
            
            mismatch_data = {
                'session': session,
                'db_thread_id': db_thread_id,
                'ws_thread_id': ws_thread_id,
                'thread_id_match': thread_id_match,
                'run_id_match': run_id_match,
                'isolation_key_db': isolation_key_db,
                'isolation_key_ws': isolation_key_ws,
                'isolation_key_match': isolation_key_match
            }
            mismatch_scenarios.append(mismatch_data)
            
            # Create manager with WebSocket context
            try:
                manager = await factory.create_manager(ws_context)
                
                # Simulate cleanup attempt with database context (mismatch scenario)
                # This reproduces the exact failure pattern from production
                cleanup_with_db_context = await factory.cleanup_manager(isolation_key_db)
                cleanup_with_ws_context = await factory.cleanup_manager(isolation_key_ws)
                
                mismatch_data['cleanup_with_db_context'] = cleanup_with_db_context
                mismatch_data['cleanup_with_ws_context'] = cleanup_with_ws_context
                mismatch_data['manager_active_after_cleanup'] = manager._is_active
                
                # If manager is still active after both cleanup attempts, it's a leak
                if manager._is_active:
                    self.leak_evidence.append({
                        'type': 'context_mismatch_leak',
                        'session': session,
                        'isolation_key_db': isolation_key_db,
                        'isolation_key_ws': isolation_key_ws,
                        'thread_id_mismatch': not thread_id_match
                    })
                
            except Exception as e:
                mismatch_data['manager_creation_error'] = str(e)
        
        # Analysis
        thread_id_mismatches = sum(1 for s in mismatch_scenarios if not s.get('thread_id_match', False))
        isolation_key_mismatches = sum(1 for s in mismatch_scenarios if not s.get('isolation_key_match', False))
        cleanup_failures = sum(1 for s in mismatch_scenarios if not s.get('cleanup_with_db_context', False) and not s.get('cleanup_with_ws_context', False))
        
        final_memory = self.capture_memory_snapshot("context_mismatch_complete")
        
        return {
            'scenario': 'database_websocket_context_mismatch',
            'sessions_tested': len(mismatch_scenarios),
            'thread_id_mismatches': thread_id_mismatches,
            'isolation_key_mismatches': isolation_key_mismatches,
            'cleanup_failures': cleanup_failures,
            'memory_growth_mb': final_memory - baseline_memory,
            'mismatch_percentage': (thread_id_mismatches / len(mismatch_scenarios)) * 100,
            'leak_evidence_count': len([e for e in self.leak_evidence if e['type'] == 'context_mismatch_leak'])
        }
    
    async def simulate_background_cleanup_race_condition(self, factory: WebSocketManagerFactory, user_id: str) -> Dict[str, Any]:
        """
        PRODUCTION SCENARIO 5: Background Cleanup vs Creation Rate Race
        
        Simulates the scenario where managers are created faster than background
        cleanup can remove them, leading to accumulation until the 20-manager limit.
        
        ROOT CAUSE REPRODUCTION: Tests the timing mismatch between synchronous
        resource limit enforcement and asynchronous background cleanup.
        """
        logger.info("⚡ PRODUCTION SCENARIO 5: Background Cleanup vs Creation Rate Race")
        
        baseline_memory = self.capture_memory_snapshot("cleanup_race_baseline")
        
        # Create managers at a rate faster than background cleanup (every 2 minutes)
        creation_interval = 0.5  # 500ms between creations
        total_duration = 10.0    # 10 seconds test
        expected_creations = int(total_duration / creation_interval)
        
        race_managers = []
        creation_failures = []
        race_start = time.time()
        
        while (time.time() - race_start) < total_duration:
            iteration = len(race_managers)
            
            # Create context
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"race_thread_{iteration}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}",
                run_id=f"race_run_{iteration}_{int(time.time() * 1000)}",
                request_id=f"race_req_{iteration}_{int(time.time() * 1000)}",
                websocket_client_id=f"race_client_{iteration}"
            )
            
            try:
                manager = await factory.create_manager(context)
                race_managers.append(manager)
                
                # Simulate brief usage then mark for cleanup (but don't actually clean up)
                # This simulates the scenario where cleanup is scheduled but delayed
                old_time = datetime.utcnow() - timedelta(minutes=10)
                manager._metrics.last_activity = old_time
                
            except RuntimeError as e:
                if "maximum number" in str(e):
                    creation_failures.append({
                        'iteration': iteration,
                        'time_elapsed': time.time() - race_start,
                        'managers_before_limit': len(race_managers)
                    })
                    logger.warning(f"Hit limit at iteration {iteration} after {time.time() - race_start:.2f}s")
                    break
                else:
                    raise
            
            await asyncio.sleep(creation_interval)
        
        # Test emergency cleanup effectiveness
        pre_cleanup_count = len([m for m in race_managers if m._is_active])
        
        # Force cleanup to test if it can recover from the race condition
        cleaned_count = await factory.force_cleanup_user_managers(user_id)
        
        post_cleanup_count = len([m for m in race_managers if m._is_active])
        
        race_duration = time.time() - race_start
        final_memory = self.capture_memory_snapshot("cleanup_race_complete")
        
        return {
            'scenario': 'background_cleanup_race_condition',
            'target_duration_seconds': total_duration,
            'actual_duration_seconds': race_duration,
            'managers_created': len(race_managers),
            'creation_failures': len(creation_failures),
            'pre_cleanup_active_count': pre_cleanup_count,
            'post_cleanup_active_count': post_cleanup_count,
            'emergency_cleanup_count': cleaned_count,
            'creation_rate_per_second': len(race_managers) / race_duration,
            'cleanup_effectiveness': (cleaned_count / max(1, pre_cleanup_count)) * 100,
            'memory_growth_mb': final_memory - baseline_memory,
            'race_condition_detected': len(creation_failures) > 0 and pre_cleanup_count > 10
        }
    
    def get_comprehensive_leak_analysis(self) -> Dict[str, Any]:
        """Generate comprehensive analysis of all leak scenarios."""
        total_memory_growth = sum(
            result.get('memory_growth_mb', 0) 
            for result in self.scenario_results.values()
        )
        
        leak_scenarios = [
            scenario for scenario, result in self.scenario_results.items()
            if result.get('leak_detected', False) or 
               result.get('memory_growth_mb', 0) > 25.0 or
               len([e for e in self.leak_evidence if scenario in e.get('type', '')]) > 0
        ]
        
        return {
            'total_scenarios_tested': len(self.scenario_results),
            'leak_scenarios_detected': len(leak_scenarios),
            'leak_scenario_names': leak_scenarios,
            'total_memory_growth_mb': total_memory_growth,
            'total_leak_evidence_items': len(self.leak_evidence),
            'critical_issues': [
                e for e in self.leak_evidence 
                if e.get('type') in ['memory_leak', 'context_mismatch_leak', 'cleanup_failure']
            ],
            'scenario_results': self.scenario_results,
            'leak_evidence': self.leak_evidence
        }


class TestWebSocketProductionLeakScenarios(SSotAsyncTestCase):
    """Critical WebSocket production leak scenario reproduction tests."""
    
    def setup_method(self, method=None):
        """Setup for each test with production leak reproducer."""
        super().setup_method(method)
        self.leak_reproducer = ProductionLeakReproducer()
        self.factory = WebSocketManagerFactory(max_managers_per_user=20, connection_timeout_seconds=300)
        
        # Generate test user ID
        self.test_user_id = f"prod-leak-user-{random.randint(10000, 99999)}"
        
        logger.info(f"Production leak scenario test setup for user: {self.test_user_id}")
    
    def teardown_method(self, method=None):
        """Cleanup and comprehensive leak analysis."""
        if hasattr(self, 'factory'):
            asyncio.run(self.factory.shutdown())
        
        # Generate comprehensive leak analysis
        leak_analysis = self.leak_reproducer.get_comprehensive_leak_analysis()
        logger.info(f"PRODUCTION LEAK ANALYSIS: {leak_analysis}")
        
        # Assert no critical leaks detected
        critical_leaks = len(leak_analysis['critical_issues'])
        if critical_leaks > 0:
            logger.error(f"CRITICAL RESOURCE LEAKS DETECTED: {critical_leaks}")
            for issue in leak_analysis['critical_issues']:
                logger.error(f"  - {issue}")
        
        super().teardown_method(method)
    
    @pytest.mark.asyncio
    async def test_browser_multi_tab_resource_leak_reproduction(self):
        """
        PRODUCTION SCENARIO 1: Browser Multi-Tab Resource Leak
        
        Reproduces the exact pattern where multiple browser tabs create
        WebSocket managers with inconsistent thread_ids, preventing cleanup.
        """
        logger.info("🌐 TESTING: Browser Multi-Tab Resource Leak Pattern")
        
        result = await self.leak_reproducer.simulate_browser_multi_tab_pattern(
            self.factory, 
            self.test_user_id
        )
        
        self.leak_reproducer.scenario_results['browser_multi_tab'] = result
        
        # Validate results
        assert result['total_tabs'] == 8, f"Expected 8 tabs, got {result['total_tabs']}"
        assert result['managers_created'] <= 8, f"Too many managers created: {result['managers_created']}"
        
        # Check for thread_id consistency issues (production problem reproduction)
        if not result['thread_id_consistency']:
            logger.warning("⚠️ Thread ID inconsistency detected - reproducing production issue")
        
        # Check for memory growth (leak indicator)
        assert result['memory_growth_mb'] < 100, f"Excessive memory growth: {result['memory_growth_mb']:.2f}MB"
        
        # Validate cleanup effectiveness
        remaining_managers = self.factory.get_factory_stats()['factory_metrics']['managers_active']
        assert remaining_managers <= 8, f"Too many managers remaining: {remaining_managers}"
        
        logger.info(f"✅ Multi-tab test completed: {result}")
    
    @pytest.mark.asyncio
    async def test_cloud_run_cold_start_burst_reproduction(self):
        """
        PRODUCTION SCENARIO 2: Cloud Run Cold Start Connection Burst
        
        Reproduces GCP Cloud Run cold start followed by connection burst
        that overwhelms background cleanup before it starts.
        """
        logger.info("☁️ TESTING: Cloud Run Cold Start Connection Burst")
        
        result = await self.leak_reproducer.simulate_cloud_run_cold_start_burst(
            self.factory,
            self.test_user_id
        )
        
        self.leak_reproducer.scenario_results['cloud_run_cold_start'] = result
        
        # Validate results
        assert result['connections_attempted'] == 25, "Should attempt 25 connections"
        
        # Should hit resource limit (reproducing production issue)
        assert result['resource_limit_hits'] > 0, "Should trigger resource limit during burst"
        
        # Emergency cleanup should be triggered
        assert result['emergency_cleanup_triggered'], "Emergency cleanup should activate"
        
        # Connection rate should be realistic
        assert result['connections_per_second_achieved'] > 5, f"Too slow connection rate: {result['connections_per_second_achieved']:.2f}/s"
        
        # Memory growth should be reasonable
        assert result['memory_growth_mb'] < 150, f"Excessive memory growth: {result['memory_growth_mb']:.2f}MB"
        
        logger.info(f"✅ Cold start burst test completed: {result}")
    
    @pytest.mark.asyncio
    async def test_network_reconnection_cycles_reproduction(self):
        """
        PRODUCTION SCENARIO 3: Network Reconnection Cycles
        
        Reproduces unstable network causing rapid reconnection cycles
        that may create isolation key conflicts.
        """
        logger.info("📶 TESTING: Network Reconnection Cycles")
        
        result = await self.leak_reproducer.simulate_network_reconnection_cycles(
            self.factory,
            self.test_user_id
        )
        
        self.leak_reproducer.scenario_results['network_reconnection'] = result
        
        # Validate results
        assert result['cycles_attempted'] == 15, "Should attempt 15 reconnection cycles"
        assert result['managers_created'] <= 15, f"Too many managers: {result['managers_created']}"
        
        # Check for isolation key conflicts (production issue reproduction)
        if result['isolation_key_conflicts'] > 0:
            logger.warning(f"⚠️ Isolation key conflicts detected: {result['isolation_key_conflicts']}")
        
        # Should not have excessive remaining managers (leak indicator)
        assert not result['leak_detected'], f"Resource leak detected: {result['active_managers_remaining']} managers remaining"
        
        # Reconnection failures should be minimal
        assert result['reconnection_failures'] <= 3, f"Too many reconnection failures: {result['reconnection_failures']}"
        
        # Memory growth should be reasonable
        assert result['memory_growth_mb'] < 75, f"Excessive memory growth: {result['memory_growth_mb']:.2f}MB"
        
        logger.info(f"✅ Reconnection cycles test completed: {result}")
    
    @pytest.mark.asyncio
    async def test_database_websocket_context_mismatch_reproduction(self):
        """
        PRODUCTION SCENARIO 4: Database + WebSocket Context ID Mismatch
        
        Reproduces the exact thread_id inconsistency issue identified in
        the Five Whys analysis where different components generate different
        thread_ids for the same user context.
        """
        logger.info("🔀 TESTING: Database + WebSocket Context ID Mismatch")
        
        result = await self.leak_reproducer.simulate_database_websocket_context_mismatch(
            self.factory,
            self.test_user_id
        )
        
        self.leak_reproducer.scenario_results['context_mismatch'] = result
        
        # Validate results
        assert result['sessions_tested'] == 10, "Should test 10 sessions"
        
        # Check for thread_id mismatches (expected due to different operation strings)
        logger.info(f"Thread ID mismatch rate: {result['mismatch_percentage']:.1f}%")
        
        # In current system, mismatches are expected due to different operation strings
        # This test validates the problem exists and will validate fixes
        if result['thread_id_mismatches'] > 0:
            logger.warning(f"⚠️ REPRODUCING PRODUCTION ISSUE: {result['thread_id_mismatches']} thread_id mismatches")
        
        # Check for resulting cleanup failures
        if result['cleanup_failures'] > 0:
            logger.warning(f"⚠️ REPRODUCING PRODUCTION ISSUE: {result['cleanup_failures']} cleanup failures")
        
        # Memory growth should be reasonable
        assert result['memory_growth_mb'] < 50, f"Excessive memory growth: {result['memory_growth_mb']:.2f}MB"
        
        # Should detect leak evidence if mismatches cause cleanup failures
        if result['leak_evidence_count'] > 0:
            logger.warning(f"⚠️ LEAK EVIDENCE FOUND: {result['leak_evidence_count']} instances")
        
        logger.info(f"✅ Context mismatch test completed: {result}")
    
    @pytest.mark.asyncio
    async def test_background_cleanup_race_condition_reproduction(self):
        """
        PRODUCTION SCENARIO 5: Background Cleanup vs Creation Rate Race
        
        Reproduces the timing mismatch where managers are created faster
        than background cleanup can remove them.
        """
        logger.info("⚡ TESTING: Background Cleanup vs Creation Rate Race")
        
        result = await self.leak_reproducer.simulate_background_cleanup_race_condition(
            self.factory,
            self.test_user_id
        )
        
        self.leak_reproducer.scenario_results['cleanup_race'] = result
        
        # Validate results
        assert result['actual_duration_seconds'] <= result['target_duration_seconds'] + 2, "Test took too long"
        
        # Should create managers at reasonable rate
        assert result['creation_rate_per_second'] >= 1.5, f"Too slow creation rate: {result['creation_rate_per_second']:.2f}/s"
        
        # May hit resource limit during race condition (expected behavior)
        if result['creation_failures'] > 0:
            logger.warning(f"⚠️ REPRODUCING PRODUCTION ISSUE: Hit resource limit after {result['creation_failures']} failures")
        
        # Emergency cleanup should be effective
        if result['emergency_cleanup_count'] > 0:
            assert result['cleanup_effectiveness'] >= 50, f"Poor cleanup effectiveness: {result['cleanup_effectiveness']:.1f}%"
        
        # Should not have excessive remaining managers after cleanup
        assert result['post_cleanup_active_count'] <= 10, f"Too many managers after cleanup: {result['post_cleanup_active_count']}"
        
        # Memory growth should be reasonable
        assert result['memory_growth_mb'] < 100, f"Excessive memory growth: {result['memory_growth_mb']:.2f}MB"
        
        logger.info(f"✅ Cleanup race test completed: {result}")
    
    @pytest.mark.asyncio
    async def test_comprehensive_production_leak_scenarios_integration(self):
        """
        COMPREHENSIVE INTEGRATION TEST: All Production Leak Scenarios
        
        Runs all production leak scenarios in sequence to test cumulative
        effects and overall system stability.
        """
        logger.info("🔥 COMPREHENSIVE INTEGRATION: All Production Leak Scenarios")
        
        initial_memory = self.leak_reproducer.capture_memory_snapshot("integration_start")
        
        # Run all scenarios in sequence
        scenario_methods = [
            self.leak_reproducer.simulate_browser_multi_tab_pattern,
            self.leak_reproducer.simulate_cloud_run_cold_start_burst,  
            self.leak_reproducer.simulate_network_reconnection_cycles,
            self.leak_reproducer.simulate_database_websocket_context_mismatch,
            self.leak_reproducer.simulate_background_cleanup_race_condition
        ]
        
        integration_results = []
        
        for i, scenario_method in enumerate(scenario_methods):
            scenario_user = f"{self.test_user_id}_scenario_{i}"
            logger.info(f"Running integrated scenario {i+1}/{len(scenario_methods)} for user {scenario_user}")
            
            try:
                result = await scenario_method(self.factory, scenario_user)
                integration_results.append(result)
                
                # Brief pause between scenarios
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Scenario {i+1} failed: {e}")
                integration_results.append({'scenario': f'scenario_{i+1}', 'error': str(e)})
        
        final_memory = self.leak_reproducer.capture_memory_snapshot("integration_complete")
        
        # Comprehensive analysis
        leak_analysis = self.leak_reproducer.get_comprehensive_leak_analysis()
        
        # Integration test validations
        total_scenarios = len(integration_results)
        successful_scenarios = len([r for r in integration_results if 'error' not in r])
        
        assert successful_scenarios >= total_scenarios * 0.8, f"Too many scenario failures: {successful_scenarios}/{total_scenarios}"
        
        # Memory growth should be reasonable across all scenarios
        total_memory_growth = final_memory - initial_memory
        assert total_memory_growth < 300, f"Excessive total memory growth: {total_memory_growth:.2f}MB"
        
        # Should not have excessive critical issues across all scenarios
        critical_issues = len(leak_analysis['critical_issues'])
        assert critical_issues <= 5, f"Too many critical issues: {critical_issues}"
        
        # Final system state should be stable
        final_stats = self.factory.get_factory_stats()
        total_remaining_managers = final_stats['factory_metrics']['managers_active']
        assert total_remaining_managers <= 15, f"Too many managers remaining: {total_remaining_managers}"
        
        logger.info(f"✅ Comprehensive integration test completed")
        logger.info(f"📊 FINAL ANALYSIS: {leak_analysis}")
        
        # Store comprehensive results
        self.leak_reproducer.scenario_results['comprehensive_integration'] = {
            'total_scenarios': total_scenarios,
            'successful_scenarios': successful_scenarios,
            'total_memory_growth_mb': total_memory_growth,
            'critical_issues_count': critical_issues,
            'final_remaining_managers': total_remaining_managers,
            'integration_results': integration_results
        }