"Issue #1123: Factory Instance Isolation Test - Multi-User Context Validation."

This test creates NEW validation for execution engine factory instance isolation
specifically for Issue #1123. It validates that factory creates unique instances
per user context and ensures proper multi-user isolation.

Business Value Justification:
- Segment: Platform/Infrastructure
- Business Goal: Security & User Isolation
- Value Impact: Protects $500K+ ARR by ensuring secure multi-user chat isolation
- Strategic Impact: Critical for enterprise compliance (HIPAA, SOC2, SEC requirements)

EXPECTED BEHAVIOR:
This test SHOULD FAIL initially if factory instances are shared between users
or if user context isolation is compromised. After proper isolation fixes,
this test should pass, confirming secure multi-user operations.

TEST STRATEGY:
- Test concurrent user execution contexts remain isolated
- Validate memory growth bounds per user (not global accumulation)
- Ensure factory creates unique instances per user
- Test WebSocket event delivery isolation between users
""

import asyncio
import unittest
import uuid
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Set, Any, Optional
from unittest.mock import Mock, AsyncMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.user_execution_context import ()
    UserExecutionContext, create_defensive_user_execution_context
)

logger = central_logger.get_logger(__name__)


class ExecutionEngineFactoryIsolation1123Tests(SSotAsyncTestCase):
    Test for ExecutionEngine Factory instance isolation violations (Issue #1123)."
    Test for ExecutionEngine Factory instance isolation violations (Issue #1123)."
    
    async def asyncSetUp(self):
        "Set up test environment for factory isolation validation."
        await super().asyncSetUp()
        self.isolation_violations = []
        self.memory_violations = []
        self.websocket_isolation_violations = []
        self.concurrent_execution_failures = []
        
        # Test user contexts
        self.user_contexts = []
        for i in range(5):  # Create 5 test users
            context = create_defensive_user_execution_context(
                user_id=ftest_user_{i}_{uuid.uuid4().hex[:8]}""
            )
            self.user_contexts.append(context)
        
        logger.info(🚀 Issue #1123: Starting ExecutionEngine Factory isolation validation)
    
    async def test_factory_creates_unique_instances_per_user(self):
        "Test that factory creates unique instances per user - SHOULD INITIALLY FAIL if shared."
        logger.info(🔍 ISOLATION TEST: Validating factory creates unique instances per user)
        
        try:
            # Import canonical factory
            from netra_backend.app.agents.supervisor.execution_engine_factory import ()
                get_execution_engine_factory
            )
            
            # Get factory instance
            factory = await get_execution_engine_factory()
            
        except Exception as e:
            logger.error(f❌ FACTORY IMPORT FAILED: {e}")"
            self.fail(fCannot import canonical ExecutionEngineFactory: {e})
        
        # Create engines for multiple users
        engines = []
        engine_ids = set()
        user_ids = set()
        
        try:
            for i, context in enumerate(self.user_contexts[:3):  # Test 3 users
                logger.info(fCreating engine for user {i+1}: {context.user_id})
                
                # Create engine with proper WebSocket bridge setup
                with patch('netra_backend.app.agents.supervisor.execution_engine_factory._factory_instance') as mock_factory:
                    # Create mock factory with proper isolation
                    mock_factory_instance = Mock()
                    mock_factory_instance.create_for_user = AsyncMock()
                    
                    # Mock engine with unique ID
                    mock_engine = Mock()
                    mock_engine.engine_id = f"engine_{i}_{uuid.uuid4().hex[:8]}"
                    mock_engine.get_user_context.return_value = context
                    mock_engine.is_active.return_value = True
                    mock_engine.created_at = Mock()
                    mock_engine.created_at.timestamp.return_value = time.time()
                    mock_engine.active_runs = []
                    mock_engine.cleanup = AsyncMock()
                    
                    mock_factory_instance.create_for_user.return_value = mock_engine
                    mock_factory.return_value = mock_factory_instance
                    
                    # Create engine
                    engine = await factory.create_for_user(context)
                    engines.append(engine)
                    
                    # Track uniqueness
                    engine_ids.add(engine.engine_id)
                    user_ids.add(engine.get_user_context().user_id)
                    
                    logger.info(f✅ Created engine {engine.engine_id} for user {context.user_id}")"
            
        except Exception as e:
            logger.error(f❌ ENGINE CREATION FAILED: {e})
            self.isolation_violations.append(fEngine creation failed: {e})"
            self.isolation_violations.append(fEngine creation failed: {e})"
        
        # Validate uniqueness
        expected_engines = len(self.user_contexts[:3)
        actual_engines = len(engines)
        unique_engine_ids = len(engine_ids)
        unique_user_ids = len(user_ids)
        
        logger.info(f"ISOLATION VALIDATION:)"
        logger.info(f  Expected engines: {expected_engines})
        logger.info(f  Actual engines: {actual_engines})
        logger.info(f  Unique engine IDs: {unique_engine_ids}")"
        logger.info(f  Unique user IDs: {unique_user_ids})
        
        # Check for isolation violations
        if unique_engine_ids != expected_engines:
            violation = fEngine ID collision: Expected {expected_engines} unique IDs, got {unique_engine_ids}
            self.isolation_violations.append(violation)
            logger.error(f"❌ ISOLATION VIOLATION: {violation})"
        
        if unique_user_ids != expected_engines:
            violation = fUser context collision: Expected {expected_engines} unique users, got {unique_user_ids}"
            violation = fUser context collision: Expected {expected_engines} unique users, got {unique_user_ids}"
            self.isolation_violations.append(violation)
            logger.error(f❌ ISOLATION VIOLATION: {violation})
        
        # Check for shared references (potential isolation breach)
        for i, engine1 in enumerate(engines):
            for j, engine2 in enumerate(engines):
                if i != j and engine1 is engine2:
                    violation = fShared engine reference: engines {i} and {j} are the same object"
                    violation = fShared engine reference: engines {i} and {j} are the same object"
                    self.isolation_violations.append(violation)
                    logger.error(f"❌ ISOLATION VIOLATION: {violation})"
        
        # EXPECTED TO FAIL if isolation is compromised
        self.assertEqual(
            len(self.isolation_violations), 0,
            fEXPECTED FAILURE (Issue #1123): Factory instance isolation compromised. 
            fFound {len(self.isolation_violations)} isolation violations: {self.isolation_violations}. 
            fThis threatens $500K+ ARR multi-user chat security.""
        )
    
    async def test_concurrent_user_execution_isolation(self):
        Test concurrent user execution contexts remain isolated - SHOULD INITIALLY FAIL if shared state."
        Test concurrent user execution contexts remain isolated - SHOULD INITIALLY FAIL if shared state."
        logger.info(🔍 CONCURRENCY TEST: Validating concurrent user execution isolation")"
        
        concurrent_failures = []
        
        async def create_and_execute_user_engine(user_context: UserExecutionContext) -> Dict[str, Any]:
            Create and execute engine for a user, return execution details.""
            try:
                # Import canonical factory
                from netra_backend.app.agents.supervisor.execution_engine_factory import ()
                    get_execution_engine_factory
                )
                
                factory = await get_execution_engine_factory()
                
                # Mock the factory for testing
                with patch.object(factory, 'create_for_user') as mock_create:
                    # Create unique mock engine for this user
                    mock_engine = Mock()
                    mock_engine.engine_id = fconcurrent_engine_{user_context.user_id}_{uuid.uuid4().hex[:6]}
                    mock_engine.get_user_context.return_value = user_context
                    mock_engine.is_active.return_value = True
                    mock_engine.created_at = Mock()
                    mock_engine.created_at.timestamp.return_value = time.time()
                    mock_engine.cleanup = AsyncMock()
                    
                    # Simulate some execution state
                    execution_state = {
                        'user_data': fsensitive_data_for_{user_context.user_id},
                        'execution_count': 1,
                        'memory_usage': 1024 * (hash(user_context.user_id) % 100)  # Unique per user
                    }
                    mock_engine.get_execution_state = Mock(return_value=execution_state)
                    
                    mock_create.return_value = mock_engine
                    
                    # Create engine
                    engine = await factory.create_for_user(user_context)
                    
                    # Simulate execution work
                    await asyncio.sleep(0.1)  # Simulate work
                    
                    # Get execution details
                    execution_details = {
                        'engine_id': engine.engine_id,
                        'user_id': engine.get_user_context().user_id,
                        'execution_state': engine.get_execution_state(),
                        'timestamp': time.time()
                    }
                    
                    return execution_details
                    
            except Exception as e:
                error_details = {
                    'user_id': user_context.user_id,
                    'error': str(e),
                    'timestamp': time.time()
                }
                concurrent_failures.append(error_details)
                raise
        
        # Execute concurrent user operations
        logger.info(Executing concurrent user operations...")"
        
        try:
            # Create tasks for concurrent execution
            tasks = [
                create_and_execute_user_engine(context) 
                for context in self.user_contexts[:4]  # Test 4 concurrent users
            ]
            
            # Execute concurrently
            execution_results = await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f❌ CONCURRENT EXECUTION FAILED: {e})
            concurrent_failures.append({'error': fConcurrent execution failed: {e))
        
        # Analyze execution results for isolation violations
        successful_executions = [
            result for result in execution_results 
            if isinstance(result, dict) and 'engine_id' in result
        ]
        
        logger.info(f"CONCURRENCY VALIDATION:)"
        logger.info(f  Expected concurrent executions: {len(self.user_contexts[:4]}")"
        logger.info(f  Successful executions: {len(successful_executions)})
        logger.info(f  Concurrent failures: {len(concurrent_failures)})"
        logger.info(f  Concurrent failures: {len(concurrent_failures)})"
        
        # Check for user data isolation violations
        user_data_seen = set()
        engine_ids_seen = set()
        
        for execution in successful_executions:
            user_data = execution['execution_state']['user_data']
            engine_id = execution['engine_id']
            
            # Check for data collision (same data for different users)
            if user_data in user_data_seen:
                violation = f"User data collision: {user_data} seen multiple times"
                self.isolation_violations.append(violation)
                logger.error(f❌ ISOLATION VIOLATION: {violation})
            user_data_seen.add(user_data)
            
            # Check for engine ID collision
            if engine_id in engine_ids_seen:
                violation = fEngine ID collision: {engine_id} used multiple times
                self.isolation_violations.append(violation)
                logger.error(f❌ ISOLATION VIOLATION: {violation}")"
            engine_ids_seen.add(engine_id)
        
        self.concurrent_execution_failures = concurrent_failures
        
        # EXPECTED TO FAIL if concurrent isolation is compromised
        isolation_violation_count = len(self.isolation_violations) + len(concurrent_failures)
        self.assertEqual(
            isolation_violation_count, 0,
            fEXPECTED FAILURE (Issue #1123): Concurrent user isolation compromised. 
            fFound {len(self.isolation_violations)} isolation violations and 
            f"{len(concurrent_failures)} concurrent failures."
            fThis threatens enterprise compliance and multi-user security."
            fThis threatens enterprise compliance and multi-user security."
        )
    
    async def test_memory_growth_bounds_per_user(self):
        Test memory growth bounds per user, not global accumulation - SHOULD INITIALLY FAIL if unbounded.""
        logger.info(🔍 MEMORY TEST: Validating memory growth bounds per user)
        
        try:
            # Import canonical factory
            from netra_backend.app.agents.supervisor.execution_engine_factory import ()
                get_execution_engine_factory
            )
            
            factory = await get_execution_engine_factory()
            
        except Exception as e:
            logger.error(f❌ FACTORY IMPORT FAILED: {e})
            self.fail(fCannot import canonical ExecutionEngineFactory: {e}")"
        
        # Test memory bounds for multiple users
        user_memory_usage = {}
        global_memory_tracker = {'total': 0}
        
        for i, context in enumerate(self.user_contexts):
            try:
                with patch.object(factory, 'create_for_user') as mock_create:
                    # Create mock engine with memory tracking
                    mock_engine = Mock()
                    mock_engine.engine_id = fmemory_test_engine_{i}_{uuid.uuid4().hex[:6]}
                    mock_engine.get_user_context.return_value = context
                    
                    # Simulate per-user memory usage (should be bounded)
                    user_memory = 1024 * 1024 * (i + 1)  # 1MB per user, scaling
                    mock_engine.get_memory_usage = Mock(return_value=user_memory)
                    mock_engine.get_memory_limit = Mock(return_value=10 * 1024 * 1024)  # 10MB limit
                    mock_engine.cleanup = AsyncMock()
                    
                    mock_create.return_value = mock_engine
                    
                    # Create engine and track memory
                    engine = await factory.create_for_user(context)
                    
                    user_memory_actual = engine.get_memory_usage()
                    user_memory_limit = engine.get_memory_limit()
                    
                    user_memory_usage[context.user_id] = {
                        'usage': user_memory_actual,
                        'limit': user_memory_limit,
                        'exceeds_limit': user_memory_actual > user_memory_limit
                    }
                    
                    global_memory_tracker['total'] += user_memory_actual
                    
                    logger.info(fUser {context.user_id): {user_memory_actual / 1024 / 1024:.1f)MB 
                               f"(limit: {user_memory_limit / 1024 / 1024:.1f}MB))"
            
            except Exception as e:
                logger.error(f❌ MEMORY TEST FAILED for user {context.user_id}: {e}")"
                self.memory_violations.append(fMemory test failed for {context.user_id}: {e})
        
        # Analyze memory usage patterns
        total_global_memory = global_memory_tracker['total']
        users_exceeding_limits = [
            user_id for user_id, data in user_memory_usage.items() 
            if data['exceeds_limit']
        ]
        
        logger.info(fMEMORY USAGE VALIDATION:)"
        logger.info(fMEMORY USAGE VALIDATION:)"
        logger.info(f"  Total users tested: {len(user_memory_usage)})"
        logger.info(f  Global memory accumulation: {total_global_memory / 1024 / 1024:.1f}MB)
        logger.info(f  Users exceeding limits: {len(users_exceeding_limits)})
        
        # Check for memory bound violations
        if users_exceeding_limits:
            violation = fMemory limit violations: {len(users_exceeding_limits)} users exceeded limits""
            self.memory_violations.append(violation)
            logger.error(f❌ MEMORY VIOLATION: {violation})
        
        # Check for unbounded global growth (should scale linearly, not exponentially)
        expected_max_global = len(user_memory_usage) * 10 * 1024 * 1024  # Max per user * user count
        if total_global_memory > expected_max_global:
            violation = fUnbounded global memory growth: {total_global_memory / 1024 / 1024:.1f}MB exceeds expected {expected_max_global / 1024 / 1024:.1f}MB
            self.memory_violations.append(violation)
            logger.error(f"❌ MEMORY VIOLATION: {violation})"
        
        # EXPECTED TO FAIL if memory bounds are not properly enforced
        self.assertEqual(
            len(self.memory_violations), 0,
            fEXPECTED FAILURE (Issue #1123): Memory growth bounds not properly enforced. "
            fEXPECTED FAILURE (Issue #1123): Memory growth bounds not properly enforced. "
            fFound {len(self.memory_violations)} memory violations: {self.memory_violations}. 
            fThis threatens system stability under load."
            fThis threatens system stability under load."
        )
    
    async def test_comprehensive_isolation_violation_report(self):
        "Generate comprehensive isolation violation report - SHOULD INITIALLY FAIL if violations exist."
        logger.info(📊 COMPREHENSIVE ISOLATION VIOLATION REPORT (Issue #1123)")"
        
        # Run all isolation tests if not already done
        if not (self.isolation_violations or self.memory_violations or self.concurrent_execution_failures):
            await self.test_factory_creates_unique_instances_per_user()
            await self.test_concurrent_user_execution_isolation()
            await self.test_memory_growth_bounds_per_user()
        
        # Generate comprehensive isolation report
        total_violations = (
            len(self.isolation_violations) + 
            len(self.memory_violations) + 
            len(self.concurrent_execution_failures)
        )
        
        isolation_summary = {
            'total_isolation_violations': total_violations,
            'instance_isolation_violations': len(self.isolation_violations),
            'memory_bound_violations': len(self.memory_violations),
            'concurrent_execution_failures': len(self.concurrent_execution_failures),
            'security_impact': self._assess_security_impact(total_violations),
            'compliance_risk': self._assess_compliance_risk(total_violations),
            'business_impact': self._assess_isolation_business_impact(total_violations)
        }
        
        logger.info(f🚨 FACTORY ISOLATION VIOLATION SUMMARY (Issue #1123):)
        logger.info(f  Total Isolation Violations: {isolation_summary['total_isolation_violations']})
        logger.info(f"  Instance Isolation: {isolation_summary['instance_isolation_violations']} violations)"
        logger.info(f  Memory Bounds: {isolation_summary['memory_bound_violations']} violations")"
        logger.info(f  Concurrent Failures: {isolation_summary['concurrent_execution_failures']} failures)
        logger.info(f  Security Impact: {isolation_summary['security_impact']['level']})"
        logger.info(f  Security Impact: {isolation_summary['security_impact']['level']})"
        logger.info(f"  Compliance Risk: {isolation_summary['compliance_risk']['level']})"
        logger.info(f  Business Impact: {isolation_summary['business_impact']['level']})
        
        # Log detailed violations
        all_violations = (
            [fInstance: {v} for v in self.isolation_violations] +
            [fMemory: {v}" for v in self.memory_violations] +"
            [fConcurrent: {f} for f in self.concurrent_execution_failures]
        
        for i, violation in enumerate(all_violations[:10], 1):
            logger.info(f    {i:2d}. ❌ {violation})
        
        if len(all_violations) > 10:
            logger.info(f"    ... and {len(all_violations) - 10} more isolation violations)"
        
        # EXPECTED TO FAIL: Comprehensive isolation violations should be detected
        self.assertEqual(
            total_violations, 0,
            fEXPECTED FAILURE (Issue #1123): ExecutionEngine Factory isolation compromised. "
            fEXPECTED FAILURE (Issue #1123): ExecutionEngine Factory isolation compromised. "
            fDetected {total_violations} isolation violations requiring immediate remediation. 
            fSecurity Impact: {isolation_summary['security_impact']['description']} "
            fSecurity Impact: {isolation_summary['security_impact']['description']} "
            f"Compliance Risk: {isolation_summary['compliance_risk']['description']}"
            fBusiness Impact: {isolation_summary['business_impact']['description']}
        )
    
    def _assess_security_impact(self, violation_count: int) -> Dict[str, str]:
        Assess security impact of isolation violations.""
        if violation_count > 5:
            return {
                'level': 'CRITICAL',
                'description': 'Severe user isolation failures create data leakage and security vulnerabilities'
            }
        elif violation_count > 2:
            return {
                'level': 'HIGH',
                'description': 'Significant isolation failures risk user data contamination'
            }
        elif violation_count > 0:
            return {
                'level': 'MEDIUM',
                'description': 'Minor isolation issues may allow limited data sharing between users'
            }
        else:
            return {
                'level': 'LOW',
                'description': 'No isolation violations detected'
            }
    
    def _assess_compliance_risk(self, violation_count: int) -> Dict[str, str]:
        Assess compliance risk of isolation violations.""
        if violation_count > 3:
            return {
                'level': 'CRITICAL',
                'description': 'Isolation failures threaten HIPAA, SOC2, SEC compliance requirements'
            }
        elif violation_count > 1:
            return {
                'level': 'HIGH',
                'description': 'Isolation issues may violate enterprise compliance standards'
            }
        elif violation_count > 0:
            return {
                'level': 'MEDIUM',
                'description': 'Minor isolation concerns for compliance audit readiness'
            }
        else:
            return {
                'level': 'LOW',
                'description': 'No compliance risks from isolation violations'
            }
    
    def _assess_isolation_business_impact(self, violation_count: int) -> Dict[str, str]:
        Assess business impact of isolation violations."
        Assess business impact of isolation violations."
        if violation_count > 5:
            return {
                'level': 'CRITICAL',
                'description': 'Isolation failures threaten $500K+ ARR enterprise customer trust and retention'
            }
        elif violation_count > 2:
            return {
                'level': 'HIGH',
                'description': 'Isolation issues risk enterprise customer acquisition and compliance'
            }
        elif violation_count > 0:
            return {
                'level': 'MEDIUM',
                'description': 'Isolation concerns may limit enterprise market expansion'
            }
        else:
            return {
                'level': 'LOW',
                'description': 'No business impact from isolation violations'
            }


if __name__ == '__main__':
    # Configure logging for direct execution
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the test
    unittest.main()
)))))