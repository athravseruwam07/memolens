"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { apiGet } from "../../../lib/api";
import { getPatientId, getToken } from "../../../lib/session";
import type { FamiliarPerson } from "../../../lib/types";

export default function PatientWhoPage() {
  const [people, setPeople] = useState<FamiliarPerson[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedPerson, setSelectedPerson] = useState<FamiliarPerson | null>(null);

  useEffect(() => {
    async function load() {
      const token = getToken();
      const patientId = getPatientId();
      if (!patientId) {
        setError("Please set up your Patient ID in Patient Home first");
        setLoading(false);
        return;
      }
      const res = await apiGet<FamiliarPerson[]>(`/patients/${patientId}/people/`, token || undefined);
      setError(res.error || null);
      setPeople(res.data || []);
      setLoading(false);
    }
    void load();
  }, []);

  return (
    <main>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <Link href="/home" className="btn ghost small" style={{ marginBottom: 16, padding: '8px 12px' }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          Back
        </Link>
        <h1 style={{ marginBottom: 8 }}>Who Is This?</h1>
        <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
          View your familiar people
        </p>
      </div>

      {/* Error */}
      {error && <div className="error-message">{error}</div>}

      {/* Loading */}
      {loading && (
        <div className="grid" style={{ gap: 12 }}>
          {[1, 2, 3].map((i) => (
            <div key={i} className="card" style={{ padding: 20 }}>
              <div className="flex items-center gap-md">
                <div className="skeleton" style={{ width: 64, height: 64, borderRadius: 'var(--radius-lg)' }} />
                <div style={{ flex: 1 }}>
                  <div className="skeleton" style={{ width: '60%', height: 20, marginBottom: 8 }} />
                  <div className="skeleton" style={{ width: '40%', height: 16 }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* People List */}
      {!loading && people.length > 0 && (
        <div className="grid" style={{ gap: 12 }}>
          {people.map((person) => (
            <button
              key={person.id}
              type="button"
              onClick={() => setSelectedPerson(person)}
              className="card"
              style={{ 
                padding: 20, 
                cursor: 'pointer', 
                textAlign: 'left',
                border: '1.5px solid var(--surface-border)',
                background: 'var(--bg-secondary)',
                width: '100%',
              }}
            >
              <div className="flex items-center gap-md">
                {/* Photo or Avatar */}
                <div 
                  style={{ 
                    width: 64, 
                    height: 64, 
                    borderRadius: 'var(--radius-lg)',
                    overflow: 'hidden',
                    flexShrink: 0,
                    background: 'var(--gradient-secondary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {person.photos && person.photos.length > 0 ? (
                    <img 
                      src={person.photos[0]} 
                      alt={person.name}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                  ) : (
                    <span style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--bg-primary)' }}>
                      {person.name.charAt(0).toUpperCase()}
                    </span>
                  )}
                </div>

                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: 4, color: 'var(--text-primary)' }}>
                    {person.name}
                  </div>
                  {person.relationship && (
                    <div className="flex items-center gap-sm" style={{ color: 'var(--accent-secondary)' }}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                      </svg>
                      <span>{person.relationship}</span>
                    </div>
                  )}
                </div>

                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </div>
            </button>
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
          <h3 style={{ marginBottom: 8, color: 'var(--text-secondary)' }}>No familiar people yet</h3>
          <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
            Your caregiver can add people you know to help identify them
          </p>
        </div>
      )}

      {/* Tip */}
      {!loading && people.length > 0 && (
        <div className="card" style={{ marginTop: 24, textAlign: 'center', background: 'var(--info-muted)', borderColor: 'rgba(59, 130, 246, 0.3)' }}>
          <div className="flex items-center justify-center gap-sm" style={{ color: 'var(--info)' }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="16" x2="12" y2="12"/>
              <line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
            <span style={{ fontSize: '0.875rem' }}>
              Tap on a person to see more details
            </span>
          </div>
        </div>
      )}

      {/* Person Detail Modal */}
      {selectedPerson && (
        <div className="modal-overlay" onClick={() => setSelectedPerson(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 400 }}>
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
              {/* Main photo */}
              {selectedPerson.photos && selectedPerson.photos.length > 0 && (
                <div style={{ marginBottom: 20 }}>
                  <img
                    src={selectedPerson.photos[0]}
                    alt={selectedPerson.name}
                    style={{
                      width: '100%',
                      aspectRatio: '1',
                      objectFit: 'cover',
                      borderRadius: 'var(--radius-lg)',
                    }}
                  />
                  
                  {/* Additional photos thumbnail strip */}
                  {selectedPerson.photos.length > 1 && (
                    <div 
                      className="flex gap-sm" 
                      style={{ 
                        marginTop: 8, 
                        overflowX: 'auto', 
                        paddingBottom: 4 
                      }}
                    >
                      {selectedPerson.photos.slice(1).map((photo, idx) => (
                        <img
                          key={idx}
                          src={photo}
                          alt={`${selectedPerson.name} photo ${idx + 2}`}
                          style={{
                            width: 60,
                            height: 60,
                            objectFit: 'cover',
                            borderRadius: 'var(--radius-md)',
                            flexShrink: 0,
                          }}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Info */}
              <div className="grid" style={{ gap: 16 }}>
                {selectedPerson.relationship && (
                  <div className="flex items-center gap-md" style={{ 
                    padding: 16, 
                    background: 'var(--surface)', 
                    borderRadius: 'var(--radius-lg)' 
                  }}>
                    <div style={{
                      width: 40,
                      height: 40,
                      borderRadius: 'var(--radius-full)',
                      background: 'var(--accent-secondary-muted)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}>
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-secondary)" strokeWidth="2">
                        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                      </svg>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 2 }}>
                        Relationship
                      </div>
                      <div style={{ fontWeight: 600, fontSize: '1.125rem' }}>
                        {selectedPerson.relationship}
                      </div>
                    </div>
                  </div>
                )}

                {selectedPerson.notes && (
                  <div style={{ 
                    padding: 16, 
                    background: 'var(--surface)', 
                    borderRadius: 'var(--radius-lg)' 
                  }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>
                      Notes
                    </div>
                    <div style={{ lineHeight: 1.6, color: 'var(--text-secondary)' }}>
                      {selectedPerson.notes}
                    </div>
                  </div>
                )}

                {selectedPerson.conversation_prompt && (
                  <div style={{ 
                    padding: 16, 
                    background: 'var(--accent-muted)', 
                    borderRadius: 'var(--radius-lg)',
                    borderLeft: '4px solid var(--accent)'
                  }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>
                      Conversation Tip
                    </div>
                    <div style={{ fontStyle: 'italic', color: 'var(--text-primary)' }}>
                      &ldquo;{selectedPerson.conversation_prompt}&rdquo;
                    </div>
                  </div>
                )}
              </div>
            </div>
            <div className="modal-footer">
              <button 
                type="button" 
                className="btn full-width"
                onClick={() => setSelectedPerson(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
