"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { apiGet } from "../../../lib/api";
import { getToken, getPatientId, setPatientId } from "../../../lib/session";
import { useEventFeed } from "../../../lib/useEventFeed";
import { useVideoFeed } from "../../../lib/useVideoFeed";
import type { EventItem, Patient } from "../../../lib/types";

function pickLatest(events: EventItem[], type: string): EventItem | null {
  return events.find((e) => e.type === type) || null;
}

export default function CaregiverDashboardPage() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>(getPatientId() || "");
  const [patient, setPatient] = useState<Patient | null>(null);
  const [initialEvents, setInitialEvents] = useState<EventItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const token = getToken();
  const { events, connected, error: wsError } = useEventFeed(selectedPatientId || null, token, initialEvents);
  const { frameB64, connected: videoConnected, error: videoError } = useVideoFeed(selectedPatientId || null, token);

  const latestPerson = useMemo(() => pickLatest(events, "face_recognized"), [events]);
  const latestReminder = useMemo(() => pickLatest(events, "reminder_triggered"), [events]);
  const latestItem = useMemo(() => pickLatest(events, "item_seen"), [events]);

  async function loadPatients() {
    const tk = getToken();
    if (!tk) {
      setError("Please login to access this page");
      setLoading(false);
      return;
    }

    const res = await apiGet<Patient[]>("/patients/", tk);
    if (res.error) {
      setError(res.error);
    } else {
      setPatients(res.data || []);
      
      const storedId = getPatientId();
      if (storedId && res.data?.find(p => p.id === storedId)) {
        setSelectedPatientId(storedId);
        const selectedPatient = res.data?.find(p => p.id === storedId);
        if (selectedPatient) {
          setPatient(selectedPatient);
        }
      }
    }
    setLoading(false);
  }

  function selectPatient(patientId: string) {
    const p = patients.find(pt => pt.id === patientId);
    if (p) {
      setSelectedPatientId(patientId);
      setPatient(p);
      setPatientId(patientId);
      setInitialEvents([]);
    }
  }

  useEffect(() => {
    void loadPatients();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main style={{ paddingBottom: 100 }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Link href="/" className="btn ghost small" style={{ marginBottom: 16, padding: '8px 12px' }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          Home
        </Link>
        <h1 style={{ marginBottom: 8 }}>Caregiver Dashboard</h1>
        <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
          Monitor and manage patient care
        </p>
      </div>

      {/* Error State */}
      {error && (
        <div className="error-message" style={{ marginBottom: 16 }}>
          {error}
          {error.includes("login") && (
            <Link href="/login" className="btn small" style={{ marginLeft: 12 }}>
              Sign In
            </Link>
          )}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="skeleton" style={{ width: '100%', height: 56 }} />
        </div>
      )}

      {/* Patient Selector */}
      {!loading && !error && patients.length === 0 && (
        <div className="card text-center" style={{ padding: 48, marginBottom: 24 }}>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" style={{ margin: '0 auto 16px' }}>
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
          <h3 style={{ marginBottom: 8, color: 'var(--text-secondary)' }}>No patients yet</h3>
          <p style={{ color: 'var(--text-tertiary)', margin: 0, marginBottom: 16 }}>
            Create your first patient to start monitoring
          </p>
          <Link href="/patients/new" className="btn">
            Create Patient
          </Link>
        </div>
      )}

      {/* Patient Selection */}
      {!loading && patients.length > 0 && !patient && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 16 }}>Select Patient</h3>
          <div className="grid" style={{ gap: 10 }}>
            {patients.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => selectPatient(p.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 16,
                  padding: 16,
                  borderRadius: 'var(--radius-lg)',
                  border: '1.5px solid var(--surface-border)',
                  background: 'var(--surface)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'var(--accent)';
                  e.currentTarget.style.background = 'var(--accent-muted)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--surface-border)';
                  e.currentTarget.style.background = 'var(--surface)';
                }}
              >
                <div 
                  style={{ 
                    width: 48, 
                    height: 48, 
                    borderRadius: 'var(--radius-full)',
                    background: 'var(--gradient-secondary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <span style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--bg-primary)' }}>
                    {p.name.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>
                    {p.name}
                  </div>
                  {p.age && (
                    <div style={{ fontSize: '0.875rem', color: 'var(--text-tertiary)' }}>
                      {p.age} years old
                    </div>
                  )}
                </div>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </button>
            ))}
          </div>
          
          <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--surface-border)' }}>
            <Link href="/patients/new" className="btn secondary full-width">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19"/>
                <line x1="5" y1="12" x2="19" y2="12"/>
              </svg>
              Add New Patient
            </Link>
          </div>
        </div>
      )}

      {(wsError || videoError) && (
        <div className="error-message" style={{ marginBottom: 16 }}>
          {wsError || videoError}
        </div>
      )}

      {patient && (
        <>
          {/* Patient Header Card */}
          <div className="card" style={{ marginBottom: 24, padding: 20 }}>
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-md">
                <div 
                  style={{ 
                    width: 48, 
                    height: 48, 
                    borderRadius: 'var(--radius-full)',
                    background: 'var(--gradient-secondary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <span style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--bg-primary)' }}>
                    {patient.name.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div>
                  <h2 style={{ margin: 0, marginBottom: 4 }}>{patient.name}</h2>
                  <div className="flex items-center gap-md">
                    <div className="flex items-center gap-sm">
                      <div className={`status-dot ${connected ? 'online' : 'offline'}`} />
                      <span style={{ fontSize: '0.875rem', color: 'var(--text-tertiary)' }}>
                        {connected ? 'Live' : 'Offline'}
                      </span>
                    </div>
                    <div className="flex items-center gap-sm">
                      <div className={`status-dot ${videoConnected ? 'online' : 'offline'}`} />
                      <span style={{ fontSize: '0.875rem', color: 'var(--text-tertiary)' }}>
                        {videoConnected ? 'Video' : 'No video'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              <button 
                className="btn ghost small"
                onClick={() => {
                  setPatient(null);
                  setSelectedPatientId('');
                }}
              >
                Change
              </button>
            </div>
          </div>

          {/* Video Feed */}
          <div style={{ marginBottom: 24 }}>
            <h3 style={{ marginBottom: 12 }}>Camera Feed</h3>
            <div className="video-feed">
              {frameB64 ? (
                <img
                  src={`data:image/jpeg;base64,${frameB64}`}
                  alt="Live camera feed"
                />
              ) : (
                <div className="flex items-center justify-center" style={{ height: '100%' }}>
                  <div className="text-center">
                    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" style={{ margin: '0 auto 12px' }}>
                      <path d="M23 7l-7 5 7 5V7z"/>
                      <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
                    </svg>
                    <p style={{ color: 'var(--text-tertiary)', margin: 0, fontSize: '0.875rem' }}>
                      Waiting for video...
                    </p>
                  </div>
                </div>
              )}
              {frameB64 && (
                <div className="overlay">
                  <div className="status-dot online" />
                  <span style={{ fontSize: '0.75rem', color: '#fff' }}>LIVE</span>
                </div>
              )}
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 24 }}>
            <div className="stat-card">
              <div className="label">Last Person</div>
              <div className="value" style={{ fontSize: '1rem' }}>
                {(latestPerson?.payload?.name as string) || "—"}
              </div>
            </div>
            <div className="stat-card">
              <div className="label">Last Reminder</div>
              <div className="value" style={{ fontSize: '1rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {(latestReminder?.payload?.message as string)?.slice(0, 15) || "—"}
              </div>
            </div>
            <div className="stat-card accent">
              <div className="label">Last Item</div>
              <div className="value" style={{ fontSize: '1rem' }}>
                {(latestItem?.payload?.item_name as string) || "—"}
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div style={{ marginBottom: 32 }}>
            <h3 style={{ marginBottom: 12 }}>Manage</h3>
            <div className="grid" style={{ gap: 10 }}>
              <Link href={`/people/${patient.id}`} className="action-item">
                <div className="icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                    <circle cx="9" cy="7" r="4"/>
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
                  </svg>
                </div>
                <div className="content">
                  <div className="title">Familiar People</div>
                  <div className="subtitle">Add faces for recognition</div>
                </div>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </Link>

              <Link href={`/reminders/${patient.id}`} className="action-item">
                <div className="icon" style={{ background: 'var(--warning-muted)', color: 'var(--warning)' }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
                    <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
                  </svg>
                </div>
                <div className="content">
                  <div className="title">Reminders</div>
                  <div className="subtitle">Set up alerts and notifications</div>
                </div>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </Link>

              <Link href={`/notes/${patient.id}`} className="action-item">
                <div className="icon" style={{ background: 'var(--info-muted)', color: 'var(--info)' }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <line x1="16" y1="13" x2="8" y2="13"/>
                    <line x1="16" y1="17" x2="8" y2="17"/>
                  </svg>
                </div>
                <div className="content">
                  <div className="title">Daily Notes</div>
                  <div className="subtitle">Log important information</div>
                </div>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </Link>

              <Link href={`/items/${patient.id}`} className="action-item">
                <div className="icon" style={{ background: 'var(--success-muted)', color: 'var(--success)' }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="11" cy="11" r="8"/>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                  </svg>
                </div>
                <div className="content">
                  <div className="title">Item Tracker</div>
                  <div className="subtitle">View detected items</div>
                </div>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </Link>

              <Link href={`/timeline/${patient.id}`} className="action-item">
                <div className="icon" style={{ background: 'var(--accent-secondary-muted)', color: 'var(--accent-secondary)' }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                  </svg>
                </div>
                <div className="content">
                  <div className="title">Event Timeline</div>
                  <div className="subtitle">View activity history</div>
                </div>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </Link>

              <Link href={`/patients/${patient.id}`} className="action-item">
                <div className="icon" style={{ background: 'rgba(255,255,255,0.06)', color: 'var(--text-secondary)' }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="3"/>
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4"/>
                  </svg>
                </div>
                <div className="content">
                  <div className="title">Patient Settings</div>
                  <div className="subtitle">View patient details</div>
                </div>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </Link>
            </div>
          </div>

          {/* Recent Events */}
          <div>
            <div className="flex justify-between items-center" style={{ marginBottom: 12 }}>
              <h3 style={{ margin: 0 }}>Recent Events</h3>
              <span className="badge info">{events.length}</span>
            </div>
            
            {events.length === 0 ? (
              <div className="card text-center" style={{ padding: 32 }}>
                <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
                  No events yet. Events will appear here as they happen.
                </p>
              </div>
            ) : (
              <div className="grid" style={{ gap: 8 }}>
                {events.slice(0, 10).map((event) => (
                  <div key={event.id} className="card" style={{ padding: 12 }}>
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-sm">
                        <div 
                          className={`badge ${
                            event.type === 'face_recognized' ? 'success' : 
                            event.type === 'reminder_triggered' ? 'warning' : 
                            event.type === 'item_seen' ? 'info' : ''
                          }`}
                          style={{ textTransform: 'capitalize' }}
                        >
                          {event.type?.replace(/_/g, ' ') || "event"}
                        </div>
                      </div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {event.occurred_at ? new Date(event.occurred_at).toLocaleTimeString() : "—"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </main>
  );
}
