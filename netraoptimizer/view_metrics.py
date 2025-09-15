#!/usr/bin/env python3
"""
NetraOptimizer Metrics Viewer

View and analyze collected metrics from NetraOptimizer database.

Usage:
    python netraoptimizer/view_metrics.py                  # Show summary
    python netraoptimizer/view_metrics.py --today          # Today's metrics
    python netraoptimizer/view_metrics.py --expensive      # High-cost commands
    python netraoptimizer/view_metrics.py --batch BATCH_ID # Specific batch
    python netraoptimizer/view_metrics.py --optimize       # Optimization opportunities
"""

import asyncio
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from netraoptimizer.database import DatabaseClient


async def show_summary(db: DatabaseClient):
    """Show overall summary statistics."""
    print("\n" + "=" * 60)
    print("NETRAOPTIMIZER METRICS SUMMARY")
    print("=" * 60)

    # Get overall stats
    stats = await db.query_one('''
        SELECT
            COUNT(*) as total_commands,
            SUM(total_tokens) as total_tokens,
            AVG(cache_hit_rate) as avg_cache_rate,
            SUM(cost_usd) as total_cost,
            SUM(cache_savings_usd) as total_savings,
            MIN(timestamp) as first_execution,
            MAX(timestamp) as last_execution
        FROM command_executions
    ''')

    if stats and stats['total_commands'] > 0:
        print(f"\nTotal Commands: {stats['total_commands']:,}")
        print(f"Total Tokens: {stats['total_tokens']:,}")
        print(f"Average Cache Rate: {stats['avg_cache_rate']:.1f}%")
        print(f"Total Cost: ${stats['total_cost']:.2f}")
        print(f"Cache Savings: ${stats['total_savings']:.2f}")
        print(f"Period: {stats['first_execution'].date()} to {stats['last_execution'].date()}")

        # Get top commands
        top_commands = await db.query('''
            SELECT
                command_base,
                COUNT(*) as count,
                AVG(cache_hit_rate) as avg_cache,
                SUM(cost_usd) as total_cost
            FROM command_executions
            GROUP BY command_base
            ORDER BY count DESC
            LIMIT 5
        ''')

        print("\n" + "-" * 40)
        print("TOP COMMANDS BY FREQUENCY")
        print("-" * 40)
        for cmd in top_commands:
            print(f"{cmd['command_base']:<30} {cmd['count']:>5} runs, "
                  f"${cmd['total_cost']:.2f}, {cmd['avg_cache']:.0f}% cache")
    else:
        print("\nNo data found. Run some commands through NetraOptimizer first!")


async def show_today(db: DatabaseClient):
    """Show today's metrics."""
    print("\n" + "=" * 60)
    print(f"TODAY'S METRICS - {datetime.now().date()}")
    print("=" * 60)

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    stats = await db.query_one('''
        SELECT
            COUNT(*) as command_count,
            SUM(total_tokens) as total_tokens,
            AVG(cache_hit_rate) as avg_cache_rate,
            SUM(cost_usd) as total_cost,
            SUM(cache_savings_usd) as savings
        FROM command_executions
        WHERE timestamp >= $1
    ''', today)

    if stats and stats['command_count'] > 0:
        print(f"\nCommands Run: {stats['command_count']}")
        print(f"Total Tokens: {stats['total_tokens']:,}")
        print(f"Average Cache Rate: {stats['avg_cache_rate']:.1f}%")
        print(f"Total Cost: ${stats['total_cost']:.4f}")
        print(f"Cache Savings: ${stats['savings']:.4f}")

        # Recent commands
        recent = await db.query('''
            SELECT
                timestamp,
                command_raw,
                total_tokens,
                cache_hit_rate,
                cost_usd
            FROM command_executions
            WHERE timestamp >= $1
            ORDER BY timestamp DESC
            LIMIT 10
        ''', today)

        if recent:
            print("\n" + "-" * 40)
            print("RECENT COMMANDS")
            print("-" * 40)
            for cmd in recent:
                time_str = cmd['timestamp'].strftime('%H:%M:%S')
                cmd_str = cmd['command_raw'][:40] + ('...' if len(cmd['command_raw']) > 40 else '')
                print(f"{time_str} | {cmd_str:<43} | "
                      f"{cmd['total_tokens']:>8,} tokens | "
                      f"{cmd['cache_hit_rate']:>5.1f}% | "
                      f"${cmd['cost_usd']:.4f}")
    else:
        print("\nNo commands run today.")


async def show_expensive(db: DatabaseClient):
    """Show expensive commands."""
    print("\n" + "=" * 60)
    print("EXPENSIVE COMMANDS (> $0.50)")
    print("=" * 60)

    expensive = await db.query('''
        SELECT
            timestamp,
            command_raw,
            total_tokens,
            cache_hit_rate,
            cost_usd,
            execution_time_ms
        FROM command_executions
        WHERE cost_usd > 0.50
        ORDER BY cost_usd DESC
        LIMIT 20
    ''')

    if expensive:
        print(f"\nFound {len(expensive)} expensive commands:\n")
        print(f"{'Timestamp':<20} {'Command':<40} {'Tokens':>10} {'Cache':>7} {'Cost':>10}")
        print("-" * 95)

        for cmd in expensive:
            timestamp = cmd['timestamp'].strftime('%Y-%m-%d %H:%M')
            command = cmd['command_raw'][:38] + ('...' if len(cmd['command_raw']) > 38 else '')
            print(f"{timestamp:<20} {command:<40} {cmd['total_tokens']:>10,} "
                  f"{cmd['cache_hit_rate']:>6.1f}% ${cmd['cost_usd']:>9.2f}")

        total_cost = sum(cmd['cost_usd'] for cmd in expensive)
        print("-" * 95)
        print(f"{'TOTAL':<70} ${total_cost:>9.2f}")
    else:
        print("\nNo expensive commands found (all under $0.50)")


async def show_batch(db: DatabaseClient, batch_id: str):
    """Show metrics for a specific batch."""
    print("\n" + "=" * 60)
    print(f"BATCH METRICS - {batch_id}")
    print("=" * 60)

    # Get batch summary
    summary = await db.query_one('''
        SELECT
            COUNT(*) as command_count,
            MIN(timestamp) as start_time,
            MAX(timestamp) as end_time,
            SUM(total_tokens) as total_tokens,
            AVG(cache_hit_rate) as avg_cache_rate,
            SUM(cost_usd) as total_cost
        FROM command_executions
        WHERE batch_id = $1
    ''', batch_id)

    if summary and summary['command_count'] > 0:
        duration = (summary['end_time'] - summary['start_time']).total_seconds()
        print(f"\nCommands: {summary['command_count']}")
        print(f"Duration: {duration:.1f} seconds")
        print(f"Total Tokens: {summary['total_tokens']:,}")
        print(f"Average Cache Rate: {summary['avg_cache_rate']:.1f}%")
        print(f"Total Cost: ${summary['total_cost']:.4f}")

        # Get individual commands
        commands = await db.query('''
            SELECT
                execution_sequence,
                command_raw,
                total_tokens,
                cache_hit_rate,
                cost_usd,
                status
            FROM command_executions
            WHERE batch_id = $1
            ORDER BY execution_sequence
        ''', batch_id)

        print("\n" + "-" * 40)
        print("BATCH COMMANDS")
        print("-" * 40)
        for cmd in commands:
            seq = f"[{cmd['execution_sequence']}]" if cmd['execution_sequence'] is not None else "[-]"
            status_icon = "✅" if cmd['status'] == 'completed' else "❌"
            print(f"{seq:>4} {status_icon} {cmd['command_raw'][:40]:<40} | "
                  f"{cmd['total_tokens']:>8,} tokens | "
                  f"{cmd['cache_hit_rate']:>5.1f}% | "
                  f"${cmd['cost_usd']:.4f}")
    else:
        print(f"\nNo data found for batch {batch_id}")


async def show_optimization(db: DatabaseClient):
    """Show optimization opportunities."""
    print("\n" + "=" * 60)
    print("OPTIMIZATION OPPORTUNITIES")
    print("=" * 60)

    # Commands with low cache rates
    low_cache = await db.query('''
        SELECT
            command_base,
            COUNT(*) as execution_count,
            AVG(cache_hit_rate) as avg_cache_rate,
            SUM(cost_usd) as total_cost,
            SUM(cost_usd * (1 - cache_hit_rate/100.0)) as potential_savings
        FROM command_executions
        GROUP BY command_base
        HAVING COUNT(*) > 3 AND AVG(cache_hit_rate) < 50
        ORDER BY potential_savings DESC
        LIMIT 10
    ''')

    if low_cache:
        print("\n🔴 COMMANDS WITH LOW CACHE RATES (<50%)")
        print("-" * 40)
        for cmd in low_cache:
            print(f"{cmd['command_base']:<30}")
            print(f"  Runs: {cmd['execution_count']}, "
                  f"Avg Cache: {cmd['avg_cache_rate']:.1f}%, "
                  f"Cost: ${cmd['total_cost']:.2f}")
            print(f"  💡 Potential Savings: ${cmd['potential_savings']:.2f}")
            print()

    # Frequently run expensive commands
    frequent_expensive = await db.query('''
        SELECT
            command_base,
            COUNT(*) as count,
            AVG(cost_usd) as avg_cost,
            SUM(cost_usd) as total_cost
        FROM command_executions
        WHERE cost_usd > 0.10
        GROUP BY command_base
        HAVING COUNT(*) > 5
        ORDER BY total_cost DESC
        LIMIT 5
    ''')

    if frequent_expensive:
        print("\n🟡 FREQUENTLY RUN EXPENSIVE COMMANDS")
        print("-" * 40)
        for cmd in frequent_expensive:
            print(f"{cmd['command_base']:<30}")
            print(f"  Runs: {cmd['count']}, "
                  f"Avg Cost: ${cmd['avg_cost']:.2f}, "
                  f"Total: ${cmd['total_cost']:.2f}")
            print(f"  💡 Consider batching or caching strategy")
            print()

    # Best performing commands
    best_cache = await db.query('''
        SELECT
            command_base,
            COUNT(*) as count,
            AVG(cache_hit_rate) as avg_cache,
            SUM(cache_savings_usd) as total_savings
        FROM command_executions
        WHERE cache_hit_rate > 90
        GROUP BY command_base
        HAVING COUNT(*) > 3
        ORDER BY total_savings DESC
        LIMIT 5
    ''')

    if best_cache:
        print("\n🟢 BEST CACHE PERFORMANCE (>90%)")
        print("-" * 40)
        for cmd in best_cache:
            print(f"{cmd['command_base']:<30}")
            print(f"  Runs: {cmd['count']}, "
                  f"Avg Cache: {cmd['avg_cache']:.1f}%, "
                  f"Savings: ${cmd['total_savings']:.2f}")
            print()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='View NetraOptimizer metrics')
    parser.add_argument('--today', action='store_true', help="Show today's metrics")
    parser.add_argument('--expensive', action='store_true', help='Show expensive commands')
    parser.add_argument('--batch', type=str, help='Show specific batch metrics')
    parser.add_argument('--optimize', action='store_true', help='Show optimization opportunities')

    args = parser.parse_args()

    # Initialize database client
    db = DatabaseClient()
    await db.initialize()

    try:
        if args.today:
            await show_today(db)
        elif args.expensive:
            await show_expensive(db)
        elif args.batch:
            await show_batch(db, args.batch)
        elif args.optimize:
            await show_optimization(db)
        else:
            # Default: show summary
            await show_summary(db)

        print()  # Final newline

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. PostgreSQL is running (or Cloud SQL Proxy for CloudSQL)")
        print("  2. Database is set up (run database/setup.py)")
        print("  3. You've run some commands through NetraOptimizer")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())