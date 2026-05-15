"use client";

import { useState } from "react";
import { Post, generatePdf } from "@/lib/api";

interface ReportButtonProps {
  posts: Post[];
  selectedIds: Set<string>;
}

export default function ReportButton({ posts, selectedIds }: ReportButtonProps) {
  const [generating, setGenerating] = useState(false);

  const selectedPosts = posts.filter(p => selectedIds.has(p.id));

  const handleGenerate = async () => {
    if (!selectedPosts.length) return;
    setGenerating(true);
    try {
      await generatePdf(selectedPosts);
    } catch (err) {
      console.error("PDF error:", err);
      alert("Error al generar el PDF. Verificá que el backend esté activo.");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <button
      className="btn btn-gold"
      onClick={handleGenerate}
      disabled={generating || selectedPosts.length === 0}
      title={selectedPosts.length === 0 ? "Seleccioná al menos un post" : `Generar PDF con ${selectedPosts.length} post(s)`}
      style={{ padding: "10px 18px", fontSize: "13px" }}
    >
      {generating ? (
        <>
          <span style={{ animation: "spin 1s linear infinite", display: "inline-block" }}>⟳</span>
          Generando...
        </>
      ) : (
        <>
          📄 Informe PDF
          {selectedPosts.length > 0 && (
            <span style={{
              background: "rgba(0,0,0,0.2)", borderRadius: "10px",
              padding: "0px 7px", fontSize: "11px", fontWeight: 700,
            }}>
              {selectedPosts.length}
            </span>
          )}
        </>
      )}
      <style>{`@keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }`}</style>
    </button>
  );
}
