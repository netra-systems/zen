"""Tool Usage Analysis Module.

Analyzes function calling, tool usage, and agent tools.
Maps tool definitions and usage patterns.
"""

from typing import Dict, List, Any, Optional
import re
from collections import defaultdict

from app.logging_config import central_logger as logger


class ToolUsageAnalyzer:
    """Analyzes tool and function usage in AI systems."""
    
    def __init__(self):
        """Initialize tool patterns."""
        self.tool_patterns = self._init_tool_patterns()
        self.function_patterns = self._init_function_patterns()
    
    def _init_tool_patterns(self) -> Dict[str, List[str]]:
        """Initialize tool detection patterns."""
        return {
            "langchain_tools": self._get_langchain_patterns(),
            "openai_functions": self._get_openai_patterns(),
            "agent_tools": self._get_agent_patterns(),
            "custom_tools": self._get_custom_patterns(),
            "retrieval_tools": self._get_retrieval_patterns()
        }
    
    def _get_langchain_patterns(self) -> List[str]:
        """Get LangChain tool patterns."""
        return self._build_langchain_pattern_list()

    def _build_langchain_pattern_list(self) -> List[str]:
        """Build LangChain pattern list."""
        return [
            r"@tool",
            r"Tool\(",
            r"StructuredTool",
            r"FunctionTool",
            r"from langchain\.tools"
        ]
    
    def _get_openai_patterns(self) -> List[str]:
        """Get OpenAI function patterns."""
        return self._build_openai_pattern_list()

    def _build_openai_pattern_list(self) -> List[str]:
        """Build OpenAI pattern list."""
        return [
            r"functions\s*=",
            r"function_call",
            r"tool_calls",
            r"tools\s*=\s*\[",
            r"function_calling"
        ]
    
    def _get_agent_patterns(self) -> List[str]:
        """Get agent tool patterns."""
        return self._build_agent_pattern_list()

    def _build_agent_pattern_list(self) -> List[str]:
        """Build agent pattern list."""
        return [
            r"AgentExecutor",
            r"create_.*_agent",
            r"initialize_agent",
            r"tools\s*=\s*\[.*Tool"
        ]
    
    def _get_custom_patterns(self) -> List[str]:
        """Get custom tool patterns."""
        return self._build_custom_pattern_list()

    def _build_custom_pattern_list(self) -> List[str]:
        """Build custom pattern list."""
        return [
            r"class\s+\w*Tool",
            r"def\s+execute_tool",
            r"register_tool",
            r"tool_registry"
        ]
    
    def _get_retrieval_patterns(self) -> List[str]:
        """Get retrieval tool patterns."""
        return self._build_retrieval_pattern_list()

    def _build_retrieval_pattern_list(self) -> List[str]:
        """Build retrieval pattern list."""
        return [
            r"VectorStore",
            r"similarity_search",
            r"RetrievalQA",
            r"retrieve_documents"
        ]
    
    def _init_function_patterns(self) -> Dict[str, str]:
        """Initialize function definition patterns."""
        return {
            "name": r"['\"]name['\"]\s*:\s*['\"]([^'\"]+)['\"]",
            "description": r"['\"]description['\"]\s*:\s*['\"]([^'\"]+)['\"]",
            "parameters": r"['\"]parameters['\"]\s*:\s*\{",
            "required": r"['\"]required['\"]\s*:\s*\[([^\]]+)\]"
        }
    
    async def analyze_tool_usage(
        self, 
        patterns: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze tool usage from patterns."""
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
            "content": content
        }
    
    def _add_tool_type_to_info(self, tool_info: Dict[str, Any], content: str) -> None:
        """Add tool type to info structure."""
        tool_info["type"] = self._identify_tool_type(content)
    
    def _identify_tool_type(self, content: str) -> str:
        """Identify type of tool."""
        content_lower = content.lower()
        return self._classify_tool_by_patterns(content, content_lower)
    
    def _classify_tool_by_patterns(self, content: str, content_lower: str) -> str:
        """Classify tool type by matching patterns."""
        if self._is_langchain_tool(content):
            return "langchain_tool"
        return self._classify_non_langchain_tool(content_lower)
    
    def _is_langchain_tool(self, content: str) -> bool:
        """Check if content indicates LangChain tool."""
        return "@tool" in content or "Tool(" in content
    
    def _classify_non_langchain_tool(self, content_lower: str) -> str:
        """Classify non-LangChain tool types."""
        if "function" in content_lower or "tool_calls" in content_lower:
            return "function_calling"
        return self._classify_specialized_tool(content_lower)
    
    def _classify_specialized_tool(self, content_lower: str) -> str:
        """Classify specialized tool types."""
        if "vectorstore" in content_lower or "retrieval" in content_lower:
            return "retrieval_tool"
        elif "agent" in content_lower:
            return "agent_tool"
        return "custom_tool"
    
    def _extract_tool_details(self, content: str) -> Dict[str, Any]:
        """Extract tool details from content."""
        details = {}
        self._populate_tool_details(details, content)
        return details
    
    def _populate_tool_details(self, details: Dict[str, Any], content: str) -> None:
        """Populate tool details dictionary."""
        self._extract_function_patterns(details, content)
        self._extract_tool_names(details, content)
    
    def _extract_function_patterns(
        self, 
        details: Dict[str, Any], 
        content: str
    ) -> None:
        """Extract function patterns from content."""
        for pattern_name, pattern in self.function_patterns.items():
            self._try_extract_single_pattern(details, pattern_name, pattern, content)
    
    def _try_extract_single_pattern(
        self, details: Dict[str, Any], pattern_name: str, pattern: str, content: str
    ) -> None:
        """Try to extract a single pattern from content."""
        match = re.search(pattern, content)
        if match:
            self._process_pattern_match(details, pattern_name, match)
    
    def _process_pattern_match(
        self, 
        details: Dict[str, Any], 
        pattern_name: str, 
        match: Any
    ) -> None:
        """Process a matched pattern."""
        if self._is_required_pattern(pattern_name):
            self._process_required_params(details, match)
        else:
            self._add_basic_pattern_match(details, pattern_name, match)
    
    def _is_required_pattern(self, pattern_name: str) -> bool:
        """Check if pattern is required parameters pattern."""
        return pattern_name == "required"
    
    def _add_basic_pattern_match(self, details: Dict[str, Any], pattern_name: str, match: Any) -> None:
        """Add basic pattern match to details."""
        details[pattern_name] = match.group(1)
    
    def _process_required_params(
        self, 
        details: Dict[str, Any], 
        match: Any
    ) -> None:
        """Process required parameters."""
        required = match.group(1)
        processed_params = self._parse_required_params_string(required)
        details["required_params"] = processed_params
    
    def _parse_required_params_string(self, required: str) -> List[str]:
        """Parse required parameters string into list."""
        return [
            p.strip().strip("'\"") 
            for p in required.split(",")
        ]
    
    def _extract_tool_names(
        self, 
        details: Dict[str, Any], 
        content: str
    ) -> None:
        """Extract decorator and class-based tool names."""
        self._extract_decorator_name(details, content)
        self._extract_class_name(details, content)
    
    def _extract_decorator_name(
        self, 
        details: Dict[str, Any], 
        content: str
    ) -> None:
        """Extract decorator-based tool name."""
        tool_decorator = re.search(r"@tool\(['\"]([^'\"]+)['\"]", content)
        if tool_decorator:
            details["name"] = tool_decorator.group(1)
    
    def _extract_class_name(
        self, 
        details: Dict[str, Any], 
        content: str
    ) -> None:
        """Extract class-based tool name."""
        class_tool = re.search(r"class\s+(\w+Tool)", content)
        if class_tool:
            details["name"] = class_tool.group(1)
    
    def _add_tool_info(
        self, 
        tool_map: Dict[str, Any],
        tool_info: Dict[str, Any]
    ) -> None:
        """Add tool information to map."""
        tool_type = tool_info.get("type", "unknown")
        self._process_tool_info_addition(tool_map, tool_info, tool_type)
    
    def _process_tool_info_addition(
        self, tool_map: Dict[str, Any], tool_info: Dict[str, Any], tool_type: str
    ) -> None:
        """Process addition of tool info to map."""
        self._categorize_tool(tool_map, tool_type)
        self._add_tool_entry(tool_map, tool_info, tool_type)
        self._track_usage_pattern(tool_map, tool_info, tool_type)
    
    def _categorize_tool(
        self, 
        tool_map: Dict[str, Any], 
        tool_type: str
    ) -> None:
        """Categorize tool by type."""
        tool_map["tool_categories"][tool_type] += 1
    
    def _add_tool_entry(
        self, 
        tool_map: Dict[str, Any], 
        tool_info: Dict[str, Any], 
        tool_type: str
    ) -> None:
        """Add tool entry to appropriate list."""
        tool_entry = self._create_tool_entry(tool_info, tool_type)
        self._append_to_tool_list(tool_map, tool_entry, tool_type)
    
    def _create_tool_entry(
        self, 
        tool_info: Dict[str, Any], 
        tool_type: str
    ) -> Dict[str, Any]:
        """Create tool entry dictionary."""
        base_entry = self._create_tool_entry_base(tool_info, tool_type)
        self._add_tool_entry_metadata(base_entry, tool_info)
        return base_entry
    
    def _create_tool_entry_base(
        self, tool_info: Dict[str, Any], tool_type: str
    ) -> Dict[str, Any]:
        """Create base tool entry structure."""
        return {
            "file": tool_info["file"],
            "line": tool_info["line"],
            "type": tool_type
        }
    
    def _add_tool_entry_metadata(self, entry: Dict[str, Any], tool_info: Dict[str, Any]) -> None:
        """Add metadata to tool entry."""
        entry["name"] = tool_info.get("name", "unnamed")
        entry["description"] = tool_info.get("description")
    
    def _append_to_tool_list(
        self, 
        tool_map: Dict[str, Any], 
        tool_entry: Dict[str, Any], 
        tool_type: str
    ) -> None:
        """Append tool entry to correct list."""
        target_list = self._determine_target_list(tool_map, tool_type)
        target_list.append(tool_entry)
    
    def _determine_target_list(
        self, tool_map: Dict[str, Any], tool_type: str
    ) -> List[Dict[str, Any]]:
        """Determine target list for tool entry."""
        if tool_type == "function_calling":
            return tool_map["functions"]
        return tool_map["tools"]
    
    def _track_usage_pattern(
        self, 
        tool_map: Dict[str, Any], 
        tool_info: Dict[str, Any], 
        tool_type: str
    ) -> None:
        """Track usage pattern for tool."""
        pattern_entry = self._create_usage_pattern_entry(tool_info, tool_type)
        tool_map["usage_patterns"].append(pattern_entry)
    
    def _create_usage_pattern_entry(
        self, tool_info: Dict[str, Any], tool_type: str
    ) -> Dict[str, Any]:
        """Create usage pattern entry."""
        return {
            "file": tool_info["file"],
            "type": tool_type,
            "has_params": "parameters" in tool_info
        }
    
    def _generate_summary(self, tool_map: Dict[str, Any]) -> Dict[str, Any]:
        """Generate tool usage summary."""
        total_tools = self._calculate_total_tools(tool_map)
        complexity = self._estimate_complexity(tool_map)
        most_common = self._find_most_common_type(tool_map)
        return self._build_summary_dict(
            tool_map, total_tools, complexity, most_common
        )
    
    def _calculate_total_tools(self, tool_map: Dict[str, Any]) -> int:
        """Calculate total number of tools."""
        return len(tool_map["tools"]) + len(tool_map["functions"])
    
    def _find_most_common_type(
        self, 
        tool_map: Dict[str, Any]
    ) -> Optional[str]:
        """Find most common tool type."""
        categories = tool_map["tool_categories"]
        if not categories:
            return None
        return self._get_max_category_by_count(categories)
    
    def _get_max_category_by_count(self, categories: Dict[str, int]) -> str:
        """Get category with maximum count."""
        return max(categories, key=categories.get)
    
    def _build_summary_dict(
        self,
        tool_map: Dict[str, Any],
        total_tools: int,
        complexity: str,
        most_common: Optional[str]
    ) -> Dict[str, Any]:
        """Build summary dictionary."""
        base_summary = self._create_base_summary(
            tool_map, total_tools, complexity, most_common
        )
        self._enhance_summary_with_features(base_summary, tool_map)
        return base_summary
    
    def _enhance_summary_with_features(
        self, base_summary: Dict[str, Any], tool_map: Dict[str, Any]
    ) -> None:
        """Enhance summary with feature information."""
        base_summary.update(self._create_feature_summary(tool_map))
    
    def _create_base_summary(
        self, tool_map: Dict[str, Any], total_tools: int, 
        complexity: str, most_common: Optional[str]
    ) -> Dict[str, Any]:
        """Create base summary statistics."""
        counts = self._extract_tool_counts(tool_map)
        metadata = self._create_summary_metadata(most_common, complexity, total_tools)
        return {**counts, **metadata}
    
    def _extract_tool_counts(self, tool_map: Dict[str, Any]) -> Dict[str, int]:
        """Extract tool count information."""
        return {
            "function_tools": len(tool_map["functions"]),
            "other_tools": len(tool_map["tools"]),
            "tool_types": len(tool_map["tool_categories"])
        }
    
    def _create_summary_metadata(
        self, most_common: Optional[str], complexity: str, total_tools: int
    ) -> Dict[str, Any]:
        """Create summary metadata fields."""
        return {
            "total_tools": total_tools,
            "most_common_type": most_common,
            "complexity": complexity
        }
    
    def _create_feature_summary(self, tool_map: Dict[str, Any]) -> Dict[str, Any]:
        """Create feature-specific summary."""
        return {
            "has_retrieval": self._has_retrieval(tool_map),
            "has_agents": self._has_agents(tool_map)
        }
    
    def _estimate_complexity(self, tool_map: Dict[str, Any]) -> str:
        """Estimate tool complexity."""
        total = len(tool_map["tools"]) + len(tool_map["functions"])
        types = len(tool_map["tool_categories"])
        return self._classify_complexity_level(total, types)
    
    def _classify_complexity_level(self, total: int, types: int) -> str:
        """Classify complexity level based on counts."""
        if total > 20 or types > 5:
            return "high"
        elif total > 5 or types > 2:
            return "medium"
        else:
            return "low"
    
    def _has_retrieval(self, tool_map: Dict[str, Any]) -> bool:
        """Check if retrieval tools are present."""
        return "retrieval_tool" in tool_map["tool_categories"]
    
    def _has_agents(self, tool_map: Dict[str, Any]) -> bool:
        """Check if agent tools are present."""
        return "agent_tool" in tool_map["tool_categories"]