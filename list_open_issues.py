#!/usr/bin/env python3
"""
Simple script to list open GitHub issues
"""
import subprocess
import json
import sys
from datetime import datetime, timedelta

def get_open_issues():
    """Get list of open issues using gh CLI"""
    try:
        # Get open issues in JSON format
        result = subprocess.run(
            ["gh", "issue", "list", "--state", "open", "--json", "number,title,labels,updatedAt"],
            capture_output=True,
            text=True,
            check=True
        )

        issues = json.loads(result.stdout)
        return issues
    except subprocess.CalledProcessError as e:
        print(f"Error running gh command: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return []

def filter_issues(issues):
    """Filter out issues with recent agent session tags"""
    current_time = datetime.now()
    twenty_minutes_ago = current_time - timedelta(minutes=20)

    filtered_issues = []

    for issue in issues:
        # Check for actively-being-worked-on label
        if any(label.get('name') == 'actively-being-worked-on' for label in issue.get('labels', [])):
            print(f"Skipping issue #{issue['number']} - actively being worked on")
            continue

        # Check for recent agent session tags
        recent_agent_session = False
        for label in issue.get('labels', []):
            label_name = label.get('name', '')
            if label_name.startswith('agent-session-'):
                # Extract timestamp from label (format: agent-session-YYYYMMDD-HHMMSS)
                try:
                    timestamp_str = label_name.replace('agent-session-', '')
                    # Parse timestamp
                    label_time = datetime.strptime(timestamp_str, '%Y%m%d-%H%M%S')
                    if label_time > twenty_minutes_ago:
                        recent_agent_session = True
                        print(f"Skipping issue #{issue['number']} - recent agent session: {label_name}")
                        break
                except (ValueError, IndexError):
                    # If we can't parse the timestamp, assume it's not recent
                    pass

        if not recent_agent_session:
            filtered_issues.append(issue)

    return filtered_issues

def prioritize_issues(issues):
    """Prioritize issues based on criticality"""
    critical_keywords = ['websocket', 'chat', 'database', 'p0', 'critical', 'outage', 'golden path']

    def get_priority_score(issue):
        score = 0
        title = issue['title'].lower()

        for keyword in critical_keywords:
            if keyword in title:
                score += 10

        # Check labels for priority indicators
        for label in issue.get('labels', []):
            label_name = label.get('name', '').lower()
            if 'p0' in label_name or 'critical' in label_name:
                score += 20
            elif 'p1' in label_name or 'high' in label_name:
                score += 15
            elif 'bug' in label_name:
                score += 5

        return score

    return sorted(issues, key=get_priority_score, reverse=True)

def main():
    print("Fetching open GitHub issues...")
    issues = get_open_issues()

    if not issues:
        print("No issues found or error fetching issues")
        return

    print(f"Found {len(issues)} open issues")

    # Filter out issues with recent activity
    filtered_issues = filter_issues(issues)
    print(f"After filtering: {len(filtered_issues)} issues available")

    # Prioritize issues
    prioritized_issues = prioritize_issues(filtered_issues)

    # Display top issues
    print("\nTop priority issues:")
    for i, issue in enumerate(prioritized_issues[:5]):
        print(f"{i+1}. Issue #{issue['number']}: {issue['title']}")
        print(f"   Labels: {[label['name'] for label in issue.get('labels', [])]}")
        print(f"   Updated: {issue.get('updatedAt', 'Unknown')}")
        print()

    if prioritized_issues:
        return prioritized_issues[0]['number']
    else:
        print("No suitable issues found")
        return None

if __name__ == "__main__":
    issue_number = main()
    if issue_number:
        print(f"Recommended issue: #{issue_number}")
    else:
        sys.exit(1)