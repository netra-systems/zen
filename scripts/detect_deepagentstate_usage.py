#!/usr/bin/env python3
"""DeepAgentState Usage Detection Script

This script analyzes the codebase to identify all DeepAgentState usage patterns
and generate a comprehensive migration report.

Usage:
    python scripts/detect_deepagentstate_usage.py
    python scripts/detect_deepagentstate_usage.py --output migration_report.md
    python scripts/detect_deepagentstate_usage.py --json migration_data.json
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any
import glob

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from netra_backend.app.agents.migration.deepagentstate_adapter import MigrationDetector
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def find_python_files(root_dir: str, exclude_patterns: List[str] = None) -> List[str]:
    """Find all Python files in the directory tree.
    
    Args:
        root_dir: Root directory to search
        exclude_patterns: Patterns to exclude (e.g., ['__pycache__', '.git'])
        
    Returns:
        List of Python file paths
    """
    if exclude_patterns is None:
        exclude_patterns = ['__pycache__', '.git', '.pytest_cache', 'node_modules', 'venv', '.venv', 'env', '.env']
    
    python_files = []
    
    for pattern in ['**/*.py']:
        files = glob.glob(os.path.join(root_dir, pattern), recursive=True)
        for file_path in files:
            # Check if file should be excluded
            should_exclude = False
            for exclude_pattern in exclude_patterns:
                if exclude_pattern in file_path:
                    should_exclude = True
                    break
            
            if not should_exclude:
                python_files.append(file_path)
    
    return sorted(python_files)


def analyze_codebase(root_dir: str = None) -> Dict[str, Any]:
    """Analyze the entire codebase for DeepAgentState usage.
    
    Args:
        root_dir: Root directory to analyze (defaults to project root)
        
    Returns:
        Analysis results dictionary
    """
    if root_dir is None:
        root_dir = str(project_root)
    
    logger.info(f"Analyzing codebase for DeepAgentState usage in: {root_dir}")
    
    # Find all Python files
    python_files = find_python_files(root_dir)
    logger.info(f"Found {len(python_files)} Python files to analyze")
    
    # Analyze each file
    all_usage_patterns = []
    files_analyzed = 0
    files_with_usage = 0
    
    for file_path in python_files:
        try:
            usage_patterns = MigrationDetector.find_deepagentstate_usage(file_path)
            
            if usage_patterns:
                all_usage_patterns.extend(usage_patterns)
                files_with_usage += 1
            
            files_analyzed += 1
            
            if files_analyzed % 100 == 0:
                logger.info(f"Analyzed {files_analyzed}/{len(python_files)} files...")
                
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
    
    # Generate summary statistics
    usage_by_type = {}
    usage_by_file = {}
    
    for pattern in all_usage_patterns:
        usage_type = pattern['type']
        file_path = pattern['file']
        
        # Count by type
        if usage_type not in usage_by_type:
            usage_by_type[usage_type] = 0
        usage_by_type[usage_type] += 1
        
        # Count by file
        if file_path not in usage_by_file:
            usage_by_file[file_path] = 0
        usage_by_file[file_path] += 1
    
    analysis_results = {
        'summary': {
            'total_files_analyzed': files_analyzed,
            'files_with_usage': files_with_usage,
            'total_usage_patterns': len(all_usage_patterns),
            'usage_by_type': usage_by_type,
            'most_used_files': sorted(
                usage_by_file.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
        },
        'usage_patterns': all_usage_patterns,
        'migration_priority': classify_migration_priority(all_usage_patterns)
    }
    
    logger.info(f"Analysis complete: {len(all_usage_patterns)} usage patterns found in {files_with_usage} files")
    
    return analysis_results


def classify_migration_priority(usage_patterns: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Classify files by migration priority based on usage patterns.
    
    Args:
        usage_patterns: List of usage patterns
        
    Returns:
        Dictionary with priority levels and associated files
    """
    # Define priority keywords
    ultra_critical_keywords = [
        'user_execution_engine', 'agent_execution_core', 'execution_engine',
        'base_agent', 'supervisor'
    ]
    
    high_critical_keywords = [
        'data_helper', 'reporting_sub_agent', 'synthetic_data',
        'quality_supervisor', 'triage'
    ]
    
    medium_critical_keywords = [
        'execution_context', 'workflow', 'pipeline', 'tool_dispatcher'
    ]
    
    # Classify files
    priority_files = {
        'ultra_critical': set(),
        'high_critical': set(), 
        'medium_critical': set(),
        'low_critical': set()
    }
    
    for pattern in usage_patterns:
        file_path = pattern['file'].lower()
        
        # Check priority keywords
        if any(keyword in file_path for keyword in ultra_critical_keywords):
            priority_files['ultra_critical'].add(pattern['file'])
        elif any(keyword in file_path for keyword in high_critical_keywords):
            priority_files['high_critical'].add(pattern['file'])
        elif any(keyword in file_path for keyword in medium_critical_keywords):
            priority_files['medium_critical'].add(pattern['file'])
        else:
            priority_files['low_critical'].add(pattern['file'])
    
    # Convert sets to sorted lists
    return {
        priority: sorted(list(files)) 
        for priority, files in priority_files.items()
    }


def generate_markdown_report(analysis_results: Dict[str, Any]) -> str:
    """Generate a markdown migration report.
    
    Args:
        analysis_results: Results from analyze_codebase()
        
    Returns:
        Markdown formatted report string
    """
    summary = analysis_results['summary']
    patterns = analysis_results['usage_patterns']
    priorities = analysis_results['migration_priority']
    
    report = f"""# DeepAgentState Migration Analysis Report

**Generated:** {json.dumps({"timestamp": "auto"}, indent=2)}  
**Status:** ACTIVE MIGRATION REQUIRED

## 🚨 Executive Summary

- **Total Files Analyzed:** {summary['total_files_analyzed']:,}
- **Files with DeepAgentState Usage:** {summary['files_with_usage']:,}
- **Total Usage Patterns:** {summary['total_usage_patterns']:,}

### Usage by Type
"""
    
    for usage_type, count in summary['usage_by_type'].items():
        report += f"- **{usage_type}:** {count:,} occurrences\n"
    
    report += "\n## 🎯 Migration Priority Classification\n\n"
    
    priority_labels = {
        'ultra_critical': '🔴 ULTRA CRITICAL',
        'high_critical': '🟠 HIGH CRITICAL', 
        'medium_critical': '🟡 MEDIUM CRITICAL',
        'low_critical': '🔵 LOW CRITICAL'
    }
    
    for priority, files in priorities.items():
        if files:
            report += f"### {priority_labels[priority]} ({len(files)} files)\n\n"
            for file_path in files[:10]:  # Show top 10
                report += f"- `{file_path}`\n"
            
            if len(files) > 10:
                report += f"- ... and {len(files) - 10} more files\n"
            report += "\n"
    
    report += "## 📊 Most Used Files\n\n"
    for file_path, count in summary['most_used_files']:
        report += f"- `{file_path}` ({count} patterns)\n"
    
    report += "\n## 📋 Detailed Usage Patterns\n\n"
    
    # Group patterns by file
    patterns_by_file = {}
    for pattern in patterns:
        file_path = pattern['file']
        if file_path not in patterns_by_file:
            patterns_by_file[file_path] = []
        patterns_by_file[file_path].append(pattern)
    
    for file_path, file_patterns in list(patterns_by_file.items())[:20]:  # Show top 20 files
        report += f"### `{file_path}`\n\n"
        for pattern in file_patterns:
            report += f"- Line {pattern['line']} ({pattern['type']}): `{pattern['content']}`\n"
        report += "\n"
    
    if len(patterns_by_file) > 20:
        report += f"... and {len(patterns_by_file) - 20} more files with usage patterns.\n\n"
    
    report += """## ⚡ Recommended Actions

1. **START WITH ULTRA CRITICAL**: Begin migration with user-facing and core execution components
2. **VALIDATE ISOLATION**: Ensure each migrated component maintains proper user isolation  
3. **TEST THOROUGHLY**: Run comprehensive test suites after each migration
4. **MONITOR PROGRESS**: Use this report to track migration completion

**🚨 CRITICAL**: Every day DeepAgentState remains in production increases user data leakage risk.
"""
    
    return report


def main():
    """Main script execution."""
    parser = argparse.ArgumentParser(description='Detect DeepAgentState usage for migration planning')
    parser.add_argument(
        '--output', '-o', 
        help='Output file path for markdown report'
    )
    parser.add_argument(
        '--json', '-j',
        help='Output file path for JSON data'
    )
    parser.add_argument(
        '--root', '-r',
        help='Root directory to analyze (defaults to project root)',
        default=None
    )
    
    args = parser.parse_args()
    
    try:
        # Analyze codebase
        analysis_results = analyze_codebase(args.root)
        
        # Generate markdown report
        markdown_report = generate_markdown_report(analysis_results)
        
        if args.output:
            # Write markdown report to file with UTF-8 BOM for Windows
            with open(args.output, 'w', encoding='utf-8-sig') as f:
                f.write(markdown_report)
            print(f"SUCCESS: Markdown report written to: {args.output}")
        else:
            # Print to stdout with safe encoding
            try:
                print(markdown_report)
            except UnicodeEncodeError:
                print(markdown_report.encode('utf-8', 'replace').decode('utf-8'))
        
        if args.json:
            # Write JSON data to file
            with open(args.json, 'w', encoding='utf-8-sig') as f:
                json.dump(analysis_results, f, indent=2)
            print(f"SUCCESS: JSON data written to: {args.json}")
        
        # Print summary to stderr so it's always visible
        summary = analysis_results['summary']
        print(
            f"SUMMARY: {summary['total_usage_patterns']} patterns in "
            f"{summary['files_with_usage']} files need migration",
            file=sys.stderr
        )
        
        # Exit with error code if usage found (for CI/CD)
        if summary['total_usage_patterns'] > 0:
            sys.exit(1)
        else:
            print("SUCCESS: No DeepAgentState usage found - migration complete!", file=sys.stderr)
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Script failed: {e}", exc_info=True)
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()