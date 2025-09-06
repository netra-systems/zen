#!/usr/bin/env python3
"""
Architecture Compliance Checker - Main Entry Point
Enforces CLAUDE.md architectural rules using modular design.

This script has been refactored into focused modules under scripts/compliance/
to comply with the 450-line file limit and 25-line function limit.
"""

import sys
import os
from pathlib import Path

# Fix Unicode encoding issues on Windows - MUST be done early
if sys.platform == "win32":
    import io
    # Set UTF-8 for subprocess and all Python I/O
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    
    # Force Windows console to use UTF-8
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass
    
    # Reconfigure stdout/stderr for UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.compliance import ArchitectureEnforcer, CLIHandler, OutputHandler
from scripts.compliance.mro_auditor import MROAuditor


def _run_mro_audit(args):
    """Run standalone MRO complexity audit"""
    auditor = MROAuditor(Path(args.path))
    
    # Audit agent modules
    agent_paths = [
        Path(args.path) / "netra_backend" / "app" / "agents",
        Path(args.path) / "auth_service" / "app" / "agents"
    ]
    
    all_results = []
    for agent_path in agent_paths:
        if agent_path.exists():
            audit_result = auditor.audit_module(agent_path)
            all_results.extend(audit_result.get("results", []))
    
    # Generate and print report
    report = auditor.generate_report(all_results)
    print(report)
    
    # Exit with appropriate code
    violations = sum(len(r.violations) for r in all_results)
    critical = sum(1 for r in all_results for v in r.violations if v.severity == "critical")
    
    if critical > 0:
        sys.exit(2)  # Critical violations
    elif violations > 0:
        sys.exit(1)  # Has violations
    else:
        sys.exit(0)  # Clean


def main() -> None:
    """Main entry point with enhanced CI/CD features"""
    parser = CLIHandler.create_argument_parser()
    args = parser.parse_args()
    
    # Handle MRO audit specifically if requested
    if getattr(args, 'mro_audit', False):
        _run_mro_audit(args)
        return
    
    enforcer = _create_enforcer(args)
    results = enforcer.run_all_checks()
    OutputHandler.process_output(args, enforcer, results)
    OutputHandler.handle_exit_code(args, results)


def _create_enforcer(args):
    """Create architecture enforcer from arguments"""
    show_all = getattr(args, 'show_all', False)
    violation_limit = 999999 if show_all else getattr(args, 'violation_limit', 10)
    smart_limits = not getattr(args, 'no_smart_limits', False)
    use_emoji = not getattr(args, 'no_emoji', False)
    target_folders = getattr(args, 'target_folders', None)
    ignore_folders = getattr(args, 'ignore_folders', None)
    check_test_limits = not getattr(args, 'no_test_limits', False)
    return ArchitectureEnforcer(
        root_path=args.path,
        max_file_lines=args.max_file_lines,
        max_function_lines=args.max_function_lines,
        violation_limit=violation_limit,
        smart_limits=smart_limits,
        use_emoji=use_emoji,
        target_folders=target_folders,
        ignore_folders=ignore_folders,
        check_test_limits=check_test_limits
    )


if __name__ == "__main__":
    main()