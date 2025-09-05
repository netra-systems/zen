"""Test Suite: Configuration Isolation and Boundary Validation

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: System stability and maintainability
- Value Impact: Prevents cross-service config leakage
- Strategic Impact: Ensures microservice independence per SPEC

This test suite validates configuration isolation patterns,
ensuring proper boundaries between services and preventing
configuration leakage across service boundaries.
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import ast
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pytest

class ConfigIsolationAnalyzer:
    """Analyzer for configuration isolation patterns."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.service_boundaries = {
            'main_backend': 'netra_backend/app',
            'auth_service': 'auth_service',
            'frontend': 'frontend'
        }
        self.violations = []
        self.cross_service_refs = []
        self.config_leaks = []
        
    def analyze_file(self, filepath: str) -> Dict:
        """Analyze a single file for isolation violations."""
        service = self._identify_service(filepath)
        violations = {
            'cross_service': [],
            'config_leak': [],
            'boundary_violation': []
        }
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
                
                # Check for cross-service imports
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        imported = self._get_import_module(node)
                        if imported:
                            target_service = self._identify_service_from_import(imported)
                            if target_service and target_service != service:
                                violations['cross_service'].append({
                                    'line': node.lineno,
                                    'from_service': service,
                                    'to_service': target_service,
                                    'import': imported
                                })
                                
                # Check for config value leakage
                config_patterns = self._extract_config_patterns(content)
                for pattern in config_patterns:
                    if self._is_config_leak(pattern, service):
                        violations['config_leak'].append(pattern)
                        
        except Exception as e:
            pass
            
        return violations
        
    def _identify_service(self, filepath: str) -> Optional[str]:
        """Identify which service a file belongs to."""
        filepath = filepath.replace('\\', '/')
        for service, path in self.service_boundaries.items():
            if path in filepath:
                return service
        return None
        
    def _identify_service_from_import(self, import_path: str) -> Optional[str]:
        """Identify service from import path."""
        for service, path in self.service_boundaries.items():
            if path.replace('/', '.') in import_path:
                return service
        return None
        
    def _get_import_module(self, node) -> Optional[str]:
        """Extract module name from import node."""
        if isinstance(node, ast.Import):
            return node.names[0].name if node.names else None
        elif isinstance(node, ast.ImportFrom):
            return node.module
        return None
        
    def _extract_config_patterns(self, content: str) -> List[Dict]:
        """Extract configuration access patterns from content."""
        patterns = []
        
        # Look for config key references
        config_refs = re.findall(r'config\.(\w+)', content)
        config_refs += re.findall(r'settings\.(\w+)', content)
        config_refs += re.findall(r'get_config\(\)\.(\w+)', content)
        
        for ref in config_refs:
            patterns.append({
                'type': 'config_access',
                'key': ref
            })
            
        # Look for environment variable references
        env_refs = re.findall(r'["\']([A-Z_]+_(?:URL|KEY|TOKEN|SECRET|PASSWORD))["\']', content)
        for ref in env_refs:
            patterns.append({
                'type': 'env_var',
                'key': ref
            })
            
        return patterns
        
    def _is_config_leak(self, pattern: Dict, service: str) -> bool:
        """Check if a config pattern represents a leak."""
        key = pattern['key']
        
        # Service-specific config keys that shouldn't be accessed elsewhere
        service_specific = {
            'auth_service': ['AUTH_', 'JWT_', 'OAUTH_'],
            'main_backend': ['NETRA_', 'BACKEND_', 'API_'],
            'frontend': ['REACT_', 'FRONTEND_', 'UI_']
        }
        
        if service:
            for other_service, prefixes in service_specific.items():
                if other_service != service:
                    for prefix in prefixes:
                        if key.startswith(prefix):
                            return True
        return False

class TestConfigIsolationPatterns:
    """Test Suite 3: Validate Configuration Isolation Patterns"""
    
    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        
    @pytest.fixture
    def analyzer(self, project_root):
        """Create isolation analyzer instance."""
        return ConfigIsolationAnalyzer(project_root)
        
    def test_no_cross_service_config_imports(self, project_root, analyzer):
        """Test 1: No cross-service configuration imports."""
        violations = []
        
        for root, dirs, files in os.walk(project_root):
            if 'venv' in root or '__pycache__' in root:
                continue
                
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                    
                filepath = os.path.join(root, filename)
                service = analyzer._identify_service(filepath)
                
                if not service:
                    continue
                    
                file_violations = analyzer.analyze_file(filepath)
                
                for violation in file_violations['cross_service']:
                    # Allow specific exceptions
                    if violation['import'] and 'config' in violation['import']:
                        violations.append({
                            'file': filepath,
                            'line': violation['line'],
                            'detail': f"{violation['from_service']} importing from {violation['to_service']}: {violation['import']}"
                        })
                        
        assert len(violations) == 0, (
            f"Found {len(violations)} cross-service config import violations:\n" +
            "\n".join([f"  {v['file']}:{v['line']}\n    {v['detail']}" 
                      for v in violations[:10]])
        )
        
    def test_config_values_scoped_to_service(self, project_root):
        """Test 2: Configuration values are properly scoped to services."""
        service_configs = {}
        
        # Collect config keys per service
        for root, dirs, files in os.walk(project_root):
            if 'venv' in root or '__pycache__' in root or 'test' in root:
                continue
                
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                    
                filepath = os.path.join(root, filename)
                
                # Identify service
                service = None
                if 'netra_backend/app' in filepath.replace('\\', '/'):
                    service = 'main_backend'
                elif 'auth_service' in filepath.replace('\\', '/'):
                    service = 'auth_service'
                elif 'frontend' in filepath.replace('\\', '/'):
                    service = 'frontend'
                    
                if not service:
                    continue
                    
                if service not in service_configs:
                    service_configs[service] = set()
                    
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Extract config keys
                        keys = re.findall(r'["\']([A-Z_]+(?:_URL|_KEY|_TOKEN|_HOST|_PORT))["\']', content)
                        service_configs[service].update(keys)
                except Exception:
                    continue
                    
        # Check for config key overlaps
        overlaps = []
        services = list(service_configs.keys())
        
        for i in range(len(services)):
            for j in range(i + 1, len(services)):
                service1, service2 = services[i], services[j]
                common = service_configs[service1] & service_configs[service2]
                
                # Some common configs are acceptable
                allowed_common = {'DATABASE_URL', 'REDIS_URL', 'LOG_LEVEL', 'DEBUG', 'ENVIRONMENT'}
                unexpected = common - allowed_common
                
                if unexpected:
                    overlaps.append({
                        'services': f"{service1} <-> {service2}",
                        'keys': list(unexpected)
                    })
                    
        assert len(overlaps) == 0, (
            f"Found {len(overlaps)} config key overlaps between services:\n" +
            "\n".join([f"  {o['services']}: {o['keys']}" for o in overlaps])
        )
        
    def test_no_hardcoded_config_values(self, project_root):
        """Test 3: No hardcoded configuration values in code."""
        hardcoded = []
        
        # Patterns that indicate hardcoded config
        patterns = [
            (r'["\']http://localhost:\d+', 'hardcoded localhost URL'),
            (r'["\']postgres://.*@', 'hardcoded database URL'),
            (r'["\']redis://.*@', 'hardcoded Redis URL'),
            (r'["\'][a-zA-Z0-9]{32,}["\']', 'hardcoded secret/key'),
            (r'api_key\s*=\s*["\'][^"\']+["\']', 'hardcoded API key'),
            (r'password\s*=\s*["\'][^"\']+["\']', 'hardcoded password')
        ]
        
        for root, dirs, files in os.walk(project_root):
            if 'venv' in root or '__pycache__' in root or 'test' in root:
                continue
                
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                    
                filepath = os.path.join(root, filename)
                
                # Skip config files themselves
                if 'config' in filename or 'settings' in filename:
                    continue
                    
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        for pattern, description in patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            if matches:
                                # Check if it's a justified exception
                                for match in matches:
                                    if not self._is_justified_hardcode(content, match):
                                        hardcoded.append({
                                            'file': filepath,
                                            'type': description,
                                            'value': match[:50]  # Truncate for security
                                        })
                except Exception:
                    continue
                    
        assert len(hardcoded) == 0, (
            f"Found {len(hardcoded)} hardcoded configuration values:\n" +
            "\n".join([f"  {h['file']}: {h['type']}" for h in hardcoded[:10]])
        )
        
    def test_config_initialization_order(self, project_root):
        """Test 4: Verify proper configuration initialization order."""
        init_patterns = []
        
        # Look for configuration initialization patterns
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
                        
                        # Look for config initialization
                        if 'get_config()' in content or 'ConfigManager()' in content:
                            # Check if it's at module level (potential issue)
                            tree = ast.parse(content)
                            for node in ast.walk(tree):
                                if isinstance(node, ast.Call):
                                    if hasattr(node.func, 'id') and node.func.id == 'get_config':
                                        # Check if it's at module level
                                        if node.col_offset == 0:
                                            init_patterns.append({
                                                'file': filepath,
                                                'line': node.lineno,
                                                'type': 'module_level_init'
                                            })
                except Exception:
                    continue
                    
        # Module-level initialization should be lazy
        eager_inits = [p for p in init_patterns if p['type'] == 'module_level_init']
        
        # Allow some specific files
        allowed_files = ['main.py', 'app.py', 'manage.py', 'config.py']
        eager_inits = [p for p in eager_inits 
                      if not any(allowed in os.path.basename(p['file']) 
                                for allowed in allowed_files)]
        
        assert len(eager_inits) == 0, (
            f"Found {len(eager_inits)} eager config initializations at module level:\n" +
            "\n".join([f"  {p['file']}:{p['line']}" for p in eager_inits[:10]])
        )
        
    def test_config_access_through_facades(self, project_root):
        """Test 5: Verify config access uses proper facade patterns."""
        direct_access = []
        facade_usage = []
        
        for root, dirs, files in os.walk(project_root):
            if 'venv' in root or '__pycache__' in root or 'test' in root:
                continue
                
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                    
                filepath = os.path.join(root, filename)
                
                # Skip config system files
                if 'configuration' in filepath or 'config' in filename:
                    continue
                    
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        tree = ast.parse(content)
                        
                        for node in ast.walk(tree):
                            # Check for direct AppConfig instantiation
                            if isinstance(node, ast.Call):
                                if hasattr(node.func, 'id') and node.func.id == 'AppConfig':
                                    direct_access.append({
                                        'file': filepath,
                                        'line': node.lineno,
                                        'type': 'direct_instantiation'
                                    })
                                    
                            # Check for proper facade usage
                            if isinstance(node, ast.Call):
                                if hasattr(node.func, 'id') and node.func.id in ['get_config', 'reload_config']:
                                    facade_usage.append({
                                        'file': filepath,
                                        'line': node.lineno
                                    })
                except Exception:
                    continue
                    
        # Should use facades, not direct instantiation
        assert len(direct_access) == 0, (
            f"Found {len(direct_access)} direct AppConfig instantiations (should use get_config()):\n" +
            "\n".join([f"  {d['file']}:{d['line']}" for d in direct_access[:10]])
        )
        
        # Should have significant facade usage
        assert len(facade_usage) > 0, "No facade usage found - config system may not be properly used"
        
    def _is_justified_hardcode(self, content: str, value: str) -> bool:
        """Check if a hardcoded value is justified."""
        # Look for justification markers near the value
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if value in line:
                # Check surrounding lines for justification
                for j in range(max(0, i - 2), min(i + 2, len(lines))):
                    if '@marked' in lines[j].lower() or '@justified' in lines[j].lower():
                        return True
                    if 'example' in lines[j].lower() or 'test' in lines[j].lower():
                        return True
        return False