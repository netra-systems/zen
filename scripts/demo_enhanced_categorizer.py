#!/usr/bin/env python3
"""
Demonstration of Enhanced String Literal Categorizer
Shows comparison between old and new categorization approaches.
"""

import json
from pathlib import Path
from typing import Dict, List

from string_literals import scan_directory
from string_literals.categorizer_enhanced import (
    EnhancedStringLiteralCategorizer,
    print_categorization_report
)


def load_existing_index(filepath: str) -> Dict:
    """Load the existing string literals index."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Existing index not found at {filepath}")
        return {}


def compare_categorization_approaches(sample_size: int = 100) -> None:
    """Compare old vs new categorization approaches."""
    print("=== Enhanced String Literal Categorizer Demo ===\n")
    
    # Load existing index for comparison
    existing_index = load_existing_index('SPEC/generated/string_literals.json')
    
    if existing_index:
        total_existing = existing_index['metadata']['total_literals']
        uncategorized_existing = existing_index['categories'].get('uncategorized', {}).get('count', 0)
        categorized_existing = total_existing - uncategorized_existing
        
        print(f"Existing Index Statistics:")
        print(f"  Total literals: {total_existing}")
        print(f"  Categorized: {categorized_existing} ({categorized_existing/total_existing*100:.1f}%)")
        print(f"  Uncategorized: {uncategorized_existing} ({uncategorized_existing/total_existing*100:.1f}%)")
        print()
    
    # Scan a sample of files with the enhanced categorizer
    print(f"Scanning sample files with enhanced categorizer...")
    
    root_dir = Path('.')
    sample_dirs = ['netra_backend/app', 'frontend', 'scripts']
    
    all_literals = []
    for dir_name in sample_dirs:
        dir_path = root_dir / dir_name
        if dir_path.exists():
            print(f"  Scanning {dir_name}...")
            literals = scan_directory(dir_path, root_dir, {'node_modules', '__pycache__', '.git'})
            all_literals.extend(literals[:sample_size // len(sample_dirs)])  # Limit sample
    
    print(f"Found {len(all_literals)} literals in sample\n")
    
    # Categorize with enhanced categorizer
    categorizer = EnhancedStringLiteralCategorizer()
    categorized_literals = categorizer.categorize_batch(all_literals)
    
    # Print enhanced categorization report
    print_categorization_report(categorized_literals)
    
    # Show some example categorizations
    print(f"\n=== Sample Enhanced Categorizations ===")
    
    # Group by category for display
    by_category = {}
    for literal in categorized_literals[:20]:  # Show first 20
        category = literal.full_category
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(literal)
    
    for category, literals in sorted(by_category.items()):
        print(f"\n{category}:")
        for literal in literals[:3]:  # Show max 3 per category
            print(f"  '{literal.value[:50]}...' (confidence: {literal.confidence:.2f})")
            if literal.context:
                print(f"    Context: {literal.context}")
    
    # Improvement analysis
    enhanced_stats = categorizer.get_categorization_stats(categorized_literals)
    enhanced_uncategorized_rate = enhanced_stats['uncategorized'] / enhanced_stats['total'] * 100
    
    print(f"\n=== Improvement Analysis ===")
    if existing_index:
        existing_uncategorized_rate = uncategorized_existing / total_existing * 100
        improvement = existing_uncategorized_rate - enhanced_uncategorized_rate
        print(f"Uncategorized rate improvement: {improvement:.1f}% (from {existing_uncategorized_rate:.1f}% to {enhanced_uncategorized_rate:.1f}%)")
    
    print(f"Average confidence: {enhanced_stats['avg_confidence']:.3f}")
    print(f"High confidence categorizations: {enhanced_stats['by_confidence']['high']/enhanced_stats['total']*100:.1f}%")


def categorize_specific_examples() -> None:
    """Demonstrate categorization of specific challenging examples."""
    print("\n=== Challenging Examples Demo ===")
    
    # Examples that are commonly uncategorized
    challenging_examples = [
        "192.168.1.1",  # IP address
        "application/json",  # MIME type
        "v1.2.3",  # Version number
        "ab12cd34ef56",  # Hash/ID
        "--verbose",  # CLI argument
        "user_session_timeout",  # Config parameter
        "on_message_received",  # Event handler
        "auth_token_expired",  # Event type
        "request_duration_seconds",  # Metric name
        "DEBUG: Starting service",  # Log message
        "User not found",  # Error message
        "SELECT id, name FROM users WHERE active = true",  # Complex SQL
        "/api/v2/users/{user_id}/messages",  # Parameterized API path
        "{timestamp}: {level} - {message}",  # Log format template
    ]
    
    categorizer = EnhancedStringLiteralCategorizer()
    
    print("Categorizing challenging examples:")
    for example in challenging_examples:
        # Create a dummy RawLiteral for testing
        from string_literals.scanner_core import RawLiteral
        raw_literal = RawLiteral(example, "demo.py", 1, None, "demo_function")
        result = categorizer.categorize(raw_literal)
        
        print(f"  '{example[:40]}...'")
        print(f"    -> {result.full_category} (confidence: {result.confidence:.2f})")


if __name__ == '__main__':
    compare_categorization_approaches(200)
    categorize_specific_examples()