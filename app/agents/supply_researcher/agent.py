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
        super().__init__(
            llm_manager,
            name="SupplyResearcherAgent",
            description="Researches and updates AI model supply information using Google Deep Research"
        )
        self.db = db
        self.supply_service = supply_service or SupplyResearchService(db)
        self.research_timeout = 300
        self.confidence_threshold = 0.7
        
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
            request = state.user_request or "Provide AI market overview"
            
            await self._send_parsing_update(run_id, stream_updates)
            parsed_request = self.parser.parse_natural_language_request(request)
            logger.info(f"Parsed request: {parsed_request}")
            
            research_session = await self._create_research_session(parsed_request, state)
            
            await self._send_research_update(run_id, stream_updates, parsed_request)
            research_result = await self._conduct_research(parsed_request, research_session)
            
            await self._send_processing_update(run_id, stream_updates)
            result = await self._process_research_results(
                research_result, parsed_request, research_session, run_id, stream_updates
            )
            
            state.supply_research_result = result
            await self._send_completion_update(run_id, stream_updates, result)
            
            logger.info(f"SupplyResearcherAgent completed for run_id: {run_id}")
            
        except Exception as e:
            await self._handle_execution_error(e, state, run_id, stream_updates)
            raise
    
    async def process_scheduled_research(
        self,
        research_type: ResearchType,
        providers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Process scheduled research for multiple providers"""
        if providers is None:
            providers = list(self.parser.provider_patterns.keys())
        
        results = []
        for provider in providers:
            try:
                state = self._create_scheduled_state(research_type, provider)
                await self.execute(state, f"scheduled_{provider}_{datetime.now().timestamp()}", False)
                
                if hasattr(state, 'supply_research_result'):
                    results.append({
                        "provider": provider,
                        "result": state.supply_research_result
                    })
            
            except Exception as e:
                logger.error(f"Scheduled research failed for {provider}: {e}")
                results.append({
                    "provider": provider,
                    "error": str(e)
                })
        
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
        
        research_session = ResearchSession(
            query=research_query,
            status="pending",
            initiated_by=f"user_{state.user_id}" if hasattr(state, 'user_id') else "system",
            created_at=datetime.now(UTC)
        )
        self.db.add(research_session)
        self.db.commit()
        
        return research_session
    
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
        
        research_session.status = "researching"
        init_result = await self.research_engine.call_deep_research_api(research_query)
        session_id = init_result.get("session_id")
        research_session.session_id = session_id
        
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
        supply_items = self.data_extractor.extract_supply_data(research_result, parsed_request)
        confidence = self.data_extractor.calculate_confidence_score(research_result, supply_items)
        
        update_result = {"updates_count": 0, "updates": []}
        if confidence >= self.confidence_threshold and supply_items:
            update_result = await self.db_manager.update_database(supply_items, research_session.id)
            research_session.processed_data = json.dumps(supply_items, default=str)
        
        research_session.status = "completed"
        research_session.completed_at = datetime.now(UTC)
        self.db.commit()
        
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
        
        if 'research_session' in locals():
            research_session.status = "failed"
            research_session.error_message = str(error)
            self.db.commit()
        
        state.supply_research_result = {
            "status": "error",
            "error": str(error)
        }
        
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
        research_session.research_plan = research_result.get("research_plan")
        research_session.questions_answered = json.dumps(research_result.get("questions_answered", []))
        research_session.raw_results = json.dumps(research_result)
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
                await self.websocket_manager.send_agent_update(
                    run_id,
                    "supply_researcher",
                    update
                )
            except Exception as e:
                logger.error(f"Failed to send WebSocket update: {e}")