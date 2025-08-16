"""GitHub Code Analysis Agent - Main orchestration module.

Analyzes repositories to map AI/LLM operations and configurations.
Integrates with existing supervisor, state management, and error handling.
"""

from typing import Dict, Optional, List, Any
import asyncio
from datetime import datetime

from app.llm.llm_manager import LLMManager
from app.agents.base import BaseSubAgent
from app.schemas.strict_types import TypedAgentResult
from app.core.type_validators import agent_type_safe
from app.agents.tool_dispatcher import ToolDispatcher
from app.agents.state import DeepAgentState
from app.logging_config import central_logger as logger
from app.core.reliability import get_reliability_wrapper
from app.agents.input_validation import validate_agent_input

# Import modular components
from .scanner_core import RepositoryScanner
from .pattern_detector import AIPatternDetector
from .config_parser import ConfigurationExtractor
from .llm_mapper import LLMCallMapper
from .tool_analyzer import ToolUsageAnalyzer
from .output_formatter import AIOperationsMapFormatter
from .github_client import GitHubAPIClient


class GitHubAnalyzerAgent(BaseSubAgent):
    """Agent for analyzing GitHub repos to map AI operations."""
    
    def __init__(
        self, 
        llm_manager: LLMManager, 
        tool_dispatcher: ToolDispatcher
    ) -> None:
        """Initialize with LLM manager and tool dispatcher."""
        super().__init__(
            llm_manager=llm_manager,
            name="GitHubAnalyzerAgent",
            description="Analyzes GitHub repositories for AI/LLM usage"
        )
        self.tool_dispatcher = tool_dispatcher
        self._init_components()
        self._init_reliability()
    
    def _init_components(self) -> None:
        """Initialize all analysis components."""
        self.scanner = RepositoryScanner()
        self.pattern_detector = AIPatternDetector()
        self.config_extractor = ConfigurationExtractor()
        self.llm_mapper = LLMCallMapper()
        self.tool_analyzer = ToolUsageAnalyzer()
        self.formatter = AIOperationsMapFormatter()
        self.github_client = GitHubAPIClient()
    
    def _init_reliability(self) -> None:
        """Setup reliability wrappers."""
        self.reliability_wrapper = get_reliability_wrapper(
            circuit_breaker_enabled=True,
            retry_enabled=True,
            timeout_seconds=300
        )
    
    @agent_type_safe
    async def execute(
        self, 
        state: DeepAgentState, 
        context: Dict[str, Any]
    ) -> TypedAgentResult:
        """Execute repository analysis."""
        try:
            await self._validate_input(context)
            repo_url = context.get("repository_url")
            
            # Report progress via WebSocket
            await self._report_progress(state, "Starting analysis", 0)
            
            # Phase 1: Clone/access repository
            repo_path = await self._access_repository(repo_url, state)
            await self._report_progress(state, "Repository accessed", 20)
            
            # Phase 2: Scan for AI patterns
            ai_patterns = await self._scan_patterns(repo_path, state)
            await self._report_progress(state, "Patterns detected", 40)
            
            # Phase 3: Extract configurations
            configs = await self._extract_configs(repo_path, state)
            await self._report_progress(state, "Configurations extracted", 60)
            
            # Phase 4: Map LLM calls and tools
            llm_map = await self._map_llm_usage(ai_patterns, state)
            tool_map = await self._analyze_tools(ai_patterns, state)
            await self._report_progress(state, "Mapping complete", 80)
            
            # Phase 5: Generate output map
            result_map = await self._generate_map(
                repo_url, ai_patterns, configs, llm_map, tool_map
            )
            await self._report_progress(state, "Analysis complete", 100)
            
            return self._create_success_result(result_map)
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            return self._create_error_result(str(e))
    
    async def _validate_input(self, context: Dict[str, Any]) -> None:
        """Validate input parameters."""
        if not context.get("repository_url"):
            raise ValueError("repository_url is required")
        validate_agent_input(context, ["repository_url"])
    
    async def _access_repository(
        self, 
        repo_url: str, 
        state: DeepAgentState
    ) -> str:
        """Clone or access repository."""
        return await self.github_client.clone_repository(repo_url)
    
    async def _scan_patterns(
        self, 
        repo_path: str, 
        state: DeepAgentState
    ) -> Dict[str, Any]:
        """Scan for AI/LLM patterns."""
        files = await self.scanner.get_relevant_files(repo_path)
        patterns = await self.pattern_detector.detect_patterns(files)
        return patterns
    
    async def _extract_configs(
        self, 
        repo_path: str, 
        state: DeepAgentState
    ) -> Dict[str, Any]:
        """Extract AI-related configurations."""
        return await self.config_extractor.extract_configurations(repo_path)
    
    async def _map_llm_usage(
        self, 
        patterns: Dict[str, Any], 
        state: DeepAgentState
    ) -> Dict[str, Any]:
        """Map LLM API calls and usage."""
        return await self.llm_mapper.map_llm_calls(patterns)
    
    async def _analyze_tools(
        self, 
        patterns: Dict[str, Any], 
        state: DeepAgentState
    ) -> Dict[str, Any]:
        """Analyze tool and function usage."""
        return await self.tool_analyzer.analyze_tool_usage(patterns)
    
    async def _generate_map(
        self,
        repo_url: str,
        patterns: Dict[str, Any],
        configs: Dict[str, Any],
        llm_map: Dict[str, Any],
        tool_map: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate final AI operations map."""
        return await self.formatter.format_output(
            repo_url=repo_url,
            patterns=patterns,
            configurations=configs,
            llm_mappings=llm_map,
            tool_mappings=tool_map,
            analyzed_at=datetime.utcnow()
        )
    
    async def _report_progress(
        self, 
        state: DeepAgentState, 
        message: str, 
        progress: int
    ) -> None:
        """Report progress via WebSocket."""
        if self.websocket_manager and self.user_id:
            await self.websocket_manager.send_agent_progress(
                user_id=self.user_id,
                agent_name=self.name,
                message=message,
                progress=progress
            )
    
    def _create_success_result(
        self, 
        result_map: Dict[str, Any]
    ) -> TypedAgentResult:
        """Create success result."""
        return TypedAgentResult(
            success=True,
            data=result_map,
            error=None,
            metadata={
                "agent": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def _create_error_result(self, error: str) -> TypedAgentResult:
        """Create error result."""
        return TypedAgentResult(
            success=False,
            data=None,
            error=error,
            metadata={
                "agent": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def handle_delegation(
        self, 
        task: str, 
        context: Dict[str, Any]
    ) -> TypedAgentResult:
        """Handle delegated tasks from supervisor."""
        if task == "analyze_repository":
            return await self.execute(
                DeepAgentState(), 
                context
            )
        elif task == "quick_scan":
            # Lighter weight scan for quick checks
            patterns = await self.pattern_detector.quick_scan(
                context.get("file_paths", [])
            )
            return self._create_success_result(patterns)
        else:
            return self._create_error_result(
                f"Unknown task: {task}"
            )