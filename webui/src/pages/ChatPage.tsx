import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, type PackSummary, type RunEvent, type RunSummary } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ClassificationBadge } from "@/components/ClassificationBadge";
import { EventCard } from "@/components/EventCard";
import { JsonBlock } from "@/components/JsonBlock";
import { Send, Loader2, Database } from "lucide-react";
import { toast } from "sonner";

export function ChatPage() {
  const [packs, setPacks] = useState<PackSummary[]>([]);
  const [pack, setPack] = useState<string>("");
  const [input, setInput] = useState<string>("");
  const [run, setRun] = useState<RunSummary | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [running, setRunning] = useState(false);
  const transcriptRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    api.packs().then((ps) => {
      const visible = ps.filter((p) => !p.error);
      setPacks(visible);
      if (visible.length > 0 && !pack) setPack(visible[0].name);
    }).catch((e) => toast.error(`Failed to load packs: ${e.message}`));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-scroll on new events.
  useEffect(() => {
    const el = transcriptRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [events.length]);

  const finalText = useMemo(() => {
    const parts = events.filter((e) => e.type === "model_text").map((e) => e.delta ?? "");
    return parts[parts.length - 1] ?? "";
  }, [events]);

  async function startRun() {
    if (!pack || !input.trim() || running) return;
    setEvents([]);
    setRun(null);
    setRunning(true);

    let started: RunSummary;
    try {
      started = await api.startRun(pack, input.trim());
    } catch (e) {
      toast.error(`Failed to start run: ${(e as Error).message}`);
      setRunning(false);
      return;
    }
    setRun(started);
    setInput("");

    const es = new EventSource(api.runStreamUrl(started.run_id));

    const handle = (ev: MessageEvent) => {
      try {
        const data = JSON.parse(ev.data);
        if (data?.run_id && (data.status === "done" || data.status === "error")) {
          setRun(data);
          setRunning(false);
          es.close();
          if (data.status === "error") toast.error(`Run failed: ${data.error}`);
          return;
        }
        setEvents((prev) => [...prev, data as RunEvent]);
      } catch {
        // ignore non-JSON heartbeats
      }
    };

    [
      "message",
      "skill_activated",
      "tool_call",
      "tool_result",
      "model_text",
      "error",
    ].forEach((type) => es.addEventListener(type, handle as EventListener));
    es.addEventListener("done", handle as EventListener);
    es.onerror = () => {
      es.close();
      setRunning(false);
    };
  }

  const selectedPack = packs.find((p) => p.name === pack);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
      {/* Sidebar */}
      <aside className="space-y-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Pack</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Select value={pack} onValueChange={setPack} disabled={running}>
              <SelectTrigger>
                <SelectValue placeholder="Choose a pack..." />
              </SelectTrigger>
              <SelectContent>
                {packs.map((p) => (
                  <SelectItem key={p.name} value={p.name}>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{p.name}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selectedPack && (
              <div className="space-y-2 text-sm">
                <p className="text-muted-foreground">{selectedPack.description}</p>
                <div className="flex flex-wrap items-center gap-2">
                  <ClassificationBadge value={selectedPack.classification} />
                  <span className="text-xs text-muted-foreground font-mono">
                    {selectedPack.model}
                  </span>
                </div>
                <div className="text-xs text-muted-foreground">
                  Skills:{" "}
                  <span className="font-mono text-foreground">
                    {selectedPack.skills.join(", ")}
                  </span>
                </div>
                <Link
                  to={`/packs#${selectedPack.name}`}
                  className="text-xs text-muted-foreground hover:text-foreground underline underline-offset-2"
                >
                  view pack detail →
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        {run && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Run</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="font-mono text-xs text-muted-foreground">{run.run_id}</div>
              <div className="flex items-center gap-2">
                <StatusDot status={run.status} />
                <span className="capitalize">{run.status}</span>
              </div>
              {run.stats && (
                <div className="text-xs text-muted-foreground space-y-0.5">
                  <div>turns: {run.stats.turns}</div>
                  <div>tool_calls: {run.stats.tool_calls}</div>
                  <div>finish: {run.stats.finish_reason}</div>
                </div>
              )}
              <Sheet>
                <SheetTrigger asChild>
                  <Button variant="outline" size="sm" className="w-full">
                    <Database className="size-3.5" /> Raw audit
                  </Button>
                </SheetTrigger>
                <SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto">
                  <SheetHeader>
                    <SheetTitle>Audit events — {run.run_id}</SheetTitle>
                  </SheetHeader>
                  <div className="p-4">
                    <JsonBlock value={events} />
                  </div>
                </SheetContent>
              </Sheet>
            </CardContent>
          </Card>
        )}
      </aside>

      {/* Main column */}
      <section className="space-y-4 min-h-[60vh] flex flex-col">
        <Card className="flex-1 flex flex-col">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle>Transcript</CardTitle>
              <span className="text-xs text-muted-foreground font-mono">
                {events.length} event{events.length === 1 ? "" : "s"}
              </span>
            </div>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col gap-3">
            <ScrollArea className="flex-1 max-h-[55vh] -mx-1 px-1">
              <div ref={transcriptRef} className="space-y-2 pr-2">
                {!run && (
                  <div className="text-sm text-muted-foreground py-12 text-center">
                    Pick a pack on the left, type a message below, and hit Send.
                  </div>
                )}
                {run && (
                  <div className="border rounded-md p-3 bg-muted/40">
                    <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">
                      You
                    </div>
                    <div className="whitespace-pre-wrap text-sm">{run.user_message}</div>
                  </div>
                )}
                {events
                  .filter((e) => e.type !== "model_text")
                  .map((e, i) => (
                    <EventCard key={i} event={e} />
                  ))}
                {finalText && (
                  <div className="border rounded-md p-4 bg-card">
                    <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">
                      Assistant
                    </div>
                    <div className="whitespace-pre-wrap text-sm leading-relaxed">{finalText}</div>
                  </div>
                )}
                {running && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                    <Loader2 className="size-3.5 animate-spin" /> running...
                  </div>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Composer */}
        <Card>
          <CardContent className="pt-4">
            <Label htmlFor="msg" className="sr-only">
              Message
            </Label>
            <div className="flex gap-2">
              <Textarea
                id="msg"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault();
                    startRun();
                  }
                }}
                placeholder="Type a message... (⌘/Ctrl+Enter to send)"
                rows={3}
                disabled={running}
                className="resize-none"
              />
              <Button onClick={startRun} disabled={running || !input.trim() || !pack}>
                {running ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
              </Button>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function StatusDot({ status }: { status: string }) {
  const cls =
    status === "done"
      ? "bg-emerald-500"
      : status === "error"
      ? "bg-rose-500"
      : status === "running"
      ? "bg-sky-500 animate-pulse"
      : "bg-muted-foreground";
  return <span className={`inline-block size-2 rounded-full ${cls}`} />;
}
