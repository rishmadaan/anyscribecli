import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { Mic, Clock, Settings, Waves, Power } from "lucide-react";
import SetupBanner from "./SetupBanner";

const NAV = [
  { to: "/", icon: Mic, label: "Transcribe" },
  { to: "/history", icon: Clock, label: "History" },
  { to: "/settings", icon: Settings, label: "Settings" },
] as const;

export default function Layout() {
  const [confirmShutdown, setConfirmShutdown] = useState(false);
  const [stopped, setStopped] = useState(false);

  const handleShutdown = async () => {
    try {
      await fetch("/api/shutdown", { method: "POST" });
    } catch {
      // Expected — server is shutting down
    }
    setStopped(true);
    // Try to close the tab (works if opened by JS, e.g. window.open)
    setTimeout(() => {
      window.close();
    }, 300);
  };

  if (stopped) {
    return (
      <div className="flex items-center justify-center min-h-dvh bg-bg">
        <div className="text-center">
          <Power className="w-8 h-8 text-text-muted mx-auto mb-3" />
          <p className="text-lg font-medium text-text mb-1">Server stopped</p>
          <p className="text-sm text-text-muted">You can close this tab.</p>
        </div>
      </div>
    );
  }

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

        {/* Bottom — shutdown */}
        <div className="mt-auto px-3 pb-4">
          {!confirmShutdown ? (
            <button
              onClick={() => setConfirmShutdown(true)}
              className="
                flex items-center gap-2 w-full px-3 py-2 rounded-lg
                text-xs text-text-muted hover:text-red hover:bg-surface-hover
                transition-colors cursor-pointer
              "
            >
              <Power className="w-3.5 h-3.5" />
              Quit
            </button>
          ) : (
            <div className="flex items-center gap-1.5">
              <button
                onClick={handleShutdown}
                className="
                  flex items-center gap-1.5 px-3 py-2 rounded-lg
                  text-xs text-red bg-red/5 border border-red/20
                  hover:bg-red/10 transition-colors cursor-pointer
                "
              >
                <Power className="w-3.5 h-3.5" />
                Quit?
              </button>
              <button
                onClick={() => setConfirmShutdown(false)}
                className="text-xs text-text-muted hover:text-text cursor-pointer px-2 py-2"
              >
                no
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <SetupBanner />
        <Outlet />
      </main>
    </div>
  );
}
