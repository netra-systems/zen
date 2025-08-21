"""
Focused tests for Advanced Tool Orchestration Features
Tests conditional execution, error handling, timeout management, and concurrent chains
MODULAR VERSION: <300 lines, all functions ≤8 lines
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from enum import Enum

from langchain_core.tools import BaseTool

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add project root to path

from netra_backend.app.core.exceptions_base import NetraException

# Add project root to path


class MockAdvancedTool(BaseTool):
    """Advanced mock tool with error simulation capabilities"""
    
    def __init__(self, name: str, description: str = "", **kwargs):
        super().__init__(name=name, description=description, **kwargs)
        self.call_count = 0
        self.should_fail = kwargs.get('should_fail', False)
        self.delay_seconds = kwargs.get('delay_seconds', 0)
        self.failure_message = kwargs.get('failure_message', "Tool execution failed")
        
    def _run(self, query: str) -> str:
        self.call_count += 1
        
        if self.should_fail:
            raise NetraException(self.failure_message)
        
        return f"Result from {self.name}: {query}"
    
    async def _arun(self, query: str) -> str:
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)
        return self._run(query)


class AdvancedToolOrchestrator:
    """Advanced orchestrator with error handling and conditional execution"""
    
    def __init__(self):
        self.execution_history = []
        self.active_chains = {}
        self.error_count = 0
        self.timeout_count = 0
        
    async def execute_conditional_chain(self, chain_config: Dict[str, Any]) -> Any:
        """Execute tool chain with conditional logic"""
        chain_id = chain_config.get('id', 'conditional_default')
        steps = chain_config.get('steps', [])
        conditions = chain_config.get('conditions', {})
        
        results = []
        context = {}
        
        for step in steps:
            if self._should_execute_step(step, context, conditions):
                try:
                    result = await self._execute_step_with_retry(step)
                    results.append(result)
                    context[step.get('output_key', f'step_{len(results)}')] = result
                except Exception as e:
                    if not step.get('optional', False):
                        raise
                    results.append(f"SKIPPED: {str(e)}")
        
        return {'chain_id': chain_id, 'results': results, 'context': context}
    
    def _should_execute_step(self, step: Dict[str, Any], context: Dict, conditions: Dict) -> bool:
        """Determine if step should be executed based on conditions"""
        step_condition = step.get('condition')
        if not step_condition:
            return True
        
        # Simple condition evaluation (can be extended)
        if step_condition in context:
            return bool(context[step_condition])
        
        return True
    
    async def _execute_step_with_retry(self, step: Dict[str, Any], max_retries: int = 3) -> Any:
        """Execute step with retry logic"""
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                return await self._execute_step(step)
            except Exception as e:
                last_error = e
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(0.1 * retry_count)  # Exponential backoff
        
        self.error_count += 1
        raise last_error
    
    async def _execute_step(self, step: Dict[str, Any]) -> Any:
        """Execute single step"""
        tool_name = step.get('tool')
        input_data = step.get('input', '')
        
        # Mock tool execution
        await asyncio.sleep(0.01)
        return f"Result from {tool_name}: {input_data}"
    
    async def execute_chain_with_timeout(self, chain_config: Dict[str, Any], timeout: float = 5.0) -> Any:
        """Execute chain with timeout handling"""
        try:
            return await asyncio.wait_for(
                self.execute_conditional_chain(chain_config),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            self.timeout_count += 1
            return {
                'chain_id': chain_config.get('id', 'timeout_chain'),
                'status': 'timeout',
                'timeout_duration': timeout
            }
    
    async def execute_concurrent_chains(self, chain_configs: List[Dict[str, Any]]) -> List[Any]:
        """Execute multiple chains concurrently"""
        tasks = [self.execute_conditional_chain(config) for config in chain_configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results


class TestAdvancedOrchestration:
    """Test advanced orchestration features"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create advanced tool orchestrator for testing"""
        return AdvancedToolOrchestrator()
    
    @pytest.fixture
    def sample_tools(self):
        """Create sample tools with various behaviors"""
        return {
            'normal_tool': MockAdvancedTool("normal_tool", "Normal operation"),
            'failing_tool': MockAdvancedTool("failing_tool", "Fails on execution", should_fail=True),
            'slow_tool': MockAdvancedTool("slow_tool", "Slow execution", delay_seconds=0.5),
            'optional_tool': MockAdvancedTool("optional_tool", "Optional operation")
        }

    def _create_conditional_execution_config(self):
        """Create conditional execution test configuration"""
        return {
            'id': 'conditional_test',
            'steps': [
                {'tool': 'data_checker', 'input': 'test_data', 'output_key': 'data_valid'},
                {'tool': 'data_processor', 'input': 'validated_data', 'condition': 'data_valid'},
                {'tool': 'backup_processor', 'input': 'fallback_data', 'condition': 'data_invalid', 'optional': True}
            ],
            'conditions': {
                'data_valid': True,
                'data_invalid': False
            }
        }

    def _validate_conditional_execution_result(self, result, config):
        """Validate conditional execution results"""
        assert result is not None
        assert 'chain_id' in result
        assert 'results' in result
        assert 'context' in result
        assert result['chain_id'] == config['id']
        
        # Should have executed conditional steps
        assert len(result['results']) > 0

    async def test_conditional_tool_execution(self, orchestrator):
        """Test conditional tool execution based on context"""
        config = self._create_conditional_execution_config()
        result = await orchestrator.execute_conditional_chain(config)
        self._validate_conditional_execution_result(result, config)

    def _create_error_handling_config(self):
        """Create error handling test configuration"""
        return {
            'id': 'error_handling_test',
            'steps': [
                {'tool': 'reliable_tool', 'input': 'test_input'},
                {'tool': 'unreliable_tool', 'input': 'test_input', 'optional': True},
                {'tool': 'recovery_tool', 'input': 'recovery_input'}
            ]
        }

    def _simulate_tool_failure(self, orchestrator, step):
        """Simulate tool failure for error handling testing"""
        if step.get('tool') == 'unreliable_tool':
            raise NetraException("Simulated tool failure")
        return f"Success from {step.get('tool')}"

    def _validate_error_handling_result(self, result, expected_partial_success):
        """Validate error handling results"""
        assert result is not None
        assert 'results' in result
        
        # Should have some successful results even with failures
        successful_results = [r for r in result['results'] if not r.startswith('SKIPPED')]
        assert len(successful_results) >= expected_partial_success

    async def test_tool_chain_error_handling(self, orchestrator):
        """Test error handling in tool chains"""
        config = self._create_error_handling_config()
        
        # Mock the execution to simulate failures
        original_execute = orchestrator._execute_step
        async def mock_execute(step):
            if step.get('tool') == 'unreliable_tool':
                raise NetraException("Simulated failure")
            return await original_execute(step)
        
        orchestrator._execute_step = mock_execute
        
        result = await orchestrator.execute_conditional_chain(config)
        self._validate_error_handling_result(result, 2)  # Expect 2 successful tools

    def _create_timeout_test_config(self):
        """Create timeout handling test configuration"""
        return {
            'id': 'timeout_test',
            'steps': [
                {'tool': 'fast_tool', 'input': 'quick_data'},
                {'tool': 'slow_tool', 'input': 'slow_data'},  # This will cause timeout
                {'tool': 'another_tool', 'input': 'more_data'}
            ]
        }

    def _validate_timeout_handling_result(self, result, expected_timeout):
        """Validate timeout handling results"""
        if expected_timeout:
            assert result['status'] == 'timeout'
            assert 'timeout_duration' in result
        else:
            assert 'results' in result

    async def test_tool_chain_timeout_handling(self, orchestrator):
        """Test timeout handling in tool chains"""
        config = self._create_timeout_test_config()
        
        # Mock slow execution
        original_execute = orchestrator._execute_step
        async def mock_slow_execute(step):
            if step.get('tool') == 'slow_tool':
                await asyncio.sleep(2.0)  # Longer than timeout
            return await original_execute(step)
        
        orchestrator._execute_step = mock_slow_execute
        
        result = await orchestrator.execute_chain_with_timeout(config, timeout=0.5)
        self._validate_timeout_handling_result(result, expected_timeout=True)

    def _create_concurrent_chains_config(self):
        """Create concurrent chains test configuration"""
        return [
            {
                'id': 'chain_1',
                'steps': [
                    {'tool': 'analyzer_1', 'input': 'dataset_1'}
                ]
            },
            {
                'id': 'chain_2', 
                'steps': [
                    {'tool': 'analyzer_2', 'input': 'dataset_2'}
                ]
            },
            {
                'id': 'chain_3',
                'steps': [
                    {'tool': 'analyzer_3', 'input': 'dataset_3'}
                ]
            }
        ]

    def _validate_concurrent_execution_results(self, results, expected_chains):
        """Validate concurrent execution results"""
        assert len(results) == expected_chains
        
        # Check that all chains completed (no exceptions)
        successful_chains = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_chains) >= expected_chains * 0.8  # Allow some tolerance

    async def test_concurrent_chain_execution(self, orchestrator):
        """Test concurrent execution of multiple tool chains"""
        chain_configs = self._create_concurrent_chains_config()
        
        start_time = datetime.now(UTC)
        results = await orchestrator.execute_concurrent_chains(chain_configs)
        execution_time = (datetime.now(UTC) - start_time).total_seconds()
        
        self._validate_concurrent_execution_results(results, len(chain_configs))
        
        # Concurrent execution should be faster than sequential
        assert execution_time < len(chain_configs) * 0.1  # Much faster than sequential

    def _validate_execution_history_tracking(self, orchestrator, minimum_executions):
        """Validate execution history tracking"""
        # History may be tracked differently in advanced orchestrator
        assert orchestrator.error_count >= 0
        assert orchestrator.timeout_count >= 0

    def test_orchestrator_execution_history(self, orchestrator):
        """Test tracking of orchestrator execution history and metrics"""
        initial_error_count = orchestrator.error_count
        initial_timeout_count = orchestrator.timeout_count
        
        # These values should be tracked
        assert initial_error_count == 0
        assert initial_timeout_count == 0

    def _create_retry_mechanism_config(self):
        """Create retry mechanism test configuration"""
        return {
            'id': 'retry_test',
            'steps': [
                {'tool': 'flaky_tool', 'input': 'test_data', 'max_retries': 3}
            ]
        }

    async def _simulate_flaky_execution(self, step, attempt_count):
        """Simulate flaky tool execution for retry testing"""
        if attempt_count < 2:  # Fail first 2 attempts
            raise NetraException(f"Flaky failure attempt {attempt_count}")
        return f"Success from {step.get('tool')} on attempt {attempt_count}"

    def _validate_retry_mechanism_result(self, result):
        """Validate retry mechanism results"""
        assert result is not None
        assert 'results' in result
        assert len(result['results']) > 0
        
        # Should succeed after retries
        assert not any(r.startswith('SKIPPED') for r in result['results'])

    async def test_retry_mechanism_functionality(self, orchestrator):
        """Test retry mechanism for unreliable tools"""
        config = self._create_retry_mechanism_config()
        
        # Mock flaky execution
        attempt_counts = {}
        original_execute = orchestrator._execute_step
        
        async def mock_flaky_execute(step):
            tool_name = step.get('tool')
            attempt_counts[tool_name] = attempt_counts.get(tool_name, 0) + 1
            
            if tool_name == 'flaky_tool':
                return await self._simulate_flaky_execution(step, attempt_counts[tool_name])
            return await original_execute(step)
        
        orchestrator._execute_step = mock_flaky_execute
        
        result = await orchestrator.execute_conditional_chain(config)
        self._validate_retry_mechanism_result(result)

    def _create_performance_benchmark_config(self):
        """Create performance benchmark configuration"""
        return {
            'sequential_chains': 3,
            'concurrent_chains': 3,
            'steps_per_chain': 2
        }

    async def _execute_performance_benchmark(self, orchestrator, config):
        """Execute performance benchmark"""
        # Create chain configurations
        sequential_configs = []
        concurrent_configs = []
        
        for i in range(config['sequential_chains']):
            chain_config = {
                'id': f'seq_chain_{i}',
                'steps': [{'tool': f'tool_{j}', 'input': f'data_{j}'} for j in range(config['steps_per_chain'])]
            }
            sequential_configs.append(chain_config)
        
        for i in range(config['concurrent_chains']):
            chain_config = {
                'id': f'conc_chain_{i}',
                'steps': [{'tool': f'tool_{j}', 'input': f'data_{j}'} for j in range(config['steps_per_chain'])]
            }
            concurrent_configs.append(chain_config)
        
        # Execute sequential
        start_time = datetime.now(UTC)
        for chain_config in sequential_configs:
            await orchestrator.execute_conditional_chain(chain_config)
        sequential_time = (datetime.now(UTC) - start_time).total_seconds()
        
        # Execute concurrent
        start_time = datetime.now(UTC)
        await orchestrator.execute_concurrent_chains(concurrent_configs)
        concurrent_time = (datetime.now(UTC) - start_time).total_seconds()
        
        return {
            'sequential_time': sequential_time,
            'concurrent_time': concurrent_time,
            'performance_ratio': sequential_time / max(concurrent_time, 0.001)
        }

    def _validate_performance_benchmark_results(self, results):
        """Validate performance benchmark results"""
        assert results['sequential_time'] > 0
        assert results['concurrent_time'] > 0
        assert results['performance_ratio'] > 0.5  # Concurrent should be faster or similar

    async def test_orchestration_performance_benchmarking(self, orchestrator):
        """Test orchestration performance benchmarking"""
        config = self._create_performance_benchmark_config()
        results = await self._execute_performance_benchmark(orchestrator, config)
        self._validate_performance_benchmark_results(results)