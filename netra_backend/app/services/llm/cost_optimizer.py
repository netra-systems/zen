"""
LLM cost optimization service.
Analyzes and optimizes costs for language model operations.
"""

from shared.logging.unified_logging_ssot import get_logger
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


logger = get_logger(__name__)


@dataclass
class CostAnalysis:
    """Result of cost analysis for LLM operations."""
    current_cost: Decimal
    optimized_cost: Decimal
    savings: Decimal
    savings_percentage: float
    recommendations: List[str]


@dataclass
class ModelCost:
    """Cost information for a specific model."""
    model_name: str
    input_cost_per_token: Decimal
    output_cost_per_token: Decimal
    context_window: int
    performance_score: float


class LLMCostOptimizer:
    """
    Service for optimizing LLM costs through model selection and usage patterns.
    Analyzes costs and provides recommendations for cost reduction.
    """
    
    def __init__(self):
        self.model_costs: Dict[str, ModelCost] = {}
        self._initialize_model_costs()
    
    def _initialize_model_costs(self) -> None:
        """Initialize cost data for different models."""
        # Sample model cost data - in real implementation would come from config
        self.model_costs = {
            LLMModel.GEMINI_2_5_FLASH.value: ModelCost(
                model_name=LLMModel.GEMINI_2_5_FLASH.value,
                input_cost_per_token=Decimal("0.00003"),
                output_cost_per_token=Decimal("0.00006"),
                context_window=8192,
                performance_score=0.95
            ),
            LLMModel.GEMINI_2_5_FLASH.value: ModelCost(
                model_name=LLMModel.GEMINI_2_5_FLASH.value, 
                input_cost_per_token=Decimal("0.000001"),
                output_cost_per_token=Decimal("0.000002"),
                context_window=4096,
                performance_score=0.85
            ),
            LLMModel.GEMINI_2_5_FLASH.value: ModelCost(
                model_name=LLMModel.GEMINI_2_5_FLASH.value,
                input_cost_per_token=Decimal("0.000015"),
                output_cost_per_token=Decimal("0.000075"),
                context_window=200000,
                performance_score=0.92
            )
        }
    
    async def analyze_costs(
        self, 
        usage_data: Dict[str, Any]
    ) -> CostAnalysis:
        """
        Analyze current costs and provide optimization recommendations.
        
        Args:
            usage_data: Dictionary containing usage statistics
            
        Returns:
            CostAnalysis with recommendations
        """
        try:
            current_model = usage_data.get("current_model", LLMModel.GEMINI_2_5_FLASH.value)
            input_tokens = usage_data.get("input_tokens", 0)
            output_tokens = usage_data.get("output_tokens", 0)
            
            # Calculate current cost
            current_cost = self._calculate_cost(current_model, input_tokens, output_tokens)
            
            # Find optimal model
            optimal_model = self._find_optimal_model(usage_data)
            optimized_cost = self._calculate_cost(optimal_model, input_tokens, output_tokens)
            
            savings = current_cost - optimized_cost
            savings_percentage = float((savings / current_cost) * 100) if current_cost > 0 else 0
            
            recommendations = self._generate_recommendations(
                current_model, optimal_model, usage_data
            )
            
            return CostAnalysis(
                current_cost=current_cost,
                optimized_cost=optimized_cost,
                savings=savings,
                savings_percentage=savings_percentage,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Cost analysis failed: {e}")
            return CostAnalysis(
                current_cost=Decimal("0"),
                optimized_cost=Decimal("0"),
                savings=Decimal("0"),
                savings_percentage=0.0,
                recommendations=["Unable to analyze costs due to error"]
            )
    
    def _calculate_cost(
        self, 
        model_name: str, 
        input_tokens: int, 
        output_tokens: int
    ) -> Decimal:
        """Calculate cost for given model and token usage."""
        if model_name not in self.model_costs:
            return Decimal("0")
        
        model_cost = self.model_costs[model_name]
        input_cost = Decimal(input_tokens) * model_cost.input_cost_per_token
        output_cost = Decimal(output_tokens) * model_cost.output_cost_per_token
        
        return input_cost + output_cost
    
    def _find_optimal_model(self, usage_data: Dict[str, Any]) -> str:
        """Find the most cost-effective model for given usage pattern."""
        required_context = usage_data.get("max_context_length", 4096)
        quality_threshold = usage_data.get("min_quality_score", 0.8)
        
        best_model = None
        best_cost_efficiency = float('inf')
        
        for model_name, model_cost in self.model_costs.items():
            if (model_cost.context_window >= required_context and
                model_cost.performance_score >= quality_threshold):
                
                # Calculate cost efficiency (cost per performance point)
                avg_cost_per_token = (model_cost.input_cost_per_token + 
                                    model_cost.output_cost_per_token) / 2
                cost_efficiency = float(avg_cost_per_token) / model_cost.performance_score
                
                if cost_efficiency < best_cost_efficiency:
                    best_cost_efficiency = cost_efficiency
                    best_model = model_name
        
        return best_model or LLMModel.GEMINI_2_5_FLASH.value  # Fallback
    
    def _generate_recommendations(
        self, 
        current_model: str, 
        optimal_model: str, 
        usage_data: Dict[str, Any]
    ) -> List[str]:
        """Generate cost optimization recommendations."""
        recommendations = []
        
        if current_model != optimal_model:
            recommendations.append(
                f"Switch from {current_model} to {optimal_model} for better cost efficiency"
            )
        
        # Add general recommendations
        if usage_data.get("input_tokens", 0) > 2000:
            recommendations.append("Consider prompt compression to reduce input token count")
        
        if usage_data.get("output_tokens", 0) > 1000:
            recommendations.append("Optimize response length to reduce output costs")
        
        recommendations.append("Implement caching for repeated queries")
        recommendations.append("Use batch processing for multiple requests")
        
        return recommendations
    
    async def get_model_recommendations(
        self, 
        requirements: Dict[str, Any]
    ) -> List[str]:
        """Get model recommendations based on requirements."""
        context_needed = requirements.get("context_window", 4096)
        quality_needed = requirements.get("quality_score", 0.8)
        budget_per_1k_tokens = requirements.get("budget_per_1k_tokens")
        
        suitable_models = []
        
        for model_name, model_cost in self.model_costs.items():
            if (model_cost.context_window >= context_needed and
                model_cost.performance_score >= quality_needed):
                
                if budget_per_1k_tokens:
                    avg_cost_1k = float(
                        (model_cost.input_cost_per_token + model_cost.output_cost_per_token) * 500
                    )
                    if avg_cost_1k <= budget_per_1k_tokens:
                        suitable_models.append(model_name)
                else:
                    suitable_models.append(model_name)
        
        return suitable_models


# Global instance
llm_cost_optimizer = LLMCostOptimizer()

# Create alias for backwards compatibility
CostOptimizer = LLMCostOptimizer