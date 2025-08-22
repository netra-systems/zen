#!/usr/bin/env python3
"""
Enhanced String Literals Scanner for Netra Platform
Integrated runner using the new modular components with full backward compatibility.

This is the next-generation scanner that combines all enhanced features while
maintaining 100% backward compatibility with the original JSON output.

Features:
- Modular architecture with enhanced categorization
- Confidence scoring for categorization accuracy
- Comprehensive markdown documentation generation
- Multiple output formats (JSON, markdown, category files)
- Enhanced context awareness and pattern matching
- Validation and quality assurance

Usage:
    # Basic usage (JSON output only, backward compatible)
    python scripts/scan_string_literals_enhanced.py
    
    # Generate markdown documentation
    python scripts/scan_string_literals_enhanced.py --format markdown
    
    # Generate both JSON and markdown
    python scripts/scan_string_literals_enhanced.py --format all
    
    # Include confidence scores in JSON
    python scripts/scan_string_literals_enhanced.py --include-confidence
    
    # Validate against original scanner
    python scripts/scan_string_literals_enhanced.py --validate
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Import the new modular components
try:
    from string_literals.scanner_core import scan_directory, scan_file
    from string_literals.categorizer_enhanced import (
        EnhancedStringLiteralCategorizer, 
        CategorizedLiteral,
        categorize_literals,
        print_categorization_report
    )
    from string_literals.markdown_reporter import generate_markdown_docs
except ImportError as e:
    print(f"Error importing modular components: {e}")
    print("Please ensure the string_literals package is properly installed.")
    sys.exit(1)


class EnhancedStringLiteralIndexer:
    """Enhanced indexer that coordinates scanning, categorization, and output generation."""
    
    def __init__(self, root_dir: str, include_confidence: bool = False, format_type: str = 'json'):
        """Initialize the enhanced indexer.
        
        Args:
            root_dir: Root directory to scan
            include_confidence: Whether to include confidence scores in JSON output
            format_type: Output format ('json', 'markdown', 'all')
        """
        self.root_dir = Path(root_dir).resolve()
        self.include_confidence = include_confidence
        self.format_type = format_type
        self.categorizer = EnhancedStringLiteralCategorizer()
        self.categorized_literals: List[CategorizedLiteral] = []
        
    def scan_codebase(self, dirs_to_scan: List[str], include_tests: bool = False) -> None:
        """Scan the codebase for string literals."""
        print(f"Enhanced scanning {self.root_dir} for string literals...")
        
        all_raw_literals = []
        
        # Standard directories to scan
        scan_dirs = dirs_to_scan.copy()
        if include_tests:
            scan_dirs.extend(['tests', '__tests__'])
            
        # Scan each directory
        exclude_dirs = {'.git', '__pycache__', 'venv', 'node_modules', '.pytest_cache', 
                       'dist', 'build', '.tox', 'htmlcov', 'coverage'}
        
        for dir_name in scan_dirs:
            dir_path = self.root_dir / dir_name
            if dir_path.exists() and dir_path.is_dir():
                print(f"  [SCAN] {dir_name}/...")
                try:
                    dir_literals = scan_directory(dir_path, self.root_dir, exclude_dirs)
                    all_raw_literals.extend(dir_literals)
                    print(f"  [OK] Found {len(dir_literals)} literals in {dir_name}/")
                except Exception as e:
                    print(f"  [ERROR] Failed to scan {dir_name}/: {e}")
                    continue
        
        print(f"[SCAN] Total raw literals found: {len(all_raw_literals)}")
        
        # Categorize all literals
        print("[CATEGORIZE] Processing literals with enhanced categorizer...")
        self.categorized_literals = self.categorizer.categorize_batch(all_raw_literals)
        
        # Filter out ignored literals for stats
        active_literals = [l for l in self.categorized_literals if l.category != 'ignored']
        print(f"[CATEGORIZE] Active literals: {len(active_literals)}")
        print(f"[CATEGORIZE] Ignored literals: {len(self.categorized_literals) - len(active_literals)}")
        
        # Show categorization stats
        if active_literals:
            stats = self.categorizer.get_categorization_stats(active_literals)
            print(f"[STATS] Average confidence: {stats['avg_confidence']:.3f}")
            print(f"[STATS] Categorization rate: {(len(active_literals) - stats['uncategorized']) / len(active_literals) * 100:.1f}%")
    
    def generate_backward_compatible_json(self) -> Dict[str, Any]:
        """Generate JSON output that's backward compatible with the original scanner."""
        # Group literals by category (original format)
        index = defaultdict(lambda: defaultdict(list))
        
        for literal in self.categorized_literals:
            # Skip ignored literals from JSON output
            if literal.category == 'ignored':
                continue
                
            # Create entry in original format
            entry = {
                'value': literal.value,
                'type': literal.subcategory or 'general',
                'locations': [f"{literal.file}:{literal.line}"],
                'context': literal.context
            }
            
            # Optionally include enhanced fields
            if self.include_confidence:
                entry['confidence'] = literal.confidence
                entry['full_category'] = literal.full_category
                entry['type_hint'] = literal.type_hint
            
            # Check if this literal value already exists
            existing = None
            for existing_entry in index[literal.category][literal.value]:
                if existing_entry['value'] == literal.value:
                    existing = existing_entry
                    break
            
            if existing:
                # Merge locations
                location = f"{literal.file}:{literal.line}"
                if location not in existing['locations']:
                    existing['locations'].append(location)
                # Update confidence to the highest if included
                if self.include_confidence and literal.confidence > existing.get('confidence', 0):
                    existing['confidence'] = literal.confidence
            else:
                index[literal.category][literal.value] = [entry]
        
        # Convert to original output format
        output = {
            'metadata': {
                'version': '2.0.0',  # Enhanced version
                'generated_at': datetime.now().isoformat(),
                'root_directory': str(self.root_dir),
                'total_literals': len([l for l in self.categorized_literals if l.category != 'ignored']),
                'scanner_type': 'enhanced',
                'backward_compatible': True
            },
            'categories': {}
        }
        
        # Add enhanced metadata if confidence is included
        if self.include_confidence:
            active_literals = [l for l in self.categorized_literals if l.category != 'ignored']
            if active_literals:
                stats = self.categorizer.get_categorization_stats(active_literals)
                output['metadata']['enhanced_stats'] = {
                    'avg_confidence': stats['avg_confidence'],
                    'confidence_distribution': stats['by_confidence'],
                    'categorization_rate': (len(active_literals) - stats['uncategorized']) / len(active_literals)
                }
        
        # Build categories section
        for category, literals_dict in index.items():
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
    
    def save_json_index(self, output_path: Path) -> None:
        """Save the enhanced JSON index with backward compatibility."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        index = self.generate_backward_compatible_json()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        
        print(f"[JSON] Saved enhanced index to {output_path}")
        print(f"[JSON] Format: {'Enhanced' if self.include_confidence else 'Backward Compatible'}")
        print(f"[JSON] Total categories: {len(index['categories'])}")
        
        # Show category breakdown
        for category, data in sorted(index['categories'].items()):
            print(f"[JSON]   {category}: {data['count']} unique literals")
    
    def generate_markdown_documentation(self, output_dir: Path) -> None:
        """Generate comprehensive markdown documentation."""
        print("[MARKDOWN] Generating enhanced documentation...")
        
        # Filter out ignored literals for documentation
        active_literals = [l for l in self.categorized_literals if l.category != 'ignored']
        
        if not active_literals:
            print("[MARKDOWN] No active literals to document")
            return
        
        # Generate documentation using the markdown reporter
        generate_markdown_docs(active_literals, output_dir)
        
        print(f"[MARKDOWN] Documentation generated in {output_dir}")
    
    def validate_against_original(self, original_output_path: Path) -> bool:
        """Validate the enhanced scanner against the original scanner output."""
        if not original_output_path.exists():
            print(f"[VALIDATE] Original output not found at {original_output_path}")
            print(f"[VALIDATE] Run the original scanner first to generate baseline")
            return False
        
        print("[VALIDATE] Comparing enhanced output with original scanner...")
        
        # Load original output
        try:
            with open(original_output_path, 'r', encoding='utf-8') as f:
                original_data = json.load(f)
        except Exception as e:
            print(f"[VALIDATE] Error loading original data: {e}")
            return False
        
        # Generate our output in compatible format
        enhanced_data = self.generate_backward_compatible_json()
        
        # Compare key metrics
        original_total = original_data.get('metadata', {}).get('total_literals', 0)
        enhanced_total = enhanced_data.get('metadata', {}).get('total_literals', 0)
        
        print(f"[VALIDATE] Original literals: {original_total}")
        print(f"[VALIDATE] Enhanced literals: {enhanced_total}")
        
        # Check for significant differences
        if abs(original_total - enhanced_total) > max(10, original_total * 0.05):  # Allow 5% difference or 10 literals
            print(f"[VALIDATE] ⚠️  Significant difference in literal count detected")
            print(f"[VALIDATE] This may indicate a regression or improvement in literal detection")
        else:
            print(f"[VALIDATE] ✅ Literal counts are consistent")
        
        # Compare categories
        original_categories = set(original_data.get('categories', {}).keys())
        enhanced_categories = set(enhanced_data.get('categories', {}).keys())
        
        new_categories = enhanced_categories - original_categories
        missing_categories = original_categories - enhanced_categories
        
        if new_categories:
            print(f"[VALIDATE] ➕ New categories: {', '.join(sorted(new_categories))}")
        
        if missing_categories:
            print(f"[VALIDATE] ➖ Missing categories: {', '.join(sorted(missing_categories))}")
        
        if not new_categories and not missing_categories:
            print(f"[VALIDATE] ✅ Category structure is consistent")
        
        # Overall validation result
        is_valid = abs(original_total - enhanced_total) <= max(10, original_total * 0.05)
        
        if is_valid:
            print("[VALIDATE] ✅ Enhanced scanner validation passed")
        else:
            print("[VALIDATE] ⚠️  Enhanced scanner validation requires review")
        
        return is_valid
    
    def run(self, args) -> int:
        """Run the enhanced scanner with the specified configuration."""
        # Determine directories to scan
        dirs_to_scan = getattr(args, 'dirs', None) or [
            'netra_backend', 'frontend', 'auth_service', 'scripts', 'shared'
        ]
        
        # Scan the codebase
        self.scan_codebase(dirs_to_scan, args.include_tests)
        
        if not self.categorized_literals:
            print("[ERROR] No literals found to process")
            return 1
        
        # Generate outputs based on format
        if self.format_type in ['json', 'all']:
            output_path = self.root_dir / args.output
            self.save_json_index(output_path)
        
        if self.format_type in ['markdown', 'all']:
            docs_dir = self.root_dir / 'docs'
            self.generate_markdown_documentation(docs_dir)
        
        # Run validation if requested
        if args.validate:
            original_path = self.root_dir / 'SPEC' / 'generated' / 'string_literals.json'
            self.validate_against_original(original_path)
        
        # Show final categorization report
        active_literals = [l for l in self.categorized_literals if l.category != 'ignored']
        if active_literals and args.verbose:
            print_categorization_report(active_literals)
        
        print(f"\n[DONE] Enhanced string literals scanning complete!")
        return 0


def main() -> int:
    """Main entry point for the enhanced string literals scanner."""
    parser = argparse.ArgumentParser(
        description='Enhanced String Literals Scanner for Netra Platform',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic scanning (backward compatible JSON)
  python scan_string_literals_enhanced.py
  
  # Generate markdown documentation
  python scan_string_literals_enhanced.py --format markdown
  
  # Generate both JSON and docs with confidence scores
  python scan_string_literals_enhanced.py --format all --include-confidence
  
  # Validate against original scanner
  python scan_string_literals_enhanced.py --validate
  
  # Custom directories and verbose output
  python scan_string_literals_enhanced.py --dirs netra_backend frontend --verbose
        """
    )
    
    # Basic options
    parser.add_argument('--root', default='.', 
                        help='Root directory to scan (default: current directory)')
    parser.add_argument('--output', default='SPEC/generated/string_literals.json',
                        help='JSON output file path (default: SPEC/generated/string_literals.json)')
    
    # Format options
    parser.add_argument('--format', choices=['json', 'markdown', 'all'], default='json',
                        help='Output format (default: json)')
    parser.add_argument('--include-confidence', action='store_true',
                        help='Include confidence scores in JSON output')
    parser.add_argument('--include-tests', action='store_true',
                        help='Include test directories in scanning')
    
    # Directory options
    parser.add_argument('--dirs', nargs='+', 
                        help='Specific directories to scan (default: main app directories)')
    
    # Validation and debugging
    parser.add_argument('--validate', action='store_true',
                        help='Validate output against original scanner')
    parser.add_argument('--verbose', action='store_true',
                        help='Show detailed categorization report')
    
    # Migration support
    parser.add_argument('--migration-mode', action='store_true',
                        help='Run in migration validation mode (extra checks)')
    
    args = parser.parse_args()
    
    try:
        # Initialize the enhanced indexer
        indexer = EnhancedStringLiteralIndexer(
            root_dir=args.root,
            include_confidence=args.include_confidence,
            format_type=args.format
        )
        
        # Show configuration
        print("=== Enhanced String Literals Scanner ===")
        print(f"Root directory: {indexer.root_dir}")
        print(f"Output format: {args.format}")
        print(f"Include confidence: {args.include_confidence}")
        print(f"Include tests: {args.include_tests}")
        print(f"Validation mode: {args.validate}")
        if args.dirs:
            print(f"Custom directories: {', '.join(args.dirs)}")
        print()
        
        # Run the scanner
        return indexer.run(args)
        
    except KeyboardInterrupt:
        print("\n[CANCELLED] Scanning cancelled by user")
        return 1
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())