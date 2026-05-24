import { useEffect, useMemo, useRef, useState } from "react";
import { api, type FileMeta, type PackSummary, type RunEvent, type RunSummary } from "@/lib/api";
import { FilesSidebar } from "@/components/FilesSidebar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
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
import { Markdown } from "@/components/Markdown";
import { Send, Loader2, Database, Settings2, Sparkles } from "lucide-react";
import { toast } from "sonner";

type Turn = {
  user_message: string;
  run: RunSummary | null;
  events: RunEvent[];
  finished: boolean;
};

export function ChatPage() {
  const [packs, setPacks] = useState<PackSummary[]>([]);
  const [allowed, setAllowed] = useState<Set<string>>(new Set());
  const [input, setInput] = useState<string>("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [running, setRunning] = useState(false);
  const transcriptRef = useRef<HTMLDivElement | null>(null);

  // One conversation_id per ChatPage mount — scopes uploaded files so the
  // server can group them and we can pass the full set to every run. Lazy
  // useState initializer keeps the id stable across re-renders.
  const [conversationId] = useState(
    () => `conv_${Math.random().toString(36).slice(2, 14)}`,
  );
  const [files, setFiles] = useState<FileMeta[]>([]);
  const [uploading, setUploading] = useState(false);

  // Load specialist packs (everything except 'router').
  useEffect(() => {
    api
      .packs()
      .then((ps) => {
        const specialists = ps.filter((p) => !p.error && p.name !== "router");
        setPacks(specialists);
        setAllowed(new Set(specialists.map((p) => p.name)));
      })
      .catch((e) => toast.error(`Failed to load packs: ${e.message}`));
  }, []);

  // Auto-scroll to latest turn.
  useEffect(() => {
    const el = transcriptRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [turns]);

  async function handleUpload(list: FileList) {
    setUploading(true);
    try {
      const uploaded: FileMeta[] = [];
      for (const f of Array.from(list)) {
        try {
          uploaded.push(await api.uploadFile(conversationId, f));
        } catch (e) {
          toast.error(`Upload failed for ${f.name}: ${(e as Error).message}`);
        }
      }
      if (uploaded.length > 0) {
        setFiles((prev) => [...prev, ...uploaded]);
        toast.success(
          uploaded.length === 1
            ? `Uploaded ${uploaded[0].name}`
            : `Uploaded ${uploaded.length} files`,
        );
      }
    } finally {
      setUploading(false);
    }
  }

  async function handleDeleteFile(file_id: string) {
    const prev = files;
    setFiles((p) => p.filter((f) => f.file_id !== file_id));
    try {
      await api.deleteFile(file_id);
    } catch (e) {
      toast.error(`Delete failed: ${(e as Error).message}`);
      setFiles(prev);
    }
  }

  async function send() {
    const msg = input.trim();
    if (!msg || running) return;

    const turn: Turn = { user_message: msg, run: null, events: [], finished: false };
    setTurns((prev) => [...prev, turn]);
    setInput("");
    setRunning(true);

    let started: RunSummary;
    try {
      started = await api.startRun(msg, Array.from(allowed), files);
    } catch (e) {
      toast.error(`Failed to start run: ${(e as Error).message}`);
      setRunning(false);
      return;
    }

    setTurns((prev) => {
      const next = [...prev];
      next[next.length - 1] = { ...next[next.length - 1], run: started };
      return next;
    });

    const es = new EventSource(api.runStreamUrl(started.run_id));
    const handle = (ev: MessageEvent) => {
      try {
        const data = JSON.parse(ev.data);
        if (data?.run_id && (data.status === "done" || data.status === "error")) {
          setTurns((prev) => {
            const next = [...prev];
            next[next.length - 1] = {
              ...next[next.length - 1],
              run: data,
              finished: true,
            };
            return next;
          });
          setRunning(false);
          es.close();
          if (data.status === "error") toast.error(`Run failed: ${data.error}`);
          return;
        }
        setTurns((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          next[next.length - 1] = { ...last, events: [...last.events, data as RunEvent] };
          return next;
        });
      } catch {
        // ignore non-JSON heartbeats
      }
    };

    ["message", "skill_activated", "tool_call", "tool_result", "model_text", "error"].forEach(
      (type) => es.addEventListener(type, handle as EventListener),
    );
    es.addEventListener("done", handle as EventListener);
    es.onerror = () => {
      es.close();
      setRunning(false);
      setTurns((prev) => {
        const next = [...prev];
        next[next.length - 1] = { ...next[next.length - 1], finished: true };
        return next;
      });
    };
  }

  function toggle(name: string) {
    setAllowed((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  function clearTranscript() {
    setTurns([]);
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr_280px] gap-6 h-[calc(100vh-7rem)]">
      {/* Sidebar — orchestrator config */}
      <aside className="space-y-4 overflow-y-auto pb-2">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Settings2 className="size-4" />
              Allowed specialists
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-xs text-muted-foreground">
              Toggle which packs the orchestrator may delegate to. Disabled
              packs are invisible to it.
            </p>
            <div className="space-y-1.5 pt-1">
              {packs.length === 0 && (
                <div className="text-xs text-muted-foreground italic">
                  Loading...
                </div>
              )}
              {packs.map((p) => (
                <label
                  key={p.name}
                  className="flex items-start gap-2 cursor-pointer rounded-md px-2 py-1.5 hover:bg-accent/40 transition-colors"
                >
                  <Checkbox
                    checked={allowed.has(p.name)}
                    onCheckedChange={() => toggle(p.name)}
                    className="mt-0.5"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-sm">{p.name}</span>
                      <ClassificationBadge value={p.classification} />
                    </div>
                    <div className="text-xs text-muted-foreground line-clamp-2">
                      {p.description}
                    </div>
                  </div>
                </label>
              ))}
            </div>
            <div className="pt-2 text-xs text-muted-foreground">
              {allowed.size} of {packs.length} enabled
            </div>
          </CardContent>
        </Card>

        {turns.length > 0 && (
          <Button variant="ghost" size="sm" onClick={clearTranscript} className="w-full">
            Clear conversation
          </Button>
        )}
      </aside>


      {/* Main column — chat */}
      <section className="flex flex-col min-h-0">
        <ScrollArea className="flex-1 -mx-2 px-2">
          <div ref={transcriptRef} className="space-y-6 pb-4">
            {turns.length === 0 && <EmptyState allowedCount={allowed.size} />}
            {turns.map((t, i) => (
              <TurnView key={i} turn={t} isLast={i === turns.length - 1} running={running} />
            ))}
          </div>
        </ScrollArea>

        {/* Composer */}
        <div className="pt-3 mt-3 border-t">
          <Label htmlFor="msg" className="sr-only">
            Message
          </Label>
          <div className="flex gap-2 items-end">
            <Textarea
              id="msg"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  send();
                }
              }}
              placeholder={
                allowed.size === 0
                  ? "Enable at least one specialist on the left, then type a message..."
                  : "Type a message... (⌘/Ctrl+Enter to send)"
              }
              rows={3}
              disabled={running}
              className="resize-none flex-1"
            />
            <Button
              onClick={send}
              disabled={running || !input.trim() || allowed.size === 0}
              size="lg"
            >
              {running ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
            </Button>
          </div>
        </div>
      </section>

      {/* Right sidebar — files in the conversation */}
      <aside className="hidden lg:block min-h-0">
        <FilesSidebar
          files={files}
          uploading={uploading}
          onUpload={handleUpload}
          onDelete={handleDeleteFile}
        />
      </aside>
    </div>
  );
}

function EmptyState({ allowedCount }: { allowedCount: number }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-20 px-6 max-w-md mx-auto">
      <Sparkles className="size-10 text-muted-foreground/40 mb-4" />
      <h2 className="text-lg font-semibold mb-1">Ask the orchestrator</h2>
      <p className="text-sm text-muted-foreground">
        Type any request. The orchestrator picks the right specialist from
        your <span className="font-medium text-foreground">{allowedCount}</span>{" "}
        enabled pack{allowedCount === 1 ? "" : "s"} and routes the work.
      </p>
    </div>
  );
}

function TurnView({
  turn,
  isLast,
  running,
}: {
  turn: Turn;
  isLast: boolean;
  running: boolean;
}) {
  // The final reply is the last top-level model_text (not from a sub-agent).
  const finalText = useMemo(() => {
    const topLevel = turn.events.filter(
      (e) => e.type === "model_text" && !e.subagent_of,
    );
    return topLevel[topLevel.length - 1]?.delta ?? "";
  }, [turn.events]);

  // Hide raw model_text from the activity list — the bubble shows the final.
  const interiorEvents = turn.events.filter((e) => e.type !== "model_text");
  const isRunning = !turn.finished && isLast && running;

  return (
    <div className="space-y-3">
      {/* User bubble */}
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-md bg-primary text-primary-foreground px-4 py-2.5 text-sm whitespace-pre-wrap">
          {turn.user_message}
        </div>
      </div>

      {/* Orchestrator activity */}
      {interiorEvents.length > 0 && (
        <details className="group" open>
          <summary className="cursor-pointer text-xs text-muted-foreground inline-flex items-center gap-1 select-none">
            <span className="group-open:hidden">▸</span>
            <span className="hidden group-open:inline">▾</span>
            orchestrator activity ({interiorEvents.length})
          </summary>
          <div className="space-y-1.5 mt-2">
            {interiorEvents.map((e, i) => (
              <EventCard key={i} event={e} />
            ))}
          </div>
        </details>
      )}

      {/* Assistant bubble */}
      {finalText && (
        <div className="flex justify-start">
          <div className="max-w-[85%] rounded-2xl rounded-bl-md bg-muted px-4 py-2.5">
            <Markdown>{finalText}</Markdown>
          </div>
        </div>
      )}

      {isRunning && (
        <div className="flex justify-start">
          <div className="rounded-2xl rounded-bl-md bg-muted px-4 py-2.5 text-sm text-muted-foreground inline-flex items-center gap-2">
            <Loader2 className="size-3.5 animate-spin" /> thinking...
          </div>
        </div>
      )}

      {turn.run && turn.finished && (
        <div className="flex justify-start">
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="sm" className="h-7 text-xs text-muted-foreground">
                <Database className="size-3" /> raw audit
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto">
              <SheetHeader>
                <SheetTitle className="font-mono text-sm">{turn.run.run_id}</SheetTitle>
              </SheetHeader>
              <div className="p-4">
                <JsonBlock value={turn.events} />
              </div>
            </SheetContent>
          </Sheet>
        </div>
      )}
    </div>
  );
}
