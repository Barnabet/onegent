import { NavLink, Outlet } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";

const NAV = [
  { to: "/", label: "Chat" },
  { to: "/runs", label: "Runs" },
  { to: "/packs", label: "Packs" },
  { to: "/skills", label: "Skills" },
  { to: "/tools", label: "Tools" },
  { to: "/evals", label: "Evals" },
];

export function Layout() {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <header className="border-b">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="size-6 rounded bg-primary" />
            <span className="font-semibold tracking-tight">CIB Agents</span>
            <span className="text-xs text-muted-foreground hidden sm:inline">
              skills × tools
            </span>
          </div>
          <nav className="flex items-center gap-1">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded-md text-sm transition-colors ${
                    isActive
                      ? "bg-accent text-accent-foreground font-medium"
                      : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
                  }`
                }
              >
                {n.label}
              </NavLink>
            ))}
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
