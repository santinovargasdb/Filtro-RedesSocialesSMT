from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import apify_fetcher
import filters
import docx_generator
import datetime
import os

app = FastAPI(title="SMATA Social Monitor API")

# Configuración de CORS con tu URL de Vercel
FRONTEND_URL = "https://filtro-redes-sociales-smt.vercel.app"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"], # Localhost para pruebas
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CLASE MEJORADA: Valores por defecto para evitar errores de validación
class SearchRequest(BaseModel):
    keywords: List[str] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)
    accounts: List[str] = Field(default_factory=list)
    networks: List[str] = Field(default_factory=list)
    date: str = Field(default_factory=lambda: datetime.date.today().isoformat())
    strict_mode: bool = False

class Post(BaseModel):
    id: str
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
        # LOG DE DEBUG: Esto aparecerá en Railway para saber qué llega del frontend
        print(f"DEBUG: Petición recibida -> Networks: {request.networks}, Keywords: {request.keywords}")
        
        # 1. Fetch posts desde Apify
        # Si no se eligen redes, por defecto busca en twitter para no romper el actor
        selected_networks = request.networks if request.networks else ["twitter"]
        
        raw_posts = apify_fetcher.fetch_posts(
            networks=selected_networks,
            keywords=request.keywords,
            hashtags=request.hashtags,
            accounts=request.accounts,
            date_since=request.date
        )
        
        # 2. Aplicar filtros y scoring
        processed_posts = filters.filter_posts(raw_posts, strict_mode=request.strict_mode)
        
        # 3. Resumen de resultados
        summary = {
            "total": len(processed_posts),
            "by_network": {
                "twitter": len([p for p in processed_posts if p["network"] == "twitter"]),
                "instagram": len([p for p in processed_posts if p["network"] == "instagram"]),
                "tiktok": len([p for p in processed_posts if p["network"] == "tiktok"]),
            },
            "top_keywords": request.keywords
        }
        
        return {
            "posts": processed_posts,
            "summary": summary
        }
    except Exception as e:
        print(f"ERROR CRÍTICO: {str(e)}")
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
    # Railway requiere leer la variable de entorno PORT
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
