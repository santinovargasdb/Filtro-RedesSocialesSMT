const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Post {
  id: string;
  network: "twitter" | "instagram" | "tiktok";
  author: string;
  author_url: string;
  text: string;
  date: string;
  post_url: string;
  relevance_score: number;
  relevance_level: "alta" | "media" | "baja";
  matched_terms: string[];
  video_url: string | null;
}

export interface SearchRequest {
  keywords: string[];
  hashtags: string[];
  accounts: string[];
  networks: ("twitter" | "instagram" | "tiktok")[];
  date: string;
  // Modo SMATA: true = criterio estricto (solo SMATA/automotor),
  // false = monitor de prensa amplio.
  smata_mode: boolean;
}

export interface SearchResponse {
  posts: Post[];
  summary: {
    total: number;
    by_network: Record<string, number>;
    top_keywords: string[];
  };
}

// El backend corre en Render free tier, que duerme la instancia tras ~15 min de
// inactividad. La primera request la despierta y puede tardar ~40-50s; mientras
// arranca, el proxy de Render responde 502 sin headers CORS (se ve como "error de
// CORS" en el navegador). Por eso usamos un timeout amplio y un reintento.
const SEARCH_TIMEOUT_MS = 100_000;

async function postJson(path: string, body: unknown, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timer);
  }
}

export type SearchStatus = "connecting" | "waking";

export async function searchPosts(
  req: SearchRequest,
  onStatus?: (status: SearchStatus) => void,
): Promise<SearchResponse> {
  const attempt = async (): Promise<SearchResponse> => {
    const res = await postJson("/api/search", req, SEARCH_TIMEOUT_MS);
    if (!res.ok) throw new Error(`Search failed: ${res.status} ${res.statusText}`);
    return res.json();
  };

  onStatus?.("connecting");
  try {
    return await attempt();
  } catch {
    // Falló el primer intento: muy probablemente Render estaba despertando del
    // modo reposo. Avisamos y reintentamos una vez con todo el timeout de nuevo.
    onStatus?.("waking");
    try {
      return await attempt();
    } catch {
      throw new Error(
        "No se pudo conectar con el servidor. Puede estar despertando del modo reposo; " +
        "esperá unos segundos y volvé a intentar.",
      );
    }
  }
}

export async function generateDocx(posts: Post[]): Promise<void> {
  const res = await fetch(`${API_BASE}/api/generate-docx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ posts }),
  });
  if (!res.ok) throw new Error("DOCX generation failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `informe_smata_${new Date().toISOString().split("T")[0]}.docx`;
  a.click();
  URL.revokeObjectURL(url);
}
