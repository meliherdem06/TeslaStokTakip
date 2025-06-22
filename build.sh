#!/bin/bash
echo "Starting build process..."
echo "Python version: $(python --version)"

# Force clean environment
echo "Cleaning up cached configurations..."
rm -rf ~/.cache/pip
rm -rf .venv
rm -rf venv
rm -rf __pycache__
rm -rf *.pyc

# Create fresh virtual environment
echo "Creating fresh virtual environment..."
python -m venv .venv
source .venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Verify no eventlet is installed
echo "Verifying dependencies..."
pip list | grep -i eventlet || echo "No eventlet found - good!"
pip list | grep -i selenium || echo "No selenium found - good!"

echo "Build completed successfully!" 