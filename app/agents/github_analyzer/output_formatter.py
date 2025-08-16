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
        # Build the complete map
        ai_map = self._build_ai_map(
            repo_url,
            patterns,
            configurations,
            llm_mappings,
            tool_mappings,
            analyzed_at
        )
        
        # Add metrics
        ai_map["metrics"] = self._calculate_metrics(ai_map)
        
        # Add recommendations
        ai_map["recommendations"] = self._generate_recommendations(ai_map)
        
        # Format based on requested format
        if output_format == "markdown":
            ai_map["formatted_output"] = self._format_markdown(ai_map)
        elif output_format == "html":
            ai_map["formatted_output"] = self._format_html(ai_map)
        
        return ai_map
    
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
            "repository_info": {
                "url": repo_url,
                "analyzed_at": analyzed_at.isoformat(),
                "analysis_version": "1.0.0"
            },
            "ai_infrastructure": {
                "providers": patterns.get("detected_providers", []),
                "llm_endpoints": llm_mappings.get("endpoints", []),
                "models": self._format_models(llm_mappings),
                "agents": self._extract_agents(patterns, tool_mappings),
                "tools": tool_mappings.get("tools", []),
                "functions": tool_mappings.get("functions", []),
                "configurations": self._format_configs(configurations),
                "patterns": self._summarize_patterns(patterns)
            },
            "code_locations": {
                "ai_files": self._get_ai_files(patterns),
                "config_files": self._get_config_files(configurations),
                "hotspots": self._identify_hotspots(patterns, llm_mappings)
            },
            "security": self._analyze_security(configurations),
            "dependencies": self._extract_dependencies(patterns, configurations)
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
        
        # Find agent patterns
        for location in patterns.get("pattern_locations", []):
            for pattern in location["patterns"]:
                if pattern.get("category") == "agents":
                    agents.append({
                        "file": location["file"],
                        "line": pattern.get("line"),
                        "type": pattern.get("provider"),
                        "pattern": pattern.get("content", "")[:100]
                    })
        
        return agents
    
    def _format_configs(self, configurations: Dict[str, Any]) -> Dict[str, Any]:
        """Format configuration information."""
        return {
            "environment_variables": configurations.get("env_variables", {}),
            "config_files": [
                {
                    "file": cf["file"],
                    "ai_configs": len(cf.get("configs", {}))
                }
                for cf in configurations.get("config_files", [])
            ],
            "detected_providers": configurations.get("summary", {}).get(
                "detected_providers", []
            )
        }
    
    def _summarize_patterns(self, patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize detected patterns."""
        summary = patterns.get("summary", {})
        
        return {
            "total_patterns": sum(
                summary.get("pattern_counts", {}).values()
            ),
            "by_provider": summary.get("pattern_counts", {}),
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
        file_counts = {}
        
        # Count patterns per file
        for location in patterns.get("pattern_locations", []):
            file_path = location["file"]
            pattern_count = len(location["patterns"])
            file_counts[file_path] = file_counts.get(file_path, 0) + pattern_count
        
        # Sort by count and return top files
        hotspots = sorted(
            file_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
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
        
        # Check for exposed API keys
        for key, values in configurations.get("env_variables", {}).items():
            if "KEY" in key or "TOKEN" in key:
                for value_info in values:
                    if not value_info["value"].startswith("****"):
                        security["warnings"].append(
                            f"Potential exposed credential: {key}"
                        )
        
        # Add recommendations
        if security["warnings"]:
            security["recommendations"].append(
                "Use environment variables or secret management service"
            )
        
        return security
    
    def _extract_dependencies(
        self, 
        patterns: Dict[str, Any],
        configurations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract AI-related dependencies."""
        dependencies = {
            "detected_libraries": [],
            "providers": patterns.get("detected_providers", []),
            "frameworks": []
        }
        
        # Check for known libraries
        providers = set(patterns.get("detected_providers", []))
        
        if "openai" in providers:
            dependencies["detected_libraries"].append("openai")
        if "anthropic" in providers:
            dependencies["detected_libraries"].append("anthropic")
        if "langchain" in providers:
            dependencies["frameworks"].append("langchain")
        
        return dependencies
    
    def _calculate_metrics(self, ai_map: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate analysis metrics."""
        infra = ai_map["ai_infrastructure"]
        
        return {
            "total_llm_calls": len(infra.get("llm_endpoints", [])),
            "unique_models": len(infra.get("models", {}).get("used_models", [])),
            "agent_count": len(infra.get("agents", [])),
            "tool_count": len(infra.get("tools", [])) + len(infra.get("functions", [])),
            "config_files": len(ai_map["code_locations"].get("config_files", [])),
            "ai_files": len(ai_map["code_locations"].get("ai_files", [])),
            "estimated_complexity": infra.get("patterns", {}).get("complexity", "unknown")
        }
    
    def _generate_recommendations(self, ai_map: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        metrics = ai_map.get("metrics", {})
        
        # Complexity recommendations
        if metrics.get("estimated_complexity") == "high":
            recommendations.append(
                "Consider modularizing AI operations for better maintainability"
            )
        
        # Model diversity
        if metrics.get("unique_models", 0) > 3:
            recommendations.append(
                "Standardize on fewer models to reduce complexity"
            )
        
        # Security recommendations
        security = ai_map.get("security", {})
        if security.get("warnings"):
            recommendations.append(
                "Review and secure exposed API credentials"
            )
        
        # Tool recommendations
        if metrics.get("tool_count", 0) > 10:
            recommendations.append(
                "Consider consolidating tools to reduce overhead"
            )
        
        return recommendations
    
    def _format_markdown(self, ai_map: Dict[str, Any]) -> str:
        """Format output as Markdown."""
        md = []
        md.append("# AI Operations Analysis Report\n")
        md.append(f"**Repository**: {ai_map['repository_info']['url']}\n")
        md.append(f"**Analyzed**: {ai_map['repository_info']['analyzed_at']}\n")
        
        # Metrics
        md.append("\n## Metrics\n")
        for key, value in ai_map["metrics"].items():
            md.append(f"- **{key}**: {value}\n")
        
        # Providers
        md.append("\n## AI Providers\n")
        for provider in ai_map["ai_infrastructure"]["providers"]:
            md.append(f"- {provider}\n")
        
        # Recommendations
        if ai_map["recommendations"]:
            md.append("\n## Recommendations\n")
            for rec in ai_map["recommendations"]:
                md.append(f"- {rec}\n")
        
        return "".join(md)
    
    def _format_html(self, ai_map: Dict[str, Any]) -> str:
        """Format output as HTML."""
        # Simplified HTML output
        html = f"""
        <html>
        <head><title>AI Operations Report</title></head>
        <body>
            <h1>AI Operations Analysis</h1>
            <p>Repository: {ai_map['repository_info']['url']}</p>
            <h2>Metrics</h2>
            <ul>
                {''.join(f"<li>{k}: {v}</li>" for k, v in ai_map["metrics"].items())}
            </ul>
        </body>
        </html>
        """
        return html