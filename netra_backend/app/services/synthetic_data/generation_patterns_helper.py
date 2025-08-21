"""
Generation Patterns Helper - Advanced pattern generation utilities
"""

import asyncio
from datetime import datetime, UTC
from typing import List, Dict
from netra_backend.app.services.synthetic_data.generation_patterns import (
    generate_with_temporal_patterns as _generate_with_temporal_patterns,
    generate_with_errors as _generate_with_errors,
    generate_domain_specific as _generate_domain_specific
)


class GenerationPatternsHelper:
    """Helper class for advanced generation patterns"""

    async def generate_with_temporal_patterns(self, config) -> List[Dict]:
        """Generate with temporal patterns"""
        async def gen_fn(cfg, _, idx):
            return {"timestamp": datetime.now(UTC).isoformat(), "index": idx}
        return await _generate_with_temporal_patterns(config, gen_fn)

    async def generate_with_errors(self, config) -> List[Dict]:
        """Generate with error scenarios"""
        async def gen_fn(cfg, _, idx):
            return {"timestamp": datetime.now(UTC).isoformat(), "index": idx}
        return await _generate_with_errors(config, gen_fn)

    async def generate_domain_specific(self, config) -> List[Dict]:
        """Generate domain-specific data"""
        async def gen_fn(cfg, _, idx):
            return {"timestamp": datetime.now(UTC).isoformat(), "index": idx}
        return await _generate_domain_specific(config, gen_fn)

    async def generate_with_distribution(self, config) -> List[Dict]:
        """Generate with specific distributions"""
        import numpy as np
        import random
        
        records = []
        num_traces = getattr(config, 'num_traces', 10)
        dist = getattr(config, 'latency_distribution', 'normal')
        
        for i in range(num_traces):
            lat = np.random.normal(100, 20) if dist == 'normal' else random.uniform(50, 150)
            records.append({"latency_ms": max(0, lat), "index": i})
        
        return records

    async def generate_with_custom_tools(self, config) -> List[Dict]:
        """Generate with custom tools"""
        import random
        
        records = []
        num_traces = getattr(config, 'num_traces', 5)
        tools = getattr(config, 'tool_catalog', [])
        
        for i in range(num_traces):
            tool_invocations = self._create_tool_invocations(tools, i)
            records.append({"tool_invocations": tool_invocations, "index": i})
        
        return records

    def _create_tool_invocations(self, tools: List, index: int) -> List[Dict]:
        """Create tool invocations for record"""
        import random
        
        tool_invocations = []
        if tools:
            for tool in tools[:2]:  # Use up to 2 tools per record
                tool_invocations.append({
                    "tool_name": tool.get("name"),
                    "tool_type": tool.get("type"),
                    "latency_ms": random.randint(10, 100)
                })
        return tool_invocations

    async def generate_trace_hierarchies(self, cnt: int, min_d: int, max_d: int) -> List[Dict]:
        """Generate trace hierarchies"""
        import random
        import uuid
        
        traces = []
        for i in range(cnt):
            trace = {"trace_id": str(uuid.uuid4()), "spans": []}
            depth = random.randint(min_d, max_d)
            
            for j in range(depth):
                trace["spans"].append({
                    "span_id": str(uuid.uuid4()),
                    "level": j
                })
            traces.append(trace)
        
        return traces