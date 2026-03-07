#!/bin/bash
# Run this once on the Pi to set up the environment.
# Requires Raspberry Pi OS (Buster or later) with Python 3.

set -e

cd /home/pi/memolens

# Recreate venv
rm -rf venv
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Configure piwheels for pre-built ARM wheels
mkdir -p ~/.config/pip
cat > ~/.config/pip/pip.conf << EOF
[global]
extra-index-url=https://www.piwheels.org/simple
EOF

# Install ATLAS from Debian archive (needed by numpy)
cd /tmp
wget -q "http://archive.debian.org/debian/pool/main/a/atlas/libatlas3-base_3.10.3-8_armhf.deb" -O libatlas3-base.deb
sudo dpkg -i libatlas3-base.deb
cd /home/pi/memolens

# Install Python packages (binary-only for speed)
pip install --only-binary=:all: numpy
pip install --only-binary=:all: opencv-python-headless
pip install websockets

echo ""
echo "Verifying installs..."
python3 -c "import numpy; print('numpy OK:', numpy.__version__)"
python3 -c "import cv2; print('cv2 OK:', cv2.__version__)"
python3 -c "import websockets; print('websockets OK')"
python3 -c "
import cv2
cap = cv2.VideoCapture(0)
print('webcam:', 'OK' if cap.isOpened() else 'FAILED')
cap.release()
"

echo ""
echo "Setup complete. Run with:"
echo "  BACKEND_WS_URL=ws://<backend-ip>:8000/ws/stream/<patient-id> ./run.sh"
