"""
Advanced Generation Methods - Delegation methods for advanced generation patterns
"""

import uuid
import random
from datetime import datetime, UTC
from typing import Dict, List


class AdvancedGenerationMethods:
    """Advanced generation methods delegation class"""

    def __init__(self, patterns_helper, tool_helper):
        self.patterns_helper = patterns_helper
        self.tool_helper = tool_helper

    async def generate_trace_hierarchies(self, cnt: int, min_d: int, max_d: int) -> List[Dict]:
        """Generate trace hierarchies"""
        return await self.patterns_helper.generate_trace_hierarchies(cnt, min_d, max_d)

    async def generate_with_distribution(self, config) -> List[Dict]:
        """Generate with specific distributions"""
        return await self.patterns_helper.generate_with_distribution(config)

    async def generate_with_custom_tools(self, config) -> List[Dict]:
        """Generate with custom tool catalog"""
        return await self.patterns_helper.generate_with_custom_tools(config)

    async def generate_from_corpus(self, config, corpus_content: List[Dict]) -> List[Dict]:
        """Generate data from corpus content"""
        num_traces = getattr(config, 'num_traces', 5)
        records = []
        
        for i in range(num_traces):
            base_record = self._select_corpus_record(corpus_content)
            record = self._build_corpus_record(i, base_record)
            records.append(record)
        
        return records

    def _select_corpus_record(self, corpus_content: List[Dict]) -> Dict:
        """Select corpus record for generation"""
        return random.choice(corpus_content) if corpus_content else {"prompt": "test", "response": "test"}

    def _build_corpus_record(self, index: int, base_record: Dict) -> Dict:
        """Build record from corpus content"""
        return {
            "index": index,
            "timestamp": datetime.now(UTC).isoformat(),
            "trace_id": str(uuid.uuid4()),
            "corpus_data": base_record
        }

    async def generate_with_temporal_patterns(self, config) -> List[Dict]:
        """Generate with temporal patterns"""
        return await self.patterns_helper.generate_with_temporal_patterns(config)

    async def generate_with_errors(self, config) -> List[Dict]:
        """Generate with error scenarios"""
        return await self.patterns_helper.generate_with_errors(config)

    async def generate_domain_specific(self, config) -> List[Dict]:
        """Generate domain-specific data"""
        return await self.patterns_helper.generate_domain_specific(config)

    async def generate_tool_invocations(self, count: int, pattern: str) -> List[Dict]:
        """Generate tool invocations for testing"""
        return await self.tool_helper.generate_tool_invocations(count, pattern)