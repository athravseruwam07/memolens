"use client";

import Link from "next/link";

export default function NewPersonPage({ params }: { params: { patientId: string } }) {
  return (
    <main>
      <h1>Add Familiar Person</h1>
      <p>Use the main people page form for now.</p>
      <Link href={`/people/${params.patientId}`}>Back to People</Link>
    </main>
  );
}
