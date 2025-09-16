#!/usr/bin/env python3
"""Validate Current Redis SSOT State

Quick validation script to assess current Redis SSOT violations and provide
immediate actionable remediation steps.

Usage:
    python scripts/validate_redis_ssot_current_state.py
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def find_redis_violations(base_path: Path) -> Dict[str, List[Dict]]:
    """Find all Redis SSOT violations in the codebase."""
    violations = defaultdict(list)

    # Violation patterns
    patterns = {
        'direct_instantiation': r'RedisManager\(\)',
        'auth_instantiation': r'AuthRedisManager\(\)',
        'variable_assignment': r'\w+\s*=\s*(?:Redis|Auth)Manager\(\)',
        'class_attribute': r'self\.\w+\s*=\s*(?:Redis|Auth)Manager\(\)',
    }

    # Priority file categories
    priority_files = {
        'websocket_core': [
            'netra_backend/app/websocket_core/',
            'netra_backend/app/routes/websocket.py',
            'netra_backend/app/core/websocket_cors.py'
        ],
        'agent_execution': [
            'netra_backend/app/agents/',
            'netra_backend/app/services/state_persistence'
        ],
        'service_init': [
            'netra_backend/app/startup_module.py',
            'netra_backend/app/core/startup_validation.py'
        ],
        'auth_service': [
            'auth_service/'
        ],
        'tests': [
            'tests/',
            'netra_backend/tests/'
        ]
    }

    def categorize_file(file_path: str) -> str:
        """Categorize file by priority."""
        for category, paths in priority_files.items():
            if any(path in file_path for path in paths):
                return category
        return 'other'

    # Search for violations
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if not file.endswith('.py'):
                continue

            file_path = Path(root) / file
            rel_path = file_path.relative_to(base_path)

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')

                for line_num, line in enumerate(lines, 1):
                    for pattern_name, pattern in patterns.items():
                        if re.search(pattern, line):
                            violation = {
                                'file': str(rel_path),
                                'line': line_num,
                                'code': line.strip(),
                                'pattern': pattern_name,
                                'category': categorize_file(str(rel_path))
                            }
                            violations[pattern_name].append(violation)

            except Exception as e:
                logger.warning(f"Error reading {file_path}: {e}")

    return violations


def analyze_violations(violations: Dict[str, List[Dict]]) -> Dict:
    """Analyze violations and prioritize remediation."""

    # Count by category
    category_counts = defaultdict(int)
    for pattern_violations in violations.values():
        for violation in pattern_violations:
            category_counts[violation['category']] += 1

    # Priority mapping
    priority_map = {
        'websocket_core': 1,
        'agent_execution': 2,
        'service_init': 3,
        'auth_service': 3,
        'tests': 4,
        'other': 4
    }

    # Priority analysis
    priority_violations = defaultdict(list)
    for pattern_violations in violations.values():
        for violation in pattern_violations:
            priority = priority_map.get(violation['category'], 4)
            priority_violations[priority].append(violation)

    total_violations = sum(len(v) for v in violations.values())

    analysis = {
        'total_violations': total_violations,
        'violations_by_pattern': {k: len(v) for k, v in violations.items()},
        'violations_by_category': dict(category_counts),
        'violations_by_priority': {p: len(v) for p, v in priority_violations.items()},
        'priority_breakdown': {
            1: {'name': 'Core WebSocket Integration', 'count': len(priority_violations[1])},
            2: {'name': 'Agent Execution Components', 'count': len(priority_violations[2])},
            3: {'name': 'Service Initialization', 'count': len(priority_violations[3])},
            4: {'name': 'Test Infrastructure', 'count': len(priority_violations[4])}
        }
    }

    return analysis, priority_violations


def check_ssot_infrastructure(base_path: Path) -> Dict[str, bool]:
    """Check if SSOT infrastructure is in place."""

    checks = {
        'main_redis_manager': (base_path / 'netra_backend/app/redis_manager.py').exists(),
        'auth_redis_manager': (base_path / 'auth_service/auth_core/redis_manager.py').exists(),
        'global_singleton': False,
        'factory_function': False,
        'validation_tests': (base_path / 'tests/mission_critical/test_redis_ssot_factory_validation.py').exists()
    }

    # Check for global singleton
    redis_manager_file = base_path / 'netra_backend/app/redis_manager.py'
    if redis_manager_file.exists():
        try:
            with open(redis_manager_file, 'r') as f:
                content = f.read()
                if 'redis_manager = RedisManager()' in content:
                    checks['global_singleton'] = True
                if 'def get_redis_manager()' in content:
                    checks['factory_function'] = True
        except Exception:
            pass

    return checks


def generate_immediate_action_plan(analysis: Dict, priority_violations: Dict,
                                 ssot_status: Dict) -> List[str]:
    """Generate immediate action plan."""

    actions = []

    # Check SSOT readiness
    if not all(ssot_status.values()):
        actions.append("❌ SSOT infrastructure incomplete - fix infrastructure first")
        missing = [k for k, v in ssot_status.items() if not v]
        actions.append(f"   Missing components: {', '.join(missing)}")
    else:
        actions.append("✅ SSOT infrastructure ready")

    # Priority 1 actions
    p1_count = analysis['priority_breakdown'][1]['count']
    if p1_count > 0:
        actions.append(f"🔥 IMMEDIATE: Fix {p1_count} Priority 1 violations (WebSocket core)")
        actions.append("   Command: python scripts/redis_ssot_remediation_priority1.py --dry-run")
        actions.append("   Then: python scripts/redis_ssot_remediation_priority1.py")

    # Priority 2 actions
    p2_count = analysis['priority_breakdown'][2]['count']
    if p2_count > 0:
        actions.append(f"⚡ NEXT: Fix {p2_count} Priority 2 violations (Agent execution)")

    # Validation actions
    if analysis['total_violations'] > 0:
        actions.append("🧪 VALIDATE: Run tests after each priority level")
        actions.append("   Test: python tests/mission_critical/test_redis_ssot_factory_validation.py")
        actions.append("   Test: python tests/mission_critical/test_websocket_agent_events_suite.py")

    return actions


def main():
    """Main execution."""
    base_path = Path("C:/netra-apex")

    if not base_path.exists():
        logger.error(f"Base path not found: {base_path}")
        return 1

    logger.info("🔍 Scanning for Redis SSOT violations...")
    violations = find_redis_violations(base_path)

    logger.info("📊 Analyzing violations...")
    analysis, priority_violations = analyze_violations(violations)

    logger.info("🏗️ Checking SSOT infrastructure...")
    ssot_status = check_ssot_infrastructure(base_path)

    # Display results
    print("\n" + "="*80)
    print("REDIS SSOT VIOLATION ANALYSIS")
    print("="*80)

    print(f"\n📈 SUMMARY:")
    print(f"   Total violations: {analysis['total_violations']}")
    print(f"   By pattern:")
    for pattern, count in analysis['violations_by_pattern'].items():
        print(f"     - {pattern}: {count}")

    print(f"\n🎯 PRIORITY BREAKDOWN:")
    for priority, info in analysis['priority_breakdown'].items():
        if info['count'] > 0:
            print(f"   Priority {priority} ({info['name']}): {info['count']} violations")

    print(f"\n🏗️ SSOT INFRASTRUCTURE:")
    for component, status in ssot_status.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {component}: {'Ready' if status else 'Missing'}")

    # Generate action plan
    actions = generate_immediate_action_plan(analysis, priority_violations, ssot_status)

    print(f"\n🎯 IMMEDIATE ACTION PLAN:")
    for i, action in enumerate(actions, 1):
        print(f"   {i}. {action}")

    # Save detailed report
    report = {
        'summary': analysis,
        'ssot_infrastructure': ssot_status,
        'action_plan': actions,
        'detailed_violations': {k: v for k, v in violations.items()}
    }

    report_path = base_path / "redis_ssot_current_state_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n📋 Detailed report saved: {report_path}")

    # Determine urgency
    p1_violations = analysis['priority_breakdown'][1]['count']
    if p1_violations > 0:
        print(f"\n🚨 CRITICAL: {p1_violations} Priority 1 violations found!")
        print("   These directly impact WebSocket functionality and chat reliability.")
        print("   Immediate remediation required for Golden Path restoration.")
        return 2  # Critical urgency
    elif analysis['total_violations'] > 0:
        print(f"\n⚠️ WARNING: {analysis['total_violations']} total violations found.")
        print("   Plan remediation to prevent future issues.")
        return 1  # Warning level
    else:
        print("\n✅ SUCCESS: No Redis SSOT violations found!")
        return 0  # All good


if __name__ == "__main__":
    exit(main())