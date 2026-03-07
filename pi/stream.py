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

async def stream():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("ERROR: Could not open camera at /dev/video0")
        return

    print("Camera opened successfully")
    print("Connecting to backend at: " + BACKEND_WS_URL)

    try:
        async with websockets.connect(BACKEND_WS_URL) as ws:
            print("Connected to backend. Streaming frames...")
            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Warning: Failed to capture frame, retrying...")
                    await asyncio.sleep(0.1)
                    continue

                frame_count += 1
                if frame_count % 3 != 0:
                    continue

                _, buf = cv2.imencode(
                    ".jpg", frame,
                    [cv2.IMWRITE_JPEG_QUALITY, 70]
                )
                encoded = base64.b64encode(buf).decode("utf-8")
                await ws.send(encoded)

                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=0.05)
                    result = json.loads(msg)
                    handle_result(result)
                except asyncio.TimeoutError:
                    pass
                except json.JSONDecodeError:
                    print("Warning: Could not parse result from backend")

    except ConnectionRefusedError:
        print("ERROR: Could not connect to backend at " + BACKEND_WS_URL)
        print("Make sure the backend is running and BACKEND_WS_URL is correct")
    except Exception as e:
        print("ERROR: " + str(e))
    finally:
        cap.release()
        print("Camera released")

def handle_result(result):
    rtype = result.get("type")
    if rtype == "person":
        name = result.get("name", "unknown")
        rel = result.get("relationship", "")
        print("\n RECOGNIZED: " + name + " - " + rel)
        if result.get("notes"):
            print("   Note: " + result.get("notes"))
        if result.get("conversation_prompt"):
            print("   Prompt: " + result.get("conversation_prompt"))
    elif rtype == "item":
        item = result.get("item", "unknown")
        room = result.get("room", "unknown location")
        print("\n ITEM DETECTED: " + item + " in " + room)
        if result.get("last_seen_at"):
            print("   Last seen: " + result.get("last_seen_at"))
    elif rtype == "reminder":
        print("\n REMINDER: " + result.get("message", ""))
    elif rtype == "no_match":
        pass
    else:
        print("\n Result: " + str(result))

if __name__ == "__main__":
    print("MemoLens Pi Streaming Client")
    print("============================")
    print()
    asyncio.run(stream())
