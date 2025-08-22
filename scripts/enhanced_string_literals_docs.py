#!/usr/bin/env python3
"""
Enhanced String Literals Documentation Generator
Full pipeline: Scan -> Enhanced Categorize -> Generate Markdown Docs
"""

import sys
from pathlib import Path
from typing import List, Set

# Add string_literals package to path
sys.path.insert(0, str(Path(__file__).parent / "string_literals"))

from string_literals.scanner_core import scan_directory
from string_literals.categorizer_enhanced import categorize_literals
from string_literals.markdown_reporter import generate_markdown_docs


def scan_and_generate_docs(
    root_dir: Path,
    output_dir: Path,
    include_dirs: List[str] = None,
    exclude_dirs: Set[str] = None
) -> None:
    """Complete pipeline: scan -> categorize -> generate docs."""
    
    if include_dirs is None:
        include_dirs = ['app', 'frontend', 'auth_service', 'scripts', 'netra_backend']
    
    if exclude_dirs is None:
        exclude_dirs = {'.git', '__pycache__', 'venv', 'node_modules', '.pytest_cache', 'dist', 'build'}
    
    print(f"Scanning directories: {', '.join(include_dirs)}")
    print(f"Root directory: {root_dir}")
    
    # Scan for raw literals
    all_raw_literals = []
    for dir_name in include_dirs:
        dir_path = root_dir / dir_name
        if dir_path.exists() and dir_path.is_dir():
            print(f"  Scanning {dir_name}/...")
            literals = scan_directory(dir_path, root_dir, exclude_dirs)
            all_raw_literals.extend(literals)
            print(f"    Found {len(literals)} literals")
        else:
            print(f"  Skipping {dir_name}/ (not found)")
    
    print(f"\nTotal raw literals found: {len(all_raw_literals)}")
    
    # Enhanced categorization
    print("Performing enhanced categorization...")
    categorized_literals = categorize_literals(all_raw_literals)
    
    # Filter out ignored literals for reporting
    active_literals = [l for l in categorized_literals if l.category != 'ignored']
    print(f"Active literals after filtering: {len(active_literals)}")
    
    # Generate markdown documentation
    print(f"\nGenerating documentation in: {output_dir}")
    generate_markdown_docs(categorized_literals, output_dir)
    
    # Print summary
    categories = {}
    for literal in active_literals:
        categories[literal.category] = categories.get(literal.category, 0) + 1
    
    print(f"\n=== Summary ===")
    print(f"Total active literals: {len(active_literals)}")
    print(f"Categories found: {len(categories)}")
    for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  {category}: {count}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced string literals documentation generator')
    parser.add_argument('--root', default='.', help='Root directory to scan')
    parser.add_argument('--output', default='SPEC/generated', help='Output directory for markdown files')
    parser.add_argument('--dirs', nargs='+', help='Directories to scan (default: app, frontend, auth_service, scripts, netra_backend)')
    parser.add_argument('--include-tests', action='store_true', help='Include test directories')
    
    args = parser.parse_args()
    
    # Resolve paths
    root_dir = Path(args.root).resolve()
    output_dir = root_dir / args.output
    
    # Determine directories to scan
    include_dirs = args.dirs
    if include_dirs is None:
        include_dirs = ['app', 'frontend', 'auth_service', 'scripts', 'netra_backend']
        if args.include_tests:
            include_dirs.extend(['tests', '__tests__'])
    
    try:
        scan_and_generate_docs(root_dir, output_dir, include_dirs)
        print(f"\n[SUCCESS] Enhanced documentation generated successfully!")
        print(f"Main index: {output_dir / 'string_literals_index.md'}")
        print(f"Category files: {output_dir / 'string_literals'}/")
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] Failed to generate documentation: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())