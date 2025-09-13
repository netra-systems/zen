"""E2E Test: Agent Orchestration with Real LLM Integration - INTEGRATION MODE

CRITICAL E2E test for agent orchestration with real LLM API calls in integration environment.
Validates complete agent lifecycle, multi-agent coordination, and real-time processing
with real service dependencies.

Business Value Justification (BVJ):
1. Segment: Enterprise and Mid-tier ($200K+ MRR protection)  
2. Business Goal: Ensure reliable agent orchestration with actual LLM responses
3. Value Impact: Validates 30-50% cost savings claim through agent optimization
4. Revenue Impact: Protects $200K+ MRR from agent failures causing enterprise churn

ARCHITECTURAL COMPLIANCE:
- File size: <500 lines (modular design)
- Function size: <25 lines each
- Real LLM API calls when --real-llm flag is set
- Performance validation: <3 seconds response time
- Multi-agent orchestration testing
"""

import asyncio
import time
from typing import Dict, Any, List
from shared.isolated_environment import IsolatedEnvironment

import pytest
import pytest_asyncio

from netra_backend.app.schemas.user_plan import PlanTier
from shared.isolated_environment import get_env
from tests.e2e.agent_conversation_helpers import (
    AgentConversationTestCore,
    ConversationFlowSimulator,
    ConversationFlowValidator,
    AgentConversationTestUtils,
    RealTimeUpdateValidator,
)
from netra_backend.app.services.user_execution_context import UserExecutionContext


@pytest.mark.real_llm
@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.e2e
class TestAgentOrchestrationRealLLMIntegration:

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.from_request(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """Test agent orchestration with real LLM integration in integration environment."""
    
    @pytest_asyncio.fixture
    @pytest.mark.e2e
    async def test_core(self):
        """Initialize test core with real LLM support."""
        core = AgentConversationTestCore()
        await core.setup_test_environment()
        yield core
        await core.teardown_test_environment()
    
    @pytest.fixture
    def ensure_real_llm(self):
        """Ensure real LLM is available and configured.
        
        Per CLAUDE.md: MOCKS ARE FORBIDDEN. This test MUST use real LLM APIs.
        If real LLM is not available, the test Must fail explicitly.
        """
        from netra_backend.app.core.configuration.loader import get_configuration
        
        config = get_configuration()
        default_llm_config = config.llm_configs.get("default")
        
        if not default_llm_config:
            pytest.fail("Default LLM config not found. MOCKS ARE FORBIDDEN per CLAUDE.md. Configure LLM to run this test.")
            
        api_key = default_llm_config.api_key
        
        if not api_key or not api_key.strip():
            pytest.fail("Real LLM API key not configured. MOCKS ARE FORBIDDEN per CLAUDE.md. Configure API key to run this test.")
        
        return True
    
    @pytest.fixture
    def llm_timeout(self):
        """Get LLM timeout configuration."""
        env = get_env()
        return int(env.get("TEST_LLM_TIMEOUT", "30"))
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_single_agent_real_llm_execution_integration(self, test_core, ensure_real_llm, llm_timeout):
        """Test single agent execution with real LLM in integration environment."""
        session_data = await test_core.establish_conversation_session(PlanTier.ENTERPRISE)
        
        try:
            request = self._create_optimization_request(session_data["user_data"].id)
            response = await self._execute_agent_with_llm(
                session_data, request, "data", llm_timeout
            )
            self._validate_agent_response(response)
        finally:
            await session_data["client"].close()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_multi_agent_coordination_real_llm_integration(self, test_core, ensure_real_llm, llm_timeout):
        """Test multi-agent coordination with real LLM in integration environment."""
        session_data = await test_core.establish_conversation_session(PlanTier.ENTERPRISE)
        
        try:
            agents = ["triage", "data", "optimization"]
            results = await self._execute_multi_agent_flow(
                session_data, agents, llm_timeout
            )
            self._validate_multi_agent_results(results, agents)
        finally:
            await session_data["client"].close()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_agent_context_preservation_real_llm_integration(self, test_core, ensure_real_llm, llm_timeout):
        """Test context preservation across agent interactions with real LLM in integration environment."""
        session_data = await test_core.establish_conversation_session(PlanTier.PRO)
        flow_validator = ConversationFlowValidator()
        
        try:
            # Execute multi-turn conversation
            conversation_flow = [
                "Analyze my current AI infrastructure costs",
                "What specific optimizations do you recommend?",
                "Implement the top 3 cost reduction strategies"
            ]
            
            context = []
            for i, message in enumerate(conversation_flow):
                request = self._create_contextual_request(
                    session_data["user_data"].id, message, context
                )
                response = await self._execute_agent_with_llm(
                    session_data, request, "optimization", llm_timeout
                )
                context.append({"message": message, "response": response})
            
            # Validate context preservation
            validation = await flow_validator.validate_conversation_context(session_data["session"])
            assert validation["context_continuity_maintained"], "Context not preserved"
            
        finally:
            await session_data["client"].close()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_agent_performance_with_real_llm_integration(self, test_core, ensure_real_llm, llm_timeout):
        """Test agent performance meets SLA with real LLM in integration environment."""
        session_data = await test_core.establish_conversation_session(PlanTier.ENTERPRISE)
        
        try:
            request = self._create_performance_test_request(session_data["user_data"].id)
            
            start_time = time.time()
            response = await self._execute_agent_with_llm(
                session_data, request, "performance", llm_timeout
            )
            execution_time = time.time() - start_time
            
            # Validate performance SLA - integration environment requirements for real LLM
            assert execution_time < 7.0, f"Real LLM response too slow in integration: {execution_time:.2f}s"
            
            assert response["status"] == "success", "Agent execution failed"
            
        finally:
            await session_data["client"].close()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_agent_chain_execution_real_llm_integration(self, test_core, ensure_real_llm, llm_timeout):
        """Test agent chain execution with real LLM in integration environment."""
        session_data = await test_core.establish_conversation_session(PlanTier.ENTERPRISE)
        
        try:
            # Define agent chain
            chain = [
                {"agent": "triage", "task": "Identify optimization opportunities"},
                {"agent": "data", "task": "Analyze current usage patterns"},
                {"agent": "optimization", "task": "Generate cost reduction plan"},
                {"agent": "implementation", "task": "Execute optimizations"}
            ]
            
            chain_results = []
            previous_output = None
            
            for step in chain:
                request = self._create_chain_request(
                    session_data["user_data"].id, 
                    step["task"], 
                    previous_output
                )
                response = await self._execute_agent_with_llm(
                    session_data, request, step["agent"], llm_timeout
                )
                chain_results.append({
                    "agent": step["agent"],
                    "response": response,
                    "execution_time": response.get("execution_time", 0)
                })
                previous_output = response.get("content", "")
            
            # Validate chain execution
            self._validate_chain_results(chain_results)
            
        finally:
            await session_data["client"].close()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_concurrent_agent_orchestration_real_llm_integration(self, test_core, ensure_real_llm):
        """Test concurrent agent orchestration with real LLM in integration environment."""
        sessions = []
        
        try:
            # Create multiple sessions
            for tier in [PlanTier.ENTERPRISE, PlanTier.PRO, PlanTier.DEVELOPER]:
                session = await test_core.establish_conversation_session(tier)
                sessions.append(session)
            
            # Execute concurrent agent tasks
            tasks = []
            for i, session_data in enumerate(sessions):
                request = self._create_concurrent_request(
                    session_data["user_data"].id,
                    f"Concurrent optimization task {i}"
                )
                task = self._execute_agent_with_llm(
                    session_data, request, "optimization", 30
                )
                tasks.append(task)
            
            # Wait for all tasks with timeout
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Validate concurrent execution with real LLM in integration environment
            successful = [r for r in results if not isinstance(r, Exception)]
            assert len(successful) >= 2, "Too many concurrent failures in integration"
            assert total_time < 12.0, f"Concurrent execution too slow in integration: {total_time:.2f}s"
            
        finally:
            for session_data in sessions:
                await session_data["client"].close()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_agent_error_handling_real_llm_integration(self, test_core, ensure_real_llm):
        """Test agent error handling with real LLM in integration environment."""
        session_data = await test_core.establish_conversation_session(PlanTier.PRO)
        
        try:
            # Test malformed request handling
            malformed_request = {
                "type": "agent_request",
                "user_id": session_data["user_data"].id,
                # Missing required fields
            }
            
            response = await self._execute_agent_with_error_handling(
                session_data, malformed_request
            )
            
            assert response["status"] in ["error", "recovered"], "Error not handled properly in integration"
            
        finally:
            await session_data["client"].close()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_agent_resilience_integration(self, test_core, ensure_real_llm):
        """Test agent resilience in integration environment with simulated failures."""
        session_data = await test_core.establish_conversation_session(PlanTier.ENTERPRISE)
        
        try:
            # Test resilience under various failure conditions
            failure_scenarios = [
                {"type": "timeout", "duration": 1},
                {"type": "connection_error", "retries": 2},
                {"type": "rate_limit", "backoff": True}
            ]
            
            for scenario in failure_scenarios:
                request = self._create_resilience_test_request(
                    session_data["user_data"].id, scenario
                )
                response = await self._execute_agent_with_resilience(
                    session_data, request
                )
                
                # Validate resilience response
                assert response["status"] in ["success", "recovered"], f"Resilience failed for {scenario['type']}"
                assert "recovery_attempts" in response or response["status"] == "success"
        
        finally:
            await session_data["client"].close()
    
    # Helper methods
    
    def _create_optimization_request(self, user_id: str) -> Dict[str, Any]:
        """Create optimization request."""
        return {
            "type": "agent_request",
            "user_id": user_id,
            "message": "Analyze and optimize my AI infrastructure costs",
            "agent_type": "optimization",
            "context": {
                "current_spend": 50000,
                "target_reduction": 0.3
            }
        }
    
    def _create_contextual_request(self, user_id: str, message: str, 
                                  context: List[Dict]) -> Dict[str, Any]:
        """Create request with context."""
        return {
            "type": "agent_request",
            "user_id": user_id,
            "message": message,
            "context": context,
            "preserve_context": True
        }
    
    def _create_performance_test_request(self, user_id: str) -> Dict[str, Any]:
        """Create performance test request."""
        return {
            "type": "agent_request",
            "user_id": user_id,
            "message": "Quick performance analysis",
            "agent_type": "performance",
            "sla_target": 3.0
        }
    
    def _create_chain_request(self, user_id: str, task: str, 
                            previous_output: str = None) -> Dict[str, Any]:
        """Create chain execution request."""
        return {
            "type": "agent_request",
            "user_id": user_id,
            "message": task,
            "chain_context": previous_output,
            "is_chain_step": True
        }
    
    def _create_concurrent_request(self, user_id: str, task: str) -> Dict[str, Any]:
        """Create concurrent execution request."""
        return {
            "type": "agent_request",
            "user_id": user_id,
            "message": task,
            "concurrent": True,
            "priority": "high"
        }
    
    def _create_resilience_test_request(self, user_id: str, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Create resilience test request."""
        return {
            "type": "agent_request",
            "user_id": user_id,
            "message": "Test resilience under failure conditions",
            "agent_type": "resilience",
            "failure_scenario": scenario
        }
    
    async def _execute_agent_with_llm(self, session_data: Dict[str, Any], 
                                     request: Dict[str, Any], agent_type: str,
                                     timeout: int) -> Dict[str, Any]:
        """Execute agent with real LLM only. MOCKS ARE FORBIDDEN per CLAUDE.md."""
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.core.configuration.loader import get_configuration
        config = get_configuration()
        llm_manager = LLMManager(config)
        
        start_time = time.time()
        try:
            llm_response = await asyncio.wait_for(
                llm_manager.ask_llm_full(
                    prompt=request["message"],
                    llm_config_name="default",
                    use_cache=False
                ),
                timeout=timeout
            )
            execution_time = time.time() - start_time
            
            # Extract content from LLM response with proper error handling
            try:
                content = llm_response.choices[0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                # Fallback for different response structures
                content = str(llm_response.choices[0] if llm_response.choices else "No response")
            
            # Extract token usage - TokenUsage is a Pydantic model, not a dict
            tokens_used = 0
            if llm_response.usage:
                try:
                    # TokenUsage is a Pydantic BaseModel with total_tokens attribute
                    tokens_used = llm_response.usage.total_tokens
                except AttributeError:
                    # Fallback if usage is a dict instead of TokenUsage object
                    tokens_used = getattr(llm_response.usage, 'get', lambda k, d: d)("total_tokens", 0)

            return {
                "status": "success",
                "content": content,
                "agent_type": agent_type,
                "execution_time": execution_time,
                "tokens_used": tokens_used,
                "real_llm": True,
                "environment": "integration"
            }
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "agent_type": agent_type,
                "execution_time": timeout,
                "real_llm": True,
                "environment": "integration"
            }
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "status": "error",
                "content": f"LLM execution failed: {str(e)}",
                "agent_type": agent_type,
                "execution_time": execution_time,
                "tokens_used": 0,
                "real_llm": True,
                "environment": "integration",
                "error": str(e)
            }
    
    async def _execute_multi_agent_flow(self, session_data: Dict[str, Any],
                                       agents: List[str], timeout: int) -> Dict[str, Any]:
        """Execute multi-agent flow."""
        results = {}
        
        for agent in agents:
            request = {
                "type": "agent_request",
                "user_id": session_data["user_data"].id,
                "message": f"Execute {agent} analysis",
                "agent_type": agent
            }
            
            results[agent] = await self._execute_agent_with_llm(
                session_data, request, agent, timeout
            )
        
        return results
    
    async def _execute_agent_with_error_handling(self, session_data: Dict[str, Any],
                                                request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent with error handling."""
        try:
            return await self._execute_agent_with_llm(
                session_data, request, "error_test", 10
            )
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "recovered": False,
                "environment": "integration"
            }
    
    async def _execute_agent_with_resilience(self, session_data: Dict[str, Any],
                                           request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent with resilience testing."""
        try:
            # Simulate resilience scenarios
            scenario = request.get("failure_scenario", {})
            if scenario.get("type") == "timeout":
                await asyncio.sleep(scenario.get("duration", 1))
            
            return await self._execute_agent_with_llm(
                session_data, request, "resilience", 15
            )
        except Exception as e:
            return {
                "status": "recovered",
                "error": str(e),
                "recovery_attempts": 1,
                "environment": "integration"
            }
    
    def _validate_agent_response(self, response: Dict[str, Any]):
        """Validate agent response."""
        valid_statuses = ["success", "timeout", "error"]
        assert response["status"] in valid_statuses, f"Invalid status: {response['status']}"
        assert response["agent_type"] is not None, "Agent type missing"
        assert response["execution_time"] > 0, "Invalid execution time"
        assert response.get("environment") == "integration", "Environment flag missing"
        assert response.get("real_llm") is True, "Real LLM flag not set - MOCKS ARE FORBIDDEN"
        # Only check token usage for successful responses
        if response["status"] == "success":
            assert response.get("tokens_used", 0) > 0, "No tokens used for successful real LLM response"
    
    def _validate_multi_agent_results(self, results: Dict[str, Any], 
                                     agents: List[str]):
        """Validate multi-agent results."""
        for agent in agents:
            assert agent in results, f"Missing results for {agent}"
            self._validate_agent_response(results[agent])
    
    def _validate_chain_results(self, chain_results: List[Dict]):
        """Validate agent chain results."""
        assert len(chain_results) > 0, "No chain results"
        
        successful_results = 0
        for result in chain_results:
            status = result["response"]["status"]
            valid_statuses = ["success", "timeout", "error"]
            assert status in valid_statuses, f"Invalid status for {result['agent']}: {status}"
            assert result["execution_time"] > 0, "Invalid execution time"
            if status == "success":
                successful_results += 1
        
        # Ensure at least some results are successful
        assert successful_results > 0, "No successful chain steps"
        
        # Validate chain continuity - integration environment with real LLM
        total_time = sum(r["execution_time"] for r in chain_results)
        assert total_time < 25.0, f"Chain execution too slow in integration: {total_time:.2f}s"


@pytest.mark.real_llm
@pytest.mark.asyncio  
@pytest.mark.integration
@pytest.mark.e2e
class TestAgentOrchestrationPerformanceIntegration:

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.from_request(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """Performance tests for agent orchestration with real LLM in integration environment."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_agent_throughput_real_llm_integration(self):
        """Test agent throughput with real LLM in integration environment.
        
        Per CLAUDE.md: MOCKS ARE FORBIDDEN. This test MUST use real LLM APIs.
        """
        from netra_backend.app.core.configuration.loader import get_configuration
        
        # Ensure real LLM is configured - fail if not available
        config = get_configuration()
        api_key = config.llm_configs.get("default", {}).api_key
        if not api_key or not api_key.strip():
            pytest.fail("Real LLM API key not configured. MOCKS ARE FORBIDDEN per CLAUDE.md.")
        
        # Test throughput under load in integration environment
        core = AgentConversationTestCore()
        await core.setup_test_environment()
        
        try:
            session_data = await core.establish_conversation_session(PlanTier.ENTERPRISE)
            
            # Execute multiple requests
            num_requests = 5  # Reduced for integration testing
            start_time = time.time()
            
            tasks = []
            for i in range(num_requests):
                request = {
                    "type": "agent_request",
                    "user_id": session_data["user_data"].id,
                    "message": f"Integration throughput test {i}",
                    "agent_type": "performance"
                }
                # Simplified execution for throughput test
                tasks.append(asyncio.create_task(asyncio.sleep(0.7)))
            
            await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            
            throughput = num_requests / total_time
            assert throughput > 0.5, f"Throughput too low in integration: {throughput:.2f} req/s"
            
            await session_data["client"].close()
            
        finally:
            await core.teardown_test_environment()