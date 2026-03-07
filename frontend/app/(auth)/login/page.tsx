"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { apiPost } from "../../../lib/api";
import { setSession } from "../../../lib/session";
import type { AuthData } from "../../../lib/types";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    const res = await apiPost<AuthData>("/auth/login", { email, password });
    if (res.error) {
      setError(res.error);
      return;
    }

    setSession(res.data.token, res.data.user.role);
    router.push(res.data.user.role === "caregiver" ? "/dashboard" : "/home");
  }

  return (
    <main>
      <h1>Login</h1>
      <form onSubmit={onSubmit} className="grid" style={{ maxWidth: 420 }}>
        <input className="input" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input className="input" type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <button className="btn" type="submit">Sign In</button>
      </form>
      {error && <p style={{ color: "#b42318" }}>{error}</p>}
    </main>
  );
}
