
from typing import Dict, Any

KV_CACHING_AUDIT: Dict[str, Any] = {
    "name": "KV Caching Audit",
    "description": "Audits all uses of KV caching in the system to find optimization opportunities.",
    "steps": [
        "identify_all_kv_caches",
        "analyze_cache_hit_rates",
        "identify_inefficient_cache_usage",
        "propose_optimizations",
        "generate_report"
    ]
}
