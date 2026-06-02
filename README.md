# Monitor de Medios SMATA

Monitor institucional de medios y redes sociales para el Departamento de Prensa de SMATA (sindicato automotriz argentino). Busca publicaciones en X/Twitter, Instagram y TikTok, las puntúa por relevancia con IA y arma informes en Word.

## Stack técnico

| Capa | Tecnología |
|------|------------|
| Frontend | Next.js 14 (App Router) → **Vercel** |
| Backend | FastAPI (Python) → **Render** (`uvicorn`, ver `Procfile`) |
| Búsqueda | SerpAPI (Google con `site:` por red) |
| Scoring IA | Google Gemini 2.5 Flash (cascada de modelos) |
| Informes | `python-docx` |
| Secrets | Variables de entorno en Render (backend) y Vercel (frontend) |

## Arquitectura del backend (3 capas)

El backend respeta una separación estricta por capas; cada cambio se hace de forma quirúrgica sobre la capa que corresponde:

- **Capa 1 — Controlador/API** (`main.py`): endpoints, CORS, modelos Pydantic.
- **Capa 2 — Fetcher ciego** (`fetcher.py`): solo SerpAPI. No conoce a las otras capas.
- **Capa 3 — Normalización/IA** (`normalizer.py`): scoring con Gemini, parseo de URLs, filtros, y la orquestación `fetch_posts`.

Dependencia: `main.py → normalizer.py → fetcher.py`.

## Estructura

```text
/
├── vercel.json                  ← Build del frontend en Vercel
├── .github/workflows/
│   └── keep-warm.yml            ← Ping periódico al backend (anti cold-start)
│
├── frontend/                    ← Next.js 14 (App Router) → Vercel
│   ├── app/
│   │   ├── page.tsx             ← Pantalla principal del monitor
│   │   ├── layout.tsx           ← Layout global, header y toggle de tema
│   │   └── globals.css          ← Variables CSS (tema claro/oscuro + branding)
│   ├── components/
│   │   ├── SearchPanel.tsx      ← Panel de parámetros de búsqueda
│   │   ├── PostCard.tsx         ← Card de un post analizado
│   │   ├── ResultsGrid.tsx      ← Grilla de resultados rankeados
│   │   ├── ReportButton.tsx     ← Botón de informe Word
│   │   ├── ScoreBadge.tsx       ← Badge de score
│   │   └── ThemeToggle.tsx      ← Toggle de tema claro/oscuro
│   └── lib/api.ts               ← Cliente HTTP del backend
│
└── backend/                     ← FastAPI → Render
    ├── main.py                  ← Capa 1: Controlador/API
    ├── fetcher.py               ← Capa 2: Fetcher ciego (SerpAPI)
    ├── normalizer.py            ← Capa 3: Normalización/Filtro/IA (Gemini)
    ├── docx_generator.py        ← Generación del informe Word
    ├── config.py                ← Colores institucionales del informe
    ├── test_fetcher.py          ← Tests de la Capa 2 (pytest)
    ├── test_normalizer.py       ← Tests de la Capa 3 (pytest)
    ├── Procfile                 ← Comando de arranque en Render
    ├── requirements.txt
    └── requirements-dev.txt     ← Dependencias de desarrollo (pytest)
```

## Setup local

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows  (source venv/bin/activate en Linux/Mac)
pip install -r requirements.txt

# Crear backend/.env con las claves:
#   SERPAPI_API_KEY=tu_clave
#   GEMINI_API_KEY=tu_clave

python main.py                   # o: uvicorn main:app --reload
# → http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install

# Crear frontend/.env.local con:
#   NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev
# → http://localhost:3000
```

### Tests

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest -q
```

## Deploy

### Frontend → Vercel

1. Conectar el repositorio en [vercel.com](https://vercel.com).
2. Dejar el **Root Directory** vacío (raíz del proyecto): Vercel usa `vercel.json` y buildea `frontend/`.
3. En **Environment Variables**, agregar `NEXT_PUBLIC_API_URL` = URL pública del backend en Render (ej. `https://tu-backend.onrender.com`). Es una variable de build: requiere redeploy al cambiarla.

### Backend → Render

1. Crear un **Web Service** apuntando a `backend/` (Render usa el `Procfile`: `uvicorn main:app`).
2. En **Environment**, agregar:
   - `SERPAPI_API_KEY`
   - `GEMINI_API_KEY`
   - `ALLOWED_ORIGINS` (opcional; orígenes permitidos por CORS, separados por coma).

> Nota: en el plan free de Render la instancia se duerme tras ~15 min de inactividad y la primera request luego tarda ~40-50 s. El workflow `keep-warm.yml` mitiga esos cold-starts.

## API

### `POST /api/search`

Envía los criterios de búsqueda y retorna los posts parseados y puntuados por la IA.

```json
{
  "keywords": ["SMATA", "paritaria"],
  "hashtags": ["smata"],
  "accounts": [],
  "networks": ["twitter", "instagram", "tiktok"],
  "date": null,
  "smata_mode": false
}
```

`smata_mode`: `true` = filtro estricto (solo SMATA / sector automotor), `false` = monitor de prensa amplio.

### `POST /api/generate-docx`

Recibe los posts seleccionados y devuelve el informe en formato Word (`.docx`).

### Modelo de datos (`Post`)

```ts
interface Post {
  id: string;
  network: "twitter" | "instagram" | "tiktok";
  author: string;
  author_url: string;
  text: string;
  date: string;
  post_url: string;
  relevance_score: number;          // 0-100, calculado por Gemini
  relevance_level: "alta" | "media" | "baja";
  matched_terms: string[];
  video_url: string | null;
}
```

## Branding SMATA

Colores institucionales aplicados en la interfaz:

```css
--smata-green-dark:  #1B4D2E;
--smata-green-mid:   #2E7D32;
--smata-green-light: #4CAF50;
--smata-green-pale:  #E8F5E9;
--smata-gold:        #FFC107;
```
