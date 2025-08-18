"""AI Map Builder Module.

Main orchestration module for building structured AI operations maps.
Coordinates with specialized component builders for modular functionality.
"""

from typing import Dict, List, Any
from datetime import datetime

from app.logging_config import central_logger as logger
from .map_components import MapComponentsBuilder
from .security_analyzer import SecurityAnalyzer
from .dependency_extractor import DependencyExtractor


class AIMapBuilder:
    """Builds structured AI operations maps from analysis data."""
    
    def __init__(self):
        """Initialize AI Map Builder with component modules."""
        self.components_builder = MapComponentsBuilder()
        self.security_analyzer = SecurityAnalyzer()
        self.dependency_extractor = DependencyExtractor()
    
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
        components = self._build_map_components(repo_url, patterns, configurations, llm_mappings, tool_mappings, analyzed_at)
        return self._assemble_final_map(*components)
    
    def _build_map_components(
        self, repo_url: str, patterns: Dict[str, Any], configurations: Dict[str, Any],
        llm_mappings: Dict[str, Any], tool_mappings: Dict[str, Any], analyzed_at: datetime
    ) -> tuple:
        """Build all map components."""
        repo_info = self.components_builder.build_repo_info(repo_url, analyzed_at)
        ai_infra = self.components_builder.build_ai_infrastructure(patterns, llm_mappings, tool_mappings, configurations)
        code_locations = self.components_builder.build_code_locations(patterns, configurations, llm_mappings)
        security = self.security_analyzer.analyze_security(configurations)
        dependencies = self.dependency_extractor.extract_dependencies(patterns, configurations)
        return repo_info, ai_infra, code_locations, security, dependencies
    
    def _assemble_final_map(
        self, repo_info: Dict[str, str], ai_infra: Dict[str, Any], code_locations: Dict[str, Any],
        security: Dict[str, Any], dependencies: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assemble final AI map dictionary."""
        return self._create_final_map_dict(repo_info, ai_infra, code_locations, security, dependencies)
    
    def _create_final_map_dict(
        self, repo_info: Dict[str, str], ai_infra: Dict[str, Any], code_locations: Dict[str, Any],
        security: Dict[str, Any], dependencies: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create final map dictionary."""
        return {
            "repository_info": repo_info,
            "ai_infrastructure": ai_infra,
            "code_locations": code_locations,
            "security": security,
            "dependencies": dependencies
        }