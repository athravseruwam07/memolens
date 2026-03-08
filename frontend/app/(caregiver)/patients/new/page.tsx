"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { apiPost } from "../../../../lib/api";
import { getToken, setPatientId } from "../../../../lib/session";
import type { Patient } from "../../../../lib/types";

const COMMON_ITEMS = [
  { label: 'Keys', value: 'keys' },
  { label: 'Phone', value: 'phone' },
  { label: 'Wallet', value: 'wallet' },
  { label: 'Glasses', value: 'glasses' },
  { label: 'Medication', value: 'medication' },
  { label: 'Remote', value: 'remote' },
  { label: 'Watch', value: 'watch' },
  { label: 'Hearing Aid', value: 'hearing aid' },
];

export default function NewPatientPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [selectedItems, setSelectedItems] = useState<string[]>(['keys', 'phone', 'wallet']);
  const [customItems, setCustomItems] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function toggleItem(item: string) {
    setSelectedItems(prev => 
      prev.includes(item) 
        ? prev.filter(i => i !== item)
        : [...prev, item]
    );
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token) {
      setError("Please login to access this page");
      return;
    }

    const customItemsList = customItems
      .split(',')
      .map(s => s.trim().toLowerCase())
      .filter(Boolean);

    const allItems = [...new Set([...selectedItems, ...customItemsList])];

    const payload = {
      name,
      age: age ? Number(age) : null,
      tracked_items: allItems
    };

    setLoading(true);
    const res = await apiPost<Patient>("/patients/", payload, token);
    if (res.error) {
      setError(res.error);
      setLoading(false);
      return;
    }

    setPatientId(res.data.id);
    router.push(`/patients/${res.data.id}`);
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
        <h1 style={{ marginBottom: 4 }}>Create Patient</h1>
        <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
          Set up a new patient profile
        </p>
      </div>

      <form className="grid" style={{ gap: 24 }} onSubmit={onSubmit}>
        {/* Basic Info */}
        <div className="card">
          <h3 style={{ marginBottom: 16 }}>Basic Information</h3>
          <div className="grid" style={{ gap: 16 }}>
            <div>
              <label style={{ display: 'block', marginBottom: 8, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                Patient Name *
              </label>
              <input
                placeholder="e.g., John Smith"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: 8, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                Age
              </label>
              <input
                type="number"
                placeholder="e.g., 75"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                min="0"
                max="150"
              />
            </div>
          </div>
        </div>

        {/* Tracked Items */}
        <div className="card">
          <h3 style={{ marginBottom: 8 }}>Tracked Items</h3>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-tertiary)', marginBottom: 16 }}>
            Select items the system should track for this patient
          </p>
          
          <div className="flex flex-wrap gap-sm" style={{ marginBottom: 16 }}>
            {COMMON_ITEMS.map((item) => (
              <button
                key={item.value}
                type="button"
                onClick={() => toggleItem(item.value)}
                className={`btn small ${selectedItems.includes(item.value) ? '' : 'secondary'}`}
                style={{ 
                  minHeight: 36,
                  padding: '6px 12px'
                }}
              >
                {selectedItems.includes(item.value) && (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                )}
                {item.label}
              </button>
            ))}
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: 8, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              Additional Items (comma-separated)
            </label>
            <input
              placeholder="e.g., cane, dentures, hearing aid"
              value={customItems}
              onChange={(e) => setCustomItems(e.target.value)}
            />
          </div>
        </div>

        {error && (
          <div className="error-message">
            {error}
            {error.includes("login") && (
              <Link href="/login" className="btn small" style={{ marginLeft: 12 }}>
                Sign In
              </Link>
            )}
          </div>
        )}

        <button className="btn full-width" type="submit" disabled={loading || !name.trim()}>
          {loading ? (
            <>
              <div className="spinner" style={{ width: 18, height: 18 }} />
              Creating...
            </>
          ) : (
            'Create Patient'
          )}
        </button>
      </form>
    </main>
  );
}
