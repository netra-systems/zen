import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.message_handlers import MessageHandlerService, MessageType
from app.schemas.WebSocket import MessageRequest, MessageResponse

@pytest.mark.asyncio
async def test_message_handler_service_initialization():
    handler_service = MessageHandlerService()
    assert handler_service.handlers == {}
    assert handler_service.middleware == []

@pytest.mark.asyncio
async def test_register_message_handler():
    handler_service = MessageHandlerService()
    
    async def test_handler(message):
        return {"status": "handled", "data": message}
    
    handler_service.register_handler(MessageType.USER_MESSAGE, test_handler)
    
    assert MessageType.USER_MESSAGE in handler_service.handlers
    assert handler_service.handlers[MessageType.USER_MESSAGE] == test_handler

@pytest.mark.asyncio
async def test_handle_user_message():
    handler_service = MessageHandlerService()
    
    async def user_message_handler(message):
        return MessageResponse(
            type='response',
            content=f"Processed: {message.content}",
            thread_id=message.thread_id
        )
    
    handler_service.register_handler(MessageType.USER_MESSAGE, user_message_handler)
    
    request = MessageRequest(
        type=MessageType.USER_MESSAGE,
        content="Hello, AI!",
        thread_id="thread_123"
    )
    
    response = await handler_service.handle_message(request)
    assert response.content == "Processed: Hello, AI!"
    assert response.thread_id == "thread_123"

@pytest.mark.asyncio
async def test_handle_agent_response():
    handler_service = MessageHandlerService()
    
    async def agent_response_handler(message):
        return MessageResponse(
            type='agent_response',
            content=message.content,
            thread_id=message.thread_id,
            metadata={"processed": True}
        )
    
    handler_service.register_handler(MessageType.AGENT_RESPONSE, agent_response_handler)
    
    request = MessageRequest(
        type=MessageType.AGENT_RESPONSE,
        content="Analysis complete",
        thread_id="thread_456"
    )
    
    response = await handler_service.handle_message(request)
    assert response.metadata["processed"] is True

@pytest.mark.asyncio
async def test_message_middleware():
    handler_service = MessageHandlerService()
    
    async def logging_middleware(message, next_handler):
        message.metadata = message.metadata or {}
        message.metadata["logged"] = True
        return await next_handler(message)
    
    async def auth_middleware(message, next_handler):
        if not message.metadata.get("user_id"):
            raise ValueError("Authentication required")
        return await next_handler(message)
    
    handler_service.add_middleware(logging_middleware)
    handler_service.add_middleware(auth_middleware)
    
    async def test_handler(message):
        return MessageResponse(
            type='response',
            content="Handled",
            thread_id=message.thread_id
        )
    
    handler_service.register_handler(MessageType.USER_MESSAGE, test_handler)
    
    request = MessageRequest(
        type=MessageType.USER_MESSAGE,
        content="Test",
        thread_id="thread_123",
        metadata={"user_id": "user_456"}
    )
    
    response = await handler_service.handle_message(request)
    assert response.content == "Handled"

@pytest.mark.asyncio
async def test_error_handling():
    handler_service = MessageHandlerService()
    
    async def failing_handler(message):
        raise Exception("Handler failed")
    
    handler_service.register_handler(MessageType.USER_MESSAGE, failing_handler)
    
    request = MessageRequest(
        type=MessageType.USER_MESSAGE,
        content="Test",
        thread_id="thread_123"
    )
    
    with pytest.raises(Exception):
        await handler_service.handle_message(request)