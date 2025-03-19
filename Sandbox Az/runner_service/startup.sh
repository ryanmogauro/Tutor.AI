#!/bin/bash
set -e

# Install dependencies
pip install --no-cache-dir -r requirements.txt

# Start the app
gunicorn --bind=0.0.0.0:${PORT:-8000} \
         --workers=2 \
         --threads=4 \
         --timeout=300 \
         --access-logfile=- \
         --error-logfile=- \
         --log-level=info \
         run_server:app