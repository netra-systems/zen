from langchain_core.tools import tool
from typing import Any, List
from pydantic import BaseModel, Field

class RawLog(BaseModel):
    response: Any = Field(..., description="The response from the LLM.")
    performance: Any = Field(..., description="The performance metrics for the LLM call.")
    trace_context: Any = Field(..., description="The trace context for the LLM call.")

@tool
async def log_enricher_and_clusterer(raw_logs: List[RawLog], db_session: Any, llm_manager: Any, log_pattern_identifier: any) -> str:
    """Enriches logs and applies KMeans clustering."""
    if not raw_logs:
        return "No logs to enrich and cluster."

    # Enrichment
    for span in raw_logs:
        usage = span.response.usage
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = prompt_tokens + completion_tokens
        latency_ms = span.performance.latency_ms['total_e2e_ms']
        ttft_ms = span.performance.latency_ms['time_to_first_token_ms']
        
        inter_token_latency = None
        if completion_tokens > 1 and latency_ms > ttft_ms:
            inter_token_latency = (latency_ms - ttft_ms) / (completion_tokens - 1)
        
        span.enriched_metrics = {
            "prefill_ratio": prompt_tokens / max(total_tokens, 1),
            "generation_ratio": completion_tokens / max(total_tokens, 1),
            "throughput_tokens_per_sec": total_tokens / max(latency_ms / 1000, 0.001),
            "inter_token_latency_ms": inter_token_latency
        }

    enriched_spans_data = [{'span_id': s.trace_context.span_id, **s.enriched_metrics} for s in raw_logs if hasattr(s, 'enriched_metrics')]
    if not enriched_spans_data:
        return "No enriched spans to cluster."

    patterns, descriptions = await log_pattern_identifier.identify_patterns(enriched_spans_data)

    return f"Successfully discovered {len(patterns)} patterns."