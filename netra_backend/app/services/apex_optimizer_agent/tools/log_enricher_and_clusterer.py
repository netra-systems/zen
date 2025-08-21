from langchain_core.tools import tool
from typing import Any, List
from pydantic import BaseModel, Field
from netra_backend.app.services.context import ToolContext

class RawLog(BaseModel):
    response: Any = Field(..., description="The response from the LLM.")
    performance: Any = Field(..., description="The performance metrics for the LLM call.")
    trace_context: Any = Field(..., description="The trace context for the LLM call.")

def _validate_input(raw_logs: List[RawLog]) -> str:
    """Validates input logs."""
    if not raw_logs:
        return "No logs to enrich and cluster."
    return ""

def _extract_usage_metrics(usage: Any) -> tuple[int, int, int]:
    """Extracts token usage metrics."""
    prompt_tokens = usage.get('prompt_tokens', 0)
    completion_tokens = usage.get('completion_tokens', 0)
    total_tokens = prompt_tokens + completion_tokens
    return prompt_tokens, completion_tokens, total_tokens

def _extract_timing_metrics(performance: Any) -> tuple[float, float]:
    """Extracts timing metrics."""
    latency_ms = performance.latency_ms['total_e2e_ms']
    ttft_ms = performance.latency_ms['time_to_first_token_ms']
    return latency_ms, ttft_ms

def _calculate_inter_token_latency(latency_ms: float, ttft_ms: float, completion_tokens: int) -> float:
    """Calculates inter-token latency."""
    if completion_tokens > 1 and latency_ms > ttft_ms:
        return (latency_ms - ttft_ms) / (completion_tokens - 1)
    return None

def _build_enriched_metrics(prompt_tokens: int, completion_tokens: int, total_tokens: int, latency_ms: float, inter_token_latency: float) -> dict:
    """Builds enriched metrics dictionary."""
    return {
        "prefill_ratio": prompt_tokens / max(total_tokens, 1),
        "generation_ratio": completion_tokens / max(total_tokens, 1),
        "throughput_tokens_per_sec": total_tokens / max(latency_ms / 1000, 0.001),
        "inter_token_latency_ms": inter_token_latency
    }

def _enrich_single_log(span: RawLog) -> None:
    """Enriches a single log span with metrics."""
    prompt_tokens, completion_tokens, total_tokens = _extract_usage_metrics(span.response.usage)
    latency_ms, ttft_ms = _extract_timing_metrics(span.performance)
    inter_token_latency = _calculate_inter_token_latency(latency_ms, ttft_ms, completion_tokens)
    span.enriched_metrics = _build_enriched_metrics(prompt_tokens, completion_tokens, total_tokens, latency_ms, inter_token_latency)

def _prepare_clustering_data(raw_logs: List[RawLog]) -> List[dict]:
    """Prepares enriched spans data for clustering."""
    return [{'span_id': s.trace_context.span_id, **s.enriched_metrics} for s in raw_logs if hasattr(s, 'enriched_metrics')]

async def _identify_patterns_and_return(context: ToolContext, enriched_spans_data: List[dict]) -> str:
    """Identifies patterns and returns result."""
    if not enriched_spans_data:
        return "No enriched spans to cluster."
    patterns, descriptions = await context.log_pattern_identifier.identify_patterns(enriched_spans_data)
    return f"Successfully discovered {len(patterns)} patterns."

@tool
async def log_enricher_and_clusterer(context: ToolContext, raw_logs: List[RawLog]) -> str:
    """Enriches logs and applies KMeans clustering."""
    validation_result = _validate_input(raw_logs)
    if validation_result:
        return validation_result
    for span in raw_logs:
        _enrich_single_log(span)
    enriched_spans_data = _prepare_clustering_data(raw_logs)
    return await _identify_patterns_and_return(context, enriched_spans_data)