"""MCP Intent Detection Module.

Detects when user requests require MCP tool execution and routes them appropriately.
Follows strict 25-line function design and 450-line limit.
"""

import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from netra_backend.app.core.unified_error_handler import agent_error_handler as ExecutionErrorHandler
from netra_backend.app.agents.base.interface import (
    ExecutionContext,
    ExecutionResult,
)
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.core_enums import ExecutionStatus

logger = central_logger.get_logger(__name__)


@dataclass
class MCPIntent:
    """Represents detected MCP intent."""
    requires_mcp: bool
    server_name: Optional[str] = None
    tool_name: Optional[str] = None
    confidence: float = 0.0
    parameters: Dict[str, str] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


class MCPKeywordMatcher:
    """Matches MCP-related keywords in user requests."""
    
    def __init__(self):
        self.mcp_keywords = self._load_mcp_keywords()
        self.tool_patterns = self._load_tool_patterns()
    
    def _load_mcp_keywords(self) -> Dict[str, List[str]]:
        """Load MCP-related keywords by category."""
        return {
            "general": ["mcp", "external tool", "plugin", "extension"],
            "file_ops": ["read file", "write file", "edit file", "file system"],
            "web_ops": ["fetch url", "web request", "http", "api call"],
            "data_ops": ["query database", "search", "index", "retrieve"],
            "system_ops": ["run command", "execute", "system call"]
        }
    
    def _load_tool_patterns(self) -> List[str]:
        """Load regex patterns for tool name detection."""
        return [
            r"use\s+(\w+)\s+tool",
            r"run\s+(\w+)",
            r"execute\s+(\w+)",
            r"call\s+(\w+)",
            r"(\w+)\s+function"
        ]
    
    def find_mcp_indicators(self, request: str) -> List[str]:
        """Find MCP-related indicators in request."""
        request_lower = request.lower()
        indicators = []
        self._collect_keyword_indicators(request_lower, indicators)
        return indicators
    
    def _collect_keyword_indicators(self, request_lower: str, indicators: List[str]) -> None:
        """Collect keyword-based indicators."""
        for category, keywords in self.mcp_keywords.items():
            for keyword in keywords:
                if keyword in request_lower:
                    indicators.append(f"{category}:{keyword}")
    
    def extract_tool_name(self, request: str) -> Optional[str]:
        """Extract potential tool name from request."""
        for pattern in self.tool_patterns:
            match = re.search(pattern, request, re.IGNORECASE)
            if match:
                return match.group(1)
        return None


class MCPServerMatcher:
    """Matches requests to appropriate MCP servers."""
    
    def __init__(self):
        self.server_mappings = self._load_server_mappings()
    
    def _load_server_mappings(self) -> Dict[str, List[str]]:
        """Load server capability mappings."""
        return {
            "filesystem": ["file", "directory", "path", "read", "write"],
            "web_scraper": ["url", "web", "scrape", "html", "fetch"],
            "database": ["query", "sql", "database", "table", "search"],
            "system": ["command", "system", "execute", "run", "shell"]
        }
    
    def find_matching_server(self, request: str) -> Optional[str]:
        """Find best matching server for request."""
        request_lower = request.lower()
        best_match = None
        max_score = 0
        
        for server, keywords in self.server_mappings.items():
            score = self._calculate_match_score(request_lower, keywords)
            if score > max_score:
                max_score = score
                best_match = server
        
        return best_match if max_score > 0 else None
    
    def _calculate_match_score(self, request: str, keywords: List[str]) -> int:
        """Calculate match score for server keywords."""
        return sum(1 for keyword in keywords if keyword in request)


class MCPParameterExtractor:
    """Extracts parameters from MCP tool requests."""
    
    def __init__(self):
        self.parameter_patterns = self._load_parameter_patterns()
    
    def _load_parameter_patterns(self) -> Dict[str, str]:
        """Load regex patterns for parameter extraction."""
        return {
            "file_path": r"(?:file|path):\s*[\"']?([^\"'\s]+)[\"']?",
            "url": r"(?:url|link):\s*[\"']?(https?://[^\s\"']+)[\"']?",
            "query": r"(?:query|search):\s*[\"']?([^\"']+)[\"']?",
            "command": r"(?:command|cmd):\s*[\"']?([^\"']+)[\"']?"
        }
    
    def extract_parameters(self, request: str) -> Dict[str, str]:
        """Extract structured parameters from request."""
        parameters = {}
        for param_name, pattern in self.parameter_patterns.items():
            match = re.search(pattern, request, re.IGNORECASE)
            if match:
                parameters[param_name] = match.group(1)
        return parameters
    
    def extract_simple_params(self, request: str) -> Dict[str, str]:
        """Extract simple key-value parameters."""
        params = {}
        # Look for "param: value" patterns
        pattern = r"(\w+):\s*([^,\n]+)"
        matches = re.findall(pattern, request)
        for key, value in matches:
            params[key.strip()] = value.strip()
        return params


class MCPIntentDetector:
    """Main MCP intent detector with execution monitoring."""
    
    def __init__(self):
        self.keyword_matcher = MCPKeywordMatcher()
        self.server_matcher = MCPServerMatcher()
        self.parameter_extractor = MCPParameterExtractor()
        self.execution_monitor = ExecutionMonitor()
        self.error_handler = ExecutionErrorHandler
    
    def detect_intent(self, request: str) -> MCPIntent:
        """Detect MCP intent from user request."""
        indicators = self.keyword_matcher.find_mcp_indicators(request)
        
        if not indicators:
            return MCPIntent(requires_mcp=False)
        
        return self._build_mcp_intent(request, indicators)
    
    def _build_mcp_intent(self, request: str, indicators: List[str]) -> MCPIntent:
        """Build MCP intent from request and indicators."""
        server_name = self.server_matcher.find_matching_server(request)
        tool_name = self.keyword_matcher.extract_tool_name(request)
        parameters = self._extract_all_parameters(request)
        confidence = self._calculate_confidence(indicators, server_name, tool_name)
        return self._create_intent_object(server_name, tool_name, confidence, parameters)
    
    def _create_intent_object(self, server_name: Optional[str], tool_name: Optional[str],
                            confidence: float, parameters: Dict[str, str]) -> MCPIntent:
        """Create MCPIntent object with validated parameters."""
        return MCPIntent(
            requires_mcp=True,
            server_name=server_name,
            tool_name=tool_name,
            confidence=confidence,
            parameters=parameters
        )
    
    def _extract_all_parameters(self, request: str) -> Dict[str, str]:
        """Extract all possible parameters from request."""
        structured_params = self.parameter_extractor.extract_parameters(request)
        simple_params = self.parameter_extractor.extract_simple_params(request)
        return {**structured_params, **simple_params}
    
    def _calculate_confidence(self, indicators: List[str], 
                            server_name: Optional[str], 
                            tool_name: Optional[str]) -> float:
        """Calculate confidence score for MCP intent."""
        base_score = len(indicators) * 0.2
        server_bonus = 0.3 if server_name else 0.0
        tool_bonus = 0.2 if tool_name else 0.0
        return min(1.0, base_score + server_bonus + tool_bonus)
    
    def should_route_to_mcp(self, request: str, threshold: float = 0.5) -> bool:
        """Check if request should be routed to MCP."""
        intent = self.detect_intent(request)
        return intent.requires_mcp and intent.confidence >= threshold
    
    def get_routing_info(self, request: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Get MCP routing information for request."""
        intent = self.detect_intent(request)
        if intent.requires_mcp:
            return True, intent.server_name, intent.tool_name
        return False, None, None
    
    async def detect_intent_with_reliability(self, request: str, run_id: str) -> ExecutionResult:
        """Detect MCP intent with execution monitoring and error handling."""
        start_time = time.time()
        context = self._create_detection_context(request, run_id)
        self.execution_monitor.start_execution(context)
        
        try:
            intent = await self._execute_detection_with_monitoring(request)
            return self._create_success_detection_result(intent, start_time)
        except Exception as e:
            return await self._handle_detection_error(e, context)
    
    def _create_detection_context(self, request: str, run_id: str) -> ExecutionContext:
        """Create execution context for intent detection."""
        from netra_backend.app.schemas.agent_models import DeepAgentState
        state = DeepAgentState(agent_name="MCPIntentDetector")
        state.current_request = request
        return self.create_execution_context(state, run_id)
    
    async def _execute_detection_with_monitoring(self, request: str) -> MCPIntent:
        """Execute detection with monitoring wrapper."""
        intent = self.detect_intent(request)
        return intent
    
    def _create_success_detection_result(self, intent: MCPIntent, start_time: float) -> ExecutionResult:
        """Create successful detection result."""
        execution_time_ms = (time.time() - start_time) * 1000
        return self.create_success_result(
            {"intent": intent, "requires_mcp": intent.requires_mcp},
            execution_time_ms
        )
    
    async def _handle_detection_error(self, error: Exception, context: ExecutionContext) -> ExecutionResult:
        """Handle detection error with fallback strategies."""
        self.execution_monitor.record_error(context, error)
        return await self.error_handler.handle_execution_error(error, context)