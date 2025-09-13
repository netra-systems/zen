"""

Streaming response generation utilities for WebSocket testing.



Business Value Justification (BVJ):

- Segment: All Segments

- Business Goal: Streaming Response Testing

- Value Impact: Generates realistic streaming responses for testing

- Strategic/Revenue Impact: Validates streaming response handling

"""



import asyncio

import hashlib

import json

import uuid

from datetime import datetime, timezone

from typing import Any, AsyncGenerator, Dict, Optional



from tests.e2e.websocket_resilience.fixtures.shared_websocket_fixtures import (

    ResponseType,

)





class StreamingResponseGenerator:

    """Generates streaming responses for testing."""

    

    def __init__(self, response_type: ResponseType, total_size: int, chunk_size: int = 64):

        self.response_type = response_type

        self.total_size = total_size

        self.chunk_size = chunk_size

        self.generated_size = 0

        self.start_time = None

        

    async def generate_text_stream(self, delay_between_chunks: float = 0.1) -> AsyncGenerator[str, None]:

        """Generate streaming text response."""

        self.start_time = datetime.now(timezone.utc)

        

        while self.generated_size < self.total_size:

            remaining = min(self.chunk_size, self.total_size - self.generated_size)

            chunk = f"Text chunk {self.generated_size // self.chunk_size + 1}: " + "x" * (remaining - 20)

            

            self.generated_size += len(chunk)

            yield chunk

            

            if delay_between_chunks > 0:

                await asyncio.sleep(delay_between_chunks)

    

    async def generate_json_stream(self, delay_between_chunks: float = 0.1) -> AsyncGenerator[str, None]:

        """Generate streaming JSON response."""

        self.start_time = datetime.now(timezone.utc)

        

        chunk_id = 0

        while self.generated_size < self.total_size:

            chunk_data = {

                "chunk_id": chunk_id,

                "timestamp": datetime.now(timezone.utc).isoformat(),

                "data": "x" * (self.chunk_size - 100)  # Account for JSON overhead

            }

            

            chunk = json.dumps(chunk_data)

            self.generated_size += len(chunk)

            chunk_id += 1

            

            yield chunk

            

            if delay_between_chunks > 0:

                await asyncio.sleep(delay_between_chunks)

    

    async def generate_multipart_stream(self, delay_between_chunks: float = 0.1) -> AsyncGenerator[str, None]:

        """Generate streaming multipart response."""

        self.start_time = datetime.now(timezone.utc)

        boundary = f"----boundary_{uuid.uuid4().hex[:8]}"

        

        # Start multipart response

        header = f"Content-Type: multipart/mixed; boundary={boundary}\r\n\r\n"

        yield header

        self.generated_size += len(header)

        

        part_id = 0

        while self.generated_size < self.total_size:

            part_header = f"--{boundary}\r\nContent-Type: text/plain\r\n\r\n"

            part_data = f"Part {part_id}: " + "x" * (self.chunk_size - 20)

            part_footer = "\r\n"

            

            part = part_header + part_data + part_footer

            self.generated_size += len(part)

            part_id += 1

            

            yield part

            

            if delay_between_chunks > 0:

                await asyncio.sleep(delay_between_chunks)

        

        # End multipart response

        end_boundary = f"--{boundary}--\r\n"

        yield end_boundary

    

    async def generate_stream(self, delay_between_chunks: float = 0.1) -> AsyncGenerator[str, None]:

        """Generate stream based on response type."""

        if self.response_type == ResponseType.TEXT:

            async for chunk in self.generate_text_stream(delay_between_chunks):

                yield chunk

        elif self.response_type == ResponseType.JSON:

            async for chunk in self.generate_json_stream(delay_between_chunks):

                yield chunk

        elif self.response_type == ResponseType.MULTIPART:

            async for chunk in self.generate_multipart_stream(delay_between_chunks):

                yield chunk

        else:

            # Default to text

            async for chunk in self.generate_text_stream(delay_between_chunks):

                yield chunk

    

    def get_expected_checksum(self) -> str:

        """Calculate expected checksum for complete response."""

        # This is a simplified checksum calculation for testing

        content = f"{self.response_type.value}_{self.total_size}_{self.chunk_size}"

        return hashlib.md5(content.encode()).hexdigest()

    

    def get_generation_stats(self) -> Dict[str, Any]:

        """Get generation statistics."""

        end_time = datetime.now(timezone.utc)

        duration = (end_time - self.start_time).total_seconds() if self.start_time else 0

        

        return {

            "response_type": self.response_type.value,

            "total_size": self.total_size,

            "generated_size": self.generated_size,

            "chunk_size": self.chunk_size,

            "chunks_generated": self.generated_size // self.chunk_size,

            "generation_duration": duration,

            "generation_rate_kbps": (self.generated_size / 1024 / duration) if duration > 0 else 0

        }

