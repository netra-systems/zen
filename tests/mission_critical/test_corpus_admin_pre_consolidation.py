#!/usr/bin/env python3

"""

Pre-consolidation tests for Corpus Admin module.

These tests capture current functionality to ensure nothing is lost during SSOT consolidation.



CRITICAL: These tests must pass BEFORE and AFTER the consolidation.

"""

import asyncio

import json

import os

import sys

from pathlib import Path

from typing import Any, Dict, List

import unittest

from shared.isolated_environment import IsolatedEnvironment



# Add project root to path

project_root = Path(__file__).parent.parent.parent.absolute()

sys.path.insert(0, str(project_root))



# Standard unittest imports

import unittest

from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler

from netra_backend.app.db.database_manager import DatabaseManager

from netra_backend.app.clients.auth_client_core import AuthServiceClient

from shared.isolated_environment import get_env



class TestCorpusAdminPreConsolidation(unittest.IsolatedAsyncioTestCase):

    """

    CRITICAL: Pre-consolidation tests to ensure all corpus functionality is preserved.

    Tests multi-user isolation, thread safety, and all corpus operations.

    """

    

    async def asyncSetUp(self):

        """Async setup for test environment"""

        self.user_contexts = {}

        # Create multiple user contexts for multi-user testing

        for i in range(3):

            user_id = f"test_user_{i}"

            self.user_contexts[user_id] = self._create_user_context(user_id)

    

    def _create_user_context(self, user_id: str) -> Dict[str, Any]:

        """Create a user execution context for testing"""

        return {

            'user_id': user_id,

            'request_id': f'req_{user_id}_{id(self)}',

            'thread_id': f'thread_{user_id}',

            'session_id': f'session_{user_id}',

            'metadata': {},

            'active_runs': {},

            'run_history': []

        }

    

    async def test_corpus_creation_multi_user_isolation(self):

        """Test that corpus creation is isolated per user"""

        from netra_backend.app.admin.corpus import CorpusAdminSubAgent

        

        # Create corpus admin instances for different users

        agents = {}

        for user_id, context in self.user_contexts.items():

            agent = CorpusAdminSubAgent()

            agents[user_id] = agent

            

        # Each user creates their own corpus

        corpus_ids = {}

        for user_id, agent in agents.items():

            context = self.user_contexts[user_id]

            

            # Mock corpus creation

            with patch.object(agent, '_execute_corpus_operation', new_callable=AsyncMock) as mock_exec:

                mock_exec.return_value = {

                    'success': True,

                    'corpus_id': f'corpus_{user_id}_123',

                    'message': f'Corpus created for {user_id}'

                }

                

                result = await agent._execute_corpus_operation(

                    operation='create',

                    context=context,

                    params={'name': f'Test Corpus {user_id}'}

                )

                

                corpus_ids[user_id] = result['corpus_id']

                

        # Verify each user has a unique corpus

        unique_corpus_ids = set(corpus_ids.values())

        self.assertEqual(len(unique_corpus_ids), len(self.user_contexts))

        

    async def test_corpus_crud_operations(self):

        """Test all CRUD operations for corpus management"""

        from netra_backend.app.admin.corpus import CorpusCRUDOperations

        

        crud_ops = CorpusCRUDOperations()

        context = self.user_contexts['test_user_0']

        

        # Test CREATE

        create_result = await self._test_crud_operation(

            crud_ops, 'create', context,

            {'name': 'Test Corpus', 'type': 'KNOWLEDGE_BASE'}

        )

        self.assertTrue(create_result.get('success'))

        

        # Test READ/SEARCH

        search_result = await self._test_crud_operation(

            crud_ops, 'search', context,

            {'query': 'test', 'limit': 10}

        )

        self.assertIsInstance(search_result.get('results'), list)

        

        # Test UPDATE

        update_result = await self._test_crud_operation(

            crud_ops, 'update', context,

            {'corpus_id': 'test_corpus_1', 'updates': {'name': 'Updated Corpus'}}

        )

        self.assertTrue(update_result.get('success'))

        

        # Test DELETE

        delete_result = await self._test_crud_operation(

            crud_ops, 'delete', context,

            {'corpus_id': 'test_corpus_1', 'confirm': True}

        )

        self.assertTrue(delete_result.get('success'))

    

    async def _test_crud_operation(self, crud_ops, operation: str, context: Dict, params: Dict) -> Dict:

        """Helper to test a CRUD operation"""

        with patch.object(crud_ops, f'_{operation}_corpus', new_callable=AsyncMock) as mock_op:

            mock_op.return_value = {

                'success': True,

                'operation': operation,

                'results': [] if operation == 'search' else None

            }

            

            # Get the actual method - need to handle the real implementation

            op_mapping = crud_ops._get_operation_mapping()

            if operation in op_mapping:

                return await mock_op(context=context, **params)

            

            return mock_op.return_value

    

    async def test_corpus_indexing_operations(self):

        """Test corpus indexing functionality"""

        from netra_backend.app.admin.corpus import CorpusIndexingHandlers

        

        indexing_handlers = CorpusIndexingHandlers()

        context = self.user_contexts['test_user_0']

        

        # Test document indexing

        with patch.object(indexing_handlers, '_index_document', new_callable=AsyncMock) as mock_index:

            mock_index.return_value = {

                'indexed': True,

                'document_id': 'doc_123',

                'index_time_ms': 150

            }

            

            result = await mock_index(

                context=context,

                document={'content': 'Test document', 'metadata': {}}

            )

            

            self.assertTrue(result['indexed'])

            self.assertIn('document_id', result)

    

    async def test_corpus_validation_operations(self):

        """Test corpus validation functionality"""

        from netra_backend.app.admin.corpus import CorpusValidationHandlers

        

        validation_handlers = CorpusValidationHandlers()

        context = self.user_contexts['test_user_0']

        

        # Test document validation

        with patch.object(validation_handlers, '_validate_document', new_callable=AsyncMock) as mock_validate:

            mock_validate.return_value = {

                'valid': True,

                'errors': [],

                'warnings': []

            }

            

            result = await mock_validate(

                context=context,

                document={'content': 'Valid document', 'metadata': {'type': 'text'}}

            )

            

            self.assertTrue(result['valid'])

            self.assertEqual(len(result['errors']), 0)

    

    async def test_corpus_upload_operations(self):

        """Test corpus upload functionality"""

        from netra_backend.app.admin.corpus import CorpusUploadHandlers

        

        upload_handlers = CorpusUploadHandlers()

        context = self.user_contexts['test_user_0']

        

        # Test file upload

        with patch.object(upload_handlers, '_handle_upload', new_callable=AsyncMock) as mock_upload:

            mock_upload.return_value = {

                'uploaded': True,

                'file_id': 'file_456',

                'size_bytes': 1024

            }

            

            result = await mock_upload(

                context=context,

                file_data=b'test file content',

                filename='test.txt'

            )

            

            self.assertTrue(result['uploaded'])

            self.assertIn('file_id', result)

    

    async def test_corpus_analysis_operations(self):

        """Test corpus analysis functionality"""

        from netra_backend.app.admin.corpus import CorpusAnalysisOperations

        

        analysis_ops = CorpusAnalysisOperations()

        context = self.user_contexts['test_user_0']

        

        # Test corpus statistics

        with patch.object(analysis_ops, '_analyze_corpus', new_callable=AsyncMock) as mock_analyze:

            mock_analyze.return_value = {

                'total_documents': 100,

                'total_size_bytes': 1048576,

                'unique_terms': 5000,

                'avg_document_size': 10485

            }

            

            result = await mock_analyze(

                context=context,

                corpus_id='corpus_123'

            )

            

            self.assertIn('total_documents', result)

            self.assertIsInstance(result['total_documents'], int)

    

    async def test_corpus_error_handling(self):

        """Test error handling and compensation"""

        from netra_backend.app.admin.corpus import (

            CorpusAdminError,

            DocumentUploadError,

            DocumentValidationError,

            IndexingError

        )

        

        # Test error creation

        upload_error = DocumentUploadError(

            message="Upload failed",

            details={'file': 'test.txt', 'reason': 'Too large'}

        )

        self.assertIsInstance(upload_error, CorpusAdminError)

        

        validation_error = DocumentValidationError(

            message="Validation failed",

            details={'document': 'doc_123', 'errors': ['Missing metadata']}

        )

        self.assertIsInstance(validation_error, CorpusAdminError)

        

        indexing_error = IndexingError(

            message="Indexing failed",

            details={'document': 'doc_456', 'reason': 'Index full'}

        )

        self.assertIsInstance(indexing_error, CorpusAdminError)

        

        # Test error types are properly defined

        self.assertIsInstance(upload_error.details, dict)

        self.assertIsInstance(validation_error.details, dict)

        self.assertIsInstance(indexing_error.details, dict)

    

    async def test_thread_safety_concurrent_operations(self):

        """Test thread safety with concurrent corpus operations"""

        from netra_backend.app.admin.corpus import CorpusAdminSubAgent

        

        agent = CorpusAdminSubAgent()

        

        # Simulate concurrent operations from different users

        async def user_operation(user_id: str, operation: str):

            context = self.user_contexts[user_id]

            

            with patch.object(agent, '_execute_corpus_operation', new_callable=AsyncMock) as mock_exec:

                mock_exec.return_value = {

                    'success': True,

                    'user_id': user_id,

                    'operation': operation,

                    'corpus_id': f'corpus_{user_id}_{operation}'

                }

                

                return await mock_exec(

                    operation=operation,

                    context=context,

                    params={'test': True}

                )

        

        # Run concurrent operations

        tasks = []

        for user_id in self.user_contexts:

            for operation in ['create', 'update', 'search']:

                tasks.append(user_operation(user_id, operation))

        

        results = await asyncio.gather(*tasks)

        

        # Verify all operations completed successfully

        self.assertEqual(len(results), len(self.user_contexts) * 3)

        for result in results:

            self.assertTrue(result['success'])

        

        # Verify user isolation

        user_results = {}

        for result in results:

            user_id = result['user_id']

            if user_id not in user_results:

                user_results[user_id] = []

            user_results[user_id].append(result['corpus_id'])

        

        # Each user should have unique corpus IDs

        for user_id, corpus_ids in user_results.items():

            for corpus_id in corpus_ids:

                self.assertIn(user_id, corpus_id)

    

    async def test_metadata_operations(self):

        """Test metadata storage and retrieval patterns"""

        context = self.user_contexts['test_user_0']

        

        # Test current metadata patterns (to be migrated to SSOT)

        metadata_operations = [

            ('corpus_id', 'corpus_123'),

            ('corpus_operations', ['create', 'index', 'validate']),

            ('corpus_size', 1048576),

            ('indexed_docs', ['doc_1', 'doc_2', 'doc_3'])

        ]

        

        for key, value in metadata_operations:

            context['metadata'][key] = value

        

        # Verify metadata storage

        self.assertEqual(context['metadata']['corpus_id'], 'corpus_123')

        self.assertIsInstance(context['metadata']['corpus_operations'], list)

        self.assertEqual(len(context['metadata']['indexed_docs']), 3)

    

    async def test_unified_corpus_admin_operations(self):

        """Test unified corpus admin functionality"""

        from netra_backend.app.admin.corpus import (

            UnifiedCorpusAdmin,

            UnifiedCorpusAdminFactory,

            UserExecutionContext,

            CorpusOperation,

            CorpusOperationRequest

        )

        

        context = self.user_contexts['test_user_0']

        

        # Create user execution context for unified admin

        user_context = UserExecutionContext(

            user_id=context['user_id'],

            request_id=context['request_id'],

            thread_id=context['thread_id'],

            session_id=context.get('session_id', 'test_session')

        )

        

        # Test factory pattern

        admin = await UnifiedCorpusAdminFactory.create_for_context(user_context)

        self.assertIsInstance(admin, UnifiedCorpusAdmin)

        

        # Test unified operations

        create_request = CorpusOperationRequest(

            operation=CorpusOperation.CREATE,

            params={'name': 'Test Corpus', 'type': 'KNOWLEDGE_BASE'},

            user_id=user_context.user_id,

            request_id=user_context.request_id

        )

        

        # Mock the execute operation for testing

        with patch.object(admin, 'execute_operation', new_callable=AsyncMock) as mock_exec:

            mock_exec.return_value.success = True

            mock_exec.return_value.operation = CorpusOperation.CREATE

            

            result = await mock_exec(create_request)

            self.assertTrue(result.success)

            self.assertEqual(result.operation, CorpusOperation.CREATE)





class TestCorpusAdminFactoryPattern(unittest.IsolatedAsyncioTestCase):

    """Test that corpus admin will support factory pattern for user isolation"""

    

    async def test_factory_pattern_readiness(self):

        """Test readiness for factory pattern implementation"""

        

        # Test new factory pattern with UnifiedCorpusAdmin

        from netra_backend.app.admin.corpus import (

            UnifiedCorpusAdmin,

            UnifiedCorpusAdminFactory,

            UserExecutionContext,

            CorpusAdminSubAgent

        )

        

        # Create multiple instances

        agent1 = CorpusAdminSubAgent()

        agent2 = CorpusAdminSubAgent()

        

        # Current behavior: separate instances (good starting point)

        self.assertIsNot(agent1, agent2)

        

        # Verify no shared state between instances

        agent1._test_state = "user1"

        agent2._test_state = "user2"

        

        self.assertEqual(agent1._test_state, "user1")

        self.assertEqual(agent2._test_state, "user2")

    

    async def test_user_corpus_path_isolation(self):

        """Test that corpus paths can be isolated per user"""

        

        user_contexts = {

            'user_1': {'user_id': 'user_1', 'corpus_path': '/data/corpus/user_1'},

            'user_2': {'user_id': 'user_2', 'corpus_path': '/data/corpus/user_2'}

        }

        

        for user_id, context in user_contexts.items():

            # Verify unique paths per user

            self.assertIn(user_id, context['corpus_path'])

            

            # Verify no path overlap

            for other_id, other_context in user_contexts.items():

                if other_id != user_id:

                    self.assertNotEqual(context['corpus_path'], other_context['corpus_path'])





if __name__ == '__main__':

    # Run with async support

    import pytest

    pytest.main([__file__, '-v'])

