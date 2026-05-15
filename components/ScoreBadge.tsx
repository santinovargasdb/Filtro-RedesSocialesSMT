"use client";

interface ScoreBadgeProps {
  score: number;
}

export default function ScoreBadge({ score }: ScoreBadgeProps) {
  const getColors = () => {
    if (score >= 70) return { bg: "rgba(76,175,80,0.2)", border: "rgba(76,175,80,0.5)", text: "#4CAF50" };
    if (score >= 40) return { bg: "rgba(255,193,7,0.2)", border: "rgba(255,193,7,0.5)", text: "#FFC107" };
    return { bg: "rgba(120,120,120,0.15)", border: "rgba(120,120,120,0.3)", text: "#888" };
  };

  const { bg, border, text } = getColors();
  const label = score >= 70 ? "Alta" : score >= 40 ? "Media" : "Baja";

  return (
    <div style={{
      display: "inline-flex", alignItems: "center", gap: "5px",
      background: bg, border: `1px solid ${border}`,
      borderRadius: "20px", padding: "3px 10px",
      fontSize: "12px", fontWeight: 700, color: text,
      whiteSpace: "nowrap",
    }}>
      <span style={{
        width: "6px", height: "6px", borderRadius: "50%",
        background: text, display: "inline-block",
        boxShadow: `0 0 6px ${text}`,
      }} />
      {score} · {label}
    </div>
  );
}
