"""Golden Pattern SummaryExtractorSubAgent - Clean business logic only (<200 lines).

Golden Pattern Implementation:
- Inherits reliability management, execution patterns, WebSocket events from BaseAgent
- Contains ONLY summary extraction business logic
- Clean single inheritance pattern
- No infrastructure duplication
- Proper AgentError handling
- <200 lines total

Business Value: Extracts actionable summaries from data to help users understand insights.
BVJ: ALL segments | User Experience | Enables users to quickly understand complex data through AI-powered summaries
"""

import json
import time
from typing import Any, Dict, List, Optional, Union

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.agent_error_types import AgentValidationError
from netra_backend.app.core.exceptions_agent import AgentError
from netra_backend.app.agents.input_validation import validate_agent_input
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext, validate_user_context
# DatabaseSessionManager removed - use SSOT database module get_db() instead
from netra_backend.app.agents.utils import extract_json_from_response, extract_thread_id
from netra_backend.app.llm.observability import (
    generate_llm_correlation_id,
    log_agent_input,
    log_agent_output,
    start_llm_heartbeat,
    stop_llm_heartbeat,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SummaryExtractorSubAgent(BaseAgent):
    """SummaryExtractorSubAgent using UserExecutionContext pattern.
    
    Migrated to use UserExecutionContext for request isolation and state management.
    - Uses UserExecutionContext for all per-request data
    - No global state or session storage
    - DatabaseSessionManager for database operations
    - Complete request isolation
    
    Extracts actionable summaries from various data sources to provide users
    with clear, concise insights that enable quick understanding and decision-making.
    """
    
    def __init__(self):
        # Initialize BaseAgent
        super().__init__(
            name="SummaryExtractorSubAgent", 
            description="Summary extraction agent using UserExecutionContext pattern",
            enable_reliability=False,  # DISABLED: Was hiding errors - see AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md
            enable_execution_engine=True,
            enable_caching=True,
        )

    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute summary extraction using UserExecutionContext.
        
        Args:
            context: User execution context with request data
            stream_updates: Whether to send streaming updates
            
        Returns:
            Summary extraction results
        """
        # Validate context
        context = validate_user_context(context)
        
        try:
            # Create database session manager (stub implementation)
            session_mgr = DatabaseSessionManager()
            
            # Validate preconditions
            if not await self._validate_preconditions(context):
                raise AgentValidationError("No data available to extract summaries from")
                
            # Execute core logic
            result = await self._execute_core_logic(context)
            return result
            
        except Exception as e:
            await self.emit_error(f"Summary extraction failed: {str(e)}")
            error_msg = f"Summary extraction failed: {str(e)}"
            self.logger.error(f"{error_msg} for run_id: {context.run_id}")
            raise AgentError(error_msg, context={"run_id": context.run_id})
        finally:
            # Ensure proper cleanup
            try:
                if 'session_mgr' in locals():
                    await session_mgr.cleanup()
            except Exception as cleanup_e:
                logger.error(f"Session cleanup error: {cleanup_e}")
    
    async def _validate_preconditions(self, context: UserExecutionContext) -> bool:
        """Validate execution preconditions for summary extraction."""
        # Check for data to summarize - can be from various sources in context metadata
        data_sources = [
            (context.metadata.get('data_result'), "data_result"),
            (context.metadata.get('triage_result'), "triage_result"), 
            (context.metadata.get('optimizations_result'), "optimizations_result"),
            (context.metadata.get('action_plan_result'), "action_plan_result"),
            (context.metadata.get('raw_data'), "raw_data"),
            (context.metadata.get('analysis_data'), "analysis_data")
        ]
        
        available_data = [(data, name) for data, name in data_sources if data]
        if not available_data:
            error_msg = "No data available to extract summaries from"
            self.logger.warning(f"{error_msg} for run_id: {context.run_id}")
            return False
            
        return True
    
    async def _execute_core_logic(self, context: UserExecutionContext) -> Dict[str, Any]:
        """Execute core summary extraction logic with WebSocket events."""
        # Emit thinking events for user visibility
        await self.emit_thinking("Starting intelligent summary extraction from your data")
        await self.emit_thinking("Analyzing available data sources for key insights...")
        
        # Collect and analyze available data
        await self.emit_progress("Collecting data from all available sources...")
        collected_data = self._collect_available_data(context)
        
        await self.emit_thinking(f"Found {len(collected_data)} data sources to summarize")
        
        # Extract summaries from each data source
        await self.emit_progress("Extracting key insights and patterns...")
        summaries = await self._extract_summaries_from_data(collected_data, context.run_id)
        
        # Generate comprehensive summary
        await self.emit_thinking("Synthesizing findings into comprehensive summary...")
        comprehensive_summary = await self._generate_comprehensive_summary(summaries, context.run_id)
        
        # Process and format results
        await self.emit_progress("Formatting summary results for optimal readability...")
        result = self._format_summary_result(comprehensive_summary, summaries, collected_data)
        
        # Store result in context metadata
        context.metadata['summary_result'] = result
        
        # Send completion update
        await self._send_summary_completion_update(context.run_id, True, result)
        
        await self.emit_progress("Summary extraction completed successfully", is_complete=True)
        return result

    def _collect_available_data(self, context: UserExecutionContext) -> Dict[str, Any]:
        """Collect all available data sources for summarization."""
        collected = {}
        
        # Collect from various context metadata
        data_mappings = {
            'data_analysis': context.metadata.get('data_result'),
            'triage_analysis': context.metadata.get('triage_result'),
            'optimizations': context.metadata.get('optimizations_result'), 
            'action_plan': context.metadata.get('action_plan_result'),
            'raw_data': context.metadata.get('raw_data'),
            'analysis_data': context.metadata.get('analysis_data'),
            'user_request': context.metadata.get('user_request')
        }
        
        for key, data in data_mappings.items():
            if data:
                collected[key] = data
                
        return collected

    async def _extract_summaries_from_data(self, collected_data: Dict[str, Any], run_id: str) -> Dict[str, Dict[str, Any]]:
        """Extract individual summaries from each data source."""
        summaries = {}
        
        for source_name, source_data in collected_data.items():
            await self.emit_thinking(f"Extracting key points from {source_name}...")
            
            try:
                summary = await self._summarize_data_source(source_name, source_data, run_id)
                summaries[source_name] = summary
                await self.emit_progress(f"Extracted {len(summary.get('key_points', []))} key points from {source_name}")
                
            except Exception as e:
                self.logger.warning(f"Failed to summarize {source_name}: {str(e)}")
                summaries[source_name] = {
                    'key_points': [f"Data available but summarization failed: {str(e)}"],
                    'summary': f"Raw data from {source_name} (processing error)",
                    'confidence': 0.3
                }
        
        return summaries

    async def _summarize_data_source(self, source_name: str, source_data: Any, run_id: str) -> Dict[str, Any]:
        """Summarize a single data source using AI."""
        # Build prompt for AI summarization
        prompt = self._build_summarization_prompt(source_name, source_data)
        correlation_id = generate_llm_correlation_id()
        
        # Execute LLM with observability
        try:
            start_llm_heartbeat(correlation_id, "SummaryExtractorSubAgent")
            log_agent_input("SummaryExtractorSubAgent", "LLM", len(prompt), correlation_id)
            
            response = await self.llm_manager.query_async(prompt, max_tokens=500)
            
            log_agent_output("LLM", "SummaryExtractorSubAgent", len(response) if response else 0, "success", correlation_id)
            
            # Parse the response
            parsed_summary = self._parse_summary_response(response, source_name)
            return parsed_summary
            
        except Exception as e:
            self.logger.error(f"LLM summarization failed for {source_name}: {str(e)}")
            log_agent_output("LLM", "SummaryExtractorSubAgent", 0, "error", correlation_id)
            return {
                'key_points': [f"Unable to process {source_name}"],
                'summary': str(source_data)[:200] + "..." if len(str(source_data)) > 200 else str(source_data),
                'confidence': 0.1
            }
        finally:
            stop_llm_heartbeat(correlation_id)

    async def _generate_comprehensive_summary(self, summaries: Dict[str, Dict[str, Any]], run_id: str) -> Dict[str, Any]:
        """Generate a comprehensive summary from all individual summaries."""
        await self.emit_thinking("Synthesizing all findings into unified insights...")
        
        # Build comprehensive prompt
        prompt = self._build_comprehensive_summary_prompt(summaries)
        correlation_id = generate_llm_correlation_id()
        
        try:
            start_llm_heartbeat(correlation_id, "SummaryExtractorSubAgent")
            log_agent_input("SummaryExtractorSubAgent", "LLM", len(prompt), correlation_id)
            
            response = await self.llm_manager.query_async(prompt, max_tokens=800)
            
            log_agent_output("LLM", "SummaryExtractorSubAgent", len(response) if response else 0, "success", correlation_id)
            
            # Parse comprehensive summary
            comprehensive = self._parse_comprehensive_summary(response)
            return comprehensive
            
        except Exception as e:
            self.logger.error(f"Comprehensive summary generation failed: {str(e)}")
            log_agent_output("LLM", "SummaryExtractorSubAgent", 0, "error", correlation_id)
            # Fallback to combining individual summaries
            return self._create_fallback_comprehensive_summary(summaries)
        finally:
            stop_llm_heartbeat(correlation_id)

    def _build_summarization_prompt(self, source_name: str, source_data: Any) -> str:
        """Build prompt for summarizing a single data source."""
        data_str = json.dumps(source_data, indent=2) if isinstance(source_data, dict) else str(source_data)
        
        return f"""
Extract key insights and create a summary from the following {source_name} data:

Data:
{data_str[:1500]}...

Please provide a JSON response with:
1. "key_points": List of 3-5 most important insights
2. "summary": 2-3 sentence overview
3. "confidence": Confidence level (0-1) in the summary quality

Focus on actionable insights that would help users understand the data quickly.
"""

    def _build_comprehensive_summary_prompt(self, summaries: Dict[str, Dict[str, Any]]) -> str:
        """Build prompt for comprehensive summary generation."""
        summary_text = ""
        for source, summary in summaries.items():
            summary_text += f"\n{source.upper()}:\n"
            summary_text += f"Summary: {summary.get('summary', 'N/A')}\n"
            summary_text += f"Key Points: {', '.join(summary.get('key_points', []))}\n"
        
        return f"""
Create a comprehensive summary that synthesizes all the following analysis results:

{summary_text}

Please provide a JSON response with:
1. "overall_summary": Comprehensive 3-4 sentence summary
2. "top_insights": List of 5-7 most critical insights across all data
3. "recommendations": List of 3-5 actionable recommendations
4. "confidence": Overall confidence in synthesis quality (0-1)

Focus on connecting insights across different data sources and highlighting the most valuable information for decision-making.
"""

    def _parse_summary_response(self, response: str, source_name: str) -> Dict[str, Any]:
        """Parse AI response for individual summary."""
        try:
            parsed = extract_json_from_response(response)
            if parsed:
                return {
                    'key_points': parsed.get('key_points', []),
                    'summary': parsed.get('summary', ''),
                    'confidence': max(0.0, min(1.0, parsed.get('confidence', 0.5)))
                }
        except Exception:
            pass
        
        # Fallback parsing
        return {
            'key_points': [f"Analysis from {source_name}"],
            'summary': response[:200] + "..." if len(response) > 200 else response,
            'confidence': 0.5
        }

    def _parse_comprehensive_summary(self, response: str) -> Dict[str, Any]:
        """Parse comprehensive summary response."""
        try:
            parsed = extract_json_from_response(response)
            if parsed:
                return parsed
        except Exception:
            pass
        
        # Fallback parsing
        return {
            'overall_summary': response[:300] + "..." if len(response) > 300 else response,
            'top_insights': ["Comprehensive analysis completed"],
            'recommendations': ["Review detailed findings"],
            'confidence': 0.5
        }

    def _create_fallback_comprehensive_summary(self, summaries: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Create fallback comprehensive summary when AI processing fails."""
        all_points = []
        all_summaries = []
        
        for source, summary in summaries.items():
            all_points.extend(summary.get('key_points', []))
            if summary.get('summary'):
                all_summaries.append(f"{source}: {summary['summary']}")
        
        return {
            'overall_summary': ' '.join(all_summaries)[:300] + "...",
            'top_insights': all_points[:7],
            'recommendations': ["Review individual analysis results for detailed insights"],
            'confidence': 0.4
        }

    def _format_summary_result(self, comprehensive: Dict[str, Any], summaries: Dict[str, Dict[str, Any]], collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format the final summary result."""
        return {
            'comprehensive_summary': comprehensive,
            'individual_summaries': summaries,
            'data_sources_processed': list(collected_data.keys()),
            'extraction_timestamp': time.time(),
            'total_sources': len(collected_data),
            'extraction_quality': {
                'overall_confidence': comprehensive.get('confidence', 0.5),
                'sources_successfully_processed': len([s for s in summaries.values() if s.get('confidence', 0) > 0.3]),
                'processing_errors': len([s for s in summaries.values() if s.get('confidence', 0) <= 0.3])
            }
        }

    async def _send_summary_completion_update(self, run_id: str, stream_updates: bool, result: Dict[str, Any]) -> None:
        """Send completion update with summary results."""
        if stream_updates:
            summary_message = f"Summary extraction completed! Processed {result['total_sources']} data sources with {len(result['comprehensive_summary'].get('top_insights', []))} key insights identified."
            
            update_data = {
                "status": "summary_completed",
                "message": summary_message,
                "run_id": run_id,
                "timestamp": time.time(),
                "data": {
                    "sources_processed": result['total_sources'],
                    "key_insights_count": len(result['comprehensive_summary'].get('top_insights', [])),
                    "confidence_score": result['extraction_quality']['overall_confidence']
                }
            }
            
            # Send via inherited WebSocket infrastructure
            await self.emit_progress(summary_message, is_complete=True, data=update_data)
