#!/usr/bin/env python3
"""
Comprehensive GitHub Issues Search Script
Searches for existing issues related to test failures on Windows
"""

import subprocess
import json
import sys
from datetime import datetime

def run_gh_command(cmd_args):
    """Execute a GitHub CLI command and return parsed output."""
    try:
        result = subprocess.run(
            ['gh'] + cmd_args,
            capture_output=True,
            text=True,
            check=True
        )
        return {'success': True, 'output': result.stdout.strip(), 'error': None}
    except subprocess.CalledProcessError as e:
        return {'success': False, 'output': e.stdout, 'error': e.stderr}
    except FileNotFoundError:
        return {'success': False, 'output': '', 'error': 'GitHub CLI not found'}

def search_issues_by_keywords(keywords):
    """Search for issues using specific keywords."""
    print(f"\n🔍 Searching for issues with keywords: {', '.join(keywords)}")

    all_results = []

    for keyword in keywords:
        print(f"  → Searching: '{keyword}'")
        result = run_gh_command([
            'issue', 'list',
            '--search', keyword,
            '--state', 'all',
            '--limit', '20',
            '--json', 'number,title,state,labels,createdAt,updatedAt'
        ])

        if result['success']:
            try:
                issues = json.loads(result['output'])
                for issue in issues:
                    issue['search_keyword'] = keyword
                all_results.extend(issues)
            except json.JSONDecodeError:
                print(f"    ❌ Failed to parse JSON for keyword '{keyword}'")
        else:
            print(f"    ❌ Search failed for '{keyword}': {result['error']}")

    return all_results

def get_specific_issues(issue_numbers):
    """Get details for specific issue numbers."""
    print(f"\n📋 Getting details for specific issues: {', '.join(map(str, issue_numbers))}")

    issue_details = {}

    for issue_num in issue_numbers:
        print(f"  → Getting issue #{issue_num}")
        result = run_gh_command([
            'issue', 'view', str(issue_num),
            '--json', 'number,title,state,labels,body,comments,createdAt,updatedAt'
        ])

        if result['success']:
            try:
                issue_data = json.loads(result['output'])
                issue_details[issue_num] = issue_data
                print(f"    ✅ Issue #{issue_num}: {issue_data['title'][:50]}...")
            except json.JSONDecodeError:
                print(f"    ❌ Failed to parse JSON for issue #{issue_num}")
        else:
            print(f"    ❌ Failed to get issue #{issue_num}: {result['error']}")

    return issue_details

def get_priority_issues():
    """Get high priority open issues."""
    print(f"\n🚨 Getting high priority open issues")

    priority_labels = ['P0', 'P1', 'critical', 'urgent', 'infrastructure-crisis']
    priority_issues = []

    for label in priority_labels:
        result = run_gh_command([
            'issue', 'list',
            '--label', label,
            '--state', 'open',
            '--json', 'number,title,state,labels,createdAt,updatedAt'
        ])

        if result['success']:
            try:
                issues = json.loads(result['output'])
                for issue in issues:
                    issue['priority_label'] = label
                priority_issues.extend(issues)
            except json.JSONDecodeError:
                print(f"    ❌ Failed to parse JSON for label '{label}'")
        else:
            print(f"    ❌ Failed to search label '{label}': {result['error']}")

    return priority_issues

def main():
    """Main execution function."""
    print("🔍 GitHub Issues Comprehensive Search")
    print("=" * 50)

    # Check GitHub CLI availability
    auth_result = run_gh_command(['auth', 'status'])
    if not auth_result['success']:
        print("❌ GitHub CLI not authenticated or not available")
        print("Please run: gh auth login")
        return 1

    print("✅ GitHub CLI authenticated and ready")

    # Define search keywords for test failures
    test_failure_keywords = [
        "agent test failure",
        "e2e test failure",
        "test failing",
        "python execution",
        "windows test",
        "golden path test",
        "staging test",
        "websocket test",
        "infrastructure test",
        "test timeout",
        "test collection",
        "pytest error",
        "python command",
        "test runner",
        "agent execution",
        "test infrastructure"
    ]

    # Specific issue numbers mentioned in the project
    specific_issues = [1176, 1142, 667, 1278, 1184, 1115, 1197, 891]

    # Search for test failure related issues
    search_results = search_issues_by_keywords(test_failure_keywords)

    # Get specific issue details
    issue_details = get_specific_issues(specific_issues)

    # Get high priority issues
    priority_issues = get_priority_issues()

    # Compile comprehensive report
    print("\n" + "=" * 50)
    print("📊 COMPREHENSIVE GITHUB ISSUES REPORT")
    print("=" * 50)

    # Remove duplicates from search results
    unique_issues = {}
    for issue in search_results:
        issue_num = issue['number']
        if issue_num not in unique_issues:
            unique_issues[issue_num] = issue
        else:
            # Add additional search keywords
            if 'search_keywords' not in unique_issues[issue_num]:
                unique_issues[issue_num]['search_keywords'] = [unique_issues[issue_num]['search_keyword']]
            unique_issues[issue_num]['search_keywords'].append(issue['search_keyword'])

    print(f"\n🔍 SEARCH RESULTS SUMMARY:")
    print(f"  • Found {len(unique_issues)} unique issues from keyword searches")
    print(f"  • Retrieved {len(issue_details)} specific issue details")
    print(f"  • Found {len(priority_issues)} high priority open issues")

    # Test failure related issues
    print(f"\n📋 TEST FAILURE RELATED ISSUES:")
    test_related_count = 0
    for issue_num, issue in unique_issues.items():
        title = issue['title'].lower()
        if any(keyword in title for keyword in ['test', 'agent', 'e2e', 'staging', 'websocket', 'python', 'execution']):
            test_related_count += 1
            state_icon = "🟢" if issue['state'] == 'closed' else "🔴"
            print(f"  {state_icon} #{issue_num}: {issue['title'][:80]}...")
            if 'search_keywords' in issue:
                print(f"      Keywords: {', '.join(issue['search_keywords'])}")

    print(f"\n  Total test-related issues: {test_related_count}")

    # Specific tracked issues
    print(f"\n📌 SPECIFIC TRACKED ISSUES:")
    for issue_num in specific_issues:
        if issue_num in issue_details:
            issue = issue_details[issue_num]
            state_icon = "🟢" if issue['state'] == 'closed' else "🔴"
            print(f"  {state_icon} #{issue_num}: {issue['title'][:80]}...")
            print(f"      State: {issue['state']}")
            print(f"      Updated: {issue['updatedAt'][:10]}")
            if issue['labels']:
                labels = [label['name'] for label in issue['labels']]
                print(f"      Labels: {', '.join(labels)}")
        else:
            print(f"  ❓ #{issue_num}: Could not retrieve details")

    # High priority issues
    print(f"\n🚨 HIGH PRIORITY OPEN ISSUES:")
    if priority_issues:
        for issue in priority_issues[:10]:  # Limit to 10 most recent
            print(f"  🔴 #{issue['number']}: {issue['title'][:80]}...")
            if issue['labels']:
                labels = [label['name'] for label in issue['labels']]
                print(f"      Labels: {', '.join(labels)}")
    else:
        print("  ✅ No high priority open issues found")

    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")

    # Check for existing agent/test failure issues
    agent_issues = [i for i in unique_issues.values() if 'agent' in i['title'].lower() and i['state'] == 'open']
    e2e_issues = [i for i in unique_issues.values() if 'e2e' in i['title'].lower() and i['state'] == 'open']
    test_issues = [i for i in unique_issues.values() if 'test' in i['title'].lower() and i['state'] == 'open']

    if agent_issues:
        print(f"  📝 Found {len(agent_issues)} open agent-related issues - consider updating existing issues")
    else:
        print(f"  🆕 No open agent-related issues found - may need to create new issue")

    if e2e_issues:
        print(f"  📝 Found {len(e2e_issues)} open E2E test issues - consider updating existing issues")
    else:
        print(f"  🆕 No open E2E test issues found - may need to create new issue")

    if test_issues:
        print(f"  📝 Found {len(test_issues)} open test-related issues - review for relevance")
    else:
        print(f"  🆕 No open test-related issues found")

    # Windows/Python specific
    windows_issues = [i for i in unique_issues.values() if any(w in i['title'].lower() for w in ['windows', 'python', 'execution', 'command'])]
    if windows_issues:
        print(f"  🖥️ Found {len(windows_issues)} Windows/Python execution issues")
    else:
        print(f"  🆕 No Windows/Python execution issues found - may need to create")

    # Save detailed report to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"github_issues_search_report_{timestamp}.json"

    report_data = {
        "timestamp": datetime.now().isoformat(),
        "search_keywords": test_failure_keywords,
        "unique_search_results": dict(unique_issues),
        "specific_issue_details": issue_details,
        "priority_issues": priority_issues,
        "summary": {
            "total_unique_issues": len(unique_issues),
            "test_related_count": test_related_count,
            "agent_issues_open": len(agent_issues),
            "e2e_issues_open": len(e2e_issues),
            "test_issues_open": len(test_issues),
            "windows_python_issues": len(windows_issues)
        }
    }

    with open(report_file, 'w') as f:
        json.dump(report_data, f, indent=2)

    print(f"\n💾 Detailed report saved to: {report_file}")
    print(f"\n✅ GitHub issues search complete!")

    return 0

if __name__ == '__main__':
    sys.exit(main())