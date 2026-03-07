"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

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

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    const res = await apiPost<AuthData>("/auth/register", { name, email, password, role });
    if (res.error) {
      setError(res.error);
      return;
    }

    setSession(res.data.token, res.data.user.role);
    router.push(res.data.user.role === "caregiver" ? "/dashboard" : "/home");
  }

  return (
    <main>
      <h1>Register</h1>
      <form onSubmit={onSubmit} className="grid" style={{ maxWidth: 420 }}>
        <input className="input" placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} required />
        <input className="input" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input className="input" type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <select value={role} onChange={(e) => setRole(e.target.value as "caregiver" | "patient")}>
          <option value="caregiver">Caregiver</option>
          <option value="patient">Patient</option>
        </select>
        <button className="btn" type="submit">Create Account</button>
      </form>
      {error && <p style={{ color: "#b42318" }}>{error}</p>}
    </main>
  );
}
