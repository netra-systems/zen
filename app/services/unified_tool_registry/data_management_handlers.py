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
        
        if action == 'create':
            corpus = await corpus_service.create_corpus(
                name=arguments['name'],
                description=arguments.get('description'),
                user_id=user.id
            )
            return {
                "type": "text",
                "text": f"Created corpus: {corpus.name}",
                "corpus_id": corpus.id
            }
        elif action == 'delete':
            await corpus_service.delete_corpus(
                corpus_id=arguments['corpus_id'],
                user_id=user.id
            )
            return {
                "type": "text",
                "text": f"Deleted corpus: {arguments['corpus_id']}"
            }
        elif action == 'list':
            corpora = await corpus_service.list_corpora(user_id=user.id)
            return {
                "type": "text",
                "text": f"Found {len(corpora)} corpora",
                "corpora": corpora
            }
        else:
            return {
                "type": "text",
                "text": f"Unknown action: {action}"
            }