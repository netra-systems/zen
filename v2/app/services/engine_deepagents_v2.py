import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from deepagents import create_deep_agent
from app.services.engine import replace

import json
from clickhouse_driver import Client

import pandas as pd
from sklearn.cluster import KMeans
from ..services.engine import GeminiLLMConnector, AppConfig

# Assuming these models are defined elsewhere and are importable
from ..db.models_clickhouse import UnifiedLogEntry, AnalysisRequest
from ..db.models_postgres import SupplyOption
from ..schema import AnalysisRun, DiscoveredPattern, LearnedPolicy, PredictedOutcome, CostComparison

# --- Core Tools for Deep Agents V2 ---

async def query_raw_logs(
    db_session: Any, # Should be sqlmodel.Session, but avoiding circular import
    source_table: str,
    start_time: datetime,
    end_time: datetime,
    filters: Optional[Dict[str, Any]] = None,
) -> List[UnifiedLogEntry]:
    """
    Connects to the user's ClickHouse database to fetch raw, unprocessed log data.
    This is the primary data gathering mechanism, providing the foundational data for analysis.
    It allows filtering by time range and other specific log attributes.
    """
    """
    credentials = security_service.get_user_credentials(user_id=db_session.info["user_id"], db_session=db_session)
    if not credentials:
        raise ValueError("ClickHouse credentials not found for user.")

    client = Client(**credentials.model_dump())
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

async def get_supply_catalog(db_session: Any) -> List[SupplyOption]:
    """
    Provides a complete, up-to-date list of all available "supply options" (e.g., models).
    The catalog contains critical metadata for each option, including cost structure, quality scores,
    and performance characteristics, which is essential for the simulation engine.
    """
    """
    return db_session.exec(select(SupplyOption)).all()

async def enrich_and_cluster_logs(
    spans: List[UnifiedLogEntry],
    n_patterns: int = 5,
    llm_connector: GeminiLLMConnector = None # Added for generating descriptions
) -> List[DiscoveredPattern]:
    """
    Takes raw log entries, enriches them with calculated performance metrics (e.g., throughput),
    and then applies KMeans clustering to identify and group similar usage patterns.
    It uses an LLM to generate a human-readable name and description for each pattern.
    """
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
        prompt = f'''
        Analyze the following LLM usage pattern features. For each pattern, generate a concise, 2-4 word name and a one-sentence description.
        **Pattern Features (JSON):**\n{features_json}\n
        **Output Format (JSON ONLY):**
        Respond with a single JSON object where keys are the pattern identifiers (e.g., "pattern_0"). Each value should be an object containing "name" and "description".
        '''
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

async def simulate_policy_outcome(
    pattern: DiscoveredPattern,
    supply_option: SupplyOption,
    user_goal: str,
    llm_connector: GeminiLLMConnector, # Added for simulation
    span: UnifiedLogEntry # Added for representative span usage
) -> PredictedOutcome:
    """
    The core "what-if" engine. It takes a single usage pattern and a single supply option
    and uses an LLM to predict the performance and cost outcome. It calculates a final
    "utility score" based on the user's stated goal ('cost', 'latency', or 'quality').
    """
    """
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
    ) * sim_data.get('confidence', 0.85)

    return PredictedOutcome(supply_option_name=supply_option.name, utility_score=utility_score, **sim_data)

async def propose_optimal_policies(
    db_session: Any,
    patterns: List[DiscoveredPattern],
    span_map: Dict[str, UnifiedLogEntry],
    llm_connector: GeminiLLMConnector
) -> List[LearnedPolicy]:
    """
    High-level orchestration tool that finds the best routing policies. It runs simulations
    for every relevant pattern-supply pair, ranks the outcomes by utility score, and formulates
    a `LearnedPolicy` with the top recommendation and expected impact.
    """
    """
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

async def read_project_files(
    file_paths: List[str],
) -> Dict[str, str]:
    """
    Reads the content of specified files within the user's project directory to gain
    context that isn't present in logs alone, such as configuration or source code.
    This allows for more specific and actionable recommendations.
    """
    # This would use a file system utility to read files.
    print(f"Reading project files: {file_paths}")
    return {path: "File content placeholder" for path in file_paths}

async def google_web_search(query: str) -> str:
    """
    Searches the public internet to find "unknown unknowns," such as new model releases,
    API changes, or novel optimization techniques. This keeps recommendations current
    and comprehensive.
    """
    # This would use a Google Search API.
    print(f"Performing Google web search for: '{query}'")
    return "Search results placeholder"

async def lookup_previous_analysis(
    db_session: Any,
    user_id: str,
    limit: int = 3,
) -> List[AnalysisRun]:
    """
    Provides a memory of past work by querying the application's database for previous
    analysis runs for the same user. This helps the agent build on prior knowledge and
    track the resolution of past issues.
    """
    """
    return db_session.exec(
        select(AnalysisRun)
        .where(AnalysisRun.user_id == user_id)
        .order_by(AnalysisRun.created_at.desc())
        .limit(limit)
    ).all()

async def draft_configuration_change(
    file_path: str,
    old_string: str,
    new_string: str,
) -> str:
    """
    Action-oriented tool that translates a learned policy into a concrete, reviewable
    artifact. It reads a configuration file and generates a proposed change based on
    a policy recommendation, which is then presented to the user for review.
    """
    """
    return replace(file_path=file_path, old_string=old_string, new_string=new_string)

async def request_human_review(
    analysis_summary: str,
    policies: List[LearnedPolicy],
    cost_comparison: CostComparison,
    drafted_changes: Optional[Dict[str, str]] = None,
) -> str:
    """
    The final hand-off tool. It packages the entire analysis—patterns, policies, cost savings,
    and drafted changes—into a clear, concise report for the user's final review and approval.
    """
    # This would format the final results into a human-readable report.
    print("Requesting human review with a full analysis report.")
    return "Review request sent."


# --- Deep Agent V2 Definition ---

async def run_analysis_with_deepagents_v2(
    run_id: str, request: AnalysisRequest, db_session, preloaded_spans: Optional[List[UnifiedLogEntry]] = None
):
    """
    Runs the analysis pipeline using a deep agent v2.
    """
    update_run_status(run_id, "running", log_message="Starting analysis with deep agents v2...")

    # 1. Define the tools for the agent
    tools = [
        query_raw_logs,
        get_supply_catalog,
        enrich_and_cluster_logs,
        simulate_policy_outcome,
        propose_optimal_policies,
        read_project_files,
        google_web_search,
        lookup_previous_analysis,
        draft_configuration_change,
        request_human_review,
    ]

    # 2. Define the sub-agents
    sub_agents = [
        {
            "name": "triage_agent",
            "description": "Parses user goals and determines the best course of action.",
            "prompt": "You are a triage agent. Your job is to analyze the user's request and create a high-level plan of which tools and sub-agents to use to achieve the user's goal. Start by understanding the core objective (e.g., 'reduce cost', 'improve latency', 'find anomalies').",
        },
        {
            "name": "planner_agent",
            "description": "Creates a detailed, step-by-step plan for the analysis.",
            "prompt": "You are a planner agent. Based on the triage, create a detailed, step-by-step plan. You must sequence the tool calls logically. For example: 1. `query_raw_logs`, 2. `enrich_and_cluster_logs`, 3. `get_supply_catalog`, 4. `propose_optimal_policies`, 5. `request_human_review`.",
        },
        {
            "name": "optimization_agent",
            "description": "Focuses specifically on recommending and validating optimization strategies.",
            "prompt": "You are an optimization agent. Your role is to look beyond simple model routing. Use `read_project_files` to inspect code and `google_web_search` to find advanced techniques (e.g., KV caching, prompt engineering). Your goal is to find non-obvious improvements.",
        },
    ]

    # 3. Define the instructions for the main agent
    instructions = """
    You are the Core Apex Agent, a powerful analysis engine. Your goal is to conduct a comprehensive analysis of the user's LLM usage and provide actionable recommendations for optimization.

    Your process is as follows:
    1.  **Triage:** Use the `triage_agent` to understand the user's primary goal.
    2.  **Plan:** Use the `planner_agent` to create a detailed, step-by-step execution plan.
    3.  **Execute:** Follow the plan, using the available tools and sub-agents to gather data, discover patterns, simulate outcomes, and find optimizations.
    4.  **Report:** Once the analysis is complete, use the `request_human_review` tool to present a full report of your findings, including recommended policies, projected savings, and any drafted configuration changes.
    """

    # 4. Create the deep agent
    agent = create_deep_agent(tools=tools, instructions=instructions, subagents=sub_agents)

    # 5. Run the agent
    try:
        # In a real scenario, the initial message would be more dynamic.
        initial_message = f"Analyze the following request: {request.model_dump_json(indent=2)}"
        if preloaded_spans:
            # The deepagents library would need a way to handle file-like objects or data in memory.
            # For this example, we'll just mention it in the prompt.
            initial_message += f"\n\nUse the {len(preloaded_spans)} pre-loaded spans provided for the analysis."

        result = await agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": initial_message,
                    }
                ],
            }
        )
        # The final result from the agent would be processed into a standard format.
        update_run_status(run_id, "completed", "Analysis complete.", result=result)
    except Exception as e:
        update_run_status(run_id, "failed", f"An error occurred: {e}", error=str(e))

# Placeholder for update_run_status if this file is run standalone
def update_run_status(run_id: str, status: str, log_message: str = "", result: Any = None, error: str = ""):
    print(f"[{run_id}] Status: {status} | Message: {log_message} | Result: {result} | Error: {error}")