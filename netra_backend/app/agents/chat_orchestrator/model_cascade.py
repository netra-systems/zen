"""Advanced Model Cascade for intelligent LLM routing and optimization.

Business Value Justification (BVJ):
- Segment: All tiers (model optimization impacts all users)
- Business Goal: Optimize cost, latency, quality, throughput through smart routing
- Value Impact: Automated model selection based on query complexity and requirements
- Revenue Impact: Reduce operational costs while maintaining quality standards

Date Created: 2025-01-22
Last Updated: 2025-01-22
"""

import asyncio
import hashlib
import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.llm.model_selector import ModelSelector, SelectionCriteria
from netra_backend.app.agents.chat_orchestrator.quality_evaluator import QualityEvaluator, EvaluationCriteria
from netra_backend.app.services.analytics.cost_tracker import CostTracker
from netra_backend.app.services.monitoring.metrics_service import MetricsService
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
env = IsolatedEnvironment()


class ModelTier(Enum):
    """Model tiers for performance and cost optimization."""
    SMALL = "small"      # Fast, low-cost models
    MEDIUM = "medium"    # Balanced performance and cost
    LARGE = "large"      # High performance, higher cost


@dataclass
class CascadePolicies:
    """Policies governing cascade behavior."""
    quality_threshold: float = 0.8
    max_cost_per_request: float = 0.5
    latency_sla_ms: float = 2000
    escalation_enabled: bool = True
    fallback_enabled: bool = True
    max_escalations: int = 3
    cache_enabled: bool = True
    consensus_threshold: float = 0.8
    exploration_rate: float = 0.1
    learning_rate: float = 0.1
    performance_window_hours: int = 24
    initial_model_preference: str = "balanced"


@dataclass
class CacheEntry:
    """Cache entry for semantic caching."""
    response: str
    model_used: str
    quality_score: float
    cost: float
    timestamp: datetime
    hit_count: int = 0


@dataclass
class PerformanceHistory:
    """Performance history for adaptive learning."""
    quality_scores: deque = field(default_factory=lambda: deque(maxlen=100))
    latencies: deque = field(default_factory=lambda: deque(maxlen=100))
    costs: deque = field(default_factory=lambda: deque(maxlen=100))
    success_rate: float = 1.0
    avg_quality: float = 0.0
    avg_latency: float = 0.0
    avg_cost: float = 0.0


class ModelCascade:
    """Advanced model cascade with intelligent routing, caching, and learning."""
    
    def __init__(
        self,
        llm_manager: LLMManager,
        model_selector: ModelSelector,
        quality_evaluator: QualityEvaluator,
        cost_tracker: CostTracker,
        metrics_service: MetricsService
    ):
        """Initialize ModelCascade without global session storage.
        
        CRITICAL: This class no longer stores db_session as instance variable.
        Database sessions must be passed as parameters to methods that need them.
        """
        self.llm_manager = llm_manager
        self.model_selector = model_selector
        self.quality_evaluator = quality_evaluator
        self.cost_tracker = cost_tracker
        self.metrics_service = metrics_service
        # REMOVED: self.db_session = db_session (global session storage removed)
        
        # Initialize policies and caches
        self.policies = CascadePolicies()
        self._semantic_cache: Dict[str, CacheEntry] = {}
        self._performance_history: Dict[str, Dict[str, PerformanceHistory]] = defaultdict(lambda: defaultdict(PerformanceHistory))
        self._routing_preferences: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        
        # Cache configuration
        self._cache_similarity_threshold = 0.95
        self._cache_ttl_seconds = 300
        
        # Initialize model mappings
        self._init_model_mappings()
        
    def _init_model_mappings(self) -> None:
        """Initialize model tier mappings."""
        self.tier_mappings = {
            ModelTier.SMALL: ["gpt-3.5-turbo", "claude-3-haiku"],
            ModelTier.MEDIUM: ["gpt-4-turbo", "claude-3-sonnet"],
            ModelTier.LARGE: ["gpt-4", "claude-3-opus"]
        }
        
        # Task complexity mappings
        self.complexity_mappings = {
            "trivial": ModelTier.SMALL,
            "simple": ModelTier.SMALL,
            "medium": ModelTier.MEDIUM,
            "balanced": ModelTier.MEDIUM,
            "high": ModelTier.LARGE,
            "complex": ModelTier.LARGE,
            "expert": ModelTier.LARGE,
            "creative": ModelTier.MEDIUM
        }
    
    def set_policies(self, policies: Dict[str, Any]) -> None:
        """Update cascade policies."""
        for key, value in policies.items():
            if hasattr(self.policies, key):
                setattr(self.policies, key, value)
            else:
                logger.warning(f"Unknown policy key: {key}")
    
    async def execute(
        self,
        query: str,
        quality_requirement: float = 0.8,
        max_cost: float = 0.1,
        metadata: Optional[Dict[str, Any]] = None,
        enable_cache: bool = True
    ) -> Dict[str, Any]:
        """Execute query through model cascade."""
        start_time = time.time()
        metadata = metadata or {}
        
        try:
            # Check semantic cache first
            if enable_cache and self.policies.cache_enabled:
                cache_result = await self._check_cache(query)
                if cache_result:
                    return {
                        "response": cache_result.response,
                        "model_selected": cache_result.model_used,
                        "quality_score": cache_result.quality_score,
                        "total_cost": 0.0,  # Cache hit = no cost
                        "latency_ms": (time.time() - start_time) * 1000,
                        "cache_hit": True,
                        "selection_reasoning": "Cache hit - reusing previous result"
                    }
            
            # Select optimal model
            model_name = await self._select_model(query, quality_requirement, max_cost, metadata)
            
            # Generate response
            response_start = time.time()
            response = await self.llm_manager.generate_response(
                prompt=query,
                model_name=model_name
            )
            response_time = (time.time() - response_start) * 1000
            
            # Evaluate quality
            criteria = EvaluationCriteria(
                content_type=metadata.get("expected_complexity", "general"),
                min_quality_score=quality_requirement
            )
            quality_metrics = await self.quality_evaluator.evaluate_response(
                response, query, criteria, model_name
            )
            
            # Calculate cost (simplified)
            estimated_cost = await self._calculate_cost(model_name, query, response)
            
            # Cache result if enabled
            if enable_cache and self.policies.cache_enabled:
                await self._cache_result(query, response, model_name, quality_metrics.overall_score, estimated_cost)
            
            # Track metrics
            await self._track_execution_metrics(
                model_name, metadata.get("query_id", "unknown"),
                quality_metrics.overall_score, response_time, estimated_cost
            )
            
            total_time = (time.time() - start_time) * 1000
            
            return {
                "response": response,
                "model_selected": model_name,
                "quality_score": quality_metrics.overall_score,
                "total_cost": estimated_cost,
                "latency_ms": total_time,
                "cache_hit": False,
                "selection_reasoning": f"Selected {model_name} for complexity: {metadata.get('expected_complexity', 'unknown')}",
                "total_tokens": len(query.split()) + len(response.split())  # Simplified token count
            }
            
        except Exception as e:
            logger.error(f"Cascade execution failed: {e}")
            # Use UnifiedServiceInitializer for transparent error handling
            from netra_backend.app.services.service_initialization.unified_service_initializer import (
                UnifiedServiceInitializer, UnifiedServiceException
            )
            from netra_backend.app.schemas.shared_types import ErrorContext
            
            # Create transparent error context instead of mock response
            error_context = ErrorContext(
                user_id=metadata.get("user_id", "unknown"),
                request_id=metadata.get("request_id", "unknown"), 
                service_name="model_cascade",
                error_type="llm_generation_failure"
            )
            
            # Raise transparent exception instead of returning mock response
            raise UnifiedServiceException(
                message=f"Model cascade service temporarily unavailable: {str(e)}",
                error_context=error_context,
                should_retry=True,
                estimated_recovery_time_seconds=120,
                alternative_suggestions=[
                    "Try a simpler query",
                    "Check back in a few minutes", 
                    "Contact support if this persists"
                ]
            )
    
    async def execute_with_escalation_tracking(
        self,
        query: str,
        quality_requirement: float,
        track_attempts: bool = True
    ) -> Dict[str, Any]:
        """Execute with quality-based escalation tracking."""
        escalation_history = []
        current_tier = ModelTier.SMALL
        attempts = 0
        max_attempts = self.policies.max_escalations
        
        while attempts < max_attempts:
            attempts += 1
            
            # Get model for current tier
            model_candidates = self.tier_mappings.get(current_tier, ["gpt-3.5-turbo"])
            model_name = model_candidates[0] if model_candidates else "gpt-3.5-turbo"
            
            # Execute with current model
            start_time = time.time()
            try:
                response = await self.llm_manager.generate_response(prompt=query, model_name=model_name)
                response_time = (time.time() - start_time) * 1000
                
                # Evaluate quality
                criteria = EvaluationCriteria(min_quality_score=quality_requirement)
                quality_metrics = await self.quality_evaluator.evaluate_response(
                    response, query, criteria, model_name
                )
                
                cost = await self._calculate_cost(model_name, query, response)
                
                attempt_data = {
                    "attempt": attempts,
                    "model": model_name,
                    "tier": current_tier.value,
                    "quality_score": quality_metrics.overall_score,
                    "cost": cost,
                    "latency_ms": response_time,
                    "response": response
                }
                
                escalation_history.append(attempt_data)
                
                # Check if quality requirement is met
                if quality_metrics.overall_score >= quality_requirement * 0.95:
                    return {
                        "final_response": response,
                        "escalation_history": escalation_history,
                        "total_attempts": attempts,
                        "final_quality_score": quality_metrics.overall_score,
                        "cumulative_cost": sum(h["cost"] for h in escalation_history)
                    }
                
                # Escalate to next tier
                if current_tier == ModelTier.SMALL:
                    current_tier = ModelTier.MEDIUM
                elif current_tier == ModelTier.MEDIUM:
                    current_tier = ModelTier.LARGE
                else:
                    break  # Already at highest tier
                    
            except Exception as e:
                logger.error(f"Escalation attempt {attempts} failed: {e}")
                break
        
        # Return best result from history
        if escalation_history:
            best_attempt = max(escalation_history, key=lambda x: x["quality_score"])
            return {
                "final_response": best_attempt["response"],
                "escalation_history": escalation_history,
                "total_attempts": attempts,
                "final_quality_score": best_attempt["quality_score"],
                "cumulative_cost": sum(h["cost"] for h in escalation_history)
            }
        
        # Transparent failure instead of mock response
        from netra_backend.app.services.service_initialization.unified_service_initializer import (
            UnifiedServiceException
        )
        from netra_backend.app.schemas.shared_types import ErrorContext
        
        error_context = ErrorContext(
            user_id="unknown",  # TODO: pass user_id through parameters
            request_id="unknown",
            service_name="model_cascade_escalation",
            error_type="quality_escalation_failure"
        )
        
        raise UnifiedServiceException(
            message=f"Unable to generate satisfactory response after {attempts} escalation attempts",
            error_context=error_context,
            should_retry=True,
            estimated_recovery_time_seconds=300,
            alternative_suggestions=[
                "Try rephrasing your query",
                "Break complex requests into simpler parts",
                "Contact support for complex analysis needs"
            ]
        )
    
    def enable_semantic_cache(self, similarity_threshold: float = 0.95, ttl_seconds: int = 300) -> None:
        """Enable semantic caching with specified parameters."""
        self.policies.cache_enabled = True
        self._cache_similarity_threshold = similarity_threshold
        self._cache_ttl_seconds = ttl_seconds
        logger.info(f"Semantic cache enabled: threshold={similarity_threshold}, ttl={ttl_seconds}s")
    
    async def execute_with_consensus(
        self,
        query: str,
        models_to_query: List[str],
        consensus_threshold: float = 0.8,
        aggregation_method: str = "weighted_average"
    ) -> Dict[str, Any]:
        """Execute query across multiple models for consensus."""
        individual_responses = []
        total_cost = 0.0
        start_time = time.time()
        
        # Query all models in parallel
        tasks = []
        for model_name in models_to_query:
            if await self._is_model_available(model_name):
                tasks.append(self._query_single_model(query, model_name))
        
        if not tasks:
            raise ValueError("No available models for consensus")
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Model {models_to_query[i]} failed: {result}")
                continue
                
            model_name, response, quality_score, cost, latency = result
            individual_responses.append({
                "model": model_name,
                "response": response,
                "quality_score": quality_score,
                "confidence": min(1.0, quality_score * 1.2),  # Boost confidence for high quality
                "cost": cost,
                "latency_ms": latency
            })
            total_cost += cost
        
        if not individual_responses:
            raise ValueError("No successful responses for consensus")
        
        # Generate consensus response
        consensus_response = await self._generate_consensus(
            individual_responses, aggregation_method
        )
        
        # Calculate consensus score
        consensus_score = self._calculate_consensus_score(individual_responses)
        
        # Identify disagreements
        disagreements = self._identify_disagreements(individual_responses)
        
        total_latency = (time.time() - start_time) * 1000
        
        return {
            "consensus_response": consensus_response,
            "individual_responses": individual_responses,
            "consensus_score": consensus_score,
            "disagreement_points": disagreements,
            "total_cost": total_cost,
            "total_latency_ms": total_latency
        }
    
    def enable_adaptive_routing(
        self,
        learning_rate: float = 0.1,
        exploration_rate: float = 0.2,
        performance_window_hours: int = 24
    ) -> None:
        """Enable adaptive routing with learning parameters."""
        self.policies.learning_rate = learning_rate
        self.policies.exploration_rate = exploration_rate
        self.policies.performance_window_hours = performance_window_hours
        logger.info(f"Adaptive routing enabled: lr={learning_rate}, explore={exploration_rate}")
    
    async def execute_adaptive(
        self,
        query: str,
        query_category: str,
        quality_requirement: float = 0.85,
        learn_from_result: bool = True
    ) -> Dict[str, Any]:
        """Execute with adaptive model selection based on learned performance."""
        # Decide exploration vs exploitation
        is_exploration = self._should_explore(query_category)
        
        if is_exploration:
            # Explore: try a random model
            available_models = await self._get_available_models()
            model_name = self._select_exploration_model(available_models, query_category)
            selection_reason = "exploration"
        else:
            # Exploit: use best known model for category
            model_name = self._select_exploitation_model(query_category)
            selection_reason = "exploitation"
        
        # Predict performance
        predicted_performance = self._predict_performance(model_name, query_category)
        
        # Execute query
        start_time = time.time()
        try:
            response = await self.llm_manager.generate_response(prompt=query, model_name=model_name)
            response_time = (time.time() - start_time) * 1000
            
            # Evaluate actual performance
            criteria = EvaluationCriteria(min_quality_score=quality_requirement)
            quality_metrics = await self.quality_evaluator.evaluate_response(
                response, query, criteria, model_name
            )
            
            cost = await self._calculate_cost(model_name, query, response)
            
            actual_performance = {
                "quality": quality_metrics.overall_score,
                "latency_ms": response_time,
                "cost": cost
            }
            
            # Update learning if enabled
            if learn_from_result:
                await self._update_performance_history(
                    model_name, query_category, actual_performance
                )
            
            return {
                "response": response,
                "model_selected": model_name,
                "routing_reason": selection_reason,
                "exploration": is_exploration,
                "performance_prediction": predicted_performance,
                "actual_performance": actual_performance
            }
            
        except Exception as e:
            logger.error(f"Adaptive execution failed: {e}")
            # Transparent failure instead of mock response
            from netra_backend.app.services.service_initialization.unified_service_initializer import (
                UnifiedServiceException
            )
            from netra_backend.app.schemas.shared_types import ErrorContext
            
            error_context = ErrorContext(
                user_id="unknown",  # TODO: pass user_id through parameters
                request_id="unknown",
                service_name="model_cascade_adaptive",
                error_type="adaptive_routing_failure"
            )
            
            raise UnifiedServiceException(
                message=f"Adaptive model routing failed: {str(e)}",
                error_context=error_context,
                should_retry=True,
                estimated_recovery_time_seconds=60,
                alternative_suggestions=[
                    "Try with manual model selection",
                    "Use standard execution instead of adaptive",
                    "Retry in a few moments"
                ]
            )
    
    async def update_routing_performance(
        self,
        category: str,
        model: str,
        quality_score: float,
        latency_ms: float,
        cost: float
    ) -> None:
        """Update routing performance history."""
        history = self._performance_history[category][model]
        history.quality_scores.append(quality_score)
        history.latencies.append(latency_ms)
        history.costs.append(cost)
        
        # Update averages
        history.avg_quality = sum(history.quality_scores) / len(history.quality_scores)
        history.avg_latency = sum(history.latencies) / len(history.latencies)
        history.avg_cost = sum(history.costs) / len(history.costs)
        
        logger.debug(f"Updated performance for {model} in {category}: quality={history.avg_quality:.2f}")
    
    async def get_routing_recommendations(self) -> Dict[str, Any]:
        """Get routing recommendations based on learned performance."""
        recommendations = {}
        confidence_scores = {}
        performance_summary = {}
        
        for category, models in self._performance_history.items():
            if not models:
                continue
                
            # Find best model for category
            best_model = None
            best_score = 0.0
            
            for model_name, history in models.items():
                if len(history.quality_scores) < 3:  # Need minimum data
                    continue
                    
                # Combined score: quality weighted by recency, penalized by cost
                combined_score = (
                    history.avg_quality * 0.6 +  # Quality weight
                    (1.0 / max(history.avg_latency / 1000, 0.1)) * 0.2 +  # Speed bonus
                    (1.0 / max(history.avg_cost, 0.001)) * 0.2  # Cost efficiency bonus
                )
                
                if combined_score > best_score:
                    best_score = combined_score
                    best_model = model_name
            
            if best_model:
                # Get fallback models
                fallback_models = [
                    m for m, h in models.items() 
                    if m != best_model and len(h.quality_scores) >= 2
                ]
                fallback_models.sort(key=lambda m: models[m].avg_quality, reverse=True)
                
                recommendations[category] = {
                    "primary": best_model,
                    "fallbacks": fallback_models[:2],  # Top 2 fallbacks
                    "avg_performance": {
                        "quality": models[best_model].avg_quality,
                        "latency_ms": models[best_model].avg_latency,
                        "cost": models[best_model].avg_cost
                    },
                    "max_cost": models[best_model].avg_cost * 1.5  # Allow 50% cost variance
                }
                
                # Confidence based on data points
                data_points = len(models[best_model].quality_scores)
                confidence_scores[category] = min(1.0, data_points / 20.0)  # Full confidence at 20+ data points
                
                performance_summary[category] = {
                    "models_tested": len(models),
                    "total_queries": sum(len(h.quality_scores) for h in models.values()),
                    "avg_quality": sum(h.avg_quality for h in models.values()) / len(models)
                }
        
        return {
            "category_model_mapping": recommendations,
            "confidence_scores": confidence_scores,
            "performance_summary": performance_summary
        }
    
    # Helper methods
    async def _select_model(
        self,
        query: str,
        quality_requirement: float,
        max_cost: float,
        metadata: Dict[str, Any]
    ) -> str:
        """Select optimal model based on requirements."""
        complexity = metadata.get("expected_complexity", "medium")
        
        # Map complexity to tier
        tier = self.complexity_mappings.get(complexity, ModelTier.MEDIUM)
        
        # Get available models for tier
        candidates = self.tier_mappings.get(tier, ["gpt-3.5-turbo"])
        
        # Select first available model (simplified selection)
        for model in candidates:
            if await self._is_model_available(model):
                return model
        
        # Fallback to any available model
        available = await self._get_available_models()
        return available[0] if available else "gpt-3.5-turbo"
    
    async def _is_model_available(self, model_name: str) -> bool:
        """Check if model is available."""
        try:
            available_models = self.llm_manager.get_available_models()
            return model_name in available_models
        except Exception:
            return True  # Assume available if check fails
    
    async def _get_available_models(self) -> List[str]:
        """Get list of available models."""
        try:
            return self.llm_manager.get_available_models()
        except Exception:
            return ["gpt-3.5-turbo", "gpt-4", "claude-3-haiku"]  # Fallback list
    
    async def _calculate_cost(self, model_name: str, query: str, response: str) -> float:
        """Calculate estimated cost for model usage."""
        # Simplified cost calculation
        input_tokens = len(query.split())
        output_tokens = len(response.split())
        total_tokens = input_tokens + output_tokens
        
        # Model-specific pricing (simplified)
        cost_per_1k_tokens = {
            "gpt-3.5-turbo": 0.002,
            "gpt-4": 0.06,
            "claude-3-haiku": 0.001,
            "claude-3-sonnet": 0.003,
            "claude-3-opus": 0.015
        }
        
        rate = cost_per_1k_tokens.get(model_name, 0.003)
        return (total_tokens / 1000.0) * rate
    
    async def _check_cache(self, query: str) -> Optional[CacheEntry]:
        """Check semantic cache for similar queries."""
        query_hash = self._hash_query(query)
        
        # Check exact match first
        if query_hash in self._semantic_cache:
            entry = self._semantic_cache[query_hash]
            # Check TTL
            if (datetime.now(UTC) - entry.timestamp).seconds < self._cache_ttl_seconds:
                entry.hit_count += 1
                return entry
            else:
                del self._semantic_cache[query_hash]
        
        # TODO: Implement semantic similarity search for cache
        return None
    
    async def _cache_result(
        self, 
        query: str, 
        response: str, 
        model_name: str, 
        quality_score: float, 
        cost: float
    ) -> None:
        """Cache query result."""
        query_hash = self._hash_query(query)
        entry = CacheEntry(
            response=response,
            model_used=model_name,
            quality_score=quality_score,
            cost=cost,
            timestamp=datetime.now(UTC)
        )
        self._semantic_cache[query_hash] = entry
        
        # Limit cache size
        if len(self._semantic_cache) > 1000:
            # Remove oldest entries
            oldest_keys = sorted(
                self._semantic_cache.keys(),
                key=lambda k: self._semantic_cache[k].timestamp
            )[:100]
            for key in oldest_keys:
                del self._semantic_cache[key]
    
    def _hash_query(self, query: str) -> str:
        """Create hash for query caching."""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    async def _track_execution_metrics(
        self, 
        model_name: str, 
        query_id: str, 
        quality_score: float, 
        latency_ms: float, 
        cost: float
    ) -> None:
        """Track execution metrics."""
        try:
            # Track in metrics service
            self.metrics_service.record_histogram("model_cascade_latency_ms", latency_ms, {"model": model_name})
            self.metrics_service.record_histogram("model_cascade_quality", quality_score, {"model": model_name})
            self.metrics_service.increment_counter("model_cascade_requests", 1.0, {"model": model_name})
            
            # Track cost
            from decimal import Decimal
            await self.cost_tracker.track_operation_cost(
                operation_id=query_id,
                operation_type="model_cascade",
                model_name=model_name,
                tokens_used=int(latency_ms / 10),  # Simplified token estimation
                cost=Decimal(str(cost))
            )
        except Exception as e:
            logger.warning(f"Failed to track metrics: {e}")
    
    async def _query_single_model(self, query: str, model_name: str) -> Tuple[str, str, float, float, float]:
        """Query a single model and return results."""
        start_time = time.time()
        
        response = await self.llm_manager.generate_response(prompt=query, model_name=model_name)
        response_time = (time.time() - start_time) * 1000
        
        # Evaluate quality
        criteria = EvaluationCriteria()
        quality_metrics = await self.quality_evaluator.evaluate_response(
            response, query, criteria, model_name
        )
        
        cost = await self._calculate_cost(model_name, query, response)
        
        return model_name, response, quality_metrics.overall_score, cost, response_time
    
    async def _generate_consensus(self, responses: List[Dict], method: str) -> str:
        """Generate consensus response from multiple model outputs."""
        if method == "weighted_average":
            # Use highest quality response as base, mention if there's agreement
            best_response = max(responses, key=lambda r: r["quality_score"])
            return best_response["response"]
        elif method == "majority_vote":
            # Simplified: return most common response pattern
            return responses[0]["response"]  # Placeholder
        else:
            return responses[0]["response"]
    
    def _calculate_consensus_score(self, responses: List[Dict]) -> float:
        """Calculate consensus score across responses."""
        if len(responses) < 2:
            return 1.0
        
        # Simple consensus: average quality scores
        avg_quality = sum(r["quality_score"] for r in responses) / len(responses)
        
        # Penalty for high variance in quality
        quality_scores = [r["quality_score"] for r in responses]
        variance = sum((q - avg_quality) ** 2 for q in quality_scores) / len(quality_scores)
        
        consensus_score = avg_quality - (variance * 0.5)  # Penalty for disagreement
        return max(0.0, min(1.0, consensus_score))
    
    def _identify_disagreements(self, responses: List[Dict]) -> List[Dict]:
        """Identify points of disagreement between models."""
        # Simplified: return empty list for now
        # TODO: Implement semantic disagreement detection
        return []
    
    def _should_explore(self, category: str) -> bool:
        """Decide whether to explore or exploit for given category."""
        import random
        return random.random() < self.policies.exploration_rate
    
    def _select_exploration_model(self, available_models: List[str], category: str) -> str:
        """Select model for exploration."""
        import random
        # Avoid models we've used too much recently
        history = self._performance_history[category]
        underexplored = [m for m in available_models if len(history[m].quality_scores) < 5]
        
        if underexplored:
            return random.choice(underexplored)
        return random.choice(available_models)
    
    def _select_exploitation_model(self, category: str) -> str:
        """Select best known model for category."""
        history = self._performance_history[category]
        if not history:
            return "gpt-3.5-turbo"  # Default
        
        # Select model with best average quality
        best_model = max(
            history.keys(),
            key=lambda m: history[m].avg_quality if len(history[m].quality_scores) > 0 else 0
        )
        return best_model
    
    def _predict_performance(self, model_name: str, category: str) -> Dict[str, float]:
        """Predict performance for model-category combination."""
        history = self._performance_history[category][model_name]
        
        if len(history.quality_scores) == 0:
            # No history, return defaults
            return {
                "quality": 0.7,
                "latency_ms": 1500,
                "cost": 0.01
            }
        
        return {
            "quality": history.avg_quality,
            "latency_ms": history.avg_latency,
            "cost": history.avg_cost
        }
    
    async def _update_performance_history(
        self, 
        model_name: str, 
        category: str, 
        performance: Dict[str, Any]
    ) -> None:
        """Update performance history with learning."""
        await self.update_routing_performance(
            category, model_name,
            performance["quality"],
            performance["latency_ms"],
            performance["cost"]
        )
    
    # Legacy compatibility methods
    def get_model_for_task(self, task_type: str) -> str:
        """Get optimal model for task type (legacy compatibility)."""
        tier = self.complexity_mappings.get(task_type.lower(), ModelTier.MEDIUM)
        candidates = self.tier_mappings.get(tier, ["gpt-3.5-turbo"])
        return candidates[0] if candidates else "gpt-3.5-turbo"
    
    def get_model_for_agent(self, agent_name: str, action: str) -> str:
        """Get model for specific agent action (legacy compatibility)."""
        task_type = self._infer_task_type(agent_name, action)
        return self.get_model_for_task(task_type)
    
    def _infer_task_type(self, agent_name: str, action: str) -> str:
        """Infer task type from agent and action (legacy compatibility)."""
        if "research" in action.lower():
            return "medium"
        elif "analysis" in action.lower():
            return "complex"
        elif "validate" in action.lower():
            return "medium"
        return "simple"
    
    def estimate_cost_tier(self, tier: ModelTier) -> float:
        """Estimate relative cost for model tier (legacy compatibility)."""
        cost_map = {
            ModelTier.SMALL: 0.1,
            ModelTier.MEDIUM: 0.5,
            ModelTier.LARGE: 1.0,
        }
        return cost_map.get(tier, 0.5)