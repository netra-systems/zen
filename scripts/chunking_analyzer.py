"""
Chunking Analyzer - Determines if log files need chunking.

Analyzes log files based on:
1. Total file size (bytes)
2. Number of entries
3. Multiple file scenarios

Implements three main scenarios:
- Single file: chunk if >4.5 MB OR >250 entries
- Multiple files (all small): process separately
- Multiple files (any large): chunk large ones, keep small ones intact
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import json
import hashlib


@dataclass
class FileAnalysis:
    """Analysis result for a single log file"""
    file_name: str
    file_path: Optional[str]
    size_bytes: int
    size_mb: float
    entry_count: int
    file_hash: str  # SHA256 first 16 chars
    needs_chunking: bool
    reason: str  # Why chunking is/isn't needed


@dataclass
class ChunkingStrategy:
    """Overall chunking strategy for all files"""
    total_files: int
    total_size_bytes: int
    total_entries: int
    files_needing_chunking: int
    strategy: str  # 'no_chunking', 'single_file_chunking', 'multi_file_chunking'
    file_analyses: List[FileAnalysis]


class ChunkingAnalyzer:
    """
    Analyzes log files and determines optimal chunking strategy.

    Thresholds:
    - SIZE_THRESHOLD_MB: 4.5 MB (hard limit for single transmission)
    - ENTRY_THRESHOLD: 250 entries (LLM performance limit)
    - CHUNK_SIZE_MB: 2.5 MB (target chunk size)
    - CHUNK_ENTRY_COUNT: 250 (target entries per chunk)
    """

    # Configuration constants
    SIZE_THRESHOLD_MB = 4.5
    ENTRY_THRESHOLD = 250
    CHUNK_SIZE_MB = 2.5
    CHUNK_ENTRY_COUNT = 250

    def __init__(self):
        """Initialize analyzer"""
        pass

    def analyze_files(
        self,
        logs: List[Dict[str, Any]],
        file_info: List[Dict[str, str]]
    ) -> ChunkingStrategy:
        """
        Analyze log files and determine chunking strategy.

        Args:
            logs: List of log entry dictionaries
            file_info: List of file metadata dicts with keys:
                - 'name': filename
                - 'path': file path (optional)
                - 'entries': number of entries in this file
                - 'hash': file hash (optional)

        Returns:
            ChunkingStrategy with analysis for all files

        Algorithm:
        1. For each file, calculate size and entry count
        2. Determine if chunking needed (>4.5 MB OR >250 entries)
        3. Decide overall strategy based on file count and characteristics
        """

        if not file_info:
            # Treat all logs as single unnamed file
            file_info = [{'name': 'unnamed.jsonl', 'entries': len(logs)}]

        # Analyze each file
        file_analyses = []
        total_size = 0
        total_entries = len(logs)
        files_needing_chunking = 0

        # Track entry offsets for multi-file scenarios
        entry_offset = 0

        for file_meta in file_info:
            file_entries_count = file_meta.get('entries', 0)

            # Extract entries for this file
            file_entries = logs[entry_offset:entry_offset + file_entries_count]
            entry_offset += file_entries_count

            # Calculate file size (serialize to JSON to get accurate size)
            file_json = json.dumps(file_entries)
            file_size_bytes = len(file_json.encode('utf-8'))
            file_size_mb = file_size_bytes / (1024 * 1024)

            # Generate file hash
            file_hash = self._generate_file_hash(file_entries, file_meta['name'])

            # Determine if chunking needed
            needs_chunking = (
                file_size_mb > self.SIZE_THRESHOLD_MB or
                file_entries_count > self.ENTRY_THRESHOLD
            )

            # Reason for decision
            if needs_chunking:
                reasons = []
                if file_size_mb > self.SIZE_THRESHOLD_MB:
                    reasons.append(f"size {file_size_mb:.2f} MB > {self.SIZE_THRESHOLD_MB} MB")
                if file_entries_count > self.ENTRY_THRESHOLD:
                    reasons.append(f"entries {file_entries_count} > {self.ENTRY_THRESHOLD}")
                reason = "Chunking required: " + ", ".join(reasons)
                files_needing_chunking += 1
            else:
                reason = f"No chunking needed (size: {file_size_mb:.2f} MB, entries: {file_entries_count})"

            analysis = FileAnalysis(
                file_name=file_meta['name'],
                file_path=file_meta.get('path'),
                size_bytes=file_size_bytes,
                size_mb=file_size_mb,
                entry_count=file_entries_count,
                file_hash=file_hash,
                needs_chunking=needs_chunking,
                reason=reason
            )

            file_analyses.append(analysis)
            total_size += file_size_bytes

        # Determine overall strategy
        if len(file_info) == 1:
            # Single file scenario
            if file_analyses[0].needs_chunking:
                strategy = 'single_file_chunking'
            else:
                strategy = 'no_chunking'
        else:
            # Multiple files scenario
            if files_needing_chunking == 0:
                strategy = 'multi_file_no_chunking'
            else:
                strategy = 'multi_file_chunking'

        return ChunkingStrategy(
            total_files=len(file_info),
            total_size_bytes=total_size,
            total_entries=total_entries,
            files_needing_chunking=files_needing_chunking,
            strategy=strategy,
            file_analyses=file_analyses
        )

    def _generate_file_hash(self, entries: List[Dict], filename: str) -> str:
        """
        Generate deterministic hash for file.

        Args:
            entries: List of log entries
            filename: Name of the file

        Returns:
            First 16 characters of SHA256 hash
        """
        # Create deterministic string from entries + filename
        hash_input = filename + json.dumps(entries, sort_keys=True)
        hash_bytes = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
        return hash_bytes[:16]  # First 16 chars sufficient for uniqueness


# Example usage for testing
if __name__ == '__main__':
    # Test with sample data
    analyzer = ChunkingAnalyzer()

    # Simulate 500 log entries
    sample_logs = [
        {'type': 'info', 'message': f'Log entry {i}', 'timestamp': '2024-10-20T10:00:00'}
        for i in range(500)
    ]

    # Simulate single large file
    file_info = [{'name': 'large.jsonl', 'entries': 500}]

    strategy = analyzer.analyze_files(sample_logs, file_info)

    print(f"Strategy: {strategy.strategy}")
    print(f"Total files: {strategy.total_files}")
    print(f"Files needing chunking: {strategy.files_needing_chunking}")

    for analysis in strategy.file_analyses:
        print(f"\nFile: {analysis.file_name}")
        print(f"  Size: {analysis.size_mb:.2f} MB")
        print(f"  Entries: {analysis.entry_count}")
        print(f"  Needs chunking: {analysis.needs_chunking}")
        print(f"  Reason: {analysis.reason}")
