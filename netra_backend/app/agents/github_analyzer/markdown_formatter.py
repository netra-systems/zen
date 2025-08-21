"""Markdown Formatter Module.

Formats AI operations maps into Markdown output.
Handles header, metrics, providers, and recommendations sections.
"""

from typing import Dict, List, Any

from app.logging_config import central_logger as logger


class MarkdownFormatter:
    """Formats AI operations maps as Markdown."""
    
    def format_markdown(self, ai_map: Dict[str, Any]) -> str:
        """Format output as Markdown."""
        md = []
        self._add_markdown_header(md, ai_map)
        self._add_markdown_metrics(md, ai_map)
        self._add_markdown_providers(md, ai_map)
        self._add_markdown_recommendations(md, ai_map)
        return "".join(md)
    
    def _add_markdown_header(
        self, 
        md: List[str], 
        ai_map: Dict[str, Any]
    ) -> None:
        """Add markdown header section."""
        repo_info = ai_map['repository_info']
        md.append("# AI Operations Analysis Report\n")
        md.append(f"**Repository**: {repo_info['url']}\n")
        md.append(f"**Analyzed**: {repo_info['analyzed_at']}\n")
    
    def _add_markdown_metrics(
        self, 
        md: List[str], 
        ai_map: Dict[str, Any]
    ) -> None:
        """Add metrics section to markdown."""
        md.append("\n## Metrics\n")
        for key, value in ai_map["metrics"].items():
            md.append(f"- **{key}**: {value}\n")
    
    def _add_markdown_providers(
        self, 
        md: List[str], 
        ai_map: Dict[str, Any]
    ) -> None:
        """Add providers section to markdown."""
        md.append("\n## AI Providers\n")
        for provider in ai_map["ai_infrastructure"]["providers"]:
            md.append(f"- {provider}\n")
    
    def _add_markdown_recommendations(
        self, 
        md: List[str], 
        ai_map: Dict[str, Any]
    ) -> None:
        """Add recommendations section to markdown."""
        if ai_map["recommendations"]:
            md.append("\n## Recommendations\n")
            for rec in ai_map["recommendations"]:
                md.append(f"- {rec}\n")