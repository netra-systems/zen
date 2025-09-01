#!/usr/bin/env python
"""WebSocket Event Compliance Validator

Validates that the WebSocket implementation follows the specification from 
SPEC/learnings/websocket_agent_integration_critical.xml
"""

import os
import sys
import json
from typing import Dict, List, Set, Tuple
from pathlib import Path
import xml.etree.ElementTree as ET
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class WebSocketComplianceValidator:
    """Validates WebSocket implementation against specification."""
    
    def __init__(self):
        self.spec_path = project_root / "SPEC" / "learnings" / "websocket_agent_integration_critical.xml"
        self.required_events: Set[str] = set()
        self.critical_events: Set[str] = set()
        self.validation_results: List[Dict] = []
        self.compliance_score = 0
        
    def load_specification(self) -> bool:
        """Load WebSocket specification from XML."""
        try:
            tree = ET.parse(self.spec_path)
            root = tree.getroot()
            
            # Extract required events
            events = root.find('.//required_events')
            if events:
                for event in events.findall('event'):
                    event_name = event.get('name')
                    is_critical = event.get('critical') == 'true'
                    
                    self.required_events.add(event_name)
                    if is_critical:
                        self.critical_events.add(event_name)
                        
            logger.info(f"Loaded {len(self.required_events)} required events, {len(self.critical_events)} critical")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load specification: {e}")
            return False
    
    def validate_websocket_notifier(self) -> Tuple[bool, List[str]]:
        """Validate WebSocketNotifier implementation."""
        notifier_path = project_root / "netra_backend" / "app" / "agents" / "supervisor" / "websocket_notifier.py"
        
        if not notifier_path.exists():
            return False, ["WebSocketNotifier file not found"]
        
        issues = []
        with open(notifier_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for required event methods
        for event in self.required_events:
            method_name = f"send_{event}"
            if method_name not in content:
                issues.append(f"Missing method: {method_name}")
                
        # Check for async implementation
        for event in self.required_events:
            method_sig = f"async def send_{event}"
            if method_sig not in content:
                issues.append(f"Method not async: send_{event}")
                
        return len(issues) == 0, issues
    
    def validate_agent_registry(self) -> Tuple[bool, List[str]]:
        """Validate AgentRegistry WebSocket enhancement."""
        registry_path = project_root / "netra_backend" / "app" / "agents" / "supervisor" / "agent_registry.py"
        
        if not registry_path.exists():
            return False, ["AgentRegistry file not found"]
        
        issues = []
        with open(registry_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for WebSocket manager integration
        if "set_websocket_manager" not in content:
            issues.append("Missing set_websocket_manager method")
            
        # Check for tool dispatcher enhancement
        if "enhance_tool_dispatcher_with_notifications" not in content:
            issues.append("Tool dispatcher not enhanced with notifications")
            
        # Check for WebSocket manager storage
        if "self.websocket_manager" not in content:
            issues.append("WebSocket manager not stored in registry")
            
        return len(issues) == 0, issues
    
    def validate_execution_engine(self) -> Tuple[bool, List[str]]:
        """Validate ExecutionEngine WebSocket integration."""
        engine_path = project_root / "netra_backend" / "app" / "agents" / "supervisor" / "execution_engine.py"
        
        if not engine_path.exists():
            return False, ["ExecutionEngine file not found"]
        
        issues = []
        with open(engine_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for WebSocketNotifier usage
        if "WebSocketNotifier" not in content:
            issues.append("WebSocketNotifier not imported")
            
        if "self.websocket_notifier" not in content:
            issues.append("WebSocketNotifier not initialized")
            
        # Check for event sending
        critical_calls = [
            "send_agent_started",
            "send_agent_thinking",
            "send_agent_completed"
        ]
        
        for call in critical_calls:
            if call not in content:
                issues.append(f"Missing critical event call: {call}")
                
        return len(issues) == 0, issues
    
    def validate_unified_tool_execution(self) -> Tuple[bool, List[str]]:
        """Validate UnifiedToolExecutionEngine implementation."""
        enhanced_path = project_root / "netra_backend" / "app" / "agents" / "unified_tool_execution.py"
        
        if not enhanced_path.exists():
            return False, ["UnifiedToolExecutionEngine file not found"]
        
        issues = []
        with open(enhanced_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for tool event sending
        if "send_tool_executing" not in content:
            issues.append("Missing send_tool_executing")
            
        if "send_tool_completed" not in content:
            issues.append("Missing send_tool_completed")
            
        # Check for enhancement function
        if "enhance_tool_dispatcher_with_notifications" not in content:
            issues.append("Missing enhancement function")
            
        # Check for _websocket_enhanced flag
        if "_websocket_enhanced" not in content:
            issues.append("Missing _websocket_enhanced flag")
            
        return len(issues) == 0, issues
    
    def validate_frontend_provider(self) -> Tuple[bool, List[str]]:
        """Validate frontend WebSocketProvider."""
        provider_path = project_root / "frontend" / "providers" / "WebSocketProvider.tsx"
        
        if not provider_path.exists():
            return False, ["WebSocketProvider file not found"]
        
        issues = []
        with open(provider_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for event handling
        for event in self.critical_events:
            if f"'{event}'" not in content and f'"{event}"' not in content:
                issues.append(f"Frontend not handling event: {event}")
                
        # Check for reconnection logic
        if "reconnect" not in content.lower():
            issues.append("No reconnection logic found")
            
        # Check for error handling
        if "onError" not in content:
            issues.append("No error handling callback")
            
        # Check for auth integration
        if "token" not in content.lower():
            issues.append("No token/auth integration")
            
        return len(issues) == 0, issues
    
    def validate_test_coverage(self) -> Tuple[bool, List[str]]:
        """Validate test coverage for WebSocket events."""
        test_path = project_root / "tests" / "mission_critical" / "test_websocket_agent_events_suite.py"
        
        if not test_path.exists():
            return False, ["Mission critical test suite not found"]
        
        issues = []
        with open(test_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for critical event testing
        for event in self.critical_events:
            if event not in content:
                issues.append(f"Event not tested: {event}")
                
        # Check for validation methods
        required_validations = [
            "validate_critical_requirements",
            "validate_event_ordering",
            "validate_all_events_sent"
        ]
        
        for validation in required_validations:
            if validation not in content:
                issues.append(f"Missing validation: {validation}")
                
        return len(issues) == 0, issues
    
    def run_compliance_check(self) -> Dict:
        """Run full compliance check."""
        logger.info("Starting WebSocket compliance validation...")
        
        if not self.load_specification():
            return {
                'compliant': False,
                'score': 0,
                'error': 'Failed to load specification'
            }
        
        # Run all validations
        validations = [
            ('WebSocketNotifier', self.validate_websocket_notifier),
            ('AgentRegistry', self.validate_agent_registry),
            ('ExecutionEngine', self.validate_execution_engine),
            ('EnhancedToolExecution', self.validate_unified_tool_execution),
            ('FrontendProvider', self.validate_frontend_provider),
            ('TestCoverage', self.validate_test_coverage)
        ]
        
        results = {}
        total_score = 0
        max_score = len(validations) * 100
        
        for name, validator in validations:
            is_valid, issues = validator()
            score = 100 if is_valid else max(0, 100 - (len(issues) * 20))
            total_score += score
            
            results[name] = {
                'valid': is_valid,
                'score': score,
                'issues': issues
            }
            
            if is_valid:
                logger.success(f"[OK] {name}: COMPLIANT")
            else:
                logger.warning(f"[FAIL] {name}: {len(issues)} issues found")
                for issue in issues:
                    logger.debug(f"  - {issue}")
        
        # Calculate overall compliance
        compliance_score = (total_score / max_score) * 100
        is_compliant = compliance_score >= 80  # 80% threshold
        
        # Generate report
        report = {
            'compliant': is_compliant,
            'score': compliance_score,
            'required_events': list(self.required_events),
            'critical_events': list(self.critical_events),
            'validations': results,
            'summary': {
                'total_validations': len(validations),
                'passed': sum(1 for r in results.values() if r['valid']),
                'failed': sum(1 for r in results.values() if not r['valid']),
                'total_issues': sum(len(r['issues']) for r in results.values())
            }
        }
        
        return report
    
    def generate_compliance_report(self, report: Dict) -> str:
        """Generate human-readable compliance report."""
        lines = [
            "=" * 60,
            "WEBSOCKET EVENT COMPLIANCE REPORT",
            "=" * 60,
            "",
            f"Overall Compliance Score: {report['score']:.1f}%",
            f"Status: {'COMPLIANT' if report['compliant'] else 'NON-COMPLIANT'}",
            "",
            "Required Events:",
            *[f"  - {event}" for event in report['required_events']],
            "",
            "Critical Events (MUST have):",
            *[f"  - {event}" for event in report['critical_events']],
            "",
            "Validation Results:",
            "-" * 40
        ]
        
        for name, result in report['validations'].items():
            status = "[OK]" if result['valid'] else "[FAIL]"
            lines.append(f"{status} {name}: {result['score']}%")
            if not result['valid']:
                for issue in result['issues'][:3]:  # Show first 3 issues
                    lines.append(f"    - {issue}")
                if len(result['issues']) > 3:
                    lines.append(f"    ... and {len(result['issues']) - 3} more issues")
        
        lines.extend([
            "",
            "-" * 40,
            "Summary:",
            f"  Total Validations: {report['summary']['total_validations']}",
            f"  Passed: {report['summary']['passed']}",
            f"  Failed: {report['summary']['failed']}",
            f"  Total Issues: {report['summary']['total_issues']}",
            "",
            "=" * 60
        ])
        
        return "\n".join(lines)


def main():
    """Run compliance validation."""
    validator = WebSocketComplianceValidator()
    report = validator.run_compliance_check()
    
    # Generate and print report
    report_text = validator.generate_compliance_report(report)
    print(report_text)
    
    # Save report to file
    report_path = project_root / "WEBSOCKET_COMPLIANCE_REPORT.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Report saved to {report_path}")
    
    # Exit with appropriate code
    sys.exit(0 if report['compliant'] else 1)


if __name__ == "__main__":
    main()