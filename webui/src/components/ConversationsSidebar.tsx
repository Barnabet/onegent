import { useState } from "react";
import type { ConversationSummary } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageSquarePlus, MoreHorizontal, Pencil, Trash2 } from "lucide-react";

type Props = {
  conversations: ConversationSummary[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
};

export function ConversationsSidebar({
  conversations,
  activeId,
  onSelect,
  onCreate,
  onRename,
  onDelete,
}: Props) {
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");

  function startRename(c: ConversationSummary) {
    setRenamingId(c.id);
    setDraftTitle(c.title);
  }

  function commitRename() {
    if (renamingId && draftTitle.trim()) {
      onRename(renamingId, draftTitle.trim());
    }
    setRenamingId(null);
    setDraftTitle("");
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="pb-3">
        <Button
          onClick={onCreate}
          variant="outline"
          size="sm"
          className="w-full justify-start"
        >
          <MessageSquarePlus className="size-4" />
          New conversation
        </Button>
      </div>

      <ScrollArea className="flex-1 -mx-2 px-2">
        <div className="space-y-0.5">
          {conversations.length === 0 && (
            <div className="text-xs text-muted-foreground italic px-2 py-4 text-center">
              No conversations yet.
            </div>
          )}
          {conversations.map((c) => {
            const isActive = c.id === activeId;
            const isRenaming = renamingId === c.id;
            return (
              <div
                key={c.id}
                className={`group rounded-md transition-colors ${
                  isActive ? "bg-accent" : "hover:bg-accent/40"
                }`}
              >
                {isRenaming ? (
                  <div className="px-2 py-1.5">
                    <Input
                      value={draftTitle}
                      onChange={(e) => setDraftTitle(e.target.value)}
                      onBlur={commitRename}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") commitRename();
                        else if (e.key === "Escape") {
                          setRenamingId(null);
                          setDraftTitle("");
                        }
                      }}
                      autoFocus
                      className="h-7 text-sm"
                    />
                  </div>
                ) : (
                  <div className="flex items-center gap-1 px-1">
                    <button
                      onClick={() => onSelect(c.id)}
                      className="flex-1 min-w-0 text-left px-2 py-2"
                    >
                      <div
                        className={`truncate text-sm ${
                          isActive ? "font-medium" : ""
                        }`}
                      >
                        {c.title}
                      </div>
                      <div className="text-[10px] text-muted-foreground">
                        {c.message_count} msg
                        {c.message_count === 1 ? "" : "s"}
                        {c.file_count > 0
                          ? ` · ${c.file_count} file${c.file_count === 1 ? "" : "s"}`
                          : ""}
                      </div>
                    </button>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-7 opacity-0 group-hover:opacity-100 data-[state=open]:opacity-100"
                        >
                          <MoreHorizontal className="size-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-40">
                        <DropdownMenuItem onClick={() => startRename(c)}>
                          <Pencil className="size-3.5" /> Rename
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => onDelete(c.id)}
                          className="text-destructive focus:text-destructive"
                        >
                          <Trash2 className="size-3.5" /> Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
}
