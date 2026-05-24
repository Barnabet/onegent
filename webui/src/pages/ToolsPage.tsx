import { useEffect, useState } from "react";
import { api, type Tool, type ToolDetail } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ClassificationBadge } from "@/components/ClassificationBadge";
import { ROUTER_ONLY_TOOLS } from "@/lib/utils";
import { JsonBlock } from "@/components/JsonBlock";
import { toast } from "sonner";

export function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [filter, setFilter] = useState("");
  const [detail, setDetail] = useState<ToolDetail | null>(null);

  useEffect(() => {
    api
      .tools()
      .then((all) => setTools(all.filter((t) => !ROUTER_ONLY_TOOLS.has(t.name))))
      .catch((e) => toast.error(e.message));
  }, []);

  const filtered = tools.filter(
    (t) =>
      t.name.toLowerCase().includes(filter.toLowerCase()) ||
      t.tags.some((tag) => tag.toLowerCase().includes(filter.toLowerCase())),
  );

  async function openDetail(name: string) {
    try {
      setDetail(await api.tool(name));
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Tools</h1>
          <p className="text-sm text-muted-foreground">
            Deterministic capabilities registered via <code>@tool</code>. {tools.length} total.
          </p>
        </div>
        <Input
          placeholder="Filter by name or tag..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="max-w-xs"
        />
      </header>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((t) => (
          <Dialog key={t.name} onOpenChange={(o) => o && openDetail(t.name)}>
            <DialogTrigger asChild>
              <Card className="cursor-pointer hover:border-foreground/40 transition-colors">
                <CardHeader className="pb-2">
                  <CardTitle className="font-mono text-base">{t.name}</CardTitle>
                  <CardDescription className="text-xs">
                    {t.owner} · v{t.version}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex flex-wrap items-center gap-1.5">
                  <ClassificationBadge value={t.classification} />
                  {t.tags.map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </CardContent>
              </Card>
            </DialogTrigger>
            <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="font-mono">{t.name}</DialogTitle>
              </DialogHeader>
              {detail && detail.name === t.name && (
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <ClassificationBadge value={detail.classification} />
                    <span className="text-xs text-muted-foreground">
                      {detail.owner} · v{detail.version}
                    </span>
                    {detail.tags.map((tag) => (
                      <Badge key={tag} variant="secondary" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                  <section>
                    <h3 className="text-sm font-semibold mb-2">Tool card</h3>
                    <pre className="text-xs whitespace-pre-wrap font-mono bg-muted/50 border rounded-md p-3">
                      {detail.card}
                    </pre>
                  </section>
                  <section>
                    <h3 className="text-sm font-semibold mb-2">JSON schema</h3>
                    <JsonBlock value={detail.schema} />
                  </section>
                </div>
              )}
            </DialogContent>
          </Dialog>
        ))}
      </div>
    </div>
  );
}
