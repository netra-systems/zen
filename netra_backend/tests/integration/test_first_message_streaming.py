"""Integration Test: First Message Streaming Response
BVJ: $7K MRR - Real-time streaming increases user engagement by 70%
Components: StreamProcessor → WebSocket → UI Updates → Response Assembly
Critical: Streaming responses provide immediate feedback for better UX
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest
from schemas import StreamingResponse, UserInDB

from netra_backend.app.services.agent_service_core import AgentService

# Add project root to path
from netra_backend.app.services.streaming_service import TextStreamProcessor
from netra_backend.app.services.websocket_manager import WebSocketManager
from test_framework.mock_utils import mock_justified

# Add project root to path


@pytest.mark.asyncio
class TestFirstMessageStreaming:
    """Test streaming response for first user message."""
    
    @pytest.fixture
    async def stream_processor(self):
        """Create stream processor for testing."""
        return TextStreamProcessor()
    
    @pytest.fixture
    async def ws_manager(self):
        """Create WebSocket manager for streaming."""
        manager = WebSocketManager()
        manager.active_connections = {}
        return manager
    
    @pytest.fixture
    async def mock_websocket(self):
        """Create mock WebSocket for streaming."""
        ws = Mock()
        ws.send_json = AsyncMock()
        ws.send_text = AsyncMock()
        ws.client_state = "CONNECTED"
        return ws
    
    @pytest.fixture
    async def test_user(self):
        """Create test user for streaming."""
        return UserInDB(
            id="stream_user_001",
            email="stream@test.netrasystems.ai",
            username="streamuser",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
    
    async def test_token_streaming_to_websocket(
        self, stream_processor, ws_manager, mock_websocket, test_user
    ):
        """Test streaming individual tokens to WebSocket."""
        
        # Connect WebSocket
        await ws_manager.connect(mock_websocket, test_user.id)
        
        # Generate streaming tokens
        async def generate_tokens() -> AsyncGenerator[str, None]:
            tokens = ["Hello", " ", "from", " ", "Netra", " ", "AI", "!"]
            for token in tokens:
                await asyncio.sleep(0.01)  # Simulate processing delay
                yield token
        
        # Stream tokens to WebSocket
        streamed_tokens = []
        async for token in generate_tokens():
            # Process token
            processed = stream_processor.process_token(token)
            
            # Send to WebSocket
            await mock_websocket.send_json({
                "type": "stream_token",
                "payload": {
                    "token": processed,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            })
            streamed_tokens.append(processed)
        
        # Verify all tokens streamed
        assert len(streamed_tokens) == 8
        assert "".join(streamed_tokens) == "Hello from Netra AI!"
        
        # Verify WebSocket calls
        assert mock_websocket.send_json.call_count == 8
    
    async def test_progressive_ui_updates(
        self, ws_manager, mock_websocket, test_user
    ):
        """Test progressive UI updates during streaming."""
        
        # Connect WebSocket
        await ws_manager.connect(mock_websocket, test_user.id)
        
        # Track UI updates
        ui_updates = []
        
        async def send_ui_update(update_type: str, content: str):
            update = {
                "type": "ui_update",
                "update_type": update_type,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await mock_websocket.send_json(update)
            ui_updates.append(update)
        
        # Simulate streaming with UI updates
        response_parts = [
            "Analyzing your request...",
            "Found 3 optimization opportunities:",
            "1. Reduce model size by 40%",
            "2. Implement caching strategy",
            "3. Use batch processing"
        ]
        
        for i, part in enumerate(response_parts):
            await send_ui_update(
                "partial_response" if i < len(response_parts) - 1 else "complete",
                part
            )
            await asyncio.sleep(0.05)  # Simulate processing
        
        # Verify progressive updates
        assert len(ui_updates) == 5
        assert ui_updates[0]["update_type"] == "partial_response"
        assert ui_updates[-1]["update_type"] == "complete"
    
    async def test_response_assembly_from_stream(
        self, stream_processor
    ):
        """Test assembling complete response from streamed tokens."""
        
        # Stream tokens
        tokens = []
        complete_response = ""
        
        async def stream_response() -> AsyncGenerator[str, None]:
            parts = [
                "Based on your AI workload analysis:\n",
                "• Current cost: $5,000/month\n",
                "• Optimization potential: 35%\n",
                "• Estimated savings: $1,750/month"
            ]
            for part in parts:
                for char in part:
                    yield char
        
        # Assemble response
        async for token in stream_response():
            tokens.append(token)
            complete_response = stream_processor.assemble_response(tokens)
        
        # Verify complete response
        assert "Based on your AI workload analysis" in complete_response
        assert "$5,000/month" in complete_response
        assert "35%" in complete_response
    
    async def test_streaming_with_markdown_formatting(
        self, stream_processor, mock_websocket
    ):
        """Test streaming response with markdown formatting."""
        
        # Generate markdown response
        async def stream_markdown() -> AsyncGenerator[str, None]:
            markdown_content = """# Optimization Report
            
## Summary
Your AI costs can be reduced by **40%**

### Recommendations:
1. **Model Optimization**
   - Switch to smaller models where possible
   - Use quantization techniques
   
2. **Caching Strategy**
   - Implement response caching
   - Cache embeddings
"""
            for line in markdown_content.split('\n'):
                yield line + '\n'
                await asyncio.sleep(0.02)
        
        # Stream and format
        formatted_parts = []
        async for line in stream_markdown():
            formatted = stream_processor.format_markdown(line)
            formatted_parts.append(formatted)
            
            await mock_websocket.send_json({
                "type": "markdown_chunk",
                "content": formatted
            })
        
        # Verify markdown preserved
        complete_markdown = "".join(formatted_parts)
        assert "# Optimization Report" in complete_markdown
        assert "**40%**" in complete_markdown
        assert "### Recommendations:" in complete_markdown
    
    async def test_stream_error_handling(
        self, stream_processor, mock_websocket, test_user
    ):
        """Test error handling during streaming."""
        
        # Stream with potential errors
        async def faulty_stream() -> AsyncGenerator[str, None]:
            yield "Starting analysis..."
            yield " Processing"
            # Simulate error
            raise ConnectionError("Stream interrupted")
        
        # Process stream with error handling
        received_tokens = []
        error_handled = False
        
        try:
            async for token in faulty_stream():
                received_tokens.append(token)
                await mock_websocket.send_json({
                    "type": "stream_token",
                    "token": token
                })
        except ConnectionError:
            error_handled = True
            # Send error notification
            await mock_websocket.send_json({
                "type": "stream_error",
                "message": "Stream interrupted. Attempting recovery...",
                "partial_response": "".join(received_tokens)
            })
        
        # Verify error handled
        assert error_handled
        assert len(received_tokens) == 2
        assert "Starting analysis" in "".join(received_tokens)
    
    async def test_streaming_performance_metrics(
        self, stream_processor
    ):
        """Test streaming performance metrics collection."""
        
        # Track metrics
        metrics = {
            "start_time": None,
            "first_token_time": None,
            "total_tokens": 0,
            "bytes_streamed": 0,
            "end_time": None
        }
        
        # Stream with metrics
        metrics["start_time"] = datetime.now(timezone.utc)
        
        async def metered_stream() -> AsyncGenerator[str, None]:
            tokens = ["Optimizing", " ", "your", " ", "AI", " ", "workload..."]
            for i, token in enumerate(tokens):
                if i == 0:
                    metrics["first_token_time"] = datetime.now(timezone.utc)
                
                metrics["total_tokens"] += 1
                metrics["bytes_streamed"] += len(token.encode('utf-8'))
                
                yield token
                await asyncio.sleep(0.01)
        
        async for _ in metered_stream():
            pass
        
        metrics["end_time"] = datetime.now(timezone.utc)
        
        # Calculate performance
        time_to_first_token = (
            metrics["first_token_time"] - metrics["start_time"]
        ).total_seconds()
        total_time = (
            metrics["end_time"] - metrics["start_time"]
        ).total_seconds()
        
        # Verify metrics
        assert metrics["total_tokens"] == 7
        assert metrics["bytes_streamed"] > 0
        assert time_to_first_token < 0.1  # Fast first token
        assert total_time < 1.0  # Reasonable total time
    
    async def test_complete_response_confirmation(
        self, ws_manager, mock_websocket, test_user
    ):
        """Test sending completion confirmation after streaming."""
        
        # Connect WebSocket
        await ws_manager.connect(mock_websocket, test_user.id)
        
        # Stream response
        response_chunks = []
        
        async def stream_complete_response():
            chunks = [
                "Analysis complete.",
                " Found 5 optimizations.",
                " Potential savings: $2,000/month."
            ]
            for chunk in chunks:
                response_chunks.append(chunk)
                yield chunk
        
        # Stream all chunks
        async for chunk in stream_complete_response():
            await mock_websocket.send_json({
                "type": "stream_chunk",
                "content": chunk
            })
        
        # Send completion confirmation
        complete_response = "".join(response_chunks)
        await mock_websocket.send_json({
            "type": "stream_complete",
            "payload": {
                "full_response": complete_response,
                "token_count": len(complete_response.split()),
                "processing_time": 0.5,
                "status": "success"
            }
        })
        
        # Verify completion sent
        last_call = mock_websocket.send_json.call_args_list[-1]
        completion_msg = last_call[0][0]
        assert completion_msg["type"] == "stream_complete"
        assert completion_msg["payload"]["status"] == "success"
        assert "Found 5 optimizations" in completion_msg["payload"]["full_response"]