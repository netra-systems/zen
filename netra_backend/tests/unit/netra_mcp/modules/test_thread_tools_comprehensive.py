"""
Comprehensive Unit Tests for ThreadTools MCP Module

Business Value: Platform/Internal - Thread Management Infrastructure & AI Chat Sessions
- Validates thread lifecycle management operations for multi-user AI chat
- Ensures MCP tool registration and execution reliability
- Provides coverage for thread creation and history retrieval business logic
- Supports core chat functionality that delivers 90% of platform value

Test Coverage Target: 100% of all public and private methods
Test Categories: Thread Creation, Thread History, Error Handling, Validation, Edge Cases

CRITICAL REQUIREMENTS:
- Tests real business logic without bypassing validation
- Uses SSOT patterns from test_framework
- Strongly typed IDs from shared.types.core_types
- Comprehensive error handling validation
- Thread service integration testing
"""
import json
import uuid
import pytest
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, Mock, MagicMock, patch, call
from test_framework.ssot import BaseTestCase, get_mock_factory
from shared.types.core_types import UserID, ThreadID, RequestID
from netra_backend.app.netra_mcp.modules.thread_tools import ThreadTools

class TestThreadToolsComprehensive(BaseTestCase):
    """Comprehensive test suite for ThreadTools MCP module."""

    def setUp(self):
        """Set up test fixtures using SSOT patterns."""
        super().setUp()
        self.mock_factory = get_mock_factory()
        self.mock_mcp_instance = Mock()
        self.mock_mcp_instance.tool = Mock()
        self.mock_server = Mock()
        self.mock_thread_service = AsyncMock()
        self.mock_server.thread_service = self.mock_thread_service
        self.thread_tools = ThreadTools(self.mock_mcp_instance)
        self.test_user_id = UserID('test_user_123')
        self.test_thread_id = ThreadID('thread_456')
        self.test_request_id = RequestID('req_789')
        self.test_thread_title = 'Test Thread Title'
        self.test_metadata = {'user_id': str(self.test_user_id), 'priority': 'high', 'category': 'chat'}
        self.mock_thread_service.create_thread = AsyncMock(return_value=str(self.test_thread_id))
        self.mock_thread_service.get_thread_messages = AsyncMock(return_value=[{'id': 'msg_1', 'content': 'Hello', 'role': 'user', 'created_at': '2025-01-01T10:00:00Z'}, {'id': 'msg_2', 'content': 'Hi there!', 'role': 'assistant', 'created_at': '2025-01-01T10:00:30Z'}])

    def tearDown(self):
        """Clean up test fixtures."""
        super().tearDown()

    def test_thread_tools_initialization(self):
        """Test ThreadTools proper initialization."""
        thread_tools = ThreadTools(self.mock_mcp_instance)
        self.assertEqual(thread_tools.mcp, self.mock_mcp_instance)
        self.assertIsNotNone(thread_tools)

    def test_register_all_tools(self):
        """Test registration of all thread management tools."""
        self.thread_tools.register_all(self.mock_server)
        self.assertEqual(self.mock_mcp_instance.tool.call_count, 2)
        calls = self.mock_mcp_instance.tool.call_args_list
        self.assertEqual(len(calls), 2)

    @pytest.mark.asyncio
    async def test_thread_creation_success(self):
        """Test successful thread creation with proper metadata."""
        self.thread_tools._register_create_thread_tool(self.mock_server)
        create_thread_func = self.mock_mcp_instance.tool.call_args_list[0][0][0]
        result = await create_thread_func(title=self.test_thread_title, metadata=self.test_metadata.copy())
        self.mock_thread_service.create_thread.assert_called_once()
        call_args = self.mock_thread_service.create_thread.call_args
        self.assertEqual(call_args.kwargs['title'], self.test_thread_title)
        expected_metadata = self.test_metadata.copy()
        expected_metadata['source'] = 'mcp'
        self.assertEqual(call_args.kwargs['metadata'], expected_metadata)
        result_data = json.loads(result)
        self.assertEqual(result_data['thread_id'], str(self.test_thread_id))
        self.assertEqual(result_data['title'], self.test_thread_title)
        self.assertTrue(result_data['created'])

    @pytest.mark.asyncio
    async def test_thread_creation_with_default_title(self):
        """Test thread creation with default title when none provided."""
        self.thread_tools._register_create_thread_tool(self.mock_server)
        create_thread_func = self.mock_mcp_instance.tool.call_args_list[0][0][0]
        result = await create_thread_func()
        call_args = self.mock_thread_service.create_thread.call_args
        self.assertEqual(call_args.kwargs['title'], 'New Thread')
        expected_metadata = {'source': 'mcp'}
        self.assertEqual(call_args.kwargs['metadata'], expected_metadata)

    @pytest.mark.asyncio
    async def test_thread_creation_with_none_metadata(self):
        """Test thread creation with None metadata."""
        self.thread_tools._register_create_thread_tool(self.mock_server)
        create_thread_func = self.mock_mcp_instance.tool.call_args_list[0][0][0]
        result = await create_thread_func(title=self.test_thread_title, metadata=None)
        call_args = self.mock_thread_service.create_thread.call_args
        expected_metadata = {'source': 'mcp'}
        self.assertEqual(call_args.kwargs['metadata'], expected_metadata)

    @pytest.mark.asyncio
    async def test_thread_creation_thread_service_unavailable(self):
        """Test thread creation when thread service is not available."""
        self.mock_server.thread_service = None
        self.thread_tools._register_create_thread_tool(self.mock_server)
        create_thread_func = self.mock_mcp_instance.tool.call_args_list[0][0][0]
        result = await create_thread_func(title=self.test_thread_title)
        result_data = json.loads(result)
        self.assertIn('error', result_data)
        self.assertEqual(result_data['error'], 'Thread service not available')

    @pytest.mark.asyncio
    async def test_thread_creation_service_exception(self):
        """Test thread creation handling service exceptions."""
        self.mock_thread_service.create_thread.side_effect = Exception('Database connection failed')
        self.thread_tools._register_create_thread_tool(self.mock_server)
        create_thread_func = self.mock_mcp_instance.tool.call_args_list[0][0][0]
        result = await create_thread_func(title=self.test_thread_title)
        result_data = json.loads(result)
        self.assertIn('error', result_data)
        self.assertEqual(result_data['error'], 'Database connection failed')

    @pytest.mark.asyncio
    async def test_thread_history_success(self):
        """Test successful thread history retrieval."""
        self.thread_tools._register_thread_history_tool(self.mock_server)
        get_history_func = self.mock_mcp_instance.tool.call_args_list[0][0][0]
        result = await get_history_func(thread_id=str(self.test_thread_id), limit=50)
        self.mock_thread_service.get_thread_messages.assert_called_once_with(thread_id=str(self.test_thread_id), limit=50)
        result_data = json.loads(result)
        self.assertEqual(len(result_data), 2)
        self.assertEqual(result_data[0]['id'], 'msg_1')
        self.assertEqual(result_data[1]['id'], 'msg_2')

    @pytest.mark.asyncio
    async def test_thread_history_custom_limit(self):
        """Test thread history with custom limit parameter."""
        self.thread_tools._register_thread_history_tool(self.mock_server)
        get_history_func = self.mock_mcp_instance.tool.call_args_list[0][0][0]
        custom_limit = 25
        result = await get_history_func(thread_id=str(self.test_thread_id), limit=custom_limit)
        self.mock_thread_service.get_thread_messages.assert_called_once_with(thread_id=str(self.test_thread_id), limit=custom_limit)

    @pytest.mark.asyncio
    async def test_thread_history_default_limit(self):
        """Test thread history with default limit when not specified."""
        self.thread_tools._register_thread_history_tool(self.mock_server)
        get_history_func = self.mock_mcp_instance.tool.call_args_list[0][0][0]
        result = await get_history_func(thread_id=str(self.test_thread_id))
        self.mock_thread_service.get_thread_messages.assert_called_once_with(thread_id=str(self.test_thread_id), limit=50)

    @pytest.mark.asyncio
    async def test_thread_history_service_unavailable(self):
        """Test thread history when thread service is not available."""
        self.mock_server.thread_service = None
        self.thread_tools._register_thread_history_tool(self.mock_server)
        get_history_func = self.mock_mcp_instance.tool.call_args_list[0][0][0]
        result = await get_history_func(thread_id=str(self.test_thread_id))
        result_data = json.loads(result)
        self.assertIn('error', result_data)
        self.assertEqual(result_data['error'], 'Thread service not available')

    @pytest.mark.asyncio
    async def test_thread_history_service_exception(self):
        """Test thread history handling service exceptions."""
        self.mock_thread_service.get_thread_messages.side_effect = Exception('Query timeout')
        self.thread_tools._register_thread_history_tool(self.mock_server)
        get_history_func = self.mock_mcp_instance.tool.call_args_list[0][0][0]
        result = await get_history_func(thread_id=str(self.test_thread_id))
        result_data = json.loads(result)
        self.assertIn('error', result_data)
        self.assertEqual(result_data['error'], 'Query timeout')

    @pytest.mark.asyncio
    async def test_execute_thread_creation_success_path(self):
        """Test _execute_thread_creation success path."""
        result = await self.thread_tools._execute_thread_creation(self.mock_server, self.test_thread_title, self.test_metadata.copy())
        result_data = json.loads(result)
        self.assertEqual(result_data['thread_id'], str(self.test_thread_id))
        self.assertEqual(result_data['title'], self.test_thread_title)
        self.assertTrue(result_data['created'])

    @pytest.mark.asyncio
    async def test_execute_thread_creation_no_service(self):
        """Test _execute_thread_creation when service is unavailable."""
        self.mock_server.thread_service = None
        result = await self.thread_tools._execute_thread_creation(self.mock_server, self.test_thread_title, self.test_metadata.copy())
        result_data = json.loads(result)
        self.assertIn('error', result_data)
        self.assertEqual(result_data['error'], 'Thread service not available')

    @pytest.mark.asyncio
    async def test_perform_thread_creation(self):
        """Test _perform_thread_creation business logic."""
        result = await self.thread_tools._perform_thread_creation(self.mock_server, self.test_thread_title, self.test_metadata.copy())
        self.mock_thread_service.create_thread.assert_called_once()
        call_args = self.mock_thread_service.create_thread.call_args
        expected_metadata = self.test_metadata.copy()
        expected_metadata['source'] = 'mcp'
        self.assertEqual(call_args.kwargs['metadata'], expected_metadata)
        result_data = json.loads(result)
        self.assertEqual(result_data['thread_id'], str(self.test_thread_id))
        self.assertEqual(result_data['title'], self.test_thread_title)

    def test_prepare_thread_metadata_with_data(self):
        """Test _prepare_thread_metadata with existing metadata."""
        input_metadata = self.test_metadata.copy()
        result = self.thread_tools._prepare_thread_metadata(input_metadata)
        expected = input_metadata.copy()
        expected['source'] = 'mcp'
        self.assertEqual(result, expected)

    def test_prepare_thread_metadata_with_none(self):
        """Test _prepare_thread_metadata with None input."""
        result = self.thread_tools._prepare_thread_metadata(None)
        expected = {'source': 'mcp'}
        self.assertEqual(result, expected)

    def test_prepare_thread_metadata_with_empty_dict(self):
        """Test _prepare_thread_metadata with empty dictionary."""
        result = self.thread_tools._prepare_thread_metadata({})
        expected = {'source': 'mcp'}
        self.assertEqual(result, expected)

    def test_format_thread_result(self):
        """Test _format_thread_result formatting logic."""
        result = self.thread_tools._format_thread_result(str(self.test_thread_id), self.test_thread_title)
        result_data = json.loads(result)
        expected = {'thread_id': str(self.test_thread_id), 'title': self.test_thread_title, 'created': True}
        self.assertEqual(result_data, expected)

    def test_format_service_error(self):
        """Test _format_service_error formatting logic."""
        error_message = 'Database connection timeout'
        result = self.thread_tools._format_service_error(error_message)
        result_data = json.loads(result)
        expected = {'error': error_message}
        self.assertEqual(result_data, expected)

    @pytest.mark.asyncio
    async def test_execute_thread_history_query_success(self):
        """Test _execute_thread_history_query success path."""
        result = await self.thread_tools._execute_thread_history_query(self.mock_server, str(self.test_thread_id), 50)
        self.mock_thread_service.get_thread_messages.assert_called_once_with(thread_id=str(self.test_thread_id), limit=50)
        result_data = json.loads(result)
        self.assertEqual(len(result_data), 2)

    @pytest.mark.asyncio
    async def test_fetch_thread_messages(self):
        """Test _fetch_thread_messages business logic."""
        result = await self.thread_tools._fetch_thread_messages(self.mock_server, str(self.test_thread_id), 25)
        self.mock_thread_service.get_thread_messages.assert_called_once_with(thread_id=str(self.test_thread_id), limit=25)
        result_data = json.loads(result)
        self.assertEqual(len(result_data), 2)
        self.assertEqual(result_data[0]['id'], 'msg_1')

    @pytest.mark.asyncio
    async def test_thread_creation_empty_string_title(self):
        """Test thread creation with empty string title."""
        self.thread_tools._register_create_thread_tool(self.mock_server)
        create_thread_func = self.mock_mcp_instance.tool.call_args_list[0][0][0]
        result = await create_thread_func(title='', metadata=None)
        call_args = self.mock_thread_service.create_thread.call_args
        self.assertEqual(call_args.kwargs['title'], '')

    @pytest.mark.asyncio
    async def test_thread_history_zero_limit(self):
        """Test thread history with zero limit."""
        self.thread_tools._register_thread_history_tool(self.mock_server)
        get_history_func = self.mock_mcp_instance.tool.call_args_list[0][0][0]
        result = await get_history_func(thread_id=str(self.test_thread_id), limit=0)
        self.mock_thread_service.get_thread_messages.assert_called_once_with(thread_id=str(self.test_thread_id), limit=0)

    @pytest.mark.asyncio
    async def test_thread_history_negative_limit(self):
        """Test thread history with negative limit."""
        self.thread_tools._register_thread_history_tool(self.mock_server)
        get_history_func = self.mock_mcp_instance.tool.call_args_list[0][0][0]
        result = await get_history_func(thread_id=str(self.test_thread_id), limit=-1)
        self.mock_thread_service.get_thread_messages.assert_called_once_with(thread_id=str(self.test_thread_id), limit=-1)

    @pytest.mark.asyncio
    async def test_thread_creation_very_large_metadata(self):
        """Test thread creation with large metadata object."""
        large_metadata = {f'field_{i}': f'value_{i}' for i in range(100)}
        self.thread_tools._register_create_thread_tool(self.mock_server)
        create_thread_func = self.mock_mcp_instance.tool.call_args_list[0][0][0]
        result = await create_thread_func(title=self.test_thread_title, metadata=large_metadata)
        call_args = self.mock_thread_service.create_thread.call_args
        expected_metadata = large_metadata.copy()
        expected_metadata['source'] = 'mcp'
        self.assertEqual(call_args.kwargs['metadata'], expected_metadata)

    @pytest.mark.asyncio
    async def test_thread_history_empty_thread_id(self):
        """Test thread history with empty thread ID."""
        self.thread_tools._register_thread_history_tool(self.mock_server)
        get_history_func = self.mock_mcp_instance.tool.call_args_list[0][0][0]
        result = await get_history_func(thread_id='', limit=50)
        self.mock_thread_service.get_thread_messages.assert_called_once_with(thread_id='', limit=50)

    @pytest.mark.asyncio
    async def test_multiple_tool_registrations(self):
        """Test that multiple tool registrations work correctly."""
        self.thread_tools.register_all(self.mock_server)
        self.thread_tools.register_all(self.mock_server)
        self.assertEqual(self.mock_mcp_instance.tool.call_count, 4)

    def test_thread_tools_with_different_mcp_instances(self):
        """Test ThreadTools with different MCP instances."""
        mock_mcp_2 = Mock()
        mock_mcp_2.tool = Mock()
        thread_tools_2 = ThreadTools(mock_mcp_2)
        self.assertEqual(self.thread_tools.mcp, self.mock_mcp_instance)
        self.assertEqual(thread_tools_2.mcp, mock_mcp_2)
        self.assertNotEqual(self.thread_tools.mcp, thread_tools_2.mcp)

    @pytest.mark.asyncio
    async def test_concurrent_thread_operations(self):
        """Test ThreadTools handling concurrent operations."""
        import asyncio
        self.thread_tools._register_create_thread_tool(self.mock_server)
        self.thread_tools._register_thread_history_tool(self.mock_server)
        create_func = self.mock_mcp_instance.tool.call_args_list[0][0][0]
        history_func = self.mock_mcp_instance.tool.call_args_list[1][0][0]
        tasks = [create_func(title='Thread 1'), create_func(title='Thread 2'), history_func(thread_id='thread_1'), history_func(thread_id='thread_2')]
        results = await asyncio.gather(*tasks)
        self.assertEqual(len(results), 4)
        self.assertEqual(self.mock_thread_service.create_thread.call_count, 2)
        self.assertEqual(self.mock_thread_service.get_thread_messages.call_count, 2)

    def test_metadata_source_injection_business_rule(self):
        """Test that MCP source is always injected into metadata (business requirement)."""
        test_cases = [None, {}, {'existing': 'data'}, {'source': 'existing_source'}]
        for input_metadata in test_cases:
            with self.subTest(metadata=input_metadata):
                result = self.thread_tools._prepare_thread_metadata(input_metadata)
                self.assertEqual(result['source'], 'mcp')
                if input_metadata and input_metadata != {}:
                    for key, value in input_metadata.items():
                        if key != 'source':
                            self.assertEqual(result[key], value)

    @pytest.mark.asyncio
    async def test_error_propagation_business_requirement(self):
        """Test that errors are properly propagated to users (business requirement)."""
        error_scenarios = [('Service timeout', 'Service timeout'), ('Invalid thread ID', 'Invalid thread ID'), ('Permission denied', 'Permission denied'), ('', '')]
        for service_error, expected_error in error_scenarios:
            with self.subTest(error=service_error):
                self.mock_thread_service.create_thread.side_effect = Exception(service_error)
                self.thread_tools._register_create_thread_tool(self.mock_server)
                create_func = self.mock_mcp_instance.tool.call_args_list[-1][0][0]
                result = await create_func(title='Test')
                result_data = json.loads(result)
                self.assertIn('error', result_data)
                self.assertEqual(result_data['error'], expected_error)
                self.mock_mcp_instance.tool.reset_mock()
                self.mock_thread_service.create_thread.side_effect = None
                self.mock_thread_service.create_thread.return_value = str(self.test_thread_id)

    @pytest.mark.asyncio
    async def test_json_response_formatting_business_requirement(self):
        """Test that all responses are properly formatted JSON (business requirement)."""
        self.thread_tools._register_create_thread_tool(self.mock_server)
        self.thread_tools._register_thread_history_tool(self.mock_server)
        create_func = self.mock_mcp_instance.tool.call_args_list[0][0][0]
        history_func = self.mock_mcp_instance.tool.call_args_list[1][0][0]
        create_result = await create_func(title='Test')
        self.assertIsInstance(json.loads(create_result), dict)
        history_result = await history_func(thread_id='test')
        self.assertIsInstance(json.loads(history_result), list)
        self.mock_server.thread_service = None
        error_create_result = await create_func(title='Test')
        self.assertIsInstance(json.loads(error_create_result), dict)
        self.assertIn('error', json.loads(error_create_result))
        error_history_result = await history_func(thread_id='test')
        self.assertIsInstance(json.loads(error_history_result), dict)
        self.assertIn('error', json.loads(error_history_result))
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')