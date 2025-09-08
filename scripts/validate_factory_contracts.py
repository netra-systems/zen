#!/usr/bin/env python3
"""
Factory Interface Contract Validation Script

This script validates all factory patterns in the codebase against registered
interface contracts to prevent parameter name mismatches and interface
evolution violations.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Automated prevention of interface contract failures
- Value Impact: Zero production failures from factory parameter mismatches
- Strategic Impact: Implementation of ROOT CAUSE #5 governance solution

Usage:
    python scripts/validate_factory_contracts.py                    # Full codebase scan
    python scripts/validate_factory_contracts.py --dir netra_backend # Specific directory
    python scripts/validate_factory_contracts.py --fix              # Apply automated fixes
    python scripts/validate_factory_contracts.py --pre-commit       # Pre-commit hook mode

Features:
- Comprehensive factory pattern analysis
- Parameter name mismatch detection
- Automated fix recommendations
- Pre-commit hook integration
- Detailed violation reports

Root Cause Prevention:
This script directly addresses the root cause identified in the Five Whys analysis:
WHY #5: Interface Evolution Governance - Systematic validation prevents future failures
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.lifecycle.interface_contract_validation import (
    validate_codebase_contracts,
    get_global_registry,
    InterfaceContractRegistry,
    CodebaseContractScanner,
    ParameterContract,
    InterfaceContract
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_extended_contracts() -> None:
    """Create extended contracts for all factory patterns."""
    registry = get_global_registry()
    
    # Add more factory contracts beyond the basic ones
    
    # Agent Instance Factory Contract
    agent_factory_params = [
        ParameterContract("user_id", "str", is_required=True),
        ParameterContract("thread_id", "str", is_required=True),
        ParameterContract("run_id", "str", is_required=True),
        ParameterContract("agent_name", "str", is_required=True),
        ParameterContract("websocket_client_id", "Optional[str]", is_required=False,
                         deprecated_names={"websocket_connection_id"}),
        ParameterContract("llm_client", "Any", is_required=False),
        ParameterContract("tool_dispatcher", "Any", is_required=False)
    ]
    
    agent_factory_contract = InterfaceContract(
        name="create_agent_instance",
        parameters=agent_factory_params,
        return_type="AgentBase"
    )
    
    registry.register_contract(agent_factory_contract)
    
    # WebSocket Manager Factory Contract
    websocket_factory_params = [
        ParameterContract("user_context", "UserExecutionContext", is_required=True),
        ParameterContract("max_connections", "int", is_required=False)
    ]
    
    websocket_factory_contract = InterfaceContract(
        name="create_websocket_manager",
        parameters=websocket_factory_params,
        return_type="IsolatedWebSocketManager"
    )
    
    registry.register_contract(websocket_factory_contract)
    
    # Tool Dispatcher Factory Contract
    tool_factory_params = [
        ParameterContract("user_context", "UserExecutionContext", is_required=True),
        ParameterContract("websocket_bridge", "Any", is_required=False),
        ParameterContract("tools", "List[Type]", is_required=False)
    ]
    
    tool_factory_contract = InterfaceContract(
        name="create_tool_dispatcher",
        parameters=tool_factory_params,
        return_type="UnifiedToolDispatcher"
    )
    
    registry.register_contract(tool_factory_contract)
    
    # Register factory-to-constructor mappings
    registry.register_factory_mapping("create_agent_instance", "UserExecutionContext.__init__")
    registry.register_factory_mapping("create_websocket_manager", "UserExecutionContext.__init__")
    registry.register_factory_mapping("create_tool_dispatcher", "UserExecutionContext.__init__")
    
    logger.info("Extended factory contracts created")
    
def scan_codebase(directory: Optional[Path] = None, pattern: str = "*.py") -> Dict[str, Any]:
    """Scan codebase for contract violations."""
    if directory is None:
        directory = project_root
    
    logger.info(f"Scanning {directory} for factory contract violations...")
    
    # Create extended contracts
    create_extended_contracts()
    
    # Perform the scan
    results = validate_codebase_contracts(directory)
    
    return results
    
def generate_detailed_report(results: Dict[str, Any]) -> str:
    """Generate detailed human-readable report."""
    scan_results = results["scan_results"]
    detailed_report = results["detailed_report"]
    registry_summary = results["registry_summary"]
    
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("FACTORY INTERFACE CONTRACT VALIDATION REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    # Summary
    report_lines.append("SUMMARY:")
    report_lines.append(f"  Files Scanned: {scan_results['files_scanned']}")
    report_lines.append(f"  Violations Found: {scan_results['violations_found']}")
    report_lines.append(f"  Files with Violations: {len(scan_results['files_with_violations'])}")
    report_lines.append(f"  Registered Contracts: {registry_summary['total_contracts']}")
    report_lines.append("")
    
    # Most Common Violations
    if detailed_report["most_common_violations"]:
        report_lines.append("MOST COMMON VIOLATIONS:")
        for violation, count in sorted(detailed_report["most_common_violations"].items(), 
                                     key=lambda x: x[1], reverse=True)[:10]:
            report_lines.append(f"  {count:3d}: {violation}")
        report_lines.append("")
    
    # Recommended Fixes
    if detailed_report["recommended_fixes"]:
        report_lines.append("RECOMMENDED FIXES:")
        for i, fix in enumerate(detailed_report["recommended_fixes"], 1):
            report_lines.append(f"  {i}. {fix['fix']}")
            report_lines.append(f"     Violation: {fix['violation']}")
            report_lines.append(f"     Occurrences: {fix['count']}")
            report_lines.append(f"     Automation: {fix['automation']}")
            report_lines.append("")
    
    # Files with Violations
    if scan_results["files_with_violations"]:
        report_lines.append("FILES WITH VIOLATIONS:")
        for file_path in sorted(scan_results["files_with_violations"]):
            report_lines.append(f"  - {file_path}")
        report_lines.append("")
    
    # Violations by Function
    if detailed_report["violations_by_function"]:
        report_lines.append("VIOLATIONS BY FUNCTION:")
        for func_name, violations in detailed_report["violations_by_function"].items():
            report_lines.append(f"  {func_name} ({len(violations)} violations):")
            for violation in violations[:3]:  # Show first 3
                if violation.get("source_location"):
                    report_lines.append(f"    - {violation['source_location']}")
                for v_msg in violation["violations"]:
                    report_lines.append(f"      • {v_msg}")
            if len(violations) > 3:
                report_lines.append(f"    ... and {len(violations) - 3} more")
            report_lines.append("")
    
    return "\n".join(report_lines)
    
def apply_automated_fixes(results: Dict[str, Any]) -> Dict[str, Any]:
    """Apply automated fixes for common violations."""
    detailed_report = results["detailed_report"]
    fixes_applied = []
    
    # Analyze recommended fixes
    for fix in detailed_report["recommended_fixes"]:
        if "websocket_connection_id" in fix["violation"] and "websocket_client_id" in fix["violation"]:
            # This is the exact fix for our root cause issue
            logger.info(f"Applying automated fix: {fix['fix']}")
            
            # Find all files with this violation
            for func_name, violations in detailed_report["violations_by_function"].items():
                for violation in violations:
                    if any("websocket_connection_id" in v for v in violation["violations"]):
                        source_location = violation.get("source_location")
                        if source_location:
                            file_path = source_location.split(":")[0]
                            line_number = source_location.split(":")[1]
                            
                            # Apply the fix
                            success = _apply_parameter_name_fix(
                                Path(file_path),
                                "websocket_connection_id",
                                "websocket_client_id"
                            )
                            
                            if success:
                                fixes_applied.append({
                                    "file": file_path,
                                    "line": line_number,
                                    "fix": fix["fix"],
                                    "function": func_name
                                })
    
    return {
        "fixes_applied": fixes_applied,
        "total_fixes": len(fixes_applied)
    }
    
def _apply_parameter_name_fix(file_path: Path, old_name: str, new_name: str) -> bool:
    """Apply parameter name fix to a specific file."""
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple regex replacement (more sophisticated AST-based replacement could be added)
        import re
        
        # Pattern to match parameter assignments
        pattern = rf"\b{old_name}\s*="
        replacement = f"{new_name}="
        
        modified_content = re.sub(pattern, replacement, content)
        
        if modified_content != content:
            # Write the modified content back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            
            logger.info(f"Applied fix to {file_path}: {old_name} -> {new_name}")
            return True
        else:
            logger.debug(f"No changes needed in {file_path}")
            return False
    
    except Exception as e:
        logger.error(f"Error applying fix to {file_path}: {e}")
        return False
    
    
    


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate factory interface contracts",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--dir", "-d",
        type=Path,
        help="Directory to scan (defaults to project root)"
    )
    
    parser.add_argument(
        "--pattern", "-p",
        default="*.py",
        help="File pattern to scan (default: *.py)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output file for report (defaults to stdout)"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format"
    )
    
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply automated fixes for common violations"
    )
    
    parser.add_argument(
        "--pre-commit",
        action="store_true",
        help="Pre-commit hook mode (exit with error code if violations found)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Scan the codebase
        results = scan_codebase(args.dir, args.pattern)
        
        # Apply fixes if requested
        if args.fix:
            fix_results = apply_automated_fixes(results)
            results["fix_results"] = fix_results
        
        # Generate output
        if args.json:
            output_content = json.dumps(results, indent=2, default=str)
        else:
            output_content = generate_detailed_report(results)
        
        # Write output
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_content)
            logger.info(f"Report written to {args.output}")
        else:
            print(output_content)
        
        # Exit with error code for pre-commit mode
        if args.pre_commit:
            violations_found = results["scan_results"]["violations_found"]
            if violations_found > 0:
                logger.error(f"Pre-commit check failed: {violations_found} contract violations found")
                sys.exit(1)
            else:
                logger.info("Pre-commit check passed: No contract violations found")
                sys.exit(0)
        
        # Normal exit
        violations_found = results["scan_results"]["violations_found"]
        if violations_found > 0:
            logger.warning(f"Contract validation completed with {violations_found} violations")
            if not args.fix:
                logger.info("Use --fix to apply automated fixes")
        else:
            logger.info("Contract validation passed: No violations found")
        
    except Exception as e:
        logger.error(f"Contract validation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()