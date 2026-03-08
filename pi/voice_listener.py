"""
Voice Listener module for MemoLens Pi wearable.
Handles speech recognition, intent detection, and backend queries.
"""

import os
import re
import json
import asyncio
from typing import Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

import requests

# Try custom speech recognizer first (doesn't need FLAC)
try:
    from speech_recognizer import SpeechRecognizer, listen_once as custom_listen
    CUSTOM_STT_AVAILABLE = True
except ImportError:
    CUSTOM_STT_AVAILABLE = False
    custom_listen = None

# Fallback to speech_recognition library
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    sr = None

STT_AVAILABLE = CUSTOM_STT_AVAILABLE or SR_AVAILABLE

if not STT_AVAILABLE:
    print("WARNING: No speech recognition available. Voice input will be disabled.")

# Microphone device index - set to None for default, or specify index
MICROPHONE_INDEX = int(os.environ.get("MICROPHONE_INDEX", "2"))  # Default to webcam mic (index 2)

# Use custom recognizer by default (avoids FLAC dependency)
USE_CUSTOM_STT = os.environ.get("USE_CUSTOM_STT", "true").lower() == "true"

from tts import speak, speak_response, speak_item_location, speak_reminder


class Intent(Enum):
    """Detected intents from voice input."""
    FIND_ITEM = "find_item"
    IDENTIFY_PERSON = "identify_person"
    TODAY_REMINDERS = "today_reminders"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """Result of intent detection."""
    intent: Intent
    entities: dict = field(default_factory=dict)
    raw_text: str = ""


@dataclass
class QueryResponse:
    """Response from backend query."""
    answer_type: str
    message: str
    results: dict = field(default_factory=dict)


# Extract backend host from BACKEND_WS_URL if BACKEND_API_URL not set
def _get_backend_api_url():
    explicit_url = os.environ.get("BACKEND_API_URL")
    if explicit_url:
        return explicit_url
    
    # Try to extract from WebSocket URL
    ws_url = os.environ.get("BACKEND_WS_URL", "")
    if ws_url:
        # ws://172.20.10.3:8000/ws/stream/xxx -> http://172.20.10.3:8000/api/v1
        import re
        match = re.match(r'wss?://([^/]+)', ws_url)
        if match:
            host = match.group(1)
            return f"http://{host}/api/v1"
    
    return "http://localhost:8000/api/v1"

BACKEND_API_URL = _get_backend_api_url()

# Extract patient ID from WebSocket URL if not set
def _get_patient_id():
    explicit_id = os.environ.get("PATIENT_ID")
    if explicit_id and explicit_id != "test-patient-id":
        return explicit_id
    
    # Try to extract from WebSocket URL
    ws_url = os.environ.get("BACKEND_WS_URL", "")
    if ws_url:
        # ws://host:port/ws/stream/PATIENT_ID -> extract PATIENT_ID
        import re
        match = re.search(r'/ws/stream/([^/]+)$', ws_url)
        if match:
            return match.group(1)
    
    return os.environ.get("PATIENT_ID", "test-patient-id")

PATIENT_ID = _get_patient_id()
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "")

# Print config on import (for debugging)
print(f"[Voice Config] API URL: {BACKEND_API_URL}")
print(f"[Voice Config] Patient ID: {PATIENT_ID}")


ITEM_PATTERNS = [
    r"where (?:are|is) (?:my |the )?(.+?)(?:\?|$)",
    r"find (?:my |the )?(.+?)(?:\?|$)",
    r"(?:have you seen|did you see) (?:my |the )?(.+?)(?:\?|$)",
    r"(?:where did i (?:put|leave)) (?:my |the )?(.+?)(?:\?|$)",
]

PERSON_PATTERNS = [
    r"who is (?:this|that|he|she)",
    r"who(?:'s| is) (?:this|that)",
    r"identify (?:this |that )?person",
    r"do i know (?:this |that )?person",
    r"who am i (?:looking at|seeing)",
]

REMINDER_PATTERNS = [
    r"what (?:do i|should i) (?:need to )?remember",
    r"(?:what are|tell me) (?:my |today'?s? )?reminders",
    r"what(?:'s| is) (?:on )?(?:my |the )?schedule",
    r"what (?:do i have|am i doing) today",
    r"remind me",
]


def detect_intent(text: str) -> IntentResult:
    """
    Detect the user's intent from spoken text using rule-based matching.
    
    Args:
        text: Transcribed speech text
        
    Returns:
        IntentResult with detected intent and entities
    """
    text_lower = text.lower().strip()

    for pattern in ITEM_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            item = match.group(1).strip()
            item = re.sub(r"\s+", " ", item)
            return IntentResult(
                intent=Intent.FIND_ITEM,
                entities={"item": item},
                raw_text=text
            )

    for pattern in PERSON_PATTERNS:
        if re.search(pattern, text_lower):
            return IntentResult(
                intent=Intent.IDENTIFY_PERSON,
                raw_text=text
            )

    for pattern in REMINDER_PATTERNS:
        if re.search(pattern, text_lower):
            return IntentResult(
                intent=Intent.TODAY_REMINDERS,
                raw_text=text
            )

    return IntentResult(intent=Intent.UNKNOWN, raw_text=text)


def send_query(question: str, patient_id: str = None, token: str = None) -> Optional[QueryResponse]:
    """
    Send a query to the backend API.
    
    Args:
        question: The question to ask
        patient_id: Patient ID (uses env var if not provided)
        token: Auth token (uses env var if not provided)
        
    Returns:
        QueryResponse or None if failed
    """
    patient_id = patient_id or PATIENT_ID
    token = token or AUTH_TOKEN

    # Use device endpoint (no auth needed) for Pi
    url = f"{BACKEND_API_URL}/voice/query/device"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "patient_id": patient_id,
        "query": question  # Note: voice endpoint uses 'query' not 'question'
    }

    try:
        print(f"[DEBUG] Sending to: {url}")
        print(f"[DEBUG] Payload: {payload}")
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response body: {response.text[:500]}")
        response.raise_for_status()
        data = response.json()

        if "data" in data:
            result_data = data["data"]
            # Voice endpoint returns 'type' and 'message' directly
            return QueryResponse(
                answer_type=result_data.get("type", result_data.get("answer_type", "unknown")),
                message=result_data.get("message", "I couldn't process that."),
                results=result_data.get("results", {})
            )
        return None

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Query failed: {e}")
        # Try to print response body for debugging
        try:
            print(f"[DEBUG] Error response: {e.response.text if hasattr(e, 'response') and e.response else 'No response body'}")
        except:
            pass
        return None
    except json.JSONDecodeError:
        print("ERROR: Invalid JSON response from backend")
        return None


def format_response_message(data: dict) -> str:
    """
    Format the backend response into a speakable message.
    
    Args:
        data: Response data from backend
        
    Returns:
        Human-readable message
    """
    answer_type = data.get("answer_type", "unknown")
    results = data.get("results")

    if answer_type == "item_location":
        if isinstance(results, list) and results:
            item = results[0]
            item_name = item.get("item", "item")
            room = item.get("room", "unknown location")
            last_seen = item.get("last_seen_at")
            time_ago = _format_time_ago(last_seen) if last_seen else None

            if time_ago:
                return f"Your {item_name} were last seen in the {room} {time_ago}."
            return f"Your {item_name} were last seen in the {room}."
        return "I couldn't find that item in my records."

    if answer_type == "person_recognized":
        if results:
            name = results.get("name", "someone")
            return f"The last person I recognized was {name}."
        return "I haven't recognized anyone recently."

    if answer_type == "daily_summary":
        if isinstance(results, dict):
            messages = []
            reminders = results.get("reminders", [])
            notes = results.get("notes", [])

            if reminders:
                messages.append(f"You have {len(reminders)} reminders today.")
                for r in reminders[:3]:
                    messages.append(r.get("message", ""))

            if notes:
                messages.append("Today's notes include:")
                for n in notes[:2]:
                    messages.append(n.get("content", ""))

            if not messages:
                return "You have no reminders or notes for today."
            return " ".join(messages)
        return "I couldn't find your schedule."

    if answer_type == "medication":
        if isinstance(results, dict):
            reminders = results.get("reminders", [])
            if reminders:
                return f"You have {len(reminders)} medication reminders. " + \
                       " ".join(r.get("message", "") for r in reminders[:2])
        return "I don't have any medication reminders for you."

    if isinstance(results, str):
        return results

    return "I'm sorry, I couldn't understand that question. Try asking about an item, person, or your reminders."


def _format_time_ago(timestamp: str) -> Optional[str]:
    """Format an ISO timestamp into a human-readable time ago string."""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        diff = now - dt

        seconds = diff.total_seconds()
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        if seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    except Exception:
        return None


class VoiceListener:
    """
    Continuous voice listener for MemoLens.
    Listens for voice commands, detects intent, queries backend, and speaks responses.
    """

    def __init__(
        self,
        patient_id: str = None,
        auth_token: str = None,
        on_speech_detected: Callable[[str], None] = None,
        on_response: Callable[[str], None] = None,
    ):
        self.patient_id = patient_id or PATIENT_ID
        self.auth_token = auth_token or AUTH_TOKEN
        self.on_speech_detected = on_speech_detected
        self.on_response = on_response
        self._running = False
        self._recognizer: Optional["sr.Recognizer"] = None
        self._microphone: Optional["sr.Microphone"] = None

        if STT_AVAILABLE:
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 300
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.pause_threshold = 0.8

    def listen_once(self, timeout: float = 5.0) -> Optional[str]:
        """
        Listen for a single voice command.
        
        Args:
            timeout: Max seconds to wait for speech
            
        Returns:
            Transcribed text or None
        """
        if not STT_AVAILABLE:
            print("ERROR: Speech recognition not available")
            return None

        # Use custom recognizer (no FLAC needed)
        if USE_CUSTOM_STT and CUSTOM_STT_AVAILABLE:
            try:
                print("Listening...")
                text = custom_listen(timeout=timeout)
                if text:
                    print(f"Heard: {text}")
                return text
            except Exception as e:
                print(f"Custom STT error: {e}")
                # Fall through to try speech_recognition
                if not SR_AVAILABLE:
                    return None

        # Fallback to speech_recognition library
        if SR_AVAILABLE and self._recognizer:
            try:
                with sr.Microphone(device_index=MICROPHONE_INDEX) as source:
                    print("Listening...")
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = self._recognizer.listen(source, timeout=timeout, phrase_time_limit=10)

                print("Processing speech...")
                try:
                    text = self._recognizer.recognize_google(audio)
                    print(f"Heard: {text}")
                    return text
                except sr.UnknownValueError:
                    print("Could not understand audio")
                    return None
                except sr.RequestError as e:
                    print(f"Speech recognition error: {e}")
                    return None
            except sr.WaitTimeoutError:
                return None
            except Exception as e:
                print(f"ERROR: Listen failed: {e}")
                return None

        return None

    def process_voice_command(self, text: str) -> Optional[str]:
        """
        Process a voice command: detect intent, query backend, return response.
        
        Args:
            text: Transcribed speech
            
        Returns:
            Response message to speak, or None if intent not understood
        """
        if self.on_speech_detected:
            self.on_speech_detected(text)

        intent_result = detect_intent(text)
        print(f"Intent: {intent_result.intent.value}, Entities: {intent_result.entities}")

        # If intent is unknown, stay silent
        if intent_result.intent == Intent.UNKNOWN:
            print(f"Unknown intent, staying silent for: '{text}'")
            return None

        response = send_query(text, self.patient_id, self.auth_token)

        if response:
            message = response.message
            # Check if backend returned a "didn't understand" type response
            if response.answer_type == "unknown" or "couldn't understand" in message.lower() or "sorry" in message.lower():
                print(f"Backend didn't understand, staying silent")
                return None
        else:
            # No response from backend, stay silent
            print("No backend response, staying silent")
            return None

        if self.on_response:
            self.on_response(message)

        return message

    def listen_and_respond(self) -> bool:
        """
        Listen for one command and speak the response.
        
        Returns:
            True if a command was processed, False otherwise
        """
        text = self.listen_once()
        if not text:
            return False

        # Filter out very short or noise-like transcriptions
        words = text.split()
        if len(words) < 2:
            print(f"Ignoring short input: '{text}'")
            return False
        
        # Filter out common noise misrecognitions
        noise_phrases = ["the", "a", "um", "uh", "hmm", "ah", "oh"]
        if text.lower().strip() in noise_phrases:
            print(f"Ignoring noise: '{text}'")
            return False

        message = self.process_voice_command(text)
        if message:
            speak_response(message)
            return True
        # If message is None, we intentionally stay silent (unknown intent)
        return False

    def start_continuous_listening(self) -> None:
        """Start continuous voice listening loop."""
        if not STT_AVAILABLE:
            print("ERROR: Cannot start - speech recognition not available")
            return

        self._running = True
        print("Starting continuous voice listener...")
        speak("Voice assistant ready. How can I help you?")

        while self._running:
            try:
                self.listen_and_respond()
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"ERROR in listen loop: {e}")
                continue

        print("Voice listener stopped.")

    def stop(self) -> None:
        """Stop the continuous listening loop."""
        self._running = False


def handle_voice_event(event: dict) -> None:
    """
    Handle a voice event from WebSocket (person detected, reminder triggered).
    
    Args:
        event: Event dictionary with 'type' and optionally 'message'
    """
    event_type = event.get("type")

    if event_type == "voice":
        message = event.get("message", "")
        if message:
            speak_response(message)

    elif event_type == "person":
        name = event.get("name", "someone")
        relationship = event.get("relationship")
        conversation_prompt = event.get("conversation_prompt")

        if relationship:
            message = f"This is {name}, your {relationship}."
        else:
            message = f"This is {name}."

        if conversation_prompt:
            message += f" {conversation_prompt}"

        speak_response(message)

    elif event_type == "reminder":
        message = event.get("message", "You have a reminder")
        speak_reminder(message)


if __name__ == "__main__":
    print("Testing VoiceListener...")

    test_phrases = [
        "Where are my keys?",
        "Who is this?",
        "What do I need to remember today?",
        "Find my phone",
        "What's on my schedule?",
        "Hello there",
    ]

    for phrase in test_phrases:
        result = detect_intent(phrase)
        print(f"'{phrase}' -> {result.intent.value}, {result.entities}")

    print("\nStarting voice listener (Ctrl+C to stop)...")
    listener = VoiceListener()
    listener.start_continuous_listening()
