// Minimal HTTP client for the agents API.
// All endpoints are proxied via Vite to http://127.0.0.1:8000 during dev.

export type Tool = {
  name: string;
  classification: string;
  owner: string;
  tags: string[];
  version: string;
};

export type ToolDetail = Tool & {
  card: string;
  schema: Record<string, unknown>;
};

export type SkillSummary = {
  name: string;
  description: string;
  version: string;
};

export type SkillDetail = {
  name: string;
  description: string;
  version: string;
  body: string;
  manifest: {
    name: string;
    requires_tools: string[];
    classification: string;
    owner: string;
    references?: string[];
  };
};

export type PackSummary = {
  name: string;
  version: string;
  owner: string;
  description: string;
  skills: string[];
  classification: string;
  model: string;
  error?: string;
};

export type PackDetail = {
  name: string;
  version: string;
  owner: string;
  description: string;
  classification: string;
  allowed_data_sources: string[];
  model: string;
  limits: { max_tool_calls_per_run: number; max_tokens_per_run: number; timeout_seconds: number };
  skills: { name: string; description: string }[];
  tools: string[];
  effective_classification: string;
};

export type RunSummary = {
  run_id: string;
  pack: string;
  user_message: string;
  user_id: string;
  started_at: number;
  status: "running" | "done" | "error" | "persisted";
  error: string | null;
  final_text: string;
  stats: { turns: number; tool_calls: number; finish_reason: string } | null;
  events_count: number;
};

export type RunEvent = {
  type: string;
  // Common event fields (loosely typed — different per event type):
  name?: string;
  call_id?: string;
  args?: Record<string, unknown>;
  payload?: { ok: boolean; data?: unknown; error?: { code: string; message: string } | null; warnings?: string[]; citations?: unknown[] };
  ok?: boolean;
  delta?: string;
  final?: string;
  message?: string;
  stats?: Record<string, unknown>;
  // Set by orchestrator.delegate to mark events that came from a sub-agent.
  subagent_of?: string;
};

export type RunDetail = RunSummary & { events: RunEvent[] };

export type FileMeta = {
  file_id: string;
  conversation_id: string;
  name: string;
  size: number;
  mime: string;
  uploaded_at: number;
  path: string;
};

export type ConversationMessage = {
  role: "user" | "assistant";
  content: string;
  ts: number;
  run_id?: string | null;
};

export type ConversationSummary = {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  message_count: number;
  file_count: number;
};

export type ConversationDetail = {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  messages: ConversationMessage[];
  file_ids: string[];
  files: FileMeta[];
};

export type EvalAssertion = { kind: string; [k: string]: unknown };

export type EvalCase = {
  id: string;
  pack: string;
  description: string;
  user_message: string;
  timeout: number;
  assertions: EvalAssertion[];
  source_path: string | null;
};

export type AssertionResult = {
  kind: string;
  passed: boolean;
  detail: string;
  score: number | null;
  rationale: string | null;
};

export type CaseResult = {
  case_id: string;
  pack: string;
  run_id: string;
  passed: boolean;
  duration_s: number;
  final_text: string;
  assertion_results: AssertionResult[];
  error: string | null;
  stats: Record<string, unknown> | null;
};

export type EvalJob = {
  job_id: string;
  pack: string | null;
  case: string | null;
  use_judge: boolean;
  started_at: number;
  status: "running" | "done" | "error";
  error: string | null;
  case_results: CaseResult[];
};

export type EvalResultsFile = {
  file: string;
  total: number;
  passed: number;
  cases: CaseResult[];
};

async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText} on ${path}`);
  return r.json() as Promise<T>;
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText} on ${path}`);
  return r.json() as Promise<T>;
}

export const api = {
  health: () => getJSON<{ ok: boolean; tools: number }>("/api/health"),

  tools: () => getJSON<Tool[]>("/api/tools"),
  tool: (name: string) => getJSON<ToolDetail>(`/api/tools/${encodeURIComponent(name)}`),

  skills: () => getJSON<SkillSummary[]>("/api/skills"),
  skill: (name: string) => getJSON<SkillDetail>(`/api/skills/${encodeURIComponent(name)}`),

  packs: () => getJSON<PackSummary[]>("/api/packs"),
  pack: (name: string) => getJSON<PackDetail>(`/api/packs/${encodeURIComponent(name)}`),

  startRun: (
    user_message: string,
    conversation_id: string,
    allowed_packs?: string[],
  ) =>
    postJSON<RunSummary>("/api/runs", {
      user_message,
      conversation_id,
      allowed_packs,
    }),
  runs: () => getJSON<RunSummary[]>("/api/runs"),
  run: (id: string) => getJSON<RunDetail>(`/api/runs/${encodeURIComponent(id)}`),
  runStreamUrl: (id: string) => `/api/runs/${encodeURIComponent(id)}/stream`,

  listFiles: (conversation_id: string) =>
    getJSON<FileMeta[]>(`/api/files?conversation_id=${encodeURIComponent(conversation_id)}`),
  uploadFile: async (conversation_id: string, file: File): Promise<FileMeta> => {
    const fd = new FormData();
    fd.append("conversation_id", conversation_id);
    fd.append("file", file);
    const r = await fetch("/api/files", { method: "POST", body: fd });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText} on /api/files`);
    return r.json();
  },
  deleteFile: async (file_id: string): Promise<void> => {
    const r = await fetch(`/api/files/${encodeURIComponent(file_id)}`, { method: "DELETE" });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText} on /api/files/${file_id}`);
  },

  conversations: () => getJSON<ConversationSummary[]>("/api/conversations"),
  conversation: (id: string) =>
    getJSON<ConversationDetail>(`/api/conversations/${encodeURIComponent(id)}`),
  createConversation: (title?: string) =>
    postJSON<ConversationDetail>("/api/conversations", { title: title ?? null }),
  renameConversation: async (id: string, title: string): Promise<ConversationDetail> => {
    const r = await fetch(`/api/conversations/${encodeURIComponent(id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText} on PATCH /api/conversations/${id}`);
    return r.json();
  },
  deleteConversation: async (id: string): Promise<void> => {
    const r = await fetch(`/api/conversations/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText} on /api/conversations/${id}`);
  },

  evalCases: () => getJSON<EvalCase[]>("/api/evals/cases"),
  startEval: (pack: string | null, caseId: string | null, useJudge: boolean) =>
    postJSON<EvalJob>("/api/evals/run", { pack, case: caseId, use_judge: useJudge }),
  evalJobs: () => getJSON<EvalJob[]>("/api/evals/jobs"),
  evalJob: (id: string) => getJSON<EvalJob>(`/api/evals/jobs/${encodeURIComponent(id)}`),
  evalJobStreamUrl: (id: string) => `/api/evals/jobs/${encodeURIComponent(id)}/stream`,
  evalResults: () => getJSON<EvalResultsFile[]>("/api/evals/results"),
};
