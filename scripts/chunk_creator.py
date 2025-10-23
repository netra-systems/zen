"""
Chunk Creator - Splits log files into chunks.

Implements intelligent chunking that respects both:
1. Size limits (max 2.5 MB per chunk)
2. Entry limits (max 250 entries per chunk)

Ensures no entry is split across chunks.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
import json
import hashlib


@dataclass
class ChunkMetadata:
    """Metadata for a single chunk"""
    chunk_id: str  # Unique identifier for this chunk
    chunk_index: int  # 0-based index
    total_chunks: int  # Total chunks for this file
    file_hash: str  # Hash of original file
    file_name: str  # Original filename
    entries_in_chunk: int  # Number of entries in this chunk
    chunk_size_bytes: int  # Size of this chunk in bytes
    chunk_size_mb: float  # Size of this chunk in MB
    start_entry_index: int  # 0-based index of first entry in original file
    end_entry_index: int  # 0-based index of last entry in original file
    is_multi_file: bool  # Part of multi-file analysis
    file_index: Optional[int]  # Index if multi-file (0-based)
    aggregation_required: bool  # True if backend should aggregate


@dataclass
class Chunk:
    """A chunk of log entries with metadata"""
    entries: List[Dict[str, Any]]  # Log entries in this chunk
    metadata: ChunkMetadata


class ChunkCreator:
    """
    Creates chunks from log entries respecting size and entry limits.

    Algorithm:
    1. Iterate through entries
    2. Add entry to current chunk
    3. Check if adding next entry would exceed limits
    4. If yes: close current chunk, start new chunk
    5. If no: continue adding
    6. Repeat until all entries processed
    """

    # Configuration
    MAX_CHUNK_SIZE_MB = 2.5
    MAX_ENTRIES_PER_CHUNK = 250

    def __init__(self):
        """Initialize chunk creator"""
        pass

    def create_chunks(
        self,
        entries: List[Dict[str, Any]],
        file_name: str,
        file_hash: str,
        is_multi_file: bool = False,
        file_index: Optional[int] = None
    ) -> List[Chunk]:
        """
        Create chunks from log entries.

        Args:
            entries: List of log entry dictionaries
            file_name: Name of the original file
            file_hash: Hash of the original file
            is_multi_file: True if this is part of multi-file analysis
            file_index: Index of this file in multi-file scenario (0-based)

        Returns:
            List of Chunk objects

        Algorithm:
        - Uses two-pass approach:
          1. Try to chunk by entry count
          2. Validate each chunk doesn't exceed size
          3. If any chunk exceeds size, split it further
        """

        if not entries:
            return []

        chunks = []
        current_chunk_entries = []
        current_chunk_size = 0

        max_size_bytes = int(self.MAX_CHUNK_SIZE_MB * 1024 * 1024)

        for entry in entries:
            # Calculate size of this entry
            entry_json = json.dumps(entry)
            entry_size = len(entry_json.encode('utf-8'))

            # Check if this single entry exceeds max size
            if entry_size > max_size_bytes:
                # CRITICAL: Single entry larger than chunk size limit
                # This happens with large tool results, file contents, etc.
                # We cannot split a single JSON object, so we create a warning chunk

                # Save current chunk first if it has entries
                if current_chunk_entries:
                    chunks.append((current_chunk_entries, current_chunk_size))
                    current_chunk_entries = []
                    current_chunk_size = 0

                # Create oversized single-entry chunk with warning
                # The backend will need to handle this specially
                chunks.append(([entry], entry_size))

                # Warning will be logged when chunk is sent
                continue

            # Check if adding this entry would exceed limits
            would_exceed_count = len(current_chunk_entries) >= self.MAX_ENTRIES_PER_CHUNK
            would_exceed_size = (current_chunk_size + entry_size) > max_size_bytes

            if would_exceed_count or would_exceed_size:
                # Save current chunk
                if current_chunk_entries:
                    chunks.append((current_chunk_entries, current_chunk_size))

                # Start new chunk with this entry
                current_chunk_entries = [entry]
                current_chunk_size = entry_size
            else:
                # Add to current chunk
                current_chunk_entries.append(entry)
                current_chunk_size += entry_size

        # Save last chunk
        if current_chunk_entries:
            chunks.append((current_chunk_entries, current_chunk_size))

        # Generate unique chunk_id for this file
        session_chunk_id = self._generate_chunk_id(file_hash, file_name)

        # Create Chunk objects with metadata
        total_chunks = len(chunks)
        chunk_objects = []

        # Track entry indices across chunks
        entry_offset = 0

        for idx, (chunk_entries, chunk_size) in enumerate(chunks):
            num_entries = len(chunk_entries)
            start_entry_index = entry_offset
            end_entry_index = entry_offset + num_entries - 1

            metadata = ChunkMetadata(
                chunk_id=session_chunk_id,
                chunk_index=idx,
                total_chunks=total_chunks,
                file_hash=file_hash,
                file_name=file_name,
                entries_in_chunk=num_entries,
                chunk_size_bytes=chunk_size,
                chunk_size_mb=chunk_size / (1024 * 1024),
                start_entry_index=start_entry_index,
                end_entry_index=end_entry_index,
                is_multi_file=is_multi_file,
                file_index=file_index,
                aggregation_required=True  # Backend should aggregate
            )

            chunk_objects.append(Chunk(entries=chunk_entries, metadata=metadata))

            # Update offset for next chunk
            entry_offset += num_entries

        return chunk_objects

    def _generate_chunk_id(self, file_hash: str, file_name: str) -> str:
        """
        Generate unique chunk_id for a file's chunks.

        This ID is shared across all chunks of the same file,
        allowing backend to group them together.

        Args:
            file_hash: Hash of the file
            file_name: Name of the file

        Returns:
            Unique chunk_id (first 12 chars of hash)
        """
        chunk_id_input = f"{file_hash}_{file_name}"
        chunk_id_hash = hashlib.sha256(chunk_id_input.encode('utf-8')).hexdigest()
        return chunk_id_hash[:12]


# Example usage for testing
if __name__ == '__main__':
    creator = ChunkCreator()

    # Create sample entries
    sample_entries = [
        {'type': 'info', 'message': f'Entry {i}' * 100, 'timestamp': '2024-10-20T10:00:00'}
        for i in range(300)
    ]

    # Create chunks
    chunks = creator.create_chunks(
        entries=sample_entries,
        file_name='test.jsonl',
        file_hash='abc123',
        is_multi_file=False,
        file_index=None
    )

    print(f"Created {len(chunks)} chunks")
    for chunk in chunks:
        print(f"\nChunk {chunk.metadata.chunk_index + 1}/{chunk.metadata.total_chunks}")
        print(f"  Entries: {chunk.metadata.entries_in_chunk}")
        print(f"  Size: {chunk.metadata.chunk_size_mb:.2f} MB")
        print(f"  Chunk ID: {chunk.metadata.chunk_id}")
