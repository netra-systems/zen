"""Advanced Generators Module - Advanced generation methods and specialized functionality"""

import random
from typing import Any, Dict, List, Optional, Union

from netra_backend.app.services.synthetic_data.content_generator import generate_content
from netra_backend.app.services.synthetic_data.core_service_base import CoreServiceBase


class AdvancedGenerators(CoreServiceBase):
    """Handles advanced generation methods and specialized functionality"""

    async def get_preview(
        self,
        corpus_id: Optional[str],
        workload_type: str,
        sample_size: int = 10
    ) -> List[Dict]:
        """Generate preview samples"""
        from netra_backend.app import schemas
        config = schemas.LogGenParams(
            num_logs=sample_size,
            corpus_id=corpus_id or "preview"
        )
        return await self.generation_engine.generate_preview(
            config, corpus_id, workload_type, sample_size
        )

    def _generate_content(
        self,
        workload_type: str,
        corpus_content: Optional[List[Dict]]
    ) -> tuple[str, str]:
        """Generate synthetic content using content generator"""
        return generate_content(workload_type, corpus_content)

    async def generate_batch(
        self,
        config: Union[Any, Any],
        batch_size: int = 100
    ) -> List[Dict[str, Any]]:
        """Generate single batch"""
        return await self.generation_engine.generate_batch(config, batch_size)

    async def ingest_batch(
        self,
        records: List[Dict],
        table_name: str = None
    ) -> Dict:
        """Ingest batch to ClickHouse"""
        return await self.ingestion_manager.ingest_batch(records, table_name)

    async def generate_incremental(
        self,
        config,
        checkpoint_callback=None
    ) -> Dict:
        """Generate data incrementally with checkpoints"""
        return await self.generation_engine.generate_incremental(config, checkpoint_callback)

    async def generate_with_temporal_patterns(self, config) -> List[Dict]:
        """Generate with temporal patterns"""
        return await self.generation_engine.generate_with_temporal_patterns(config)

    async def generate_with_errors(self, config) -> List[Dict]:
        """Generate with error scenarios"""
        return await self.generation_engine.generate_with_errors(config)

    async def generate_domain_specific(self, config) -> List[Dict]:
        """Generate domain-specific data"""
        return await self.generation_engine.generate_domain_specific(config)

    async def generate_trace_hierarchies(self, cnt: int, min_d: int, max_d: int) -> List[Dict]:
        """Generate trace hierarchies"""
        return await self.generation_engine.generate_trace_hierarchies(cnt, min_d, max_d)

    async def generate_with_distribution(self, config) -> List[Dict]:
        """Generate with specific distributions"""
        return await self.generation_engine.generate_with_distribution(config)

    async def generate_with_custom_tools(self, config) -> List[Dict]:
        """Generate with custom tool catalog"""
        return await self.generation_engine.generate_with_custom_tools(config)

    async def generate_from_corpus(self, config, corpus_content: List[Dict]) -> List[Dict]:
        """Generate data from corpus content"""
        return await self.generation_engine.generate_from_corpus(config, corpus_content)

    async def generate_tool_invocations(self, count: int, pattern: str) -> List[Dict]:
        """Generate synthetic tool invocation data"""
        return await self.generation_engine.generate_tool_invocations(count, pattern)

    def _select_workload_type(self) -> str:
        """Select random workload type for synthetic data generation"""
        workload_types = [
            "simple_queries", "tool_orchestration", "data_analysis",
            "optimization_workflows", "error_scenarios"
        ]
        return random.choice(workload_types)

    def _select_agent_type(self, workload_type: str) -> str:
        """Select agent type based on workload type"""
        agent_mapping = {
            "simple_queries": "triage",
            "tool_orchestration": "supervisor", 
            "data_analysis": "data_analysis",
            "optimization_workflows": "optimization",
            "error_scenarios": "triage"
        }
        return agent_mapping.get(workload_type, "general")

    def _generate_tool_invocations(self, pattern: str) -> List[Dict]:
        """Generate tool invocations for specific patterns"""
        if pattern == "error_scenarios":
            return [self._create_error_test_tool()]
        return []

    def _create_error_test_tool(self) -> Dict:
        """Create error test tool invocation"""
        return {
            "name": "error_test_tool", "type": "query", "latency_ms": 150,
            "status": "failed", "error": "Simulated error"
        }

    def _create_tool_invocation(self, tool: Dict) -> Dict:
        """Create individual tool invocation from tool definition"""
        latency_ms = self._calculate_tool_latency(tool)
        is_failed = self._determine_tool_failure(tool)
        return self._build_tool_invocation_record(tool, latency_ms, is_failed)

    def _calculate_tool_latency(self, tool: Dict) -> int:
        """Calculate random latency for tool invocation"""
        latency_range = tool.get("latency_ms_range", (50, 200))
        return random.randint(latency_range[0], latency_range[1])

    def _determine_tool_failure(self, tool: Dict) -> bool:
        """Determine if tool invocation should fail based on failure rate"""
        failure_rate = tool.get("failure_rate", 0.0)
        return random.random() < failure_rate

    def _build_tool_invocation_record(self, tool: Dict, latency_ms: int, is_failed: bool) -> Dict:
        """Build complete tool invocation record"""
        return {
            "name": tool["name"], "type": tool["type"], "latency_ms": latency_ms,
            "status": "failed" if is_failed else "success",
            "error": "Tool execution failed" if is_failed else None
        }