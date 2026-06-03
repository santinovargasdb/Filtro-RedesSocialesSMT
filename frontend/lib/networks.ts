/**
 * Color de acento por red social, sensible al tema.
 *
 * TikTok usa el negro (#000000) como color de marca: perfecto sobre fondo claro,
 * pero invisible sobre el fondo oscuro de la app (se fusiona con el contenedor).
 * Por eso en modo oscuro lo cambiamos por su cian característico (#00f2fe), que
 * contrasta de forma excelente. X (azul) e Instagram (rosa) ya contrastan bien en
 * ambos temas, así que su color no depende del tema.
 *
 * Devuelve siempre un HEX para que el patrón `color + "20"` (tinte con alpha) que
 * usan los componentes siga produciendo un color válido (#RRGGBBAA).
 */
const NETWORK_BASE: Record<string, string> = {
  twitter: "#1DA1F2",
  instagram: "#E1306C",
  tiktok: "#000000",
};

// Acento de TikTok en modo oscuro: su cian de marca.
const TIKTOK_DARK = "#00f2fe";

export function networkColor(network: string, isDark: boolean): string {
  if (network === "tiktok") return isDark ? TIKTOK_DARK : NETWORK_BASE.tiktok;
  return NETWORK_BASE[network] ?? "#888";
}
