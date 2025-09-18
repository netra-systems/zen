"""
Model selection service for choosing optimal LLM models.
Selects models based on requirements, performance, and cost constraints.
"""

from shared.logging.unified_logging_ssot import get_logger
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


logger = get_logger(__name__)


class ModelCapability(Enum):
    """Available model capabilities."""
    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    ANALYSIS = "analysis"
    REASONING = "reasoning"
    FUNCTION_CALLING = "function_calling"
    MULTI_MODAL = "multi_modal"


@dataclass
class ModelSpec:
    """Specification for a language model."""
    name: str
    provider: str
    context_window: int
    capabilities: List[ModelCapability]
    performance_score: float
    cost_score: float  # Lower is better
    availability: bool = True


@dataclass
class SelectionCriteria:
    """Criteria for model selection."""
    min_context_window: int = 4096
    required_capabilities: List[ModelCapability] = None
    max_cost_score: Optional[float] = None
    min_performance_score: float = 0.7
    preferred_provider: Optional[str] = None


class ModelSelector:
    """
    Service for selecting optimal LLM models based on requirements.
    Evaluates models against criteria and returns ranked recommendations.
    """
    
    def __init__(self):
        self.available_models: Dict[str, ModelSpec] = {}
        self._initialize_models()
    
    def _initialize_models(self) -> None:
        """Initialize available model specifications."""
        self.available_models = {
            LLMModel.GEMINI_2_5_FLASH.value: ModelSpec(
                name=LLMModel.GEMINI_2_5_FLASH.value,
                provider="openai",
                context_window=8192,
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.ANALYSIS,
                    ModelCapability.REASONING,
                    ModelCapability.FUNCTION_CALLING
                ],
                performance_score=0.95,
                cost_score=8.5
            ),
            LLMModel.GEMINI_2_5_FLASH.value: ModelSpec(
                name=LLMModel.GEMINI_2_5_FLASH.value,
                provider="openai",
                context_window=4096,
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.FUNCTION_CALLING
                ],
                performance_score=0.85,
                cost_score=2.0
            ),
            LLMModel.GEMINI_2_5_FLASH.value: ModelSpec(
                name=LLMModel.GEMINI_2_5_FLASH.value,
                provider="anthropic",
                context_window=200000,
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.ANALYSIS,
                    ModelCapability.REASONING
                ],
                performance_score=0.92,
                cost_score=6.0
            ),
            "claude-3-haiku": ModelSpec(
                name="claude-3-haiku",
                provider="anthropic", 
                context_window=200000,
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION
                ],
                performance_score=0.82,
                cost_score=1.5
            )
        }
    
    async def select_model(
        self, 
        criteria: SelectionCriteria
    ) -> Optional[str]:
        """
        Select the best model based on criteria.
        
        Args:
            criteria: Selection criteria
            
        Returns:
            Name of selected model or None if no suitable model found
        """
        try:
            candidates = self._filter_candidates(criteria)
            if not candidates:
                logger.warning("No models meet the specified criteria")
                return None
            
            # Score and rank candidates
            scored_candidates = self._score_candidates(candidates, criteria)
            
            # Return best candidate
            best_model = max(scored_candidates, key=lambda x: x[1])
            logger.info(f"Selected model: {best_model[0]} (score: {best_model[1]:.3f})")
            return best_model[0]
            
        except Exception as e:
            logger.error(f"Model selection failed: {e}")
            return None
    
    async def get_ranked_models(
        self, 
        criteria: SelectionCriteria
    ) -> List[Tuple[str, float]]:
        """
        Get all suitable models ranked by score.
        
        Args:
            criteria: Selection criteria
            
        Returns:
            List of (model_name, score) tuples, sorted by score descending
        """
        try:
            candidates = self._filter_candidates(criteria)
            scored_candidates = self._score_candidates(candidates, criteria)
            
            # Sort by score descending
            return sorted(scored_candidates, key=lambda x: x[1], reverse=True)
            
        except Exception as e:
            logger.error(f"Model ranking failed: {e}")
            return []
    
    def _filter_candidates(self, criteria: SelectionCriteria) -> List[ModelSpec]:
        """Filter models that meet basic criteria."""
        candidates = []
        
        for model in self.available_models.values():
            if not model.availability:
                continue
                
            # Check context window
            if model.context_window < criteria.min_context_window:
                continue
                
            # Check performance score
            if model.performance_score < criteria.min_performance_score:
                continue
                
            # Check cost constraint
            if (criteria.max_cost_score is not None and 
                model.cost_score > criteria.max_cost_score):
                continue
                
            # Check provider preference
            if (criteria.preferred_provider is not None and 
                model.provider != criteria.preferred_provider):
                continue
                
            # Check required capabilities
            if criteria.required_capabilities:
                if not all(cap in model.capabilities 
                          for cap in criteria.required_capabilities):
                    continue
            
            candidates.append(model)
        
        return candidates
    
    def _score_candidates(
        self, 
        candidates: List[ModelSpec], 
        criteria: SelectionCriteria
    ) -> List[Tuple[str, float]]:
        """Score candidate models based on criteria."""
        scored = []
        
        for model in candidates:
            score = 0.0
            
            # Performance score (weighted 40%)
            score += model.performance_score * 0.4
            
            # Cost score (weighted 30%, inverted so lower cost = higher score)
            max_cost = max(m.cost_score for m in candidates)
            cost_score = (max_cost - model.cost_score) / max_cost
            score += cost_score * 0.3
            
            # Context window bonus (weighted 20%)
            max_context = max(m.context_window for m in candidates)
            context_score = model.context_window / max_context
            score += context_score * 0.2
            
            # Capability bonus (weighted 10%)
            if criteria.required_capabilities:
                capability_score = len(model.capabilities) / len(ModelCapability)
                score += capability_score * 0.1
            
            scored.append((model.name, score))
        
        return scored
    
    async def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific model."""
        if model_name not in self.available_models:
            return None
        
        model = self.available_models[model_name]
        return {
            "name": model.name,
            "provider": model.provider,
            "context_window": model.context_window,
            "capabilities": [cap.value for cap in model.capabilities],
            "performance_score": model.performance_score,
            "cost_score": model.cost_score,
            "availability": model.availability
        }
    
    async def recommend_for_task(self, task_type: str) -> List[str]:
        """Recommend models for a specific task type."""
        task_capability_map = {
            "code_generation": [ModelCapability.CODE_GENERATION],
            "analysis": [ModelCapability.ANALYSIS, ModelCapability.REASONING],
            "text_generation": [ModelCapability.TEXT_GENERATION],
            "function_calling": [ModelCapability.FUNCTION_CALLING],
            "reasoning": [ModelCapability.REASONING]
        }
        
        required_caps = task_capability_map.get(task_type, [])
        if not required_caps:
            logger.warning(f"Unknown task type: {task_type}")
            return []
        
        criteria = SelectionCriteria(required_capabilities=required_caps)
        ranked_models = await self.get_ranked_models(criteria)
        
        return [model_name for model_name, _ in ranked_models[:3]]  # Top 3


# Global instance
model_selector = ModelSelector()