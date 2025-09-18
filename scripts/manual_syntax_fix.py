#!/usr/bin/env python3
"""
Manual Syntax Fix Script for Specific Patterns
==============================================

This script fixes specific syntax error patterns that the automated script missed.
"""

import os
import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_specific_files():
    """Fix specific files with known patterns"""
    
    fixes = [
        # Unterminated docstrings
        {
            'file': 'tests/critical/test_health_route_configuration_chaos.py',
            'pattern': r"^Test suite to expose health route configuration and environment chaos\.",
            'replacement': '"""Test suite to expose health route configuration and environment chaos.',
            'add_closing': True
        },
        {
            'file': 'tests/critical/test_health_route_duplication_audit.py', 
            'pattern': r"^Test suite to expose health route duplication and legacy issues\.",
            'replacement': '"""Test suite to expose health route duplication and legacy issues.',
            'add_closing': True
        },
        {
            'file': 'tests/database/test_port_configuration_mismatch.py',
            'pattern': r"^Database Port Configuration Mismatch Test",
            'replacement': '"""Database Port Configuration Mismatch Test',
            'add_closing': True
        },
        # Unmatched braces/parentheses
        {
            'file': 'tests/deployment/test_oauth_staging_flow.py',
            'find': 'response.status_code}"',
            'replace': 'response.status_code}'
        },
        # Dollar sign literals
        {
            'file': 'tests/critical/test_websocket_comprehensive_failure_suite.py',
            'find': '- Each failure mode represents a potential $50K+ ARR impact',
            'replace': '- Each failure mode represents a potential \\$50K+ ARR impact'
        },
        # Invalid decimal literals in other files
        {
            'file': 'tests/validate_ws_speed.py',
            'pattern': r'\$(\d+[KMB]\+?)',
            'replacement': r'\\$\1'
        },
        {
            'file': 'tests/test_alpine_container_selection.py',
            'pattern': r'\$(\d+[KMB]\+?)',
            'replacement': r'\\$\1'
        }
    ]
    
    for fix in fixes:
        try:
            filepath = Path(fix['file'])
            if not filepath.exists():
                continue
                
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            if 'pattern' in fix:
                content = re.sub(fix['pattern'], fix['replacement'], content)
            elif 'find' in fix:
                content = content.replace(fix['find'], fix['replace'])
            
            if fix.get('add_closing'):
                # Find end of description and add closing quotes
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if ('import' in line or 'from' in line) and i > 5:
                        lines.insert(i, '"""')
                        break
                content = '\n'.join(lines)
            
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Fixed {filepath}")
        
        except Exception as e:
            logger.error(f"Error fixing {fix['file']}: {e}")

def fix_unmatched_parentheses():
    """Fix specific unmatched parentheses patterns"""
    
    # Fix specific files with known issues
    unmatched_fixes = [
        {
            'file': 'tests/e2e/agent_goldenpath/test_advanced_agent_features_e2e.py',
            'find': ')))',
            'replace': '))'
        },
        {
            'file': 'tests/e2e/agent_goldenpath/test_advanced_error_recovery_e2e.py',
            'find': ')))',
            'replace': '))'
        }
    ]
    
    for fix in unmatched_fixes:
        try:
            filepath = Path(fix['file'])
            if not filepath.exists():
                continue
                
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if fix['find'] in content:
                content = content.replace(fix['find'], fix['replace'])
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Fixed unmatched parentheses in {filepath}")
        
        except Exception as e:
            logger.error(f"Error fixing {fix['file']}: {e}")

def apply_comprehensive_fixes():
    """Apply comprehensive fixes to remaining files"""
    
    # Find all test files
    test_dirs = [Path('tests'), Path('netra_backend/tests'), Path('auth_service/tests')]
    test_files = []
    
    for test_dir in test_dirs:
        if test_dir.exists():
            test_files.extend(test_dir.rglob('test_*.py'))
            test_files.extend(test_dir.rglob('*_test.py'))
    
    for filepath in test_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Fix multiple closing quotes patterns
            content = re.sub(r'"""([^"]*?)""""', r'"""\1"""', content)
            content = re.sub(r"'''([^']*?)''''", r"'''\1'''", content)
            
            # Fix specific unterminated patterns
            content = re.sub(r"'''([^']*?)'$", r"'''\1'''", content, flags=re.MULTILINE)
            content = re.sub(r'"""([^"]*?)"$', r'"""\1"""', content, flags=re.MULTILINE)
            
            # Fix logger statements with empty strings
            content = re.sub(r'logger\.(info|debug|warning|error)\("")\)', 
                           r'# logger.\1("")  # TODO: Add proper log message', content)
            
            # Fix missing method indentation
            lines = content.split('\n')
            fixed_lines = []
            
            for i, line in enumerate(lines):
                # Fix methods that should be inside classes
                if (line.strip().startswith('def test_') and 
                    not line.startswith('    ') and 
                    i > 0):
                    # Check if we're inside a class
                    in_class = False
                    for j in range(i-1, -1, -1):
                        if lines[j].strip().startswith('class '):
                            in_class = True
                            break
                        elif lines[j].strip().startswith('def ') and not lines[j].startswith('    '):
                            break
                    
                    if in_class:
                        line = '    ' + line
                
                fixed_lines.append(line)
            
            content = '\n'.join(fixed_lines)
            
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Applied comprehensive fixes to {filepath}")
        
        except Exception as e:
            logger.error(f"Error applying comprehensive fixes to {filepath}: {e}")

def main():
    logger.info("Starting manual syntax fixes...")
    
    fix_specific_files()
    fix_unmatched_parentheses()
    apply_comprehensive_fixes()
    
    logger.info("Manual syntax fixes completed")

if __name__ == '__main__':
    main()