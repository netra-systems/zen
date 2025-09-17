#!/usr/bin/env python3
import subprocess
import sys
import json
from datetime import datetime, timedelta

def find_agent_issues():
    try:
        # Try to get issue list with gh CLI
        result = subprocess.run(['gh', 'issue', 'list', '--state', 'open', '--json', 'number,title,body,labels,updatedAt', '--limit', '50'],
                              capture_output=True, text=True, check=True)
        issues = json.loads(result.stdout)

        # Filter for agent-related issues
        agent_issues = []
        for issue in issues:
            title_body = f"{issue['title']} {issue.get('body', '')}".lower()
            if 'agent' in title_body:
                # Check for recent agent session tags
                labels = [label['name'] for label in issue.get('labels', [])]
                has_active_work = 'actively-being-worked-on' in labels

                # Check for recent agent session tags (last 20 minutes)
                recent_agent_session = False
                now = datetime.now()
                for label in labels:
                    if label.startswith('agent-session-'):
                        try:
                            # Extract datetime from label
                            datetime_str = label.replace('agent-session-', '')
                            # Try different formats
                            try:
                                label_time = datetime.strptime(datetime_str, '%Y%m%d_%H%M%S')
                            except ValueError:
                                try:
                                    label_time = datetime.strptime(datetime_str, '%Y-%m-%d-%H%M%S')
                                except ValueError:
                                    continue

                            if (now - label_time).total_seconds() < 1200:  # 20 minutes
                                recent_agent_session = True
                                break
                        except:
                            continue

                if not (has_active_work and recent_agent_session):
                    agent_issues.append({
                        'number': issue['number'],
                        'title': issue['title'],
                        'labels': labels,
                        'updatedAt': issue['updatedAt'],
                        'has_active_work': has_active_work,
                        'recent_agent_session': recent_agent_session
                    })

        # Sort by importance (presence of critical keywords)
        def importance_score(issue):
            title_body = f"{issue['title']}".lower()
            score = 0
            if 'critical' in title_body or 'p0' in title_body: score += 10
            if 'pipeline' in title_body or 'execution' in title_body: score += 8
            if 'websocket' in title_body: score += 6
            if 'golden path' in title_body: score += 10
            if 'staging' in title_body: score += 5
            if 'ssot' in title_body: score += 4
            return score

        agent_issues.sort(key=importance_score, reverse=True)

        print('AGENT-RELATED ISSUES FOUND:')
        for issue in agent_issues[:10]:
            print(f"Issue #{issue['number']}: {issue['title']}")
            print(f"  Labels: {issue['labels']}")
            print(f"  Active work: {issue['has_active_work']}, Recent session: {issue['recent_agent_session']}")
            print(f"  Importance: {importance_score(issue)}")
            print()

        if agent_issues:
            print(f'RECOMMENDED ISSUE: #{agent_issues[0]["number"]}')
            return agent_issues[0]['number']
        else:
            print('NO SUITABLE AGENT ISSUES FOUND')
            return None

    except subprocess.CalledProcessError as e:
        print(f'ERROR: {e}')
        print('GitHub CLI not available or not authenticated')
        return None
    except Exception as e:
        print(f'ERROR: {e}')
        return None

if __name__ == "__main__":
    find_agent_issues()