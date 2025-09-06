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
        self.critical_refs = {
            'MISSION_CRITICAL_NAMED_VALUES_INDEX.xml': 'Master index of ALL values that cause cascade failures',
            'CONFIG_REGRESSION_PREVENTION_PLAN.md': 'Config regression prevention strategies',
            'OAUTH_REGRESSION_ANALYSIS_20250905.md': 'OAuth configuration regression analysis',
            'docs/configuration_architecture.md': 'Complete configuration architecture'
        }
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
            result = {
                'valid': True,
                'value': value,
                'category': exact['category'],
                'locations': exact.get('locations', [])
            }
            
            # Add warnings for critical items
            if exact['category'] == 'critical_config':
                result['warning'] = 'CRITICAL CONFIG! See MISSION_CRITICAL_NAMED_VALUES_INDEX.xml before modifying!'
                result['cross_references'] = ['MISSION_CRITICAL_NAMED_VALUES_INDEX.xml', 'CONFIG_REGRESSION_PREVENTION_PLAN.md']
            elif exact['category'].startswith('critical_domain_'):
                env = exact['category'].replace('critical_domain_', '')
                result['warning'] = f'CRITICAL DOMAIN for {env} environment! Verify ALL references before changing!'
                result['environment'] = env
                result['cross_references'] = ['MISSION_CRITICAL_NAMED_VALUES_INDEX.xml']
                
            return result
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
            'categories': {},
            'critical_summary': {
                'critical_configs': 0,
                'critical_domains': {},
                'cross_references': self.index.get('metadata', {}).get('cross_references', {})
            }
        }
        
        for cat, data in self.index['categories'].items():
            stats['categories'][cat] = {
                'count': data['count'],
                'types': {}
            }
            
            # Count literals (no type field in new structure)
            stats['categories'][cat]['literals_count'] = len(data['literals'])
            
            # Track critical items
            if cat == 'critical_config':
                stats['critical_summary']['critical_configs'] = data['count']
            elif cat.startswith('critical_domain_'):
                env = cat.replace('critical_domain_', '')
                stats['critical_summary']['critical_domains'][env] = data['count']
                
        return stats
    
    def check_environment_config(self, environment: str) -> Dict[str, Any]:
        """Check if all required configs exist for an environment."""
        if 'critical_config_protection' not in self.index:
            return {
                'error': 'Index does not contain critical config protection data. Re-run scan_string_literals.py'
            }
            
        env_data = self.index['critical_config_protection']['environments'].get(environment)
        if not env_data:
            return {
                'error': f'Unknown environment: {environment}',
                'valid_environments': list(self.index['critical_config_protection']['environments'].keys())
            }
            
        # Check which required variables are present
        required_vars = env_data['required_variables']
        found_vars = []
        missing_vars = []
        
        for var in required_vars:
            if self.get_exact(var, 'critical_config'):
                found_vars.append(var)
            else:
                missing_vars.append(var)
                
        # Check domains
        expected_domains = env_data['expected_domains']
        found_domains = {}
        missing_domains = {}
        
        for key, domain in expected_domains.items():
            if self.get_exact(domain):
                found_domains[key] = domain
            else:
                missing_domains[key] = domain
                
        return {
            'environment': environment,
            'config_status': {
                'required_variables': len(required_vars),
                'found_variables': len(found_vars),
                'missing_variables': missing_vars
            },
            'domain_status': {
                'expected_domains': len(expected_domains),
                'found_domains': len(found_domains),
                'missing_domains': missing_domains
            },
            'health': 'HEALTHY' if not missing_vars and not missing_domains else 'CRITICAL',
            'cross_references': [
                'MISSION_CRITICAL_NAMED_VALUES_INDEX.xml',
                'CONFIG_REGRESSION_PREVENTION_PLAN.md'
            ]
        }

def main():
    """CLI interface for querying string literals."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Query string literals index with critical config protection')
    parser.add_argument('action', choices=['search', 'validate', 'list', 'stats', 'check-env', 'show-critical'],
                        help='Action to perform')
    parser.add_argument('value', nargs='?', help='Value to search/validate or environment to check')
    parser.add_argument('--category', '-c', help='Limit to specific category')
    parser.add_argument('--index', default='SPEC/generated/string_literals.json',
                        help='Path to index file')
    parser.add_argument('--environment', '-e', choices=['local', 'development', 'staging', 'production'],
                        help='Environment to check (for check-env action)')
    
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
                print(f"\n  {r['value']} ({r['category']})")
                for loc in r.get('locations', [])[:3]:
                    print(f"    - {loc}")
                if len(r.get('locations', [])) > 3:
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
            print(f"[VALID] '{result['value']}'")
            print(f"  Category: {result['category']}")
            print(f"  Used in {len(result['locations'])} locations")
        else:
            print(f"[INVALID] '{result['value']}'")
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
        
        # Show critical summary
        if stats.get('critical_summary'):
            print(f"\nCRITICAL CONFIG SUMMARY:")
            print(f"  Critical configs: {stats['critical_summary']['critical_configs']}")
            if stats['critical_summary']['critical_domains']:
                print(f"  Critical domains by environment:")
                for env, count in stats['critical_summary']['critical_domains'].items():
                    print(f"    - {env}: {count} domains")
            print(f"\n  Cross-references:")
            for ref, desc in stats['critical_summary'].get('cross_references', {}).items():
                print(f"    - {ref}")
        
        print(f"\nBy category:")
        for cat, data in stats['categories'].items():
            marker = ' [CRITICAL]' if cat.startswith('critical_') else ''
            print(f"\n  {cat}{marker}: {data['count']} literals")
            for type_name, count in sorted(data['types'].items()):
                print(f"    - {type_name}: {count}")
                
    elif args.action == 'check-env':
        env = args.value or args.environment
        if not env:
            print("Error: check-env requires an environment (local/development/staging/production)")
            return 1
            
        result = query.check_environment_config(env)
        
        if 'error' in result:
            print(f"Error: {result['error']}")
            if 'valid_environments' in result:
                print(f"Valid environments: {', '.join(result['valid_environments'])}")
            return 1
            
        print(f"Environment Check: {result['environment']}")
        print(f"="*40)
        print(f"Status: {result['health']}")
        
        print(f"\nConfiguration Variables:")
        print(f"  Required: {result['config_status']['required_variables']}")
        print(f"  Found: {result['config_status']['found_variables']}")
        if result['config_status']['missing_variables']:
            print(f"  MISSING: {', '.join(result['config_status']['missing_variables'])}")
            
        print(f"\nDomain Configuration:")
        print(f"  Expected: {result['domain_status']['expected_domains']}")
        print(f"  Found: {result['domain_status']['found_domains']}")
        if result['domain_status']['missing_domains']:
            print(f"  MISSING:")
            for key, domain in result['domain_status']['missing_domains'].items():
                print(f"    - {key}: {domain}")
                
        print(f"\nCross-references:")
        for ref in result['cross_references']:
            print(f"  - {ref}")
            
    elif args.action == 'show-critical':
        print("CRITICAL CONFIGURATION VALUES")
        print("="*40)
        print("WARNING: These values can cause CASCADE FAILURES if modified incorrectly!\n")
        
        # Show critical configs
        critical_cat = query.index['categories'].get('critical_config', {})
        if critical_cat:
            print("Critical Environment Variables:")
            for literal in sorted(critical_cat.get('literals', {}).keys()):
                print(f"  - {literal}")
                
        # Show critical domains by environment  
        print("\nCritical Domains by Environment:")
        for cat_name in sorted(query.index['categories'].keys()):
            if cat_name.startswith('critical_domain_'):
                env = cat_name.replace('critical_domain_', '')
                print(f"\n  {env.upper()}:")
                cat_data = query.index['categories'][cat_name]
                for domain in sorted(cat_data.get('literals', {}).keys()):
                    print(f"    - {domain}")
                    
        print("\nIMPORTANT: Always check MISSION_CRITICAL_NAMED_VALUES_INDEX.xml before modifying!")
                
    return 0

if __name__ == '__main__':
    exit(main())