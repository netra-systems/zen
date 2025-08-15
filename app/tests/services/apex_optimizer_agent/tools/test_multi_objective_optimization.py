"""
Comprehensive unit tests for MultiObjectiveOptimizationTool.
Designed with ultra-thinking for robust multi-objective optimization testing.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from app.services.apex_optimizer_agent.tools.multi_objective_optimization import MultiObjectiveOptimizationTool
from app.services.context import ToolContext


class TestMultiObjectiveOptimizationTool:
    """Comprehensive test suite for MultiObjectiveOptimizationTool"""

    @pytest.fixture
    def mock_context(self):
        """Create a mock ToolContext"""
        context = Mock(spec=ToolContext)
        context.logs = [
            Mock(model_dump=Mock(return_value={"cost": 0.05, "latency": 120, "quality": 0.85})),
            Mock(model_dump=Mock(return_value={"cost": 0.03, "latency": 200, "quality": 0.75})),
            Mock(model_dump=Mock(return_value={"cost": 0.08, "latency": 80, "quality": 0.95}))
        ]
        return context

    @pytest.fixture
    def optimization_tool(self):
        """Create a MultiObjectiveOptimizationTool instance"""
        return MultiObjectiveOptimizationTool()

    def test_tool_metadata(self, optimization_tool):
        """Test that tool metadata is properly configured"""
        metadata = optimization_tool.get_metadata()
        
        assert metadata["name"] == "MultiObjectiveOptimization"
        assert metadata["description"] == "Performs multi-objective optimization."
        assert metadata["version"] == "1.0.0"
        assert metadata["status"] == "in_review"

    @pytest.mark.asyncio
    async def test_run_complete_workflow(self, optimization_tool, mock_context):
        """Test the complete multi-objective optimization workflow"""
        with patch.object(optimization_tool, 'define_optimization_goals', return_value="Goals defined") as mock_goals, \
             patch.object(optimization_tool, 'analyze_trade_offs', return_value="Trade-offs analyzed") as mock_tradeoffs, \
             patch.object(optimization_tool, 'propose_balanced_optimizations', return_value="Optimizations proposed") as mock_optimizations, \
             patch.object(optimization_tool, 'simulate_multi_objective_impact', return_value="Impact simulated") as mock_impact:
            
            result = await optimization_tool.run(mock_context, test_param="test_value")
            
            assert result == "Multi-objective optimization complete."
            
            # Verify all methods were called in correct order
            mock_goals.assert_called_once_with(mock_context, test_param="test_value")
            mock_tradeoffs.assert_called_once_with(mock_context, test_param="test_value")
            mock_optimizations.assert_called_once_with(mock_context, test_param="test_value")
            mock_impact.assert_called_once_with(mock_context, test_param="test_value")

    @pytest.mark.asyncio
    async def test_define_optimization_goals(self, optimization_tool, mock_context):
        """Test define_optimization_goals method"""
        result = await optimization_tool.define_optimization_goals(mock_context)
        assert result == "Defined optimization goals."

    @pytest.mark.asyncio
    async def test_analyze_trade_offs(self, optimization_tool, mock_context):
        """Test analyze_trade_offs method"""
        result = await optimization_tool.analyze_trade_offs(mock_context)
        assert result == "Analyzed trade-offs."

    @pytest.mark.asyncio
    async def test_propose_balanced_optimizations(self, optimization_tool, mock_context):
        """Test propose_balanced_optimizations method"""
        result = await optimization_tool.propose_balanced_optimizations(mock_context)
        assert result == "Proposed balanced optimizations."

    @pytest.mark.asyncio
    async def test_simulate_multi_objective_impact(self, optimization_tool, mock_context):
        """Test simulate_multi_objective_impact method"""
        result = await optimization_tool.simulate_multi_objective_impact(mock_context)
        assert result == "Simulated multi-objective impact."

    @pytest.mark.asyncio
    async def test_run_with_various_kwargs(self, optimization_tool, mock_context):
        """Test run method with various keyword arguments"""
        kwargs = {
            "cost_weight": 0.4,
            "latency_weight": 0.3,
            "quality_weight": 0.3,
            "optimization_method": "pareto_optimal",
            "max_iterations": 100
        }
        
        result = await optimization_tool.run(mock_context, **kwargs)
        assert result == "Multi-objective optimization complete."

    @pytest.mark.asyncio
    async def test_method_execution_order(self, optimization_tool, mock_context):
        """Test that methods are executed in the correct order"""
        call_order = []
        
        async def track_define_goals(context, **kwargs):
            call_order.append("define_goals")
            return "Goals defined"
        
        async def track_analyze_tradeoffs(context, **kwargs):
            call_order.append("analyze_tradeoffs")
            return "Trade-offs analyzed"
        
        async def track_propose_optimizations(context, **kwargs):
            call_order.append("propose_optimizations")
            return "Optimizations proposed"
        
        async def track_simulate_impact(context, **kwargs):
            call_order.append("simulate_impact")
            return "Impact simulated"
        
        # Mock all methods to track execution order
        optimization_tool.define_optimization_goals = track_define_goals
        optimization_tool.analyze_trade_offs = track_analyze_tradeoffs
        optimization_tool.propose_balanced_optimizations = track_propose_optimizations
        optimization_tool.simulate_multi_objective_impact = track_simulate_impact
        
        result = await optimization_tool.run(mock_context)
        
        assert result == "Multi-objective optimization complete."
        assert call_order == ["define_goals", "analyze_tradeoffs", "propose_optimizations", "simulate_impact"]

    @pytest.mark.asyncio
    async def test_run_method_failure_propagation(self, optimization_tool, mock_context):
        """Test that failures in individual methods are propagated"""
        # Test failure in define_optimization_goals
        with patch.object(optimization_tool, 'define_optimization_goals', side_effect=Exception("Goals definition failed")):
            with pytest.raises(Exception) as exc_info:
                await optimization_tool.run(mock_context)
            assert "Goals definition failed" in str(exc_info.value)
        
        # Test failure in analyze_trade_offs
        with patch.object(optimization_tool, 'analyze_trade_offs', side_effect=Exception("Trade-off analysis failed")):
            with pytest.raises(Exception) as exc_info:
                await optimization_tool.run(mock_context)
            assert "Trade-off analysis failed" in str(exc_info.value)
        
        # Test failure in propose_balanced_optimizations
        with patch.object(optimization_tool, 'propose_balanced_optimizations', side_effect=Exception("Optimization proposal failed")):
            with pytest.raises(Exception) as exc_info:
                await optimization_tool.run(mock_context)
            assert "Optimization proposal failed" in str(exc_info.value)
        
        # Test failure in simulate_multi_objective_impact
        with patch.object(optimization_tool, 'simulate_multi_objective_impact', side_effect=Exception("Impact simulation failed")):
            with pytest.raises(Exception) as exc_info:
                await optimization_tool.run(mock_context)
            assert "Impact simulation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_concurrent_execution(self, mock_context):
        """Test concurrent execution of multiple tool instances"""
        tool1 = MultiObjectiveOptimizationTool()
        tool2 = MultiObjectiveOptimizationTool()
        
        # Execute both tools concurrently
        results = await asyncio.gather(
            tool1.run(mock_context, instance_id=1),
            tool2.run(mock_context, instance_id=2)
        )
        
        assert len(results) == 2
        assert all(result == "Multi-objective optimization complete." for result in results)

    @pytest.mark.asyncio
    async def test_async_behavior_timing(self, optimization_tool, mock_context):
        """Test that the tool properly handles async operations"""
        async def slow_define_goals(context, **kwargs):
            await asyncio.sleep(0.01)
            return "Goals defined slowly"
        
        optimization_tool.define_optimization_goals = slow_define_goals
        
        start_time = asyncio.get_event_loop().time()
        result = await optimization_tool.run(mock_context)
        elapsed = asyncio.get_event_loop().time() - start_time
        
        assert result == "Multi-objective optimization complete."
        assert elapsed >= 0.009  # Allow for timing variations

    @pytest.mark.asyncio
    async def test_execute_wrapper_integration(self, optimization_tool, mock_context):
        """Test that the BaseTool execute wrapper works with this tool"""
        with patch('app.services.apex_optimizer_agent.tools.base.logger') as mock_logger:
            result = await optimization_tool.execute(mock_context, test_integration="true")
            
            # Verify logging occurred
            mock_logger.debug.assert_called_once()
            mock_logger.info.assert_called_once()
            
            # Verify result
            assert result == "Multi-objective optimization complete."

    def test_tool_inheritance(self, optimization_tool):
        """Test that the tool properly inherits from BaseTool"""
        from app.services.apex_optimizer_agent.tools.base import BaseTool
        
        assert isinstance(optimization_tool, BaseTool)
        assert hasattr(optimization_tool, 'metadata')
        assert hasattr(optimization_tool, 'get_metadata')
        assert hasattr(optimization_tool, 'execute')
        assert hasattr(optimization_tool, 'run')

    @pytest.mark.asyncio
    async def test_context_parameter_passing(self, optimization_tool, mock_context):
        """Test that context and parameters are properly passed to sub-methods"""
        test_kwargs = {
            "param1": "value1",
            "param2": 42,
            "param3": {"nested": "data"}
        }
        
        # Track calls to verify parameters are passed correctly
        with patch.object(optimization_tool, 'define_optimization_goals', return_value="Goals") as mock_define, \
             patch.object(optimization_tool, 'analyze_trade_offs', return_value="Tradeoffs") as mock_analyze, \
             patch.object(optimization_tool, 'propose_balanced_optimizations', return_value="Optimizations") as mock_propose, \
             patch.object(optimization_tool, 'simulate_multi_objective_impact', return_value="Impact") as mock_simulate:
            
            await optimization_tool.run(mock_context, **test_kwargs)
            
            # Verify all methods were called with correct parameters
            for mock_method in [mock_define, mock_analyze, mock_propose, mock_simulate]:
                mock_method.assert_called_once_with(mock_context, **test_kwargs)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=app.services.apex_optimizer_agent.tools.multi_objective_optimization"])