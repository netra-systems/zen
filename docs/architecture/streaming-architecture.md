# Streaming Architecture

## Overview
The Netra platform implements a production-grade streaming service for real-time data transmission across multiple protocols (SSE, WebSocket, HTTP streaming).

## Architecture

### Core Components

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐     ┌────────────────┐
│   Client    │────▶│  API Route   │────▶│  AgentService    │────▶│StreamingService│
└─────────────┘     └──────────────┘     └──────────────────┘     └────────────────┘
                                                    │                       │
                                                    ▼                       ▼
                                          ┌──────────────────┐     ┌────────────────┐
                                          │   Supervisor     │     │TextProcessor   │
                                          └──────────────────┘     └────────────────┘
```

### Key Files
- `app/services/streaming_service.py` - Core streaming infrastructure
- `app/services/agent_service.py` - Agent integration with streaming
- `app/routes/agent_route.py` - HTTP/SSE endpoints
- `app/tests/services/test_streaming_service.py` - Comprehensive tests

## StreamingService API

### Basic Usage

```python
from netra_backend.app.services.streaming_service import get_streaming_service, TextStreamProcessor

# Get singleton instance
streaming_service = get_streaming_service()

# Create text processor
processor = TextStreamProcessor(chunk_size=5)

# Stream data
async for chunk in streaming_service.create_stream(processor, text):
    # Each chunk is a StreamChunk object with:
    # - type: "stream_start", "data", "stream_end", "error"
    # - data: The actual content
    # - metadata: Additional information
    # - timestamp: ISO format timestamp
    # - id: Unique chunk identifier
    print(chunk.to_dict())
```

### StreamChunk Structure

```python
{
    "id": "uuid",
    "type": "data|stream_start|stream_end|error",
    "data": "actual content or error message",
    "metadata": {
        "stream_id": "uuid",
        "chunk_index": 0,
        "protocol": "sse|websocket|http_stream"
    },
    "timestamp": "2025-08-14T10:00:00.000Z"
}
```

## Protocol Support

### Server-Sent Events (SSE)

```python
@router.post("/stream")
async def stream_response(request_model: RequestModel):
    agent_service = get_agent_service(db_session, llm_manager)
    
    async def generate():
        async for chunk in agent_service.generate_stream(request_model.query):
            yield f"data: {json.dumps(chunk)}\\n\\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
```

### WebSocket Streaming

```python
async def handle_websocket_stream(websocket: WebSocket, message: str):
    async for chunk in agent_service.generate_stream(message):
        await websocket.send_json(chunk)
```

### HTTP Streaming

```python
async def http_stream(message: str):
    async for chunk in agent_service.generate_stream(message):
        yield chunk.to_json() + "\n"
```

## Features

### Buffer Management
- Configurable buffer size for batch processing
- Automatic buffer flushing on stream completion
- Memory-efficient for large streams

### Rate Limiting
- Configurable chunk delay (milliseconds)
- Prevents client overwhelm
- Smooth streaming experience

### Error Handling
- Structured error chunks
- Graceful degradation
- Stream cleanup on failure

### Stream Lifecycle
1. **stream_start** - Initialize with metadata
2. **data** - Content chunks with sequential ordering
3. **stream_end** - Success completion with statistics
4. **error** - Failure with error details

## Configuration

```python
StreamingService(
    buffer_size=100,        # Chunks per buffer
    chunk_delay_ms=50      # Delay between chunks
)
```

## Best Practices

1. **Always use StreamingService** for streaming needs
2. **Never fake streaming** with post-processing chunking
3. **Include proper headers** for SSE (Cache-Control, X-Accel-Buffering)
4. **Use StreamChunk objects** for structured metadata
5. **Implement proper lifecycle** (start → data → end/error)
6. **Handle disconnections gracefully** with cleanup
7. **Track active streams** for monitoring and resource management

## Testing

Run comprehensive tests:
```bash
pytest app/tests/services/test_streaming_service.py -v
```

Test coverage includes:
- Service initialization
- Text processing and chunking
- Stream lifecycle management
- Error handling and recovery
- Buffer management
- Active stream tracking
- Protocol conversions (SSE, JSON)

## Migration Guide

### From Old generate_stream

**Before:**
```python
# Fake streaming - processes entire message then chunks
async def generate_stream(message: str):
    response = await process_message(message)
    text = response.get("response", "")
    chunk_size = len(text) // 10
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]
```

**After:**
```python
# Real streaming with proper infrastructure
async def generate_stream(message: str, thread_id: Optional[str] = None):
    streaming_service = get_streaming_service()
    processor = AgentResponseProcessor(supervisor, message, thread_id)
    async for chunk in streaming_service.create_stream(processor, None):
        yield chunk.to_dict()
```

## Performance Considerations

- Stream chunks are yielded immediately, not buffered
- Rate limiting prevents network congestion
- Active stream tracking enables resource management
- Singleton pattern reduces overhead
- Async generators minimize memory usage

## Monitoring

Check active streams:
```python
active_streams = streaming_service.get_active_streams()
# Returns dict with stream_id, start_time, protocol, chunk_count, duration
```

Terminate stuck streams:
```python
await streaming_service.terminate_stream(stream_id)
```

## Common Issues

### Issue: No streaming output
**Solution:** Check SSE headers, especially `X-Accel-Buffering: no` for nginx

### Issue: Chunks arrive all at once
**Solution:** Verify `chunk_delay_ms` configuration and async processing

### Issue: Memory growth with long streams
**Solution:** Use buffer_stream() for batch processing of large streams

### Issue: Client disconnection not handled
**Solution:** Implement try/finally blocks with stream cleanup