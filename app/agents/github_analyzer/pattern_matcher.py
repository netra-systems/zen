"""Pattern Matcher Module.

Handles pattern matching logic and result processing.
Includes regex matching, result merging, and summary generation.
"""

import re
from typing import Dict, List, Any, Tuple

from app.logging_config import central_logger as logger


class GitHubAnalyzerPatternMatcher:
    """Handles pattern matching and result processing."""
    
    def scan_content(
        self, 
        content: str, 
        file_path: str, 
        patterns: Dict[str, Dict[str, List[str]]]
    ) -> Dict[str, Any]:
        """Scan content for patterns."""
        results = {
            "file": file_path,
            "providers": set(),
            "patterns": []
        }
        
        lines = content.split('\n')
        
        for provider, categories in patterns.items():
            self._scan_provider_patterns(results, lines, provider, categories)
        
        return results
    
    def _scan_provider_patterns(
        self,
        results: Dict[str, Any],
        lines: List[str],
        provider: str,
        categories: Dict[str, List[str]]
    ) -> None:
        """Scan for specific provider patterns."""
        for category, pattern_list in categories.items():
            for pattern in pattern_list:
                matches = self._find_matches(lines, pattern)
                if matches:
                    self._add_pattern_matches(results, provider, category, pattern, matches)
    
    def _add_pattern_matches(
        self,
        results: Dict[str, Any],
        provider: str,
        category: str,
        pattern: str,
        matches: List[Tuple[int, str]]
    ) -> None:
        """Add pattern matches to results."""
        results["providers"].add(provider)
        for line_num, line_content in matches:
            results["patterns"].append({
                "provider": provider,
                "category": category,
                "pattern": pattern,
                "line": line_num,
                "content": line_content[:100]
            })
    
    def find_matches(
        self, 
        lines: List[str], 
        pattern: str
    ) -> List[Tuple[int, str]]:
        """Find pattern matches in lines."""
        return self._find_matches(lines, pattern)
    
    def _find_matches(
        self, 
        lines: List[str], 
        pattern: str
    ) -> List[Tuple[int, str]]:
        """Find pattern matches in lines."""
        matches = []
        regex = re.compile(pattern, re.IGNORECASE)
        
        for i, line in enumerate(lines, 1):
            if regex.search(line):
                matches.append((i, line.strip()))
        
        return matches
    
    def merge_results(
        self, 
        main_results: Dict[str, Any], 
        file_result: Dict[str, Any]
    ) -> None:
        """Merge file results into main results."""
        main_results["detected_providers"].update(file_result["providers"])
        
        if file_result["patterns"]:
            main_results["pattern_locations"].append({
                "file": file_result["file"],
                "patterns": file_result["patterns"]
            })
    
    def generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate analysis summary."""
        pattern_counts = self._count_patterns_by_provider(results)
        
        return {
            "total_files_analyzed": len(results["pattern_locations"]),
            "providers_detected": len(results["detected_providers"]),
            "pattern_counts": pattern_counts,
            "complexity": self._estimate_complexity(pattern_counts)
        }
    
    def _count_patterns_by_provider(
        self, 
        results: Dict[str, Any]
    ) -> Dict[str, int]:
        """Count patterns by provider."""
        pattern_counts = {}
        for location in results["pattern_locations"]:
            for pattern in location["patterns"]:
                provider = pattern["provider"]
                if provider not in pattern_counts:
                    pattern_counts[provider] = 0
                pattern_counts[provider] += 1
        return pattern_counts
    
    def estimate_complexity(self, pattern_counts: Dict[str, int]) -> str:
        """Estimate AI infrastructure complexity."""
        return self._estimate_complexity(pattern_counts)
    
    def _estimate_complexity(self, pattern_counts: Dict[str, int]) -> str:
        """Estimate AI infrastructure complexity."""
        total_patterns = sum(pattern_counts.values())
        providers = len(pattern_counts)
        
        if total_patterns > 100 or providers > 3:
            return "high"
        elif total_patterns > 30 or providers > 1:
            return "medium"
        else:
            return "low"