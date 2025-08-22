#!/usr/bin/env python3
"""
Schema Import Fixer

This script automatically fixes schema import violations by:
1. Moving schemas to canonical locations
2. Updating all imports to use the canonical paths
"""

import ast
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


class SchemaImportFixer:
    """Fixes schema import violations"""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.canonical_schema_dir = self.root_path / "netra_backend" / "app" / "schemas"
        self.fixes_applied = []
        self.schemas_moved = []
        
    def move_schemas_to_canonical_location(self):
        """Move non-canonical schemas to the canonical location"""
        
        # List of non-canonical schema locations to process
        non_canonical_locations = [
            self.root_path / "netra_backend" / "app" / "routes" / "unified_tools" / "schemas.py",
            self.root_path / "netra_backend" / "app" / "models" / "schemas.py",
            self.root_path / "netra_backend" / "app" / "configuration" / "schemas.py",
        ]
        
        for schema_file in non_canonical_locations:
            if schema_file.exists():
                self._move_schema_file(schema_file)
                
    def _move_schema_file(self, source_file: Path):
        """Move a schema file to the canonical location"""
        
        # Determine the new name for the schema file
        parent_name = source_file.parent.name
        if parent_name == "unified_tools":
            new_name = "unified_tools.py"
        elif parent_name == "models":
            new_name = "workload_models.py"  # More descriptive name
        elif parent_name == "configuration":
            new_name = "config.py"  # Already have configuration.py, use config.py
        else:
            new_name = f"{parent_name}_schemas.py"
            
        target_file = self.canonical_schema_dir / new_name
        
        # Ensure the canonical directory exists
        self.canonical_schema_dir.mkdir(parents=True, exist_ok=True)
        
        # Read the source file
        with open(source_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check if target already exists
        if target_file.exists():
            print(f"Warning: Target file {target_file} already exists. Merging content...")
            with open(target_file, 'r', encoding='utf-8') as f:
                existing_content = f.read()
                
            # Parse both files to merge classes
            source_tree = ast.parse(content)
            target_tree = ast.parse(existing_content)
            
            # Get class names from both
            source_classes = {node.name for node in ast.walk(source_tree) if isinstance(node, ast.ClassDef)}
            target_classes = {node.name for node in ast.walk(target_tree) if isinstance(node, ast.ClassDef)}
            
            # If there are new classes, append them
            new_classes = source_classes - target_classes
            if new_classes:
                # Extract the new class definitions
                lines = content.splitlines()
                new_content = []
                in_new_class = False
                class_indent = 0
                
                for i, line in enumerate(lines):
                    # Simple extraction - could be improved
                    if line.strip().startswith('class ') and any(cls in line for cls in new_classes):
                        in_new_class = True
                        class_indent = len(line) - len(line.lstrip())
                        new_content.append(line)
                    elif in_new_class:
                        if line.strip() and not line[class_indent:class_indent+1].isspace() and not line.strip().startswith('#'):
                            in_new_class = False
                        else:
                            new_content.append(line)
                            
                if new_content:
                    with open(target_file, 'a', encoding='utf-8') as f:
                        f.write('\n\n' + '\n'.join(new_content))
                        
                print(f"  Merged {len(new_classes)} new classes to {target_file}")
        else:
            # Just copy the file
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Moved {source_file} -> {target_file}")
            
        self.schemas_moved.append((str(source_file), str(target_file)))
        
        # Delete the original file
        source_file.unlink()
        print(f"  Deleted original file: {source_file}")
        
    def fix_imports_in_file(self, file_path: Path):
        """Fix imports in a single file"""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original_content = content
        
        # Define replacement patterns
        replacements = [
            # unified_tools schemas
            (r'from netra_backend\.app\.routes\.unified_tools\.schemas import',
             'from netra_backend.app.schemas.unified_tools import'),
            
            # models schemas  
            (r'from netra_backend\.app\.models\.schemas import',
             'from netra_backend.app.schemas.workload_models import'),
             
            # configuration schemas
            (r'from netra_backend\.app\.configuration\.schemas import',
             'from netra_backend.app.schemas.config import'),
        ]
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
            
        # Only write if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.fixes_applied.append(str(file_path))
            return True
            
        return False
        
    def fix_all_imports(self):
        """Fix imports in all Python files"""
        
        print("Fixing imports in all Python files...")
        
        # Get all Python files
        python_files = list(self.root_path.glob("**/*.py"))
        
        # Filter out virtual environments and cache
        python_files = [
            f for f in python_files 
            if not any(part in str(f) for part in ['venv', '.venv', '__pycache__', 'site-packages'])
        ]
        
        fixed_count = 0
        for file_path in python_files:
            if self.fix_imports_in_file(file_path):
                fixed_count += 1
                
        print(f"Fixed imports in {fixed_count} files")
        
    def update_init_files(self):
        """Update __init__.py files if needed"""
        
        # Check if schemas __init__ exists
        init_file = self.canonical_schema_dir / "__init__.py"
        
        if not init_file.exists():
            print(f"Creating {init_file}")
            init_file.touch()
            
        # Get all schema files in canonical location
        schema_files = [f for f in self.canonical_schema_dir.glob("*.py") if f.name != "__init__.py"]
        
        # Build import statements
        imports = []
        for schema_file in schema_files:
            module_name = schema_file.stem
            
            # Parse file to get exported classes
            with open(schema_file, 'r', encoding='utf-8') as f:
                try:
                    tree = ast.parse(f.read())
                    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
                    
                    if classes:
                        imports.append(f"from .{module_name} import {', '.join(classes)}")
                except:
                    pass
                    
        # Write __init__.py
        if imports:
            init_content = '"""Schema definitions for Netra Backend"""\n\n'
            init_content += '\n'.join(sorted(imports))
            init_content += '\n\n__all__ = [\n'
            
            # Extract all class names for __all__
            all_classes = []
            for imp in imports:
                # Parse the import statement
                match = re.search(r'import (.+)$', imp)
                if match:
                    classes = [c.strip() for c in match.group(1).split(',')]
                    all_classes.extend(classes)
                    
            for cls in sorted(all_classes):
                init_content += f'    "{cls}",\n'
            init_content += ']\n'
            
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write(init_content)
                
            print(f"Updated {init_file}")
            
    def generate_report(self):
        """Generate a report of all fixes applied"""
        
        report = []
        report.append("=" * 80)
        report.append("SCHEMA IMPORT FIX REPORT")
        report.append("=" * 80)
        report.append("")
        
        if self.schemas_moved:
            report.append("SCHEMAS MOVED TO CANONICAL LOCATION")
            report.append("-" * 40)
            for source, target in self.schemas_moved:
                report.append(f"  {source}")
                report.append(f"    -> {target}")
            report.append("")
            
        if self.fixes_applied:
            report.append(f"IMPORTS FIXED IN {len(self.fixes_applied)} FILES")
            report.append("-" * 40)
            for file_path in sorted(self.fixes_applied):
                # Show relative path
                try:
                    rel_path = Path(file_path).relative_to(self.root_path)
                    report.append(f"  {rel_path}")
                except:
                    report.append(f"  {file_path}")
            report.append("")
            
        report.append("SUMMARY")
        report.append("-" * 40)
        report.append(f"  Schemas moved: {len(self.schemas_moved)}")
        report.append(f"  Files with fixed imports: {len(self.fixes_applied)}")
        report.append("")
        
        return "\n".join(report)
        

def main():
    """Main entry point"""
    
    # Get the root path
    script_dir = Path(__file__).parent
    root_path = script_dir.parent
    
    print(f"Fixing schema imports in: {root_path}")
    print("=" * 80)
    
    # Create fixer
    fixer = SchemaImportFixer(root_path)
    
    # Step 1: Move schemas to canonical location
    print("\nStep 1: Moving schemas to canonical location...")
    fixer.move_schemas_to_canonical_location()
    
    # Step 2: Fix all imports
    print("\nStep 2: Fixing imports...")
    fixer.fix_all_imports()
    
    # Step 3: Update __init__ files
    print("\nStep 3: Updating __init__.py files...")
    fixer.update_init_files()
    
    # Generate report
    report = fixer.generate_report()
    print("\n" + report)
    
    # Save report
    report_path = root_path / "reports" / "schema_import_fixes.txt"
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"Report saved to: {report_path}")
    
    return 0
    

if __name__ == "__main__":
    sys.exit(main())