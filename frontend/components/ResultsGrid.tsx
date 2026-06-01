"use client";

import { Post } from "@/lib/api";
import PostCard from "./PostCard";

interface ResultsGridProps {
  posts: Post[];
  selectedIds: Set<string>;
  onToggle: (id: string) => void;
  loading: boolean;
  hasSearched?: boolean;
  summary?: {
    total: number;
    by_network: Record<string, number>;
    top_keywords: string[];
  };
}

function SkeletonCard() {
  return (
    <div style={{
      background: "var(--bg-card)", border: "1px solid var(--border-color)",
      borderRadius: "var(--radius-md)", padding: "18px",
      display: "flex", flexDirection: "column", gap: "12px",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <div style={{ width: "90px", height: "22px", borderRadius: "4px", background: "rgba(255,255,255,0.06)", animation: "pulse 1.5s ease-in-out infinite" }} />
        <div style={{ width: "60px", height: "22px", borderRadius: "20px", background: "rgba(255,255,255,0.06)", animation: "pulse 1.5s ease-in-out infinite" }} />
      </div>
      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
        <div style={{ width: "30px", height: "30px", borderRadius: "50%", background: "rgba(255,255,255,0.06)", animation: "pulse 1.5s ease-in-out infinite" }} />
        <div style={{ width: "120px", height: "14px", borderRadius: "4px", background: "rgba(255,255,255,0.06)", animation: "pulse 1.5s ease-in-out infinite" }} />
      </div>
      {[100, 80, 90, 60].map((w, i) => (
        <div key={i} style={{ width: `${w}%`, height: "13px", borderRadius: "4px", background: "rgba(255,255,255,0.05)", animation: "pulse 1.5s ease-in-out infinite", animationDelay: `${i * 0.1}s` }} />
      ))}
    </div>
  );
}

const NET_COLORS: Record<string, string> = {
  twitter: "#1DA1F2", instagram: "#E1306C", tiktok: "#000000",
};

export default function ResultsGrid({ posts, selectedIds, onToggle, loading, summary, hasSearched }: ResultsGridProps) {
  if (loading) {
    return (
      <div style={{ flex: 1, padding: "24px", overflowY: "auto" }}>
        <div style={{ marginBottom: "20px" }}>
          <div style={{ width: "200px", height: "16px", borderRadius: "4px", background: "rgba(255,255,255,0.07)", animation: "pulse 1.5s ease-in-out infinite" }} />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "16px" }}>
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
        <style>{`@keyframes pulse { 0%,100%{opacity:0.5} 50%{opacity:1} }`}</style>
      </div>
    );
  }

  if (!posts.length) {
    return (
      <div style={{
        flex: 1, display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center", gap: "16px",
        color: "var(--text-muted)", padding: "60px",
      }}>
        <div style={{ fontSize: "48px", opacity: 0.3 }}>{hasSearched ? "🔍" : "📡"}</div>
        <div style={{ fontSize: "16px", fontWeight: 600 }}>
          {hasSearched ? "No se encontraron resultados" : "Configurá tu búsqueda y presioná Buscar"}
        </div>
        <div style={{ fontSize: "13px" }}>
          {hasSearched
            ? "Probá con otra keyword, sumá redes o apagá el Modo SMATA para un monitoreo más amplio."
            : "Los resultados rankeados aparecerán aquí"}
        </div>
      </div>
    );
  }

  return (
    <div style={{ flex: 1, padding: "24px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Summary bar */}
      {summary && (
        <div style={{
          display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center",
          padding: "14px 16px", borderRadius: "var(--radius-md)",
          background: "var(--bg-card)", border: "1px solid var(--border-color)",
        }}>
          <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>
            {summary.total} posts encontrados
          </span>
          <span style={{ color: "var(--border-color)" }}>·</span>
          {Object.entries(summary.by_network).map(([net, count]) => (
            <span key={net} style={{ fontSize: "12px", color: NET_COLORS[net] ?? "#888", fontWeight: 600 }}>
              {net}: {count}
            </span>
          ))}
          <span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--text-muted)" }}>
            {selectedIds.size} seleccionados para el informe
          </span>
        </div>
      )}

      {/* Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "16px" }}>
        {posts.map(post => (
          <PostCard
            key={post.id}
            post={post}
            selected={selectedIds.has(post.id)}
            onToggle={onToggle}
          />
        ))}
      </div>
    </div>
  );
}
