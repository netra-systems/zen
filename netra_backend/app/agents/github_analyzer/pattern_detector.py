"""AI Pattern Detection Module.

Backwards compatibility interface for refactored pattern detection.
This module now delegates to the modular components.
"""

from typing import Dict, List, Any, Optional, TypedDict
from pathlib import Path

from netra_backend.app.agents.github_analyzer.pattern_scanner import PatternScanner

# Type definitions for backwards compatibility
class PatternCategory(TypedDict):
    """Type definition for pattern categories."""
    imports: List[str]
    api_calls: List[str]
    models: List[str]
    configs: List[str]


class ProviderPatterns(TypedDict):
    """Type definition for provider patterns."""
    openai: PatternCategory
    anthropic: PatternCategory
    langchain: Dict[str, List[str]]
    agents: Dict[str, List[str]]
    embeddings: Dict[str, List[str]]
    tools: Dict[str, List[str]]


class AIPatternDetector:
    """Backwards compatibility class for pattern detection."""
    
    def __init__(self):
        """Initialize with refactored pattern scanner."""
        self.scanner = PatternScanner()
        # Expose internal properties for backwards compatibility
        self.patterns = self.scanner.patterns
        self.file_extensions = self.scanner.file_extensions
    
    async def detect_patterns(
        self, 
        files: List[Path]
    ) -> Dict[str, Any]:
        """Detect AI patterns in files."""
        return await self.scanner.detect_patterns(files)
    
    async def quick_scan(self, file_paths: List[str]) -> Dict[str, Any]:
        """Perform quick scan on specific files."""
        return await self.scanner.quick_scan(file_paths)


# Maintain the same interface for existing code
__all__ = ['AIPatternDetector', 'PatternCategory', 'ProviderPatterns']