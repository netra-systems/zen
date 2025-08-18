"""Tool pattern definitions for usage analysis."""

from typing import Dict, List


class ToolPatternDefinitions:
    """Defines patterns for detecting different types of tools."""
    
    def __init__(self):
        """Initialize pattern definitions."""
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

    def get_tool_patterns(self) -> Dict[str, List[str]]:
        """Get all tool patterns."""
        return self.tool_patterns
    
    def get_function_patterns(self) -> Dict[str, str]:
        """Get function definition patterns."""
        return self.function_patterns