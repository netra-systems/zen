"""Tool processing core operations."""

from collections import defaultdict
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger as logger


class ToolProcessingCore:
    """Core tool processing operations."""
    
    def __init__(self):
        """Initialize processing core."""
        pass
    
    def process_tool_patterns(self, patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Process tool patterns and build tool map."""
        tool_map = self._initialize_tool_map()
        self._process_pattern_locations(patterns, tool_map)
        self._finalize_tool_map(tool_map)
        return tool_map
    
    def _initialize_tool_map(self) -> Dict[str, Any]:
        """Initialize empty tool map structure."""
        return self._build_empty_tool_map()

    def _build_empty_tool_map(self) -> Dict[str, Any]:
        """Build empty tool map structure."""
        return {
            "tools": [],
            "functions": [],
            "tool_categories": defaultdict(int),
            "usage_patterns": [],
            "summary": {}
        }
    
    def _process_pattern_locations(
        self, 
        patterns: Dict[str, Any], 
        tool_map: Dict[str, Any]
    ) -> None:
        """Process all pattern locations."""
        for location in patterns.get("pattern_locations", []):
            self._process_location_patterns(location, tool_map)
    
    def _process_location_patterns(
        self, 
        location: Dict[str, Any], 
        tool_map: Dict[str, Any]
    ) -> None:
        """Process patterns for a single location."""
        file_path = location["file"]
        self._process_location_pattern_list(location, tool_map, file_path)
    
    def _process_location_pattern_list(
        self, location: Dict[str, Any], tool_map: Dict[str, Any], file_path: str
    ) -> None:
        """Process pattern list for a location."""
        for pattern_info in location["patterns"]:
            self._process_single_pattern_info(pattern_info, tool_map, file_path)
    
    def _process_single_pattern_info(
        self, pattern_info: Dict[str, Any], tool_map: Dict[str, Any], file_path: str
    ) -> None:
        """Process single pattern info entry."""
        tool_info = self._extract_tool_info(pattern_info, file_path)
        if tool_info:
            self._add_tool_info(tool_map, tool_info)
    
    def _finalize_tool_map(self, tool_map: Dict[str, Any]) -> None:
        """Finalize tool map with summary and conversions."""
        tool_map["summary"] = self._generate_summary(tool_map)
        tool_map["tool_categories"] = dict(tool_map["tool_categories"])
    
    def _extract_tool_info(
        self, 
        pattern_info: Dict[str, Any],
        file_path: str
    ) -> Optional[Dict[str, Any]]:
        """Extract tool information from pattern."""
        if not self._is_tool_related_pattern(pattern_info):
            return None
        return self._build_complete_tool_info(pattern_info, file_path)
    
    def _build_complete_tool_info(
        self, pattern_info: Dict[str, Any], file_path: str
    ) -> Dict[str, Any]:
        """Build complete tool info with details."""
        tool_info = self._build_base_tool_info(pattern_info, file_path)
        self._enrich_tool_info_with_details(tool_info)
        return tool_info
    
    def _enrich_tool_info_with_details(self, tool_info: Dict[str, Any]) -> None:
        """Enrich tool info with extracted details."""
        details = self._extract_tool_details(tool_info["content"])
        if details:
            tool_info.update(details)
    
    def _is_tool_related_pattern(self, pattern_info: Dict[str, Any]) -> bool:
        """Check if pattern is tool-related."""
        category = pattern_info.get("category")
        content = pattern_info.get("content", "")
        return category == "tools" or "tool" in content.lower()
    
    def _build_base_tool_info(
        self, pattern_info: Dict[str, Any], file_path: str
    ) -> Dict[str, Any]:
        """Build base tool info structure."""
        content = pattern_info.get("content", "")
        base_info = self._create_tool_info_structure(pattern_info, file_path, content)
        self._add_tool_type_to_info(base_info, content)
        return base_info
    
    def _create_tool_info_structure(
        self, pattern_info: Dict[str, Any], file_path: str, content: str
    ) -> Dict[str, Any]:
        """Create base tool info structure."""
        return {
            "file": file_path,
            "line": pattern_info.get("line", 0),
            "pattern_type": pattern_info.get("pattern", "unknown"),
            "content": content
        }
    
    def _add_tool_type_to_info(self, tool_info: Dict[str, Any], content: str) -> None:
        """Add tool type to info structure."""
        tool_info["tool_type"] = self._identify_tool_type(content)

    def _identify_tool_type(self, content: str) -> str:
        """Identify tool type from content."""
        content_lower = content.lower()
        return self._classify_tool_by_patterns(content, content_lower)

    def _classify_tool_by_patterns(self, content: str, content_lower: str) -> str:
        """Classify tool by content patterns."""
        if self._is_langchain_tool(content):
            return "langchain"
        elif self._is_openai_function(content_lower):
            return "openai_function"
        elif self._is_agent_tool(content_lower):
            return "agent_tool"
        return "custom"

    def _is_langchain_tool(self, content: str) -> bool:
        """Check if content indicates LangChain tool."""
        langchain_indicators = ["@tool", "Tool(", "StructuredTool", "langchain.tools"]
        return any(indicator in content for indicator in langchain_indicators)

    def _is_openai_function(self, content_lower: str) -> bool:
        """Check if content indicates OpenAI function."""
        openai_indicators = ["function_call", "tool_calls", "functions="]
        return any(indicator in content_lower for indicator in openai_indicators)

    def _is_agent_tool(self, content_lower: str) -> bool:
        """Check if content indicates agent tool."""
        agent_indicators = ["agentexecutor", "initialize_agent", "create_"]
        return any(indicator in content_lower for indicator in agent_indicators)

    def _extract_tool_details(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract tool details from content."""
        details = {}
        name = self._extract_tool_name(content)
        if name:
            details["name"] = name
        
        description = self._extract_tool_description(content)
        if description:
            details["description"] = description
            
        return details if details else None

    def _extract_tool_name(self, content: str) -> Optional[str]:
        """Extract tool name from content."""
        import re
        name_pattern = r"['\"]name['\"]\s*:\s*['\"]([^'\"]+)['\"]"
        match = re.search(name_pattern, content)
        return match.group(1) if match else None

    def _extract_tool_description(self, content: str) -> Optional[str]:
        """Extract tool description from content."""
        import re
        desc_pattern = r"['\"]description['\"]\s*:\s*['\"]([^'\"]+)['\"]"
        match = re.search(desc_pattern, content)
        return match.group(1) if match else None

    def _add_tool_info(self, tool_map: Dict[str, Any], tool_info: Dict[str, Any]) -> None:
        """Add tool info to tool map."""
        if tool_info.get("tool_type") == "openai_function":
            tool_map["functions"].append(tool_info)
        else:
            tool_map["tools"].append(tool_info)
        
        # Update categories
        tool_type = tool_info.get("tool_type", "unknown")
        tool_map["tool_categories"][tool_type] += 1

    def _generate_summary(self, tool_map: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of tool analysis."""
        return {
            "total_tools": len(tool_map["tools"]),
            "total_functions": len(tool_map["functions"]),
            "total_categories": len(tool_map["tool_categories"]),
            "most_common_type": self._get_most_common_type(tool_map["tool_categories"])
        }

    def _get_most_common_type(self, categories: Dict[str, int]) -> str:
        """Get most common tool type."""
        if not categories:
            return "none"
        return max(categories.items(), key=lambda x: x[1])[0]