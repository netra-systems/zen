"""
Content operations - handles content upload, retrieval, and search operations
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from ...db import models_postgres as models
from .base import CorpusNotFoundError
from .base_service import BaseCorpusService


class ContentOperationsService(BaseCorpusService):
    """Service for content-related operations"""
    
    async def upload_content(self, db: Session, corpus_id: str, records: List[Dict],
                           batch_id: Optional[str] = None, 
                           is_final_batch: bool = False) -> Dict:
        """Upload content to corpus"""
        db_corpus = await self._get_corpus_for_upload(db, corpus_id)
        return await self._execute_content_upload(
            db_corpus, records, batch_id, is_final_batch
        )
    
    async def _get_corpus_for_upload(self, db: Session, 
                                   corpus_id: str) -> models.Corpus:
        """Get and validate corpus for upload operation"""
        db_corpus = await self.corpus_manager.get_corpus(db, corpus_id)
        if not db_corpus:
            raise CorpusNotFoundError(f"Corpus {corpus_id} not found")
        return db_corpus
    
    async def _execute_content_upload(self, db_corpus: models.Corpus, 
                                    records: List[Dict], 
                                    batch_id: Optional[str], 
                                    is_final_batch: bool) -> Dict:
        """Execute content upload through document manager"""
        return await self.document_manager.upload_content(
            db_corpus, records, batch_id, is_final_batch
        )
    
    async def get_corpus_content(self, db: Session, corpus_id: str, 
                               limit: int = 100, offset: int = 0,
                               workload_type: Optional[str] = None) -> Optional[List[Dict]]:
        """Get corpus content from ClickHouse"""
        db_corpus = await self._get_corpus_for_content_retrieval(db, corpus_id)
        return await self._retrieve_corpus_content(
            db_corpus, limit, offset, workload_type
        )
    
    async def _get_corpus_for_content_retrieval(self, db: Session, 
                                              corpus_id: str) -> models.Corpus:
        """Get and validate corpus for content retrieval"""
        db_corpus = await self.corpus_manager.get_corpus(db, corpus_id)
        if not db_corpus:
            raise CorpusNotFoundError(f"Corpus {corpus_id} not found")
        return db_corpus
    
    async def _retrieve_corpus_content(self, db_corpus: models.Corpus, 
                                     limit: int, offset: int,
                                     workload_type: Optional[str]) -> Optional[List[Dict]]:
        """Retrieve corpus content through document manager"""
        return await self.document_manager.get_corpus_content(
            db_corpus, limit, offset, workload_type
        )
    
    async def get_corpus_statistics(self, db: Session, 
                                  corpus_id: str) -> Optional[Dict]:
        """Get corpus statistics from ClickHouse"""
        db_corpus = await self._get_corpus_for_statistics(db, corpus_id)
        return await self._retrieve_corpus_statistics(db_corpus)
    
    async def _get_corpus_for_statistics(self, db: Session, 
                                       corpus_id: str) -> models.Corpus:
        """Get and validate corpus for statistics retrieval"""
        db_corpus = await self.corpus_manager.get_corpus(db, corpus_id)
        if not db_corpus:
            raise CorpusNotFoundError(f"Corpus {corpus_id} not found")
        return db_corpus
    
    async def _retrieve_corpus_statistics(self, 
                                        db_corpus: models.Corpus) -> Optional[Dict]:
        """Retrieve corpus statistics through search operations"""
        return await self.search_operations.get_corpus_statistics(db_corpus)
    
    async def search_corpus_content(self, db: Session, corpus_id: str, 
                                  search_params: Dict):
        """Search corpus content with advanced filtering"""
        db_corpus = await self._get_corpus_for_search(db, corpus_id)
        return await self._execute_corpus_search(db_corpus, search_params)
    
    async def _get_corpus_for_search(self, db: Session, 
                                   corpus_id: str) -> models.Corpus:
        """Get and validate corpus for search operation"""
        db_corpus = await self.corpus_manager.get_corpus(db, corpus_id)
        if not db_corpus:
            raise CorpusNotFoundError(f"Corpus {corpus_id} not found")
        return db_corpus
    
    async def _execute_corpus_search(self, db_corpus: models.Corpus, 
                                   search_params: Dict):
        """Execute corpus search through search operations"""
        return await self.search_operations.search_corpus_content(
            db_corpus, search_params
        )
    
    async def get_corpus_sample(self, db: Session, corpus_id: str, 
                              sample_size: int = 10,
                              workload_type: Optional[str] = None):
        """Get a random sample of corpus content"""
        db_corpus = await self._get_corpus_for_sample(db, corpus_id)
        return await self._retrieve_corpus_sample(
            db_corpus, sample_size, workload_type
        )
    
    async def _get_corpus_for_sample(self, db: Session, 
                                   corpus_id: str) -> models.Corpus:
        """Get and validate corpus for sample retrieval"""
        db_corpus = await self.corpus_manager.get_corpus(db, corpus_id)
        if not db_corpus:
            raise CorpusNotFoundError(f"Corpus {corpus_id} not found")
        return db_corpus
    
    async def _retrieve_corpus_sample(self, db_corpus: models.Corpus, 
                                    sample_size: int,
                                    workload_type: Optional[str]):
        """Retrieve corpus sample through search operations"""
        return await self.search_operations.get_corpus_sample(
            db_corpus, sample_size, workload_type
        )
    
    async def get_workload_type_analytics(self, db: Session, corpus_id: str):
        """Get detailed analytics by workload type"""
        db_corpus = await self._get_corpus_for_analytics(db, corpus_id)
        return await self._retrieve_workload_analytics(db_corpus)
    
    async def _get_corpus_for_analytics(self, db: Session, 
                                      corpus_id: str) -> models.Corpus:
        """Get and validate corpus for analytics retrieval"""
        db_corpus = await self.corpus_manager.get_corpus(db, corpus_id)
        if not db_corpus:
            raise CorpusNotFoundError(f"Corpus {corpus_id} not found")
        return db_corpus
    
    async def _retrieve_workload_analytics(self, db_corpus: models.Corpus):
        """Retrieve workload analytics through search operations"""
        return await self.search_operations.get_workload_type_analytics(db_corpus)
    
    async def incremental_index(self, corpus_id: str, 
                              new_documents: List[Dict]) -> Dict:
        """Incrementally index new documents into existing corpus"""
        return await self.document_manager.incremental_index(corpus_id, new_documents)
    
    async def index_with_deduplication(self, corpus_id: str, 
                                     documents: List[Dict]) -> Dict:
        """Index documents with deduplication"""
        return await self.document_manager.index_with_deduplication(corpus_id, documents)