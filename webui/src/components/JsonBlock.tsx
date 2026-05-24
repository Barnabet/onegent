export function JsonBlock({ value, className = "" }: { value: unknown; className?: string }) {
  let text = "";
  try {
    text = JSON.stringify(value, null, 2);
  } catch {
    text = String(value);
  }
  return (
    <pre
      className={`text-xs font-mono bg-muted/50 border rounded-md p-3 overflow-x-auto whitespace-pre ${className}`}
    >
      {text}
    </pre>
  );
}
