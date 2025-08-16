"""Output Formatter Module.

Formats analysis results into structured AI operations map.
Supports multiple output formats (JSON, Markdown, HTML).
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from app.logging_config import central_logger as logger


class AIOperationsMapFormatter:
    """Formats AI analysis results into structured maps."""
    
    def __init__(self):
        """Initialize formatter configuration."""
        self.output_formats = ["json", "markdown", "html"]
        self.default_format = "json"
    
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
        ai_map = self._build_ai_map(
            repo_url, patterns, configurations, 
            llm_mappings, tool_mappings, analyzed_at
        )
        ai_map["metrics"] = self._calculate_metrics(ai_map)
        ai_map["recommendations"] = self._generate_recommendations(ai_map)
        self._add_formatted_output(ai_map, output_format)
        return ai_map
    
    def _add_formatted_output(
        self, 
        ai_map: Dict[str, Any], 
        output_format: str
    ) -> None:
        """Add formatted output based on requested format."""
        if output_format == "markdown":
            ai_map["formatted_output"] = self._format_markdown(ai_map)
        elif output_format == "html":
            ai_map["formatted_output"] = self._format_html(ai_map)
    
    def _build_ai_map(
        self,
        repo_url: str,
        patterns: Dict[str, Any],
        configurations: Dict[str, Any],
        llm_mappings: Dict[str, Any],
        tool_mappings: Dict[str, Any],
        analyzed_at: datetime
    ) -> Dict[str, Any]:
        """Build complete AI operations map."""
        return {
            "repository_info": self._build_repo_info(repo_url, analyzed_at),
            "ai_infrastructure": self._build_ai_infrastructure(
                patterns, llm_mappings, tool_mappings, configurations
            ),
            "code_locations": self._build_code_locations(
                patterns, configurations, llm_mappings
            ),
            "security": self._analyze_security(configurations),
            "dependencies": self._extract_dependencies(patterns, configurations)
        }
    
    def _build_repo_info(self, repo_url: str, analyzed_at: datetime) -> Dict[str, str]:
        """Build repository information section."""
        return {
            "url": repo_url,
            "analyzed_at": analyzed_at.isoformat(),
            "analysis_version": "1.0.0"
        }
    
    def _build_ai_infrastructure(
        self,
        patterns: Dict[str, Any],
        llm_mappings: Dict[str, Any],
        tool_mappings: Dict[str, Any],
        configurations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build AI infrastructure section."""
        return {
            "providers": patterns.get("detected_providers", []),
            "llm_endpoints": llm_mappings.get("endpoints", []),
            "models": self._format_models(llm_mappings),
            "agents": self._extract_agents(patterns, tool_mappings),
            "tools": tool_mappings.get("tools", []),
            "functions": tool_mappings.get("functions", []),
            "configurations": self._format_configs(configurations),
            "patterns": self._summarize_patterns(patterns)
        }
    
    def _build_code_locations(
        self,
        patterns: Dict[str, Any],
        configurations: Dict[str, Any],
        llm_mappings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build code locations section."""
        return {
            "ai_files": self._get_ai_files(patterns),
            "config_files": self._get_config_files(configurations),
            "hotspots": self._identify_hotspots(patterns, llm_mappings)
        }
    
    def _format_models(self, llm_mappings: Dict[str, Any]) -> Dict[str, Any]:
        """Format model information."""
        models = llm_mappings.get("models", {})
        summary = llm_mappings.get("summary", {})
        
        return {
            "used_models": list(models.keys()),
            "model_counts": models,
            "most_used": summary.get("most_used_model"),
            "parameter_ranges": summary.get("parameter_stats", {})
        }
    
    def _extract_agents(
        self, 
        patterns: Dict[str, Any],
        tool_mappings: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract agent information."""
        agents = []
        for location in patterns.get("pattern_locations", []):
            location_agents = self._extract_location_agents(location)
            agents.extend(location_agents)
        return agents
    
    def _extract_location_agents(self, location: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract agents from a single location."""
        agents = []
        for pattern in location["patterns"]:
            if pattern.get("category") == "agents":
                agent_info = self._build_agent_info(location, pattern)
                agents.append(agent_info)
        return agents
    
    def _build_agent_info(
        self, 
        location: Dict[str, Any], 
        pattern: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build agent information dictionary."""
        return {
            "file": location["file"],
            "line": pattern.get("line"),
            "type": pattern.get("provider"),
            "pattern": pattern.get("content", "")[:100]
        }
    
    def _format_configs(self, configurations: Dict[str, Any]) -> Dict[str, Any]:
        """Format configuration information."""
        config_files = self._format_config_files(configurations)
        detected_providers = self._get_detected_providers(configurations)
        return {
            "environment_variables": configurations.get("env_variables", {}),
            "config_files": config_files,
            "detected_providers": detected_providers
        }
    
    def _format_config_files(self, configurations: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format configuration files list."""
        return [
            {
                "file": cf["file"],
                "ai_configs": len(cf.get("configs", {}))
            }
            for cf in configurations.get("config_files", [])
        ]
    
    def _get_detected_providers(self, configurations: Dict[str, Any]) -> List[str]:
        """Get detected providers from configurations."""
        return configurations.get("summary", {}).get("detected_providers", [])
    
    def _summarize_patterns(self, patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize detected patterns."""
        summary = patterns.get("summary", {})
        pattern_counts = summary.get("pattern_counts", {})
        total_patterns = sum(pattern_counts.values())
        return {
            "total_patterns": total_patterns,
            "by_provider": pattern_counts,
            "complexity": summary.get("complexity", "unknown")
        }
    
    def _get_ai_files(self, patterns: Dict[str, Any]) -> List[str]:
        """Get list of files with AI code."""
        files = set()
        
        for location in patterns.get("pattern_locations", []):
            files.add(location["file"])
        
        return sorted(list(files))
    
    def _get_config_files(self, configurations: Dict[str, Any]) -> List[str]:
        """Get list of configuration files."""
        return [
            cf["file"] 
            for cf in configurations.get("config_files", [])
        ]
    
    def _identify_hotspots(
        self, 
        patterns: Dict[str, Any],
        llm_mappings: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify AI hotspots in code."""
        file_counts = self._count_patterns_per_file(patterns)
        hotspots = self._get_top_hotspots(file_counts)
        return self._format_hotspots(hotspots)
    
    def _count_patterns_per_file(self, patterns: Dict[str, Any]) -> Dict[str, int]:
        """Count patterns per file."""
        file_counts = {}
        for location in patterns.get("pattern_locations", []):
            file_path = location["file"]
            pattern_count = len(location["patterns"])
            file_counts[file_path] = file_counts.get(file_path, 0) + pattern_count
        return file_counts
    
    def _get_top_hotspots(self, file_counts: Dict[str, int]) -> List[tuple]:
        """Get top 10 hotspots by pattern count."""
        return sorted(
            file_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
    
    def _format_hotspots(self, hotspots: List[tuple]) -> List[Dict[str, Any]]:
        """Format hotspots as dictionaries."""
        return [
            {"file": file, "ai_operations": count}
            for file, count in hotspots
        ]
    
    def _analyze_security(self, configurations: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze security aspects."""
        security = {
            "exposed_keys": [],
            "warnings": [],
            "recommendations": []
        }
        self._check_exposed_credentials(security, configurations)
        self._add_security_recommendations(security)
        return security
    
    def _check_exposed_credentials(
        self, 
        security: Dict[str, Any], 
        configurations: Dict[str, Any]
    ) -> None:
        """Check for exposed API credentials."""
        env_vars = configurations.get("env_variables", {})
        for key, values in env_vars.items():
            if self._is_credential_key(key):
                for value_info in values:
                    if not value_info["value"].startswith("****"):
                        security["warnings"].append(
                            f"Potential exposed credential: {key}"
                        )
    
    def _is_credential_key(self, key: str) -> bool:
        """Check if key represents a credential."""
        return "KEY" in key or "TOKEN" in key
    
    def _add_security_recommendations(self, security: Dict[str, Any]) -> None:
        """Add security recommendations if warnings exist."""
        if security["warnings"]:
            security["recommendations"].append(
                "Use environment variables or secret management service"
            )
    
    def _extract_dependencies(
        self, 
        patterns: Dict[str, Any],
        configurations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract AI-related dependencies."""
        providers = set(patterns.get("detected_providers", []))
        return {
            "detected_libraries": self._get_detected_libraries(providers),
            "providers": list(providers),
            "frameworks": self._get_detected_frameworks(providers)
        }
    
    def _get_detected_libraries(self, providers: set) -> List[str]:
        """Get detected AI libraries."""
        libraries = []
        if "openai" in providers:
            libraries.append("openai")
        if "anthropic" in providers:
            libraries.append("anthropic")
        return libraries
    
    def _get_detected_frameworks(self, providers: set) -> List[str]:
        """Get detected AI frameworks."""
        frameworks = []
        if "langchain" in providers:
            frameworks.append("langchain")
        return frameworks
    
    def _calculate_metrics(self, ai_map: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate analysis metrics."""
        infra = ai_map["ai_infrastructure"]
        code_locations = ai_map["code_locations"]
        return {
            "total_llm_calls": len(infra.get("llm_endpoints", [])),
            "unique_models": len(infra.get("models", {}).get("used_models", [])),
            "agent_count": len(infra.get("agents", [])),
            "tool_count": self._calculate_tool_count(infra),
            "config_files": len(code_locations.get("config_files", [])),
            "ai_files": len(code_locations.get("ai_files", [])),
            "estimated_complexity": infra.get("patterns", {}).get("complexity", "unknown")
        }
    
    def _calculate_tool_count(self, infra: Dict[str, Any]) -> int:
        """Calculate total tool count."""
        tools = len(infra.get("tools", []))
        functions = len(infra.get("functions", []))
        return tools + functions
    
    def _generate_recommendations(self, ai_map: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        metrics = ai_map.get("metrics", {})
        security = ai_map.get("security", {})
        
        self._add_complexity_recommendations(recommendations, metrics)
        self._add_model_recommendations(recommendations, metrics)
        self._add_security_recommendations_to_list(recommendations, security)
        self._add_tool_recommendations(recommendations, metrics)
        return recommendations
    
    def _add_complexity_recommendations(
        self, 
        recommendations: List[str], 
        metrics: Dict[str, Any]
    ) -> None:
        """Add complexity-based recommendations."""
        if metrics.get("estimated_complexity") == "high":
            recommendations.append(
                "Consider modularizing AI operations for better maintainability"
            )
    
    def _add_model_recommendations(
        self, 
        recommendations: List[str], 
        metrics: Dict[str, Any]
    ) -> None:
        """Add model diversity recommendations."""
        if metrics.get("unique_models", 0) > 3:
            recommendations.append(
                "Standardize on fewer models to reduce complexity"
            )
    
    def _add_security_recommendations_to_list(
        self, 
        recommendations: List[str], 
        security: Dict[str, Any]
    ) -> None:
        """Add security recommendations."""
        if security.get("warnings"):
            recommendations.append(
                "Review and secure exposed API credentials"
            )
    
    def _add_tool_recommendations(
        self, 
        recommendations: List[str], 
        metrics: Dict[str, Any]
    ) -> None:
        """Add tool-related recommendations."""
        if metrics.get("tool_count", 0) > 10:
            recommendations.append(
                "Consider consolidating tools to reduce overhead"
            )
    
    def _format_markdown(self, ai_map: Dict[str, Any]) -> str:
        """Format output as Markdown."""
        md = []
        self._add_markdown_header(md, ai_map)
        self._add_markdown_metrics(md, ai_map)
        self._add_markdown_providers(md, ai_map)
        self._add_markdown_recommendations(md, ai_map)
        return "".join(md)
    
    def _add_markdown_header(self, md: List[str], ai_map: Dict[str, Any]) -> None:
        """Add markdown header section."""
        repo_info = ai_map['repository_info']
        md.append("# AI Operations Analysis Report\n")
        md.append(f"**Repository**: {repo_info['url']}\n")
        md.append(f"**Analyzed**: {repo_info['analyzed_at']}\n")
    
    def _add_markdown_metrics(self, md: List[str], ai_map: Dict[str, Any]) -> None:
        """Add metrics section to markdown."""
        md.append("\n## Metrics\n")
        for key, value in ai_map["metrics"].items():
            md.append(f"- **{key}**: {value}\n")
    
    def _add_markdown_providers(self, md: List[str], ai_map: Dict[str, Any]) -> None:
        """Add providers section to markdown."""
        md.append("\n## AI Providers\n")
        for provider in ai_map["ai_infrastructure"]["providers"]:
            md.append(f"- {provider}\n")
    
    def _add_markdown_recommendations(self, md: List[str], ai_map: Dict[str, Any]) -> None:
        """Add recommendations section to markdown."""
        if ai_map["recommendations"]:
            md.append("\n## Recommendations\n")
            for rec in ai_map["recommendations"]:
                md.append(f"- {rec}\n")
    
    def _format_html(self, ai_map: Dict[str, Any]) -> str:
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