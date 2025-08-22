#!/usr/bin/env python3
"""
Spec-code alignment checker for code review system.
Validates alignment between specifications and implementation.
"""

from typing import List, Tuple

from scripts.review.command_runner import CommandRunner
from scripts.review.core import ReviewConfig, ReviewData


class SpecChecker:
    """Checks alignment between specifications and code"""
    
    def __init__(self, config: ReviewConfig, command_runner: CommandRunner):
        self.config = config
        self.runner = command_runner
    
    def check_spec_code_alignment(self, review_data: ReviewData) -> None:
        """Check alignment between specifications and code"""
        print("\n[SPEC] Checking Spec-Code Alignment...")
        if not self._validate_spec_directory(review_data):
            return
        self._check_key_specifications(review_data)
        self._check_code_without_specs(review_data)
    
    def _validate_spec_directory(self, review_data: ReviewData) -> bool:
        """Validate that SPEC directory exists"""
        if not self.runner.check_directory_exists("SPEC"):
            review_data.issue_tracker.add_issue("high", "SPEC directory not found")
            return False
        return True
    
    def _check_key_specifications(self, review_data: ReviewData) -> None:
        """Check key specifications for corresponding implementations"""
        key_specs = self._get_key_spec_mappings()
        for spec_file, code_paths in key_specs:
            if self._spec_exists(spec_file):
                self._validate_implementations(spec_file, code_paths, review_data)
    
    def _get_key_spec_mappings(self) -> List[Tuple[str, List[str]]]:
        """Get key specification to code path mappings"""
        return [
            ("websockets.xml", ["app/ws_manager.py", "app/routes/websockets.py"]),
            ("subagents.xml", ["app/agents/", "app/services/agent_service.py"]),
            ("database.xml", ["app/services/database/", "app/db/"]),
            ("security.xml", ["app/auth/", "app/services/security_service.py"]),
        ]
    
    def _spec_exists(self, spec_file: str) -> bool:
        """Check if specification file exists"""
        return self.runner.check_file_exists(f"SPEC/{spec_file}")
    
    def _validate_implementations(self, spec_file: str, code_paths: List[str], 
                                 review_data: ReviewData) -> None:
        """Validate that implementations exist for specification"""
        for code_path in code_paths:
            if not self._implementation_exists(code_path):
                conflict = f"Spec {spec_file} exists but implementation missing: {code_path}"
                review_data.add_spec_conflict(conflict)
    
    def _implementation_exists(self, code_path: str) -> bool:
        """Check if implementation path exists"""
        return (self.runner.check_file_exists(code_path) or 
                self.runner.check_directory_exists(code_path))
    
    def _check_code_without_specs(self, review_data: ReviewData) -> None:
        """Check for important code modules without specifications"""
        important_modules = self._get_important_modules()
        for module in important_modules:
            if self._module_exists(module):
                self._check_module_spec_exists(module, review_data)
    
    def _get_important_modules(self) -> List[str]:
        """Get list of important modules to check"""
        return [
            "app/services/apex_optimizer_agent/",
            "app/services/state/",
            "app/services/cache/",
        ]
    
    def _module_exists(self, module: str) -> bool:
        """Check if module exists"""
        return self.runner.check_directory_exists(module)
    
    def _check_module_spec_exists(self, module: str, review_data: ReviewData) -> None:
        """Check if module has corresponding specification"""
        module_name = self._extract_module_name(module)
        if not self._find_matching_spec(module_name):
            print(f"  [WARN] No specification found for: {module}")
            review_data.issue_tracker.add_issue("medium", f"Code without specification: {module}")
    
    def _extract_module_name(self, module: str) -> str:
        """Extract module name from path"""
        return module.split('/')[-2] if module.endswith('/') else module.split('/')[-1]
    
    def _find_matching_spec(self, module_name: str) -> bool:
        """Find matching specification for module"""
        success, output = self.runner.run(f"find SPEC -name '*{module_name}*.xml'")
        return success and output.strip() != ""