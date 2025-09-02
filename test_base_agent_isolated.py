#!/usr/bin/env python3
"""
ISOLATED BASE AGENT TEST - Direct execution without pytest dependencies

This script tests BaseAgent infrastructure directly to validate core functionality.
"""

import asyncio
import gc
import os
import sys
import time
from unittest.mock import Mock

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'netra_backend'))

# Set up test environment variables BEFORE any imports
os.environ["TEST_COLLECTION_MODE"] = "1"
os.environ["TESTING"] = "1" 
os.environ["NETRA_ENV"] = "testing"
os.environ["ENVIRONMENT"] = "testing"
os.environ["LOG_LEVEL"] = "ERROR"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_HOST"] = "localhost"
os.environ["TEST_DISABLE_REDIS"] = "true"
os.environ["CLICKHOUSE_ENABLED"] = "false"


class TestResult:
    def __init__(self, name, success, error=None, details=None):
        self.name = name
        self.success = success
        self.error = error
        self.details = details or {}


class IsolatedBaseAgentTester:
    def __init__(self):
        self.test_results = []
        self.agent = None
        
    def run_all_tests(self):
        """Run all isolated tests."""
        print("=" * 80)
        print("ISOLATED BASE AGENT INFRASTRUCTURE TESTS")  
        print("=" * 80)
        
        tests = [
            self.test_base_agent_creation,
            self.test_reliability_infrastructure_presence,
            self.test_health_status_reporting,
            self.test_websocket_adapter_functionality,
            self.test_modern_execution_pattern,
            self.test_concurrent_execution_safety,
            self.test_memory_usage_basic,
            self.test_circuit_breaker_status,
        ]
        
        for test in tests:
            try:
                print(f"\nRunning {test.__name__}...")
                result = test()
                self.test_results.append(result)
                if result.success:
                    print(f"  PASSED: {result.name}")
                    if result.details:
                        for key, value in result.details.items():
                            print(f"    {key}: {value}")
                else:
                    print(f"  FAILED: {result.name}")
                    print(f"    Error: {result.error}")
            except Exception as e:
                print(f"  CRASHED: {test.__name__}")
                print(f"    Exception: {e}")
                self.test_results.append(TestResult(
                    test.__name__, False, str(e)
                ))
        
        self._print_summary()
    
    def test_base_agent_creation(self):
        """Test that BaseAgent can be created successfully."""
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.llm.llm_manager import LLMManager
            
            # Mock LLM manager
            mock_llm = Mock(spec=LLMManager)
            
            # Create agent
            class TestAgent(BaseAgent):
                async def execute_core_logic(self, context):
                    return {"status": "test_success"}
                    
                async def validate_preconditions(self, context):
                    return True
            
            self.agent = TestAgent(
                llm_manager=mock_llm,
                name="IsolatedTestAgent", 
                enable_reliability=True,
                enable_execution_engine=True
            )
            
            return TestResult(
                "BaseAgent Creation", 
                True,
                details={
                    "agent_name": self.agent.name,
                    "agent_state": str(self.agent.state)
                }
            )
        except Exception as e:
            return TestResult("BaseAgent Creation", False, str(e))
    
    def test_reliability_infrastructure_presence(self):
        """Test that reliability infrastructure is present."""
        if not self.agent:
            return TestResult("Reliability Infrastructure", False, "No agent created")
            
        try:
            # Check for reliability components
            has_reliability_manager = hasattr(self.agent, '_reliability_manager')
            has_execution_engine = hasattr(self.agent, '_execution_engine') 
            has_execution_monitor = hasattr(self.agent, '_execution_monitor')
            
            # Check that components are not None
            rm_not_none = getattr(self.agent, '_reliability_manager', None) is not None
            ee_not_none = getattr(self.agent, '_execution_engine', None) is not None
            em_not_none = getattr(self.agent, '_execution_monitor', None) is not None
            
            # Check property access
            rm_property = self.agent.reliability_manager is not None
            ee_property = self.agent.execution_engine is not None
            em_property = self.agent.execution_monitor is not None
            
            all_present = all([
                has_reliability_manager, has_execution_engine, has_execution_monitor,
                rm_not_none, ee_not_none, em_not_none,
                rm_property, ee_property, em_property
            ])
            
            return TestResult(
                "Reliability Infrastructure",
                all_present,
                None if all_present else "Missing reliability components",
                details={
                    "reliability_manager": f"Present: {has_reliability_manager}, Not None: {rm_not_none}, Property: {rm_property}",
                    "execution_engine": f"Present: {has_execution_engine}, Not None: {ee_not_none}, Property: {ee_property}",
                    "execution_monitor": f"Present: {has_execution_monitor}, Not None: {em_not_none}, Property: {em_property}"
                }
            )
        except Exception as e:
            return TestResult("Reliability Infrastructure", False, str(e))
    
    def test_health_status_reporting(self):
        """Test health status reporting functionality."""
        if not self.agent:
            return TestResult("Health Status Reporting", False, "No agent created")
            
        try:
            health_status = self.agent.get_health_status()
            
            # Basic checks
            is_dict = isinstance(health_status, dict)
            has_agent_name = "agent_name" in health_status
            has_state = "state" in health_status
            has_overall_status = "overall_status" in health_status
            
            # Check for reliability information
            has_reliability_info = any(
                key in health_status for key in 
                ["legacy_reliability", "modern_execution", "monitoring", "reliability_manager"]
            )
            
            success = all([is_dict, has_agent_name, has_state, has_overall_status, has_reliability_info])
            
            return TestResult(
                "Health Status Reporting",
                success,
                None if success else "Health status missing required fields",
                details={
                    "is_dict": is_dict,
                    "keys_count": len(health_status),
                    "has_agent_name": has_agent_name,
                    "has_state": has_state,  
                    "has_overall_status": has_overall_status,
                    "has_reliability_info": has_reliability_info,
                    "all_keys": list(health_status.keys())
                }
            )
        except Exception as e:
            return TestResult("Health Status Reporting", False, str(e))
    
    def test_websocket_adapter_functionality(self):
        """Test WebSocket adapter functionality."""
        if not self.agent:
            return TestResult("WebSocket Adapter", False, "No agent created")
            
        try:
            # Check WebSocket adapter presence
            has_adapter = hasattr(self.agent, '_websocket_adapter')
            adapter_not_none = getattr(self.agent, '_websocket_adapter', None) is not None
            
            # Test context methods
            initial_context = self.agent.has_websocket_context()
            
            # Mock bridge setup
            mock_bridge = Mock()
            self.agent.set_websocket_bridge(mock_bridge, "test_run_123")
            after_setup_context = self.agent.has_websocket_context()
            
            success = all([has_adapter, adapter_not_none, not initial_context, after_setup_context])
            
            return TestResult(
                "WebSocket Adapter",
                success,
                None if success else "WebSocket adapter issues",
                details={
                    "has_adapter": has_adapter,
                    "adapter_not_none": adapter_not_none,
                    "initial_context": initial_context,
                    "after_setup_context": after_setup_context
                }
            )
        except Exception as e:
            return TestResult("WebSocket Adapter", False, str(e))
    
    def test_modern_execution_pattern(self):
        """Test modern execution pattern."""
        if not self.agent:
            return TestResult("Modern Execution", False, "No agent created")
            
        async def _test():
            try:
                from netra_backend.app.agents.state import DeepAgentState
                
                # Create test state
                state = DeepAgentState()
                state.user_request = "Isolated test execution"
                # Don't set thread_id and user_id if they don't exist as fields
                
                # Execute using modern pattern
                result = await self.agent.execute_modern(
                    state=state,
                    run_id="isolated_test_run",
                    stream_updates=False
                )
                
                # Verify result
                success = (
                    hasattr(result, 'success') and 
                    hasattr(result, 'result') and
                    result.success is True and
                    result.result is not None
                )
                
                return TestResult(
                    "Modern Execution",
                    success,
                    None if success else "Modern execution failed",
                    details={
                        "result_type": str(type(result)),
                        "has_success": hasattr(result, 'success'),
                        "has_result": hasattr(result, 'result'),
                        "success_value": getattr(result, 'success', None),
                        "result_status": getattr(result.result, 'get', lambda x: None)('status') if hasattr(result, 'result') and result.result else None
                    }
                )
            except Exception as e:
                return TestResult("Modern Execution", False, str(e))
        
        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_test())
        finally:
            loop.close()
    
    def test_concurrent_execution_safety(self):
        """Test basic concurrent execution safety."""
        if not self.agent:
            return TestResult("Concurrent Execution Safety", False, "No agent created")
            
        async def _test():
            try:
                from netra_backend.app.agents.state import DeepAgentState
                
                # Create multiple concurrent executions
                tasks = []
                for i in range(5):
                    state = DeepAgentState()
                    state.user_request = f"Concurrent test {i}"
                    # Don't set thread_id if it doesn't exist as a field
                    
                    task = self.agent.execute_modern(
                        state=state,
                        run_id=f"concurrent_run_{i}"
                    )
                    tasks.append(task)
                
                # Execute concurrently
                start_time = time.time()
                results = await asyncio.gather(*tasks, return_exceptions=True)
                end_time = time.time()
                
                # Analyze results
                successful_count = sum(
                    1 for r in results 
                    if hasattr(r, 'success') and r.success
                )
                
                execution_time = end_time - start_time
                success = successful_count == 5 and execution_time < 5.0
                
                return TestResult(
                    "Concurrent Execution Safety",
                    success,
                    None if success else f"Concurrent execution issues: {successful_count}/5 success",
                    details={
                        "successful_count": successful_count,
                        "total_tasks": len(tasks),
                        "execution_time_seconds": round(execution_time, 3),
                        "results_types": [str(type(r)) for r in results]
                    }
                )
            except Exception as e:
                return TestResult("Concurrent Execution Safety", False, str(e))
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_test())
        finally:
            loop.close()
    
    def test_memory_usage_basic(self):
        """Test basic memory usage patterns."""
        if not self.agent:
            return TestResult("Memory Usage Basic", False, "No agent created")
            
        try:
            import psutil
            
            # Get initial memory
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Create and destroy some agents to test memory cleanup
            agents = []
            for i in range(10):
                from netra_backend.app.llm.llm_manager import LLMManager
                mock_llm = Mock(spec=LLMManager)
                
                class TempAgent(self.agent.__class__):
                    pass
                
                temp_agent = TempAgent(
                    llm_manager=mock_llm,
                    name=f"TempAgent_{i}"
                )
                agents.append(temp_agent)
            
            # Force garbage collection
            agents.clear()
            gc.collect()
            
            # Check final memory
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_growth = final_memory - initial_memory
            
            # Allow reasonable memory growth (less than 20MB)
            success = memory_growth < 20
            
            return TestResult(
                "Memory Usage Basic",
                success,
                None if success else f"Excessive memory growth: {memory_growth:.1f}MB",
                details={
                    "initial_memory_mb": round(initial_memory, 1),
                    "final_memory_mb": round(final_memory, 1),
                    "memory_growth_mb": round(memory_growth, 1)
                }
            )
        except Exception as e:
            return TestResult("Memory Usage Basic", False, str(e))
    
    def test_circuit_breaker_status(self):
        """Test circuit breaker status reporting."""
        if not self.agent:
            return TestResult("Circuit Breaker Status", False, "No agent created")
            
        try:
            cb_status = self.agent.get_circuit_breaker_status()
            
            # Should be a dictionary with state information
            is_dict = isinstance(cb_status, dict)
            has_status = "status" in cb_status if is_dict else False
            has_state = "state" in cb_status if is_dict else False
            
            # Allow for circuit breaker to be not available in some configurations
            if is_dict and cb_status.get("status") == "not_available":
                success = True  # This is a valid state
            elif is_dict and has_state:
                success = True  # Circuit breaker has state field (valid)
            else:
                success = is_dict and has_status
            
            return TestResult(
                "Circuit Breaker Status",
                success,
                None if success else "Circuit breaker status issues",
                details={
                    "is_dict": is_dict,
                    "has_status": has_status,
                    "has_state": has_state,
                    "status_keys": list(cb_status.keys()) if is_dict else None,
                    "status_value": cb_status.get("status") if is_dict else None,
                    "state_value": cb_status.get("state") if is_dict else None
                }
            )
        except Exception as e:
            return TestResult("Circuit Breaker Status", False, str(e))
    
    def _print_summary(self):
        """Print test results summary."""
        print("\n" + "=" * 80)
        print("TEST RESULTS SUMMARY")
        print("=" * 80)
        
        passed_count = sum(1 for result in self.test_results if result.success)
        total_count = len(self.test_results)
        
        print(f"Tests passed: {passed_count}/{total_count}")
        print(f"Success rate: {passed_count/total_count*100:.1f}%")
        
        if passed_count < total_count:
            print(f"\nFAILED TESTS:")
            for result in self.test_results:
                if not result.success:
                    print(f"  FAILED: {result.name}: {result.error}")
        
        print("\nPASSED TESTS:")
        for result in self.test_results:
            if result.success:
                print(f"  PASSED: {result.name}")
        
        print("=" * 80)


if __name__ == "__main__":
    tester = IsolatedBaseAgentTester()
    tester.run_all_tests()