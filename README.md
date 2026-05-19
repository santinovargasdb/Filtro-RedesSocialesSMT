# SMATA Social Monitor v2

Monitor institucional de redes sociales para el Departamento de Prensa de SMATA (sindicato automotriz argentino).

## Stack Técnico

| Capa | Tecnología |
|------|------------|
| Frontend | Next.js 14 (App Router) → Vercel |
| Backend | FastAPI (Python) → Railway / Render |
| Scraping | Apify Python SDK |
| PDF | WeasyPrint |
| Secrets | Variables de entorno `.env` |

## Estructura

```
/
├── frontend/          ← Next.js 14
│   ├── app/
│   │   ├── page.tsx           ← pantalla principal
│   │   ├── layout.tsx         ← layout global SMATA
│   │   └── globals.css        ← variables CSS branding
│   ├── components/
│   │   ├── SearchPanel.tsx    ← sidebar búsqueda
│   │   ├── PostCard.tsx       ← card de post
│   │   ├── ResultsGrid.tsx    ← grilla rankeada
│   │   ├── ReportButton.tsx   ← botón PDF
│   │   └── ScoreBadge.tsx     ← badge relevancia
│   └── lib/
│       └── api.ts             ← fetch al backend
│
└── backend/           ← FastAPI
    ├── main.py                ← endpoints
    ├── apify_fetcher.py       ← integración Apify
    ├── filters.py             ← scoring semántico
    ├── pdf_generator.py       ← generación PDF
    ├── config.py              ← constantes y términos
    └── requirements.txt
```

## Setup Local

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate         # Windows
pip install -r requirements.txt

# Copiar y completar variables de entorno
copy .env.example .env
# Agregar APIFY_API_KEY en .env

python main.py
# → http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### Variable de entorno del frontend

Crear `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Deploy

### Backend → Railway

1. Conectar repo en [railway.app](https://railway.app)
2. Configurar **Root Directory** = `backend`
3. Agregar variable de entorno `APIFY_API_KEY`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Frontend → Vercel

1. Conectar repo en [vercel.com](https://vercel.com)
2. Configurar **Root Directory** = `frontend`
3. Agregar variable de entorno `NEXT_PUBLIC_API_URL=<URL del backend Railway>`

## API Endpoints

### `POST /api/search`
```json
{
  "keywords": ["SMATA", "paritaria"],
  "hashtags": ["sindicato"],
  "accounts": [],
  "networks": ["twitter", "instagram", "tiktok"],
  "date": "2026-05-14",
  "strict_mode": false
}
```

### `POST /api/generate-pdf`
Body: array de objetos `Post` seleccionados. Retorna PDF binario.

## Modelo Post

```typescript
{
  id: string,
  network: "twitter" | "instagram" | "tiktok",
  author: string,
  author_url: string,
  text: string,
  date: string,
  post_url: string,
  relevance_score: number,   // 0-100
  matched_terms: string[]
}
```

## Branding SMATA

```css
--smata-green-dark:  #1B4D2E
--smata-green-mid:   #2E7D32
--smata-green-light: #4CAF50
--smata-green-pale:  #E8F5E9
--smata-gold:        #FFC107
```
