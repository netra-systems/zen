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
        return [
            r"@tool",
            r"Tool\(",
            r"StructuredTool",
            r"FunctionTool",
            r"from langchain\.tools"
        ]
    
    def _get_openai_patterns(self) -> List[str]:
        """Get OpenAI function patterns."""
        return [
            r"functions\s*=",
            r"function_call",
            r"tool_calls",
            r"tools\s*=\s*\[",
            r"function_calling"
        ]
    
    def _get_agent_patterns(self) -> List[str]:
        """Get agent tool patterns."""
        return [
            r"AgentExecutor",
            r"create_.*_agent",
            r"initialize_agent",
            r"tools\s*=\s*\[.*Tool"
        ]
    
    def _get_custom_patterns(self) -> List[str]:
        """Get custom tool patterns."""
        return [
            r"class\s+\w*Tool",
            r"def\s+execute_tool",
            r"register_tool",
            r"tool_registry"
        ]
    
    def _get_retrieval_patterns(self) -> List[str]:
        """Get retrieval tool patterns."""
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
        for pattern_info in location["patterns"]:
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
        
        tool_info = self._build_base_tool_info(pattern_info, file_path)
        details = self._extract_tool_details(tool_info["content"])
        if details:
            tool_info.update(details)
        return tool_info
    
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
        return {
            "file": file_path,
            "line": pattern_info.get("line", 0),
            "content": content,
            "type": self._identify_tool_type(content)
        }
    
    def _identify_tool_type(self, content: str) -> str:
        """Identify type of tool."""
        content_lower = content.lower()
        
        if "@tool" in content or "Tool(" in content:
            return "langchain_tool"
        elif "function" in content_lower or "tool_calls" in content_lower:
            return "function_calling"
        elif "vectorstore" in content_lower or "retrieval" in content_lower:
            return "retrieval_tool"
        elif "agent" in content_lower:
            return "agent_tool"
        else:
            return "custom_tool"
    
    def _extract_tool_details(self, content: str) -> Dict[str, Any]:
        """Extract tool details from content."""
        details = {}
        
        # Extract function patterns
        self._extract_function_patterns(details, content)
        
        # Extract decorator and class names
        self._extract_tool_names(details, content)
        
        return details
    
    def _extract_function_patterns(
        self, 
        details: Dict[str, Any], 
        content: str
    ) -> None:
        """Extract function patterns from content."""
        for pattern_name, pattern in self.function_patterns.items():
            match = re.search(pattern, content)
            if match:
                self._process_pattern_match(
                    details, pattern_name, match
                )
    
    def _process_pattern_match(
        self, 
        details: Dict[str, Any], 
        pattern_name: str, 
        match: Any
    ) -> None:
        """Process a matched pattern."""
        if pattern_name == "required":
            self._process_required_params(details, match)
        else:
            details[pattern_name] = match.group(1)
    
    def _process_required_params(
        self, 
        details: Dict[str, Any], 
        match: Any
    ) -> None:
        """Process required parameters."""
        required = match.group(1)
        details["required_params"] = [
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
        return {
            "file": tool_info["file"],
            "line": tool_info["line"],
            "type": tool_type,
            "name": tool_info.get("name", "unnamed"),
            "description": tool_info.get("description")
        }
    
    def _append_to_tool_list(
        self, 
        tool_map: Dict[str, Any], 
        tool_entry: Dict[str, Any], 
        tool_type: str
    ) -> None:
        """Append tool entry to correct list."""
        if tool_type == "function_calling":
            tool_map["functions"].append(tool_entry)
        else:
            tool_map["tools"].append(tool_entry)
    
    def _track_usage_pattern(
        self, 
        tool_map: Dict[str, Any], 
        tool_info: Dict[str, Any], 
        tool_type: str
    ) -> None:
        """Track usage pattern for tool."""
        tool_map["usage_patterns"].append({
            "file": tool_info["file"],
            "type": tool_type,
            "has_params": "parameters" in tool_info
        })
    
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
        if not tool_map["tool_categories"]:
            return None
        return max(
            tool_map["tool_categories"], 
            key=tool_map["tool_categories"].get
        )
    
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
        base_summary.update(self._create_feature_summary(tool_map))
        return base_summary
    
    def _create_base_summary(
        self, tool_map: Dict[str, Any], total_tools: int, 
        complexity: str, most_common: Optional[str]
    ) -> Dict[str, Any]:
        """Create base summary statistics."""
        return {
            "total_tools": total_tools,
            "function_tools": len(tool_map["functions"]),
            "other_tools": len(tool_map["tools"]),
            "tool_types": len(tool_map["tool_categories"]),
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