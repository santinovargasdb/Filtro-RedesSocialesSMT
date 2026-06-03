"use client";

import { useEffect, useState } from "react";

export type Theme = "light" | "dark";

/**
 * Devuelve el tema activo ("light" | "dark") y se re-renderiza cuando cambia.
 *
 * El tema vive como atributo `data-theme` en <html> (lo togglea ThemeToggle y lo
 * setea el script inline del <head> antes del paint). Como no hay un contexto de
 * tema, este hook lo lee del DOM y observa sus cambios con un MutationObserver,
 * así los componentes con estilos inline (PostCard, ResultsGrid, SearchPanel)
 * pueden colorear según el tema sin acoplarse a ThemeToggle.
 *
 * Inicia en "light" y corrige en el efecto (igual que ThemeToggle) para no romper
 * la hidratación: el HTML del server siempre asume "light".
 */
export function useTheme(): Theme {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const el = document.documentElement;
    const read = () => setTheme((el.getAttribute("data-theme") as Theme) || "light");
    read();
    const observer = new MutationObserver(read);
    observer.observe(el, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);

  return theme;
}
