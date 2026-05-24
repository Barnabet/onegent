import { useEffect, useState } from "react";
import { api, type RunSummary, type RunDetail } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { EventCard } from "@/components/EventCard";
import { JsonBlock } from "@/components/JsonBlock";
import { toast } from "sonner";
import { RefreshCw } from "lucide-react";

export function RunsPage() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [detail, setDetail] = useState<RunDetail | null>(null);

  function refresh() {
    api.runs().then(setRuns).catch((e) => toast.error(e.message));
  }

  useEffect(refresh, []);

  async function openDetail(id: string) {
    try {
      setDetail(await api.run(id));
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Runs</h1>
          <p className="text-sm text-muted-foreground">
            Live + persisted runs from audit_logs/. {runs.length} total.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={refresh}>
          <RefreshCw className="size-3.5" /> Refresh
        </Button>
      </header>

      <div className="space-y-2">
        {runs.length === 0 && (
          <div className="text-sm text-muted-foreground border rounded-md p-6 text-center">
            No runs yet. Start one from the Chat page.
          </div>
        )}
        {runs.map((r) => (
          <Sheet key={r.run_id} onOpenChange={(o) => o && openDetail(r.run_id)}>
            <SheetTrigger asChild>
              <Card className="cursor-pointer hover:border-foreground/40 transition-colors">
                <CardContent className="py-3 flex items-center gap-3">
                  <StatusBadge status={r.status} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="font-mono text-xs text-muted-foreground">{r.run_id}</span>
                      <Badge variant="outline" className="font-mono text-xs">
                        {r.pack}
                      </Badge>
                    </div>
                    <div className="text-sm truncate text-muted-foreground">
                      {r.user_message || "(no preview)"}
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground text-right shrink-0">
                    {r.stats && <div>{r.stats.tool_calls} tools · {r.stats.turns} turns</div>}
                    <div>{r.events_count} events</div>
                  </div>
                </CardContent>
              </Card>
            </SheetTrigger>
            <SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto">
              <SheetHeader>
                <SheetTitle className="font-mono text-sm">{r.run_id}</SheetTitle>
              </SheetHeader>
              {detail && detail.run_id === r.run_id && (
                <div className="p-4 space-y-4">
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm">User message</CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm whitespace-pre-wrap">
                      {detail.user_message || "(unknown — persisted run)"}
                    </CardContent>
                  </Card>
                  {detail.final_text && (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Final reply</CardTitle>
                      </CardHeader>
                      <CardContent className="text-sm whitespace-pre-wrap">
                        {detail.final_text}
                      </CardContent>
                    </Card>
                  )}
                  <section className="space-y-2">
                    <h3 className="text-sm font-semibold">Events</h3>
                    {detail.events
                      .filter((e) => e.type !== "model_text")
                      .map((e, i) => (
                        <EventCard key={i} event={e} />
                      ))}
                  </section>
                  <details>
                    <summary className="text-xs text-muted-foreground cursor-pointer">
                      raw json
                    </summary>
                    <JsonBlock value={detail} className="mt-2" />
                  </details>
                </div>
              )}
            </SheetContent>
          </Sheet>
        ))}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === "done"
      ? "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/40 dark:text-emerald-200"
      : status === "error"
      ? "bg-rose-100 text-rose-900 dark:bg-rose-900/40 dark:text-rose-200"
      : status === "running"
      ? "bg-sky-100 text-sky-900 dark:bg-sky-900/40 dark:text-sky-200"
      : "bg-muted text-muted-foreground";
  return <Badge className={cls}>{status}</Badge>;
}
