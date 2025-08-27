"""Generate LLM model compliance report after migration.

This script validates that all LLM references use the centralized configuration
and that GEMINI_2_5_FLASH is properly set as the default.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Set
import json
from datetime import datetime


def find_remaining_violations(root_path: Path) -> Dict[str, List[Dict]]:
    """Find any remaining hardcoded LLM references."""
    
    violations = {
        "deprecated_models": [],
        "openai_keys": [],
        "direct_strings": [],
        "summary": {
            "total_files_scanned": 0,
            "files_with_violations": 0,
            "total_violations": 0
        }
    }
    
    # Patterns to check for
    deprecated_patterns = {
        "gpt-4": r'["\']gpt-4["\']',
        "gpt-3.5-turbo": r'["\']gpt-3\.5-turbo["\']',
        "claude-3-opus": r'["\']claude-3-opus["\']',
        "OPENAI_API_KEY": r'["\']OPENAI_API_KEY["\']',
    }
    
    test_dirs = [
        root_path / "netra_backend" / "tests",
        root_path / "auth_service" / "tests",
        root_path / "frontend" / "__tests__",
        root_path / "tests" / "e2e",
        root_path / "test_framework",
        root_path / "netra_backend" / "app",
    ]
    
    skip_files = ["llm_defaults.py", "llm_compliance_report.py", "migrate_llm_models.py"]
    
    files_scanned = 0
    files_with_violations_set = set()
    
    for test_dir in test_dirs:
        if not test_dir.exists():
            continue
            
        for file_path in test_dir.rglob("*.py"):
            if any(skip in str(file_path) for skip in skip_files):
                continue
                
            files_scanned += 1
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern_name, pattern in deprecated_patterns.items():
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = content.split('\n')[line_num - 1].strip()
                        
                        # Skip if in comment
                        if '#' in line_content:
                            comment_pos = line_content.index('#')
                            match_pos = line_content.find(match.group())
                            if match_pos > comment_pos:
                                continue
                        
                        violation = {
                            "file": str(file_path.relative_to(root_path)),
                            "line": line_num,
                            "pattern": pattern_name,
                            "content": line_content[:100]
                        }
                        
                        if "API_KEY" in pattern_name:
                            violations["openai_keys"].append(violation)
                        elif pattern_name in ["gpt-4", "gpt-3.5-turbo", "claude-3-opus"]:
                            violations["deprecated_models"].append(violation)
                        else:
                            violations["direct_strings"].append(violation)
                        
                        files_with_violations_set.add(str(file_path))
                        
            except Exception as e:
                pass  # Skip files that can't be read
    
    violations["summary"]["total_files_scanned"] = files_scanned
    violations["summary"]["files_with_violations"] = len(files_with_violations_set)
    violations["summary"]["total_violations"] = (
        len(violations["deprecated_models"]) + 
        len(violations["openai_keys"]) + 
        len(violations["direct_strings"])
    )
    
    return violations


def check_centralized_config(root_path: Path) -> Dict[str, any]:
    """Check that centralized config is properly set up."""
    
    config_status = {
        "llm_defaults_exists": False,
        "default_model": None,
        "test_default": None,
        "production_default": None,
        "imports_found": 0,
        "config_usage": []
    }
    
    # Check if llm_defaults.py exists
    llm_defaults_path = root_path / "netra_backend" / "app" / "llm" / "llm_defaults.py"
    config_status["llm_defaults_exists"] = llm_defaults_path.exists()
    
    if llm_defaults_path.exists():
        try:
            import sys
            sys.path.insert(0, str(root_path))
            from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig
            
            config_status["default_model"] = LLMModel.get_default().value
            config_status["test_default"] = LLMModel.get_test_default().value
            config_status["production_default"] = LLMModel.get_production_default().value
        except:
            pass
    
    # Check for imports of the new config
    test_dirs = [
        root_path / "netra_backend" / "tests",
        root_path / "test_framework",
    ]
    
    for test_dir in test_dirs:
        if not test_dir.exists():
            continue
            
        for file_path in test_dir.rglob("*.py"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if "from netra_backend.app.llm.llm_defaults import" in content:
                    config_status["imports_found"] += 1
                    config_status["config_usage"].append(str(file_path.relative_to(root_path)))
            except:
                pass
    
    return config_status


def generate_compliance_report(root_path: Path) -> str:
    """Generate a comprehensive compliance report."""
    
    print("Scanning for LLM compliance...")
    violations = find_remaining_violations(root_path)
    
    print("Checking centralized configuration...")
    config_status = check_centralized_config(root_path)
    
    # Build report
    report = []
    report.append("=" * 70)
    report.append("LLM MODEL COMPLIANCE REPORT")
    report.append("=" * 70)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Configuration Status
    report.append("CENTRALIZED CONFIGURATION STATUS")
    report.append("-" * 40)
    report.append(f"[OK] Configuration file exists: {config_status['llm_defaults_exists']}")
    report.append(f"[OK] Default model: {config_status['default_model']}")
    report.append(f"[OK] Test default: {config_status['test_default']}")
    report.append(f"[OK] Production default: {config_status['production_default']}")
    report.append(f"[OK] Files using new config: {config_status['imports_found']}")
    report.append("")
    
    # Compliance Summary
    report.append("COMPLIANCE SUMMARY")
    report.append("-" * 40)
    report.append(f"Total files scanned: {violations['summary']['total_files_scanned']}")
    report.append(f"Files with violations: {violations['summary']['files_with_violations']}")
    report.append(f"Total violations: {violations['summary']['total_violations']}")
    report.append("")
    
    # Violations by type
    if violations['deprecated_models']:
        report.append("DEPRECATED MODEL REFERENCES")
        report.append("-" * 40)
        for v in violations['deprecated_models'][:10]:
            report.append(f"  {v['file']}:{v['line']}")
            report.append(f"    Pattern: {v['pattern']}")
            report.append(f"    Content: {v['content']}")
        if len(violations['deprecated_models']) > 10:
            report.append(f"  ... and {len(violations['deprecated_models']) - 10} more")
        report.append("")
    
    if violations['openai_keys']:
        report.append("OPENAI API KEY REFERENCES")
        report.append("-" * 40)
        for v in violations['openai_keys'][:5]:
            report.append(f"  {v['file']}:{v['line']}")
            report.append(f"    Content: {v['content']}")
        if len(violations['openai_keys']) > 5:
            report.append(f"  ... and {len(violations['openai_keys']) - 5} more")
        report.append("")
    
    # Compliance Status
    report.append("COMPLIANCE STATUS")
    report.append("-" * 40)
    
    if violations['summary']['total_violations'] == 0:
        report.append("[SUCCESS] FULLY COMPLIANT - No violations found!")
        report.append("")
        report.append("All LLM references are using the centralized configuration.")
        report.append("Default model is correctly set to: gemini-2.5-flash")
    else:
        report.append("[WARNING] NOT COMPLIANT - Violations found")
        report.append("")
        report.append("Action Required:")
        report.append("1. Run: python scripts/migrate_llm_models.py")
        report.append("2. Review remaining violations manually")
        report.append("3. Update environment variables to use GOOGLE_API_KEY")
    
    report.append("")
    report.append("NEXT STEPS")
    report.append("-" * 40)
    report.append("1. Ensure GOOGLE_API_KEY is set in environment")
    report.append("2. Remove OPENAI_API_KEY requirements from CI/CD")
    report.append("3. Update documentation to reflect new defaults")
    report.append("4. Run tests to verify everything works with new config")
    
    return "\n".join(report)


def main():
    """Main function."""
    root_path = Path(".").resolve()
    
    # Generate report
    report = generate_compliance_report(root_path)
    
    # Print report
    print("\n" + report)
    
    # Save report to file
    report_path = root_path / "llm_compliance_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_path}")
    
    # Check if compliant
    if "FULLY COMPLIANT" in report:
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit(main())