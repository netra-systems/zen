"""Agent service streaming response processor.

Provides streaming functionality for agent responses with chunk processing
and content extraction capabilities.
"""

from netra_backend.app.services.streaming_service import TextStreamProcessor


class AgentResponseProcessor:
    """Processor for streaming agent responses."""
    
    def __init__(self, supervisor, message, thread_id):
        """Initialize response processor."""
        self.supervisor = supervisor
        self.message = message
        self.thread_id = thread_id
    
    async def process(self, _):
        """Process and yield response chunks."""
        async for chunk in self._generate_response_chunks():
            yield chunk
    
    async def _generate_response_chunks(self):
        """Generate response chunks from supervisor."""
        result = await self._run_supervisor_for_stream()
        content = self._extract_content(result)
        text_processor = TextStreamProcessor(chunk_size=5)
        async for chunk in text_processor.process(content):
            yield chunk
    
    async def _run_supervisor_for_stream(self):
        """Run supervisor for streaming response."""
        return await self.supervisor.run(
            self.message,
            self.thread_id or "default",
            "default_user",
            self.thread_id or "default"
        )
    
    def _extract_content(self, result) -> str:
        """Extract content from supervisor result."""
        if hasattr(result, 'response'):
            return str(result.response)
        return str(result)