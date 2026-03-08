"""
MemoLens Pi Stream - Video streaming with voice integration.
Captures webcam frames, sends to backend for CV processing,
and provides voice feedback for person recognition and reminders.
"""

import cv2
import asyncio
import websockets
import base64
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Load .env file if it exists
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

from tts import speak, speak_person_recognized, speak_reminder, get_tts
from voice_listener import VoiceListener, handle_voice_event

BACKEND_WS_URL = os.environ.get(
    "BACKEND_WS_URL",
    "ws://localhost:8000/ws/stream/test-patient-id"
)
BACKEND_API_URL = os.environ.get(
    "BACKEND_API_URL",
    "http://localhost:8000/api/v1"
)

# Extract patient ID from WS URL if not explicitly set
def _extract_patient_id():
    explicit_id = os.environ.get("PATIENT_ID")
    if explicit_id and explicit_id != "test-patient-id":
        return explicit_id
    # Extract from WebSocket URL: ws://host:port/ws/stream/PATIENT_ID
    import re
    match = re.search(r'/ws/stream/([^/]+)$', BACKEND_WS_URL)
    if match:
        return match.group(1)
    return explicit_id or "test-patient-id"

PATIENT_ID = _extract_patient_id()
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "")

FRAME_INTERVAL = 2
JPEG_QUALITY = 55
FRAME_WIDTH = 320
FRAME_HEIGHT = 240

VOICE_ENABLED = os.environ.get("VOICE_ENABLED", "true").lower() == "true"
VOICE_ANNOUNCE_PERSONS = os.environ.get("VOICE_ANNOUNCE_PERSONS", "true").lower() == "true"
VOICE_ANNOUNCE_REMINDERS = os.environ.get("VOICE_ANNOUNCE_REMINDERS", "true").lower() == "true"
VOICE_INPUT_ENABLED = os.environ.get("VOICE_INPUT_ENABLED", "true").lower() == "true"  # Uses custom STT (no FLAC needed)

_last_announced_person = None
_person_cooldown_seconds = 30.0
_last_person_time = 0.0

_voice_listener = None
_voice_thread = None


def handle_result(result):
    """
    Handle WebSocket result from backend.
    Announces persons and reminders via TTS when enabled.
    """
    global _last_announced_person, _last_person_time

    rtype = result.get("type")

    if rtype == "person":
        name = result.get("name") or "unknown"
        relationship = result.get("relationship")
        conversation_prompt = result.get("conversation_prompt")
        notes = result.get("notes")
        print(f"[DETECTED] {name} person detected")

        if VOICE_ENABLED and VOICE_ANNOUNCE_PERSONS:
            import time
            current_time = time.time()

            if name != _last_announced_person or (current_time - _last_person_time) > _person_cooldown_seconds:
                _last_announced_person = name
                _last_person_time = current_time
                speak_person_recognized(name, relationship, conversation_prompt)

    elif rtype == "no_match":
        pass  # Stay silent when no person detected

    elif rtype == "reminder":
        message = result.get("message", "")
        print(f"[REMINDER] {message}")

        if VOICE_ENABLED and VOICE_ANNOUNCE_REMINDERS and message:
            speak_reminder(message)

    elif rtype == "item":
        item_name = result.get("item_name")
        room = result.get("room")
        print(f"[ITEM] {item_name} seen in {room}")

    elif rtype == "voice":
        message = result.get("message", "")
        if message:
            speak(message)

    elif rtype == "error":
        error_msg = result.get("error", "Unknown error")
        print(f"[ERROR] {error_msg}")


def start_voice_listener_thread():
    """Start the voice listener in a background thread."""
    global _voice_listener, _voice_thread

    if not VOICE_INPUT_ENABLED:
        print("Voice input disabled (set VOICE_INPUT_ENABLED=true to enable)")
        return

    if not VOICE_ENABLED:
        print("Voice disabled - skipping voice listener")
        return

    # Check if speech recognition is available before starting
    try:
        from voice_listener import STT_AVAILABLE, CUSTOM_STT_AVAILABLE
        if not STT_AVAILABLE:
            print("Voice input disabled - no speech recognition available")
            return
        if CUSTOM_STT_AVAILABLE:
            print("Using custom speech recognizer (no FLAC needed)")
    except ImportError:
        print("Voice input disabled - voice_listener module not available")
        return

    _voice_listener = VoiceListener(
        patient_id=PATIENT_ID,
        auth_token=AUTH_TOKEN,
        on_speech_detected=lambda text: print(f"[VOICE] Heard: {text}"),
        on_response=lambda msg: print(f"[VOICE] Response: {msg}"),
    )

    def run_listener():
        _voice_listener.start_continuous_listening()

    _voice_thread = threading.Thread(target=run_listener, daemon=True)
    _voice_thread.start()
    print("Voice listener started in background thread")


def stop_voice_listener():
    """Stop the voice listener."""
    global _voice_listener
    if _voice_listener:
        _voice_listener.stop()


async def stream():
    """
    Main video streaming loop.
    Captures frames, sends to backend, handles responses with voice.
    """
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    if not cap.isOpened():
        print("ERROR: Could not open camera at /dev/video0")
        return

    if VOICE_ENABLED:
        speak("MemoLens started. I'm here to help you.")
        start_voice_listener_thread()

    try:
        async with websockets.connect(BACKEND_WS_URL) as ws:
            print(f"Connected to backend: {BACKEND_WS_URL}")
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
        if VOICE_ENABLED:
            speak("I cannot connect to the server. Please check the connection.")
    except Exception as e:
        print("ERROR: " + str(e))
    finally:
        cap.release()
        stop_voice_listener()
        get_tts().stop()


if __name__ == "__main__":
    print("Starting MemoLens Pi with voice support...")
    print(f"Voice enabled: {VOICE_ENABLED}")
    print(f"Announce persons: {VOICE_ANNOUNCE_PERSONS}")
    print(f"Announce reminders: {VOICE_ANNOUNCE_REMINDERS}")
    asyncio.run(stream())
