import { NavLink, Outlet } from "react-router-dom";
import { Mic, Clock, Settings, Waves } from "lucide-react";

const NAV = [
  { to: "/", icon: Mic, label: "Transcribe" },
  { to: "/history", icon: Clock, label: "History" },
  { to: "/settings", icon: Settings, label: "Settings" },
] as const;

export default function Layout() {
  return (
    <div className="flex min-h-dvh">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 border-r border-border-subtle bg-surface flex flex-col">
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-5 py-5">
          <Waves className="w-5 h-5 text-amber" />
          <span
            className="text-lg font-semibold tracking-tight text-text"
            style={{ fontFamily: "var(--font-display)" }}
          >
            scribe
          </span>
        </div>

        {/* Nav */}
        <nav className="flex flex-col gap-0.5 px-3 mt-2">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? "bg-surface-raised text-text font-medium"
                    : "text-text-secondary hover:text-text hover:bg-surface-hover"
                }`
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Bottom */}
        <div className="mt-auto px-5 pb-5">
          <div className="text-[11px] font-mono text-text-muted">
            scribe ui
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
