"""
Custom Speech Recognition module that doesn't require FLAC.
Uses WAV format directly with Google Speech Recognition API.
"""

import io
import os
import json
import wave
import base64
import struct
from typing import Optional

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

MICROPHONE_INDEX = int(os.environ.get("MICROPHONE_INDEX", "2"))
SAMPLE_RATE = 16000
CHUNK_SIZE = 1024
CHANNELS = 1
FORMAT = pyaudio.paInt16 if PYAUDIO_AVAILABLE else None

GOOGLE_SPEECH_URL = "http://www.google.com/speech-api/v2/recognize"
GOOGLE_API_KEY = "AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw"  # Public key used by Chrome


class AudioRecorder:
    """Records audio from microphone."""

    def __init__(self, device_index: int = None):
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError("PyAudio not available")
        
        self.device_index = device_index
        self.audio = pyaudio.PyAudio()

    def record(self, duration: float = 8.0, silence_timeout: float = 2.5) -> bytes:
        """
        Record audio with silence detection.
        
        Args:
            duration: Maximum recording duration in seconds
            silence_timeout: Stop recording after this many seconds of silence
            
        Returns:
            WAV audio data as bytes
        """
        stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=CHUNK_SIZE
        )

        frames = []
        silent_chunks = 0
        speech_detected = False
        max_silent_chunks = int(silence_timeout * SAMPLE_RATE / CHUNK_SIZE)
        max_chunks = int(duration * SAMPLE_RATE / CHUNK_SIZE)
        silence_threshold = 300  # Lower threshold = more sensitive to speech
        speech_threshold = 600   # Higher threshold to confirm speech started
        min_speech_chunks = 30   # Require ~2 seconds of audio before checking silence

        print("Recording...")
        
        for i in range(max_chunks):
            try:
                data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                frames.append(data)

                # Check for silence/speech
                rms = self._calculate_rms(data)
                
                # Detect if speech has started
                if rms > speech_threshold:
                    speech_detected = True
                    silent_chunks = 0
                elif rms < silence_threshold:
                    silent_chunks += 1
                else:
                    # In between - don't count as silence if speech started
                    if speech_detected:
                        silent_chunks = max(0, silent_chunks - 1)

                # Only stop on silence AFTER speech was detected AND enough audio captured
                if speech_detected and len(frames) > min_speech_chunks and silent_chunks > max_silent_chunks:
                    break
            except Exception as e:
                print(f"Recording error: {e}")
                break

        stream.stop_stream()
        stream.close()

        # Convert to WAV
        return self._frames_to_wav(frames)

    def _calculate_rms(self, data: bytes) -> float:
        """Calculate RMS (volume level) of audio data."""
        count = len(data) // 2
        shorts = struct.unpack(f"{count}h", data)
        sum_squares = sum(s * s for s in shorts)
        return (sum_squares / count) ** 0.5

    def _frames_to_wav(self, frames: list) -> bytes:
        """Convert raw audio frames to WAV format."""
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.audio.get_sample_size(FORMAT))
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b''.join(frames))
        return buffer.getvalue()

    def close(self):
        """Clean up resources."""
        self.audio.terminate()


def recognize_google_wav(audio_data: bytes, language: str = "en-US") -> Optional[str]:
    """
    Send WAV audio to Google Speech Recognition API.
    
    Args:
        audio_data: WAV audio data
        language: Language code
        
    Returns:
        Transcribed text or None
    """
    if not REQUESTS_AVAILABLE:
        print("ERROR: requests library not available")
        return None

    url = f"{GOOGLE_SPEECH_URL}?output=json&lang={language}&key={GOOGLE_API_KEY}"
    
    headers = {
        "Content-Type": f"audio/l16; rate={SAMPLE_RATE}"
    }

    # Extract raw PCM from WAV
    buffer = io.BytesIO(audio_data)
    with wave.open(buffer, 'rb') as wf:
        pcm_data = wf.readframes(wf.getnframes())

    try:
        response = requests.post(url, data=pcm_data, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Google API error: {response.status_code}")
            return None

        # Parse response (multiple JSON objects, one per line)
        text = response.text.strip()
        for line in text.split('\n'):
            if not line.strip():
                continue
            try:
                result = json.loads(line)
                if 'result' in result and result['result']:
                    alternatives = result['result'][0].get('alternative', [])
                    if alternatives:
                        return alternatives[0].get('transcript')
            except json.JSONDecodeError:
                continue

        return None

    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None


class SpeechRecognizer:
    """High-level speech recognition interface."""

    def __init__(self, device_index: int = None):
        self.device_index = device_index if device_index is not None else MICROPHONE_INDEX
        self.recorder = None

    def listen_and_recognize(self, timeout: float = 5.0) -> Optional[str]:
        """
        Listen for speech and return transcribed text.
        
        Args:
            timeout: Maximum listening time in seconds
            
        Returns:
            Transcribed text or None
        """
        if not PYAUDIO_AVAILABLE:
            print("ERROR: PyAudio not available")
            return None

        try:
            if self.recorder is None:
                self.recorder = AudioRecorder(self.device_index)

            audio_data = self.recorder.record(duration=timeout)
            
            if len(audio_data) < 1000:
                print("No audio captured")
                return None

            print("Sending to Google...")
            text = recognize_google_wav(audio_data)
            
            if text:
                print(f"Recognized: {text}")
            else:
                print("Could not recognize speech")
                
            return text

        except Exception as e:
            print(f"Recognition error: {e}")
            return None

    def close(self):
        """Clean up resources."""
        if self.recorder:
            self.recorder.close()
            self.recorder = None


# Singleton instance
_recognizer: Optional[SpeechRecognizer] = None


def get_recognizer() -> SpeechRecognizer:
    """Get singleton recognizer instance."""
    global _recognizer
    if _recognizer is None:
        _recognizer = SpeechRecognizer()
    return _recognizer


def listen_once(timeout: float = 5.0) -> Optional[str]:
    """
    Convenience function to listen and recognize speech once.
    
    Args:
        timeout: Maximum listening time
        
    Returns:
        Transcribed text or None
    """
    return get_recognizer().listen_and_recognize(timeout)


if __name__ == "__main__":
    print("Testing speech recognizer...")
    print(f"PyAudio available: {PYAUDIO_AVAILABLE}")
    print(f"Requests available: {REQUESTS_AVAILABLE}")
    print(f"Microphone index: {MICROPHONE_INDEX}")
    
    print("\nSpeak now...")
    text = listen_once()
    if text:
        print(f"You said: {text}")
    else:
        print("No speech detected")
