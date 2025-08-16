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
            "langchain_tools": [
                r"@tool",
                r"Tool\(",
                r"StructuredTool",
                r"FunctionTool",
                r"from langchain\.tools"
            ],
            "openai_functions": [
                r"functions\s*=",
                r"function_call",
                r"tool_calls",
                r"tools\s*=\s*\[",
                r"function_calling"
            ],
            "agent_tools": [
                r"AgentExecutor",
                r"create_.*_agent",
                r"initialize_agent",
                r"tools\s*=\s*\[.*Tool"
            ],
            "custom_tools": [
                r"class\s+\w*Tool",
                r"def\s+execute_tool",
                r"register_tool",
                r"tool_registry"
            ],
            "retrieval_tools": [
                r"VectorStore",
                r"similarity_search",
                r"RetrievalQA",
                r"retrieve_documents"
            ]
        }
    
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
        tool_map = {
            "tools": [],
            "functions": [],
            "tool_categories": defaultdict(int),
            "usage_patterns": [],
            "summary": {}
        }
        
        # Process pattern locations
        for location in patterns.get("pattern_locations", []):
            file_path = location["file"]
            
            for pattern_info in location["patterns"]:
                # Extract tool information
                tool_info = self._extract_tool_info(pattern_info, file_path)
                if tool_info:
                    self._add_tool_info(tool_map, tool_info)
        
        # Generate summary
        tool_map["summary"] = self._generate_summary(tool_map)
        
        # Convert defaultdict to regular dict
        tool_map["tool_categories"] = dict(tool_map["tool_categories"])
        
        return tool_map
    
    def _extract_tool_info(
        self, 
        pattern_info: Dict[str, Any],
        file_path: str
    ) -> Optional[Dict[str, Any]]:
        """Extract tool information from pattern."""
        category = pattern_info.get("category")
        content = pattern_info.get("content", "")
        line = pattern_info.get("line", 0)
        
        # Check if this is tool-related
        if category != "tools" and "tool" not in content.lower():
            return None
        
        tool_info = {
            "file": file_path,
            "line": line,
            "content": content,
            "type": self._identify_tool_type(content)
        }
        
        # Extract tool details
        details = self._extract_tool_details(content)
        if details:
            tool_info.update(details)
        
        return tool_info
    
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
        
        # Extract tool name
        for pattern_name, pattern in self.function_patterns.items():
            match = re.search(pattern, content)
            if match:
                if pattern_name == "required":
                    # Parse required fields
                    required = match.group(1)
                    details["required_params"] = [
                        p.strip().strip("'\"") 
                        for p in required.split(",")
                    ]
                else:
                    details[pattern_name] = match.group(1)
        
        # Extract decorator-based tool name
        tool_decorator = re.search(r"@tool\(['\"]([^'\"]+)['\"]", content)
        if tool_decorator:
            details["name"] = tool_decorator.group(1)
        
        # Extract class-based tool name
        class_tool = re.search(r"class\s+(\w+Tool)", content)
        if class_tool:
            details["name"] = class_tool.group(1)
        
        return details
    
    def _add_tool_info(
        self, 
        tool_map: Dict[str, Any],
        tool_info: Dict[str, Any]
    ) -> None:
        """Add tool information to map."""
        # Categorize tool
        tool_type = tool_info.get("type", "unknown")
        tool_map["tool_categories"][tool_type] += 1
        
        # Add to tools list
        tool_entry = {
            "file": tool_info["file"],
            "line": tool_info["line"],
            "type": tool_type,
            "name": tool_info.get("name", "unnamed"),
            "description": tool_info.get("description")
        }
        
        if tool_type == "function_calling":
            tool_map["functions"].append(tool_entry)
        else:
            tool_map["tools"].append(tool_entry)
        
        # Track usage pattern
        tool_map["usage_patterns"].append({
            "file": tool_info["file"],
            "type": tool_type,
            "has_params": "parameters" in tool_info
        })
    
    def _generate_summary(self, tool_map: Dict[str, Any]) -> Dict[str, Any]:
        """Generate tool usage summary."""
        total_tools = len(tool_map["tools"]) + len(tool_map["functions"])
        
        # Analyze complexity
        complexity = self._estimate_complexity(tool_map)
        
        # Find most common tool type
        most_common = None
        if tool_map["tool_categories"]:
            most_common = max(
                tool_map["tool_categories"], 
                key=tool_map["tool_categories"].get
            )
        
        return {
            "total_tools": total_tools,
            "function_tools": len(tool_map["functions"]),
            "other_tools": len(tool_map["tools"]),
            "tool_types": len(tool_map["tool_categories"]),
            "most_common_type": most_common,
            "complexity": complexity,
            "has_retrieval": self._has_retrieval(tool_map),
            "has_agents": self._has_agents(tool_map)
        }
    
    def _estimate_complexity(self, tool_map: Dict[str, Any]) -> str:
        """Estimate tool complexity."""
        total = len(tool_map["tools"]) + len(tool_map["functions"])
        types = len(tool_map["tool_categories"])
        
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