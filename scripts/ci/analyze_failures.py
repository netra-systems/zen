#!/usr/bin/env python3
"""Analyze test failures to determine fixability and strategy."""

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


@dataclass
class FailureAnalysis:
    """Analysis of a test failure."""
    file: str
    name: str
    error_type: str
    error_message: str
    error_summary: str
    confidence: int
    fixable: bool
    suggested_approach: str
    context_needed: List[str]


class TestFailureAnalyzer:
    """Analyze test failures to determine fixability."""
    
    # Error patterns and their fixability confidence
    ERROR_PATTERNS = {
        # High confidence fixes (90-100%)
        r"ImportError|ModuleNotFoundError": ("import_error", 95, True),
        r"NameError: name '(\w+)' is not defined": ("name_error", 90, True),
        r"SyntaxError": ("syntax_error", 95, True),
        r"IndentationError": ("indentation_error", 98, True),
        r"TypeError: .* got an unexpected keyword argument": ("type_error", 85, True),
        r"AttributeError: '(\w+)' object has no attribute '(\w+)'": ("attribute_error", 80, True),
        
        # Medium confidence fixes (50-80%)
        r"AssertionError": ("assertion_error", 60, True),
        r"ValueError": ("value_error", 55, True),
        r"KeyError": ("key_error", 65, True),
        r"IndexError": ("index_error", 70, True),
        r"TypeError: .* missing \d+ required positional argument": ("missing_argument", 75, True),
        
        # Low confidence fixes (20-50%)
        r"TimeoutError|asyncio.TimeoutError": ("timeout_error", 30, False),
        r"ConnectionError|ConnectionRefusedError": ("connection_error", 25, False),
        r"PermissionError": ("permission_error", 20, False),
        
        # Likely not fixable
        r"SystemExit": ("system_exit", 10, False),
        r"KeyboardInterrupt": ("keyboard_interrupt", 0, False),
    }
    
    def __init__(self, results_dir: str):
        """Initialize analyzer with test results directory."""
        self.results_dir = Path(results_dir)
        self.failures = []
        
    def analyze_all(self) -> Dict[str, Any]:
        """Analyze all test failures in the results directory."""
        # Load all test result files
        for result_file in self.results_dir.glob("**/*.json"):
            self._analyze_file(result_file)
            
        # Categorize failures
        fixable = [f for f in self.failures if f.fixable]
        not_fixable = [f for f in self.failures if not f.fixable]
        
        # Sort by confidence
        fixable.sort(key=lambda x: x.confidence, reverse=True)
        
        return {
            "total_failures": len(self.failures),
            "fixable_count": len(fixable),
            "not_fixable_count": len(not_fixable),
            "high_confidence_count": len([f for f in fixable if f.confidence >= 80]),
            "medium_confidence_count": len([f for f in fixable if 50 <= f.confidence < 80]),
            "low_confidence_count": len([f for f in fixable if f.confidence < 50]),
            "fixable_tests": [asdict(f) for f in fixable],
            "not_fixable_tests": [asdict(f) for f in not_fixable],
            "suggested_strategy": self._determine_strategy(fixable),
            "estimated_success_rate": self._estimate_success_rate(fixable)
        }
        
    def _analyze_file(self, result_file: Path) -> None:
        """Analyze failures in a single test result file."""
        try:
            with open(result_file) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return
            
        # Extract failed tests
        tests = data.get("tests", [])
        for test in tests:
            if test.get("status") == "failed":
                analysis = self._analyze_failure(test)
                if analysis:
                    self.failures.append(analysis)
                    
    def _analyze_failure(self, test: Dict[str, Any]) -> FailureAnalysis:
        """Analyze a single test failure."""
        error_msg = test.get("error", "")
        traceback = test.get("traceback", "")
        
        # Determine error type and confidence
        error_type, confidence, fixable = self._classify_error(error_msg, traceback)
        
        # Determine what context is needed
        context_needed = self._determine_context(error_type, error_msg)
        
        # Suggest approach
        approach = self._suggest_approach(error_type, confidence)
        
        return FailureAnalysis(
            file=test.get("file", "unknown"),
            name=test.get("name", "unknown"),
            error_type=error_type,
            error_message=error_msg[:500],  # Limit message length
            error_summary=self._summarize_error(error_msg),
            confidence=confidence,
            fixable=fixable,
            suggested_approach=approach,
            context_needed=context_needed
        )
        
    def _classify_error(self, error_msg: str, traceback: str) -> Tuple[str, int, bool]:
        """Classify the error type and determine fixability."""
        full_text = f"{error_msg}\n{traceback}"
        
        for pattern, (error_type, confidence, fixable) in self.ERROR_PATTERNS.items():
            if re.search(pattern, full_text, re.IGNORECASE):
                return error_type, confidence, fixable
                
        # Unknown error type
        return "unknown_error", 20, False
        
    def _determine_context(self, error_type: str, error_msg: str) -> List[str]:
        """Determine what context files are needed for the fix."""
        context = ["test_file", "error_trace"]
        
        if error_type in ["import_error", "module_not_found"]:
            context.extend(["requirements.txt", "setup.py", "pyproject.toml"])
        elif error_type in ["attribute_error", "name_error"]:
            context.extend(["source_file", "related_imports"])
        elif error_type in ["type_error", "missing_argument"]:
            context.extend(["function_signature", "call_site"])
        elif error_type == "assertion_error":
            context.extend(["test_data", "expected_values", "actual_implementation"])
            
        return context
        
    def _suggest_approach(self, error_type: str, confidence: int) -> str:
        """Suggest an approach for fixing the error."""
        approaches = {
            "import_error": "Check and fix import statements, add missing dependencies",
            "syntax_error": "Fix syntax issues in the code",
            "indentation_error": "Correct indentation to match Python requirements",
            "type_error": "Adjust function calls or type annotations",
            "attribute_error": "Add missing attributes or fix attribute access",
            "assertion_error": "Update test assertions or fix implementation",
            "name_error": "Define missing variables or import required names",
            "value_error": "Fix value validation or adjust test inputs",
            "key_error": "Handle missing dictionary keys or fix key access",
            "index_error": "Fix list/array indexing or add bounds checking"
        }
        
        return approaches.get(error_type, "Analyze error context and apply appropriate fix")
        
    def _summarize_error(self, error_msg: str) -> str:
        """Create a brief summary of the error."""
        # Take first line or first 100 chars
        lines = error_msg.split('\n')
        if lines:
            summary = lines[0][:100]
            if len(lines[0]) > 100:
                summary += "..."
            return summary
        return "Unknown error"
        
    def _determine_strategy(self, fixable: List[FailureAnalysis]) -> str:
        """Determine the overall fix strategy."""
        if not fixable:
            return "no_automatic_fix"
            
        high_conf = [f for f in fixable if f.confidence >= 80]
        if len(high_conf) >= len(fixable) * 0.7:
            return "aggressive"  # Most fixes are high confidence
        elif len(high_conf) >= len(fixable) * 0.3:
            return "balanced"  # Mix of confidence levels
        else:
            return "conservative"  # Mostly low confidence
            
    def _estimate_success_rate(self, fixable: List[FailureAnalysis]) -> float:
        """Estimate overall success rate based on confidence scores."""
        if not fixable:
            return 0.0
            
        # Weight by confidence
        total_confidence = sum(f.confidence for f in fixable)
        return total_confidence / len(fixable)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Analyze test failures")
    parser.add_argument("--results-dir", required=True, help="Directory containing test results")
    parser.add_argument("--output-json", required=True, help="Output analysis JSON file")
    
    args = parser.parse_args()
    
    analyzer = TestFailureAnalyzer(args.results_dir)
    analysis = analyzer.analyze_all()
    
    # Save analysis
    output_path = Path(args.output_json)
    with open(output_path, 'w') as f:
        json.dump(analysis, f, indent=2)
        
    print(f"Analysis complete: {analysis['fixable_count']}/{analysis['total_failures']} failures are fixable")
    print(f"Estimated success rate: {analysis['estimated_success_rate']:.1f}%")
    print(f"Analysis saved to {output_path}")


if __name__ == "__main__":
    main()