import { useEffect, useState } from "react";
import { api, type SkillSummary, type SkillDetail } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ClassificationBadge } from "@/components/ClassificationBadge";
import { ROUTER_ONLY_SKILLS } from "@/lib/utils";
import { toast } from "sonner";

export function SkillsPage() {
  const [skills, setSkills] = useState<SkillSummary[]>([]);
  const [detail, setDetail] = useState<SkillDetail | null>(null);

  useEffect(() => {
    api
      .skills()
      .then((all) => setSkills(all.filter((s) => !ROUTER_ONLY_SKILLS.has(s.name))))
      .catch((e) => toast.error(e.message));
  }, []);

  async function openDetail(name: string) {
    try {
      setDetail(await api.skill(name));
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Skills</h1>
        <p className="text-sm text-muted-foreground">
          SKILL.md playbooks that compose existing tools. {skills.length} total.
        </p>
      </header>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {skills.map((s) => (
          <Dialog key={s.name} onOpenChange={(o) => o && openDetail(s.name)}>
            <DialogTrigger asChild>
              <Card className="cursor-pointer hover:border-foreground/40 transition-colors">
                <CardHeader>
                  <CardTitle className="font-mono text-base">{s.name}</CardTitle>
                  <CardDescription className="text-xs">v{s.version}</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground line-clamp-3">{s.description}</p>
                </CardContent>
              </Card>
            </DialogTrigger>
            <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="font-mono">{s.name}</DialogTitle>
              </DialogHeader>
              {detail && detail.name === s.name && (
                <div className="space-y-4">
                  <p className="text-sm text-muted-foreground">{detail.description}</p>
                  <div className="flex flex-wrap items-center gap-2">
                    <ClassificationBadge value={detail.manifest.classification} />
                    <span className="text-xs text-muted-foreground">
                      {detail.manifest.owner} · v{detail.version}
                    </span>
                  </div>
                  <section>
                    <h3 className="text-sm font-semibold mb-2">Required tools</h3>
                    <div className="flex flex-wrap gap-1.5">
                      {detail.manifest.requires_tools.map((t) => (
                        <Badge key={t} variant="outline" className="font-mono text-xs">
                          {t}
                        </Badge>
                      ))}
                    </div>
                  </section>
                  <section>
                    <h3 className="text-sm font-semibold mb-2">SKILL.md body</h3>
                    <pre className="text-xs whitespace-pre-wrap font-mono bg-muted/50 border rounded-md p-3 max-h-[40vh] overflow-y-auto">
                      {detail.body}
                    </pre>
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
