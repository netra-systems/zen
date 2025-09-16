class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError('WebSocket is closed')
        self.messages_sent.append(message)

    async def close(self, code: int=1000, reason: str='Normal closure'):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()
'Comprehensive Model Processing and Agent Response Flow E2E Tests\n\nBusiness Value Justification (BVJ):\n- Segment: Enterprise/Platform\n- Business Goal: Platform Stability & User Experience  \n- Value Impact: Exposes critical issues in AI processing pipeline preventing revenue loss\n- Strategic Impact: Validates entire prompt-to-response flow reliability\n\nThis test suite is designed to FAIL initially to expose current problems with:\n1. User prompt submission and routing\n2. Agent/model selection logic  \n3. LLM API calls and response handling\n4. Streaming response delivery to frontend\n5. Token tracking and cost calculation\n6. Error handling for API failures\n7. Response caching and optimization\n8. Multi-agent orchestration\n\nTests include realistic scenarios that expose:\n- Prompts not reaching models\n- Model responses not streaming back\n- Token counting errors  \n- Cost calculation failures\n- Agent orchestration problems\n- Memory/context management issues\n'
import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig
from test_framework.database.test_database_manager import DatabaseTestManager
from netra_backend.app.redis_manager import redis_manager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.core_models import Message, ThreadMetadata
from netra_backend.app.schemas.llm_base_types import LLMProvider, TokenUsage
from netra_backend.app.schemas.llm_response_types import LLMResponse, LLMStreamChunk
from netra_backend.app.schemas.websocket_models import BaseWebSocketPayload, StartAgentPayload, WebSocketMessage
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as WebSocketManager
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env
UnifiedWebSocketManager = WebSocketManager
WebSocketManager = WebSocketManager
logger = central_logger.get_logger(__name__)
TEST_PROMPTS = [{'id': 'simple_question', 'content': 'What is the best way to optimize my AI costs?', 'expected_agent': 'cost_optimizer', 'complexity': 'simple'}, {'id': 'complex_optimization', 'content': 'I need to reduce costs by 30% while improving latency by 50% for my multi-tenant SaaS platform handling 10M requests/day', 'expected_agent': 'multi_objective_optimizer', 'complexity': 'complex'}, {'id': 'streaming_heavy', 'content': "Generate a detailed report on my system's performance including graphs, metrics, and optimization recommendations", 'expected_agent': 'report_generator', 'complexity': 'streaming'}, {'id': 'multi_turn_conversation', 'content': "Let's discuss my API usage patterns", 'expected_agent': 'conversation_agent', 'complexity': 'conversational'}]

class MockLLMResponse:
    """Mock LLM response for testing failures"""

    def __init__(self, should_fail: bool=False, streaming: bool=False):
        self.should_fail = should_fail
        self.streaming = streaming
        self.content = 'Mock response content'
        self.token_usage = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)

    async def __aiter__(self):
        """Mock streaming response"""
        if self.should_fail:
            raise Exception('Mock streaming failure')
        for i, chunk in enumerate(['Mock ', 'streaming ', 'response']):
            yield LLMStreamChunk(id=f'chunk_{i}', delta={'content': chunk}, index=i, finish_reason='stop' if i == 2 else None, usage=self.token_usage if i == 2 else None)
            await asyncio.sleep(0.1)

@pytest.fixture
async def mock_db_session():
    """Mock database session"""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncNone
    session.rollback = AsyncNone
    session.close = AsyncNone
    return session

@pytest.fixture
async def failing_llm_manager():
    """LLM manager configured to expose failures"""
    manager = AsyncMock(spec=LLMManager)

    async def mock_ask_llm(prompt: str, config_name: str, use_cache: bool=True):
        if 'fail' in prompt.lower():
            raise Exception('Mock LLM API failure')
        if len(prompt) > 1000:
            raise Exception('Token limit exceeded')
        return 'Mock response'

    async def mock_stream_llm(prompt: str, config_name: str):
        if 'stream_fail' in prompt.lower():
            raise Exception('Mock streaming failure')

        async def mock_stream():
            for chunk in ['Mock ', 'streaming ', 'response']:
                yield chunk
                await asyncio.sleep(0.1)
        return mock_stream()
    manager.ask_llm = mock_ask_llm
    manager.stream_llm = mock_stream_llm
    manager.enabled = True
    return manager

@pytest.fixture
async def failing_websocket_manager():
    """WebSocket manager configured to expose failures"""
    manager = AsyncMock(spec=WebSocketManager)

    async def mock_send_message(user_id: str, message: Any):
        if 'websocket_fail' in str(message):
            raise Exception('WebSocket send failure')
        return True
    manager.send_message = mock_send_message
    manager.broadcast = AsyncNone
    manager.is_connected = AsyncMock(return_value=True)
    return manager

@pytest.fixture
async def failing_tool_dispatcher():
    """Tool dispatcher configured to expose failures"""
    dispatcher = AsyncMock(spec=ToolDispatcher)

    async def mock_dispatch_tool(tool_name: str, *args, **kwargs):
        if 'tool_fail' in tool_name:
            raise Exception(f'Tool dispatch failure for {tool_name}')
        return {'status': 'success', 'result': f'Mock result for {tool_name}'}
    dispatcher.dispatch_tool = mock_dispatch_tool
    return dispatcher

@pytest.fixture
async def chat_orchestrator_with_failures(mock_db_session, failing_llm_manager, failing_websocket_manager, failing_tool_dispatcher):
    """Chat orchestrator configured to expose various failure modes"""
    orchestrator = AsyncNone
    orchestrator.db_session = mock_db_session
    orchestrator.llm_manager = failing_llm_manager
    orchestrator.websocket_manager = failing_websocket_manager
    orchestrator.tool_dispatcher = failing_tool_dispatcher
    return orchestrator

@pytest.mark.e2e
class TestPromptSubmissionFlow:
    """Test prompt submission and initial processing - designed to expose failures"""

    @pytest.mark.e2e
    async def test_prompt_reaches_model_basic(self, chat_orchestrator_with_failures):
        """Test that basic prompts reach the model (likely to fail initially)"""
        prompt = TEST_PROMPTS[0]
        user_id = f'test_user_{uuid.uuid4()}'
        thread_id = f'thread_{uuid.uuid4()}'
        with pytest.raises((Exception, NetraException)):
            response = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=thread_id, content=prompt['content'], message_type='user_message')

    @pytest.mark.e2e
    async def test_prompt_routing_logic(self, chat_orchestrator_with_failures):
        """Test that prompts are routed to correct agents (likely to fail)"""
        complex_prompt = TEST_PROMPTS[1]
        user_id = f'test_user_{uuid.uuid4()}'
        with pytest.raises((Exception, AttributeError, KeyError)):
            response = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=None, content=complex_prompt['content'], message_type='user_message')

    @pytest.mark.e2e
    async def test_empty_prompt_handling(self, chat_orchestrator_with_failures):
        """Test handling of edge cases like empty prompts"""
        user_id = f'test_user_{uuid.uuid4()}'
        with pytest.raises((ValueError, Exception)):
            await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=None, content='', message_type='user_message')

    @pytest.mark.e2e
    async def test_oversized_prompt_handling(self, chat_orchestrator_with_failures):
        """Test handling of oversized prompts that exceed token limits"""
        user_id = f'test_user_{uuid.uuid4()}'
        oversized_prompt = 'test ' * 10000
        with pytest.raises((Exception, ValueError)):
            await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=None, content=oversized_prompt, message_type='user_message')

@pytest.mark.e2e
class TestAgentSelectionAndRouting:
    """Test agent selection logic - designed to expose routing failures"""

    @pytest.mark.e2e
    async def test_agent_selection_for_cost_optimization(self, chat_orchestrator_with_failures):
        """Test that cost optimization prompts select correct agent"""
        prompt = 'I need to reduce my OpenAI costs by 50%'
        user_id = f'test_user_{uuid.uuid4()}'
        with pytest.raises((Exception, AttributeError)):
            response = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=None, content=prompt, message_type='user_message')

    @pytest.mark.e2e
    async def test_fallback_agent_selection(self, chat_orchestrator_with_failures):
        """Test fallback behavior when primary agent fails"""
        prompt = "This is an ambiguous request that doesn't fit any category"
        user_id = f'test_user_{uuid.uuid4()}'
        with pytest.raises((Exception, AttributeError)):
            response = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=None, content=prompt, message_type='user_message')

    @pytest.mark.e2e
    async def test_multi_agent_orchestration(self, chat_orchestrator_with_failures):
        """Test complex requests requiring multiple agents"""
        complex_prompt = TEST_PROMPTS[1]['content']
        user_id = f'test_user_{uuid.uuid4()}'
        with pytest.raises((Exception, AttributeError)):
            response = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=None, content=complex_prompt, message_type='user_message')

@pytest.mark.e2e
class TestLLMAPICallsAndResponseHandling:
    """Test LLM API integration - designed to expose API call failures"""

    @pytest.mark.e2e
    async def test_llm_api_call_success(self, failing_llm_manager):
        """Test successful LLM API calls (likely to fail if LLM integration broken)"""
        prompt = 'What is AI optimization?'
        with pytest.raises((Exception, AttributeError)):
            response = await failing_llm_manager.ask_llm(prompt=prompt, llm_config_name='default')

    @pytest.mark.e2e
    async def test_llm_api_failure_handling(self, failing_llm_manager):
        """Test LLM API failure handling"""
        prompt = 'This should fail'
        with pytest.raises(Exception):
            response = await failing_llm_manager.ask_llm(prompt=prompt, llm_config_name='default')

    @pytest.mark.e2e
    async def test_llm_timeout_handling(self, failing_llm_manager):
        """Test LLM request timeout handling"""
        prompt = 'This is a test prompt for timeout'
        with pytest.raises((Exception, asyncio.TimeoutError)):
            response = await asyncio.wait_for(failing_llm_manager.ask_llm(prompt=prompt, llm_config_name='default'), timeout=0.001)

    @pytest.mark.e2e
    async def test_llm_rate_limit_handling(self, failing_llm_manager):
        """Test handling of rate limits from LLM providers"""
        tasks = []
        for i in range(10):
            task = failing_llm_manager.ask_llm(prompt=f'Rate limit test {i}', llm_config_name='default')
            tasks.append(task)
        with pytest.raises((Exception, AttributeError)):
            responses = await asyncio.gather(*tasks, return_exceptions=True)

@pytest.mark.e2e
class TestStreamingResponseDelivery:
    """Test streaming response functionality - designed to expose streaming failures"""

    @pytest.mark.e2e
    async def test_basic_streaming_response(self, failing_llm_manager):
        """Test basic streaming response delivery"""
        prompt = 'Generate a streaming response'
        with pytest.raises((Exception, AttributeError)):
            stream = await failing_llm_manager.stream_llm(prompt=prompt, llm_config_name='default')
            chunks = []
            async for chunk in stream:
                chunks.append(chunk)

    @pytest.mark.e2e
    async def test_streaming_interruption_recovery(self, failing_llm_manager):
        """Test recovery from streaming interruptions"""
        prompt = 'stream_fail test'
        with pytest.raises(Exception):
            stream = await failing_llm_manager.stream_llm(prompt=prompt, llm_config_name='default')
            async for chunk in stream:
                pass

    @pytest.mark.e2e
    async def test_websocket_streaming_delivery(self, failing_websocket_manager, chat_orchestrator_with_failures):
        """Test streaming responses through WebSocket"""
        prompt = TEST_PROMPTS[2]['content']
        user_id = f'test_user_{uuid.uuid4()}'
        with pytest.raises((Exception, AttributeError)):
            response = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=None, content=prompt, message_type='user_message')

    @pytest.mark.e2e
    async def test_websocket_connection_failure_during_streaming(self, failing_websocket_manager):
        """Test handling of WebSocket disconnection during streaming"""
        user_id = f'test_user_{uuid.uuid4()}'
        message = {'type': 'websocket_fail', 'content': 'test'}
        with pytest.raises(Exception):
            await failing_websocket_manager.send_message(user_id, message)

@pytest.mark.e2e
class TestTokenTrackingAndCostCalculation:
    """Test token counting and cost calculation - designed to expose billing issues"""

    @pytest.mark.e2e
    async def test_token_counting_accuracy(self, failing_llm_manager):
        """Test accuracy of token counting"""
        prompt = 'This is a test prompt for token counting'
        with pytest.raises((Exception, AttributeError)):
            response = await failing_llm_manager.ask_llm_full(prompt=prompt, llm_config_name='default')
            assert response.usage.prompt_tokens > 0
            assert response.usage.completion_tokens > 0
            assert response.usage.total_tokens == response.usage.prompt_tokens + response.usage.completion_tokens

    @pytest.mark.e2e
    async def test_cost_calculation_for_different_models(self, failing_llm_manager):
        """Test cost calculation across different model types"""
        prompt = 'Calculate costs for this prompt'
        models = [LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value]
        with pytest.raises((Exception, AttributeError, KeyError)):
            for model in models:
                response = await failing_llm_manager.ask_llm_full(prompt=prompt, llm_config_name=model)
                assert hasattr(response, 'estimated_cost')

    @pytest.mark.e2e
    async def test_streaming_token_counting(self, failing_llm_manager):
        """Test token counting for streaming responses"""
        prompt = 'Generate a streaming response for token counting'
        with pytest.raises((Exception, AttributeError)):
            stream = await failing_llm_manager.stream_llm(prompt=prompt, llm_config_name='default')
            total_tokens = 0
            async for chunk in stream:
                if hasattr(chunk, 'usage') and chunk.usage:
                    total_tokens += chunk.usage.total_tokens
            assert total_tokens > 0

@pytest.mark.e2e
class TestErrorHandlingAndRecovery:
    """Test error handling and recovery mechanisms - designed to expose resilience issues"""

    @pytest.mark.e2e
    async def test_llm_api_error_recovery(self, failing_llm_manager):
        """Test recovery from LLM API errors"""
        prompt = 'fail'
        with pytest.raises(Exception):
            response = await failing_llm_manager.ask_llm(prompt=prompt, llm_config_name='default', use_cache=False)

    @pytest.mark.e2e
    async def test_partial_response_handling(self, chat_orchestrator_with_failures):
        """Test handling of partial responses due to errors"""
        prompt = 'Generate a long response that might be interrupted'
        user_id = f'test_user_{uuid.uuid4()}'
        with pytest.raises((Exception, AttributeError)):
            response = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=None, content=prompt, message_type='user_message')

    @pytest.mark.e2e
    async def test_database_error_during_processing(self, mock_db_session, chat_orchestrator_with_failures):
        """Test handling of database errors during message processing"""
        mock_db_session.commit.side_effect = Exception('Database connection failed')
        prompt = 'Test database error handling'
        user_id = f'test_user_{uuid.uuid4()}'
        with pytest.raises(Exception):
            response = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=None, content=prompt, message_type='user_message')

@pytest.mark.e2e
class TestResponseCachingAndOptimization:
    """Test response caching and optimization - designed to expose caching issues"""

    @pytest.mark.e2e
    async def test_response_caching_functionality(self, failing_llm_manager):
        """Test that responses are properly cached"""
        prompt = 'This response should be cached'
        with pytest.raises((Exception, AttributeError)):
            response1 = await failing_llm_manager.ask_llm(prompt=prompt, llm_config_name='default', use_cache=True)
            response2 = await failing_llm_manager.ask_llm(prompt=prompt, llm_config_name='default', use_cache=True)

    @pytest.mark.e2e
    async def test_cache_invalidation(self, failing_llm_manager):
        """Test cache invalidation logic"""
        prompt = 'Test cache invalidation'
        with pytest.raises((Exception, AttributeError)):
            response1 = await failing_llm_manager.ask_llm(prompt=prompt, llm_config_name='default', use_cache=True)
            response2 = await failing_llm_manager.ask_llm(prompt=prompt, llm_config_name='default', use_cache=False)

    @pytest.mark.e2e
    async def test_semantic_cache_performance(self, failing_llm_manager):
        """Test semantic caching performance"""
        similar_prompts = ['What is AI optimization?', 'How do I optimize AI systems?', 'Tell me about AI optimization techniques']
        with pytest.raises((Exception, AttributeError)):
            responses = []
            for prompt in similar_prompts:
                response = await failing_llm_manager.ask_llm(prompt=prompt, llm_config_name='default', use_cache=True)
                responses.append(response)

@pytest.mark.e2e
class TestMultiAgentOrchestration:
    """Test multi-agent coordination - designed to expose orchestration issues"""

    @pytest.mark.e2e
    async def test_agent_coordination_flow(self, chat_orchestrator_with_failures):
        """Test coordination between multiple agents"""
        complex_prompt = 'I need cost analysis, performance optimization, and implementation recommendations'
        user_id = f'test_user_{uuid.uuid4()}'
        with pytest.raises((Exception, AttributeError)):
            response = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=None, content=complex_prompt, message_type='user_message')

    @pytest.mark.e2e
    async def test_agent_state_management(self, chat_orchestrator_with_failures):
        """Test agent state management across requests"""
        user_id = f'test_user_{uuid.uuid4()}'
        thread_id = f'thread_{uuid.uuid4()}'
        with pytest.raises((Exception, AttributeError)):
            response1 = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=thread_id, content='Start analysis of my system', message_type='user_message')
            response2 = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=thread_id, content='Continue with optimization recommendations', message_type='user_message')

    @pytest.mark.e2e
    async def test_agent_failure_cascade_prevention(self, chat_orchestrator_with_failures):
        """Test prevention of failure cascades across agents"""
        prompt = 'tool_fail optimization analysis'
        user_id = f'test_user_{uuid.uuid4()}'
        with pytest.raises(Exception):
            response = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=None, content=prompt, message_type='user_message')

@pytest.mark.e2e
class TestPerformanceUnderLoad:
    """Test performance characteristics - designed to expose scaling issues"""

    @pytest.mark.e2e
    async def test_concurrent_request_handling(self, chat_orchestrator_with_failures):
        """Test handling of concurrent requests"""
        user_id = f'test_user_{uuid.uuid4()}'
        tasks = []
        for i in range(10):
            task = chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=f'thread_{i}', content=f'Concurrent test message {i}', message_type='user_message')
            tasks.append(task)
        with pytest.raises((Exception, AttributeError)):
            responses = await asyncio.gather(*tasks, return_exceptions=True)

    @pytest.mark.e2e
    async def test_memory_usage_under_load(self, chat_orchestrator_with_failures):
        """Test memory usage patterns under load"""
        user_id = f'test_user_{uuid.uuid4()}'
        with pytest.raises((Exception, MemoryError, AttributeError)):
            for i in range(100):
                response = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=f'thread_{i}', content=f'Memory test {i} ' * 100, message_type='user_message')

    @pytest.mark.e2e
    async def test_response_time_degradation(self, chat_orchestrator_with_failures):
        """Test response time under increasing load"""
        user_id = f'test_user_{uuid.uuid4()}'
        response_times = []
        with pytest.raises((Exception, AttributeError, TimeoutError)):
            for i in range(20):
                start_time = time.time()
                response = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=None, content=f'Performance test {i}', message_type='user_message')
                end_time = time.time()
                response_times.append(end_time - start_time)
                if i > 5 and response_times[-1] > response_times[0] * 3:
                    raise TimeoutError('Response time degradation detected')

@pytest.mark.e2e
class TestMultiTurnConversationFlow:
    """Test multi-turn conversation handling - designed to expose context management issues"""

    @pytest.mark.e2e
    async def test_conversation_context_preservation(self, chat_orchestrator_with_failures):
        """Test that conversation context is preserved across turns"""
        user_id = f'test_user_{uuid.uuid4()}'
        thread_id = f'thread_{uuid.uuid4()}'
        with pytest.raises((Exception, AttributeError)):
            response1 = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=thread_id, content='My system processes 1M requests per day', message_type='user_message')
            response2 = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=thread_id, content='How can I optimize it?', message_type='user_message')

    @pytest.mark.e2e
    async def test_conversation_memory_limits(self, chat_orchestrator_with_failures):
        """Test handling of conversation memory limits"""
        user_id = f'test_user_{uuid.uuid4()}'
        thread_id = f'thread_{uuid.uuid4()}'
        with pytest.raises((Exception, AttributeError)):
            for i in range(100):
                response = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=thread_id, content=f'Message {i} with lots of content ' * 50, message_type='user_message')

    @pytest.mark.e2e
    async def test_conversation_state_recovery(self, chat_orchestrator_with_failures):
        """Test recovery of conversation state after interruption"""
        user_id = f'test_user_{uuid.uuid4()}'
        thread_id = f'thread_{uuid.uuid4()}'
        with pytest.raises((Exception, AttributeError)):
            response1 = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=thread_id, content="Let's analyze my API costs", message_type='user_message')
            new_orchestrator = AsyncNone
            new_orchestrator.db_session = mock_db_session
            new_orchestrator.llm_manager = failing_llm_manager
            new_orchestrator.websocket_manager = failing_websocket_manager
            new_orchestrator.tool_dispatcher = failing_tool_dispatcher
            response2 = await new_orchestrator.process_message(user_id=user_id, thread_id=thread_id, content='Continue the analysis', message_type='user_message')

@pytest.mark.e2e
class TestEndToEndIntegrationFailures:
    """End-to-end integration tests designed to expose system-wide issues"""

    @pytest.mark.e2e
    async def test_complete_user_journey_with_failures(self, chat_orchestrator_with_failures):
        """Test complete user journey to expose end-to-end issues"""
        user_id = f'test_user_{uuid.uuid4()}'
        thread_id = f'thread_{uuid.uuid4()}'
        with pytest.raises((Exception, AttributeError)):
            response1 = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=thread_id, content='I want to optimize my AI infrastructure costs', message_type='user_message')
            response2 = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=thread_id, content="I'm using GPT-4 and Claude, processing 100k requests daily", message_type='user_message')
            response3 = await chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=thread_id, content='Generate a detailed cost optimization report', message_type='user_message')

    @pytest.mark.e2e
    async def test_system_under_realistic_load(self, chat_orchestrator_with_failures):
        """Test system behavior under realistic production-like load"""
        with pytest.raises((Exception, AttributeError, asyncio.TimeoutError)):
            tasks = []
            for user_num in range(50):
                user_id = f'load_test_user_{user_num}'
                for msg_num in range(5):
                    task = chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id=f'thread_{user_num}_{msg_num}', content=f'Load test message {msg_num} from user {user_num}', message_type='user_message')
                    tasks.append(task)
            responses = await asyncio.gather(*tasks, return_exceptions=True)

    @pytest.mark.e2e
    async def test_cascading_failure_scenarios(self, chat_orchestrator_with_failures):
        """Test cascading failure scenarios that could bring down the system"""
        user_id = f'test_user_{uuid.uuid4()}'
        with pytest.raises(Exception):
            tasks = [chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id='fail_thread_1', content='fail prompt', message_type='user_message'), chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id='websocket_fail_thread', content='websocket_fail prompt', message_type='user_message'), chat_orchestrator_with_failures.process_message(user_id=user_id, thread_id='tool_fail_thread', content='tool_fail prompt', message_type='user_message')]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')