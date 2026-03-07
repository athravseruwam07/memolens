"use client";

import { FormEvent, useEffect, useState } from "react";

import { apiGet, apiPost } from "../../../../lib/api";
import { getToken, setPatientId } from "../../../../lib/session";
import type { DailyNote } from "../../../../lib/types";

export default function NotesPage({ params }: { params: { patientId: string } }) {
  const [notes, setNotes] = useState<DailyNote[]>([]);
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const token = getToken();
    if (!token) return;
    const res = await apiGet<DailyNote[]>(`/patients/${params.patientId}/daily-notes/`, token);
    setError(res.error || null);
    setNotes(res.data || []);
  }

  useEffect(() => {
    setPatientId(params.patientId);
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.patientId]);

  async function addNote(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token) return;

    const res = await apiPost<DailyNote>(`/patients/${params.patientId}/daily-notes/`, { content }, token);
    if (res.error) {
      setError(res.error);
      return;
    }

    setContent("");
    await load();
  }

  return (
    <main>
      <h1>Daily Notes</h1>
      <form className="grid" style={{ maxWidth: 600 }} onSubmit={addNote}>
        <textarea rows={4} placeholder="Note content" value={content} onChange={(e) => setContent(e.target.value)} required />
        <button className="btn" type="submit">Add Note</button>
      </form>
      {error && <p style={{ color: "#b42318" }}>{error}</p>}

      <div className="grid" style={{ marginTop: 16 }}>
        {notes.map((n) => (
          <div className="card" key={n.id}>
            <div>{n.content}</div>
            <small>{n.note_date}</small>
          </div>
        ))}
      </div>
    </main>
  );
}
