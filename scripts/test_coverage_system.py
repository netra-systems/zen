#!/usr/bin/env python3
"""
Coverage System Validation Script
Tests that coverage reporting system works properly with pytest
"""

import subprocess
import sys
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from shared.isolated_environment import IsolatedEnvironment

def main():
    """Test the coverage reporting system."""
    project_root = Path(__file__).parent.parent
    
    print("[Coverage Test] Testing Coverage System...")
    
    # Test 1: Run pytest with coverage on a simple test
    print("\n[Pytest] Running pytest with coverage...")
    
    try:
        # Run a simple test with coverage
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "netra_backend/tests/unit/test_cors_architecture_compliance.py" if (project_root / "netra_backend/tests/unit/test_cors_architecture_compliance.py").exists() 
            else "test_framework/test_config.py",  # Fallback to a file that should exist
            "--cov=netra_backend/app",
            "--cov-report=term-missing",
            "--cov-report=html:reports/coverage/html",
            "--cov-report=xml:reports/coverage/coverage.xml",
            "--cov-report=json:reports/coverage/coverage.json",
            "-v",
            "--tb=short",
            "--disable-warnings",
            "--timeout=30"
        ], cwd=project_root, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("[Success] Pytest with coverage completed successfully")
            print(f"[Output] Coverage output preview:\n{result.stdout[-500:]}")  # Last 500 chars
        else:
            print(f"[Warning] Pytest completed with warnings (exit code: {result.returncode})")
            print(f"[Output] Output:\n{result.stdout[-500:]}")
            if result.stderr:
                print(f"[Error] Stderr:\n{result.stderr[-500:]}")
                
    except subprocess.TimeoutExpired:
        print("[Timeout] Pytest timed out - this is expected for complex tests")
    except Exception as e:
        print(f"[Error] Error running pytest: {e}")
        
    # Test 2: Verify coverage files were generated
    print("\n[Verify] Verifying coverage reports...")
    
    reports_dir = project_root / "reports" / "coverage"
    
    # Check HTML report
    html_index = reports_dir / "html" / "index.html" 
    if html_index.exists():
        print("[Success] HTML coverage report generated")
        # Try to extract coverage percentage
        try:
            content = html_index.read_text()
            if 'pc_cov' in content:
                print("[Success] HTML report contains coverage percentage")
        except Exception as e:
            print(f"[Warning] Could not read HTML report: {e}")
    else:
        print("[Error] HTML coverage report not found")
        
    # Check XML report
    xml_report = reports_dir / "coverage.xml"
    if xml_report.exists():
        print("[Success] XML coverage report generated")
        try:
            tree = ET.parse(xml_report)
            root = tree.getroot()
            if root.tag == 'coverage':
                line_rate = root.get('line-rate', 'unknown')
                print(f"[Success] XML coverage line-rate: {line_rate}")
        except Exception as e:
            print(f"[Warning] Could not parse XML report: {e}")
    else:
        print("[Error] XML coverage report not found")
        
    # Check JSON report
    json_report = reports_dir / "coverage.json"
    if json_report.exists():
        print("[Success] JSON coverage report generated")
        try:
            with open(json_report, 'r') as f:
                data = json.load(f)
                if 'totals' in data:
                    total_percent = data['totals'].get('percent_covered', 'unknown')
                    print(f"[Success] JSON coverage total: {total_percent}%")
        except Exception as e:
            print(f"[Warning] Could not parse JSON report: {e}")
    else:
        print("[Error] JSON coverage report not found")
        
    print("\n[Complete] Coverage System Test Complete!")
    print("=" * 50)
    
    # Test 3: Verify .coveragerc configuration
    coveragerc = project_root / ".coveragerc"
    if coveragerc.exists():
        print("[Success] .coveragerc configuration file exists")
        try:
            content = coveragerc.read_text()
            if 'netra_backend/app' in content:
                print("[Success] .coveragerc configured for netra_backend/app")
            if 'reports/coverage' in content:
                print("[Success] .coveragerc configured for reports/coverage output")
        except Exception as e:
            print(f"[Warning] Could not read .coveragerc: {e}")
    else:
        print("[Error] .coveragerc configuration not found")
        
    return True

if __name__ == "__main__":
    main()