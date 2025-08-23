"""Analyst Agent for NACIS - Performs technical analysis and calculations.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Provides TCO calculations, benchmarking, and risk assessment
with business grounding validation.
"""

from typing import Any, Dict, List, Optional

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.tools.sandboxed_interpreter import SandboxedInterpreter

logger = central_logger.get_logger(__name__)


class AnalystAgent(BaseSubAgent):
    """Performs analysis with sandboxed execution for calculations (<300 lines)."""
    
    def __init__(self, llm_manager: LLMManager, 
                 sandbox: Optional[SandboxedInterpreter] = None):
        super().__init__(llm_manager, name="AnalystAgent",
                        description="NACIS analyst for TCO and benchmarking")
        self._init_analysis_components(sandbox)
        self._init_analysis_templates()
    
    def _init_analysis_components(self, sandbox: Optional[SandboxedInterpreter]) -> None:
        """Initialize analysis components."""
        self.sandbox = sandbox or SandboxedInterpreter()
        self.analysis_model = "quality_llm"  # Tier 3 for complex analysis
        self.max_calculation_time = 10000  # 10 seconds
    
    def _init_analysis_templates(self) -> None:
        """Initialize analysis templates."""
        self.templates = {
            "tco_analysis": self._get_tco_template(),
            "benchmarking": self._get_benchmark_template(),
            "optimization": self._get_optimization_template()
        }
    
    def _get_tco_template(self) -> str:
        """Get TCO analysis template."""
        return """
# TCO Analysis
monthly_cost = {monthly_cost}
annual_cost = monthly_cost * 12
efficiency_factor = {efficiency_factor}
optimized_cost = annual_cost * efficiency_factor
savings = annual_cost - optimized_cost
roi = (savings / annual_cost) * 100
"""
    
    def _get_benchmark_template(self) -> str:
        """Get benchmarking template."""
        return """
# Performance Benchmarking
baseline = {baseline}
current = {current}
improvement = ((current - baseline) / baseline) * 100
relative_performance = current / baseline
"""
    
    def _get_optimization_template(self) -> str:
        """Get optimization template."""
        return """
# Optimization Analysis
current_tokens = {tokens}
current_cost = {cost}
cost_per_token = current_cost / current_tokens
optimization_factor = {factor}
new_tokens = current_tokens * optimization_factor
new_cost = new_tokens * cost_per_token
"""
    
    async def execute_from_context(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute analysis from orchestrator context."""
        analysis_type = self._extract_analysis_type(context)
        research_data = self._extract_research_data(context)
        analysis = await self._perform_analysis(analysis_type, research_data)
        risks = self._assess_risks(analysis)
        return self._format_analysis_response(analysis, risks)
    
    def _extract_analysis_type(self, context: ExecutionContext) -> str:
        """Extract analysis type from context."""
        if context.state and hasattr(context.state, 'accumulated_data'):
            return context.state.accumulated_data.get('analysis_type', 'general')
        return 'general'
    
    def _extract_research_data(self, context: ExecutionContext) -> Dict:
        """Extract research data from context."""
        if context.state and hasattr(context.state, 'accumulated_data'):
            return context.state.accumulated_data.get('data', {})
        return {}
    
    async def _perform_analysis(self, analysis_type: str, data: Dict) -> Dict:
        """Perform the requested analysis."""
        if analysis_type == "tco_analysis":
            return await self._perform_tco_analysis(data)
        elif analysis_type == "benchmarking":
            return await self._perform_benchmarking(data)
        else:
            return await self._perform_general_analysis(data)
    
    async def _perform_tco_analysis(self, data: Dict) -> Dict:
        """Perform Total Cost of Ownership analysis."""
        params = self._extract_tco_params(data)
        code = self.templates["tco_analysis"].format(**params)
        result = await self.sandbox.execute(code, self.max_calculation_time)
        return self._process_tco_result(result)
    
    def _extract_tco_params(self, data: Dict) -> Dict:
        """Extract TCO parameters from data."""
        return {
            "monthly_cost": data.get("monthly_cost", 1000),
            "efficiency_factor": data.get("efficiency_factor", 0.7)
        }
    
    def _process_tco_result(self, result: Dict) -> Dict:
        """Process TCO calculation result."""
        if result.get("status") == "success":
            return self._extract_tco_metrics(result)
        return {"error": "TCO calculation failed"}
    
    def _extract_tco_metrics(self, result: Dict) -> Dict:
        """Extract TCO metrics from result."""
        output = result.get("output", {})
        return {
            "annual_cost": output.get("annual_cost", 0),
            "optimized_cost": output.get("optimized_cost", 0),
            "savings": output.get("savings", 0),
            "roi": output.get("roi", 0)
        }
    
    async def _perform_benchmarking(self, data: Dict) -> Dict:
        """Perform benchmarking analysis."""
        params = self._extract_benchmark_params(data)
        code = self.templates["benchmarking"].format(**params)
        result = await self.sandbox.execute(code, self.max_calculation_time)
        return self._process_benchmark_result(result)
    
    def _extract_benchmark_params(self, data: Dict) -> Dict:
        """Extract benchmark parameters."""
        return {
            "baseline": data.get("baseline", 100),
            "current": data.get("current", 150)
        }
    
    def _process_benchmark_result(self, result: Dict) -> Dict:
        """Process benchmark result."""
        if result.get("status") == "success":
            return result.get("output", {})
        return {"error": "Benchmark calculation failed"}
    
    async def _perform_general_analysis(self, data: Dict) -> Dict:
        """Perform general analysis using LLM."""
        prompt = self._build_analysis_prompt(data)
        response = await self.llm_manager.ask_llm(prompt, self.analysis_model)
        return {"analysis": response}
    
    def _build_analysis_prompt(self, data: Dict) -> str:
        """Build analysis prompt for LLM."""
        return f"""Analyze the following data for AI optimization insights:
{data}

Provide practical recommendations with business grounding."""
    
    def _assess_risks(self, analysis: Dict) -> List[str]:
        """Assess risks and generate warnings."""
        risks = []
        if self._check_high_cost(analysis):
            risks.append("WARNING: High cost detected - consider optimization")
        if self._check_performance_degradation(analysis):
            risks.append("WARNING: Potential performance degradation")
        return risks
    
    def _check_high_cost(self, analysis: Dict) -> bool:
        """Check for high cost indicators."""
        annual_cost = analysis.get("annual_cost", 0)
        return annual_cost > 100000  # $100k threshold
    
    def _check_performance_degradation(self, analysis: Dict) -> bool:
        """Check for performance degradation."""
        improvement = analysis.get("improvement", 0)
        return improvement < -10  # 10% degradation
    
    def _format_analysis_response(self, analysis: Dict, risks: List[str]) -> Dict:
        """Format analysis response."""
        return {
            "status": "success",
            "analysis": analysis,
            "risks": risks,
            "recommendations": self._generate_recommendations(analysis)
        }
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        if analysis.get("roi", 0) > 20:
            recommendations.append("Strong ROI - proceed with optimization")
        if analysis.get("savings", 0) > 10000:
            recommendations.append("Significant cost savings opportunity")
        return recommendations