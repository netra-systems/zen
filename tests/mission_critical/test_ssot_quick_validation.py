from shared.isolated_environment import get_env
'''
Quick SSOT Compliance Validation - No External Dependencies

This version runs the core SSOT validation without requiring external service connections.
Perfect for CI/CD and immediate validation of SSOT fixes.
'''

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.mission_critical.test_ssot_compliance_suite import SSotComplianceSuite


def run_quick_ssot_validation():
    "Run SSOT validation without external dependencies.
print(QUICK SSOT COMPLIANCE VALIDATION"")
print(= * 50)"

suite = SSotComplianceSuite()

    # Run core validations (skip WebSocket events test)
print(1. WebSocket Manager Consolidation")
websocket_violations = suite.validate_websocket_manager_consolidation()
print("")

print(2. JWT Validation Security)"
jwt_violations = suite.validate_jwt_validation_security()
print(")

print(
3. Agent Registry Consolidation"")
agent_violations = suite.validate_agent_registry_consolidation()
print(")"

print(
4. IsolatedEnvironment Consolidation)
env_violations = suite.validate_isolated_environment_consolidation()
print("")

print(
5. Session Management Consolidation")"
session_violations = suite.validate_session_management_consolidation()
print()"

print(
6. Tool Execution Consolidation")
tool_violations = suite.validate_tool_execution_consolidation()
print("")

print(
7. Direct os.environ Access)"
os_violations = suite.validate_direct_os_environ_access()
print(")

    # Calculate results
all_violations = (websocket_violations + jwt_violations + agent_violations + )
env_violations + session_violations + tool_violations +
os_violations)

critical_count = sum(1 for v in all_violations if v.severity == 'CRITICAL')
high_count = sum(1 for v in all_violations if v.severity == 'HIGH')

    # Calculate compliance score
max_score = 100
deductions = (critical_count * 50) + (high_count * 30) + \
(sum(1 for v in all_violations if v.severity == 'MEDIUM') * 15) + \
(sum(1 for v in all_violations if v.severity == 'LOW') * 5)

compliance_score = max(0, max_score - deductions)

print(f )
 + "= * 50)
print(fSSOT COMPLIANCE RESULTS:")
print("")
print(formatted_string)"
print(")
print(formatted_string"")

    # Show critical violations details
critical_violations = [item for item in []]
if critical_violations:
    print(f )
CRITICAL VIOLATIONS (TOP 10):)
for i, violation in enumerate(critical_violations[:10], 1):
    print(formatted_string"")
    print(")"
print(formatted_string)

print(f" ")
 + = * 50)

if compliance_score >= 85:
    print(STATUS: PASSED - Ready for deployment")"
return True
else:
    print(STATUS: FAILED - Critical SSOT violations must be fixed"")"
return False


if __name__ == '__main__':
    success = run_quick_ssot_validation()
sys.exit(0 if success else 1)

pass
