#!/usr/bin/env python3
"""
Validator Generator - Generates metadata validator script
Focused module for validator script creation
"""

from pathlib import Path

from scripts.metadata_tracking.script_generator import ScriptGeneratorBase


class ValidatorGenerator(ScriptGeneratorBase):
    """Generates metadata validator script"""

    def __init__(self, project_root: Path):
        super().__init__(project_root)
        self.script_filename = "metadata_validator.py"

    def _get_validator_imports(self) -> str:
        """Get validator script imports"""
        header = self._get_script_header("Metadata Validator - Validates AI agent metadata headers in modified files")
        standard_imports = self._get_standard_imports()
        additional_imports = '''import re
from datetime import datetime'''
        argparse_import = self._get_argparse_imports()
        
        return self._combine_imports(header, standard_imports, additional_imports, argparse_import)

    def _get_class_constants(self) -> str:
        """Get validator class constants"""
        return '''class MetadataValidator:
    """Validates metadata headers in files"""
    
    REQUIRED_FIELDS = [
        "Timestamp",
        "Agent", 
        "Context",
        "Git",
        "Change",
        "Session",
        "Review"
    ]
    
    def __init__(self):
        self.errors = []
        self.warnings = []'''

    def _get_modified_files_method(self) -> str:
        """Get modified files method"""
        return '''    def get_modified_files(self) -> List[str]:
        """Get list of modified files from git"""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True, text=True, check=True
            )
            return [f for f in result.stdout.splitlines() 
                   if f.endswith(('.py', '.js', '.ts', '.jsx', '.tsx'))]
        except subprocess.CalledProcessError:
            return []'''

    def _get_validate_file_method(self) -> str:
        """Get validate file method"""
        return '''    def validate_file(self, file_path: str) -> bool:
        """Validate metadata header in a single file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(2000)  # Read first 2000 chars
            
            if not self._check_metadata_header(content, file_path):
                return False
            
            if not self._validate_required_fields(content, file_path):
                return False
            
            self._validate_timestamp_format(content, file_path)
            return True
            
        except Exception as e:
            self.errors.append(f"{file_path}: Error reading file - {e}")
            return False'''

    def _get_helper_methods(self) -> str:
        """Get validator helper methods"""
        return '''    def _check_metadata_header(self, content: str, file_path: str) -> bool:
        """Check for metadata header presence"""
        if "AI AGENT MODIFICATION METADATA" not in content:
            self.errors.append(f"{file_path}: Missing metadata header")
            return False
        return True

    def _validate_required_fields(self, content: str, file_path: str) -> bool:
        """Validate all required fields are present"""
        for field in self.REQUIRED_FIELDS:
            if field not in content[:1000]:
                self.errors.append(f"{file_path}: Missing required field '{field}'")
                return False
        return True

    def _validate_timestamp_format(self, content: str, file_path: str) -> None:
        """Validate timestamp format"""
        timestamp_match = re.search(r'Timestamp:\\s*(\\S+)', content)
        if timestamp_match:
            timestamp = timestamp_match.group(1)
            try:
                datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                self.warnings.append(f"{file_path}: Invalid timestamp format")'''

    def _get_validate_all_method(self) -> str:
        """Get validate all method"""
        return '''    def validate_all(self) -> bool:
        """Validate all modified files"""
        files = self.get_modified_files()
        
        if not files:
            print("No modified files to validate")
            return True
        
        print(f"Validating {len(files)} modified files...")
        
        all_valid = self._process_files(files)
        self._print_results()
        
        return all_valid and not self.errors

    def _process_files(self, files: List[str]) -> bool:
        """Process all files for validation"""
        all_valid = True
        for file_path in files:
            if not self.validate_file(file_path):
                all_valid = False
        return all_valid

    def _print_results(self) -> None:
        """Print validation results"""
        if self.errors:
            print("\\n FAIL:  Validation Errors:")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print("\\n WARNING: [U+FE0F]  Validation Warnings:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if not self.errors and not self.warnings:
            print("\\n PASS:  All files have valid metadata headers")'''

    def _get_main_function(self) -> str:
        """Get main function"""
        return '''def main():
    parser = argparse.ArgumentParser(description="Validate AI agent metadata headers")
    parser.add_argument("--validate-all", action="store_true", 
                       help="Validate all modified files")
    parser.add_argument("--validate", help="Validate specific file")
    
    args = parser.parse_args()
    validator = MetadataValidator()
    
    if args.validate_all:
        success = validator.validate_all()
        sys.exit(0 if success else 1)
    elif args.validate:
        success = validator.validate_file(args.validate)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()'''

    def _generate_complete_content(self) -> str:
        """Generate complete validator script content"""
        imports = self._get_validator_imports()
        class_constants = self._get_class_constants()
        modified_files_method = self._get_modified_files_method()
        validate_file_method = self._get_validate_file_method()
        helper_methods = self._get_helper_methods()
        validate_all_method = self._get_validate_all_method()
        main_function = self._get_main_function()
        
        return f"""{imports}

{class_constants}

{modified_files_method}

{validate_file_method}

{helper_methods}

{validate_all_method}


{main_function}"""

    def create_validator_script(self) -> bool:
        """Create metadata validator script"""
        content = self._generate_complete_content()
        return self._create_script(self.script_filename, content)

    def validator_exists(self) -> bool:
        """Check if validator script exists"""
        return self.script_exists(self.script_filename)