import { Badge } from "@/components/ui/badge";

const TONES: Record<string, string> = {
  public: "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/40 dark:text-emerald-200",
  internal: "bg-sky-100 text-sky-900 dark:bg-sky-900/40 dark:text-sky-200",
  confidential: "bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-200",
  restricted: "bg-rose-100 text-rose-900 dark:bg-rose-900/40 dark:text-rose-200",
};

export function ClassificationBadge({ value }: { value: string }) {
  const tone = TONES[value] ?? "bg-muted text-muted-foreground";
  return (
    <Badge variant="outline" className={tone}>
      {value}
    </Badge>
  );
}
