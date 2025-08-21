"""
Tool Handlers

Contains the implementation methods for handling tool execution requests.
Split into separate modules for better maintainability.
"""
from typing import Dict, Any, TYPE_CHECKING
from netra_backend.app.db.models_postgres import User

if TYPE_CHECKING:
    from .registry import UnifiedToolRegistry


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
        from netra_backend.app.agents.supervisor import SupervisorAgent
        
        supervisor = SupervisorAgent(self.db)
        agents = supervisor.get_registered_agents()
        
        agent_list = []
        for name, agent_class in agents.items():
            agent_list.append({
                "name": name,
                "type": agent_class.__name__,
                "capabilities": getattr(agent_class, 'capabilities', [])
            })
        
        return {
            "type": "text",
            "text": f"Available agents ({len(agent_list)}): " + ", ".join([a['name'] for a in agent_list]),
            "agents": agent_list
        }


class AnalyticsToolHandlers:
    """Handlers for analytics tools"""
    
    async def _analyze_workload_handler(self: "UnifiedToolRegistry", arguments: Dict[str, Any], user: User):
        """Handler for analyze_workload tool"""
        from netra_backend.app.services.apex_optimizer_service import ApexOptimizerService
        
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