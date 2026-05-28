const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Post {
  id: string;
  network: string;
  
  // 1. Soportamos tanto title como text para el cuerpo del post
  title?: string; 
  text?: string;
  content?: string;

  // 2. Soportamos el nombre del usuario
  author?: string;
  author_url?: string;
  user?: string; // Por si Python manda 'user' en vez de 'author'

  // 3. Soportamos todas las variantes de score para la relevancia
  relevance_score?: number;
  score?: number; 
  relevance?: number;

  // 4. Fecha
  date?: string;
  created_at?: string; // Por si Python usa el formato estándar de Twitter
}

export interface SearchRequest {
  keywords: string[];
  hashtags: string[];
  accounts: string[];
  networks: ("twitter" | "instagram" | "tiktok")[];
  date: string;
  strict_mode: boolean;
}

export interface SearchResponse {
  posts: Post[];
  summary: {
    total: number;
    by_network: Record<string, number>;
    top_keywords: string[];
  };
}

export async function searchPosts(req: SearchRequest): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`Search failed: ${res.statusText}`);
  return res.json();
}

export async function generatePdf(posts: Post[]): Promise<void> {
  const res = await fetch(`${API_BASE}/api/generate-pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(posts),
  });
  if (!res.ok) throw new Error("PDF generation failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `informe_smata_${new Date().toISOString().split("T")[0]}.pdf`;
  a.click();
  URL.revokeObjectURL(url);
}
