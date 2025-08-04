import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from sklearn.cluster import KMeans
from sqlalchemy.future import select

from app.db.models_clickhouse import UnifiedLogEntry
from app.db.models_postgres import SupplyOption
from app.schema import DiscoveredPattern, LearnedPolicy, PredictedOutcome
from app.services.security_service import security_service
from app.db.clickhouse import get_clickhouse_client
from app.config import settings

async def query_raw_logs(
    db_session: Any,
    source_table: str,
    start_time: datetime,
    end_time: datetime,
    filters: Optional[Dict[str, Any]] = None,
) -> List[UnifiedLogEntry]:
    """Connects to ClickHouse to fetch raw log data."""
    credentials = security_service.get_user_credentials(user_id=db_session.info["user_id"], db_session=db_session)
    if not credentials:
        raise ValueError("ClickHouse credentials not found for user.")

    client = get_clickhouse_client(credentials)
    database, table = source_table.split('.', 1)
    query = f"SELECT * FROM {database}.{table} WHERE timestamp BETWEEN '{start_time}' AND '{end_time}'"

    if filters:
        for key, value in filters.items():
            query += f" AND {key} = '{value}'"

    query_result = client.execute(query, with_column_types=True)
    if not query_result or not query_result[0]:
        return []

    column_names = [col[0] for col in query_result[1]]
    data_rows = query_result[0]

    log_entries = []
    for row in data_rows:
        try:
            row_dict = dict(zip(column_names, row))
            for key, value in row_dict.items():
                if isinstance(value, str) and value.startswith('{'):
                    try:
                        row_dict[key] = json.loads(value)
                    except json.JSONDecodeError:
                        pass
            log_entries.append(UnifiedLogEntry.model_validate(row_dict))
        except Exception as e:
            print(f"Skipping a row due to parsing/validation error: {e}. Row data: {row}")
            continue
    return log_entries


async def enrich_and_cluster_logs(
    spans: List[UnifiedLogEntry],
    n_patterns: int = 5,
    llm_connector: any = None
) -> List[DiscoveredPattern]:
    """Enriches logs and applies KMeans clustering."""
    if not spans:
        return []

    # Enrichment
    for span in spans:
        usage = span.response.get('usage', {})
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = prompt_tokens + completion_tokens
        latency_ms = span.performance['latency_ms']['total_e2e_ms']
        ttft_ms = span.performance['latency_ms']['time_to_first_token_ms']
        
        inter_token_latency = None
        if completion_tokens > 1 and latency_ms > ttft_ms:
            inter_token_latency = (latency_ms - ttft_ms) / (completion_tokens - 1)
        
        span.enriched_metrics = {
            "prefill_ratio": prompt_tokens / max(total_tokens, 1),
            "generation_ratio": completion_tokens / max(total_tokens, 1),
            "throughput_tokens_per_sec": total_tokens / max(latency_ms / 1000, 0.001),
            "inter_token_latency_ms": inter_token_latency
        }

    # Clustering
    enriched_spans_data = [{'span_id': s.trace_context.span_id, **s.enriched_metrics} for s in spans if s.enriched_metrics]
    if not enriched_spans_data:
        return []

    df = pd.DataFrame(enriched_spans_data).dropna()
    features = ['prefill_ratio', 'generation_ratio', 'throughput_tokens_per_sec']
    if len(df) < n_patterns:
        n_patterns = len(df)
    if n_patterns == 0:
        return []

    kmeans = KMeans(n_clusters=n_patterns, random_state=42, n_init='auto')
    df['pattern_id_num'] = kmeans.fit_predict(df[features])
    
    centroids = [df[df['pattern_id_num'] == i][features].mean().to_dict() for i in range(n_patterns) if not df[df['pattern_id_num'] == i].empty]
    
    if not centroids:
        return []

    # Generate descriptions
    descriptions = {}
    if llm_connector:
        features_json = json.dumps({f"pattern_{i}": features for i, features in enumerate(centroids)}, indent=2)
        prompt = f"""
        Analyze the following LLM usage pattern features. For each pattern, generate a concise, 2-4 word name and a one-sentence description.
        **Pattern Features (JSON):**
{features_json}

        **Output Format (JSON ONLY):**
        Respond with a single JSON object where keys are the pattern identifiers (e.g., "pattern_0"). Each value should be an object containing "name" and "description".
        """
        response = await llm_connector.generate_text_async(prompt, settings.analysis_model, settings.analysis_model_fallback)
        descriptions = json.loads(response) if response else {}

    patterns = []
    for i, centroid in enumerate(centroids):
        cluster_df = df[df['pattern_id_num'] == i]
        desc_data = descriptions.get(f"pattern_{i}", {})
        patterns.append(DiscoveredPattern(
            pattern_name=desc_data.get('name', f'Pattern {i+1}') if desc_data else f'Pattern {i+1}',
            pattern_description=desc_data.get('description', 'A general usage pattern.') if desc_data else 'A general usage pattern.',
            centroid_features=centroid, member_span_ids=cluster_df['span_id'].tolist(),
            member_count=len(cluster_df)
        ))
    return patterns


async def propose_optimal_policies(
    db_session: Any,
    patterns: List[DiscoveredPattern],
    span_map: Dict[str, UnifiedLogEntry],
    llm_connector: any
) -> List[LearnedPolicy]:
    """Finds the best routing policies through simulation."""
    policies = []
    all_options = await get_supply_catalog(db_session)

    for pattern in patterns:
        member_spans = [span_map[sid] for sid in pattern.member_span_ids if sid in span_map]
        if not member_spans:
            continue

        representative_span = member_spans[0]
        user_goal = representative_span.request.user_goal

        sim_tasks = [simulate_policy_outcome(pattern, supply, user_goal, llm_connector, representative_span) for supply in all_options]
        outcomes = [o for o in await asyncio.gather(*sim_tasks) if o]

        if not outcomes:
            continue

        sorted_outcomes = sorted(outcomes, key=lambda x: x.utility_score, reverse=True)

        baseline_metrics = {
            "avg_cost_usd": sum(s.finops['total_cost_usd'] for s in member_spans) / len(member_spans),
            "avg_latency_ms": sum(s.performance['latency_ms']['total_e2e_ms'] for s in member_spans) / len(member_spans),
            "avg_quality_score": 0.8 # Placeholder
        }

        pattern_spend = sum(s.finops['total_cost_usd'] for s in member_spans)
        all_spans_spend = sum(s.finops['total_cost_usd'] for s in span_map.values())
        pattern_impact_fraction = (pattern_spend / all_spans_spend) if all_spans_spend > 0 else 0

        policies.append(LearnedPolicy(
            pattern_name=pattern.pattern_name,
            optimal_supply_option_name=sorted_outcomes[0].supply_option_name,
            predicted_outcome=sorted_outcomes[0],
            alternative_outcomes=sorted_outcomes[1:4],
            baseline_metrics=baseline_metrics,
            pattern_impact_fraction=pattern_impact_fraction
        ))
    return policies


async def simulate_policy_outcome(
    pattern: DiscoveredPattern,
    supply_option: SupplyOption,
    user_goal: str,
    llm_connector: any,
    span: UnifiedLogEntry
) -> PredictedOutcome:
    """Simulates the outcome of a single policy."""
    prompt = f"""
    As an AI Systems Performance Engineer, predict performance.
    **Workload Pattern:** {pattern.pattern_name} ({pattern.pattern_description})
    **Pattern Features:** {json.dumps(pattern.centroid_features, indent=2)}
    **Representative Span Usage:** Prompt Tokens: {span.response['usage']['prompt_tokens']}, Completion Tokens: {span.response['usage']['completion_tokens']}
    **Simulating Supply Option:** {supply_option.model_dump_json(indent=2)}
    **Task:** Predict performance. Calculate cost using the provided token counts and the supply option's cost structure.
    **Output Format (JSON ONLY):**
    {{
        "predicted_cost_usd": <float>, "predicted_latency_ms": <int>, "predicted_quality_score": <float, 0.0-1.0>,
        "explanation": "<string, concise rationale>", "confidence": <float, 0.0-1.0>
    }}
    """
    response_text = await llm_connector.generate_text_async(prompt, settings.analysis_model, settings.analysis_model_fallback)
    sim_data = json.loads(response_text) if response_text else {}

    if not sim_data:
        return None

    # Basic utility calculation, can be expanded
    norm_cost = min(sim_data.get('predicted_cost_usd', 0) / 0.05, 1.0)
    norm_latency = min(sim_data.get('predicted_latency_ms', 0) / 5000, 1.0)
    weights = {"quality": 0.5, "cost": -0.25, "latency": -0.25}
    if user_goal == 'cost': weights = {"quality": 0.2, "cost": -0.6, "latency": -0.2}
    elif user_goal == 'latency': weights = {"quality": 0.2, "cost": -0.2, "latency": -0.6}
    
    utility_score = (
        weights['quality'] * sim_data.get('predicted_quality_score', 0) + 
        weights['cost'] * norm_cost + 
        weights['latency'] * norm_latency
    ) * sim_data.get('confidence', 0.85)

    return PredictedOutcome(supply_option_name=supply_option.name, utility_score=utility_score, **sim_data)

async def get_supply_catalog(db_session: Any) -> List[SupplyOption]:
    """Retrieves the supply catalog from the database."""
    return db_session.exec(select(SupplyOption)).all()
