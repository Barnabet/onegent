import { useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  type ConversationDetail,
  type ConversationSummary,
  type FileMeta,
  type RunEvent,
  type RunSummary,
} from "@/lib/api";
import { ConversationsSidebar } from "@/components/ConversationsSidebar";
import { FilesSidebar } from "@/components/FilesSidebar";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { EventCard } from "@/components/EventCard";
import { JsonBlock } from "@/components/JsonBlock";
import { Markdown } from "@/components/Markdown";
import { Send, Loader2, Database, Sparkles, PanelLeft } from "lucide-react";
import { toast } from "sonner";

/** Per-turn view-model: the user message, the run handle, the live events,
 *  and the assistant's eventual reply (mirrored into the convo on the server). */
type Turn = {
  user_message: string;
  run: RunSummary | null;
  events: RunEvent[];
  finished: boolean;
  assistant_text?: string;
};

export function ChatPage() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [activeDetail, setActiveDetail] = useState<ConversationDetail | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [convOpen, setConvOpen] = useState(false);
  const transcriptRef = useRef<HTMLDivElement | null>(null);

  // ---- conversation list -------------------------------------------------

  async function refreshConversations(): Promise<ConversationSummary[]> {
    try {
      const list = await api.conversations();
      setConversations(list);
      return list;
    } catch (e) {
      toast.error(`Failed to load conversations: ${(e as Error).message}`);
      return [];
    }
  }

  // Initial load: list conversations, auto-select the most recent, or
  // create one if none exist.
  useEffect(() => {
    (async () => {
      const list = await refreshConversations();
      if (list.length > 0) {
        setActiveId(list[0].id);
      } else {
        try {
          const created = await api.createConversation();
          setActiveId(created.id);
          await refreshConversations();
        } catch (e) {
          toast.error(`Failed to create conversation: ${(e as Error).message}`);
        }
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // When the active conversation changes: load its detail, project messages
  // into the turns view, drop any in-flight stream.
  useEffect(() => {
    if (!activeId) {
      setActiveDetail(null);
      setTurns([]);
      return;
    }
    (async () => {
      try {
        const d = await api.conversation(activeId);
        setActiveDetail(d);
        setTurns(messagesToTurns(d));
      } catch (e) {
        toast.error(`Failed to load conversation: ${(e as Error).message}`);
      }
    })();
  }, [activeId]);

  // Auto-scroll to latest turn. The transcript lives inside Radix' ScrollArea,
  // so the actual scrollable element is the [data-slot="scroll-area-viewport"]
  // ancestor of our content div.
  useEffect(() => {
    const el = transcriptRef.current;
    if (!el) return;
    const viewport = el.closest('[data-slot="scroll-area-viewport"]') as HTMLElement | null;
    const target = viewport ?? el;
    target.scrollTop = target.scrollHeight;
  }, [turns]);

  // ---- conversation actions ----------------------------------------------

  async function createConversation() {
    try {
      const c = await api.createConversation();
      await refreshConversations();
      setActiveId(c.id);
    } catch (e) {
      toast.error(`Failed to create conversation: ${(e as Error).message}`);
    }
  }

  async function renameConversation(id: string, title: string) {
    try {
      await api.renameConversation(id, title);
      await refreshConversations();
    } catch (e) {
      toast.error(`Rename failed: ${(e as Error).message}`);
    }
  }

  async function deleteConversation(id: string) {
    if (!confirm("Delete this conversation? Attached files will be removed too.")) {
      return;
    }
    try {
      await api.deleteConversation(id);
      const list = await refreshConversations();
      if (activeId === id) {
        if (list.length > 0) setActiveId(list[0].id);
        else {
          // None left — spin up a fresh one to keep the UI usable.
          const created = await api.createConversation();
          setActiveId(created.id);
          await refreshConversations();
        }
      }
    } catch (e) {
      toast.error(`Delete failed: ${(e as Error).message}`);
    }
  }

  // ---- files -------------------------------------------------------------

  const files: FileMeta[] = activeDetail?.files ?? [];

  async function handleUpload(list: FileList) {
    if (!activeId) return;
    setUploading(true);
    try {
      const uploaded: FileMeta[] = [];
      for (const f of Array.from(list)) {
        try {
          uploaded.push(await api.uploadFile(activeId, f));
        } catch (e) {
          toast.error(`Upload failed for ${f.name}: ${(e as Error).message}`);
        }
      }
      if (uploaded.length > 0) {
        // Refresh conversation so its file_ids/files reflect the upload.
        const d = await api.conversation(activeId);
        setActiveDetail(d);
        await refreshConversations();
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
    if (!activeId) return;
    const prev = activeDetail;
    setActiveDetail((p) =>
      p
        ? {
            ...p,
            file_ids: p.file_ids.filter((id) => id !== file_id),
            files: p.files.filter((f) => f.file_id !== file_id),
          }
        : p,
    );
    try {
      await api.deleteFile(file_id);
      await refreshConversations();
    } catch (e) {
      toast.error(`Delete failed: ${(e as Error).message}`);
      setActiveDetail(prev);
    }
  }

  // ---- send a message ----------------------------------------------------

  async function send() {
    const msg = input.trim();
    if (!msg || running || !activeId) return;

    const turn: Turn = { user_message: msg, run: null, events: [], finished: false };
    setTurns((prev) => [...prev, turn]);
    setInput("");
    setRunning(true);

    let started: RunSummary;
    try {
      started = await api.startRun(msg, activeId);
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
              assistant_text: data.final_text || next[next.length - 1].assistant_text,
            };
            return next;
          });
          setRunning(false);
          es.close();
          if (data.status === "error") toast.error(`Run failed: ${data.error}`);
          // Refresh conversation list so the title (auto-derived from the
          // first user message) and updated_at are reflected in the sidebar.
          refreshConversations();
          return;
        }
        // Agent created a file → splice the new FileMeta into the sidebar
        // immediately (the server has already attached it server-side).
        if (data?.type === "file_created" && data.file && activeId) {
          const newFile = data.file as FileMeta;
          setActiveDetail((p) => {
            if (!p || p.id !== activeId) return p;
            if (p.file_ids.includes(newFile.file_id)) return p;
            return {
              ...p,
              file_ids: [...p.file_ids, newFile.file_id],
              files: [...p.files, newFile],
            };
          });
          toast.success(`Agent created ${newFile.name}`);
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

    ["message", "tool_call", "tool_result", "model_text", "file_created", "error"].forEach(
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

  // ---- render ------------------------------------------------------------

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_260px] gap-8 h-full max-w-[1600px] mx-auto">
      {/* Conversations drawer — slides in from the left edge */}
      <Sheet open={convOpen} onOpenChange={setConvOpen}>
        <SheetContent side="left" className="w-80 p-0 border-r" showCloseButton={false}>
          <SheetHeader className="sr-only">
            <SheetTitle>Conversations</SheetTitle>
          </SheetHeader>
          <div className="h-full p-3">
            <ConversationsSidebar
              conversations={conversations}
              activeId={activeId}
              onSelect={(id) => {
                setActiveId(id);
                setConvOpen(false);
              }}
              onCreate={() => {
                createConversation();
                setConvOpen(false);
              }}
              onRename={renameConversation}
              onDelete={deleteConversation}
            />
          </div>
        </SheetContent>
      </Sheet>

      {/* Main column — chat */}
      <section className="flex flex-col min-h-0 min-w-0">
        {/* Toolbar above the transcript */}
        <div className="pb-3 flex items-center gap-2 max-w-3xl mx-auto w-full">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setConvOpen(true)}
            className="gap-2"
          >
            <PanelLeft className="size-4" />
            Conversations
            <span className="text-xs text-muted-foreground">({conversations.length})</span>
          </Button>
        </div>
        <ScrollArea className="flex-1 min-h-0 -mx-2 px-2">
          <div ref={transcriptRef} className="space-y-6 pb-4 max-w-3xl mx-auto w-full">
            {turns.length === 0 && <EmptyState />}
            {turns.map((t, i) => (
              <TurnView
                key={i}
                turn={t}
                isLast={i === turns.length - 1}
                running={running}
              />
            ))}
          </div>
        </ScrollArea>

        {/* Composer */}
        <div className="pt-3 mt-3 border-t max-w-3xl mx-auto w-full">
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
                activeId
                  ? "Type a message... (⌘/Ctrl+Enter to send)"
                  : "Loading conversation..."
              }
              rows={3}
              disabled={running || !activeId}
              className="resize-none flex-1"
            />
            <Button
              onClick={send}
              disabled={running || !input.trim() || !activeId}
              size="lg"
            >
              {running ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Send className="size-4" />
              )}
            </Button>
          </div>
        </div>
      </section>

      {/* Right sidebar — files in the conversation */}
      <aside className="hidden lg:block min-h-0 min-w-0 overflow-hidden">
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

/** Project a server-side conversation into the per-turn view-model. The
 *  server stores plain (user, assistant) pairs without event history, so
 *  loaded turns have empty `events` and `finished=true`. New turns added
 *  during this page session keep their live event stream. */
function messagesToTurns(d: ConversationDetail): Turn[] {
  const turns: Turn[] = [];
  let pendingUser: string | null = null;
  for (const m of d.messages) {
    if (m.role === "user") {
      if (pendingUser !== null) {
        // Two user messages in a row (shouldn't happen but be defensive).
        turns.push({
          user_message: pendingUser,
          run: null,
          events: [],
          finished: true,
        });
      }
      pendingUser = m.content;
    } else if (m.role === "assistant" && pendingUser !== null) {
      turns.push({
        user_message: pendingUser,
        run: null,
        events: [],
        finished: true,
        assistant_text: m.content,
      });
      pendingUser = null;
    }
  }
  if (pendingUser !== null) {
    turns.push({
      user_message: pendingUser,
      run: null,
      events: [],
      finished: true,
    });
  }
  return turns;
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center text-center py-20 px-6 max-w-md mx-auto">
      <Sparkles className="size-10 text-muted-foreground/40 mb-4" />
      <h2 className="text-lg font-semibold mb-1">Ask the orchestrator</h2>
      <p className="text-sm text-muted-foreground">
        Type any request. The orchestrator picks the right specialist or
        composes one from skills, and routes the work.
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
  // The displayed reply comes from `assistant_text` if the server already
  // persisted one (replayed turns), otherwise from the live stream's last
  // top-level model_text (in-flight turns).
  const finalText = useMemo(() => {
    if (turn.assistant_text) return turn.assistant_text;
    const topLevel = turn.events.filter(
      (e) => e.type === "model_text" && !e.subagent_of,
    );
    return topLevel[topLevel.length - 1]?.delta ?? "";
  }, [turn.events, turn.assistant_text]);

  // Hide events that don't render as their own row in the activity list:
  //  - `model_text`: the reply itself is shown below
  //  - `done`: sub-agent lifecycle bookkeeping (EventCard returns null)
  //  - `tool_result`: folded into the matching `tool_call` row (one entry
  //     per call that grows a checkmark / X once the result arrives)
  const interiorEvents = turn.events.filter(
    (e) =>
      e.type !== "model_text" &&
      e.type !== "done" &&
      e.type !== "tool_result",
  );

  // call_id → tool_result, so the merged tool_call row can show outcome.
  const resultByCall = useMemo(() => {
    const m = new Map<string, RunEvent>();
    for (const e of turn.events) {
      if (e.type === "tool_result" && e.call_id) m.set(e.call_id, e);
    }
    return m;
  }, [turn.events]);
  const isRunning = !turn.finished && isLast && running;

  return (
    <div className="space-y-3">
      {/* User bubble */}
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-md bg-primary text-primary-foreground px-4 py-2.5 text-sm whitespace-pre-wrap">
          {turn.user_message}
        </div>
      </div>

      {/* Orchestrator activity (only present for live turns) */}
      {interiorEvents.length > 0 && (
        <details className="group" open>
          <summary className="cursor-pointer text-xs text-muted-foreground inline-flex items-center gap-1 select-none">
            <span className="group-open:hidden">▸</span>
            <span className="hidden group-open:inline">▾</span>
            orchestrator activity ({interiorEvents.length})
          </summary>
          <div className="space-y-1.5 mt-2">
            {interiorEvents.map((e, i) => (
              <EventCard
                key={i}
                event={e}
                result={e.call_id ? resultByCall.get(e.call_id) : undefined}
              />
            ))}
          </div>
        </details>
      )}

      {/* Assistant reply — no bubble, just text in the flow */}
      {finalText && (
        <div className="px-1">
          <Markdown>{finalText}</Markdown>
        </div>
      )}

      {isRunning && (
        <div className="px-1 text-sm text-muted-foreground inline-flex items-center gap-2">
          <Loader2 className="size-3.5 animate-spin" /> thinking...
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
