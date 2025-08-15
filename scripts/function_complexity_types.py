#!/usr/bin/env python3
"""
Function Complexity Types and Data Classes
Contains all data structures for function complexity linting.
"""

from dataclasses import dataclass
from typing import List

@dataclass
class FunctionComplexityViolation:
    """Function complexity violation data"""
    file_path: str
    function_name: str
    line_number: int
    actual_lines: int
    max_lines: int = 8
    severity: str = "error"
    message: str = ""