"""Map Components Builder Module.

Handles building individual components of the AI operations map.
Focused on repository info, infrastructure, and code locations.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from .agent_extractor import AgentExtractor
from .hotspot_analyzer import HotspotAnalyzer


class MapComponentsBuilder:
    """Builds individual components of AI operations maps."""
    
    def __init__(self):
        """Initialize with specialized extractors."""
        self.agent_extractor = AgentExtractor()
        self.hotspot_analyzer = HotspotAnalyzer()
    
    def build_repo_info(self, repo_url: str, analyzed_at: datetime) -> Dict[str, str]:
        """Build repository information section."""
        iso_timestamp = analyzed_at.isoformat()
        return self._create_repo_info_dict(repo_url, iso_timestamp)
    
    def _create_repo_info_dict(self, repo_url: str, iso_timestamp: str) -> Dict[str, str]:
        """Create repository info dictionary."""
        return {
            "url": repo_url,
            "analyzed_at": iso_timestamp,
            "analysis_version": "1.0.0"
        }
    
    def build_ai_infrastructure(
        self,
        patterns: Dict[str, Any],
        llm_mappings: Dict[str, Any],
        tool_mappings: Dict[str, Any],
        configurations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build AI infrastructure section."""
        return self._merge_infrastructure_components(patterns, llm_mappings, tool_mappings, configurations)
    
    def _merge_infrastructure_components(
        self, patterns: Dict[str, Any], llm_mappings: Dict[str, Any],
        tool_mappings: Dict[str, Any], configurations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge infrastructure components."""
        base_infra = self._build_base_infrastructure(patterns, llm_mappings, tool_mappings)
        config_infra = self._build_config_infrastructure(configurations, patterns)
        return {**base_infra, **config_infra}
    
    def _build_base_infrastructure(
        self, patterns: Dict[str, Any], llm_mappings: Dict[str, Any], tool_mappings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build base infrastructure components."""
        providers = patterns.get("detected_providers", [])
        endpoints = llm_mappings.get("endpoints", [])
        models = self._format_models(llm_mappings)
        agents = self.agent_extractor.extract_agents(patterns, tool_mappings)
        tools = tool_mappings.get("tools", [])
        functions = tool_mappings.get("functions", [])
        return self._create_base_infra_dict(providers, endpoints, models, agents, tools, functions)
    
    def _create_base_infra_dict(
        self, providers: List[str], endpoints: List[str], models: Dict[str, Any],
        agents: List[Dict[str, Any]], tools: List[str], functions: List[str]
    ) -> Dict[str, Any]:
        """Create base infrastructure dictionary."""
        return {
            "providers": providers,
            "llm_endpoints": endpoints,
            "models": models,
            "agents": agents,
            "tools": tools,
            "functions": functions
        }
    
    def _build_config_infrastructure(self, configurations: Dict[str, Any], patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Build configuration-related infrastructure."""
        return {
            "configurations": self._format_configs(configurations),
            "patterns": self._summarize_patterns(patterns)
        }
    
    def build_code_locations(
        self,
        patterns: Dict[str, Any],
        configurations: Dict[str, Any],
        llm_mappings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build code locations section."""
        return self._gather_and_create_locations(patterns, configurations, llm_mappings)
    
    def _gather_and_create_locations(
        self, patterns: Dict[str, Any], configurations: Dict[str, Any], llm_mappings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Gather location data and create dictionary."""
        ai_files = self._get_ai_files(patterns)
        config_files = self._get_config_files(configurations)
        hotspots = self.hotspot_analyzer.identify_hotspots(patterns, llm_mappings)
        return self._create_code_locations_dict(ai_files, config_files, hotspots)
    
    def _create_code_locations_dict(
        self, ai_files: List[str], config_files: List[str], hotspots: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create code locations dictionary."""
        return {"ai_files": ai_files, "config_files": config_files, "hotspots": hotspots}
    
    def _format_models(self, llm_mappings: Dict[str, Any]) -> Dict[str, Any]:
        """Format model information."""
        models = llm_mappings.get("models", {})
        summary = llm_mappings.get("summary", {})
        used_models = list(models.keys())
        most_used = summary.get("most_used_model")
        parameter_ranges = summary.get("parameter_stats", {})
        return self._create_models_dict(used_models, models, most_used, parameter_ranges)
    
    def _create_models_dict(
        self, used_models: List[str], models: Dict[str, Any], 
        most_used: Optional[str], parameter_ranges: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create models dictionary."""
        return {"used_models": used_models, "model_counts": models, "most_used": most_used, "parameter_ranges": parameter_ranges}
    
    def _format_configs(self, configurations: Dict[str, Any]) -> Dict[str, Any]:
        """Format configuration information."""
        config_files = self._format_config_files(configurations)
        detected_providers = self._get_detected_providers(configurations)
        env_vars = configurations.get("env_variables", {})
        return self._build_config_dict(env_vars, config_files, detected_providers)
    
    def _format_config_files(
        self, 
        configurations: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Format configuration files list."""
        config_files_data = configurations.get("config_files", [])
        return self._process_config_files_data(config_files_data)
    
    def _process_config_files_data(self, config_files_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process config files data into formatted list."""
        return [
            self._build_config_file_info(cf)
            for cf in config_files_data
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
        complexity = summary.get("complexity", "unknown")
        return self._build_pattern_summary(total_patterns, pattern_counts, complexity)
    
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
    
    def _build_config_dict(
        self, env_vars: Dict[str, Any], config_files: List[Dict[str, Any]], 
        detected_providers: List[str]
    ) -> Dict[str, Any]:
        """Build configuration dictionary."""
        return {
            "environment_variables": env_vars,
            "config_files": config_files,
            "detected_providers": detected_providers
        }
    
    def _build_config_file_info(self, cf: Dict[str, Any]) -> Dict[str, Any]:
        """Build configuration file information."""
        return {
            "file": cf["file"],
            "ai_configs": len(cf.get("configs", {}))
        }
    
    def _build_pattern_summary(self, total_patterns: int, pattern_counts: dict, complexity: str) -> Dict[str, Any]:
        """Build pattern summary dictionary."""
        return {
            "total_patterns": total_patterns,
            "by_provider": pattern_counts,
            "complexity": complexity
        }