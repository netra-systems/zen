#!/usr/bin/env python3
"""Merge test results from multiple shards for GitHub Actions."""

import argparse
import json
import os
import shutil
from functools import reduce
from pathlib import Path
from typing import Dict, List, Any, Optional


def create_empty_results() -> Dict[str, Any]:
    """Create empty test results structure."""
    return {
        "total_tests": 0, "passed": 0, "failed": 0, "skipped": 0,
        "errors": 0, "duration": 0.0, "shards": [],
        "failures": [], "errors_list": []
    }


def find_result_files(input_dir: Path) -> List[Path]:
    """Find all JSON test result files."""
    json_files = list(input_dir.glob("test-results-*.json"))
    if not json_files:
        print(f"No test result files found in {input_dir}")
    else:
        print(f"Found {len(json_files)} result files to merge")
    return json_files


def extract_shard_name(json_file: Path) -> str:
    """Extract shard name from file path."""
    return json_file.stem.replace("test-results-", "")


def read_json_file(json_file: Path) -> Optional[Dict[str, Any]]:
    """Read JSON file with error handling."""
    try:
        with open(json_file, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"    Error processing {json_file}: {e}")
        return None


def load_shard_data(json_file: Path) -> Optional[Dict[str, Any]]:
    """Load and prepare shard data from JSON file."""
    shard_data = read_json_file(json_file)
    if shard_data is None:
        return None
    shard_data["shard"] = extract_shard_name(json_file)
    return shard_data


def aggregate_stats(merged: Dict[str, Any], shard: Dict[str, Any]) -> Dict[str, Any]:
    """Aggregate statistics from shard into merged results."""
    stats = ["total_tests", "passed", "failed", "skipped", "errors"]
    for stat in stats:
        merged[stat] += shard.get(stat, 0)
    merged["duration"] += shard.get("duration", 0.0)
    merged["shards"].append(shard)
    return merged


def add_shard_to_items(items: List[Dict], shard_name: str) -> None:
    """Add shard name to list of items."""
    for item in items:
        item["shard"] = shard_name


def collect_failures(merged: Dict[str, Any], shard: Dict[str, Any]) -> Dict[str, Any]:
    """Collect failures and errors from shard with shard name."""
    shard_name = shard["shard"]
    failures, errors = shard.get("failures", []), shard.get("errors_list", [])
    add_shard_to_items(failures, shard_name); add_shard_to_items(errors, shard_name)
    merged["failures"].extend(failures); merged["errors_list"].extend(errors)
    return merged


def merge_shard_data(merged: Dict[str, Any], shard: Dict[str, Any]) -> Dict[str, Any]:
    """Merge single shard data into results using composition."""
    merged = aggregate_stats(merged, shard)
    merged = collect_failures(merged, shard)
    return merged


def calculate_success_rate(results: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate and add success rate to results."""
    total = results["total_tests"]
    if total > 0:
        results["success_rate"] = (results["passed"] / total) * 100
    else:
        results["success_rate"] = 0.0
    return results


def save_results(results: Dict[str, Any], output_json: Path) -> None:
    """Save merged results to JSON file with summary."""
    with open(output_json, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nMerged results saved to: {output_json}")
    print(f"Total: {results['total_tests']}, Passed: {results['passed']}, Failed: {results['failed']}")
    print(f"Success rate: {results['success_rate']:.1f}%")


def handle_coverage_files(input_dir: Path, output_coverage: Path) -> None:
    """Handle coverage file merging if files exist."""
    coverage_files = list(input_dir.glob("coverage-*.xml"))
    if not coverage_files:
        return
    print(f"\nFound {len(coverage_files)} coverage files")
    shutil.copy(coverage_files[0], output_coverage)
    print(f"Coverage report saved to: {output_coverage}")


def process_shards(json_files: List[Path]) -> Dict[str, Any]:
    """Process all shard files and merge data."""
    shard_data = [load_shard_data(f) for f in json_files]
    valid_shards = [s for s in shard_data if s is not None]
    merged = reduce(merge_shard_data, valid_shards, create_empty_results())
    return calculate_success_rate(merged)


def merge_json_results(input_dir: Path, output_json: Path, output_coverage: Path) -> None:
    """Merge multiple JSON test result files into a single report."""
    json_files = find_result_files(input_dir)
    if not json_files:
        save_results(create_empty_results(), output_json); return
    merged = process_shards(json_files)
    save_results(merged, output_json); handle_coverage_files(input_dir, output_coverage)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(description="Merge test results from multiple shards")
    parser.add_argument("--input-dir", required=True, help="Directory containing test result files")
    parser.add_argument("--output-json", required=True, help="Output JSON file path")
    parser.add_argument("--output-coverage", required=True, help="Output coverage XML file path")
    return parser


def validate_input_dir(input_dir: Path) -> bool:
    """Validate input directory exists."""
    if not input_dir.exists():
        print(f"Error: Input directory does not exist: {input_dir}")
        return False
    return True


def main() -> int:
    """Main entry point for merge results script."""
    parser = create_argument_parser(); args = parser.parse_args()
    paths = (Path(args.input_dir), Path(args.output_json), Path(args.output_coverage))
    if not validate_input_dir(paths[0]): return 1
    merge_json_results(*paths); return 0


if __name__ == "__main__":
    exit(main())