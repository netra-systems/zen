"""
Tool Handlers

Contains the implementation methods for handling tool execution requests.
Split into separate modules for better maintainability.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict

from netra_backend.app.db.models_postgres import User
from netra_backend.app.core.exceptions_tools import ToolExecutionException

if TYPE_CHECKING:
    from netra_backend.app.core.registry.universal_registry import ToolRegistry as UnifiedToolRegistry


class BasicToolHandlers:
    """Handlers for basic user tools"""
    
    async def _create_thread_handler(self: "UnifiedToolRegistry", arguments: Dict[str, Any], user: User):
        """Handler for create_thread tool"""
        from netra_backend.app.services.thread_service import ThreadService
        
        thread_service = ThreadService(self.db)
        
        thread = await thread_service.create_thread(
            user_id=user.id,
            title=arguments.get('title', 'Untitled'),
            initial_message=arguments.get('initial_message'),
            metadata=arguments.get('metadata', {})
        )
        
        return {
            "type": "text",
            "text": f"Created thread: {thread.title}",
            "thread_id": thread.id,
            "created_at": thread.created_at.isoformat()
        }
    
    async def _get_thread_history_handler(self: "UnifiedToolRegistry", arguments: Dict[str, Any], user: User):
        """Handler for get_thread_history tool"""
        from netra_backend.app.services.thread_service import ThreadService
        
        thread_service = ThreadService(self.db)
        
        history = await thread_service.get_thread_history(
            thread_id=arguments['thread_id'],
            user_id=user.id,
            limit=arguments.get('limit', 50)
        )
        
        return {
            "type": "text", 
            "text": f"Thread history for {arguments['thread_id']}",
            "messages": history.get('messages', []),
            "total_count": history.get('total_count', 0)
        }
    
    async def _list_agents_handler(self: "UnifiedToolRegistry", arguments: Dict[str, Any], user: User):
        """Handler for list_agents tool"""
        # Get agents from registry instead of creating SupervisorAgent directly
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        
        # Access global registry or create one with minimal dependencies
        # This avoids creating a SupervisorAgent without WebSocket bridge
        try:
            # Try to get registry from app state if available
            registry = getattr(self, 'registry', None)
            if not registry and hasattr(self, 'app'):
                registry = getattr(self.app.state, 'agent_registry', None)
            
            if registry:
                agents = registry.agents
                agent_list = []
                for name, agent_instance in agents.items():
                    agent_list.append({
                        "name": name,
                        "type": type(agent_instance).__name__,
                        "capabilities": getattr(type(agent_instance), 'capabilities', []),
                        "websocket_enabled": agent_instance.has_websocket_context()
                    })
            else:
                # Fallback: provide static list of known agent types
                agent_list = [
                    {"name": "triage", "type": "TriageSubAgent", "capabilities": ["user_intent_analysis", "routing"]},
                    {"name": "data_analysis", "type": "DataSubAgent", "capabilities": ["data_processing", "analytics"]},
                    {"name": "optimization", "type": "OptimizationsCoreSubAgent", "capabilities": ["cost_optimization", "performance_tuning"]},
                    {"name": "actions", "type": "ActionsToMeetGoalsSubAgent", "capabilities": ["action_planning", "execution"]},
                    {"name": "reporting", "type": "ReportingSubAgent", "capabilities": ["report_generation", "visualization"]},
                    {"name": "synthetic_data", "type": "SyntheticDataSubAgent", "capabilities": ["data_generation", "augmentation"]}
                ]
        except ImportError as e:
            # Handle missing imports gracefully
            agent_list = [{"name": "error", "type": "ImportError", "capabilities": [], "error": f"Import error: {str(e)}"}]
        except AttributeError as e:
            # Handle missing attributes or methods
            agent_list = [{"name": "error", "type": "AttributeError", "capabilities": [], "error": f"Attribute error: {str(e)}"}]
        except Exception as e:
            # Convert other exceptions to ToolExecutionException for better diagnostics
            raise ToolExecutionException(
                message=f"Failed to list agents: {str(e)}",
                tool_id="list_agents",
                tool_name="List Agents",
                user_id=user.id if user else None,
                execution_error=str(e),
                details={
                    'exception_type': type(e).__name__,
                    'handler_function': '_list_agents_handler'
                }
            )
        
        return {
            "type": "text",
            "text": f"Available agents ({len(agent_list)}): " + ", ".join([a['name'] for a in agent_list]),
            "agents": agent_list
        }


class AnalyticsToolHandlers:
    """Handlers for analytics tools"""
    
    async def _analyze_workload_handler(self: "UnifiedToolRegistry", arguments: Dict[str, Any], user: User):
        """Handler for analyze_workload tool"""
        from netra_backend.app.services.apex_optimizer_service import (
            ApexOptimizerService,
        )
        
        optimizer = ApexOptimizerService(self.db)
        
        analysis = await optimizer.analyze_workload({
            "workload_type": arguments.get('workload_type', 'general'),
            "metrics": arguments.get('metrics', {}),
            "user_id": user.id
        })
        
        recommendations = await optimizer.generate_recommendations(analysis)
        
        return {
            "type": "text",
            "text": "Workload analysis complete",
            "analysis": analysis,
            "recommendations": recommendations
        }
    
    async def _query_corpus_handler(self: "UnifiedToolRegistry", arguments: Dict[str, Any], user: User):
        """Handler for query_corpus tool"""
        from netra_backend.app.services.corpus_service import CorpusService
        
        corpus_service = CorpusService(self.db)
        
        results = await corpus_service.search(
            query=arguments['query'],
            filters=arguments.get('filters', {}),
            limit=arguments.get('limit', 10),
            user_id=user.id
        )
        
        return {
            "type": "text",
            "text": f"Found {len(results)} results for: {arguments['query']}",
            "results": results
        }