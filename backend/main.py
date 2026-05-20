from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from apify_fetcher import fetch_posts

app = FastAPI(title="SMATA Social Monitor API", version="1.0.0")

# Configuración de CORS imprescindible para que tu frontend en Vercel pueda consultar a Railway
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite peticiones desde cualquier origen (Vercel local/producción)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Definición del esquema de los datos que envía el frontend al presionar "Buscar"
class SearchRequest(BaseModel):
    networks: List[str]
    keywords: Optional[List[str]] = []
    hashtags: Optional[List[str]] = []
    accounts: Optional[List[str]] = []
    date_since: Optional[str] = None

@app.get("/")
def read_root():
    return {"status": "online", "message": "SMATA Backend funcionando con Google AI Studio"}

@app.post("/api/search")
async def search_posts(request: SearchRequest):
    """
    Endpoint principal consumido por Vercel para ejecutar la extracción
    gratuita y el filtrado por Inteligencia Artificial.
    """
    results = fetch_posts(
        networks=request.networks,
        keywords=request.keywords,
        hashtags=request.hashtags,
        accounts=request.accounts,
        date_since=request.date_since
    )
    return {"posts": results}
