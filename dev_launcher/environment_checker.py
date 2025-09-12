"""
Environment validation for development launcher.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from dev_launcher.utils import (
    check_dependencies,
    check_project_structure,
    print_with_emoji,
)

logger = logging.getLogger(__name__)


class EnvironmentChecker:
    """
    Validates development environment requirements.
    
    Checks dependencies, project structure, and system readiness
    for launching development services.
    """
    
    def __init__(self, project_root: Path, use_emoji: bool = True):
        """Initialize environment checker."""
        self.project_root = project_root
        self.use_emoji = use_emoji
    
    def _print(self, emoji: str, text: str, message: str):
        """Print with emoji support."""
        print_with_emoji(emoji, text, message, self.use_emoji)
    
    def check_environment(self) -> bool:
        """Check if environment is ready for launch."""
        self._print(" SEARCH: ", "CHECK", "Checking environment...")
        if not self._check_dependencies():
            return False
        if not self._check_project_structure():
            return False
        self._print(" PASS: ", "OK", "Environment check passed")
        return True
    
    def _check_dependencies(self) -> bool:
        """Check required dependencies."""
        deps = check_dependencies()
        missing_deps = self._get_missing_deps(deps)
        if missing_deps:
            self._print_missing_deps(missing_deps)
            return False
        return True
    
    def _get_missing_deps(self, deps: Dict) -> List[str]:
        """Get list of missing dependencies."""
        missing = []
        self._check_uvicorn_dep(deps, missing)
        self._check_fastapi_dep(deps, missing)
        self._check_node_dep(deps, missing)
        self._check_npm_dep(deps, missing)
        return missing
    
    def _check_uvicorn_dep(self, deps: Dict, missing: List[str]):
        """Check uvicorn dependency."""
        if not deps.get('uvicorn', False):
            missing.append('uvicorn (pip install uvicorn)')
    
    def _check_fastapi_dep(self, deps: Dict, missing: List[str]):
        """Check fastapi dependency."""
        if not deps.get('fastapi', False):
            missing.append('fastapi (pip install fastapi)')
    
    def _check_node_dep(self, deps: Dict, missing: List[str]):
        """Check Node.js dependency."""
        if not deps.get('node', False):
            missing.append('Node.js (visit nodejs.org)')
    
    def _check_npm_dep(self, deps: Dict, missing: List[str]):
        """Check npm dependency."""
        if not deps.get('npm', False):
            missing.append('npm (comes with Node.js)')
    
    def _print_missing_deps(self, missing_deps: List[str]):
        """Print missing dependencies error."""
        self._print(" FAIL: ", "ERROR", "Missing required dependencies:")
        for dep in missing_deps:
            print(f"     [U+2022] {dep}")
        print("\nInstall the missing dependencies and try again.")
    
    def _check_project_structure(self) -> bool:
        """Check project structure."""
        structure = check_project_structure(self.project_root)
        missing_structure = self._get_missing_structure(structure)
        if missing_structure:
            self._print_missing_structure(missing_structure)
            return False
        return True
    
    def _get_missing_structure(self, structure: Dict) -> List[str]:
        """Get list of missing structure elements."""
        missing = []
        self._check_backend_structure(structure, missing)
        self._check_frontend_structure(structure, missing)
        self._check_frontend_deps_structure(structure, missing)
        return missing
    
    def _check_backend_structure(self, structure: Dict, missing: List[str]):
        """Check backend structure."""
        if not structure.get('backend', False):
            missing.append('Backend directory (app/) not found')
    
    def _check_frontend_structure(self, structure: Dict, missing: List[str]):
        """Check frontend structure."""
        if not structure.get('frontend', False):
            missing.append('Frontend directory (frontend/) not found')
    
    def _check_frontend_deps_structure(self, structure: Dict, missing: List[str]):
        """Check frontend dependencies structure."""
        if not structure.get('frontend_deps', False):
            missing.append('Frontend dependencies not installed (run: cd frontend && npm install)')
    
    def _print_missing_structure(self, missing_structure: List[str]):
        """Print missing structure error."""
        self._print(" FAIL: ", "ERROR", "Invalid project structure:")
        for issue in missing_structure:
            print(f"     [U+2022] {issue}")
        print(f"\nMake sure you're running from the project root: {self.project_root}")