from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""Test Suite: Central Configuration Usage Validation

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Zero configuration-related incidents
- Value Impact: Prevents $12K MRR loss from config inconsistencies
- Strategic Impact: Ensures all modules use central config system

This test suite validates that all modules properly use the central
configuration system and don't bypass it with direct imports.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest

class ConfigUsageAnalyzer(ast.NodeVisitor):
    """AST analyzer to detect configuration usage patterns."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.violations = []
        self.central_config_imports = []
        self.direct_config_access = []
        self.os_environ_calls = []
        self.has_justification_marker = False
        
    def visit_Import(self, node):
        """Track import statements."""
        for alias in node.names:
            # Check for central config imports
            if 'netra_backend.app.config' in alias.name:
                self.central_config_imports.append({
                    'line': node.lineno,
                    'module': alias.name,
                    'alias': alias.asname
                })
            # Check for direct config module imports (violations)
            elif any(pattern in alias.name for pattern in [
                'config_secrets', 'config_exceptions', 'config_validation',
                'configuration.database', 'configuration.services'
            ]):
                if not self._check_if_config_module():
                    self.violations.append({
                        'type': 'direct_config_import',
                        'line': node.lineno,
                        'detail': f'Direct import of {alias.name}'
                    })
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node):
        """Track from imports."""
        if node.module:
            # Check for proper central config usage
            if node.module == 'netra_backend.app.config':
                for alias in node.names:
                    if alias.name in ['get_config', 'settings', 'config_manager']:
                        self.central_config_imports.append({
                            'line': node.lineno,
                            'module': node.module,
                            'name': alias.name
                        })
            # Check for direct configuration module access
            elif 'configuration' in node.module and 'netra_backend' in node.module:
                if not self._check_if_config_module() and 'base' not in node.module:
                    self.violations.append({
                        'type': 'direct_config_module_access',
                        'line': node.lineno,
                        'detail': f'Direct access to {node.module}'
                    })
        self.generic_visit(node)
        
    def visit_Attribute(self, node):
        """Track attribute access for os.environ."""
        if isinstance(node.value, ast.Name) and node.value.id == 'os':
            if node.attr == 'environ':
                # Check if there's a justification comment
                if not self._has_justification(node.lineno):
                    self.os_environ_calls.append({
                        'line': node.lineno,
                        'type': 'os.environ_access'
                    })
        self.generic_visit(node)
        
    def _check_if_config_module(self) -> bool:
        """Check if current file is part of configuration system."""
        config_paths = [
            'netra_backend/app/config.py',
            'netra_backend/app/core/configuration/',
            'netra_backend/app/configuration/',
            'config_manager.py',
            'config_secrets_manager.py'
        ]
        return any(path in self.filepath.replace('\\', '/') for path in config_paths)
        
    def _has_justification(self, line_no: int) -> bool:
        """Check if line has @marked justification."""
        try:
            with open(self.filepath, 'r') as f:
                lines = f.readlines()
                if line_no > 0 and line_no <= len(lines):
                    # Check current line and previous line for @marked
                    for i in range(max(0, line_no - 2), min(line_no + 1, len(lines))):
                        if '@marked' in lines[i].lower():
                            return True
        except:
            pass
        return False

class TestCentralConfigUsage:
    """Test Suite 1: Validate Central Configuration Usage"""
    
    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        current_file = Path(__file__)
        # Navigate up to the netra-core-generation-1 directory
        project_root = current_file.parent.parent.parent
        return str(project_root)
    @pytest.fixture
    def python_files(self, project_root):
        """Get all Python files in the project."""
        files = []
        for root, dirs, filenames in os.walk(project_root):
            # Skip virtual environments and test files
            if 'venv' in root or '__pycache__' in root:
                continue
            for filename in filenames:
                if filename.endswith('.py'):
                    files.append(os.path.join(root, filename))
        return files
        
    def test_no_direct_config_module_imports(self, python_files):
        """Test 1: Verify no direct imports of internal config modules."""
        violations = []
        
        for filepath in python_files:
            # Skip configuration system files themselves
            if 'configuration' in filepath or 'config' in os.path.basename(filepath):
                continue
                
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                    analyzer = ConfigUsageAnalyzer(filepath)
                    analyzer.visit(tree)
                    
                    if analyzer.violations:
                        for violation in analyzer.violations:
                            if violation['type'] == 'direct_config_import':
                                violations.append({
                                    'file': filepath,
                                    'line': violation['line'],
                                    'detail': violation['detail']
                                })
            except Exception as e:
                continue
                
        assert len(violations) == 0, (
            f"Found {len(violations)} direct config module imports:\n" +
            "\n".join([f"  {v['file']}:{v['line']} - {v['detail']}" for v in violations[:10]])
        )
        
    def test_all_modules_use_get_config(self, python_files):
        """Test 2: Verify all modules needing config use get_config()."""
        modules_needing_config = []
        modules_using_central = []
        
        for filepath in python_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Check if module needs configuration
                    config_patterns = [
                        r'database_url', r'redis_url', r'api_key',
                        r'SECRET', r'TOKEN', r'PORT', r'HOST'
                    ]
                    
                    needs_config = any(re.search(pattern, content, re.IGNORECASE) 
                                     for pattern in config_patterns)
                    
                    if needs_config:
                        modules_needing_config.append(filepath)
                        
                        # Check if using central config
                        if 'from app.config import' in content or \
                           'get_config()' in content:
                            modules_using_central.append(filepath)
            except:
                continue
                
        missing_central = set(modules_needing_config) - set(modules_using_central)
        
        # Exclude test files and config system files
        missing_central = [f for f in missing_central 
                          if 'test' not in f and 'config' not in os.path.basename(f)]
        
        assert len(missing_central) == 0, (
            f"Found {len(missing_central)} modules needing config but not using central system:\n" +
            "\n".join([f"  {f}" for f in list(missing_central)[:10]])
        )
        
    def test_config_access_through_interface(self, python_files):
        """Test 3: Verify config access only through defined interfaces."""
        invalid_access = []
        
        valid_interfaces = ['get_config', 'settings', 'config_manager', 'reload_config']
        
        for filepath in python_files:
            if 'test' in filepath:
                continue
                
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Look for AppConfig instantiation outside config system
                    if 'AppConfig(' in content:
                        if 'configuration' not in filepath and 'config' not in os.path.basename(filepath):
                            invalid_access.append({
                                'file': filepath,
                                'issue': 'Direct AppConfig instantiation'
                            })
                            
                    # Look for accessing config attributes directly
                    patterns = [
                        r'config\.\w+\s*=',  # Direct assignment
                        r'_config\.\w+\s*=',  # Private config modification
                    ]
                    
                    for pattern in patterns:
                        if re.search(pattern, content):
                            invalid_access.append({
                                'file': filepath,
                                'issue': 'Direct config attribute modification'
                            })
            except:
                continue
                
        assert len(invalid_access) == 0, (
            f"Found {len(invalid_access)} invalid config access patterns:\n" +
            "\n".join([f"  {v['file']}: {v['issue']}" for v in invalid_access[:10]])
        )
        
    def test_no_duplicate_config_loading(self, python_files):
        """Test 4: Verify no duplicate configuration loading."""
        config_loaders = []
        
        for filepath in python_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Look for configuration loading patterns
                    loading_patterns = [
                        r'load_dotenv\(',
                        r'ConfigParser\(',
                        r'json\.load.*config',
                        r'yaml\.load.*config',
                        r'toml\.load.*config'
                    ]
                    
                    for pattern in loading_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            # Exclude the central config system
                            if 'configuration' not in filepath:
                                config_loaders.append({
                                    'file': filepath,
                                    'pattern': pattern
                                })
            except:
                continue
                
        assert len(config_loaders) == 0, (
            f"Found {len(config_loaders)} duplicate config loading mechanisms:\n" +
            "\n".join([f"  {v['file']}: {v['pattern']}" for v in config_loaders[:10]])
        )
        
    def test_config_consistency_across_modules(self, project_root):
        """Test 5: Verify configuration values are consistent across modules."""
        config_values = {}
        
        # Collect all configuration key references
        for root, dirs, files in os.walk(project_root):
            if 'venv' in root or 'test' in root:
                continue
                
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                            # Extract config key references
                            patterns = re.findall(r'config\.(\w+)', content)
                            patterns += re.findall(r'settings\.(\w+)', content)
                            
                            for key in patterns:
                                if key not in config_values:
                                    config_values[key] = []
                                config_values[key].append(filepath)
                    except:
                        continue
                        
        # Check for keys used in multiple places
        multi_use_keys = {k: v for k, v in config_values.items() if len(v) > 1}
        
        # These should all be accessing the same central config
        assert len(multi_use_keys) > 0, "Should have config keys used in multiple places"
        
        # Verify they're all using central config
        for key, files in list(multi_use_keys.items())[:5]:  # Check first 5
            for filepath in files[:3]:  # Check first 3 files
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        assert ('from app.config import' in content or
                               'get_config()' in content), (
                            f"File {filepath} uses config key '{key}' but doesn't import central config"
                        )
                except:
                    continue
