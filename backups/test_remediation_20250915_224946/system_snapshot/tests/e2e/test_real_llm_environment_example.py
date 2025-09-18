"""
Example test demonstrating Real LLM Test Environment usage.

This test shows how to use the dedicated test environment with real LLM calls,
seed data management, and transaction-based isolation.

Business Value Justification (BVJ):
1. Segment: Platform/Internal
2. Business Goal: Testing Infrastructure Excellence
3. Value Impact: Demonstrates reliable real LLM testing capabilities
4. Revenue Impact: Ensures production-quality AI optimization through comprehensive testing
"""

import asyncio
import os
from datetime import datetime
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig
from shared.isolated_environment import IsolatedEnvironment


import pytest

from test_framework.real_llm_config import get_real_llm_manager, is_real_llm_enabled
from test_framework.seed_data_manager import (
    TestEnvironmentConfig,
    get_seed_data_manager,
)
from test_framework.test_environment_setup import test_session_context


@pytest.mark.e2e
class RealLLMEnvironmentTests:
    """Test class demonstrating real LLM environment usage."""

    @pytest.mark.asyncio
    @pytest.mark.real_llm  # Mark for selective execution
    @pytest.mark.e2e
    async def test_basic_optimization_with_real_llm(self):
        """Test basic optimization functionality with real LLM and seed data."""
        
        # Use context manager for automatic setup and cleanup
        async with test_session_context(
            test_level="unit",
            use_real_llm=True,
            llm_model="gemini-2.5-flash",
            datasets=["basic_optimization"]
        ) as (session_id, orchestrator):
            
            # Verify session was created
            session_info = orchestrator.get_session_info(session_id)
            assert session_info is not None
            assert session_info['test_level'] == "unit"
            assert session_info['use_real_llm'] is True
            assert "basic_optimization" in session_info['datasets_loaded']
            
            # Test LLM manager functionality
            llm_manager = get_real_llm_manager()
            if is_real_llm_enabled():
                # Execute a real LLM call for cost optimization
                prompt = "Analyze this AI usage pattern and suggest cost optimizations: 1000 GPT-4 calls per day at $0.03 per 1K tokens"
                response = await llm_manager.execute_llm_call(
                    prompt=prompt,
                    model_key="gemini-2.5-flash"
                )
                
                # Validate response structure
                assert 'content' in response
                assert 'model' in response
                assert 'tokens_used' in response
                assert 'execution_time' in response
                assert response['real_llm'] is True
                
                # Validate response content quality
                content = response['content'].lower()
                optimization_keywords = ['cost', 'optimize', 'reduce', 'efficient', 'save']
                assert any(keyword in content for keyword in optimization_keywords)
            
            # Test seed data access
            seed_manager = await get_seed_data_manager()
            test_data_summary = await seed_manager.get_test_data_summary(session_id)
            
            assert test_data_summary is not None
            assert test_data_summary['test_id'] == session_id
            assert 'basic_optimization' in test_data_summary['active_datasets']
            
            # Validate seed data integrity
            basic_data = seed_manager.data_loader.get_seed_data('basic_optimization')
            assert 'users' in basic_data
            assert 'threads' in basic_data
            assert 'models' in basic_data
            assert 'metrics' in basic_data
            
            # Check that users were loaded
            users = basic_data['users']
            assert len(users) == 5  # As defined in seed data
            assert any(user['tier'] == 'enterprise' for user in users)
    
    @pytest.mark.asyncio
    @pytest.mark.real_llm
    @pytest.mark.e2e
    async def test_complex_workflow_with_multiple_agents(self):
        """Test complex multi-agent workflow with real LLM calls."""
        
        async with test_session_context(
            test_level="integration", 
            use_real_llm=True,
            llm_model=LLMModel.GEMINI_2_5_FLASH.value,
            datasets=["basic_optimization", "complex_workflows"]
        ) as (session_id, orchestrator):
            
            # Verify both datasets loaded
            session_info = orchestrator.get_session_info(session_id)
            assert len(session_info['datasets_loaded']) == 2
            
            # Test workflow coordination
            seed_manager = await get_seed_data_manager()
            complex_data = seed_manager.data_loader.get_seed_data('complex_workflows')
            
            # Check workflow templates
            workflow_templates = complex_data['workflow_templates']
            comprehensive_template = next(
                (wf for wf in workflow_templates if wf['id'] == 'template_comprehensive_analysis'), 
                None
            )
            assert comprehensive_template is not None
            assert len(comprehensive_template['steps']) == 5  # Should have 5 agent steps
            
            # Simulate multi-agent coordination with real LLM
            if is_real_llm_enabled():
                llm_manager = get_real_llm_manager()
                
                # Step 1: Data collection agent
                data_prompt = "Collect AI usage metrics for analysis: analyze 1000 requests over 7 days"
                data_response = await llm_manager.execute_llm_call(data_prompt, LLMModel.GEMINI_2_5_FLASH.value)
                
                # Step 2: Analysis agent  
                analysis_prompt = f"Based on this data collection: {data_response['content'][:200]}, identify usage patterns"
                analysis_response = await llm_manager.execute_llm_call(analysis_prompt, LLMModel.GEMINI_2_5_FLASH.value)
                
                # Step 3: Optimization agent
                optimization_prompt = f"Generate optimization recommendations based on: {analysis_response['content'][:200]}"
                optimization_response = await llm_manager.execute_llm_call(optimization_prompt, LLMModel.GEMINI_2_5_FLASH.value)
                
                # Validate coordination worked
                assert all(resp['real_llm'] for resp in [data_response, analysis_response, optimization_response])
                assert all('content' in resp for resp in [data_response, analysis_response, optimization_response])
                
                # Check that responses build on each other (basic coherence test)
                assert len(data_response['content']) > 50
                assert len(analysis_response['content']) > 50 
                assert len(optimization_response['content']) > 50

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_transaction_isolation(self):
        """Test that test environments are properly isolated via transactions."""
        
        # Create two separate test sessions
        session1_task = test_session_context("unit", use_real_llm=False, datasets=["basic_optimization"])
        session2_task = test_session_context("unit", use_real_llm=False, datasets=["basic_optimization"])
        
        async with session1_task as (session1_id, orchestrator1):
            async with session2_task as (session2_id, orchestrator2):
                
                # Verify sessions are independent
                assert session1_id != session2_id
                
                session1_info = orchestrator1.get_session_info(session1_id)
                session2_info = orchestrator2.get_session_info(session2_id)
                
                assert session1_info['session_id'] != session2_info['session_id']
                
                # Both should have access to same seed data but in isolation
                seed_manager = await get_seed_data_manager()
                
                summary1 = await seed_manager.get_test_data_summary(session1_id)
                summary2 = await seed_manager.get_test_data_summary(session2_id)
                
                assert summary1 is not None
                assert summary2 is not None
                assert summary1['test_id'] != summary2['test_id']
                assert summary1['active_datasets'] == summary2['active_datasets']  # Same datasets
    
    @pytest.mark.asyncio
    @pytest.mark.real_llm
    @pytest.mark.e2e
    async def test_cost_tracking_and_budgets(self):
        """Test LLM cost tracking and budget management."""
        
        async with test_session_context(
            test_level="unit",
            use_real_llm=True, 
            llm_model="gemini-2.5-flash"  # Use cheaper model for cost testing
        ) as (session_id, orchestrator):
            
            if is_real_llm_enabled():
                llm_manager = get_real_llm_manager()
                
                # Get initial cost tracking state
                initial_stats = llm_manager.get_execution_stats()
                initial_cost = initial_stats['cost_summary']['total_cost']
                
                # Execute a series of LLM calls
                test_prompts = [
                    "What is AI optimization?",
                    "How do you reduce LLM costs?", 
                    "Explain model selection strategies."
                ]
                
                for prompt in test_prompts:
                    response = await llm_manager.execute_llm_call(prompt, "gemini-2.5-flash")
                    assert response['real_llm'] is True
                    assert 'cost' not in response or response.get('cost', 0) >= 0
                
                # Check that costs were tracked
                final_stats = llm_manager.get_execution_stats()
                final_cost = final_stats['cost_summary']['total_cost']
                
                # Cost should have increased (unless all responses were cached)
                assert final_cost >= initial_cost
                assert final_stats['total_calls'] >= len(test_prompts)
                assert final_stats['cost_summary']['total_calls'] >= len(test_prompts)
                
                # Budget utilization should be reasonable for small test
                assert final_stats['cost_summary']['budget_utilization'] < 0.5  # Less than 50% of budget

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_error_handling_and_recovery(self):
        """Test error handling in real LLM environment."""
        
        async with test_session_context(
            test_level="integration",
            use_real_llm=True,
            datasets=["edge_cases"]
        ) as (session_id, orchestrator):
            
            # Test with edge case data
            seed_manager = await get_seed_data_manager()
            edge_data = seed_manager.data_loader.get_seed_data('edge_cases')
            
            # Check malformed requests handling
            malformed_requests = edge_data['malformed_requests']
            assert len(malformed_requests) > 0
            
            extremely_long_case = next(
                (req for req in malformed_requests if req['name'] == 'Extremely long message'), 
                None
            )
            assert extremely_long_case is not None
            assert extremely_long_case['expected_error'] == 'content_too_long_error'
            
            if is_real_llm_enabled():
                llm_manager = get_real_llm_manager()
                
                # Test with a moderately long prompt (not extreme to avoid API issues)
                long_prompt = "A" * 1000 + " - Analyze this pattern and provide optimization suggestions."
                
                try:
                    response = await llm_manager.execute_llm_call(long_prompt, "gemini-2.5-flash")
                    # Should handle gracefully - either succeed or return error response
                    assert 'content' in response
                    assert response.get('provider') in ['google', 'mock', 'error']
                    
                except Exception as e:
                    # Exception should be handled gracefully
                    assert "timeout" in str(e).lower() or "rate" in str(e).lower() or "length" in str(e).lower()


@pytest.mark.skip_if_no_real_llm
@pytest.mark.e2e
class RealLLMIntegrationTests:
    """Integration tests that require real LLM access."""
    
    @pytest.mark.asyncio
    @pytest.mark.real_llm
    @pytest.mark.slow
    @pytest.mark.e2e
    async def test_comprehensive_optimization_analysis(self):
        """Comprehensive test of AI optimization analysis with real LLM."""
        
        async with test_session_context(
            test_level="comprehensive",
            use_real_llm=True,
            llm_model=LLMModel.GEMINI_2_5_FLASH.value,  # Use more capable model for complex analysis
            datasets=["basic_optimization", "complex_workflows", "edge_cases"]
        ) as (session_id, orchestrator):
            
            if is_real_llm_enabled():
                llm_manager = get_real_llm_manager()
                seed_manager = await get_seed_data_manager()
                
                # Get comprehensive seed data
                basic_data = seed_manager.data_loader.get_seed_data('basic_optimization')
                metrics_data = basic_data['metrics']['daily_aggregates']
                
                # Create comprehensive analysis prompt
                analysis_prompt = f"""
                Analyze this AI usage data and provide optimization recommendations:
                
                Daily metrics over 7 days:
                - Average requests: {sum(day['total_requests'] for day in metrics_data) / len(metrics_data):.0f}
                - Total cost: ${sum(day['total_cost'] for day in metrics_data):.2f}
                - Average response time: {sum(day['avg_response_time_ms'] for day in metrics_data) / len(metrics_data):.0f}ms
                
                Models used:
                - GPT-4 (premium, $0.03/1K tokens)
                - Claude-3 (premium, $0.015/1K tokens) 
                - Gemini Flash (budget, $0.002/1K tokens)
                
                Provide specific optimization recommendations focusing on:
                1. Cost reduction strategies
                2. Latency improvements
                3. Model selection optimization
                4. Expected savings and performance impact
                """
                
                response = await llm_manager.execute_llm_call(analysis_prompt, LLMModel.GEMINI_2_5_FLASH.value)
                
                # Validate comprehensive response
                assert response['real_llm'] is True
                assert len(response['content']) > 500  # Should be detailed
                
                content = response['content'].lower()
                
                # Should address all requested areas
                optimization_areas = ['cost', 'latency', 'model', 'saving']
                assert all(area in content for area in optimization_areas)
                
                # Should provide specific recommendations
                recommendation_indicators = ['recommend', 'suggest', 'optimize', 'reduce', 'improve']
                assert any(indicator in content for indicator in recommendation_indicators)
                
                # Should mention specific models
                models_mentioned = [LLMModel.GEMINI_2_5_FLASH.value, 'claude', 'gemini']
                assert any(model in content for model in models_mentioned)
                
                # Verify execution stats
                stats = llm_manager.get_execution_stats()
                assert stats['total_calls'] > 0
                assert stats['successful_calls'] > 0
                assert stats['cost_summary']['total_cost'] > 0
