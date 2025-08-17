#!/usr/bin/env python3
"""Audit backend route permissions."""

import re
import os
from pathlib import Path
from typing import List, Tuple, Dict

def analyze_route_file(filepath: Path) -> Dict[str, List[str]]:
    """Analyze a single route file for permissions."""
    content = filepath.read_text()
    
    admin_routes = []
    authenticated_routes = []
    public_routes = []
    
    # Find all route definitions
    route_patterns = re.findall(
        r'@router\.(get|post|put|delete|patch)\(["\'](.*?)["\'].*?\).*?\n.*?def\s+(\w+)',
        content,
        re.DOTALL
    )
    
    for method, path, func_name in route_patterns:
        # Check for authentication in function
        func_pattern = rf'def\s+{func_name}.*?(?=\ndef|\Z)'
        func_match = re.search(func_pattern, content, re.DOTALL)
        
        if func_match:
            func_text = func_match.group(0)
            route_info = f'{path} ({method.upper()})'
            
            if 'AdminDep' in func_text or 'require_admin' in func_text:
                admin_routes.append(route_info)
            elif 'get_current_user' in func_text or 'require_permission' in func_text or 'DeveloperDep' in func_text:
                authenticated_routes.append(route_info)
            else:
                public_routes.append(route_info)
    
    return {
        'admin': admin_routes,
        'authenticated': authenticated_routes,
        'public': public_routes
    }

def main():
    """Run permission audit on all route files."""
    route_dir = Path('app/routes')
    route_files = [f for f in route_dir.glob('*.py') if f.name != '__init__.py']
    
    all_admin = []
    all_authenticated = []
    all_public = []
    
    for route_file in route_files:
        results = analyze_route_file(route_file)
        
        for route in results['admin']:
            all_admin.append(f'{route_file.stem}: {route}')
        for route in results['authenticated']:
            all_authenticated.append(f'{route_file.stem}: {route}')
        for route in results['public']:
            all_public.append(f'{route_file.stem}: {route}')
    
    print('=' * 60)
    print('BACKEND ROUTES PERMISSION AUDIT REPORT')
    print('=' * 60)
    
    print(f'\n[ADMIN] ADMIN-ONLY ROUTES ({len(all_admin)}):')
    print('-' * 40)
    for route in sorted(all_admin):
        print(f'  + {route}')
    
    print(f'\n[AUTH] AUTHENTICATED ROUTES ({len(all_authenticated)}):')
    print('-' * 40)
    # Show first 15 authenticated routes
    for route in sorted(all_authenticated)[:15]:
        print(f'  + {route}')
    if len(all_authenticated) > 15:
        print(f'  ... and {len(all_authenticated) - 15} more')
    
    print(f'\n[WARNING] PUBLIC ROUTES - NO AUTH REQUIRED ({len(all_public)}):')
    print('-' * 40)
    for route in sorted(all_public):
        print(f'  ! {route}')
    
    # Special attention to sensitive routes
    print('\n' + '=' * 60)
    print('CRITICAL FINDINGS:')
    print('=' * 60)
    
    sensitive_keywords = ['factory', 'report', 'admin', 'config', 'settings', 'monitor', 'database']
    
    public_sensitive = []
    for route in all_public:
        for keyword in sensitive_keywords:
            if keyword.lower() in route.lower():
                public_sensitive.append(route)
                break
    
    if public_sensitive:
        print('\n[CRITICAL] POTENTIALLY SENSITIVE PUBLIC ROUTES:')
        for route in public_sensitive:
            print(f'  X {route}')
    else:
        print('\n[OK] No sensitive public routes found')
    
    print('\n' + '=' * 60)
    print('SUMMARY:')
    print(f'  Total Routes: {len(all_admin) + len(all_authenticated) + len(all_public)}')
    print(f'  Admin-only: {len(all_admin)}')
    print(f'  Authenticated: {len(all_authenticated)}')
    print(f'  Public: {len(all_public)}')
    print('=' * 60)

if __name__ == '__main__':
    main()