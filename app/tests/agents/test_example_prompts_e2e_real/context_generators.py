"""
Context generators for different prompt types in example prompts E2E tests.
Generates synthetic context data for testing various optimization scenarios.
"""

import random
from datetime import datetime, timedelta
from typing import Union

from app.schemas.llm_config_types import (
    CostOptimizationContext,
    LatencyOptimizationContext,
    CapacityPlanningContext,
    FunctionOptimizationContext,
    ModelSelectionContext,
    AuditContext,
    MultiObjectiveContext,
    ToolMigrationContext,
    RollbackAnalysisContext,
    DefaultContext,
    CostMetrics,
    FeatureMetrics,
    LatencyMetrics,
    InfrastructureConfig,
    UsageMetrics,
    RateLimitConfig,
    FunctionMetrics,
    ModelInfo,
    EvaluationMetrics,
    WorkloadCharacteristics,
    CacheConfiguration,
    OptimizationObjectives,
    OptimizationConstraints,
    CurrentSystemState,
    AgentTool,
    MigrationCriteria,
    ComparisonMetrics,
    MetricsComparison,
    SystemInfo,
    SystemMetrics
)


class ContextGenerators:
    """Generates synthetic context data for testing different prompt types"""
    
    def generate_cost_context(self) -> CostOptimizationContext:
        """Generate synthetic cost optimization context"""
        return CostOptimizationContext(
            current_costs=CostMetrics(
                daily=random.uniform(100, 1000),
                monthly=random.uniform(3000, 30000),
                per_request=random.uniform(0.001, 0.01)
            ),
            features={
                "feature_X": FeatureMetrics(
                    current_latency=random.uniform(100, 400),
                    acceptable_latency=500,
                    usage_percentage=random.uniform(10, 40)
                ),
                "feature_Y": FeatureMetrics(
                    current_latency=200,
                    required_latency=200,
                    usage_percentage=random.uniform(20, 60)
                )
            },
            models_in_use=["gpt-4", "claude-2", "gpt-3.5-turbo"],
            total_requests_daily=random.randint(10000, 1000000)
        )
    
    def generate_latency_context(self) -> LatencyOptimizationContext:
        """Generate synthetic latency optimization context"""
        return LatencyOptimizationContext(
            current_latency=LatencyMetrics(
                p50=random.uniform(100, 300),
                p95=random.uniform(300, 800),
                p99=random.uniform(500, 1500)
            ),
            target_improvement=3.0,
            budget_constraint="maintain_current",
            infrastructure=InfrastructureConfig(
                gpu_type=random.choice(["A100", "V100", "T4"]),
                gpu_count=random.randint(1, 8),
                memory_gb=random.choice([16, 32, 64, 128])
            )
        )
    
    def generate_capacity_context(self) -> CapacityPlanningContext:
        """Generate synthetic capacity planning context"""
        return CapacityPlanningContext(
            current_usage=UsageMetrics(
                requests_per_day=random.randint(10000, 100000),
                peak_rps=random.randint(10, 1000),
                average_rps=random.randint(5, 500)
            ),
            expected_growth=1.5,  # 50% increase
            rate_limits={
                "gpt-4": RateLimitConfig(rpm=10000, tpm=150000),
                "claude-2": RateLimitConfig(rpm=5000, tpm=100000)
            },
            cost_per_1k_tokens={
                "gpt-4": 0.03,
                "claude-2": 0.024
            }
        )
    
    def generate_function_context(self) -> FunctionOptimizationContext:
        """Generate synthetic function optimization context"""
        return FunctionOptimizationContext(
            function_name="user_authentication",
            current_metrics=FunctionMetrics(
                avg_execution_time_ms=random.uniform(50, 200),
                memory_usage_mb=random.uniform(100, 500),
                success_rate=random.uniform(0.95, 0.999),
                daily_invocations=random.randint(10000, 1000000)
            ),
            bottlenecks=[
                "database_queries",
                "token_generation",
                "cache_misses"
            ],
            optimization_methods_available=[
                "caching",
                "batching",
                "async_processing",
                "connection_pooling"
            ]
        )
    
    def generate_model_context(self) -> ModelSelectionContext:
        """Generate synthetic model selection context"""
        return ModelSelectionContext(
            current_models=ModelInfo(
                primary="gpt-4",
                fallback="gpt-3.5-turbo"
            ),
            candidate_models=["gpt-4o", "claude-3-sonnet"],
            evaluation_metrics=EvaluationMetrics(
                quality_threshold=0.9,
                latency_target_ms=200,
                cost_budget_daily=500
            ),
            workload_characteristics=WorkloadCharacteristics(
                avg_prompt_tokens=random.randint(100, 1000),
                avg_completion_tokens=random.randint(50, 500),
                complexity=random.choice(["low", "medium", "high"])
            )
        )
    
    def generate_audit_context(self) -> AuditContext:
        """Generate synthetic audit context"""
        return AuditContext(
            kv_cache_instances=random.randint(5, 20),
            cache_configurations=[
                CacheConfiguration(
                    name=f"cache_{i}",
                    size_mb=random.randint(100, 1000),
                    hit_rate=random.uniform(0.3, 0.9),
                    ttl_seconds=random.choice([60, 300, 3600])
                )
                for i in range(random.randint(3, 8))
            ],
            optimization_opportunities=[
                "increase_ttl",
                "implement_lru",
                "add_compression",
                "optimize_key_structure"
            ]
        )
    
    def generate_multi_objective_context(self) -> MultiObjectiveContext:
        """Generate synthetic multi-objective optimization context"""
        return MultiObjectiveContext(
            objectives=OptimizationObjectives(
                cost_reduction=0.2,  # 20%
                latency_improvement=2.0,  # 2x
                usage_increase=0.3  # 30%
            ),
            constraints=OptimizationConstraints(
                min_quality_score=0.85,
                max_error_rate=0.01,
                budget_limit=10000
            ),
            current_state=CurrentSystemState(
                daily_cost=random.uniform(500, 2000),
                avg_latency_ms=random.uniform(100, 500),
                daily_requests=random.randint(10000, 100000)
            )
        )
    
    def generate_tool_migration_context(self) -> ToolMigrationContext:
        """Generate synthetic tool migration context"""
        return ToolMigrationContext(
            agent_tools=[
                AgentTool(
                    name=f"tool_{i}",
                    current_model=random.choice(["gpt-4", "gpt-3.5", "claude-2"]),
                    usage_frequency=random.choice(["high", "medium", "low"]),
                    complexity=random.choice(["simple", "moderate", "complex"])
                )
                for i in range(random.randint(5, 15))
            ],
            new_model="GPT-5",
            migration_criteria=MigrationCriteria(
                min_quality_improvement=0.1,
                max_cost_increase=1.5,
                verbosity_options=["concise", "standard", "detailed"]
            )
        )
    
    def generate_rollback_context(self) -> RollbackAnalysisContext:
        """Generate synthetic rollback analysis context"""
        return RollbackAnalysisContext(
            upgrade_timestamp=(datetime.now() - timedelta(days=1)).isoformat(),
            upgraded_model="GPT-5",
            previous_model="GPT-4",
            metrics_comparison=MetricsComparison(
                before=ComparisonMetrics(
                    quality_score=random.uniform(0.8, 0.9),
                    cost_per_1k_tokens=0.03,
                    avg_latency_ms=random.uniform(100, 200)
                ),
                after=ComparisonMetrics(
                    quality_score=random.uniform(0.82, 0.95),
                    cost_per_1k_tokens=0.06,
                    avg_latency_ms=random.uniform(80, 180)
                )
            ),
            affected_endpoints=random.randint(10, 50)
        )
    
    def generate_default_context(self) -> DefaultContext:
        """Generate default synthetic context"""
        return DefaultContext(
            system_info=SystemInfo(
                version="1.0.0",
                environment="production",
                region=random.choice(["us-east-1", "us-west-2", "eu-west-1"])
            ),
            metrics=SystemMetrics(
                uptime_percentage=random.uniform(99.0, 99.99),
                error_rate=random.uniform(0.001, 0.01),
                avg_response_time_ms=random.uniform(50, 500)
            )
        )

    def generate_context_by_type(self, prompt_type: str) -> Union[
        CostOptimizationContext,
        LatencyOptimizationContext,
        CapacityPlanningContext,
        FunctionOptimizationContext,
        ModelSelectionContext,
        AuditContext,
        MultiObjectiveContext,
        ToolMigrationContext,
        RollbackAnalysisContext,
        DefaultContext
    ]:
        """Generate synthetic context data for a given prompt type"""
        context_generators = {
            "cost_optimization": self.generate_cost_context,
            "latency_optimization": self.generate_latency_context,
            "capacity_planning": self.generate_capacity_context,
            "function_optimization": self.generate_function_context,
            "model_selection": self.generate_model_context,
            "audit": self.generate_audit_context,
            "multi_objective": self.generate_multi_objective_context,
            "tool_migration": self.generate_tool_migration_context,
            "rollback_analysis": self.generate_rollback_context
        }
        
        return context_generators.get(prompt_type, self.generate_default_context)()