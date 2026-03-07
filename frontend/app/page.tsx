"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { clearSession, getRole, getToken } from "../lib/session";

export default function HomePage() {
  const router = useRouter();
  const token = getToken();
  const role = getRole();

  return (
    <main>
      <h1>MemoLens Frontend</h1>
      <p>Use the links below to navigate connected pages.</p>
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}>
        <div className="card">
          <h3>Auth</h3>
          <Link href="/login">Login</Link>
          <br />
          <Link href="/register">Register</Link>
        </div>
        <div className="card">
          <h3>Caregiver</h3>
          <Link href="/dashboard">Dashboard</Link>
        </div>
        <div className="card">
          <h3>Patient</h3>
          <Link href="/home">Patient Home</Link>
        </div>
      </div>

      {token && (
        <div style={{ marginTop: 20 }}>
          <p>Signed in as: {role || "unknown"}</p>
          <button
            className="btn secondary"
            type="button"
            onClick={() => {
              clearSession();
              router.push("/login");
            }}
          >
            Sign Out
          </button>
        </div>
      )}
    </main>
  );
}
