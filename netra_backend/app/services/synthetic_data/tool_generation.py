"""
Tool Generation Utilities - Helper functions for tool invocation generation
"""

import uuid
from typing import List, Dict
from netra_backend.app.tools import generate_tool_invocations


class ToolGenerationHelper:
    """Helper class for tool-related generation tasks"""

    def __init__(self, default_tools: List[Dict]):
        self.default_tools = default_tools

    async def generate_tool_invocations(self, count: int, pattern: str) -> List[Dict]:
        """Generate synthetic tool invocation data"""
        invocations = []
        for i in range(count):
            inv = self._generate_single_tool_set(pattern)
            invocations.extend(self._enhance_tool_invocation(inv, i))
        return invocations

    def _generate_single_tool_set(self, pattern: str) -> List[Dict]:
        """Generate single set of tool invocations"""
        return generate_tool_invocations(pattern, self.default_tools)

    def _enhance_tool_invocation(self, inv: List[Dict], sequence: int) -> List[Dict]:
        """Enhance tool invocations with metadata"""
        enhanced = []
        for j, item in enumerate(inv[:1]):  # Take first for each iteration
            item['sequence_number'] = sequence
            item['trace_id'] = str(uuid.uuid4())
            item['invocation_id'] = str(uuid.uuid4())
            enhanced.append(item)
        return enhanced

    def generate_tool_catalog(self, tool_types: List[str]) -> List[Dict]:
        """Generate tool catalog for configuration"""
        catalog = []
        for tool_type in tool_types:
            tools = [t for t in self.default_tools if t.get('type') == tool_type]
            catalog.extend(tools)
        return catalog

    def validate_tool_pattern(self, pattern: str) -> bool:
        """Validate tool generation pattern"""
        valid_patterns = ['simple', 'complex', 'mixed', 'error_prone', 'high_latency']
        return pattern in valid_patterns

    def get_pattern_description(self, pattern: str) -> str:
        """Get description for tool pattern"""
        descriptions = {
            'simple': 'Basic tools with low complexity',
            'complex': 'Advanced tools with high complexity',
            'mixed': 'Combination of simple and complex tools',
            'error_prone': 'Tools that simulate error conditions',
            'high_latency': 'Tools that simulate high latency scenarios'
        }
        return descriptions.get(pattern, 'Unknown pattern')

    def calculate_tool_metrics(self, invocations: List[Dict]) -> Dict:
        """Calculate metrics for tool invocations"""
        if not invocations:
            return {'total_tools': 0, 'avg_latency': 0, 'unique_tools': 0}

        total_tools = len(invocations)
        unique_tools = len(set(inv.get('name', '') for inv in invocations))
        total_latency = sum(inv.get('latency_ms', 0) for inv in invocations)
        avg_latency = total_latency / total_tools if total_tools > 0 else 0

        return {
            'total_tools': total_tools,
            'unique_tools': unique_tools,
            'avg_latency': avg_latency,
            'total_latency': total_latency
        }