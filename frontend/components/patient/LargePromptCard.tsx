export function LargePromptCard({ message }: { message: string }) {
  return (
    <div className="card" style={{ fontSize: 28, fontWeight: 600 }}>
      {message}
    </div>
  );
}
