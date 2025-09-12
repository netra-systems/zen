#!/usr/bin/env python3
"""
Simple Import Analysis - Static Analysis Only
Analyzes import statements without executing files to avoid runtime errors.
"""

import ast
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set


class SimpleImportAnalyzer:
    """Analyzes imports using static analysis only."""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.app_tests_path = self.base_path / "app" / "tests"
        self.app_path = self.base_path / "app"
        
        # Track all modules and imports
        self.all_imports = defaultdict(list)
        self.relative_imports = defaultdict(list)
        self.missing_modules = set()
        self.import_patterns = defaultdict(int)
        
        # Results structure
        self.results = {
            "summary": {
                "total_files_analyzed": 0,
                "files_with_imports": 0,
                "total_imports_found": 0,
                "relative_imports_count": 0,
                "potentially_missing_modules": 0,
                "scan_directory": str(self.app_tests_path)
            },
            "import_analysis": {
                "all_imports": {},
                "relative_imports": {},
                "import_patterns": {},
                "potentially_missing": []
            },
            "file_details": []
        }
    
    def parse_file_imports(self, file_path: Path) -> Dict[str, Any]:
        """Parse imports from a single file using AST."""
        file_info = {
            "file_path": str(file_path.relative_to(self.base_path)),
            "absolute_path": str(file_path),
            "file_size": file_path.stat().st_size,
            "imports": [],
            "relative_imports": [],
            "from_imports": [],
            "parsing_error": None
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the AST
            tree = ast.parse(content, filename=str(file_path))
            
            # Extract import information
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        import_info = {
                            "module": alias.name,
                            "alias": alias.asname,
                            "type": "import"
                        }
                        file_info["imports"].append(import_info)
                        self.all_imports[alias.name].append(str(file_path))
                        self.import_patterns[alias.name] += 1
                        
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    level = node.level
                    
                    import_info = {
                        "module": module,
                        "level": level,
                        "names": [alias.name for alias in node.names],
                        "type": "from_import"
                    }
                    
                    file_info["from_imports"].append(import_info)
                    
                    # Track relative imports
                    if level > 0:
                        file_info["relative_imports"].append(import_info)
                        self.relative_imports[module or "local"].append(str(file_path))
                    
                    # Track all modules
                    if module:
                        self.all_imports[module].append(str(file_path))
                        self.import_patterns[module] += 1
                        
        except SyntaxError as e:
            file_info["parsing_error"] = {
                "error_type": "SyntaxError",
                "message": str(e),
                "line": e.lineno,
                "offset": e.offset
            }
        except Exception as e:
            file_info["parsing_error"] = {
                "error_type": type(e).__name__,
                "message": str(e)
            }
        
        return file_info
    
    def check_module_existence(self, module_name: str) -> bool:
        """Check if a module likely exists based on common patterns."""
        
        # Standard library modules (partial list)
        stdlib_modules = {
            'os', 'sys', 'json', 'ast', 'pathlib', 'typing', 'collections',
            'datetime', 'time', 'traceback', 'importlib', 'asyncio', 'logging',
            'unittest', 'pytest', 're', 'uuid', 'hashlib', 'base64', 'urllib'
        }
        
        # Third-party common modules
        third_party = {
            'pytest', 'pydantic', 'fastapi', 'sqlalchemy', 'redis', 'requests',
            'pandas', 'numpy', 'clickhouse_driver', 'openai', 'anthropic'
        }
        
        # Check if it's a known module
        if module_name in stdlib_modules or module_name in third_party:
            return True
        
        # Check if it starts with app (our application)
        if module_name.startswith('app.'):
            # Check if the corresponding file/directory exists
            path_parts = module_name.split('.')
            check_path = self.base_path
            for part in path_parts:
                check_path = check_path / part
                if check_path.is_file() or (check_path / "__init__.py").exists():
                    continue
                else:
                    return False
            return True
        
        return None  # Unknown, could exist
    
    def analyze_all_files(self) -> Dict[str, Any]:
        """Analyze all test files for import patterns."""
        from datetime import datetime
        
        print("Starting simple import analysis...")
        print(f"Analyzing directory: {self.app_tests_path}")
        
        # Find all test files
        test_files = []
        if self.app_tests_path.exists():
            for file_path in self.app_tests_path.rglob("test_*.py"):
                if "__pycache__" not in str(file_path):
                    test_files.append(file_path)
        
        test_files = sorted(test_files)
        print(f"Found {len(test_files)} test files to analyze")
        
        if not test_files:
            print("No test files found!")
            return self.results
        
        # Analyze each file
        files_with_imports = 0
        total_imports = 0
        relative_imports_count = 0
        
        for i, file_path in enumerate(test_files, 1):
            if i % 100 == 0:
                print(f"Progress: {i}/{len(test_files)} files analyzed")
            
            file_info = self.parse_file_imports(file_path)
            self.results["file_details"].append(file_info)
            
            # Count statistics
            if file_info["imports"] or file_info["from_imports"]:
                files_with_imports += 1
            
            total_imports += len(file_info["imports"]) + len(file_info["from_imports"])
            relative_imports_count += len(file_info["relative_imports"])
        
        # Analyze potentially missing modules
        potentially_missing = []
        for module, files in self.all_imports.items():
            if module.startswith('app.'):
                existence = self.check_module_existence(module)
                if existence is False:
                    potentially_missing.append({
                        "module": module,
                        "used_in_files": files,
                        "usage_count": len(files)
                    })
                    self.missing_modules.add(module)
        
        # Update results
        self.results["summary"].update({
            "total_files_analyzed": len(test_files),
            "files_with_imports": files_with_imports,
            "total_imports_found": total_imports,
            "relative_imports_count": relative_imports_count,
            "potentially_missing_modules": len(potentially_missing),
            "scan_timestamp": datetime.now().isoformat()
        })
        
        self.results["import_analysis"].update({
            "all_imports": dict(self.all_imports),
            "relative_imports": dict(self.relative_imports),
            "import_patterns": dict(self.import_patterns),
            "potentially_missing": potentially_missing
        })
        
        print(f"\nAnalysis completed:")
        print(f"   [U+2022] Total files analyzed: {len(test_files)}")
        print(f"   [U+2022] Files with imports: {files_with_imports}")
        print(f"   [U+2022] Total imports found: {total_imports}")
        print(f"   [U+2022] Relative imports: {relative_imports_count}")
        print(f"   [U+2022] Potentially missing modules: {len(potentially_missing)}")
        
        return self.results
    
    def save_report(self, output_file: str = "test_import_errors_report.json"):
        """Save the analysis results to JSON file."""
        output_path = self.base_path / output_file
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"Report saved to: {output_path}")
        return output_path
    
    def print_summary_report(self):
        """Print a human-readable summary of findings."""
        print("\n" + "="*80)
        print("TEST IMPORT ANALYSIS SUMMARY REPORT")
        print("="*80)
        
        summary = self.results["summary"]
        print(f"Analysis Directory: {summary['scan_directory']}")
        print(f"Analysis Statistics:")
        print(f"   [U+2022] Total files analyzed: {summary['total_files_analyzed']}")
        print(f"   [U+2022] Files with imports: {summary['files_with_imports']}")
        print(f"   [U+2022] Total imports found: {summary['total_imports_found']}")
        print(f"   [U+2022] Relative imports: {summary['relative_imports_count']}")
        print(f"   [U+2022] Potentially missing modules: {summary['potentially_missing_modules']}")
        
        # Most common imports
        print(f"\nTop 15 Most Used Imports:")
        sorted_imports = sorted(self.import_patterns.items(), key=lambda x: x[1], reverse=True)
        for i, (module, count) in enumerate(sorted_imports[:15], 1):
            print(f"   {i:2d}. {module} ({count} files)")
        
        # Potentially missing modules
        potentially_missing = self.results["import_analysis"]["potentially_missing"]
        if potentially_missing:
            print(f"\nPotentially Missing Modules (Top 10):")
            sorted_missing = sorted(potentially_missing, key=lambda x: x["usage_count"], reverse=True)
            for i, missing in enumerate(sorted_missing[:10], 1):
                print(f"   {i:2d}. {missing['module']} (used in {missing['usage_count']} files)")
        
        # Relative imports analysis
        if self.relative_imports:
            print(f"\nFiles with Relative Imports (Top 10):")
            relative_count = defaultdict(int)
            for files in self.relative_imports.values():
                for file in files:
                    relative_count[file] += 1
            
            sorted_relative = sorted(relative_count.items(), key=lambda x: x[1], reverse=True)
            for i, (file, count) in enumerate(sorted_relative[:10], 1):
                file_name = Path(file).name
                print(f"   {i:2d}. {file_name} ({count} relative imports)")


def main():
    """Main function to run the import analyzer."""
    base_path = Path(__file__).parent
    
    print("Simple Test Import Analyzer")
    print("="*50)
    print("Task: Analyze import patterns in app/tests directory")
    print("Method: Static AST analysis (no execution)")
    print("Output: Comprehensive JSON report of import patterns")
    print("")
    
    # Initialize analyzer
    analyzer = SimpleImportAnalyzer(str(base_path))
    
    # Analyze all files
    results = analyzer.analyze_all_files()
    
    # Save detailed JSON report
    report_path = analyzer.save_report()
    
    # Print human-readable summary
    analyzer.print_summary_report()
    
    print(f"\nSimple import analysis completed!")
    print(f"Full report available at: {report_path}")
    
    return results


if __name__ == "__main__":
    main()