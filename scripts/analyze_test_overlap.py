"""
Test Overlap Analyzer
Analyzes test files for similarity and potential duplication using vector similarity techniques.
"""

import ast
import hashlib
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class TestInfo:
    """Information about a test."""
    file_path: str
    test_name: str
    category: str
    subcategory: str
    content: str
    imports: List[str]
    fixtures_used: List[str]
    assertions: List[str]
    line_count: int
    complexity: int
    hash: str


@dataclass
class SimilarityResult:
    """Result of similarity analysis between two tests."""
    test1: TestInfo
    test2: TestInfo
    content_similarity: float
    structural_similarity: float
    import_similarity: float
    fixture_similarity: float
    assertion_similarity: float
    overall_similarity: float
    similarity_type: str  # 'duplicate', 'highly_similar', 'similar', 'related'


class TestOverlapAnalyzer:
    """Analyzes test files for overlap and similarity."""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.tests: List[TestInfo] = []
        self.similarity_results: List[SimilarityResult] = []
        self.category_stats: Dict[str, Dict] = defaultdict(lambda: {
            'total_tests': 0,
            'total_lines': 0,
            'avg_complexity': 0,
            'duplicates': 0,
            'highly_similar': 0
        })
        
    def analyze(self, test_dir: str = "netra_backend/tests") -> Dict:
        """Main analysis entry point."""
        print(f"Starting test overlap analysis for {test_dir}...")
        
        # Collect all test files
        self._collect_tests(test_dir)
        print(f"Collected {len(self.tests)} test functions from {len(set(t.file_path for t in self.tests))} files")
        
        # Analyze similarities
        self._analyze_similarities()
        print(f"Found {len(self.similarity_results)} similarity relationships")
        
        # Generate report
        report = self._generate_report()
        
        # Save report
        self._save_report(report)
        
        return report
    
    def _collect_tests(self, test_dir: str):
        """Collect all test functions from test files."""
        test_path = self.base_path / test_dir
        
        for root, dirs, files in os.walk(test_path):
            # Skip __pycache__ and other non-test directories
            dirs[:] = [d for d in dirs if not d.startswith('__') and not d.startswith('.')]
            
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    file_path = Path(root) / file
                    self._extract_tests_from_file(file_path, test_path)
    
    def _extract_tests_from_file(self, file_path: Path, base_test_path: Path):
        """Extract test functions from a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            # Determine category and subcategory
            rel_path = file_path.relative_to(base_test_path)
            parts = rel_path.parts[:-1]  # Exclude filename
            category = parts[0] if parts else 'root'
            subcategory = '/'.join(parts[1:]) if len(parts) > 1 else ''
            
            # Extract imports
            imports = self._extract_imports(tree)
            
            # Extract test functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and (
                    node.name.startswith('test_') or 
                    node.name.startswith('Test')
                ):
                    test_info = self._create_test_info(
                        node, file_path, category, subcategory, content, imports
                    )
                    self.tests.append(test_info)
                    
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    def _extract_imports(self, tree: ast.Module) -> List[str]:
        """Extract import statements from AST."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        return imports
    
    def _create_test_info(self, node: ast.FunctionDef, file_path: Path, 
                         category: str, subcategory: str, 
                         file_content: str, imports: List[str]) -> TestInfo:
        """Create TestInfo object from AST node."""
        # Extract function content
        start_line = node.lineno - 1
        end_line = node.end_lineno or start_line
        lines = file_content.split('\n')[start_line:end_line]
        content = '\n'.join(lines)
        
        # Extract fixtures (from decorator and parameters)
        fixtures = self._extract_fixtures(node)
        
        # Extract assertions
        assertions = self._extract_assertions(node)
        
        # Calculate complexity
        complexity = self._calculate_complexity(node)
        
        # Generate hash
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        return TestInfo(
            file_path=str(file_path),
            test_name=node.name,
            category=category,
            subcategory=subcategory,
            content=content,
            imports=imports,
            fixtures_used=fixtures,
            assertions=assertions,
            line_count=end_line - start_line,
            complexity=complexity,
            hash=content_hash
        )
    
    def _extract_fixtures(self, node: ast.FunctionDef) -> List[str]:
        """Extract pytest fixtures used by test."""
        fixtures = []
        
        # Check decorators
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                if decorator.attr == 'fixture':
                    fixtures.append('fixture')
            elif isinstance(decorator, ast.Call):
                if hasattr(decorator.func, 'attr'):
                    if decorator.func.attr in ['parametrize', 'mark']:
                        fixtures.append(decorator.func.attr)
        
        # Check function parameters
        for arg in node.args.args:
            arg_name = arg.arg
            if arg_name not in ['self', 'cls']:
                fixtures.append(arg_name)
        
        return fixtures
    
    def _extract_assertions(self, node: ast.FunctionDef) -> List[str]:
        """Extract assertion patterns from test."""
        assertions = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.Assert):
                assertions.append('assert')
            elif isinstance(child, ast.Call):
                if hasattr(child.func, 'attr'):
                    attr = child.func.attr
                    if attr.startswith('assert'):
                        assertions.append(attr)
                elif hasattr(child.func, 'id'):
                    if child.func.id == 'pytest':
                        assertions.append('pytest')
        
        return assertions
    
    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of test function."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With):
                complexity += 1
        
        return complexity
    
    def _analyze_similarities(self):
        """Analyze similarities between all test pairs."""
        if not self.tests:
            return
        
        # Prepare content for vectorization
        test_contents = [t.content for t in self.tests]
        
        # Create TF-IDF vectors
        print("Creating TF-IDF vectors...")
        vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 2),
            stop_words='english'
        )
        tfidf_matrix = vectorizer.fit_transform(test_contents)
        
        # Calculate cosine similarities
        print("Calculating cosine similarities...")
        similarities = cosine_similarity(tfidf_matrix)
        
        # Analyze each pair
        print("Analyzing test pairs...")
        n = len(self.tests)
        for i in range(n):
            for j in range(i + 1, n):
                test1 = self.tests[i]
                test2 = self.tests[j]
                
                # Skip if same file and similar names (likely test variants)
                if test1.file_path == test2.file_path:
                    name_similarity = SequenceMatcher(None, test1.test_name, test2.test_name).ratio()
                    if name_similarity < 0.7:  # Only compare if names are different enough
                        continue
                
                # Calculate various similarity metrics
                content_sim = similarities[i, j]
                
                # Only process if content similarity is significant
                if content_sim > 0.3:
                    result = self._calculate_detailed_similarity(test1, test2, content_sim)
                    if result.overall_similarity > 0.4:
                        self.similarity_results.append(result)
    
    def _calculate_detailed_similarity(self, test1: TestInfo, test2: TestInfo, 
                                      content_sim: float) -> SimilarityResult:
        """Calculate detailed similarity metrics between two tests."""
        # Structural similarity (line count, complexity)
        structural_sim = 1.0 - abs(test1.line_count - test2.line_count) / max(test1.line_count, test2.line_count)
        structural_sim *= 1.0 - abs(test1.complexity - test2.complexity) / max(test1.complexity, test2.complexity, 1)
        
        # Import similarity
        imports1 = set(test1.imports)
        imports2 = set(test2.imports)
        if imports1 or imports2:
            import_sim = len(imports1 & imports2) / len(imports1 | imports2)
        else:
            import_sim = 0.0
        
        # Fixture similarity
        fixtures1 = set(test1.fixtures_used)
        fixtures2 = set(test2.fixtures_used)
        if fixtures1 or fixtures2:
            fixture_sim = len(fixtures1 & fixtures2) / len(fixtures1 | fixtures2)
        else:
            fixture_sim = 0.0
        
        # Assertion similarity
        assertions1 = set(test1.assertions)
        assertions2 = set(test2.assertions)
        if assertions1 or assertions2:
            assertion_sim = len(assertions1 & assertions2) / len(assertions1 | assertions2)
        else:
            assertion_sim = 0.0
        
        # Calculate overall similarity (weighted average)
        overall_sim = (
            content_sim * 0.4 +
            structural_sim * 0.2 +
            import_sim * 0.15 +
            fixture_sim * 0.15 +
            assertion_sim * 0.1
        )
        
        # Determine similarity type
        if test1.hash == test2.hash:
            sim_type = 'duplicate'
        elif overall_sim > 0.8:
            sim_type = 'highly_similar'
        elif overall_sim > 0.6:
            sim_type = 'similar'
        else:
            sim_type = 'related'
        
        return SimilarityResult(
            test1=test1,
            test2=test2,
            content_similarity=content_sim,
            structural_similarity=structural_sim,
            import_similarity=import_sim,
            fixture_similarity=fixture_sim,
            assertion_similarity=assertion_sim,
            overall_similarity=overall_sim,
            similarity_type=sim_type
        )
    
    def _generate_report(self) -> Dict:
        """Generate comprehensive overlap report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_test_files': len(set(t.file_path for t in self.tests)),
                'total_test_functions': len(self.tests),
                'total_similarity_pairs': len(self.similarity_results),
                'duplicate': 0,
                'highly_similar': 0,
                'similar': 0,
                'related': 0
            },
            'categories': {},
            'duplicates': [],
            'highly_similar': [],
            'similar': [],
            'top_overlaps_by_category': {},
            'recommendations': []
        }
        
        # Count similarity types
        for result in self.similarity_results:
            report['summary'][result.similarity_type] += 1
            
            # Add to detailed lists
            result_dict = {
                'test1': f"{result.test1.file_path}::{result.test1.test_name}",
                'test2': f"{result.test2.file_path}::{result.test2.test_name}",
                'overall_similarity': round(result.overall_similarity, 3),
                'content_similarity': round(result.content_similarity, 3),
                'structural_similarity': round(result.structural_similarity, 3),
                'category1': result.test1.category,
                'category2': result.test2.category
            }
            
            if result.similarity_type == 'duplicate':
                report['duplicates'].append(result_dict)
            elif result.similarity_type == 'highly_similar':
                report['highly_similar'].append(result_dict)
            elif result.similarity_type == 'similar':
                report['similar'].append(result_dict)
        
        # Analyze by category
        category_tests = defaultdict(list)
        for test in self.tests:
            category_tests[test.category].append(test)
        
        for category, tests in category_tests.items():
            # Find overlaps within category
            category_overlaps = [
                r for r in self.similarity_results
                if r.test1.category == category and r.test2.category == category
            ]
            
            # Find cross-category overlaps
            cross_category_overlaps = [
                r for r in self.similarity_results
                if (r.test1.category == category or r.test2.category == category) 
                and r.test1.category != r.test2.category
            ]
            
            report['categories'][category] = {
                'total_tests': len(tests),
                'total_lines': sum(t.line_count for t in tests),
                'avg_complexity': sum(t.complexity for t in tests) / len(tests) if tests else 0,
                'internal_overlaps': len(category_overlaps),
                'cross_category_overlaps': len(cross_category_overlaps),
                'duplicates': sum(1 for r in category_overlaps if r.similarity_type == 'duplicate'),
                'highly_similar': sum(1 for r in category_overlaps if r.similarity_type == 'highly_similar')
            }
            
            # Top overlaps for this category
            top_overlaps = sorted(
                category_overlaps,
                key=lambda x: x.overall_similarity,
                reverse=True
            )[:5]
            
            report['top_overlaps_by_category'][category] = [
                {
                    'test1': f"{r.test1.test_name}",
                    'test2': f"{r.test2.test_name}",
                    'similarity': round(r.overall_similarity, 3),
                    'type': r.similarity_type
                }
                for r in top_overlaps
            ]
        
        # Generate recommendations
        report['recommendations'] = self._generate_recommendations(report)
        
        return report
    
    def _generate_recommendations(self, report: Dict) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        # Check for duplicates
        if report['summary']['duplicate'] > 0:
            recommendations.append(
                f"CRITICAL: Found {report['summary']['duplicate']} exact duplicate test pairs. "
                "These should be immediately reviewed and consolidated."
            )
        
        # Check for highly similar tests
        if report['summary']['highly_similar'] > 10:
            recommendations.append(
                f"WARNING: Found {report['summary']['highly_similar']} highly similar test pairs. "
                "Consider refactoring these using parametrized tests or test utilities."
            )
        
        # Check categories with high internal overlap
        for category, stats in report['categories'].items():
            if stats['internal_overlaps'] > 20:
                recommendations.append(
                    f"Category '{category}' has {stats['internal_overlaps']} internal overlaps. "
                    "Consider reorganizing tests or extracting common test utilities."
                )
            
            if stats['avg_complexity'] > 10:
                recommendations.append(
                    f"Category '{category}' has high average complexity ({stats['avg_complexity']:.1f}). "
                    "Consider breaking down complex tests into simpler units."
                )
        
        # Check for test distribution
        total_tests = report['summary']['total_test_functions']
        if total_tests > 1000:
            categories_with_few_tests = [
                cat for cat, stats in report['categories'].items()
                if stats['total_tests'] < 5
            ]
            if categories_with_few_tests:
                recommendations.append(
                    f"Categories with very few tests: {', '.join(categories_with_few_tests)}. "
                    "Consider consolidating or improving test coverage."
                )
        
        # Check for cross-category duplication
        cross_category_duplicates = [
            r for r in self.similarity_results
            if r.test1.category != r.test2.category and r.similarity_type in ['duplicate', 'highly_similar']
        ]
        if len(cross_category_duplicates) > 5:
            recommendations.append(
                f"Found {len(cross_category_duplicates)} cross-category duplicates/highly similar tests. "
                "Consider creating shared test utilities or fixtures."
            )
        
        return recommendations
    
    def _save_report(self, report: Dict):
        """Save report to multiple formats."""
        # Save JSON report
        json_path = self.base_path / "test_reports" / "test_overlap_report.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        print(f"JSON report saved to {json_path}")
        
        # Save Markdown report
        md_path = self.base_path / "test_reports" / "test_overlap_report.md"
        self._save_markdown_report(report, md_path)
        print(f"Markdown report saved to {md_path}")
        
        # Save CSV of similarities
        csv_path = self.base_path / "test_reports" / "test_similarities.csv"
        self._save_csv_report(csv_path)
        print(f"CSV report saved to {csv_path}")
    
    def _save_markdown_report(self, report: Dict, path: Path):
        """Save report in Markdown format."""
        lines = [
            "# Test Overlap Analysis Report",
            f"\nGenerated: {report['timestamp']}",
            "",
            "## Executive Summary",
            "",
            f"- **Total Test Files**: {report['summary']['total_test_files']}",
            f"- **Total Test Functions**: {report['summary']['total_test_functions']}",
            f"- **Total Similarity Pairs**: {report['summary']['total_similarity_pairs']}",
            "",
            "### Similarity Breakdown",
            "",
            f"- **Exact Duplicates**: {report['summary']['duplicate']}  WARNING: [U+FE0F]" if report['summary']['duplicate'] > 0 else f"- **Exact Duplicates**: 0  PASS: ",
            f"- **Highly Similar**: {report['summary']['highly_similar']}",
            f"- **Similar**: {report['summary']['similar']}",
            f"- **Related**: {report['summary']['related']}",
            "",
            "## Recommendations",
            ""
        ]
        
        if report['recommendations']:
            for i, rec in enumerate(report['recommendations'], 1):
                lines.append(f"{i}. {rec}")
        else:
            lines.append("No critical issues found. Test suite appears well-organized.")
        
        lines.extend([
            "",
            "## Category Analysis",
            ""
        ])
        
        # Sort categories by number of overlaps
        sorted_categories = sorted(
            report['categories'].items(),
            key=lambda x: x[1]['internal_overlaps'],
            reverse=True
        )
        
        for category, stats in sorted_categories[:10]:  # Top 10 categories
            lines.extend([
                f"### {category}",
                "",
                f"- Tests: {stats['total_tests']}",
                f"- Total Lines: {stats['total_lines']}",
                f"- Avg Complexity: {stats['avg_complexity']:.1f}",
                f"- Internal Overlaps: {stats['internal_overlaps']}",
                f"- Cross-Category Overlaps: {stats['cross_category_overlaps']}",
                f"- Duplicates: {stats['duplicates']}",
                f"- Highly Similar: {stats['highly_similar']}",
                ""
            ])
            
            # Add top overlaps for this category
            if category in report['top_overlaps_by_category']:
                overlaps = report['top_overlaps_by_category'][category]
                if overlaps:
                    lines.append("**Top Overlaps:**")
                    lines.append("")
                    for overlap in overlaps:
                        lines.append(f"- `{overlap['test1']}` [U+2194] `{overlap['test2']}` (similarity: {overlap['similarity']}, type: {overlap['type']})")
                    lines.append("")
        
        # Add duplicates section if any
        if report['duplicates']:
            lines.extend([
                "## Exact Duplicates  WARNING: [U+FE0F]",
                "",
                "These test pairs appear to be exact duplicates and should be consolidated:",
                ""
            ])
            
            for dup in report['duplicates'][:20]:  # Show top 20
                lines.append(f"1. `{dup['test1']}`")
                lines.append(f"   [U+2194] `{dup['test2']}`")
                lines.append(f"   (similarity: {dup['overall_similarity']})")
                lines.append("")
        
        # Add highly similar section
        if report['highly_similar']:
            lines.extend([
                "## Highly Similar Tests",
                "",
                "These test pairs are highly similar and might benefit from refactoring:",
                ""
            ])
            
            for sim in report['highly_similar'][:20]:  # Show top 20
                lines.append(f"- `{sim['test1']}`")
                lines.append(f"  [U+2194] `{sim['test2']}`")
                lines.append(f"  (similarity: {sim['overall_similarity']})")
                lines.append("")
        
        # Write to file
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def _save_csv_report(self, path: Path):
        """Save similarity results as CSV."""
        if not self.similarity_results:
            return
        
        rows = []
        for result in self.similarity_results:
            rows.append({
                'test1_file': result.test1.file_path,
                'test1_name': result.test1.test_name,
                'test1_category': result.test1.category,
                'test2_file': result.test2.file_path,
                'test2_name': result.test2.test_name,
                'test2_category': result.test2.category,
                'overall_similarity': result.overall_similarity,
                'content_similarity': result.content_similarity,
                'structural_similarity': result.structural_similarity,
                'import_similarity': result.import_similarity,
                'fixture_similarity': result.fixture_similarity,
                'assertion_similarity': result.assertion_similarity,
                'similarity_type': result.similarity_type,
                'test1_lines': result.test1.line_count,
                'test2_lines': result.test2.line_count,
                'test1_complexity': result.test1.complexity,
                'test2_complexity': result.test2.complexity
            })
        
        df = pd.DataFrame(rows)
        df = df.sort_values('overall_similarity', ascending=False)
        df.to_csv(path, index=False)


def main():
    """Main entry point."""
    analyzer = TestOverlapAnalyzer()
    report = analyzer.analyze()
    
    # Print summary
    print("\n" + "="*60)
    print("TEST OVERLAP ANALYSIS COMPLETE")
    print("="*60)
    print(f"Total Tests Analyzed: {report['summary']['total_test_functions']}")
    print(f"Duplicates Found: {report['summary']['duplicate']}")
    print(f"Highly Similar: {report['summary']['highly_similar']}")
    print(f"Similar: {report['summary']['similar']}")
    print("\nRecommendations:")
    for i, rec in enumerate(report['recommendations'][:5], 1):
        print(f"{i}. {rec}")
    
    print("\nFull reports saved to test_reports/")


if __name__ == "__main__":
    main()