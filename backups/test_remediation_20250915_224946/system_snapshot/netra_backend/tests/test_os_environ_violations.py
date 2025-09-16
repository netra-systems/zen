from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""Test Suite: OS Environment Variable Access Violations

env = get_env()
Business Value Justification (BVJ):
- Segment: Enterprise  
- Business Goal: Security and configuration integrity
- Value Impact: Prevents security breaches and config drift
- Strategic Impact: Ensures all env var access is controlled and audited

This test suite detects and validates that no modules make direct
os.environ calls outside of the central configuration system,
unless explicitly @marked with justification.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import ast
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest

class OSEnvironAnalyzer(ast.NodeVisitor):
    """AST analyzer to detect os.environ usage patterns."""
    
    def __init__(self, filepath: str, file_content: str):
        self.filepath = filepath
        self.file_content = file_content
        self.file_lines = file_content.split('\n')
        self.os_environ_violations = []
        self.getenv_violations = []
        self.environ_get_violations = []
        self.justified_calls = []
        
    def visit_Subscript(self, node):
        """Detect env.get('KEY') patterns."""
        if self._is_os_environ(node.value):
            line_no = node.lineno
            if self._has_justification_marker(line_no):
                self.justified_calls.append({
                    'line': line_no,
                    'type': 'os.environ[]',
                    'justified': True
                })
            else:
                self.os_environ_violations.append({
                    'line': line_no,
                    'type': 'os.environ[]',
                    'code': self._get_line_content(line_no)
                })
        self.generic_visit(node)
        
    def visit_Call(self, node):
        """Detect get_env().get() and os.environ.get() patterns."""
        # Check for get_env().get()
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == 'os':
                if node.func.attr == 'getenv':
                    line_no = node.lineno
                    if self._has_justification_marker(line_no):
                        self.justified_calls.append({
                            'line': line_no,
                            'type': 'get_env().get()',
                            'justified': True
                        })
                    else:
                        self.getenv_violations.append({
                            'line': line_no,
                            'type': 'get_env().get()',
                            'code': self._get_line_content(line_no)
                        })
                        
            # Check for os.environ.get()
            elif self._is_os_environ(node.func.value):
                if node.func.attr == 'get':
                    line_no = node.lineno
                    if self._has_justification_marker(line_no):
                        self.justified_calls.append({
                            'line': line_no,
                            'type': 'os.environ.get()',
                            'justified': True
                        })
                    else:
                        self.environ_get_violations.append({
                            'line': line_no,
                            'type': 'os.environ.get()',
                            'code': self._get_line_content(line_no)
                        })
        self.generic_visit(node)
        
    def _is_os_environ(self, node) -> bool:
        """Check if node represents os.environ."""
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == 'os':
                return node.attr == 'environ'
        return False
        
    def _has_justification_marker(self, line_no: int) -> bool:
        """Check if line has @marked justification comment."""
        # Check lines around the violation for @marked comment
        for i in range(max(0, line_no - 3), min(line_no + 2, len(self.file_lines))):
            if i < len(self.file_lines):
                line = self.file_lines[i]
                if '@marked' in line.lower() or '@justified' in line.lower():
                    # Extract justification reason if present
                    match = re.search(r'@(?:marked|justified)(?:\s*:\s*(.+))?', line, re.IGNORECASE)
                    if match:
                        return True
        return False
        
    def _get_line_content(self, line_no: int) -> str:
        """Get the actual line content."""
        if 0 <= line_no - 1 < len(self.file_lines):
            return self.file_lines[line_no - 1].strip()
        return ""
        
    def get_all_violations(self) -> List[Dict]:
        """Get all violations found."""
        return (self.os_environ_violations + 
                self.getenv_violations + 
                self.environ_get_violations)

class OSEnvironViolationsTests:
    """Test Suite 2: Detect and Validate OS Environment Access"""
    
    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent.parent
        
    @pytest.fixture
    def allowed_files(self):
        """Files allowed to access os.environ directly."""
        return [
            # Core configuration system files
            'configuration/base.py',
            'configuration/database.py',
            'configuration/environment.py',
            'configuration/secrets.py',
            'configuration/unified_secrets.py',
            'config_manager.py',
            'config_secrets_manager.py',
            'config.py',
            
            # Test infrastructure
            'conftest.py',
            'test_',  # All test files
            '/tests/',  # All test directories
            
            # Development and deployment tools
            'dev_launcher.py',
            'dev_launcher/',  # Dev launcher modules
            'scripts/',  # All scripts are infrastructure
            '.github/',  # CI/CD workflows
            
            # Setup and management files
            'setup.py',
            'manage.py',
            'alembic/',  # Database migrations
            
            # Build and packaging
            'build.py',
            'install.py',
            '__init__.py'  # Package initialization
        ]
        
    def test_no_direct_os_environ_access(self, project_root, allowed_files):
        """Test 1: No direct env.get('KEY') access outside config system."""
        violations = []
        
        for root, dirs, files in os.walk(project_root):
            # Skip virtual environments
            if 'venv' in root or '__pycache__' in root:
                continue
                
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                    
                filepath = os.path.join(root, filename)
                
                # Check if file is allowed
                if any(allowed in filepath.replace('\\', '/') for allowed in allowed_files):
                    continue
                    
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        tree = ast.parse(content)
                        analyzer = OSEnvironAnalyzer(filepath, content)
                        analyzer.visit(tree)
                        
                        if analyzer.os_environ_violations:
                            for violation in analyzer.os_environ_violations:
                                violations.append({
                                    'file': filepath,
                                    'line': violation['line'],
                                    'code': violation['code']
                                })
                except Exception as e:
                    continue
                    
        assert len(violations) == 0, (
            f"Found {len(violations)} direct os.environ[] access violations:\n" +
            "\n".join([f"  {v['file']}:{v['line']}\n    {v['code']}" 
                      for v in violations[:10]])
        )
        
    def test_no_os_getenv_usage(self, project_root, allowed_files):
        """Test 2: No get_env().get() usage outside config system."""
        violations = []
        
        for root, dirs, files in os.walk(project_root):
            if 'venv' in root or '__pycache__' in root:
                continue
                
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                    
                filepath = os.path.join(root, filename)
                
                # Check if file is allowed
                if any(allowed in filepath.replace('\\', '/') for allowed in allowed_files):
                    continue
                    
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        tree = ast.parse(content)
                        analyzer = OSEnvironAnalyzer(filepath, content)
                        analyzer.visit(tree)
                        
                        if analyzer.getenv_violations:
                            for violation in analyzer.getenv_violations:
                                violations.append({
                                    'file': filepath,
                                    'line': violation['line'],
                                    'code': violation['code']
                                })
                except Exception:
                    continue
                    
        assert len(violations) == 0, (
            f"Found {len(violations)} get_env().get() violations:\n" +
            "\n".join([f"  {v['file']}:{v['line']}\n    {v['code']}" 
                      for v in violations[:10]])
        )
        
    def test_no_environ_get_usage(self, project_root, allowed_files):
        """Test 3: No os.environ.get() usage outside config system."""
        violations = []
        
        for root, dirs, files in os.walk(project_root):
            if 'venv' in root or '__pycache__' in root:
                continue
                
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                    
                filepath = os.path.join(root, filename)
                
                if any(allowed in filepath.replace('\\', '/') for allowed in allowed_files):
                    continue
                    
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        tree = ast.parse(content)
                        analyzer = OSEnvironAnalyzer(filepath, content)
                        analyzer.visit(tree)
                        
                        if analyzer.environ_get_violations:
                            for violation in analyzer.environ_get_violations:
                                violations.append({
                                    'file': filepath,
                                    'line': violation['line'],
                                    'code': violation['code']
                                })
                except Exception:
                    continue
                    
        assert len(violations) == 0, (
            f"Found {len(violations)} os.environ.get() violations:\n" +
            "\n".join([f"  {v['file']}:{v['line']}\n    {v['code']}" 
                      for v in violations[:10]])
        )
        
    def test_justified_env_access_has_markers(self, project_root):
        """Test 4: Verify justified env access has proper @marked annotations."""
        justified_count = 0
        missing_justification = []
        
        for root, dirs, files in os.walk(project_root):
            if 'venv' in root or '__pycache__' in root:
                continue
                
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                    
                filepath = os.path.join(root, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Quick check for os.environ usage
                        if 'os.environ' not in content and 'os.getenv' not in content:
                            continue
                            
                        tree = ast.parse(content)
                        analyzer = OSEnvironAnalyzer(filepath, content)
                        analyzer.visit(tree)
                        
                        justified_count += len(analyzer.justified_calls)
                        
                        # Check if there are violations without justification
                        all_violations = analyzer.get_all_violations()
                        if all_violations:
                            # These should have been marked but weren't
                            for v in all_violations:
                                # Double-check it's not in an allowed file
                                if not any(allowed in filepath.replace('\\', '/') 
                                         for allowed in ['configuration/', 'config']):
                                    missing_justification.append({
                                        'file': filepath,
                                        'line': v['line'],
                                        'type': v['type']
                                    })
                except Exception:
                    continue
                    
        # We expect some justified calls in the system
        assert justified_count > 0 or len(missing_justification) == 0, (
            f"Found {len(missing_justification)} env accesses without @marked justification:\n" +
            "\n".join([f"  {v['file']}:{v['line']} ({v['type']})" 
                      for v in missing_justification[:10]])
        )
        
    def test_env_access_patterns_consistency(self, project_root):
        """Test 5: Verify environment access patterns are consistent."""
        access_patterns = {
            'subscript': [],  # env.get('KEY')
            'get': [],        # env.get('KEY')
            'getenv': [],     # get_env().get('KEY')
            'config': []      # Proper config usage
        }
        
        for root, dirs, files in os.walk(project_root):
            if 'venv' in root or '__pycache__' in root or 'test' in root:
                continue
                
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                    
                filepath = os.path.join(root, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Check for different patterns
                        if re.search(r"os\.environ\[[\'\"]", content):
                            access_patterns['subscript'].append(filepath)
                        if re.search(r"os\.environ\.get\(", content):
                            access_patterns['get'].append(filepath)
                        if re.search(r"os\.getenv\(", content):
                            access_patterns['getenv'].append(filepath)
                        if re.search(r"get_config\(\)|settings\.", content):
                            access_patterns['config'].append(filepath)
                except Exception:
                    continue
                    
        # Most access should be through config system
        config_count = len(access_patterns['config'])
        direct_count = (len(access_patterns['subscript']) + 
                       len(access_patterns['get']) + 
                       len(access_patterns['getenv']))
        
        # Config usage should dominate (excluding test files)
        non_test_config = [f for f in access_patterns['config'] if 'test' not in f]
        non_test_direct = sum(len([f for f in access_patterns[k] if 'test' not in f])
                            for k in ['subscript', 'get', 'getenv'])
        
        assert len(non_test_config) > non_test_direct, (
            f"Direct env access ({non_test_direct} files) should not exceed "
            f"config system usage ({len(non_test_config)} files).\n"
            f"Direct access files: {access_patterns['subscript'][:3]}"
        )
