import type { Metadata } from "next";
import "./globals.css";
import ThemeToggle from "@/components/ThemeToggle";

export const metadata: Metadata = {
  title: "Monitor de Medios SMT",
  description: "Monitor institucional de medios y redes sociales — Departamento de Prensa SMATA",
};

// Aplica el tema guardado ANTES del primer paint para evitar el flash claro→oscuro.
// Por defecto: claro (no se setea data-theme). Solo aplica 'dark' si está guardado.
const themeInitScript = `try{if(localStorage.getItem('theme')==='dark'){document.documentElement.setAttribute('data-theme','dark');}}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body>
        <header style={{
          background: "linear-gradient(90deg, var(--smata-green-dark) 0%, #1e5c35 100%)",
          borderBottom: "1px solid rgba(76,175,80,0.2)",
          padding: "0 32px",
          height: "60px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          position: "sticky",
          top: 0,
          zIndex: 100,
          boxShadow: "0 2px 20px rgba(0,0,0,0.5)",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <div style={{
              width: "36px", height: "36px", borderRadius: "8px",
              background: "linear-gradient(135deg, var(--smata-green-mid), var(--smata-green-light))",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontWeight: 800, fontSize: "14px", color: "white", letterSpacing: "-0.5px"
            }}>SM</div>
            <div>
              <div style={{ fontWeight: 700, fontSize: "15px", letterSpacing: "0.02em", color: "white" }}>
                Monitor de Medios SMT
              </div>
              <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.6)", fontWeight: 400 }}>
                Departamento de Prensa · SMATA
              </div>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{
              fontSize: "12px", color: "rgba(255,255,255,0.75)", fontWeight: 500,
              padding: "4px 12px", borderRadius: "20px",
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.15)"
            }}>
              {new Date().toLocaleDateString("es-AR", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
            </div>
            <ThemeToggle />
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
