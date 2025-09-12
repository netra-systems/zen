#!/usr/bin/env python3
"""
API Contract Validator - Level 2 Interface Validation
CRITICAL: Prevents interface contract violations during development

Business Value: Protects $500K+ ARR by ensuring interface consistency
Revenue Impact: Eliminates service integration failures
"""

import argparse
import ast
import hashlib
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import inspect
from enum import Enum


class ContractSeverity(Enum):
    CRITICAL = "CRITICAL"    # Breaking changes
    ERROR = "ERROR"          # Interface violations
    WARNING = "WARNING"      # Compatibility issues
    INFO = "INFO"           # Style/best practice


@dataclass 
class FunctionContract:
    """Contract definition for a function"""
    name: str
    is_async: bool
    parameters: List[Dict[str, Any]]
    return_type: Optional[str]
    module_path: str
    line_number: int
    docstring: Optional[str] = None
    decorators: List[str] = None
    contract_hash: str = ""
    
    def __post_init__(self):
        if self.decorators is None:
            self.decorators = []
        self.contract_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute hash for contract comparison"""
        contract_data = {
            'name': self.name,
            'is_async': self.is_async,
            'parameters': self.parameters,
            'return_type': self.return_type
        }
        contract_str = json.dumps(contract_data, sort_keys=True)
        return hashlib.sha256(contract_str.encode()).hexdigest()[:16]


@dataclass
class ContractViolation:
    """Violation of API contract"""
    file_path: str
    violation_type: str
    line_number: int
    function_name: str
    severity: ContractSeverity
    message: str
    fix_suggestion: str
    old_contract: Optional[FunctionContract] = None
    new_contract: Optional[FunctionContract] = None


class ContractExtractor(ast.NodeVisitor):
    """Extract function contracts from AST"""
    
    def __init__(self, source_code: str, module_path: str):
        self.source_code = source_code
        self.source_lines = source_code.splitlines()
        self.module_path = module_path
        self.contracts: List[FunctionContract] = []
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Extract contract from regular function"""
        contract = self._extract_function_contract(node, is_async=False)
        self.contracts.append(contract)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Extract contract from async function"""
        contract = self._extract_function_contract(node, is_async=True)
        self.contracts.append(contract)
        self.generic_visit(node)
    
    def _extract_function_contract(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], is_async: bool) -> FunctionContract:
        """Extract contract from function node"""
        # Extract parameters
        parameters = []
        for arg in node.args.args:
            param = {
                'name': arg.arg,
                'annotation': ast.unparse(arg.annotation) if arg.annotation else None,
                'has_default': False
            }
            parameters.append(param)
        
        # Handle defaults
        if node.args.defaults:
            defaults_start = len(parameters) - len(node.args.defaults)
            for i, default in enumerate(node.args.defaults):
                parameters[defaults_start + i]['has_default'] = True
                parameters[defaults_start + i]['default_value'] = ast.unparse(default)
        
        # Extract return type
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns)
        
        # Extract docstring
        docstring = None
        if (node.body and isinstance(node.body[0], ast.Expr) 
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)):
            docstring = node.body[0].value.value
        
        # Extract decorators
        decorators = []
        for decorator in node.decorator_list:
            decorators.append(ast.unparse(decorator))
        
        return FunctionContract(
            name=node.name,
            is_async=is_async,
            parameters=parameters,
            return_type=return_type,
            module_path=self.module_path,
            line_number=node.lineno,
            docstring=docstring,
            decorators=decorators
        )


class ContractDatabase:
    """Database for storing and comparing function contracts"""
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or Path('.api_contracts.json')
        self.contracts: Dict[str, FunctionContract] = {}
        self.load_contracts()
    
    def load_contracts(self) -> None:
        """Load existing contracts from database"""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r') as f:
                    data = json.load(f)
                
                for contract_data in data.get('contracts', []):
                    contract = FunctionContract(**contract_data)
                    key = f"{contract.module_path}::{contract.name}"
                    self.contracts[key] = contract
            except Exception as e:
                print(f"Warning: Could not load contract database: {e}")
    
    def save_contracts(self) -> None:
        """Save contracts to database"""
        try:
            data = {
                'contracts': [asdict(contract) for contract in self.contracts.values()],
                'generated_at': json.dumps(None)  # Would be timestamp in real implementation
            }
            
            with open(self.db_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save contract database: {e}")
    
    def add_contract(self, contract: FunctionContract) -> None:
        """Add or update a contract"""
        key = f"{contract.module_path}::{contract.name}"
        self.contracts[key] = contract
    
    def get_contract(self, module_path: str, function_name: str) -> Optional[FunctionContract]:
        """Get existing contract for function"""
        key = f"{module_path}::{function_name}"
        return self.contracts.get(key)
    
    def compare_contracts(self, old_contract: FunctionContract, new_contract: FunctionContract) -> List[ContractViolation]:
        """Compare old and new contracts for violations"""
        violations = []
        
        # Check async/sync compatibility
        if old_contract.is_async != new_contract.is_async:
            severity = ContractSeverity.CRITICAL
            message = f"Function async status changed: {old_contract.is_async} -> {new_contract.is_async}"
            fix_suggestion = "This is a breaking change. Update all callers to match new async pattern."
            
            violation = ContractViolation(
                file_path=new_contract.module_path,
                violation_type="async_status_change",
                line_number=new_contract.line_number,
                function_name=new_contract.name,
                severity=severity,
                message=message,
                fix_suggestion=fix_suggestion,
                old_contract=old_contract,
                new_contract=new_contract
            )
            violations.append(violation)
        
        # Check parameter compatibility
        param_violations = self._compare_parameters(old_contract, new_contract)
        violations.extend(param_violations)
        
        # Check return type compatibility
        if old_contract.return_type != new_contract.return_type:
            # This could be breaking depending on the change
            severity = ContractSeverity.WARNING if self._is_compatible_return_type(old_contract.return_type, new_contract.return_type) else ContractSeverity.CRITICAL
            
            violation = ContractViolation(
                file_path=new_contract.module_path,
                violation_type="return_type_change",
                line_number=new_contract.line_number,
                function_name=new_contract.name,
                severity=severity,
                message=f"Return type changed: {old_contract.return_type} -> {new_contract.return_type}",
                fix_suggestion="Verify all callers handle new return type correctly",
                old_contract=old_contract,
                new_contract=new_contract
            )
            violations.append(violation)
        
        return violations
    
    def _compare_parameters(self, old_contract: FunctionContract, new_contract: FunctionContract) -> List[ContractViolation]:
        """Compare parameters between contracts"""
        violations = []
        old_params = {p['name']: p for p in old_contract.parameters}
        new_params = {p['name']: p for p in new_contract.parameters}
        
        # Check for removed parameters
        for param_name in old_params:
            if param_name not in new_params:
                violation = ContractViolation(
                    file_path=new_contract.module_path,
                    violation_type="parameter_removed",
                    line_number=new_contract.line_number,
                    function_name=new_contract.name,
                    severity=ContractSeverity.CRITICAL,
                    message=f"Parameter '{param_name}' was removed",
                    fix_suggestion="This is a breaking change. Update all callers.",
                    old_contract=old_contract,
                    new_contract=new_contract
                )
                violations.append(violation)
        
        # Check for added parameters without defaults
        for param_name in new_params:
            if param_name not in old_params:
                new_param = new_params[param_name]
                if not new_param.get('has_default', False):
                    violation = ContractViolation(
                        file_path=new_contract.module_path,
                        violation_type="required_parameter_added",
                        line_number=new_contract.line_number,
                        function_name=new_contract.name,
                        severity=ContractSeverity.CRITICAL,
                        message=f"Required parameter '{param_name}' was added",
                        fix_suggestion="Add default value or update all callers",
                        old_contract=old_contract,
                        new_contract=new_contract
                    )
                    violations.append(violation)
        
        # Check for parameter type changes
        for param_name in old_params:
            if param_name in new_params:
                old_annotation = old_params[param_name].get('annotation')
                new_annotation = new_params[param_name].get('annotation')
                
                if old_annotation != new_annotation:
                    severity = ContractSeverity.WARNING if self._is_compatible_type(old_annotation, new_annotation) else ContractSeverity.ERROR
                    
                    violation = ContractViolation(
                        file_path=new_contract.module_path,
                        violation_type="parameter_type_change",
                        line_number=new_contract.line_number,
                        function_name=new_contract.name,
                        severity=severity,
                        message=f"Parameter '{param_name}' type changed: {old_annotation} -> {new_annotation}",
                        fix_suggestion="Verify type compatibility with existing callers",
                        old_contract=old_contract,
                        new_contract=new_contract
                    )
                    violations.append(violation)
        
        return violations
    
    def _is_compatible_return_type(self, old_type: Optional[str], new_type: Optional[str]) -> bool:
        """Check if return type change is compatible"""
        # Simplified compatibility check
        if old_type is None or new_type is None:
            return True
        
        # Allow more specific types (inheritance)
        compatible_changes = [
            ('Any', 'str'),
            ('Any', 'int'),
            ('Any', 'Dict'),
            ('Union', 'str'),  # Union to specific type
        ]
        
        for old_pattern, new_pattern in compatible_changes:
            if old_pattern in (old_type or '') and new_pattern in (new_type or ''):
                return True
        
        return old_type == new_type
    
    def _is_compatible_type(self, old_type: Optional[str], new_type: Optional[str]) -> bool:
        """Check if parameter type change is compatible"""
        return self._is_compatible_return_type(old_type, new_type)


class APIContractValidator:
    """Main validator for API contracts"""
    
    def __init__(self, db_path: Path = None):
        self.contract_db = ContractDatabase(db_path)
        self.total_files_processed = 0
        self.total_contracts_extracted = 0
    
    def extract_contracts_from_file(self, file_path: Path) -> List[FunctionContract]:
        """Extract all contracts from a Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                source_code = f.read()
            
            # Parse AST
            try:
                tree = ast.parse(source_code)
            except SyntaxError:
                # Skip files with syntax errors
                return []
            
            # Extract contracts
            extractor = ContractExtractor(source_code, str(file_path))
            extractor.visit(tree)
            
            self.total_files_processed += 1
            self.total_contracts_extracted += len(extractor.contracts)
            
            return extractor.contracts
            
        except Exception:
            return []
    
    def validate_file_contracts(self, file_path: Path) -> List[ContractViolation]:
        """Validate contracts in a file against existing database"""
        violations = []
        
        new_contracts = self.extract_contracts_from_file(file_path)
        
        for new_contract in new_contracts:
            existing_contract = self.contract_db.get_contract(new_contract.module_path, new_contract.name)
            
            if existing_contract:
                # Compare contracts
                contract_violations = self.contract_db.compare_contracts(existing_contract, new_contract)
                violations.extend(contract_violations)
            
            # Update database with new contract
            self.contract_db.add_contract(new_contract)
        
        return violations
    
    def generate_contracts_for_codebase(self, root_path: Path = None) -> List[FunctionContract]:
        """Generate contracts for entire codebase"""
        if root_path is None:
            root_path = Path.cwd()
        
        all_contracts = []
        
        # Target directories
        target_dirs = [
            'netra_backend/app',
            'auth_service/auth_core',
            'test_framework'
        ]
        
        for target_dir in target_dirs:
            dir_path = root_path / target_dir
            if dir_path.exists():
                for py_file in dir_path.rglob('*.py'):
                    contracts = self.extract_contracts_from_file(py_file)
                    all_contracts.extend(contracts)
                    
                    # Add to database
                    for contract in contracts:
                        self.contract_db.add_contract(contract)
        
        # Save updated database
        self.contract_db.save_contracts()
        
        return all_contracts
    
    def validate_codebase_contracts(self, root_path: Path = None) -> List[ContractViolation]:
        """Validate all contracts in codebase"""
        if root_path is None:
            root_path = Path.cwd()
        
        all_violations = []
        
        # Target directories
        target_dirs = [
            'netra_backend/app',
            'auth_service/auth_core', 
            'test_framework'
        ]
        
        for target_dir in target_dirs:
            dir_path = root_path / target_dir
            if dir_path.exists():
                for py_file in dir_path.rglob('*.py'):
                    violations = self.validate_file_contracts(py_file)
                    all_violations.extend(violations)
        
        # Save updated database
        self.contract_db.save_contracts()
        
        return all_violations


class ContractReporter:
    """Reporter for contract validation results"""
    
    @staticmethod
    def generate_console_report(violations: List[ContractViolation], contracts_processed: int = 0) -> str:
        """Generate human-readable console report"""
        if not violations:
            return f" PASS:  All {contracts_processed} API contracts are compatible"
        
        report_lines = []
        report_lines.append("[U+1F534] API CONTRACT VIOLATIONS DETECTED")
        report_lines.append("=" * 60)
        
        # Group by severity
        critical = [v for v in violations if v.severity == ContractSeverity.CRITICAL]
        errors = [v for v in violations if v.severity == ContractSeverity.ERROR]
        warnings = [v for v in violations if v.severity == ContractSeverity.WARNING]
        infos = [v for v in violations if v.severity == ContractSeverity.INFO]
        
        for severity_name, violations_list in [
            ("CRITICAL (BREAKING CHANGES)", critical),
            ("ERRORS", errors), 
            ("WARNINGS", warnings),
            ("INFO", infos)
        ]:
            if violations_list:
                report_lines.append(f"\n{severity_name} ({len(violations_list)}):")
                for violation in violations_list:
                    report_lines.append(f"  [U+1F4C1] {violation.file_path}:{violation.line_number}")
                    report_lines.append(f"     Function: {violation.function_name}")
                    report_lines.append(f"     Issue: {violation.message}")
                    report_lines.append(f"     Fix: {violation.fix_suggestion}")
                    report_lines.append("")
        
        total_breaking = len(critical)
        report_lines.append(f"Summary: {len(violations)} total violations ({total_breaking} breaking changes)")
        
        if critical:
            report_lines.append("\n ALERT:  BREAKING CHANGES DETECTED: These changes will break existing code")
        
        return "\n".join(report_lines)
    
    @staticmethod
    def generate_json_report(violations: List[ContractViolation], stats: Dict[str, int] = None) -> str:
        """Generate JSON report for CI/CD integration"""
        if stats is None:
            stats = {}
        
        violation_data = []
        for v in violations:
            data = asdict(v)
            # Convert enums to strings
            data['severity'] = v.severity.value
            # Remove complex objects that don't serialize well
            data.pop('old_contract', None)
            data.pop('new_contract', None)
            violation_data.append(data)
        
        critical_count = len([v for v in violations if v.severity == ContractSeverity.CRITICAL])
        
        return json.dumps({
            'total_violations': len(violations),
            'breaking_changes': critical_count,
            'violations': violation_data,
            'statistics': stats,
            'compliance_status': 'PASS' if critical_count == 0 else 'FAIL',
            'deployment_allowed': critical_count == 0
        }, indent=2)


def collect_target_files(specified_files: List[str]) -> List[Path]:
    """Collect Python files to validate"""
    if specified_files:
        return [Path(f) for f in specified_files if Path(f).exists() and Path(f).suffix == '.py']
    
    # Auto-discover Python files in target directories
    current_dir = Path.cwd()
    target_dirs = ['netra_backend/app', 'auth_service/auth_core', 'test_framework']
    
    files = []
    for target_dir in target_dirs:
        dir_path = current_dir / target_dir
        if dir_path.exists():
            files.extend(dir_path.rglob('*.py'))
    
    return files


def create_argument_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="API Contract Validator - Prevents interface violations"
    )
    
    # Main actions
    parser.add_argument('--generate-contracts', action='store_true',
                       help='Generate contract database for codebase')
    parser.add_argument('--validate-all', action='store_true', 
                       help='Validate all contracts against database')
    parser.add_argument('--validate-files', action='store_true',
                       help='Validate specific files')
    
    # Database options
    parser.add_argument('--db-path', type=str,
                       help='Path to contract database file')
    parser.add_argument('--reset-db', action='store_true',
                       help='Reset contract database')
    
    # Filtering options
    parser.add_argument('--breaking-changes-only', action='store_true',
                       help='Only report breaking changes')
    parser.add_argument('--include-warnings', action='store_true',
                       help='Include warning-level violations')
    
    # Output options
    parser.add_argument('--json', action='store_true',
                       help='Output results in JSON format')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    # File selection
    parser.add_argument('files', nargs='*',
                       help='Python files to validate (if not provided, uses target directories)')
    
    return parser


def main() -> int:
    """Main contract validation orchestrator"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Setup database path
    db_path = Path(args.db_path) if args.db_path else None
    
    # Reset database if requested
    if args.reset_db:
        if db_path and db_path.exists():
            db_path.unlink()
        elif Path('.api_contracts.json').exists():
            Path('.api_contracts.json').unlink()
        print(" PASS:  Contract database reset")
    
    # Initialize validator
    validator = APIContractValidator(db_path)
    
    # Handle main actions
    if args.generate_contracts:
        print("Generating API contracts for codebase...")
        contracts = validator.generate_contracts_for_codebase()
        print(f" PASS:  Generated {len(contracts)} contracts from {validator.total_files_processed} files")
        return 0
    
    elif args.validate_all:
        print("Validating all API contracts...")
        violations = validator.validate_codebase_contracts()
    
    elif args.validate_files:
        target_files = collect_target_files(args.files)
        if not target_files:
            print("No Python files to validate")
            return 0
        
        print(f"Validating {len(target_files)} files...")
        violations = []
        for file_path in target_files:
            file_violations = validator.validate_file_contracts(file_path)
            violations.extend(file_violations)
    
    else:
        # Default: validate current changes
        target_files = collect_target_files(args.files)
        violations = []
        for file_path in target_files:
            file_violations = validator.validate_file_contracts(file_path)
            violations.extend(file_violations)
    
    # Filter violations
    filtered_violations = violations
    if args.breaking_changes_only:
        filtered_violations = [v for v in violations if v.severity == ContractSeverity.CRITICAL]
    elif not args.include_warnings:
        filtered_violations = [v for v in violations if v.severity in [ContractSeverity.CRITICAL, ContractSeverity.ERROR]]
    
    # Generate report
    stats = {
        'files_processed': validator.total_files_processed,
        'contracts_extracted': validator.total_contracts_extracted
    }
    
    if args.json:
        print(ContractReporter.generate_json_report(filtered_violations, stats))
    else:
        print(ContractReporter.generate_console_report(filtered_violations, validator.total_contracts_extracted))
    
    # Exit with appropriate code
    breaking_changes = len([v for v in filtered_violations if v.severity == ContractSeverity.CRITICAL])
    return 1 if breaking_changes > 0 else 0


if __name__ == "__main__":
    sys.exit(main())