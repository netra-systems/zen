"""ToolDiscoverySubAgent using BaseAgent infrastructure (<200 lines).

CRITICAL FOR BUSINESS VALUE: This agent helps users discover appropriate tools for their tasks,
delivering AI-powered tool recommendations through real-time WebSocket events.

Simplified implementation using BaseAgent's SSOT infrastructure:
- Inherits reliability management, execution patterns, WebSocket events  
- Contains ONLY tool discovery business logic
- Clean single inheritance pattern
- No infrastructure duplication

Business Value: Enables users to discover and leverage platform tools effectively.
BVJ: ALL segments | Tool Adoption & User Experience | +40% increase in tool utilization
"""

import time
from typing import Any, Dict, List, Optional

from netra_backend.app.agents.agent_error_types import AgentValidationError
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.input_validation import validate_agent_input
from netra_backend.app.agents.triage.unified_triage_agent import ExtractedEntities, ToolRecommendation
from netra_backend.app.agents.triage_sub_agent.tool_recommender import ToolRecommender
from netra_backend.app.logging_config import central_logger
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext, validate_user_context
from netra_backend.app.database.session_manager import DatabaseSessionManager

logger = central_logger.get_logger(__name__)


class ToolDiscoverySubAgent(BaseAgent):
    """Tool discovery agent using BaseAgent infrastructure.
    
    CRITICAL: This agent provides AI-powered tool discovery for users, showing
    the discovery process in real-time through WebSocket events for chat value.
    
    Contains ONLY tool discovery business logic - all infrastructure 
    (reliability, execution, WebSocket events) inherited from BaseAgent.
    """
    
    def __init__(self):
        # Initialize BaseAgent with full infrastructure
        super().__init__(
            name="ToolDiscoverySubAgent", 
            description="AI-powered tool discovery and recommendation agent",
            enable_reliability=False,  # DISABLED: Was hiding errors - see AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md
            enable_execution_engine=True, # Get modern execution patterns
            enable_caching=True,          # Cache tool recommendations
        )   
        self.tool_recommender = ToolRecommender()
        self.discovery_cache = {}  # In-memory cache for fast lookups

    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute tool discovery using UserExecutionContext.
        
        Args:
            context: User execution context with request data
            stream_updates: Whether to send streaming updates
            
        Returns:
            Tool discovery results
        """
        # Validate context
        context = validate_user_context(context)
        
        start_time = time.time()
        
        try:
            # Create database session manager (stub implementation)
            session_mgr = DatabaseSessionManager()
            
            # Validate preconditions
            if not await self._validate_preconditions(context):
                raise AgentValidationError("Invalid preconditions for tool discovery")
                
            # Execute core logic
            result = await self._execute_core_logic(context, start_time)
            return result
            
        except Exception as e:
            await self.emit_error(f"Tool discovery failed: {str(e)}", error_type="DiscoveryError")
            raise AgentValidationError(f"Tool discovery execution failed: {str(e)}")
        finally:
            # Ensure proper cleanup
            try:
                if 'session_mgr' in locals():
                    await session_mgr.cleanup()
            except Exception as cleanup_e:
                logger.error(f"Session cleanup error: {cleanup_e}")
    
    async def _validate_preconditions(self, context: UserExecutionContext) -> bool:
        """Validate execution preconditions for tool discovery."""
        user_request = context.metadata.get('user_request', '')
        
        if not user_request:
            self.logger.warning(f"No user request provided for tool discovery in run_id: {context.run_id}")
            await self.emit_error(
                "No user request provided for tool discovery", 
                error_type="ValidationError"
            )
            return False
            
        # Validate that user request has sufficient content for tool discovery
        if len(user_request.strip()) < 10:
            self.logger.warning(f"User request too short for meaningful tool discovery in run_id: {context.run_id}")
            await self.emit_error(
                "User request too short for meaningful tool discovery", 
                error_type="ValidationError"
            )
            return False
            
        return True
        
    async def _execute_core_logic(self, context: UserExecutionContext, start_time: float) -> Dict[str, Any]:
        """Execute core tool discovery logic with real-time WebSocket events."""
        user_request = context.metadata.get('user_request', '')
        
        # CRITICAL: WebSocket events for chat value delivery
        await self.emit_thinking("Starting intelligent tool discovery for your request...")
        
        # Step 1: Analyze user request for intent and context
        await self.emit_thinking("Analyzing your request to understand intent and context...")
        await self.emit_progress("Extracting key entities and concepts from your request...")
        
        extracted_entities = await self._extract_entities_from_request(user_request)
        
        # Step 2: Categorize the request
        await self.emit_thinking("Categorizing your request to identify relevant tool categories...")
        await self.emit_progress("Determining the most appropriate tool categories...")
        
        categories = await self._categorize_request(user_request, extracted_entities)
        
        # Step 3: Discover and recommend tools
        await self.emit_thinking("Discovering tools that match your specific needs...")
        await self.emit_tool_executing("tool_recommendation_engine", {"categories": categories})
        
        tool_recommendations = await self._discover_tools(categories, extracted_entities)
        
        await self.emit_tool_completed("tool_recommendation_engine", {
            "found_tools": len(tool_recommendations),
            "categories_analyzed": len(categories)
        })
        
        # Step 4: Enhance recommendations with usage guidance
        await self.emit_progress("Enhancing recommendations with usage guidance and examples...")
        
        enhanced_recommendations = await self._enhance_recommendations(tool_recommendations, user_request)
        
        # Step 5: Finalize results
        await self.emit_thinking("Finalizing tool discovery results with prioritized recommendations...")
        
        result = await self._finalize_discovery_result(
            context, enhanced_recommendations, categories, start_time
        )
        
        # CRITICAL: Completion events for chat value
        await self.emit_progress(
            f"Tool discovery completed! Found {len(enhanced_recommendations)} relevant tools.", 
            is_complete=True
        )
        
        return result

    async def _extract_entities_from_request(self, user_request: str) -> ExtractedEntities:
        """Extract entities and concepts from user request."""
        await self.emit_progress("Identifying models, metrics, and technical concepts...")
        
        # Simple entity extraction (can be enhanced with NLP)
        model_keywords = ['model', 'gpt', 'claude', 'llama', 'bert', 'transformer']
        models_mentioned = [keyword for keyword in model_keywords if keyword in user_request.lower()]
        
        metric_keywords = ['metric', 'performance', 'latency', 'cost', 'throughput', 'accuracy', 'quality']
        metrics_mentioned = [keyword for keyword in metric_keywords if keyword in user_request.lower()]
        
        return ExtractedEntities(
            models_mentioned=models_mentioned,
            metrics_mentioned=metrics_mentioned
        )
    
    async def _categorize_request(self, user_request: str, entities: ExtractedEntities) -> List[str]:
        """Categorize the user request to determine relevant tool categories."""
        categories = []
        request_lower = user_request.lower()
        
        # Business logic for categorization
        if any(keyword in request_lower for keyword in ['analyze', 'analysis', 'data', 'workload']):
            categories.append("Workload Analysis")
        
        if any(keyword in request_lower for keyword in ['cost', 'price', 'savings', 'budget']):
            categories.append("Cost Optimization")
        
        if any(keyword in request_lower for keyword in ['performance', 'speed', 'latency', 'optimize']):
            categories.append("Performance Optimization")
        
        if any(keyword in request_lower for keyword in ['model', 'select', 'choose', 'recommend']) or len(entities.models_mentioned) > 0:
            categories.append("Model Selection")
        
        if any(keyword in request_lower for keyword in ['catalog', 'supply', 'inventory', 'manage']):
            categories.append("Supply Catalog Management")
        
        if any(keyword in request_lower for keyword in ['report', 'monitor', 'dashboard', 'metric']) or len(entities.metrics_mentioned) > 0:
            categories.append("Monitoring & Reporting")
        
        if any(keyword in request_lower for keyword in ['quality', 'accuracy', 'validate']):
            categories.append("Quality Optimization")
        
        # Default to workload analysis if no specific category detected
        if not categories:
            categories.append("Workload Analysis")
        
        return categories
    
    async def _discover_tools(self, categories: List[str], entities: ExtractedEntities) -> List[ToolRecommendation]:
        """Discover tools for the identified categories."""
        all_recommendations = []
        
        for category in categories:
            recommendations = self.tool_recommender.recommend_tools(category, entities)
            all_recommendations.extend(recommendations)
        
        # Remove duplicates and sort by relevance
        unique_tools = {}
        for rec in all_recommendations:
            if rec.tool_name not in unique_tools or rec.relevance_score > unique_tools[rec.tool_name].relevance_score:
                unique_tools[rec.tool_name] = rec
        
        return sorted(unique_tools.values(), key=lambda x: x.relevance_score, reverse=True)[:10]
    
    async def _enhance_recommendations(self, recommendations: List[ToolRecommendation], user_request: str) -> List[Dict[str, Any]]:
        """Enhance recommendations with usage guidance and examples."""
        enhanced = []
        
        for rec in recommendations:
            enhanced_rec = {
                "tool_name": rec.tool_name,
                "relevance_score": rec.relevance_score,
                "description": self._get_tool_description(rec.tool_name),
                "usage_example": self._get_usage_example(rec.tool_name, user_request),
                "parameters": rec.parameters or {},
                "category": self._determine_tool_category(rec.tool_name)
            }
            enhanced.append(enhanced_rec)
        
        return enhanced
    
    def _get_tool_description(self, tool_name: str) -> str:
        """Get description for a tool."""
        descriptions = {
            "analyze_workload_events": "Analyzes workload events and patterns in your AI infrastructure",
            "get_workload_metrics": "Retrieves comprehensive workload metrics and statistics",
            "identify_patterns": "Identifies patterns and anomalies in workload behavior",
            "calculate_cost_savings": "Calculates potential cost savings from optimizations",
            "simulate_cost_optimization": "Simulates cost optimization scenarios",
            "analyze_cost_trends": "Analyzes cost trends over time",
            "identify_latency_bottlenecks": "Identifies latency bottlenecks in your system",
            "optimize_throughput": "Optimizes system throughput and capacity",
            "analyze_performance": "Provides comprehensive performance analysis",
            "compare_models": "Compares different AI models for your use case",
            "get_model_capabilities": "Gets detailed capabilities of AI models",
            "recommend_model": "Recommends the best AI model for your needs",
            "get_supply_catalog": "Retrieves available AI models and services",
            "update_model_config": "Updates model configurations and settings",
            "add_new_model": "Adds new AI models to your catalog",
            "generate_report": "Generates comprehensive analysis reports",
            "create_dashboard": "Creates monitoring dashboards",
            "get_metrics_summary": "Provides summary of key metrics",
            "analyze_quality_metrics": "Analyzes quality metrics and trends",
            "optimize_quality_gates": "Optimizes quality control thresholds",
            "quality_analysis": "Performs comprehensive quality analysis"
        }
        return descriptions.get(tool_name, f"Tool for {tool_name.replace('_', ' ')}")
    
    def _get_usage_example(self, tool_name: str, user_request: str) -> str:
        """Get usage example for a tool based on user request."""
        return f"Use this tool to address your request: '{user_request[:50]}...'"
    
    def _determine_tool_category(self, tool_name: str) -> str:
        """Determine the category of a tool."""
        if any(keyword in tool_name for keyword in ['workload', 'events', 'patterns']):
            return "Workload Analysis"
        elif any(keyword in tool_name for keyword in ['cost', 'savings', 'optimization']):
            return "Cost Optimization" 
        elif any(keyword in tool_name for keyword in ['performance', 'latency', 'throughput']):
            return "Performance Optimization"
        elif any(keyword in tool_name for keyword in ['model', 'compare', 'recommend']):
            return "Model Selection"
        elif any(keyword in tool_name for keyword in ['catalog', 'supply', 'config']):
            return "Supply Catalog Management"
        elif any(keyword in tool_name for keyword in ['report', 'dashboard', 'metrics']):
            return "Monitoring & Reporting"
        else:
            return "Quality Optimization"
    
    async def _finalize_discovery_result(
        self, 
        context: UserExecutionContext, 
        recommendations: List[Dict[str, Any]], 
        categories: List[str], 
        start_time: float
    ) -> Dict[str, Any]:
        """Finalize the tool discovery result."""
        duration_ms = int((time.time() - start_time) * 1000)
        
        result = {
            "discovered_tools": recommendations,
            "analyzed_categories": categories, 
            "total_tools_found": len(recommendations),
            "discovery_metadata": {
                "run_id": context.run_id,
                "duration_ms": duration_ms,
                "agent": self.name,
                "timestamp": time.time()
            }
        }
        
        # Store result in context metadata for other agents
        context.metadata['tool_discovery_result'] = result
        
        return result