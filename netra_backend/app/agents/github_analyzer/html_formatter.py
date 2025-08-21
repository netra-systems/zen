"""HTML Formatter Module.

Formats AI operations maps into HTML output.
Handles HTML template generation and metrics formatting.
"""

from typing import Dict, Any

from netra_backend.app.logging_config import central_logger as logger


class HTMLFormatter:
    """Formats AI operations maps as HTML."""
    
    def format_html(self, ai_map: Dict[str, Any]) -> str:
        """Format output as HTML."""
        repo_url = ai_map['repository_info']['url']
        metrics_html = self._build_metrics_html(ai_map["metrics"])
        html_template = self._get_html_template()
        return html_template.format(
            repo_url=repo_url,
            metrics_html=metrics_html
        )
    
    def _build_metrics_html(self, metrics: Dict[str, Any]) -> str:
        """Build HTML for metrics section."""
        return ''.join(
            f"<li>{k}: {v}</li>" 
            for k, v in metrics.items()
        )
    
    def _get_html_template(self) -> str:
        """Get HTML template string."""
        return """
        <html>
        <head><title>AI Operations Report</title></head>
        <body>
            <h1>AI Operations Analysis</h1>
            <p>Repository: {repo_url}</p>
            <h2>Metrics</h2>
            <ul>{metrics_html}</ul>
        </body>
        </html>
        """