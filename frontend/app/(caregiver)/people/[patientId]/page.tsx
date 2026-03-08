"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";

import { apiGet, apiPost, apiDelete } from "../../../../lib/api";
import { getToken, setPatientId } from "../../../../lib/session";
import type { FamiliarPerson } from "../../../../lib/types";

export default function PeoplePage({ params }: { params: { patientId: string } }) {
  const [people, setPeople] = useState<FamiliarPerson[]>([]);
  const [name, setName] = useState("");
  const [relationship, setRelationship] = useState("");
  const [photos, setPhotos] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [selectedPerson, setSelectedPerson] = useState<FamiliarPerson | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function load() {
    const token = getToken();
    if (!token) {
      setError("Please login to access this page");
      setLoading(false);
      return;
    }
    const res = await apiGet<FamiliarPerson[]>(`/patients/${params.patientId}/people/`, token);
    setError(res.error || null);
    setPeople(res.data || []);
    setLoading(false);
  }

  useEffect(() => {
    setPatientId(params.patientId);
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.patientId]);

  async function addPerson(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token) return;

    const fd = new FormData();
    fd.append("name", name);
    if (relationship) fd.append("relationship", relationship);
    if (photos.length === 0) {
      setError("Please upload at least one face photo.");
      return;
    }
    for (const photo of photos) {
      fd.append("photos", photo);
    }

    setSubmitting(true);
    const res = await apiPost<FamiliarPerson>(`/patients/${params.patientId}/people/`, fd, token);
    if (res.error) {
      setError(res.error);
      setSubmitting(false);
      return;
    }
    setName("");
    setRelationship("");
    setPhotos([]);
    setError(null);
    setShowForm(false);
    setSubmitting(false);
    await load();
  }

  async function deletePerson(personId: string) {
    const token = getToken();
    if (!token) return;

    setDeletingId(personId);
    const res = await apiDelete(`/patients/${params.patientId}/people/${personId}`, token);
    if (res.error) {
      setError(res.error);
    } else {
      setPeople(people.filter(p => p.id !== personId));
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
        <div className="flex justify-between items-center">
          <div>
            <h1 style={{ marginBottom: 4 }}>Familiar People</h1>
            <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
              Manage people for face recognition
            </p>
          </div>
          <button 
            className={`btn ${showForm ? 'secondary' : ''}`}
            onClick={() => setShowForm(!showForm)}
          >
            {showForm ? 'Cancel' : 'Add Person'}
          </button>
        </div>
      </div>

      {/* Add Form */}
      {showForm && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 16 }}>Add New Person</h3>
          <form className="grid" style={{ gap: 16 }} onSubmit={addPerson}>
            <div>
              <label style={{ display: 'block', marginBottom: 8, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                Name *
              </label>
              <input
                placeholder="e.g., Sarah Johnson"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: 8, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                Relationship
              </label>
              <input
                placeholder="e.g., Daughter, Friend, Doctor"
                value={relationship}
                onChange={(e) => setRelationship(e.target.value)}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: 8, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                Face Photos *
              </label>
              <input
                type="file"
                accept="image/*"
                multiple
                onChange={(e) => setPhotos(Array.from(e.target.files || []))}
                required
              />
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 8 }}>
                Upload clear photos of the person&apos;s face for best recognition
              </p>
            </div>
            <button className="btn full-width" type="submit" disabled={submitting}>
              {submitting ? (
                <>
                  <div className="spinner" style={{ width: 18, height: 18 }} />
                  Adding...
                </>
              ) : (
                'Add Person'
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
              <div className="flex items-center gap-md">
                <div className="skeleton" style={{ width: 64, height: 64, borderRadius: 'var(--radius-lg)' }} />
                <div style={{ flex: 1 }}>
                  <div className="skeleton" style={{ width: '50%', height: 18, marginBottom: 8 }} />
                  <div className="skeleton" style={{ width: '30%', height: 14 }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* People List */}
      {!loading && people.length > 0 && (
        <div className="grid" style={{ gap: 12 }}>
          {people.map((p) => (
            <div key={p.id} className="card">
              <div className="flex items-center gap-md">
                {/* Photo thumbnail - clickable */}
                <button
                  type="button"
                  onClick={() => setSelectedPerson(p)}
                  style={{ 
                    width: 64, 
                    height: 64, 
                    borderRadius: 'var(--radius-lg)',
                    overflow: 'hidden',
                    flexShrink: 0,
                    border: 'none',
                    padding: 0,
                    cursor: 'pointer',
                    background: 'var(--gradient-secondary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {p.photos && p.photos.length > 0 ? (
                    <img 
                      src={p.photos[0]} 
                      alt={p.name}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                  ) : (
                    <span style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--bg-primary)' }}>
                      {p.name.charAt(0).toUpperCase()}
                    </span>
                  )}
                </button>

                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600 }}>{p.name}</div>
                  {p.relationship && (
                    <div style={{ fontSize: '0.875rem', color: 'var(--text-tertiary)' }}>
                      {p.relationship}
                    </div>
                  )}
                  {p.photos && p.photos.length > 0 && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                      {p.photos.length} photo{p.photos.length !== 1 ? 's' : ''}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-sm">
                  <button
                    type="button"
                    onClick={() => setSelectedPerson(p)}
                    className="btn ghost small"
                    style={{ padding: 8 }}
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10"/>
                      <line x1="12" y1="16" x2="12" y2="12"/>
                      <line x1="12" y1="8" x2="12.01" y2="8"/>
                    </svg>
                  </button>
                  <button
                    type="button"
                    onClick={() => deletePerson(p.id)}
                    disabled={deletingId === p.id}
                    className="btn ghost small"
                    style={{ padding: 8, color: 'var(--error)' }}
                  >
                    {deletingId === p.id ? (
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
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && people.length === 0 && !error && (
        <div className="card text-center" style={{ padding: 48 }}>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" style={{ margin: '0 auto 16px' }}>
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
          </svg>
          <h3 style={{ marginBottom: 8, color: 'var(--text-secondary)' }}>No people added yet</h3>
          <p style={{ color: 'var(--text-tertiary)', margin: 0, marginBottom: 16 }}>
            Add familiar people so the system can recognize and announce them
          </p>
          <button className="btn" onClick={() => setShowForm(true)}>
            Add First Person
          </button>
        </div>
      )}

      {/* Person Detail Modal */}
      {selectedPerson && (
        <div className="modal-overlay" onClick={() => setSelectedPerson(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{selectedPerson.name}</h3>
              <button 
                type="button" 
                className="modal-close"
                onClick={() => setSelectedPerson(null)}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
            <div className="modal-body">
              {/* Photos gallery */}
              {selectedPerson.photos && selectedPerson.photos.length > 0 && (
                <div style={{ marginBottom: 20 }}>
                  <div 
                    style={{ 
                      display: 'grid', 
                      gridTemplateColumns: selectedPerson.photos.length === 1 ? '1fr' : 'repeat(2, 1fr)',
                      gap: 8 
                    }}
                  >
                    {selectedPerson.photos.map((photo, idx) => (
                      <img
                        key={idx}
                        src={photo}
                        alt={`${selectedPerson.name} photo ${idx + 1}`}
                        style={{
                          width: '100%',
                          aspectRatio: '1',
                          objectFit: 'cover',
                          borderRadius: 'var(--radius-md)',
                        }}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Info */}
              <div className="grid" style={{ gap: 12 }}>
                {selectedPerson.relationship && (
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase' }}>
                      Relationship
                    </div>
                    <div style={{ fontWeight: 500 }}>{selectedPerson.relationship}</div>
                  </div>
                )}
                {selectedPerson.notes && (
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase' }}>
                      Notes
                    </div>
                    <div>{selectedPerson.notes}</div>
                  </div>
                )}
                {selectedPerson.conversation_prompt && (
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase' }}>
                      Conversation Prompt
                    </div>
                    <div style={{ fontStyle: 'italic', color: 'var(--text-secondary)' }}>
                      &ldquo;{selectedPerson.conversation_prompt}&rdquo;
                    </div>
                  </div>
                )}
              </div>
            </div>
            <div className="modal-footer">
              <button 
                type="button" 
                className="btn secondary"
                onClick={() => setSelectedPerson(null)}
              >
                Close
              </button>
              <button
                type="button"
                className="btn danger"
                onClick={() => {
                  deletePerson(selectedPerson.id);
                  setSelectedPerson(null);
                }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
