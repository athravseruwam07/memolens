"""
Text-to-Speech module for MemoLens Pi wearable.
Provides voice output for person recognition, reminders, and query responses.
Uses gTTS (Google Text-to-Speech) with fallback to pyttsx3.
"""

import os
import threading
import queue
import tempfile
import subprocess
from typing import Optional

TTS_ENGINE = os.environ.get("TTS_ENGINE", "gtts")

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    print("WARNING: gTTS not installed.")

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    print("WARNING: pyttsx3 not installed.")


class TextToSpeech:
    """
    Thread-safe text-to-speech engine.
    Uses a queue to handle concurrent speech requests without blocking.
    """

    def __init__(self, rate: int = 150, volume: float = 1.0):
        self._queue: queue.Queue[Optional[str]] = queue.Queue()
        self._rate = rate
        self._volume = volume
        self._running = False
        self._thread: Optional[threading.Thread] = None

        if GTTS_AVAILABLE or PYTTSX3_AVAILABLE:
            self._start_engine()
        else:
            print("WARNING: No TTS engine available. Speech will be printed only.")

    def _start_engine(self) -> None:
        """Initialize and start the TTS engine in a background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self) -> None:
        """Background loop that processes speech requests."""
        while self._running:
            try:
                text = self._queue.get(timeout=0.5)
                if text is None:
                    break
                self._speak_internal(text)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"ERROR: TTS failed: {e}")

    def _speak_internal(self, text: str) -> None:
        """Actually speak the text using available engine."""
        if GTTS_AVAILABLE and TTS_ENGINE == "gtts":
            self._speak_gtts(text)
        elif PYTTSX3_AVAILABLE:
            self._speak_pyttsx3(text)
        else:
            print(f"[SPEAK] {text}")

    def _speak_gtts(self, text: str) -> None:
        """Speak using Google TTS."""
        try:
            tts = gTTS(text=text, lang='en', slow=False)
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                temp_path = f.name
            tts.save(temp_path)

            # Try different audio players
            players = [
                ['mpg123', '-q', temp_path],
                ['mpg321', '-q', temp_path],
                ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', temp_path],
                ['aplay', temp_path],
            ]

            for player_cmd in players:
                try:
                    subprocess.run(player_cmd, check=True, capture_output=True)
                    break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue

            os.unlink(temp_path)
        except Exception as e:
            print(f"ERROR: gTTS failed: {e}")
            if PYTTSX3_AVAILABLE:
                self._speak_pyttsx3(text)

    def _speak_pyttsx3(self, text: str) -> None:
        """Speak using pyttsx3 (offline)."""
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", self._rate)
            engine.setProperty("volume", self._volume)
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"ERROR: pyttsx3 failed: {e}")

    def speak(self, text: str) -> None:
        """
        Queue text to be spoken. Non-blocking.
        
        Args:
            text: The text to speak
        """
        if not self._running:
            print(f"[TTS DISABLED] Would say: {text}")
            return

        self._queue.put(text)

    def speak_sync(self, text: str) -> None:
        """
        Speak text synchronously (blocking).
        
        Args:
            text: The text to speak
        """
        self._speak_internal(text)

    def stop(self) -> None:
        """Stop the TTS engine and cleanup."""
        self._running = False
        self._queue.put(None)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def set_rate(self, rate: int) -> None:
        """Set speech rate (words per minute)."""
        self._rate = rate

    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)."""
        self._volume = max(0.0, min(1.0, volume))


_tts_instance: Optional[TextToSpeech] = None


def get_tts() -> TextToSpeech:
    """Get the singleton TTS instance."""
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = TextToSpeech()
    return _tts_instance


def speak(text: str) -> None:
    """
    Convenience function to speak text using the singleton TTS instance.
    
    Args:
        text: The text to speak
    """
    get_tts().speak(text)


def speak_person_recognized(name: str, relationship: str = None, conversation_prompt: str = None) -> None:
    """
    Announce a recognized person to the patient.
    
    Args:
        name: Person's name
        relationship: Their relationship to the patient
        conversation_prompt: Optional conversation starter
    """
    if relationship:
        message = f"This is {name}, your {relationship}."
    else:
        message = f"This is {name}."

    if conversation_prompt:
        message += f" {conversation_prompt}"

    speak(message)


def speak_reminder(message: str) -> None:
    """
    Announce a reminder.
    
    Args:
        message: The reminder message
    """
    speak(f"Reminder: {message}")


def speak_item_location(item: str, room: str, time_ago: str = None) -> None:
    """
    Announce an item's location.
    
    Args:
        item: Name of the item
        room: Where it was last seen
        time_ago: How long ago (e.g., "5 minutes ago")
    """
    if time_ago:
        speak(f"Your {item} were last seen in the {room} {time_ago}.")
    else:
        speak(f"Your {item} were last seen in the {room}.")


def speak_response(message: str) -> None:
    """
    Speak a general response message.
    
    Args:
        message: The message to speak
    """
    speak(message)


if __name__ == "__main__":
    print("Testing TTS module...")
    print(f"gTTS available: {GTTS_AVAILABLE}")
    print(f"pyttsx3 available: {PYTTSX3_AVAILABLE}")
    print(f"Using engine: {TTS_ENGINE}")

    speak_sync = get_tts().speak_sync
    speak_sync("Hello, this is MemoLens.")
    speak_sync("This is Sarah, your daughter.")
    speak_sync("Reminder: take your medication.")

    print("TTS test complete.")
