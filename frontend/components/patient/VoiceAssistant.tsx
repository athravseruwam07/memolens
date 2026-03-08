"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiPost } from "../../lib/api";
import { getPatientId, getToken } from "../../lib/session";

type VoiceState = "idle" | "listening" | "processing" | "speaking" | "error";

interface VoiceResponse {
  type: string;
  message: string;
  results?: unknown;
}

interface VoiceAssistantProps {
  patientId?: string;
  autoStart?: boolean;
  onStateChange?: (state: VoiceState) => void;
  onTranscript?: (text: string) => void;
  onResponse?: (response: VoiceResponse) => void;
  onError?: (error: string) => void;
  showUI?: boolean;
  speakResponses?: boolean;
}

declare global {
  interface Window {
    webkitSpeechRecognition: new () => SpeechRecognition;
    SpeechRecognition: new () => SpeechRecognition;
  }
}

interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message?: string;
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
}

function getSpeechRecognition(): SpeechRecognition | null {
  if (typeof window === "undefined") return null;

  const SpeechRecognitionClass =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognitionClass) return null;

  return new SpeechRecognitionClass();
}

function speak(text: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      resolve();
      return;
    }

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.9;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = voices.find(
      (v) => v.lang.startsWith("en") && v.name.includes("Female")
    );
    if (preferredVoice) {
      utterance.voice = preferredVoice;
    }

    utterance.onend = () => resolve();
    utterance.onerror = (e) => reject(e);

    window.speechSynthesis.speak(utterance);
  });
}

export function VoiceAssistant({
  patientId: propPatientId,
  autoStart = false,
  onStateChange,
  onTranscript,
  onResponse,
  onError,
  showUI = true,
  speakResponses = true,
}: VoiceAssistantProps) {
  const [state, setState] = useState<VoiceState>("idle");
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState<VoiceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState(true);

  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const isListeningRef = useRef(false);

  const updateState = useCallback(
    (newState: VoiceState) => {
      setState(newState);
      onStateChange?.(newState);
    },
    [onStateChange]
  );

  const handleError = useCallback(
    (errorMsg: string) => {
      setError(errorMsg);
      onError?.(errorMsg);
      updateState("error");
    },
    [onError, updateState]
  );

  const processQuery = useCallback(
    async (query: string) => {
      const patientId = propPatientId || getPatientId();
      const token = getToken();

      if (!patientId) {
        handleError("No patient ID set. Please set up your profile first.");
        return;
      }

      updateState("processing");

      try {
        const res = await apiPost<VoiceResponse>(
          "/voice/query",
          { patient_id: patientId, query },
          token || undefined
        );

        if (res.error) {
          handleError(res.error);
          return;
        }

        if (res.data) {
          setResponse(res.data);
          onResponse?.(res.data);

          if (speakResponses && res.data.message) {
            updateState("speaking");
            try {
              await speak(res.data.message);
            } catch {
              // TTS may fail silently
            }
          }
        }

        updateState("idle");
      } catch (err) {
        handleError(
          err instanceof Error ? err.message : "Failed to process query"
        );
      }
    },
    [
      propPatientId,
      handleError,
      updateState,
      onResponse,
      speakResponses,
    ]
  );

  const startListening = useCallback(() => {
    if (isListeningRef.current) return;

    const recognition = getSpeechRecognition();
    if (!recognition) {
      handleError("Speech recognition is not supported in this browser.");
      setIsSupported(false);
      return;
    }

    recognitionRef.current = recognition;
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onstart = () => {
      isListeningRef.current = true;
      setTranscript("");
      setError(null);
      updateState("listening");
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interimTranscript = "";
      let finalTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript;
        } else {
          interimTranscript += result[0].transcript;
        }
      }

      const currentTranscript = finalTranscript || interimTranscript;
      setTranscript(currentTranscript);

      if (finalTranscript) {
        onTranscript?.(finalTranscript);
        void processQuery(finalTranscript);
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      isListeningRef.current = false;

      if (event.error === "no-speech") {
        updateState("idle");
        return;
      }

      if (event.error === "aborted") {
        return;
      }

      handleError(`Speech recognition error: ${event.error}`);
    };

    recognition.onend = () => {
      isListeningRef.current = false;
      if (state === "listening") {
        updateState("idle");
      }
    };

    try {
      recognition.start();
    } catch {
      handleError("Failed to start speech recognition. Please try again.");
    }
  }, [handleError, onTranscript, processQuery, state, updateState]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current && isListeningRef.current) {
      recognitionRef.current.stop();
      isListeningRef.current = false;
    }
    window.speechSynthesis?.cancel();
    updateState("idle");
  }, [updateState]);

  const toggleListening = useCallback(() => {
    if (state === "listening") {
      stopListening();
    } else if (state === "idle" || state === "error") {
      startListening();
    }
  }, [state, startListening, stopListening]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const recognition = getSpeechRecognition();
      setIsSupported(!!recognition);

      if (window.speechSynthesis) {
        window.speechSynthesis.getVoices();
      }
    }
  }, []);

  useEffect(() => {
    if (autoStart && isSupported) {
      startListening();
    }
  }, [autoStart, isSupported, startListening]);

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
      window.speechSynthesis?.cancel();
    };
  }, []);

  if (!showUI) return null;

  const stateConfig = {
    idle: { 
      bg: 'var(--gradient-primary)', 
      shadow: 'var(--shadow-glow)',
      label: 'Tap to speak'
    },
    listening: { 
      bg: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)', 
      shadow: '0 0 40px rgba(239, 68, 68, 0.4)',
      label: 'Listening...'
    },
    processing: { 
      bg: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', 
      shadow: '0 0 40px rgba(245, 158, 11, 0.4)',
      label: 'Processing...'
    },
    speaking: { 
      bg: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)', 
      shadow: '0 0 40px rgba(34, 197, 94, 0.4)',
      label: 'Speaking...'
    },
    error: { 
      bg: 'var(--surface)', 
      shadow: 'none',
      label: 'Tap to try again'
    },
  };

  const currentConfig = stateConfig[state];

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 20,
      padding: 24,
      background: 'var(--surface)',
      borderRadius: 'var(--radius-lg)',
      border: '1px solid var(--surface-border)',
    }}>
      {!isSupported ? (
        <div style={{ textAlign: 'center', color: 'var(--text-tertiary)', padding: 16 }}>
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ margin: '0 auto 12px' }}>
            <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
            <path d="M19 10v1a7 7 0 0 1-14 0v-1"/>
            <line x1="1" y1="1" x2="23" y2="23"/>
          </svg>
          <p style={{ margin: 0, marginBottom: 8 }}>Voice recognition not supported</p>
          <p style={{ margin: 0, fontSize: '0.875rem' }}>Use Chrome, Edge, or Safari</p>
        </div>
      ) : (
        <>
          {/* Main Button */}
          <button
            onClick={toggleListening}
            disabled={state === "processing" || state === "speaking"}
            style={{
              width: 88,
              height: 88,
              borderRadius: '50%',
              border: 'none',
              background: currentConfig.bg,
              boxShadow: currentConfig.shadow,
              cursor: state === "processing" || state === "speaking" ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s ease',
              opacity: state === "processing" || state === "speaking" ? 0.8 : 1,
              animation: state === 'listening' ? 'pulse 1.5s infinite' : 'none',
            }}
            aria-label={state === "listening" ? "Stop listening" : "Start listening"}
          >
            <style>{`
              @keyframes pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.05); }
              }
            `}</style>
            
            {state === "listening" ? (
              <svg width="32" height="32" viewBox="0 0 24 24" fill="var(--bg-primary)">
                <rect x="6" y="6" width="12" height="12" rx="2" />
              </svg>
            ) : state === "processing" ? (
              <div style={{
                width: 32,
                height: 32,
                border: '3px solid rgba(10,10,15,0.3)',
                borderTopColor: 'var(--bg-primary)',
                borderRadius: '50%',
                animation: 'spin 0.8s linear infinite',
              }}>
                <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
              </div>
            ) : state === "speaking" ? (
              <svg width="32" height="32" viewBox="0 0 24 24" fill="var(--bg-primary)">
                <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z" />
              </svg>
            ) : (
              <svg width="32" height="32" viewBox="0 0 24 24" fill={state === 'error' ? 'var(--text-muted)' : 'var(--bg-primary)'}>
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.91-3c-.49 0-.9.36-.98.85C16.52 14.2 14.47 16 12 16s-4.52-1.8-4.93-4.15c-.08-.49-.49-.85-.98-.85-.61 0-1.09.54-1 1.14.49 3 2.89 5.35 5.91 5.78V20c0 .55.45 1 1 1s1-.45 1-1v-2.08c3.02-.43 5.42-2.78 5.91-5.78.1-.6-.39-1.14-1-1.14z" />
              </svg>
            )}
          </button>

          {/* Status Label */}
          <div style={{
            fontSize: '0.875rem',
            color: 'var(--text-tertiary)',
            textAlign: 'center',
          }}>
            {currentConfig.label}
          </div>

          {/* Transcript */}
          {transcript && (
            <div style={{
              width: '100%',
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--surface-border)',
              borderRadius: 'var(--radius-md)',
              padding: '12px 16px',
              fontSize: '1rem',
              color: 'var(--text-primary)',
              textAlign: 'center',
            }}>
              &ldquo;{transcript}&rdquo;
            </div>
          )}

          {/* Response */}
          {response && state !== "listening" && (
            <div style={{
              width: '100%',
              background: 'var(--accent-muted)',
              borderRadius: 'var(--radius-md)',
              padding: 16,
              fontSize: '1.125rem',
              lineHeight: 1.5,
              color: 'var(--text-primary)',
              textAlign: 'center',
            }}>
              {response.message}
            </div>
          )}

          {/* Error */}
          {error && (
            <div style={{
              width: '100%',
              background: 'var(--error-muted)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: 'var(--radius-md)',
              padding: '12px 16px',
              color: 'var(--error)',
              fontSize: '0.875rem',
              textAlign: 'center',
            }}>
              {error}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function useVoiceAssistant(patientId?: string) {
  const [state, setState] = useState<VoiceState>("idle");
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState<VoiceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState(true);

  const recognitionRef = useRef<SpeechRecognition | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setIsSupported(!!getSpeechRecognition());
    }
  }, []);

  const startListening = useCallback(() => {
    const recognition = getSpeechRecognition();
    if (!recognition) {
      setIsSupported(false);
      return;
    }

    recognitionRef.current = recognition;
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onresult = async (event: SpeechRecognitionEvent) => {
      const text = event.results[0][0].transcript;
      setTranscript(text);
      setState("processing");

      const pid = patientId || getPatientId();
      const token = getToken();

      if (!pid) {
        setError("No patient ID");
        setState("error");
        return;
      }

      try {
        const res = await apiPost<VoiceResponse>(
          "/voice/query",
          { patient_id: pid, query: text },
          token || undefined
        );

        if (res.data) {
          setResponse(res.data);
          setState("speaking");
          await speak(res.data.message);
        }
        setState("idle");
      } catch {
        setError("Query failed");
        setState("error");
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      if (event.error !== "no-speech" && event.error !== "aborted") {
        setError(event.error);
        setState("error");
      } else {
        setState("idle");
      }
    };

    recognition.onend = () => {
      if (state === "listening") {
        setState("idle");
      }
    };

    recognition.start();
    setState("listening");
  }, [patientId, state]);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    window.speechSynthesis?.cancel();
    setState("idle");
  }, []);

  return {
    state,
    transcript,
    response,
    error,
    isSupported,
    startListening,
    stopListening,
    speak,
  };
}

export function speakMessage(message: string): Promise<void> {
  return speak(message);
}

export { speak };
