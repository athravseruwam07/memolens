"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";

import { apiGet, apiPost, apiDelete } from "../../../../lib/api";
import { getToken, setPatientId } from "../../../../lib/session";
import type { DailyNote } from "../../../../lib/types";

export default function NotesPage({ params }: { params: { patientId: string } }) {
  const [notes, setNotes] = useState<DailyNote[]>([]);
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function load() {
    const token = getToken();
    if (!token) {
      setError("Please login to access this page");
      setLoading(false);
      return;
    }
    const res = await apiGet<DailyNote[]>(`/patients/${params.patientId}/daily-notes/`, token);
    setError(res.error || null);
    setNotes(res.data || []);
    setLoading(false);
  }

  useEffect(() => {
    setPatientId(params.patientId);
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.patientId]);

  async function addNote(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token) return;

    setSubmitting(true);
    const res = await apiPost<DailyNote>(`/patients/${params.patientId}/daily-notes/`, { content }, token);
    if (res.error) {
      setError(res.error);
      setSubmitting(false);
      return;
    }

    setContent("");
    setSubmitting(false);
    await load();
  }

  async function deleteNote(noteId: string) {
    const token = getToken();
    if (!token) return;

    setDeletingId(noteId);
    const res = await apiDelete(`/patients/${params.patientId}/daily-notes/${noteId}`, token);
    if (res.error) {
      setError(res.error);
    } else {
      setNotes(notes.filter(n => n.id !== noteId));
    }
    setDeletingId(null);
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
        <h1 style={{ marginBottom: 4 }}>Daily Notes</h1>
        <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
          Log important information for the patient
        </p>
      </div>

      {/* Add Note Form */}
      <div className="card" style={{ marginBottom: 24 }}>
        <form onSubmit={addNote}>
          <textarea
            rows={3}
            placeholder="Write a note about today... (e.g., 'Had a good day, went for a walk in the garden')"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            required
            style={{ marginBottom: 12 }}
          />
          <button className="btn full-width" type="submit" disabled={submitting || !content.trim()}>
            {submitting ? (
              <>
                <div className="spinner" style={{ width: 18, height: 18 }} />
                Adding...
              </>
            ) : (
              <>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="12" y1="5" x2="12" y2="19"/>
                  <line x1="5" y1="12" x2="19" y2="12"/>
                </svg>
                Add Note
              </>
            )}
          </button>
        </form>
      </div>

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
              <div className="skeleton" style={{ width: '100%', height: 48, marginBottom: 8 }} />
              <div className="skeleton" style={{ width: '30%', height: 14 }} />
            </div>
          ))}
        </div>
      )}

      {/* Notes List */}
      {!loading && notes.length > 0 && (
        <div className="grid" style={{ gap: 12 }}>
          {notes.map((n) => (
            <div key={n.id} className="card">
              <div className="flex justify-between items-start gap-md">
                <div style={{ flex: 1 }}>
                  <div style={{ marginBottom: 12, lineHeight: 1.6 }}>
                    {n.content}
                  </div>
                  <div className="flex items-center gap-sm" style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                      <line x1="16" y1="2" x2="16" y2="6"/>
                      <line x1="8" y1="2" x2="8" y2="6"/>
                      <line x1="3" y1="10" x2="21" y2="10"/>
                    </svg>
                    <span>{n.note_date}</span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => deleteNote(n.id)}
                  disabled={deletingId === n.id}
                  className="btn ghost small"
                  style={{ padding: 8, color: 'var(--error)', flexShrink: 0 }}
                >
                  {deletingId === n.id ? (
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
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && notes.length === 0 && !error && (
        <div className="card text-center" style={{ padding: 48 }}>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" style={{ margin: '0 auto 16px' }}>
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
          <h3 style={{ marginBottom: 8, color: 'var(--text-secondary)' }}>No notes yet</h3>
          <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
            Start logging daily notes to track important information
          </p>
        </div>
      )}
    </main>
  );
}
