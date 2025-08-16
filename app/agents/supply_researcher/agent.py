"""
Supply Researcher Agent

Main agent class for supply research with modular operation handling.
Maintains 8-line function limit and single responsibility.
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from app.agents.base import BaseSubAgent
from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager
from app.services.supply_research_service import SupplyResearchService
from app.db.models_postgres import ResearchSession
from app.logging_config import central_logger as logger
from .models import ResearchType
from .parsers import SupplyRequestParser
from .research_engine import SupplyResearchEngine
from .data_extractor import SupplyDataExtractor
from .database_manager import SupplyDatabaseManager


class SupplyResearcherAgent(BaseSubAgent):
    """Agent for researching and updating AI supply information"""
    
    def __init__(
        self,
        llm_manager: LLMManager,
        db: Session,
        supply_service: Optional[SupplyResearchService] = None
    ):
        super().__init__(llm_manager, name="SupplyResearcherAgent", 
                        description="Researches and updates AI model supply information using Google Deep Research")
        self._init_database_components(db, supply_service)
        self._init_research_components(db)
    
    def _init_database_components(self, db: Session, supply_service: Optional[SupplyResearchService]) -> None:
        """Initialize database-related components."""
        self.db = db
        self.supply_service = supply_service or SupplyResearchService(db)
        self.research_timeout = 300
        self.confidence_threshold = 0.7
    
    def _init_research_components(self, db: Session) -> None:
        """Initialize research-related components."""
        self.parser = SupplyRequestParser()
        self.research_engine = SupplyResearchEngine()
        self.data_extractor = SupplyDataExtractor()
        self.db_manager = SupplyDatabaseManager(db)
    
    async def execute(
        self,
        state: DeepAgentState,
        run_id: str,
        stream_updates: bool = False
    ) -> None:
        """Execute supply research based on request"""
        try:
            await self._execute_research_pipeline(state, run_id, stream_updates)
        except Exception as e:
            await self._handle_execution_error(e, state, run_id, stream_updates)
            raise
    
    async def _execute_research_pipeline(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute the main research pipeline."""
        request = state.user_request or "Provide AI market overview"
        parsed_request = await self._parse_and_log_request(request, run_id, stream_updates)
        research_session = await self._create_research_session(parsed_request, state)
        research_result = await self._conduct_research_with_updates(parsed_request, research_session, run_id, stream_updates)
        result = await self._process_and_finalize_results(research_result, parsed_request, research_session, run_id, stream_updates, state)
        logger.info(f"SupplyResearcherAgent completed for run_id: {run_id}")
    
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
    
    async def _process_and_finalize_results(self, research_result, parsed_request, research_session, run_id: str, stream_updates: bool, state: DeepAgentState):
        """Process results and finalize state."""
        await self._send_processing_update(run_id, stream_updates)
        result = await self._process_research_results(research_result, parsed_request, research_session, run_id, stream_updates)
        state.supply_research_result = result
        await self._send_completion_update(run_id, stream_updates, result)
        return result
    
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
            state = self._create_scheduled_state(research_type, provider)
            await self.execute(state, f"scheduled_{provider}_{datetime.now().timestamp()}", False)
            return self._create_success_provider_result(provider, state)
        except Exception as e:
            return self._create_error_provider_result(provider, e)
    
    def _create_success_provider_result(self, provider: str, state: DeepAgentState) -> Dict[str, Any]:
        """Create successful provider result."""
        if hasattr(state, 'supply_research_result'):
            return {"provider": provider, "result": state.supply_research_result}
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
        state: DeepAgentState
    ) -> ResearchSession:
        """Create research session record"""
        research_query = self.research_engine.generate_research_query(parsed_request)
        research_session = self._build_research_session(research_query, state)
        self._save_research_session(research_session)
        return research_session
    
    def _build_research_session(self, research_query: str, state: DeepAgentState) -> ResearchSession:
        """Build research session object."""
        return ResearchSession(
            query=research_query,
            status="pending",
            initiated_by=f"user_{state.user_id}" if hasattr(state, 'user_id') else "system",
            created_at=datetime.now(UTC)
        )
    
    def _save_research_session(self, research_session: ResearchSession) -> None:
        """Save research session to database."""
        self.db.add(research_session)
        self.db.commit()
    
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
        self._finalize_research_session(research_session)
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
    
    def _finalize_research_session(self, research_session: ResearchSession) -> None:
        """Finalize research session status"""
        research_session.status = "completed"
        research_session.completed_at = datetime.now(UTC)
        self.db.commit()
    
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
        state: DeepAgentState,
        run_id: str,
        stream_updates: bool
    ) -> None:
        """Handle execution errors"""
        logger.error(f"SupplyResearcherAgent execution failed: {error}")
        await self._update_failed_session_if_exists(error)
        self._store_error_result(error, state)
        await self._send_error_notification(run_id, error, stream_updates)
    
    async def _update_failed_session_if_exists(self, error: Exception) -> None:
        """Update research session if it exists"""
        if 'research_session' in locals():
            research_session.status = "failed"
            research_session.error_message = str(error)
            self.db.commit()
    
    def _store_error_result(self, error: Exception, state: DeepAgentState) -> None:
        """Store error result in state"""
        state.supply_research_result = {
            "status": "error",
            "error": str(error)
        }
    
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
    
    def _create_scheduled_state(self, research_type: ResearchType, provider: str) -> DeepAgentState:
        """Create state for scheduled research"""
        return DeepAgentState(
            user_request=f"Update {research_type.value} for {provider}",
            chat_thread_id=f"scheduled_{research_type.value}",
            user_id="scheduler"
        )
    
    async def _send_update(self, run_id: str, update: Dict[str, Any]) -> None:
        """Send update via WebSocket manager"""
        if self.websocket_manager:
            try:
                await self._send_websocket_update(run_id, update)
            except Exception as e:
                logger.error(f"Failed to send WebSocket update: {e}")
    
    async def _send_websocket_update(self, run_id: str, update: Dict[str, Any]) -> None:
        """Send WebSocket update with proper parameters"""
        await self.websocket_manager.send_agent_update(
            run_id,
            "supply_researcher",
            update
        )