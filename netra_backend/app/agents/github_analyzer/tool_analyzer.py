"""Tool Usage Analysis Module.

Analyzes function calling, tool usage, and agent tools.
Maps tool definitions and usage patterns.
"""

from typing import Dict, Any

from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.agents.github_analyzer.tool_patterns import ToolPatternDefinitions
from netra_backend.app.agents.github_analyzer.tool_processing_core import ToolProcessingCore


class ToolUsageAnalyzer:
    """Analyzes tool and function usage in AI systems."""
    
    def __init__(self):
        """Initialize tool analyzer with pattern definitions and processing core."""
        self.pattern_definitions = ToolPatternDefinitions()
        self.processing_core = ToolProcessingCore()
    
    async def analyze_tool_usage(
        self, 
        patterns: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze tool usage from patterns."""
        return self.processing_core.process_tool_patterns(patterns)
    
    def get_tool_patterns(self) -> Dict[str, list]:
        """Get all defined tool patterns."""
        return self.pattern_definitions.get_tool_patterns()
    
    def get_function_patterns(self) -> Dict[str, str]:
        """Get function definition patterns."""
        return self.pattern_definitions.get_function_patterns()