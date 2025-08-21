"""Agent Extractor Module.

Specialized module for extracting and processing agent information from patterns.
Handles agent detection, pattern processing, and information formatting.
"""

from typing import Any, Dict, List, Optional


class AgentExtractor:
    """Extracts agent information from patterns."""
    
    def extract_agents(
        self, 
        patterns: Dict[str, Any],
        tool_mappings: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract agent information."""
        return self._process_all_pattern_locations(patterns)
    
    def _process_all_pattern_locations(self, patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process all pattern locations."""
        agents: List[Dict[str, Any]] = []
        pattern_locations = patterns.get("pattern_locations", [])
        return self._process_pattern_locations(agents, pattern_locations)
    
    def _process_pattern_locations(
        self, agents: List[Dict[str, Any]], pattern_locations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Process pattern locations to extract agents."""
        for location in pattern_locations:
            location_agents = self._extract_location_agents(location)
            agents.extend(location_agents)
        return agents
    
    def _extract_location_agents(
        self, 
        location: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract agents from a single location."""
        agents: List[Dict[str, Any]] = []
        patterns = location.get("patterns", [])
        return self._process_location_patterns(agents, location, patterns)
    
    def _process_location_patterns(
        self, agents: List[Dict[str, Any]], location: Dict[str, Any], patterns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Process patterns for a location."""
        return self._add_agent_patterns(agents, location, patterns)
    
    def _add_agent_patterns(
        self, agents: List[Dict[str, Any]], location: Dict[str, Any], patterns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Add agent patterns to list."""
        for pattern in patterns:
            if self._is_agent_pattern(pattern):
                agent_info = self._build_agent_info(location, pattern)
                agents.append(agent_info)
        return agents
    
    def _build_agent_info(
        self, 
        location: Dict[str, Any], 
        pattern: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build agent information dictionary."""
        return self._extract_and_create_agent_info(location, pattern)
    
    def _extract_and_create_agent_info(
        self, location: Dict[str, Any], pattern: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract data and create agent info."""
        file_path = location["file"]
        line_number = pattern.get("line")
        agent_type = pattern.get("provider")
        pattern_content = pattern.get("content", "")[:100]
        return self._create_agent_info_dict(file_path, line_number, agent_type, pattern_content)
    
    def _create_agent_info_dict(
        self, file_path: str, line_number: Optional[int], 
        agent_type: Optional[str], pattern_content: str
    ) -> Dict[str, Any]:
        """Create agent info dictionary."""
        return {"file": file_path, "line": line_number, "type": agent_type, "pattern": pattern_content}
    
    def _is_agent_pattern(self, pattern: Dict[str, Any]) -> bool:
        """Check if pattern represents an agent."""
        return pattern.get("category") == "agents"