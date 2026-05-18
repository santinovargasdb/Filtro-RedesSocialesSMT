from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import apify_fetcher
import filters
import docx_generator
import datetime
import os

app = FastAPI()

# --- AQUÍ CONFIGURAMOS LOS PERMISOS DE CORS ---
origins = [
    "https://filtro-redes-sociales-smt.vercel.app",  # Tu URL de Vercel
    "http://localhost:3000",                         # Por si pruebas en tu PC local
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # Permite el acceso a estas webs
    allow_credentials=True,
    allow_methods=["*"],              # Permite todos los métodos (POST, GET, etc.)
    allow_headers=["*"],              # Permite todos los headers
)
# ----------------------------------------------

# ... abajo siguen tus rutas normales, como app.post("/api/search") ...

class SearchRequest(BaseModel):
    keywords: List[str]
    hashtags: List[str]
    accounts: List[str]
    networks: List[str]
    date: str = datetime.date.today().isoformat()
    strict_mode: bool = False

class Post(BaseModel):
    id: Optional[str] = ""
    network: str
    author: str
    author_url: str
    text: str
    date: str
    post_url: str
    video_url: Optional[str] = None
    relevance_score: Optional[int] = 0
    matched_terms: Optional[List[str]] = []

@app.post("/api/search")
async def search_posts(request: SearchRequest):
    try:
        # 1. Fetch posts from Apify
        raw_posts = apify_fetcher.fetch_posts(
            networks=request.networks,
            keywords=request.keywords,
            hashtags=request.hashtags,
            accounts=request.accounts,
            date_since=request.date
        )
        
        # 2. Apply filters and scoring
        processed_posts = filters.filter_posts(raw_posts, strict_mode=request.strict_mode)
        
        # 3. Generate summary
        summary = {
            "total": len(processed_posts),
            "by_network": {
                "twitter": len([p for p in processed_posts if p["network"] == "twitter"]),
                "instagram": len([p for p in processed_posts if p["network"] == "instagram"]),
                "tiktok": len([p for p in processed_posts if p["network"] == "tiktok"]),
            },
            "top_keywords": request.keywords # Simplified for now
        }
        
        return {
            "posts": processed_posts,
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-docx")
async def generate_report(posts: List[Post]):
    try:
        docx_bytes = docx_generator.generate_docx([p.dict() for p in posts])
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=informe_smata_{datetime.date.today()}.docx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    import os
    # Esto lee el puerto que Railway te asigna dinámicamente en sus servidores
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
