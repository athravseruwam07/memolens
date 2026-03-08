"use client";

import Link from "next/link";

export default function NewPersonPage({ params }: { params: { patientId: string } }) {
  return (
    <main>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Link href={`/people/${params.patientId}`} className="btn ghost small" style={{ marginBottom: 16, padding: '8px 12px' }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          Back
        </Link>
        <h1 style={{ marginBottom: 4 }}>Add Familiar Person</h1>
        <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
          Add a new person for face recognition
        </p>
      </div>

      <div className="card text-center" style={{ padding: 48 }}>
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" style={{ margin: '0 auto 16px' }}>
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
          <circle cx="9" cy="7" r="4"/>
          <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
        </svg>
        <h3 style={{ marginBottom: 12, color: 'var(--text-secondary)' }}>Use Main Form</h3>
        <p style={{ color: 'var(--text-tertiary)', marginBottom: 16 }}>
          Please use the form on the Familiar People page to add new people
        </p>
        <Link href={`/people/${params.patientId}`} className="btn">
          Go to Familiar People
        </Link>
      </div>
    </main>
  );
}
