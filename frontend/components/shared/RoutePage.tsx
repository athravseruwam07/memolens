import { SectionCard } from "./SectionCard";

export function RoutePage({ title, note }: { title: string; note: string }) {
  return (
    <main>
      <SectionCard title={title}>
        <p>{note}</p>
      </SectionCard>
    </main>
  );
}
