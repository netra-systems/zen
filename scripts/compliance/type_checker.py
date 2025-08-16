#!/usr/bin/env python3
"""
Type duplication compliance checker.
Enforces CLAUDE.md single source of truth for type definitions.
"""

import glob
import re
from collections import defaultdict
from pathlib import Path
from typing import List, Dict

from .core import Violation, ComplianceConfig, ViolationBuilder


class TypeChecker:
    """Checks for duplicate type definitions"""
    
    def __init__(self, config: ComplianceConfig):
        self.config = config
    
    def check_duplicate_types(self) -> List[Violation]:
        """Find duplicate type definitions (excluding legitimate cases)"""
        type_definitions = defaultdict(list)
        self._scan_python_types(type_definitions)
        self._scan_typescript_types(type_definitions)
        filtered_defs = self._filter_legitimate_duplicates(type_definitions)
        return self._create_duplicate_violations(filtered_defs)
    
    def _scan_python_types(self, type_definitions: Dict) -> None:
        """Scan Python files for class definitions"""
        pattern = 'app/**/*.py'
        filepaths = self._get_matching_files(pattern)
        for filepath in filepaths:
            if not self.config.should_skip_file(filepath):
                self._extract_python_types(filepath, type_definitions)
    
    def _get_matching_files(self, pattern: str) -> List[str]:
        """Get files matching pattern"""
        return glob.glob(str(self.config.root_path / pattern), recursive=True)
    
    def _extract_python_types(self, filepath: str, type_definitions: Dict) -> None:
        """Extract Python type definitions from file"""
        try:
            content = self._read_file(filepath)
            rel_path = str(Path(filepath).relative_to(self.config.root_path))
            self._find_python_classes(content, rel_path, type_definitions)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    
    def _read_file(self, filepath: str) -> str:
        """Read file content"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _find_python_classes(self, content: str, rel_path: str, type_definitions: Dict) -> None:
        """Find Python class definitions in content"""
        for match in re.finditer(r'^class\s+(\w+)', content, re.MULTILINE):
            type_name = match.group(1)
            type_definitions[type_name].append(rel_path)
    
    def _scan_typescript_types(self, type_definitions: Dict) -> None:
        """Scan TypeScript files for type definitions"""
        patterns = self.config.get_typescript_patterns()
        for pattern in patterns:
            self._scan_typescript_pattern(pattern, type_definitions)
    
    def _scan_typescript_pattern(self, pattern: str, type_definitions: Dict) -> None:
        """Scan TypeScript files matching pattern"""
        filepaths = self._get_matching_files(pattern)
        for filepath in filepaths:
            if 'node_modules' not in filepath:
                self._extract_typescript_types(filepath, type_definitions)
    
    def _extract_typescript_types(self, filepath: str, type_definitions: Dict) -> None:
        """Extract TypeScript type definitions from file"""
        try:
            content = self._read_file(filepath)
            rel_path = str(Path(filepath).relative_to(self.config.root_path))
            self._find_typescript_types(content, rel_path, type_definitions)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    
    def _find_typescript_types(self, content: str, rel_path: str, type_definitions: Dict) -> None:
        """Find TypeScript type definitions in content"""
        for match in re.finditer(r'(?:interface|type)\s+(\w+)', content):
            type_name = match.group(1)
            type_definitions[type_name].append(rel_path)
    
    def _filter_legitimate_duplicates(self, type_definitions: Dict) -> Dict:
        """Filter out legitimate duplicates that shouldn't be violations"""
        filtered = {}
        for type_name, files in type_definitions.items():
            problematic_files = self._get_problematic_duplicates(type_name, files)
            if len(problematic_files) > 1:
                filtered[type_name] = problematic_files
        return filtered
    
    def _get_problematic_duplicates(self, type_name: str, files: List[str]) -> List[str]:
        """Identify which duplicate files are actually problematic"""
        categorized = self._categorize_files(files)
        return self._filter_by_legitimacy(categorized)
    
    def _categorize_files(self, files: List[str]) -> Dict[str, List[str]]:
        """Categorize files by type"""
        categories = {
            'test': [], 'backup': [], 'example': [], 
            'frontend': [], 'backend': []
        }
        for file in files:
            file_lower = file.lower()
            if any(x in file_lower for x in ['test', 'tests']):
                categories['test'].append(file)
            elif any(x in file_lower for x in ['backup', '_old', '_legacy']):
                categories['backup'].append(file)
            elif any(x in file_lower for x in ['example', 'demo', 'sample']):
                categories['example'].append(file)
            elif 'frontend' in file_lower:
                categories['frontend'].append(file)
            else:
                categories['backend'].append(file)
        return categories
    
    def _filter_by_legitimacy(self, categorized: Dict[str, List[str]]) -> List[str]:
        """Filter files to identify truly problematic duplicates"""
        problematic = []
        backend_filtered = self._filter_backend_files(categorized['backend'])
        if len(backend_filtered) > 1 and not self._are_legitimate_separations(backend_filtered):
            problematic.extend(backend_filtered)
        if len(categorized['frontend']) > 1 and not self._are_frontend_separations(categorized['frontend']):
            problematic.extend(categorized['frontend'])
        return problematic if problematic else []
    
    def _filter_backend_files(self, files: List[str]) -> List[str]:
        """Filter backend files to exclude legitimate patterns"""
        filtered = []
        for file in files:
            file_lower = file.lower()
            skip_patterns = ['schema', 'interface', 'types.py', 'models.py']
            if any(x in file_lower for x in skip_patterns):
                continue
            if 'db/' in file and 'services/' in file:
                continue
            filtered.append(file)
        return filtered
    
    def _are_legitimate_separations(self, files: List[str]) -> bool:
        """Check if files represent legitimate architectural separations"""
        has_agent = any('agents/' in f for f in files)
        has_service = any('services/' in f for f in files)
        if has_agent and has_service:
            return True
        has_db = any('db/' in f for f in files)
        has_domain = any(f for f in files if 'db/' not in f)
        if has_db and has_domain and len(files) == 2:
            return True
        return self._are_separated_modules(files)
    
    def _are_frontend_separations(self, files: List[str]) -> bool:
        """Check if frontend duplicates are legitimate separations"""
        has_global_types = any('types/' in f for f in files)
        has_component = any('components/' in f for f in files)
        return has_global_types and has_component and len(files) == 2
    
    def _are_separated_modules(self, files: List[str]) -> bool:
        """Check if files are intentionally separated modules"""
        if any('_old' in f for f in files) and any('_old' not in f for f in files):
            return True
        modules = set()
        for file in files:
            normalized = file.replace('\\', '/')
            parts = normalized.split('/')
            if 'agents' in parts:
                idx = parts.index('agents')
                if idx + 1 < len(parts):
                    modules.add(parts[idx + 1])
        return len(modules) > 1
    
    def _create_duplicate_violations(self, type_definitions: Dict) -> List[Violation]:
        """Create violations for duplicate type definitions"""
        violations = []
        for type_name, files in type_definitions.items():
            if len(files) > 1:
                violation = ViolationBuilder.duplicate_violation(type_name, files)
                violations.append(violation)
        return violations