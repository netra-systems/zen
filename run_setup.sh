#!/bin/bash
export NETRA_DB_HOST=localhost
export NETRA_DB_PORT=5433
export NETRA_DB_NAME=netra_optimizer
export NETRA_DB_USER=rindhujajohnson
export NETRA_DB_PASSWORD=

python netraoptimizer/database/setup.py
