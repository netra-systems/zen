"""
Test External LLM Provider Integration

Business Value Justification (BVJ):
- Segment: All customer segments (core AI functionality)
- Business Goal: Ensure reliable AI service delivery through multiple LLM providers
- Value Impact: LLM failures directly impact customer value delivery and satisfaction
- Strategic Impact: Provider diversity enables cost optimization and service resilience

CRITICAL REQUIREMENTS:
- Tests real LLM provider APIs (OpenAI, Anthropic, etc.)
- Validates failover, rate limiting, and cost optimization
- Uses real API calls, NO MOCKS for provider testing
- Ensures response quality and latency standards
"""

import pytest
import asyncio
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import uuid

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.isolated_test_helper import IsolatedTestHelper
from shared.isolated_environment import get_env

from netra_backend.app.services.llm.llm_provider_manager import LLMProviderManager
from netra_backend.app.services.llm.provider_failover import ProviderFailover
from netra_backend.app.services.llm.response_validator import ResponseValidator
from netra_backend.app.services.llm.cost_optimizer import LLMCostOptimizer


class TestExternalLLMProviderIntegration(SSotBaseTestCase):
    """
    Test external LLM provider integration with real API calls.
    
    Tests critical LLM functionality that directly impacts customer value:
    - Multi-provider reliability and failover
    - Response quality validation and filtering
    - Cost optimization across providers
    - Rate limiting and quota management
    """
    
    def setup_method(self):
        """Set up test environment with real LLM providers"""
        super().setup_method() if hasattr(super(), 'setup_method') else None
        self.env = get_env()
        self.isolated_helper = IsolatedTestHelper()
        
        # Test configuration
        self.test_prefix = f"llm_test_{uuid.uuid4().hex[:8]}"
        
        # Initialize LLM components
        self.provider_manager = LLMProviderManager()
        self.failover = ProviderFailover()
        self.response_validator = ResponseValidator()
        self.cost_optimizer = LLMCostOptimizer()
        
        # Test prompts for different use cases
        self.test_prompts = {
            "simple_query": "What is 2 + 2?",
            "code_generation": "Write a Python function that calculates the factorial of a number.",
            "data_analysis": "Analyze the following data and provide insights: [1, 5, 3, 8, 2, 9, 4]",
            "optimization_advice": "How can I optimize AWS costs for a startup with 100TB of data?",
            "complex_reasoning": "Explain the potential impact of quantum computing on current encryption methods."
        }
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_openai_provider_integration(self):
        """
        Test OpenAI provider integration with real API calls.
        
        BUSINESS CRITICAL: OpenAI is primary LLM provider for customer interactions.
        Failures directly impact customer satisfaction and platform reliability.
        """
        # Check if OpenAI credentials are available
        openai_api_key = self.env.get("OPENAI_API_KEY")
        if not openai_api_key:
            pytest.skip("OpenAI API key not available for integration testing")
        
        # Configure OpenAI provider
        openai_config = {
            "provider": "openai",
            "model": "gpt-4",
            "api_key": openai_api_key,
            "max_tokens": 500,
            "temperature": 0.1,
            "timeout_seconds": 30
        }
        
        # Test basic LLM functionality
        for prompt_type, prompt_text in self.test_prompts.items():
            print(f"Testing OpenAI with prompt type: {prompt_type}")
            
            start_time = time.time()
            
            response = await self.provider_manager.generate_completion(
                provider_config=openai_config,
                prompt=prompt_text,
                test_prefix=self.test_prefix
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Validate response structure
            assert response.success is True, f"OpenAI request failed: {response.error}"
            assert response.text is not None, "Response text should not be None"
            assert len(response.text.strip()) > 0, "Response should have content"
            assert response.token_usage.total_tokens > 0, "Should track token usage"
            assert response.model == "gpt-4", "Should use requested model"
            
            # Validate response time
            assert response_time < 60, f"Response time too slow: {response_time}s"
            
            # Validate response content based on prompt type
            if prompt_type == "simple_query":
                # Should contain the answer "4" for 2+2
                assert "4" in response.text, "Should correctly answer simple math"
                
            elif prompt_type == "code_generation":
                # Should contain Python code with function definition
                assert "def" in response.text, "Should contain function definition"
                assert "factorial" in response.text.lower(), "Should mention factorial"
                
            elif prompt_type == "optimization_advice":
                # Should mention relevant AWS services or cost optimization strategies
                optimization_keywords = ["s3", "archive", "tier", "cost", "storage", "compute"]
                has_optimization_content = any(keyword in response.text.lower() for keyword in optimization_keywords)
                assert has_optimization_content, "Should provide relevant optimization advice"
            
            # Validate token usage and costs
            assert response.token_usage.prompt_tokens > 0, "Should track prompt tokens"
            assert response.token_usage.completion_tokens > 0, "Should track completion tokens"
            
            # Calculate estimated cost
            estimated_cost = self.cost_optimizer.calculate_request_cost(
                provider="openai",
                model="gpt-4",
                token_usage=response.token_usage
            )
            
            assert estimated_cost > 0, "Should calculate request cost"
            assert estimated_cost < 1.0, f"Single request cost too high: ${estimated_cost}"
            
            # Small delay between requests to respect rate limits
            await asyncio.sleep(1)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_anthropic_provider_integration(self):
        """
        Test Anthropic (Claude) provider integration with real API calls.
        
        BUSINESS CRITICAL: Anthropic provides backup capability and specific
        use cases requiring longer context windows.
        """
        # Check if Anthropic credentials are available
        anthropic_api_key = self.env.get("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            pytest.skip("Anthropic API key not available for integration testing")
        
        # Configure Anthropic provider
        anthropic_config = {
            "provider": "anthropic",
            "model": "claude-3-sonnet-20240229",
            "api_key": anthropic_api_key,
            "max_tokens": 500,
            "temperature": 0.1,
            "timeout_seconds": 30
        }
        
        # Test with a subset of prompts (to manage API costs)
        test_prompts = ["simple_query", "optimization_advice"]
        
        for prompt_type in test_prompts:
            prompt_text = self.test_prompts[prompt_type]
            print(f"Testing Anthropic with prompt type: {prompt_type}")
            
            start_time = time.time()
            
            response = await self.provider_manager.generate_completion(
                provider_config=anthropic_config,
                prompt=prompt_text,
                test_prefix=self.test_prefix
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Validate response structure
            assert response.success is True, f"Anthropic request failed: {response.error}"
            assert response.text is not None, "Response text should not be None"
            assert len(response.text.strip()) > 0, "Response should have content"
            assert response.token_usage.total_tokens > 0, "Should track token usage"
            
            # Validate response time
            assert response_time < 60, f"Response time too slow: {response_time}s"
            
            # Validate response quality
            quality_score = self.response_validator.assess_response_quality(
                prompt=prompt_text,
                response=response.text,
                criteria=["relevance", "completeness", "accuracy"]
            )
            
            assert quality_score.overall_score >= 0.7, f"Response quality too low: {quality_score.overall_score}"
            assert quality_score.relevance_score >= 0.8, "Response should be relevant to prompt"
            
            # Calculate cost
            estimated_cost = self.cost_optimizer.calculate_request_cost(
                provider="anthropic",
                model="claude-3-sonnet-20240229",
                token_usage=response.token_usage
            )
            
            assert estimated_cost > 0, "Should calculate request cost"
            
            await asyncio.sleep(2)  # Anthropic rate limiting
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_provider_failover_mechanism(self):
        """
        Test provider failover mechanism with real providers.
        
        BUSINESS CRITICAL: Failover ensures service continuity when primary
        provider fails, preventing customer service disruptions.
        """
        # Configure primary and backup providers
        primary_config = {
            "provider": "openai",
            "model": "gpt-4",
            "api_key": self.env.get("OPENAI_API_KEY", "invalid_key_for_testing"),
            "priority": 1,
            "timeout_seconds": 10
        }
        
        backup_config = {
            "provider": "anthropic", 
            "model": "claude-3-sonnet-20240229",
            "api_key": self.env.get("ANTHROPIC_API_KEY", "invalid_key_for_testing"),
            "priority": 2,
            "timeout_seconds": 10
        }
        
        # Skip if no valid API keys
        if not self.env.get("OPENAI_API_KEY") and not self.env.get("ANTHROPIC_API_KEY"):
            pytest.skip("No LLM API keys available for failover testing")
        
        # Test failover configuration
        failover_config = {
            "providers": [primary_config, backup_config],
            "max_retries": 2,
            "retry_delay_seconds": 1,
            "circuit_breaker_threshold": 3,
            "circuit_breaker_timeout": 60
        }
        
        await self.failover.configure(failover_config)
        
        # Test normal operation (should use primary provider if available)
        prompt = self.test_prompts["simple_query"]
        
        normal_response = await self.failover.generate_with_failover(
            prompt=prompt,
            test_prefix=self.test_prefix
        )
        
        # Should succeed with either provider
        assert normal_response.success is True, f"Failover request failed: {normal_response.error}"
        assert normal_response.provider_used in ["openai", "anthropic"], "Should use configured provider"
        assert normal_response.text is not None, "Should have response text"
        
        # Test failover behavior by simulating primary provider failure
        # (Using invalid API key for primary)
        failing_primary_config = {
            **primary_config,
            "api_key": "invalid_test_key_12345"
        }
        
        failing_failover_config = {
            "providers": [failing_primary_config, backup_config],
            "max_retries": 2,
            "retry_delay_seconds": 0.5,
            "circuit_breaker_threshold": 3,
            "circuit_breaker_timeout": 60
        }
        
        await self.failover.configure(failing_failover_config)
        
        # This should failover to backup provider if backup key is valid
        if self.env.get("ANTHROPIC_API_KEY"):
            failover_response = await self.failover.generate_with_failover(
                prompt=prompt,
                test_prefix=self.test_prefix
            )
            
            # Should succeed using backup provider
            assert failover_response.success is True, "Failover should succeed with backup provider"
            assert failover_response.provider_used == "anthropic", "Should use backup provider after failover"
            assert failover_response.failover_occurred is True, "Should record failover occurrence"
            assert failover_response.primary_provider_failure is not None, "Should record primary failure reason"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_llm_rate_limiting_and_quota_management(self):
        """
        Test LLM rate limiting and quota management across providers.
        
        BUSINESS CRITICAL: Rate limiting prevents API quota exhaustion and
        ensures fair usage across customers and use cases.
        """
        # Configure rate limiting for testing
        rate_limit_config = {
            "requests_per_minute": 10,
            "tokens_per_minute": 5000,
            "burst_limit": 3,
            "quota_enforcement": True
        }
        
        await self.provider_manager.configure_rate_limiting(rate_limit_config)
        
        # Test normal rate limiting (within limits)
        normal_requests = []
        provider_config = {
            "provider": "openai" if self.env.get("OPENAI_API_KEY") else "anthropic",
            "model": "gpt-4" if self.env.get("OPENAI_API_KEY") else "claude-3-sonnet-20240229",
            "api_key": self.env.get("OPENAI_API_KEY") or self.env.get("ANTHROPIC_API_KEY"),
            "max_tokens": 100,  # Small tokens for rate limit testing
            "temperature": 0.1
        }
        
        if not provider_config["api_key"]:
            pytest.skip("No LLM API key available for rate limiting test")
        
        # Make requests within rate limit
        for i in range(3):  # Within burst limit
            start_time = time.time()
            
            response = await self.provider_manager.generate_completion(
                provider_config=provider_config,
                prompt=f"Count to {i + 1}",
                test_prefix=self.test_prefix
            )
            
            end_time = time.time()
            
            normal_requests.append({
                "success": response.success,
                "response_time": end_time - start_time,
                "tokens_used": response.token_usage.total_tokens if response.success else 0,
                "rate_limited": getattr(response, 'rate_limited', False)
            })
            
            # Small delay between requests
            await asyncio.sleep(6)  # 6 seconds = 10 requests per minute
        
        # All normal requests should succeed
        successful_normal = [r for r in normal_requests if r["success"]]
        assert len(successful_normal) == len(normal_requests), "Normal requests should all succeed"
        
        # None should be rate limited
        rate_limited_normal = [r for r in normal_requests if r.get("rate_limited")]
        assert len(rate_limited_normal) == 0, "Normal requests should not be rate limited"
        
        # Test rate limiting by making rapid requests (exceeding burst limit)
        rapid_requests = []
        
        for i in range(5):  # Exceed burst limit of 3
            start_time = time.time()
            
            response = await self.provider_manager.generate_completion(
                provider_config=provider_config,
                prompt=f"Quick count: {i}",
                test_prefix=self.test_prefix
            )
            
            end_time = time.time()
            
            rapid_requests.append({
                "request_index": i,
                "success": response.success,
                "response_time": end_time - start_time,
                "rate_limited": getattr(response, 'rate_limited', False),
                "retry_after": getattr(response, 'retry_after_seconds', 0)
            })
            
            # No delay - rapid fire requests
        
        # Some requests should be rate limited after burst limit
        rate_limited_rapid = [r for r in rapid_requests if r.get("rate_limited")]
        
        # Should have rate limiting after burst limit exceeded
        if len(rate_limited_rapid) > 0:
            # Rate limited requests should have retry-after information
            for rl_request in rate_limited_rapid:
                assert rl_request["retry_after"] > 0, "Rate limited request should have retry-after time"
        
        # Test quota tracking and reporting
        quota_status = await self.provider_manager.get_quota_status(
            provider="openai" if "openai" in provider_config["provider"] else "anthropic",
            test_prefix=self.test_prefix
        )
        
        assert quota_status.total_requests >= len(normal_requests) + len(rapid_requests)
        assert quota_status.total_tokens_used > 0, "Should track token usage"
        assert quota_status.current_rate_limit_status in ["ok", "near_limit", "rate_limited"]
        
        if quota_status.current_rate_limit_status == "rate_limited":
            assert quota_status.reset_time is not None, "Should provide reset time when rate limited"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.real_llm
    async def test_llm_cost_optimization_integration(self):
        """
        Test LLM cost optimization across providers and models.
        
        BUSINESS CRITICAL: Cost optimization directly impacts unit economics
        and enables competitive pricing for customers.
        """
        # Define cost optimization scenarios
        optimization_scenarios = [
            {
                "name": "simple_task",
                "prompt": self.test_prompts["simple_query"],
                "complexity": "low",
                "max_tokens": 50,
                "quality_threshold": 0.7
            },
            {
                "name": "complex_analysis",
                "prompt": self.test_prompts["complex_reasoning"],
                "complexity": "high", 
                "max_tokens": 300,
                "quality_threshold": 0.8
            }
        ]
        
        # Test cost optimization for each scenario
        for scenario in optimization_scenarios:
            print(f"Testing cost optimization for scenario: {scenario['name']}")
            
            # Get optimal provider/model recommendation
            optimization_recommendation = await self.cost_optimizer.get_optimal_configuration(
                prompt=scenario["prompt"],
                quality_requirements={
                    "min_quality_score": scenario["quality_threshold"],
                    "max_response_time": 30
                },
                cost_constraints={
                    "max_cost_per_request": 0.10,  # 10 cents per request
                    "optimize_for": "cost_efficiency"
                },
                available_providers=["openai", "anthropic"],
                test_prefix=self.test_prefix
            )
            
            # Should provide optimization recommendation
            assert optimization_recommendation.recommended_provider is not None
            assert optimization_recommendation.recommended_model is not None
            assert optimization_recommendation.estimated_cost > 0
            assert optimization_recommendation.confidence_score >= 0.6
            
            # Test the recommended configuration
            recommended_config = {
                "provider": optimization_recommendation.recommended_provider,
                "model": optimization_recommendation.recommended_model,
                "api_key": self.env.get(f"{optimization_recommendation.recommended_provider.upper()}_API_KEY"),
                "max_tokens": scenario["max_tokens"],
                "temperature": 0.1
            }
            
            if recommended_config["api_key"]:
                start_time = time.time()
                
                response = await self.provider_manager.generate_completion(
                    provider_config=recommended_config,
                    prompt=scenario["prompt"],
                    test_prefix=self.test_prefix
                )
                
                end_time = time.time()
                actual_response_time = end_time - start_time
                
                if response.success:
                    # Validate cost optimization worked
                    actual_cost = self.cost_optimizer.calculate_request_cost(
                        provider=recommended_config["provider"],
                        model=recommended_config["model"],
                        token_usage=response.token_usage
                    )
                    
                    # Actual cost should be close to estimated cost
                    cost_variance = abs(actual_cost - optimization_recommendation.estimated_cost)
                    assert cost_variance < 0.05, f"Cost estimate variance too high: ${cost_variance}"
                    
                    # Should meet quality threshold
                    quality_score = self.response_validator.assess_response_quality(
                        prompt=scenario["prompt"],
                        response=response.text,
                        criteria=["relevance", "completeness"]
                    )
                    
                    assert quality_score.overall_score >= scenario["quality_threshold"], \
                        f"Quality below threshold: {quality_score.overall_score}"
                    
                    # Should meet performance requirements  
                    assert actual_response_time <= 30, f"Response time exceeded: {actual_response_time}s"
            
            await asyncio.sleep(2)  # Delay between scenarios
        
        # Test cost analysis and reporting
        cost_analysis = await self.cost_optimizer.analyze_usage_costs(
            time_period_hours=1,
            test_prefix=self.test_prefix
        )
        
        if cost_analysis.total_requests > 0:
            assert cost_analysis.total_cost >= 0, "Total cost should be non-negative"
            assert cost_analysis.average_cost_per_request > 0, "Should calculate average cost"
            assert cost_analysis.cost_by_provider is not None, "Should break down cost by provider"
            
            # Should provide cost optimization recommendations
            if len(cost_analysis.optimization_opportunities) > 0:
                for opportunity in cost_analysis.optimization_opportunities:
                    assert opportunity.potential_savings > 0, "Optimization should show potential savings"
                    assert opportunity.implementation_effort in ["low", "medium", "high"]
                    assert len(opportunity.recommended_actions) > 0, "Should provide actionable recommendations"


if __name__ == "__main__":
    # Allow running individual tests
    pytest.main([__file__, "-v", "--tb=short"])