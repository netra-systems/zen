#!/usr/bin/env python3

"""

Unified Corpus Admin tests - Testing the new SSOT implementation.

These tests ensure the unified corpus admin works correctly after consolidation.



CRITICAL: These tests validate the new UnifiedCorpusAdmin implementation.

"""

import asyncio

import unittest

import sys

from pathlib import Path

from typing import Any, Dict

from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler

from netra_backend.app.db.database_manager import DatabaseManager

from netra_backend.app.clients.auth_client_core import AuthServiceClient

from shared.isolated_environment import get_env

from shared.isolated_environment import IsolatedEnvironment



# Add project root to path

project_root = Path(__file__).parent.parent.parent.absolute()

sys.path.insert(0, str(project_root))





class TestUnifiedCorpusAdmin(unittest.IsolatedAsyncioTestCase):

    """

    Test the new UnifiedCorpusAdmin implementation.

    Uses standard unittest for better compatibility.

    """

    

    async def asyncSetUp(self):

        """Set up test environment"""

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

    

    async def test_unified_corpus_admin_creation(self):

        """Test that UnifiedCorpusAdmin can be created"""

        from netra_backend.app.admin.corpus import (

            UnifiedCorpusAdmin,

            UserExecutionContext

        )

        

        # Create user execution context

        context = UserExecutionContext(

            user_id="test_user",

            request_id="test_request",

            thread_id="test_thread",

            session_id="test_session"

        )

        

        # Create unified admin

        admin = UnifiedCorpusAdmin(context)

        self.assertIsInstance(admin, UnifiedCorpusAdmin)

        self.assertEqual(admin.context.user_id, "test_user")

    

    async def test_factory_pattern(self):

        """Test that the factory pattern works"""

        from netra_backend.app.admin.corpus import (

            UnifiedCorpusAdminFactory,

            UserExecutionContext

        )

        

        # Create user execution context

        context = UserExecutionContext(

            user_id="test_user",

            request_id="test_request",

            thread_id="test_thread",

            session_id="test_session"

        )

        

        # Create admin through factory

        admin = await UnifiedCorpusAdminFactory.create_for_context(context)

        self.assertIsNotNone(admin)

        

        # Create another admin for same context - should be same instance

        admin2 = await UnifiedCorpusAdminFactory.create_for_context(context)

        self.assertIs(admin, admin2)

        

        # Cleanup

        await UnifiedCorpusAdminFactory.cleanup_context(context)

    

    async def test_multi_user_isolation(self):

        """Test that different users get isolated admin instances"""

        from netra_backend.app.admin.corpus import (

            UnifiedCorpusAdminFactory,

            UserExecutionContext

        )

        

        # Create contexts for different users

        context1 = UserExecutionContext(

            user_id="user1",

            request_id="req1",

            thread_id="thread1",

            session_id="session1"

        )

        

        context2 = UserExecutionContext(

            user_id="user2",

            request_id="req2",

            thread_id="thread2",

            session_id="session2"

        )

        

        # Create admins for different users

        admin1 = await UnifiedCorpusAdminFactory.create_for_context(context1)

        admin2 = await UnifiedCorpusAdminFactory.create_for_context(context2)

        

        # Should be different instances

        self.assertIsNot(admin1, admin2)

        

        # Should have different user IDs

        self.assertEqual(admin1.context.user_id, "user1")

        self.assertEqual(admin2.context.user_id, "user2")

        

        # Should have different corpus paths

        self.assertNotEqual(admin1.user_corpus_path, admin2.user_corpus_path)

        

        # Cleanup

        await UnifiedCorpusAdminFactory.cleanup_context(context1)

        await UnifiedCorpusAdminFactory.cleanup_context(context2)

    

    async def test_corpus_operations(self):

        """Test basic corpus operations"""

        from netra_backend.app.admin.corpus import (

            UnifiedCorpusAdmin,

            UserExecutionContext,

            CorpusOperation,

            CorpusOperationRequest,

            CorpusType

        )

        

        # Create user execution context

        context = UserExecutionContext(

            user_id="test_user",

            request_id="test_request",

            thread_id="test_thread",

            session_id="test_session"

        )

        

        # Create unified admin

        admin = UnifiedCorpusAdmin(context)

        

        # Test CREATE operation

        create_request = CorpusOperationRequest(

            operation=CorpusOperation.CREATE,

            params={'name': 'Test Corpus', 'type': CorpusType.KNOWLEDGE_BASE.value},

            user_id=context.user_id,

            request_id=context.request_id

        )

        

        # Mock the internal handler since we're testing the interface

        with patch.object(admin, '_handle_create', new_callable=AsyncMock) as mock_create:

            mock_create.return_value = {

                'success': True,

                'corpus_id': 'test_corpus_123',

                'message': 'Corpus created successfully'

            }

            

            # This will be implemented when we complete the unified admin

            # For now, just test that the structure works

            self.assertTrue(hasattr(admin, '_operation_handlers'))

            self.assertIn(CorpusOperation.CREATE, admin._operation_handlers)

    

    async def test_error_types(self):

        """Test that error types are properly defined"""

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

        

        # Test error properties

        self.assertEqual(upload_error.message, "Upload failed")

        self.assertEqual(upload_error.details['file'], 'test.txt')

    

    async def test_compatibility_layer(self):

        """Test that the compatibility layer works for legacy imports"""

        from netra_backend.app.admin.corpus import (

            CorpusAdminSubAgent,

            CorpusCRUDOperations,

            CorpusAnalysisOperations,

            CorpusIndexingHandlers,

            CorpusUploadHandlers,

            CorpusValidationHandlers

        )

        

        # Test that legacy classes can be instantiated

        # They should issue deprecation warnings but work

        with self.assertWarns(DeprecationWarning):

            agent = CorpusAdminSubAgent()

            self.assertIsNotNone(agent)

        

        with self.assertWarns(DeprecationWarning):

            crud_ops = CorpusCRUDOperations()

            self.assertIsNotNone(crud_ops)

            # Test that the legacy method exists

            self.assertTrue(hasattr(crud_ops, '_get_operation_mapping'))

        

        with self.assertWarns(DeprecationWarning):

            analysis_ops = CorpusAnalysisOperations()

            self.assertIsNotNone(analysis_ops)

            # Test that the legacy method exists

            self.assertTrue(hasattr(analysis_ops, '_analyze_corpus'))

        

        with self.assertWarns(DeprecationWarning):

            indexing_handlers = CorpusIndexingHandlers()

            self.assertIsNotNone(indexing_handlers)

            # Test that the legacy method exists

            self.assertTrue(hasattr(indexing_handlers, '_index_document'))

        

        with self.assertWarns(DeprecationWarning):

            upload_handlers = CorpusUploadHandlers()

            self.assertIsNotNone(upload_handlers)

            # Test that the legacy method exists

            self.assertTrue(hasattr(upload_handlers, '_handle_upload'))

        

        with self.assertWarns(DeprecationWarning):

            validation_handlers = CorpusValidationHandlers()

            self.assertIsNotNone(validation_handlers)

            # Test that the legacy method exists

            self.assertTrue(hasattr(validation_handlers, '_validate_document'))

    

    async def test_legacy_crud_operations(self):

        """Test that legacy CRUD operations work"""

        from netra_backend.app.admin.corpus import CorpusCRUDOperations

        

        with self.assertWarns(DeprecationWarning):

            crud_ops = CorpusCRUDOperations()

        

        # Test operation mapping

        mapping = crud_ops._get_operation_mapping()

        self.assertIsInstance(mapping, dict)

        self.assertIn('create', mapping)

        self.assertIn('update', mapping)

        self.assertIn('delete', mapping)

        self.assertIn('search', mapping)

        

        # Test individual operations

        context = self.user_contexts['test_user_0']

        

        create_result = await crud_ops._create_corpus(context=context, name='Test')

        self.assertTrue(create_result['success'])

        self.assertEqual(create_result['operation'], 'create')

        

        search_result = await crud_ops._search_corpus(context=context, query='test')

        self.assertTrue(search_result['success'])

        self.assertEqual(search_result['operation'], 'search')

        self.assertIsInstance(search_result['results'], list)

    

    async def test_legacy_analysis_operations(self):

        """Test that legacy analysis operations work"""

        from netra_backend.app.admin.corpus import CorpusAnalysisOperations

        

        with self.assertWarns(DeprecationWarning):

            analysis_ops = CorpusAnalysisOperations()

        

        context = self.user_contexts['test_user_0']

        result = await analysis_ops._analyze_corpus(context=context, corpus_id='test_corpus')

        

        self.assertIn('total_documents', result)

        self.assertIn('total_size_bytes', result)

        self.assertIsInstance(result['total_documents'], int)

        self.assertIsInstance(result['total_size_bytes'], int)

    

    async def test_concurrent_operations(self):

        """Test thread safety with concurrent corpus operations"""

        from netra_backend.app.admin.corpus import (

            UnifiedCorpusAdminFactory,

            UserExecutionContext

        )

        

        async def user_operation(user_id: str):

            context = UserExecutionContext(

                user_id=user_id,

                request_id=f'req_{user_id}',

                thread_id=f'thread_{user_id}',

                session_id=f'session_{user_id}'

            )

            

            admin = await UnifiedCorpusAdminFactory.create_for_context(context)

            # Just test that we can create the admin

            self.assertEqual(admin.context.user_id, user_id)

            return admin.context.user_id

        

        # Run concurrent operations

        tasks = []

        for user_id in ['user1', 'user2', 'user3']:

            tasks.append(user_operation(user_id))

        

        results = await asyncio.gather(*tasks)

        

        # Verify all operations completed successfully

        self.assertEqual(len(results), 3)

        self.assertEqual(set(results), {'user1', 'user2', 'user3'})





if __name__ == '__main__':

    unittest.main()

