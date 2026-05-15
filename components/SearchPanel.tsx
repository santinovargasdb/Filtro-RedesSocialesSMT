"use client";
import { useState, KeyboardEvent } from "react";
import type { SearchRequest } from "@/lib/api";

interface TagInputProps {
  label: string;
  placeholder: string;
  tags: string[];
  setTags: (tags: string[]) => void;
  prefix?: string;
}

function TagInput({ label, placeholder, tags, setTags, prefix = "" }: TagInputProps) {
  const [input, setInput] = useState("");

  const addTag = () => {
    const val = input.trim().replace(/^[#@]/, "");
    if (val && !tags.includes(val)) setTags([...tags, val]);
    setInput("");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") { e.preventDefault(); addTag(); }
    if (e.key === "Backspace" && !input && tags.length > 0) setTags(tags.slice(0, -1));
  };

  return (
    <div className="form-group">
      <label className="form-label">{label}</label>
      <div className="tag-input-wrapper" onClick={() => document.getElementById(`ti-${label}`)?.focus()}>
        {tags.map(t => (
          <span key={t} className="tag">
            {prefix}{t}
            <button className="tag-remove" onClick={() => setTags(tags.filter(x => x !== t))}>×</button>
          </span>
        ))}
        <input
          id={`ti-${label}`}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={addTag}
          placeholder={tags.length === 0 ? placeholder : ""}
        />
      </div>
    </div>
  );
}

interface SearchPanelProps {
  onSearch: (params: SearchRequest) => void;
  loading: boolean;
}

const NETWORKS = [
  { id: "twitter", label: "X / Twitter", color: "#1DA1F2", icon: "𝕏" },
  { id: "instagram", label: "Instagram", color: "#E1306C", icon: "📷" },
  { id: "tiktok", label: "TikTok", color: "#000000", icon: "♪" },
];

export default function SearchPanel({ onSearch, loading }: SearchPanelProps) {
  const [keywords, setKeywords] = useState<string[]>([]);
  const [hashtags, setHashtags] = useState<string[]>([]);
  const [accounts, setAccounts] = useState<string[]>([]);
  const [networks, setNetworks] = useState<string[]>(["twitter", "instagram", "tiktok"]);
  const [date, setDate] = useState(new Date().toISOString().split("T")[0]);
  const [strictMode, setStrictMode] = useState(false);

  const toggleNetwork = (id: string) =>
    setNetworks(prev => prev.includes(id) ? prev.filter(n => n !== id) : [...prev, id]);

  const handleSearch = () => {
    if (!keywords.length && !hashtags.length) return;
    onSearch({ keywords, hashtags, accounts, networks: networks as SearchRequest["networks"], date, strict_mode: strictMode });
  };

  return (
    <aside style={{
      width: "300px",
      minWidth: "300px",
      background: "var(--bg-secondary)",
      borderRight: "1px solid var(--border-color)",
      padding: "24px 20px",
      display: "flex",
      flexDirection: "column",
      gap: "20px",
      overflowY: "auto",
      height: "calc(100vh - 60px)",
      position: "sticky",
      top: "60px",
    }}>
      <div>
        <h2 style={{ fontSize: "13px", fontWeight: 700, color: "var(--smata-green-light)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "4px" }}>
          Configurar búsqueda
        </h2>
        <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>Presioná Enter para agregar cada término</p>
      </div>

      <hr className="divider" />

      <TagInput label="Keywords" placeholder="Ej: SMATA, paritaria..." tags={keywords} setTags={setKeywords} />
      <TagInput label="Hashtags" placeholder="#sindicato, #automotriz..." tags={hashtags} setTags={setHashtags} prefix="#" />
      <TagInput label="Cuentas (opcional)" placeholder="@smataoficial..." tags={accounts} setTags={setAccounts} prefix="@" />

      <hr className="divider" />

      <div className="form-group">
        <label className="form-label">Redes sociales</label>
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {NETWORKS.map(net => (
            <label key={net.id} style={{
              display: "flex", alignItems: "center", gap: "10px", cursor: "pointer",
              padding: "8px 12px", borderRadius: "var(--radius-sm)",
              border: `1px solid ${networks.includes(net.id) ? net.color + "66" : "var(--border-color)"}`,
              background: networks.includes(net.id) ? net.color + "15" : "transparent",
              transition: "all 0.2s",
            }}>
              <input
                type="checkbox"
                checked={networks.includes(net.id)}
                onChange={() => toggleNetwork(net.id)}
                style={{ accentColor: net.color, width: "16px", height: "16px" }}
              />
              <span style={{ fontSize: "13px", fontWeight: 500, color: networks.includes(net.id) ? net.color : "var(--text-secondary)" }}>
                {net.icon} {net.label}
              </span>
            </label>
          ))}
        </div>
      </div>

      <hr className="divider" />

      <div className="form-group">
        <label className="form-label">Fecha desde</label>
        <input type="date" value={date} onChange={e => setDate(e.target.value)} className="form-input"
          style={{ colorScheme: "dark" }} />
      </div>

      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "12px", borderRadius: "var(--radius-sm)",
        background: strictMode ? "rgba(255,193,7,0.1)" : "rgba(255,255,255,0.04)",
        border: `1px solid ${strictMode ? "rgba(255,193,7,0.4)" : "var(--border-color)"}`,
        transition: "all 0.2s", cursor: "pointer",
      }} onClick={() => setStrictMode(!strictMode)}>
        <div>
          <div style={{ fontSize: "13px", fontWeight: 600, color: strictMode ? "var(--smata-gold)" : "var(--text-primary)" }}>
            Strict SMATA Mode
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Solo posts con score ≥ 50</div>
        </div>
        <div style={{
          width: "38px", height: "22px", borderRadius: "11px",
          background: strictMode ? "var(--smata-gold)" : "rgba(255,255,255,0.1)",
          position: "relative", transition: "all 0.2s",
        }}>
          <div style={{
            position: "absolute", top: "3px", left: strictMode ? "19px" : "3px",
            width: "16px", height: "16px", borderRadius: "50%",
            background: "white", transition: "left 0.2s",
          }} />
        </div>
      </div>

      <button
        className="btn btn-primary w-full"
        onClick={handleSearch}
        disabled={loading || (!keywords.length && !hashtags.length)}
        style={{ marginTop: "auto", padding: "12px", fontSize: "15px" }}
      >
        {loading ? (
          <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ animation: "spin 1s linear infinite", display: "inline-block" }}>⟳</span>
            Buscando...
          </span>
        ) : "🔍 Buscar"}
      </button>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </aside>
  );
}
