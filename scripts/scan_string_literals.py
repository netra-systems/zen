#!/usr/bin/env python3
"""
String Literals Scanner for Netra Platform
Scans codebase for string literals and maintains a master index.
"""

import ast
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict
from datetime import datetime

class StringLiteralScanner(ast.NodeVisitor):
    """AST visitor to extract string literals with context."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.literals: List[Dict[str, Any]] = []
        self.current_class = None
        self.current_function = None
        
    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
        
    def visit_FunctionDef(self, node):
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function
        
    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)
        
    def visit_Constant(self, node):
        if isinstance(node.value, str) and node.value:
            # Skip docstrings and comments
            if not (self.current_function and node.col_offset == 0):
                self.literals.append({
                    'value': node.value,
                    'line': node.lineno,
                    'context': self._get_context(),
                    'file': self.filepath
                })
        self.generic_visit(node)
        
    def _get_context(self) -> str:
        parts = []
        if self.current_class:
            parts.append(f"class:{self.current_class}")
        if self.current_function:
            parts.append(f"func:{self.current_function}")
        return '.'.join(parts) if parts else 'module'

class StringLiteralCategorizer:
    """Categorizes string literals based on patterns and context."""
    
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
    
    def categorize(self, literal: str, context: str = '') -> Tuple[str, str]:
        """Categorize a string literal based on patterns."""
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
        self.scanner = None
        self.categorizer = StringLiteralCategorizer()
        
    def scan_file(self, filepath: Path) -> List[Dict[str, Any]]:
        """Scan a single Python file for string literals."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            scanner = StringLiteralScanner(str(filepath.relative_to(self.root_dir)))
            scanner.visit(tree)
            return scanner.literals
        except Exception as e:
            print(f"Error scanning {filepath}: {e}")
            return []
            
    def scan_directory(self, directory: Path, exclude_dirs: Set[str] = None) -> None:
        """Recursively scan directory for Python files."""
        if exclude_dirs is None:
            exclude_dirs = {'.git', '__pycache__', 'venv', 'node_modules', '.pytest_cache'}
            
        for item in directory.iterdir():
            if item.is_dir():
                if item.name not in exclude_dirs:
                    self.scan_directory(item, exclude_dirs)
            elif item.suffix == '.py':
                literals = self.scan_file(item)
                self.process_literals(literals)
                
    def process_literals(self, literals: List[Dict[str, Any]]) -> None:
        """Process and categorize literals."""
        for literal_info in literals:
            value = literal_info['value']
            category, subtype = self.categorizer.categorize(value, literal_info['context'])
            
            # Skip uncategorized messages
            if category == 'uncategorized' and subtype == 'message':
                continue
                
            # Create entry
            entry = {
                'value': value,
                'type': subtype,
                'locations': [f"{literal_info['file']}:{literal_info['line']}"],
                'context': literal_info['context']
            }
            
            # Check if already exists
            existing = None
            for existing_entry in self.index[category][value]:
                if existing_entry['value'] == value:
                    existing = existing_entry
                    break
                    
            if existing:
                # Add new location
                location = f"{literal_info['file']}:{literal_info['line']}"
                if location not in existing['locations']:
                    existing['locations'].append(location)
            else:
                self.index[category][value] = [entry]
                
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
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scan codebase for string literals')
    parser.add_argument('--root', default='.', help='Root directory to scan')
    parser.add_argument('--output', default='SPEC/generated/string_literals.json', 
                        help='Output file path')
    parser.add_argument('--include-tests', action='store_true', 
                        help='Include test directories')
    
    args = parser.parse_args()
    
    root_dir = Path(args.root).resolve()
    output_path = root_dir / args.output
    
    print(f"Scanning {root_dir} for string literals...")
    
    indexer = StringLiteralIndexer(root_dir)
    
    # Scan main directories
    dirs_to_scan = ['app', 'frontend', 'auth_service', 'scripts', 'dev_launcher']
    if args.include_tests:
        dirs_to_scan.append('tests')
        
    for dir_name in dirs_to_scan:
        dir_path = root_dir / dir_name
        if dir_path.exists():
            print(f"Scanning {dir_name}/...")
            indexer.scan_directory(dir_path)
            
    # Save the index
    indexer.save_index(output_path)
    
    return 0

if __name__ == '__main__':
    exit(main())