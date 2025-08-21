#!/usr/bin/env python3
"""
String Literals Query Tool for Netra Platform
Allows querying and validation of string literals from the index.
"""

import json
import sys
from difflib import get_close_matches
from pathlib import Path
from typing import Any, Dict, List, Optional


class StringLiteralQuery:
    """Query interface for string literals index."""
    
    def __init__(self, index_path: str = 'SPEC/generated/string_literals.json'):
        self.index_path = Path(index_path)
        self.index: Dict[str, Any] = {}
        self.load_index()
        
    def load_index(self) -> None:
        """Load the string literals index."""
        if not self.index_path.exists():
            print(f"Index file not found at {self.index_path}")
            print("Run 'python scripts/scan_string_literals.py' first to generate the index.")
            sys.exit(1)
            
        with open(self.index_path, 'r', encoding='utf-8') as f:
            self.index = json.load(f)
            
    def search(self, query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for literals matching the query."""
        results = []
        categories_to_search = [category] if category else self.index['categories'].keys()
        
        for cat in categories_to_search:
            if cat not in self.index['categories']:
                continue
                
            cat_data = self.index['categories'][cat]
            for value, entry in cat_data['literals'].items():
                if query.lower() in value.lower():
                    result = entry.copy()
                    result['category'] = cat
                    results.append(result)
                    
        return results
        
    def get_exact(self, value: str, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get exact match for a literal value."""
        categories_to_search = [category] if category else self.index['categories'].keys()
        
        for cat in categories_to_search:
            if cat not in self.index['categories']:
                continue
                
            cat_data = self.index['categories'][cat]
            if value in cat_data['literals']:
                result = cat_data['literals'][value].copy()
                result['category'] = cat
                return result
                
        return None
        
    def suggest(self, value: str, category: Optional[str] = None, n: int = 3) -> List[str]:
        """Suggest similar literals if exact match not found."""
        all_values = []
        categories_to_search = [category] if category else self.index['categories'].keys()
        
        for cat in categories_to_search:
            if cat not in self.index['categories']:
                continue
                
            cat_data = self.index['categories'][cat]
            all_values.extend(cat_data['literals'].keys())
            
        return get_close_matches(value, all_values, n=n)
        
    def validate(self, value: str, category: Optional[str] = None) -> Dict[str, Any]:
        """Validate if a literal exists in the index."""
        exact = self.get_exact(value, category)
        
        if exact:
            return {
                'valid': True,
                'value': value,
                'category': exact['category'],
                'type': exact['type'],
                'locations': exact['locations']
            }
        else:
            suggestions = self.suggest(value, category)
            return {
                'valid': False,
                'value': value,
                'suggestions': suggestions,
                'message': f"Literal '{value}' not found in index."
            }
            
    def list_category(self, category: str) -> List[str]:
        """List all literals in a category."""
        if category not in self.index['categories']:
            return []
            
        return list(self.index['categories'][category]['literals'].keys())
        
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the index."""
        stats = {
            'total_literals': self.index['metadata']['total_literals'],
            'categories': {}
        }
        
        for cat, data in self.index['categories'].items():
            stats['categories'][cat] = {
                'count': data['count'],
                'types': {}
            }
            
            # Count by type
            for entry in data['literals'].values():
                entry_type = entry['type']
                if entry_type not in stats['categories'][cat]['types']:
                    stats['categories'][cat]['types'][entry_type] = 0
                stats['categories'][cat]['types'][entry_type] += 1
                
        return stats

def main():
    """CLI interface for querying string literals."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Query string literals index')
    parser.add_argument('action', choices=['search', 'validate', 'list', 'stats'],
                        help='Action to perform')
    parser.add_argument('value', nargs='?', help='Value to search/validate')
    parser.add_argument('--category', '-c', help='Limit to specific category')
    parser.add_argument('--index', default='SPEC/generated/string_literals.json',
                        help='Path to index file')
    
    args = parser.parse_args()
    
    query = StringLiteralQuery(args.index)
    
    if args.action == 'search':
        if not args.value:
            print("Error: search requires a value")
            return 1
            
        results = query.search(args.value, args.category)
        if results:
            print(f"Found {len(results)} matches:")
            for r in results:
                print(f"\n  {r['value']} ({r['category']}/{r['type']})")
                for loc in r['locations'][:3]:
                    print(f"    - {loc}")
                if len(r['locations']) > 3:
                    print(f"    ... and {len(r['locations']) - 3} more")
        else:
            print("No matches found")
            suggestions = query.suggest(args.value, args.category)
            if suggestions:
                print(f"Did you mean: {', '.join(suggestions)}?")
                
    elif args.action == 'validate':
        if not args.value:
            print("Error: validate requires a value")
            return 1
            
        result = query.validate(args.value, args.category)
        if result['valid']:
            print(f"✓ Valid: '{result['value']}'")
            print(f"  Category: {result['category']}")
            print(f"  Type: {result['type']}")
            print(f"  Used in {len(result['locations'])} locations")
        else:
            print(f"✗ Invalid: '{result['value']}'")
            if result['suggestions']:
                print(f"  Did you mean: {', '.join(result['suggestions'])}?")
                
    elif args.action == 'list':
        if not args.category:
            print("Available categories:")
            for cat in query.index['categories'].keys():
                count = query.index['categories'][cat]['count']
                print(f"  - {cat} ({count} literals)")
        else:
            literals = query.list_category(args.category)
            if literals:
                print(f"Literals in '{args.category}':")
                for lit in sorted(literals)[:20]:
                    print(f"  - {lit}")
                if len(literals) > 20:
                    print(f"  ... and {len(literals) - 20} more")
            else:
                print(f"Category '{args.category}' not found")
                
    elif args.action == 'stats':
        stats = query.get_stats()
        print(f"String Literals Index Statistics")
        print(f"================================")
        print(f"Total literals: {stats['total_literals']}")
        print(f"\nBy category:")
        for cat, data in stats['categories'].items():
            print(f"\n  {cat}: {data['count']} literals")
            for type_name, count in sorted(data['types'].items()):
                print(f"    - {type_name}: {count}")
                
    return 0

if __name__ == '__main__':
    exit(main())