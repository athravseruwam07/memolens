"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { apiGet } from "../../../../lib/api";
import { getToken, setPatientId } from "../../../../lib/session";
import type { CaregiverLink, Patient } from "../../../../lib/types";

export default function PatientDetailPage({ params }: { params: { id: string } }) {
  const [patient, setPatient] = useState<Patient | null>(null);
  const [caregivers, setCaregivers] = useState<CaregiverLink[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const token = getToken();
      if (!token) {
        setError("Please login to access this page");
        setLoading(false);
        return;
      }
      const p = await apiGet<Patient>(`/patients/${params.id}`, token);
      const c = await apiGet<CaregiverLink[]>(`/patients/${params.id}/caregivers`, token);
      setError(p.error || c.error || null);
      setPatient(p.data || null);
      setCaregivers(c.data || []);
      setPatientId(params.id);
      setLoading(false);
    }
    void load();
  }, [params.id]);

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
        <h1 style={{ marginBottom: 4 }}>Patient Details</h1>
        <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
          View and manage patient information
        </p>
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
        <div className="grid" style={{ gap: 16 }}>
          <div className="card">
            <div className="skeleton" style={{ width: '50%', height: 24, marginBottom: 12 }} />
            <div className="skeleton" style={{ width: '30%', height: 16 }} />
          </div>
        </div>
      )}

      {/* Patient Info */}
      {!loading && patient && (
        <>
          <div className="card" style={{ marginBottom: 24 }}>
            <div className="flex items-center gap-lg" style={{ marginBottom: 20 }}>
              <div 
                style={{ 
                  width: 64, 
                  height: 64, 
                  borderRadius: '50%',
                  background: 'var(--gradient-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '1.75rem',
                  fontWeight: 600,
                  color: 'var(--bg-primary)',
                  flexShrink: 0
                }}
              >
                {patient.name?.charAt(0).toUpperCase() || 'P'}
              </div>
              <div>
                <h2 style={{ margin: 0, marginBottom: 4 }}>{patient.name}</h2>
                <div style={{ color: 'var(--text-tertiary)', fontSize: '0.875rem' }}>
                  Patient ID: {params.id.slice(0, 8)}...
                </div>
              </div>
            </div>

            <div className="divider" style={{ margin: '16px 0' }} />

            <div className="grid" style={{ gap: 16 }}>
              <div>
                <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: 4 }}>Age</div>
                <div style={{ fontWeight: 600 }}>{patient.age ?? "Not specified"}</div>
              </div>
              <div>
                <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: 4 }}>Tracked Items</div>
                <div className="flex flex-wrap gap-sm">
                  {(patient.tracked_items || []).length > 0 ? (
                    patient.tracked_items?.map((item) => (
                      <span key={item} className="badge info" style={{ textTransform: 'capitalize' }}>
                        {item}
                      </span>
                    ))
                  ) : (
                    <span style={{ color: 'var(--text-tertiary)' }}>No items configured</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Caregivers */}
          <div style={{ marginBottom: 24 }}>
            <h2 style={{ marginBottom: 12 }}>Assigned Caregivers</h2>
            {caregivers.length > 0 ? (
              <div className="grid" style={{ gap: 12 }}>
                {caregivers.map((c) => (
                  <div key={c.caregiver_id} className="card">
                    <div className="flex items-center gap-md">
                      <div 
                        style={{ 
                          width: 40, 
                          height: 40, 
                          borderRadius: '50%',
                          background: 'var(--accent-secondary-muted)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: 'var(--accent-secondary)',
                          fontWeight: 600,
                          flexShrink: 0
                        }}
                      >
                        {(c.caregiver_name || c.caregiver_email || 'C').charAt(0).toUpperCase()}
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600 }}>
                          {c.caregiver_name || c.caregiver_email || c.caregiver_id.slice(0, 8)}
                        </div>
                        <div style={{ fontSize: '0.875rem', color: 'var(--text-tertiary)' }}>
                          {c.role || 'Caregiver'}
                        </div>
                      </div>
                      <div className="badge success">Active</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="card text-center" style={{ padding: 32 }}>
                <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
                  No caregivers assigned yet
                </p>
              </div>
            )}
          </div>

          {/* Quick Actions */}
          <div>
            <h2 style={{ marginBottom: 12 }}>Quick Actions</h2>
            <div className="grid" style={{ gap: 10 }}>
              <Link href={`/people/${params.id}`} className="action-item">
                <div className="icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                    <circle cx="9" cy="7" r="4"/>
                  </svg>
                </div>
                <div className="content">
                  <div className="title">Manage Familiar People</div>
                  <div className="subtitle">Add faces for recognition</div>
                </div>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </Link>

              <Link href={`/reminders/${params.id}`} className="action-item">
                <div className="icon" style={{ background: 'var(--warning-muted)', color: 'var(--warning)' }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
                    <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
                  </svg>
                </div>
                <div className="content">
                  <div className="title">Manage Reminders</div>
                  <div className="subtitle">Set up alerts and notifications</div>
                </div>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </Link>
            </div>
          </div>
        </>
      )}
    </main>
  );
}
