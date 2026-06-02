from dotenv import load_dotenv
load_dotenv()  # Carga .env antes que cualquier otro módulo

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Literal, Optional
from normalizer import fetch_posts, UpstreamUnavailableError
from docx_generator import generate_docx
import datetime
import io
import os

app = FastAPI()

# CORS abierto a cualquier origen. Vercel genera un subdominio distinto en cada
# preview/deploy, así que en esta etapa de pruebas de Prensa permitimos todos los
# orígenes con el comodín. El comodín solo es válido con allow_credentials=False
# (que es nuestro caso: el frontend no manda cookies ni auth en el fetch).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    networks: List[str] = []
    keywords: List[str] = []
    hashtags: List[str] = []
    accounts: List[str] = []
    date: Optional[str] = None
    # Switch "Modo SMATA": True = criterio hiper-estricto (solo SMATA/automotor),
    # False = monitor de prensa amplio (no exige mención de SMATA).
    smata_mode: bool = False
    # Compat hacia atrás: el frontend viejo enviaba 'strict_mode'. Si llega en True
    # mientras conviven builds durante el deploy, se respeta como Modo SMATA.
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
    # RENDER_GIT_COMMIT lo inyecta Render con el SHA del deploy en curso; en local
    # no existe, así que cae en "dev". Sirve para confirmar qué versión está viva.
    commit = os.environ.get("RENDER_GIT_COMMIT", "dev")
    return {
        "status": "ok",
        "message": "Backend Monitor de Medios SMATA corriendo",
        "commit": commit[:7] if commit else "dev",
    }


@app.post("/api/search")
async def search_endpoint(request: SearchRequest):
    try:
        # Hashtags se tratan como keywords (sin '#') porque Google indexa el contenido,
        # no el hashtag literal: '#Smata' como token reduce drásticamente los resultados.
        hashtag_words = [h.lstrip("#") for h in request.hashtags if h and h.strip()]
        partes = request.keywords + hashtag_words
        termino = " ".join(partes) if partes else "SMATA"

        # smata_mode es el switch nuevo; strict_mode queda como alias de compat.
        smata_mode = request.smata_mode or request.strict_mode

        print(f"Keywords recibidas: {request.keywords}, Modo SMATA: {smata_mode}")
        print(f"DEBUG: término armado = '{termino}' | smata_mode={smata_mode}")

        raw = fetch_posts(
            termino=termino,
            fecha_desde=request.date,
            smata_mode=smata_mode,
            keywords=request.keywords,
            accounts=request.accounts,
            networks=request.networks,
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
    except UpstreamUnavailableError as e:
        # SerpAPI/Gemini sin cuota o caídos: 503 con mensaje claro para el front.
        print(f"Upstream no disponible: {e}")
        raise HTTPException(status_code=503, detail=str(e))
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
