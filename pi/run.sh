#!/bin/bash
cd /home/pi/memolens
source venv/bin/activate
echo "Starting MemoLens stream..."
echo "Backend URL: ${BACKEND_WS_URL:-ws://localhost:8000/ws/stream/test-patient-id}"
python3 stream.py
