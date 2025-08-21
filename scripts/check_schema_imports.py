#!/usr/bin/env python3
"""
Schema Import Violation Detector

This script identifies and reports schema import violations in the Netra codebase.
It enforces the principle that schemas should be imported from their canonical location
in the schemas directory, not from sub-modules or other locations.

Correct pattern:
    from netra_backend.app.schemas.request import RequestModel
    
Wrong patterns:
    from netra_backend.app.schemas.unified_tools import RequestModel
    from netra_backend.app.agents.some_agent.schemas import SomeSchema
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass, field
import json
from collections import defaultdict
import re


@dataclass
class SchemaViolation:
    """Represents a schema import violation"""
    file_path: str
    line_number: int
    import_statement: str
    imported_from: str
    imported_items: List[str]
    violation_type: str
    suggested_fix: Optional[str] = None
    
    def to_dict(self):
        return {
            'file_path': self.file_path,
            'line_number': self.line_number,
            'import_statement': self.import_statement,
            'imported_from': self.imported_from,
            'imported_items': self.imported_items,
            'violation_type': self.violation_type,
            'suggested_fix': self.suggested_fix
        }


@dataclass
class SchemaDefinition:
    """Represents a schema definition in the codebase"""
    file_path: str
    class_name: str
    module_path: str
    is_canonical: bool
    
    
@dataclass 
class ImportAnalysis:
    """Analysis results for schema imports"""
    violations: List[SchemaViolation] = field(default_factory=list)
    schema_definitions: List[SchemaDefinition] = field(default_factory=list)
    statistics: Dict = field(default_factory=dict)
    

class SchemaImportAnalyzer:
    """Analyzes Python files for schema import violations"""
    
    # Canonical schema paths
    CANONICAL_SCHEMA_PATHS = [
        'netra_backend/app/schemas',
        'auth_service/app/schemas',
        'frontend/schemas'
    ]
    
    # Patterns that indicate non-canonical schema locations
    NON_CANONICAL_PATTERNS = [
        r'\.routes\.[^.]+\.schemas',
        r'\.agents\.[^.]+\.schemas',
        r'\.services\.[^.]+\.schemas',
        r'\.handlers\.[^.]+\.schemas',
        r'\.utils\.[^.]+\.schemas',
        r'\.tests\.[^.]+\.schemas',
    ]
    
    # Known schema classes (will be populated by scanning)
    KNOWN_SCHEMAS: Dict[str, str] = {}
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.analysis = ImportAnalysis()
        self._build_schema_registry()
        
    def _build_schema_registry(self):
        """Build a registry of all schema classes in the codebase"""
        print("Building schema registry...")
        
        for path_pattern in self.CANONICAL_SCHEMA_PATHS:
            schema_dir = self.root_path / path_pattern
            if schema_dir.exists():
                self._scan_directory_for_schemas(schema_dir, is_canonical=True)
                
        # Also scan for schemas in non-canonical locations
        for root, dirs, files in os.walk(self.root_path):
            root_path = Path(root)
            
            # Skip test directories and __pycache__
            if '__pycache__' in root or 'test' in root.lower():
                continue
                
            if root_path.name == 'schemas' and not self._is_canonical_path(root_path):
                self._scan_directory_for_schemas(root_path, is_canonical=False)
                
        print(f"Found {len(self.analysis.schema_definitions)} schema definitions")
        
    def _is_canonical_path(self, path: Path) -> bool:
        """Check if a path is in a canonical schema location"""
        path_str = str(path.relative_to(self.root_path)).replace('\\', '/')
        for canonical in self.CANONICAL_SCHEMA_PATHS:
            if path_str.startswith(canonical):
                return True
        return False
        
    def _scan_directory_for_schemas(self, directory: Path, is_canonical: bool):
        """Scan a directory for schema definitions"""
        for file_path in directory.rglob('*.py'):
            if file_path.name.startswith('__'):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read(), filename=str(file_path))
                    
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Check if it's likely a schema class
                        if self._is_schema_class(node):
                            rel_path = file_path.relative_to(self.root_path)
                            module_path = str(rel_path.with_suffix('')).replace(os.sep, '.')
                            
                            schema_def = SchemaDefinition(
                                file_path=str(rel_path),
                                class_name=node.name,
                                module_path=module_path,
                                is_canonical=is_canonical
                            )
                            self.analysis.schema_definitions.append(schema_def)
                            
                            if is_canonical:
                                self.KNOWN_SCHEMAS[node.name] = module_path
                                
            except Exception as e:
                print(f"Error scanning {file_path}: {e}")
                
    def _is_schema_class(self, node: ast.ClassDef) -> bool:
        """Determine if a class is likely a schema"""
        # Check class name patterns
        if any(pattern in node.name.lower() for pattern in ['schema', 'model', 'request', 'response', 'dto']):
            return True
            
        # Check base classes
        for base in node.bases:
            if isinstance(base, ast.Name):
                if any(pattern in base.id.lower() for pattern in ['base', 'schema', 'model', 'pydantic']):
                    return True
            elif isinstance(base, ast.Attribute):
                if any(pattern in base.attr.lower() for pattern in ['base', 'schema', 'model']):
                    return True
                    
        return False
        
    def analyze_file(self, file_path: Path) -> List[SchemaViolation]:
        """Analyze a single Python file for schema import violations"""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content, filename=str(file_path))
                
            lines = content.splitlines()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        violation = self._check_import(
                            file_path, 
                            alias.name, 
                            [], 
                            node.lineno,
                            lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                        )
                        if violation:
                            violations.append(violation)
                            
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported_items = [alias.name for alias in node.names]
                        violation = self._check_import(
                            file_path,
                            node.module,
                            imported_items,
                            node.lineno,
                            lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                        )
                        if violation:
                            violations.append(violation)
                            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            
        return violations
        
    def _check_import(self, file_path: Path, module: str, items: List[str], 
                     line_number: int, line_content: str) -> Optional[SchemaViolation]:
        """Check if an import statement violates schema import rules"""
        
        # Check if this is importing from a non-canonical schema location
        for pattern in self.NON_CANONICAL_PATTERNS:
            if re.search(pattern, module):
                # This is importing from a non-canonical location
                violation_type = "non_canonical_import"
                
                # Try to find the canonical location for these schemas
                suggested_fix = None
                if items:
                    for item in items:
                        if item in self.KNOWN_SCHEMAS:
                            canonical_module = self.KNOWN_SCHEMAS[item]
                            suggested_fix = f"from {canonical_module} import {item}"
                            break
                            
                return SchemaViolation(
                    file_path=str(file_path.relative_to(self.root_path)),
                    line_number=line_number,
                    import_statement=line_content.strip(),
                    imported_from=module,
                    imported_items=items,
                    violation_type=violation_type,
                    suggested_fix=suggested_fix
                )
                
        # Check for other types of violations
        # For example, importing schemas from test modules
        if 'test' in module.lower() and 'schemas' in module:
            return SchemaViolation(
                file_path=str(file_path.relative_to(self.root_path)),
                line_number=line_number,
                import_statement=line_content.strip(),
                imported_from=module,
                imported_items=items,
                violation_type="test_schema_import",
                suggested_fix="Move schema to canonical location or use test fixtures"
            )
            
        return None
        
    def analyze_codebase(self):
        """Analyze the entire codebase for schema import violations"""
        print("Analyzing codebase for schema import violations...")
        
        python_files = []
        for pattern in ['**/*.py']:
            python_files.extend(self.root_path.glob(pattern))
            
        total_files = len(python_files)
        files_with_violations = 0
        
        for i, file_path in enumerate(python_files, 1):
            # Skip test files for now (unless they have violations)
            rel_path = file_path.relative_to(self.root_path)
            
            # Skip __pycache__ and migration files
            if '__pycache__' in str(rel_path) or 'migration' in str(rel_path):
                continue
                
            if i % 100 == 0:
                print(f"Progress: {i}/{total_files} files analyzed")
                
            violations = self.analyze_file(file_path)
            if violations:
                files_with_violations += 1
                self.analysis.violations.extend(violations)
                
        # Calculate statistics
        self.analysis.statistics = {
            'total_files_analyzed': total_files,
            'files_with_violations': files_with_violations,
            'total_violations': len(self.analysis.violations),
            'violation_types': defaultdict(int),
            'most_common_violations': [],
            'canonical_schemas_found': len([s for s in self.analysis.schema_definitions if s.is_canonical]),
            'non_canonical_schemas_found': len([s for s in self.analysis.schema_definitions if not s.is_canonical])
        }
        
        # Count violation types
        for violation in self.analysis.violations:
            self.analysis.statistics['violation_types'][violation.violation_type] += 1
            
        print(f"\nAnalysis complete: {len(self.analysis.violations)} violations found")
        
    def generate_report(self) -> str:
        """Generate a detailed report of schema import violations"""
        report = []
        report.append("=" * 80)
        report.append("SCHEMA IMPORT VIOLATION REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary statistics
        report.append("SUMMARY")
        report.append("-" * 40)
        stats = self.analysis.statistics
        report.append(f"Total files analyzed: {stats['total_files_analyzed']}")
        report.append(f"Files with violations: {stats['files_with_violations']}")
        report.append(f"Total violations: {stats['total_violations']}")
        report.append(f"Canonical schemas found: {stats['canonical_schemas_found']}")
        report.append(f"Non-canonical schemas found: {stats['non_canonical_schemas_found']}")
        report.append("")
        
        # Violation type breakdown
        report.append("VIOLATION TYPES")
        report.append("-" * 40)
        for vtype, count in stats['violation_types'].items():
            report.append(f"  {vtype}: {count}")
        report.append("")
        
        # Non-canonical schema locations
        if self.analysis.schema_definitions:
            non_canonical = [s for s in self.analysis.schema_definitions if not s.is_canonical]
            if non_canonical:
                report.append("NON-CANONICAL SCHEMA LOCATIONS")
                report.append("-" * 40)
                locations = defaultdict(list)
                for schema in non_canonical:
                    dir_path = os.path.dirname(schema.file_path)
                    locations[dir_path].append(schema.class_name)
                    
                for location, schemas in sorted(locations.items()):
                    report.append(f"\n  {location}/")
                    for schema in sorted(schemas):
                        report.append(f"    - {schema}")
                report.append("")
                
        # Detailed violations
        report.append("DETAILED VIOLATIONS")
        report.append("-" * 40)
        
        # Group violations by file
        violations_by_file = defaultdict(list)
        for violation in self.analysis.violations:
            violations_by_file[violation.file_path].append(violation)
            
        for file_path in sorted(violations_by_file.keys()):
            violations = violations_by_file[file_path]
            report.append(f"\n{file_path}")
            report.append("  " + "=" * 60)
            
            for violation in sorted(violations, key=lambda v: v.line_number):
                report.append(f"  Line {violation.line_number}: {violation.violation_type}")
                report.append(f"    Current: {violation.import_statement}")
                if violation.suggested_fix:
                    report.append(f"    Suggested: {violation.suggested_fix}")
                report.append("")
                
        # Recommended actions
        report.append("RECOMMENDED ACTIONS")
        report.append("-" * 40)
        report.append("1. Move all schema definitions to canonical locations:")
        for path in self.CANONICAL_SCHEMA_PATHS:
            report.append(f"   - {path}/")
        report.append("")
        report.append("2. Update all imports to use canonical paths")
        report.append("3. Remove duplicate schema definitions")
        report.append("4. Consider creating a schema index for easier discovery")
        report.append("")
        
        return "\n".join(report)
        
    def export_violations_json(self, output_path: str):
        """Export violations to a JSON file for programmatic fixing"""
        data = {
            'summary': self.analysis.statistics,
            'violations': [v.to_dict() for v in self.analysis.violations],
            'schema_definitions': [
                {
                    'file_path': s.file_path,
                    'class_name': s.class_name,
                    'module_path': s.module_path,
                    'is_canonical': s.is_canonical
                }
                for s in self.analysis.schema_definitions
            ],
            'canonical_schema_mapping': self.KNOWN_SCHEMAS
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            
        print(f"Violations exported to {output_path}")
        

def main():
    """Main entry point"""
    # Get the root path of the project
    script_dir = Path(__file__).parent
    root_path = script_dir.parent
    
    print(f"Analyzing schema imports in: {root_path}")
    print("=" * 80)
    
    # Create analyzer and run analysis
    analyzer = SchemaImportAnalyzer(root_path)
    analyzer.analyze_codebase()
    
    # Generate and print report
    report = analyzer.generate_report()
    print(report)
    
    # Save report to file
    report_path = root_path / "reports" / "schema_import_violations.txt"
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")
    
    # Export violations as JSON for automated fixing
    json_path = root_path / "reports" / "schema_import_violations.json"
    analyzer.export_violations_json(str(json_path))
    
    # Return exit code based on violations found
    if analyzer.analysis.violations:
        print(f"\n[WARNING] Found {len(analyzer.analysis.violations)} schema import violations")
        return 1
    else:
        print("\n[SUCCESS] No schema import violations found")
        return 0
        

if __name__ == "__main__":
    sys.exit(main())