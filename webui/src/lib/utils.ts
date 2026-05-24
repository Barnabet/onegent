import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Router-only resources. The router pack is the orchestrator itself — it
// fronts every chat automatically — so we hide it (and the skill / tools it
// uses) from the public catalog pages. The server still exposes them.
export const ROUTER_ONLY_PACKS = new Set(["router"])
export const ROUTER_ONLY_SKILLS = new Set(["router"])
export const ROUTER_ONLY_TOOLS = new Set([
  "orchestrator.list_packs",
  "orchestrator.delegate",
])
