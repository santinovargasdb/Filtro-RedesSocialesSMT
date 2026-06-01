"use client";

import { useEffect, useState } from "react";

type Theme = "light" | "dark";

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");

  // Al montar, leemos el tema ya aplicado por el script inline del <head>
  // (que corre antes del paint para evitar el flash).
  useEffect(() => {
    const current = (document.documentElement.getAttribute("data-theme") as Theme) || "light";
    setTheme(current);
  }, []);

  const toggle = () => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    if (next === "dark") {
      document.documentElement.setAttribute("data-theme", "dark");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
    try { localStorage.setItem("theme", next); } catch { /* sin localStorage */ }
  };

  const isDark = theme === "dark";
  return (
    <button
      onClick={toggle}
      aria-label={isDark ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
      title={isDark ? "Modo claro" : "Modo oscuro"}
      style={{
        display: "inline-flex", alignItems: "center", justifyContent: "center",
        gap: "6px",
        width: "auto", height: "32px", padding: "0 12px",
        borderRadius: "20px",
        background: "rgba(255,255,255,0.08)",
        border: "1px solid rgba(255,255,255,0.18)",
        color: "rgba(255,255,255,0.85)",
        fontSize: "13px", fontWeight: 600, cursor: "pointer",
        transition: "background 0.2s",
      }}
      onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.15)")}
      onMouseLeave={e => (e.currentTarget.style.background = "rgba(255,255,255,0.08)")}
    >
      <span style={{ fontSize: "15px", lineHeight: 1 }}>{isDark ? "☀️" : "🌙"}</span>
      <span>{isDark ? "Claro" : "Oscuro"}</span>
    </button>
  );
}
