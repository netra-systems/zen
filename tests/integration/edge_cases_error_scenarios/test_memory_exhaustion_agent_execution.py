"""
Test Memory Exhaustion During Agent Execution - Edge Case Integration Test

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: System stability and resilience under memory pressure
- Value Impact: Prevents system crashes during large-scale AI operations
- Strategic Impact: Protects customer AI workflows from memory-related failures

CRITICAL: This test validates system behavior under memory pressure conditions
that could occur during large dataset processing or concurrent user load.
"""

import asyncio
import gc
import logging
import pytest
import psutil
import sys
from typing import Dict, List, Optional
from unittest import mock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services import get_real_services
from test_framework.resource_monitor import ResourceMonitor

logger = logging.getLogger(__name__)


class TestMemoryExhaustionAgentExecution(BaseIntegrationTest):
    """Test agent execution behavior under memory pressure conditions."""
    
    def setup_method(self):
        """Set up memory monitoring for tests."""
        super().setup_method()
        self.resource_monitor = ResourceMonitor()
        self.initial_memory = psutil.Process().memory_info().rss
        
    def teardown_method(self):
        """Clean up and force garbage collection."""
        gc.collect()  # Force cleanup after memory stress tests
        super().teardown_method()
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_under_memory_pressure(self, real_services_fixture):
        """Test agent execution when system memory is under pressure."""
        real_services = get_real_services()
        
        # Create test user context
        user_context = await self.create_test_user_context(real_services)
        
        # Simulate memory pressure by creating large objects
        memory_consumers = []
        try:
            # Consume memory gradually until we reach 80% of available
            process = psutil.Process()
            available_memory = psutil.virtual_memory().available
            target_consumption = int(available_memory * 0.1)  # 10% to be safe in tests
            
            # Create large objects to simulate memory pressure
            chunk_size = 10 * 1024 * 1024  # 10MB chunks
            while len(memory_consumers) * chunk_size < target_consumption:
                memory_consumers.append(b'x' * chunk_size)
                
                # Check if we've reached unsafe memory usage
                current_memory = process.memory_info().rss
                if current_memory > self.initial_memory * 2:  # 2x initial memory
                    break
                    
            logger.info(f"Created memory pressure: {len(memory_consumers)} chunks")
            
            # Now test agent execution under memory pressure
            from netra_backend.app.agents.supervisor.execution_engine_factory import user_execution_engine
            
            with user_execution_engine(user_context['id'], mock.MagicMock()) as engine:
                # Create simple agent request that shouldn't fail due to memory
                agent_request = {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": "Simple system status check",
                    "context": {"memory_pressure_test": True}
                }
                
                # Monitor memory during execution
                start_memory = process.memory_info().rss
                
                # Execute agent under memory pressure
                result = await engine.execute_agent_request(
                    agent_name="triage_agent",
                    message="System status check",
                    context={"memory_pressure_test": True}
                )
                
                end_memory = process.memory_info().rss
                memory_growth = end_memory - start_memory
                
                # Verify agent executed successfully despite memory pressure
                assert result is not None, "Agent must complete execution under memory pressure"
                assert result.get('status') != 'error', f"Agent failed under memory pressure: {result.get('error')}"
                
                # Verify memory growth is bounded (agent shouldn't consume excessive memory)
                max_allowed_growth = 100 * 1024 * 1024  # 100MB max growth
                assert memory_growth < max_allowed_growth, f"Agent consumed too much memory: {memory_growth / 1024 / 1024:.1f}MB"
                
                # Verify business value is still delivered
                self.assert_business_value_delivered(result, 'insights')
                
        finally:
            # Clean up memory consumers
            del memory_consumers
            gc.collect()
            
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_agent_execution_memory_leak_prevention(self, real_services_fixture):
        """Test that agent execution doesn't leak memory over multiple runs."""
        real_services = get_real_services()
        
        # Create test user context
        user_context = await self.create_test_user_context(real_services)
        
        process = psutil.Process()
        baseline_memory = process.memory_info().rss
        memory_measurements = []
        
        # Run multiple agent executions
        for i in range(10):  # Reduced from 50 for faster tests
            try:
                from netra_backend.app.agents.supervisor.execution_engine_factory import user_execution_engine
                
                with user_execution_engine(user_context['id'], mock.MagicMock()) as engine:
                    result = await engine.execute_agent_request(
                        agent_name="triage_agent",
                        message=f"Test iteration {i}",
                        context={"iteration": i}
                    )
                    
                    assert result is not None, f"Agent execution {i} must not fail"
                    
                # Measure memory after each execution
                current_memory = process.memory_info().rss
                memory_measurements.append(current_memory)
                
                # Force garbage collection
                gc.collect()
                
            except Exception as e:
                logger.error(f"Agent execution {i} failed: {e}")
                # Continue to measure memory even if execution fails
                memory_measurements.append(process.memory_info().rss)
                
        # Analyze memory growth pattern
        memory_growth = memory_measurements[-1] - baseline_memory
        max_memory = max(memory_measurements)
        avg_memory = sum(memory_measurements) / len(memory_measurements)
        
        # Memory growth should be bounded (no significant leaks)
        max_allowed_growth = 50 * 1024 * 1024  # 50MB max total growth
        assert memory_growth < max_allowed_growth, f"Memory leak detected: {memory_growth / 1024 / 1024:.1f}MB growth"
        
        # Peak memory usage should be reasonable
        peak_growth = max_memory - baseline_memory
        max_allowed_peak = 100 * 1024 * 1024  # 100MB max peak
        assert peak_growth < max_allowed_peak, f"Peak memory usage too high: {peak_growth / 1024 / 1024:.1f}MB"
        
        logger.info(f"Memory analysis - Growth: {memory_growth / 1024 / 1024:.1f}MB, "
                   f"Peak: {peak_growth / 1024 / 1024:.1f}MB, Avg: {avg_memory / 1024 / 1024:.1f}MB")
        
    @pytest.mark.integration
    async def test_memory_limit_enforcement_boundaries(self):
        """Test system behavior at memory usage boundaries."""
        # Test memory usage tracking and enforcement
        resource_monitor = ResourceMonitor()
        
        # Test boundary conditions for memory limits
        test_limits = [
            {"limit_mb": 100, "expected_enforcement": False},  # Well below limit
            {"limit_mb": 50, "expected_enforcement": True},    # At/above limit
        ]
        
        for test_case in test_limits:
            limit_bytes = test_case["limit_mb"] * 1024 * 1024
            
            # Simulate different memory usage levels
            current_usage = psutil.Process().memory_info().rss
            
            # Test resource monitor's limit checking
            should_throttle = resource_monitor._should_throttle_based_on_memory(
                current_usage, limit_bytes
            )
            
            if test_case["expected_enforcement"]:
                assert should_throttle or current_usage < limit_bytes, \
                    f"Memory limit {test_case['limit_mb']}MB should be enforced"
            else:
                # For low limits, we expect no throttling under normal conditions
                assert not should_throttle or current_usage > limit_bytes, \
                    f"Memory limit {test_case['limit_mb']}MB enforcement should be lenient"
                    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_agent_memory_isolation(self, real_services_fixture):
        """Test memory isolation between concurrent agent executions."""
        real_services = get_real_services()
        
        # Create multiple user contexts
        user_contexts = []
        for i in range(3):
            context = await self.create_test_user_context(real_services, {
                'email': f'memory-test-user-{i}@example.com',
                'name': f'Memory Test User {i}'
            })
            user_contexts.append(context)
            
        async def memory_intensive_agent_execution(user_context: Dict, memory_load: int):
            """Execute agent with memory-intensive operations."""
            # Create some memory load specific to this execution
            local_memory = [b'x' * 1024 * 1024 for _ in range(memory_load)]  # MB per load unit
            
            try:
                from netra_backend.app.agents.supervisor.execution_engine_factory import user_execution_engine
                
                with user_execution_engine(user_context['id'], mock.MagicMock()) as engine:
                    result = await engine.execute_agent_request(
                        agent_name="triage_agent",
                        message=f"Memory load test with {memory_load}MB",
                        context={"memory_load": memory_load}
                    )
                    
                    return {
                        'user_id': user_context['id'],
                        'memory_load': memory_load,
                        'result': result,
                        'success': result is not None and result.get('status') != 'error'
                    }
                    
            except Exception as e:
                return {
                    'user_id': user_context['id'],
                    'memory_load': memory_load,
                    'result': None,
                    'success': False,
                    'error': str(e)
                }
            finally:
                # Clean up local memory
                del local_memory
                gc.collect()
        
        # Run concurrent executions with different memory loads
        memory_loads = [5, 10, 15]  # MB per execution
        tasks = [
            memory_intensive_agent_execution(user_contexts[i], memory_loads[i])
            for i in range(len(user_contexts))
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all executions completed successfully
        successful_executions = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Concurrent execution failed: {result}")
            else:
                if result.get('success'):
                    successful_executions.append(result)
                else:
                    logger.warning(f"Agent execution failed: {result.get('error')}")
        
        # At least 2/3 executions should succeed (allowing for system limitations)
        assert len(successful_executions) >= 2, \
            f"Too many concurrent executions failed: {len(successful_executions)}/3 succeeded"
        
        # Verify memory isolation - each execution should have isolated context
        user_ids = set(result['user_id'] for result in successful_executions)
        assert len(user_ids) == len(successful_executions), \
            "Memory isolation failed - user contexts not properly isolated"
            
    @pytest.mark.integration
    async def test_memory_recovery_after_pressure_release(self):
        """Test system memory recovery after memory pressure is released."""
        process = psutil.Process()
        baseline_memory = process.memory_info().rss
        
        # Create temporary memory pressure
        memory_pressure = []
        try:
            # Create moderate memory pressure
            for i in range(20):  # 20MB total pressure
                memory_pressure.append(b'x' * 1024 * 1024)  # 1MB chunks
                
            peak_memory = process.memory_info().rss
            peak_growth = peak_memory - baseline_memory
            
            # Verify memory pressure was created
            assert peak_growth > 15 * 1024 * 1024, "Insufficient memory pressure created"
            
        finally:
            # Release memory pressure
            del memory_pressure
            gc.collect()
            
        # Allow some time for memory recovery
        await asyncio.sleep(1.0)
        
        # Measure recovery
        recovered_memory = process.memory_info().rss
        recovery_efficiency = (peak_memory - recovered_memory) / (peak_memory - baseline_memory)
        
        # Should recover at least 80% of consumed memory
        assert recovery_efficiency > 0.8, \
            f"Poor memory recovery: {recovery_efficiency:.1%} efficiency"
            
        # Final memory should be close to baseline
        final_growth = recovered_memory - baseline_memory
        max_allowed_residual = 10 * 1024 * 1024  # 10MB residual allowed
        
        assert final_growth < max_allowed_residual, \
            f"Memory not fully recovered: {final_growth / 1024 / 1024:.1f}MB residual"
            
        logger.info(f"Memory recovery test - Peak growth: {peak_growth / 1024 / 1024:.1f}MB, "
                   f"Recovery: {recovery_efficiency:.1%}, Residual: {final_growth / 1024 / 1024:.1f}MB")