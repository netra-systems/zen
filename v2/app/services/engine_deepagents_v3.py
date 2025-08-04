import asyncio
import json
from typing import List, Dict, Any, Optional, Callable, Type
from datetime import datetime
import pandas as pd
from sklearn.cluster import KMeans
from langfuse import Langfuse
from langfuse.model import CreateTrace

from app.deepagents.graph import create_deep_agent, DeepAgentState
from app.services.engine import GeminiLLMConnector, AppConfig
from app.db.models_clickhouse import UnifiedLogEntry, AnalysisRequest
from app.db.models_postgres import SupplyOption
from app.schema import AnalysisRun, DiscoveredPattern, LearnedPolicy, PredictedOutcome, CostComparison
from app.services.security_service import security_service
from app.db.clickhouse import get_clickhouse_client

# --- State Management ---

class AgentState(DeepAgentState):
    """Extends the base state to include analysis-specific data."""
    request: Optional[AnalysisRequest] = None
    raw_logs: Optional[List[UnifiedLogEntry]] = None
    patterns: Optional[List[DiscoveredPattern]] = None
    policies: Optional[List[LearnedPolicy]] = None
    cost_comparison: Optional[CostComparison] = None
    final_report: Optional[str] = None

# --- V3 Engine ---

from app.db.models_postgres import DeepAgentRun

class DeepAgentV3:
    """
    A stateful, step-by-step agent for conducting deep analysis of LLM usage.
    This engine is designed for interactive control, monitoring, and extensibility.
    """

    def __init__(self, run_id: str, request: AnalysisRequest, db_session: Any, llm_connector: GeminiLLMConnector):
        self.run_id = run_id
        self.request = request
        self.db_session = db_session
        self.llm_connector = llm_connector
        self.state = AgentState(messages=[])
        self.langfuse = Langfuse() # Add your Langfuse credentials here

        self.steps = [
            self._step_1_fetch_raw_logs,
            self._step_2_enrich_and_cluster,
            self._step_3_propose_optimal_policies,
            self._step_4_generate_final_report,
        ]
        self.current_step_index = 0

    async def run_full_analysis(self):
        """Executes the entire analysis pipeline from start to finish."""
        trace = self.langfuse.trace(CreateTrace(id=self.run_id, name="FullAnalysis"))
        
        for step_func in self.steps:
            await self._execute_step(step_func, trace)
        
        return self.state.final_report

    async def run_next_step(self):
        """Executes the next step in the analysis pipeline."""
        if self.is_complete():
            return {"status": "complete", "message": "Analysis is already complete."}

        step_func = self.steps[self.current_step_index]
        trace = self.langfuse.trace(CreateTrace(id=f"{self.run_id}-{self.current_step_index}", name=step_func.__name__))

        result = await self._execute_step(step_func, trace)
        self.current_step_index += 1
        return result

    async def _execute_step(self, step_func: Callable, trace: Any):
        step_name = step_func.__name__
        span = trace.span(name=step_name)

        try:
            input_data = self.state.dict() # Capture state before the step
            result = await step_func()
            output_data = self.state.dict() # Capture state after the step

            span.end(output=output_data)
            self._record_step_history(step_name, input_data, output_data)

            return {"status": "in_progress", "completed_step": step_name, "result": result}
        except Exception as e:
            span.end(level="ERROR", status_message=str(e))
            return {"status": "failed", "step": step_name, "error": str(e)}

    def _record_step_history(self, step_name: str, input_data: Dict, output_data: Dict):
        new_run = DeepAgentRun(
            run_id=self.run_id,
            step_name=step_name,
            step_input=input_data,
            step_output=output_data,
        )
        self.db_session.add(new_run)
        self.db_session.commit()

    def is_complete(self) -> bool:
        """Checks if the analysis has completed all steps."""
        return self.current_step_index >= len(self.steps)

    # --- Analysis Steps ---

    async def _step_1_fetch_raw_logs(self):
        """Fetches raw log data from the user's ClickHouse database."""
        self.state.raw_logs = await query_raw_logs(
            db_session=self.db_session,
            source_table=self.request.data_source.source_table,
            start_time=self.request.time_range.start_time,
            end_time=self.request.time_range.end_time,
            filters=self.request.data_source.filters,
        )
        return f"Fetched {len(self.state.raw_logs)} log entries."

    async def _step_2_enrich_and_cluster(self):
        """Enriches logs and clusters them to find usage patterns."""
        if not self.state.raw_logs:
            raise ValueError("Cannot perform clustering without raw logs.")

        self.state.patterns = await enrich_and_cluster_logs(
            spans=self.state.raw_logs,
            llm_connector=self.llm_connector,
        )
        return f"Discovered {len(self.state.patterns)} usage patterns."

    async def _step_3_propose_optimal_policies(self):
        """Simulates outcomes and proposes optimal routing policies."""
        if not self.state.patterns:
            raise ValueError("Cannot propose policies without discovered patterns.")

        span_map = {span.trace_context.span_id: span for span in self.state.raw_logs}
        self.state.policies = await propose_optimal_policies(
            db_session=self.db_session,
            patterns=self.state.patterns,
            span_map=span_map,
            llm_connector=self.llm_connector,
        )
        return f"Generated {len(self.state.policies)} optimal policies."

    async def _step_4_generate_final_report(self):
        """Generates a human-readable summary of the analysis."""
        if not self.state.policies:
            raise ValueError("Cannot generate a report without policies.")
            
        # This step can be expanded to use an LLM for a more narrative report
        report = "Analysis Complete. Recommended Policies:\n"
        for policy in self.state.policies:
            report += f"- For pattern '{policy.pattern_name}', recommend using '{policy.optimal_supply_option_name}'.\n"
        
        self.state.final_report = report
        return "Final report generated."


# --- Core Tools (Adapted from V2) ---

async def query_raw_logs(
    db_session: Any,
    source_table: str,
    start_time: datetime,
    end_time: datetime,
    filters: Optional[Dict[str, Any]] = None,
) -> List[UnifiedLogEntry]:
    """Connects to ClickHouse to fetch raw log data."""
    # This function remains largely the same but should use proper dependency injection for credentials
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
    # ... (rest of the parsing logic remains the same)
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
    llm_connector: GeminiLLMConnector = None
) -> List[DiscoveredPattern]:
    """Enriches logs and applies KMeans clustering."""
    # This function remains largely the same
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
        **Pattern Features (JSON):**\n{features_json}\n
        **Output Format (JSON ONLY):**
        Respond with a single JSON object where keys are the pattern identifiers (e.g., \"pattern_0\"). Each value should be an object containing \"name\" and \"description\".
        """
        config = AppConfig()
        response = await llm_connector.generate_text_async(prompt, config.ANALYSIS_MODEL, config.ANALYSIS_MODEL_FALLBACK)
        descriptions = json.loads(response) if response else {}

    patterns = []
    for i, centroid in enumerate(centroids):
        cluster_df = df[df['pattern_id_num'] == i]
        desc_data = descriptions.get(f"pattern_{i}", {{}})
        patterns.append(DiscoveredPattern(
            pattern_name=desc_data.get('name', f'Pattern {i+1}'),
            pattern_description=desc_data.get('description', 'A general usage pattern.'),
            centroid_features=centroid, member_span_ids=cluster_df['span_id'].tolist(),
            member_count=len(cluster_df)
        ))
    return patterns


async def propose_optimal_policies(
    db_session: Any,
    patterns: List[DiscoveredPattern],
    span_map: Dict[str, UnifiedLogEntry],
    llm_connector: GeminiLLMConnector
) -> List[LearnedPolicy]:
    """Finds the best routing policies through simulation."""
    # This function remains largely the same
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
    llm_connector: GeminiLLMConnector,
    span: UnifiedLogEntry
) -> PredictedOutcome:
    """Simulates the outcome of a single policy."""
    # This function remains largely the same
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
    config = AppConfig()
    response_text = await llm_connector.generate_text_async(prompt, config.ANALYSIS_MODEL, config.ANALYSIS_MODEL_FALLBACK)
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
    ) * sim_.get('confidence', 0.85)

    return PredictedOutcome(supply_option_name=supply_option.name, utility_score=utility_score, **sim_data)

async def get_supply_catalog(db_session: Any) -> List[SupplyOption]:
    """Retrieves the supply catalog from the database."""
    # This function remains largely the same
    return db_session.exec(select(SupplyOption)).all()