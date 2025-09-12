#!/usr/bin/env python3
"""
Claude Coverage Command - Quick access to coverage intelligence for Claude
==========================================================================

This is a streamlined command specifically designed for Claude to quickly:
1. Get coverage status and test priorities  
2. Generate actionable test creation recommendations
3. Understand line vs branch coverage differences
4. Export findings for further analysis

USAGE (Claude Commands):
    python scripts/claude_coverage_command.py status     # Quick coverage status
    python scripts/claude_coverage_command.py priorities # Top test priorities  
    python scripts/claude_coverage_command.py explain    # Line vs Branch explanation
    python scripts/claude_coverage_command.py full       # Complete analysis
    python scripts/claude_coverage_command.py export     # JSON export for analysis
"""

import sys
import subprocess
from pathlib import Path

# Setup project root
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Windows encoding fix
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def run_coverage_intelligence(args: list):
    """Run the coverage intelligence script with specified arguments."""
    cmd = [sys.executable, "scripts/coverage_intelligence.py"] + args
    
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f" FAIL:  Coverage analysis failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f" FAIL:  Error running coverage analysis: {e}")
        return False

def show_usage():
    """Show usage instructions optimized for Claude."""
    print("""
[U+1F916] CLAUDE COVERAGE COMMAND GUIDE
===============================

QUICK COMMANDS:
    python scripts/claude_coverage_command.py status       # Coverage status summary
    python scripts/claude_coverage_command.py priorities   # Top 5 test priorities
    python scripts/claude_coverage_command.py explain      # Line vs branch coverage explanation
    python scripts/claude_coverage_command.py full         # Detailed analysis report
    python scripts/claude_coverage_command.py export       # Export JSON for analysis

FOR TEST CREATION WORKFLOW:
    1. Run 'priorities' to see top opportunities
    2. Run 'explain' to understand coverage types
    3. Create tests based on recommendations
    4. Run 'status' to check improvements

INTEGRATION WITH UNIFIED TEST RUNNER:
    # Refresh coverage data first
    python tests/unified_test_runner.py --category unit
    
    # Then analyze coverage
    python scripts/claude_coverage_command.py priorities
    """)

def main():
    if len(sys.argv) < 2:
        show_usage()
        return
    
    command = sys.argv[1].lower()
    
    if command == "status":
        print(" CHART:  COVERAGE STATUS OVERVIEW")
        print("=" * 40)
        run_coverage_intelligence(["--priority-only"])
        
    elif command == "priorities":
        print(" TARGET:  TOP TEST CREATION PRIORITIES")
        print("=" * 40)
        run_coverage_intelligence(["--priority-only"])
        
    elif command == "explain":
        print("[U+1F4DA] LINE vs BRANCH COVERAGE EXPLANATION")
        print("=" * 50)
        # Run full report but focus on explanation section
        run_coverage_intelligence([])
        
    elif command == "full":
        print("[U+1F4CB] COMPLETE COVERAGE INTELLIGENCE REPORT")
        print("=" * 50)
        run_coverage_intelligence([])
        
    elif command == "export":
        output_file = "coverage_intelligence_report.json"
        print(f"[U+1F4C4] EXPORTING COVERAGE ANALYSIS TO {output_file}")
        print("=" * 50)
        success = run_coverage_intelligence(["--format", "json", "--output", output_file])
        if success:
            print(f" PASS:  Report exported to {output_file}")
            print("   Use this JSON data for further analysis or automation")
        
    elif command in ["help", "--help", "-h"]:
        show_usage()
        
    else:
        print(f" FAIL:  Unknown command: {command}")
        show_usage()

if __name__ == "__main__":
    main()