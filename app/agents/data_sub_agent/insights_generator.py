"""Modernized Insights Generator with BaseExecutionInterface

Generates actionable insights from analysis data with modern execution patterns.
Now supports BaseExecutionInterface for standardized execution with modular analyzers.

Business Value: Critical for customer optimization insights and recommendations.
BVJ: Growth & Enterprise | Analytics Intelligence | +20% value capture
"""

from typing import Dict, List, Any, Optional

from app.logging_config import central_logger as logger
from app.agents.base.interface import (
    BaseExecutionInterface, ExecutionContext, WebSocketManagerProtocol
)
from app.agents.base.executor import BaseExecutionEngine
from app.agents.base.reliability_manager import ReliabilityManager
from app.agents.base.monitoring import ExecutionMonitor

from .insights_performance_analyzer import PerformanceInsightsAnalyzer
from .insights_usage_analyzer import UsageInsightsAnalyzer
from .insights_recommendations import InsightsRecommendationsGenerator


class InsightsGenerator(BaseExecutionInterface):
    """Modernized insights generator with BaseExecutionInterface.
    
    Generates actionable insights from analysis data with modern execution patterns,
    reliability management, and performance monitoring using specialized analyzers.
    """
    
    def __init__(self, websocket_manager: Optional[WebSocketManagerProtocol] = None,
                 reliability_manager: Optional[ReliabilityManager] = None):
        """Initialize modernized insights generator."""
        self._init_base_interface(websocket_manager)
        self._init_modern_components(reliability_manager)
        self._init_specialized_analyzers()
        
    def _init_base_interface(self, websocket_manager: Optional[WebSocketManagerProtocol]) -> None:
        """Initialize base execution interface."""
        BaseExecutionInterface.__init__(self, "InsightsGenerator", websocket_manager)
        self.logger = logger.get_logger(__name__)
        
    def _init_modern_components(self, reliability_manager: Optional[ReliabilityManager]) -> None:
        """Initialize modern execution components."""
        self.reliability_manager = reliability_manager
        self.execution_engine = BaseExecutionEngine(reliability_manager, ExecutionMonitor())
        
    def _init_specialized_analyzers(self) -> None:
        """Initialize specialized insight analyzers."""
        self.thresholds = self._create_analysis_thresholds()
        self.performance_analyzer = PerformanceInsightsAnalyzer(self.thresholds)
        self.usage_analyzer = UsageInsightsAnalyzer(self.thresholds)
        self.recommendations_generator = InsightsRecommendationsGenerator()
        
    def _create_analysis_thresholds(self) -> Dict[str, Any]:
        """Create analysis threshold configuration."""
        return {
            "error_rate": 0.05, "cost_per_event": 0.01, "daily_cost": 100.0,
            "off_hours_start": 22, "off_hours_end": 6
        }
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute insights generation with modern execution patterns."""
        request_data = context.state.request_data
        performance_data = request_data.get("performance_data", {})
        usage_data = request_data.get("usage_data", {})
        return await self._generate_insights_with_monitoring(performance_data, usage_data)
        
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate insights generation preconditions."""
        request_data = context.state.request_data
        return self._validate_input_data(request_data)
        
    def _validate_input_data(self, request_data: Dict[str, Any]) -> bool:
        """Validate input data requirements."""
        has_performance = "performance_data" in request_data
        has_usage = "usage_data" in request_data
        return has_performance or has_usage
        
    async def _generate_insights_with_monitoring(self, performance_data: Dict[str, Any], 
                                               usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights with execution monitoring."""
        insights = self._initialize_insights_structure()
        return await self._process_all_insights(performance_data, usage_data, insights)
        
    async def generate_insights(self, performance_data: Dict[str, Any], 
                              usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy interface for backward compatibility."""
        insights = self._initialize_insights_structure()
        return await self._process_all_insights(performance_data, usage_data, insights)
    
    async def _process_all_insights(self, performance_data: Dict[str, Any], 
                                  usage_data: Dict[str, Any], insights: Dict[str, Any]) -> Dict[str, Any]:
        """Process all insight types using specialized analyzers."""
        await self.performance_analyzer.analyze_performance_trends(performance_data, insights)
        await self.usage_analyzer.analyze_usage_patterns(usage_data, insights)
        return insights
    
    def _initialize_insights_structure(self) -> Dict[str, Any]:
        """Initialize insights structure with empty collections."""
        return {
            "performance_insights": [], "usage_insights": [], 
            "cost_insights": [], "recommendations": []
        }

    async def generate_performance_insights(self, performance_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights specifically from performance data."""
        return await self.performance_analyzer.generate_performance_insights(performance_data)
    
    async def generate_cost_insights(self, performance_data: Dict[str, Any], 
                                   usage_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate cost-related insights using specialized analyzer."""
        return await self.usage_analyzer.generate_cost_insights(performance_data, usage_data)
    
    async def generate_recommendations(self, all_insights: List[Dict[str, Any]]) -> List[str]:
        """Generate specific recommendations based on insights."""
        return await self.recommendations_generator.generate_recommendations(all_insights)
    
    async def execute_with_modern_patterns(self, performance_data: Dict[str, Any],
                                         usage_data: Dict[str, Any], run_id: str) -> Dict[str, Any]:
        """Execute insights generation with modern execution patterns."""
        from app.agents.state import DeepAgentState
        mock_state = DeepAgentState(request_data={"performance_data": performance_data, "usage_data": usage_data})
        context = self._create_execution_context(mock_state, run_id)
        result = await self.execution_engine.execute(self, context)
        return result.result if result.success else {"error": result.error}
        
    def _create_execution_context(self, state: Any, run_id: str) -> ExecutionContext:
        """Create execution context for insights generation."""
        return ExecutionContext(run_id=run_id, agent_name=self.agent_name, state=state)
        
    def get_health_status(self) -> Dict[str, Any]:
        """Get insights generator health status."""
        return {"status": "healthy", "thresholds": self.thresholds, 
                "execution_engine": self.execution_engine.get_health_status()}
    
    def get_analyzer_status(self) -> Dict[str, Any]:
        """Get specialized analyzer status."""
        return {
            "performance_analyzer": "active",
            "usage_analyzer": "active", 
            "recommendations_generator": "active",
            "thresholds": self.thresholds
        }


# Backward compatibility alias
ModernInsightsGenerator = InsightsGenerator