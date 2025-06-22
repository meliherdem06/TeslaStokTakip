#!/bin/bash
set -e

echo "=== FORCE CLEAN BUILD STARTING ==="
echo "Python version: $(python --version)"

# Kill any existing processes
echo "Killing any existing processes..."
pkill -f "python app.py" || true
pkill -f "gunicorn" || true

# Force clean environment
echo "Cleaning up cached configurations..."
rm -rf ~/.cache/pip
rm -rf .venv
rm -rf venv
rm -rf __pycache__
rm -rf *.pyc
rm -rf .pytest_cache

# Create fresh virtual environment
echo "Creating fresh virtual environment..."
python -m venv .venv
source .venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Verify NO eventlet is installed
echo "Verifying dependencies..."
if pip list | grep -i eventlet; then
    echo "ERROR: eventlet found! Removing..."
    pip uninstall eventlet -y
fi

if pip list | grep -i selenium; then
    echo "ERROR: selenium found! Removing..."
    pip uninstall selenium -y
fi

echo "Final package list:"
pip list

echo "=== BUILD COMPLETED SUCCESSFULLY ===" 