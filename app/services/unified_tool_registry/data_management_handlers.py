"""
Data Management Tool Handlers

Contains handlers for data management, corpus management, and synthetic data tools.
"""
from typing import Dict, Any, TYPE_CHECKING
from app.db.models_postgres import User

if TYPE_CHECKING:
    from .registry import UnifiedToolRegistry


class DataManagementHandlers:
    """Handlers for data management tools"""
    
    async def _generate_synthetic_data_handler(self: "UnifiedToolRegistry", arguments: Dict[str, Any], user: User):
        """Handler for generate_synthetic_data tool"""
        from app.services.synthetic_data_service import SyntheticDataService
        
        synthetic_service = SyntheticDataService(self.db)
        
        data = await synthetic_service.generate(
            data_type=arguments.get('data_type', 'generic'),
            count=arguments.get('count', 10),
            schema=arguments.get('schema', {}),
            user_id=user.id
        )
        
        return {
            "type": "text",
            "text": f"Generated {len(data)} synthetic records",
            "data": data
        }
    
    async def _corpus_manager_handler(self: "UnifiedToolRegistry", arguments: Dict[str, Any], user: User):
        """Handler for corpus_manager tool"""
        from app.services.corpus_service import CorpusService
        
        corpus_service = CorpusService(self.db)
        action = arguments['action']
        
        return await self._execute_corpus_action(corpus_service, action, arguments, user)
    
    async def _execute_corpus_action(self, corpus_service, action: str, arguments: Dict[str, Any], user: User):
        """Execute corpus management action"""
        if action == 'create':
            return await self._handle_corpus_create(corpus_service, arguments, user)
        elif action == 'delete':
            return await self._handle_corpus_delete(corpus_service, arguments, user)
        elif action == 'list':
            return await self._handle_corpus_list(corpus_service, user)
        else:
            return self._handle_unknown_action(action)
    
    async def _handle_corpus_create(self, corpus_service, arguments: Dict[str, Any], user: User):
        """Handle corpus creation"""
        corpus = await corpus_service.create_corpus(
            name=arguments['name'],
            description=arguments.get('description'),
            user_id=user.id
        )
        return self._build_create_response(corpus)
    
    def _build_create_response(self, corpus):
        """Build response for corpus creation"""
        return {
            "type": "text",
            "text": f"Created corpus: {corpus.name}",
            "corpus_id": corpus.id
        }
    
    async def _handle_corpus_delete(self, corpus_service, arguments: Dict[str, Any], user: User):
        """Handle corpus deletion"""
        await corpus_service.delete_corpus(
            corpus_id=arguments['corpus_id'],
            user_id=user.id
        )
        return self._build_delete_response(arguments['corpus_id'])
    
    def _build_delete_response(self, corpus_id: str):
        """Build response for corpus deletion"""
        return {
            "type": "text",
            "text": f"Deleted corpus: {corpus_id}"
        }
    
    async def _handle_corpus_list(self, corpus_service, user: User):
        """Handle corpus listing"""
        corpora = await corpus_service.list_corpora(user_id=user.id)
        return self._build_list_response(corpora)
    
    def _build_list_response(self, corpora):
        """Build response for corpus listing"""
        return {
            "type": "text",
            "text": f"Found {len(corpora)} corpora",
            "corpora": corpora
        }
    
    def _handle_unknown_action(self, action: str):
        """Handle unknown corpus action"""
        return {
            "type": "text",
            "text": f"Unknown action: {action}"
        }