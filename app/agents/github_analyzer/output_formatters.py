"""Output Formatters Module.

Main orchestrator for AI operations map formatting.
Coordinates AI map building, metrics calculation, and output formatting.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from app.logging_config import central_logger as logger
from .ai_map_builder import AIMapBuilder
from .metrics_calculator import GitHubAnalyzerMetricsCalculator
from .recommendation_generator import RecommendationGenerator
from .markdown_formatter import MarkdownFormatter
from .html_formatter import HTMLFormatter


class AIOperationsMapFormatter:
    """Main formatter that orchestrates AI operations map creation."""
    
    def __init__(self):
        """Initialize formatter with component dependencies."""
        self.output_formats = ["json", "markdown", "html"]
        self.default_format = "json"
        self.ai_map_builder = AIMapBuilder()
        self.metrics_calculator = GitHubAnalyzerMetricsCalculator()
        self.recommendation_generator = RecommendationGenerator()
        self.markdown_formatter = MarkdownFormatter()
        self.html_formatter = HTMLFormatter()
    
    async def format_output(
        self,
        repo_url: str,
        patterns: Dict[str, Any],
        configurations: Dict[str, Any],
        llm_mappings: Dict[str, Any],
        tool_mappings: Dict[str, Any],
        analyzed_at: datetime,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """Format analysis output into AI operations map."""
        ai_map = self.ai_map_builder.build_ai_map(
            repo_url, patterns, configurations, 
            llm_mappings, tool_mappings, analyzed_at
        )
        ai_map["metrics"] = self.metrics_calculator.calculate_metrics(ai_map)
        ai_map["recommendations"] = self.recommendation_generator.generate_recommendations(ai_map)
        self._add_formatted_output(ai_map, output_format)
        return ai_map
    
    def _add_formatted_output(
        self, 
        ai_map: Dict[str, Any], 
        output_format: str
    ) -> None:
        """Add formatted output based on requested format."""
        if output_format == "markdown":
            ai_map["formatted_output"] = self.markdown_formatter.format_markdown(ai_map)
        elif output_format == "html":
            ai_map["formatted_output"] = self.html_formatter.format_html(ai_map)