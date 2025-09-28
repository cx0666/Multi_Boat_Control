#!/bin/bash

# Installation script for multi_boat_control Python dependencies
# This script installs the required Python packages for hardware interface

set -e  # Exit on any error

echo "=== Multi-Boat Control Dependencies Installation ==="
echo "This script will install Python dependencies for hardware communication"
echo ""

# Check if pip is available
if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    echo "ERROR: pip is not installed. Please install pip first:"
    echo "sudo apt update && sudo apt install python3-pip"
    exit 1
fi

# Use pip3 if available, otherwise pip
PIP_CMD="pip3"
if ! command -v pip3 &> /dev/null; then
    PIP_CMD="pip"
fi

echo "Using pip command: $PIP_CMD"
echo ""

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Check if requirements.txt exists
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "ERROR: requirements.txt not found at $REQUIREMENTS_FILE"
    exit 1
fi

echo "Installing dependencies from requirements.txt..."
echo "File location: $REQUIREMENTS_FILE"
echo ""

# Install dependencies
$PIP_CMD install --user -r "$REQUIREMENTS_FILE"

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Installed packages:"
echo "  - dronekit: Python API for MAVLink communication"
echo "  - pymavlink: Low-level MAVLink protocol implementation"
echo ""
echo "Next steps:"
echo "1. Ensure your user is in the 'dialout' group for serial port access:"
echo "   sudo usermod -a -G dialout \$USER"
echo "   (then logout and login again)"
echo ""
echo "2. Build the ROS package:"
echo "   cd /path/to/your/catkin_workspace"
echo "   catkin_make"
echo ""
echo "3. Test the installation:"
echo "   roslaunch multi_boat_control test_control_interface.launch"
echo ""
echo "For troubleshooting, check the README or contact the development team."