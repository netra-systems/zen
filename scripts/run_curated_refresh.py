#!/usr/bin/env python3
"""Trigger BigQuery refresh of curated analytics tables."""

import argparse
from pathlib import Path

from google.cloud import bigquery


def run_query(client: bigquery.Client, sql_file: Path, project_id: str) -> None:
    with sql_file.open("r", encoding="utf-8") as f:
        query = f.read()
    # Substitute project_id placeholder
    query = query.replace("${project_id}", project_id)
    job = client.query(query)
    job.result()


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh Zen analytics tables")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--sql", required=True, type=Path, help="SQL file to execute")
    args = parser.parse_args()

    client = bigquery.Client(project=args.project)
    run_query(client, args.sql, args.project)
    print(f"Executed {args.sql}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

