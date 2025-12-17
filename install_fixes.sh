#!/bin/bash

# Installation script for fixes
# This script installs the required packages for the bug fixes

echo "========================================"
echo "Installing Bug Fixes and Enhancements"
echo "========================================"
echo ""

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: Not in a virtual environment"
    echo "It's recommended to use a virtual environment"
    echo ""
fi

echo "Step 1: Installing brotli for aiohttp compression support..."
pip install brotli==1.1.0 brotlipy==0.7.0

echo ""
echo "Step 2: Installing alternative search libraries..."
pip install googlesearch-python==1.2.4 duckduckgo-search==4.1.1

echo ""
echo "Step 3: Verifying existing dependencies..."
pip install -q --upgrade aiohttp playwright selenium

echo ""
echo "Step 4: Installing Playwright browsers (if needed)..."
playwright install chromium || echo "Playwright browsers installation skipped"

echo ""
echo "========================================"
echo "Installation Complete!"
echo "========================================"
echo ""
echo "Key improvements:"
echo "  ✓ Fixed brotli decoding error in aiohttp"
echo "  ✓ Enhanced browser automation with anti-detection"
echo "  ✓ Added advanced header fingerprinting"
echo "  ✓ Implemented googlesearch-python as fallback"
echo "  ✓ Improved IP rotation and stealth techniques"
echo ""
echo "To verify the installation, run:"
echo "  python verify_fixes.py"
echo ""
