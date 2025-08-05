import asyncio
from typing import List, Dict, Any
from app.db.models_postgres import SupplyOption
from app.schema import LearnedPolicy, PredictedOutcome, DiscoveredPattern
from app.db.models_clickhouse import UnifiedLogEntry
from sqlalchemy.future import select
from app.services.apex_optimizer_agent.tools.base import BaseTool, ToolMetadata

class PolicyProposer(BaseTool):
    metadata = ToolMetadata(
        name="policy_proposer",
        description="Finds the best routing policies through simulation.",
        version="1.0.0",
        status="in_review"
    )

    async def run(
        self, patterns: List[DiscoveredPattern], span_map: Dict[str, UnifiedLogEntry]
    ) -> (List[LearnedPolicy], List[PredictedOutcome]):
        """Finds the best routing policies through simulation."""
        policies = []
        outcomes = []
        all_options = await self._get_supply_catalog()

        for pattern in patterns:
            member_spans = [span_map[sid] for sid in pattern.member_span_ids if sid in span_map]
            if not member_spans:
                continue

            representative_span = member_spans[0]
            user_goal = representative_span.request.user_goal

            sim_tasks = [self._simulate_policy_outcome(pattern, supply, user_goal, representative_span) for supply in all_options]
            policy_outcomes = [o for o in await asyncio.gather(*sim_tasks) if o]

            if not policy_outcomes:
                continue

            sorted_outcomes = sorted(policy_outcomes, key=lambda x: x.utility_score, reverse=True)
            outcomes.extend(sorted_outcomes)

            baseline_metrics = {
                "avg_cost_usd": sum(s.finops.total_cost_usd for s in member_spans) / len(member_spans),
                "avg_latency_ms": sum(s.performance.latency_ms.total_e2e_ms for s in member_spans) / len(member_spans),
                "avg_quality_score": sum(s.quality.score for s in member_spans) / len(member_spans) if all(s.quality for s in member_spans) else 0.8,
            }

            pattern_spend = sum(s.finops.total_cost_usd for s in member_spans)
            all_spans_spend = sum(s.finops.total_cost_usd for s in span_map.values())
            pattern_impact_fraction = (pattern_spend / all_spans_spend) if all_spans_spend > 0 else 0

            policies.append(LearnedPolicy(
                pattern_name=pattern.pattern_name,
                optimal_supply_option_name=sorted_outcomes[0].supply_option_name,
                predicted_outcome=sorted_outcomes[0],
                alternative_outcomes=sorted_outcomes[1:4],
                baseline_metrics=baseline_metrics,
                pattern_impact_fraction=pattern_impact_fraction
            ))
        return policies, outcomes

    async def _simulate_policy_outcome(self, pattern: DiscoveredPattern, supply_option: SupplyOption, user_goal: str, span: UnifiedLogEntry) -> PredictedOutcome:
        prompt = f"""
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
        llm = self.get_llm()
        response = await llm.ainvoke(prompt)
        try:
            return PredictedOutcome.model_validate_json(response.content)
        except Exception as e:
            # Handle parsing errors
            return None

    async def _get_supply_catalog(self) -> List[SupplyOption]:
        """Retrieves the supply catalog from the database."""
        result = await self.db_session.execute(select(SupplyOption))
        return result.scalars().all()