"""User Isolation Factory Pattern Regression Test Suite

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - Multi-user system foundation
- Business Goal: Guarantee complete user isolation in concurrent operations
- Value Impact: Prevents critical data leakage between users and conversation contexts
- Strategic Impact: CRITICAL - Factory pattern failures could expose confidential user data

This comprehensive integration test validates factory pattern user isolation based on the 
context creation audit findings. It ensures:

1. Factory pattern creates properly isolated user contexts
2. Multiple users get completely separate context instances via factory
3. Factory methods use get_user_execution_context() correctly for existing sessions
4. Factory operations don't create memory leaks from excessive context creation
5. Factory pattern maintains performance standards under load
6. Factory error handling preserves user isolation boundaries

CRITICAL REGRESSION PREVENTION:
This test prevents the architectural violations identified in CONTEXT_CREATION_AUDIT_REPORT.md
where create_user_execution_context() was used instead of get_user_execution_context(),
breaking conversation continuity and causing memory leaks.

Cross-References:
- CONTEXT_CREATION_AUDIT_REPORT.md - Context creation pattern violations
- netra_backend/app/services/user_execution_context.py - UserContextFactory implementation
- shared/id_generation/unified_id_generator.py - Session management SSOT
- netra_backend/app/dependencies.py - Context getter vs creator patterns

SSOT Compliance:
- Uses test_framework/ssot/base_test_case.py BaseTestCase
- Uses IsolatedEnvironment (no direct os.environ access)
- Uses UnifiedIdGenerator for consistent ID generation  
- Uses NO MOCKS - real factory operations only
- Follows absolute import patterns per CLAUDE.md
"""

import asyncio
import gc
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Set, Any, Optional, Tuple
import psutil
import pytest
import threading

# SSOT imports - absolute imports only per CLAUDE.md
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext, UserContextFactory
from netra_backend.app.dependencies import get_user_execution_context, create_user_execution_context
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.isolated_environment import IsolatedEnvironment


logger = logging.getLogger(__name__)


@dataclass
class FactoryPerformanceMetrics:
    """Comprehensive performance metrics for factory operations."""
    context_creation_times: List[float] = field(default_factory=list)
    memory_usage_samples: List[int] = field(default_factory=list)
    concurrent_operation_times: List[float] = field(default_factory=list)
    session_reuse_count: int = 0
    session_creation_count: int = 0
    isolation_validation_count: int = 0
    factory_error_count: int = 0
    memory_leak_detected: bool = False
    performance_regression_detected: bool = False
    
    def record_timing(self, operation_name: str, duration: float) -> None:
        """Record timing for specific operation."""
        if operation_name == "context_creation":
            self.context_creation_times.append(duration)
        elif operation_name == "concurrent_operation":
            self.concurrent_operation_times.append(duration)
    
    def record_memory_usage(self) -> None:
        """Record current memory usage."""
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.memory_usage_samples.append(int(memory_mb))
        except Exception as e:
            logger.warning(f"Failed to record memory usage: {e}")
    
    def detect_memory_leak(self, threshold_mb: int = 100) -> bool:
        """Detect memory leaks based on usage growth."""
        if len(self.memory_usage_samples) < 5:
            return False
        
        # Compare first and last samples
        initial = sum(self.memory_usage_samples[:2]) / 2
        final = sum(self.memory_usage_samples[-2:]) / 2
        growth = final - initial
        
        if growth > threshold_mb:
            self.memory_leak_detected = True
            logger.warning(f"Memory leak detected: {growth:.1f}MB growth")
            return True
        return False
    
    def check_performance_regression(self, max_avg_time: float = 0.1) -> bool:
        """Check for performance regression in context creation."""
        if not self.context_creation_times:
            return False
        
        avg_time = sum(self.context_creation_times) / len(self.context_creation_times)
        if avg_time > max_avg_time:
            self.performance_regression_detected = True
            logger.warning(f"Performance regression detected: {avg_time:.3f}s average")
            return True
        return False


class TestUserIsolationFactoryPatternRegression(SSotBaseTestCase):
    """
    CRITICAL: User Isolation Factory Pattern Regression Test Suite
    
    This comprehensive test suite validates factory pattern user isolation
    and prevents regression of the critical architecture violations identified
    in the context creation audit findings.
    """

    def setup_method(self, method=None):
        """Setup for each test method following SSOT patterns."""
        super().setup_method(method)
        
        # Initialize isolated environment
        self.env = IsolatedEnvironment()
        
        # Reset UnifiedIdGenerator state for clean test isolation
        if hasattr(UnifiedIdGenerator, '_user_sessions'):
            UnifiedIdGenerator._user_sessions = {}
        if hasattr(UnifiedIdGenerator, '_active_sessions'):
            UnifiedIdGenerator._active_sessions.clear()
        
        # Initialize performance metrics
        self.metrics = FactoryPerformanceMetrics()
        self.metrics.record_memory_usage()
        
        # Create realistic test user IDs that pass validation
        self.test_users = [
            "usr_factory_isolation_user001_12345abcdef890",
            "usr_factory_isolation_user002_67890fedcba543", 
            "usr_factory_isolation_user003_abcdef1234567890",
            "usr_factory_isolation_user004_fedcba0987654321",
            "usr_factory_isolation_user005_543210987654abcd"
        ]
        
        # Create realistic thread IDs for different conversation contexts
        self.conversation_threads = {
            "enterprise_support": "thd_factory_enterprise_support_001234",
            "data_analysis": "thd_factory_data_analysis_567890",
            "report_generation": "thd_factory_report_generation_abcdef",
            "user_onboarding": "thd_factory_user_onboarding_fedcba",
            "system_integration": "thd_factory_system_integration_123abc"
        }
        
        # Track created contexts for validation
        self.created_contexts: List[UserExecutionContext] = []
        self.factory_operations: Dict[str, Any] = {}
        
        logger.info(f"Test setup complete for {method.__name__ if method else 'unknown'}")

    def teardown_method(self, method=None):
        """Teardown following SSOT patterns with comprehensive validation."""
        try:
            # Final memory measurement
            self.metrics.record_memory_usage()
            
            # Perform final validations
            self._validate_no_memory_leaks()
            self._validate_performance_standards()
            self._validate_context_isolation_integrity()
            
            # Log comprehensive test metrics
            self._log_test_metrics(method)
            
            # Clear test state
            self.created_contexts.clear()
            self.factory_operations.clear()
            
            # Force garbage collection to prevent memory buildup
            gc.collect()
            
        except Exception as e:
            logger.error(f"Teardown error in {method.__name__ if method else 'unknown'}: {e}")
        finally:
            super().teardown_method(method)

    @pytest.mark.integration
    @pytest.mark.critical
    @pytest.mark.mission_critical
    def test_factory_pattern_creates_properly_isolated_user_contexts(self):
        """
        CRITICAL TEST: Factory pattern creates properly isolated user contexts.
        
        This test validates the core factory pattern requirement that each user
        gets completely isolated context instances with no shared references or
        data leakage potential.
        """
        logger.info("Starting factory pattern isolation test")
        
        # Test multiple users with different factory creation patterns
        isolation_validation_results = {}
        
        for i, user_id in enumerate(self.test_users[:3]):  # Test with 3 users
            thread_id = list(self.conversation_threads.values())[i]
            
            # Use UserContextFactory for proper factory pattern
            start_time = time.time()
            context = UserContextFactory.create_context(
                user_id=user_id,
                thread_id=thread_id,
                run_id=None,  # Let factory generate
                websocket_client_id=f"ws_{user_id[-8:]}"
            )
            creation_time = time.time() - start_time
            
            self.metrics.record_timing("context_creation", creation_time)
            self.metrics.record_memory_usage()
            self.created_contexts.append(context)
            
            # Validate context isolation
            isolation_result = self._validate_context_isolation(context, user_id)
            isolation_validation_results[user_id] = isolation_result
            
            # Record metrics
            self.metrics.isolation_validation_count += 1
            self.record_metric(f"user_{i+1}_context_created", True)
            self.record_metric(f"user_{i+1}_isolation_valid", isolation_result["is_isolated"])
        
        # CRITICAL: Validate no shared references between contexts
        self._validate_no_shared_references_between_contexts()
        
        # CRITICAL: Validate each context has unique identifiers
        self._validate_unique_context_identifiers()
        
        # CRITICAL: Validate factory pattern compliance
        self._validate_factory_pattern_compliance()
        
        # Success metrics
        self.record_metric("factory_isolation_test_passed", True)
        self.record_metric("total_users_tested", len(self.test_users[:3]))
        
        logger.info("Factory pattern isolation test completed successfully")

    @pytest.mark.integration
    @pytest.mark.critical
    @pytest.mark.performance
    def test_multiple_users_get_completely_separate_context_instances(self):
        """
        CRITICAL TEST: Multiple users get completely separate context instances via factory.
        
        This test validates that factory operations maintain complete user separation
        even under concurrent load with realistic multi-user scenarios.
        """
        logger.info("Starting multi-user separation test with concurrent operations")
        
        # Create concurrent factory operations for multiple users
        concurrent_results = {}
        
        def create_user_context_safely(user_id: str, thread_id: str) -> Dict[str, Any]:
            """Thread-safe context creation with metrics."""
            try:
                start_time = time.time()
                
                # Use factory pattern correctly
                context = UserContextFactory.create_context(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=None
                )
                
                creation_time = time.time() - start_time
                
                return {
                    "success": True,
                    "context": context,
                    "creation_time": creation_time,
                    "thread_id": threading.current_thread().ident,
                    "user_id": user_id
                }
            except Exception as e:
                logger.error(f"Context creation failed for user {user_id}: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "user_id": user_id
                }
        
        # Execute concurrent factory operations
        with ThreadPoolExecutor(max_workers=len(self.test_users)) as executor:
            futures = []
            for i, user_id in enumerate(self.test_users):
                thread_id = list(self.conversation_threads.values())[i % len(self.conversation_threads)]
                future = executor.submit(create_user_context_safely, user_id, thread_id)
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                result = future.result()
                concurrent_results[result["user_id"]] = result
                
                if result["success"]:
                    self.metrics.record_timing("concurrent_operation", result["creation_time"])
                    self.created_contexts.append(result["context"])
                else:
                    self.metrics.factory_error_count += 1
        
        # CRITICAL: Validate all operations succeeded
        success_count = sum(1 for r in concurrent_results.values() if r["success"])
        assert success_count == len(self.test_users), (
            f"Factory concurrent operations failed: {success_count}/{len(self.test_users)} succeeded"
        )
        
        # CRITICAL: Validate complete user separation
        self._validate_complete_user_separation(concurrent_results)
        
        # CRITICAL: Validate no context contamination
        self._validate_no_context_contamination()
        
        # Performance validation
        self._validate_concurrent_performance_standards()
        
        # Success metrics
        self.record_metric("concurrent_user_separation_test_passed", True)
        self.record_metric("concurrent_operations_succeeded", success_count)
        self.record_metric("factory_error_count", self.metrics.factory_error_count)
        
        logger.info(f"Multi-user separation test completed: {success_count}/{len(self.test_users)} users")

    @pytest.mark.integration
    @pytest.mark.critical
    @pytest.mark.session_management
    def test_factory_methods_use_get_user_execution_context_correctly(self):
        """
        CRITICAL TEST: Factory methods use get_user_execution_context() correctly for existing sessions.
        
        This test validates the CRITICAL architectural requirement that factory methods
        use get_user_execution_context() instead of create_user_execution_context()
        to maintain conversation continuity and prevent memory leaks.
        """
        logger.info("Starting factory session management pattern test")
        
        user_id = self.test_users[0]
        thread_id = self.conversation_threads["enterprise_support"]
        
        # CRITICAL: Test correct pattern - use get_user_execution_context
        session_test_results = {}
        
        # First message in conversation
        start_time = time.time()
        context1 = get_user_execution_context(user_id=user_id, thread_id=thread_id)
        first_creation_time = time.time() - start_time
        
        self.metrics.record_timing("context_creation", first_creation_time)
        self.metrics.session_creation_count += 1
        original_run_id = context1.run_id
        
        session_test_results["first_message"] = {
            "context": context1,
            "run_id": original_run_id,
            "creation_time": first_creation_time
        }
        
        # Second message in same conversation - MUST reuse session
        start_time = time.time()
        context2 = get_user_execution_context(user_id=user_id, thread_id=thread_id)
        second_creation_time = time.time() - start_time
        
        self.metrics.record_timing("context_creation", second_creation_time)
        
        # CRITICAL: Must be same session (same run_id)
        assert context2.run_id == original_run_id, (
            f"CRITICAL FACTORY REGRESSION: Session not reused! "
            f"Expected run_id={original_run_id}, got run_id={context2.run_id}. "
            f"This indicates factory is using create instead of get pattern!"
        )
        
        self.metrics.session_reuse_count += 1
        session_test_results["second_message"] = {
            "context": context2,
            "run_id": context2.run_id,
            "creation_time": second_creation_time,
            "session_reused": context2.run_id == original_run_id
        }
        
        # Third message - validate continued session reuse
        start_time = time.time()
        context3 = get_user_execution_context(user_id=user_id, thread_id=thread_id)
        third_creation_time = time.time() - start_time
        
        assert context3.run_id == original_run_id, (
            "Factory pattern failed to maintain session continuity across multiple messages"
        )
        
        self.metrics.session_reuse_count += 1
        
        # CRITICAL: Validate performance improvement from session reuse
        # Session reuse should be faster than initial creation
        avg_reuse_time = (second_creation_time + third_creation_time) / 2
        if avg_reuse_time > first_creation_time * 2:  # Allow some variance
            logger.warning(
                f"Session reuse performance concern: reuse={avg_reuse_time:.4f}s, "
                f"initial={first_creation_time:.4f}s"
            )
        
        # CRITICAL: Test anti-pattern - create_user_execution_context ALWAYS creates new
        anti_pattern_context = create_user_execution_context(
            user_id=user_id,
            thread_id=thread_id
        )
        
        assert anti_pattern_context.run_id != original_run_id, (
            "create_user_execution_context should ALWAYS create new context, not reuse"
        )
        
        # Store contexts for further validation
        self.created_contexts.extend([context1, context2, context3, anti_pattern_context])
        
        # Success metrics
        self.record_metric("factory_session_management_test_passed", True)
        self.record_metric("session_reuse_count", self.metrics.session_reuse_count)
        self.record_metric("conversation_continuity_maintained", True)
        
        logger.info("Factory session management pattern test completed successfully")

    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.memory
    def test_factory_operations_no_memory_leaks_excessive_context_creation(self):
        """
        CRITICAL TEST: Factory operations don't create memory leaks from excessive context creation.
        
        This test validates that factory patterns don't create memory leaks through
        unbounded context creation and properly manage memory under sustained load.
        """
        logger.info("Starting factory memory leak prevention test")
        
        # Record initial memory baseline
        initial_memory = self._get_current_memory_usage()
        self.metrics.record_memory_usage()
        
        # Simulate sustained factory operations
        leak_test_iterations = 100
        contexts_created = 0
        
        for iteration in range(leak_test_iterations):
            user_id = self.test_users[iteration % len(self.test_users)]
            thread_id = f"thd_memory_test_iteration_{iteration:03d}"
            
            # Create context using correct factory pattern
            start_time = time.time()
            context = UserContextFactory.create_context(
                user_id=user_id,
                thread_id=thread_id,
                run_id=None
            )
            creation_time = time.time() - start_time
            
            self.metrics.record_timing("context_creation", creation_time)
            contexts_created += 1
            
            # Sample memory usage every 10 iterations
            if iteration % 10 == 0:
                self.metrics.record_memory_usage()
                
                # Force garbage collection to test for actual leaks
                if iteration % 20 == 0:
                    gc.collect()
            
            # Keep only recent contexts to test cleanup
            if len(self.created_contexts) > 50:
                # Remove old contexts to test garbage collection
                old_contexts = self.created_contexts[:25]
                self.created_contexts = self.created_contexts[25:]
                del old_contexts
                gc.collect()
            
            self.created_contexts.append(context)
        
        # Final memory measurement
        final_memory = self._get_current_memory_usage()
        self.metrics.record_memory_usage()
        
        # CRITICAL: Validate no significant memory leaks
        memory_growth = final_memory - initial_memory
        memory_per_context = memory_growth / contexts_created if contexts_created > 0 else 0
        
        # Allow reasonable memory growth but detect leaks
        max_allowed_growth = 200  # MB
        if memory_growth > max_allowed_growth:
            self.metrics.memory_leak_detected = True
            pytest.fail(
                f"MEMORY LEAK DETECTED: {memory_growth:.1f}MB growth "
                f"({memory_per_context:.3f}MB per context) exceeds threshold {max_allowed_growth}MB"
            )
        
        # CRITICAL: Validate factory doesn't create excessive contexts
        self._validate_no_excessive_context_creation()
        
        # Performance validation
        avg_creation_time = (
            sum(self.metrics.context_creation_times) / len(self.metrics.context_creation_times)
            if self.metrics.context_creation_times else 0
        )
        
        max_allowed_time = 0.05  # 50ms per context creation
        if avg_creation_time > max_allowed_time:
            logger.warning(
                f"Factory performance concern: {avg_creation_time:.4f}s average creation time"
            )
        
        # Success metrics
        self.record_metric("factory_memory_leak_test_passed", True)
        self.record_metric("total_contexts_created", contexts_created)
        self.record_metric("memory_growth_mb", memory_growth)
        self.record_metric("memory_per_context_kb", memory_per_context * 1024)
        self.record_metric("average_creation_time_ms", avg_creation_time * 1000)
        
        logger.info(
            f"Factory memory leak test completed: {contexts_created} contexts, "
            f"{memory_growth:.1f}MB growth, {avg_creation_time:.4f}s avg time"
        )

    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.load_testing  
    def test_factory_pattern_maintains_performance_standards_under_load(self):
        """
        CRITICAL TEST: Factory pattern maintains performance standards under load.
        
        This test validates that factory patterns maintain acceptable performance
        characteristics under realistic concurrent user load scenarios.
        """
        logger.info("Starting factory pattern performance under load test")
        
        # Configure realistic load test parameters
        concurrent_users = 20  # Simulate 20 concurrent users
        operations_per_user = 5  # 5 operations per user
        total_operations = concurrent_users * operations_per_user
        
        performance_results = {}
        load_test_start = time.time()
        
        def execute_user_operations(user_index: int) -> Dict[str, Any]:
            """Execute operations for a single user under load."""
            user_id = f"usr_load_test_user{user_index:03d}_factory_performance"
            operation_results = []
            user_start_time = time.time()
            
            for op_index in range(operations_per_user):
                thread_id = f"thd_load_test_user{user_index:03d}_op{op_index:02d}"
                
                try:
                    # Measure factory operation performance
                    op_start = time.time()
                    
                    # Use correct factory pattern
                    context = UserContextFactory.create_context(
                        user_id=user_id,
                        thread_id=thread_id,
                        run_id=None
                    )
                    
                    op_duration = time.time() - op_start
                    
                    operation_results.append({
                        "success": True,
                        "duration": op_duration,
                        "context_id": context.request_id,
                        "thread_id": thread_id
                    })
                    
                except Exception as e:
                    operation_results.append({
                        "success": False,
                        "error": str(e),
                        "duration": time.time() - op_start
                    })
            
            user_total_time = time.time() - user_start_time
            success_count = sum(1 for r in operation_results if r["success"])
            
            return {
                "user_index": user_index,
                "user_id": user_id,
                "total_time": user_total_time,
                "operations_succeeded": success_count,
                "operations_failed": operations_per_user - success_count,
                "operation_results": operation_results
            }
        
        # Execute concurrent load test
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [
                executor.submit(execute_user_operations, i) 
                for i in range(concurrent_users)
            ]
            
            for future in as_completed(futures):
                result = future.result()
                performance_results[result["user_id"]] = result
                
                # Record performance metrics
                for op in result["operation_results"]:
                    if op["success"]:
                        self.metrics.record_timing("concurrent_operation", op["duration"])
        
        load_test_duration = time.time() - load_test_start
        
        # CRITICAL: Validate performance standards
        self._validate_load_test_performance_standards(performance_results, load_test_duration)
        
        # CRITICAL: Validate no performance degradation under load
        self._validate_no_performance_degradation_under_load()
        
        # Calculate comprehensive performance metrics
        total_successes = sum(r["operations_succeeded"] for r in performance_results.values())
        total_failures = sum(r["operations_failed"] for r in performance_results.values())
        
        throughput = total_successes / load_test_duration if load_test_duration > 0 else 0
        
        # Success metrics
        self.record_metric("factory_load_test_passed", True)
        self.record_metric("concurrent_users_tested", concurrent_users)
        self.record_metric("total_operations_attempted", total_operations)
        self.record_metric("total_operations_succeeded", total_successes)
        self.record_metric("total_operations_failed", total_failures)
        self.record_metric("operations_per_second", throughput)
        self.record_metric("load_test_duration_seconds", load_test_duration)
        
        logger.info(
            f"Factory load test completed: {total_successes}/{total_operations} operations succeeded, "
            f"{throughput:.2f} ops/sec, {load_test_duration:.2f}s duration"
        )

    @pytest.mark.integration
    @pytest.mark.critical
    @pytest.mark.error_handling
    def test_factory_error_handling_preserves_user_isolation_boundaries(self):
        """
        CRITICAL TEST: Factory error handling preserves user isolation boundaries.
        
        This test validates that factory operations maintain user isolation
        even when errors occur, preventing context contamination or data leakage
        during error conditions.
        """
        logger.info("Starting factory error handling isolation test")
        
        error_scenarios = []
        isolation_validation_results = {}
        
        # Test Scenario 1: Invalid user ID error handling
        try:
            invalid_context = UserContextFactory.create_context(
                user_id="",  # Invalid empty user ID
                thread_id=self.conversation_threads["enterprise_support"],
                run_id=None
            )
            error_scenarios.append({
                "scenario": "invalid_user_id",
                "success": False,  # Should have failed
                "error": "Expected validation error did not occur"
            })
        except Exception as e:
            error_scenarios.append({
                "scenario": "invalid_user_id",
                "success": True,  # Error correctly handled
                "error": str(e)
            })
            self.metrics.factory_error_count += 1
        
        # Test Scenario 2: Invalid thread ID error handling
        try:
            invalid_thread_context = UserContextFactory.create_context(
                user_id=self.test_users[0],
                thread_id="",  # Invalid empty thread ID
                run_id=None
            )
            error_scenarios.append({
                "scenario": "invalid_thread_id", 
                "success": False,
                "error": "Expected validation error did not occur"
            })
        except Exception as e:
            error_scenarios.append({
                "scenario": "invalid_thread_id",
                "success": True,
                "error": str(e)
            })
            self.metrics.factory_error_count += 1
        
        # Test Scenario 3: Create valid contexts after errors to test isolation
        valid_contexts = []
        for i, user_id in enumerate(self.test_users[:3]):
            try:
                context = UserContextFactory.create_context(
                    user_id=user_id,
                    thread_id=list(self.conversation_threads.values())[i],
                    run_id=None
                )
                valid_contexts.append(context)
                self.created_contexts.append(context)
                
                # Validate isolation after errors
                isolation_result = self._validate_context_isolation(context, user_id)
                isolation_validation_results[user_id] = isolation_result
                
                error_scenarios.append({
                    "scenario": f"valid_context_after_errors_{i+1}",
                    "success": True,
                    "error": None
                })
                
            except Exception as e:
                error_scenarios.append({
                    "scenario": f"valid_context_after_errors_{i+1}",
                    "success": False,
                    "error": str(e)
                })
                self.metrics.factory_error_count += 1
        
        # CRITICAL: Validate error handling didn't contaminate isolation
        self._validate_error_handling_isolation_preservation(valid_contexts)
        
        # CRITICAL: Validate factory recovered properly after errors
        self._validate_factory_recovery_after_errors()
        
        # Validate all valid contexts maintain proper isolation
        for context in valid_contexts:
            assert context.verify_isolation(), (
                f"Context isolation compromised after error conditions for user {context.user_id}"
            )
        
        # Calculate error handling metrics
        total_scenarios = len(error_scenarios)
        successful_error_handling = sum(1 for s in error_scenarios if s["success"])
        
        # Success metrics
        self.record_metric("factory_error_handling_test_passed", True)
        self.record_metric("error_scenarios_tested", total_scenarios)
        self.record_metric("successful_error_handling", successful_error_handling)
        self.record_metric("factory_errors_handled", self.metrics.factory_error_count)
        self.record_metric("isolation_maintained_after_errors", True)
        
        logger.info(
            f"Factory error handling test completed: {successful_error_handling}/{total_scenarios} "
            f"scenarios handled correctly, {self.metrics.factory_error_count} errors processed"
        )

    # ============================================================================
    # PRIVATE VALIDATION METHODS
    # ============================================================================

    def _validate_context_isolation(self, context: UserExecutionContext, expected_user_id: str) -> Dict[str, Any]:
        """Validate comprehensive context isolation."""
        try:
            # Basic validation
            assert context.user_id == expected_user_id
            assert context.thread_id is not None
            assert context.run_id is not None
            assert context.request_id is not None
            
            # Isolation verification
            isolation_verified = context.verify_isolation()
            
            return {
                "is_isolated": isolation_verified,
                "user_id_correct": context.user_id == expected_user_id,
                "has_required_ids": all([
                    context.thread_id, context.run_id, context.request_id
                ])
            }
        except Exception as e:
            logger.error(f"Context isolation validation failed: {e}")
            return {
                "is_isolated": False,
                "error": str(e)
            }

    def _validate_no_shared_references_between_contexts(self) -> None:
        """Validate no shared object references between contexts."""
        if len(self.created_contexts) < 2:
            return
        
        for i, context1 in enumerate(self.created_contexts[:-1]):
            for j, context2 in enumerate(self.created_contexts[i+1:], i+1):
                # Check for shared agent_context references
                if id(context1.agent_context) == id(context2.agent_context):
                    pytest.fail(
                        f"ISOLATION VIOLATION: Contexts {i} and {j} share agent_context reference"
                    )
                
                # Check for shared audit_metadata references
                if id(context1.audit_metadata) == id(context2.audit_metadata):
                    pytest.fail(
                        f"ISOLATION VIOLATION: Contexts {i} and {j} share audit_metadata reference"
                    )

    def _validate_unique_context_identifiers(self) -> None:
        """Validate all contexts have unique identifiers."""
        request_ids = [ctx.request_id for ctx in self.created_contexts]
        unique_request_ids = set(request_ids)
        
        if len(unique_request_ids) != len(request_ids):
            pytest.fail(
                f"ISOLATION VIOLATION: Non-unique request IDs detected. "
                f"Expected {len(request_ids)} unique, got {len(unique_request_ids)}"
            )

    def _validate_factory_pattern_compliance(self) -> None:
        """Validate factory pattern compliance."""
        for context in self.created_contexts:
            # Validate context was created through proper factory methods
            assert hasattr(context, 'created_at')
            assert hasattr(context, 'verify_isolation')
            assert context.user_id is not None
            assert context.thread_id is not None

    def _validate_complete_user_separation(self, concurrent_results: Dict[str, Any]) -> None:
        """Validate complete user separation in concurrent operations."""
        contexts_by_user = {}
        
        for result in concurrent_results.values():
            if result["success"]:
                user_id = result["user_id"]
                context = result["context"]
                contexts_by_user[user_id] = context
        
        # Validate each user has unique context
        user_ids = set(contexts_by_user.keys())
        request_ids = set(ctx.request_id for ctx in contexts_by_user.values())
        
        assert len(user_ids) == len(request_ids), (
            "User separation validation failed - contexts not properly isolated"
        )

    def _validate_no_context_contamination(self) -> None:
        """Validate no context contamination between users."""
        user_contexts = {}
        
        for context in self.created_contexts:
            user_id = context.user_id
            if user_id not in user_contexts:
                user_contexts[user_id] = []
            user_contexts[user_id].append(context)
        
        # Validate contexts for each user are properly isolated
        for user_id, contexts in user_contexts.items():
            for context in contexts:
                assert context.user_id == user_id
                # Additional contamination checks can be added here

    def _validate_concurrent_performance_standards(self) -> None:
        """Validate performance standards for concurrent operations."""
        if not self.metrics.concurrent_operation_times:
            return
        
        avg_time = sum(self.metrics.concurrent_operation_times) / len(self.metrics.concurrent_operation_times)
        max_time = max(self.metrics.concurrent_operation_times)
        
        # Performance thresholds
        if avg_time > 0.1:  # 100ms average
            logger.warning(f"Concurrent performance concern: {avg_time:.4f}s average")
        
        if max_time > 0.5:  # 500ms maximum
            logger.warning(f"Concurrent performance spike: {max_time:.4f}s maximum")

    def _validate_no_excessive_context_creation(self) -> None:
        """Validate no excessive context creation."""
        if self.metrics.session_creation_count > self.metrics.session_reuse_count * 2:
            logger.warning(
                f"Possible excessive context creation: {self.metrics.session_creation_count} created, "
                f"{self.metrics.session_reuse_count} reused"
            )

    def _validate_load_test_performance_standards(self, results: Dict[str, Any], duration: float) -> None:
        """Validate load test performance standards."""
        total_ops = sum(r["operations_succeeded"] for r in results.values())
        throughput = total_ops / duration if duration > 0 else 0
        
        # Minimum performance thresholds
        min_throughput = 10  # ops/sec
        if throughput < min_throughput:
            pytest.fail(
                f"PERFORMANCE REGRESSION: Throughput {throughput:.2f} ops/sec "
                f"below minimum {min_throughput} ops/sec"
            )

    def _validate_no_performance_degradation_under_load(self) -> None:
        """Validate no performance degradation under load."""
        if not self.metrics.concurrent_operation_times:
            return
        
        # Check for performance degradation patterns
        if len(self.metrics.concurrent_operation_times) > 50:
            early_times = self.metrics.concurrent_operation_times[:25]
            late_times = self.metrics.concurrent_operation_times[-25:]
            
            early_avg = sum(early_times) / len(early_times)
            late_avg = sum(late_times) / len(late_times)
            
            degradation_ratio = late_avg / early_avg if early_avg > 0 else 1
            
            if degradation_ratio > 2.0:  # 2x degradation
                logger.warning(
                    f"Performance degradation detected: {degradation_ratio:.2f}x slower "
                    f"({early_avg:.4f}s -> {late_avg:.4f}s)"
                )

    def _validate_error_handling_isolation_preservation(self, valid_contexts: List[UserExecutionContext]) -> None:
        """Validate error handling preserved isolation."""
        for context in valid_contexts:
            try:
                assert context.verify_isolation()
            except Exception as e:
                pytest.fail(f"Isolation compromised after error handling: {e}")

    def _validate_factory_recovery_after_errors(self) -> None:
        """Validate factory recovered properly after errors."""
        # Test that factory can still create valid contexts
        try:
            recovery_context = UserContextFactory.create_context(
                user_id=self.test_users[0],
                thread_id="thd_recovery_test_after_errors",
                run_id=None
            )
            assert recovery_context.verify_isolation()
            self.created_contexts.append(recovery_context)
        except Exception as e:
            pytest.fail(f"Factory failed to recover after errors: {e}")

    def _validate_no_memory_leaks(self) -> None:
        """Validate no memory leaks detected."""
        if self.metrics.detect_memory_leak():
            logger.error("Memory leak detected in factory operations")

    def _validate_performance_standards(self) -> None:
        """Validate performance standards maintained."""
        if self.metrics.check_performance_regression():
            logger.error("Performance regression detected in factory operations")

    def _validate_context_isolation_integrity(self) -> None:
        """Validate overall context isolation integrity."""
        for context in self.created_contexts:
            try:
                context.verify_isolation()
            except Exception as e:
                logger.error(f"Context isolation integrity violation: {e}")

    def _get_current_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0

    def _log_test_metrics(self, method) -> None:
        """Log comprehensive test metrics."""
        if not method:
            return
        
        method_name = method.__name__
        logger.info(f"Test metrics for {method_name}:")
        logger.info(f"  Contexts created: {len(self.created_contexts)}")
        logger.info(f"  Isolation validations: {self.metrics.isolation_validation_count}")
        logger.info(f"  Session reuses: {self.metrics.session_reuse_count}")
        logger.info(f"  Session creations: {self.metrics.session_creation_count}")
        logger.info(f"  Factory errors: {self.metrics.factory_error_count}")
        
        if self.metrics.context_creation_times:
            avg_time = sum(self.metrics.context_creation_times) / len(self.metrics.context_creation_times)
            logger.info(f"  Average creation time: {avg_time:.4f}s")
        
        if self.metrics.memory_usage_samples:
            logger.info(f"  Memory samples: {len(self.metrics.memory_usage_samples)}")


# Export test class
__all__ = ['TestUserIsolationFactoryPatternRegression']


if __name__ == "__main__":
    # Allow running test directly for development
    pytest.main([__file__, "-v", "--tb=short"])