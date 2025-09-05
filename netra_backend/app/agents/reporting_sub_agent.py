""" SSOT ReportingSubAgent
Business Value: Final output for ALL analyses - CRITICAL revenue impact.
BVJ: ALL segments | Customer Experience | +30% reduction in report generation failures
"""

import time
from typing import Any, Dict, List, Optional

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.agent_error_types import AgentValidationError
from netra_backend.app.agents.prompts import reporting_prompt_template
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.core.serialization.unified_json_handler import (
    LLMResponseParser,
    JSONErrorFixer
)
from netra_backend.app.services.cache.cache_helpers import CacheHelpers
from netra_backend.app.database.session_manager import DatabaseSessionManager
from netra_backend.app.llm.observability import (
    generate_llm_correlation_id,
    log_agent_input,
    log_agent_output,
    start_llm_heartbeat,
    stop_llm_heartbeat,
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.agents.reporting.templates import ReportTemplates

logger = central_logger.get_logger(__name__)


class ReportingSubAgent(BaseAgent):
    
    def __init__(self, context: Optional[UserExecutionContext] = None):
        # Initialize BaseAgent with full infrastructure
        super().__init__(
            name="ReportingSubAgent", 
            description="UVS-enhanced reporting agent that NEVER crashes and ALWAYS delivers value",
            enable_reliability=False,  # DISABLED: Was hiding errors - see AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md
            enable_execution_engine=True, # Get modern execution patterns
            enable_caching=True,         # Get Redis caching
        )
        
        # Store context for factory pattern integration
        self._user_context = context
        
        # Initialize cache helper for SSOT key generation
        self._cache_helper = CacheHelpers(None)  # Pass None for key generation only
        
        # Initialize template system for guaranteed value delivery
        self._templates = ReportTemplates()
    
    async def validate_preconditions(self, context) -> bool:
        """Validate that we have sufficient data to generate a meaningful report.
        
        Returns False if critical analysis results are missing.
        """
        # Extract state from context metadata
        if hasattr(context, 'metadata') and context.metadata:
            state = context.metadata.get('state')
            if state:
                # Check for core analysis results (convert to boolean explicitly)
                has_triage = bool(hasattr(state, 'triage_result') and state.triage_result)
                has_optimizations = bool(hasattr(state, 'optimizations_result') and state.optimizations_result)  
                has_data = bool(hasattr(state, 'data_result') and state.data_result)
                has_action_plan = bool(hasattr(state, 'action_plan_result') and state.action_plan_result)
                
                # Need at least 2 types of analysis results to generate meaningful report
                required_count = sum([has_triage, has_optimizations, has_data, has_action_plan])
                return required_count >= 2
        
        return False  # No state means no data to work with

    def _assess_available_data(self, context: UserExecutionContext) -> Dict[str, Any]:
        """Safely assess what data is available without throwing errors.
        
        UVS Requirement: Must handle missing, malformed, or incomplete data gracefully.
        """
        metadata = context.metadata if context and hasattr(context, 'metadata') else {}
        
        # Safely check for each type of result
        assessment = {
            'has_full_data': False,
            'has_partial_data': False,
            'has_triage': bool(metadata.get('triage_result')),
            'has_data': bool(metadata.get('data_result')),
            'has_optimizations': bool(metadata.get('optimizations_result')),
            'has_action_plan': bool(metadata.get('action_plan_result')),
            'available_sections': [],
            'missing_sections': []
        }
        
        # Determine available sections
        if assessment['has_triage']:
            assessment['available_sections'].append('triage analysis')
        else:
            assessment['missing_sections'].append('triage')
            
        if assessment['has_data']:
            assessment['available_sections'].append('data insights')
        else:
            assessment['missing_sections'].append('data analysis')
            
        if assessment['has_optimizations']:
            assessment['available_sections'].append('optimization recommendations')
        else:
            assessment['missing_sections'].append('optimizations')
            
        if assessment['has_action_plan']:
            assessment['available_sections'].append('action plan')
        else:
            assessment['missing_sections'].append('action plan')
        
        # Determine overall data status
        if len(assessment['available_sections']) >= 3:  # Most data available
            assessment['has_full_data'] = True
        elif len(assessment['available_sections']) >= 1:  # Some data available
            assessment['has_partial_data'] = True
        
        self.logger.info(f"Data assessment for run_id {context.run_id if context else 'unknown'}: "
                        f"Available: {assessment['available_sections']}, "
                        f"Missing: {assessment['missing_sections']}")
        
        return assessment

    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute report generation with UVS resilience - GUARANTEED to return value.
        
        UVS Requirements:
        - NEVER crashes regardless of input
        - ALWAYS delivers meaningful value to user
        - Works with NO data, partial data, or full data
        - Every response has actionable next_steps
        """
        # UVS: Handle invalid context gracefully
        from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext as UEC
        import uuid
        
        if not context or not isinstance(context, UEC):
            self.logger.warning(f"Invalid context provided: {type(context)}")
            # Create minimal context to proceed - with required IDs
            if not context:
                context = UEC(
                    user_id="fallback_user",
                    thread_id="fallback_thread",
                    run_id=str(uuid.uuid4())
                )
        
        # REQUIRED: Emit agent started - with error handling
        if stream_updates:
            try:
                await self.emit_agent_started("Generating your optimization report...")
            except Exception as e:
                self.logger.warning(f"Failed to emit start event: {e}")
        
        try:
            # UVS: Assess available data without throwing errors
            data_assessment = self._assess_available_data(context)
            
            # REQUIRED: Show thinking based on data availability
            if stream_updates:
                try:
                    if data_assessment['has_full_data']:
                        await self.emit_thinking("Analyzing complete data set and generating comprehensive report...")
                    elif data_assessment['has_partial_data']:
                        await self.emit_thinking("Working with available data to provide insights...")
                    else:
                        await self.emit_thinking("Preparing guidance to help you get started...")
                except Exception as e:
                    self.logger.warning(f"Failed to emit thinking: {e}")
            
            # UVS: Three-tier report generation based on data availability
            if data_assessment['has_full_data']:
                # Tier 1: Full report with all data
                result = await self._generate_full_report(context, data_assessment, stream_updates)
            elif data_assessment['has_partial_data']:
                # Tier 2: Partial report with available data
                result = await self._generate_partial_report(context, data_assessment, stream_updates)
            else:
                # Tier 3: Guidance report with no data
                result = await self._generate_guidance_report(context, data_assessment, stream_updates)
            
            # Ensure result always has next_steps
            if 'next_steps' not in result:
                result['next_steps'] = self._generate_default_next_steps(data_assessment)
            
            # REQUIRED: Emit completion with results
            if stream_updates:
                try:
                    await self.emit_agent_completed(result)
                except Exception as e:
                    self.logger.warning(f"Failed to emit completion: {e}")
            
            self.logger.info(f"Report delivered successfully (type: {result.get('report_type')}) "
                           f"for run_id: {context.run_id if context else 'unknown'}")
            return result
            
        except Exception as e:
            # UVS: Ultimate fallback - this should RARELY execute
            self.logger.error(f"UVS fallback triggered: {str(e)}")
            
            # REQUIRED: Try to emit error event
            if stream_updates:
                try:
                    await self.emit_error("Recovering from technical issue...", "recovery_mode")
                except:
                    pass  # Even error emission can fail - continue anyway
            
            # UVS: Get emergency fallback that NEVER fails
            result = self._get_emergency_fallback_report(context, e)
            
            # REQUIRED: Try to emit recovery completion
            if stream_updates:
                try:
                    await self.emit_agent_completed(result)
                except:
                    pass
            
            return result

    async def _execute_reporting_llm_with_observability(
        self, prompt: str, correlation_id: str, context: UserExecutionContext, 
        stream_updates: bool = False
    ) -> str:
        """Execute LLM call with full observability and user feedback."""
        
        # REQUIRED: Show LLM processing start
        if stream_updates:
            await self.emit_tool_executing("llm_report_generation", {
                "model": "reporting",
                "prompt_length": len(prompt)
            })
        
        start_llm_heartbeat(correlation_id, "ReportingSubAgent")
        try:
            # Use context for user-specific logging
            log_agent_input(
                "ReportingSubAgent", "LLM", len(prompt), correlation_id
            )
            
            # REQUIRED: Show thinking during LLM processing
            if stream_updates:
                await self.emit_thinking("Generating comprehensive analysis report using AI reasoning...")
                
            response = await self.llm_manager.ask_llm(prompt, llm_config_name='reporting')
            
            # REQUIRED: Show LLM completion
            if stream_updates:
                await self.emit_tool_completed("llm_report_generation", {
                    "status": "success",
                    "response_length": len(response)
                })
                
            log_agent_output(
                "LLM", "ReportingSubAgent", len(response), "success", correlation_id
            )
            return response
        except Exception as e:
            # REQUIRED: Show LLM failure
            if stream_updates:
                await self.emit_tool_completed("llm_report_generation", {
                    "status": "error", 
                    "error": str(e)
                })
            log_agent_output(
                "LLM", "ReportingSubAgent", 0, "error", correlation_id
            )
            raise
        finally:
            stop_llm_heartbeat(correlation_id)

    def _build_reporting_prompt(self, context: UserExecutionContext) -> str:
        """Build the reporting prompt from context metadata."""
        metadata = context.metadata
        
        # Serialize ActionPlanResult if it's a Pydantic model
        action_plan = metadata.get("action_plan_result", "")
        if hasattr(action_plan, 'model_dump'):
            action_plan = action_plan.model_dump(mode='json', exclude_none=True)
        elif hasattr(action_plan, 'dict'):
            action_plan = action_plan.dict(exclude_none=True)
        
        return reporting_prompt_template.format(
            action_plan=action_plan,
            optimizations=metadata.get("optimizations_result", ""),
            data=metadata.get("data_result", ""),
            triage_result=metadata.get("triage_result", ""),
            user_request=metadata.get("user_request", "")
        )
    
    def _extract_and_validate_report(self, llm_response_str: str, run_id: str) -> Dict[str, Any]:
        """Extract and validate JSON result from LLM response using canonical parser."""
        # Use canonical LLMResponseParser from unified_json_handler
        parser = LLMResponseParser()
        report_result = parser.safe_json_parse(llm_response_str)
        
        # If result is a dict, return it; otherwise try error fixing
        if isinstance(report_result, dict):
            return report_result
            
        # Apply comprehensive error fixing for malformed JSON
        error_fixer = JSONErrorFixer()
        fixed_result = error_fixer.recover_truncated_json(llm_response_str)
        
        if fixed_result and isinstance(fixed_result, dict):
            self.logger.info(f"Successfully recovered malformed JSON for run_id: {run_id}")
            return fixed_result
        
        # Final fallback
        self.logger.warning(f"Could not extract or recover JSON from LLM response for run_id: {run_id}. Using fallback report.")
        return {"report": "No report could be generated from LLM response."}
    
    async def _send_success_update(self, run_id: str, stream_updates: bool, result: Dict[str, Any]) -> None:
        """Send success status update via WebSocket."""
        if stream_updates:
            await self._send_update(run_id, {
                "status": "processed",
                "message": "Final report generated successfully",
                "result": result
            })
    
    def _create_report_result(self, data: Dict[str, Any]) -> 'ReportResult':
        """Convert dictionary to ReportResult object."""
        from netra_backend.app.agents.state import ReportResult, ReportSection
        
        # Convert sections to ReportSection objects
        sections_data = data.get("sections", [])
        sections = [
            ReportSection(
                section_id=section.get("section_id", f"section_{i}") if isinstance(section, dict) else f"section_{i}",
                title=section.get("title", f"Section {i}") if isinstance(section, dict) else section.capitalize(),
                content=section.get("content", "") if isinstance(section, dict) else f"Content for {section}",
                section_type=section.get("section_type", "standard") if isinstance(section, dict) else "standard"
            )
            for i, section in enumerate(sections_data)
        ]
        
        return ReportResult(
            report_type="analysis",
            content=data.get("report", "No content available"),
            sections=sections,
            metadata=data.get("metadata", {})
        )

    async def _generate_full_report(self, context: UserExecutionContext, 
                                   data_assessment: Dict[str, Any], 
                                   stream_updates: bool = False) -> Dict[str, Any]:
        """Generate comprehensive report when all data is available.
        
        UVS: Even with full data, must handle partial failures gracefully.
        """
        try:
            # Generate cache key
            cache_key = self._generate_report_cache_key(context)
            
            # Try cache first
            cached_result = await self._get_cached_report(cache_key)
            if cached_result:
                self.logger.info(f"Using cached full report for run_id: {context.run_id}")
                return cached_result
            
            # Build prompt and generate report via LLM
            prompt = self._build_reporting_prompt(context)
            correlation_id = generate_llm_correlation_id()
            
            llm_response_str = await self._execute_reporting_llm_with_observability(
                prompt, correlation_id, context, stream_updates
            )
            
            # Extract and validate
            result = self._extract_and_validate_report(llm_response_str, context.run_id)
            
            # Enhance with UVS requirements
            result['report_type'] = 'full_analysis'
            result['status'] = 'success'
            result['data_completeness'] = 'complete'
            
            # Ensure next_steps exist
            if 'next_steps' not in result:
                result['next_steps'] = [
                    "Review the complete analysis above",
                    "Prioritize high-impact optimizations",
                    "Implement quick wins first",
                    "Schedule follow-up analysis in 30 days"
                ]
            
            # Cache the result
            await self._cache_report_result(cache_key, result)
            
            return result
            
        except Exception as e:
            self.logger.warning(f"Full report generation failed, falling back to partial: {e}")
            # Fallback to partial report with available data
            return await self._generate_partial_report(context, data_assessment, stream_updates)
    
    async def _generate_partial_report(self, context: UserExecutionContext,
                                      data_assessment: Dict[str, Any],
                                      stream_updates: bool = False) -> Dict[str, Any]:
        """Generate report with incomplete data.
        
        UVS: Work with whatever data is available.
        """
        try:
            metadata = context.metadata if context else {}
            available_sections = data_assessment.get('available_sections', [])
            
            # Start with template
            report = self._templates.get_partial_data_template(available_sections)
            
            # Add whatever data we have
            if data_assessment.get('has_data'):
                data_result = metadata.get('data_result', {})
                report['data_insights'] = self._format_data_insights(data_result)
            
            if data_assessment.get('has_optimizations'):
                opt_result = metadata.get('optimizations_result', {})
                report['optimizations'] = self._format_optimization_insights(opt_result)
            
            if data_assessment.get('has_action_plan'):
                action_plan = metadata.get('action_plan_result', {})
                report['action_plan'] = self._format_action_plan_summary(action_plan)
            
            # Add context about what's missing
            report['missing_data_guidance'] = self._generate_missing_data_guidance(data_assessment)
            
            # Ensure actionable next steps
            report['next_steps'] = [
                f"Review the {', '.join(available_sections)} provided",
                "Provide additional data for complete analysis",
                "Start with any quick wins identified",
                "Consider the data collection guide above"
            ]
            
            return report
            
        except Exception as e:
            self.logger.warning(f"Partial report generation failed, falling back to guidance: {e}")
            # Fallback to guidance report
            return await self._generate_guidance_report(context, data_assessment, stream_updates)
    
    async def _generate_guidance_report(self, context: UserExecutionContext,
                                       data_assessment: Dict[str, Any], 
                                       stream_updates: bool = False) -> Dict[str, Any]:
        """Generate helpful guidance when no data is available.
        
        UVS: This is the most important tier - helps users get started.
        """
        try:
            # Get comprehensive guidance template
            report = self._templates.get_no_data_template()
            
            # Enhance with any context we have
            if context and hasattr(context, 'metadata'):
                metadata = context.metadata or {}
                
                # If we have user request, acknowledge it
                if metadata.get('user_request'):
                    report['user_request_acknowledged'] = True
                    report['understanding'] = {
                        'your_request': metadata.get('user_request')[:200],
                        'how_to_proceed': "I understand your request. Let's gather some information to provide the best recommendations."
                    }
                
                # If triage provided any insights
                if metadata.get('triage_result'):
                    triage = metadata.get('triage_result', {})
                    if isinstance(triage, dict):
                        report['initial_assessment'] = {
                            'identified_needs': triage.get('identified_needs', []),
                            'suggested_focus': triage.get('optimization_focus', 'general')
                        }
            
            # Always ensure strong next steps for engagement
            report['next_steps'] = [
                "Answer any of the quick assessment questions above",
                "Upload your AI usage data (CSV, JSON, or text format)",
                "Or simply describe your current setup and optimization goals",
                "Review the example optimizations for immediate ideas"
            ]
            
            return report
            
        except Exception as e:
            self.logger.error(f"Guidance report generation failed, using emergency fallback: {e}")
            # Ultimate fallback
            return self._get_emergency_fallback_report(context, e)
    
    def _get_emergency_fallback_report(self, context: Any, error: Exception) -> Dict[str, Any]:
        """Ultimate fallback - MUST return valid response.
        
        UVS CRITICAL: This method MUST NEVER raise an exception.
        """
        try:
            # Log error safely
            error_id = None
            try:
                import uuid
                error_id = str(uuid.uuid4())[:8]
                self.logger.error(f"Emergency fallback triggered [{error_id}]: {str(error)}")
            except:
                pass  # Even logging can fail
            
            # Get emergency template
            template = self._templates.get_emergency_fallback_template(debug_id=error_id)
            
            # Try to add any context we can
            if context:
                try:
                    template = self._templates.enhance_with_context(template, context)
                except:
                    pass  # Context enhancement is optional
            
            return template
            
        except:
            # Absolute last resort - hardcoded response
            # This should NEVER happen, but ensures we always return something
            return {
                'report_type': 'fallback',
                'status': 'ready_to_help',
                'message': 'Ready to help optimize your AI usage.',
                'next_steps': [
                    'Share your AI usage data',
                    'Describe your optimization goals',
                    'Ask any questions about AI cost optimization'
                ],
                'metadata': {'ultimate_fallback': True}
            }
    
    def _format_data_insights(self, data_result: Any) -> Dict[str, Any]:
        """Safely format data insights."""
        try:
            if hasattr(data_result, 'model_dump'):
                data_result = data_result.model_dump(mode='json', exclude_none=True)
            elif hasattr(data_result, 'dict'):
                data_result = data_result.dict(exclude_none=True)
            
            return {
                'summary': 'Data analysis completed',
                'details': data_result if isinstance(data_result, dict) else str(data_result)
            }
        except:
            return {'summary': 'Data processed', 'status': 'available'}
    
    def _format_optimization_insights(self, opt_result: Any) -> Dict[str, Any]:
        """Safely format optimization insights."""
        try:
            if hasattr(opt_result, 'model_dump'):
                opt_result = opt_result.model_dump(mode='json', exclude_none=True)
            elif hasattr(opt_result, 'dict'):
                opt_result = opt_result.dict(exclude_none=True)
            
            return {
                'summary': 'Optimization opportunities identified',
                'recommendations': opt_result if isinstance(opt_result, dict) else str(opt_result)
            }
        except:
            return {'summary': 'Optimizations available', 'status': 'ready'}
    
    def _format_action_plan_summary(self, action_plan: Any) -> Dict[str, Any]:
        """Safely format action plan summary."""
        try:
            if hasattr(action_plan, 'model_dump'):
                action_plan = action_plan.model_dump(mode='json', exclude_none=True)
            elif hasattr(action_plan, 'dict'):
                action_plan = action_plan.dict(exclude_none=True)
                
            return {
                'summary': 'Implementation plan created',
                'plan': action_plan if isinstance(action_plan, dict) else str(action_plan)
            }
        except:
            return {'summary': 'Action plan prepared', 'status': 'ready'}
    
    def _generate_missing_data_guidance(self, data_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Generate guidance for missing data."""
        missing = data_assessment.get('missing_sections', [])
        
        guidance = {
            'title': 'Additional Data Needed',
            'missing_components': missing,
            'how_to_provide': []
        }
        
        if 'data analysis' in missing:
            guidance['how_to_provide'].append('Upload your AI usage data (CSV or JSON)')
        
        if 'triage' in missing:
            guidance['how_to_provide'].append('Describe your optimization goals')
            
        if 'optimizations' in missing:
            guidance['how_to_provide'].append('Share performance metrics or cost concerns')
        
        return guidance
    
    def _generate_default_next_steps(self, data_assessment: Dict[str, Any]) -> List[str]:
        """Generate default next steps based on data availability."""
        if data_assessment.get('has_full_data'):
            return [
                "Review the complete analysis",
                "Implement high-priority optimizations",
                "Monitor results and iterate"
            ]
        elif data_assessment.get('has_partial_data'):
            return [
                "Review available insights",
                "Provide missing data for complete analysis",
                "Start with identified quick wins"
            ]
        else:
            return [
                "Share your AI usage data",
                "Describe your optimization goals",
                "Review the getting started guide"
            ]
    
    def _create_fallback_report(self, context: UserExecutionContext) -> Dict[str, Any]:
        """Legacy fallback - now routes to UVS emergency fallback."""
        return self._get_emergency_fallback_report(context, Exception("Legacy fallback invoked"))
    
    def _generate_report_cache_key(self, context: UserExecutionContext) -> str:
        """Generate cache key for report with user context isolation."""
        # Build key data with user context
        # Serialize ActionPlanResult if present
        action_plan = context.metadata.get("action_plan_result", "")
        if hasattr(action_plan, 'model_dump'):
            action_plan = str(action_plan.model_dump(mode='json', exclude_none=True))
        elif hasattr(action_plan, 'dict'):
            action_plan = str(action_plan.dict(exclude_none=True))
        
        key_data = {
            "agent": "reporting",
            "action_plan": action_plan,
            "optimizations": context.metadata.get("optimizations_result", ""), 
            "data_result": context.metadata.get("data_result", ""),
            "triage_result": context.metadata.get("triage_result", ""),
            "user_request": context.metadata.get("user_request", "")
        }
        
        # CRITICAL: Include user context for proper isolation
        if context:
            key_data["user_id"] = context.user_id
            key_data["thread_id"] = context.thread_id
            
        # Use SSOT CacheHelpers for hash generation
        return self._cache_helper.hash_key_data(key_data)

    async def _get_cached_report(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached report result."""
        if not hasattr(self, 'redis_manager') or not self.redis_manager:
            return None
        
        try:
            cached_data = await self.redis_manager.get(f"report_cache:{cache_key}")
            if cached_data:
                import json
                return json.loads(cached_data)
        except Exception as e:
            self.logger.warning(f"Failed to retrieve cached report: {e}")
        
        return None

    async def _cache_report_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache report result with TTL."""
        if not hasattr(self, 'redis_manager') or not self.redis_manager:
            return
            
        try:
            import json
            # Ensure any Pydantic models are serialized properly
            def serialize_value(v):
                if hasattr(v, 'model_dump'):
                    return v.model_dump(mode='json', exclude_none=True)
                elif hasattr(v, 'dict'):
                    return v.dict(exclude_none=True)
                return v
            
            # Deep copy and serialize any Pydantic models
            serializable_result = {}
            for key, value in result.items():
                if isinstance(value, dict):
                    serializable_result[key] = {k: serialize_value(v) for k, v in value.items()}
                else:
                    serializable_result[key] = serialize_value(value)
            
            cache_data = json.dumps(serializable_result)
            ttl = getattr(self, 'cache_ttl', 3600)  # Default 1 hour TTL
            await self.redis_manager.set(
                f"report_cache:{cache_key}",
                cache_data, 
                ex=ttl
            )
            self.logger.debug(f"Cached report result with key: {cache_key[:12]}...")
        except Exception as e:
            self.logger.warning(f"Failed to cache report result: {e}")

    @classmethod
    def create_agent_with_context(cls, context: 'UserExecutionContext') -> 'ReportingSubAgent':
        """Factory method for creating agent with user context.
        
        This method enables the agent to be created through AgentInstanceFactory
        with proper user context isolation.
        
        Args:
            context: User execution context for isolation
            
        Returns:
            ReportingSubAgent: Configured agent instance
        """
        return cls(context=context)

    # All infrastructure methods (WebSocket, monitoring, health status) inherited from BaseAgent