from dotenv import load_dotenv
load_dotenv()  # Carga .env antes que cualquier otro módulo

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from apify_fetcher import fetch_posts
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    networks: List[str] = []
    keywords: List[str] = []
    hashtags: List[str] = []
    accounts: List[str] = []
    date: Optional[str] = None
    strict_mode: bool = False


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Backend SMATA Social Monitor corriendo"}


@app.post("/api/search")
async def search_endpoint(request: SearchRequest):
    try:
        # Armar un término único combinando keywords y hashtags
        partes = request.keywords + [f"#{h.lstrip('#')}" for h in request.hashtags]
        termino = " ".join(partes) if partes else "SMATA"

        print(f"DEBUG: término armado = '{termino}'")

        results = fetch_posts(
            termino=termino,
            fecha_desde=request.date,
            strict_mode=request.strict_mode,
        )

        return {
            "posts": results,
            "summary": {
                "total": len(results),
                "by_network": {"twitter": len(results)},
                "top_keywords": request.keywords,
            }
        }
    except Exception as e:
        print(f"Error interno: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
