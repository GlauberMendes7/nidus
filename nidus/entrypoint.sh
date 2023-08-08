#!/bin/bash

export PATH="/app/.venv/bin:${PATH}"
export PYTHONPATH=/app/

. /app/.venv/bin/activate

python /app/nidus/measurer.py