import { useState } from "react";
import type { RunEvent } from "@/lib/api";
import { JsonBlock } from "@/components/JsonBlock";
import { Badge } from "@/components/ui/badge";
import { ChevronRight, Wrench, CheckCircle2, XCircle, Sparkles, AlertCircle } from "lucide-react";

export function EventCard({ event }: { event: RunEvent }) {
  const [open, setOpen] = useState(false);

  if (event.type === "skill_activated") {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground border rounded-md px-3 py-2 bg-muted/30">
        <Sparkles className="size-4" />
        <span>
          Skill activated: <span className="font-medium text-foreground">{event.name}</span>
        </span>
      </div>
    );
  }

  if (event.type === "tool_call") {
    return (
      <div className="border rounded-md bg-card">
        <button
          onClick={() => setOpen(!open)}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent/40 transition-colors"
        >
          <ChevronRight className={`size-4 transition-transform ${open ? "rotate-90" : ""}`} />
          <Wrench className="size-4 text-muted-foreground" />
          <span className="font-mono font-medium">{event.name}</span>
          <Badge variant="secondary" className="ml-auto text-xs font-mono">
            {event.call_id?.slice(0, 14)}
          </Badge>
        </button>
        {open && (
          <div className="border-t p-3">
            <div className="text-xs text-muted-foreground mb-1">arguments</div>
            <JsonBlock value={event.args ?? {}} />
          </div>
        )}
      </div>
    );
  }

  if (event.type === "tool_result") {
    const ok = event.ok ?? event.payload?.ok ?? false;
    return (
      <div className="border rounded-md bg-card -mt-1.5 ml-4">
        <button
          onClick={() => setOpen(!open)}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent/40 transition-colors"
        >
          <ChevronRight className={`size-4 transition-transform ${open ? "rotate-90" : ""}`} />
          {ok ? (
            <CheckCircle2 className="size-4 text-emerald-600" />
          ) : (
            <XCircle className="size-4 text-rose-600" />
          )}
          <span className="font-mono text-muted-foreground">{event.name}</span>
          <span className="text-xs text-muted-foreground">
            → {ok ? "ok" : event.payload?.error?.code ?? "error"}
          </span>
        </button>
        {open && (
          <div className="border-t p-3 space-y-2">
            <div>
              <div className="text-xs text-muted-foreground mb-1">payload</div>
              <JsonBlock value={event.payload ?? {}} />
            </div>
          </div>
        )}
      </div>
    );
  }

  if (event.type === "error") {
    return (
      <div className="border border-destructive/40 bg-destructive/10 rounded-md p-3 text-sm">
        <div className="flex items-center gap-2 font-medium text-destructive">
          <AlertCircle className="size-4" /> Error
        </div>
        <div className="mt-1 font-mono text-xs">{event.message}</div>
      </div>
    );
  }

  // Fallback (e.g. unexpected event type) — show raw JSON.
  return <JsonBlock value={event} />;
}
