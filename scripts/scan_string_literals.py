#!/usr/bin/env python3
"""
String Literals Scanner for Netra Platform
Scans codebase for string literals and maintains a master index.

DEPRECATION NOTICE:
This is the legacy scanner maintained for backward compatibility.
For new projects and enhanced features, use scan_string_literals_enhanced.py instead.

The enhanced scanner provides:
- Better categorization with confidence scores
- Markdown documentation generation
- Improved pattern matching
- Validation capabilities
- Multiple output formats

Usage:
    # Continue using this scanner (legacy mode)
    python scripts/scan_string_literals.py
    
    # Switch to enhanced scanner (recommended)
    python scripts/scan_string_literals_enhanced.py
"""

import json
import re
import warnings
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Import from the new modular components while maintaining compatibility
try:
    from string_literals.scanner_core import RawLiteral, scan_directory as scan_directory_core
    from string_literals.categorizer_enhanced import EnhancedStringLiteralCategorizer
    ENHANCED_AVAILABLE = True
except ImportError:
    # Fallback to embedded implementation for compatibility
    from string_literals import RawLiteral, scan_directory as scan_directory_core
    ENHANCED_AVAILABLE = False

class StringLiteralCategorizer:
    """Legacy categorizer maintained for backward compatibility.
    
    This class now uses the enhanced categorizer when available,
    but falls back to the original implementation for compatibility.
    """
    
    # Original patterns preserved for backward compatibility
    PATTERNS = {
        'configuration': [
            (r'^[A-Z_]+$', 'env_var'),  # Environment variables
            (r'_(url|uri|host|port|key|token|secret)$', 'config_key'),
            (r'^(max|min|default|timeout|retry)_', 'config_param'),
            (r'_config$', 'config_name'),
        ],
        'paths': [
            (r'^/api/', 'api_endpoint'),
            (r'^/ws|^/websocket', 'websocket_endpoint'),
            (r'\.(py|json|xml|yaml|yml|env)$', 'file_path'),
            (r'^(app|frontend|scripts|tests|SPEC)/', 'dir_path'),
            (r'^https?://', 'url'),
        ],
        'identifiers': [
            (r'_(agent|manager|executor|service)$', 'component_name'),
            (r'^(auth|main|frontend)_service$', 'service_name'),
            (r'_id$', 'id_field'),
        ],
        'database': [
            (r'^(threads|messages|users|agents|configs)', 'table_name'),
            (r'_(at|by|id|name|type|status)$', 'column_name'),
            (r'^(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE)', 'sql_keyword'),
        ],
        'events': [
            (r'^(on|emit|handle)_', 'event_handler'),
            (r'_(created|updated|deleted|connected|disconnected)$', 'event_type'),
            (r'^websocket_', 'websocket_event'),
        ],
        'metrics': [
            (r'_(count|total|rate|duration|latency|size)$', 'metric_name'),
            (r'^(error|success|failure|timeout)_', 'metric_status'),
        ],
        'environment': [
            (r'^(NETRA|APP|DB|REDIS|LOG|ENV)_', 'env_var_name'),
            (r'^(development|staging|production|test)$', 'env_type'),
        ],
        'states': [
            (r'^(pending|active|completed|failed|error|success)$', 'status_value'),
            (r'^(healthy|degraded|offline|online)$', 'health_status'),
            (r'^(enabled|disabled|true|false)$', 'boolean_state'),
        ],
    }
    
    def __init__(self):
        """Initialize categorizer, using enhanced version if available."""
        if ENHANCED_AVAILABLE:
            self._enhanced_categorizer = EnhancedStringLiteralCategorizer()
            self._use_enhanced = True
        else:
            self._use_enhanced = False
    
    def categorize(self, literal: str, context: str = '') -> Tuple[str, str]:
        """Categorize a string literal based on patterns.
        
        Uses enhanced categorizer when available, falls back to legacy implementation.
        """
        if self._use_enhanced:
            # Use enhanced categorizer but convert to legacy format
            # Create a pseudo-context from the context string
            if 'func:' in context:
                func_context = context.split('func:')[-1].strip()
            else:
                func_context = None
                
            if 'class:' in context:
                class_context = context.split('class:')[1].split('.')[0].strip()
            else:
                class_context = None
                
            raw_literal = RawLiteral(literal, "legacy", 1, class_context, func_context)
            categorized = self._enhanced_categorizer.categorize(raw_literal)
            
            # Skip ignored literals
            if categorized.category == 'ignored':
                return ('uncategorized', 'message')
            
            # Convert to legacy format
            return (categorized.category, categorized.subcategory or 'unknown')
        else:
            # Use original implementation
            return self._legacy_categorize(literal, context)
    
    def _legacy_categorize(self, literal: str, context: str = '') -> Tuple[str, str]:
        """Original categorization logic for fallback compatibility."""
        # Skip if too short or too long
        if len(literal) < 2 or len(literal) > 200:
            return ('uncategorized', 'unknown')
            
        # Skip if it looks like a message or documentation
        if ' ' in literal and len(literal.split()) > 3:
            return ('uncategorized', 'message')
            
        # Check patterns
        for category, patterns in self.PATTERNS.items():
            for pattern, subtype in patterns:
                if re.search(pattern, literal, re.IGNORECASE):
                    return (category, subtype)
                    
        # Check context hints
        context_lower = context.lower()
        if 'config' in context_lower:
            return ('configuration', 'config_value')
        elif 'route' in context_lower or 'endpoint' in context_lower:
            return ('paths', 'endpoint')
        elif 'event' in context_lower or 'handler' in context_lower:
            return ('events', 'event_name')
            
        return ('uncategorized', 'unknown')

class StringLiteralIndexer:
    """Main indexer that coordinates scanning and categorization."""
    
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.index: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))
        self.categorizer = StringLiteralCategorizer()
                
    def scan_directory(self, directory: Path, exclude_dirs: Set[str] = None) -> None:
        """Recursively scan directory for Python files."""
        if exclude_dirs is None:
            exclude_dirs = {'.git', '__pycache__', 'venv', 'node_modules', '.pytest_cache'}
            
        literals = scan_directory_core(directory, self.root_dir, exclude_dirs)
        self.process_literals(literals)
                
    def process_literals(self, literals: List[RawLiteral]) -> None:
        """Process and categorize literals."""
        for literal in literals:
            category, subtype = self.categorizer.categorize(literal.value, literal.context)
            
            # Skip uncategorized messages
            if category == 'uncategorized' and subtype == 'message':
                continue
                
            # Create entry
            entry = {
                'value': literal.value,
                'type': subtype,
                'locations': [f"{literal.file}:{literal.line}"],
                'context': literal.context
            }
            
            # Check if already exists
            existing = None
            for existing_entry in self.index[category][literal.value]:
                if existing_entry['value'] == literal.value:
                    existing = existing_entry
                    break
                    
            if existing:
                # Add new location
                location = f"{literal.file}:{literal.line}"
                if location not in existing['locations']:
                    existing['locations'].append(location)
            else:
                self.index[category][literal.value] = [entry]
                
    def generate_index(self) -> Dict[str, Any]:
        """Generate the final index structure."""
        output = {
            'metadata': {
                'version': '1.0.0',
                'generated_at': datetime.now().isoformat(),
                'root_directory': str(self.root_dir),
                'total_literals': sum(len(entries) for cat in self.index.values() for entries in cat.values())
            },
            'categories': {}
        }
        
        for category, literals_dict in self.index.items():
            if not literals_dict:
                continue
                
            category_data = {
                'count': len(literals_dict),
                'literals': {}
            }
            
            # Sort by value for consistency
            for value in sorted(literals_dict.keys()):
                entries = literals_dict[value]
                if entries:
                    category_data['literals'][value] = entries[0]
                    
            output['categories'][category] = category_data
            
        return output
        
    def save_index(self, output_path: Path) -> None:
        """Save index to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        index = self.generate_index()
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
            
        print(f"Index saved to {output_path}")
        print(f"Total literals indexed: {index['metadata']['total_literals']}")
        for category, data in index['categories'].items():
            print(f"  {category}: {data['count']} unique literals")

def main():
    """Main entry point for the legacy scanner."""
    import argparse
    
    # Show deprecation warning
    if ENHANCED_AVAILABLE:
        warnings.warn(
            "This is the legacy string literals scanner. "
            "Consider switching to scan_string_literals_enhanced.py for improved features and performance.",
            DeprecationWarning,
            stacklevel=2
        )
        print("INFO: Enhanced scanner available at scripts/scan_string_literals_enhanced.py")
        print("   Features: Better categorization, confidence scores, markdown docs, validation")
        print()
    
    parser = argparse.ArgumentParser(
        description='Legacy String Literals Scanner (Backward Compatible)',
        epilog="For enhanced features, use scan_string_literals_enhanced.py instead."
    )
    parser.add_argument('--root', default='.', help='Root directory to scan')
    parser.add_argument('--output', default='SPEC/generated/string_literals.json', 
                        help='Output file path')
    parser.add_argument('--include-tests', action='store_true', 
                        help='Include test directories')
    parser.add_argument('--enhanced-mode', action='store_true',
                        help='Use enhanced categorizer when available (preview)')
    
    args = parser.parse_args()
    
    root_dir = Path(args.root).resolve()
    output_path = root_dir / args.output
    
    print(f"Legacy scanning {root_dir} for string literals...")
    if args.enhanced_mode and ENHANCED_AVAILABLE:
        print("Using enhanced categorizer in compatibility mode")
    elif not ENHANCED_AVAILABLE:
        print("WARNING: Enhanced modules not available, using legacy implementation")
    print()
    
    indexer = StringLiteralIndexer(root_dir)
    
    # Scan main directories (updated directory list)
    dirs_to_scan = ['netra_backend', 'frontend', 'auth_service', 'scripts', 'shared']
    if args.include_tests:
        dirs_to_scan.extend(['tests', '__tests__'])
        
    for dir_name in dirs_to_scan:
        dir_path = root_dir / dir_name
        if dir_path.exists():
            print(f"Scanning {dir_name}/...")
            indexer.scan_directory(dir_path)
            
    # Save the index
    indexer.save_index(output_path)
    
    # Show migration suggestion
    if ENHANCED_AVAILABLE:
        print()
        print("TIP: Consider switching to the enhanced scanner:")
        print("   python scripts/scan_string_literals_enhanced.py --format all")
    
    return 0

if __name__ == '__main__':
    exit(main())