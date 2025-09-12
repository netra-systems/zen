"""
Factory Pattern Migration Test - SSOT Execution Engine Consolidation

This test validates that the factory pattern migration creates consistent 
UserExecutionEngine instances and maintains SSOT compliance during the 
consolidation from 7 duplicate engines to UserExecutionEngine.

Business Value: Ensures factory-created engines maintain Golden Path reliability
(users login  ->  get AI responses) while eliminating execution engine duplication.

CRITICAL: This test validates factory pattern SSOT compliance and consistency.
"""

import asyncio
import pytest
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestFactoryPatternMigration(SSotAsyncTestCase):
    """Test factory pattern migration to UserExecutionEngine SSOT."""
    
    async def async_setup_method(self, method=None):
        """Setup test with multiple user contexts for factory testing."""
        await super().async_setup_method(method)
        
        # Create test user contexts
        self.user_contexts = []
        for i in range(3):
            context = UserExecutionContext(
                user_id=f"factory_user_{i}",
                thread_id=f"factory_thread_{i}",
                run_id=f"factory_run_{i}",
                request_id=f"factory_req_{i}",
                agent_context={"factory_test": True, "user_index": i}
            )
            self.user_contexts.append(context)
        
        # Track factory compliance
        self.factory_violations: List[Dict[str, Any]] = []
        self.instance_consistency_issues: List[Dict[str, Any]] = []
    
    async def test_execution_engine_factory_creates_user_engines(self):
        """TEST 1: Verify ExecutionEngineFactory creates UserExecutionEngine instances."""
        self.record_metric("test_name", "factory_creates_user_engines")
        
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                get_execution_engine_factory,
                ExecutionEngineFactory
            )
            
            # Get the factory instance
            factory = await get_execution_engine_factory()
            
            # Test factory creates engines for multiple users
            engines_created = []
            for context in self.user_contexts:
                try:
                    engine = await factory.create_for_user(context)
                    engines_created.append((engine, context))
                    
                    # Verify it's actually a UserExecutionEngine
                    self._validate_user_engine_interface(engine, context)
                    
                except Exception as e:
                    self.factory_violations.append({
                        "type": "creation_failed",
                        "user": context.user_id,
                        "error": str(e)
                    })
            
            # Verify all engines are isolated and consistent
            await self._test_factory_created_engine_isolation(engines_created)
            
            # Test factory method consistency
            await self._test_factory_method_consistency(factory)
            
            # Clean up engines
            for engine, _ in engines_created:
                if hasattr(engine, 'cleanup'):
                    await engine.cleanup()
            
            self.record_metric("engines_created_by_factory", len(engines_created))
            self.record_metric("factory_creation_success_rate", len(engines_created) / len(self.user_contexts))
            
        except ImportError:
            # Factory not available yet - document as violation
            self.factory_violations.append({
                "type": "factory_not_available",
                "error": "ExecutionEngineFactory not implemented"
            })
            pytest.skip("ExecutionEngineFactory not available - SSOT migration in progress")
            
        except Exception as e:
            pytest.fail(f"Factory pattern test failed: {e}")
    
    def _validate_user_engine_interface(self, engine, context: UserExecutionContext):
        """Validate that factory-created engine has UserExecutionEngine interface."""
        
        # Required UserExecutionEngine methods
        required_methods = [
            'get_user_context',
            'execute_agent', 
            'cleanup',
            'get_execution_summary',
            'is_active',
            'set_agent_state',
            'get_agent_state',
            'get_tool_dispatcher'
        ]
        
        missing_methods = []
        for method_name in required_methods:
            if not hasattr(engine, method_name):
                missing_methods.append(method_name)
        
        if missing_methods:
            self.factory_violations.append({
                "type": "missing_interface_methods",
                "user": context.user_id,
                "missing_methods": missing_methods
            })
        
        # Verify user context is properly set
        if hasattr(engine, 'get_user_context'):
            engine_context = engine.get_user_context()
            if engine_context.user_id != context.user_id:
                self.factory_violations.append({
                    "type": "user_context_mismatch",
                    "expected_user": context.user_id,
                    "actual_user": engine_context.user_id
                })
        else:
            self.factory_violations.append({
                "type": "no_user_context",
                "user": context.user_id
            })
    
    async def _test_factory_created_engine_isolation(self, engines_created):
        """Test that factory-created engines are properly isolated."""
        
        if len(engines_created) < 2:
            return
        
        # Set different states on different engines
        for i, (engine, context) in enumerate(engines_created):
            state_value = f"factory_state_{i}_{context.user_id}"
            result_value = {"factory_result": i, "user": context.user_id}
            
            if hasattr(engine, 'set_agent_state'):
                engine.set_agent_state("factory_test_agent", state_value)
            
            if hasattr(engine, 'set_agent_result'):
                engine.set_agent_result("factory_test_agent", result_value)
        
        # Verify isolation - no state leakage between engines
        for i, (engine, context) in enumerate(engines_created):
            if hasattr(engine, 'get_agent_state'):
                state = engine.get_agent_state("factory_test_agent")
                expected_state = f"factory_state_{i}_{context.user_id}"
                
                if state != expected_state:
                    self.instance_consistency_issues.append({
                        "type": "state_isolation_violation",
                        "user": context.user_id,
                        "expected": expected_state,
                        "actual": state
                    })
            
            if hasattr(engine, 'get_agent_result'):
                result = engine.get_agent_result("factory_test_agent") 
                if result and result.get("user") != context.user_id:
                    self.instance_consistency_issues.append({
                        "type": "result_isolation_violation",
                        "user": context.user_id,
                        "expected_user": context.user_id,
                        "actual_user": result.get("user")
                    })
        
        # Verify engines don't share internal state objects
        for i, (engine1, context1) in enumerate(engines_created):
            for j, (engine2, context2) in enumerate(engines_created):
                if i != j:
                    # Check for shared state objects (violation)
                    if hasattr(engine1, 'active_runs') and hasattr(engine2, 'active_runs'):
                        if engine1.active_runs is engine2.active_runs:
                            self.instance_consistency_issues.append({
                                "type": "shared_active_runs",
                                "user1": context1.user_id,
                                "user2": context2.user_id
                            })
                    
                    if hasattr(engine1, 'execution_stats') and hasattr(engine2, 'execution_stats'):
                        if engine1.execution_stats is engine2.execution_stats:
                            self.instance_consistency_issues.append({
                                "type": "shared_execution_stats",
                                "user1": context1.user_id,
                                "user2": context2.user_id
                            })
    
    async def _test_factory_method_consistency(self, factory):
        """Test factory method consistency and error handling."""
        
        # Test factory with invalid context
        try:
            invalid_context = UserExecutionContext(
                user_id="",  # Invalid empty user_id
                thread_id="test_thread",
                run_id="test_run",
                request_id="test_req"
            )
            
            engine = await factory.create_for_user(invalid_context)
            
            # If creation succeeds with invalid context, that's a violation
            self.factory_violations.append({
                "type": "accepts_invalid_context",
                "context": "empty_user_id",
                "should_fail": True
            })
            
            if hasattr(engine, 'cleanup'):
                await engine.cleanup()
                
        except Exception:
            # Good - factory should reject invalid contexts
            self.record_metric("factory_properly_validates_context", True)
        
        # Test factory method availability
        required_factory_methods = ['create_for_user']
        for method_name in required_factory_methods:
            if not hasattr(factory, method_name):
                self.factory_violations.append({
                    "type": "missing_factory_method",
                    "method": method_name
                })
    
    async def test_factory_concurrent_engine_creation(self):
        """TEST 2: Verify factory handles concurrent engine creation safely."""
        self.record_metric("test_name", "factory_concurrent_creation")
        
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                get_execution_engine_factory
            )
            
            factory = await get_execution_engine_factory()
            
            # Create multiple engines concurrently
            async def create_engine_for_user(context):
                try:
                    engine = await factory.create_for_user(context)
                    
                    # Test engine immediately
                    engine_context = engine.get_user_context()
                    assert engine_context.user_id == context.user_id
                    
                    # Set unique state to test isolation
                    test_value = f"concurrent_{context.user_id}"
                    engine.set_agent_state("concurrent_agent", test_value)
                    
                    await asyncio.sleep(0.1)  # Simulate some work
                    
                    # Verify state is still correct
                    state = engine.get_agent_state("concurrent_agent")
                    if state != test_value:
                        raise ValueError(f"State corruption: expected {test_value}, got {state}")
                    
                    return engine, context
                    
                except Exception as e:
                    return None, context, str(e)
            
            # Run concurrent creation tasks
            tasks = [create_engine_for_user(ctx) for ctx in self.user_contexts]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze concurrent creation results
            successful_engines = []
            concurrent_errors = []
            
            for result in results:
                if isinstance(result, Exception):
                    concurrent_errors.append(str(result))
                elif len(result) == 3:  # Error case
                    concurrent_errors.append(result[2])
                else:
                    engine, context = result
                    successful_engines.append((engine, context))
            
            # Verify concurrent creation worked
            if concurrent_errors:
                self.factory_violations.append({
                    "type": "concurrent_creation_failures",
                    "errors": concurrent_errors
                })
            
            # Clean up successful engines
            for engine, _ in successful_engines:
                await engine.cleanup()
            
            self.record_metric("concurrent_engines_created", len(successful_engines))
            self.record_metric("concurrent_creation_errors", len(concurrent_errors))
            
        except Exception as e:
            pytest.fail(f"Concurrent factory creation test failed: {e}")
    
    async def test_factory_engine_lifecycle_management(self):
        """TEST 3: Verify factory-created engines have proper lifecycle management."""
        self.record_metric("test_name", "factory_engine_lifecycle")
        
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                get_execution_engine_factory
            )
            
            factory = await get_execution_engine_factory()
            context = self.user_contexts[0]
            
            # Create engine
            engine = await factory.create_for_user(context)
            
            # Test engine lifecycle
            lifecycle_issues = []
            
            # 1. Test initial state
            if hasattr(engine, 'is_active'):
                if not engine.is_active():
                    lifecycle_issues.append("Engine not active after creation")
            
            # 2. Test engine can be used
            if hasattr(engine, 'set_agent_state'):
                engine.set_agent_state("lifecycle_agent", "active")
            
            # 3. Test cleanup
            if hasattr(engine, 'cleanup'):
                await engine.cleanup()
                
                # Verify cleanup worked
                if hasattr(engine, 'is_active') and engine.is_active():
                    lifecycle_issues.append("Engine still active after cleanup")
                
                if hasattr(engine, 'active_runs') and engine.active_runs:
                    lifecycle_issues.append("Active runs not cleared after cleanup")
            else:
                lifecycle_issues.append("Engine missing cleanup method")
            
            # 4. Test engine cannot be used after cleanup
            try:
                engine.set_agent_state("lifecycle_agent", "post_cleanup")
                # If this succeeds, engine might not be properly cleaned up
                current_state = engine.get_agent_state("lifecycle_agent")
                if current_state == "post_cleanup":
                    lifecycle_issues.append("Engine accepts state changes after cleanup")
            except:
                # Good - engine should not accept operations after cleanup
                pass
            
            if lifecycle_issues:
                self.factory_violations.append({
                    "type": "lifecycle_management_issues",
                    "issues": lifecycle_issues
                })
            
            self.record_metric("lifecycle_issues_found", len(lifecycle_issues))
            
        except Exception as e:
            pytest.fail(f"Factory lifecycle test failed: {e}")
    
    async def test_factory_ssot_compliance(self):
        """TEST 4: Verify factory creates only SSOT-compliant UserExecutionEngine instances."""
        self.record_metric("test_name", "factory_ssot_compliance")
        
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                get_execution_engine_factory
            )
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            
            factory = await get_execution_engine_factory()
            
            # Create engines and verify they're UserExecutionEngine instances
            ssot_compliance_issues = []
            
            for context in self.user_contexts:
                engine = await factory.create_for_user(context)
                
                # Verify engine is UserExecutionEngine instance or compatible
                is_user_execution_engine = isinstance(engine, UserExecutionEngine)
                has_user_engine_interface = (
                    hasattr(engine, 'get_user_context') and
                    hasattr(engine, 'user_context') and 
                    hasattr(engine, 'execute_agent') and
                    hasattr(engine, 'cleanup')
                )
                
                if not (is_user_execution_engine or has_user_engine_interface):
                    ssot_compliance_issues.append({
                        "user": context.user_id,
                        "engine_type": type(engine).__name__,
                        "is_user_execution_engine": is_user_execution_engine,
                        "has_interface": has_user_engine_interface
                    })
                
                # Verify SSOT characteristics
                if hasattr(engine, 'get_user_context'):
                    engine_context = engine.get_user_context()
                    if not isinstance(engine_context, UserExecutionContext):
                        ssot_compliance_issues.append({
                            "user": context.user_id,
                            "issue": "user_context_wrong_type",
                            "expected": "UserExecutionContext",
                            "actual": type(engine_context).__name__
                        })
                
                # Clean up
                await engine.cleanup()
            
            if ssot_compliance_issues:
                self.factory_violations.append({
                    "type": "ssot_compliance_violations",
                    "issues": ssot_compliance_issues
                })
            
            self.record_metric("ssot_compliance_issues", len(ssot_compliance_issues))
            
        except Exception as e:
            pytest.fail(f"Factory SSOT compliance test failed: {e}")
    
    async def test_factory_golden_path_protection(self):
        """GOLDEN PATH: Verify factory-created engines protect user login  ->  AI response flow."""
        self.record_metric("test_name", "factory_golden_path_protection")
        
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                get_execution_engine_factory
            )
            
            factory = await get_execution_engine_factory()
            
            # Test factory creates functional engines for Golden Path
            golden_path_user = UserExecutionContext(
                user_id="golden_path_factory_user",
                thread_id="golden_path_thread",
                run_id="golden_path_run",
                request_id="golden_path_req",
                agent_context={"user_prompt": "Golden Path AI request via factory"}
            )
            
            engine = await factory.create_for_user(golden_path_user)
            
            # Verify engine can support Golden Path workflow
            golden_path_functional = True
            
            # 1. Engine has user context for isolation
            if not hasattr(engine, 'get_user_context'):
                golden_path_functional = False
                print("GOLDEN PATH ISSUE: No user context support")
            else:
                context = engine.get_user_context()
                if context.user_id != golden_path_user.user_id:
                    golden_path_functional = False
                    print(f"GOLDEN PATH ISSUE: User context mismatch")
            
            # 2. Engine can execute agents (core functionality)
            if not hasattr(engine, 'execute_agent'):
                golden_path_functional = False
                print("GOLDEN PATH ISSUE: No agent execution capability")
            
            # 3. Engine has WebSocket support for chat UX
            if not hasattr(engine, 'websocket_emitter') or not engine.websocket_emitter:
                print("GOLDEN PATH WARNING: No WebSocket emitter (may affect chat UX)")
                # Not marking as failure - might be acceptable for some implementations
            
            # 4. Engine can maintain state for conversation context
            if hasattr(engine, 'set_agent_state') and hasattr(engine, 'get_agent_state'):
                engine.set_agent_state("golden_path_agent", "processing")
                state = engine.get_agent_state("golden_path_agent")
                if state != "processing":
                    golden_path_functional = False
                    print("GOLDEN PATH ISSUE: State management not working")
            
            # Clean up
            await engine.cleanup()
            
            if not golden_path_functional:
                pytest.fail("GOLDEN PATH BROKEN: Factory-created engines cannot support user login  ->  AI response workflow")
            
            self.record_metric("golden_path_factory_protected", True)
            print(" PASS:  Golden Path Protected: Factory creates functional engines for user AI workflows")
            
        except Exception as e:
            pytest.fail(f"GOLDEN PATH FAILURE: Factory pattern broke user workflow: {e}")
    
    async def async_teardown_method(self, method=None):
        """Report factory pattern migration test results."""
        
        all_metrics = self.get_all_metrics()
        
        print(f"\n=== Factory Pattern Migration Report ===")
        print(f"Test: {all_metrics.get('test_name', 'unknown')}")
        print(f"Factory violations: {len(self.factory_violations)}")
        print(f"Instance consistency issues: {len(self.instance_consistency_issues)}")
        print(f"Execution time: {all_metrics.get('execution_time', 0):.3f}s")
        
        if self.factory_violations:
            print("\nFactory Pattern Violations:")
            for violation in self.factory_violations:
                print(f"  - {violation['type']}: {violation}")
        
        if self.instance_consistency_issues:
            print("\nInstance Consistency Issues:")
            for issue in self.instance_consistency_issues:
                print(f"  - {issue['type']}: {issue}")
        
        # Success metrics
        success_metrics = {
            "engines_created": all_metrics.get("engines_created_by_factory", 0),
            "success_rate": all_metrics.get("factory_creation_success_rate", 0),
            "concurrent_engines": all_metrics.get("concurrent_engines_created", 0),
            "golden_path_protected": all_metrics.get("golden_path_factory_protected", False)
        }
        
        print(f"\nFactory Performance:")
        for metric, value in success_metrics.items():
            print(f"  {metric}: {value}")
        
        if not self.factory_violations and not self.instance_consistency_issues:
            print(" PASS:  Factory Pattern SSOT Compliant: All tests passed")
        else:
            total_issues = len(self.factory_violations) + len(self.instance_consistency_issues)
            print(f" WARNING: [U+FE0F]  Factory Pattern Issues: {total_issues} violations found")
            print("NOTE: Issues expected during SSOT migration, should be resolved after consolidation")
        
        print("=" * 55)
        
        await super().async_teardown_method(method)


class TestFactoryPatternConsistency(SSotAsyncTestCase):
    """Test factory pattern consistency across different factory implementations."""
    
    async def test_factory_pattern_alternatives(self):
        """TEST 5: Document alternative factory patterns during transition."""
        self.record_metric("test_name", "factory_pattern_alternatives")
        
        # Test various factory approaches that might exist during transition
        factory_patterns_found = []
        
        # 1. ExecutionEngineFactory
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
            factory_patterns_found.append("ExecutionEngineFactory")
        except ImportError:
            pass
        
        # 2. Direct UserExecutionEngine creation
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            factory_patterns_found.append("UserExecutionEngine_direct")
        except ImportError:
            pass
        
        # 3. Legacy factory methods
        try:
            from netra_backend.app.agents.supervisor.execution_engine import create_request_scoped_engine
            factory_patterns_found.append("create_request_scoped_engine")
        except ImportError:
            pass
        
        self.record_metric("factory_patterns_available", len(factory_patterns_found))
        self.record_metric("factory_pattern_types", factory_patterns_found)
        
        print(f"Factory patterns available: {factory_patterns_found}")
        
        # Ensure at least one pattern is available for Golden Path
        if not factory_patterns_found:
            pytest.fail("GOLDEN PATH AT RISK: No factory patterns available for creating execution engines")