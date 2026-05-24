import { useEffect, useState } from "react";
import {
  api,
  type EvalCase,
  type EvalJob,
  type CaseResult,
  type EvalResultsFile,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { JsonBlock } from "@/components/JsonBlock";
import { toast } from "sonner";
import { Play, CheckCircle2, XCircle, Loader2 } from "lucide-react";

export function EvalsPage() {
  const [cases, setCases] = useState<EvalCase[]>([]);
  const [results, setResults] = useState<EvalResultsFile[]>([]);
  const [job, setJob] = useState<EvalJob | null>(null);
  const [packFilter, setPackFilter] = useState<string>("__all__");
  const [caseFilter, setCaseFilter] = useState<string>("__all__");
  const [useJudge, setUseJudge] = useState<boolean>(true);
  const [running, setRunning] = useState<boolean>(false);

  useEffect(() => {
    api.evalCases().then(setCases).catch((e) => toast.error(e.message));
    api.evalResults().then(setResults).catch((e) => toast.error(e.message));
  }, []);

  const packs = Array.from(new Set(cases.map((c) => c.pack))).sort();

  async function runEval() {
    setRunning(true);
    setJob(null);
    let started: EvalJob;
    try {
      started = await api.startEval(
        packFilter === "__all__" ? null : packFilter,
        caseFilter === "__all__" ? null : caseFilter,
        useJudge,
      );
    } catch (e) {
      toast.error((e as Error).message);
      setRunning(false);
      return;
    }
    setJob(started);

    const es = new EventSource(api.evalJobStreamUrl(started.job_id));
    const handle = (ev: MessageEvent) => {
      try {
        const data = JSON.parse(ev.data);
        if (data?.job_id && (data.status === "done" || data.status === "error")) {
          setJob(data);
          setRunning(false);
          es.close();
          api.evalResults().then(setResults);
          return;
        }
        if (data?.type === "case_done" && data.result) {
          setJob((prev) =>
            prev
              ? { ...prev, case_results: [...prev.case_results, data.result] }
              : prev,
          );
        }
      } catch {
        /* heartbeat */
      }
    };
    ["message", "job_started", "case_done", "job_done", "error"].forEach((t) =>
      es.addEventListener(t, handle as EventListener),
    );
    es.addEventListener("done", handle as EventListener);
    es.onerror = () => {
      es.close();
      setRunning(false);
    };
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Evals</h1>
        <p className="text-sm text-muted-foreground">
          YAML-driven case suite + LLM-as-judge. {cases.length} cases.
        </p>
      </header>

      <Tabs defaultValue="run">
        <TabsList>
          <TabsTrigger value="run">Run</TabsTrigger>
          <TabsTrigger value="cases">Cases</TabsTrigger>
          <TabsTrigger value="results">Results history</TabsTrigger>
        </TabsList>

        {/* Run tab */}
        <TabsContent value="run" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Configure</CardTitle>
            </CardHeader>
            <CardContent className="grid sm:grid-cols-3 gap-4">
              <div>
                <Label className="text-xs">Pack</Label>
                <Select value={packFilter} onValueChange={setPackFilter}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">all packs</SelectItem>
                    {packs.map((p) => (
                      <SelectItem key={p} value={p}>{p}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Case</Label>
                <Select value={caseFilter} onValueChange={setCaseFilter}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">all cases</SelectItem>
                    {cases
                      .filter((c) => packFilter === "__all__" || c.pack === packFilter)
                      .map((c) => (
                        <SelectItem key={c.id} value={c.id}>
                          {c.id}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={useJudge}
                    onChange={(e) => setUseJudge(e.target.checked)}
                    className="size-4"
                  />
                  use LLM judge
                </label>
              </div>
            </CardContent>
          </Card>

          <Button onClick={runEval} disabled={running} size="lg">
            {running ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />}
            {running ? "Running..." : "Run evals"}
          </Button>

          {job && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  Live job
                  <span className="font-mono text-xs text-muted-foreground">{job.job_id}</span>
                  <Badge variant={job.status === "done" ? "default" : "secondary"}>
                    {job.status}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {job.case_results.map((cr) => (
                  <CaseRow key={cr.case_id} cr={cr} />
                ))}
                {job.case_results.length === 0 && (
                  <div className="text-sm text-muted-foreground py-2">Waiting for first case...</div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Cases tab */}
        <TabsContent value="cases" className="space-y-3">
          {cases.map((c) => (
            <Card key={c.id}>
              <CardHeader>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <CardTitle className="font-mono text-sm">{c.id}</CardTitle>
                    <CardDescription className="text-xs">
                      pack <code>{c.pack}</code> · timeout {c.timeout}s · {c.assertions.length} assertion(s)
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground">{c.description}</p>
                <div>
                  <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
                    User message
                  </div>
                  <div className="text-sm whitespace-pre-wrap border rounded-md p-2 bg-muted/30">
                    {c.user_message}
                  </div>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {c.assertions.map((a, i) => (
                    <Badge key={i} variant="outline" className="text-xs font-mono">
                      {a.kind}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        {/* Results tab */}
        <TabsContent value="results" className="space-y-3">
          {results.length === 0 && (
            <div className="text-sm text-muted-foreground border rounded-md p-6 text-center">
              No results yet. Run an eval to generate one.
            </div>
          )}
          {results.map((r) => (
            <Card key={r.file}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="font-mono text-sm">{r.file}</CardTitle>
                  <Badge variant={r.passed === r.total ? "default" : "destructive"}>
                    {r.passed}/{r.total} passed
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                {r.cases.map((cr) => (
                  <CaseRow key={cr.case_id + cr.run_id} cr={cr} />
                ))}
              </CardContent>
            </Card>
          ))}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function CaseRow({ cr }: { cr: CaseResult }) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <button className="w-full border rounded-md px-3 py-2 flex items-center gap-2 text-sm hover:bg-accent/40 transition-colors text-left">
          {cr.passed ? (
            <CheckCircle2 className="size-4 text-emerald-600" />
          ) : (
            <XCircle className="size-4 text-rose-600" />
          )}
          <span className="font-mono">{cr.case_id}</span>
          <Badge variant="outline" className="text-xs ml-1">
            {cr.pack}
          </Badge>
          <span className="ml-auto text-xs text-muted-foreground">{cr.duration_s}s</span>
        </button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-mono">{cr.case_id}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Badge variant={cr.passed ? "default" : "destructive"}>
              {cr.passed ? "passed" : "failed"}
            </Badge>
            <span className="text-muted-foreground">
              pack <code>{cr.pack}</code> · run <code className="font-mono">{cr.run_id}</code> · {cr.duration_s}s
            </span>
          </div>
          {cr.error && (
            <div className="text-sm border border-destructive/40 bg-destructive/10 rounded-md p-3">
              <div className="font-medium text-destructive">Error</div>
              <div className="font-mono text-xs mt-1">{cr.error}</div>
            </div>
          )}
          <section>
            <h3 className="text-sm font-semibold mb-2">Assertions</h3>
            <div className="space-y-2">
              {cr.assertion_results.map((r, i) => (
                <div
                  key={i}
                  className="border rounded-md px-3 py-2 flex items-start gap-2 text-sm"
                >
                  {r.passed ? (
                    <CheckCircle2 className="size-4 text-emerald-600 mt-0.5" />
                  ) : (
                    <XCircle className="size-4 text-rose-600 mt-0.5" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs">{r.kind}</span>
                      {r.score != null && (
                        <Badge variant="secondary" className="text-xs">
                          {r.score}/5
                        </Badge>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground">{r.detail}</div>
                    {r.rationale && (
                      <div className="text-xs italic text-muted-foreground mt-1">
                        ↳ {r.rationale}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
          {cr.final_text && (
            <section>
              <h3 className="text-sm font-semibold mb-2">Final reply</h3>
              <pre className="text-sm whitespace-pre-wrap border rounded-md p-3 bg-muted/30">
                {cr.final_text}
              </pre>
            </section>
          )}
          {cr.stats && (
            <details>
              <summary className="text-xs text-muted-foreground cursor-pointer">stats</summary>
              <JsonBlock value={cr.stats} className="mt-2" />
            </details>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
