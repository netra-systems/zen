"""Pattern Scanner Module.

Handles file scanning and async pattern detection.
Manages file processing, batching, and result aggregation.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from netra_backend.app.agents.github_analyzer.ai_pattern_definitions import (
    AIPatternDefinitions,
)
from netra_backend.app.agents.github_analyzer.pattern_matcher import (
    GitHubAnalyzerPatternMatcher,
)
from netra_backend.app.logging_config import central_logger as logger


class PatternScanner:
    """Handles file scanning and pattern detection operations."""
    
    def __init__(self):
        """Initialize scanner with dependencies."""
        self.pattern_definitions = AIPatternDefinitions()
        self.pattern_matcher = GitHubAnalyzerPatternMatcher()
        self.patterns = self.pattern_definitions.get_all_patterns()
        self.file_extensions = self._init_extensions()
    
    def _init_extensions(self) -> Set[str]:
        """Initialize supported file extensions."""
        return {
            ".py", ".js", ".ts", ".jsx", ".tsx",
            ".java", ".go", ".rs", ".rb", ".php",
            ".cs", ".cpp", ".c", ".h", ".hpp"
        }
    
    async def detect_patterns(
        self, 
        files: List[Path]
    ) -> Dict[str, Any]:
        """Detect AI patterns in files."""
        results = {
            "detected_providers": set(),
            "pattern_locations": [],
            "summary": {}
        }
        
        batch_results = await self._process_files_in_batches(files)
        self._merge_all_results(results, batch_results)
        self._finalize_results(results)
        
        return results
    
    async def _process_files_in_batches(
        self, 
        files: List[Path]
    ) -> List[Optional[Dict[str, Any]]]:
        """Process files in batches for better performance."""
        batch_size = 10
        all_results = []
        
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[self._analyze_file(f) for f in batch]
            )
            all_results.extend(batch_results)
        
        return all_results
    
    def _merge_all_results(
        self,
        results: Dict[str, Any],
        batch_results: List[Optional[Dict[str, Any]]]
    ) -> None:
        """Merge all batch results into main results."""
        for file_result in batch_results:
            if file_result:
                self.pattern_matcher.merge_results(results, file_result)
    
    def _finalize_results(self, results: Dict[str, Any]) -> None:
        """Finalize results for JSON serialization."""
        results["detected_providers"] = list(results["detected_providers"])
        results["summary"] = self.pattern_matcher.generate_summary(results)
    
    async def analyze_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Analyze single file for patterns (public interface)."""
        return await self._analyze_file(file_path)
    
    async def _analyze_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Analyze single file for patterns."""
        if file_path.suffix not in self.file_extensions:
            return None
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            return self.pattern_matcher.scan_content(
                content, str(file_path), self.patterns
            )
        except Exception as e:
            logger.warning(f"Error reading {file_path}: {e}")
            return None
    
    async def quick_scan(self, file_paths: List[str]) -> Dict[str, Any]:
        """Perform quick scan on specific files."""
        paths = [Path(p) for p in file_paths]
        return await self.detect_patterns(paths)