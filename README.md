Markdown
# SMATA Social Monitor v2

Monitor institucional de redes sociales para el Departamento de Prensa de SMATA (sindicato automotriz argentino).

## Stack Técnico

| Capa | Tecnología |
|------|------------|
| Frontend | Next.js 14 (App Router) → Vercel (Arquitectura Híbrida) |
| Backend | FastAPI (Python) → Serverless en Vercel (`/api`) |
| Integraciones | SerpAPI (Búsqueda en X/Twitter) y Google Gemini 2.5 Flash |
| Secrets | Variables de entorno `.env` en Backend y Vercel |

## Estructura

/
├── vercel.json        ← Configuración de ruteo híbrido para Vercel
├── frontend/          ← Next.js 14
│   ├── app/
│   │   ├── page.tsx           ← Pantalla principal del monitor
│   │   ├── layout.tsx         ← Layout global con identidad SMATA
│   │   └── globals.css        ← Variables CSS de branding
│   └── components/
│       ├── SearchPanel.tsx    ← Sidebar de parámetros de búsqueda
│       ├── PostCard.tsx       ← Card con el contenido del post analizado
│       └── ResultsGrid.tsx    ← Grilla de resultados rankeados
│
└── backend/           ← FastAPI
├── api/
│   └── index.py           ← Entrada principal adaptada para Vercel Serverless
├── main.py                ← Endpoints locales
├── apify_fetcher.py       ← Extractor de posts con SerpAPI y análisis de Gemini
├── filters.py             ← Scoring semántico y filtrado
├── config.py              ← Constantes, prompts y términos clave
└── requirements.txt       ← Dependencias del backend


## Setup Local

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate         # En Windows
pip install -r requirements.txt

# Copiar y completar variables de entorno
copy .env.example .env
# Agregar las siguientes claves en .env:
# SERPAPI_API_KEY=tu_clave_aqui
# GEMINI_API_KEY=tu_clave_aqui

python main.py
# → http://localhost:8000
Frontend
Bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
Variable de entorno del frontend
Crear frontend/.env.local:

NEXT_PUBLIC_API_URL=http://localhost:8000
Deploy en Vercel
Gracias al archivo vercel.json en la raíz, el despliegue del frontend y backend se realiza de forma unificada en un solo paso:

Conectar el repositorio de GitHub en vercel.com

Dejar el Root Directory vacío (raíz del proyecto /) para que lea el archivo vercel.json.

En la sección Environment Variables de Vercel, agregar las credenciales requeridas por el backend:

SERPAPI_API_KEY

GEMINI_API_KEY

Darle a Deploy. Vercel mapeará automáticamente el backend bajo las rutas /api/* y el frontend en la raíz.

API Endpoints
POST /api/search
Envía los criterios y retorna los posts parseados y puntuados por la IA.

JSON
{
  "keywords": ["SMATA", "paritaria"],
  "hashtags": ["smata"],
  "accounts": [],
  "networks": ["twitter", "instagram", "tiktok"],
  "strict_mode": false
}
Modelo de Datos (Post)
TypeScript
{
  id: string,
  network: "twitter" | "instagram" | "tiktok",
  author: string,
  author_url: string,
  text: string,
  date: string,
  post_url: string,
  relevance_score: number,   // Escala 0-100 calculada por Gemini
  matched_terms: string[]
}
Branding SMATA
Colores corporativos aplicados en la interfaz para mantener la identidad institucional:

CSS
--smata-green-dark:  #1B4D2E
--smata-green-mid:   #2E7D32
--smata-green-light: #4CAF50
--smata-green-pale:  #E8F5E9
--smata-gold:        #FFC107
