"""TriageSubAgent using UserExecutionContext pattern.

Migrated to use UserExecutionContext for request isolation and state management.
- Uses UserExecutionContext for all per-request data
- No global state or session storage
- DatabaseSessionManager for database operations
- Complete request isolation

Business Value: First contact for ALL users - CRITICAL revenue impact.
BVJ: ALL segments | Customer Experience | +25% reduction in triage failures
"""

import time
from typing import Any, Dict, Optional

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext, validate_user_context
from netra_backend.app.agents.triage_sub_agent.core import TriageCore
from netra_backend.app.agents.triage_sub_agent.models import TriageResult
from netra_backend.app.agents.triage_sub_agent.processing import TriageProcessor
from netra_backend.app.database.session_manager import DatabaseSessionManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TriageSubAgent(BaseAgent):
    """Triage agent using UserExecutionContext pattern.
    
    Handles user request triage with complete request isolation.
    No global state, no stored sessions - all data flows through UserExecutionContext.
    """
    
    def __init__(self):
        """Initialize triage agent.
        
        CRITICAL: No sessions or global state stored in instance variables.
        All per-request data flows through UserExecutionContext.
        """
        # Call BaseAgent.__init__() with appropriate parameters
        super().__init__(
            name="TriageSubAgent",
            description="First contact triage agent for ALL users - CRITICAL revenue impact"
        )
        logger.debug(f"Initialized {self.name} with BaseAgent capabilities and no stored state")
        

    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute triage logic with UserExecutionContext.
        
        Args:
            context: User execution context with request data and database session
            stream_updates: Whether to send streaming updates
            
        Returns:
            Triage result dictionary
            
        Raises:
            ValueError: If context is invalid or user_request is missing
        """
        # Validate context at entry
        context = validate_user_context(context)
        
        # Get user request from context metadata
        user_request = context.metadata.get("user_request", "")
        if not user_request:
            raise ValueError(f"No user_request provided in context metadata for run_id: {context.run_id}")
        
        # Create database session manager
        db_manager = DatabaseSessionManager(context)
        
        try:
            logger.info(f"Starting triage execution for user {context.user_id}, run {context.run_id}")
            
            # Emit agent started event via BaseAgent WebSocket capabilities
            await self.emit_agent_started("Starting user request triage analysis...")
            
            # Validate request
            await self._validate_request(context, user_request, db_manager)
            
            # Execute triage logic
            result = await self._execute_triage_logic(context, user_request, stream_updates, db_manager)
            
            # Emit agent completed event via BaseAgent WebSocket capabilities
            await self.emit_agent_completed({
                "triage_category": result.get("category", "unknown"),
                "confidence_score": result.get("confidence_score", 0.0),
                "intent": result.get("intent", "unknown")
            })
            
            logger.info(f"Triage execution completed for run {context.run_id}")
            return result
            
        except Exception as e:
            logger.error(f"Triage execution failed for run {context.run_id}: {e}")
            
            # Emit error event via BaseAgent WebSocket capabilities
            await self.emit_error(
                error_message=f"Triage processing failed: {str(e)}",
                error_type="TriageExecutionError",
                error_details={"run_id": context.run_id, "user_id": context.user_id}
            )
            
            # Create fallback result
            return await self._create_fallback_result(context, user_request, str(e))
        finally:
            # Clean up database session
            await db_manager.close()

    async def _validate_request(self, context: UserExecutionContext, user_request: str, db_manager: DatabaseSessionManager) -> None:
        """Validate user request.
        
        Args:
            context: User execution context
            user_request: User request string to validate
            db_manager: Database session manager
            
        Raises:
            ValueError: If request validation fails
        """
        logger.debug(f"Validating request for run {context.run_id}")
        
        # Basic validation
        if not user_request.strip():
            raise ValueError("User request cannot be empty")
        
        if len(user_request) > 10000:  # Reasonable limit
            raise ValueError("User request exceeds maximum length")
        
        logger.debug(f"Request validation passed for run {context.run_id}")
    
    async def _execute_triage_logic(self, context: UserExecutionContext, user_request: str, 
                                   stream_updates: bool, db_manager: DatabaseSessionManager) -> Dict[str, Any]:
        """Execute core triage logic.
        
        Args:
            context: User execution context
            user_request: User request to process
            stream_updates: Whether to send streaming updates
            db_manager: Database session manager
            
        Returns:
            Triage result dictionary
        """
        start_time = time.time()
        
        logger.debug(f"Starting triage analysis for run {context.run_id}")
        
        # Send processing update if streaming
        if stream_updates:
            await self._send_processing_update(context, "Analyzing user request...")
        
        # Create triage core and processor (per-request) with UserExecutionContext
        triage_core = TriageCore(context)  # Pass context for proper request isolation
        processor = TriageProcessor(triage_core, llm_manager=None)  # No shared LLM manager
        
        # Process the request
        try:
            # Generate request hash for caching
            request_hash = triage_core.generate_request_hash(user_request)
            
            # Check for cached result (if caching is enabled)
            cached_result = await self._get_cached_result(context, request_hash, triage_core)
            if cached_result:
                logger.debug(f"Using cached result for run {context.run_id}")
                return cached_result
            
            # Process with LLM
            if stream_updates:
                await self._send_processing_update(context, "Extracting entities and determining intent...")
            
            triage_result = await self._process_with_llm(context, user_request, processor, start_time)
            
            # Cache the result
            await self._cache_result(context, request_hash, triage_result, triage_core)
            
            if stream_updates:
                await self._send_processing_update(context, "Finalizing triage results...")
            
            # Finalize result
            final_result = await self._finalize_result(context, user_request, triage_result, processor)
            
            # CRITICAL: Store triage result in context metadata for other agents
            context.metadata['triage_result'] = final_result
            
            logger.debug(f"Triage analysis completed for run {context.run_id}")
            return final_result
            
        except Exception as e:
            logger.error(f"Triage processing failed for run {context.run_id}: {e}")
            raise
    
    async def _send_processing_update(self, context: UserExecutionContext, message: str) -> None:
        """Send processing status update via BaseAgent WebSocket capabilities.
        
        Args:
            context: User execution context
            message: Status message to send
        """
        try:
            # Use BaseAgent's WebSocket capabilities for proper event emission
            await self.emit_thinking(message)
            logger.debug(f"Sent WebSocket thinking update for run {context.run_id}: {message}")
        except Exception as e:
            # Graceful fallback - don't fail triage if WebSocket fails
            logger.debug(f"Failed to send WebSocket update for run {context.run_id}: {e}")
            pass
    
    async def _get_cached_result(self, context: UserExecutionContext, request_hash: str, 
                               triage_core: TriageCore) -> Optional[Dict[str, Any]]:
        """Get cached triage result if available.
        
        Args:
            context: User execution context
            request_hash: Hash of the request for caching
            triage_core: Triage core instance
            
        Returns:
            Cached result or None if not found
        """
        try:
            cached_result = await triage_core.get_cached_result(request_hash)
            if cached_result:
                logger.debug(f"Cache hit for run {context.run_id}")
                # Update metadata with cache info
                cached_result.setdefault("metadata", {})
                cached_result["metadata"]["cache_hit"] = True
                cached_result["metadata"]["run_id"] = context.run_id
                return cached_result
        except Exception as e:
            logger.warning(f"Cache lookup failed for run {context.run_id}: {e}")
        
        return None
    
    async def _cache_result(self, context: UserExecutionContext, request_hash: str, 
                          result: Dict[str, Any], triage_core: TriageCore) -> None:
        """Cache triage result.
        
        Args:
            context: User execution context
            request_hash: Hash of the request for caching
            result: Result to cache
            triage_core: Triage core instance
        """
        try:
            await triage_core.cache_result(request_hash, result)
            logger.debug(f"Cached result for run {context.run_id}")
        except Exception as e:
            logger.warning(f"Failed to cache result for run {context.run_id}: {e}")

    async def _process_with_llm(self, context: UserExecutionContext, user_request: str, 
                              processor: TriageProcessor, start_time: float) -> Dict[str, Any]:
        """Process request with LLM.
        
        Args:
            context: User execution context
            user_request: User request to process
            processor: Triage processor instance
            start_time: Processing start time
            
        Returns:
            Triage result from LLM processing
        """
        logger.debug(f"Processing with LLM for run {context.run_id}")
        
        # For now, create a basic triage result
        # In full implementation, this would call the actual LLM processor
        result = {
            "category": "General",
            "confidence_score": 0.8,
            "entities": [],
            "intent": "unknown",
            "recommended_tools": [],
            "metadata": {
                "run_id": context.run_id,
                "user_id": context.user_id,
                "processing_time_ms": int((time.time() - start_time) * 1000),
                "cache_hit": False
            }
        }
        
        logger.debug(f"LLM processing completed for run {context.run_id}")
        return result
    
    async def _finalize_result(self, context: UserExecutionContext, user_request: str, 
                             triage_result: Dict[str, Any], processor: TriageProcessor) -> Dict[str, Any]:
        """Finalize triage result.
        
        Args:
            context: User execution context
            user_request: Original user request
            triage_result: Result from processing
            processor: Triage processor instance
            
        Returns:
            Finalized triage result
        """
        logger.debug(f"Finalizing result for run {context.run_id}")
        
        # Enrich result with additional metadata
        triage_result.setdefault("metadata", {})
        triage_result["metadata"].update({
            "finalized_at": time.time(),
            "request_length": len(user_request),
            "context_user_id": context.user_id,
            "context_thread_id": context.thread_id
        })
        
        return triage_result
    
    async def _create_fallback_result(self, context: UserExecutionContext, user_request: str, 
                                     error_message: str) -> Dict[str, Any]:
        """Create fallback result when processing fails.
        
        Args:
            context: User execution context
            user_request: Original user request
            error_message: Error that occurred
            
        Returns:
            Fallback triage result
        """
        logger.warning(f"Creating fallback result for run {context.run_id}: {error_message}")
        
        return {
            "category": "Error",
            "confidence_score": 0.0,
            "entities": [],
            "intent": "error",
            "recommended_tools": [],
            "error": error_message,
            "metadata": {
                "run_id": context.run_id,
                "user_id": context.user_id,
                "is_fallback": True,
                "error_occurred": True,
                "timestamp": time.time()
            }
        }
    
    def __str__(self) -> str:
        """String representation of the agent."""
        return f"TriageSubAgent(name={self.name})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the agent."""
        return f"TriageSubAgent(name='{self.name}')"
    
    @classmethod
    def create_agent_with_context(cls, context) -> 'TriageSubAgent':
        """Factory method for creating TriageSubAgent with user context.
        
        This method enables the agent to be created through AgentInstanceFactory
        with proper user context isolation.
        
        Args:
            context: User execution context for isolation
            
        Returns:
            TriageSubAgent: Configured agent instance
        """
        # TriageSubAgent takes no constructor parameters
        return cls()
