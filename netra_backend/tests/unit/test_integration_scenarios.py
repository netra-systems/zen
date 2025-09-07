"""Integration Scenarios Tests.

Tests cross-service integration patterns and end-to-end workflows
to ensure components work together correctly.
"""

import pytest
from netra_backend.app.services.cost_calculator import CostCalculatorService
from netra_backend.app.schemas.llm_base_types import TokenUsage, LLMProvider
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment


class TestCrossServiceIntegration:
    """Test integration between different services."""

    def test_cost_calculation_with_thread_service_pattern(self):
        """Test cost calculation integrated with thread service patterns."""
        from netra_backend.app.services.thread_service import _handle_database_error
        
        cost_calc = CostCalculatorService()
        usage = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        
        # Calculate cost
        cost = cost_calc.calculate_cost(usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
        
        # Simulate integration with thread service error handling
        context = {"cost": str(cost), "tokens": usage.total_tokens}
        error_result = _handle_database_error("calculate_thread_cost", context)
        
        assert cost is not None
        assert error_result is not None

    def test_service_interaction_patterns(self):
        """Test common service interaction patterns."""
        # Test services can be used together
        cost_calc = CostCalculatorService()
        
        from netra_backend.app.services.user_service import pwd_context
        
        # Simulate user context with cost tracking
        password = "user_password"
        hashed = pwd_context.hash(password)
        
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        cost = cost_calc.calculate_cost(usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
        
        # Both services should work independently
        assert hashed is not None
        assert cost is not None

    @pytest.mark.asyncio
    async def test_async_sync_service_integration(self):
        """Test integration between async and sync services."""
        from netra_backend.app.services.thread_service import ThreadService
        
        thread_service = ThreadService()
        cost_calc = CostCalculatorService()
        
        # Async operation that uses sync cost calculation
        async def cost_aware_operation(uow):
            usage = TokenUsage(prompt_tokens=200, completion_tokens=100, total_tokens=300)
            cost = cost_calc.calculate_cost(usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
            return {"cost": str(cost), "status": "completed"}
        
        with patch('netra_backend.app.services.thread_service.get_unit_of_work') as mock_get_uow:
            mock_uow = AsyncNone  # TODO: Use real service instance
            mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
            mock_uow.__aexit__ = AsyncMock(return_value=None)
            mock_get_uow.return_value = mock_uow
            
            result = await thread_service._execute_with_uow(cost_aware_operation)
            
            assert "cost" in result
            assert result["status"] == "completed"


class TestDataFlowIntegration:
    """Test data flow integration scenarios."""

    def test_token_usage_cost_calculation_flow(self):
        """Test complete token usage to cost calculation flow."""
        # Simulate a complete flow from token usage to final cost
        cost_calc = CostCalculatorService()
        
        # Different stages of token usage
        stages = [
            TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            TokenUsage(prompt_tokens=500, completion_tokens=300, total_tokens=800),
            TokenUsage(prompt_tokens=1000, completion_tokens=600, total_tokens=1600),
        ]
        
        stage_costs = []
        
        for stage in stages:
            cost = cost_calc.calculate_cost(stage, LLMProvider.OPENAI, "gpt-3.5-turbo")
            stage_costs.append(cost)
        
        # Costs should increase with usage and all be positive
        assert all(cost > 0 for cost in stage_costs)
        assert stage_costs[0] < stage_costs[1] < stage_costs[2]

    def test_error_context_propagation(self):
        """Test error context propagation across services."""
        from netra_backend.app.services.thread_service import _handle_database_error
        
        # Simulate error propagation with rich context
        original_context = {
            "user_id": "user_123",
            "thread_id": "thread_456", 
            "operation": "cost_calculation",
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        error = _handle_database_error("integrated_operation", original_context)
        
        # Error should preserve context
        assert error is not None
        error_str = str(error)
        assert "integrated_operation" in error_str

    def test_configuration_consistency_across_services(self):
        """Test that services have consistent configuration patterns."""
        # Test multiple service instantiations
        cost_calc1 = CostCalculatorService()
        cost_calc2 = CostCalculatorService()
        
        from netra_backend.app.services.thread_service import ThreadService
        thread_service = ThreadService()
        
        # Services should be independently functional
        usage = TokenUsage(prompt_tokens=200, completion_tokens=100, total_tokens=300)
        
        cost1 = cost_calc1.calculate_cost(usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
        cost2 = cost_calc2.calculate_cost(usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
        
        # Should be consistent
        assert cost1 == cost2
        
        # Thread service should also be functional
        assert hasattr(thread_service, '_execute_with_uow')


class TestEndToEndWorkflows:
    """Test end-to-end workflow scenarios."""

    @pytest.mark.asyncio
    async def test_user_thread_cost_workflow(self):
        """Test complete user thread with cost tracking workflow."""
        from netra_backend.app.services.thread_service import ThreadService
        from netra_backend.app.services.user_service import pwd_context
        
        # Simulate complete workflow
        cost_calc = CostCalculatorService()
        thread_service = ThreadService()
        
        # 1. User authentication
        password = "workflow_password"
        hashed = pwd_context.hash(password)
        
        # 2. Thread creation with cost tracking
        async def thread_with_cost_operation(uow):
            usage = TokenUsage(prompt_tokens=500, completion_tokens=250, total_tokens=750)
            cost = cost_calc.calculate_cost(usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
            
            return {
                "thread_id": "thread_workflow_123",
                "cost": str(cost),
                "user_authenticated": True
            }
        
        with patch('netra_backend.app.services.thread_service.get_unit_of_work') as mock_get_uow:
            mock_uow = AsyncNone  # TODO: Use real service instance
            mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
            mock_uow.__aexit__ = AsyncMock(return_value=None)
            mock_get_uow.return_value = mock_uow
            
            # 3. Execute complete workflow
            result = await thread_service._execute_with_uow(thread_with_cost_operation)
            
            # Verify workflow completion
            assert hashed is not None
            assert "thread_id" in result
            assert "cost" in result
            assert result["user_authenticated"] is True

    def test_multi_provider_cost_comparison_workflow(self):
        """Test workflow comparing costs across providers."""
        cost_calc = CostCalculatorService()
        usage = TokenUsage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)
        
        providers = [LLMProvider.OPENAI, LLMProvider.ANTHROPIC, LLMProvider.GOOGLE]
        models = ["gpt-3.5-turbo", "claude-3-sonnet", "gemini-pro"]
        
        cost_comparisons = []
        for provider, model in zip(providers, models):
            try:
                cost = cost_calc.calculate_cost(usage, provider, model)
                cost_comparisons.append({
                    "provider": provider,
                    "model": model,
                    "cost": cost
                })
            except Exception:
                # Some providers might not be configured
                pass
        
        # Should have at least one successful calculation
        assert len(cost_comparisons) > 0

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """Test error recovery in complex workflows."""
        from netra_backend.app.services.thread_service import ThreadService, _handle_database_error
        
        thread_service = ThreadService()
        
        # Simulate workflow with error recovery
        async def error_prone_operation(uow):
            # Simulate partial failure and recovery
            try:
                raise ValueError("Simulated operation failure")
            except ValueError as e:
                # Handle error and recover
                error_context = {"operation": "workflow_step", "error": str(e)}
                db_error = _handle_database_error("workflow_recovery", error_context)
                
                # Return recovery result
                return {"recovered": True, "error_handled": True}
        
        with patch('netra_backend.app.services.thread_service.get_unit_of_work') as mock_get_uow:
            mock_uow = AsyncNone  # TODO: Use real service instance
            mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
            mock_uow.__aexit__ = AsyncMock(return_value=None)
            mock_get_uow.return_value = mock_uow
            
            result = await thread_service._execute_with_uow(error_prone_operation)
            
            # Should have recovered gracefully
            assert result["recovered"] is True
            assert result["error_handled"] is True


class TestServiceBoundaryIntegration:
    """Test integration at service boundaries."""

    def test_service_interface_compatibility(self):
        """Test that services maintain compatible interfaces."""
        from netra_backend.app.services.service_interfaces import IThreadService
        from netra_backend.app.services.thread_service import ThreadService
        
        # ThreadService should implement the interface
        thread_service = ThreadService()
        assert isinstance(thread_service, IThreadService)

    def test_cross_service_data_validation(self):
        """Test data validation across service boundaries."""
        cost_calc = CostCalculatorService()
        
        # Test with various data formats that might cross service boundaries
        test_cases = [
            {"prompt": 100, "completion": 50, "total": 150},
            {"prompt": "100", "completion": "50", "total": "150"},  # String numbers
        ]
        
        for case in test_cases:
            try:
                # Convert to proper format
                if isinstance(case["prompt"], str):
                    usage = TokenUsage(
                        prompt_tokens=int(case["prompt"]),
                        completion_tokens=int(case["completion"]),
                        total_tokens=int(case["total"])
                    )
                else:
                    usage = TokenUsage(
                        prompt_tokens=case["prompt"],
                        completion_tokens=case["completion"],
                        total_tokens=case["total"]
                    )
                
                cost = cost_calc.calculate_cost(usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
                assert cost is not None
            except Exception as e:
                # Should fail gracefully with clear error
                assert "token" in str(e).lower() or "usage" in str(e).lower()

    @pytest.mark.asyncio
    async def test_async_sync_boundary_handling(self):
        """Test handling at async/sync boundaries."""
        from netra_backend.app.services.thread_service import ThreadService
        
        thread_service = ThreadService()
        cost_calc = CostCalculatorService()
        
        # Mixed async/sync operations
        async def mixed_boundary_operation(uow):
            # Sync operation within async context
            usage = TokenUsage(prompt_tokens=300, completion_tokens=150, total_tokens=450)
            cost = cost_calc.calculate_cost(usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
            
            # Return async result
            return {"boundary_cost": str(cost), "operation": "mixed"}
        
        with patch('netra_backend.app.services.thread_service.get_unit_of_work') as mock_get_uow:
            mock_uow = AsyncNone  # TODO: Use real service instance
            mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
            mock_uow.__aexit__ = AsyncMock(return_value=None)
            mock_get_uow.return_value = mock_uow
            
            result = await thread_service._execute_with_uow(mixed_boundary_operation)
            
            assert "boundary_cost" in result
            assert result["operation"] == "mixed"


class TestIntegrationPerformance:
    """Test performance of integrated operations."""

    def test_integrated_operation_performance(self):
        """Test performance of operations that use multiple services."""
        import time
        
        cost_calc = CostCalculatorService()
        
        # Measure cost calculation performance (lightweight operation)
        start_time = time.time()
        
        for i in range(100):
            # Focus on cost calculation performance only
            usage = TokenUsage(prompt_tokens=100+i, completion_tokens=50+i, total_tokens=150+i*2)
            cost = cost_calc.calculate_cost(usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
            assert cost is not None
        
        total_time = time.time() - start_time
        avg_time = total_time / 100
        
        # Cost calculations should be very fast
        assert avg_time < 0.001, f"Cost calculations too slow: {avg_time:.6f}s average"

    @pytest.mark.asyncio
    async def test_async_integration_performance(self):
        """Test performance of async integrated operations."""
        from netra_backend.app.services.thread_service import ThreadService
        import time
        
        services = [ThreadService() for _ in range(5)]
        cost_calc = CostCalculatorService()
        
        async def integrated_async_operation(uow, operation_id):
            # Sync cost calculation within async operation
            usage = TokenUsage(prompt_tokens=200, completion_tokens=100, total_tokens=300)
            cost = cost_calc.calculate_cost(usage, LLMProvider.OPENAI, "gpt-3.5-turbo")
            return {"id": operation_id, "cost": str(cost)}
        
        with patch('netra_backend.app.services.thread_service.get_unit_of_work') as mock_get_uow:
            mock_uow = AsyncNone  # TODO: Use real service instance
            mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
            mock_uow.__aexit__ = AsyncMock(return_value=None)
            mock_get_uow.return_value = mock_uow
            
            start_time = time.time()
            
            results = []
            for i, service in enumerate(services):
                result = await service._execute_with_uow(integrated_async_operation, operation_id=i)
                results.append(result)
            
            total_time = time.time() - start_time
            
            # Should complete async integrations efficiently
            assert total_time < 0.1, f"Async integrations too slow: {total_time:.3f}s"
            assert len(results) == 5