"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { apiPost } from "../../../lib/api";
import { setSession } from "../../../lib/session";
import type { AuthData } from "../../../lib/types";

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"caregiver" | "patient">("caregiver");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await apiPost<AuthData>("/auth/register", { name, email, password, role });
      if (res.error) {
        setError(res.error);
        setLoading(false);
        return;
      }

      setSession(res.data.token, res.data.user.role);
      router.push(res.data.user.role === "caregiver" ? "/dashboard" : "/home");
    } catch {
      setError("An unexpected error occurred");
      setLoading(false);
    }
  }

  return (
    <main className="flex flex-col items-center justify-center" style={{ minHeight: '100dvh', padding: 24 }}>
      {/* Back button */}
      <div style={{ position: 'absolute', top: 16, left: 16 }}>
        <Link href="/" className="btn ghost" style={{ padding: '8px 12px' }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          Back
        </Link>
      </div>

      <div style={{ width: '100%', maxWidth: 400 }}>
        {/* Logo */}
        <div className="text-center" style={{ marginBottom: 40 }}>
          <div 
            style={{ 
              width: 64, 
              height: 64, 
              background: 'var(--gradient-primary)',
              borderRadius: 16,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px',
              boxShadow: 'var(--shadow-glow)'
            }}
          >
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--bg-primary)' }}>
              <circle cx="12" cy="12" r="3"/>
              <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
            </svg>
          </div>
          <h1 style={{ marginBottom: 8 }}>Create account</h1>
          <p style={{ color: 'var(--text-tertiary)', margin: 0 }}>
            Get started with MemoLens
          </p>
        </div>

        {/* Form */}
        <form onSubmit={onSubmit} className="grid" style={{ gap: 16 }}>
          <div>
            <label 
              htmlFor="name" 
              style={{ 
                display: 'block', 
                marginBottom: 8, 
                fontSize: '0.875rem', 
                fontWeight: 500,
                color: 'var(--text-secondary)'
              }}
            >
              Full Name
            </label>
            <input
              id="name"
              type="text"
              placeholder="John Doe"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              autoComplete="name"
            />
          </div>

          <div>
            <label 
              htmlFor="email" 
              style={{ 
                display: 'block', 
                marginBottom: 8, 
                fontSize: '0.875rem', 
                fontWeight: 500,
                color: 'var(--text-secondary)'
              }}
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              autoCapitalize="off"
            />
          </div>

          <div>
            <label 
              htmlFor="password" 
              style={{ 
                display: 'block', 
                marginBottom: 8, 
                fontSize: '0.875rem', 
                fontWeight: 500,
                color: 'var(--text-secondary)'
              }}
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="new-password"
              minLength={6}
            />
          </div>

          <div>
            <label 
              htmlFor="role" 
              style={{ 
                display: 'block', 
                marginBottom: 8, 
                fontSize: '0.875rem', 
                fontWeight: 500,
                color: 'var(--text-secondary)'
              }}
            >
              I am a...
            </label>
            <div className="grid grid-2" style={{ gap: 12 }}>
              <button
                type="button"
                onClick={() => setRole("caregiver")}
                className="card"
                style={{
                  cursor: 'pointer',
                  textAlign: 'center',
                  padding: 16,
                  border: role === 'caregiver' ? '2px solid var(--accent)' : '1px solid var(--surface-border)',
                  background: role === 'caregiver' ? 'var(--accent-muted)' : 'var(--surface)'
                }}
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={role === 'caregiver' ? 'var(--accent)' : 'var(--text-tertiary)'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto 8px' }}>
                  <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
                  <circle cx="9" cy="7" r="4"/>
                  <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
                </svg>
                <div style={{ fontWeight: 600, color: role === 'caregiver' ? 'var(--accent)' : 'var(--text-primary)' }}>
                  Caregiver
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', marginTop: 4 }}>
                  Manage patients
                </div>
              </button>

              <button
                type="button"
                onClick={() => setRole("patient")}
                className="card"
                style={{
                  cursor: 'pointer',
                  textAlign: 'center',
                  padding: 16,
                  border: role === 'patient' ? '2px solid var(--accent-secondary)' : '1px solid var(--surface-border)',
                  background: role === 'patient' ? 'var(--accent-secondary-muted)' : 'var(--surface)'
                }}
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={role === 'patient' ? 'var(--accent-secondary)' : 'var(--text-tertiary)'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto 8px' }}>
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                  <circle cx="12" cy="7" r="4"/>
                </svg>
                <div style={{ fontWeight: 600, color: role === 'patient' ? 'var(--accent-secondary)' : 'var(--text-primary)' }}>
                  Patient
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', marginTop: 4 }}>
                  Get assistance
                </div>
              </button>
            </div>
          </div>

          {error && (
            <div className="error-message">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: 8, flexShrink: 0 }}>
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              {error}
            </div>
          )}

          <button 
            className="btn full-width" 
            type="submit" 
            disabled={loading}
            style={{ marginTop: 8 }}
          >
            {loading ? (
              <>
                <div className="spinner" style={{ width: 20, height: 20 }} />
                Creating account...
              </>
            ) : (
              "Create Account"
            )}
          </button>
        </form>

        {/* Footer */}
        <div className="text-center" style={{ marginTop: 32 }}>
          <p style={{ color: 'var(--text-tertiary)', fontSize: '0.875rem' }}>
            Already have an account?{" "}
            <Link href="/login" style={{ fontWeight: 600 }}>
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
