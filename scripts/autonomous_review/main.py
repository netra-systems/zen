#!/usr/bin/env python3
"""
Autonomous Test Review System - Main Entry Point
Command-line interface for the autonomous test review system
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from .test_reviewer import AutonomousTestReviewer
from .types import ReviewMode


async def main():
    """Main entry point for autonomous test review"""
    parser = _create_argument_parser()
    args = parser.parse_args()
    mode = _determine_review_mode(args)
    reviewer = _setup_reviewer(args)
    await _execute_review_session(reviewer, mode)

def _create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser"""
    parser = argparse.ArgumentParser(
        description="Autonomous Test Review System - Ultra-thinking powered test improvement"
    )
    _add_mode_arguments(parser)
    _add_execution_arguments(parser)
    _add_configuration_arguments(parser)
    return parser

def _add_mode_arguments(parser: argparse.ArgumentParser) -> None:
    """Add mode selection arguments"""
    parser.add_argument(
        "--mode",
        type=str,
        choices=[mode.value for mode in ReviewMode],
        default="auto",
        help="Review execution mode"
    )

def _add_execution_arguments(parser: argparse.ArgumentParser) -> None:
    """Add execution type arguments"""
    parser.add_argument("--auto", action="store_true", help="Run in fully autonomous mode with auto-fixes")
    parser.add_argument("--quick", action="store_true", help="Quick test refresh (< 5 minutes)")
    parser.add_argument("--full-analysis", action="store_true", help="Complete test suite analysis with ultra-thinking")
    parser.add_argument("--smart-generate", action="store_true", help="Intelligently generate missing tests")
    parser.add_argument("--continuous", action="store_true", help="Run continuous background review")
    parser.add_argument("--ultra-think", action="store_true", help="Enable ultra-thinking deep analysis")

def _add_configuration_arguments(parser: argparse.ArgumentParser) -> None:
    """Add configuration arguments"""
    parser.add_argument(
        "--target-coverage",
        type=float,
        default=97.0,
        help="Target coverage percentage (default: 97)"
    )

def _determine_review_mode(args) -> ReviewMode:
    """Determine review mode from command line arguments"""
    if args.auto:
        return ReviewMode.AUTO
    elif args.quick:
        return ReviewMode.QUICK
    elif args.full_analysis:
        return ReviewMode.FULL_ANALYSIS
    elif args.smart_generate:
        return ReviewMode.SMART_GENERATE
    elif args.continuous:
        return ReviewMode.CONTINUOUS
    elif args.ultra_think:
        return ReviewMode.ULTRA_THINK
    else:
        return ReviewMode(args.mode)

def _setup_reviewer(args) -> AutonomousTestReviewer:
    """Setup and configure test reviewer"""
    reviewer = AutonomousTestReviewer()
    reviewer.coverage_goal = args.target_coverage
    return reviewer

async def _execute_review_session(reviewer: AutonomousTestReviewer, mode: ReviewMode) -> None:
    """Execute the review session based on mode"""
    if mode == ReviewMode.CONTINUOUS:
        await _run_continuous_review(reviewer)
    else:
        await _run_single_review(reviewer, mode)

async def _run_continuous_review(reviewer: AutonomousTestReviewer) -> None:
    """Run continuous review loop"""
    print("[CONTINUOUS] Starting continuous test review...")
    while True:
        try:
            analysis = await reviewer.run_review(ReviewMode.AUTO)
            _print_continuous_status(analysis)
            print("[WAITING] Next review in 1 hour...")
            await asyncio.sleep(3600)
        except KeyboardInterrupt:
            print("\n[STOPPED] Continuous review stopped")
            break

def _print_continuous_status(analysis) -> None:
    """Print continuous review status"""
    print(f"\n[STATUS] Coverage: {analysis.coverage_percentage:.1f}% | Quality: {analysis.quality_score:.0f}/100")

async def _run_single_review(reviewer: AutonomousTestReviewer, mode: ReviewMode) -> None:
    """Run single review session"""
    analysis = await reviewer.run_review(mode)
    _print_review_summary(analysis, reviewer)

def _print_review_summary(analysis, reviewer: AutonomousTestReviewer) -> None:
    """Print review completion summary"""
    print("\n" + "=" * 60)
    print("REVIEW COMPLETE")
    print("=" * 60)
    _print_coverage_metrics(analysis, reviewer)
    _print_analysis_metrics(analysis)
    _print_recommendations(analysis)

def _print_coverage_metrics(analysis, reviewer: AutonomousTestReviewer) -> None:
    """Print coverage metrics"""
    print(f"Coverage: {analysis.coverage_percentage:.1f}% (Target: {reviewer.coverage_goal}%)")
    print(f"Quality Score: {analysis.quality_score:.0f}/100")

def _print_analysis_metrics(analysis) -> None:
    """Print analysis metrics"""
    print(f"Critical Gaps: {len(analysis.critical_gaps)}")
    print(f"Missing Tests: {len(analysis.missing_tests)}")
    print(f"Test Debt: {analysis.test_debt} issues")

def _print_recommendations(analysis) -> None:
    """Print top recommendations"""
    if analysis.recommendations:
        print("\nTop Recommendations:")
        for i, rec in enumerate(analysis.recommendations[:3], 1):
            print(f"  {i}. {rec}")


if __name__ == "__main__":
    asyncio.run(main())