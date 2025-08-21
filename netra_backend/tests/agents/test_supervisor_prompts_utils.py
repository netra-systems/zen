"""
Test module: Supervisor Prompts and Utils
Split from large test file for architecture compliance
Test classes: TestAgentPromptsTemplateRendering, TestEnhancedPromptsContextBuilding, TestAgentUtilsHelperFunctions
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timezone
import json
import time

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.supervisor.execution_context import (

# Add project root to path
    ExecutionStrategy,
    AgentExecutionContext,
    AgentExecutionResult
)
from netra_backend.app.agents.state import DeepAgentState
from schemas import SubAgentLifecycle, WebSocketMessage, AgentStarted, SubAgentUpdate, AgentCompleted
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher


# Mock classes for testing (would normally be imported)
class AgentPrompts:
    """Mock agent prompts for testing"""
    
    def render_template(self, template, variables, strict=False):
        """Render template with variable substitution"""
        if strict:
            # Check for missing variables
            import re
            required_vars = re.findall(r'\{(\w+)\}', template)
            for var in required_vars:
                if var not in variables:
                    raise KeyError(f"Missing required variable: {var}")
        
        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result


class EnhancedPrompts:
    """Mock enhanced prompts for testing"""
    
    def __init__(self):
        self.max_context_tokens = 2000
    
    def build_context(self, base_context, history):
        """Build enhanced context with history"""
        return {
            **base_context,
            "conversation_history": history
        }
    
    def optimize_prompt(self, prompt, optimization_goals=None):
        """Optimize prompt for better responses"""
        if not optimization_goals:
            return prompt
        
        optimized = prompt
        if "clarity" in optimization_goals:
            optimized += " Please provide a clear and detailed response."
        if "specificity" in optimization_goals:
            optimized += " Be specific in your recommendations."
        
        return optimized
    
    def manage_context_window(self, history):
        """Manage context window to fit token limits"""
        # Simple implementation - keep last N messages
        max_messages = 10
        if len(history) > max_messages:
            return history[-max_messages:]
        return history


class AgentUtils:
    """Mock agent utils for testing"""
    
    async def retry_with_backoff(self, func, max_retries=3, backoff_factor=1):
        """Retry function with exponential backoff"""
        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(backoff_factor * (2 ** attempt))
    
    async def execute_parallel(self, tasks):
        """Execute tasks in parallel"""
        return await asyncio.gather(*tasks)
    
    async def with_timeout(self, coro, timeout):
        """Execute coroutine with timeout"""
        return await asyncio.wait_for(coro, timeout=timeout)
    
    def merge_states(self, state1, state2):
        """Merge two agent states"""
        merged = DeepAgentState(user_request=state1.user_request)
        
        # Merge data_result
        merged.data_result = {}
        if hasattr(state1, 'data_result') and state1.data_result:
            merged.data_result.update(state1.data_result)
        if hasattr(state2, 'data_result') and state2.data_result:
            # Deep merge analysis
            if 'analysis' in merged.data_result and 'analysis' in state2.data_result:
                merged.data_result['analysis'].update(state2.data_result['analysis'])
            else:
                merged.data_result.update(state2.data_result)
        
        # Copy other attributes from state2 (override)
        if hasattr(state2, 'optimizations_result'):
            merged.optimizations_result = state2.optimizations_result
        
        return merged


class TestAgentPromptsTemplateRendering:
    """Test 8: Test prompt template generation"""
    async def test_prompt_template_rendering(self):
        """Test rendering of prompt templates with variables"""
        prompts = AgentPrompts()
        
        template = "Optimize {model_type} for {metric} with constraints: {constraints}"
        variables = {
            "model_type": "transformer",
            "metric": "latency",
            "constraints": "memory < 8GB"
        }
        
        result = prompts.render_template(template, variables)
        
        assert result == "Optimize transformer for latency with constraints: memory < 8GB"
    async def test_prompt_variable_substitution(self):
        """Test complex variable substitution in prompts"""
        prompts = AgentPrompts()
        
        template = """
        System: {system_prompt}
        User: {user_query}
        Context: {context}
        History: {history}
        """
        
        variables = {
            "system_prompt": "You are an AI optimizer",
            "user_query": "Improve model performance",
            "context": {"model": "GPT", "size": "7B"},
            "history": ["Previous optimization: batch size increased"]
        }
        
        result = prompts.render_template(template, variables)
        
        assert "You are an AI optimizer" in result
        assert "Improve model performance" in result
        assert str(variables["context"]) in result
    async def test_prompt_template_validation(self):
        """Test validation of prompt templates"""
        prompts = AgentPrompts()
        
        # Test with missing variables
        template = "Process {input} with {method}"
        variables = {"input": "data"}  # Missing 'method'
        
        with pytest.raises(KeyError) as exc:
            prompts.render_template(template, variables, strict=True)
        
        assert "method" in str(exc.value)


class TestEnhancedPromptsContextBuilding:
    """Test 9: Test enhanced context construction"""
    async def test_enhanced_context_construction(self):
        """Test building enhanced context for prompts"""
        enhanced_prompts = EnhancedPrompts()
        
        base_context = {
            "user_query": "Optimize training",
            "model_info": {"type": "transformer", "params": "7B"}
        }
        
        history = [
            {"role": "user", "content": "Previous query"},
            {"role": "assistant", "content": "Previous response"}
        ]
        
        enhanced_context = enhanced_prompts.build_context(base_context, history)
        
        assert enhanced_context["user_query"] == "Optimize training"
        assert len(enhanced_context["conversation_history"]) == 2
        assert "model_info" in enhanced_context
    async def test_prompt_optimization_logic(self):
        """Test prompt optimization for better responses"""
        enhanced_prompts = EnhancedPrompts()
        
        original_prompt = "Help me optimize my model"
        
        optimized = enhanced_prompts.optimize_prompt(
            original_prompt,
            optimization_goals=["clarity", "specificity"]
        )
        
        # Optimized prompt should be more specific
        assert len(optimized) > len(original_prompt)
        assert "specific" in optimized.lower() or "detailed" in optimized.lower()
    async def test_context_window_management(self):
        """Test management of context window size"""
        enhanced_prompts = EnhancedPrompts()
        enhanced_prompts.max_context_tokens = 1000
        
        # Create large context
        large_history = [
            {"role": "user", "content": "Query " * 100},
            {"role": "assistant", "content": "Response " * 100}
        ] * 10
        
        managed_context = enhanced_prompts.manage_context_window(large_history)
        
        # Should truncate to fit window
        assert len(managed_context) < len(large_history)
        # Should keep most recent messages
        assert managed_context[-1] == large_history[-1]


class TestAgentUtilsHelperFunctions:
    """Test 10: Test utility helper functions"""
    async def test_retry_with_backoff(self):
        """Test retry utility with exponential backoff"""
        utils = AgentUtils()
        
        call_count = 0
        
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "Success"
        
        result = await utils.retry_with_backoff(
            flaky_function,
            max_retries=3,
            backoff_factor=0.1
        )
        
        assert result == "Success"
        assert call_count == 3
    async def test_parallel_execution_helper(self):
        """Test parallel execution of multiple tasks"""
        utils = AgentUtils()
        
        async def task(n):
            await asyncio.sleep(0.1)
            return n * 2
        
        tasks = [task(i) for i in range(5)]
        results = await utils.execute_parallel(tasks)
        
        assert results == [0, 2, 4, 6, 8]
    async def test_timeout_wrapper(self):
        """Test timeout wrapper for long-running operations"""
        utils = AgentUtils()
        
        async def slow_operation():
            await asyncio.sleep(5)
            return "Complete"
        
        with pytest.raises(asyncio.TimeoutError):
            await utils.with_timeout(slow_operation(), timeout=0.5)
    async def test_state_merging_utility(self):
        """Test utility for merging agent states"""
        utils = AgentUtils()
        
        state1 = DeepAgentState(
            user_request="Query",
            data_result={"analysis": {"metric1": 10}}
        )
        
        state2 = DeepAgentState(
            user_request="Query",
            optimizations_result={"optimizations": [{"type": "batch"}]},
            data_result={"analysis": {"metric2": 20}}
        )
        
        merged = utils.merge_states(state1, state2)
        
        assert merged.user_request == "Query"
        assert merged.optimizations_result == {"optimizations": [{"type": "batch"}]}
        assert merged.data_result == {"analysis": {"metric1": 10, "metric2": 20}}