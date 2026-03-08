"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";

import { apiGet, apiPost, apiDelete } from "../../../../lib/api";
import { getToken, setPatientId } from "../../../../lib/session";
import type { Reminder } from "../../../../lib/types";


const REMINDER_TYPES = [
  { value: 'time', label: 'Time-based', icon: '⏰', description: 'Triggers at specific times' },
  { value: 'person', label: 'Person-based', icon: '👤', description: 'Triggers when person is seen' },
  { value: 'location', label: 'Location-based', icon: '📍', description: 'Triggers at certain locations' },
  { value: 'object', label: 'Object-based', icon: '📦', description: 'Triggers when object is detected' },
];

const DAYS_OF_WEEK = [
  { value: 'mon', label: 'Mon' },
  { value: 'tue', label: 'Tue' },
  { value: 'wed', label: 'Wed' },
  { value: 'thu', label: 'Thu' },
  { value: 'fri', label: 'Fri' },
  { value: 'sat', label: 'Sat' },
  { value: 'sun', label: 'Sun' },
];

const COMMON_ROOMS = ['Living Room', 'Kitchen', 'Bedroom', 'Bathroom', 'Front Door', 'Garage'];

export default function RemindersPage({ params }: { params: { patientId: string } }) {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [type, setType] = useState("time");
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Time-based settings
  const [triggerTime, setTriggerTime] = useState("09:00");
  const [selectedDays, setSelectedDays] = useState<string[]>([]);
  const [repeatDaily, setRepeatDaily] = useState(true);

  // Person-based settings
  const [personName, setPersonName] = useState("");

  // Location-based settings
  const [roomName, setRoomName] = useState("");

  // Object-based settings
  const [objectName, setObjectName] = useState("");

  async function load() {
    const token = getToken();
    if (!token) {
      setError("Please login to access this page");
      setLoading(false);
      return;
    }
    const res = await apiGet<Reminder[]>(`/patients/${params.patientId}/reminders/`, token);
    setError(res.error || null);
    setReminders(res.data || []);
    setLoading(false);
  }

  useEffect(() => {
    setPatientId(params.patientId);
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.patientId]);

  function buildTriggerMeta(): Record<string, unknown> {
    switch (type) {
      case 'time':
        return {
          time: triggerTime,
          days: repeatDaily ? ['daily'] : selectedDays,
        };
      case 'person':
        return { person_name: personName };
      case 'location':
        return { room: roomName };
      case 'object':
        return { object: objectName };
      default:
        return {};
    }
  }

  function formatTriggerMeta(r: Reminder): string {
    const meta = r.trigger_meta;
    if (!meta) return '';
    
    switch (r.type) {
      case 'time':
        const time = meta.time as string;
        const days = meta.days as string[] | undefined;
        if (days?.includes('daily')) return `Daily at ${time}`;
        if (days?.length) return `${days.map(d => d.charAt(0).toUpperCase() + d.slice(1)).join(', ')} at ${time}`;
        return `At ${time}`;
      case 'person':
        return `When ${meta.person_name} is seen`;
      case 'location':
        return `In ${meta.room}`;
      case 'object':
        return `When ${meta.object} is detected`;
      default:
        return JSON.stringify(meta);
    }
  }

  async function createReminder(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token) return;

    const triggerMeta = buildTriggerMeta();

    setSubmitting(true);
    const res = await apiPost<Reminder>(
      `/patients/${params.patientId}/reminders/`,
      { type, trigger_meta: triggerMeta, message, active: true },
      token
    );
    if (res.error) {
      setError(res.error);
      setSubmitting(false);
      return;
    }

    // Reset form
    setMessage("");
    setTriggerTime("09:00");
    setSelectedDays([]);
    setRepeatDaily(true);
    setPersonName("");
    setRoomName("");
    setObjectName("");
    setShowForm(false);
    setSubmitting(false);
    await load();
  }

  async function deleteReminder(reminderId: string) {
    const token = getToken();
    if (!token) return;

    setDeletingId(reminderId);
    const res = await apiDelete(`/patients/${params.patientId}/reminders/${reminderId}`, token);
    if (res.error) {
      setError(res.error);
    } else {
      setReminders(reminders.filter(r => r.id !== reminderId));
    }
    setDeletingId(null);
  }

  function toggleDay(day: string) {
    if (selectedDays.includes(day)) {
      setSelectedDays(selectedDays.filter(d => d !== day));
    } else {
      setSelectedDays([...selectedDays, day]);
    }
  }

  return (
    <main>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Link href="/dashboard" className="btn ghost small" style={{ marginBottom: 16, padding: '8px 12px' }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          Dashboard
        </Link>
        <div className="flex justify-between items-center">
          <div>
            <h1 style={{ marginBottom: 4 }}>Reminders</h1>
            <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
              Set up alerts for the patient
            </p>
          </div>
          <button 
            className={`btn ${showForm ? 'secondary' : ''}`}
            onClick={() => setShowForm(!showForm)}
          >
            {showForm ? 'Cancel' : 'Add Reminder'}
          </button>
        </div>
      </div>

      {/* Add Form */}
      {showForm && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 16 }}>Create Reminder</h3>
          <form className="grid" style={{ gap: 20 }} onSubmit={createReminder}>
            {/* Reminder Type Selection */}
            <div>
              <label style={{ display: 'block', marginBottom: 10, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                Reminder Type
              </label>
              <div className="grid grid-2" style={{ gap: 10 }}>
                {REMINDER_TYPES.map((t) => (
                  <button
                    key={t.value}
                    type="button"
                    onClick={() => setType(t.value)}
                    style={{
                      cursor: 'pointer',
                      textAlign: 'left',
                      padding: 14,
                      borderRadius: 'var(--radius-lg)',
                      border: type === t.value ? '2px solid var(--accent)' : '1.5px solid var(--surface-border)',
                      background: type === t.value ? 'var(--accent-muted)' : 'var(--surface)',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    <div style={{ fontSize: '1.25rem', marginBottom: 6 }}>{t.icon}</div>
                    <div style={{ fontWeight: 600, color: type === t.value ? 'var(--accent)' : 'var(--text-primary)', fontSize: '0.9rem' }}>
                      {t.label}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>
                      {t.description}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Time-based settings */}
            {type === 'time' && (
              <div className="grid" style={{ gap: 16 }}>
                <div>
                  <label style={{ display: 'block', marginBottom: 8, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    Time
                  </label>
                  <input
                    type="time"
                    value={triggerTime}
                    onChange={(e) => setTriggerTime(e.target.value)}
                    required
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: 8, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    Repeat
                  </label>
                  <div className="flex items-center gap-md" style={{ marginBottom: 12 }}>
                    <button
                      type="button"
                      onClick={() => setRepeatDaily(true)}
                      style={{
                        padding: '10px 20px',
                        borderRadius: 'var(--radius-lg)',
                        border: repeatDaily ? '2px solid var(--accent)' : '1.5px solid var(--surface-border)',
                        background: repeatDaily ? 'var(--accent-muted)' : 'var(--surface)',
                        color: repeatDaily ? 'var(--accent)' : 'var(--text-secondary)',
                        fontWeight: 500,
                        cursor: 'pointer',
                      }}
                    >
                      Daily
                    </button>
                    <button
                      type="button"
                      onClick={() => setRepeatDaily(false)}
                      style={{
                        padding: '10px 20px',
                        borderRadius: 'var(--radius-lg)',
                        border: !repeatDaily ? '2px solid var(--accent)' : '1.5px solid var(--surface-border)',
                        background: !repeatDaily ? 'var(--accent-muted)' : 'var(--surface)',
                        color: !repeatDaily ? 'var(--accent)' : 'var(--text-secondary)',
                        fontWeight: 500,
                        cursor: 'pointer',
                      }}
                    >
                      Specific Days
                    </button>
                  </div>
                  {!repeatDaily && (
                    <div className="flex flex-wrap gap-sm">
                      {DAYS_OF_WEEK.map((day) => (
                        <button
                          key={day.value}
                          type="button"
                          onClick={() => toggleDay(day.value)}
                          style={{
                            padding: '8px 14px',
                            borderRadius: 'var(--radius-md)',
                            border: selectedDays.includes(day.value) ? '2px solid var(--accent)' : '1.5px solid var(--surface-border)',
                            background: selectedDays.includes(day.value) ? 'var(--accent)' : 'var(--surface)',
                            color: selectedDays.includes(day.value) ? 'var(--bg-primary)' : 'var(--text-secondary)',
                            fontWeight: 500,
                            cursor: 'pointer',
                            fontSize: '0.875rem',
                          }}
                        >
                          {day.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Person-based settings */}
            {type === 'person' && (
              <div>
                <label style={{ display: 'block', marginBottom: 8, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                  Person Name
                </label>
                <input
                  type="text"
                  placeholder="e.g., Sarah, Dr. Smith"
                  value={personName}
                  onChange={(e) => setPersonName(e.target.value)}
                  required
                />
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 8 }}>
                  Reminder will trigger when this person is recognized
                </p>
              </div>
            )}

            {/* Location-based settings */}
            {type === 'location' && (
              <div>
                <label style={{ display: 'block', marginBottom: 8, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                  Room/Location
                </label>
                <input
                  type="text"
                  placeholder="e.g., Kitchen, Front Door"
                  value={roomName}
                  onChange={(e) => setRoomName(e.target.value)}
                  required
                  list="common-rooms"
                />
                <datalist id="common-rooms">
                  {COMMON_ROOMS.map(room => (
                    <option key={room} value={room} />
                  ))}
                </datalist>
                <div className="flex flex-wrap gap-sm" style={{ marginTop: 10 }}>
                  {COMMON_ROOMS.map(room => (
                    <button
                      key={room}
                      type="button"
                      onClick={() => setRoomName(room)}
                      style={{
                        padding: '6px 12px',
                        borderRadius: 'var(--radius-md)',
                        border: roomName === room ? '2px solid var(--accent)' : '1px solid var(--surface-border)',
                        background: roomName === room ? 'var(--accent-muted)' : 'transparent',
                        color: roomName === room ? 'var(--accent)' : 'var(--text-muted)',
                        fontSize: '0.75rem',
                        cursor: 'pointer',
                      }}
                    >
                      {room}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Object-based settings */}
            {type === 'object' && (
              <div>
                <label style={{ display: 'block', marginBottom: 8, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                  Object Name
                </label>
                <input
                  type="text"
                  placeholder="e.g., Keys, Wallet, Medication"
                  value={objectName}
                  onChange={(e) => setObjectName(e.target.value)}
                  required
                />
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 8 }}>
                  Reminder will trigger when this object is detected
                </p>
              </div>
            )}

            {/* Message */}
            <div>
              <label style={{ display: 'block', marginBottom: 8, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                Reminder Message *
              </label>
              <input
                placeholder="e.g., Take your morning medication"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                required
              />
            </div>

            <button className="btn full-width" type="submit" disabled={submitting}>
              {submitting ? (
                <>
                  <div className="spinner" style={{ width: 18, height: 18 }} />
                  Creating...
                </>
              ) : (
                'Create Reminder'
              )}
            </button>
          </form>
        </div>
      )}

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
        <div className="grid" style={{ gap: 12 }}>
          {[1, 2, 3].map((i) => (
            <div key={i} className="card">
              <div className="skeleton" style={{ width: '70%', height: 18, marginBottom: 8 }} />
              <div className="skeleton" style={{ width: '40%', height: 14 }} />
            </div>
          ))}
        </div>
      )}

      {/* Reminders List */}
      {!loading && reminders.length > 0 && (
        <div className="grid" style={{ gap: 12 }}>
          {reminders.map((r) => {
            const typeInfo = REMINDER_TYPES.find(t => t.value === r.type);
            return (
              <div 
                key={r.id} 
                className="card"
                style={{ 
                  borderLeft: r.active ? '4px solid var(--accent)' : '4px solid var(--text-muted)',
                  opacity: r.active ? 1 : 0.6
                }}
              >
                <div className="flex justify-between items-start gap-md">
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: 8 }}>
                      {r.message}
                    </div>
                    <div className="flex items-center gap-sm" style={{ flexWrap: 'wrap' }}>
                      <span style={{ fontSize: '1rem' }}>{typeInfo?.icon}</span>
                      <span style={{ fontSize: '0.875rem', color: 'var(--text-tertiary)' }}>
                        {formatTriggerMeta(r)}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-sm">
                    <div className={`badge ${r.active ? 'success' : ''}`}>
                      {r.active ? 'Active' : 'Inactive'}
                    </div>
                    <button
                      type="button"
                      onClick={() => deleteReminder(r.id)}
                      disabled={deletingId === r.id}
                      className="btn ghost small"
                      style={{ padding: 8, color: 'var(--error)' }}
                    >
                      {deletingId === r.id ? (
                        <div className="spinner" style={{ width: 18, height: 18 }} />
                      ) : (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polyline points="3 6 5 6 21 6"/>
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Empty State */}
      {!loading && reminders.length === 0 && !error && (
        <div className="card text-center" style={{ padding: 48 }}>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" style={{ margin: '0 auto 16px' }}>
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
          </svg>
          <h3 style={{ marginBottom: 8, color: 'var(--text-secondary)' }}>No reminders yet</h3>
          <p style={{ color: 'var(--text-tertiary)', margin: 0, marginBottom: 16 }}>
            Create reminders to help the patient stay on track
          </p>
          <button className="btn" onClick={() => setShowForm(true)}>
            Create First Reminder
          </button>
        </div>
      )}
    </main>
  );
}
