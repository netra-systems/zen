#!/usr/bin/env python3
"""
Script Generator Base - Common utilities for script generation
Focused module for script generation functionality
"""

import os
from pathlib import Path


class ScriptGeneratorBase:
    """Base class for script generation utilities"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.scripts_dir = self._get_scripts_directory()

    def _get_scripts_directory(self) -> Path:
        """Get scripts directory path"""
        return self.project_root / "scripts"

    def _ensure_scripts_directory(self) -> None:
        """Ensure scripts directory exists"""
        self.scripts_dir.mkdir(parents=True, exist_ok=True)

    def _write_script_file(self, script_path: Path, content: str) -> bool:
        """Write script content to file"""
        try:
            with open(script_path, 'w') as f:
                f.write(content)
            return True
        except Exception:
            return False

    def _make_executable(self, file_path: Path) -> None:
        """Make script file executable"""
        os.chmod(file_path, 0o755)

    def _create_script(self, filename: str, content: str) -> bool:
        """Create script file with content and permissions"""
        try:
            self._ensure_scripts_directory()
            script_path = self.scripts_dir / filename
            
            if self._write_script_file(script_path, content):
                self._make_executable(script_path)
                print(f"[SUCCESS] Script created at {script_path}")
                return True
            else:
                print(f"[ERROR] Failed to write script file {script_path}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Failed to create script {filename}: {e}")
            return False

    def _get_script_header(self, description: str) -> str:
        """Get standard script header"""
        return f'''#!/usr/bin/env python3
"""
{description}
"""

'''

    def _get_standard_imports(self) -> str:
        """Get standard imports for metadata scripts"""
        return '''import os
import sys
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Any'''

    def _get_argparse_imports(self) -> str:
        """Get argparse imports"""
        return 'import argparse'

    def _combine_imports(self, *import_blocks) -> str:
        """Combine multiple import blocks"""
        combined = []
        for block in import_blocks:
            if block.strip():
                combined.append(block.strip())
        return '\n'.join(combined)

    def script_exists(self, filename: str) -> bool:
        """Check if script file exists"""
        script_path = self.scripts_dir / filename
        return script_path.exists()

    def validate_script_content(self, filename: str, expected_content: str) -> bool:
        """Validate script contains expected content"""
        try:
            script_path = self.scripts_dir / filename
            if not script_path.exists():
                return False
                
            with open(script_path, 'r') as f:
                content = f.read()
            return expected_content in content
        except Exception:
            return False