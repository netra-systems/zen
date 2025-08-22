#!/usr/bin/env python3
"""
Authentication Constants Migration Utility

This script helps identify and migrate hardcoded auth-related strings to use
the centralized auth constants module.

Business Value: Platform/Internal - Reduces technical debt and improves
security consistency by eliminating hardcoded auth strings.

Usage:
    python scripts/auth_constants_migration.py --check
    python scripts/auth_constants_migration.py --migrate --dry-run
    python scripts/auth_constants_migration.py --migrate
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


class AuthConstantsMigrator:
    """Utility for migrating hardcoded auth strings to centralized constants."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.auth_constants_path = "app.core.auth_constants"
        
        # Define mappings from hardcoded strings to constants
        self.string_mappings = {
            # JWT constants
            '"JWT_SECRET_KEY"': 'JWTConstants.JWT_SECRET_KEY',
            '"FERNET_KEY"': 'JWTConstants.FERNET_KEY',
            '"access_token"': 'JWTConstants.ACCESS_TOKEN',
            '"refresh_token"': 'JWTConstants.REFRESH_TOKEN',
            '"token_type"': 'JWTConstants.TOKEN_TYPE',
            '"expires_in"': 'JWTConstants.EXPIRES_IN',
            '"access"': 'JWTConstants.ACCESS_TOKEN_TYPE',
            '"refresh"': 'JWTConstants.REFRESH_TOKEN_TYPE',
            '"service"': 'JWTConstants.SERVICE_TOKEN_TYPE',
            '"sub"': 'JWTConstants.SUBJECT',
            '"email"': 'JWTConstants.EMAIL',
            '"iat"': 'JWTConstants.ISSUED_AT',
            '"exp"': 'JWTConstants.EXPIRES_AT',
            '"iss"': 'JWTConstants.ISSUER',
            '"permissions"': 'JWTConstants.PERMISSIONS',
            '"netra-auth-service"': 'JWTConstants.NETRA_AUTH_SERVICE',
            '"HS256"': 'JWTConstants.HS256_ALGORITHM',
            
            # Header constants
            '"Authorization"': 'HeaderConstants.AUTHORIZATION',
            '"Content-Type"': 'HeaderConstants.CONTENT_TYPE',
            '"User-Agent"': 'HeaderConstants.USER_AGENT',
            '"Bearer "': 'HeaderConstants.BEARER_PREFIX',
            '"Basic "': 'HeaderConstants.BASIC_PREFIX',
            '"application/json"': 'HeaderConstants.APPLICATION_JSON',
            
            # Credential constants
            '"GOOGLE_CLIENT_ID"': 'CredentialConstants.GOOGLE_CLIENT_ID',
            '"GOOGLE_CLIENT_SECRET"': 'CredentialConstants.GOOGLE_CLIENT_SECRET',
            '"GEMINI_API_KEY"': 'CredentialConstants.GEMINI_API_KEY',
            '"api_key"': 'CredentialConstants.API_KEY',
            '"DATABASE_URL"': 'CredentialConstants.DATABASE_URL',
            '"password"': 'CredentialConstants.PASSWORD',
            
            # OAuth constants
            '"authorization_code"': 'OAuthConstants.AUTHORIZATION_CODE',
            '"client_id"': 'OAuthConstants.CLIENT_ID',
            '"client_secret"': 'OAuthConstants.CLIENT_SECRET',
            '"redirect_uri"': 'OAuthConstants.REDIRECT_URI',
            '"scope"': 'OAuthConstants.SCOPE',
            '"code"': 'OAuthConstants.CODE',
            '"state"': 'OAuthConstants.STATE',
            
            # Auth service constants
            '"auth_service_url"': 'AuthConstants.AUTH_SERVICE_URL',
            '"auth_service_enabled"': 'AuthConstants.AUTH_SERVICE_ENABLED',
            '"service_id"': 'AuthConstants.SERVICE_ID',
            '"service_secret"': 'AuthConstants.SERVICE_SECRET',
        }
        
        # Files to exclude from migration
        self.exclude_patterns = [
            r'.*__pycache__.*',
            r'.*\.pyc$',
            r'.*\.pyo$',
            r'.*\.git.*',
            r'.*node_modules.*',
            r'.*venv.*',
            r'.*\.venv.*',
            r'.*auth_constants\.py$',  # Don't modify the constants file itself
            r'.*test.*constants.*',    # Don't modify test constant files
        ]
        
        # Required import groups for different constants
        self.import_groups = {
            'JWTConstants': 'app.core.auth_constants',
            'HeaderConstants': 'app.core.auth_constants', 
            'CredentialConstants': 'app.core.auth_constants',
            'AuthConstants': 'app.core.auth_constants',
            'OAuthConstants': 'app.core.auth_constants',
            'AuthErrorConstants': 'app.core.auth_constants',
            'CacheConstants': 'app.core.auth_constants',
            'ValidationConstants': 'app.core.auth_constants',
        }
    
    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from migration."""
        file_str = str(file_path)
        return any(re.match(pattern, file_str) for pattern in self.exclude_patterns)
    
    def find_python_files(self) -> List[Path]:
        """Find all Python files in the project."""
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(re.match(pattern, os.path.join(root, d)) 
                                                 for pattern in self.exclude_patterns)]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    if not self.should_exclude_file(file_path):
                        python_files.append(file_path)
        
        return python_files
    
    def analyze_file(self, file_path: Path) -> Dict[str, List[Tuple[int, str]]]:
        """Analyze a file for hardcoded auth strings."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            return {}
        
        findings = {}
        
        for line_num, line in enumerate(lines, 1):
            for hardcoded_string, constant_name in self.string_mappings.items():
                if hardcoded_string in line:
                    # Skip if it's in a comment
                    comment_pos = line.find('#')
                    string_pos = line.find(hardcoded_string)
                    if comment_pos != -1 and string_pos > comment_pos:
                        continue
                    
                    if hardcoded_string not in findings:
                        findings[hardcoded_string] = []
                    findings[hardcoded_string].append((line_num, line.strip()))
        
        return findings
    
    def get_required_imports(self, findings: Dict[str, List]) -> Set[str]:
        """Determine required imports based on findings."""
        required_classes = set()
        
        for hardcoded_string in findings.keys():
            constant_name = self.string_mappings[hardcoded_string]
            class_name = constant_name.split('.')[0]
            required_classes.add(class_name)
        
        return required_classes
    
    def generate_import_statement(self, required_classes: Set[str]) -> str:
        """Generate import statement for required constants."""
        if not required_classes:
            return ""
        
        sorted_classes = sorted(required_classes)
        if len(sorted_classes) == 1:
            return f"from {self.auth_constants_path} import {sorted_classes[0]}"
        else:
            classes_str = ", ".join(sorted_classes)
            return f"from {self.auth_constants_path} import {classes_str}"
    
    def migrate_file(self, file_path: Path, dry_run: bool = True) -> bool:
        """Migrate a single file to use auth constants."""
        findings = self.analyze_file(file_path)
        if not findings:
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return False
        
        # Make replacements
        modified_content = content
        for hardcoded_string, constant_name in self.string_mappings.items():
            if hardcoded_string in findings:
                modified_content = modified_content.replace(hardcoded_string, constant_name)
        
        # Add import statement if needed
        required_classes = self.get_required_imports(findings)
        if required_classes:
            import_statement = self.generate_import_statement(required_classes)
            
            # Find a good place to insert the import
            lines = modified_content.split('\n')
            import_inserted = False
            
            # Look for existing imports
            for i, line in enumerate(lines):
                if line.strip().startswith('from netra_backend.app.core.auth_constants import'):
                    # Update existing import
                    existing_classes = self._extract_imported_classes(line)
                    all_classes = existing_classes.union(required_classes)
                    new_import = self.generate_import_statement(all_classes)
                    lines[i] = new_import
                    import_inserted = True
                    break
            
            if not import_inserted:
                # Find last import line
                last_import_index = -1
                for i, line in enumerate(lines):
                    if (line.strip().startswith('import ') or 
                        line.strip().startswith('from ')) and not line.strip().startswith('#'):
                        last_import_index = i
                
                if last_import_index >= 0:
                    lines.insert(last_import_index + 1, import_statement)
                else:
                    # Insert after docstring or at top
                    insert_index = 0
                    if lines and lines[0].strip().startswith('"""'):
                        for i in range(1, len(lines)):
                            if '"""' in lines[i]:
                                insert_index = i + 1
                                break
                    lines.insert(insert_index, import_statement)
            
            modified_content = '\n'.join(lines)
        
        if not dry_run:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                print(f"Migrated {file_path}")
            except Exception as e:
                print(f"Error writing {file_path}: {e}")
                return False
        else:
            print(f"Would migrate {file_path}")
        
        return True
    
    def _extract_imported_classes(self, import_line: str) -> Set[str]:
        """Extract class names from an import line."""
        # Parse "from netra_backend.app.core.auth_constants import Class1, Class2"
        if ' import ' in import_line:
            import_part = import_line.split(' import ')[1]
            classes = [cls.strip() for cls in import_part.split(',')]
            return set(classes)
        return set()
    
    def check_project(self) -> Dict[str, Dict]:
        """Check the entire project for hardcoded auth strings."""
        python_files = self.find_python_files()
        project_findings = {}
        
        print(f"Scanning {len(python_files)} Python files...")
        
        for file_path in python_files:
            findings = self.analyze_file(file_path)
            if findings:
                project_findings[str(file_path.relative_to(self.project_root))] = findings
        
        return project_findings
    
    def migrate_project(self, dry_run: bool = True) -> int:
        """Migrate the entire project."""
        python_files = self.find_python_files()
        migrated_count = 0
        
        print(f"{'Checking' if dry_run else 'Migrating'} {len(python_files)} Python files...")
        
        for file_path in python_files:
            if self.migrate_file(file_path, dry_run):
                migrated_count += 1
        
        return migrated_count
    
    def generate_report(self, findings: Dict) -> str:
        """Generate a detailed report of findings."""
        if not findings:
            return "No hardcoded auth strings found!"
        
        report_lines = [
            "Authentication Constants Migration Report",
            "=" * 50,
            ""
        ]
        
        total_occurrences = sum(len(file_findings) for file_findings in findings.values())
        report_lines.append(f"Found hardcoded auth strings in {len(findings)} files")
        report_lines.append(f"Total occurrences: {total_occurrences}")
        report_lines.append("")
        
        for file_path, file_findings in findings.items():
            report_lines.append(f"File: {file_path}")
            report_lines.append("-" * (len(file_path) + 6))
            
            for hardcoded_string, occurrences in file_findings.items():
                constant_name = self.string_mappings[hardcoded_string]
                report_lines.append(f"  {hardcoded_string} → {constant_name}")
                
                for line_num, line_content in occurrences:
                    report_lines.append(f"    Line {line_num}: {line_content}")
                
                report_lines.append("")
            
            report_lines.append("")
        
        # Add migration recommendations
        report_lines.extend([
            "Recommended Actions:",
            "1. Run: python scripts/auth_constants_migration.py --migrate --dry-run",
            "2. Review the proposed changes",
            "3. Run: python scripts/auth_constants_migration.py --migrate",
            "4. Test the application to ensure nothing broke",
            "5. Commit the changes",
            ""
        ])
        
        return "\n".join(report_lines)


def main():
    parser = argparse.ArgumentParser(description="Migrate hardcoded auth strings to centralized constants")
    parser.add_argument('--check', action='store_true', help='Check for hardcoded strings without migrating')
    parser.add_argument('--migrate', action='store_true', help='Perform migration')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    
    args = parser.parse_args()
    
    if not args.check and not args.migrate:
        parser.print_help()
        sys.exit(1)
    
    migrator = AuthConstantsMigrator(args.project_root)
    
    if args.check:
        findings = migrator.check_project()
        report = migrator.generate_report(findings)
        print(report)
        
        if findings:
            sys.exit(1)  # Exit with error code if issues found
    
    elif args.migrate:
        migrated_count = migrator.migrate_project(dry_run=args.dry_run)
        
        if args.dry_run:
            print(f"\nDry run complete. Would migrate {migrated_count} files.")
            print("Run without --dry-run to apply changes.")
        else:
            print(f"\nMigration complete! Updated {migrated_count} files.")
            print("Please test your application and commit the changes.")


if __name__ == '__main__':
    main()