"""GitHub Code Analysis Service - Main orchestration module.

Analyzes repositories to map AI/LLM operations and configurations.
Integrates with existing supervisor, state management, and error handling.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.executor import (
    BaseExecutionEngine, ExecutionStrategy, ExecutionWorkflowBuilder,
    LambdaExecutionPhase, AgentMethodExecutionPhase
)
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.github_analyzer.config_parser import (
    ConfigurationExtractor,
)
from netra_backend.app.agents.github_analyzer.github_client import GitHubAPIClient
from netra_backend.app.agents.github_analyzer.llm_mapper import LLMCallMapper
from netra_backend.app.agents.github_analyzer.output_formatter import (
    AIOperationsMapFormatter,
)
from netra_backend.app.agents.github_analyzer.pattern_detector import AIPatternDetector

# Import modular components
from netra_backend.app.agents.github_analyzer.scanner_core import RepositoryScanner
from netra_backend.app.agents.github_analyzer.tool_analyzer import ToolUsageAnalyzer
from netra_backend.app.agents.input_validation import validate_agent_input
from netra_backend.app.schemas.agent_models import DeepAgentState, UserExecutionContextAdapter
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.core.reliability import get_reliability_wrapper
from netra_backend.app.core.type_validators import agent_type_safe
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.schemas.strict_types import TypedAgentResult


class GitHubAnalyzerService(BaseAgent):
    """Service for analyzing GitHub repos to map AI operations."""
    
    def __init__(
        self, 
        llm_manager: LLMManager, 
        tool_dispatcher: UnifiedToolDispatcher
    ) -> None:
        """Initialize with LLM manager and tool dispatcher."""
        self._init_base_agent(llm_manager)
        self.tool_dispatcher = tool_dispatcher
        self._init_components()
        self._init_reliability()
    
    def _init_base_agent(self, llm_manager: LLMManager) -> None:
        """Initialize base agent configuration."""
        super().__init__(
            llm_manager=llm_manager,
            name="GitHubAnalyzerService",
            description="Analyzes GitHub repositories for AI/LLM usage"
        )
    
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
        self._init_execution_engine()
    
    def _init_execution_engine(self) -> None:
        """Initialize BaseExecutionEngine with phases."""
        # Create execution phases for GitHub analysis workflow
        phase_1 = AgentMethodExecutionPhase("repository_access", self, "_execute_phase_1_method")
        phase_2 = AgentMethodExecutionPhase("pattern_scanning", self, "_execute_phase_2_method", ["repository_access"])
        phase_3 = AgentMethodExecutionPhase("config_extraction", self, "_execute_phase_3_method", ["repository_access"])
        phase_4 = AgentMethodExecutionPhase("mapping_generation", self, "_execute_phase_4_method", ["pattern_scanning"])
        phase_5 = AgentMethodExecutionPhase("final_map_creation", self, "_execute_phase_5_method", ["config_extraction", "mapping_generation"])
        
        # Build execution engine with pipeline strategy
        self.execution_engine = ExecutionWorkflowBuilder() \
            .add_phases([phase_1, phase_2, phase_3, phase_4, phase_5]) \
            .set_strategy(ExecutionStrategy.PIPELINE) \
            .add_pre_execution_hook(self._pre_execution_hook) \
            .add_post_execution_hook(self._post_execution_hook) \
            .build()
    
    def _create_user_execution_context(
        self, 
        state: DeepAgentState, 
        context: Dict[str, Any]
    ) -> UserExecutionContext:
        """Create UserExecutionContext for proper user isolation.
        
        PHASE 1 MIGRATION: Creates UserExecutionContext from DeepAgentState and context
        to ensure proper user isolation during GitHub repository analysis.
        
        SECURITY CRITICAL: Prevents cross-user data contamination by establishing
        proper isolation boundaries for each analysis request.
        """
        from shared.id_generation.unified_id_generator import UnifiedIdGenerator
        
        # Extract user information with fallbacks
        user_id = context.get("user_id") or state.user_id
        if not user_id:
            # Generate a secure user_id for anonymous analysis (still isolated)
            user_id = UnifiedIdGenerator.generate_base_id("github_user")
        
        thread_id = context.get("thread_id") or state.chat_thread_id
        if not thread_id:
            thread_id = UnifiedIdGenerator.generate_base_id("github_thread")
        
        run_id = context.get("run_id") or state.run_id
        if not run_id:
            run_id = UnifiedIdGenerator.generate_base_id("github_run")
        
        # Create agent context for analysis-specific data
        agent_context = {
            'operation_name': 'github_repository_analysis',
            'repository_url': context.get('repository_url'),
            'analysis_type': context.get('analysis_type', 'full'),
            'stream_updates': context.get('stream_updates', False),
            'user_request': state.user_request,
            'user_prompt': state.user_prompt
        }
        
        # Merge existing agent_context from state
        if state.agent_context:
            agent_context.update(state.agent_context)
        
        # Create audit metadata for compliance and debugging
        audit_metadata = {
            'component': 'GitHubAnalyzerService',
            'migration_phase': 'phase_1',
            'correlation_id': context.get('correlation_id'),
            'original_context': {k: v for k, v in context.items() if k not in ['repository_url']},  # Exclude sensitive data
            'state_metadata': state.metadata.model_dump() if state.metadata else {}
        }
        
        return UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            websocket_client_id=context.get('websocket_client_id'),
            agent_context=agent_context,
            audit_metadata=audit_metadata,
            operation_depth=0
        )

    @agent_type_safe
    async def execute(
        self, 
        state: DeepAgentState, 
        context: Dict[str, Any]
    ) -> TypedAgentResult:
        """Execute repository analysis using BaseExecutionEngine with enhanced user isolation.
        
        PHASE 1 MIGRATION: Now uses UserExecutionContext for proper user isolation
        during GitHub repository analysis, preventing cross-user data contamination.
        """
        try:
            await self._validate_input(context)
            
            # PHASE 1 MIGRATION: Create UserExecutionContext for proper isolation
            try:
                user_context = self._create_user_execution_context(state, context)
                # Validate that migration is safe
                UserExecutionContextAdapter.validate_migration_compatibility(state, user_context)
                
                # Update state with UserExecutionContext data for enhanced isolation
                enhanced_state = UserExecutionContextAdapter.create_deep_state_from_user_context(user_context)
                
                logger.info(
                    f"PHASE 1 MIGRATION: Created isolated execution context for GitHub analysis. "
                    f"user_id={user_context.user_id[:8]}..., run_id={user_context.run_id}, "
                    f"repository_url={context.get('repository_url', 'unknown')}"
                )
                
            except Exception as migration_error:
                logger.warning(
                    f"PHASE 1 MIGRATION: Failed to create UserExecutionContext, falling back to legacy pattern. "
                    f"Error: {migration_error}"
                )
                enhanced_state = state
                user_context = None
            
            # Create execution context (backward compatible)
            execution_context = ExecutionContext(
                run_id=context.get("run_id", "github_analysis"),
                agent_name=self.name,
                state=enhanced_state,
                stream_updates=context.get("stream_updates", False),
                thread_id=context.get("thread_id"),
                user_id=context.get("user_id") or enhanced_state.user_id,
                correlation_id=context.get("correlation_id")
            )
            
            # Store both contexts for enhanced isolation tracking
            execution_context.analysis_context = context
            if user_context:
                execution_context.user_context = user_context
            
            # Store analysis context in execution context
            execution_context.analysis_context = context
            
            # Execute using BaseExecutionEngine with phases
            result = await self.execution_engine.execute_phases(execution_context)
            
            if result.success:
                return self._create_success_result(result.result.get("final_map_creation", {}).get("result_map", {}))
            else:
                return self._create_error_result(result.error)
                
        except Exception as e:
            return await self._handle_execution_error(e)
    
    async def _handle_execution_error(self, error: Exception) -> TypedAgentResult:
        """Handle execution errors with logging."""
        error_msg = str(error)
        logger.error(f"Analysis failed: {error_msg}")
        return self._create_error_result(error_msg)
    
    async def _pre_execution_hook(self, context: ExecutionContext) -> None:
        """Pre-execution hook for setup."""
        await self._report_progress(context.state, "Starting GitHub analysis", 0)
        logger.info(f"Starting GitHub analysis for {context.analysis_context.get('repository_url')}")
    
    async def _post_execution_hook(self, context: ExecutionContext, phase_results: Dict[str, Any]) -> None:
        """Post-execution hook for cleanup."""
        await self._report_progress(context.state, "GitHub analysis complete", 100)
        logger.info(f"GitHub analysis completed with {len(phase_results)} phases")
    
    # New phase execution methods for BaseExecutionEngine integration
    async def _execute_phase_1_method(self, context: ExecutionContext, previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 1: Repository access - method wrapper."""
        repo_url = context.analysis_context.get("repository_url")
        repo_path = await self._access_repository(repo_url, context.state)
        await self._report_progress(context.state, "Repository accessed", 20)
        return {"repo_path": repo_path, "repo_url": repo_url}
    
    async def _execute_phase_2_method(self, context: ExecutionContext, previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 2: Pattern scanning - method wrapper."""
        repo_path = previous_results["repository_access"]["repo_path"]
        ai_patterns = await self._scan_patterns(repo_path, context.state)
        await self._report_progress(context.state, "Patterns detected", 40)
        return {"ai_patterns": ai_patterns}
    
    async def _execute_phase_3_method(self, context: ExecutionContext, previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 3: Config extraction - method wrapper."""
        repo_path = previous_results["repository_access"]["repo_path"]
        configs = await self._extract_configs(repo_path, context.state)
        await self._report_progress(context.state, "Configurations extracted", 60)
        return {"configs": configs}
    
    async def _execute_phase_4_method(self, context: ExecutionContext, previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 4: Mapping generation - method wrapper."""
        ai_patterns = previous_results["pattern_scanning"]["ai_patterns"]
        llm_map, tool_map = await self._generate_mappings(ai_patterns, context.state)
        await self._report_progress(context.state, "Mapping complete", 80)
        return {"llm_map": llm_map, "tool_map": tool_map}
    
    async def _execute_phase_5_method(self, context: ExecutionContext, previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 5: Final map creation - method wrapper."""
        repo_url = previous_results["repository_access"]["repo_url"]
        ai_patterns = previous_results["pattern_scanning"]["ai_patterns"]
        configs = previous_results["config_extraction"]["configs"]
        llm_map = previous_results["mapping_generation"]["llm_map"]
        tool_map = previous_results["mapping_generation"]["tool_map"]
        
        result_map = await self._generate_final_map(
            repo_url, ai_patterns, configs, llm_map, tool_map
        )
        await self._report_progress(context.state, "Analysis complete", 100)
        return {"result_map": result_map}
    
    async def _run_sequential_phases(
        self, 
        repo_url: str, 
        state: DeepAgentState
    ) -> TypedAgentResult:
        """Run all phases sequentially."""
        repo_path = await self._execute_phase_1(repo_url, state)
        ai_patterns = await self._execute_phase_2(repo_path, state)
        configs = await self._execute_phase_3(repo_path, state)
        llm_map, tool_map = await self._execute_phase_4(ai_patterns, state)
        result_map = await self._execute_phase_5(
            repo_url, ai_patterns, configs, llm_map, tool_map, state
        )
        return self._create_success_result(result_map)
    
    async def _execute_phase_1(
        self, 
        repo_url: str, 
        state: DeepAgentState
    ) -> str:
        """Phase 1: Clone/access repository."""
        repo_path = await self._access_repository(repo_url, state)
        await self._report_progress(state, "Repository accessed", 20)
        return repo_path
    
    async def _execute_phase_2(
        self, 
        repo_path: str, 
        state: DeepAgentState
    ) -> Dict[str, Any]:
        """Phase 2: Scan for AI patterns."""
        ai_patterns = await self._scan_patterns(repo_path, state)
        await self._report_progress(state, "Patterns detected", 40)
        return ai_patterns
    
    async def _execute_phase_3(
        self, 
        repo_path: str, 
        state: DeepAgentState
    ) -> Dict[str, Any]:
        """Phase 3: Extract configurations."""
        configs = await self._extract_configs(repo_path, state)
        await self._report_progress(state, "Configurations extracted", 60)
        return configs
    
    async def _execute_phase_4(
        self, 
        ai_patterns: Dict[str, Any], 
        state: DeepAgentState
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Phase 4: Map LLM calls and tools."""
        mappings = await self._generate_mappings(ai_patterns, state)
        await self._report_progress(state, "Mapping complete", 80)
        return mappings
    
    async def _generate_mappings(
        self, 
        ai_patterns: Dict[str, Any], 
        state: DeepAgentState
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Generate LLM and tool mappings."""
        llm_map = await self._map_llm_usage(ai_patterns, state)
        tool_map = await self._analyze_tools(ai_patterns, state)
        return llm_map, tool_map
    
    async def _execute_phase_5(
        self,
        repo_url: str,
        ai_patterns: Dict[str, Any],
        configs: Dict[str, Any],
        llm_map: Dict[str, Any],
        tool_map: Dict[str, Any],
        state: DeepAgentState
    ) -> Dict[str, Any]:
        """Phase 5: Generate output map."""
        result_map = await self._generate_final_map(
            repo_url, ai_patterns, configs, llm_map, tool_map
        )
        await self._report_progress(state, "Analysis complete", 100)
        return result_map
    
    async def _generate_final_map(
        self,
        repo_url: str,
        ai_patterns: Dict[str, Any],
        configs: Dict[str, Any],
        llm_map: Dict[str, Any],
        tool_map: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate final AI operations map."""
        return await self._generate_map(
            repo_url, ai_patterns, configs, llm_map, tool_map
        )
    
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
        format_params = self._build_format_params(
            repo_url, patterns, configs, llm_map, tool_map
        )
        return await self.formatter.format_output(**format_params)
    
    def _build_format_params(
        self,
        repo_url: str,
        patterns: Dict[str, Any],
        configs: Dict[str, Any],
        llm_map: Dict[str, Any],
        tool_map: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build formatter parameters."""
        return {
            "repo_url": repo_url,
            "patterns": patterns,
            "configurations": configs,
            "llm_mappings": llm_map,
            "tool_mappings": tool_map,
            "analyzed_at": datetime.now(timezone.utc)
        }
    
    async def _report_progress(
        self, 
        state: DeepAgentState, 
        message: str, 
        progress: int
    ) -> None:
        """Report progress via WebSocket."""
        if self._should_report_progress():
            await self._send_progress_update(message, progress)
    
    def _should_report_progress(self) -> bool:
        """Check if progress should be reported."""
        return bool(self.websocket_manager and self.user_id)
    
    async def _send_progress_update(
        self, 
        message: str, 
        progress: int
    ) -> None:
        """Send progress update via WebSocket."""
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
        metadata = self._build_result_metadata()
        return TypedAgentResult(
            success=True,
            data=result_map,
            error=None,
            metadata=metadata
        )
    
    def _create_error_result(self, error: str) -> TypedAgentResult:
        """Create error result."""
        metadata = self._build_result_metadata()
        return TypedAgentResult(
            success=False,
            data=None,
            error=error,
            metadata=metadata
        )
    
    def _build_result_metadata(self) -> Dict[str, str]:
        """Build result metadata."""
        return {
            "agent": self.name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def handle_delegation(
        self, 
        task: str, 
        context: Dict[str, Any]
    ) -> TypedAgentResult:
        """Handle delegated tasks from supervisor."""
        if task == "analyze_repository":
            return await self._handle_repository_analysis(context)
        elif task == "quick_scan":
            return await self._handle_quick_scan(context)
        else:
            return self._create_error_result(f"Unknown task: {task}")
    
    async def _handle_repository_analysis(
        self, 
        context: Dict[str, Any]
    ) -> TypedAgentResult:
        """Handle repository analysis delegation."""
        return await self.execute(DeepAgentState(), context)
    
    async def _handle_quick_scan(
        self, 
        context: Dict[str, Any]
    ) -> TypedAgentResult:
        """Handle quick scan delegation."""
        file_paths = context.get("file_paths", [])
        patterns = await self.pattern_detector.quick_scan(file_paths)
        return self._create_success_result(patterns)


# Create an alias for GitHubAnalyzerAgent to match expected import in agent_class_initialization.py
GitHubAnalyzerAgent = GitHubAnalyzerService

# Export both names for backwards compatibility
__all__ = ["GitHubAnalyzerService", "GitHubAnalyzerAgent"]