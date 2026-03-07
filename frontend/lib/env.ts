export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export function websocketBase(): string {
  // Convert API base (http://host/api/v1) -> ws://host
  const url = new URL(API_BASE);
  const protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${url.host}`;
}
