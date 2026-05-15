#!/bin/bash
# MEMBRA CompanyOS — Development startup script
set -e

echo "Starting MEMBRA CompanyOS development environment..."

# Check if virtual environment exists
if [ ! -d "backend/venv" ]; then
    echo "Creating virtual environment..."
    python3.11 -m venv backend/venv
fi

source backend/venv/bin/activate

echo "Installing dependencies..."
pip install -q -r backend/requirements.txt

echo "Starting uvicorn with auto-reload..."
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info
