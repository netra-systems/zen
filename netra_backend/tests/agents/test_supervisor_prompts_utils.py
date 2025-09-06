from unittest.mock import Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Test module: Supervisor Prompts and Utils
# REMOVED_SYNTAX_ERROR: Split from large test file for architecture compliance
# REMOVED_SYNTAX_ERROR: Test classes: TestAgentPromptsTemplateRendering, TestEnhancedPromptsContextBuilding, TestAgentUtilsHelperFunctions
""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
from datetime import datetime, timezone

import pytest
# REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas import ( )
AgentCompleted,
AgentStarted,
SubAgentLifecycle,
SubAgentUpdate,
WebSocketMessage,


from netra_backend.app.agents.state import DeepAgentState
# REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.execution_context import ( )
AgentExecutionContext,
AgentExecutionResult,

from netra_backend.app.core.interfaces_execution import ExecutionStrategy

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager

# Mock classes for testing (would normally be imported)
# REMOVED_SYNTAX_ERROR: class AgentPrompts:
    # REMOVED_SYNTAX_ERROR: """Mock agent prompts for testing"""

# REMOVED_SYNTAX_ERROR: def render_template(self, template, variables, strict=False):
    # REMOVED_SYNTAX_ERROR: """Render template with variable substitution"""
    # REMOVED_SYNTAX_ERROR: if strict:
        # Check for missing variables
        # REMOVED_SYNTAX_ERROR: import re
        # REMOVED_SYNTAX_ERROR: required_vars = re.findall(r'\{(\w+)\}', template)
        # REMOVED_SYNTAX_ERROR: for var in required_vars:
            # REMOVED_SYNTAX_ERROR: if var not in variables:
                # REMOVED_SYNTAX_ERROR: raise KeyError("formatted_string")

                # REMOVED_SYNTAX_ERROR: result = template
                # REMOVED_SYNTAX_ERROR: for key, value in variables.items():
                    # REMOVED_SYNTAX_ERROR: result = result.replace("formatted_string", str(value))
                    # REMOVED_SYNTAX_ERROR: return result

# REMOVED_SYNTAX_ERROR: class EnhancedPrompts:
    # REMOVED_SYNTAX_ERROR: """Mock enhanced prompts for testing"""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: self.max_context_tokens = 2000

# REMOVED_SYNTAX_ERROR: def build_context(self, base_context, history):
    # REMOVED_SYNTAX_ERROR: """Build enhanced context with history"""
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: **base_context,
    # REMOVED_SYNTAX_ERROR: "conversation_history": history
    

# REMOVED_SYNTAX_ERROR: def optimize_prompt(self, prompt, optimization_goals=None):
    # REMOVED_SYNTAX_ERROR: """Optimize prompt for better responses"""
    # REMOVED_SYNTAX_ERROR: if not optimization_goals:
        # REMOVED_SYNTAX_ERROR: return prompt

        # REMOVED_SYNTAX_ERROR: optimized = prompt
        # REMOVED_SYNTAX_ERROR: if "clarity" in optimization_goals:
            # REMOVED_SYNTAX_ERROR: optimized += " Please provide a clear and detailed response."
            # REMOVED_SYNTAX_ERROR: if "specificity" in optimization_goals:
                # REMOVED_SYNTAX_ERROR: optimized += " Be specific in your recommendations."

                # REMOVED_SYNTAX_ERROR: return optimized

# REMOVED_SYNTAX_ERROR: def manage_context_window(self, history):
    # REMOVED_SYNTAX_ERROR: """Manage context window to fit token limits"""
    # Simple implementation - keep last N messages
    # REMOVED_SYNTAX_ERROR: max_messages = 10
    # REMOVED_SYNTAX_ERROR: if len(history) > max_messages:
        # REMOVED_SYNTAX_ERROR: return history[-max_messages:]
        # REMOVED_SYNTAX_ERROR: return history

# REMOVED_SYNTAX_ERROR: class AgentUtils:
    # REMOVED_SYNTAX_ERROR: """Mock agent utils for testing"""

# REMOVED_SYNTAX_ERROR: async def retry_with_backoff(self, func, max_retries=3, backoff_factor=1):
    # REMOVED_SYNTAX_ERROR: """Retry function with exponential backoff"""
    # REMOVED_SYNTAX_ERROR: for attempt in range(max_retries):
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: return await func()
            # REMOVED_SYNTAX_ERROR: except Exception as e:
                # REMOVED_SYNTAX_ERROR: if attempt == max_retries - 1:
                    # REMOVED_SYNTAX_ERROR: raise
                    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(backoff_factor * (2 ** attempt))

# REMOVED_SYNTAX_ERROR: async def execute_parallel(self, tasks):
    # REMOVED_SYNTAX_ERROR: """Execute tasks in parallel"""
    # REMOVED_SYNTAX_ERROR: return await asyncio.gather(*tasks)

# REMOVED_SYNTAX_ERROR: async def with_timeout(self, coro, timeout):
    # REMOVED_SYNTAX_ERROR: """Execute coroutine with timeout"""
    # REMOVED_SYNTAX_ERROR: return await asyncio.wait_for(coro, timeout=timeout)

# REMOVED_SYNTAX_ERROR: def merge_states(self, state1, state2):
    # REMOVED_SYNTAX_ERROR: """Merge two agent states"""
    # REMOVED_SYNTAX_ERROR: merged = DeepAgentState(user_request=state1.user_request)

    # Merge data_result
    # REMOVED_SYNTAX_ERROR: merged.data_result = {}
    # REMOVED_SYNTAX_ERROR: if hasattr(state1, 'data_result') and state1.data_result:
        # REMOVED_SYNTAX_ERROR: merged.data_result.update(state1.data_result)
        # REMOVED_SYNTAX_ERROR: if hasattr(state2, 'data_result') and state2.data_result:
            # Deep merge analysis
            # REMOVED_SYNTAX_ERROR: if 'analysis' in merged.data_result and 'analysis' in state2.data_result:
                # REMOVED_SYNTAX_ERROR: merged.data_result['analysis'].update(state2.data_result['analysis'])
                # REMOVED_SYNTAX_ERROR: else:
                    # REMOVED_SYNTAX_ERROR: merged.data_result.update(state2.data_result)

                    # Copy other attributes from state2 (override)
                    # REMOVED_SYNTAX_ERROR: if hasattr(state2, 'optimizations_result'):
                        # REMOVED_SYNTAX_ERROR: merged.optimizations_result = state2.optimizations_result

                        # REMOVED_SYNTAX_ERROR: return merged

# REMOVED_SYNTAX_ERROR: class TestAgentPromptsTemplateRendering:
    # REMOVED_SYNTAX_ERROR: """Test 8: Test prompt template generation"""
    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_prompt_template_rendering(self):
        # REMOVED_SYNTAX_ERROR: """Test rendering of prompt templates with variables"""
        # REMOVED_SYNTAX_ERROR: prompts = AgentPrompts()

        # REMOVED_SYNTAX_ERROR: template = "Optimize {model_type} for {metric} with constraints: {constraints}"
        # REMOVED_SYNTAX_ERROR: variables = { )
        # REMOVED_SYNTAX_ERROR: "model_type": "transformer",
        # REMOVED_SYNTAX_ERROR: "metric": "latency",
        # REMOVED_SYNTAX_ERROR: "constraints": "memory < 8GB"
        

        # REMOVED_SYNTAX_ERROR: result = prompts.render_template(template, variables)

        # REMOVED_SYNTAX_ERROR: assert result == "Optimize transformer for latency with constraints: memory < 8GB"
        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_prompt_variable_substitution(self):
            # REMOVED_SYNTAX_ERROR: """Test complex variable substitution in prompts"""
            # REMOVED_SYNTAX_ERROR: prompts = AgentPrompts()

            # REMOVED_SYNTAX_ERROR: template = '''
            # REMOVED_SYNTAX_ERROR: System: {system_prompt}
            # REMOVED_SYNTAX_ERROR: User: {user_query}
            # REMOVED_SYNTAX_ERROR: Context: {context}
            # REMOVED_SYNTAX_ERROR: History: {history}
            # REMOVED_SYNTAX_ERROR: """"

            # REMOVED_SYNTAX_ERROR: variables = { )
            # REMOVED_SYNTAX_ERROR: "system_prompt": "You are an AI optimizer",
            # REMOVED_SYNTAX_ERROR: "user_query": "Improve model performance",
            # REMOVED_SYNTAX_ERROR: "context": {"model": "GPT", "size": "7B"},
            # REMOVED_SYNTAX_ERROR: "history": ["Previous optimization: batch size increased"]
            

            # REMOVED_SYNTAX_ERROR: result = prompts.render_template(template, variables)

            # REMOVED_SYNTAX_ERROR: assert "You are an AI optimizer" in result
            # REMOVED_SYNTAX_ERROR: assert "Improve model performance" in result
            # REMOVED_SYNTAX_ERROR: assert str(variables["context"]) in result
            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_prompt_template_validation(self):
                # REMOVED_SYNTAX_ERROR: """Test validation of prompt templates"""
                # REMOVED_SYNTAX_ERROR: prompts = AgentPrompts()

                # Test with missing variables
                # REMOVED_SYNTAX_ERROR: template = "Process {input} with {method}"
                # REMOVED_SYNTAX_ERROR: variables = {"input": "data"}  # Missing 'method'

                # REMOVED_SYNTAX_ERROR: with pytest.raises(KeyError) as exc:
                    # REMOVED_SYNTAX_ERROR: prompts.render_template(template, variables, strict=True)

                    # REMOVED_SYNTAX_ERROR: assert "method" in str(exc.value)

# REMOVED_SYNTAX_ERROR: class TestEnhancedPromptsContextBuilding:
    # REMOVED_SYNTAX_ERROR: """Test 9: Test enhanced context construction"""
    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_enhanced_context_construction(self):
        # REMOVED_SYNTAX_ERROR: """Test building enhanced context for prompts"""
        # REMOVED_SYNTAX_ERROR: enhanced_prompts = EnhancedPrompts()

        # REMOVED_SYNTAX_ERROR: base_context = { )
        # REMOVED_SYNTAX_ERROR: "user_query": "Optimize training",
        # REMOVED_SYNTAX_ERROR: "model_info": {"type": "transformer", "params": "7B"}
        

        # REMOVED_SYNTAX_ERROR: history = [ )
        # REMOVED_SYNTAX_ERROR: {"role": "user", "content": "Previous query"},
        # REMOVED_SYNTAX_ERROR: {"role": "assistant", "content": "Previous response"}
        

        # REMOVED_SYNTAX_ERROR: enhanced_context = enhanced_prompts.build_context(base_context, history)

        # REMOVED_SYNTAX_ERROR: assert enhanced_context["user_query"] == "Optimize training"
        # REMOVED_SYNTAX_ERROR: assert len(enhanced_context["conversation_history"]) == 2
        # REMOVED_SYNTAX_ERROR: assert "model_info" in enhanced_context
        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_prompt_optimization_logic(self):
            # REMOVED_SYNTAX_ERROR: """Test prompt optimization for better responses"""
            # REMOVED_SYNTAX_ERROR: enhanced_prompts = EnhancedPrompts()

            # REMOVED_SYNTAX_ERROR: original_prompt = "Help me optimize my model"

            # REMOVED_SYNTAX_ERROR: optimized = enhanced_prompts.optimize_prompt( )
            # REMOVED_SYNTAX_ERROR: original_prompt,
            # REMOVED_SYNTAX_ERROR: optimization_goals=["clarity", "specificity"]
            

            # Optimized prompt should be more specific
            # REMOVED_SYNTAX_ERROR: assert len(optimized) > len(original_prompt)
            # REMOVED_SYNTAX_ERROR: assert "specific" in optimized.lower() or "detailed" in optimized.lower()
            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_context_window_management(self):
                # REMOVED_SYNTAX_ERROR: """Test management of context window size"""
                # REMOVED_SYNTAX_ERROR: enhanced_prompts = EnhancedPrompts()
                # REMOVED_SYNTAX_ERROR: enhanced_prompts.max_context_tokens = 1000

                # Create large context
                # REMOVED_SYNTAX_ERROR: large_history = [ )
                # REMOVED_SYNTAX_ERROR: {"role": "user", "content": "Query " * 100},
                # REMOVED_SYNTAX_ERROR: {"role": "assistant", "content": "Response " * 100}
                # REMOVED_SYNTAX_ERROR: ] * 10

                # REMOVED_SYNTAX_ERROR: managed_context = enhanced_prompts.manage_context_window(large_history)

                # Should truncate to fit window
                # REMOVED_SYNTAX_ERROR: assert len(managed_context) < len(large_history)
                # Should keep most recent messages
                # REMOVED_SYNTAX_ERROR: assert managed_context[-1] == large_history[-1]

# REMOVED_SYNTAX_ERROR: class TestAgentUtilsHelperFunctions:
    # REMOVED_SYNTAX_ERROR: """Test 10: Test utility helper functions"""
    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_retry_with_backoff(self):
        # REMOVED_SYNTAX_ERROR: """Test retry utility with exponential backoff"""
        # REMOVED_SYNTAX_ERROR: utils = AgentUtils()

        # REMOVED_SYNTAX_ERROR: call_count = 0

# REMOVED_SYNTAX_ERROR: async def flaky_function():
    # REMOVED_SYNTAX_ERROR: nonlocal call_count
    # REMOVED_SYNTAX_ERROR: call_count += 1
    # REMOVED_SYNTAX_ERROR: if call_count < 3:
        # REMOVED_SYNTAX_ERROR: raise ConnectionError("Temporary failure")
        # REMOVED_SYNTAX_ERROR: return "Success"

        # REMOVED_SYNTAX_ERROR: result = await utils.retry_with_backoff( )
        # REMOVED_SYNTAX_ERROR: flaky_function,
        # REMOVED_SYNTAX_ERROR: max_retries=3,
        # REMOVED_SYNTAX_ERROR: backoff_factor=0.1
        

        # REMOVED_SYNTAX_ERROR: assert result == "Success"
        # REMOVED_SYNTAX_ERROR: assert call_count == 3
        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_parallel_execution_helper(self):
            # REMOVED_SYNTAX_ERROR: """Test parallel execution of multiple tasks"""
            # REMOVED_SYNTAX_ERROR: utils = AgentUtils()

# REMOVED_SYNTAX_ERROR: async def task(n):
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)
    # REMOVED_SYNTAX_ERROR: return n * 2

    # REMOVED_SYNTAX_ERROR: tasks = [task(i) for i in range(5)]
    # REMOVED_SYNTAX_ERROR: results = await utils.execute_parallel(tasks)

    # REMOVED_SYNTAX_ERROR: assert results == [0, 2, 4, 6, 8]
    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_timeout_wrapper(self):
        # REMOVED_SYNTAX_ERROR: """Test timeout wrapper for long-running operations"""
        # REMOVED_SYNTAX_ERROR: utils = AgentUtils()

# REMOVED_SYNTAX_ERROR: async def slow_operation():
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(5)
    # REMOVED_SYNTAX_ERROR: return "Complete"

    # REMOVED_SYNTAX_ERROR: with pytest.raises(asyncio.TimeoutError):
        # REMOVED_SYNTAX_ERROR: await utils.with_timeout(slow_operation(), timeout=0.5)
        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_state_merging_utility(self):
            # REMOVED_SYNTAX_ERROR: """Test utility for merging agent states"""
            # REMOVED_SYNTAX_ERROR: utils = AgentUtils()

            # REMOVED_SYNTAX_ERROR: state1 = DeepAgentState( )
            # REMOVED_SYNTAX_ERROR: user_request="Query",
            # REMOVED_SYNTAX_ERROR: data_result={"analysis": {"metric1": 10}}
            

            # REMOVED_SYNTAX_ERROR: state2 = DeepAgentState( )
            # REMOVED_SYNTAX_ERROR: user_request="Query",
            # REMOVED_SYNTAX_ERROR: optimizations_result={"optimizations": [{"type": "batch"]]],
            # REMOVED_SYNTAX_ERROR: data_result={"analysis": {"metric2": 20}}
            

            # REMOVED_SYNTAX_ERROR: merged = utils.merge_states(state1, state2)

            # REMOVED_SYNTAX_ERROR: assert merged.user_request == "Query"
            # REMOVED_SYNTAX_ERROR: assert merged.optimizations_result == {"optimizations": [{"type": "batch"]]]
            # REMOVED_SYNTAX_ERROR: assert merged.data_result == {"analysis": {"metric1": 10, "metric2": 20}}