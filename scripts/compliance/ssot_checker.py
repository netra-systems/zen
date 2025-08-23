#!/usr/bin/env python3
"""
Single Source of Truth (SSOT) compliance checker.
Enforces CLAUDE.md SSOT principles - no duplicate implementations.
"""

import ast
import glob
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

from scripts.compliance.core import ComplianceConfig, Violation


class SSOTChecker:
    """Checks for Single Source of Truth violations"""
    
    def __init__(self, config: ComplianceConfig):
        self.config = config
    
    def check_ssot_violations(self) -> List[Violation]:
        """Check for SSOT violations - duplicate implementations"""
        violations = []
        
        # Check for duplicate function implementations
        violations.extend(self._check_duplicate_functions())
        
        # Check for similar handler patterns
        violations.extend(self._check_duplicate_handlers())
        
        return violations
    
    def _check_duplicate_functions(self) -> List[Violation]:
        """Check for duplicate function implementations across files"""
        violations = []
        function_map = defaultdict(list)
        
        patterns = self.config.get_python_patterns()
        for pattern in patterns:
            filepaths = glob.glob(str(self.config.root_path / pattern), recursive=True)
            for filepath in filepaths:
                if self.config.should_skip_file(filepath):
                    continue
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        tree = ast.parse(f.read())
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            # Look for functions with similar patterns
                            func_signature = self._get_function_signature(node)
                            rel_path = str(Path(filepath).relative_to(self.config.root_path))
                            function_map[func_signature].append((rel_path, node.name))
                
                except Exception:
                    continue
        
        # Find duplicates
        for signature, locations in function_map.items():
            if len(locations) > 1:
                # Check if these are truly duplicates (not just similar signatures)
                if self._are_likely_duplicates(signature, locations):
                    files = [loc[0] for loc in locations]
                    func_names = list(set(loc[1] for loc in locations))
                    violations.append(Violation(
                        file_path=", ".join(files[:2]) + ("..." if len(files) > 2 else ""),
                        violation_type="ssot_violation",
                        severity="high",
                        description=f"Duplicate function pattern '{func_names[0]}' in {len(files)} files",
                        fix_suggestion="Consolidate into single implementation and reuse",
                        actual_value=len(files),
                        expected_value=1
                    ))
        
        return violations
    
    def _check_duplicate_handlers(self) -> List[Violation]:
        """Check for duplicate handler/manager patterns"""
        violations = []
        handler_patterns = defaultdict(list)
        
        patterns = self.config.get_python_patterns()
        for pattern in patterns:
            filepaths = glob.glob(str(self.config.root_path / pattern), recursive=True)
            for filepath in filepaths:
                if self.config.should_skip_file(filepath):
                    continue
                
                filename = Path(filepath).stem
                rel_path = str(Path(filepath).relative_to(self.config.root_path))
                
                # Check for handler/manager patterns with similar names
                if 'handler' in filename.lower():
                    base_name = filename.lower().replace('_handler', '').replace('handler', '')
                    handler_patterns[f"handler_{base_name}"].append(rel_path)
                elif 'manager' in filename.lower():
                    base_name = filename.lower().replace('_manager', '').replace('manager', '')
                    handler_patterns[f"manager_{base_name}"].append(rel_path)
        
        # Find duplicates
        for pattern, files in handler_patterns.items():
            if len(files) > 1:
                # Filter out test files
                non_test_files = [f for f in files if not self.config.is_test_file(f)]
                if len(non_test_files) > 1:
                    violations.append(Violation(
                        file_path=", ".join(non_test_files[:2]) + ("..." if len(non_test_files) > 2 else ""),
                        violation_type="ssot_violation",
                        severity="medium",
                        description=f"Multiple {pattern.split('_')[0]}s for similar functionality",
                        fix_suggestion="Consider consolidating into single handler/manager",
                        actual_value=len(non_test_files),
                        expected_value=1
                    ))
        
        return violations
    
    def _get_function_signature(self, node: ast.FunctionDef) -> str:
        """Extract function signature for comparison"""
        # Get parameter names (excluding self)
        params = []
        for arg in node.args.args:
            if arg.arg != 'self':
                params.append(arg.arg)
        
        # Create a signature based on function characteristics
        has_async = isinstance(node, ast.AsyncFunctionDef)
        num_lines = node.end_lineno - node.lineno if node.end_lineno else 0
        
        # Group by similar characteristics
        if num_lines < 5:
            size = "small"
        elif num_lines < 20:
            size = "medium"
        else:
            size = "large"
        
        # Look for common patterns in function names
        name_pattern = "generic"
        if "create" in node.name.lower():
            name_pattern = "create"
        elif "update" in node.name.lower():
            name_pattern = "update"
        elif "delete" in node.name.lower():
            name_pattern = "delete"
        elif "get" in node.name.lower() or "fetch" in node.name.lower():
            name_pattern = "get"
        elif "handle" in node.name.lower():
            name_pattern = "handle"
        elif "process" in node.name.lower():
            name_pattern = "process"
        
        return f"{name_pattern}_{len(params)}params_{size}_{has_async}"
    
    def _are_likely_duplicates(self, signature: str, locations: List[tuple]) -> bool:
        """Determine if functions with similar signatures are likely duplicates"""
        # Don't flag as duplicates if they're in test files vs production
        test_files = [loc for loc in locations if self.config.is_test_file(loc[0])]
        prod_files = [loc for loc in locations if not self.config.is_test_file(loc[0])]
        
        # Only flag if multiple production files have similar implementations
        if len(prod_files) > 1:
            # Check if they have very similar names
            func_names = [loc[1] for loc in prod_files]
            if len(set(func_names)) == 1:  # Same function name
                return True
            
            # Check for obvious pattern duplicates
            if signature.startswith("handle_") or signature.startswith("process_"):
                return True
        
        return False