#!/usr/bin/env python
"""
Test Categorization Script - Analyzes and categorizes tests based on their dependencies
Separates real service tests from mock/plumbing tests
"""

import os
import sys
import re
import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

class TestCategorizer:
    """Analyzes test files to categorize them based on dependencies"""
    
    def __init__(self):
        self.test_dir = PROJECT_ROOT / "app" / "tests"
        self.categories = {
            "real_llm": [],
            "real_database": [],
            "real_redis": [],
            "real_clickhouse": [],
            "real_services": [],
            "mock_only": [],
            "unit": [],
            "integration": [],
            "e2e": [],
            "uncategorized": []
        }
        
        # Patterns to identify test dependencies
        self.patterns = {
            "real_llm": [
                r"ANTHROPIC_API_KEY",
                r"OPENAI_API_KEY",
                r"GEMINI_API_KEY",
                r"ENABLE_REAL_LLM",
                r"real.*llm",
                r"actual.*llm"
            ],
            "real_database": [
                r"create_engine.*postgresql",
                r"asyncpg\.connect",
                r"real.*database",
                r"actual.*postgres"
            ],
            "real_redis": [
                r"redis\.Redis\(",
                r"aioredis\.create_redis",
                r"real.*redis",
                r"actual.*redis"
            ],
            "real_clickhouse": [
                r"clickhouse_driver\.Client",
                r"ClickHouseClient",
                r"real.*clickhouse",
                r"actual.*clickhouse"
            ],
            "mock_patterns": [
                r"Mock\(",
                r"AsyncMock\(",
                r"MagicMock\(",
                r"@patch",
                r"monkeypatch",
                r"mock_.*=",
                r"fake_.*="
            ],
            "integration_patterns": [
                r"test.*integration",
                r"test.*e2e",
                r"test.*workflow",
                r"test.*orchestration",
                r"WebSocketManager",
                r"AgentService"
            ],
            "unit_patterns": [
                r"test.*unit",
                r"test.*isolated",
                r"test.*component"
            ]
        }
    
    def analyze_file(self, file_path: Path) -> Dict[str, bool]:
        """Analyze a single test file for dependencies"""
        results = {
            "uses_real_llm": False,
            "uses_real_database": False,
            "uses_real_redis": False,
            "uses_real_clickhouse": False,
            "uses_mocks": False,
            "is_integration": False,
            "is_unit": False,
            "is_e2e": False,
            "has_skip_marker": False
        }
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Check for real service usage
            for pattern in self.patterns["real_llm"]:
                if re.search(pattern, content, re.IGNORECASE):
                    results["uses_real_llm"] = True
                    break
            
            for pattern in self.patterns["real_database"]:
                if re.search(pattern, content, re.IGNORECASE):
                    results["uses_real_database"] = True
                    break
            
            for pattern in self.patterns["real_redis"]:
                if re.search(pattern, content, re.IGNORECASE):
                    results["uses_real_redis"] = True
                    break
            
            for pattern in self.patterns["real_clickhouse"]:
                if re.search(pattern, content, re.IGNORECASE):
                    results["uses_real_clickhouse"] = True
                    break
            
            # Check for mock usage
            for pattern in self.patterns["mock_patterns"]:
                if re.search(pattern, content):
                    results["uses_mocks"] = True
                    break
            
            # Check test type
            for pattern in self.patterns["integration_patterns"]:
                if re.search(pattern, content, re.IGNORECASE):
                    results["is_integration"] = True
                    break
            
            for pattern in self.patterns["unit_patterns"]:
                if re.search(pattern, content, re.IGNORECASE):
                    results["is_unit"] = True
                    break
            
            # Check for E2E
            if "e2e" in str(file_path).lower() or "end.to.end" in content.lower():
                results["is_e2e"] = True
            
            # Check for skip markers
            if re.search(r"@pytest\.mark\.skip", content):
                results["has_skip_marker"] = True
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
        
        return results
    
    def categorize_test(self, file_path: Path, analysis: Dict[str, bool]) -> List[str]:
        """Categorize a test based on analysis results"""
        categories = []
        
        # Check for real services
        if analysis["uses_real_llm"]:
            categories.append("real_llm")
        if analysis["uses_real_database"]:
            categories.append("real_database")
        if analysis["uses_real_redis"]:
            categories.append("real_redis")
        if analysis["uses_real_clickhouse"]:
            categories.append("real_clickhouse")
        
        # If any real service is used, mark as real_services
        if any([analysis["uses_real_llm"], analysis["uses_real_database"], 
                analysis["uses_real_redis"], analysis["uses_real_clickhouse"]]):
            categories.append("real_services")
        
        # If only uses mocks and no real services
        if analysis["uses_mocks"] and not any([analysis["uses_real_llm"], 
                                                analysis["uses_real_database"],
                                                analysis["uses_real_redis"], 
                                                analysis["uses_real_clickhouse"]]):
            categories.append("mock_only")
        
        # Test type categorization
        if analysis["is_e2e"]:
            categories.append("e2e")
        elif analysis["is_integration"]:
            categories.append("integration")
        elif analysis["is_unit"]:
            categories.append("unit")
        
        # If no category assigned, mark as uncategorized
        if not categories:
            categories.append("uncategorized")
        
        return categories
    
    def scan_tests(self):
        """Scan all test files and categorize them"""
        test_files = list(self.test_dir.rglob("test_*.py"))
        
        results = {}
        for test_file in test_files:
            relative_path = test_file.relative_to(self.test_dir)
            analysis = self.analyze_file(test_file)
            categories = self.categorize_test(test_file, analysis)
            
            results[str(relative_path)] = {
                "analysis": analysis,
                "categories": categories,
                "full_path": str(test_file)
            }
            
            # Add to category lists
            for category in categories:
                if category in self.categories:
                    self.categories[category].append(str(relative_path))
        
        return results
    
    def _create_report_header(self) -> List[str]:
        """Create report header section"""
        header = []
        header.append("=" * 80)
        header.append("TEST CATEGORIZATION REPORT")
        header.append("=" * 80)
        header.append("")
        return header
    
    def _calculate_summary_stats(self, results: Dict) -> List[str]:
        """Calculate summary statistics section"""
        stats = []
        stats.append("SUMMARY:")
        stats.append(f"Total test files analyzed: {len(results)}")
        stats.append("")
        return stats
    
    def _format_category_counts(self) -> List[str]:
        """Format category counts section"""
        counts = ["CATEGORY COUNTS:"]
        for category, files in self.categories.items():
            if files:
                counts.append(f"  {category}: {len(files)} files")
        counts.append("")
        return counts
    
    def _extract_real_service_tests(self, results: Dict) -> List[str]:
        """Extract and format real service tests"""
        section = ["TESTS REQUIRING REAL SERVICES:", "-" * 40]
        service_tests = self._build_service_test_list(results)
        section.extend(service_tests if service_tests else ["  None found"])
        section.append("")
        return section
    
    def _build_service_test_list(self, results: Dict) -> List[str]:
        """Build list of tests using real services"""
        tests = []
        for file_path, data in results.items():
            if "real_services" in data["categories"]:
                services = self._extract_service_names(data["analysis"])
                tests.append(f"  {file_path}: {', '.join(services)}")
        return tests
    
    def _extract_service_names(self, analysis: Dict) -> List[str]:
        """Extract service names from analysis"""
        service_map = {
            "uses_real_llm": "LLM", "uses_real_database": "Database",
            "uses_real_redis": "Redis", "uses_real_clickhouse": "ClickHouse"
        }
        return [name for key, name in service_map.items() if analysis[key]]
    
    def _format_mock_only_tests(self) -> List[str]:
        """Format mock-only tests section"""
        section = ["MOCK-ONLY TESTS (Good for CI/CD):", "-" * 40]
        mock_tests = self._get_limited_test_list("mock_only")
        section.extend(mock_tests if mock_tests else ["  None found"])
        section.append("")
        return section
    
    def _get_limited_test_list(self, category: str, limit: int = 10) -> List[str]:
        """Get limited list of tests with overflow indicator"""
        tests = [f"  {file}" for file in self.categories[category][:limit]]
        if len(self.categories[category]) > limit:
            overflow = len(self.categories[category]) - limit
            tests.append(f"  ... and {overflow} more")
        return tests
    
    def _format_e2e_tests(self) -> List[str]:
        """Format E2E tests section"""
        section = ["END-TO-END TESTS:", "-" * 40]
        e2e_tests = [f"  {file}" for file in self.categories["e2e"]]
        section.extend(e2e_tests if e2e_tests else ["  None found"])
        section.append("")
        return section
    
    def _extract_skipped_tests(self, results: Dict) -> List[str]:
        """Extract and format skipped tests"""
        section = ["SKIPPED TESTS:", "-" * 40]
        skipped = self._find_skipped_tests(results)
        section.extend(skipped if skipped else ["  None found"])
        section.append("")
        return section
    
    def _find_skipped_tests(self, results: Dict) -> List[str]:
        """Find tests with skip markers"""
        skipped = [f"  {fp}" for fp, data in results.items() 
                  if data["analysis"]["has_skip_marker"]]
        if len(skipped) > 10:
            skipped = skipped[:10] + [f"  ... and {len(skipped) - 10} more"]
        return skipped
    
    def _format_uncategorized_tests(self) -> List[str]:
        """Format uncategorized tests section"""
        if not self.categories["uncategorized"]:
            return []
        section = ["UNCATEGORIZED TESTS (Need Review):", "-" * 40]
        section.extend(self._get_limited_test_list("uncategorized"))
        section.append("")
        return section
    
    def generate_report(self, results: Dict) -> str:
        """Generate a report of test categorization"""
        report = []
        self._add_report_sections(report, results)
        return "\n".join(report)
    
    def _add_report_sections(self, report: List[str], results: Dict):
        """Add all report sections to report list"""
        self._add_header_and_stats(report, results)
        self._add_category_sections(report, results)
    
    def _add_header_and_stats(self, report: List[str], results: Dict):
        """Add header and statistics sections"""
        report.extend(self._create_report_header())
        report.extend(self._calculate_summary_stats(results))
        report.extend(self._format_category_counts())
    
    def _add_category_sections(self, report: List[str], results: Dict):
        """Add category-specific sections"""
        report.extend(self._extract_real_service_tests(results))
        report.extend(self._format_mock_only_tests())
        report.extend(self._format_e2e_tests())
        report.extend(self._extract_skipped_tests(results))
        report.extend(self._format_uncategorized_tests())
    
    def save_categorization(self, results: Dict):
        """Save categorization to JSON file for use by test runner"""
        output = {
            "timestamp": str(Path(__file__).stat().st_mtime),
            "categories": self.categories,
            "test_details": results
        }
        
        output_file = PROJECT_ROOT / "test_categorization.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
        
        print(f"Categorization saved to: {output_file}")


def main():
    """Main entry point"""
    print("Analyzing test files...")
    categorizer = TestCategorizer()
    
    results = categorizer.scan_tests()
    report = categorizer.generate_report(results)
    
    print(report)
    
    # Save results
    categorizer.save_categorization(results)
    
    # Provide recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS:")
    print("=" * 80)
    print("1. Add appropriate pytest markers to test files:")
    print("   - @pytest.mark.real_llm for tests requiring LLM APIs")
    print("   - @pytest.mark.real_database for tests requiring PostgreSQL")
    print("   - @pytest.mark.mock_only for tests using only mocks")
    print("")
    print("2. Run different test suites based on environment:")
    print("   - CI/CD: pytest -m 'not real_services'")
    print("   - Local: pytest -m mock_only")
    print("   - Staging: pytest -m real_services --real-llm")
    print("")
    print("3. Consider moving real service tests to separate directory:")
    print("   - app/tests/real_services/")
    print("   - app/tests/mock_tests/")


if __name__ == "__main__":
    main()