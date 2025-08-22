"""
Error Detector for Dev Launcher

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide error detection functionality for dev launcher tests
- Value Impact: Enables dev launcher error tests to execute without import errors
- Strategic Impact: Enables error detection functionality validation
"""

import logging
import re
from typing import Dict, List, Optional, Pattern
from pathlib import Path


class ErrorDetector:
    """Detects and analyzes errors in development launcher processes."""
    
    def __init__(self):
        """Initialize error detector."""
        self.error_patterns: List[Pattern] = []
        self.error_counts: Dict[str, int] = {}
        self.logger = logging.getLogger(__name__)
    
    def add_error_pattern(self, pattern: str) -> None:
        """Add an error pattern to detect."""
        compiled_pattern = re.compile(pattern, re.IGNORECASE)
        self.error_patterns.append(compiled_pattern)
    
    def detect_errors(self, text: str) -> List[Dict[str, str]]:
        """Detect errors in given text."""
        errors = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            for pattern in self.error_patterns:
                if pattern.search(line):
                    error_info = {
                        'line': line,
                        'line_number': line_num,
                        'pattern': pattern.pattern,
                        'type': 'error'
                    }
                    errors.append(error_info)
                    
                    # Update error counts
                    error_type = pattern.pattern
                    self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        return errors
    
    def detect_errors_in_file(self, file_path: Path) -> List[Dict[str, str]]:
        """Detect errors in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.detect_errors(content)
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            return []
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of detected errors."""
        return self.error_counts.copy()
    
    def reset_error_counts(self) -> None:
        """Reset error counts."""
        self.error_counts.clear()
    
    def has_errors(self) -> bool:
        """Check if any errors have been detected."""
        return sum(self.error_counts.values()) > 0