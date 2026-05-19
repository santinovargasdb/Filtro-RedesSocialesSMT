from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from apify_fetcher import fetch_posts  # Asegúrate de que coincida con tu importación actual
from collections import Counter
import os

app = FastAPI()

# ========================================================
# 1. CONFIGURACIÓN DE CORS MIDDLEWARE (Siempre arriba)
# ========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite peticiones desde cualquier origen de forma temporal
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ========================================================
# 2. MODELOS DE DATOS (Ajustalo si tus campos se llaman distinto)
# ========================================================
class SearchRequest(BaseModel):
    networks: List[str]
    keywords: List[str]
    hashtags: List[str]
    accounts: List[str]
    date_since: Optional[str] = None

# ========================================================
# 3. RUTAS Y ENDPOINTS
# ========================================================
@app.get("/")
def read_root():
    return {"status": "ok", "message": "Backend de Filtro de Redes Sociales corriendo perfectamente"}
    
@app.post("/api/search")
async def search_endpoint(request: SearchRequest):
    try:
        results = fetch_posts(
            networks=request.networks,
            keywords=request.keywords,
            hashtags=request.hashtags,
            accounts=request.accounts,
            date_since=request.date_since
        )

        # Armar summary
        by_network = Counter(p["network"] for p in results)
        all_terms = [term for p in results for term in p.get("matched_terms", [])]
        top_keywords = [term for term, _ in Counter(all_terms).most_common(5)]

        return {
            "posts": results,
            "summary": {
                "total": len(results),
                "by_network": dict(by_network),
                "top_keywords": top_keywords,
            }
        }
    except Exception as e:
        print(f"Error interno: {e}")
        return {"status": "error", "message": str(e)}
# ========================================================
# 4. CONFIGURACIÓN DEL PUERTO DINÁMICO PARA RAILWAY
# ========================================================
if __name__ == "__main__":
    import uvicorn
    # Railway asigna un puerto aleatorio en la variable de entorno PORT
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
