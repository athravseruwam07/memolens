"""
Live webcam face recognition test.
Captures frames from your Mac's webcam, sends to backend over WebSocket,
and logs when a known person is recognized.

Usage: python3 test_webcam.py
"""

import asyncio
import base64
import json
import cv2
import websockets

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYzVjM2Q0Mi1mZWEzLTQzZjYtOWYwZi1jZTU1ZjQwYzUwOTYiLCJleHAiOjE3NzM1MjgzMTB9.3_ahnIyVp763C2sdlowopuOVre0t5cvfZgCSAidL_bo"
PATIENT_ID = "8746fe0d-6194-469f-a495-7629421baca2"
WS_URL = f"ws://localhost:8000/ws/stream/{PATIENT_ID}?token={TOKEN}"

FRAME_INTERVAL = 2  # send every Nth frame
JPEG_QUALITY = 55
FRAME_WIDTH = 320
FRAME_HEIGHT = 240


async def stream():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Cannot open webcam")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    print("Webcam opened. Streaming to backend... (Ctrl+C to stop)")

    async with websockets.connect(WS_URL) as ws:
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                print("ERROR: Failed to read frame")
                break

            frame_count += 1
            if frame_count % FRAME_INTERVAL != 0:
                continue

            _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            b64 = base64.b64encode(jpeg.tobytes()).decode()

            await ws.send(json.dumps({"frame_b64": b64}))

            try:
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(response)

                if data.get("type") == "person":
                    name = data.get("name", "unknown")
                    print(f"{name} person detected")
                elif data.get("type") == "no_match":
                    print("person not detected")

                # Drain any additional responses for this frame
                while True:
                    try:
                        extra = await asyncio.wait_for(ws.recv(), timeout=0.5)
                        extra_data = json.loads(extra)
                        if extra_data.get("type") == "person":
                            print(f"{extra_data.get('name', 'unknown')} person detected")
                        elif extra_data.get("type") == "no_match":
                            print("person not detected")
                    except asyncio.TimeoutError:
                        break

            except asyncio.TimeoutError:
                pass

    cap.release()


if __name__ == "__main__":
    try:
        asyncio.run(stream())
    except KeyboardInterrupt:
        print("\nStopped.")
