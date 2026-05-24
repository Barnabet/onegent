import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type PackSummary, type PackDetail } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ClassificationBadge } from "@/components/ClassificationBadge";
import { JsonBlock } from "@/components/JsonBlock";
import { toast } from "sonner";
import { PlayCircle } from "lucide-react";

export function PacksPage() {
  const [packs, setPacks] = useState<PackSummary[]>([]);
  const [detail, setDetail] = useState<PackDetail | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.packs().then(setPacks).catch((e) => toast.error(e.message));
  }, []);

  async function openDetail(name: string) {
    try {
      setDetail(await api.pack(name));
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Packs</h1>
        <p className="text-sm text-muted-foreground">
          Persona-scoped bundles of skills. {packs.length} total.
        </p>
      </header>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {packs.map((p) => (
          <Dialog key={p.name} onOpenChange={(o) => o && openDetail(p.name)}>
            <DialogTrigger asChild>
              <Card
                id={p.name}
                className="cursor-pointer hover:border-foreground/40 transition-colors"
              >
                <CardHeader>
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="font-mono text-base">{p.name}</CardTitle>
                    <ClassificationBadge value={p.classification} />
                  </div>
                  <CardDescription className="text-xs">
                    {p.owner} · v{p.version}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm text-muted-foreground line-clamp-3">{p.description}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {p.skills.map((s) => (
                      <Badge key={s} variant="outline" className="font-mono text-xs">
                        {s}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </DialogTrigger>
            <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="font-mono">{p.name}</DialogTitle>
              </DialogHeader>
              {detail && detail.name === p.name && (
                <div className="space-y-4">
                  <p className="text-sm text-muted-foreground">{detail.description}</p>
                  <div className="flex flex-wrap items-center gap-2">
                    <ClassificationBadge value={detail.classification} />
                    <span className="text-xs text-muted-foreground">
                      {detail.owner} · v{detail.version} · model{" "}
                      <code className="font-mono">{detail.model}</code>
                    </span>
                  </div>
                  <section className="grid grid-cols-3 gap-3 text-xs">
                    <Stat label="effective" value={detail.effective_classification} />
                    <Stat
                      label="max tool calls"
                      value={String(detail.limits.max_tool_calls_per_run)}
                    />
                    <Stat label="timeout" value={`${detail.limits.timeout_seconds}s`} />
                  </section>
                  <section>
                    <h3 className="text-sm font-semibold mb-2">Skills</h3>
                    <div className="space-y-1.5">
                      {detail.skills.map((s) => (
                        <div key={s.name} className="border rounded-md px-3 py-2">
                          <div className="font-mono text-sm">{s.name}</div>
                          <div className="text-xs text-muted-foreground">{s.description}</div>
                        </div>
                      ))}
                    </div>
                  </section>
                  <section>
                    <h3 className="text-sm font-semibold mb-2">Effective tool set</h3>
                    <div className="flex flex-wrap gap-1.5">
                      {detail.tools.map((t) => (
                        <Badge key={t} variant="secondary" className="font-mono text-xs">
                          {t}
                        </Badge>
                      ))}
                    </div>
                  </section>
                  {detail.allowed_data_sources.length > 0 && (
                    <section>
                      <h3 className="text-sm font-semibold mb-2">Allowed data sources</h3>
                      <JsonBlock value={detail.allowed_data_sources} />
                    </section>
                  )}
                  <Button
                    variant="default"
                    onClick={() => navigate(`/?pack=${detail.name}`)}
                  >
                    <PlayCircle className="size-4" /> Try in chat
                  </Button>
                </div>
              )}
            </DialogContent>
          </Dialog>
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border rounded-md p-2">
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="font-mono text-sm">{value}</div>
    </div>
  );
}
