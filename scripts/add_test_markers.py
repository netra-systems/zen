from shared.isolated_environment import get_env
#!/usr/bin/env python
"""
Script to add pytest markers to test files based on their dependencies
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List

# Add project root to path

class TestMarkerAdder:
    """Adds appropriate pytest markers to test files"""
    
    def __init__(self):
        # Load test categorization
        categorization_file = PROJECT_ROOT / "test_categorization.json"
        if not categorization_file.exists():
            print("Error: test_categorization.json not found. Run categorize_tests.py first.")
            sys.exit(1)
        
        with open(categorization_file, 'r') as f:
            self.categorization = json.load(f)
        
        self.markers_added = 0
        self.files_processed = 0
    
    def get_markers_for_file(self, test_details: Dict) -> List[str]:
        """Determine which markers should be added to a test file"""
        markers = []
        analysis = test_details["analysis"]
        categories = test_details["categories"]
        
        # Add service-specific markers
        if analysis["uses_real_llm"]:
            markers.append("@pytest.mark.real_llm")
        if analysis["uses_real_database"]:
            markers.append("@pytest.mark.real_database")
        if analysis["uses_real_redis"]:
            markers.append("@pytest.mark.real_redis")
        if analysis["uses_real_clickhouse"]:
            markers.append("@pytest.mark.real_clickhouse")
        
        # Add general category markers
        if "real_services" in categories:
            markers.append("@pytest.mark.real_services")
        if "mock_only" in categories:
            markers.append("@pytest.mark.mock_only")
        if "unit" in categories:
            markers.append("@pytest.mark.unit")
        if "integration" in categories:
            markers.append("@pytest.mark.integration")
        if "e2e" in categories:
            markers.append("@pytest.mark.e2e")
        
        return markers
    
    def add_markers_to_class(self, content: str, class_name: str, markers: List[str]) -> str:
        """Add markers to a test class"""
        # Find the class definition
        class_pattern = rf"(^|\n)(class {class_name}[^:]*:)"
        match = re.search(class_pattern, content, re.MULTILINE)
        
        if not match:
            return content
        
        # Check if markers already exist
        class_start = match.start()
        # Look backwards from class definition for existing decorators
        before_class = content[:class_start]
        lines_before = before_class.split('\n')
        
        # Find where to insert markers (just before the class definition)
        insert_pos = match.start(2) if match.group(1) else match.start()
        
        # Check if any of our markers already exist
        existing_markers = set()
        for line in reversed(lines_before[-10:]):  # Check last 10 lines before class
            if "@pytest.mark." in line:
                existing_markers.add(line.strip())
        
        # Add only new markers
        new_markers = []
        for marker in markers:
            if marker not in str(existing_markers):
                new_markers.append(marker)
        
        if new_markers:
            marker_text = '\n'.join(new_markers) + '\n'
            content = content[:insert_pos] + marker_text + content[insert_pos:]
            self.markers_added += len(new_markers)
        
        return content
    
    def add_markers_to_function(self, content: str, func_name: str, markers: List[str]) -> str:
        """Add markers to a test function"""
        # Find the function definition
        func_pattern = rf"(^|\n)(async def {func_name}|def {func_name})"
        match = re.search(func_pattern, content, re.MULTILINE)
        
        if not match:
            return content
        
        # Similar logic as class markers
        insert_pos = match.start(2) if match.group(1) else match.start()
        
        # Check for existing markers
        before_func = content[:match.start()]
        lines_before = before_func.split('\n')
        
        existing_markers = set()
        for line in reversed(lines_before[-10:]):
            if "@pytest.mark." in line:
                existing_markers.add(line.strip())
        
        # Add only new markers
        new_markers = []
        for marker in markers:
            if marker not in str(existing_markers):
                new_markers.append(marker)
        
        if new_markers:
            marker_text = '\n'.join(new_markers) + '\n'
            content = content[:insert_pos] + marker_text + content[insert_pos:]
            self.markers_added += len(new_markers)
        
        return content
    
    def process_file(self, file_path: str, test_details: Dict) -> bool:
        """Process a single test file to add markers"""
        full_path = Path(test_details["full_path"])
        
        if not full_path.exists():
            print(f"Warning: File not found: {full_path}")
            return False
        
        # Skip files that are already well-marked
        if "mock_only" in test_details["categories"] and len(test_details["categories"]) == 1:
            # Pure mock test, likely doesn't need markers
            return False
        
        markers = self.get_markers_for_file(test_details)
        if not markers:
            return False
        
        try:
            content = full_path.read_text(encoding='utf-8')
            original_content = content
            
            # Find all test classes and functions
            class_pattern = r"class (Test\w+)[^:]*:"
            func_pattern = r"(?:async )?def (test_\w+)"
            
            # Add markers to classes
            for match in re.finditer(class_pattern, content):
                class_name = match.group(1)
                content = self.add_markers_to_class(content, class_name, markers)
            
            # If no classes found, add markers to individual functions
            if not re.search(class_pattern, content):
                for match in re.finditer(func_pattern, content):
                    func_name = match.group(1)
                    content = self.add_markers_to_function(content, func_name, markers)
            
            # Only write if content changed
            if content != original_content:
                full_path.write_text(content, encoding='utf-8')
                self.files_processed += 1
                return True
                
        except Exception as e:
            print(f"Error processing {full_path}: {e}")
        
        return False
    
    def add_conditional_skip_for_real_services(self, content: str) -> str:
        """Add conditional skip for real service tests"""
        # Check if file has real service markers
        if "@pytest.mark.real_llm" in content:
            # Add skipif condition if not already present
            if "ENABLE_REAL_LLM_TESTING" not in content:
                # Find the first test class or function
                match = re.search(r"(@pytest\.mark\.real_llm.*?\n)(class |def |async def )", content, re.DOTALL)
                if match:
                    insert_pos = match.end(1)
                    skip_condition = '''@pytest.mark.skipif(
    os.environ.get("ENABLE_REAL_LLM_TESTING") != "true",
    reason="Real LLM tests disabled. Set ENABLE_REAL_LLM_TESTING=true to run"
)
'''
                    content = content[:insert_pos] + skip_condition + content[insert_pos:]
        
        return content
    
    def run(self, dry_run: bool = False):
        """Process all test files"""
        print("Adding pytest markers to test files...")
        
        # Priority files that definitely need markers
        priority_files = [
            "test_categories.py",
            "agents/test_example_prompts_e2e_real.py",
            "test_realistic_data_integration.py",
            "services/test_synthetic_data_service_v3.py",
            "clickhouse/test_realistic_clickhouse_operations.py"
        ]
        
        for file_path, test_details in self.categorization["test_details"].items():
            # Check if this is a priority file or has real services
            is_priority = any(p in file_path for p in priority_files)
            has_real_services = "real_services" in test_details["categories"]
            
            if is_priority or has_real_services:
                if dry_run:
                    markers = self.get_markers_for_file(test_details)
                    if markers:
                        print(f"Would add to {file_path}: {', '.join(markers)}")
                else:
                    if self.process_file(file_path, test_details):
                        print(f"[U+2713] Updated: {file_path}")
        
        print(f"\nSummary:")
        print(f"  Files processed: {self.files_processed}")
        print(f"  Markers added: {self.markers_added}")


def main():
    """Main entry point"""
    import argparse
    parser = argparse.ArgumentParser(description="Add pytest markers to test files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    args = parser.parse_args()
    
    adder = TestMarkerAdder()
    adder.run(dry_run=args.dry_run)
    
    if not args.dry_run:
        print("\nNext steps:")
        print("1. Review the changes with: git diff")
        print("2. Run mock-only tests: pytest -m mock_only")
        print("3. Run real service tests: ENABLE_REAL_LLM_TESTING=true pytest -m real_services")


if __name__ == "__main__":
    main()
