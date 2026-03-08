"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { clearSession, getRole, getToken } from "../lib/session";

export default function HomePage() {
  const router = useRouter();
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [role, setRole] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    const userRole = getRole();
    setIsLoggedIn(!!token);
    setRole(userRole);
  }, []);

  const handleSignOut = () => {
    clearSession();
    setIsLoggedIn(false);
    setRole(null);
    router.push("/login");
  };

  return (
    <main className="flex flex-col" style={{ paddingBottom: 100 }}>
      {/* Hero Section */}
      <div className="text-center" style={{ marginBottom: 48 }}>
        <div 
          style={{ 
            width: 80, 
            height: 80, 
            background: 'var(--gradient-primary)',
            borderRadius: 20,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 24px',
            boxShadow: 'var(--shadow-glow)'
          }}
        >
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--bg-primary)' }}>
            <circle cx="12" cy="12" r="3"/>
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
          </svg>
        </div>
        <h1 style={{ marginBottom: 12 }}>MemoLens</h1>
        <p style={{ fontSize: '1.125rem', maxWidth: 320, margin: '0 auto' }}>
          AI-powered memory assistant for dementia care
        </p>
      </div>

      {/* Quick Actions */}
      <div className="grid" style={{ gap: 12, marginBottom: 32 }}>
        <Link href="/home" className="action-item">
          <div className="icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
          </div>
          <div className="content">
            <div className="title">Patient Mode</div>
            <div className="subtitle">Voice assistant & reminders</div>
          </div>
          <div className="arrow">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </div>
        </Link>

        <Link href="/dashboard" className="action-item">
          <div className="icon" style={{ background: 'var(--accent-secondary-muted)', color: 'var(--accent-secondary)' }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7"/>
              <rect x="14" y="3" width="7" height="7"/>
              <rect x="14" y="14" width="7" height="7"/>
              <rect x="3" y="14" width="7" height="7"/>
            </svg>
          </div>
          <div className="content">
            <div className="title">Caregiver Dashboard</div>
            <div className="subtitle">Manage patients & monitor activity</div>
          </div>
          <div className="arrow">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </div>
        </Link>
      </div>

      {/* Auth Section */}
      <div className="card" style={{ textAlign: 'center' }}>
        {isLoggedIn ? (
          <>
            <div className="flex items-center justify-center gap-sm" style={{ marginBottom: 16 }}>
              <div className="status-dot online" />
              <span style={{ color: 'var(--text-secondary)' }}>
                Signed in as <span style={{ color: 'var(--accent)', fontWeight: 500 }}>{role || "User"}</span>
              </span>
            </div>
            <button className="btn secondary full-width" type="button" onClick={handleSignOut}>
              Sign Out
            </button>
          </>
        ) : (
          <>
            <p style={{ marginBottom: 16 }}>Sign in to access all features</p>
            <div className="grid" style={{ gap: 12 }}>
              <Link href="/login" className="btn full-width">
                Sign In
              </Link>
              <Link href="/register" className="btn secondary full-width">
                Create Account
              </Link>
            </div>
          </>
        )}
      </div>

      {/* Features Preview */}
      <div style={{ marginTop: 48 }}>
        <h2 style={{ textAlign: 'center', marginBottom: 24 }}>Features</h2>
        <div className="grid" style={{ gap: 16 }}>
          <div className="card">
            <div className="flex items-center gap-md" style={{ marginBottom: 8 }}>
              <div style={{ 
                width: 36, 
                height: 36, 
                background: 'var(--success-muted)', 
                borderRadius: 10,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                  <path d="M19 10v1a7 7 0 0 1-14 0v-1M12 18.5v3.5M8 22h8"/>
                </svg>
              </div>
              <h3 style={{ margin: 0 }}>Voice Assistant</h3>
            </div>
            <p style={{ margin: 0, fontSize: '0.875rem' }}>
              Ask questions about reminders, people, and item locations using voice
            </p>
          </div>

          <div className="card">
            <div className="flex items-center gap-md" style={{ marginBottom: 8 }}>
              <div style={{ 
                width: 36, 
                height: 36, 
                background: 'var(--info-muted)', 
                borderRadius: 10,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--info)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="3"/>
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                </svg>
              </div>
              <h3 style={{ margin: 0 }}>Object Detection</h3>
            </div>
            <p style={{ margin: 0, fontSize: '0.875rem' }}>
              Automatically track where items were last seen using AI vision
            </p>
          </div>

          <div className="card">
            <div className="flex items-center gap-md" style={{ marginBottom: 8 }}>
              <div style={{ 
                width: 36, 
                height: 36, 
                background: 'var(--warning-muted)', 
                borderRadius: 10,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--warning)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                  <circle cx="9" cy="7" r="4"/>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
                </svg>
              </div>
              <h3 style={{ margin: 0 }}>Face Recognition</h3>
            </div>
            <p style={{ margin: 0, fontSize: '0.875rem' }}>
              Identify familiar people and provide helpful context about them
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
