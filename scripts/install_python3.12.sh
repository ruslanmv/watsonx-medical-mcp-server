#!/bin/bash

# This script installs Python 3.12 on an Ubuntu system and sets it as the
# default version for 'python3' and 'python'.
#
# It uses the 'deadsnakes' PPA to get the latest Python versions.
#
# WARNING: Changing the default system Python can potentially affect system
# utilities that rely on a specific version. This script uses
# 'update-alternatives', which is a safe way to manage different versions,
# but proceed with caution.

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- [Step 1/5] Updating package list and installing prerequisites ---"
sudo apt-get update
sudo apt-get install -y software-properties-common
echo "--- Prerequisites installed successfully ---"

echo "--- [Step 2/5] Adding the deadsnakes PPA for modern Python versions ---"
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt-get update
echo "--- PPA added successfully ---"

echo "--- [Step 3/5] Installing Python 3.12 and required packages (dev, venv) ---"
sudo apt-get install -y python3.12 python3.12-dev python3.12-venv
echo "--- Python 3.12 installed successfully ---"

echo "--- [Step 4/5] Setting Python 3.12 as the default 'python3' and 'python' ---"
# This command tells the system that /usr/bin/python3.12 is an alternative for /usr/bin/python3.
# The '1' at the end is the priority.
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# This command does the same for the 'python' command.
sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1
echo "--- Default Python version updated ---"

echo "--- [Step 5/5] Installing pip for Python 3.12 ---"
# We use the official bootstrap script to install pip for our new Python version.
curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python3.12
echo "--- pip for Python 3.12 installed successfully ---"

echo ""
echo "--- Installation Complete! ---"
echo "Verify the new default versions:"
echo ""
echo "python3 --version"
python3 --version
echo ""
echo "python --version"
python --version
echo ""
echo "pip --version"
pip --version
echo ""
echo "To switch between Python versions in the future, you can use:"
echo "sudo update-alternatives --config python3"
