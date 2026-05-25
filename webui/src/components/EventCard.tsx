import { useState } from "react";
import { api, type RunEvent } from "@/lib/api";
import { JsonBlock } from "@/components/JsonBlock";
import { Badge } from "@/components/ui/badge";
import {
  ChevronRight,
  Wrench,
  CheckCircle2,
  XCircle,
  Loader2,
  AlertCircle,
  CornerDownRight,
  FilePlus2,
  Download,
} from "lucide-react";

export function EventCard({
  event,
  result,
}: {
  event: RunEvent;
  // For `tool_call` events, the matching `tool_result` (if it has arrived).
  // Pairing happens in the parent so each call renders as a single row.
  result?: RunEvent;
}) {
  const [open, setOpen] = useState(false);
  const sub = event.subagent_of;
  // Nest sub-agent events visually under the parent delegate call.
  const indent = sub ? "ml-6 border-l-2 border-l-primary/30 pl-3" : "";

  // Sub-agent lifecycle events (`done`) carry only debug-y bookkeeping
  // (turn count / tool_calls / finish_reason). The sub-agent's actual
  // reply was already streamed via `model_text` and its outcome is
  // represented by the surrounding `orchestrator.delegate` tool_result.
  // Rendering the raw JSON just clutters the activity log.
  if (event.type === "done") return null;

  // `tool_result` rows are merged into their `tool_call` parent by the
  // caller and should never render standalone.
  if (event.type === "tool_result") return null;

  const subBadge = sub ? (
    <Badge variant="outline" className="text-[10px] font-mono ml-1.5">
      <CornerDownRight className="size-3" />
      via {sub}
    </Badge>
  ) : null;

  if (event.type === "tool_call") {
    // Delegation calls keep a card so the orchestrator → sub-agent boundary
    // stays visually prominent. Every other tool call is rendered inline as
    // a single row, no border / no surface.
    const isDelegate = event.name === "orchestrator.delegate";
    const wrapperCls = isDelegate
      ? `border rounded-md bg-card ${indent}`
      : indent;

    // Pending: no result yet → spinner. Otherwise check / cross.
    const ok = result ? (result.ok ?? result.payload?.ok ?? false) : null;
    const statusIcon =
      ok === null ? (
        <Loader2 className="size-4 text-muted-foreground animate-spin" />
      ) : ok ? (
        <CheckCircle2 className="size-4 text-emerald-600" />
      ) : (
        <XCircle className="size-4 text-rose-600" />
      );
    const statusLabel =
      ok === null
        ? "running"
        : ok
        ? "ok"
        : result?.payload?.error?.code ?? "error";

    return (
      <div className={wrapperCls}>
        <button
          onClick={() => setOpen(!open)}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent/40 transition-colors rounded-md"
        >
          <ChevronRight className={`size-4 transition-transform ${open ? "rotate-90" : ""}`} />
          <Wrench className="size-4 text-muted-foreground" />
          <span className="font-mono font-medium">{event.name}</span>
          {statusIcon}
          <span className="text-xs text-muted-foreground">{statusLabel}</span>
          {subBadge}
        </button>
        {open && (
          <div className={`${isDelegate ? "border-t" : ""} p-3 space-y-3`}>
            <div>
              <div className="text-xs text-muted-foreground mb-1">arguments</div>
              <JsonBlock value={event.args ?? {}} />
            </div>
            {result && (
              <div>
                <div className="text-xs text-muted-foreground mb-1">result</div>
                <JsonBlock value={result.payload ?? {}} />
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  if (event.type === "file_created") {
    const f = event.file;
    if (f) {
      return (
        <div className={`px-3 py-2 ${sub ? indent : "ml-4"}`}>
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
