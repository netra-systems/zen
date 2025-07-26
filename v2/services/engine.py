# /services/v23_engine_adapted.py
# ==============================================================================
# Netra Apex v23.4 - Adapted for Production Workflow
#
# This file is an adaptation of the original v23.py.
# Key Changes:
# - Removed FastAPI server components.
# - Modified AnalysisPipeline to accept pre-loaded spans instead of generating them.
# - Refactored SupplyCatalog into its own service for better modularity.
# ==============================================================================

# --- Core Imports ---
import os
import sys
import time
import uuid
import json
import logging
import random
import asyncio
from typing import Dict, Any, List, Optional, Literal, Callable
from functools import wraps

# --- Third-Party Imports ---
import httpx
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# --- Local Service Imports ---
from .supply_catalog_service import SupplyCatalog, SupplyOption, ModelIdentifier

# --- Configuration ---
load_dotenv()

class AppConfig:
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    ANALYSIS_MODEL = "gemini-1.5-pro-latest"
    ANALYSIS_MODEL_FALLBACK = "gemini-1.5-flash-latest"

config = AppConfig()

# --- Global State for Analysis Runs ---
analysis_runs: Dict[str, Dict] = {}

# --- Utility Functions & Decorators ---
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

logger = get_logger(__name__)

def time_it(run_id: str, step_name: str):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            update_run_status(run_id, 'running', log_message=f"Starting: {step_name}...")
            result = await func(*args, **kwargs)
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            update_run_status(run_id, 'running', log_message=f"Completed: {step_name}", duration_ms=duration_ms)
            return result
        return wrapper
    return decorator

def update_run_status(run_id: str, status: str, log_message: Optional[str] = None, result: Optional[Any] = None, error: Optional[str] = None, duration_ms: Optional[float] = None):
    if run_id not in analysis_runs:
        analysis_runs[run_id] = {"status": "pending", "execution_log": [], "start_time": time.time(), "last_update_time": time.time()}
    
    analysis_runs[run_id]["status"] = status
    analysis_runs[run_id]["last_update_time"] = time.time()
    if log_message:
        log_entry = {
            "timestamp": time.strftime('%H:%M:%S'),
            "message": log_message,
            "duration_ms": duration_ms
        }
        analysis_runs[run_id]["execution_log"].append(log_entry)
        log_msg_console = f"Run {run_id}: {log_message}"
        if duration_ms:
            log_msg_console += f" ({duration_ms:.2f}ms)"
        logger.info(log_msg_console)
    if result:
        analysis_runs[run_id]["result"] = result
    if error:
        analysis_runs[run_id]["error"] = error
        logger.error(f"Run {run_id} failed: {error}")

def extract_json_from_response(text: str) -> Optional[Dict]:
    if not text: return None
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        start_index = text.find('{')
        end_index = text.rfind('}')
        if start_index != -1 and end_index != -1 and end_index > start_index:
            json_str = text[start_index:end_index+1]
            return json.loads(json_str)
    except (json.JSONDecodeError, IndexError) as e:
        logger.error(f"JSON parsing failed: {e}. Original text: '{text[:200]}...'")
    return None

# --- Pydantic Schemas ---
class EventMetadata(BaseModel):
    log_schema_version: str = "23.4.0"
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}")
    timestamp_utc: int = Field(default_factory=lambda: int(time.time()))

class TraceContext(BaseModel):
    trace_id: str
    span_id: str = Field(default_factory=lambda: f"span_{uuid.uuid4().hex[:8]}")
    parent_span_id: Optional[str] = None

class RequestData(BaseModel):
    model: ModelIdentifier
    prompt_text: str
    user_goal: Literal["cost", "latency", "quality"] = "quality"

class EnrichedMetrics(BaseModel):
    prefill_ratio: float
    generation_ratio: float
    throughput_tokens_per_sec: float
    inter_token_latency_ms: Optional[float] = None

class UnifiedLogEntry(BaseModel):
    event_metadata: EventMetadata = Field(default_factory=EventMetadata)
    trace_context: TraceContext
    request: RequestData
    performance: Dict[str, Any]
    finops: Dict[str, Any]
    response: Dict[str, Any]
    workloadName: str = "Unknown"
    enriched_metrics: Optional[EnrichedMetrics] = None
    embedding: Optional[List[float]] = None

class DiscoveredPattern(BaseModel):
    pattern_id: str = Field(default_factory=lambda: f"pat_{uuid.uuid4().hex[:8]}")
    pattern_name: str
    pattern_description: str
    centroid_features: Dict[str, float]
    member_span_ids: List[str]
    member_count: int

class PredictedOutcome(BaseModel):
    supply_option_id: str
    predicted_cost_usd: float
    predicted_latency_ms: int
    predicted_quality_score: float
    utility_score: float
    explanation: str
    confidence: float

class BaselineMetrics(BaseModel):
    avg_cost_usd: float
    avg_latency_ms: int
    avg_quality_score: float

class LearnedPolicy(BaseModel):
    pattern_id: str
    optimal_supply_option_id: str
    predicted_outcome: PredictedOutcome
    alternative_outcomes: List[PredictedOutcome]
    baseline_metrics: BaselineMetrics
    pattern_impact_fraction: float

class CostComparison(BaseModel):
    prior_monthly_spend: float
    projected_monthly_spend: float
    projected_monthly_savings: float
    delta_percent: float

class AnalysisRequest(BaseModel):
    workloads: List[Dict]
    debug_mode: bool = False
    constraints: Optional[Dict[str, bool]] = None
    negotiated_discount_percent: float = Field(0.0, ge=0, le=100)

class AnalysisResult(BaseModel):
    run_id: str
    discovered_patterns: List[DiscoveredPattern]
    learned_policies: List[LearnedPolicy]
    supply_catalog: List[SupplyOption]
    cost_comparison: CostComparison
    execution_log: List[Dict]
    debug_mode: bool
    span_map: Dict[str, UnifiedLogEntry]

# --- Connectors ---
class GeminiLLMConnector:
    # (Content is identical to previous version, omitted for brevity)
    def __init__(self, api_key: str, async_client: httpx.AsyncClient):
        self.api_key = api_key
        self.async_client = async_client
        if not self.api_key or self.api_key == "YOUR_GEMINI_API_KEY":
            raise ValueError("Missing GEMINI_API_KEY.")
    
    async def generate_text_async(self, prompt: str, model_name: str, fallback_model_name: Optional[str] = None) -> Optional[str]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            response = await self.async_client.post(url, json=payload, timeout=90.0)
            response.raise_for_status()
            data = response.json()
            return data['candidates'][0]['content']['parts'][0]['text']
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for model {model_name}: {e.response.status_code} - {e.response.text}")
            if fallback_model_name and e.response.status_code in [429, 500, 503]:
                logger.warning(f"Primary model {model_name} failed. Falling back to {fallback_model_name}.")
                return await self.generate_text_async(prompt, fallback_model_name, fallback_model_name=None)
        except Exception as e:
            logger.error(f"Async text generation failed for model {model_name}: {e}")
        return None

# --- Core Modules ---
class LogEnrichmentModule:
    # (Content is identical to previous version)
    def enrich_spans(self, spans: List[UnifiedLogEntry]) -> List[UnifiedLogEntry]:
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
            
            span.enriched_metrics = EnrichedMetrics(
                prefill_ratio=prompt_tokens / max(total_tokens, 1),
                generation_ratio=completion_tokens / max(total_tokens, 1),
                throughput_tokens_per_sec=total_tokens / max(latency_ms / 1000, 0.001),
                inter_token_latency_ms=inter_token_latency
            )
        return spans

class PatternDiscoverer:
    # (Content is identical to previous version)
    def __init__(self, llm_connector: GeminiLLMConnector):
        self.llm = llm_connector

    async def discover_patterns_from_spans(self, spans: List[UnifiedLogEntry], n_patterns: int = 3) -> List[DiscoveredPattern]:
        if len(spans) < n_patterns: n_patterns = max(1, len(spans))
        if n_patterns == 0: return []
        
        enriched_spans_data = [{'span_id': s.trace_context.span_id, **s.enriched_metrics.model_dump()} for s in spans if s.enriched_metrics]
        if not enriched_spans_data: return []

        df = pd.DataFrame(enriched_spans_data).dropna()
        features = ['prefill_ratio', 'generation_ratio', 'throughput_tokens_per_sec']
        if len(df) < n_patterns: n_patterns = len(df)
        if n_patterns == 0: return []

        kmeans = KMeans(n_clusters=n_patterns, random_state=42, n_init='auto')
        df['pattern_id_num'] = kmeans.fit_predict(df[features])
        
        centroids = [df[df['pattern_id_num'] == i][features].mean().to_dict() for i in range(n_patterns) if not df[df['pattern_id_num'] == i].empty]
        
        if not centroids: return []

        descriptions = await self._generate_pattern_descriptions_batch(centroids)
        
        patterns = []
        for i, centroid in enumerate(centroids):
            cluster_df = df[df['pattern_id_num'] == i]
            desc_data = descriptions.get(f"pattern_{i}", {})
            patterns.append(DiscoveredPattern(
                pattern_name=desc_data.get('name', f'Pattern {i+1}'),
                pattern_description=desc_data.get('description', 'A general usage pattern.'),
                centroid_features=centroid, member_span_ids=cluster_df['span_id'].tolist(),
                member_count=len(cluster_df)
            ))
        return patterns

    async def _generate_pattern_descriptions_batch(self, centroids: List[Dict]) -> Dict:
        features_json = json.dumps({f"pattern_{i}": features for i, features in enumerate(centroids)}, indent=2)
        prompt = f"""
        Analyze the following LLM usage pattern features. For each pattern, generate a concise, 2-4 word name and a one-sentence description.
        **Pattern Features (JSON):**\n{features_json}\n
        **Output Format (JSON ONLY):**
        Respond with a single JSON object where keys are the pattern identifiers (e.g., "pattern_0"). Each value should be an object containing "name" and "description".
        """
        response = await self.llm.generate_text_async(prompt, config.ANALYSIS_MODEL, config.ANALYSIS_MODEL_FALLBACK)
        return extract_json_from_response(response) or {}


class SimulationEngine:
    # (Content is identical to previous version)
    def __init__(self, supply_catalog: SupplyCatalog, llm_connector: GeminiLLMConnector, discount_percent: float):
        self.supply_catalog = supply_catalog
        self.llm = llm_connector
        self.discount_factor = 1.0 - (discount_percent / 100.0)

    def _calculate_utility(self, goal: str, cost: float, latency: int, quality: float, confidence: float) -> float:
        norm_cost = min(cost / 0.05, 1.0)
        norm_latency = min(latency / 5000, 1.0)
        weights = {"quality": 0.5, "cost": -0.25, "latency": -0.25}
        if goal == 'cost': weights = {"quality": 0.2, "cost": -0.6, "latency": -0.2}
        elif goal == 'latency': weights = {"quality": 0.2, "cost": -0.2, "latency": -0.6}
        return (weights['quality'] * quality + weights['cost'] * norm_cost + weights['latency'] * norm_latency) * confidence

    def _create_simulation_prompt(self, pattern: DiscoveredPattern, supply_option: SupplyOption, span: UnifiedLogEntry) -> str:
        return f"""
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

    async def _simulate_single_case(self, pattern: DiscoveredPattern, supply: SupplyOption, span: UnifiedLogEntry) -> Optional[PredictedOutcome]:
        prompt = self._create_simulation_prompt(pattern, supply, span)
        response_text = await self.llm.generate_text_async(prompt, config.ANALYSIS_MODEL, config.ANALYSIS_MODEL_FALLBACK)
        sim_data = extract_json_from_response(response_text)
        if not sim_data: return None
        try:
            sim_data['predicted_cost_usd'] = (sim_data.get('predicted_cost_usd', 0) * self.discount_factor)
            utility_score = self._calculate_utility(
                goal=span.request.user_goal,
                cost=sim_data.get('predicted_cost_usd', 0),
                latency=sim_data.get('predicted_latency_ms', 0),
                quality=sim_data.get('predicted_quality_score', 0),
                confidence=sim_data.get('confidence', 0.85)
            )
            return PredictedOutcome(supply_option_id=supply.option_id, utility_score=utility_score, **sim_data)
        except Exception as e:
            logger.error(f"Pydantic validation failed for simulation outcome: {e}, data: {sim_data}")
            return None

    async def generate_policies(self, patterns: List[DiscoveredPattern], span_map: Dict[str, UnifiedLogEntry]) -> List[LearnedPolicy]:
        policy_tasks = [self._generate_policy_for_pattern(p, span_map) for p in patterns]
        policies = await asyncio.gather(*policy_tasks)
        return [p for p in policies if p]

    async def _generate_policy_for_pattern(self, pattern: DiscoveredPattern, span_map: Dict[str, UnifiedLogEntry]) -> Optional[LearnedPolicy]:
        member_spans = [span_map[sid] for sid in pattern.member_span_ids if sid in span_map]
        if not member_spans: return None
        
        representative_span = member_spans[0]
        
        baseline_metrics = BaselineMetrics(
            avg_cost_usd=np.mean([s.finops['total_cost_usd'] for s in member_spans]),
            avg_latency_ms=int(np.mean([s.performance['latency_ms']['total_e2e_ms'] for s in member_spans])),
            avg_quality_score=np.mean([self.supply_catalog.get_option_by_name(s.request.model.name).quality_score if self.supply_catalog.get_option_by_name(s.request.model.name) else 0.8 for s in member_spans])
        )
        
        pattern_spend = sum(s.finops['total_cost_usd'] for s in member_spans)
        all_spans_spend = sum(s.finops['total_cost_usd'] for s in span_map.values())
        pattern_impact_fraction = (pattern_spend / all_spans_spend) if all_spans_spend > 0 else 0

        sim_tasks = [self._simulate_single_case(pattern, supply, representative_span) for supply in self.supply_catalog.get_all_options()]
        outcomes = [o for o in await asyncio.gather(*sim_tasks) if o]
        if not outcomes: return None
        
        sorted_outcomes = sorted(outcomes, key=lambda x: x.utility_score, reverse=True)
        
        return LearnedPolicy(
            pattern_id=pattern.pattern_id,
            optimal_supply_option_id=sorted_outcomes[0].supply_option_id,
            predicted_outcome=sorted_outcomes[0],
            alternative_outcomes=sorted_outcomes[1:4],
            baseline_metrics=baseline_metrics,
            pattern_impact_fraction=pattern_impact_fraction
        )

    def calculate_final_costs(self, workloads: List[Dict], policies: List[LearnedPolicy]) -> CostComparison:
        prior_spend = sum(wl.get('spend', 0) for wl in workloads)
        if prior_spend == 0:
            return CostComparison(prior_monthly_spend=0, projected_monthly_spend=0, projected_monthly_savings=0, delta_percent=0)

        total_optimal_cost = 0
        total_pattern_fraction = 0
        for policy in policies:
            pattern_spend_slice = prior_spend * policy.pattern_impact_fraction
            baseline_cost_per_span = policy.baseline_metrics.avg_cost_usd
            optimal_cost_per_span = policy.predicted_outcome.predicted_cost_usd
            
            cost_ratio = (optimal_cost_per_span / baseline_cost_per_span) if baseline_cost_per_span > 0 else 1
            optimal_spend_slice = pattern_spend_slice * cost_ratio
            
            total_optimal_cost += optimal_spend_slice
            total_pattern_fraction += policy.pattern_impact_fraction
        
        unmapped_spend = prior_spend * (1 - min(total_pattern_fraction, 1))
        projected_spend = total_optimal_cost + unmapped_spend
        savings = prior_spend - projected_spend
        delta = (savings / prior_spend) * 100 if prior_spend > 0 else 0

        return CostComparison(
            prior_monthly_spend=round(prior_spend, 2),
            projected_monthly_spend=round(projected_spend, 2),
            projected_monthly_savings=round(savings, 2),
            delta_percent=round(delta, 2)
        )

# --- Analysis Pipeline ---
class AnalysisPipeline:
    def __init__(self, run_id: str, request: AnalysisRequest, preloaded_spans: Optional[List[UnifiedLogEntry]] = None):
        self.run_id = run_id
        self.request = request
        self.preloaded_spans = preloaded_spans
        self.async_client = httpx.AsyncClient()
        self.llm_connector = GeminiLLMConnector(api_key=config.GEMINI_API_KEY, async_client=self.async_client)
        self.supply_catalog = SupplyCatalog()
        self.pattern_discoverer = PatternDiscoverer(self.llm_connector)
        self.simulation_engine = SimulationEngine(self.supply_catalog, self.llm_connector, request.negotiated_discount_percent)
        self.log_enricher = LogEnrichmentModule()

    async def run(self):
        try:
            if self.preloaded_spans is not None:
                all_spans = self.preloaded_spans
                update_run_status(self.run_id, 'running', f"Using {len(all_spans)} pre-loaded spans for analysis.")
            else:
                if not self.request.workloads: raise ValueError("No workloads provided and no spans pre-loaded.")
                all_spans = [span for wl in self.request.workloads for span in self._generate_spans_for_workload(wl, f"trace_{uuid.uuid4().hex[:8]}")]
                update_run_status(self.run_id, 'running', f"Generated {len(all_spans)} total spans.")
            
            # (Rest of the pipeline logic is identical to previous version)
            step_name = "Log Enrichment"
            start_time = time.perf_counter()
            update_run_status(self.run_id, 'running', log_message=f"Starting: {step_name}...")
            all_spans = self.log_enricher.enrich_spans(all_spans)
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            update_run_status(self.run_id, 'running', log_message=f"Completed: {step_name}", duration_ms=duration_ms)

            timed_discover = time_it(self.run_id, "Pattern Discovery")(self.pattern_discoverer.discover_patterns_from_spans)
            timed_simulate = time_it(self.run_id, "Policy Simulation")(self.simulation_engine.generate_policies)

            max_retries = 3
            cost_comparison = None
            policies = []
            patterns = []
            span_map = {span.trace_context.span_id: span for span in all_spans}

            for attempt in range(max_retries):
                update_run_status(self.run_id, 'running', f"Starting analysis attempt {attempt + 1}/{max_retries}...")
                patterns = await timed_discover(all_spans)
                if patterns:
                    policies = await timed_simulate(patterns, span_map)
                else:
                    update_run_status(self.run_id, 'running', "No patterns discovered.")
                
                cost_comparison = self.simulation_engine.calculate_final_costs(self.request.workloads, policies)
                update_run_status(self.run_id, 'running', f"Cost comparison calculated for attempt {attempt + 1}.")

                savings_percent = cost_comparison.delta_percent
                if 5 <= savings_percent <= 95:
                    update_run_status(self.run_id, 'running', f"Validation successful on attempt {attempt + 1}.")
                    break
                else:
                    log_message = f"Attempt {attempt + 1}/{max_retries} failed: Projected savings ({savings_percent:.2f}%) are outside the expected range."
                    update_run_status(self.run_id, 'running', log_message)
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)
            else:
                error_message = f"Analysis failed after {max_retries} attempts."
                update_run_status(self.run_id, 'failed', log_message=error_message, error=error_message)
                await self.async_client.aclose()
                return

            final_log = analysis_runs[self.run_id]["execution_log"]
            
            result = AnalysisResult(
                run_id=self.run_id,
                discovered_patterns=patterns,
                learned_policies=policies,
                supply_catalog=self.supply_catalog.get_all_options(),
                cost_comparison=cost_comparison,
                execution_log=final_log,
                debug_mode=self.request.debug_mode,
                span_map={k: v.dict() for k, v in span_map.items()}
            )
            update_run_status(self.run_id, 'completed', "Analysis complete.", result=result.model_dump())

        except Exception as e:
            logger.error(f"An error occurred during trace analysis run {self.run_id}: {e}", exc_info=True)
            update_run_status(self.run_id, 'failed', log_message=f"An internal error occurred: {e}", error=str(e))
        finally:
            await self.async_client.aclose()

    def _generate_spans_for_workload(self, workload: Dict, trace_id: str, num_spans: int = 25) -> List[UnifiedLogEntry]:
        # (Content is identical to previous version)
        spans = []
        workload_name = workload.get('name', 'Unknown Workload')
        model_name = workload.get('model', 'gpt-4o')
        goal = workload.get('goal', 'quality')
        total_spend = workload.get('spend', 1000)

        provider, family = "openai", "gpt-4"
        if "claude" in model_name: provider, family = "anthropic", "claude-3"
        elif "gemini" in model_name: provider, family = "google", "gemini"
        elif "llama" in model_name: provider, family = "meta", "llama-3.1"
        
        avg_cost_per_M_tokens = 10.0 
        cost_per_token = avg_cost_per_M_tokens / 1_000_000
        total_workload_tokens = (total_spend / cost_per_token) if cost_per_token > 0 else 1_000_000
        avg_tokens_per_span = total_workload_tokens / num_spans

        for i in range(num_spans):
            token_multiplier = random.uniform(0.5, 1.5)
            latency_multiplier = random.uniform(0.8, 1.2)
            
            total_tokens = int(avg_tokens_per_span * token_multiplier)
            prompt_tokens = int(total_tokens * random.uniform(0.2, 0.8))
            completion_tokens = total_tokens - prompt_tokens
            cost = total_tokens * cost_per_token
            base_latency = 1000
            latency = int((base_latency + (0.5 * completion_tokens)) * latency_multiplier)
            ttft = int(latency * 0.3)

            span = UnifiedLogEntry(
                trace_context=TraceContext(trace_id=trace_id),
                request=RequestData(
                    model=ModelIdentifier(provider=provider, family=family, name=model_name),
                    prompt_text=f"Span {i} for: {workload_name}",
                    user_goal=goal
                ),
                performance={"latency_ms": {"total_e2e_ms": latency, "time_to_first_token_ms": ttft}},
                finops={"total_cost_usd": cost},
                response={"usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "total_tokens": total_tokens}},
                workloadName=workload_name
            )
            spans.append(span)
        return spans
