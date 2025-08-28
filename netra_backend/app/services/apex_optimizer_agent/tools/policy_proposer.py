import asyncio
from typing import Any, Dict, List, Tuple

from sqlalchemy.future import select

from netra_backend.app.db.models_clickhouse import UnifiedLogEntry
from netra_backend.app.db.models_postgres import SupplyOption
from netra_backend.app.schemas.pattern import DiscoveredPattern
from netra_backend.app.schemas.policy import LearnedPolicy, PredictedOutcome
from netra_backend.app.services.apex_optimizer_agent.tools.base import (
    BaseTool,
    ToolMetadata,
)
from netra_backend.app.services.apex_optimizer_agent.tools.context import ToolContext


class PolicyProposer(BaseTool):
    metadata = ToolMetadata(
        name="policy_proposer",
        description="Finds the best routing policies through simulation.",
        version="1.0.0",
        status="in_review"
    )

    def _get_member_spans(self, pattern: DiscoveredPattern, span_map: Dict[str, UnifiedLogEntry]) -> List[UnifiedLogEntry]:
        """Get member spans for a pattern"""
        return [span_map[sid] for sid in pattern.member_span_ids if sid in span_map]

    async def _simulate_all_outcomes(self, context: ToolContext, pattern: DiscoveredPattern, 
                                   all_options: List, user_goal: str, representative_span: UnifiedLogEntry) -> List:
        """Simulate outcomes for all supply options"""
        sim_tasks = [self._simulate_policy_outcome(context, pattern, supply, user_goal, representative_span) for supply in all_options]
        policy_outcomes = [o for o in await asyncio.gather(*sim_tasks) if o]
        return sorted(policy_outcomes, key=lambda x: x.utility_score, reverse=True)

    def _calculate_baseline_metrics(self, member_spans: List[UnifiedLogEntry]) -> Dict[str, float]:
        """Calculate baseline metrics for member spans"""
        return {
            "avg_cost_usd": sum(s.finops.total_cost_usd for s in member_spans) / len(member_spans),
            "avg_latency_ms": sum(s.performance.latency_ms.total_e2e_ms for s in member_spans) / len(member_spans),
            "avg_quality_score": sum(s.quality.score for s in member_spans) if all(s.quality for s in member_spans) else 0.8,
        }

    def _calculate_pattern_impact(self, member_spans: List[UnifiedLogEntry], span_map: Dict[str, UnifiedLogEntry]) -> float:
        """Calculate pattern impact fraction"""
        pattern_spend = sum(s.finops.total_cost_usd for s in member_spans)
        all_spans_spend = sum(s.finops.total_cost_usd for s in span_map.values())
        return (pattern_spend / all_spans_spend) if all_spans_spend > 0 else 0

    def _create_learned_policy(self, pattern: DiscoveredPattern, sorted_outcomes: List, 
                             baseline_metrics: Dict, pattern_impact_fraction: float) -> LearnedPolicy:
        """Create a learned policy from outcomes"""
        return LearnedPolicy(
            pattern_name=pattern.pattern_name, optimal_supply_option_name=sorted_outcomes[0].supply_option_name,
            predicted_outcome=sorted_outcomes[0], alternative_outcomes=sorted_outcomes[1:4],
            baseline_metrics=baseline_metrics, pattern_impact_fraction=pattern_impact_fraction)

    async def run(
        self, context: ToolContext, patterns: List[DiscoveredPattern], span_map: Dict[str, UnifiedLogEntry]
    ) -> Tuple[List[LearnedPolicy], List[PredictedOutcome]]:
        """Finds the best routing policies through simulation."""
        policies, outcomes, all_options = [], [], await self._get_supply_catalog(context)
        for pattern in patterns:
            member_spans = self._get_member_spans(pattern, span_map)
            if not member_spans:
                continue
            sorted_outcomes = await self._simulate_all_outcomes(context, pattern, all_options, member_spans[0].request.user_goal, member_spans[0])
            if not sorted_outcomes:
                continue
            outcomes.extend(sorted_outcomes)
            baseline_metrics = self._calculate_baseline_metrics(member_spans)
            pattern_impact_fraction = self._calculate_pattern_impact(member_spans, span_map)
            policies.append(self._create_learned_policy(pattern, sorted_outcomes, baseline_metrics, pattern_impact_fraction))
        return policies, outcomes

    def _build_simulation_prompt(self, pattern: DiscoveredPattern, supply_option: SupplyOption, user_goal: str) -> str:
        """Build prompt for simulation LLM call"""
        return f"""
        Simulate the outcome of routing a request with the following characteristics to the given supply option.

        Request Pattern:
        - Name: {pattern.pattern_name}
        - Description: {pattern.pattern_description}
        - User Goal: {user_goal}

        Supply Option:
        - Name: {supply_option.name}
        - Provider: {supply_option.provider}
        - Family: {supply_option.family}

        Based on this information, predict the following:
        - utility_score (0.0 to 1.0)
        - predicted_cost_usd (float)
        - predicted_latency_ms (int)
        - predicted_quality_score (0.0 to 1.0)
        - explanation (string)
        - confidence (0.0 to 1.0)

        Return the result as a JSON object.
        """

    async def _execute_llm_simulation(self, context: ToolContext, prompt: str) -> Any:
        """Execute LLM simulation call"""
        llm = context.llm_manager.get_llm(self.llm_name or "default")
        response = await llm.ainvoke(prompt)
        return response

    def _parse_simulation_response(self, response: Any) -> PredictedOutcome:
        """Parse simulation response and handle errors"""
        try:
            content = response.content if hasattr(response, 'content') else str(response)
            return PredictedOutcome.model_validate_json(content)
        except Exception as e:
            return None

    async def _simulate_policy_outcome(self, context: ToolContext, pattern: DiscoveredPattern, supply_option: SupplyOption, user_goal: str, span: UnifiedLogEntry) -> PredictedOutcome:
        """Simulate policy outcome through LLM prediction"""
        prompt = self._build_simulation_prompt(pattern, supply_option, user_goal)
        response = await self._execute_llm_simulation(context, prompt)
        return self._parse_simulation_response(response)

    async def _get_supply_catalog(self, context: ToolContext) -> List[SupplyOption]:
        """Retrieves the supply catalog from the database."""
        result = await context.db_session.execute(select(SupplyOption))
        return result.scalars().all()
