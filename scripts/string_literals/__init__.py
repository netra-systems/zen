"""
String Literals Scanner Package
Modular components for scanning and processing string literals in Python codebases.
"""

from .scanner_core import RawLiteral, StringLiteralScanner, scan_file, scan_directory
from .categorizer_enhanced import (
    CategorizedLiteral, 
    EnhancedStringLiteralCategorizer,
    categorize_literals,
    print_categorization_report
)

__all__ = [
    'RawLiteral',
    'StringLiteralScanner', 
    'scan_file',
    'scan_directory',
    'CategorizedLiteral',
    'EnhancedStringLiteralCategorizer',
    'categorize_literals',
    'print_categorization_report'
]