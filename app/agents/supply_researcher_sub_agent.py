"""
Supply Researcher Agent - Autonomous AI supply information research and updates
"""

import json
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import re
import aiohttp
from enum import Enum

from app.agents.base import BaseSubAgent
from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager
from app.services.supply_research_service import SupplyResearchService
from app.core.exceptions import NetraException
from app.redis_manager import RedisManager
from app.db.models_postgres import AISupplyItem, ResearchSession, SupplyUpdateLog
from app.schemas import SubAgentLifecycle
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ResearchType(Enum):
    PRICING = "pricing"
    CAPABILITIES = "capabilities"
    AVAILABILITY = "availability"
    MARKET_OVERVIEW = "market_overview"
    NEW_MODEL = "new_model"
    DEPRECATION = "deprecation"


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
        self.redis_manager = None
        self.research_timeout = 300  # 5 minutes
        self.confidence_threshold = 0.7
        
        # Initialize Redis for caching
        try:
            self.redis_manager = RedisManager()
        except Exception as e:
            logger.warning(f"Redis not available for caching: {e}")
        
        # Provider patterns for extraction
        self.provider_patterns = {
            "openai": ["gpt", "davinci", "curie", "babbage", "ada"],
            "anthropic": ["claude"],
            "google": ["gemini", "palm", "bard"],
            "mistral": ["mistral", "mixtral"],
            "cohere": ["command", "generate"],
            "ai21": ["jurassic", "j2"]
        }
    
    def _parse_natural_language_request(self, request: str) -> Dict[str, Any]:
        """Parse natural language request into structured query"""
        request_lower = request.lower()
        
        # Determine research type
        research_type = ResearchType.MARKET_OVERVIEW
        if any(word in request_lower for word in ["price", "pricing", "cost", "dollar", "$"]):
            research_type = ResearchType.PRICING
        elif any(word in request_lower for word in ["capability", "feature", "context", "token"]):
            research_type = ResearchType.CAPABILITIES
        elif any(word in request_lower for word in ["available", "access", "api", "endpoint"]):
            research_type = ResearchType.AVAILABILITY
        elif any(word in request_lower for word in ["new", "release", "announce"]):
            research_type = ResearchType.NEW_MODEL
        elif any(word in request_lower for word in ["deprecat", "sunset", "retire"]):
            research_type = ResearchType.DEPRECATION
        
        # Extract model/provider information
        provider = None
        model_name = None
        
        # Look for specific model mentions
        for prov, patterns in self.provider_patterns.items():
            for pattern in patterns:
                if pattern in request_lower:
                    provider = prov
                    # Extract full model name (e.g., "GPT-5" from "Add GPT-5 pricing")
                    model_pattern = rf"\b{pattern}[-\s]?[\d\.]+\w*\b"
                    match = re.search(model_pattern, request, re.IGNORECASE)
                    if match:
                        model_name = match.group()
                    break
        
        # Extract time frame if mentioned
        timeframe = "current"
        if "latest" in request_lower:
            timeframe = "latest"
        elif "month" in request_lower:
            timeframe = "monthly"
        elif "week" in request_lower:
            timeframe = "weekly"
        
        return {
            "research_type": research_type,
            "provider": provider,
            "model_name": model_name,
            "timeframe": timeframe,
            "original_request": request
        }
    
    def _generate_research_query(self, parsed_request: Dict[str, Any]) -> str:
        """Generate Deep Research query from parsed request"""
        research_type = parsed_request["research_type"]
        provider = parsed_request.get("provider", "all major providers")
        model_name = parsed_request.get("model_name", "models")
        timeframe = parsed_request.get("timeframe", "current")
        
        # Research query templates
        templates = {
            ResearchType.PRICING: (
                f"What is the {timeframe} pricing structure for {provider} {model_name} including:\n"
                "- Cost per million input tokens in USD\n"
                "- Cost per million output tokens in USD\n"
                "- Volume discounts or enterprise pricing tiers\n"
                "- Batch processing rates if available\n"
                "- Fine-tuning costs if applicable\n"
                "Please provide official documentation links and pricing pages."
            ),
            ResearchType.CAPABILITIES: (
                f"What are the technical capabilities of {provider} {model_name}:\n"
                "- Maximum context window size (in tokens)\n"
                "- Maximum output token limit\n"
                "- Supported languages and modalities (text, vision, audio)\n"
                "- Special features (function calling, JSON mode, etc.)\n"
                "- Performance benchmarks (MMLU, HumanEval, etc.)\n"
                "Include comparisons with previous versions."
            ),
            ResearchType.AVAILABILITY: (
                f"What is the current availability status of {provider} {model_name}:\n"
                "- General availability in different regions\n"
                "- API endpoints and base URLs\n"
                "- Access requirements (API key, waitlist, etc.)\n"
                "- Rate limits and quotas\n"
                "- Any deprecation timeline if announced"
            ),
            ResearchType.NEW_MODEL: (
                f"What are the latest AI model releases from {provider}:\n"
                "- New models announced in the past {timeframe}\n"
                "- Release dates and availability status\n"
                "- Key improvements over previous versions\n"
                "- Pricing information\n"
                "- Access requirements"
            ),
            ResearchType.DEPRECATION: (
                f"What AI models from {provider} are being deprecated:\n"
                "- Models scheduled for sunset\n"
                "- Deprecation timelines\n"
                "- Migration paths to newer models\n"
                "- Feature parity comparisons\n"
                "- Cost implications of migration"
            ),
            ResearchType.MARKET_OVERVIEW: (
                f"Provide a comprehensive overview of the {timeframe} AI model market:\n"
                "- Pricing changes across OpenAI, Anthropic, Google, and others\n"
                "- New model releases and announcements\n"
                "- Deprecated or sunset models\n"
                "- Performance comparisons\n"
                "- Market trends and competitive positioning\n"
                "Focus on production-ready API services."
            )
        }
        
        return templates.get(research_type, templates[ResearchType.MARKET_OVERVIEW])
    
    async def _call_deep_research_api(
        self,
        query: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Call Google Deep Research API"""
        # Note: This is a simplified implementation
        # In production, you would use proper Google Cloud credentials
        
        api_endpoint = "https://discoveryengine.googleapis.com/v1/projects/{project_id}/locations/global/collections/default_collection/engines/{app_id}/assistants/default_assistant:streamAssist"
        
        headers = {
            "Authorization": "Bearer {token}",  # Would get from gcloud auth
            "Content-Type": "application/json",
            "X-Goog-User-Project": "{project_id}"
        }
        
        if session_id:
            # Continue existing research session
            payload = {
                "query": {"text": "Start Research"},
                "session": session_id,
                "agentsSpec": {"agentSpecs": {"agentId": "deep_research"}},
                "toolsSpec": {
                    "webGroundingSpec": {}
                }
            }
        else:
            # Initialize new research session
            payload = {
                "query": {"text": query},
                "agentsSpec": {"agentSpecs": {"agentId": "deep_research"}},
                "toolsSpec": {
                    "webGroundingSpec": {}
                }
            }
        
        # Simulate API call (in production, use aiohttp)
        # For now, return mock data
        return {
            "session_id": "mock_session_123",
            "status": "completed",
            "research_plan": f"Researching: {query[:100]}...",
            "questions_answered": [
                {"question": "What is the pricing?", "answer": "Model pricing varies..."},
                {"question": "What are the capabilities?", "answer": "Model supports..."}
            ],
            "citations": [
                {"source": "Official Documentation", "url": "https://example.com/docs"},
                {"source": "Pricing Page", "url": "https://example.com/pricing"}
            ],
            "summary": "Research completed successfully with mock data"
        }
    
    def _extract_supply_data(
        self,
        research_result: Dict[str, Any],
        parsed_request: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract structured supply data from research results"""
        supply_items = []
        
        # Parse research answers for supply information
        for qa in research_result.get("questions_answered", []):
            answer = qa.get("answer", "")
            
            # Extract pricing information
            pricing_pattern = r"\$?([\d,]+\.?\d*)\s*(?:per|/)?\s*(?:1M|million)?\s*(?:input|output)?\s*tokens?"
            pricing_matches = re.findall(pricing_pattern, answer, re.IGNORECASE)
            
            # Extract context window
            context_pattern = r"(\d+)[kK]?\s*(?:token)?\s*context"
            context_matches = re.findall(context_pattern, answer)
            
            # Build supply item
            if pricing_matches or context_matches:
                item = {
                    "provider": parsed_request.get("provider", "unknown"),
                    "model_name": parsed_request.get("model_name", "unknown"),
                    "pricing_input": None,
                    "pricing_output": None,
                    "context_window": None,
                    "last_updated": datetime.utcnow(),
                    "research_source": "Google Deep Research",
                    "confidence_score": 0.8
                }
                
                # Parse pricing
                if len(pricing_matches) >= 2:
                    item["pricing_input"] = Decimal(pricing_matches[0].replace(",", ""))
                    item["pricing_output"] = Decimal(pricing_matches[1].replace(",", ""))
                elif len(pricing_matches) == 1:
                    item["pricing_input"] = Decimal(pricing_matches[0].replace(",", ""))
                
                # Parse context window
                if context_matches:
                    context_size = int(context_matches[0])
                    if context_size < 1000:  # Likely in K tokens
                        context_size *= 1000
                    item["context_window"] = context_size
                
                supply_items.append(item)
        
        return supply_items
    
    def _calculate_confidence_score(
        self,
        research_result: Dict[str, Any],
        extracted_data: List[Dict[str, Any]]
    ) -> float:
        """Calculate confidence score for extracted data"""
        score = 0.5  # Base score
        
        # Increase score based on citations
        citations = research_result.get("citations", [])
        if citations:
            score += min(0.2, len(citations) * 0.05)
        
        # Increase score if official sources mentioned
        for citation in citations:
            if any(word in citation.get("source", "").lower() 
                   for word in ["official", "documentation", "pricing"]):
                score += 0.1
        
        # Increase score based on data completeness
        for item in extracted_data:
            if item.get("pricing_input") and item.get("pricing_output"):
                score += 0.1
            if item.get("context_window"):
                score += 0.05
        
        return min(1.0, score)
    
    async def _update_database(
        self,
        supply_items: List[Dict[str, Any]],
        research_session_id: str
    ) -> Dict[str, Any]:
        """Update database with new supply information"""
        updates_made = []
        
        for item_data in supply_items:
            try:
                # Check for existing item
                existing = self.db.query(AISupplyItem).filter(
                    AISupplyItem.provider == item_data["provider"],
                    AISupplyItem.model_name == item_data["model_name"]
                ).first()
                
                if existing:
                    # Log changes
                    changes = []
                    if item_data.get("pricing_input") and existing.pricing_input != item_data["pricing_input"]:
                        changes.append({
                            "field": "pricing_input",
                            "old": str(existing.pricing_input),
                            "new": str(item_data["pricing_input"])
                        })
                        existing.pricing_input = item_data["pricing_input"]
                    
                    if item_data.get("pricing_output") and existing.pricing_output != item_data["pricing_output"]:
                        changes.append({
                            "field": "pricing_output",
                            "old": str(existing.pricing_output),
                            "new": str(item_data["pricing_output"])
                        })
                        existing.pricing_output = item_data["pricing_output"]
                    
                    if changes:
                        existing.last_updated = datetime.utcnow()
                        existing.research_source = item_data["research_source"]
                        existing.confidence_score = item_data["confidence_score"]
                        
                        # Create update logs
                        for change in changes:
                            log = SupplyUpdateLog(
                                supply_item_id=existing.id,
                                field_updated=change["field"],
                                old_value=change["old"],
                                new_value=change["new"],
                                research_session_id=research_session_id,
                                update_reason="Research update",
                                updated_by="SupplyResearcherAgent",
                                updated_at=datetime.utcnow()
                            )
                            self.db.add(log)
                        
                        updates_made.append({
                            "action": "updated",
                            "model": f"{existing.provider} {existing.model_name}",
                            "changes": changes
                        })
                else:
                    # Create new item
                    new_item = AISupplyItem(**item_data)
                    self.db.add(new_item)
                    updates_made.append({
                        "action": "created",
                        "model": f"{item_data['provider']} {item_data['model_name']}"
                    })
            
            except Exception as e:
                logger.error(f"Failed to update supply item: {e}")
        
        # Commit changes
        if updates_made:
            self.db.commit()
        
        return {
            "updates_count": len(updates_made),
            "updates": updates_made
        }
    
    async def execute(
        self,
        state: DeepAgentState,
        run_id: str,
        stream_updates: bool = False
    ) -> None:
        """Execute supply research based on request"""
        try:
            # Get request from state
            request = state.user_request or "Provide AI market overview"
            
            # Send initial update
            if stream_updates and self.websocket_manager:
                await self._send_update(run_id, {
                    "status": "parsing",
                    "message": "Parsing research request..."
                })
            
            # Parse natural language request
            parsed_request = self._parse_natural_language_request(request)
            logger.info(f"Parsed request: {parsed_request}")
            
            # Generate research query
            research_query = self._generate_research_query(parsed_request)
            
            # Create research session record
            research_session = ResearchSession(
                query=research_query,
                status="pending",
                initiated_by=f"user_{state.user_id}" if hasattr(state, 'user_id') else "system",
                created_at=datetime.utcnow()
            )
            self.db.add(research_session)
            self.db.commit()
            
            # Send research starting update
            if stream_updates and self.websocket_manager:
                await self._send_update(run_id, {
                    "status": "researching",
                    "message": f"Starting Deep Research for {parsed_request['research_type'].value}..."
                })
            
            # Call Deep Research API (Phase 1: Initialize)
            research_session.status = "researching"
            init_result = await self._call_deep_research_api(research_query)
            session_id = init_result.get("session_id")
            research_session.session_id = session_id
            
            # Call Deep Research API (Phase 2: Execute Research)
            research_result = await self._call_deep_research_api("Start Research", session_id)
            
            # Update research session
            research_session.research_plan = research_result.get("research_plan")
            research_session.questions_answered = json.dumps(research_result.get("questions_answered", []))
            research_session.raw_results = json.dumps(research_result)
            research_session.citations = json.dumps(research_result.get("citations", []))
            
            # Send processing update
            if stream_updates and self.websocket_manager:
                await self._send_update(run_id, {
                    "status": "processing",
                    "message": "Processing research results..."
                })
            
            # Extract supply data from research
            supply_items = self._extract_supply_data(research_result, parsed_request)
            
            # Calculate confidence score
            confidence = self._calculate_confidence_score(research_result, supply_items)
            
            # Update database if confidence is sufficient
            update_result = {"updates_count": 0, "updates": []}
            if confidence >= self.confidence_threshold and supply_items:
                update_result = await self._update_database(supply_items, research_session.id)
                research_session.processed_data = json.dumps(supply_items, default=str)
            
            # Complete research session
            research_session.status = "completed"
            research_session.completed_at = datetime.utcnow()
            self.db.commit()
            
            # Prepare final result
            result = {
                "research_type": parsed_request["research_type"].value,
                "confidence_score": confidence,
                "updates_made": update_result,
                "citations": research_result.get("citations", []),
                "summary": research_result.get("summary", "Research completed")
            }
            
            # Store result in state
            state.supply_research_result = result
            
            # Send completion update
            if stream_updates and self.websocket_manager:
                await self._send_update(run_id, {
                    "status": "completed",
                    "message": f"Supply research completed. {update_result['updates_count']} updates made.",
                    "result": result
                })
            
            logger.info(f"SupplyResearcherAgent completed for run_id: {run_id}")
            
        except Exception as e:
            logger.error(f"SupplyResearcherAgent execution failed: {e}")
            
            # Update research session as failed
            if 'research_session' in locals():
                research_session.status = "failed"
                research_session.error_message = str(e)
                self.db.commit()
            
            # Store error in state
            state.supply_research_result = {
                "status": "error",
                "error": str(e)
            }
            
            if stream_updates and self.websocket_manager:
                await self._send_update(run_id, {
                    "status": "failed",
                    "message": f"Research failed: {str(e)}"
                })
            
            raise
    
    async def process_scheduled_research(
        self,
        research_type: ResearchType,
        providers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Process scheduled research for multiple providers"""
        if providers is None:
            providers = list(self.provider_patterns.keys())
        
        results = []
        for provider in providers:
            try:
                # Create a mock state for scheduled research
                state = DeepAgentState(
                    user_request=f"Update {research_type.value} for {provider}",
                    chat_thread_id=f"scheduled_{research_type.value}",
                    user_id="scheduler"
                )
                
                # Execute research
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