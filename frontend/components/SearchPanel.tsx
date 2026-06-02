"use client";
import { useState, KeyboardEvent } from "react";
import countries from "i18n-iso-countries";
import esLocale from "i18n-iso-countries/langs/es.json";
import type { SearchRequest } from "@/lib/api";

// Lista completa de países (250) con nombres en español, vía librería: el value
// es el código ISO 3166-1 alpha-2 en minúscula, que el backend usa como 'gl' de
// SerpAPI (B.4). Así no mantenemos ninguna lista hardcodeada.
countries.registerLocale(esLocale);
const COUNTRY_OPTIONS = Object.entries(countries.getNames("es"))
  .map(([code, name]) => ({ code: code.toLowerCase(), name }))
  .sort((a, b) => a.name.localeCompare(b.name, "es"));

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
  const [country, setCountry] = useState("ar");
  const [smataMode, setSmataMode] = useState(false);

  // B.2: el Modo SMATA solo rige si el país es Argentina. Fuera de AR se fuerza OFF
  // y el switch queda deshabilitado.
  const isArgentina = country === "ar";

  const toggleNetwork = (id: string) =>
    setNetworks(prev => prev.includes(id) ? prev.filter(n => n !== id) : [...prev, id]);

  const handleCountryChange = (code: string) => {
    setCountry(code);
    if (code !== "ar") setSmataMode(false);  // apaga el Modo SMATA fuera de Argentina
  };

  const handleSearch = () => {
    if (!keywords.length && !hashtags.length) return;
    onSearch({
      keywords, hashtags, accounts,
      networks: networks as SearchRequest["networks"],
      date,
      country,
      smata_mode: isArgentina ? smataMode : false,
    });
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

      <div className="form-group">
        <label className="form-label">País</label>
        <select
          className="form-input"
          value={country}
          onChange={e => handleCountryChange(e.target.value)}
          style={{ colorScheme: "dark", cursor: "pointer" }}
        >
          {COUNTRY_OPTIONS.map(c => (
            <option key={c.code} value={c.code}>{c.name}</option>
          ))}
        </select>
        <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "6px" }}>
          Define la región de los resultados. El Modo SMATA solo aplica en Argentina.
        </p>
      </div>

      <TagInput label="Palabras clave" placeholder="Ej: SMATA, paritaria..." tags={keywords} setTags={setKeywords} />
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

      <div
        title={isArgentina ? "" : "El Modo SMATA solo está disponible con el país en Argentina"}
        style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "12px", borderRadius: "var(--radius-sm)",
        background: smataMode ? "rgba(255,193,7,0.1)" : "var(--input-bg)",
        border: `1px solid ${smataMode ? "rgba(255,193,7,0.4)" : "var(--border-color)"}`,
        transition: "all 0.2s",
        cursor: isArgentina ? "pointer" : "not-allowed",
        opacity: isArgentina ? 1 : 0.5,
      }} onClick={() => { if (isArgentina) setSmataMode(!smataMode); }}>
        <div>
          <div style={{ fontSize: "13px", fontWeight: 600, color: smataMode ? "var(--smata-gold)" : "var(--text-primary)" }}>
            Modo SMATA
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
            {!isArgentina
              ? "Solo disponible con país: Argentina"
              : smataMode ? "Estricto: solo SMATA / sector automotor" : "Amplio: monitoreo de prensa general"}
          </div>
        </div>
        <div style={{
          width: "38px", height: "22px", borderRadius: "11px",
          background: smataMode ? "var(--smata-gold)" : "var(--track-off)",
          position: "relative", transition: "all 0.2s",
        }}>
          <div style={{
            position: "absolute", top: "3px", left: smataMode ? "19px" : "3px",
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
