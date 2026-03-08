"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";

import { apiPost } from "../../../lib/api";
import { getPatientId, getToken } from "../../../lib/session";
import type { QueryResult } from "../../../lib/types";

const QUICK_QUERIES = [
  { icon: "🔑", label: "Keys", query: "Where are my keys?" },
  { icon: "📱", label: "Phone", query: "Where is my phone?" },
  { icon: "👓", label: "Glasses", query: "Where are my glasses?" },
  { icon: "👛", label: "Wallet", query: "Where is my wallet?" },
  { icon: "💊", label: "Medication", query: "Where is my medication?" },
  { icon: "📺", label: "Remote", query: "Where is the remote?" },
];

export default function PatientQueryPage() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submitQuery(queryText: string) {
    const token = getToken();
    const patientId = getPatientId();
    if (!patientId) {
      setError("Please set up your Patient ID in Patient Home first");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const res = await apiPost<QueryResult>("/query", { patient_id: patientId, question: queryText }, token || undefined);
    setError(res.error || null);
    setResult(res.data || null);
    setLoading(false);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    await submitQuery(question);
  }

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
        <h1 style={{ marginBottom: 8 }}>Find My Things</h1>
        <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
          Ask where you left your belongings
        </p>
      </div>

      {/* Search Form */}
      <form onSubmit={onSubmit} style={{ marginBottom: 24 }}>
        <div style={{ position: 'relative' }}>
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Where are my keys?"
            style={{ 
              paddingRight: 56,
              fontSize: '1.125rem',
              minHeight: 56
            }}
          />
          <button 
            type="submit" 
            className="btn-icon primary"
            disabled={loading || !question.trim()}
            style={{ 
              position: 'absolute', 
              right: 4, 
              top: '50%', 
              transform: 'translateY(-50%)',
              width: 44,
              height: 44
            }}
          >
            {loading ? (
              <div className="spinner" style={{ width: 20, height: 20, borderTopColor: 'var(--bg-primary)' }} />
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
            )}
          </button>
        </div>
      </form>

      {/* Quick Query Buttons */}
      <div style={{ marginBottom: 32 }}>
        <h3 style={{ marginBottom: 12, fontSize: '0.875rem', color: 'var(--text-tertiary)' }}>
          Quick search
        </h3>
        <div className="flex flex-wrap gap-sm">
          {QUICK_QUERIES.map((q) => (
            <button
              key={q.query}
              type="button"
              onClick={() => {
                setQuestion(q.query);
                void submitQuery(q.query);
              }}
              className="btn secondary small"
              disabled={loading}
              style={{ 
                padding: '8px 14px',
                minHeight: 40
              }}
            >
              <span>{q.icon}</span>
              {q.label}
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && <div className="error-message">{error}</div>}

      {/* Result */}
      {result && (
        <div className="card" style={{ borderLeft: '4px solid var(--accent)' }}>
          <div className="badge success" style={{ marginBottom: 12 }}>
            {result.answer_type === 'item_location' ? 'Found' : result.answer_type}
          </div>
          
          {result.answer_type === 'item_location' && Array.isArray(result.results) && result.results.length > 0 ? (
            <div className="grid" style={{ gap: 16 }}>
              {result.results.map((item: { item?: string; room?: string; last_seen_at?: string }, idx: number) => (
                <div key={idx}>
                  <div style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: 4 }}>
                    {item.item || 'Item'}
                  </div>
                  <div className="flex items-center gap-sm" style={{ color: 'var(--text-secondary)' }}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                      <circle cx="12" cy="10" r="3"/>
                    </svg>
                    <span>Last seen in <strong style={{ color: 'var(--accent)' }}>{item.room || 'unknown location'}</strong></span>
                  </div>
                  {item.last_seen_at && (
                    <div style={{ fontSize: '0.875rem', color: 'var(--text-tertiary)', marginTop: 8 }}>
                      {formatTimeAgo(item.last_seen_at)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : result.answer_type === 'item_location' ? (
            <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
              I couldn&apos;t find that item in my records. Try asking about a different item.
            </p>
          ) : (
            <pre style={{ 
              whiteSpace: 'pre-wrap', 
              margin: 0,
              fontSize: '0.875rem'
            }}>
              {JSON.stringify(result.results, null, 2)}
            </pre>
          )}
        </div>
      )}

      {/* Empty state */}
      {!result && !error && !loading && (
        <div className="card text-center" style={{ padding: 40 }}>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" style={{ margin: '0 auto 16px' }}>
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
            Ask a question or tap a quick search button above
          </p>
        </div>
      )}
    </main>
  );
}

function formatTimeAgo(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
  } catch {
    return timestamp;
  }
}
