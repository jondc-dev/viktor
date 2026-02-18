#!/bin/bash
# Setup Playwright for Viktor's browser tool

set -e

echo "Setting up browser tool for Viktor..."

# Install Python dependencies
echo "Installing playwright and beautifulsoup4..."
pip install playwright beautifulsoup4

# Install Chromium browser
echo "Installing Chromium browser..."
playwright install chromium

# Create browser profiles directory
echo "Creating browser profiles directory..."
mkdir -p ~/.viktor/browser-profiles

echo "✅ Browser tool ready."
echo ""
echo "Usage: scripts/browser_tool.py --help"
