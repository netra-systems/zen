"""
Cross-Service Validation Orchestrator

Coordinates and executes cross-service validation with scheduling,
reporting, and integration with monitoring systems.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from netra_backend.app.contract_validators import (
    APIContractValidator,
    EndpointValidator,
    SchemaCompatibilityValidator,
    WebSocketContractValidator,
)
from netra_backend.app.data_consistency_validators import (
    CrossServiceDataValidator,
    MessageDeliveryValidator,
    SessionStateValidator,
    UserDataConsistencyValidator,
)
from netra_backend.app.performance_validators import (
    CommunicationOverheadValidator,
    LatencyValidator,
    ResourceUsageValidator,
    ThroughputValidator,
)
from netra_backend.app.security_validators import (
    AuditTrailValidator,
    PermissionEnforcementValidator,
    ServiceAuthValidator,
    TokenValidationValidator,
)
from netra_backend.app.validator_framework import (
    CrossServiceValidatorFramework,
    ValidationReport,
)


class ValidationScheduler:
    """Schedules and manages validation runs."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.schedule = self.config.get("schedule", {})
        self.logger = logging.getLogger("validation_scheduler")
        self.running_tasks = {}
    
    async def start_scheduled_validation(
        self,
        orchestrator: 'ValidationOrchestrator'
    ) -> None:
        """Start scheduled validation runs."""
        schedules = [
            {
                "name": "critical_checks",
                "interval_minutes": 5,
                "validators": ["token_validation", "api_contract"],
                "services": ["frontend", "backend", "auth"]
            },
            {
                "name": "comprehensive_checks", 
                "interval_minutes": 30,
                "validators": "all",
                "services": ["frontend", "backend", "auth"]
            },
            {
                "name": "performance_checks",
                "interval_minutes": 15,
                "validators": ["latency", "throughput", "resource_usage"],
                "services": ["frontend", "backend", "auth"]
            }
        ]
        
        for schedule in schedules:
            task = asyncio.create_task(
                self._run_scheduled_validation(schedule, orchestrator)
            )
            self.running_tasks[schedule["name"]] = task
    
    async def _run_scheduled_validation(
        self,
        schedule: Dict[str, Any],
        orchestrator: 'ValidationOrchestrator'
    ) -> None:
        """Run validation on schedule."""
        interval = schedule["interval_minutes"] * 60
        
        while True:
            try:
                self.logger.info(f"Starting scheduled validation: {schedule['name']}")
                
                report = await orchestrator.run_validation(
                    services=schedule["services"],
                    validator_names=schedule["validators"] if schedule["validators"] != "all" else None
                )
                
                await self._handle_scheduled_report(schedule["name"], report)
                
            except Exception as e:
                self.logger.error(f"Scheduled validation failed: {e}")
            
            await asyncio.sleep(interval)
    
    async def _handle_scheduled_report(
        self,
        schedule_name: str,
        report: ValidationReport
    ) -> None:
        """Handle scheduled validation report."""
        # Save report
        report_path = Path(f"reports/scheduled_{schedule_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report.model_dump(), f, indent=2, default=str)
        
        # Check for critical failures
        if report.failed_checks > 0:
            await self._send_alert(schedule_name, report)
    
    async def _send_alert(
        self,
        schedule_name: str,
        report: ValidationReport
    ) -> None:
        """Send alert for validation failures."""
        # Mock alert implementation
        self.logger.warning(
            f"ALERT: Validation failures in {schedule_name}: "
            f"{report.failed_checks} failed, {report.warning_checks} warnings"
        )


class ValidationReporter:
    """Generates validation reports and dashboards."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.output_dir = Path(self.config.get("output_dir", "validation_reports"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def generate_detailed_report(
        self,
        report: ValidationReport,
        format: str = "json"
    ) -> str:
        """Generate detailed validation report."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            return await self._generate_json_report(report, timestamp)
        elif format == "html":
            return await self._generate_html_report(report, timestamp)
        elif format == "markdown":
            return await self._generate_markdown_report(report, timestamp)
        else:
            raise ValueError(f"Unsupported report format: {format}")
    
    async def _generate_json_report(
        self,
        report: ValidationReport,
        timestamp: str
    ) -> str:
        """Generate JSON format report."""
        report_path = self.output_dir / f"validation_report_{timestamp}.json"
        
        with open(report_path, 'w') as f:
            json.dump(report.model_dump(), f, indent=2, default=str)
        
        return str(report_path)
    
    async def _generate_html_report(
        self,
        report: ValidationReport,
        timestamp: str
    ) -> str:
        """Generate HTML format report."""
        report_path = self.output_dir / f"validation_report_{timestamp}.html"
        
        html_content = self._create_html_report(report)
        
        with open(report_path, 'w') as f:
            f.write(html_content)
        
        return str(report_path)
    
    async def _generate_markdown_report(
        self,
        report: ValidationReport,
        timestamp: str
    ) -> str:
        """Generate Markdown format report."""
        report_path = self.output_dir / f"validation_report_{timestamp}.md"
        
        markdown_content = self._create_markdown_report(report)
        
        with open(report_path, 'w') as f:
            f.write(markdown_content)
        
        return str(report_path)
    
    def _create_html_report(self, report: ValidationReport) -> str:
        """Create HTML report content."""
        status_color = {
            "passed": "green",
            "warning": "orange", 
            "failed": "red"
        }
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Cross-Service Validation Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background-color: #f5f5f5; padding: 20px; border-radius: 5px; }}
                .status {{ color: {status_color.get(report.overall_status, 'black')}; font-weight: bold; }}
                .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
                .metric {{ background: #f0f0f0; padding: 10px; border-radius: 3px; text-align: center; }}
                .results {{ margin-top: 30px; }}
                .result {{ margin: 10px 0; padding: 15px; border-left: 4px solid #ccc; background: #f9f9f9; }}
                .result.failed {{ border-left-color: red; }}
                .result.warning {{ border-left-color: orange; }}
                .result.passed {{ border-left-color: green; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Cross-Service Validation Report</h1>
                <p><strong>Report ID:</strong> {report.report_id}</p>
                <p><strong>Generated:</strong> {report.generated_at}</p>
                <p><strong>Status:</strong> <span class="status">{report.overall_status.upper()}</span></p>
                <p><strong>Services:</strong> {', '.join(report.services_validated)}</p>
            </div>
            
            <div class="summary">
                <div class="metric">
                    <div style="font-size: 24px; font-weight: bold;">{report.total_checks}</div>
                    <div>Total Checks</div>
                </div>
                <div class="metric">
                    <div style="font-size: 24px; font-weight: bold; color: green;">{report.passed_checks}</div>
                    <div>Passed</div>
                </div>
                <div class="metric">
                    <div style="font-size: 24px; font-weight: bold; color: orange;">{report.warning_checks}</div>
                    <div>Warnings</div>
                </div>
                <div class="metric">
                    <div style="font-size: 24px; font-weight: bold; color: red;">{report.failed_checks}</div>
                    <div>Failed</div>
                </div>
                <div class="metric">
                    <div style="font-size: 24px; font-weight: bold;">{report.execution_time_ms:.0f}ms</div>
                    <div>Execution Time</div>
                </div>
            </div>
            
            <div class="results">
                <h2>Validation Results</h2>
        """
        
        for result in report.results:
            html += f"""
                <div class="result {result.status}">
                    <h3>{result.validator_name} - {result.check_name}</h3>
                    <p><strong>Status:</strong> {result.status}</p>
                    <p><strong>Severity:</strong> {result.severity}</p>
                    <p><strong>Message:</strong> {result.message}</p>
                    {f'<p><strong>Service Pair:</strong> {result.service_pair}</p>' if result.service_pair else ''}
                    {f'<p><strong>Execution Time:</strong> {result.execution_time_ms:.2f}ms</p>' if result.execution_time_ms else ''}
                </div>
            """
        
        html += """
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _create_markdown_report(self, report: ValidationReport) -> str:
        """Create Markdown report content."""
        md = f"""# Cross-Service Validation Report

## Summary

- **Report ID:** {report.report_id}
- **Generated:** {report.generated_at}
- **Status:** {report.overall_status.upper()}
- **Services:** {', '.join(report.services_validated)}
- **Execution Time:** {report.execution_time_ms:.0f}ms

## Metrics

| Metric | Count |
|--------|-------|
| Total Checks | {report.total_checks} |
| Passed | {report.passed_checks} |
| Warnings | {report.warning_checks} |
| Failed | {report.failed_checks} |
| Skipped | {report.skipped_checks} |

## Validation Results

"""
        
        for result in report.results:
            status_icon = {"passed": " PASS: ", "warning": " WARNING: [U+FE0F]", "failed": " FAIL: ", "skipped": "[U+23ED][U+FE0F]"}
            icon = status_icon.get(result.status, "[U+2753]")
            
            md += f"""### {icon} {result.validator_name} - {result.check_name}

- **Status:** {result.status}
- **Severity:** {result.severity}
- **Message:** {result.message}
"""
            if result.service_pair:
                md += f"- **Service Pair:** {result.service_pair}\n"
            if result.execution_time_ms:
                md += f"- **Execution Time:** {result.execution_time_ms:.2f}ms\n"
            
            md += "\n"
        
        if report.recommendations:
            md += "## Recommendations\n\n"
            for i, rec in enumerate(report.recommendations, 1):
                md += f"{i}. {rec}\n"
        
        return md


class ValidationOrchestrator:
    """Main orchestrator for cross-service validation."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.framework = CrossServiceValidatorFramework(config)
        self.reporter = ValidationReporter(config.get("reporter", {}))
        self.scheduler = ValidationScheduler(config.get("scheduler", {}))
        self.logger = logging.getLogger("validation_orchestrator")
        
        # Register all validators
        self._register_validators()
    
    def _register_validators(self) -> None:
        """Register all available validators."""
        # Contract validators
        self.framework.registry.register(
            APIContractValidator(self.config.get("api_contract", {})),
            category="contract"
        )
        self.framework.registry.register(
            WebSocketContractValidator(self.config.get("websocket_contract", {})),
            category="contract"
        )
        self.framework.registry.register(
            SchemaCompatibilityValidator(self.config.get("schema_compatibility", {})),
            category="contract"
        )
        self.framework.registry.register(
            EndpointValidator(self.config.get("endpoint", {})),
            category="contract"
        )
        
        # Data consistency validators
        self.framework.registry.register(
            UserDataConsistencyValidator(self.config.get("user_data", {})),
            category="data_consistency"
        )
        self.framework.registry.register(
            SessionStateValidator(self.config.get("session_state", {})),
            category="data_consistency"
        )
        self.framework.registry.register(
            MessageDeliveryValidator(self.config.get("message_delivery", {})),
            category="data_consistency"
        )
        self.framework.registry.register(
            CrossServiceDataValidator(self.config.get("cross_service_data", {})),
            category="data_consistency"
        )
        
        # Performance validators
        self.framework.registry.register(
            LatencyValidator(self.config.get("latency", {})),
            category="performance"
        )
        self.framework.registry.register(
            ThroughputValidator(self.config.get("throughput", {})),
            category="performance"
        )
        self.framework.registry.register(
            ResourceUsageValidator(self.config.get("resource_usage", {})),
            category="performance"
        )
        self.framework.registry.register(
            CommunicationOverheadValidator(self.config.get("communication_overhead", {})),
            category="performance"
        )
        
        # Security validators
        self.framework.registry.register(
            TokenValidationValidator(self.config.get("token_validation", {})),
            category="security"
        )
        self.framework.registry.register(
            PermissionEnforcementValidator(self.config.get("permission_enforcement", {})),
            category="security"
        )
        self.framework.registry.register(
            AuditTrailValidator(self.config.get("audit_trail", {})),
            category="security"
        )
        self.framework.registry.register(
            ServiceAuthValidator(self.config.get("service_auth", {})),
            category="security"
        )
    
    async def run_validation(
        self,
        services: List[str],
        validator_names: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        report_formats: List[str] = ["json"]
    ) -> ValidationReport:
        """Run comprehensive cross-service validation."""
        self.logger.info(f"Starting validation for services: {services}")
        
        # Prepare context
        validation_context = context or {}
        validation_context.update({
            "service_urls": self._get_service_urls(),
            "test_users": self._get_test_users(),
            "test_sessions": self._get_test_sessions()
        })
        
        # Run validation
        report = await self.framework.run_validation(
            services=services,
            validator_names=validator_names,
            categories=categories,
            context=validation_context
        )
        
        # Generate reports
        report_paths = []
        for format in report_formats:
            try:
                report_path = await self.reporter.generate_detailed_report(report, format)
                report_paths.append(report_path)
                self.logger.info(f"Generated {format} report: {report_path}")
            except Exception as e:
                self.logger.error(f"Failed to generate {format} report: {e}")
        
        # Log summary
        self._log_validation_summary(report)
        
        return report
    
    async def start_continuous_validation(self) -> None:
        """Start continuous validation with scheduling."""
        self.logger.info("Starting continuous validation")
        await self.scheduler.start_scheduled_validation(self)
    
    def _get_service_urls(self) -> Dict[str, str]:
        """Get service URLs for testing."""
        return self.config.get("service_urls", {
            "frontend": "http://localhost:3000",
            "backend": "http://localhost:8000", 
            "auth": "http://localhost:8081"
        })
    
    def _get_test_users(self) -> List[str]:
        """Get test user IDs for validation."""
        return self.config.get("test_users", [
            "test-user-123",
            "test-user-456", 
            "admin-user-789"
        ])
    
    def _get_test_sessions(self) -> List[str]:
        """Get test session IDs for validation."""
        return self.config.get("test_sessions", [
            "test-session-abc123",
            "test-session-def456"
        ])
    
    def _log_validation_summary(self, report: ValidationReport) -> None:
        """Log validation summary."""
        self.logger.info(f"Validation completed: {report.overall_status}")
        self.logger.info(f"Total checks: {report.total_checks}")
        self.logger.info(f"Passed: {report.passed_checks}")
        self.logger.info(f"Warnings: {report.warning_checks}")
        self.logger.info(f"Failed: {report.failed_checks}")
        self.logger.info(f"Execution time: {report.execution_time_ms:.2f}ms")
        
        if report.failed_checks > 0:
            self.logger.warning("Validation failures detected - check report for details")
        
        if report.recommendations:
            self.logger.info("Recommendations available - check report for details")


# CLI interface for running validations
async def main():
    """Main CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Cross-Service Validation")
    parser.add_argument("--services", nargs="+", default=["frontend", "backend", "auth"],
                        help="Services to validate")
    parser.add_argument("--categories", nargs="+", 
                        choices=["contract", "data_consistency", "performance", "security"],
                        help="Validation categories to run")
    parser.add_argument("--validators", nargs="+", help="Specific validators to run")
    parser.add_argument("--format", nargs="+", default=["json"], 
                        choices=["json", "html", "markdown"],
                        help="Report formats to generate")
    parser.add_argument("--continuous", action="store_true",
                        help="Run continuous validation")
    parser.add_argument("--config", help="Configuration file path")
    
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if args.config:
        with open(args.config) as f:
            config = json.load(f)
    
    # Create orchestrator
    orchestrator = ValidationOrchestrator(config)
    
    if args.continuous:
        # Start continuous validation
        await orchestrator.start_continuous_validation()
    else:
        # Run one-time validation
        report = await orchestrator.run_validation(
            services=args.services,
            validator_names=args.validators,
            categories=args.categories,
            report_formats=args.format
        )
        
        print(f"Validation completed with status: {report.overall_status}")
        print(f"Results: {report.passed_checks} passed, {report.warning_checks} warnings, {report.failed_checks} failed")


if __name__ == "__main__":
    asyncio.run(main())