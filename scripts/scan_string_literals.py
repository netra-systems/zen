#!/usr/bin/env python3
"""
String Literals Scanner for Netra Platform
Scans project source code for string literals and maintains a focused index.
Excludes dependencies, build artifacts, and noise for a clean, usable index.
"""

import ast
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Optional

class StringLiteralScanner:
    """Scanner that focuses on actual project code, excluding dependencies and noise."""
    
    # Directories to completely exclude
    EXCLUDE_DIRS = {
        '.git', '__pycache__', 'venv', '.venv', 'node_modules', 
        '.pytest_cache', 'htmlcov', 'coverage', 'dist', 'build',
        '.tox', '.eggs', '.mypy_cache', '.ruff_cache', 'site-packages',
        'dist-packages', 'Lib', 'Scripts', 'Include', '.next',
        'out', 'cypress', 'public', 'static', 'env', '.env',
        '.idea', '.vscode', 'tmp', 'temp', 'cache'
    }
    
    # File patterns to exclude
    EXCLUDE_FILES = {
        'package-lock.json', 'yarn.lock', 'poetry.lock', 'Pipfile.lock',
        'requirements.txt', 'setup.py', 'setup.cfg', 'pyproject.toml'
    }
    
    # Extensions to scan
    INCLUDE_EXTENSIONS = {'.py', '.ts', '.tsx', '.js', '.jsx'}
    
    # Test file patterns (for separate handling)
    TEST_PATTERNS = [
        r'test_.*\.py$',
        r'.*_test\.py$',
        r'.*\.test\.[jt]sx?$',
        r'.*\.spec\.[jt]sx?$',
        r'__tests__',
        r'/tests/',
    ]
    
    # Common noise patterns to filter out
    NOISE_PATTERNS = [
        r'^$',  # Empty strings
        r'^\s+$',  # Whitespace only
        r'^[0-9]+$',  # Just numbers
        r'^[a-f0-9]{32,}$',  # Hashes
        r'^\W+$',  # Only special characters
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',  # UUIDs
    ]
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.literals_by_category = defaultdict(lambda: defaultdict(list))
        self.file_count = 0
        self.literal_count = 0
        self.errors = []
        
    def should_skip_dir(self, dir_path: Path) -> bool:
        """Check if directory should be skipped."""
        return (
            dir_path.name in self.EXCLUDE_DIRS or 
            dir_path.name.startswith('.') or
            dir_path.name.endswith('.egg-info')
        )
        
    def should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        if file_path.name in self.EXCLUDE_FILES:
            return True
        if file_path.suffix not in self.INCLUDE_EXTENSIONS:
            return True
        # Skip minified files
        if '.min.' in file_path.name or '.bundle.' in file_path.name:
            return True
        # Skip generated files
        if any(pattern in str(file_path) for pattern in ['generated/', 'gen/', 'protobuf/']):
            return True
        return False
        
    def is_test_file(self, file_path: Path) -> bool:
        """Check if file is a test file."""
        path_str = str(file_path).replace('\\', '/')
        return any(re.search(pattern, path_str) for pattern in self.TEST_PATTERNS)
        
    def is_noise_literal(self, literal: str) -> bool:
        """Check if literal is noise that should be filtered."""
        if len(literal) > 500:  # Very long strings are often data/noise
            return True
        if len(literal) < 2:  # Too short to be meaningful
            return True
        return any(re.match(pattern, literal) for pattern in self.NOISE_PATTERNS)
        
    def categorize_literal(self, literal: str, file_context: str = None) -> Optional[str]:
        """Categorize a string literal based on patterns and context."""
        # Skip noise
        if self.is_noise_literal(literal):
            return None
            
        # Environment variables
        if re.match(r'^[A-Z][A-Z0-9_]{2,}$', literal):
            if any(prefix in literal for prefix in ['NETRA_', 'DATABASE_', 'REDIS_', 'API_', 'AUTH_']):
                return 'environment'
            elif len(literal) > 3:
                return 'configuration'
        
        # API paths and routes
        if (literal.startswith('/') and 
            any(segment in literal for segment in ['/api/', '/', '/v2/', '/ws/', '/websocket/'])):
            return 'paths'
        
        # File paths
        if any(sep in literal for sep in ['/', '\\']):
            if any(ext in literal for ext in ['.py', '.ts', '.tsx', '.js', '.jsx', '.json', '.xml']):
                return 'paths'
        
        # Database fields and operations
        if re.match(r'^(id|.*_id|.*_at|created|updated|deleted|modified)$', literal):
            return 'database'
        
        # SQL/Database keywords
        if literal.upper() in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'FROM', 'WHERE', 'JOIN']:
            return 'database'
        
        # Event names
        if (re.match(r'^on[A-Z]', literal) or 
            literal.startswith(('emit:', 'broadcast:', 'listen:')) or
            literal.endswith(('_event', '_EVENT', ':event'))):
            return 'events'
        
        # WebSocket message types
        if literal in ['connect', 'disconnect', 'message', 'error', 'ping', 'pong', 'subscribe', 'unsubscribe']:
            return 'events'
        
        # Metric names
        if (re.match(r'^(metric|counter|gauge|histogram|timer)_', literal) or
            literal.endswith(('_total', '_count', '_sum', '_bucket'))):
            return 'metrics'
        
        # States and statuses
        if literal.lower() in [
            'pending', 'active', 'inactive', 'enabled', 'disabled',
            'success', 'failed', 'error', 'warning', 'info',
            'loading', 'loaded', 'ready', 'busy', 'idle',
            'open', 'closed', 'connected', 'disconnected'
        ]:
            return 'states'
        
        # Service/agent/component identifiers
        if literal.endswith(('_agent', '_service', '_manager', '_handler', '_provider', '_controller')):
            return 'identifiers'
        
        # HTTP methods
        if literal in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
            return 'configuration'
        
        # Content types
        if 'application/' in literal or 'text/' in literal or 'image/' in literal:
            return 'configuration'
        
        # Short meaningful identifiers
        if 3 <= len(literal) <= 50:
            # Check if it's a valid identifier-like string
            clean = literal.replace('_', '').replace('-', '').replace(':', '')
            if clean and clean[0].isalpha() and clean.replace(' ', '').isalnum():
                return 'identifiers'
        
        # Log messages and user-facing text
        if ' ' in literal and len(literal) > 10:
            return 'messages'
            
        return None  # Filter out uncategorized
        
    def scan_python_file(self, file_path: Path) -> List[tuple]:
        """Scan a Python file for string literals."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            literals = []
            
            class LiteralVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.literals = []
                    self.in_docstring = False
                    
                def visit_FunctionDef(self, node):
                    # Skip function docstrings
                    if (node.body and 
                        isinstance(node.body[0], ast.Expr) and
                        isinstance(node.body[0].value, ast.Constant) and
                        isinstance(node.body[0].value.value, str)):
                        self.in_docstring = True
                        self.visit(node.body[0])
                        self.in_docstring = False
                        for child in node.body[1:]:
                            self.visit(child)
                    else:
                        self.generic_visit(node)
                        
                def visit_ClassDef(self, node):
                    # Skip class docstrings
                    if (node.body and 
                        isinstance(node.body[0], ast.Expr) and
                        isinstance(node.body[0].value, ast.Constant) and
                        isinstance(node.body[0].value.value, str)):
                        self.in_docstring = True
                        self.visit(node.body[0])
                        self.in_docstring = False
                        for child in node.body[1:]:
                            self.visit(child)
                    else:
                        self.generic_visit(node)
                    
                def visit_Constant(self, node):
                    if isinstance(node.value, str) and not self.in_docstring:
                        literal = node.value.strip()
                        if literal:
                            self.literals.append((literal, node.lineno))
                    self.generic_visit(node)
                    
            visitor = LiteralVisitor()
            visitor.visit(tree)
            return visitor.literals
            
        except Exception as e:
            self.errors.append(f"Error scanning {file_path}: {e}")
            return []
            
    def scan_javascript_file(self, file_path: Path) -> List[tuple]:
        """Scan a JavaScript/TypeScript file for string literals."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Remove comments
            content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
            
            literals = []
            line_num = 1
            
            # Match string literals (both single and double quotes, including template literals)
            patterns = [
                r'"([^"\\]|\\.)*"',  # Double quotes
                r"'([^'\\]|\\.)*'",  # Single quotes
                r'`([^`\\]|\\.)*`',  # Template literals (basic, without interpolation)
            ]
            
            for line in content.split('\n'):
                for pattern in patterns:
                    for match in re.finditer(pattern, line):
                        literal = match.group()[1:-1]  # Remove quotes
                        literal = literal.strip()
                        if literal and not literal.startswith('${'):  # Skip template expressions
                            literals.append((literal, line_num))
                line_num += 1
                    
            return literals
            
        except Exception as e:
            self.errors.append(f"Error scanning {file_path}: {e}")
            return []
            
    def scan_file(self, file_path: Path) -> None:
        """Scan a single file for string literals."""
        is_test = self.is_test_file(file_path)
        relative_path = str(file_path.relative_to(self.root_dir)).replace('\\', '/')
        
        if file_path.suffix == '.py':
            literals = self.scan_python_file(file_path)
        else:
            literals = self.scan_javascript_file(file_path)
            
        self.file_count += 1
        
        for literal, line_no in literals:
            # Use test_literals category for test files
            if is_test:
                category = 'test_literals'
            else:
                category = self.categorize_literal(literal, relative_path)
            
            if category:
                # Store with location info
                if literal not in self.literals_by_category[category]:
                    self.literals_by_category[category][literal] = []
                self.literals_by_category[category][literal].append(f"{relative_path}:{line_no}")
                self.literal_count += 1
                
    def scan_directory(self, directory: Path) -> None:
        """Recursively scan directory for string literals."""
        if not directory.exists():
            return
            
        for item in sorted(directory.iterdir()):
            if item.is_dir():
                if not self.should_skip_dir(item):
                    self.scan_directory(item)
            elif item.is_file():
                if not self.should_skip_file(item):
                    self.scan_file(item)
                    
    def generate_index(self) -> Dict[str, Any]:
        """Generate the final index structure."""
        index = {
            'metadata': {
                'version': '3.0.0',
                'generated_at': datetime.now().isoformat(),
                'root_directory': str(self.root_dir),
                'files_scanned': self.file_count,
                'total_literals': self.literal_count,
                'unique_literals': sum(len(lits) for lits in self.literals_by_category.values()),
                'errors': len(self.errors)
            },
            'categories': {}
        }
        
        for category in sorted(self.literals_by_category.keys()):
            literals = self.literals_by_category[category]
            index['categories'][category] = {
                'count': len(literals),
                'literals': {}
            }
            
            # Include all literals with their locations
            for literal in sorted(literals.keys()):
                locations = literals[literal]
                index['categories'][category]['literals'][literal] = {
                    'value': literal,
                    'category': category,
                    'locations': locations[:10]  # Limit locations to keep file size reasonable
                }
                
        return index
        
    def save_index(self, output_path: Path) -> None:
        """Save the scan results to a JSON file and create sub-indexes by category."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        index = self.generate_index()
        
        # Save main index
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        
        # Create sub-indexes directory
        sub_index_dir = output_path.parent / 'sub_indexes'
        sub_index_dir.mkdir(exist_ok=True)
        
        # Save sub-indexes by category
        for category, data in index['categories'].items():
            sub_index = {
                'metadata': {
                    'version': '3.0.0',
                    'category': category,
                    'generated_at': datetime.now().isoformat(),
                    'root_directory': str(self.root_dir),
                    'total_literals': data['count']
                },
                'literals': data['literals']
            }
            
            sub_index_path = sub_index_dir / f'{category}.json'
            with open(sub_index_path, 'w', encoding='utf-8') as f:
                json.dump(sub_index, f, indent=2, ensure_ascii=False)
        
        # Also create a compact index with just the literal values (no metadata) for quick lookups
        compact_dir = output_path.parent / 'compact'
        compact_dir.mkdir(exist_ok=True)
        
        for category, data in index['categories'].items():
            compact_index = {
                'values': sorted(data['literals'].keys())
            }
            
            compact_path = compact_dir / f'{category}.json'
            with open(compact_path, 'w', encoding='utf-8') as f:
                json.dump(compact_index, f, indent=2, ensure_ascii=False)
            
        # Print summary
        print(f"\n{'='*50}")
        print(f"String Literals Scan Complete")
        print(f"{'='*50}")
        print(f"Files scanned: {self.file_count:,}")
        print(f"Total literals found: {self.literal_count:,}")
        print(f"Unique literals: {index['metadata']['unique_literals']:,}")
        
        if self.errors:
            print(f"Errors encountered: {len(self.errors)}")
            
        print(f"\nBreakdown by category:")
        for category, data in index['categories'].items():
            print(f"  {category:20s}: {data['count']:,} unique literals")
            
        print(f"\nIndexes saved to:")
        print(f"  Main index: {output_path}")
        print(f"  Sub-indexes: {sub_index_dir}")
        print(f"  Compact indexes: {compact_dir}")
        
        if self.errors and len(self.errors) <= 10:
            print(f"\nErrors:")
            for error in self.errors[:10]:
                print(f"  - {error}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='String Literals Scanner - Focused index for Netra Platform',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan with default settings
  python scripts/scan_string_literals.py
  
  # Scan specific directories
  python scripts/scan_string_literals.py --dirs netra_backend/app auth_service
  
  # Include test files in main index
  python scripts/scan_string_literals.py --include-tests
  
  # Custom output location
  python scripts/scan_string_literals.py --output custom_index.json
        """
    )
    
    parser.add_argument(
        '--root', 
        default='.', 
        help='Root directory to scan (default: current directory)'
    )
    parser.add_argument(
        '--output', 
        default='SPEC/generated/string_literals.json',
        help='Output file path (default: SPEC/generated/string_literals.json)'
    )
    parser.add_argument(
        '--dirs', 
        nargs='+',
        help='Specific directories to scan (default: auto-detect project dirs)'
    )
    parser.add_argument(
        '--include-tests',
        action='store_true',
        help='Include test directories in scanning (they are categorized separately)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed progress during scanning'
    )
    
    args = parser.parse_args()
    
    root_dir = Path(args.root).resolve()
    output_path = root_dir / args.output
    
    print(f"Scanning {root_dir} for string literals...")
    print(f"Excluding: dependencies, node_modules, build artifacts, etc.\n")
    
    scanner = StringLiteralScanner(root_dir)
    
    # Determine directories to scan
    if args.dirs:
        dirs_to_scan = args.dirs
    else:
        # Auto-detect project structure
        dirs_to_scan = []
        
        # Backend services
        if (root_dir / 'netra_backend' / 'app').exists():
            dirs_to_scan.append('netra_backend/app')
        elif (root_dir / 'netra_backend').exists():
            dirs_to_scan.append('netra_backend')
            
        # Auth service
        if (root_dir / 'auth_service').exists():
            dirs_to_scan.append('auth_service')
            
        # Frontend source
        for frontend_dir in ['frontend/src', 'frontend/components', 'frontend/providers', 'frontend/pages']:
            if (root_dir / frontend_dir).exists():
                dirs_to_scan.append(frontend_dir)
        
        # Scripts and shared
        for util_dir in ['scripts', 'shared']:
            if (root_dir / util_dir).exists():
                dirs_to_scan.append(util_dir)
                
        # Include test directories if requested
        if args.include_tests:
            for test_dir in ['tests', 'netra_backend/tests', 'auth_service/tests']:
                if (root_dir / test_dir).exists():
                    dirs_to_scan.append(test_dir)
    
    # Scan directories
    for dir_name in dirs_to_scan:
        dir_path = root_dir / dir_name
        if dir_path.exists():
            if args.verbose:
                print(f"Scanning {dir_name}...")
            scanner.scan_directory(dir_path)
        else:
            print(f"Warning: Directory not found: {dir_name}")
            
    # Save results
    scanner.save_index(output_path)
    
    return 0


if __name__ == '__main__':
    exit(main())