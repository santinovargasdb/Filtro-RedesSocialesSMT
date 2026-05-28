"use client";

import { Post } from "@/lib/api";
import ScoreBadge from "./ScoreBadge";

const NETWORK_META = {
  twitter:   { label: "X / Twitter", color: "#1DA1F2", icon: "𝕏" },
  instagram: { label: "Instagram",   color: "#E1306C", icon: "◉" },
  tiktok:    { label: "TikTok",      color: "#000000", icon: "♪" },
} as const;

interface PostCardProps {
  post: Post;
  selected: boolean;
  onToggle: (id: string) => void;
}

function formatDate(dateStr: string) {
  try {
    return new Date(dateStr).toLocaleString("es-AR", {
      day: "2-digit", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch { return dateStr; }
}

export default function PostCard({ post, selected, onToggle }: PostCardProps) {
  const net = NETWORK_META[post.network] ?? { label: post.network, color: "#888", icon: "●" };

  return (
    <article
      onClick={() => onToggle(post.id)}
      style={{
        background: selected ? "var(--bg-card-hover)" : "var(--bg-card)",
        border: `1px solid ${selected ? net.color + "55" : "var(--border-color)"}`,
        borderRadius: "var(--radius-md)",
        padding: "18px",
        cursor: "pointer",
        transition: "all 0.2s ease",
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        boxShadow: selected ? `0 0 0 2px ${net.color}33` : "none",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Selection indicator strip */}
      <div style={{
        position: "absolute", left: 0, top: 0, bottom: 0, width: "3px",
        background: selected ? net.color : "transparent",
        transition: "background 0.2s",
      }} />

      {/* Header row */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "8px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {/* Network badge */}
          <span style={{
            display: "inline-flex", alignItems: "center", gap: "4px",
            background: net.color + "20", border: `1px solid ${net.color}55`,
            borderRadius: "4px", padding: "2px 8px",
            fontSize: "11px", fontWeight: 700, color: net.color,
          }}>
            {net.icon} {net.label}
          </span>
          {/* Checkbox */}
          <div style={{
            width: "18px", height: "18px", borderRadius: "4px",
            border: `2px solid ${selected ? net.color : "var(--text-muted)"}`,
            background: selected ? net.color : "transparent",
            display: "flex", alignItems: "center", justifyContent: "center",
            transition: "all 0.15s", flexShrink: 0,
          }}>
            {selected && <span style={{ fontSize: "11px", color: "white", fontWeight: 700 }}>✓</span>}
          </div>
        </div>
        <ScoreBadge score={post.relevance_score || post.score || 0} />
      </div>

      {/* Author */}
      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
        <div style={{
          width: "30px", height: "30px", borderRadius: "50%",
          background: `linear-gradient(135deg, ${net.color}66, ${net.color}33)`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "13px", fontWeight: 700, color: net.color, flexShrink: 0,
        }}>
          {post.title ? post.title.charAt(0).toUpperCase() : 'X'}
        </div>
        <a
          href={post.author_url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={e => e.stopPropagation()}
          style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)", textDecoration: "none" }}
        >
          {post.title ? "Usuario de X" : ""}
        </a>
        <span style={{ fontSize: "11px", color: "var(--text-muted)", marginLeft: "auto" }}>
          {post.date ? formatDate(post.date) : "Reciente"}
        </span>
      </div>

      {/* Post text */}
      <p style={{
        fontSize: "14px", lineHeight: "1.6", color: "var(--text-secondary)",
        margin: 0,
        display: "-webkit-box", WebkitLineClamp: 5, WebkitBoxOrient: "vertical",
        overflow: "hidden",
      }}>
        {post.title || post.text || post.content || "Sin contenido"}
      </p>

      {/* Matched terms */}
{post.matched_terms && post.matched_terms?.length > 0 && (
  <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
    {post.matched_terms.slice(0, 5).map(term => (
      <span key={term} style={{
        fontSize: "11px", padding: "1px 7px", borderRadius: "3px",
        background: "rgba(76,175,80,0.12)", border: "1px solid rgba(76,175,80,0.25)",
        color: "var(--smata-green-light)",
      }}>
        {term}
      </span>
    ))}
    {post.matched_terms.length > 5 && (
      <span style={{ fontSize: "11px", color: "var(--text-muted)", alignSelf: "center" }}>
        +{post.matched_terms.length - 5}
      </span>
    )}
  </div>
)}
      {/* Footer link */}
      <div style={{ display: "flex", gap: "12px" }}>
        <a
          href={post.post_url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={e => e.stopPropagation()}
          style={{
            fontSize: "11px", color: net.color, textDecoration: "none",
            opacity: 0.7, display: "flex", alignItems: "center", gap: "4px",
          }}
        >
          Ver publicación original →
        </a>
        {post.video_url && (
          <a
            href={post.video_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={e => e.stopPropagation()}
            style={{
              fontSize: "11px", color: net.color, textDecoration: "none",
              opacity: 0.7, display: "flex", alignItems: "center", gap: "4px",
            }}
          >
            Ver video →
          </a>
        )}
      </div>
    </article>
  );
}
