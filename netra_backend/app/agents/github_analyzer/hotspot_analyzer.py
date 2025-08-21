"""Hotspot Analyzer Module.

Specialized module for identifying and analyzing AI hotspots in code.
Handles pattern counting, hotspot ranking, and result formatting.
"""

from typing import Any, Dict, List


class HotspotAnalyzer:
    """Analyzes AI hotspots in code."""
    
    def identify_hotspots(
        self, 
        patterns: Dict[str, Any],
        llm_mappings: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify AI hotspots in code."""
        file_counts = self._count_patterns_per_file(patterns)
        hotspots = self._get_top_hotspots(file_counts)
        return self._format_hotspots(hotspots)
    
    def _count_patterns_per_file(
        self, 
        patterns: Dict[str, Any]
    ) -> Dict[str, int]:
        """Count patterns per file."""
        file_counts: Dict[str, int] = {}
        pattern_locations = patterns.get("pattern_locations", [])
        return self._process_pattern_counts(file_counts, pattern_locations)
    
    def _process_pattern_counts(
        self, file_counts: Dict[str, int], pattern_locations: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Process pattern locations to count patterns per file."""
        for location in pattern_locations:
            file_path = location["file"]
            pattern_count = len(location["patterns"])
            file_counts[file_path] = file_counts.get(file_path, 0) + pattern_count
        return file_counts
    
    def _get_top_hotspots(
        self, 
        file_counts: Dict[str, int]
    ) -> List[tuple]:
        """Get top 10 hotspots by pattern count."""
        sorted_counts = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_counts[:10]
    
    def _format_hotspots(
        self, 
        hotspots: List[tuple]
    ) -> List[Dict[str, Any]]:
        """Format hotspots as dictionaries."""
        return [
            self._create_hotspot_dict(file, count)
            for file, count in hotspots
        ]
    
    def _create_hotspot_dict(self, file: str, count: int) -> Dict[str, Any]:
        """Create hotspot dictionary."""
        return {"file": file, "ai_operations": count}