from dotenv import load_dotenv
load_dotenv()  # Carga .env antes que cualquier otro módulo

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Literal, Optional
from apify_fetcher import fetch_posts
from docx_generator import generate_docx
import datetime
import io
import os

app = FastAPI()

_allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [o.strip() for o in _allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class SearchRequest(BaseModel):
    networks: List[str] = []
    keywords: List[str] = []
    hashtags: List[str] = []
    accounts: List[str] = []
    date: Optional[str] = None
    strict_mode: bool = False


class PostOut(BaseModel):
    id: str
    network: Literal["twitter", "instagram", "tiktok"]
    author: str
    author_url: str
    text: str
    date: str
    post_url: str
    relevance_score: int
    relevance_level: Literal["alta", "media", "baja"]
    matched_terms: List[str]
    video_url: Optional[str] = None


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Backend SMATA Social Monitor corriendo"}


@app.post("/api/search")
async def search_endpoint(request: SearchRequest):
    try:
        # Hashtags se tratan como keywords (sin '#') porque Google indexa el contenido,
        # no el hashtag literal: '#Smata' como token reduce drásticamente los resultados.
        hashtag_words = [h.lstrip("#") for h in request.hashtags if h and h.strip()]
        partes = request.keywords + hashtag_words
        termino = " ".join(partes) if partes else "SMATA"

        print(f"DEBUG: término armado = '{termino}'")

        raw = fetch_posts(
            termino=termino,
            fecha_desde=request.date,
            strict_mode=request.strict_mode,
            keywords=request.keywords,
            accounts=request.accounts,
        )

        posts = [PostOut(**p) for p in raw]

        by_network: dict[str, int] = {}
        for p in posts:
            by_network[p.network] = by_network.get(p.network, 0) + 1

        return {
            "posts": posts,
            "summary": {
                "total": len(posts),
                "by_network": by_network,
                "top_keywords": request.keywords,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error interno: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class GenerateDocxRequest(BaseModel):
    posts: List[PostOut]


@app.post("/api/generate-docx")
async def generate_docx_endpoint(request: GenerateDocxRequest):
    try:
        post_dicts = [p.model_dump() for p in request.posts]
        docx_bytes = generate_docx(post_dicts)
        fecha = datetime.date.today().strftime("%Y-%m-%d")
        filename = f"informe_smata_{fecha}.docx"
        return StreamingResponse(
            io.BytesIO(docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generando DOCX: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
