#!/usr/bin/env python3
"""
Status Data Collection Module
Handles file scanning, pattern detection, and data gathering.
Complies with 450-line and 25-line function limits.
"""

import glob
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

try:
    from .status_types import (
        AgentSystemStatus,
        ApexOptimizerStatus,
        ApiSyncStatus,
        ComponentHealthData,
        IntegrationStatus,
        OAuthStatus,
        PatternMatch,
        StatusConfig,
        SubAgentInfo,
        SupervisorStatus,
        TestCoverageInfo,
        TestCoverageStatus,
        TestResults,
        WebSocketStatus,
    )
except ImportError:
    from status_types import (
        AgentSystemStatus,
        ApexOptimizerStatus,
        ApiSyncStatus,
        ComponentHealthData,
        IntegrationStatus,
        OAuthStatus,
        PatternMatch,
        StatusConfig,
        SubAgentInfo,
        SupervisorStatus,
        TestCoverageInfo,
        TestCoverageStatus,
        TestResults,
        WebSocketStatus,
    )


class StatusDataCollector:
    """Collects status data from codebase"""
    
    def __init__(self, config: StatusConfig):
        self.config = config
        self.project_root = config.project_root
    
    def load_spec_root(self) -> ET.Element:
        """Load XML specification"""
        tree = ET.parse(self.config.spec_path)
        return tree.getroot()
    
    def find_pattern_matches(self, file_path: Path, patterns: List[Dict]) -> List[PatternMatch]:
        """Search patterns in file"""
        results = []
        try:
            content = self._read_file_content(file_path)
            if content:
                results = self._scan_file_patterns(file_path, content, patterns)
        except Exception:
            pass  # Skip unreadable files
        return results
    
    def _read_file_content(self, file_path: Path) -> Optional[str]:
        """Read file content safely"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return None
    
    def _scan_file_patterns(self, file_path: Path, content: str, patterns: List[Dict]) -> List[PatternMatch]:
        """Scan content for patterns"""
        results = []
        lines = content.split('\n')
        for pattern_info in patterns:
            pattern_matches = self._find_pattern_in_lines(file_path, lines, pattern_info)
            results.extend(pattern_matches)
        return results
    
    def _find_pattern_in_lines(self, file_path: Path, lines: List[str], pattern_info: Dict) -> List[PatternMatch]:
        """Find pattern in file lines"""
        matches = []
        pattern = pattern_info.get('pattern', '')
        pattern_type = pattern_info.get('type', 'general')
        priority = pattern_info.get('priority', 'medium')
        
        for line_num, line in enumerate(lines, 1):
            if re.search(pattern, line, re.IGNORECASE):
                match = self._create_pattern_match(file_path, line_num, line, pattern_type, priority, pattern)
                matches.append(match)
        return matches
    
    def _create_pattern_match(self, file_path: Path, line_num: int, line: str, 
                            pattern_type: str, priority: str, pattern: str) -> PatternMatch:
        """Create pattern match object"""
        return PatternMatch(
            file=str(file_path.relative_to(self.project_root)),
            line=line_num,
            content=line.strip(),
            type=pattern_type,
            priority=priority,
            pattern=pattern
        )


class ComponentHealthCollector:
    """Collects component health data"""
    
    def __init__(self, collector: StatusDataCollector):
        self.collector = collector
        self.project_root = collector.project_root
    
    def analyze_component_health(self, spec: ET.Element) -> Dict[str, ComponentHealthData]:
        """Analyze component health from spec"""
        health_data = {}
        category = spec.find(".//category[@id='component_health']")
        
        if category:
            for check in category.findall(".//check"):
                check_data = self._process_health_check(check)
                if check_data:
                    check_id = check.get('id')
                    health_data[check_id] = check_data
        
        return health_data
    
    def _process_health_check(self, check: ET.Element) -> Optional[ComponentHealthData]:
        """Process single health check"""
        check_id = check.get('id')
        target = check.find('target')
        patterns_elem = check.find('patterns')
        
        if target is None or patterns_elem is None:
            return None
        
        patterns = self._extract_patterns(patterns_elem)
        files = self._find_target_files(target.text)
        issues = self._scan_files_for_issues(files, patterns)
        
        return ComponentHealthData(
            total_files=len(files),
            issues_found=len(issues),
            details=issues[:self.collector.config.max_pattern_results]
        )
    
    def _extract_patterns(self, patterns_elem: ET.Element) -> List[Dict]:
        """Extract patterns from XML element"""
        patterns = []
        for pattern in patterns_elem.findall('pattern'):
            patterns.append({
                'pattern': pattern.text,
                'type': pattern.get('type', 'general')
            })
        return patterns
    
    def _find_target_files(self, target_pattern: str) -> List[str]:
        """Find files matching target pattern"""
        return glob.glob(
            str(self.project_root / target_pattern),
            recursive=True
        )
    
    def _scan_files_for_issues(self, files: List[str], patterns: List[Dict]) -> List[PatternMatch]:
        """Scan files for pattern issues"""
        all_issues = []
        for file_path in files:
            file_issues = self.collector.find_pattern_matches(Path(file_path), patterns)
            all_issues.extend(file_issues)
        return all_issues


class WipItemsCollector:
    """Collects work-in-progress items"""
    
    def __init__(self, collector: StatusDataCollector):
        self.collector = collector
        self.project_root = collector.project_root
    
    def collect_wip_items(self, spec: ET.Element) -> List[PatternMatch]:
        """Find all work-in-progress items"""
        wip_items = []
        category = spec.find(".//category[@id='work_in_progress']")
        
        if category:
            for check in category.findall(".//check"):
                check_wip = self._process_wip_check(check)
                wip_items.extend(check_wip)
        
        return wip_items
    
    def _process_wip_check(self, check: ET.Element) -> List[PatternMatch]:
        """Process single WIP check"""
        target = check.find('target')
        patterns_elem = check.find('patterns')
        
        if target is None or patterns_elem is None:
            return []
        
        patterns = self._extract_wip_patterns(patterns_elem)
        files = self._find_target_files(target.text)
        return self._scan_wip_files(files, patterns)
    
    def _extract_wip_patterns(self, patterns_elem: ET.Element) -> List[Dict]:
        """Extract WIP patterns"""
        patterns = []
        for pattern in patterns_elem.findall('pattern'):
            patterns.append({
                'pattern': pattern.text,
                'priority': pattern.get('priority', 'medium')
            })
        return patterns
    
    def _find_target_files(self, target_pattern: str) -> List[str]:
        """Find target files"""
        return glob.glob(
            str(self.project_root / target_pattern),
            recursive=True
        )
    
    def _scan_wip_files(self, files: List[str], patterns: List[Dict]) -> List[PatternMatch]:
        """Scan files for WIP patterns"""
        wip_items = []
        for file_path in files:
            file_wip = self.collector.find_pattern_matches(Path(file_path), patterns)
            wip_items.extend(file_wip)
        return wip_items


class TestResultsCollector:
    """Collects test execution results"""
    
    def __init__(self, config: StatusConfig):
        self.config = config
        self.project_root = config.project_root
    
    def run_quick_tests(self) -> TestResults:
        """Execute quick tests"""
        try:
            result = self._execute_test_command()
            return self._parse_test_results(result)
        except subprocess.TimeoutExpired:
            return self._create_timeout_result()
        except FileNotFoundError:
            return self._create_not_found_result()
        except Exception as e:
            return self._create_error_result(str(e))
    
    def _execute_test_command(self) -> subprocess.CompletedProcess:
        """Execute test runner command"""
        return subprocess.run(
            ["python", "test_runner.py", "--mode", "quick"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=self.config.timeout_seconds
        )
    
    def _parse_test_results(self, result: subprocess.CompletedProcess) -> TestResults:
        """Parse test execution results"""
        output = result.stdout + result.stderr
        passed = self._extract_test_count(output, 'passed')
        failed = self._extract_test_count(output, 'failed')
        errors = ["Test runner returned non-zero exit code"] if result.returncode != 0 else []
        
        return TestResults(
            executed=True,
            passed=passed,
            failed=failed,
            errors=errors
        )
    
    def _extract_test_count(self, output: str, test_type: str) -> int:
        """Extract test count from output"""
        matches = re.findall(rf'(\d+)\s+{test_type}', output, re.IGNORECASE)
        return int(matches[0]) if matches else 0
    
    def _create_timeout_result(self) -> TestResults:
        """Create timeout test result"""
        return TestResults(
            executed=False,
            passed=0,
            failed=0,
            errors=["Test execution timed out"]
        )
    
    def _create_not_found_result(self) -> TestResults:
        """Create not found test result"""
        return TestResults(
            executed=False,
            passed=0,
            failed=0,
            errors=["Test runner not found"]
        )
    
    def _create_error_result(self, error_msg: str) -> TestResults:
        """Create error test result"""
        return TestResults(
            executed=False,
            passed=0,
            failed=0,
            errors=[error_msg]
        )