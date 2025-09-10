#!/usr/bin/env python3
"""
DEPRECATION WARNING: This chat UI test runner is deprecated in favor of UnifiedTestRunner SSOT.

This chat UI/UX test runner now redirects to the unified test runner's e2e chat mode
to maintain SSOT compliance while preserving all existing Golden Path UI test functionality.

CRITICAL: Please migrate to using the unified test runner directly:
    python tests/unified_test_runner.py --category e2e --test-pattern "*chat*ui*"

Migration Path:
    OLD: python tests/e2e/run_chat_ui_tests.py --headless --video --report
    NEW: python tests/unified_test_runner.py --category e2e --headless --video --report

All original UI test flags and options are preserved and forwarded to the SSOT implementation.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Development Velocity & Quality Assurance
- Value Impact: Identifies UI/UX issues preventing optimal user experience
- Strategic Impact: Ensures chat platform reliability for all customer segments
"""

import sys
import subprocess
from pathlib import Path
import argparse
import os


def show_deprecation_warning():
    """Show deprecation warning to users."""
    print("WARNING: DEPRECATION WARNING")
    print("=" * 70)
    print("Chat UI/UX Test Runner - GOLDEN PATH CRITICAL")
    print("=" * 70)
    print("This chat UI test runner is deprecated.")
    print("Please migrate to UnifiedTestRunner SSOT:")
    print()
    print("  NEW: python tests/unified_test_runner.py --category e2e")
    print()
    print("All Golden Path UI test functionality preserved. Redirecting...")
    print("=" * 70)
    print()


def parse_chat_ui_test_args():
    """Parse all chat UI test arguments for compatibility."""
    parser = argparse.ArgumentParser(
        description="[DEPRECATED] Chat UI/UX Test Runner - Golden Path Critical"
    )
    
    # Core chat UI test options
    parser.add_argument("--headless", action="store_true", help="Run tests in headless mode")
    parser.add_argument("--video", action="store_true", help="Record video of test execution")
    parser.add_argument("--report", action="store_true", help="Generate comprehensive test report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--browser", choices=["chromium", "firefox", "webkit"], default="chromium", help="Browser to use")
    parser.add_argument("--slow-mo", type=int, help="Slow motion delay in milliseconds")
    parser.add_argument("--timeout", type=int, help="Test timeout in seconds")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")
    parser.add_argument("--interactive", action="store_true", help="Run tests interactively")
    parser.add_argument("--screenshot", action="store_true", help="Take screenshots on failure")
    
    return parser.parse_known_args()


def main():
    """Main entry point with deprecation wrapper."""
    show_deprecation_warning()
    
    # Parse all chat UI test arguments
    args, unknown_args = parse_chat_ui_test_args()
    
    # Get project root
    project_root = Path(__file__).parent.parent.parent
    unified_runner = project_root / "tests" / "unified_test_runner.py"
    
    if not unified_runner.exists():
        print(f"ERROR: UnifiedTestRunner not found at {unified_runner}")
        print("Falling back to original chat UI test runner...")
        return execute_fallback_chat_ui_tests()
    
    try:
        # Build unified test runner command for chat UI tests
        cmd = [
            sys.executable, str(unified_runner),
            "--category", "e2e",
            "--test-pattern", "*chat*ui*"
        ]
        
        # Forward all chat UI test arguments
        if args.headless:
            cmd.append("--headless")
        if args.video:
            cmd.append("--video")
        if args.report:
            cmd.append("--report")
        if args.verbose:
            cmd.append("--verbose")
        if args.browser != "chromium":  # Only add if not default
            cmd.extend(["--browser", args.browser])
        if args.slow_mo:
            cmd.extend(["--slow-mo", str(args.slow_mo)])
        if args.timeout:
            cmd.extend(["--timeout", str(args.timeout)])
        if args.fail_fast:
            cmd.append("--fail-fast")
        if args.interactive:
            cmd.append("--interactive")
        if args.screenshot:
            cmd.append("--screenshot")
            
        # Add any unknown arguments
        cmd.extend(unknown_args)
        
        print(f"Executing Golden Path chat UI tests via UnifiedTestRunner:")
        print(f"   {' '.join(cmd)}")
        print()
        print("BUSINESS VALUE: Testing chat platform reliability")
        print("   - Segment: Platform/Internal")
        print("   - Impact: UI/UX issues preventing optimal user experience")
        print("   - Goal: Ensure chat works for all customer segments")
        print()
        print("NOTE: These tests are designed to expose current frontend issues")
        print()
        
        # Execute unified test runner for chat UI tests
        result = subprocess.run(cmd, cwd=project_root)
        
        # Preserve original exit code behavior
        sys.exit(result.returncode)
        
    except Exception as e:
        print(f"ERROR: Failed to execute UnifiedTestRunner chat UI tests: {e}")
        print("Falling back to original chat UI test runner...")
        return execute_fallback_chat_ui_tests()


def execute_fallback_chat_ui_tests():
    """Execute original chat UI test runner as fallback."""
    try:
        # Import and execute original functionality as fallback
        project_root = Path(__file__).parent.parent.parent
        
        # Import the backed up original implementation
        backup_file = Path(__file__).parent / "run_chat_ui_tests.py.backup"
        if backup_file.exists():
            print("Using backup chat UI test runner...")
            
            # Add project root to path
            sys.path.insert(0, str(project_root))
            
            import importlib.util
            spec = importlib.util.spec_from_file_location("chat_ui_backup", backup_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Execute main from backup with original arguments
            # Reset sys.argv to original arguments for the backup script
            original_argv = sys.argv[:]
            original_argv[0] = str(backup_file)  # Update script name
            sys.argv = original_argv
            
            # Note: The backup file may have syntax errors, so handle gracefully
            try:
                module.main()
            except AttributeError:
                print("WARNING: Backup file doesn't have main() function")
                print("Running chat UI tests directly with pytest...")
                
                # Fallback to direct pytest execution
                subprocess.run([
                    sys.executable, "-m", "pytest", 
                    "tests/e2e/test_chat_ui_flow_comprehensive.py", 
                    "-v", "--tb=short"
                ], cwd=project_root)
                
        else:
            print("CRITICAL: No backup available for chat UI test runner")
            print("Running basic chat UI health check...")
            
            # Basic chat UI health check as ultimate fallback
            subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/e2e/", "-k", "chat", 
                "-v"
            ], cwd=project_root)
            
    except Exception as fallback_error:
        print(f"CRITICAL: Fallback chat UI tests failed: {fallback_error}")
        print("Manual Golden Path UI verification required.")
        sys.exit(1)


if __name__ == "__main__":
    main()