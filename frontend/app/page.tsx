"use client";

import { useState, useCallback } from "react";
import SearchPanel from "@/components/SearchPanel";
import type { SearchRequest } from "@/lib/api";
import ResultsGrid from "@/components/ResultsGrid";
import ReportButton from "@/components/ReportButton";
import { searchPosts, Post, SearchResponse } from "@/lib/api";

export default function Home() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [summary, setSummary] = useState<SearchResponse["summary"] | undefined>();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const handleSearch = useCallback(async (params: SearchRequest) => {
    setLoading(true);
    setError(null);
    setStatus(null);
    setPosts([]);
    setSelectedIds(new Set());
    try {
      const result = await searchPosts(params, (s) => {
        setStatus(
          s === "waking"
            ? "El servidor estaba en reposo. Despertándolo… puede tardar ~40s."
            : "Conectando con el servidor…",
        );
      });
      setPosts(result.posts);
      setSummary(result.summary);
      // Auto-select posts with score >= 50
      setSelectedIds(new Set(result.posts.filter(p => p.relevance_score >= 50).map(p => p.id)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al conectar con el servidor");
    } finally {
      setLoading(false);
      setStatus(null);
    }
  }, []);

  const handleToggle = useCallback((id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id); // Si ya estaba seleccionado, lo saca
      } else {
        next.add(id);    // Si no estaba, lo agrega al informe de SMATA
      }
      return next;
    });
  }, []);

  const handleSelectAll = () => setSelectedIds(new Set(posts.map(p => p.id)));
  const handleDeselectAll = () => setSelectedIds(new Set());

  return (
    <main style={{ display: "flex", height: "calc(100vh - 60px)" }}>
      <SearchPanel onSearch={handleSearch} loading={loading} />

      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Toolbar */}
        {posts.length > 0 && (
          <div style={{
            display: "flex", alignItems: "center", gap: "12px",
            padding: "12px 24px",
            borderBottom: "1px solid var(--border-color)",
            background: "var(--bg-secondary)",
          }}>
            <button
              className="btn"
              style={{ background: "transparent", border: "1px solid var(--border-color)", color: "var(--text-secondary)", padding: "6px 12px", fontSize: "12px" }}
              onClick={handleSelectAll}
            >
              Seleccionar todo
            </button>
            <button
              className="btn"
              style={{ background: "transparent", border: "1px solid var(--border-color)", color: "var(--text-secondary)", padding: "6px 12px", fontSize: "12px" }}
              onClick={handleDeselectAll}
            >
              Deseleccionar todo
            </button>
            <div style={{ marginLeft: "auto" }}>
              <ReportButton posts={posts} selectedIds={selectedIds} />
            </div>
          </div>
        )}

        {/* Status banner (cold start / conexión) */}
        {loading && status && (
          <div style={{
            margin: "16px 24px 0",
            padding: "12px 16px",
            borderRadius: "var(--radius-sm)",
            background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.3)",
            color: "#93C5FD", fontSize: "13px",
          }}>
            ⏳ {status}
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div style={{
            margin: "16px 24px 0",
            padding: "12px 16px",
            borderRadius: "var(--radius-sm)",
            background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
            color: "#F87171", fontSize: "13px",
          }}>
            ⚠️ {error}
          </div>
        )}

        <ResultsGrid
          posts={posts}
          selectedIds={selectedIds}
          onToggle={handleToggle}
          loading={loading}
          summary={summary}
        />
      </div>
    </main>
  );
}
