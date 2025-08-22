"""Dependency Extractor Module.

Extracts and analyzes AI-related dependencies from patterns and configurations.
Handles library, framework, and provider detection.
"""

from typing import Any, Dict, List


class DependencyExtractor:
    """Extracts AI-related dependencies from analysis data."""
    
    def extract_dependencies(
        self, 
        patterns: Dict[str, Any],
        configurations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract AI-related dependencies."""
        providers = set(patterns.get("detected_providers", []))
        libraries = self._get_detected_libraries(providers)
        frameworks = self._get_detected_frameworks(providers)
        return self._build_dependencies_dict(libraries, providers, frameworks)
    
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
    
    def _build_dependencies_dict(
        self, libraries: List[str], providers: set, frameworks: List[str]
    ) -> Dict[str, Any]:
        """Build dependencies dictionary."""
        providers_list = list(providers)
        return {
            "detected_libraries": libraries,
            "providers": providers_list,
            "frameworks": frameworks
        }