const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Post {
  id: string;
  network: "twitter" | "instagram" | "tiktok";
  author: string;
  author_url: string;
  text: string;
  date: string;
  post_url: string;
  video_url?: string;
  relevance_score: number;
  matched_terms: string[];
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
