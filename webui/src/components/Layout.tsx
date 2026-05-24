import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ChevronDown, MessageSquare } from "lucide-react";
import { Link } from "react-router-dom";

const SECONDARY = [
  { to: "/runs", label: "Runs", hint: "all live + persisted runs" },
  { to: "/packs", label: "Packs", hint: "specialist agent bundles" },
  { to: "/skills", label: "Skills", hint: "SKILL.md playbooks" },
  { to: "/tools", label: "Tools", hint: "deterministic capabilities" },
  { to: "/evals", label: "Evals", hint: "YAML cases + judge" },
];

export function Layout() {
  const location = useLocation();
  const currentSecondary = SECONDARY.find((n) => location.pathname.startsWith(n.to));

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <header className="border-b">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-2 shrink-0">
            <img src="/logo.png" alt="CIB Agents" className="size-7 rounded" />
            <span className="font-semibold tracking-tight">CIB Agents</span>
            <span className="text-xs text-muted-foreground hidden sm:inline">
              orchestrator
            </span>
          </Link>

          <nav className="flex items-center gap-1">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                `inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
                  isActive
                    ? "bg-accent text-accent-foreground font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
                }`
              }
            >
              <MessageSquare className="size-3.5" />
              Chat
            </NavLink>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className={
                    currentSecondary
                      ? "bg-accent text-accent-foreground font-medium"
                      : "text-muted-foreground"
                  }
                >
                  {currentSecondary ? currentSecondary.label : "More"}
                  <ChevronDown className="size-3.5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel className="text-xs text-muted-foreground">
                  Catalog & history
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                {SECONDARY.map((n) => (
                  <DropdownMenuItem key={n.to} asChild>
                    <Link to={n.to} className="flex flex-col items-start gap-0.5">
                      <span className="font-medium">{n.label}</span>
                      <span className="text-xs text-muted-foreground">{n.hint}</span>
                    </Link>
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-6">
        <Outlet />
      </main>
      <Toaster richColors position="top-right" />
    </div>
  );
}
