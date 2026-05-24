import { useState } from "react";
import { api, type RunEvent } from "@/lib/api";
import { JsonBlock } from "@/components/JsonBlock";
import { Badge } from "@/components/ui/badge";
import {
  ChevronRight,
  Wrench,
  CheckCircle2,
  XCircle,
  AlertCircle,
  CornerDownRight,
  FilePlus2,
  Download,
} from "lucide-react";

export function EventCard({ event }: { event: RunEvent }) {
  const [open, setOpen] = useState(false);
  const sub = event.subagent_of;
  // Nest sub-agent events visually under the parent delegate call.
  const indent = sub ? "ml-6 border-l-2 border-l-primary/30 pl-3" : "";

  const subBadge = sub ? (
    <Badge variant="outline" className="text-[10px] font-mono ml-1.5">
      <CornerDownRight className="size-3" />
      via {sub}
    </Badge>
  ) : null;

  if (event.type === "tool_call") {
    return (
      <div className={`border rounded-md bg-card ${indent}`}>
        <button
          onClick={() => setOpen(!open)}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent/40 transition-colors"
        >
          <ChevronRight className={`size-4 transition-transform ${open ? "rotate-90" : ""}`} />
          <Wrench className="size-4 text-muted-foreground" />
          <span className="font-mono font-medium">{event.name}</span>
          {subBadge}
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
      <div className={`border rounded-md bg-card -mt-1.5 ${sub ? indent : "ml-4"}`}>
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
          {subBadge}
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

  if (event.type === "file_created") {
    const f = event.file;
    if (f) {
      return (
        <div className={`border rounded-md bg-card px-3 py-2 ${sub ? indent : "ml-4"} -mt-1.5`}>
          <div className="flex items-center gap-2 text-sm">
            <FilePlus2 className="size-4 text-emerald-600" />
            <span className="text-muted-foreground">created</span>
            <span className="font-medium truncate" title={f.name}>{f.name}</span>
            <Badge variant="outline" className="text-[10px] font-mono">
              {(f.size / 1024).toFixed(1)} KB
            </Badge>
            {event.tool_name && (
              <span className="text-xs text-muted-foreground font-mono">via {event.tool_name}</span>
            )}
            {subBadge}
            <a
              href={api.downloadFileUrl(f.file_id)}
              download={f.name}
              className="ml-auto inline-flex items-center gap-1 text-xs text-primary hover:underline"
              title={`Download ${f.name}`}
            >
              <Download className="size-3.5" /> Download
            </a>
          </div>
        </div>
      );
    }
    // Registration failed on the server side — surface the reason.
    return (
      <div className={`border border-amber-500/40 bg-amber-500/10 rounded-md px-3 py-2 text-sm ${indent}`}>
        <div className="flex items-center gap-2">
          <AlertCircle className="size-4 text-amber-600" />
          <span>Tool wrote a file but it couldn't be attached:</span>
          <code className="text-xs">{event.error || "unknown error"}</code>
          {event.path && <code className="text-xs text-muted-foreground">{event.path}</code>}
        </div>
      </div>
    );
  }

  if (event.type === "error") {
    return (
      <div className={`border border-destructive/40 bg-destructive/10 rounded-md p-3 text-sm ${indent}`}>
        <div className="flex items-center gap-2 font-medium text-destructive">
          <AlertCircle className="size-4" /> Error{subBadge}
        </div>
        <div className="mt-1 font-mono text-xs">{event.message}</div>
      </div>
    );
  }

  // Fallback (e.g. unexpected event type) — show raw JSON.
  return <JsonBlock value={event} />;
}
