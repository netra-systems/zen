#!/usr/bin/env python
"""Team Updates - Generate human-readable codebase change summaries."""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add scripts directory to path for imports

from team_updates_orchestrator import TeamUpdatesOrchestrator


def main():
    """CLI entry point for team updates."""
    parser = argparse.ArgumentParser(
        description="Generate human-readable team update reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/team_updates.py                    # Last 24 hours
  python scripts/team_updates.py --time-frame=last_hour
  python scripts/team_updates.py --time-frame=last_week --output=report.md
  
Time frames:
  last_hour     - Changes in the last hour
  last_5_hours  - Changes in the last 5 hours  
  last_day      - Changes in the last 24 hours (default)
  last_week     - Changes in the last week
  last_month    - Changes in the last month
        """
    )
    
    parser.add_argument(
        "--time-frame",
        default="last_day",
        choices=["last_hour", "last_5_hours", "last_day", "last_week", "last_month"],
        help="Time period to analyze (default: last_day)"
    )
    
    parser.add_argument(
        "--output",
        help="Save report to file instead of printing"
    )
    
    parser.add_argument(
        "--format",
        default="markdown",
        choices=["markdown", "plain"],
        help="Output format (default: markdown)"
    )
    
    args = parser.parse_args()
    
    # Create team_updates directory if saving
    if args.output:
        output_path = Path(args.output)
        if not output_path.parent.exists():
            output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        # Default output directory
        reports_dir = Path.cwd() / "team_updates"
        reports_dir.mkdir(exist_ok=True)
        
        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        output_path = reports_dir / f"{timestamp}_{args.time_frame}.md"
        args.output = str(output_path)
    
    # Run the orchestrator
    try:
        orchestrator = TeamUpdatesOrchestrator()
        report = asyncio.run(orchestrator.generate_update(args.time_frame))
        
        if args.output:
            Path(args.output).write_text(report, encoding='utf-8')
            print(f" PASS:  Team update report saved to: {args.output}")
            print(f"\n CHART:  Report Preview:\n{'-' * 50}")
            print(report[:500] + "...\n")
            print(f"{'=' * 50}")
            print(f"View full report: {args.output}")
        else:
            print(report)
            
    except Exception as e:
        print(f" FAIL:  Error generating report: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()