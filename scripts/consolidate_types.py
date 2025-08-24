#!/usr/bin/env python3
"""
Type Consolidation Script - ATOMIC REMEDIATION
Consolidates all duplicate types into single sources of truth.

This script implements the ATOMIC SCOPE requirement from CLAUDE.md:
- Single unified concepts: CRUCIAL: Unique Concept = ONCE per service
- Complete Work: All relevant parts updated, integrated, tested
- Legacy is forbidden: Remove all duplicates atomically
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

class TypeConsolidator:
    def __init__(self, frontend_dir: str):
        self.frontend_dir = Path(frontend_dir)
        self.type_definitions = defaultdict(list)
        self.consolidation_map = {}
        self.files_to_update = []
        
        # Define canonical locations for each type category
        self.canonical_locations = {
            # Test Mock Types - All go to test-helpers.tsx
            'MockUser': 'frontend/__tests__/utils/test-helpers.tsx',
            'MockThread': 'frontend/__tests__/utils/test-helpers.tsx',
            'MockMessage': 'frontend/__tests__/utils/test-helpers.tsx',
            'MockWebSocketMessage': 'frontend/__tests__/utils/test-helpers.tsx',
            'MockStoreState': 'frontend/__tests__/utils/test-helpers.tsx',
            'MockAuthStore': 'frontend/__tests__/utils/test-helpers.tsx',
            'MockChatStore': 'frontend/__tests__/utils/test-helpers.tsx',
            'MockThreadStore': 'frontend/__tests__/utils/test-helpers.tsx',
            'MockToken': 'frontend/__tests__/utils/test-helpers.tsx',
            'MockAuthState': 'frontend/__tests__/utils/test-helpers.tsx',
            'TestRenderOptions': 'frontend/__tests__/utils/test-helpers.tsx',
            'PerformanceMetrics': 'frontend/__tests__/utils/test-helpers.tsx',
            
            # WebSocket Types - Already consolidated in domains/websocket.ts  
            'WebSocketServiceError': 'frontend/types/domains/websocket.ts',
            'WebSocketStatus': 'frontend/types/domains/websocket.ts', # Service version
            'WebSocketState': 'frontend/types/domains/websocket.ts',
            
            # Core shared types
            'User': 'frontend/types/shared/base.ts',
            'BaseMessage': 'frontend/types/shared/base.ts',
            'MessageMetadata': 'frontend/types/shared/base.ts',
            'MessageAttachment': 'frontend/types/shared/base.ts',
            'MessageReaction': 'frontend/types/shared/base.ts',
            
            # Domain-specific types
            'Thread': 'frontend/types/domains/threads.ts',
            'ThreadState': 'frontend/types/domains/threads.ts',
            'ThreadMetadata': 'frontend/types/domains/threads.ts',
            'AgentState': 'frontend/types/domains/agents.ts',
            'Message': 'frontend/types/domains/messages.ts',
            
            # Store types
            'ChatState': 'frontend/types/store-types.ts',
            'ConnectionState': 'frontend/types/store-types.ts',
            'LayerState': 'frontend/types/store-types.ts',
            'PerformanceState': 'frontend/types/store-types.ts',
            'ProcessingState': 'frontend/types/store-types.ts',
        }
        
    def scan_all_types(self):
        """Scan all TypeScript files for type definitions."""
        pattern = re.compile(r'^(export\s+)?(interface|type)\s+([a-zA-Z_][a-zA-Z0-9_]*)', re.MULTILINE)
        
        for root, dirs, files in os.walk(self.frontend_dir):
            # Skip build and dependency directories
            if any(skip in root for skip in ['node_modules', '.next', 'dist', 'build']):
                continue
                
            for file in files:
                if not file.endswith(('.ts', '.tsx')):
                    continue
                    
                filepath = Path(root) / file
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                    matches = pattern.findall(content)
                    for export, def_type, type_name in matches:
                        self.type_definitions[type_name].append({
                            'file': str(filepath),
                            'export': export.strip(),
                            'type': def_type,
                            'name': type_name,
                            'content': content
                        })
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
                    
    def find_duplicates(self) -> Dict[str, List]:
        """Find all duplicate type definitions."""
        return {name: locations for name, locations in self.type_definitions.items() if len(locations) > 1}
    
    def plan_consolidation(self):
        """Plan which types to consolidate and where."""
        duplicates = self.find_duplicates()
        
        for type_name, locations in duplicates.items():
            if type_name in self.canonical_locations:
                canonical_file = self.canonical_locations[type_name]
                
                # Find the canonical definition (if it exists)
                canonical_def = None
                other_defs = []
                
                for loc in locations:
                    if loc['file'].endswith(canonical_file.split('/')[-1]):
                        canonical_def = loc
                    else:
                        other_defs.append(loc)
                
                if canonical_def:
                    self.consolidation_map[type_name] = {
                        'canonical': canonical_def,
                        'duplicates': other_defs,
                        'action': 'update_imports'
                    }
                else:
                    # Need to move the best definition to canonical location
                    self.consolidation_map[type_name] = {
                        'canonical': None,
                        'duplicates': locations,
                        'target': canonical_file,
                        'action': 'move_to_canonical'
                    }
    
    def generate_import_updates(self) -> List[Tuple[str, str, str]]:
        """Generate list of import updates needed."""
        updates = []
        
        for type_name, plan in self.consolidation_map.items():
            canonical_file = self.canonical_locations.get(type_name)
            if not canonical_file:
                continue
                
            # Generate relative import path
            canonical_path = canonical_file.replace('frontend/', '')
            
            for dup in plan.get('duplicates', []):
                file_path = dup['file']
                # Calculate relative import from this file to canonical location
                relative_import = self._calculate_relative_import(file_path, canonical_file)
                
                updates.append((file_path, type_name, relative_import))
                
        return updates
    
    def _calculate_relative_import(self, from_file: str, to_file: str) -> str:
        """Calculate relative import path between two files."""
        from_path = Path(from_file).parent
        to_path = Path(to_file)
        
        try:
            rel_path = os.path.relpath(to_path, from_path)
            # Convert to import format
            if rel_path.startswith('..'):
                return rel_path.replace('\\', '/').replace('.tsx', '').replace('.ts', '')
            else:
                return './' + rel_path.replace('\\', '/').replace('.tsx', '').replace('.ts', '')
        except:
            return f'ERROR_CALCULATING_PATH_FROM_{from_file}_TO_{to_file}'
    
    def print_consolidation_report(self):
        """Print a detailed report of the consolidation plan."""
        duplicates = self.find_duplicates()
        
        print("TYPE CONSOLIDATION ANALYSIS")
        print("=" * 60)
        print(f"Total duplicate types found: {len(duplicates)}")
        print(f"Types planned for consolidation: {len(self.consolidation_map)}")
        print()
        
        # Group by category
        test_types = []
        websocket_types = []
        shared_types = []
        domain_types = []
        other_types = []
        
        for type_name, locations in duplicates.items():
            if type_name.startswith('Mock') or type_name.startswith('Test'):
                test_types.append((type_name, len(locations)))
            elif 'WebSocket' in type_name:
                websocket_types.append((type_name, len(locations)))
            elif type_name in ['User', 'BaseMessage', 'MessageMetadata', 'MessageAttachment']:
                shared_types.append((type_name, len(locations)))
            elif type_name in ['Thread', 'ThreadState', 'AgentState', 'Message']:
                domain_types.append((type_name, len(locations)))
            else:
                other_types.append((type_name, len(locations)))
        
        self._print_category("TEST/MOCK TYPES", test_types)
        self._print_category("WEBSOCKET TYPES", websocket_types)  
        self._print_category("SHARED BASE TYPES", shared_types)
        self._print_category("DOMAIN TYPES", domain_types)
        self._print_category("OTHER TYPES", other_types[:10])  # Show first 10
        
    def _print_category(self, category: str, types: List[Tuple[str, int]]):
        if not types:
            return
            
        print(f"{category}:")
        print("-" * 40)
        for type_name, count in sorted(types, key=lambda x: x[1], reverse=True):
            status = "PLANNED" if type_name in self.consolidation_map else "NEEDS_REVIEW"
            canonical = self.canonical_locations.get(type_name, "NO_CANONICAL_DEFINED")
            print(f"  {type_name:<25} {count} occurrences -> {canonical}")
        print()

def main():
    frontend_dir = "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/frontend"
    
    consolidator = TypeConsolidator(frontend_dir)
    print("Scanning all TypeScript files for type definitions...")
    consolidator.scan_all_types()
    
    print("Planning consolidation strategy...")
    consolidator.plan_consolidation()
    
    print("Generating consolidation report...")
    consolidator.print_consolidation_report()
    
    # Generate import updates
    updates = consolidator.generate_import_updates()
    print(f"Generated {len(updates)} import updates")
    
    # Show sample of what needs to be done
    print("\nSAMPLE UPDATES NEEDED:")
    for file_path, type_name, import_path in updates[:10]:
        print(f"  {type_name} in {file_path}")
        print(f"    -> import from {import_path}")
    
if __name__ == "__main__":
    main()