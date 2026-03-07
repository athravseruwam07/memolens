const TOKEN_KEY = "memolens_token";
const ROLE_KEY = "memolens_role";
const PATIENT_KEY = "memolens_patient_id";

function hasWindow(): boolean {
  return typeof window !== "undefined";
}

export function getToken(): string | null {
  if (!hasWindow()) return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setSession(token: string, role: string): void {
  if (!hasWindow()) return;
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(ROLE_KEY, role);
}

export function clearSession(): void {
  if (!hasWindow()) return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
}

export function getRole(): string | null {
  if (!hasWindow()) return null;
  return localStorage.getItem(ROLE_KEY);
}

export function getPatientId(): string | null {
  if (!hasWindow()) return null;
  return localStorage.getItem(PATIENT_KEY);
}

export function setPatientId(id: string): void {
  if (!hasWindow()) return;
  localStorage.setItem(PATIENT_KEY, id);
}
