#!/usr/bin/env python3
"""
Validator Script Generator for Metadata Tracking
Generates the metadata validator script with proper validation logic.
"""

from pathlib import Path
from typing import Dict, Any


class ValidatorGenerator:
    """Generates validator script for metadata tracking."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.scripts_dir = project_root / "scripts"
    
    def create_script(self) -> bool:
        """Create validator script."""
        try:
            validator_path = self._get_path()
            content = self._generate_content()
            success = self._write_script(validator_path, content)
            
            if success:
                print(f"[SUCCESS] Validator script created at {validator_path}")
            
            return success
            
        except Exception as e:
            print(f"[ERROR] Failed to create validator script: {e}")
            return False
    
    def _get_path(self) -> Path:
        """Get validator script path."""
        return self.scripts_dir / "metadata_validator.py"
    
    def _generate_content(self) -> str:
        """Generate complete validator script content."""
        return f"""{self._get_imports()}

{self._get_class()}

{self._get_main()}
"""
    
    def _get_imports(self) -> str:
        """Get validator script imports."""
        return '''#!/usr/bin/env python3
"""
AI Agent Metadata Validator
Validates metadata headers in files modified by AI agents
"""

import os
import sys
import re
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse'''
    
    def _get_class(self) -> str:
        """Get validator class definition."""
        return f'''{self._get_class_header()}

{self._get_class_methods()}'''
    
    def _get_class_header(self) -> str:
        """Get validator class header."""
        return '''class MetadataValidator:
    """Validates AI agent metadata headers in project files"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.required_headers = [
            "AI_AGENT_NAME",
            "AI_AGENT_VERSION", 
            "AI_MODIFICATION_TIMESTAMP",
            "AI_TASK_DESCRIPTION"
        ]'''
    
    def _get_class_methods(self) -> str:
        """Get validator class methods."""
        return f'''{self._get_modified_files_method()}

{self._get_validate_file_method()}

{self._get_validate_all_method()}'''
    
    def _get_modified_files_method(self) -> str:
        """Get modified files detection method."""
        return '''    def get_modified_files(self) -> List[str]:
        """Get list of modified files from git"""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                return [f for f in result.stdout.strip().split('\\n') if f]
            return []
            
        except Exception:
            return []'''
    
    def _get_validate_file_method(self) -> str:
        """Get file validation method."""
        return '''    def validate_file(self, file_path: str) -> Dict[str, Any]:
        """Validate metadata headers in a single file"""
        try:
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                return {"valid": False, "error": "File not found"}
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for AI modification markers
            ai_pattern = r'# AI_AGENT_|// AI_AGENT_|<!-- AI_AGENT_'
            
            if not re.search(ai_pattern, content):
                return {"valid": True, "message": "No AI modifications detected"}
            
            # Validate required headers
            missing_headers = []
            for header in self.required_headers:
                pattern = f'(#|//|<!--)\\s*{header}:'
                if not re.search(pattern, content):
                    missing_headers.append(header)
            
            if missing_headers:
                return {
                    "valid": False,
                    "missing_headers": missing_headers,
                    "file": file_path
                }
            
            return {"valid": True, "message": "All metadata headers present"}
            
        except Exception as e:
            return {"valid": False, "error": str(e)}'''
    
    def _get_validate_all_method(self) -> str:
        """Get validate all method."""
        return '''    def validate_all(self) -> bool:
        """Validate all modified files"""
        modified_files = self.get_modified_files()
        
        if not modified_files:
            print("No modified files to validate")
            return True
        
        validation_failed = False
        
        for file_path in modified_files:
            result = self.validate_file(file_path)
            
            if not result["valid"]:
                validation_failed = True
                print(f"❌ {file_path}: {result.get('error', 'Validation failed')}")
                
                if "missing_headers" in result:
                    for header in result["missing_headers"]:
                        print(f"   Missing: {header}")
            else:
                print(f"✅ {file_path}: {result['message']}")
        
        return not validation_failed'''
    
    def _get_main(self) -> str:
        """Get main function."""
        return '''def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Validate AI agent metadata")
    parser.add_argument("--validate-all", action="store_true", 
                       help="Validate all modified files")
    parser.add_argument("--file", type=str, help="Validate specific file")
    
    args = parser.parse_args()
    validator = MetadataValidator()
    
    if args.validate_all:
        success = validator.validate_all()
        sys.exit(0 if success else 1)
    elif args.file:
        result = validator.validate_file(args.file)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["valid"] else 1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()'''
    
    def _write_script(self, validator_path: Path, content: str) -> bool:
        """Write validator script to file."""
        try:
            validator_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(validator_path, 'w') as f:
                f.write(content)
            
            # Make script executable on Unix systems
            try:
                import stat
                current_mode = validator_path.stat().st_mode
                validator_path.chmod(current_mode | stat.S_IEXEC)
            except:
                pass  # Windows doesn't need executable permissions
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to write validator script: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get validator script status."""
        validator_path = self._get_path()
        
        return {
            "validator_script_exists": validator_path.exists(),
            "validator_path": str(validator_path)
        }