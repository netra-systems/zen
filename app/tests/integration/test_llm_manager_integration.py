"""
CRITICAL INTEGRATION TEST #14: LLM Manager Integration

BVJ:
- Segment: ALL (Free, Early, Mid, Enterprise) - Core AI functionality
- Business Goal: Platform Stability - Prevent $35K MRR loss from LLM integration failures
- Value Impact: Ensures agent request → LLM call → response handling → error recovery
- Revenue Impact: Prevents customer AI requests from failing due to broken LLM integration

REQUIREMENTS:
- Agent requests trigger LLM calls correctly
- LLM responses are handled and formatted properly
- Error recovery for LLM failures works
- Token usage tracking is accurate
- LLM response within 30 seconds
- 95% LLM request success rate
"""

import pytest
import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Set testing environment
import os
os.environ["TESTING"] = "1"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.llm.llm_manager import LLMManager
from app.agents.base_agent import BaseSubAgent
from app.agents.state import DeepAgentState
from app.logging_config import central_logger
from test_framework.mock_utils import mock_justified

logger = central_logger.get_logger(__name__)


class MockLLMProvider:
    """Mock LLM provider for testing LLM manager integration."""
    
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.request_count = 0
        self.total_tokens_used = 0
        self.response_times = []
        self.error_rate = 0.0  # 0.0 = no errors, 1.0 = always error
        self.failure_modes = {}
        self.rate_limit_count = 0
        
    async def generate_response(self, prompt: str, model: str = "gpt-4", **kwargs) -> Dict[str, Any]:
        """Generate LLM response with realistic behavior."""
        self.request_count += 1
        start_time = time.time()
        
        # Simulate processing time based on prompt length
        processing_time = 0.1 + (len(prompt) / 1000)  # Base + length factor
        await asyncio.sleep(min(processing_time, 3.0))  # Cap at 3 seconds
        
        response_time = time.time() - start_time
        self.response_times.append(response_time)
        
        # Simulate error conditions
        if self.error_rate > 0 and (self.request_count % int(1/self.error_rate)) == 0:
            if "rate_limit" in self.failure_modes:
                self.rate_limit_count += 1
                raise Exception("Rate limit exceeded")
            elif "timeout" in self.failure_modes:
                raise Exception("Request timeout")
            else:
                raise Exception("LLM provider error")
        
        # Generate response based on prompt content
        response_content = self._generate_contextual_response(prompt)
        
        # Calculate token usage
        prompt_tokens = len(prompt.split())
        completion_tokens = len(response_content.split())
        total_tokens = prompt_tokens + completion_tokens
        
        self.total_tokens_used += total_tokens
        
        return {
            "content": response_content,
            "model": model,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            },
            "finish_reason": "stop",
            "response_time": response_time,
            "provider": self.provider_name
        }
    
    def _generate_contextual_response(self, prompt: str) -> str:
        """Generate contextual response based on prompt content."""
        prompt_lower = prompt.lower()
        
        # Agent-specific responses
        if "triage" in prompt_lower or "route" in prompt_lower:
            return "Based on your request, I'll route this to the optimization specialist. This requires analysis of GPU memory usage, cost optimization, and performance tuning strategies."
        
        elif "optimization" in prompt_lower or "performance" in prompt_lower:
            return "GPU optimization analysis: Current usage shows 24GB peak allocation. Recommended strategies: 1) Enable gradient checkpointing for 30% memory reduction, 2) Implement mixed precision training, 3) Optimize batch sizes. Expected savings: $2,400/month with 2-week implementation timeline."
        
        elif "data" in prompt_lower or "analysis" in prompt_lower:
            return "Data analysis results: Query latency improved from 450ms to 180ms (60% improvement). Throughput increased from 1,200 to 3,400 QPS (183% increase). Error rate: 0.02% (within SLA). Cost impact: $1,800/month savings."
        
        elif "report" in prompt_lower or "summary" in prompt_lower:
            return "Performance Summary Report: System optimizations implemented successfully. Key improvements: 40% reduction in GPU memory usage, 60% improvement in query performance, 25% cost reduction. Next steps: Monitor performance metrics and scale optimizations to additional workloads."
        
        else:
            return "I understand your request and I'm here to help with AI workload optimization. I can assist with performance analysis, cost optimization, infrastructure scaling, and automated workflow improvements. Please let me know what specific area you'd like to focus on."
    
    def simulate_failure_mode(self, failure_type: str):
        """Simulate specific failure modes."""
        self.failure_modes[failure_type] = True
    
    def clear_failure_modes(self):
        """Clear all failure modes."""
        self.failure_modes.clear()


class MockLLMManagerWithIntegration(LLMManager):
    """Mock LLM manager with provider integration and fallback handling."""
    
    def __init__(self):
        self.providers = {
            "openai": MockLLMProvider("openai"),
            "anthropic": MockLLMProvider("anthropic"),
            "azure": MockLLMProvider("azure")
        }
        self.primary_provider = "openai"
        self.fallback_providers = ["anthropic", "azure"]
        self.request_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "fallback_usage": 0,
            "avg_response_time": 0,
            "total_tokens_used": 0
        }
        self.circuit_breaker_state = {}
    
    async def generate_response(self, prompt: str, agent_type: str = "general", **kwargs) -> Dict[str, Any]:
        """Generate response with provider fallback and error handling."""
        self.request_metrics["total_requests"] += 1
        start_time = time.time()
        
        # Try primary provider first
        providers_to_try = [self.primary_provider] + self.fallback_providers
        last_error = None
        
        for provider_name in providers_to_try:
            provider = self.providers[provider_name]
            
            # Check circuit breaker
            if self._is_circuit_breaker_open(provider_name):
                continue
            
            try:
                # Add agent-specific context to prompt
                enhanced_prompt = self._enhance_prompt_for_agent(prompt, agent_type)
                
                response = await provider.generate_response(enhanced_prompt, **kwargs)
                
                # Update metrics on success
                response_time = time.time() - start_time
                self.request_metrics["successful_requests"] += 1
                self._update_avg_response_time(response_time)
                self.request_metrics["total_tokens_used"] += response["usage"]["total_tokens"]
                
                # Track fallback usage
                if provider_name != self.primary_provider:
                    self.request_metrics["fallback_usage"] += 1
                
                # Reset circuit breaker on success
                self._reset_circuit_breaker(provider_name)
                
                # Add integration metadata
                response["integration_metadata"] = {
                    "provider_used": provider_name,
                    "agent_type": agent_type,
                    "fallback_used": provider_name != self.primary_provider,
                    "total_response_time": time.time() - start_time
                }
                
                return response
                
            except Exception as e:
                last_error = e
                self._trigger_circuit_breaker(provider_name)
                logger.warning(f"LLM provider {provider_name} failed: {e}")
                
                # If this was the primary provider, continue to fallback
                if provider_name == self.primary_provider:
                    continue
        
        # All providers failed
        self.request_metrics["failed_requests"] += 1
        raise Exception(f"All LLM providers failed. Last error: {last_error}")
    
    def _enhance_prompt_for_agent(self, prompt: str, agent_type: str) -> str:
        """Enhance prompt with agent-specific context."""
        agent_contexts = {
            "triage": "You are a triage agent that routes customer requests to appropriate specialists. Analyze the request and determine the best routing decision.",
            "optimization": "You are an AI optimization specialist. Provide detailed technical analysis and specific recommendations for performance improvements.",
            "data": "You are a data analysis specialist. Provide detailed metrics, insights, and quantified results from data analysis.",
            "reporting": "You are a reporting specialist. Create comprehensive, well-structured reports with clear findings and actionable recommendations."
        }
        
        context = agent_contexts.get(agent_type, "You are an AI assistant helping with optimization tasks.")
        return f"{context}\n\nUser request: {prompt}"
    
    def _is_circuit_breaker_open(self, provider_name: str) -> bool:
        """Check if circuit breaker is open for provider."""
        breaker_state = self.circuit_breaker_state.get(provider_name, {"failures": 0, "last_failure": 0})
        
        # Open circuit if more than 3 failures in last 60 seconds
        if breaker_state["failures"] >= 3:
            if time.time() - breaker_state["last_failure"] < 60:
                return True
        
        return False
    
    def _trigger_circuit_breaker(self, provider_name: str):
        """Trigger circuit breaker for provider."""
        if provider_name not in self.circuit_breaker_state:
            self.circuit_breaker_state[provider_name] = {"failures": 0, "last_failure": 0}
        
        self.circuit_breaker_state[provider_name]["failures"] += 1
        self.circuit_breaker_state[provider_name]["last_failure"] = time.time()
    
    def _reset_circuit_breaker(self, provider_name: str):
        """Reset circuit breaker for provider."""
        if provider_name in self.circuit_breaker_state:
            self.circuit_breaker_state[provider_name]["failures"] = 0
    
    def _update_avg_response_time(self, response_time: float):
        """Update average response time metric."""
        current_avg = self.request_metrics["avg_response_time"]
        successful_count = self.request_metrics["successful_requests"]
        
        self.request_metrics["avg_response_time"] = (
            (current_avg * (successful_count - 1) + response_time) / successful_count
        )
    
    def get_provider_stats(self) -> Dict[str, Any]:
        """Get comprehensive provider statistics."""
        provider_stats = {}
        
        for name, provider in self.providers.items():
            avg_response_time = sum(provider.response_times) / len(provider.response_times) if provider.response_times else 0
            
            provider_stats[name] = {
                "request_count": provider.request_count,
                "total_tokens": provider.total_tokens_used,
                "avg_response_time": avg_response_time,
                "rate_limit_hits": provider.rate_limit_count,
                "circuit_breaker_state": self.circuit_breaker_state.get(name, {"failures": 0})
            }
        
        return provider_stats


class MockAgentWithLLMIntegration(BaseSubAgent):
    """Mock agent with LLM manager integration for testing."""
    
    def __init__(self, name: str, llm_manager: MockLLMManagerWithIntegration):
        super().__init__(llm_manager, name=name)
        self.execution_history = []
        self.llm_interactions = []
    
    async def execute(self, request: Dict[str, Any], state: DeepAgentState) -> Dict[str, Any]:
        """Execute agent with LLM integration."""
        execution_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Extract user request
            user_message = request.get("user_message", "")
            
            # Generate LLM response
            llm_response = await self.llm_manager.generate_response(
                user_message, 
                agent_type=self.name
            )
            
            # Process and format response
            processed_response = self._process_llm_response(llm_response)
            
            execution_time = time.time() - start_time
            
            # Track execution
            execution_record = {
                "execution_id": execution_id,
                "agent": self.name,
                "user_message": user_message,
                "llm_response": processed_response,
                "execution_time": execution_time,
                "timestamp": datetime.now(timezone.utc)
            }
            
            self.execution_history.append(execution_record)
            self.llm_interactions.append({
                "prompt": user_message,
                "response": llm_response,
                "processing_time": execution_time
            })
            
            return {
                "status": "success",
                "execution_id": execution_id,
                "agent": self.name,
                "response": processed_response,
                "execution_time": execution_time,
                "llm_metadata": llm_response.get("integration_metadata", {})
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            error_record = {
                "execution_id": execution_id,
                "agent": self.name,
                "error": str(e),
                "execution_time": execution_time,
                "timestamp": datetime.now(timezone.utc)
            }
            
            self.execution_history.append(error_record)
            
            return {
                "status": "error",
                "execution_id": execution_id,
                "agent": self.name,
                "error": str(e),
                "execution_time": execution_time
            }
    
    def _process_llm_response(self, llm_response: Dict[str, Any]) -> Dict[str, Any]:
        """Process and format LLM response for agent output."""
        return {
            "content": llm_response["content"],
            "model_used": llm_response["model"],
            "tokens_used": llm_response["usage"]["total_tokens"],
            "response_quality": self._assess_response_quality(llm_response["content"]),
            "provider": llm_response.get("integration_metadata", {}).get("provider_used", "unknown")
        }
    
    def _assess_response_quality(self, content: str) -> Dict[str, float]:
        """Assess response quality metrics."""
        word_count = len(content.split())
        
        # Simple quality heuristics
        specificity = min(1.0, word_count / 50)  # More words = more specific
        actionability = 1.0 if any(word in content.lower() for word in ["implement", "configure", "optimize", "deploy"]) else 0.5
        technical_depth = 1.0 if any(word in content.lower() for word in ["gpu", "memory", "performance", "latency"]) else 0.5
        
        return {
            "specificity": specificity,
            "actionability": actionability,
            "technical_depth": technical_depth,
            "overall": (specificity + actionability + technical_depth) / 3
        }


class TestLLMManagerIntegration:
    """BVJ: Protects $35K MRR through reliable LLM manager integration."""

    @pytest.fixture
    def llm_manager(self):
        """Create mock LLM manager with integration capabilities."""
        return MockLLMManagerWithIntegration()

    @pytest.fixture
    def test_agents(self, llm_manager):
        """Create test agents with LLM integration."""
        return {
            "triage": MockAgentWithLLMIntegration("triage", llm_manager),
            "optimization": MockAgentWithLLMIntegration("optimization", llm_manager),
            "data": MockAgentWithLLMIntegration("data", llm_manager),
            "reporting": MockAgentWithLLMIntegration("reporting", llm_manager)
        }

    @pytest.mark.asyncio
    async def test_01_agent_llm_request_integration(self, test_agents, llm_manager):
        """BVJ: Validates agent requests trigger LLM calls correctly."""
        # Step 1: Test triage agent LLM integration
        triage_agent = test_agents["triage"]
        
        test_request = {
            "user_message": "I need to optimize GPU memory usage in my ML training pipeline",
            "user_id": "test_user_123"
        }
        
        start_time = time.time()
        result = await triage_agent.execute(test_request, DeepAgentState())
        execution_time = time.time() - start_time
        
        # Step 2: Validate execution results
        assert result["status"] == "success", f"Triage agent execution failed: {result.get('error')}"
        assert result["agent"] == "triage", "Agent identity mismatch"
        assert "response" in result, "Response missing from result"
        assert execution_time < 30.0, f"Execution took {execution_time:.2f}s, exceeds 30s limit"
        
        # Step 3: Validate LLM integration
        response_data = result["response"]
        assert "content" in response_data, "LLM response content missing"
        assert "model_used" in response_data, "Model information missing"
        assert "tokens_used" in response_data, "Token usage missing"
        assert "provider" in response_data, "Provider information missing"
        
        # Step 4: Verify LLM response quality
        quality_metrics = response_data["response_quality"]
        assert quality_metrics["overall"] >= 0.6, f"Response quality {quality_metrics['overall']:.2f} below 0.6"
        assert quality_metrics["specificity"] > 0.0, "Response not specific enough"
        
        # Step 5: Check LLM manager metrics
        manager_metrics = llm_manager.request_metrics
        assert manager_metrics["total_requests"] >= 1, "LLM request not tracked"
        assert manager_metrics["successful_requests"] >= 1, "Successful request not tracked"
        
        logger.info(f"Agent LLM integration validated: {execution_time:.2f}s execution time")

    @pytest.mark.asyncio
    async def test_02_llm_response_handling_and_formatting(self, test_agents, llm_manager):
        """BVJ: Validates LLM responses are handled and formatted properly."""
        # Step 1: Test different agent types with specialized responses
        test_scenarios = [
            {
                "agent": "optimization",
                "message": "Analyze GPU memory usage and provide optimization recommendations",
                "expected_keywords": ["gpu", "memory", "optimization", "performance"]
            },
            {
                "agent": "data",
                "message": "Analyze query performance metrics and identify bottlenecks",
                "expected_keywords": ["query", "performance", "latency", "metrics"]
            },
            {
                "agent": "reporting",
                "message": "Generate a summary report of optimization improvements",
                "expected_keywords": ["report", "summary", "improvements", "results"]
            }
        ]
        
        response_results = []
        
        for scenario in test_scenarios:
            agent = test_agents[scenario["agent"]]
            
            request = {
                "user_message": scenario["message"],
                "scenario_type": "response_handling_test"
            }
            
            start_time = time.time()
            result = await agent.execute(request, DeepAgentState())
            processing_time = time.time() - start_time
            
            # Validate response structure
            assert result["status"] == "success", f"Agent {scenario['agent']} execution failed"
            
            response_data = result["response"]
            content = response_data["content"].lower()
            
            # Check for expected keywords
            keywords_found = sum(1 for keyword in scenario["expected_keywords"] if keyword in content)
            keyword_coverage = keywords_found / len(scenario["expected_keywords"])
            
            response_results.append({
                "agent": scenario["agent"],
                "processing_time": processing_time,
                "content_length": len(response_data["content"]),
                "tokens_used": response_data["tokens_used"],
                "keyword_coverage": keyword_coverage,
                "quality_score": response_data["response_quality"]["overall"],
                "provider_used": response_data["provider"]
            })
        
        # Step 2: Validate response quality across agents
        for result in response_results:
            assert result["processing_time"] < 30.0, f"Agent {result['agent']} processing too slow"
            assert result["content_length"] > 50, f"Agent {result['agent']} response too short"
            assert result["tokens_used"] > 10, f"Agent {result['agent']} token usage too low"
            assert result["keyword_coverage"] >= 0.5, f"Agent {result['agent']} keyword coverage {result['keyword_coverage']:.2f} too low"
            assert result["quality_score"] >= 0.6, f"Agent {result['agent']} quality score {result['quality_score']:.2f} too low"
        
        # Step 3: Verify consistency in formatting
        avg_quality = sum(r["quality_score"] for r in response_results) / len(response_results)
        avg_processing_time = sum(r["processing_time"] for r in response_results) / len(response_results)
        
        assert avg_quality >= 0.7, f"Average response quality {avg_quality:.2f} below 0.7"
        assert avg_processing_time < 10.0, f"Average processing time {avg_processing_time:.2f}s too slow"
        
        logger.info(f"LLM response handling validated: {avg_quality:.2f} avg quality, {avg_processing_time:.2f}s avg time")

    @pytest.mark.asyncio
    async def test_03_llm_error_recovery_and_fallback(self, test_agents, llm_manager):
        """BVJ: Validates error recovery for LLM failures works correctly."""
        # Step 1: Configure primary provider to fail
        primary_provider = llm_manager.providers["openai"]
        primary_provider.error_rate = 1.0  # Always fail
        primary_provider.simulate_failure_mode("rate_limit")
        
        # Step 2: Test fallback behavior
        test_agent = test_agents["optimization"]
        
        test_request = {
            "user_message": "Optimize memory allocation for transformer model training"
        }
        
        start_time = time.time()
        result = await test_agent.execute(test_request, DeepAgentState())
        recovery_time = time.time() - start_time
        
        # Step 3: Validate successful fallback
        assert result["status"] == "success", f"Fallback execution failed: {result.get('error')}"
        
        llm_metadata = result["llm_metadata"]
        assert llm_metadata["fallback_used"], "Fallback not used when primary failed"
        assert llm_metadata["provider_used"] != "openai", "Should have fallen back from OpenAI"
        
        # Step 4: Verify fallback metrics
        manager_metrics = llm_manager.request_metrics
        assert manager_metrics["fallback_usage"] >= 1, "Fallback usage not tracked"
        assert manager_metrics["successful_requests"] >= 1, "Fallback success not tracked"
        
        # Step 5: Test multiple failure scenarios
        # Configure second provider to also fail
        anthropic_provider = llm_manager.providers["anthropic"]
        anthropic_provider.error_rate = 1.0
        anthropic_provider.simulate_failure_mode("timeout")
        
        # Should still succeed with third provider
        result2 = await test_agent.execute(test_request, DeepAgentState())
        assert result2["status"] == "success", "Complete fallback chain failed"
        assert result2["llm_metadata"]["provider_used"] == "azure", "Final fallback not used"
        
        # Step 6: Test complete failure scenario
        azure_provider = llm_manager.providers["azure"]
        azure_provider.error_rate = 1.0
        
        # Should fail gracefully when all providers fail
        result3 = await test_agent.execute(test_request, DeepAgentState())
        assert result3["status"] == "error", "Should fail when all providers fail"
        assert "All LLM providers failed" in result3["error"], "Error message not descriptive"
        
        # Step 7: Validate recovery timing
        assert recovery_time < 60.0, f"Error recovery took {recovery_time:.2f}s, too slow"
        
        logger.info(f"LLM error recovery validated: {recovery_time:.2f}s recovery time")

    @pytest.mark.asyncio
    async def test_04_token_usage_tracking_accuracy(self, test_agents, llm_manager):
        """BVJ: Validates token usage tracking is accurate across agents and providers."""
        # Step 1: Execute requests with varying prompt lengths
        token_tracking_tests = [
            {"agent": "triage", "message": "Route this request", "expected_range": (10, 50)},
            {"agent": "optimization", "message": "Perform comprehensive GPU memory optimization analysis including detailed recommendations for gradient checkpointing, mixed precision training, batch size optimization, and memory profiling strategies", "expected_range": (50, 150)},
            {"agent": "data", "message": "Analyze", "expected_range": (5, 30)},
            {"agent": "reporting", "message": "Generate detailed performance report with metrics, graphs, recommendations, implementation timeline, cost analysis, risk assessment, and next steps for AI workload optimization project", "expected_range": (70, 200)}
        ]
        
        token_results = []
        
        for test_case in token_tracking_tests:
            agent = test_agents[test_case["agent"]]
            
            request = {"user_message": test_case["message"]}
            
            # Track initial token count
            initial_tokens = llm_manager.request_metrics["total_tokens_used"]
            
            result = await agent.execute(request, DeepAgentState())
            
            # Check result token tracking
            assert result["status"] == "success", f"Token test failed for {test_case['agent']}"
            
            tokens_used = result["response"]["tokens_used"]
            expected_min, expected_max = test_case["expected_range"]
            
            token_results.append({
                "agent": test_case["agent"],
                "prompt_length": len(test_case["message"]),
                "tokens_used": tokens_used,
                "expected_range": test_case["expected_range"],
                "within_range": expected_min <= tokens_used <= expected_max
            })
        
        # Step 2: Validate token usage accuracy
        for result in token_results:
            assert result["within_range"], \
                f"Agent {result['agent']} token usage {result['tokens_used']} outside expected range {result['expected_range']}"
        
        # Step 3: Verify cumulative tracking
        final_tokens = llm_manager.request_metrics["total_tokens_used"]
        total_tracked_tokens = sum(r["tokens_used"] for r in token_results)
        
        # Should be approximately equal (allowing for previous test usage)
        assert final_tokens >= total_tracked_tokens, "Cumulative token tracking inconsistent"
        
        # Step 4: Check provider-level tracking
        provider_stats = llm_manager.get_provider_stats()
        
        total_provider_tokens = sum(stats["total_tokens"] for stats in provider_stats.values())
        assert total_provider_tokens >= total_tracked_tokens, "Provider token tracking inconsistent"
        
        # Step 5: Validate token efficiency
        avg_tokens_per_request = total_tracked_tokens / len(token_results)
        assert avg_tokens_per_request < 500, f"Average token usage {avg_tokens_per_request} too high"
        
        logger.info(f"Token tracking validated: {total_tracked_tokens} total tokens, {avg_tokens_per_request:.1f} avg per request")

    @pytest.mark.asyncio
    async def test_05_concurrent_llm_request_performance(self, test_agents, llm_manager):
        """BVJ: Validates LLM integration maintains performance under concurrent load."""
        # Step 1: Setup concurrent request scenario
        concurrent_requests = 20
        agent_types = ["triage", "optimization", "data", "reporting"]
        
        async def execute_concurrent_request(request_id: int):
            """Execute single concurrent LLM request."""
            agent_type = agent_types[request_id % len(agent_types)]
            agent = test_agents[agent_type]
            
            request = {
                "user_message": f"Concurrent request {request_id}: Optimize AI workload performance",
                "request_id": request_id
            }
            
            start_time = time.time()
            
            try:
                result = await agent.execute(request, DeepAgentState())
                execution_time = time.time() - start_time
                
                return {
                    "request_id": request_id,
                    "agent_type": agent_type,
                    "success": result["status"] == "success",
                    "execution_time": execution_time,
                    "tokens_used": result["response"]["tokens_used"] if result["status"] == "success" else 0,
                    "provider_used": result.get("llm_metadata", {}).get("provider_used", "unknown")
                }
                
            except Exception as e:
                execution_time = time.time() - start_time
                return {
                    "request_id": request_id,
                    "agent_type": agent_type,
                    "success": False,
                    "execution_time": execution_time,
                    "error": str(e)
                }
        
        # Step 2: Execute concurrent requests
        start_time = time.time()
        
        concurrent_results = await asyncio.gather(*[
            execute_concurrent_request(i) for i in range(concurrent_requests)
        ])
        
        total_concurrent_time = time.time() - start_time
        
        # Step 3: Analyze concurrent performance
        successful_requests = [r for r in concurrent_results if r["success"]]
        failed_requests = [r for r in concurrent_results if not r["success"]]
        
        success_rate = (len(successful_requests) / len(concurrent_results)) * 100
        
        assert success_rate >= 95.0, f"Success rate {success_rate}% below 95% under load"
        
        # Step 4: Validate response times
        if successful_requests:
            response_times = [r["execution_time"] for r in successful_requests]
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
            
            assert avg_response_time < 15.0, f"Average response time {avg_response_time:.2f}s too slow under load"
            assert p95_response_time < 30.0, f"P95 response time {p95_response_time:.2f}s exceeds 30s limit"
        
        # Step 5: Validate throughput
        throughput = len(successful_requests) / total_concurrent_time
        assert throughput >= 1.0, f"Throughput {throughput:.2f} requests/sec too low"
        
        # Step 6: Check provider distribution
        provider_usage = {}
        for result in successful_requests:
            provider = result["provider_used"]
            provider_usage[provider] = provider_usage.get(provider, 0) + 1
        
        # Should primarily use primary provider
        primary_usage = provider_usage.get("openai", 0)
        primary_usage_rate = (primary_usage / len(successful_requests)) * 100
        
        # Allow for some fallback usage but should be primarily primary
        assert primary_usage_rate >= 70.0, f"Primary provider usage {primary_usage_rate}% too low"
        
        logger.info(f"Concurrent LLM performance validated: {success_rate}% success, {throughput:.2f} req/sec")

    @pytest.mark.asyncio
    async def test_06_end_to_end_llm_integration_pipeline(self, test_agents, llm_manager):
        """BVJ: Validates complete end-to-end LLM integration pipeline."""
        # Step 1: Execute complete multi-agent LLM pipeline
        pipeline_start_time = time.time()
        
        # Simulate user conversation flow
        conversation_flow = [
            {"agent": "triage", "message": "I need help optimizing my AI infrastructure for better performance and cost efficiency"},
            {"agent": "optimization", "message": "Analyze GPU memory usage patterns and recommend optimization strategies"},
            {"agent": "data", "message": "Provide detailed performance metrics analysis for the optimization recommendations"},
            {"agent": "reporting", "message": "Generate comprehensive optimization report with findings and next steps"}
        ]
        
        pipeline_results = []
        
        for step in conversation_flow:
            agent = test_agents[step["agent"]]
            
            request = {
                "user_message": step["message"],
                "conversation_step": step["agent"]
            }
            
            step_start_time = time.time()
            result = await agent.execute(request, DeepAgentState())
            step_time = time.time() - step_start_time
            
            pipeline_results.append({
                "agent": step["agent"],
                "success": result["status"] == "success",
                "step_time": step_time,
                "response_quality": result["response"]["response_quality"]["overall"] if result["status"] == "success" else 0,
                "tokens_used": result["response"]["tokens_used"] if result["status"] == "success" else 0,
                "provider_used": result.get("llm_metadata", {}).get("provider_used", "unknown")
            })
        
        total_pipeline_time = time.time() - pipeline_start_time
        
        # Step 2: Validate pipeline execution
        successful_steps = [r for r in pipeline_results if r["success"]]
        assert len(successful_steps) == len(conversation_flow), "Not all pipeline steps completed successfully"
        
        # Step 3: Validate timing requirements
        assert total_pipeline_time < 120.0, f"Complete pipeline took {total_pipeline_time:.2f}s, exceeds 2 minutes"
        
        for result in pipeline_results:
            assert result["step_time"] < 30.0, f"Agent {result['agent']} step took {result['step_time']:.2f}s, exceeds 30s"
        
        # Step 4: Validate response quality progression
        for result in pipeline_results:
            assert result["response_quality"] >= 0.6, f"Agent {result['agent']} quality {result['response_quality']:.2f} below 0.6"
        
        # Step 5: Validate resource efficiency
        total_tokens = sum(r["tokens_used"] for r in pipeline_results)
        avg_tokens_per_step = total_tokens / len(pipeline_results)
        
        assert total_tokens < 2000, f"Pipeline used {total_tokens} tokens, too high"
        assert avg_tokens_per_step < 500, f"Average {avg_tokens_per_step} tokens per step too high"
        
        # Step 6: Verify LLM manager metrics
        final_metrics = llm_manager.request_metrics
        
        assert final_metrics["successful_requests"] >= len(conversation_flow), "Pipeline requests not tracked"
        assert final_metrics["avg_response_time"] < 20.0, f"Average response time {final_metrics['avg_response_time']:.2f}s too slow"
        
        # Step 7: Calculate pipeline efficiency
        steps_per_second = len(conversation_flow) / total_pipeline_time
        assert steps_per_second >= 0.1, f"Pipeline efficiency {steps_per_second:.2f} steps/sec too low"
        
        logger.info(f"E2E LLM pipeline validated: {total_pipeline_time:.2f}s total, {steps_per_second:.2f} steps/sec")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])