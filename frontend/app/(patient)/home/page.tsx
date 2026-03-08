"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { apiGet } from "../../../lib/api";
import { getPatientId, getToken, setPatientId } from "../../../lib/session";
import { useEventFeed } from "../../../lib/useEventFeed";
import type { EventItem, Reminder } from "../../../lib/types";
import { VoiceAssistant } from "../../../components/patient/VoiceAssistant";

function extractReminderMessage(event: EventItem): string | null {
  if (event.type !== "reminder_triggered") return null;
  const payload = event.payload || {};
  const msg = payload.message;
  return typeof msg === "string" ? msg : null;
}

export default function PatientHomePage() {
  const token = getToken();
  const [patientId, setPatientInput] = useState(getPatientId() || "");
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [initialEvents, setInitialEvents] = useState<EventItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showVoice, setShowVoice] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isConfigured, setIsConfigured] = useState(false);

  const { events, connected, error: wsError } = useEventFeed(patientId || null, token, initialEvents);

  const liveMessages = useMemo(() => {
    const seen = new Set<string>();
    const out: string[] = [];
    for (const e of events) {
      const msg = extractReminderMessage(e);
      if (!msg || seen.has(msg)) continue;
      seen.add(msg);
      out.push(msg);
    }
    return out.slice(0, 6);
  }, [events]);

  async function load() {
    if (!token || !patientId) return;
    setIsLoading(true);
    const [remRes, evRes] = await Promise.all([
      apiGet<Reminder[]>(`/patients/${patientId}/reminders/`, token),
      apiGet<EventItem[]>(`/patients/${patientId}/events?type=reminder_triggered&limit=30`, token),
    ]);
    setError(remRes.error || evRes.error || null);
    setReminders((remRes.data || []).filter((r) => r.active));
    setInitialEvents(evRes.data || []);
    setPatientId(patientId);
    setIsConfigured(true);
    setIsLoading(false);
  }

  useEffect(() => {
    if (patientId) {
      void load();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main style={{ paddingBottom: 120 }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <Link href="/" className="btn ghost small" style={{ marginBottom: 16, padding: '8px 12px' }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          Home
        </Link>
        <div className="flex justify-between items-center">
          <div>
            <h1 style={{ marginBottom: 8 }}>Hello there</h1>
            <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
              How can I help you today?
            </p>
          </div>
          {isConfigured && (
            <div className="flex items-center gap-sm">
              <div className={`status-dot ${connected ? 'online' : 'offline'}`} />
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {connected ? 'Live' : 'Offline'}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Setup Card - only show if not configured */}
      {!isConfigured && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 12 }}>Setup Required</h3>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-tertiary)', marginBottom: 16 }}>
            Enter your Patient ID to get started
          </p>
          <div className="grid" style={{ gap: 12 }}>
            <input
              placeholder="Enter Patient ID"
              value={patientId}
              onChange={(e) => setPatientInput(e.target.value)}
            />
            <button 
              className="btn full-width" 
              type="button" 
              onClick={() => void load()}
              disabled={isLoading || !patientId}
            >
              {isLoading ? (
                <>
                  <div className="spinner" style={{ width: 18, height: 18 }} />
                  Loading...
                </>
              ) : (
                "Connect"
              )}
            </button>
          </div>
        </div>
      )}

      {(error || wsError) && <div className="error-message" style={{ marginBottom: 16 }}>{error || wsError}</div>}

      {/* Voice Assistant - Main Feature */}
      {isConfigured && (
        <div style={{ marginBottom: 32 }}>
          <button
            className={`btn full-width ${showVoice ? 'secondary' : ''}`}
            type="button"
            onClick={() => setShowVoice(!showVoice)}
            style={{ 
              minHeight: 64,
              fontSize: '1.125rem',
              gap: 12
            }}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
              <path d="M19 10v1a7 7 0 0 1-14 0v-1M12 18.5v3.5M8 22h8"/>
            </svg>
            {showVoice ? "Hide Voice Assistant" : "Ask a Question"}
          </button>

          {showVoice && (
            <div style={{ marginTop: 16 }}>
              <VoiceAssistant
                patientId={patientId}
                onResponse={(response) => {
                  console.log("Voice response:", response);
                }}
              />
            </div>
          )}
        </div>
      )}

      {/* Quick Actions */}
      {isConfigured && (
        <div style={{ marginBottom: 32 }}>
          <h2 style={{ marginBottom: 16 }}>Quick Actions</h2>
          <div className="grid" style={{ gap: 12 }}>
            <Link href="/query" className="action-item">
              <div className="icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8"/>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
              </div>
              <div className="content">
                <div className="title">Find My Things</div>
                <div className="subtitle">Ask where you left items</div>
              </div>
              <div className="arrow">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </div>
            </Link>

            <Link href="/who" className="action-item">
              <div className="icon" style={{ background: 'var(--accent-secondary-muted)', color: 'var(--accent-secondary)' }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                  <circle cx="12" cy="7" r="4"/>
                </svg>
              </div>
              <div className="content">
                <div className="title">Who Is This?</div>
                <div className="subtitle">Identify familiar people</div>
              </div>
              <div className="arrow">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </div>
            </Link>
          </div>
        </div>
      )}

      {/* Live Messages Section */}
      {isConfigured && liveMessages.length > 0 && (
        <div style={{ marginBottom: 32 }}>
          <h2 style={{ marginBottom: 16 }}>Live Updates</h2>
          <div className="grid" style={{ gap: 12 }}>
            {liveMessages.map((msg, idx) => (
              <div 
                key={`${msg}-${idx}`} 
                className="card"
                style={{ 
                  borderLeft: '4px solid var(--accent-secondary)',
                  background: 'var(--accent-secondary-muted)',
                }}
              >
                <div style={{ fontSize: '1.125rem', fontWeight: 600 }}>
                  {msg}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Reminders Section */}
      {isConfigured && (
        <div>
          <div className="flex justify-between items-center" style={{ marginBottom: 16 }}>
            <h2 style={{ margin: 0 }}>Today&apos;s Reminders</h2>
            <span className="badge info">{reminders.length}</span>
          </div>

          {reminders.length === 0 ? (
            <div className="card text-center" style={{ padding: 32 }}>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2" style={{ margin: '0 auto 12px' }}>
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
              <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
                No active reminders
              </p>
            </div>
          ) : (
            <div className="grid" style={{ gap: 12 }}>
              {reminders.map((r) => (
                <div 
                  key={r.id} 
                  className="card"
                  style={{ 
                    borderLeft: '4px solid var(--accent)',
                    padding: '16px 16px 16px 20px'
                  }}
                >
                  <div style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: 4 }}>
                    {r.message}
                  </div>
                  <div style={{ fontSize: '0.875rem', color: 'var(--text-tertiary)' }}>
                    {r.type === 'time' ? '⏰ Time-based' : 
                     r.type === 'location' ? '📍 Location-based' : 
                     r.type === 'person' ? '👤 Person-based' : 
                     '📦 Object-based'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Patient ID display when configured */}
      {isConfigured && (
        <div className="card" style={{ marginTop: 32, textAlign: 'center' }}>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: 0 }}>
            Patient ID: <code style={{ color: 'var(--text-tertiary)' }}>{patientId.slice(0, 8)}...</code>
          </p>
          <button 
            className="btn ghost small" 
            type="button" 
            onClick={() => {
              setIsConfigured(false);
              setPatientInput('');
            }}
            style={{ marginTop: 8 }}
          >
            Change Patient
          </button>
        </div>
      )}
    </main>
  );
}
