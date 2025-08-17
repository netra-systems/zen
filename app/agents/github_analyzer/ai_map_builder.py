"""AI Map Builder Module.

Builds structured AI operations maps from analysis data.
Handles map construction, agent extraction, and hotspot identification.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from app.logging_config import central_logger as logger


class AIMapBuilder:
    """Builds structured AI operations maps from analysis data."""
    
    def build_ai_map(
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
    
    def _build_repo_info(
        self, 
        repo_url: str, 
        analyzed_at: datetime
    ) -> Dict[str, str]:
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
    
    def _extract_location_agents(
        self, 
        location: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
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
    
    def _format_config_files(
        self, 
        configurations: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Format configuration files list."""
        return [
            {
                "file": cf["file"],
                "ai_configs": len(cf.get("configs", {}))
            }
            for cf in configurations.get("config_files", [])
        ]
    
    def _get_detected_providers(
        self, 
        configurations: Dict[str, Any]
    ) -> List[str]:
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
    
    def _count_patterns_per_file(
        self, 
        patterns: Dict[str, Any]
    ) -> Dict[str, int]:
        """Count patterns per file."""
        file_counts = {}
        for location in patterns.get("pattern_locations", []):
            file_path = location["file"]
            pattern_count = len(location["patterns"])
            file_counts[file_path] = file_counts.get(file_path, 0) + pattern_count
        return file_counts
    
    def _get_top_hotspots(
        self, 
        file_counts: Dict[str, int]
    ) -> List[tuple]:
        """Get top 10 hotspots by pattern count."""
        return sorted(
            file_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
    
    def _format_hotspots(
        self, 
        hotspots: List[tuple]
    ) -> List[Dict[str, Any]]:
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
                self._check_credential_values(security, key, values)
    
    def _check_credential_values(
        self,
        security: Dict[str, Any],
        key: str,
        values: List[Dict[str, Any]]
    ) -> None:
        """Check individual credential values for exposure."""
        for value_info in values:
            if not value_info["value"].startswith("****"):
                security["warnings"].append(
                    f"Potential exposed credential: {key}"
                )
    
    def _is_credential_key(self, key: str) -> bool:
        """Check if key represents a credential."""
        return "KEY" in key or "TOKEN" in key
    
    def _add_security_recommendations(
        self, 
        security: Dict[str, Any]
    ) -> None:
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