#!/bin/bash
echo "Starting build process..."
echo "Python version: $(python --version)"
echo "Installing dependencies..."
pip install -r requirements.txt
echo "Build completed successfully!" 