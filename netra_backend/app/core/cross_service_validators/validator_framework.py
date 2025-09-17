"""
Cross-Service Validator Framework Core

Provides the base framework for validating service boundaries and interactions.
Modular design enables targeted validation of specific service aspects.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field

from netra_backend.app.core.unified_logging import get_logger


class ValidationSeverity(str, Enum):
    """Validation issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ValidationStatus(str, Enum):
    """Overall validation status."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class ValidationResult(BaseModel):
    """Single validation result."""
    validator_name: str = Field(description="Name of validator")
    check_name: str = Field(description="Specific check performed")
    status: ValidationStatus = Field(description="Result status")
    severity: ValidationSeverity = Field(description="Issue severity")
    message: str = Field(description="Human readable message")
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    service_pair: Optional[str] = Field(None, description="Services validated")
    execution_time_ms: Optional[float] = Field(None)


class ValidationReport(BaseModel):
    """Complete validation report for service boundaries."""
    report_id: str = Field(description="Unique report identifier")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    services_validated: List[str] = Field(description="Services included")
    total_checks: int = Field(description="Total validation checks")
    passed_checks: int = Field(default=0)
    failed_checks: int = Field(default=0)
    warning_checks: int = Field(default=0)
    skipped_checks: int = Field(default=0)
    overall_status: ValidationStatus = Field(description="Overall status")
    results: List[ValidationResult] = Field(default_factory=list)
    execution_time_ms: float = Field(description="Total execution time")
    recommendations: List[str] = Field(default_factory=list)
    
    def add_result(self, result: ValidationResult) -> None:
        """Add validation result and update counters."""
        self.results.append(result)
        self.total_checks += 1
        
        if result.status == ValidationStatus.PASSED:
            self.passed_checks += 1
        elif result.status == ValidationStatus.FAILED:
            self.failed_checks += 1
        elif result.status == ValidationStatus.WARNING:
            self.warning_checks += 1
        else:
            self.skipped_checks += 1
            
        # Update overall status
        if self.failed_checks > 0:
            self.overall_status = ValidationStatus.FAILED
        elif self.warning_checks > 0 and self.overall_status != ValidationStatus.FAILED:
            self.overall_status = ValidationStatus.WARNING
        elif self.passed_checks > 0:
            self.overall_status = ValidationStatus.PASSED


class BaseValidator(ABC):
    """Base class for all cross-service validators."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.logger = get_logger(f"validator.{name}")
    
    @abstractmethod
    async def validate(self, context: Dict[str, Any]) -> List[ValidationResult]:
        """Perform validation checks and return results."""
        pass
    
    def create_result(
        self,
        check_name: str,
        status: ValidationStatus,
        severity: ValidationSeverity,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        service_pair: Optional[str] = None,
        execution_time_ms: Optional[float] = None
    ) -> ValidationResult:
        """Helper to create validation result."""
        return ValidationResult(
            validator_name=self.name,
            check_name=check_name,
            status=status,
            severity=severity,
            message=message,
            details=details or {},
            service_pair=service_pair,
            execution_time_ms=execution_time_ms
        )


class ValidatorRegistry:
    """Registry for managing validators."""
    
    def __init__(self):
        self._validators: Dict[str, BaseValidator] = {}
        self._categories: Dict[str, List[str]] = {}
    
    def register(
        self, 
        validator: BaseValidator, 
        category: Optional[str] = None
    ) -> None:
        """Register a validator."""
        self._validators[validator.name] = validator
        if category:
            if category not in self._categories:
                self._categories[category] = []
            self._categories[category].append(validator.name)
    
    def get_validator(self, name: str) -> Optional[BaseValidator]:
        """Get validator by name."""
        return self._validators.get(name)
    
    def get_validators_by_category(self, category: str) -> List[BaseValidator]:
        """Get all validators in a category."""
        validator_names = self._categories.get(category, [])
        return [self._validators[name] for name in validator_names if name in self._validators]
    
    def list_validators(self) -> List[str]:
        """List all registered validator names."""
        return list(self._validators.keys())


class CrossServiceValidatorFramework:
    """Main framework for coordinating cross-service validation."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.registry = ValidatorRegistry()
        self.logger = get_logger("cross_service_validator")
    
    async def run_validation(
        self,
        services: List[str],
        validator_names: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationReport:
        """Run cross-service validation."""
        start_time = datetime.now(timezone.utc)
        report = ValidationReport(
            report_id=f"validation_{int(start_time.timestamp())}",
            services_validated=services
        )
        
        # Determine validators to run
        validators_to_run = self._determine_validators(validator_names, categories)
        
        # Prepare validation context
        validation_context = self._prepare_context(services, context or {})
        
        # Run validations
        await self._run_validators(validators_to_run, validation_context, report)
        
        # Finalize report
        end_time = datetime.now(timezone.utc)
        report.execution_time_ms = (end_time - start_time).total_seconds() * 1000
        report.recommendations = self._generate_recommendations(report)
        
        return report
    
    def _determine_validators(
        self, 
        validator_names: Optional[List[str]], 
        categories: Optional[List[str]]
    ) -> List[BaseValidator]:
        """Determine which validators to run."""
        validators = []
        
        if validator_names:
            for name in validator_names:
                validator = self.registry.get_validator(name)
                if validator:
                    validators.append(validator)
        
        if categories:
            for category in categories:
                validators.extend(self.registry.get_validators_by_category(category))
        
        if not validators:
            # Default to all validators
            validators = [
                self.registry.get_validator(name) 
                for name in self.registry.list_validators()
            ]
            validators = [v for v in validators if v is not None]
        
        return validators
    
    def _prepare_context(
        self, 
        services: List[str], 
        additional_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare validation context."""
        return {
            "services": services,
            "config": self.config,
            **additional_context
        }
    
    async def _run_validators(
        self,
        validators: List[BaseValidator],
        context: Dict[str, Any],
        report: ValidationReport
    ) -> None:
        """Run all validators and collect results."""
        tasks = []
        
        for validator in validators:
            task = self._run_single_validator(validator, context)
            tasks.append(task)
        
        # Run validators concurrently
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, results in enumerate(results_lists):
            if isinstance(results, Exception):
                # Handle validator execution error
                error_result = ValidationResult(
                    validator_name=validators[i].name,
                    check_name="validator_execution",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Validator execution failed: {str(results)}",
                    details={"error_type": type(results).__name__}
                )
                report.add_result(error_result)
            else:
                for result in results:
                    report.add_result(result)
    
    async def _run_single_validator(
        self, 
        validator: BaseValidator, 
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Run a single validator with error handling."""
        try:
            start_time = datetime.now(timezone.utc)
            results = await validator.validate(context)
            end_time = datetime.now(timezone.utc)
            
            # Add execution time to results
            execution_time = (end_time - start_time).total_seconds() * 1000
            for result in results:
                if result.execution_time_ms is None:
                    result.execution_time_ms = execution_time
            
            return results
        except Exception as e:
            self.logger.error(f"Validator {validator.name} failed: {e}")
            return [
                ValidationResult(
                    validator_name=validator.name,
                    check_name="execution_error",
                    status=ValidationStatus.FAILED,
                    severity=ValidationSeverity.HIGH,
                    message=f"Validator execution error: {str(e)}",
                    details={"exception": str(e), "type": type(e).__name__}
                )
            ]
    
    def _generate_recommendations(self, report: ValidationReport) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Check for critical failures
        critical_failures = [
            r for r in report.results 
            if r.status == ValidationStatus.FAILED and r.severity == ValidationSeverity.CRITICAL
        ]
        
        if critical_failures:
            recommendations.append(
                "Critical service boundary violations detected. "
                "Address immediately before deployment."
            )
        
        # Check for high severity issues
        high_severity_issues = [
            r for r in report.results 
            if r.severity == ValidationSeverity.HIGH
        ]
        
        if len(high_severity_issues) > 3:
            recommendations.append(
                "Multiple high-severity issues found. "
                "Consider comprehensive service boundary review."
            )
        
        # Check validation coverage
        if report.skipped_checks > report.passed_checks:
            recommendations.append(
                "Many validation checks were skipped. "
                "Ensure proper test environment setup."
            )
        
        return recommendations