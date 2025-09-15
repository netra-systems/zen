"""
Issue #1140 Architecture Compliance Tests

Tests to ensure SSOT WebSocket pattern compliance and prevent regression.

Business Value Justification (BVJ):
- Segment: Platform/Development
- Business Goal: Architecture integrity and SSOT compliance
- Value Impact: Prevents dual-path architecture violations that could impact $500K+ ARR
- Strategic Impact: Ensures consistent SSOT patterns across the entire codebase
"""

import ast
import os
import re
import pytest
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass
import json

from test_framework.base_e2e_test import BaseE2ETest


@dataclass
class ArchitectureViolation:
    """Represents an architecture violation."""
    file_path: str
    line_number: int
    violation_type: str
    description: str
    code_snippet: str


@dataclass
class ScanResults:
    """Results of architecture scanning."""
    http_fallback_count: int = 0
    dual_transport_count: int = 0
    websocket_implementations: List[str] = None
    import_violations: List[str] = None
    violations: List[ArchitectureViolation] = None
    
    def __post_init__(self):
        if self.websocket_implementations is None:
            self.websocket_implementations = []
        if self.import_violations is None:
            self.import_violations = []
        if self.violations is None:
            self.violations = []


class ArchitectureScanner:
    """Scanner for architecture compliance patterns."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize architecture scanner."""
        self.project_root = project_root or self._detect_project_root()
        self.frontend_root = self.project_root / "frontend"
        self.backend_root = self.project_root / "netra_backend"
        
        # Patterns to detect dual-path violations
        self.http_fallback_patterns = [
            r'fetch\s*\(\s*["\'].*?/api/demo/chat',
            r'fetch\s*\(\s*["\'].*?/chat',
            r'httpx\.post\s*\(\s*["\'].*?/chat',
            r'axios\.post\s*\(\s*["\'].*?/chat',
            r'POST.*?/api/demo/chat',
            r'HTTP.*?fallback',
            r'fallback.*?http',
            r'http.*?backup'
        ]
        
        self.dual_transport_patterns = [
            r'websocket.*?http',
            r'http.*?websocket',
            r'fallback.*?transport',
            r'dual.*?path',
            r'alternative.*?transport',
            r'backup.*?connection'
        ]
        
        self.websocket_import_patterns = [
            r'from.*?websocket.*?import',
            r'import.*?websocket',
            r'from.*?uvs.*?import.*?WebSocket',
            r'from.*?services.*?websocket'
        ]
    
    def _detect_project_root(self) -> Path:
        """Detect project root directory."""
        current = Path(__file__).parent
        while current.parent != current:
            if (current / "netra_backend").exists() and (current / "frontend").exists():
                return current
            current = current.parent
        raise RuntimeError("Could not detect project root")
    
    def scan_for_patterns(self, pattern_types: List[str]) -> ScanResults:
        """
        Scan codebase for architectural patterns.
        
        Args:
            pattern_types: List of pattern types to scan for
            
        Returns:
            ScanResults with found violations
        """
        results = ScanResults()
        
        # Scan frontend files
        frontend_files = self._get_files_to_scan(self.frontend_root, ['.ts', '.tsx', '.js', '.jsx'])
        
        # Scan backend files  
        backend_files = self._get_files_to_scan(self.backend_root, ['.py'])
        
        all_files = frontend_files + backend_files
        
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                self._scan_file_content(file_path, content, pattern_types, results)
                
            except Exception as e:
                # Skip files that can't be read
                continue
        
        return results
    
    def _get_files_to_scan(self, root_dir: Path, extensions: List[str]) -> List[Path]:
        """Get list of files to scan."""
        files = []
        
        if not root_dir.exists():
            return files
            
        for ext in extensions:
            files.extend(root_dir.rglob(f'*{ext}'))
        
        # Filter out node_modules, .git, __pycache__, etc.
        excluded_patterns = [
            'node_modules',
            '.git',
            '__pycache__',
            '.pytest_cache',
            'dist',
            'build',
            '.next',
            'coverage'
        ]
        
        filtered_files = []
        for file_path in files:
            if not any(pattern in str(file_path) for pattern in excluded_patterns):
                filtered_files.append(file_path)
        
        return filtered_files
    
    def _scan_file_content(self, file_path: Path, content: str, pattern_types: List[str], results: ScanResults):
        """Scan file content for patterns."""
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Check for HTTP fallback patterns
            if "HTTP_FALLBACK_PATTERN" in pattern_types:
                for pattern in self.http_fallback_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        results.http_fallback_count += 1
                        results.violations.append(ArchitectureViolation(
                            file_path=str(file_path),
                            line_number=line_num,
                            violation_type="HTTP_FALLBACK_PATTERN",
                            description=f"HTTP fallback pattern detected: {pattern}",
                            code_snippet=line.strip()
                        ))
            
            # Check for dual transport patterns
            if "DUAL_TRANSPORT_PATTERN" in pattern_types:
                for pattern in self.dual_transport_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        results.dual_transport_count += 1
                        results.violations.append(ArchitectureViolation(
                            file_path=str(file_path),
                            line_number=line_num,
                            violation_type="DUAL_TRANSPORT_PATTERN", 
                            description=f"Dual transport pattern detected: {pattern}",
                            code_snippet=line.strip()
                        ))
            
            # Check for conditional HTTP/WebSocket usage
            if "CONDITIONAL_HTTP_WEBSOCKET" in pattern_types:
                conditional_patterns = [
                    r'if.*?websocket.*?else.*?http',
                    r'if.*?http.*?else.*?websocket',
                    r'websocket.*?\?.*?http',
                    r'http.*?\?.*?websocket',
                    r'fallback.*?to.*?http',
                    r'try.*?websocket.*?except.*?http'
                ]
                
                for pattern in conditional_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        results.dual_transport_count += 1
                        results.violations.append(ArchitectureViolation(
                            file_path=str(file_path),
                            line_number=line_num,
                            violation_type="CONDITIONAL_HTTP_WEBSOCKET",
                            description=f"Conditional HTTP/WebSocket usage detected: {pattern}",
                            code_snippet=line.strip()
                        ))
    
    def find_websocket_implementations(self) -> List[str]:
        """Find WebSocket implementations in the codebase."""
        implementations = []
        
        # Check frontend WebSocket implementations
        frontend_ws_files = [
            self.frontend_root / "services" / "webSocketService.ts",
            self.frontend_root / "services" / "uvs" / "WebSocketBridgeClient.ts",
            self.frontend_root / "hooks" / "useWebSocket.ts"
        ]
        
        for file_path in frontend_ws_files:
            if file_path.exists():
                implementations.append(str(file_path))
        
        # Check backend WebSocket implementations  
        backend_ws_files = self._get_files_to_scan(self.backend_root, ['.py'])
        
        for file_path in backend_ws_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'websocket' in content.lower() and ('class' in content or 'def' in content):
                        implementations.append(str(file_path))
            except:
                continue
        
        return implementations
    
    def check_websocket_import_violations(self) -> List[str]:
        """Check for WebSocket import violations."""
        violations = []
        
        # Expected SSOT imports
        expected_imports = {
            'frontend': [
                'from @/services/uvs/WebSocketBridgeClient',
                'from @/hooks/useWebSocket'
            ],
            'backend': [
                'from netra_backend.app.websocket_core.manager',
                'from netra_backend.app.services.websocket'
            ]
        }
        
        # Check frontend files
        frontend_files = self._get_files_to_scan(self.frontend_root, ['.ts', '.tsx'])
        
        for file_path in frontend_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for non-SSOT WebSocket imports
                non_ssot_patterns = [
                    r'import.*?ws\s+from',
                    r'import.*?WebSocket\s+from.*?(?!@/services/uvs)',
                    r'from.*?websocket.*?import.*?(?!@/services)',
                    r'import.*?socket\.io'
                ]
                
                for pattern in non_ssot_patterns:
                    if re.search(pattern, content):
                        violations.append(f"{file_path}: Non-SSOT WebSocket import pattern: {pattern}")
                        
            except:
                continue
        
        return violations


@pytest.mark.unit
class TestIssue1140ArchitectureCompliance(BaseE2ETest):
    """Test architecture compliance for SSOT WebSocket pattern."""
    
    def setup_method(self):
        """Setup for each test method."""
        super().setup_method()
        self.scanner = ArchitectureScanner()
    
    @pytest.mark.unit
    def test_no_dual_path_in_codebase(self):
        """
        Scan codebase for dual-path patterns.
        Should FAIL initially if dual paths exist.
        """
        # Scan for problematic patterns
        results = self.scanner.scan_for_patterns([
            "HTTP_FALLBACK_PATTERN",
            "DUAL_TRANSPORT_PATTERN", 
            "CONDITIONAL_HTTP_WEBSOCKET"
        ])
        
        # Log violations for debugging
        if results.violations:
            print(f"\nFound {len(results.violations)} architecture violations:")
            for violation in results.violations:
                print(f"  {violation.file_path}:{violation.line_number} - {violation.violation_type}")
                print(f"    {violation.description}")
                print(f"    Code: {violation.code_snippet}")
        
        # These assertions should FAIL initially if patterns found
        assert results.http_fallback_count == 0, \
            f"Found {results.http_fallback_count} HTTP fallback patterns. Violations: {[v.description for v in results.violations if v.violation_type == 'HTTP_FALLBACK_PATTERN']}"
        
        assert results.dual_transport_count == 0, \
            f"Found {results.dual_transport_count} dual transport patterns. Violations: {[v.description for v in results.violations if v.violation_type in ['DUAL_TRANSPORT_PATTERN', 'CONDITIONAL_HTTP_WEBSOCKET']]}"

    @pytest.mark.unit  
    def test_websocket_ssot_compliance(self):
        """
        Test WebSocket implementation follows SSOT principles.
        """
        websocket_implementations = self.scanner.find_websocket_implementations()
        
        # Log found implementations
        print(f"\nFound WebSocket implementations:")
        for impl in websocket_implementations:
            print(f"  {impl}")
        
        # Should have WebSocket implementations (at least the SSOT ones)
        assert len(websocket_implementations) > 0, "No WebSocket implementations found"
        
        # Check for SSOT WebSocket files
        expected_ssot_files = [
            "WebSocketBridgeClient.ts",
            "webSocketService.ts", 
            "useWebSocket.ts"
        ]
        
        found_ssot_files = []
        for impl in websocket_implementations:
            for expected_file in expected_ssot_files:
                if expected_file in impl:
                    found_ssot_files.append(expected_file)
        
        # Should have key SSOT WebSocket implementations
        assert len(found_ssot_files) > 0, f"No SSOT WebSocket files found. Expected: {expected_ssot_files}"
        
        # Verify SSOT import patterns
        import_violations = self.scanner.check_websocket_import_violations()
        
        if import_violations:
            print(f"\nFound {len(import_violations)} import violations:")
            for violation in import_violations:
                print(f"  {violation}")
        
        assert len(import_violations) == 0, f"SSOT import violations found: {import_violations}"

    @pytest.mark.unit
    def test_demo_service_http_usage_detection(self):
        """
        Test specific detection of demo service HTTP usage.
        Should FAIL initially if demo service uses HTTP for chat.
        """
        demo_service_file = self.scanner.frontend_root / "services" / "demoService.ts"
        
        if not demo_service_file.exists():
            pytest.skip("Demo service file not found")
        
        with open(demo_service_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for HTTP chat endpoint usage
        http_chat_patterns = [
            r'/api/demo/chat',
            r'POST.*?chat',
            r'sendChatMessage.*?fetch',
            r'method:\s*["\']POST["\']'
        ]
        
        violations_found = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            for pattern in http_chat_patterns:
                if re.search(pattern, line):
                    violations_found.append({
                        'line': line_num,
                        'pattern': pattern,
                        'code': line.strip()
                    })
        
        # Log violations for debugging
        if violations_found:
            print(f"\nFound {len(violations_found)} HTTP chat patterns in demo service:")
            for violation in violations_found:
                print(f"  Line {violation['line']}: {violation['pattern']}")
                print(f"    Code: {violation['code']}")
        
        # This should FAIL initially if demo service uses HTTP for chat
        assert len(violations_found) == 0, \
            f"Demo service HTTP chat usage detected: {violations_found}"

    @pytest.mark.unit
    def test_frontend_service_architecture_consistency(self):
        """
        Test frontend service architecture for consistency.
        Should FAIL if inconsistent transport patterns found.
        """
        services_dir = self.scanner.frontend_root / "services"
        
        if not services_dir.exists():
            pytest.skip("Frontend services directory not found")
        
        service_files = list(services_dir.rglob("*.ts"))
        
        transport_usage = {
            'websocket_services': [],
            'http_services': [],
            'dual_path_services': []
        }
        
        for service_file in service_files:
            try:
                with open(service_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                has_websocket = bool(re.search(r'websocket|WebSocket', content, re.IGNORECASE))
                has_http_post = bool(re.search(r'fetch.*?POST|POST.*?fetch|httpx\.post|axios\.post', content, re.IGNORECASE))
                has_chat_endpoints = bool(re.search(r'/chat|/message|/demo', content))
                
                service_name = service_file.name
                
                if has_websocket and has_http_post and has_chat_endpoints:
                    transport_usage['dual_path_services'].append(service_name)
                elif has_websocket:
                    transport_usage['websocket_services'].append(service_name)
                elif has_http_post and has_chat_endpoints:
                    transport_usage['http_services'].append(service_name)
                    
            except Exception as e:
                continue
        
        # Log transport usage analysis
        print(f"\nTransport usage analysis:")
        print(f"  WebSocket services: {transport_usage['websocket_services']}")
        print(f"  HTTP services: {transport_usage['http_services']}")
        print(f"  Dual-path services: {transport_usage['dual_path_services']}")
        
        # Should FAIL if dual-path services found
        assert len(transport_usage['dual_path_services']) == 0, \
            f"Dual-path services detected: {transport_usage['dual_path_services']}"
        
        # In SSOT pattern, should prefer WebSocket services
        if len(transport_usage['websocket_services']) > 0 and len(transport_usage['http_services']) > 0:
            # This indicates potential dual-path architecture
            print(f"WARNING: Both WebSocket and HTTP services found - potential dual-path architecture")
            
            # For Issue #1140, we want to detect this as a violation
            assert False, f"Mixed transport architecture detected: WebSocket={len(transport_usage['websocket_services'])}, HTTP={len(transport_usage['http_services'])}"

    @pytest.mark.unit
    @pytest.mark.architecture  
    @pytest.mark.issue_1140
    def test_backend_websocket_manager_ssot_compliance(self):
        """
        Test backend WebSocket manager for SSOT compliance.
        Should validate single authoritative WebSocket implementation.
        """
        websocket_managers = []
        backend_files = self.scanner._get_files_to_scan(self.scanner.backend_root, ['.py'])
        
        for file_path in backend_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for WebSocket manager classes
                if re.search(r'class.*?WebSocket.*?Manager|class.*?Manager.*?WebSocket', content, re.IGNORECASE):
                    websocket_managers.append(str(file_path))
                
                # Look for WebSocket bridge patterns
                if re.search(r'class.*?WebSocket.*?Bridge|class.*?Bridge.*?WebSocket', content, re.IGNORECASE):
                    websocket_managers.append(str(file_path))
                    
            except Exception as e:
                continue
        
        # Remove duplicates
        websocket_managers = list(set(websocket_managers))
        
        print(f"\nFound WebSocket managers: {websocket_managers}")
        
        # Should have at least one WebSocket manager (SSOT)
        assert len(websocket_managers) > 0, "No WebSocket managers found in backend"
        
        # Check for SSOT violations - multiple competing implementations
        if len(websocket_managers) > 3:  # Allow for some reasonable number
            print(f"WARNING: Many WebSocket managers found ({len(websocket_managers)}) - potential SSOT violation")
            
        # Verify expected SSOT files exist
        expected_websocket_files = [
            "websocket_core/manager.py",
            "websocket_core", 
            "websocket"
        ]
        
        found_expected = []
        for manager in websocket_managers:
            for expected in expected_websocket_files:
                if expected in manager:
                    found_expected.append(expected)
        
        assert len(found_expected) > 0, f"No expected SSOT WebSocket files found. Expected patterns: {expected_websocket_files}"

    @pytest.mark.unit
    def test_configuration_dual_path_detection(self):
        """
        Test configuration files for dual-path transport settings.
        Should FAIL if configuration enables dual transport paths.
        """
        config_violations = []
        
        # Check for configuration files
        config_patterns = [
            "config.ts", "config.js", "config.py",
            "settings.ts", "settings.js", "settings.py", 
            ".env*", "environment*"
        ]
        
        config_files = []
        for pattern in config_patterns:
            config_files.extend(self.scanner.project_root.rglob(pattern))
        
        dual_path_config_patterns = [
            r'transport.*?fallback',
            r'websocket.*?http.*?fallback',
            r'http.*?websocket.*?fallback',
            r'dual.*?transport',
            r'backup.*?transport',
            r'alternative.*?connection'
        ]
        
        for config_file in config_files:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    for pattern in dual_path_config_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            config_violations.append({
                                'file': str(config_file),
                                'line': line_num,
                                'pattern': pattern,
                                'code': line.strip()
                            })
                            
            except Exception as e:
                continue
        
        # Log configuration violations
        if config_violations:
            print(f"\nFound {len(config_violations)} configuration dual-path patterns:")
            for violation in config_violations:
                print(f"  {violation['file']}:{violation['line']} - {violation['pattern']}")
                print(f"    Code: {violation['code']}")
        
        # Should FAIL if dual-path configuration found
        assert len(config_violations) == 0, \
            f"Dual-path configuration detected: {config_violations}"