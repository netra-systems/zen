#!/usr/bin/env python3
"""
Coverage analysis script for Netra Apex codebase.
Analyzes existing coverage data to identify critical low-coverage areas.
"""

import json
from pathlib import Path

def analyze_coverage():
    try:
        with open('coverage.json', 'r') as f:
            data = json.load(f)

        print('=== COVERAGE ANALYSIS SUMMARY ===')
        print(f'Overall Line Coverage: {data["totals"]["percent_covered"]:.1f}%')
        if "percent_covered_branches" in data["totals"]:
            print(f'Branch Coverage: {data["totals"]["percent_covered_branches"]:.1f}%')
        print(f'Total Lines: {data["totals"]["num_statements"]}')
        print(f'Covered Lines: {data["totals"]["covered_lines"]}')
        print()

        # Analyze by modules
        files = data['files']
        modules = {}

        for filepath, coverage in files.items():
            if not any(exclude in filepath for exclude in ['test', 'migration', '__pycache__']):
                # Group by main module
                parts = filepath.replace('\\', '/').split('/')
                if len(parts) >= 2:
                    if parts[0] == 'netra_backend' and len(parts) >= 3:
                        module = f'{parts[0]}/{parts[1]}/{parts[2]}' if len(parts) >= 4 else f'{parts[0]}/{parts[1]}'
                    elif parts[0] == 'auth_service':
                        module = f'{parts[0]}/{parts[1]}' if len(parts) >= 2 else parts[0]
                    elif parts[0] == 'shared':
                        module = f'{parts[0]}/{parts[1]}' if len(parts) >= 2 else parts[0]
                    else:
                        module = parts[0]

                    if module not in modules:
                        modules[module] = {'total_lines': 0, 'covered_lines': 0, 'files': 0}

                    modules[module]['total_lines'] += coverage['summary']['num_statements']
                    modules[module]['covered_lines'] += coverage['summary']['covered_lines']
                    modules[module]['files'] += 1

        # Sort by coverage percentage
        module_coverage = []
        for module, stats in modules.items():
            if stats['total_lines'] > 0:
                coverage_pct = (stats['covered_lines'] / stats['total_lines']) * 100
                module_coverage.append((module, coverage_pct, stats['total_lines'], stats['covered_lines'], stats['files']))

        module_coverage.sort(key=lambda x: x[1])  # Sort by coverage %

        print('=== MODULES BY COVERAGE (LOWEST FIRST) ===')
        print(f'{"Module":<40} {"Coverage%":<10} {"Lines":<8} {"Covered":<8} {"Files":<5}')
        print('=' * 75)

        for module, coverage_pct, total_lines, covered_lines, file_count in module_coverage[:20]:  # Top 20 lowest
            print(f'{module:<40} {coverage_pct:>7.1f}% {total_lines:>7} {covered_lines:>7} {file_count:>4}')

        print()
        print('=== BUSINESS CRITICAL MODULES (TOP PRIORITY) ===')
        business_critical = ['netra_backend/app/websocket_core', 'netra_backend/app/agents', 'netra_backend/app/auth_integration', 'netra_backend/app/db', 'auth_service']

        critical_modules = []
        for module, coverage_pct, total_lines, covered_lines, file_count in module_coverage:
            if any(bc in module for bc in business_critical):
                priority = 'CRITICAL' if coverage_pct < 20 else 'HIGH' if coverage_pct < 50 else 'MEDIUM' if coverage_pct < 70 else 'LOW'
                critical_modules.append((module, coverage_pct, total_lines, priority))

        critical_modules.sort(key=lambda x: x[1])  # Sort by coverage

        for module, coverage_pct, total_lines, priority in critical_modules:
            print(f'{module:<40} {coverage_pct:>7.1f}% {total_lines:>7} lines [{priority}]')

        print()
        print('=== RECOMMENDATIONS ===')
        lowest_critical = [m for m in critical_modules if m[3] in ['CRITICAL', 'HIGH']]
        if lowest_critical:
            top_target = lowest_critical[0]
            print(f'TOP PRIORITY: {top_target[0]}')
            print(f'  - Current Coverage: {top_target[1]:.1f}%')
            print(f'  - Lines of Code: {top_target[2]}')
            print(f'  - Business Impact: {"CRITICAL - WebSocket/Agents (90% platform value)" if "websocket" in top_target[0] or "agents" in top_target[0] else "HIGH - Core infrastructure"}')
            print(f'  - Target Coverage: 70%+ (industry standard for business-critical code)')

        return critical_modules

    except FileNotFoundError:
        print('No coverage.json file found. Please run tests with coverage first.')
        return None
    except Exception as e:
        print(f'Error reading coverage data: {e}')
        return None

if __name__ == '__main__':
    analyze_coverage()