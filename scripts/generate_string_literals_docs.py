#!/usr/bin/env python3
"""
Generate Markdown Documentation for String Literals
Integration script to create human-readable documentation from string literals index.
"""

import json
import sys
from pathlib import Path
from typing import List

# Add string_literals package to path
sys.path.insert(0, str(Path(__file__).parent / "string_literals"))

from string_literals.categorizer_enhanced import CategorizedLiteral
from string_literals.markdown_reporter import generate_markdown_docs


def load_from_json_index(json_path: Path) -> List[CategorizedLiteral]:
    """Load categorized literals from the existing JSON index."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    literals = []
    categories = data.get('categories', {})
    
    for category_name, category_data in categories.items():
        for literal_value, literal_info in category_data.get('literals', {}).items():
            # Extract file and line from first location
            locations = literal_info.get('locations', ['unknown:0'])
            first_location = locations[0]
            
            if ':' in first_location:
                file_path, line_str = first_location.rsplit(':', 1)
                try:
                    line_num = int(line_str)
                except ValueError:
                    line_num = 0
            else:
                file_path = first_location
                line_num = 0
            
            # Create CategorizedLiteral object
            # Note: The old JSON format doesn't have subcategory/confidence, so we'll estimate
            subcategory = literal_info.get('type', 'general')
            context = literal_info.get('context', '')
            
            # Estimate confidence based on category and type
            confidence = 0.8  # Default medium-high confidence
            if category_name in ['configuration', 'database', 'paths']:
                confidence = 0.9
            elif category_name == 'uncategorized':
                confidence = 0.3
                
            literal = CategorizedLiteral(
                value=literal_value,
                file=file_path,
                line=line_num,
                category=category_name,
                subcategory=subcategory,
                confidence=confidence,
                context=context,
                type_hint=subcategory
            )
            literals.append(literal)
    
    return literals


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate markdown documentation for string literals')
    parser.add_argument('--input', default='SPEC/generated/string_literals.json',
                        help='Input JSON file with string literals index')
    parser.add_argument('--output', default='SPEC/generated',
                        help='Output directory for markdown files')
    parser.add_argument('--enhanced', action='store_true',
                        help='Use enhanced categorization (requires re-scanning)')
    
    args = parser.parse_args()
    
    # Resolve paths
    root_dir = Path(__file__).parent.parent
    input_path = root_dir / args.input
    output_dir = root_dir / args.output
    
    print(f"Loading string literals from: {input_path}")
    
    if not input_path.exists():
        print(f"Error: Input file {input_path} does not exist")
        print("Run 'python scripts/scan_string_literals.py' first to generate the index")
        return 1
    
    # Load literals
    if args.enhanced:
        print("Enhanced mode is not yet implemented - using basic JSON loading")
        # TODO: In the future, this could re-scan with enhanced categorizer
    
    literals = load_from_json_index(input_path)
    print(f"Loaded {len(literals)} string literals")
    
    # Generate documentation
    print(f"Generating documentation in: {output_dir}")
    generate_markdown_docs(literals, output_dir)
    
    print("\n[SUCCESS] Markdown documentation generated successfully!")
    print(f"Main index: {output_dir / 'string_literals_index.md'}")
    print(f"Category files: {output_dir / 'string_literals'}/")
    
    return 0


if __name__ == '__main__':
    exit(main())