"""
Supply Researcher Agent

Main agent class for supply research with modular operation handling.
Maintains 25-line function limit and single responsibility.
"""

import json
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.executor import (
    BaseExecutionEngine, ExecutionStrategy, ExecutionWorkflowBuilder,
    LambdaExecutionPhase, AgentMethodExecutionPhase
)
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.services.user_execution_context import UserExecutionContext, validate_user_context
# DatabaseSessionManager removed - use SSOT database module get_db() instead
from netra_backend.app.agents.supply_researcher.data_extractor import (
    SupplyDataExtractor,
)
# Supply-specific database operations
from netra_backend.app.agents.supply_researcher.supply_database_manager import SupplyDatabaseManager
from netra_backend.app.agents.supply_researcher.models import ResearchType
from netra_backend.app.agents.supply_researcher.parsers import SupplyRequestParser
from netra_backend.app.agents.supply_researcher.research_engine import (
    SupplyResearchEngine,
)
from netra_backend.app.db.models_postgres import ResearchSession
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.services.supply_research_service import SupplyResearchService


class SupplyResearcherAgent(BaseAgent):
    """Agent for researching and updating AI supply information"""
    
    def __init__(
        self,
        llm_manager: LLMManager,
        db: AsyncSession,
        supply_service: Optional[SupplyResearchService] = None
    ):
        super().__init__(llm_manager, name="SupplyResearcherAgent", 
                         description="Researches and updates AI model supply information using Google Deep Research")
        self._init_database_components(db, supply_service)
        self._init_research_components(db)
    
    def _init_database_components(self, db: AsyncSession, supply_service: Optional[SupplyResearchService]) -> None:
        """Initialize database-related components."""
        self.db = db
        self.supply_service = supply_service or SupplyResearchService(db)
        self.research_timeout = 300
        self.confidence_threshold = 0.7
    
    def _init_research_components(self, db: AsyncSession) -> None:
        """Initialize research-related components."""
        self.parser = SupplyRequestParser()
        self.research_engine = SupplyResearchEngine()
        self.data_extractor = SupplyDataExtractor()
        self.db_manager = SupplyDatabaseManager(db)
        self._init_execution_engine()
    
    def _init_execution_engine(self) -> None:
        """Initialize BaseExecutionEngine with research phases."""
        # Create execution phases for supply research workflow
        phase_1 = AgentMethodExecutionPhase("request_parsing", self, "_execute_parsing_phase")
        phase_2 = AgentMethodExecutionPhase("research_session_creation", self, "_execute_session_creation_phase", ["request_parsing"])
        phase_3 = AgentMethodExecutionPhase("research_execution", self, "_execute_research_phase", ["research_session_creation"])
        phase_4 = AgentMethodExecutionPhase("results_processing", self, "_execute_processing_phase", ["research_execution"])
        
        # Build execution engine with sequential strategy (research needs to be sequential)
        self.execution_engine = ExecutionWorkflowBuilder() \
            .add_phases([phase_1, phase_2, phase_3, phase_4]) \
            .set_strategy(ExecutionStrategy.SEQUENTIAL) \
            .add_pre_execution_hook(self._pre_execution_hook) \
            .add_post_execution_hook(self._post_execution_hook) \
            .build()
    
    async def execute(
        self,
        context: UserExecutionContext,
        stream_updates: bool = False
    ) -> None:
        """Execute supply research using UserExecutionContext."""
        # Validate context
        context = validate_user_context(context)
        
        # Set user context for factory pattern WebSocket events
        self.set_user_context(context)
        
        try:
            # Database session available via context.db_session if needed
            
            # Create execution context for BaseExecutionEngine
            execution_context = ExecutionContext(
                run_id=context.run_id,
                agent_name=self.name,
                state=self._create_compatible_state(context),
                stream_updates=stream_updates,
                thread_id=context.thread_id,
                user_id=context.user_id,
                correlation_id=context.run_id
            )
            
            # Execute using BaseExecutionEngine with phases
            result = await self.execution_engine.execute_phases(execution_context)
            
            if not result.success:
                raise Exception(result.error)
            
            # Store result in context metadata for UserExecutionContext pattern
            if hasattr(execution_context.state, 'supply_research_result'):
                context.metadata['supply_research_result'] = execution_context.state.supply_research_result
                
        except Exception as e:
            await self._handle_execution_error(e, context, stream_updates)
            raise
        finally:
            # Session cleanup handled by context manager automatically
            pass
    
    async def _pre_execution_hook(self, context: ExecutionContext) -> None:
        """Pre-execution hook for setup."""
        logger.info(f"Starting supply research for run_id: {context.run_id}")
    
    async def _post_execution_hook(self, context: ExecutionContext, phase_results: Dict[str, Any]) -> None:
        """Post-execution hook for cleanup."""
        logger.info(f"Supply research completed for run_id: {context.run_id}")
        # Extract final result and store in state (via UserExecutionContext metadata)
        if "results_processing" in phase_results:
            result_data = phase_results["results_processing"]
            if hasattr(context.state, 'supply_research_result'):
                context.state.supply_research_result = result_data.get("final_result", {})
    
    # Phase execution methods for BaseExecutionEngine integration
    async def _execute_parsing_phase(self, context: ExecutionContext, previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 1: Request parsing - method wrapper."""
        request = context.state.user_request or "Provide AI market overview"
        await self._send_parsing_update(context.run_id, context.stream_updates)
        parsed_request = self.parser.parse_natural_language_request(request)
        logger.info(f"Parsed request: {parsed_request}")
        return {"parsed_request": parsed_request, "original_request": request}
    
    async def _execute_session_creation_phase(self, context: ExecutionContext, previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 2: Research session creation - method wrapper."""
        parsed_request = previous_results["request_parsing"]["parsed_request"]
        research_session = await self._create_research_session(parsed_request, context.state)
        return {"research_session": research_session}
    
    async def _execute_research_phase(self, context: ExecutionContext, previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 3: Research execution - method wrapper."""
        parsed_request = previous_results["request_parsing"]["parsed_request"]
        research_session = previous_results["research_session_creation"]["research_session"]
        
        await self._send_research_update(context.run_id, context.stream_updates, parsed_request)
        research_result = await self._conduct_research(parsed_request, research_session)
        return {"research_result": research_result, "research_session": research_session}
    
    async def _execute_processing_phase(self, context: ExecutionContext, previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 4: Results processing - method wrapper."""
        parsed_request = previous_results["request_parsing"]["parsed_request"]
        research_result = previous_results["research_execution"]["research_result"]
        research_session = previous_results["research_execution"]["research_session"]
        
        await self._send_processing_update(context.run_id, context.stream_updates)
        
        result = await self._process_research_results(
            research_result, parsed_request, research_session, 
            context.run_id, context.stream_updates
        )
        
        await self._send_completion_update(context.run_id, context.stream_updates, result)
        return {"final_result": result}
    
    # Legacy method - removed in favor of UserExecutionContext pattern
    # Use execute(context: UserExecutionContext, stream_updates: bool) instead
    
    async def _parse_and_log_request(self, request: str, run_id: str, stream_updates: bool):
        """Parse request and log details."""
        await self._send_parsing_update(run_id, stream_updates)
        parsed_request = self.parser.parse_natural_language_request(request)
        logger.info(f"Parsed request: {parsed_request}")
        return parsed_request
    
    async def _conduct_research_with_updates(self, parsed_request, research_session, run_id: str, stream_updates: bool):
        """Conduct research with status updates."""
        await self._send_research_update(run_id, stream_updates, parsed_request)
        return await self._conduct_research(parsed_request, research_session)
    
    # Legacy method - removed in favor of UserExecutionContext pattern
    # Results are now stored in context.metadata['supply_research_result']
    
    async def process_scheduled_research(
        self,
        research_type: ResearchType,
        providers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Process scheduled research for multiple providers"""
        provider_list = providers or list(self.parser.provider_patterns.keys())
        results = await self._process_providers_research(research_type, provider_list)
        return self._build_scheduled_research_result(research_type, results)
    
    async def _process_providers_research(self, research_type: ResearchType, providers: List[str]) -> List[Dict[str, Any]]:
        """Process research for all providers."""
        results = []
        for provider in providers:
            result = await self._process_single_provider_research(research_type, provider)
            results.append(result)
        return results
    
    async def _process_single_provider_research(self, research_type: ResearchType, provider: str) -> Dict[str, Any]:
        """Process research for a single provider."""
        try:
            context = self._create_scheduled_context(research_type, provider)
            await self.execute(context, False)
            return self._create_success_provider_result(provider, context)
        except Exception as e:
            return self._create_error_provider_result(provider, e)
    
    def _create_success_provider_result(self, provider: str, context: UserExecutionContext) -> Dict[str, Any]:
        """Create successful provider result."""
        result = context.metadata.get('supply_research_result')
        if result:
            return {"provider": provider, "result": result}
        return {"provider": provider, "error": "No result generated"}
    
    def _create_error_provider_result(self, provider: str, error: Exception) -> Dict[str, Any]:
        """Create error provider result."""
        logger.error(f"Scheduled research failed for {provider}: {error}")
        return {"provider": provider, "error": str(error)}
    
    def _build_scheduled_research_result(self, research_type: ResearchType, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build final scheduled research result."""
        return {
            "research_type": research_type.value,
            "providers_processed": len(results),
            "results": results
        }
    
    async def _send_parsing_update(self, run_id: str, stream_updates: bool) -> None:
        """Send parsing update"""
        if stream_updates and self.websocket_manager:
            await self._send_update(run_id, {
                "status": "parsing",
                "message": "Parsing research request..."
            })
    
    async def _create_research_session(
        self,
        parsed_request: Dict[str, Any],
        state: Any
    ) -> ResearchSession:
        """Create research session record"""
        research_query = self.research_engine.generate_research_query(parsed_request)
        research_session = self._build_research_session(research_query, state)
        await self._save_research_session(research_session)
        return research_session
    
    def _build_research_session(self, research_query: str, state: Any) -> ResearchSession:
        """Build research session object."""
        return ResearchSession(
            query=research_query,
            status="pending",
            initiated_by=f"user_{state.user_id}" if hasattr(state, 'user_id') else "system",
            created_at=datetime.now(UTC)
        )
    
    async def _save_research_session(self, research_session: ResearchSession) -> None:
        """Save research session to database."""
        await self.db.add(research_session)
        await self.db.commit()
    
    async def _send_research_update(
        self,
        run_id: str,
        stream_updates: bool,
        parsed_request: Dict[str, Any]
    ) -> None:
        """Send research starting update"""
        if stream_updates and self.websocket_manager:
            await self._send_update(run_id, {
                "status": "researching",
                "message": f"Starting Deep Research for {parsed_request['research_type'].value}..."
            })
    
    async def _conduct_research(
        self,
        parsed_request: Dict[str, Any],
        research_session: ResearchSession
    ) -> Dict[str, Any]:
        """Conduct the actual research"""
        research_query = self.research_engine.generate_research_query(parsed_request)
        return await self._execute_research_workflow(research_query, research_session)
    
    async def _execute_research_workflow(self, research_query: str, research_session: ResearchSession) -> Dict[str, Any]:
        """Execute the research workflow"""
        research_session.status = "researching"
        session_id = await self._initialize_research_session(research_query)
        research_session.session_id = session_id
        return await self._complete_research_execution(research_session, session_id)
    
    async def _initialize_research_session(self, research_query: str) -> str:
        """Initialize research session and get session ID"""
        init_result = await self.research_engine.call_deep_research_api(research_query)
        return init_result.get("session_id")
    
    async def _complete_research_execution(self, research_session: ResearchSession, session_id: str) -> Dict[str, Any]:
        """Complete research execution and update session"""
        research_result = await self.research_engine.call_deep_research_api("Start Research", session_id)
        self._update_research_session(research_session, research_result)
        return research_result
    
    async def _send_processing_update(self, run_id: str, stream_updates: bool) -> None:
        """Send processing update"""
        if stream_updates and self.websocket_manager:
            await self._send_update(run_id, {
                "status": "processing",
                "message": "Processing research results..."
            })
    
    async def _process_research_results(
        self,
        research_result: Dict[str, Any],
        parsed_request: Dict[str, Any],
        research_session: ResearchSession,
        run_id: str,
        stream_updates: bool
    ) -> Dict[str, Any]:
        """Process research results and update database"""
        supply_items, confidence = self._extract_and_score_data(research_result, parsed_request)
        update_result = await self._update_database_if_confident(supply_items, confidence, research_session)
        await self._finalize_research_session(research_session)
        return self._build_final_result(parsed_request, confidence, update_result, research_result)
    
    def _extract_and_score_data(self, research_result: Dict[str, Any], parsed_request: Dict[str, Any]) -> tuple:
        """Extract supply data and calculate confidence score"""
        supply_items = self.data_extractor.extract_supply_data(research_result, parsed_request)
        confidence = self.data_extractor.calculate_confidence_score(research_result, supply_items)
        return supply_items, confidence
    
    async def _update_database_if_confident(self, supply_items, confidence: float, research_session: ResearchSession) -> Dict[str, Any]:
        """Update database if confidence threshold is met"""
        update_result = {"updates_count": 0, "updates": []}
        if confidence >= self.confidence_threshold and supply_items:
            update_result = await self.db_manager.update_database(supply_items, research_session.id)
            research_session.processed_data = json.dumps(supply_items, default=str)
        return update_result
    
    async def _finalize_research_session(self, research_session: ResearchSession) -> None:
        """Finalize research session status"""
        research_session.status = "completed"
        research_session.completed_at = datetime.now(UTC)
        await self.db.commit()
    
    def _build_final_result(self, parsed_request: Dict[str, Any], confidence: float, 
                           update_result: Dict[str, Any], research_result: Dict[str, Any]) -> Dict[str, Any]:
        """Build final result dictionary"""
        return {
            "research_type": parsed_request["research_type"].value,
            "confidence_score": confidence,
            "updates_made": update_result,
            "citations": research_result.get("citations", []),
            "summary": research_result.get("summary", "Research completed")
        }
    
    async def _send_completion_update(
        self,
        run_id: str,
        stream_updates: bool,
        result: Dict[str, Any]
    ) -> None:
        """Send completion update"""
        if stream_updates and self.websocket_manager:
            await self._send_update(run_id, {
                "status": "completed",
                "message": f"Supply research completed. {result['updates_made']['updates_count']} updates made.",
                "result": result
            })
    
    async def _handle_execution_error(
        self,
        error: Exception,
        context: UserExecutionContext,
        stream_updates: bool
    ) -> None:
        """Handle execution errors"""
        logger.error(f"SupplyResearcherAgent execution failed: {error}")
        await self._update_failed_session_if_exists(error)
        await self._send_error_notification(context.run_id, error, stream_updates)
    
    async def _update_failed_session_if_exists(self, error: Exception) -> None:
        """Update research session if it exists"""
        if 'research_session' in locals():
            research_session.status = "failed"
            research_session.error_message = str(error)
            self.db.commit()
    
    def _create_compatible_state(self, context: UserExecutionContext) -> Any:
        """Create compatible state object for BaseExecutionEngine."""
        # Create a simple object with the necessary attributes
        class CompatibleState:
            def __init__(self, context: UserExecutionContext):
                self.user_request = context.metadata.get('user_request', 'Provide AI market overview')
                self.chat_thread_id = context.thread_id
                self.user_id = context.user_id
                self.supply_research_result = None
        
        return CompatibleState(context)
    
    async def _send_error_notification(self, run_id: str, error: Exception, stream_updates: bool) -> None:
        """Send error notification if streaming enabled"""
        if stream_updates and self.websocket_manager:
            await self._send_update(run_id, {
                "status": "failed",
                "message": f"Research failed: {str(error)}"
            })
    
    def _update_research_session(
        self,
        research_session: ResearchSession,
        research_result: Dict[str, Any]
    ) -> None:
        """Update research session with results"""
        self._set_research_session_data(research_session, research_result)
        self._set_research_session_json_fields(research_session, research_result)
    
    def _set_research_session_data(self, research_session: ResearchSession, research_result: Dict[str, Any]) -> None:
        """Set basic research session data"""
        research_session.research_plan = research_result.get("research_plan")
        research_session.raw_results = json.dumps(research_result)
    
    def _set_research_session_json_fields(self, research_session: ResearchSession, research_result: Dict[str, Any]) -> None:
        """Set JSON fields for research session"""
        research_session.questions_answered = json.dumps(research_result.get("questions_answered", []))
        research_session.citations = json.dumps(research_result.get("citations", []))
    
    def _create_scheduled_context(self, research_type: ResearchType, provider: str) -> UserExecutionContext:
        """Create context for scheduled research using SSOT"""
        from shared.id_generation.unified_id_generator import UnifiedIdGenerator
        
        # SSOT COMPLIANCE: Use UnifiedIdGenerator for scheduled context creation
        thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(
            user_id="scheduler", 
            operation=f"scheduled_{research_type.value}_{provider}"
        )
        
        return UserExecutionContext(
            user_id="scheduler",
            thread_id=thread_id,
            run_id=run_id,
            metadata={"user_request": f"Update {research_type.value} for {provider}"}
        )
    
    async def _send_update(self, run_id: str, update: Dict[str, Any]) -> None:
        """Send update via factory pattern for user isolation (inherits from BaseAgent)."""
        try:
            # Use BaseAgent's factory pattern method for user isolation
            emitter = await self._get_user_emitter()
            if not emitter:
                logger.debug("No user context available for SupplyResearcherAgent WebSocket updates - skipping")
                return
            status = update.get('status', 'processing')
            message = update.get('message', '')
            metadata = {"agent_name": "SupplyResearcherAgent", "message": message}
            
            # Map update status to appropriate emitter notification
            if status == 'parsing':
                await emitter.emit_agent_thinking("SupplyResearcherAgent", metadata)
            elif status == 'researching':
                await emitter.emit_tool_executing("deep_research", {
                    "research_type": message,
                    "agent_name": "SupplyResearcherAgent"
                })
            elif status == 'processing':
                await emitter.emit_agent_thinking("SupplyResearcherAgent", metadata)
            elif status == 'completed':
                await emitter.emit_agent_completed("SupplyResearcherAgent", {
                    "result": update.get('result'), 
                    "execution_time_ms": None,
                    "agent_name": "SupplyResearcherAgent"
                })
            elif status == 'failed':
                await emitter.emit_custom_event("agent_error", {
                    "agent_name": "SupplyResearcherAgent",
                    "error_message": message
                })
            else:
                # Custom status updates
                await emitter.emit_custom_event(f"supply_{status}", {
                    "agent_name": "SupplyResearcherAgent",
                    "status": status,
                    **update
                })
            
        except Exception as e:
            logger.error(f"Failed to send WebSocket update via factory pattern: {e}")