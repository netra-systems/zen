#!/bin/sh
# Minimal database wait script for Docker containers
# This should be embedded directly in Dockerfiles when possible

set -e

DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
MAX_ATTEMPTS="${1:-30}"
DELAY="${2:-2}"

echo "Waiting for database at $DB_HOST:$DB_PORT..."

attempt=0
while [ $attempt -lt $MAX_ATTEMPTS ]; do
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null 2>&1; then
        echo "Database is ready!"
        exit 0
    fi
    
    attempt=$((attempt + 1))
    echo "Attempt $attempt/$MAX_ATTEMPTS - Database not ready, waiting ${DELAY}s..."
    sleep "$DELAY"
done

echo "Database failed to become ready after $MAX_ATTEMPTS attempts"
exit 1