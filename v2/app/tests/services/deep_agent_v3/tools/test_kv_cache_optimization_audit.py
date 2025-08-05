
import asyncio
from app.services.deep_agent_v3.tools.kv_cache_optimization_audit import KVCacheOptimizationAuditTool

def test_kv_cache_optimization_audit_tool():
    """Tests the KVCacheOptimizationAuditTool."""
    tool = KVCacheOptimizationAuditTool()
    result = asyncio.run(tool.run(cache_name="test_cache"))
    
    assert "The KV cache audit is complete" in result["message"]
