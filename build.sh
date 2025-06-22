#!/bin/bash
set -e

echo "=== Tesla Stock Monitor Build Script ==="
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"

# Force Python 3.9.16
echo "Forcing Python 3.9.16..."
export PYTHON_VERSION=3.9.16

# Clean any existing environment
echo "Cleaning environment..."
pip uninstall -y eventlet gevent flask-socketio python-socketio lxml 2>/dev/null || true

# Install requirements
echo "Installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt

# Force remove any eventlet/gevent that might have been installed
echo "Force removing eventlet/gevent..."
pip uninstall -y eventlet gevent flask-socketio python-socketio lxml 2>/dev/null || true

# Verify NO eventlet is installed
echo "Verifying no eventlet is installed..."
if pip list | grep -i eventlet; then
    echo "ERROR: eventlet found! Removing..."
    pip uninstall eventlet -y
    exit 1
fi

if pip list | grep -i gevent; then
    echo "ERROR: gevent found! Removing..."
    pip uninstall gevent -y
    exit 1
fi

# Verify only required packages
echo "Installed packages:"
pip list

# Test import
echo "Testing imports..."
python -c "
import flask
import requests
from bs4 import BeautifulSoup
import sqlite3
import schedule
print('All imports successful!')
"

echo "=== Build completed successfully ==="
echo "NO EVENTLET - SYNC WORKERS ONLY" 