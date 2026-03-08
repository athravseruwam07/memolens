import cv2
import asyncio
import websockets
import base64
import json
import os

BACKEND_WS_URL = os.environ.get(
    "BACKEND_WS_URL",
    "ws://localhost:8000/ws/stream/test-patient-id"
)
FRAME_INTERVAL = 2
JPEG_QUALITY = 55
FRAME_WIDTH = 320
FRAME_HEIGHT = 240

async def stream():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    if not cap.isOpened():
        print("ERROR: Could not open camera at /dev/video0")
        return

    try:
        async with websockets.connect(BACKEND_WS_URL) as ws:
            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    await asyncio.sleep(0.1)
                    continue

                frame_count += 1
                if frame_count % FRAME_INTERVAL != 0:
                    continue

                _, buf = cv2.imencode(
                    ".jpg", frame,
                    [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
                )
                encoded = base64.b64encode(buf).decode("utf-8")
                await ws.send(encoded)

                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    result = json.loads(msg)
                    handle_result(result)
                    # Drain any extra responses for this frame
                    while True:
                        try:
                            extra = await asyncio.wait_for(ws.recv(), timeout=0.1)
                            handle_result(json.loads(extra))
                        except asyncio.TimeoutError:
                            break
                except asyncio.TimeoutError:
                    pass
                except json.JSONDecodeError:
                    pass

    except ConnectionRefusedError:
        print("ERROR: Could not connect to backend at " + BACKEND_WS_URL)
        print("Make sure the backend is running and BACKEND_WS_URL is correct")
    except Exception as e:
        print("ERROR: " + str(e))
    finally:
        cap.release()

def handle_result(result):
    rtype = result.get("type")
    if rtype == "person":
        name = result.get("name") or "unknown"
        print(f"{name} person detected")
    elif rtype == "no_match":
        print("person not detected")

if __name__ == "__main__":
    asyncio.run(stream())
